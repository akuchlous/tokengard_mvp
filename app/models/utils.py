"""
Model Utilities

This module contains utility functions for the models package.
"""

import secrets
import string
from .database import db

def generate_user_id():
    """Generate a unique 12-character user ID"""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))

def generate_activation_token():
    """Generate a secure activation token"""
    return secrets.token_urlsafe(32)

def generate_password_reset_token():
    """Generate a secure password reset token"""
    return secrets.token_urlsafe(32)

def generate_api_key():
    """Generate a secure API key with 'tk-' prefix"""
    return 'tk-' + secrets.token_urlsafe(32)

def generate_api_key_name():
    """Generate a unique 6-character alphanumeric key name"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(6))

def generate_api_key_value():
    """Generate a new API key value with 'tk-' prefix and 32 alphanumeric characters"""
    return "tk-" + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))


