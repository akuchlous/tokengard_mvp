"""
OpenAI Analytics Model

Holds provider-specific analytics for OpenAI calls. Joined to proxy analytics
via `request_id`.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from .database import db


class ProviderAnalytics(db.Model):
    """Provider-specific analytics (generic)."""

    __tablename__ = 'provider_analytics'

    id = Column(Integer, primary_key=True)

    # Join key
    request_id = Column(String(36), nullable=False, index=True, unique=True)

    # Core identifiers
    completion_id = Column(String(128), nullable=True)
    model = Column(String(64), nullable=True)
    provider = Column(String(32), nullable=True)

    # Usage
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)

    # Raw response for audit/debug (JSON string)
    raw_response = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_openai_analytics_time', 'created_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'request_id': self.request_id,
            'completion_id': self.completion_id,
            'model': self.model,
            'provider': self.provider,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


