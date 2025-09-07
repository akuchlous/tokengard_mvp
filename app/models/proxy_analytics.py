"""
Proxy Analytics Model

Captures per-request proxy analytics. Joined with provider analytics via
`request_id`.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index
from .database import db


class ProxyAnalytics(db.Model):
    """Proxy-level analytics for each proxied request."""

    __tablename__ = 'proxy_analytics'

    id = Column(Integer, primary_key=True)

    # Join key used across analytics tables
    request_id = Column(String(36), nullable=False, index=True, unique=True)

    # Foreign/user linkage
    api_key_id = Column(Integer, ForeignKey('api_keys.id'), nullable=True)
    api_key_value = Column(String(64), nullable=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)

    # Request/response characteristics
    model = Column(String(64), nullable=True)
    temperature = Column(Float, nullable=True)
    provider = Column(String(32), nullable=True)
    cache_hit = Column(Boolean, default=False)
    success = Column(Boolean, default=False)
    status_code = Column(Integer, nullable=True)
    error_code = Column(String(64), nullable=True)

    # Token/cost accounting
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    cost_input = Column(Float, nullable=True)
    cost_output = Column(Float, nullable=True)
    cost_total = Column(Float, nullable=True)

    # Timing/metadata
    processing_time_ms = Column(Integer, nullable=True)
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_proxy_analytics_user_time', 'user_id', 'created_at'),
        Index('idx_proxy_analytics_key_time', 'api_key_value', 'created_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'request_id': self.request_id,
            'api_key_id': self.api_key_id,
            'api_key_value': self.api_key_value,
            'user_id': self.user_id,
            'model': self.model,
            'provider': self.provider,
            'temperature': self.temperature,
            'cache_hit': self.cache_hit,
            'success': self.success,
            'status_code': self.status_code,
            'error_code': self.error_code,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'total_tokens': self.total_tokens,
            'cost_input': self.cost_input,
            'cost_output': self.cost_output,
            'cost_total': self.cost_total,
            'processing_time_ms': self.processing_time_ms,
            'client_ip': self.client_ip,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


