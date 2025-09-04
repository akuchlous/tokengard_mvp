"""
Proxy Log Model

FLOW OVERVIEW
- Persists proxy requests and responses with timings and metadata for analytics.
- create_log: helper to construct a new entry tied to a validated API key.
- Query helpers: by api key, by user, and aggregate stats in a date window.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from .database import db


class ProxyLog(db.Model):
    """Model for storing proxy endpoint API call logs."""
    
    __tablename__ = 'proxy_logs'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Foreign key to API key (nullable for invalid key attempts)
    api_key_id = Column(Integer, ForeignKey('api_keys.id'), nullable=True)
    
    # API key value (for quick reference without joins)
    api_key_value = Column(String(64), nullable=False, index=True)
    
    # Request details
    request_body = Column(Text, nullable=True)  # JSON string of request body
    request_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Response details
    response_status = Column(String(20), nullable=False)  # 'key_pass' or 'key_error'
    response_body = Column(Text, nullable=True)  # Response content
    response_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Request metadata
    client_ip = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(36), nullable=True)  # UUID for request tracking
    
    # Performance metrics
    processing_time_ms = Column(Integer, nullable=True)  # Processing time in milliseconds
    
    # Relationships
    api_key = relationship("APIKey", back_populates="proxy_logs")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_proxy_logs_api_key_timestamp', 'api_key_value', 'request_timestamp'),
        Index('idx_proxy_logs_timestamp', 'request_timestamp'),
        Index('idx_proxy_logs_status', 'response_status'),
    )
    
    def __repr__(self):
        return f'<ProxyLog {self.id}: {self.api_key_value} at {self.request_timestamp}>'
    
    def to_dict(self):
        """Convert log entry to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'api_key_value': self.api_key_value,
            'request_body': self.request_body,
            'request_timestamp': self.request_timestamp.isoformat() if self.request_timestamp else None,
            'response_status': self.response_status,
            'response_body': self.response_body,
            'response_timestamp': self.response_timestamp.isoformat() if self.response_timestamp else None,
            'client_ip': self.client_ip,
            'user_agent': self.user_agent,
            'request_id': self.request_id,
            'processing_time_ms': self.processing_time_ms
        }
    
    @classmethod
    def create_log(cls, api_key, request_body, response_status, response_body, 
                   client_ip=None, user_agent=None, request_id=None, processing_time_ms=None):
        """Create a new proxy log entry."""
        log_entry = cls(
            api_key_id=api_key.id,
            api_key_value=api_key.key_value,
            request_body=request_body,
            response_status=response_status,
            response_body=response_body,
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            processing_time_ms=processing_time_ms
        )
        db.session.add(log_entry)
        return log_entry
    
    @classmethod
    def get_logs_by_api_key(cls, api_key_value, limit=100, offset=0, start_date=None, end_date=None):
        """Get logs for a specific API key with optional filtering."""
        query = cls.query.filter_by(api_key_value=api_key_value)
        
        if start_date:
            query = query.filter(cls.request_timestamp >= start_date)
        if end_date:
            query = query.filter(cls.request_timestamp <= end_date)
        
        return query.order_by(cls.request_timestamp.desc()).offset(offset).limit(limit).all()
    
    @classmethod
    def get_logs_by_user(cls, user_id, limit=100, offset=0, start_date=None, end_date=None):
        """Get logs for all API keys belonging to a user."""
        from .api_key import APIKey
        
        # Get all API keys for the user
        api_keys = APIKey.query.filter_by(user_id=user_id).all()
        api_key_values = [key.key_value for key in api_keys]
        
        if not api_key_values:
            return []
        
        query = cls.query.filter(cls.api_key_value.in_(api_key_values))
        
        if start_date:
            query = query.filter(cls.request_timestamp >= start_date)
        if end_date:
            query = query.filter(cls.request_timestamp <= end_date)
        
        return query.order_by(cls.request_timestamp.desc()).offset(offset).limit(limit).all()
    
    @classmethod
    def get_log_stats_by_user(cls, user_id, days=30):
        """Get statistics for a user's API key usage."""
        from .api_key import APIKey
        from datetime import datetime, timedelta
        
        # Get all API keys for the user
        api_keys = APIKey.query.filter_by(user_id=user_id).all()
        api_key_values = [key.key_value for key in api_keys]
        
        if not api_key_values:
            return {
                'total_calls': 0,
                'successful_calls': 0,
                'failed_calls': 0,
                'unique_keys_used': 0,
                'avg_processing_time': 0
            }
        
        # Date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get logs in date range
        logs = cls.query.filter(
            cls.api_key_value.in_(api_key_values),
            cls.request_timestamp >= start_date,
            cls.request_timestamp <= end_date
        ).all()
        
        total_calls = len(logs)
        successful_calls = len([log for log in logs if log.response_status == 'key_pass'])
        failed_calls = total_calls - successful_calls
        unique_keys_used = len(set(log.api_key_value for log in logs))
        
        # Calculate average processing time
        processing_times = [log.processing_time_ms for log in logs if log.processing_time_ms is not None]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        return {
            'total_calls': total_calls,
            'successful_calls': successful_calls,
            'failed_calls': failed_calls,
            'unique_keys_used': unique_keys_used,
            'avg_processing_time': round(avg_processing_time, 2)
        }
