"""
LLM Proxy orchestration.

Coordinates policy checks, cache lookup, outbound LLM calls, logging, and
response formatting for the `/api/proxy` endpoint. The typical flow is:

1) Validate request shape and size; normalize inputs.
2) Run PolicyChecker for API key validity, banned keywords, and security rules.
3) Query LLMCacheLookup for a semantic hit; if found, return cached result.
4) On cache miss, call the configured LLM provider, capture response, and
   persist via cache_llm_response for future semantic hits.
5) Persist a ProxyLog entry and update metrics; format the response payload.

Extensibility:
- Swap out embedding model or LLM provider.
- Adjust thresholds, TTLs, and policy configuration via app config.
"""

import time
import uuid
import json
import logging
from typing import Dict, Any, Optional, Tuple
from flask import request, current_app
import os
import random
from .policy_checks import policy_checker, PolicyCheckResult
from .cache_lookup import llm_cache_lookup
from .proxy_logger import proxy_logger, metrics_collector
from .token_utils import count_tokens as tk_count_tokens, estimate_cost as tk_estimate_cost
from ..models import db
from ..models import ProxyAnalytics, ProviderAnalytics


class LLMProxyResponse:
    """Response from the LLM proxy."""
    
    def __init__(self, success: bool, data: Dict[str, Any] = None, 
                 status_code: int = 200, error_code: str = None, 
                 message: str = None, from_cache: bool = False):
        self.success = success
        self.data = data or {}
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.from_cache = from_cache
    
    def to_dict(self) -> Dict[str, Any]:
        """Return raw data for API response (already shaped)."""
        return self.data


class LLMProxy:
    """Main LLM proxy class."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_request(self, request_data: Dict[str, Any], 
                       client_ip: str = None, user_agent: str = None) -> LLMProxyResponse:
        """
        Process an LLM request through the proxy.
        
        Args:
            request_data: Request data dictionary
            client_ip: Client IP address
            user_agent: User agent string
            
        Returns:
            LLMProxyResponse with the result
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            # Log incoming request
            proxy_logger.log_request(request_data, client_ip, user_agent, request_id)
            
            # Extract API key and text
            api_key = request_data.get('api_key', '').strip()
            text = request_data.get('text', '')
            model = (request_data.get('model') or 'gpt-4o')
            temperature = request_data.get('temperature') if request_data.get('temperature') is not None else 0.7
            
            # 1. Policy checks
            policy_result = policy_checker.run_all_checks(api_key, text, client_ip)
            if not policy_result.passed:
                # OpenAI-like chat completion with textual reason for errors
                reason = policy_result.message or 'Request validation failed'
                status = 401 if policy_result.error_code in ['API_KEY_NOT_FOUND','API_KEY_INACTIVE','USER_ACCOUNT_INACTIVE'] else 400
                error_chat = {
                    'id': f"chatcmpl-{uuid.uuid4().hex[:29]}",
                    'object': 'chat.completion',
                    'created': int(time.time()),
                    'model': model,
                    'choices': [
                        {
                            'index': 0,
                            'message': {
                                'role': 'assistant',
                                'content': f"Proxy error ({policy_result.error_code}): {reason}"
                            },
                            'finish_reason': 'stop'
                        }
                    ],
                    'usage': {
                        'prompt_tokens': 0,
                        'completion_tokens': 0,
                        'total_tokens': 0
                    },
                    'proxy_id': request_id
                }
                response = LLMProxyResponse(
                    success=False,
                    status_code=status,
                    error_code=policy_result.error_code,
                    message=reason,
                    data=error_chat
                )
                
                # Log response
                processing_time = int((time.time() - start_time) * 1000)
                proxy_logger.log_response(request_id, response.to_dict(), 
                                        response.status_code, processing_time,
                                        client_ip=client_ip, user_agent=user_agent, data=request_data,
                                        model=model, from_cache=False)
                metrics_collector.record_request('/api/proxy', response.status_code, 
                                               processing_time, client_ip)
                
                return response
            
            # Get validated data from policy check
            api_key_record = policy_result.details['api_key_record']
            user = policy_result.details['user']
            # Cache scope is per-user (multiple API keys share a cache)
            user_scope = getattr(user, 'user_id', None) or str(user.id)
            
            # 2. Token count for input using tiktoken
            try:
                input_tokens = tk_count_tokens(text or '', model)
            except Exception:
                input_tokens = 0

            # 3. Check cache
            cache_found, cached_response = llm_cache_lookup.get_llm_response(
                user_scope, request_data, model, temperature
            )
            
            if cache_found:
                token_info = None
                cost_info = None
                # Return cached provider-like response with extra token_id
                response_chat = cached_response['response'] or {}
                response_chat['proxy_id'] = request_id
                response = LLMProxyResponse(
                    success=True,
                    status_code=200,
                    data=response_chat,
                    from_cache=True
                )
                
                # Log response
                processing_time = int((time.time() - start_time) * 1000)
                proxy_logger.log_response(request_id, response.to_dict(), 
                                        response.status_code, processing_time,
                                        api_key_record, client_ip, user_agent, data=request_data,
                                        model=model, from_cache=True,
                                        token_info=token_info, cost_info=cost_info)
                metrics_collector.record_request('/api/proxy', response.status_code, 
                                               processing_time, client_ip)
                
                return response
            
            # 4. Forward to LLM service
            llm_response = self._call_llm_service(text, model, temperature)
            
            if llm_response['success']:
                # Cache the response
                llm_cache_lookup.cache_llm_response(
                    user_scope, request_data, llm_response['data'], 
                    ttl=3600, model=model, temperature=temperature
                )
                
                # Provider-like response with extra token_id
                chat = llm_response['data']
                chat['proxy_id'] = request_id
                response = LLMProxyResponse(
                    success=True,
                    status_code=200,
                    data=chat
                )
            else:
                # OpenAI-like chat completion with textual reason on LLM service error
                reason = 'LLM service temporarily unavailable. Please try again later.'
                error_chat = {
                    'id': f"chatcmpl-{uuid.uuid4().hex[:29]}",
                    'object': 'chat.completion',
                    'created': int(time.time()),
                    'model': model,
                    'choices': [
                        {
                            'index': 0,
                            'message': {
                                'role': 'assistant',
                                'content': f"Proxy error (LLM_SERVICE_ERROR): {reason}"
                            },
                            'finish_reason': 'stop'
                        }
                    ],
                    'usage': {
                        'prompt_tokens': 0,
                        'completion_tokens': 0,
                        'total_tokens': 0
                    },
                    'proxy_id': request_id
                }
                response = LLMProxyResponse(
                    success=False,
                    status_code=500,
                    error_code='LLM_SERVICE_ERROR',
                    message=reason,
                    data=error_chat
                )
            
            # Log response
            processing_time = int((time.time() - start_time) * 1000)
            proxy_logger.log_response(request_id, response.to_dict(), 
                                    response.status_code, processing_time,
                                    api_key_record, client_ip, user_agent, data=request_data,
                                    model=model, from_cache=False,
                                    token_info=None, cost_info=None)
            metrics_collector.record_request('/api/proxy', response.status_code, 
                                           processing_time, client_ip)

            # Persist analytics
            try:
                self._persist_analytics(
                    request_id=request_id,
                    api_key_record=api_key_record,
                    user=user,
                    model=model,
                    temperature=temperature,
                    cache_hit=False,
                    response=response,
                    processing_time_ms=processing_time,
                    token_info=locals().get('token_info'),
                    cost_info=locals().get('cost_info'),
                    provider=llm_response.get('provider'),
                    llm_data=llm_response.get('data') if llm_response.get('success') else None
                )
            except Exception as e:
                self.logger.error(f"Failed to persist analytics: {str(e)}")
            
            # Update API key last used
            if response.success:
                try:
                    api_key_record.update_last_used()
                    from ..models import db
                    db.session.commit()
                except Exception as e:
                    self.logger.error(f"Failed to update last_used: {str(e)}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing LLM request: {str(e)}", exc_info=True)
            
            from .api_utils import response_formatter
            response_data = response_formatter.format_server_error_response(
                request_id=request_id
            )
            
            response = LLMProxyResponse(
                success=False,
                status_code=500,
                error_code=response_data['error_code'],
                message=response_data['message'],
                data=response_data['data']
            )
            
            # Log error response
            processing_time = int((time.time() - start_time) * 1000)
            proxy_logger.log_response(request_id, response.to_dict(), 
                                    response.status_code, processing_time,
                                    client_ip=client_ip, user_agent=user_agent, data=request_data,
                                    model='default', from_cache=False)
            metrics_collector.record_request('/api/proxy', response.status_code, 
                                           processing_time, client_ip)
            
            return response
    
    def _call_llm_service(self, text: str, model: str = 'default', 
                         temperature: float = 0.7) -> Dict[str, Any]:
        """
        Call the LLM service. Uses OpenAI in production if `OPEN_AI_API_KEYS` is set,
        otherwise falls back to a stubbed response.
        
        Args:
            text: Text to process
            model: Model to use
            temperature: Temperature setting
            
        Returns:
            Dictionary with success status and response data
        """
        try:
            is_testing = False
            try:
                # Prefer Flask config flag when available
                is_testing = bool(getattr(current_app, 'config', {}).get('TESTING'))
            except Exception:
                is_testing = os.getenv('FLASK_ENV', '').lower() in ['test', 'testing']

            keys_env = os.getenv('OPEN_AI_API_KEYS', '')
            api_keys = [k.strip() for k in keys_env.split(',') if k.strip()]
            should_use_openai = (not is_testing) and len(api_keys) > 0

            if should_use_openai:
                return self._call_openai(text=text, model=model, temperature=temperature, api_keys=api_keys)

            # Fallback to stub implementation
            self.logger.info(f"Using stub LLM response (testing or no OPEN_AI_API_KEYS). model={model}, temperature={temperature}")
            time.sleep(0.05)
            mock_response = {
                'id': f"chatcmpl-{uuid.uuid4().hex[:29]}",
                'object': 'chat.completion',
                'created': int(time.time()),
                'model': model,
                'choices': [
                    {
                        'index': 0,
                        'message': {
                            'role': 'assistant',
                            'content': f"Mock LLM response for: {text[:50]}..."
                        },
                        'finish_reason': 'stop'
                    }
                ],
                'usage': {
                    'prompt_tokens': len(text.split()),
                    'completion_tokens': 20,
                    'total_tokens': len(text.split()) + 20
                }
            }
            return {'success': True, 'data': mock_response, 'provider': 'stub'}

        except Exception as e:
            self.logger.error(f"Error choosing LLM service path: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _call_openai(self, text: str, model: str, temperature: float, api_keys: list) -> Dict[str, Any]:
        """Call OpenAI Chat Completions with structured logging and error handling."""
        try:
            try:
                from openai import OpenAI
            except Exception as import_err:
                self.logger.error("OpenAI SDK not installed or failed to import", exc_info=True)
                return {'success': False, 'error': f"OPENAI_SDK_IMPORT_ERROR: {str(import_err)}"}

            api_key = random.choice(api_keys)
            masked_key = f"***{api_key[-4:]}" if len(api_key) >= 4 else "***"

            # Log outbound call without sensitive payload
            self.logger.info(
                json.dumps({
                    'event': 'openai_request_start',
                    'provider': 'openai',
                    'model': model,
                    'temperature': temperature,
                    'text_preview': (text[:80] + '...') if text and len(text) > 80 else (text or ''),
                    'text_len': len(text or ''),
                    'api_key_last4': masked_key,
                })
            )

            client = OpenAI(api_key=api_key)

            started_at = time.time()
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    { 'role': 'system', 'content': 'You are a helpful assistant.' },
                    { 'role': 'user', 'content': text or '' },
                ],
                temperature=float(temperature) if temperature is not None else 0.7,
            )
            elapsed_ms = int((time.time() - started_at) * 1000)

            # Normalize to our internal structure similar to stub
            data = {
                'id': getattr(completion, 'id', f"chatcmpl-{uuid.uuid4().hex[:29]}"),
                'object': 'chat.completion',
                'created': int(time.time()),
                'model': model,
                'choices': [
                    {
                        'index': 0,
                        'message': {
                            'role': 'assistant',
                            'content': (completion.choices[0].message.content if completion.choices else '')
                        },
                        'finish_reason': getattr(completion.choices[0], 'finish_reason', 'stop') if completion.choices else 'stop'
                    }
                ],
                'usage': {
                    'prompt_tokens': getattr(getattr(completion, 'usage', None), 'prompt_tokens', 0) or 0,
                    'completion_tokens': getattr(getattr(completion, 'usage', None), 'completion_tokens', 0) or 0,
                    'total_tokens': getattr(getattr(completion, 'usage', None), 'total_tokens', 0) or 0,
                }
            }

            self.logger.info(
                json.dumps({
                    'event': 'openai_request_success',
                    'provider': 'openai',
                    'model': model,
                    'elapsed_ms': elapsed_ms,
                    'api_key_last4': masked_key,
                    'usage': data.get('usage'),
                })
            )

            return {'success': True, 'data': data, 'provider': 'openai'}

        except Exception as e:
            # Attempt to extract structured error info
            err_text = str(e)
            status = None
            try:
                # Some OpenAI errors have HTTP status attributes
                status = getattr(e, 'status_code', None) or getattr(e, 'status', None)
            except Exception:
                status = None

            self.logger.error(
                json.dumps({
                    'event': 'openai_request_error',
                    'provider': 'openai',
                    'model': model,
                    'status': status,
                    'error': err_text[:500],
                }),
                exc_info=True
            )
            # Map common error types to messages (rate limit, auth, etc.)
            if status == 401 or 'authentication' in err_text.lower():
                message = 'OpenAI authentication failed'
            elif status == 429 or 'rate limit' in err_text.lower():
                message = 'OpenAI rate limit exceeded'
            elif status and int(status) >= 500:
                message = 'OpenAI service error'
            else:
                message = 'OpenAI request failed'

            return {'success': False, 'error': f"{message}: {err_text}", 'provider': 'openai'}

    def _persist_analytics(self, request_id: str, api_key_record, user, model: str,
                           temperature: float, cache_hit: bool, response: LLMProxyResponse,
                           processing_time_ms: int, token_info: Dict[str, Any],
                           cost_info: Dict[str, Any], provider: Optional[str], llm_data: Optional[Dict[str, Any]]):
        """Persist proxy-level analytics and provider-specific analytics if available."""
        try:
            pa = ProxyAnalytics(
                request_id=request_id,
                api_key_id=(api_key_record.id if api_key_record else None),
                api_key_value=(api_key_record.key_value if api_key_record else None),
                user_id=(user.id if user else None),
                model=model,
                provider=provider,
                temperature=float(temperature) if temperature is not None else None,
                cache_hit=bool(cache_hit or response.from_cache),
                success=bool(response.success),
                status_code=int(response.status_code or 0),
                error_code=response.error_code,
                input_tokens=(token_info or {}).get('input_tokens'),
                output_tokens=(token_info or {}).get('output_tokens'),
                total_tokens=(token_info or {}).get('total_tokens'),
                cost_input=(cost_info or {}).get('input_cost'),
                cost_output=(cost_info or {}).get('output_cost'),
                cost_total=(cost_info or {}).get('actual_cost'),
                processing_time_ms=processing_time_ms,
                client_ip=request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR')),
                user_agent=request.headers.get('User-Agent')
            )
            db.session.add(pa)

            # Provider-specific analytics (generic)
            if provider and llm_data:
                usage = llm_data.get('usage') or {}
                pa2 = ProviderAnalytics(
                    request_id=request_id,
                    completion_id=llm_data.get('id'),
                    model=llm_data.get('model'),
                    provider=provider,
                    prompt_tokens=usage.get('prompt_tokens'),
                    completion_tokens=usage.get('completion_tokens'),
                    total_tokens=usage.get('total_tokens'),
                    raw_response=json.dumps(llm_data)[:100000]
                )
                db.session.add(pa2)

            db.session.commit()
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            raise e
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            return llm_cache_lookup.cache_lookup.get_cache_info()
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {str(e)}")
            return {}
    
    def get_metrics(self, minutes: int = 60) -> Dict[str, Any]:
        """Get proxy metrics."""
        try:
            return metrics_collector.get_metrics(minutes)
        except Exception as e:
            self.logger.error(f"Error getting metrics: {str(e)}")
            return {}
    
    def clear_cache(self) -> bool:
        """Clear the cache."""
        try:
            llm_cache_lookup.cache_lookup.clear()
            self.logger.info("Cache cleared")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing cache: {str(e)}")
            return False
    
    def invalidate_user_cache(self, api_key: str) -> int:
        """Invalidate cache for a specific user."""
        try:
            return llm_cache_lookup.invalidate_user_cache(api_key)
        except Exception as e:
            self.logger.error(f"Error invalidating user cache: {str(e)}")
            return 0


# Global instance
llm_proxy = LLMProxy()
