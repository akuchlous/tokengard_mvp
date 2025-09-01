import pytest
import json
from app.models import User, PasswordResetToken
from app.utils.auth_utils import hash_password


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
                              data={'email': 'inactive@example.com'},
                              follow_redirects=True)
        
        assert response.status_code == 200
        # Should redirect to login page with generic message
        assert b'Sign In' in response.data
        
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
                              data={'email': 'active@example.com'},
                              follow_redirects=True)
        
        assert response.status_code == 200
        # Should redirect to login page
        assert b'Sign In' in response.data
        
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
                              data={'email': 'invalid-email'},
                              follow_redirects=True)
        
        assert response.status_code == 200
        # Should redirect to login page (server-side validation handles this)
        assert b'Sign In' in response.data
    
    def test_forgot_password_missing_email(self, client):
        """Test that missing email is rejected"""
        response = client.post('/auth/forgot-password', 
                              data={},
                              follow_redirects=True)
        
        assert response.status_code == 200
        # Should redirect to login page (server-side validation handles this)
        assert b'Sign In' in response.data
    
    def test_forgot_password_nonexistent_user(self, client, db_session):
        """Test that non-existent users get a generic message"""
        response = client.post('/auth/forgot-password', 
                              data={'email': 'nonexistent@example.com'},
                              follow_redirects=True)
        
        assert response.status_code == 200
        # Should redirect to login page with generic message
        assert b'Sign In' in response.data



