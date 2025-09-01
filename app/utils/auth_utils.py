"""
Authentication Utilities

This module contains utility functions for authentication and user management.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from flask_mail import Message
from ..models import db, User, ActivationToken, PasswordResetToken
from flask import current_app

def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return hash_password(password) == password_hash

def create_user(email, password):
    """Create a new user with activation token"""
    # Hash the password
    password_hash = hash_password(password)
    
    # Create user
    user = User(email=email, password_hash=password_hash)
    db.session.add(user)
    db.session.flush()  # Get the user ID
    
    # Create activation token
    activation_token = ActivationToken(user.id)
    db.session.add(activation_token)
    
    db.session.commit()
    
    return user, activation_token

def authenticate_user(email, password):
    """Authenticate a user with email and password"""
    user = User.query.filter_by(email=email).first()
    
    # Security: Only active users can authenticate
    if user and user.is_active() and verify_password(password, user.password_hash):
        return user
    
    return None

def generate_jwt_token(user_id, expires_in_hours=1):
    """Generate a JWT token for a user"""
    # This is a simplified JWT implementation
    # In production, use a proper JWT library like PyJWT
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
        'iat': datetime.utcnow()
    }
    
    # For now, return a simple token
    # In production, this should be properly signed and encoded
    return secrets.token_urlsafe(32)

def verify_jwt_token(token):
    """Verify a JWT token and return user_id if valid"""
    # This is a simplified JWT verification
    # In production, use a proper JWT library like PyJWT
    
    # For now, we'll just check if the token exists in the database
    # This is not secure and should be replaced with proper JWT verification
    return None

def get_user_by_token(token):
    """Get user by token (for password reset)"""
    reset_token = PasswordResetToken.query.filter_by(token=token).first()
    
    if reset_token and reset_token.is_valid():
        return User.query.get(reset_token.user_id)
    
    return None

def send_activation_email(user, activation_token):
    """Send activation email to user"""
    try:
        # In a real application, you would use Flask-Mail to send emails
        # For now, we'll just return True to simulate success
        
        # Example of how this would work with Flask-Mail:
        # msg = Message(
        #     'Activate Your Account',
        #     recipients=[user.email],
        #     body=f'Click this link to activate your account: {activation_url}'
        # )
        # mail.send(msg)
        
        print(f"Activation email would be sent to {user.email}")
        print(f"Activation token: {activation_token.token}")
        
        return True
        
    except Exception as e:
        print(f"Failed to send activation email: {e}")
        return False

def send_password_reset_email(user, reset_token):
    """Send password reset email to user"""
    try:
        # In a real application, you would use Flask-Mail to send emails
        # For now, we'll just return True to simulate success
        
        # Example of how this would work with Flask-Mail:
        # msg = Message(
        #     'Reset Your Password',
        #     recipients=[user.email],
        #     body=f'Click this link to reset your password: {reset_url}'
        # )
        # mail.send(msg)
        
        print(f"Password reset email would be sent to {user.email}")
        print(f"Reset token: {reset_token.token}")
        
        return True
        
    except Exception as e:
        print(f"Failed to send password reset email: {e}")
        return False
