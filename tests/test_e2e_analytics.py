"""
Unit Tests for Analytics and Logging

This module contains unit tests for the analytics and logging functionality.
"""

import pytest
import time
import json
from app import create_app, db
from app.models import User, APIKey, ProxyLog
from app.utils.auth_utils import hash_password


class TestAnalyticsUnit:
    """Unit tests for analytics and logging functionality."""
    
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
        """Create test data for analytics testing."""
        # Create test user
        self.user = User(
            email='analytics@example.com',
            password_hash=hash_password('TestPass123!')
        )
        self.user.status = 'active'
        db.session.add(self.user)
        db.session.commit()
        
        # Create API keys
        self.api_key1 = APIKey(
            user_id=self.user.id,
            key_name='key_0',
            key_value='tk-analytics123456789012345678901234'
        )
        db.session.add(self.api_key1)
        
        self.api_key2 = APIKey(
            user_id=self.user.id,
            key_name='key_1',
            key_value='tk-analytics234567890123456789012345'
        )
        db.session.add(self.api_key2)
        db.session.commit()
        
        # Create sample log entries for analytics
        self.create_sample_logs()
    
    def create_sample_logs(self):
        """Create sample log entries for testing analytics."""
        # Create successful API calls
        for i in range(5):
            log = ProxyLog.create_log(
                api_key=self.api_key1,
                request_body=f'{{"test": "success_{i}", "data": "sample_data"}}',
                response_status='key_pass',
                response_body='{"status": "success", "message": "API key is valid"}',
                client_ip='127.0.0.1',
                user_agent='test-agent',
                request_id=f'test-request-{i}',
                processing_time_ms=100 + i * 10
            )
            db.session.commit()
            time.sleep(0.01)  # Ensure different timestamps
        
        # Create failed API calls
        for i in range(3):
            log = ProxyLog.create_log(
                api_key=self.api_key2,
                request_body=f'{{"test": "error_{i}", "data": "sample_data"}}',
                response_status='key_error',
                response_body='{"status": "error", "message": "API key is invalid"}',
                client_ip='127.0.0.1',
                user_agent='test-agent',
                request_id=f'test-error-{i}',
                processing_time_ms=50 + i * 5
            )
            db.session.commit()
            time.sleep(0.01)
    

    
    def test_analytics_page_access(self):
        """Test that analytics page is accessible and displays correctly."""
        with self.app.test_client() as client:
            # Login user via session
            with client.session_transaction() as sess:
                sess['user_id'] = self.user.user_id
            
            # Test logs page access
            response = client.get(f'/logs/{self.user.user_id}')
            assert response.status_code == 200
            
            # Verify page content
            assert b'API Usage Logs' in response.data
            assert b'analytics@example.com' in response.data
            assert b'stats-summary' in response.data
            assert b'excel-table-container' in response.data
    
    def test_analytics_page_requires_auth(self):
        """Analytics page should require authentication."""
        with self.app.test_client() as client:
            response = client.get(f'/analytics/{self.user.user_id}')
            assert response.status_code == 401
    
    def test_analytics_page_self_only(self):
        """Analytics page should only be viewable by the same logged-in user."""
        with self.app.test_client() as client:
            # Login as real user
            with client.session_transaction() as sess:
                sess['user_id'] = self.user.user_id
            # Attempt to view another user's analytics
            response = client.get('/analytics/OTHERUSER1234')
            assert response.status_code == 403
    
    def test_analytics_statistics_display(self):
        """Test that analytics statistics are displayed correctly."""
        with self.app.test_client() as client:
            # Login user via session
            with client.session_transaction() as sess:
                sess['user_id'] = self.user.user_id
            
            # Test logs page access
            response = client.get(f'/logs/{self.user.user_id}')
            assert response.status_code == 200
            
            # Verify stats section is present
            assert b'stats-summary' in response.data
            assert b'stat-card' in response.data
            assert b'Total Calls' in response.data
            assert b'Successful' in response.data
            assert b'Failed' in response.data
            assert b'Avg Response (ms)' in response.data
    
    def test_logs_table_display(self):
        """Test that logs table displays correctly with data."""
        with self.app.test_client() as client:
            # Login user via session
            with client.session_transaction() as sess:
                sess['user_id'] = self.user.user_id
            
            # Test logs page access
            response = client.get(f'/logs/{self.user.user_id}')
            assert response.status_code == 200
            
            # Verify table structure is present
            assert b'excel-table-container' in response.data
            assert b'Timestamp' in response.data
            assert b'API Key' in response.data
            assert b'Status' in response.data
            assert b'Request Body' in response.data
            assert b'Response' in response.data
            assert b'Processing Time' in response.data
    
    def test_logs_filtering_functionality(self):
        """Test that logs filtering works correctly."""
        with self.app.test_client() as client:
            # Login user via session
            with client.session_transaction() as sess:
                sess['user_id'] = self.user.user_id
            
            # Test logs page access
            response = client.get(f'/logs/{self.user.user_id}')
            assert response.status_code == 200
            
            # Verify filters section is present
            assert b'filters-section' in response.data
            assert b'statusFilter' in response.data
            assert b'apiKeyFilter' in response.data
            assert b'applyFilters()' in response.data
    
    def test_logs_pagination(self):
        """Test that logs pagination works correctly."""
        with self.app.test_client() as client:
            # Login user via session
            with client.session_transaction() as sess:
                sess['user_id'] = self.user.user_id
            
            # Test logs page access
            response = client.get(f'/logs/{self.user.user_id}')
            assert response.status_code == 200
            
            # Verify pagination elements are present in the HTML
            assert b'pagination' in response.data
            assert b'prevPage' in response.data
            assert b'nextPage' in response.data
            assert b'pageInfo' in response.data
    
    def test_analytics_api_endpoints(self):
        """Test that analytics API endpoints work correctly."""
        with self.app.test_client() as client:
            # Login user
            with client.session_transaction() as sess:
                sess['user_id'] = self.user.user_id
            
            # Test logs endpoint
            response = client.get('/api/logs')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'logs' in data
            assert len(data['logs']) > 0
            
            # Test stats endpoint
            response = client.get('/api/logs/stats')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'stats' in data
            stats = data['stats']
            assert stats['total_calls'] > 0
            assert stats['successful_calls'] > 0
            assert stats['failed_calls'] > 0
            
            # Test search endpoint
            search_payload = {
                'status': 'key_pass',
                'limit': 10
            }
            response = client.post('/api/logs/search', json=search_payload)
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'logs' in data
            assert len(data['logs']) > 0
            
            # Verify all returned logs have key_pass status
            for log in data['logs']:
                assert log['response_status'] == 'key_pass'
    
    def test_analytics_with_real_api_calls(self):
        """Test analytics by making real API calls and verifying they're logged."""
        with self.app.test_client() as client:
            # Login user via session
            with client.session_transaction() as sess:
                sess['user_id'] = self.user.user_id
            
            # Get initial log count
            initial_response = client.get('/api/logs')
            initial_data = json.loads(initial_response.data)
            initial_count = len(initial_data['logs'])
            
            # Make some API calls to the proxy endpoint
            test_payloads = [
                {'api_key': self.api_key1.key_value, 'text': 'test1'},
                {'api_key': self.api_key1.key_value, 'text': 'test2'},
                {'api_key': 'tk-invalidkey123456789012345678901', 'text': 'test3'}
            ]
            
            for payload in test_payloads:
                response = client.post('/api/proxy', json=payload)
                assert response.status_code in [200, 401]  # Valid or invalid key
            
            # Check that new logs were created
            final_response = client.get('/api/logs')
            final_data = json.loads(final_response.data)
            final_count = len(final_data['logs'])
            
            # Should have at least 2 new logs (2 successful calls)
            assert final_count >= initial_count + 2, f"Expected at least {initial_count + 2} logs, found {final_count}"
            
            # Test logs page access
            response = client.get(f'/logs/{self.user.user_id}')
            assert response.status_code == 200
            
            # Verify page loads correctly
            assert b'API Usage Logs' in response.data
            assert b'excel-table-container' in response.data
