from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import secrets
import string

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication and user management"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='inactive', nullable=False)
    created_at = db.Column(db.DateTime, default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    activation_tokens = db.relationship('ActivationToken', backref='user', lazy=True, cascade='all, delete-orphan')
    password_reset_tokens = db.relationship('PasswordResetToken', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, email, password_hash):
        self.user_id = self._generate_user_id()
        self.email = email
        self.password_hash = password_hash
    
    def _generate_user_id(self):
        """Generate a unique user ID for redirects (not for authentication)"""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    
    def is_active(self):
        """Check if user account is active"""
        return self.status == 'active'
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.email}>'

class ActivationToken(db.Model):
    """Token model for email verification"""
    __tablename__ = 'activation_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=func.now(), nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    
    def __init__(self, user_id, expires_in_hours=24):
        self.token = self._generate_token()
        self.user_id = user_id
        self.expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
    
    def _generate_token(self):
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)
    
    def is_valid(self):
        """Check if token is valid and not expired"""
        return not self.used and datetime.utcnow() < self.expires_at
    
    def mark_used(self):
        """Mark token as used"""
        self.used = True
        db.session.commit()
    
    def __repr__(self):
        return f'<ActivationToken {self.token[:8]}...>'

class PasswordResetToken(db.Model):
    """Token model for password reset"""
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=func.now(), nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    
    def __init__(self, user_id, expires_in_hours=1):
        self.token = self._generate_token()
        self.user_id = user_id
        self.expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
    
    def _generate_token(self):
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)
    
    def is_valid(self):
        """Check if token is valid and not expired"""
        return not self.used and datetime.utcnow() < self.expires_at
    
    def mark_used(self):
        """Mark token as used"""
        self.used = True
        db.session.commit()
    
    def __repr__(self):
        return f'<PasswordResetToken {self.token[:8]}...>'
