"""
Test configuration and shared fixtures for TokenGuard tests.

This file contains:
- Centralized test configuration
- Shared fixtures used across multiple test files
- Common test utilities
"""

import pytest
import subprocess
import time
import signal
import os
from app import create_app, db
from models import User, ActivationToken, PasswordResetToken, APIKey
from auth_utils import hash_password
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


@pytest.fixture(scope="session")
def flask_app_server():
    """Start Flask app server for e2e tests and clean up afterward."""
    # Start Flask app in background
    env = os.environ.copy()
    env['FLASK_ENV'] = 'testing'
    env['DATABASE_URL'] = 'sqlite:///:memory:'
    env['TESTING'] = 'True'
    env['SECRET_KEY'] = 'test-secret-key'
    env['JWT_SECRET_KEY'] = 'test-jwt-secret-key'
    env['MAIL_SERVER'] = 'localhost'
    env['MAIL_PORT'] = '587'
    env['MAIL_USE_TLS'] = 'False'
    env['MAIL_USE_SSL'] = 'False'
    env['MAIL_USERNAME'] = 'test@example.com'
    env['MAIL_PASSWORD'] = 'test-password'
    env['MAIL_DEFAULT_SENDER'] = 'test@example.com'
    env['WTF_CSRF_ENABLED'] = 'False'
    
    # Start the Flask app process
    process = subprocess.Popen(
        ['python', 'app.py'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for app to start and verify it's responding
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            time.sleep(1)  # Wait a bit
            response = requests.get('http://localhost:5000/health', timeout=5)
            if response.status_code == 200:
                print(f"✅ Flask server started successfully on attempt {attempt + 1}")
                break
        except Exception as e:
            if attempt == max_attempts - 1:
                print(f"❌ Failed to start Flask server after {max_attempts} attempts")
                process.terminate()
                process.wait(timeout=5)
                raise RuntimeError(f"Flask server failed to start: {e}")
            print(f"⏳ Waiting for Flask server to start... (attempt {attempt + 1}/{max_attempts})")
    
    yield process
    
    # Clean up: terminate the Flask app process
    print("🧹 Cleaning up Flask server...")
    try:
        process.terminate()
        process.wait(timeout=10)
        print("✅ Flask server terminated gracefully")
    except subprocess.TimeoutExpired:
        print("⚠️  Flask server didn't terminate gracefully, forcing kill...")
        process.kill()
        process.wait()
        print("✅ Flask server killed")


@pytest.fixture(scope="session")
def selenium_server(flask_app_server):
    """Start Flask server and wait for it to be ready for Selenium tests."""
    # The flask_app_server fixture already starts the server and verifies it's ready
    # Just do a final health check to ensure it's still responding
    try:
        response = requests.get('http://localhost:5000/health', timeout=5)
        assert response.status_code == 200
        print("✅ Flask server confirmed ready for Selenium tests")
    except Exception as e:
        raise RuntimeError(f"Flask server not ready for Selenium tests: {e}")
    
    yield flask_app_server


@pytest.fixture
def browser_driver(selenium_server):
    """Provide a WebDriver instance for browser tests with automatic cleanup."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    
    # Set up Chrome driver options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    
    # Create driver
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(5)  # Wait up to 5 seconds for elements
    
    print("🌐 WebDriver created for browser test")
    
    yield driver
    
    # Clean up
    try:
        driver.quit()
        print("✅ WebDriver cleaned up")
    except Exception as e:
        print(f"⚠️  Warning: Error cleaning up WebDriver: {e}")


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
    from models import generate_api_key_value
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
    from models import generate_api_key_value
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
