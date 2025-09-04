"""
Banned Keywords Model

FLOW OVERVIEW
- Store per-user banned keywords with uniqueness enforced per (user_id, keyword).
- get_user_keywords(user_id): list keywords for UI and checks.
- add_keyword/remove_keyword: mutate user list, with duplicate protection.
- check_banned(user_id, text): scan lowercase text for banned keywords.
- populate_default_keywords(user_id): seed defaults for new users.
"""

from datetime import datetime
from ..models.database import db


class BannedKeyword(db.Model):
    """Model for storing user-specific banned keywords."""
    
    __tablename__ = 'banned_keywords'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    keyword = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('banned_keywords', lazy=True))
    
    # Unique constraint to prevent duplicate keywords per user
    __table_args__ = (db.UniqueConstraint('user_id', 'keyword', name='unique_user_keyword'),)
    
    def __repr__(self):
        return f'<BannedKeyword {self.keyword} for user {self.user_id}>'
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'keyword': self.keyword,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_user_keywords(cls, user_id):
        """Get all banned keywords for a user."""
        return cls.query.filter_by(user_id=user_id).order_by(cls.keyword).all()
    
    @classmethod
    def add_keyword(cls, user_id, keyword):
        """Add a banned keyword for a user."""
        # Check if keyword already exists
        existing = cls.query.filter_by(user_id=user_id, keyword=keyword.lower().strip()).first()
        if existing:
            return None, "Keyword already exists"
        
        banned_keyword = cls(
            user_id=user_id,
            keyword=keyword.lower().strip()
        )
        db.session.add(banned_keyword)
        db.session.commit()
        return banned_keyword, None
    
    @classmethod
    def remove_keyword(cls, user_id, keyword_id):
        """Remove a banned keyword for a user."""
        banned_keyword = cls.query.filter_by(id=keyword_id, user_id=user_id).first()
        if not banned_keyword:
            return False, "Keyword not found"
        
        db.session.delete(banned_keyword)
        db.session.commit()
        return True, None
    
    @classmethod
    def check_banned(cls, user_id, text):
        """Check if text contains any banned keywords for the user."""
        if not text:
            return False, None
        
        text_lower = text.lower()
        banned_keywords = cls.query.filter_by(user_id=user_id).all()
        
        for banned_keyword in banned_keywords:
            if banned_keyword.keyword in text_lower:
                return True, banned_keyword.keyword
        
        return False, None
    
    @classmethod
    def populate_default_keywords(cls, user_id):
        """Populate default banned keywords for a new user."""
        default_keywords = [
            'spam', 'scam', 'fraud', 'hack', 'virus', 'malware', 'phishing',
            'illegal', 'stolen', 'fake', 'counterfeit', 'porn', 'adult',
            'gambling', 'casino', 'lottery', 'drugs', 'weapon', 'violence',
            'hate', 'racist'
        ]
        
        added_count = 0
        for keyword in default_keywords:
            banned_keyword, error = cls.add_keyword(user_id, keyword)
            if banned_keyword:
                added_count += 1
        
        return added_count
