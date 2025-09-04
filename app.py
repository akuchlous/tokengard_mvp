#!/usr/bin/env python3
"""
TokenGuard application entry point.

This module selects configuration based on environment variables, creates the
Flask application via `create_app`, and eagerly initializes an in-memory
database for testing modes. When executed directly, it runs the development
server. In production, a WSGI server should import `app` from this module.

Environment variables of interest:
- FLASK_ENV: if set to 'testing', enables in-memory DB and testing flags.
- DATABASE_URL: if set to 'sqlite:///:memory:' forces in-memory DB init.
- SECRET_KEY, JWT_SECRET_KEY, mail settings: consumed by `create_app`.
"""

import os
from app import create_app
from app.models import db

# Create app instance
if os.getenv('FLASK_ENV') == 'testing':
    # Use test configuration for testing environment
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': os.getenv('DATABASE_URL', 'sqlite:///:memory:'),
        'SECRET_KEY': os.getenv('SECRET_KEY', 'test-secret-key'),
        'JWT_SECRET_KEY': os.getenv('JWT_SECRET_KEY', 'test-jwt-secret-key'),
        'MAIL_SERVER': os.getenv('MAIL_SERVER', 'localhost'),
        'MAIL_PORT': int(os.getenv('MAIL_PORT', 587)),
        'MAIL_USE_TLS': os.getenv('MAIL_USE_TLS', 'False').lower() == 'true',
        'MAIL_USE_SSL': os.getenv('MAIL_USE_SSL', 'False').lower() == 'true',
        'MAIL_USERNAME': os.getenv('MAIL_USERNAME', 'test@example.com'),
        'MAIL_PASSWORD': os.getenv('MAIL_PASSWORD', 'test-password'),
        'MAIL_DEFAULT_SENDER': os.getenv('MAIL_DEFAULT_SENDER', 'test@example.com'),
        'WTF_CSRF_ENABLED': False
    }
    app = create_app(test_config)
else:
    app = create_app()

# Database initialization - will be done on first request
print("🚀 Starting TokenGuard server...")
if os.getenv('FLASK_ENV') == 'testing':
    print("🧪 Running in TESTING mode with in-memory database")
    with app.app_context():
        db.create_all()
        print("📊 Test database initialized")
elif os.getenv('DATABASE_URL') == 'sqlite:///:memory:':
    print("💾 Running with in-memory database")
    with app.app_context():
        db.create_all()
        print("📊 In-memory database initialized")
else:
    print("📊 Database will be initialized on first request")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
