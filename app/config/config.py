"""
Application Configuration

FLOW OVERVIEW
- Config.__init__
  • Reads FLASK_ENV to select which .env file to load (dev/prod). Testing bypasses file load.
- Properties expose configuration values, defaulting to sensible development-safe defaults.
"""

import os
from dotenv import load_dotenv

class Config:
    """Base configuration class"""
    
    def __init__(self):
        # Load environment variables based on FLASK_ENV
        env_file = os.getenv('FLASK_ENV', 'development')
        if env_file == 'testing':
            # For testing, don't load config files, use environment variables directly
            pass
        elif env_file == 'production':
            load_dotenv('config.prod.env')
        else:
            load_dotenv('config.env')  # Default to development
    
    @property
    def SECRET_KEY(self):
        """Application secret key"""
        return os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        """Database connection URI"""
        return os.getenv('DATABASE_URL', 'sqlite:///:memory:')
    
    @property
    def SQLALCHEMY_TRACK_MODIFICATIONS(self):
        """SQLAlchemy track modifications setting"""
        return False
    
    @property
    def MAIL_SERVER(self):
        """Mail server hostname"""
        return os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    
    @property
    def MAIL_PORT(self):
        """Mail server port"""
        return int(os.getenv('MAIL_PORT', 587))
    
    @property
    def MAIL_USE_TLS(self):
        """Whether to use TLS for mail"""
        return os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    
    @property
    def MAIL_USE_SSL(self):
        """Whether to use SSL for mail"""
        return os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
    
    @property
    def MAIL_USERNAME(self):
        """Mail server username"""
        return os.getenv('MAIL_USERNAME')
    
    @property
    def MAIL_PASSWORD(self):
        """Mail server password"""
        return os.getenv('MAIL_PASSWORD')
    
    @property
    def MAIL_DEFAULT_SENDER(self):
        """Default sender email address"""
        return os.getenv('MAIL_DEFAULT_SENDER')
    
    @property
    def JWT_SECRET_KEY(self):
        """JWT secret key"""
        return os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    
    @property
    def JWT_ACCESS_TOKEN_EXPIRES(self):
        """JWT access token expiration time in seconds"""
        return int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    
    @property
    def JWT_REFRESH_TOKEN_EXPIRES(self):
        """JWT refresh token expiration time in seconds"""
        return int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 604800))
    
    @property
    def SESSION_COOKIE_SECURE(self):
        """Whether session cookies should be secure (HTTPS only)"""
        return False  # Set to True in production with HTTPS
    
    @property
    def SESSION_COOKIE_HTTPONLY(self):
        """Whether session cookies should be HTTP only"""
        return True
    
    @property
    def SESSION_COOKIE_SAMESITE(self):
        """Session cookie SameSite policy"""
        return 'Lax'
    
    @property
    def PERMANENT_SESSION_LIFETIME(self):
        """Session lifetime in seconds"""
        return 3600  # 1 hour
    
    @property
    def SESSION_COOKIE_DOMAIN(self):
        """Session cookie domain"""
        return None  # Allow cookies for localhost
