import pytest
import json
from models import User, PasswordResetToken
from auth_utils import hash_password


class TestAuth:
    """Test authentication functionality"""
    
    def test_forgot_password_active_user(self, app, client, db_session):
        """Test that password reset is only allowed for active users"""
        # Create an inactive user
        inactive_user = User(
            email='inactive@example.com',
            password_hash=hash_password('hashed_password')
        )
        inactive_user.status = 'inactive'  # Ensure inactive status
        db_session.add(inactive_user)
        db_session.commit()
        
        # Try to request password reset for inactive user
        response = client.post('/auth/forgot-password', 
                              data=json.dumps({'email': 'inactive@example.com'}),
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        # Should not indicate that email was sent for inactive user
        assert 'If an account with this email exists' in data['message']
        
        # Create an active user
        active_user = User(
            email='active@example.com',
            password_hash=hash_password('hashed_password')
        )
        active_user.status = 'active'  # Mark as active
        db_session.add(active_user)
        db_session.commit()
        
        # Try to request password reset for active user
        response = client.post('/auth/forgot-password', 
                              data=json.dumps({'email': 'active@example.com'}),
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        # Should indicate that email was sent for active user
        assert 'If active user, the email will be send for passwd reset' in data['message']
        
        # Verify that a password reset token was created
        reset_token = PasswordResetToken.query.filter_by(user_id=active_user.id).first()
        assert reset_token is not None
    
    def test_forgot_password_get_page(self, client):
        """Test that the forgot password page loads correctly"""
        response = client.get('/auth/forgot-password')
        assert response.status_code == 200
        assert b'Reset Password' in response.data
        assert b'Enter your email to receive a password reset link' in response.data
    
    def test_forgot_password_invalid_email(self, client):
        """Test that invalid email format is rejected"""
        response = client.post('/auth/forgot-password', 
                              data=json.dumps({'email': 'invalid-email'}),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Invalid email format' in data['error']
    
    def test_forgot_password_missing_email(self, client):
        """Test that missing email is rejected"""
        response = client.post('/auth/forgot-password', 
                              data=json.dumps({}),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Email is required' in data['error']
    
    def test_forgot_password_nonexistent_user(self, client, db_session):
        """Test that non-existent users get a generic message"""
        response = client.post('/auth/forgot-password', 
                              data=json.dumps({'email': 'nonexistent@example.com'}),
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'If an account with this email exists' in data['message']



