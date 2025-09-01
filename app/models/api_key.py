"""
API Key Model

This module contains the APIKey model for managing user API keys.
"""

from datetime import datetime
from .database import db
from .utils import generate_api_key, generate_api_key_value

class APIKey(db.Model):
    """API Key model for user authentication and access control"""
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
    
    # Relationships
    proxy_logs = db.relationship("ProxyLog", back_populates="api_key", cascade="all, delete-orphan")
    
    def is_enabled(self):
        """Check if API key is enabled"""
        return self.state == 'enabled'
    
    def disable(self):
        """Disable the API key"""
        self.state = 'disabled'
        db.session.commit()
    
    def enable(self):
        """Enable the API key"""
        self.state = 'enabled'
        db.session.commit()
    
    def update_last_used(self):
        """Update the last used timestamp"""
        self.last_used = datetime.utcnow()
        db.session.commit()
    
    def refresh(self):
        """Generate a new key value"""
        self.key_value = generate_api_key()
        db.session.commit()
    
    def refresh_key_value(self):
        """Generate a new key_value while keeping the same key_name"""
        from .utils import generate_api_key_value
        self.key_value = generate_api_key_value()
        db.session.commit()
    
    @classmethod
    def create_default_api_key(cls, user_id):
        """Create 10 default API keys for a new user"""
        return cls.create_default_api_keys(user_id)
    
    @classmethod
    def create_default_api_keys(cls, user_id):
        """Create 10 default API keys for a new user"""
        api_keys = []
        
        for i in range(10):
            key_name = f"key_{i}"
            key_value = generate_api_key_value()
            
            api_key = cls(
                user_id=user_id,
                key_name=key_name,
                key_value=key_value,
                state='enabled'
            )
            
            db.session.add(api_key)
            api_keys.append(api_key)
        
        db.session.commit()
        return api_keys
