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
from .policy_checks import policy_checker, PolicyCheckResult
from .cache_lookup import llm_cache_lookup
from .proxy_logger import proxy_logger, metrics_collector
from .token_utils import count_tokens as tk_count_tokens, estimate_cost as tk_estimate_cost


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
        """Convert to dictionary for JSON response."""
        response = {
            'success': self.success,
            'data': self.data,
            'from_cache': self.from_cache
        }
        
        if self.error_code:
            response['error_code'] = self.error_code
        if self.message:
            response['message'] = self.message
        
        return response


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
                from .api_utils import response_formatter
                response_data, status_code = response_formatter.format_proxy_failure_response(policy_result, text)
                
                response = LLMProxyResponse(
                    success=False,
                    status_code=status_code,
                    error_code=policy_result.error_code,
                    message=response_data['message'],
                    data=response_data['data']
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
                # Return cached response
                from .api_utils import response_formatter
                response_data = cached_response['response']
                cache_info = {
                    'cached_at': cached_response['cached_at'],
                    'cache_key': cached_response['cache_key']
                }
                if 'similarity' in cached_response:
                    cache_info['similarity'] = cached_response['similarity']
                
                response_data_dict = response_formatter.format_proxy_success_response(
                    api_key_record, text, response_data, model, temperature, 
                    cached=True, cache_info=cache_info
                )

                # Attach token and cost metadata (input only for cache hits)
                token_info = {
                    'input_tokens': input_tokens,
                    'output_tokens': 0,
                    'total_tokens': input_tokens,
                }
                cost_info = {
                    'cache_hit': True,
                    'input_cost': tk_estimate_cost(input_tokens, model, is_output=False),
                    'output_cost': 0.0,
                    'actual_cost': 0.0,
                    'cost_saved': tk_estimate_cost(input_tokens, model, is_output=False),
                }
                response_data_dict['data']['tokens'] = token_info
                response_data_dict['data']['estimated_cost'] = {
                    'input': cost_info['input_cost'],
                    'output': cost_info['output_cost'],
                    'total': cost_info['actual_cost']
                }
                
                response = LLMProxyResponse(
                    success=True,
                    status_code=200,
                    data=response_data_dict['data'],
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
            
            # 4. Forward to LLM service (stub implementation)
            llm_response = self._call_llm_service(text, model, temperature)
            
            if llm_response['success']:
                # Cache the response
                llm_cache_lookup.cache_llm_response(
                    user_scope, request_data, llm_response['data'], 
                    ttl=3600, model=model, temperature=temperature
                )
                
                from .api_utils import response_formatter
                response_data_dict = response_formatter.format_proxy_success_response(
                    api_key_record, text, llm_response['data'], model, temperature, cached=False
                )

                # Count output tokens and estimate costs
                try:
                    # Extract assistant text for token counting
                    choices = llm_response['data'].get('choices', [])
                    output_text = ''
                    if choices:
                        msg = choices[0].get('message', {})
                        output_text = msg.get('content', '')
                    output_tokens = tk_count_tokens(output_text or '', model)
                except Exception:
                    output_tokens = 0

                total_tokens = input_tokens + output_tokens
                input_cost = tk_estimate_cost(input_tokens, model, is_output=False)
                output_cost = tk_estimate_cost(output_tokens, model, is_output=True)
                total_cost = round(input_cost + output_cost, 6)

                token_info = {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'total_tokens': total_tokens,
                }
                cost_info = {
                    'cache_hit': False,
                    'input_cost': input_cost,
                    'output_cost': output_cost,
                    'actual_cost': total_cost,
                }
                response_data_dict['data']['tokens'] = token_info
                response_data_dict['data']['estimated_cost'] = {
                    'input': input_cost,
                    'output': output_cost,
                    'total': total_cost
                }
                
                response = LLMProxyResponse(
                    success=True,
                    status_code=200,
                    data=response_data_dict['data']
                )
            else:
                response = LLMProxyResponse(
                    success=False,
                    status_code=500,
                    error_code='LLM_SERVICE_ERROR',
                    message='LLM service temporarily unavailable. Please try again later.',
                    data={
                        'status': 'error',
                        'model': model, 
                        'temperature': temperature,
                        'processing_info': {
                            'policy_checks_passed': True,
                            'cache_hit': False,
                            'llm_service_used': False,
                            'llm_service_error': llm_response.get('error', 'Unknown error')
                        }
                    }
                )
            
            # Log response
            processing_time = int((time.time() - start_time) * 1000)
            proxy_logger.log_response(request_id, response.to_dict(), 
                                    response.status_code, processing_time,
                                    api_key_record, client_ip, user_agent, data=request_data,
                                    model=model, from_cache=False,
                                    token_info=locals().get('token_info'), cost_info=locals().get('cost_info'))
            metrics_collector.record_request('/api/proxy', response.status_code, 
                                           processing_time, client_ip)
            
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
        Call the LLM service (stub implementation).
        
        Args:
            text: Text to process
            model: Model to use
            temperature: Temperature setting
            
        Returns:
            Dictionary with success status and response data
        """
        try:
            # This is a stub implementation
            # In a real implementation, you would call OpenAI, Anthropic, or other LLM services
            
            self.logger.info(f"Calling LLM service: model={model}, temperature={temperature}")
            
            # Simulate LLM processing time
            time.sleep(0.1)  # Simulate network delay
            
            # Generate a mock response
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
            
            return {
                'success': True,
                'data': mock_response
            }
            
        except Exception as e:
            self.logger.error(f"Error calling LLM service: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
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
