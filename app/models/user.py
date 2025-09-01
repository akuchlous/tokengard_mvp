"""
User Models

This module contains the User, ActivationToken, and PasswordResetToken models.
"""

from datetime import datetime, timedelta
from .database import db
from .utils import generate_user_id, generate_activation_token, generate_password_reset_token


class User(db.Model):
    """User model for authentication and profile management"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(12), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='inactive')  # inactive, active, suspended
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    activation_tokens = db.relationship('ActivationToken', backref='user', lazy=True)
    password_reset_tokens = db.relationship('PasswordResetToken', backref='user', lazy=True)
    api_keys = db.relationship('APIKey', backref='user', lazy=True)
    
    def __init__(self, email, password_hash):
        """Initialize a new user with comprehensive security validation"""
        # Import validators here to avoid circular imports
        from ..utils.validators import validate_email, validate_password_hash
        
        # Security: Validate email using dedicated validation module
        email_validation = validate_email(email)
        if not email_validation.is_valid:
            raise ValueError(email_validation.error_message)
        
        # Security: Validate password hash using dedicated validation module
        hash_validation = validate_password_hash(password_hash)
        if not hash_validation.is_valid:
            raise ValueError(hash_validation.error_message)
        
        # Set validated and sanitized values
        self.email = email_validation.sanitized_value
        self.password_hash = hash_validation.sanitized_value
        self.user_id = generate_user_id()
        
        # Security: Set default status to inactive until email verification
        self.status = 'inactive'
    
    def is_active(self):
        """Check if user account is active"""
        return self.status == 'active'
    
    def update_last_login(self):
        """Update the last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()

class ActivationToken(db.Model):
    """Activation token for user account activation"""
    __tablename__ = 'activation_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(255), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    
    def __init__(self, user_id, expires_in_hours=24):
        """Initialize a new activation token"""
        self.user_id = user_id
        self.token = generate_activation_token()
        self.expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
    
    def is_valid(self):
        """Check if token is valid and not expired"""
        return not self.used and datetime.utcnow() < self.expires_at
    
    def mark_used(self):
        """Mark token as used"""
        self.used = True
        db.session.commit()

class PasswordResetToken(db.Model):
    """Password reset token for password recovery"""
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(255), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    
    def __init__(self, user_id, expires_in_hours=1):
        """Initialize a new password reset token"""
        self.user_id = user_id
        self.token = generate_password_reset_token()
        self.expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
    
    def is_valid(self):
        """Check if token is valid and not expired"""
        return not self.used and datetime.utcnow() < self.expires_at
    
    def mark_used(self):
        """Mark token as used"""
        self.used = True
        db.session.commit()
