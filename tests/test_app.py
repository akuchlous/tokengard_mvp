import pytest
from app import create_app

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app({
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
    })
    return app

@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()

def test_home_page(client):
    """Test that the home page loads successfully"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'TokenGuard' in response.data
    assert b'Secure authentication system' in response.data

def test_health_endpoint(client):
    """Test the health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'

def test_home_page_content(client):
    """Test that the home page contains expected content"""
    response = client.get('/')
    # Check for key elements
    assert b'TokenGuard' in response.data
    assert b'Sign In' in response.data
    assert b'Sign Up' in response.data
    assert b'hero-section' in response.data

def test_404_error(client):
    """Test that non-existent routes return 404"""
    response = client.get('/nonexistent')
    assert response.status_code == 404

def test_home_page_structure(client):
    """Test that the home page has proper HTML structure"""
    response = client.get('/')
    # Check for HTML structure
    assert b'<!DOCTYPE html>' in response.data
    assert b'<html' in response.data
    assert b'<head>' in response.data
    assert b'<body' in response.data  # Changed from <body> to <body to handle class attribute
    assert b'</html>' in response.data
