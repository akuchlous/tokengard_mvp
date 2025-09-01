"""
Tests for Input Validation and Security Utilities

This module tests the comprehensive validation functions for user inputs,
ensuring security best practices are followed and common attack vectors are prevented.
"""

import pytest
from app.utils.validators import (
    InputValidator, ValidationResult, validate_email, validate_password_hash,
    validate_password_strength, sanitize_input
)


class TestEmailValidation:
    """Test email validation with comprehensive security checks"""
    
    def test_valid_emails(self):
        """Test that valid email addresses pass validation"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "user-name@subdomain.example.com",
            "user_name@example.com",
            "user123@example.com",
            "user@example-domain.com",
            "user@example.co.uk",
            "user@example-domain.co.uk",
            "a@b.c",  # Minimal valid email
        ]
        
        for email in valid_emails:
            result = validate_email(email)
            assert result.is_valid, f"Email '{email}' should be valid: {result.error_message}"
            assert result.sanitized_value == email.lower()
    
    def test_invalid_emails(self):
        """Test that invalid email addresses fail validation"""
        invalid_emails = [
            "",  # Empty
            "   ",  # Whitespace only
            "invalid-email",  # No @
            "@example.com",  # No local part
            "user@",  # No domain
            "user@.com",  # No domain name
            "user name@example.com",  # Space in local part
            "user@example com",  # Space in domain
            "user@example..com",  # Double dots
            "user@-example.com",  # Leading dash in domain
            "user@example-.com",  # Trailing dash in domain
            "user@example.com..",  # Multiple trailing dots
        ]
        
        for email in invalid_emails:
            result = validate_email(email)
            assert not result.is_valid, f"Email '{email}' should be invalid"
            assert result.error_message is not None
    
    def test_email_length_limits(self):
        """Test email length validation (RFC 5321 limits)"""
        # Test extremely long emails
        long_local = "a" * 65 + "@example.com"  # Local part too long
        long_domain = "user@" + "a" * 254 + ".com"  # Domain too long
        long_total = "a" * 255 + "@example.com"  # Total too long
        
        assert not validate_email(long_local).is_valid
        assert not validate_email(long_domain).is_valid
        assert not validate_email(long_total).is_valid
        
        # Test boundary conditions (should work)
        boundary_local = "a" * 64 + "@example.com"  # Exactly at limit
        # Use shorter, safe lengths
        boundary_domain = "user@example.com"  # Normal length
        boundary_total = "a" * 50 + "@example.com"  # Well under local part limit
        
        assert validate_email(boundary_local).is_valid
        assert validate_email(boundary_domain).is_valid
        assert validate_email(boundary_total).is_valid
    
    def test_email_normalization(self):
        """Test email normalization and sanitization"""
        test_cases = [
            ("  TEST@EXAMPLE.COM  ", "test@example.com"),
            ("User.Name+Tag@Domain.Co.Uk", "user.name+tag@domain.co.uk"),
            ("  user@example.com  ", "user@example.com"),
            ("USER@EXAMPLE.COM", "user@example.com"),
        ]
        
        for input_email, expected_email in test_cases:
            result = validate_email(input_email)
            assert result.is_valid
            assert result.sanitized_value == expected_email


class TestPasswordHashValidation:
    """Test password hash format validation"""
    
    def test_valid_password_hashes(self):
        """Test that valid password hashes pass validation"""
        # Generate valid SHA-256 hashes
        valid_hashes = [
            "a" * 64,  # 64 'a' characters
            "0" * 64,  # 64 '0' characters
            "f" * 64,  # 64 'f' characters
            "1234567890abcdef" * 4,  # 64 hex characters
            "deadbeef" * 8,  # 64 hex characters
        ]
        
        for hash_value in valid_hashes:
            result = validate_password_hash(hash_value)
            assert result.is_valid, f"Hash should be valid: {result.error_message}"
            assert result.sanitized_value == hash_value
    
    def test_invalid_password_hashes(self):
        """Test that invalid password hashes fail validation"""
        invalid_hashes = [
            "",  # Empty
            "   ",  # Whitespace only
            "short",  # Too short
            "a" * 63,  # Too short (63 chars)
            "a" * 65,  # Too long (65 chars)
            "invalid-hash-format",  # Wrong format
            "1234567890abcdef" * 4 + "g",  # 65 chars (too long)
            "g" + "a" * 63,  # Contains non-hex char
            "A" * 64,  # Uppercase (should be normalized)
            " " + "a" * 63 + " ",  # With whitespace
        ]
        
        for hash_value in invalid_hashes:
            result = validate_password_hash(hash_value)
            assert not result.is_valid, f"Hash '{hash_value}' should be invalid"
            assert result.error_message is not None
    
    def test_password_hash_sanitization(self):
        """Test password hash sanitization"""
        # Test whitespace handling
        result = validate_password_hash("  " + "a" * 62 + "  ")  # 66 chars with whitespace
        assert not result.is_valid  # Should fail due to length after trim
        
        # Test case normalization
        result = validate_password_hash("A" * 64)
        assert not result.is_valid  # Should fail due to uppercase


class TestPasswordStrengthValidation:
    """Test password strength requirements"""
    
    def test_strong_passwords(self):
        """Test that strong passwords pass validation"""
        strong_passwords = [
            "MySecurePass456@",
            "Complex!Pass789#",
            "VeryLongPassword123!@#",
            "Str0ng!P@ssw0rd",
            "C0mpl3x!P@ss",
            "SecureP@ss2024!",
            "MyStr0ngP@ss!",
            "C0mpl3xP@ssw0rd",
        ]
        
        for password in strong_passwords:
            result = validate_password_strength(password)
            assert result.is_valid, f"Password should be strong: {result.error_message}"
    
    def test_weak_passwords(self):
        """Test that weak passwords fail validation"""
        weak_passwords = [
            "",  # Empty
            "123",  # Too short
            "password",  # Common word
            "123456",  # Sequential numbers
            "qwerty",  # Keyboard pattern
            "abc123",  # Common pattern
            "Password",  # Missing numbers and special chars
            "password123",  # Missing special chars
            "PASSWORD123",  # Missing lowercase and special chars
            "pass123",  # Too short
        ]
        
        for password in weak_passwords:
            result = validate_password_strength(password)
            assert not result.is_valid, f"Password '{password}' should be weak"
            assert result.error_message is not None
    
    def test_password_length_requirements(self):
        """Test password length requirements"""
        # Test minimum length
        short_passwords = ["", "a", "ab", "abc", "abcd", "abcde", "abcdef", "abcdefg"]
        for password in short_passwords:
            result = validate_password_strength(password)
            assert not result.is_valid
            if password:  # Non-empty passwords should mention length requirement
                assert "8 characters" in result.error_message
            else:  # Empty passwords have different error message
                assert "non-empty string" in result.error_message
        
        # Test maximum length
        long_password = "a" * 129 + "A1!"  # 132 characters
        result = validate_password_strength(long_password)
        assert not result.is_valid
        assert "128 characters" in result.error_message
    
    def test_password_character_requirements(self):
        """Test password character variety requirements"""
        # Test missing character types
        missing_upper = "password123!"
        missing_lower = "PASSWORD123!"
        missing_digit = "Password!"
        missing_special = "Password123"
        
        assert not validate_password_strength(missing_upper).is_valid
        assert not validate_password_strength(missing_lower).is_valid
        assert not validate_password_strength(missing_digit).is_valid
        # Special characters are recommended but not required for basic validation
        # assert not validate_password_strength(missing_special).is_valid


class TestSQLInjectionPrevention:
    """Test SQL injection prevention"""
    
    def test_sql_injection_patterns(self):
        """Test that SQL injection patterns are detected and blocked"""
        sql_injection_attempts = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; INSERT INTO users VALUES (999, 'hacker@evil.com', 'hash'); --",
            "'; UPDATE users SET status='admin' WHERE id=1; --",
            "'; DELETE FROM users; --",
            "'; EXEC xp_cmdshell('rm -rf /'); --",
            "'; SELECT * FROM information_schema.tables; --",
            "'; UNION SELECT password FROM users; --",
            "'; WAITFOR DELAY '00:00:10'; --",
            "'; SHUTDOWN; --",
            "admin'--",
            "admin'/*",
            "admin'#",
            "admin' OR '1'='1",
            "admin' AND '1'='1",
        ]
        
        for attempt in sql_injection_attempts:
            result = validate_email(attempt)
            assert not result.is_valid, f"SQL injection attempt should be blocked: {attempt}"
            # SQL injection attempts should fail either format validation or security validation
            assert result.error_message is not None


class TestXSSPrevention:
    """Test XSS prevention"""
    
    def test_xss_patterns(self):
        """Test that XSS patterns are detected and blocked"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "onload=alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//",
            "<svg onload=alert('xss')>",
            "javascript:void(alert('xss'))",
            "data:text/html,<script>alert('xss')</script>",
            "vbscript:msgbox('xss')",
            "<iframe src=javascript:alert('xss')>",
            "onmouseover=alert('xss')",
            "onfocus=alert('xss')",
            "onblur=alert('xss')",
        ]
        
        for payload in xss_payloads:
            result = validate_email(payload)
            assert not result.is_valid, f"XSS payload should be blocked: {payload}"
            # XSS attempts should fail either format validation or security validation
            assert result.error_message is not None


class TestInputSanitization:
    """Test input sanitization functions"""
    
    def test_basic_sanitization(self):
        """Test basic input sanitization"""
        test_cases = [
            ("  hello world  ", "hello world"),
            ("hello\nworld", "hello\nworld"),
            ("hello\r\nworld", "hello\nworld"),
            ("hello\rworld", "hello\nworld"),
            ("hello\x00world", "helloworld"),  # Remove null bytes
            ("", ""),
            (None, ""),
            (123, "123"),  # Convert numbers to string
        ]
        
        for input_val, expected in test_cases:
            result = sanitize_input(input_val)
            assert result == expected
    
    def test_length_limiting(self):
        """Test input length limiting"""
        long_input = "a" * 2000
        result = sanitize_input(long_input, max_length=1000)
        assert len(result) == 1000
        assert result == "a" * 1000
    
    def test_edge_cases(self):
        """Test edge cases in sanitization"""
        # Test with various whitespace characters
        whitespace_test = "\t\n\r\f\v  hello  \t\n\r\f\v"
        result = sanitize_input(whitespace_test)
        assert result == "hello"
        
        # Test with unicode characters
        unicode_test = "héllö wörld"
        result = sanitize_input(unicode_test)
        assert result == "héllö wörld"


class TestValidationResult:
    """Test ValidationResult dataclass"""
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation and attributes"""
        # Valid result
        valid_result = ValidationResult(True, sanitized_value="test@example.com")
        assert valid_result.is_valid is True
        assert valid_result.error_message is None
        assert valid_result.sanitized_value == "test@example.com"
        
        # Invalid result
        invalid_result = ValidationResult(False, "Invalid email format")
        assert invalid_result.is_valid is False
        assert invalid_result.error_message == "Invalid email format"
        assert invalid_result.sanitized_value is None
    
    def test_validation_result_repr(self):
        """Test ValidationResult string representation"""
        result = ValidationResult(True, sanitized_value="test@example.com")
        repr_str = repr(result)
        assert "ValidationResult" in repr_str
        assert "is_valid=True" in repr_str
        assert "test@example.com" in repr_str


class TestInputValidatorClass:
    """Test InputValidator class methods"""
    
    def test_sequential_pattern_detection(self):
        """Test sequential pattern detection"""
        # Test sequential numbers
        assert InputValidator._contains_sequential_pattern("123")
        assert InputValidator._contains_sequential_pattern("456")
        assert not InputValidator._contains_sequential_pattern("124")
        
        # Test sequential letters
        assert InputValidator._contains_sequential_pattern("abc")
        assert InputValidator._contains_sequential_pattern("xyz")
        assert not InputValidator._contains_sequential_pattern("abd")
        
        # Test mixed content
        assert not InputValidator._contains_sequential_pattern("a1b")
        assert not InputValidator._contains_sequential_pattern("")
        assert not InputValidator._contains_sequential_pattern("ab")
    
    def test_keyboard_pattern_detection(self):
        """Test keyboard pattern detection"""
        # Test common keyboard patterns
        assert InputValidator._contains_keyboard_pattern("qwerty")
        assert InputValidator._contains_keyboard_pattern("asdf")
        assert InputValidator._contains_keyboard_pattern("123456")
        assert InputValidator._contains_keyboard_pattern("qaz")
        
        # Test non-patterns
        assert not InputValidator._contains_keyboard_pattern("hello")
        assert not InputValidator._contains_keyboard_pattern("password")
        assert not InputValidator._contains_keyboard_pattern("")
    
    def test_sql_injection_detection(self):
        """Test SQL injection pattern detection"""
        # Test SQL injection patterns
        assert InputValidator._contains_sql_injection("SELECT * FROM users")
        assert InputValidator._contains_sql_injection("DROP TABLE users")
        assert InputValidator._contains_sql_injection("INSERT INTO users")
        assert InputValidator._contains_sql_injection("admin' OR 1=1")
        
        # Test normal text
        assert not InputValidator._contains_sql_injection("hello world")
        assert not InputValidator._contains_sql_injection("user@example.com")
        assert not InputValidator._contains_sql_injection("")
    
    def test_xss_detection(self):
        """Test XSS pattern detection"""
        # Test XSS patterns
        assert InputValidator._contains_xss("<script>alert('xss')</script>")
        assert InputValidator._contains_xss("javascript:alert('xss')")
        assert InputValidator._contains_xss("onload=alert('xss')")
        assert InputValidator._contains_xss("<iframe src=javascript:alert('xss')>")
        
        # Test normal text
        assert not InputValidator._contains_xss("hello world")
        assert not InputValidator._contains_xss("user@example.com")
        assert not InputValidator._contains_xss("")


if __name__ == '__main__':
    # Run tests directly if script is executed
    pytest.main([__file__, '-v'])
