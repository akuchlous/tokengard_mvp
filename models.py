import sqlite3
from datetime import datetime, timedelta
import secrets
import string
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_property

db = SQLAlchemy()

class User(db.Model):
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
        self.email = email
        self.password_hash = password_hash
        self.user_id = generate_user_id()
    
    def is_active(self):
        return self.status == 'active'
    
    def update_last_login(self):
        self.last_login = datetime.utcnow()
        db.session.commit()

class ActivationToken(db.Model):
    __tablename__ = 'activation_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(255), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    
    def __init__(self, user_id, expires_in_hours=24):
        self.user_id = user_id
        self.token = generate_activation_token()
        self.expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
    
    def is_valid(self):
        return not self.used and datetime.utcnow() < self.expires_at
    
    def mark_used(self):
        self.used = True
        db.session.commit()

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(255), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    
    def __init__(self, user_id, expires_in_hours=1):
        self.user_id = user_id
        self.token = generate_password_reset_token()
        self.expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
    
    def is_valid(self):
        return not self.used and datetime.utcnow() < self.expires_at
    
    def mark_used(self):
        self.used = True
        db.session.commit()

class APIKey(db.Model):
    __tablename__ = 'api_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    key_name = db.Column(db.String(6), nullable=False)  # 6-digit alphanumeric
    key_value = db.Column(db.String(38), nullable=False)  # "tk-" + 32 alphanumeric
    state = db.Column(db.String(20), default='enabled')  # enabled, disabled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'key_name', name='unique_user_key_name'),
    )
    
    def is_enabled(self):
        return self.state == 'enabled'
    
    def disable(self):
        self.state = 'disabled'
        db.session.commit()
    
    def enable(self):
        self.state = 'enabled'
        db.session.commit()
    
    def refresh_key_value(self):
        """Generate a new key_value while keeping the same key_name"""
        self.key_value = generate_api_key_value()
        db.session.commit()
    
    def update_last_used(self):
        self.last_used = datetime.utcnow()
        db.session.commit()

def generate_user_id():
    """Generate a unique 12-character user ID"""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))

def generate_activation_token():
    """Generate a unique activation token"""
    while True:
        token = secrets.token_urlsafe(32)
        if not ActivationToken.query.filter_by(token=token).first():
            return token

def generate_password_reset_token():
    """Generate a unique password reset token"""
    while True:
        token = secrets.token_urlsafe(32)
        if not PasswordResetToken.query.filter_by(token=token).first():
            return token

def generate_api_key_name():
    """Generate a unique 6-character alphanumeric key name"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(6))

def generate_api_key_value():
    """Generate a new API key value with 'tk-' prefix and 32 alphanumeric characters"""
    return "tk-" + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

def create_default_api_key(user_id):
    """Create a default 'test_key' API key for newly activated users"""
    key_name = "test_key"
    key_value = generate_api_key_value()
    
    api_key = APIKey(
        user_id=user_id,
        key_name=key_name,
        key_value=key_value,
        state='enabled'
    )
    
    db.session.add(api_key)
    db.session.commit()
    return api_key
