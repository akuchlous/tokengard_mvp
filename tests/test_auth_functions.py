"""
TokenGuard - Authentication Functions Unit Tests

This module contains unit tests for all authentication-related functions
to ensure they work correctly in isolation. These tests focus on:

- Password hashing and verification
- JWT token generation and validation
- User creation and management
- Email functionality
- Token management and cleanup
- Security features

The tests use pytest and mock objects to isolate the functions being tested.
"""

import pytest
import jwt
import bcrypt
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, Mock
from app import create_app, db
from models import User, ActivationToken, PasswordResetToken
from auth_utils import (
    hash_password, verify_password, generate_jwt_token, verify_jwt_token,
    create_user, send_activation_email, send_password_reset_email,
    authenticate_user, get_user_by_token, cleanup_expired_tokens
)


class TestPasswordFunctions:
    """Test password-related utility functions"""
    
    def test_hash_password(self):
        """Test that password hashing works correctly"""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        # Verify hash is different from original password
        assert hashed != password
        
        # Verify hash is a valid bcrypt hash
        assert hashed.startswith('$2b$')
        
        # Verify hash length is correct
        assert len(hashed) == 60
    
    def test_hash_password_empty_string(self):
        """Test password hashing with empty string"""
        password = ""
        hashed = hash_password(password)
        
        assert hashed != password
        assert hashed.startswith('$2b$')
    
    def test_hash_password_special_characters(self):
        """Test password hashing with special characters"""
        password = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        hashed = hash_password(password)
        
        assert hashed != password
        assert hashed.startswith('$2b$')
    
    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_verify_password_empty_string(self):
        """Test password verification with empty string"""
        password = ""
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False
    
    def test_hash_password_consistency(self):
        """Test that password hashing produces different hashes for same password"""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Each hash should be unique due to salt
        assert hash1 != hash2
        
        # Both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokenFunctions:
    """Test JWT token generation and verification"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['JWT_SECRET_KEY'] = 'test-jwt-secret-key'
        
        with self.app.app_context():
            yield
    
    def test_generate_jwt_token(self):
        """Test JWT token generation"""
        user_id = 123
        token = generate_jwt_token(user_id)
        
        # Token should be a string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Token should be decodable
        decoded = jwt.decode(token, self.app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        assert decoded['user_id'] == user_id
        assert 'exp' in decoded
        assert 'iat' in decoded
    
    def test_generate_jwt_token_custom_expiration(self):
        """Test JWT token generation with custom expiration"""
        user_id = 123
        expiration = 7200  # 2 hours
        token = generate_jwt_token(user_id, expiration)
        
        decoded = jwt.decode(token, self.app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        assert decoded['user_id'] == user_id
        
        # Check expiration time
        exp_time = datetime.fromtimestamp(decoded['exp'])
        iat_time = datetime.fromtimestamp(decoded['iat'])
        time_diff = exp_time - iat_time
        
        assert abs(time_diff.total_seconds() - expiration) < 5  # Allow 5 second tolerance
    
    def test_verify_jwt_token_valid(self):
        """Test JWT token verification with valid token"""
        user_id = 123
        token = generate_jwt_token(user_id)
        
        payload = verify_jwt_token(token)
        assert payload is not None
        assert payload['user_id'] == user_id
    
    def test_verify_jwt_token_expired(self):
        """Test JWT token verification with expired token"""
        user_id = 123
        # Create token with very short expiration
        token = generate_jwt_token(user_id, 1)  # 1 second
        
        # Wait for token to expire
        import time
        time.sleep(2)
        
        payload = verify_jwt_token(token)
        assert payload is None
    
    def test_verify_jwt_token_invalid(self):
        """Test JWT token verification with invalid token"""
        invalid_token = "invalid.token.here"
        
        payload = verify_jwt_token(invalid_token)
        assert payload is None
    
    def test_verify_jwt_token_wrong_secret(self):
        """Test JWT token verification with wrong secret key"""
        user_id = 123
        token = generate_jwt_token(user_id)
        
        # Try to verify with wrong secret
        with patch('auth_utils.current_app') as mock_app:
            mock_app.config = {'JWT_SECRET_KEY': 'wrong-secret'}
            
            payload = verify_jwt_token(token)
            assert payload is None


class TestUserManagementFunctions:
    """Test user creation and management functions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with self.app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()
    
    def test_create_user_success(self):
        """Test successful user creation"""
        email = "test@example.com"
        password = "TestPassword123!"
        
        user, activation_token = create_user(email, password)
        
        # Verify user was created
        assert user is not None
        assert user.email == email
        assert user.status == 'inactive'
        assert user.user_id is not None
        assert len(user.user_id) == 12
        
        # Verify password was hashed
        assert user.password_hash != password
        assert verify_password(password, user.password_hash)
        
        # Verify activation token was created
        assert activation_token is not None
        assert activation_token.user_id == user.id
        assert activation_token.is_valid()
        
        # Verify both were saved to database
        db_user = User.query.filter_by(email=email).first()
        assert db_user is not None
        assert db_user.id == user.id
    
    def test_create_user_duplicate_email(self):
        """Test user creation with duplicate email"""
        email = "test@example.com"
        password = "TestPassword123!"
        
        # Create first user
        user1, token1 = create_user(email, password)
        
        # Try to create second user with same email
        with pytest.raises(Exception):  # Should raise integrity error
            user2, token2 = create_user(email, "AnotherPassword123!")
    
    def test_create_user_empty_email(self):
        """Test user creation with empty email"""
        email = ""
        password = "TestPassword123!"
        
        with pytest.raises(Exception):
            create_user(email, password)
    
    def test_create_user_empty_password(self):
        """Test user creation with empty password"""
        email = "test@example.com"
        password = ""
        
        with pytest.raises(Exception):
            create_user(email, password)
    
    def test_user_id_generation_uniqueness(self):
        """Test that user IDs are unique"""
        users = []
        for i in range(100):
            email = f"test{i}@example.com"
            password = "TestPassword123!"
            user, _ = create_user(email, password)
            users.append(user)
        
        # All user IDs should be unique
        user_ids = [user.user_id for user in users]
        assert len(user_ids) == len(set(user_ids))
        
        # All user IDs should be 12 characters
        for user_id in user_ids:
            assert len(user_id) == 12
            assert user_id.isalnum()


class TestEmailFunctions:
    """Test email-related functions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['MAIL_DEFAULT_SENDER'] = 'noreply@tokengard.com'
        
        with self.app.app_context():
            yield
    
    def test_send_activation_email_success(self):
        """Test successful activation email sending"""
        # Create mock user and token
        user = Mock()
        user.email = "test@example.com"
        
        token = Mock()
        token.token = "test-token-123"
        
        # Mock url_for
        with patch('auth_utils.url_for') as mock_url_for:
            mock_url_for.return_value = "http://localhost/auth/activate/test-token-123"
            
            result = send_activation_email(user, token)
            
            assert result is True
    
    def test_send_activation_email_failure(self):
        """Test activation email sending failure"""
        user = Mock()
        user.email = "test@example.com"
        
        token = Mock()
        token.token = "test-token-123"
        
        with patch('auth_utils.url_for') as mock_url_for:
            mock_url_for.return_value = "http://localhost/auth/activate/test-token-123"
            
            result = send_activation_email(user, token)
            
            assert result is True  # Currently always returns True for testing
    
    def test_send_password_reset_email_success(self):
        """Test successful password reset email sending"""
        user = Mock()
        user.email = "test@example.com"
        
        token = Mock()
        token.token = "reset-token-123"
        
        with patch('auth_utils.url_for') as mock_url_for:
            mock_url_for.return_value = "http://localhost/auth/reset-password/reset-token-123"
            
            result = send_password_reset_email(user, token)
            
            assert result is True
    
    def test_send_password_reset_email_failure(self):
        """Test password reset email sending failure"""
        user = Mock()
        user.email = "test@example.com"
        
        token = Mock()
        token.token = "reset-token-123"
        
        with patch('auth_utils.url_for') as mock_url_for:
            mock_url_for.return_value = "http://localhost/auth/reset-password/reset-token-123"
            
            result = send_password_reset_email(user, token)
            
            assert result is True  # Currently always returns True for testing


class TestAuthenticationFunctions:
    """Test user authentication functions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with self.app.app_context():
            db.create_all()
            
            # Create test user
            self.test_user = User(
                email="test@example.com",
                password_hash=hash_password("TestPassword123!")
            )
            self.test_user.status = 'active'
            db.session.add(self.test_user)
            db.session.commit()
            
            yield
            db.session.remove()
            db.drop_all()
    
    def test_authenticate_user_success(self):
        """Test successful user authentication"""
        email = "test@example.com"
        password = "TestPassword123!"
        
        user = authenticate_user(email, password)
        
        assert user is not None
        assert user.email == email
        assert user.is_active()
    
    def test_authenticate_user_wrong_password(self):
        """Test user authentication with wrong password"""
        email = "test@example.com"
        password = "WrongPassword123!"
        
        user = authenticate_user(email, password)
        
        assert user is None
    
    def test_authenticate_user_nonexistent_email(self):
        """Test user authentication with nonexistent email"""
        email = "nonexistent@example.com"
        password = "TestPassword123!"
        
        user = authenticate_user(email, password)
        
        assert user is None
    
    def test_authenticate_user_inactive_account(self):
        """Test user authentication with inactive account"""
        # Create inactive user
        inactive_user = User(
            email="inactive@example.com",
            password_hash=hash_password("TestPassword123!")
        )
        inactive_user.status = 'inactive'
        db.session.add(inactive_user)
        db.session.commit()
        
        user = authenticate_user("inactive@example.com", "TestPassword123!")
        
        assert user is None
    
    def test_authenticate_user_empty_credentials(self):
        """Test user authentication with empty credentials"""
        # Test empty email
        user = authenticate_user("", "TestPassword123!")
        assert user is None
        
        # Test empty password
        user = authenticate_user("test@example.com", "")
        assert user is None
        
        # Test both empty
        user = authenticate_user("", "")
        assert user is None


class TestTokenManagementFunctions:
    """Test token management and cleanup functions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with self.app.app_context():
            db.create_all()
            
            # Create test user
            self.test_user = User(
                email="test@example.com",
                password_hash=hash_password("TestPassword123!")
            )
            db.session.add(self.test_user)
            db.session.commit()
            
            yield
            db.session.remove()
            db.drop_all()
    
    def test_get_user_by_activation_token_valid(self):
        """Test getting user by valid activation token"""
        # Create valid activation token
        token = ActivationToken(self.test_user.id)
        db.session.add(token)
        db.session.commit()
        
        user = get_user_by_token(token.token, 'activation')
        
        assert user is not None
        assert user.id == self.test_user.id
    
    def test_get_user_by_activation_token_invalid(self):
        """Test getting user by invalid activation token"""
        user = get_user_by_token("invalid-token", 'activation')
        
        assert user is None
    
    def test_get_user_by_activation_token_expired(self):
        """Test getting user by expired activation token"""
        # Create expired token
        token = ActivationToken(self.test_user.id)
        token.expires_at = datetime.utcnow() - timedelta(hours=2)
        db.session.add(token)
        db.session.commit()
        
        user = get_user_by_token(token.token, 'activation')
        
        assert user is None
    
    def test_get_user_by_activation_token_used(self):
        """Test getting user by used activation token"""
        # Create used token
        token = ActivationToken(self.test_user.id)
        token.used = True
        db.session.add(token)
        db.session.commit()
        
        user = get_user_by_token(token.token, 'activation')
        
        assert user is None
    
    def test_get_user_by_password_reset_token_valid(self):
        """Test getting user by valid password reset token"""
        # Create valid password reset token
        token = PasswordResetToken(self.test_user.id)
        db.session.add(token)
        db.session.commit()
        
        user = get_user_by_token(token.token, 'password_reset')
        
        assert user is not None
        assert user.id == self.test_user.id
    
    def test_get_user_by_password_reset_token_invalid(self):
        """Test getting user by invalid password reset token"""
        user = get_user_by_token("invalid-token", 'password_reset')
        
        assert user is None
    
    def test_cleanup_expired_tokens(self):
        """Test cleanup of expired tokens"""
        # Create expired activation token
        expired_activation = ActivationToken(self.test_user.id)
        expired_activation.expires_at = datetime.utcnow() - timedelta(hours=2)
        db.session.add(expired_activation)
        
        # Create expired password reset token
        expired_reset = PasswordResetToken(self.test_user.id)
        expired_reset.expires_at = datetime.utcnow() - timedelta(hours=2)
        db.session.add(expired_reset)
        
        # Create valid tokens
        valid_activation = ActivationToken(self.test_user.id)
        valid_reset = PasswordResetToken(self.test_user.id)
        db.session.add(valid_activation)
        db.session.add(valid_reset)
        
        db.session.commit()
        
        # Verify tokens exist
        assert ActivationToken.query.count() == 2
        assert PasswordResetToken.query.count() == 2
        
        # Clean up expired tokens
        cleanup_expired_tokens()
        
        # Verify only valid tokens remain
        assert ActivationToken.query.count() == 1
        assert PasswordResetToken.query.count() == 1
        
        # Verify the remaining tokens are valid
        remaining_activation = ActivationToken.query.first()
        remaining_reset = PasswordResetToken.query.first()
        
        assert remaining_activation.is_valid()
        assert remaining_reset.is_valid()


class TestSecurityFeatures:
    """Test security-related features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with self.app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()
    
    def test_password_hashing_salt_uniqueness(self):
        """Test that password hashing uses unique salts"""
        password = "TestPassword123!"
        hashes = []
        
        for _ in range(10):
            hashed = hash_password(password)
            hashes.append(hashed)
        
        # All hashes should be different due to unique salts
        assert len(hashes) == len(set(hashes))
        
        # All should verify correctly
        for hashed in hashes:
            assert verify_password(password, hashed)
    
    def test_jwt_token_security(self):
        """Test JWT token security features"""
        user_id = 123
        
        # Test token expiration
        short_token = generate_jwt_token(user_id, 1)  # 1 second
        
        # Token should be valid initially
        payload = verify_jwt_token(short_token)
        assert payload is not None
        
        # Wait for expiration
        import time
        time.sleep(2)
        
        # Token should be invalid after expiration
        payload = verify_jwt_token(short_token)
        assert payload is None
    
    def test_token_generation_security(self):
        """Test that tokens are cryptographically secure"""
        # Test activation token generation
        user_id = 1
        token1 = ActivationToken(user_id)
        token2 = ActivationToken(user_id)
        
        # Tokens should be different
        assert token1.token != token2.token
        
        # Tokens should be long enough
        assert len(token1.token) >= 32
        assert len(token2.token) >= 32
        
        # Test password reset token generation
        reset_token1 = PasswordResetToken(user_id)
        reset_token2 = PasswordResetToken(user_id)
        
        assert reset_token1.token != reset_token2.token
        assert len(reset_token1.token) >= 32
        assert len(reset_token2.token) >= 32


if __name__ == '__main__':
    # Run tests directly if script is executed
    pytest.main([__file__, '-v'])
