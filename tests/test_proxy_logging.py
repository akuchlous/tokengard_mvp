"""
Tests for Proxy Logging Functionality

This module contains comprehensive tests for the proxy endpoint logging system.
"""

import pytest
import json
import time
from datetime import datetime, timedelta
from app import create_app, db
from app.models import User, APIKey, ProxyLog
from app.utils.auth_utils import hash_password


class TestProxyLogging:
    """Test suite for proxy endpoint logging functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment before each test."""
        # Create test app with test configuration
        test_config = {
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test-secret-key',
            'JWT_SECRET_KEY': 'test-jwt-secret-key',
            'MAIL_SERVER': 'localhost',
            'MAIL_PORT': 587,
            'MAIL_USE_TLS': False,
            'MAIL_USE_SSL': False,
            'MAIL_USERNAME': 'test@example.com',
            'MAIL_PASSWORD': 'test-password',
            'MAIL_DEFAULT_SENDER': 'test@example.com'
        }
        self.app = create_app(test_config)
        
        # Create test client
        self.client = self.app.test_client()
        
        # Create application context
        with self.app.app_context():
            # Create database tables
            db.create_all()
            
            # Create test data
            self.setup_test_data()
            
            yield
            
            # Clean up
            db.session.remove()
            db.drop_all()
    
    def setup_test_data(self):
        """Create test data for testing."""
        # Create test users
        self.user1 = User(
            email='user1@example.com',
            password_hash=hash_password('TestPass123!')
        )
        self.user1.status = 'active'
        db.session.add(self.user1)
        
        self.user2 = User(
            email='user2@example.com',
            password_hash=hash_password('TestPass123!')
        )
        self.user2.status = 'active'
        db.session.add(self.user2)
        
        db.session.commit()
        
        # Create API keys
        self.api_key1 = APIKey(
            user_id=self.user1.id,
            key_name='A_KEY',
            key_value='tk-testkey123456789012345678901234'
        )
        db.session.add(self.api_key1)
        
        self.api_key2 = APIKey(
            user_id=self.user1.id,
            key_name='B_KEY',
            key_value='tk-testkey234567890123456789012345'
        )
        db.session.add(self.api_key2)
        
        self.api_key3 = APIKey(
            user_id=self.user2.id,
            key_name='A_KEY',
            key_value='tk-testkey345678901234567890123456'
        )
        db.session.add(self.api_key3)
        
        db.session.commit()
    
    def test_proxy_endpoint_logs_valid_key(self):
        """Test that proxy endpoint logs successful requests."""
        payload = {
            'api_key': self.api_key1.key_value,
            'text': 'Hello, world!',
            'policy_only': False
        }
        
        response = self.client.post(
            '/api/proxy',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get('object') == 'chat.completion'
        
        # Check that log was created
        with self.app.app_context():
            logs = ProxyLog.query.filter_by(api_key_id=self.api_key1.id).all()
            assert len(logs) == 1
            
            log = logs[0]
            assert log.api_key_value == self.api_key1.key_value
            assert log.response_status == 'key_pass'
            assert log.request_body == json.dumps(payload)
            assert log.processing_time_ms is not None
            assert log.processing_time_ms > 0
    
    def test_proxy_endpoint_logs_invalid_key(self):
        """Test that proxy endpoint logs failed requests."""
        payload = {
            'api_key': 'tk-invalidkey123456789012345678901',
            'text': 'Hello, world!',
            'policy_only': False
        }
        
        response = self.client.post(
            '/api/proxy',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data and isinstance(data['error'], dict)
        
        # Check that log was created for invalid key attempt
        with self.app.app_context():
            logs = ProxyLog.query.filter_by(api_key_value='tk-invalidkey123456789012345678901').all()
            assert len(logs) == 1
            
            log = logs[0]
            assert log.api_key_value == 'tk-invalidkey123456789012345678901'
            assert log.response_status == 'key_error'
            assert log.request_body == json.dumps(payload)
    

    
    def test_proxy_log_model_creation(self):
        """Test ProxyLog model creation and methods."""
        with self.app.app_context():
            # Create a log entry
            log = ProxyLog.create_log(
                api_key=self.api_key1,
                request_body='{"test": "data"}',
                response_status='key_pass',
                response_body='{"status": "success"}',
                client_ip='127.0.0.1',
                user_agent='test-agent',
                request_id='test-request-id',
                processing_time_ms=150
            )
            
            db.session.commit()
            
            # Test model properties
            assert log.api_key_id == self.api_key1.id
            assert log.api_key_value == self.api_key1.key_value
            assert log.request_body == '{"test": "data"}'
            assert log.response_status == 'key_pass'
            assert log.response_body == '{"status": "success"}'
            assert log.client_ip == '127.0.0.1'
            assert log.user_agent == 'test-agent'
            assert log.request_id == 'test-request-id'
            assert log.processing_time_ms == 150
            
            # Test to_dict method
            log_dict = log.to_dict()
            assert log_dict['api_key_value'] == self.api_key1.key_value
            assert log_dict['response_status'] == 'key_pass'
            assert log_dict['processing_time_ms'] == 150
    
    def test_proxy_log_get_logs_by_api_key(self):
        """Test getting logs by API key."""
        with self.app.app_context():
            # Create multiple log entries
            for i in range(3):
                log = ProxyLog.create_log(
                    api_key=self.api_key1,
                    request_body=f'{{"test": "data_{i}"}}',
                    response_status='key_pass',
                    response_body='{"status": "success"}'
                )
                db.session.commit()
                time.sleep(0.01)  # Ensure different timestamps
            
            # Get logs for API key
            logs = ProxyLog.get_logs_by_api_key(self.api_key1.key_value)
            assert len(logs) == 3
            
            # Test with limit
            logs = ProxyLog.get_logs_by_api_key(self.api_key1.key_value, limit=2)
            assert len(logs) == 2
            
            # Test with offset
            logs = ProxyLog.get_logs_by_api_key(self.api_key1.key_value, offset=1)
            assert len(logs) == 2
    
    def test_proxy_log_get_logs_by_user(self):
        """Test getting logs by user."""
        with self.app.app_context():
            # Create log entries for different users
            ProxyLog.create_log(
                api_key=self.api_key1,
                request_body='{"user": "1"}',
                response_status='key_pass',
                response_body='{"status": "success"}'
            )
            
            ProxyLog.create_log(
                api_key=self.api_key2,
                request_body='{"user": "1"}',
                response_status='key_pass',
                response_body='{"status": "success"}'
            )
            
            ProxyLog.create_log(
                api_key=self.api_key3,
                request_body='{"user": "2"}',
                response_status='key_pass',
                response_body='{"status": "success"}'
            )
            
            db.session.commit()
            
            # Get logs for user1
            logs = ProxyLog.get_logs_by_user(self.user1.id)
            assert len(logs) == 2
            
            # Get logs for user2
            logs = ProxyLog.get_logs_by_user(self.user2.id)
            assert len(logs) == 1
    
    def test_proxy_log_get_stats_by_user(self):
        """Test getting statistics by user."""
        with self.app.app_context():
            # Create log entries with different statuses
            ProxyLog.create_log(
                api_key=self.api_key1,
                request_body='{"test": "1"}',
                response_status='key_pass',
                response_body='{"status": "success"}',
                processing_time_ms=100
            )
            
            ProxyLog.create_log(
                api_key=self.api_key1,
                request_body='{"test": "2"}',
                response_status='key_pass',
                response_body='{"status": "success"}',
                processing_time_ms=200
            )
            
            ProxyLog.create_log(
                api_key=self.api_key2,
                request_body='{"test": "3"}',
                response_status='key_error',
                response_body='{"status": "error"}',
                processing_time_ms=50
            )
            
            db.session.commit()
            
            # Get stats
            stats = ProxyLog.get_log_stats_by_user(self.user1.id)
            
            assert stats['total_calls'] == 3
            assert stats['successful_calls'] == 2
            assert stats['failed_calls'] == 1
            assert stats['unique_keys_used'] == 2
            assert stats['avg_processing_time'] == 116.67  # (100 + 200 + 50) / 3
    
    def test_proxy_log_date_filtering(self):
        """Test log filtering by date range."""
        with self.app.app_context():
            # Create logs with different timestamps
            now = datetime.utcnow()
            
            # Create log 1 hour ago
            log1 = ProxyLog.create_log(
                api_key=self.api_key1,
                request_body='{"test": "1"}',
                response_status='key_pass',
                response_body='{"status": "success"}'
            )
            log1.request_timestamp = now - timedelta(hours=1)
            
            # Create log 30 minutes ago
            log2 = ProxyLog.create_log(
                api_key=self.api_key1,
                request_body='{"test": "2"}',
                response_status='key_pass',
                response_body='{"status": "success"}'
            )
            log2.request_timestamp = now - timedelta(minutes=30)
            
            db.session.commit()
            
            # Test date filtering
            start_date = now - timedelta(minutes=45)
            end_date = now - timedelta(minutes=15)
            
            logs = ProxyLog.get_logs_by_api_key(
                self.api_key1.key_value,
                start_date=start_date,
                end_date=end_date
            )
            
            assert len(logs) == 1
            assert logs[0].request_body == '{"test": "2"}'


class TestProxyLogAPI:
    """Test suite for proxy log API endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment before each test."""
        test_config = {
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test-secret-key',
            'JWT_SECRET_KEY': 'test-jwt-secret-key',
            'MAIL_SERVER': 'localhost',
            'MAIL_PORT': 587,
            'MAIL_USE_TLS': False,
            'MAIL_USE_SSL': False,
            'MAIL_USERNAME': 'test@example.com',
            'MAIL_PASSWORD': 'test-password',
            'MAIL_DEFAULT_SENDER': 'test@example.com'
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            self.setup_test_data()
            yield
            db.session.remove()
            db.drop_all()
    
    def setup_test_data(self):
        """Create test data for API testing."""
        # Create test user
        self.user = User(
            email='test@example.com',
            password_hash=hash_password('TestPass123!')
        )
        self.user.status = 'active'
        db.session.add(self.user)
        db.session.commit()
        
        # Create API key
        self.api_key = APIKey(
            user_id=self.user.id,
            key_name='A_KEY',
            key_value='tk-testkey123456789012345678901234'
        )
        db.session.add(self.api_key)
        db.session.commit()
        
        # Create some log entries
        for i in range(5):
            log = ProxyLog.create_log(
                api_key=self.api_key,
                request_body=f'{{"test": "data_{i}"}}',
                response_status='key_pass' if i % 2 == 0 else 'key_error',
                response_body='{"status": "success"}' if i % 2 == 0 else '{"status": "error"}',
                processing_time_ms=100 + i * 10
            )
            db.session.commit()
            time.sleep(0.01)
    
    def test_get_logs_requires_authentication(self):
        """Test that getting logs requires authentication."""
        response = self.client.get('/api/logs')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'Authentication required' in data['error']
    
    def test_get_logs_with_authentication(self):
        """Test getting logs with authentication."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.user_id
        
        response = self.client.get('/api/logs')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'logs' in data
        assert len(data['logs']) == 5
        assert data['count'] == 5
    
    def test_get_logs_with_limit(self):
        """Test getting logs with limit parameter."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.user_id
        
        response = self.client.get('/api/logs?limit=3')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert len(data['logs']) == 3
        assert data['limit'] == 3
    
    def test_get_logs_with_api_key_filter(self):
        """Test getting logs filtered by API key."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.user_id
        
        response = self.client.get(f'/api/logs?api_key={self.api_key.key_value}')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert len(data['logs']) == 5
        for log in data['logs']:
            assert log['api_key_value'] == self.api_key.key_value
    
    def test_get_logs_with_invalid_api_key(self):
        """Test getting logs with invalid API key."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.user_id
        
        response = self.client.get('/api/logs?api_key=tk-invalidkey123456789012345678901')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'API key not found or access denied' in data['error']
    
    def test_get_log_stats_requires_authentication(self):
        """Test that getting log stats requires authentication."""
        response = self.client.get('/api/logs/stats')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'Authentication required' in data['error']
    
    def test_get_log_stats_with_authentication(self):
        """Test getting log stats with authentication."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.user_id
        
        response = self.client.get('/api/logs/stats')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'stats' in data
        stats = data['stats']
        assert stats['total_calls'] == 5
        assert stats['successful_calls'] == 3  # 0, 2, 4 are even (key_pass)
        assert stats['failed_calls'] == 2  # 1, 3 are odd (key_error)
        assert stats['unique_keys_used'] == 1
    
    def test_search_logs_requires_authentication(self):
        """Test that searching logs requires authentication."""
        response = self.client.post('/api/logs/search', json={})
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'Authentication required' in data['error']
    
    def test_search_logs_with_status_filter(self):
        """Test searching logs with status filter."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.user_id
        
        payload = {
            'status': 'key_pass',
            'limit': 10
        }
        
        response = self.client.post('/api/logs/search', json=payload)
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert len(data['logs']) == 3
        for log in data['logs']:
            assert log['response_status'] == 'key_pass'
    
    def test_search_logs_with_api_key_filter(self):
        """Test searching logs with API key filter."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.user_id
        
        payload = {
            'api_key': self.api_key.key_value,
            'status': 'key_error'
        }
        
        response = self.client.post('/api/logs/search', json=payload)
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert len(data['logs']) == 2
        for log in data['logs']:
            assert log['response_status'] == 'key_error'
            assert log['api_key_value'] == self.api_key.key_value
