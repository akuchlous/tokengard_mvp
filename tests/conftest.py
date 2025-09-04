"""
Test configuration and shared fixtures for TokenGuard tests.

This file contains:
- Centralized test configuration
- Shared fixtures used across multiple test files
- Common test utilities
"""

import pytest
import os
from app import create_app
from app.models import db, User, ActivationToken, PasswordResetToken, APIKey
from app.utils.auth_utils import hash_password
import requests


# Centralized test configuration
TEST_CONFIG = {
    'TESTING': True,
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'SECRET_KEY': 'test-secret-key',
    'JWT_SECRET_KEY': 'test-jwt-secret-key',
    'MAIL_SERVER': 'localhost',
    'MAIL_PORT': 587,
    'MAIL_USE_TLS': False,
    'MAIL_USE_SSL': False,
    'MAIL_USERNAME': 'test@example.com',
    'MAIL_PASSWORD': 'test-password',
    'MAIL_DEFAULT_SENDER': 'test@example.com',
    'WTF_CSRF_ENABLED': False
}


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app(TEST_CONFIG)
    return app


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Create an application context for database operations."""
    with app.app_context():
        yield


@pytest.fixture
def db_session(app_context):
    """Create a database session and clean up after tests."""
    db.create_all()
    yield db.session
    db.session.remove()
    db.drop_all()


# Removed Selenium browser_driver fixture to eliminate Selenium dependency in tests.


@pytest.fixture
def test_user(db_session):
    """Create a test user for testing."""
    user = User(
        email='test@example.com',
        password_hash=hash_password('TestPass123!')
    )
    user.status = 'active'
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_user_inactive(db_session):
    """Create an inactive test user for testing."""
    user = User(
        email='inactive@example.com',
        password_hash=hash_password('TestPass123!')
    )
    user.status = 'inactive'
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def activation_token(db_session, test_user):
    """Create an activation token for testing."""
    token = ActivationToken(test_user.id)
    db_session.add(token)
    db_session.commit()
    return token


@pytest.fixture
def password_reset_token(db_session, test_user):
    """Create a password reset token for testing."""
    token = PasswordResetToken(test_user.id)
    db_session.add(token)
    db_session.commit()
    return token


@pytest.fixture
def expired_activation_token(db_session, test_user):
    """Create an expired activation token for testing."""
    from datetime import datetime, timedelta
    token = ActivationToken(test_user.id)
    token.expires_at = datetime.utcnow() - timedelta(hours=2)
    db_session.add(token)
    db_session.commit()
    return token


@pytest.fixture
def expired_password_reset_token(db_session, test_user):
    """Create an expired password reset token for testing."""
    from datetime import datetime, timedelta
    token = PasswordResetToken(test_user.id)
    token.expires_at = datetime.utcnow() - timedelta(hours=2)
    db_session.add(token)
    db_session.commit()
    return token


@pytest.fixture
def test_api_key(db_session, test_user):
    """Create a test API key for testing."""
    from app.models.utils import generate_api_key_value
    api_key = APIKey(
        user_id=test_user.id,
        key_name='test12',
        key_value=generate_api_key_value(),
        state='enabled'
    )
    db_session.add(api_key)
    db_session.commit()
    return api_key


@pytest.fixture
def test_api_key_disabled(db_session, test_user):
    """Create a disabled test API key for testing."""
    from app.models.utils import generate_api_key_value
    api_key = APIKey(
        user_id=test_user.id,
        key_name='test34',
        key_value=generate_api_key_value(),
        state='disabled'
    )
    db_session.add(api_key)
    db_session.commit()
    return api_key


@pytest.fixture
def used_activation_token(db_session, test_user):
    """Create a used activation token for testing."""
    token = ActivationToken(test_user.id)
    token.used = True
    db_session.add(token)
    db_session.commit()
    return token


@pytest.fixture
def used_password_reset_token(db_session, test_user):
    """Create a used password reset token for testing."""
    token = PasswordResetToken(test_user.id)
    token.used = True
    db_session.add(token)
    db_session.commit()
    return token
