#!/usr/bin/env python3
"""
Tests for the proxy endpoint that validates API keys
"""

import pytest
import json
from models import db, User, APIKey, create_default_api_key
from auth_utils import hash_password


class TestProxyEndpoint:
    """Test the /api/proxy endpoint"""
    
    @pytest.fixture
    def test_user_with_keys(self, app, db_session):
        """Create a test user with API keys"""
        user = User(
            email='proxy_test@example.com',
            password_hash=hash_password('password123')
        )
        user.status = 'active'  # Make user active
        db_session.add(user)
        db_session.commit()
        
        # Create API keys for the user
        api_keys = create_default_api_key(user.id)
        
        # Deactivate one key for testing
        api_keys[1].state = 'disabled'
        db_session.commit()
        
        return user, api_keys
    
    def test_proxy_endpoint_valid_key(self, app, test_user_with_keys):
        """Test proxy endpoint with valid, active API key"""
        user, api_keys = test_user_with_keys
        active_key = api_keys[0]  # key_0 should be active
        
        with app.test_client() as client:
            response = client.post('/api/proxy', 
                json={
                    'api_key': active_key.key_value,
                    'text': 'Hello, world!'
                },
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'key_pass'
            assert data['message'] == 'API key is valid.'
            assert data['key_name'] == 'key_0'
            assert data['text_length'] == 13
    
    def test_proxy_endpoint_invalid_key(self, app, test_user_with_keys):
        """Test proxy endpoint with invalid API key"""
        with app.test_client() as client:
            response = client.post('/api/proxy', 
                json={
                    'api_key': 'tk-invalid-key-that-does-not-exist',
                    'text': 'Hello, world!'
                },
                content_type='application/json'
            )
            
            assert response.status_code == 401
            data = response.get_json()
            assert data['status'] == 'key_error'
            assert data['message'] == 'API key not found.'
    
    def test_proxy_endpoint_inactive_key(self, app, test_user_with_keys):
        """Test proxy endpoint with inactive/disabled API key"""
        user, api_keys = test_user_with_keys
        inactive_key = api_keys[1]  # key_1 was disabled in fixture
        
        with app.test_client() as client:
            response = client.post('/api/proxy', 
                json={
                    'api_key': inactive_key.key_value,
                    'text': 'Hello, world!'
                },
                content_type='application/json'
            )
            
            assert response.status_code == 401
            data = response.get_json()
            assert data['status'] == 'key_error'
            assert data['message'] == 'API key is inactive.'
    
    def test_proxy_endpoint_missing_api_key(self, app, test_user_with_keys):
        """Test proxy endpoint with missing API key"""
        with app.test_client() as client:
            response = client.post('/api/proxy', 
                json={
                    'text': 'Hello, world!'
                },
                content_type='application/json'
            )
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['status'] == 'key_error'
            assert data['message'] == 'API key is required.'
    
    def test_proxy_endpoint_empty_api_key(self, app, test_user_with_keys):
        """Test proxy endpoint with empty API key"""
        with app.test_client() as client:
            response = client.post('/api/proxy', 
                json={
                    'api_key': '',
                    'text': 'Hello, world!'
                },
                content_type='application/json'
            )
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['status'] == 'key_error'
            assert data['message'] == 'API key is required.'
    
    def test_proxy_endpoint_no_json(self, app, test_user_with_keys):
        """Test proxy endpoint with no JSON payload"""
        with app.test_client() as client:
            response = client.post('/api/proxy')
            
            # Flask returns 415 when no JSON content-type is provided
            assert response.status_code == 415 or response.status_code == 400
            
            # If we get a JSON response, check the error message
            if response.content_type and 'application/json' in response.content_type:
                data = response.get_json()
                assert data['status'] == 'key_error'
                assert data['message'] == 'Invalid request format. JSON payload required.'
    
    def test_proxy_endpoint_no_text(self, app, test_user_with_keys):
        """Test proxy endpoint with valid key but no text"""
        user, api_keys = test_user_with_keys
        active_key = api_keys[0]
        
        with app.test_client() as client:
            response = client.post('/api/proxy', 
                json={
                    'api_key': active_key.key_value
                },
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'key_pass'
            assert data['message'] == 'API key is valid.'
            assert data['key_name'] == 'key_0'
            assert data['text_length'] == 0
    
    def test_proxy_endpoint_updates_last_used(self, app, test_user_with_keys):
        """Test that proxy endpoint updates the last_used timestamp"""
        user, api_keys = test_user_with_keys
        active_key = api_keys[0]
        
        # Record initial last_used (should be None)
        initial_last_used = active_key.last_used
        assert initial_last_used is None
        
        with app.test_client() as client:
            response = client.post('/api/proxy', 
                json={
                    'api_key': active_key.key_value,
                    'text': 'Test text'
                },
                content_type='application/json'
            )
            
            assert response.status_code == 200
            
            # Refresh the key from database
            db.session.refresh(active_key)
            
            # Verify last_used was updated
            assert active_key.last_used is not None
            assert active_key.last_used != initial_last_used


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
