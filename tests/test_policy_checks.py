#!/usr/bin/env python3
"""
Unit tests for the policy checks module
"""

import pytest
from app.utils.policy_checks import PolicyChecker, PolicyCheckResult, policy_checker
from app.models import User, APIKey, BannedKeyword, db
from app.utils.auth_utils import hash_password


class TestPolicyCheckResult:
    """Test the PolicyCheckResult class."""
    
    def test_policy_check_result_creation(self):
        """Test creating a PolicyCheckResult."""
        result = PolicyCheckResult(True, "TEST_CODE", "Test message", {"key": "value"})
        
        assert result.passed is True
        assert result.error_code == "TEST_CODE"
        assert result.message == "Test message"
        assert result.details == {"key": "value"}
    
    def test_policy_check_result_to_dict(self):
        """Test converting PolicyCheckResult to dictionary."""
        result = PolicyCheckResult(False, "ERROR_CODE", "Error message", {"detail": "info"})
        result_dict = result.to_dict()
        
        expected = {
            'passed': False,
            'error_code': 'ERROR_CODE',
            'message': 'Error message',
            'details': {'detail': 'info'}
        }
        assert result_dict == expected


class TestPolicyChecker:
    """Test the PolicyChecker class."""
    
    @pytest.fixture
    def test_user_with_key(self, app, db_session):
        """Create a test user with API key."""
        user = User(
            email='policy_test@example.com',
            password_hash=hash_password('password123')
        )
        user.status = 'active'
        db_session.add(user)
        db_session.commit()
        
        # Create API key
        api_key = APIKey(
            user_id=user.id,
            key_name='test_key',
            key_value='tk-test-key-123456789012345678901234567890',
            state='enabled'
        )
        db_session.add(api_key)
        db_session.commit()
        
        return user, api_key
    
    @pytest.fixture
    def test_user_with_banned_keywords(self, app, db_session):
        """Create a test user with banned keywords."""
        user = User(
            email='banned_test@example.com',
            password_hash=hash_password('password123')
        )
        user.status = 'active'
        db_session.add(user)
        db_session.commit()
        
        # Create banned keywords
        banned_keywords = [
            BannedKeyword(user_id=user.id, keyword='spam'),
            BannedKeyword(user_id=user.id, keyword='scam'),
            BannedKeyword(user_id=user.id, keyword='fraud')
        ]
        for keyword in banned_keywords:
            db_session.add(keyword)
        db_session.commit()
        
        return user, banned_keywords
    
    def test_validate_api_key_empty(self):
        """Test validating empty API key."""
        checker = PolicyChecker()
        result = checker.validate_api_key("")
        
        assert result.passed is False
        assert result.error_code == 'MISSING_API_KEY'
    
    def test_validate_api_key_too_short(self):
        """Test validating API key that's too short."""
        checker = PolicyChecker()
        result = checker.validate_api_key("short")
        
        assert result.passed is False
        assert result.error_code == 'INVALID_API_KEY_FORMAT'
    
    def test_validate_api_key_too_long(self):
        """Test validating API key that's too long."""
        checker = PolicyChecker()
        long_key = "a" * 201  # 201 characters
        result = checker.validate_api_key(long_key)
        
        assert result.passed is False
        assert result.error_code == 'INVALID_API_KEY_FORMAT'
    
    def test_validate_api_key_invalid_chars(self):
        """Test validating API key with invalid characters."""
        checker = PolicyChecker()
        result = checker.validate_api_key("tk-key-with-<script>")
        
        assert result.passed is False
        assert result.error_code == 'INVALID_API_KEY_CHARS'
    
    def test_validate_api_key_not_found(self, app, db_session):
        """Test validating API key that doesn't exist."""
        checker = PolicyChecker()
        result = checker.validate_api_key("tk-nonexistent-key-123456789012345678901234567890")
        
        assert result.passed is False
        assert result.error_code == 'API_KEY_NOT_FOUND'
    
    def test_validate_api_key_inactive(self, app, db_session, test_user_with_key):
        """Test validating inactive API key."""
        user, api_key = test_user_with_key
        api_key.state = 'disabled'
        db_session.commit()
        
        checker = PolicyChecker()
        result = checker.validate_api_key(api_key.key_value)
        
        assert result.passed is False
        assert result.error_code == 'API_KEY_INACTIVE'
    
    def test_validate_api_key_inactive_user(self, app, db_session, test_user_with_key):
        """Test validating API key for inactive user."""
        user, api_key = test_user_with_key
        user.status = 'inactive'
        db_session.commit()
        
        checker = PolicyChecker()
        result = checker.validate_api_key(api_key.key_value)
        
        assert result.passed is False
        assert result.error_code == 'USER_ACCOUNT_INACTIVE'
    
    def test_validate_api_key_success(self, app, db_session, test_user_with_key):
        """Test validating valid API key."""
        user, api_key = test_user_with_key
        
        checker = PolicyChecker()
        result = checker.validate_api_key(api_key.key_value)
        
        assert result.passed is True
        assert result.details['api_key_record'] == api_key
        assert result.details['user'] == user
        assert result.details['key_name'] == 'test_key'
    
    def test_check_banned_keywords_no_text(self):
        """Test checking banned keywords with no text."""
        checker = PolicyChecker()
        result = checker.check_banned_keywords(1, "")
        
        assert result.passed is True
    
    def test_check_banned_keywords_clean_text(self, app, db_session, test_user_with_banned_keywords):
        """Test checking banned keywords with clean text."""
        user, banned_keywords = test_user_with_banned_keywords
        
        checker = PolicyChecker()
        result = checker.check_banned_keywords(user.id, "This is clean text without any banned words")
        
        assert result.passed is True
    
    def test_check_banned_keywords_banned_text(self, app, db_session, test_user_with_banned_keywords):
        """Test checking banned keywords with banned text."""
        user, banned_keywords = test_user_with_banned_keywords
        
        checker = PolicyChecker()
        result = checker.check_banned_keywords(user.id, "This text contains spam content")
        
        assert result.passed is False
        assert result.error_code == 'BANNED_KEYWORD'
        assert result.details['banned_keyword'] == 'spam'
    
    def test_check_external_security_no_text(self):
        """Test external security check with no text."""
        checker = PolicyChecker()
        result = checker.check_external_security("")
        
        assert result.passed is True
    
    def test_check_external_security_text_too_long(self):
        """Test external security check with text that's too long."""
        checker = PolicyChecker()
        long_text = "a" * 10001  # 10001 characters
        result = checker.check_external_security(long_text)
        
        assert result.passed is False
        assert result.error_code == 'TEXT_TOO_LONG'
    
    def test_check_external_security_repetitive_text(self):
        """Test external security check with repetitive text."""
        checker = PolicyChecker()
        repetitive_text = "spam spam spam spam spam spam spam spam spam spam spam"
        result = checker.check_external_security(repetitive_text)
        
        assert result.passed is False
        assert result.error_code == 'EXTERNAL_API_BLOCKED'
    
    def test_check_external_security_clean_text(self):
        """Test external security check with clean text."""
        checker = PolicyChecker()
        clean_text = "This is a normal text that should pass all checks"
        result = checker.check_external_security(clean_text)
        
        assert result.passed is True
        assert 'external_check' in result.details
    
    def test_run_all_checks_success(self, app, db_session, test_user_with_key):
        """Test running all checks successfully."""
        user, api_key = test_user_with_key
        
        checker = PolicyChecker()
        result = checker.run_all_checks(api_key.key_value, "Clean text for testing")
        
        assert result.passed is True
        assert result.message == 'All policy checks passed.'
        assert 'api_key_record' in result.details
        assert 'user' in result.details
        assert 'text_length' in result.details
    
    def test_run_all_checks_api_key_failure(self, app, db_session):
        """Test running all checks with invalid API key."""
        with app.app_context():
            checker = PolicyChecker()
            result = checker.run_all_checks("invalid-key", "Some text")
            
            assert result.passed is False
            assert result.error_code == 'API_KEY_NOT_FOUND'
    
    def test_run_all_checks_banned_keyword_failure(self, app, db_session, test_user_with_banned_keywords):
        """Test running all checks with banned keyword."""
        user, banned_keywords = test_user_with_banned_keywords
        
        # Create a valid API key for the user
        api_key = APIKey(
            user_id=user.id,
            key_name='test_key',
            key_value='tk-test-key-123456789012345678901234567890',
            state='enabled'
        )
        db_session.add(api_key)
        db_session.commit()
        
        checker = PolicyChecker()
        result = checker.run_all_checks(api_key.key_value, "This text contains spam")
        
        assert result.passed is False
        assert result.error_code == 'BANNED_KEYWORD'


class TestGlobalPolicyChecker:
    """Test the global policy checker instance."""
    
    def test_global_instance_exists(self):
        """Test that the global policy checker instance exists."""
        assert policy_checker is not None
        assert isinstance(policy_checker, PolicyChecker)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
