#!/usr/bin/env python3
"""
Unit tests for the LLM proxy module
"""

import pytest
import time
from unittest.mock import Mock, patch
from app.utils.llm_proxy import LLMProxy, LLMProxyResponse, llm_proxy
from app.utils.policy_checks import PolicyCheckResult
from app.models import User, APIKey, db
from app.utils.auth_utils import hash_password


class TestLLMProxyResponse:
    """Test the LLMProxyResponse class."""
    
    def test_llm_proxy_response_creation(self):
        """Test creating an LLMProxyResponse."""
        response = LLMProxyResponse(
            success=True,
            data={"key": "value"},
            status_code=200,
            from_cache=True
        )
        
        assert response.success is True
        assert response.data == {"key": "value"}
        assert response.status_code == 200
        assert response.from_cache is True
        assert response.error_code is None
        assert response.message is None
    
    def test_llm_proxy_response_to_dict(self):
        """Test converting LLMProxyResponse to dictionary."""
        response = LLMProxyResponse(
            success=False,
            error_code="TEST_ERROR",
            message="Test error message",
            data={"detail": "info"}
        )
        
        response_dict = response.to_dict()
        
        expected = {
            'success': False,
            'data': {'detail': 'info'},
            'from_cache': False,
            'error_code': 'TEST_ERROR',
            'message': 'Test error message'
        }
        assert response_dict == expected


class TestLLMProxy:
    """Test the LLMProxy class."""
    
    @pytest.fixture
    def test_user_with_key(self, app, db_session):
        """Create a test user with API key."""
        user = User(
            email='proxy_test@example.com',
            password_hash=hash_password('password123')
        )
        user.status = 'active'
        db_session.add(user)
        db_session.commit()
        
        # Create API key
        api_key = APIKey(
            user_id=user.id,
            key_name='test_key',
            key_value='tk-test-key-123456789012345678901234567890',
            state='enabled'
        )
        db_session.add(api_key)
        db_session.commit()
        
        return user, api_key
    
    def test_llm_proxy_creation(self):
        """Test creating an LLMProxy."""
        proxy = LLMProxy()
        assert proxy is not None
    
    @patch('app.utils.llm_proxy.policy_checker')
    @patch('app.utils.llm_proxy.proxy_logger')
    @patch('app.utils.llm_proxy.metrics_collector')
    def test_process_request_policy_check_failure(self, mock_metrics, mock_logger, mock_policy_checker):
        """Test processing request with policy check failure."""
        # Mock policy check failure
        mock_policy_checker.run_all_checks.return_value = PolicyCheckResult(
            passed=False,
            error_code='API_KEY_NOT_FOUND',
            message='API key not found.'
        )
        
        proxy = LLMProxy()
        request_data = {
            'api_key': 'invalid-key',
            'text': 'Hello world'
        }
        
        response = proxy.process_request(request_data, '127.0.0.1', 'test-agent')
        
        assert response.success is False
        assert response.error_code == 'API_KEY_NOT_FOUND'
        assert response.status_code == 401
        
        # Verify logging was called with new parameters
        mock_logger.log_response.assert_called_once()
        call_args = mock_logger.log_response.call_args
        assert 'model' in call_args.kwargs
        assert 'from_cache' in call_args.kwargs
        assert call_args.kwargs['from_cache'] is False
    
    @patch('app.utils.llm_proxy.policy_checker')
    @patch('app.utils.llm_proxy.llm_cache_lookup')
    @patch('app.utils.llm_proxy.proxy_logger')
    @patch('app.utils.llm_proxy.metrics_collector')
    def test_process_request_cache_hit(self, mock_metrics, mock_logger, mock_cache_lookup, mock_policy_checker):
        """Test processing request with cache hit."""
        # Mock policy check success
        mock_api_key_record = Mock()
        mock_api_key_record.key_name = 'test_key'
        mock_user = Mock()
        
        mock_policy_checker.run_all_checks.return_value = PolicyCheckResult(
            passed=True,
            details={
                'api_key_record': mock_api_key_record,
                'user': mock_user,
                'key_name': 'test_key'
            }
        )
        
        # Mock cache hit
        mock_cache_lookup.get_llm_response.return_value = (True, {
            'response': {'message': 'Cached response'},
            'cached_at': time.time(),
            'cache_key': 'test_cache_key'
        })
        
        proxy = LLMProxy()
        request_data = {
            'api_key': 'tk-test-key-123456789012345678901234567890',
            'text': 'Hello world'
        }
        
        response = proxy.process_request(request_data, '127.0.0.1', 'test-agent')
        
        assert response.success is True
        assert response.from_cache is True
        assert response.data['cached'] is True
        assert 'cache_info' in response.data
        
        # Verify logging was called with cache hit parameters
        mock_logger.log_response.assert_called_once()
        call_args = mock_logger.log_response.call_args
        assert call_args.kwargs['from_cache'] is True
    
    @patch('app.utils.llm_proxy.policy_checker')
    @patch('app.utils.llm_proxy.llm_cache_lookup')
    @patch('app.utils.llm_proxy.proxy_logger')
    @patch('app.utils.llm_proxy.metrics_collector')
    def test_process_request_cache_miss_llm_success(self, mock_metrics, mock_logger, mock_cache_lookup, mock_policy_checker):
        """Test processing request with cache miss and successful LLM call."""
        # Mock policy check success
        mock_api_key_record = Mock()
        mock_api_key_record.key_name = 'test_key'
        mock_user = Mock()
        
        mock_policy_checker.run_all_checks.return_value = PolicyCheckResult(
            passed=True,
            details={
                'api_key_record': mock_api_key_record,
                'user': mock_user,
                'key_name': 'test_key'
            }
        )
        
        # Mock cache miss
        mock_cache_lookup.get_llm_response.return_value = (False, None)
        
        # Mock successful LLM response caching
        mock_cache_lookup.cache_llm_response.return_value = True
        
        proxy = LLMProxy()
        request_data = {
            'api_key': 'tk-test-key-123456789012345678901234567890',
            'text': 'Hello world'
        }
        
        response = proxy.process_request(request_data, '127.0.0.1', 'test-agent')
        
        assert response.success is True
        assert response.from_cache is False
        assert response.data['cached'] is False
        assert 'response' in response.data
        assert 'model' in response.data
        
        # Verify logging was called with LLM call parameters
        mock_logger.log_response.assert_called_once()
        call_args = mock_logger.log_response.call_args
        assert call_args.kwargs['from_cache'] is False
    
    @patch('app.utils.llm_proxy.policy_checker')
    @patch('app.utils.llm_proxy.llm_cache_lookup')
    def test_process_request_llm_service_failure(self, mock_cache_lookup, mock_policy_checker):
        """Test processing request with LLM service failure."""
        # Mock policy check success
        mock_api_key_record = Mock()
        mock_api_key_record.key_name = 'test_key'
        mock_user = Mock()
        
        mock_policy_checker.run_all_checks.return_value = PolicyCheckResult(
            passed=True,
            details={
                'api_key_record': mock_api_key_record,
                'user': mock_user,
                'key_name': 'test_key'
            }
        )
        
        # Mock cache miss
        mock_cache_lookup.get_llm_response.return_value = (False, None)
        
        proxy = LLMProxy()
        
        # Mock LLM service failure
        with patch.object(proxy, '_call_llm_service', return_value={'success': False, 'error': 'LLM service down'}):
            request_data = {
                'api_key': 'tk-test-key-123456789012345678901234567890',
                'text': 'Hello world'
            }
            
            response = proxy.process_request(request_data, '127.0.0.1', 'test-agent')
            
            assert response.success is False
            assert response.error_code == 'LLM_SERVICE_ERROR'
            assert response.status_code == 500
    
    def test_call_llm_service_success(self):
        """Test successful LLM service call."""
        proxy = LLMProxy()
        
        response = proxy._call_llm_service("Hello world", "gpt-3.5", 0.7)
        
        assert response['success'] is True
        assert 'data' in response
        assert response['data']['model'] == 'gpt-3.5'
        assert 'choices' in response['data']
    
    def test_call_llm_service_failure(self):
        """Test LLM service call failure."""
        proxy = LLMProxy()
        
        # Mock an exception in the LLM service
        with patch('time.sleep', side_effect=Exception("Network error")):
            response = proxy._call_llm_service("Hello world", "gpt-3.5", 0.7)
            
            assert response['success'] is False
            assert 'error' in response
    
    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        proxy = LLMProxy()
        
        with patch('app.utils.llm_proxy.llm_cache_lookup') as mock_cache:
            mock_cache.cache_lookup.get_cache_info.return_value = {'size': 10, 'hits': 5}
            
            stats = proxy.get_cache_stats()
            
            assert stats == {'size': 10, 'hits': 5}
    
    def test_get_metrics(self):
        """Test getting metrics."""
        proxy = LLMProxy()
        
        with patch('app.utils.llm_proxy.metrics_collector') as mock_metrics:
            mock_metrics.get_metrics.return_value = {'total_requests': 100, 'success_rate': 95}
            
            metrics = proxy.get_metrics(60)
            
            assert metrics == {'total_requests': 100, 'success_rate': 95}
            mock_metrics.get_metrics.assert_called_once_with(60)
    
    def test_clear_cache(self):
        """Test clearing cache."""
        proxy = LLMProxy()
        
        with patch('app.utils.llm_proxy.llm_cache_lookup') as mock_cache:
            mock_cache.cache_lookup.clear.return_value = None
            
            result = proxy.clear_cache()
            
            assert result is True
            mock_cache.cache_lookup.clear.assert_called_once()
    
    def test_invalidate_user_cache(self):
        """Test invalidating user cache."""
        proxy = LLMProxy()
        
        with patch('app.utils.llm_proxy.llm_cache_lookup') as mock_cache:
            mock_cache.invalidate_user_cache.return_value = 5
            
            count = proxy.invalidate_user_cache("test-api-key")
            
            assert count == 5
            mock_cache.invalidate_user_cache.assert_called_once_with("test-api-key")


class TestGlobalLLMProxy:
    """Test the global LLM proxy instance."""
    
    def test_global_instance_exists(self):
        """Test that the global LLM proxy instance exists."""
        assert llm_proxy is not None
        assert isinstance(llm_proxy, LLMProxy)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
