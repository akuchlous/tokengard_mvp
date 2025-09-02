#!/usr/bin/env python3
"""
Unit tests for the API utilities module
"""

import pytest
from unittest.mock import Mock, patch
from app.utils.api_utils import (
    APIRequestValidator, APIResponseFormatter, APIRateLimiter,
    request_validator, response_formatter, rate_limiter
)
from app.utils.policy_checks import PolicyCheckResult


class TestAPIRequestValidator:
    """Test the APIRequestValidator class."""
    
    def test_validator_creation(self):
        """Test creating an APIRequestValidator."""
        validator = APIRequestValidator()
        assert validator is not None
    
    def test_validate_json_request_valid(self, app):
        """Test validating a valid JSON request."""
        with app.test_request_context(json={'test': 'data'}):
            validator = APIRequestValidator()
            is_valid, data, error = validator.validate_json_request('127.0.0.1')
            
            assert is_valid is True
            assert data == {'test': 'data'}
            assert error is None
    
    def test_validate_json_request_invalid_json(self, app):
        """Test validating an invalid JSON request."""
        with app.test_request_context(data='invalid json', content_type='application/json'):
            validator = APIRequestValidator()
            is_valid, data, error = validator.validate_json_request('127.0.0.1')
            
            assert is_valid is False
            assert data is None
            assert error['error_code'] == 'INVALID_JSON'
    
    def test_validate_json_request_empty_data(self, app):
        """Test validating an empty request."""
        with app.test_request_context():
            validator = APIRequestValidator()
            is_valid, data, error = validator.validate_json_request('127.0.0.1')
            
            assert is_valid is False
            assert data is None
            assert error['error_code'] == 'INVALID_JSON'  # Flask returns INVALID_JSON for empty requests
    
    def test_validate_json_request_invalid_type(self, app):
        """Test validating a request with invalid data type."""
        with app.test_request_context(json="not a dict"):
            validator = APIRequestValidator()
            is_valid, data, error = validator.validate_json_request('127.0.0.1')
            
            assert is_valid is False
            assert data is None
            assert error['error_code'] == 'INVALID_DATA_TYPE'
    
    def test_validate_api_key_valid(self):
        """Test validating a valid API key."""
        validator = APIRequestValidator()
        data = {'api_key': 'valid-key-123'}
        
        is_valid, api_key, error = validator.validate_api_key(data, '127.0.0.1')
        
        assert is_valid is True
        assert api_key == 'valid-key-123'
        assert error is None
    
    def test_validate_api_key_from_header(self, app):
        """Test validating API key from header."""
        with app.test_request_context(headers={'X-API-Key': 'header-key-123'}):
            validator = APIRequestValidator()
            data = {}
            
            is_valid, api_key, error = validator.validate_api_key(data, '127.0.0.1')
            
            assert is_valid is True
            assert api_key == 'header-key-123'
            assert error is None
    
    def test_validate_api_key_missing(self, app):
        """Test validating missing API key."""
        with app.test_request_context():
            validator = APIRequestValidator()
            data = {}
            
            is_valid, api_key, error = validator.validate_api_key(data, '127.0.0.1')
            
            assert is_valid is False
            assert api_key is None
            assert error['error_code'] == 'MISSING_API_KEY'
    
    def test_validate_text_content_valid(self):
        """Test validating valid text content."""
        validator = APIRequestValidator()
        data = {'text': 'Hello world'}
        
        is_valid, text, error = validator.validate_text_content(data, '127.0.0.1')
        
        assert is_valid is True
        assert text == 'Hello world'
        assert error is None
    
    def test_validate_text_content_required_missing(self):
        """Test validating missing required text content."""
        validator = APIRequestValidator()
        data = {}
        
        is_valid, text, error = validator.validate_text_content(data, '127.0.0.1', required=True)
        
        assert is_valid is False
        assert text is None
        assert error['error_code'] == 'MISSING_TEXT'
    
    def test_validate_text_content_optional_missing(self):
        """Test validating missing optional text content."""
        validator = APIRequestValidator()
        data = {}
        
        is_valid, text, error = validator.validate_text_content(data, '127.0.0.1', required=False)
        
        assert is_valid is True
        assert text == ''
        assert error is None
    
    def test_validate_request_size_valid(self, app):
        """Test validating valid request size."""
        with app.test_request_context():
            validator = APIRequestValidator()
            is_valid, error = validator.validate_request_size('127.0.0.1')
            
            assert is_valid is True
            assert error is None
    
    def test_validate_request_size_too_large(self, app):
        """Test validating request that's too large."""
        with app.test_request_context():
            # Mock a large content length
            with patch('app.utils.api_utils.request') as mock_request:
                mock_request.content_length = 20000  # 20KB
                
                validator = APIRequestValidator()
                is_valid, error = validator.validate_request_size('127.0.0.1')
                
                assert is_valid is False
                assert error['error_code'] == 'REQUEST_TOO_LARGE'


class TestAPIResponseFormatter:
    """Test the APIResponseFormatter class."""
    
    def test_formatter_creation(self):
        """Test creating an APIResponseFormatter."""
        formatter = APIResponseFormatter()
        assert formatter is not None
    
    def test_format_policy_success_response(self):
        """Test formatting successful policy response."""
        # Create mock objects
        mock_user = Mock()
        mock_user.id = 1
        
        mock_api_key_record = Mock()
        mock_api_key_record.id = 1
        
        policy_result = PolicyCheckResult(
            passed=True,
            details={
                'key_name': 'test_key',
                'user': mock_user,
                'api_key_record': mock_api_key_record
            }
        )
        
        response = APIResponseFormatter.format_policy_success_response(policy_result, "test text")
        
        assert response['success'] is True
        assert response['data']['status'] == 'passed'
        assert response['data']['key_name'] == 'test_key'
        assert response['data']['text_length'] == 9
        assert response['data']['checks_performed']['api_key_validation'] is True
    
    def test_format_policy_failure_response_banned_keyword(self):
        """Test formatting policy failure response for banned keyword."""
        policy_result = PolicyCheckResult(
            passed=False,
            error_code='BANNED_KEYWORD',
            message='Content contains banned keyword: spam'
        )
        
        response, status_code = APIResponseFormatter.format_policy_failure_response(policy_result, "spam text")
        
        assert response['success'] is False
        assert response['error_code'] == 'BANNED_KEYWORD'
        assert response['data']['status'] == 'content_blocked'
        assert status_code == 400
    
    def test_format_policy_failure_response_api_key_not_found(self):
        """Test formatting policy failure response for API key not found."""
        policy_result = PolicyCheckResult(
            passed=False,
            error_code='API_KEY_NOT_FOUND',
            message='API key not found'
        )
        
        response, status_code = APIResponseFormatter.format_policy_failure_response(policy_result, "test text")
        
        assert response['success'] is False
        assert response['error_code'] == 'API_KEY_NOT_FOUND'
        assert response['data']['status'] == 'authentication_failed'
        assert status_code == 401
    
    def test_format_proxy_success_response(self):
        """Test formatting successful proxy response."""
        mock_api_key_record = Mock()
        mock_api_key_record.key_name = 'test_key'
        
        llm_response = {'message': 'Hello world'}
        
        response = APIResponseFormatter.format_proxy_success_response(
            mock_api_key_record, "input text", llm_response, 'gpt-3.5', 0.7, cached=False
        )
        
        assert response['success'] is True
        assert response['data']['status'] == 'success'
        assert response['data']['key_name'] == 'test_key'
        assert response['data']['cached'] is False
        assert response['data']['model'] == 'gpt-3.5'
        assert response['data']['temperature'] == 0.7
    
    def test_format_proxy_success_response_cached(self):
        """Test formatting successful cached proxy response."""
        mock_api_key_record = Mock()
        mock_api_key_record.key_name = 'test_key'
        
        llm_response = {'message': 'Hello world'}
        cache_info = {'cached_at': 1234567890, 'cache_key': 'abc123'}
        
        response = APIResponseFormatter.format_proxy_success_response(
            mock_api_key_record, "input text", llm_response, 'gpt-3.5', 0.7, 
            cached=True, cache_info=cache_info
        )
        
        assert response['success'] is True
        assert response['data']['cached'] is True
        assert 'cached response' in response['data']['message']
        assert response['data']['cache_info'] == cache_info
    
    def test_format_server_error_response(self):
        """Test formatting server error response."""
        response = APIResponseFormatter.format_server_error_response(
            error_code='TEST_ERROR',
            message='Test error message',
            request_id='test-123'
        )
        
        assert response['success'] is False
        assert response['error_code'] == 'TEST_ERROR'
        assert response['message'] == 'Test error message'
        assert response['data']['status'] == 'server_error'
        assert response['data']['request_id'] == 'test-123'


class TestAPIRateLimiter:
    """Test the APIRateLimiter class."""
    
    def test_rate_limiter_creation(self):
        """Test creating an APIRateLimiter."""
        limiter = APIRateLimiter()
        assert limiter is not None
    
    def test_check_rate_limit_allowed(self, app):
        """Test rate limit check when allowed."""
        with app.app_context():
            limiter = APIRateLimiter()
            is_allowed, error = limiter.check_rate_limit('127.0.0.1')
            
            assert is_allowed is True
            assert error is None
    
    def test_check_rate_limit_exceeded(self, app):
        """Test rate limit check when exceeded."""
        with app.app_context():
            with patch('time.time') as mock_time:
                mock_time.return_value = 1000
                
                # Set up the app with exceeded rate limit
                app.proxy_request_counts = {
                    '127.0.0.1_16': 101  # 101 requests in minute 16
                }
                
                limiter = APIRateLimiter()
                is_allowed, error = limiter.check_rate_limit('127.0.0.1')
                
                assert is_allowed is False
                assert error['error_code'] == 'RATE_LIMIT_EXCEEDED'


class TestGlobalInstances:
    """Test the global API utility instances."""
    
    def test_global_instances_exist(self):
        """Test that global instances exist."""
        assert request_validator is not None
        assert isinstance(request_validator, APIRequestValidator)
        
        assert response_formatter is not None
        assert isinstance(response_formatter, APIResponseFormatter)
        
        assert rate_limiter is not None
        assert isinstance(rate_limiter, APIRateLimiter)
    
    def test_global_instances_are_singletons(self):
        """Test that global instances are singletons."""
        from app.utils.api_utils import request_validator as validator1
        from app.utils.api_utils import request_validator as validator2
        
        assert validator1 is validator2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
