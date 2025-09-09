"""
API Utilities Module

FLOW OVERVIEW
- APIRequestValidator
  • validate_json_request → parse/validate JSON and return (ok, data, error).
  • validate_api_key → extract key from JSON or header.
  • validate_text_content → extract text, optionally enforce presence.
  • validate_request_size → enforce 10KB content size limit.

- APIResponseFormatter
  • format_policy_success_response / format_policy_failure_response → structured policy results.
  • format_proxy_success_response / format_proxy_failure_response → unified proxy responses.
  • format_server_error_response → consistent unexpected error payload.

- APIRateLimiter
  • check_rate_limit(client_ip) → per-minute counter with simple in-app cleanup.

Used by both proxy and policy endpoints to avoid code duplication.
"""

import json
import logging
from typing import Dict, Any, Tuple, Optional
from flask import request, current_app, jsonify


class APIRequestValidator:
    """Handles common request validation logic."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_json_request(self, client_ip: str = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Validate and parse JSON request.
        
        Args:
            client_ip: Client IP for logging
            
        Returns:
            Tuple of (is_valid, data, error_response)
        """
        try:
            data = request.get_json(force=True)
        except Exception as e:
            self.logger.warning(f"Invalid JSON from {client_ip}: {str(e)}")
            return False, None, {
                'success': False,
                'error_code': 'INVALID_JSON',
                'message': 'Invalid JSON format. Request must be valid JSON.'
            }
        
        if not data:
            self.logger.warning(f"Empty request body from {client_ip}")
            return False, None, {
                'success': False,
                'error_code': 'MISSING_JSON',
                'message': 'Invalid request format. JSON payload required.'
            }
        
        if not isinstance(data, dict):
            self.logger.warning(f"Invalid data type from {client_ip}: {type(data)}")
            return False, None, {
                'success': False,
                'error_code': 'INVALID_DATA_TYPE',
                'message': 'Request data must be a JSON object.'
            }
        
        return True, data, None
    
    def validate_api_key(self, data: Dict[str, Any], client_ip: str = None) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Extract and validate API key from request.
        
        Args:
            data: Request data dictionary
            client_ip: Client IP for logging
            
        Returns:
            Tuple of (is_valid, api_key, error_response)
        """
        # Get API key from JSON payload, Authorization header (Bearer), or X-API-Key header
        api_key = (data.get('api_key') or '').strip()
        if not api_key:
            # Authorization: Bearer <key>
            auth_header = (request.headers.get('Authorization') or '').strip()
            if auth_header.lower().startswith('bearer '):
                api_key = auth_header.split(' ', 1)[1].strip()
        if not api_key:
            api_key = (request.headers.get('X-API-Key') or '').strip()
        
        if not api_key:
            self.logger.warning(f"Missing API key from {client_ip}")
            return False, None, {
                'success': False,
                'error_code': 'MISSING_API_KEY',
                'message': 'API key is required. Provide via Authorization Bearer, api_key, or X-API-Key.'
            }
        
        return True, api_key, None
    
    def validate_text_content(self, data: Dict[str, Any], client_ip: str = None, required: bool = False) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Extract and validate text content from request.
        
        Args:
            data: Request data dictionary
            client_ip: Client IP for logging
            required: Whether text is required
            
        Returns:
            Tuple of (is_valid, text, error_response)
        """
        text = data.get('text', '')
        
        if required and not text:
            self.logger.warning(f"Missing text content from {client_ip}")
            return False, None, {
                'success': False,
                'error_code': 'MISSING_TEXT',
                'message': 'Text content is required for policy validation.'
            }
        
        return True, text, None
    
    def validate_request_size(self, client_ip: str = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate request size limits.
        
        Args:
            client_ip: Client IP for logging
            
        Returns:
            Tuple of (is_valid, error_response)
        """
        content_length = request.content_length or 0
        if content_length > 10240:  # 10KB limit
            self.logger.warning(f"Large request blocked from {client_ip}: {content_length} bytes")
            return False, {
                'success': False,
                'error_code': 'REQUEST_TOO_LARGE',
                'message': 'Request too large. Maximum 10KB allowed.'
            }
        
        return True, None


class APIResponseFormatter:
    """Handles common response formatting logic."""
    
    @staticmethod
    def format_policy_success_response(policy_result, text: str) -> Dict[str, Any]:
        """Format successful policy check response."""
        return {
            'success': True,
            'data': {
                'status': 'passed',
                'message': 'All policy checks passed successfully',
                'key_name': policy_result.details.get('key_name'),
                'text_length': len(text),
                'checks_performed': {
                    'api_key_validation': True,
                    'banned_keywords_check': True,
                    'external_security_check': True
                },
                'processing_info': {
                    'user_id': policy_result.details.get('user').id if policy_result.details.get('user') else None,
                    'api_key_id': policy_result.details.get('api_key_record').id if policy_result.details.get('api_key_record') else None
                }
            }
        }
    
    @staticmethod
    def format_policy_failure_response(policy_result, text: str) -> Tuple[Dict[str, Any], int]:
        """Format failed policy check response."""
        if policy_result.error_code in ['BANNED_KEYWORD', 'TEXT_TOO_LONG', 'EXTERNAL_API_BLOCKED']:
            status_code = 400
            status = 'content_blocked'
            message = 'Content validation failed'
        elif policy_result.error_code in ['API_KEY_NOT_FOUND', 'API_KEY_INACTIVE', 'USER_ACCOUNT_INACTIVE']:
            status_code = 401
            status = 'authentication_failed'
            message = 'Authentication failed'
        else:
            status_code = 400
            status = 'validation_failed'
            message = 'Request validation failed'
        
        response = {
            'success': False,
            'error_code': policy_result.error_code,
            'message': message,
            'data': {
                'status': status,
                'error_details': policy_result.message,
                'text_length': len(text),
                'checks_performed': {
                    'api_key_validation': policy_result.error_code not in ['API_KEY_NOT_FOUND', 'API_KEY_INACTIVE', 'USER_ACCOUNT_INACTIVE'],
                    'banned_keywords_check': policy_result.error_code != 'BANNED_KEYWORD',
                    'external_security_check': policy_result.error_code not in ['TEXT_TOO_LONG', 'EXTERNAL_API_BLOCKED']
                },
                'failed_check': policy_result.error_code
            }
        }
        
        return response, status_code
    
    @staticmethod
    def format_proxy_success_response(api_key_record, text: str, llm_response: Dict[str, Any], 
                                    model: str, temperature: float, cached: bool = False, 
                                    cache_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format successful proxy response."""
        response_data = {
            'status': 'success',
            'message': 'Request processed successfully' + (' (cached response)' if cached else ''),
            'key_name': api_key_record.key_name,
            'text_length': len(text) if text else 0,
            'response': llm_response,
            'cached': cached,
            'model': model,
            'temperature': temperature,
            'processing_info': {
                'policy_checks_passed': True,
                'cache_hit': cached,
                'llm_service_used': not cached
            }
        }
        
        if cached and cache_info:
            response_data['cache_info'] = cache_info
        
        return {
            'success': True,
            'data': response_data
        }
    
    @staticmethod
    def format_proxy_failure_response(policy_result, text: str) -> Tuple[Dict[str, Any], int]:
        """Format failed proxy response."""
        if policy_result.error_code in ['BANNED_KEYWORD', 'TEXT_TOO_LONG', 'EXTERNAL_API_BLOCKED']:
            status_code = 400
            status = 'content_blocked'
            message = 'Content validation failed'
        elif policy_result.error_code in ['API_KEY_NOT_FOUND', 'API_KEY_INACTIVE', 'USER_ACCOUNT_INACTIVE']:
            status_code = 401
            status = 'authentication_failed'
            message = 'Authentication failed'
        else:
            status_code = 400
            status = 'validation_failed'
            message = 'Request validation failed'
        
        response = {
            'success': False,
            'error_code': policy_result.error_code,
            'message': message,
            'data': {
                'status': status,
                'error_details': policy_result.message,
                'processing_info': {
                    'policy_checks_passed': False,
                    'cache_hit': False,
                    'llm_service_used': False,
                    'failed_check': policy_result.error_code
                }
            }
        }
        
        return response, status_code
    
    @staticmethod
    def format_server_error_response(error_code: str = 'INTERNAL_SERVER_ERROR', 
                                   message: str = 'Internal server error. Please try again later.',
                                   request_id: str = None) -> Dict[str, Any]:
        """Format server error response."""
        response = {
            'success': False,
            'error_code': error_code,
            'message': message,
            'data': {
                'status': 'server_error',
                'processing_info': {
                    'policy_checks_passed': False,
                    'cache_hit': False,
                    'llm_service_used': False,
                    'error_type': 'unexpected_error'
                }
            }
        }
        
        if request_id:
            response['data']['request_id'] = request_id
        
        return response


class APIRateLimiter:
    """Handles rate limiting logic."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def check_rate_limit(self, client_ip: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check rate limiting for client IP.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            Tuple of (is_allowed, error_response)
        """
        if not hasattr(current_app, 'proxy_request_counts'):
            current_app.proxy_request_counts = {}
        
        import time
        current_time = int(time.time())
        minute_key = f"{client_ip}_{current_time // 60}"
        
        if minute_key in current_app.proxy_request_counts:
            current_app.proxy_request_counts[minute_key] += 1
        else:
            current_app.proxy_request_counts[minute_key] = 1
        
        # Clean old entries (older than 5 minutes)
        old_keys = [k for k in current_app.proxy_request_counts.keys() 
                    if int(k.split('_')[-1]) < (current_time // 60) - 5]
        for old_key in old_keys:
            del current_app.proxy_request_counts[old_key]
        
        # Check rate limit (100 requests per minute per IP)
        if current_app.proxy_request_counts[minute_key] > 100:
            self.logger.warning(f"Rate limit exceeded for {client_ip}: {current_app.proxy_request_counts[minute_key]} requests")
            return False, {
                'success': False,
                'error_code': 'RATE_LIMIT_EXCEEDED',
                'message': 'Rate limit exceeded. Maximum 100 requests per minute.'
            }
        
        return True, None


# Global instances
request_validator = APIRequestValidator()
response_formatter = APIResponseFormatter()
rate_limiter = APIRateLimiter()
