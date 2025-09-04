"""
Input Validation and Security Utilities

FLOW OVERVIEW
- validate_email(email)
  • RFC-like syntax checks and basic security checks; returns sanitized lowercased value.
- validate_password_hash(hash)
  • Enforce SHA-256 hex string constraints.
- validate_password_strength(password)
  • Enforce length and character variety; allows sequential patterns by project preference.
- sanitize_input(input, max_length)
  • Trim, bound length, normalize, and remove null bytes.

This module provides comprehensive validation functions for user inputs,
following security best practices and preventing common attack vectors.
"""

import re
import hashlib
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of validation operation"""
    is_valid: bool
    error_message: Optional[str] = None
    sanitized_value: Optional[str] = None


class InputValidator:
    """Comprehensive input validation class following security best practices"""
    
    # RFC 5322 compliant email regex (simplified but secure)
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    )
    
    # Common SQL injection patterns - improved patterns
    SQL_INJECTION_PATTERNS = [
        r'\b(union|select|insert|update|delete|drop|create|alter|exec|execute|script)\b',
        r'\b(or|and)\s+\d+\s*=\s*\d+',
        r'--\s*$',  # SQL comments
        r'/\*.*\*/',  # SQL block comments
        r'#\s*$',  # MySQL comments
        r';\s*(drop|delete|insert|update|select|union)',  # Multiple statements
        r'xp_cmdshell',  # SQL Server command execution
        r'information_schema',  # Database schema exploration
        r'waitfor\s+delay',  # SQL Server time delays
        r'shutdown',  # Database shutdown
    ]
    
    # XSS patterns - improved patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>',
        r'<svg[^>]*>',
        r'data:text/html',
        r'vbscript:',
        r'<img[^>]*on\w+\s*=',
        r'<a[^>]*javascript:',
        r'<form[^>]*javascript:',
    ]
    
    @classmethod
    def validate_email(cls, email: str) -> ValidationResult:
        """
        Validate email address with comprehensive security checks
        
        Args:
            email: Email address to validate
            
        Returns:
            ValidationResult with validation status and sanitized value
        """
        # Type and basic validation
        if not email or not isinstance(email, str):
            return ValidationResult(False, "Email must be a non-empty string")
        
        email = email.strip()
        if email == "":
            return ValidationResult(False, "Email cannot be empty")
        
        # Length validation (RFC 5321 limits)
        if len(email) > 254:
            return ValidationResult(False, "Email address too long (max 254 characters)")
        
        # Format validation
        if not cls.EMAIL_PATTERN.match(email):
            return ValidationResult(False, "Invalid email format")
        
        # Security validation
        if email.count('@') != 1:
            return ValidationResult(False, "Email must contain exactly one @ symbol")
        
        local_part, domain = email.split('@')
        if len(local_part) > 64:
            return ValidationResult(False, "Email local part too long (max 64 characters)")
        
        if len(domain) > 253:
            return ValidationResult(False, "Email domain too long (max 253 characters)")
        
        # Security: Local part cannot start or end with a dot
        if local_part.startswith('.') or local_part.endswith('.'):
            return ValidationResult(False, "Email local part cannot start or end with a dot")
        
        # Security: Local part cannot contain consecutive dots
        if '..' in local_part:
            return ValidationResult(False, "Email local part cannot contain consecutive dots")
        
        # Security: Domain cannot start or end with a dot
        if domain.startswith('.') or domain.endswith('.'):
            return ValidationResult(False, "Domain cannot start or end with a dot")
        
        if '..' in domain:
            return ValidationResult(False, "Domain cannot contain consecutive dots")
        
        # Check for SQL injection attempts
        if cls._contains_sql_injection(email):
            return ValidationResult(False, "Email contains invalid characters")
        
        # Check for XSS attempts
        if cls._contains_xss(email):
            return ValidationResult(False, "Email contains invalid characters")
        
        # Sanitize and normalize
        sanitized_email = email.lower()
        
        return ValidationResult(True, sanitized_value=sanitized_email)
    
    @classmethod
    def validate_password_hash(cls, password_hash: str) -> ValidationResult:
        """
        Validate password hash format and security
        
        Args:
            password_hash: Password hash to validate
            
        Returns:
            ValidationResult with validation status
        """
        # Type and basic validation
        if not password_hash or not isinstance(password_hash, str):
            return ValidationResult(False, "Password hash must be a non-empty string")
        
        password_hash = password_hash.strip()
        if password_hash == "":
            return ValidationResult(False, "Password hash cannot be empty")
        
        # Length validation (SHA-256 produces 64 hex characters)
        if len(password_hash) != 64:
            return ValidationResult(False, "Invalid password hash format: must be exactly 64 characters")
        
        # Format validation (hexadecimal characters only) - enforce lowercase
        if not all(c in '0123456789abcdef' for c in password_hash):
            return ValidationResult(False, "Invalid password hash format: must contain only lowercase hexadecimal characters")
        
        return ValidationResult(True, sanitized_value=password_hash)
    
    @classmethod
    def validate_password_strength(cls, password: str) -> ValidationResult:
        """
        Validate password strength requirements
        
        Args:
            password: Password to validate
            
        Returns:
            ValidationResult with validation status
        """
        if not password or not isinstance(password, str):
            return ValidationResult(False, "Password must be a non-empty string")
        
        if len(password) < 8:
            return ValidationResult(False, "Password must be at least 8 characters long")
        
        if len(password) > 128:
            return ValidationResult(False, "Password too long (max 128 characters)")
        
        # Check for common weak passwords
        weak_passwords = {
            'password', '123456', 'qwerty', 'abc123', 'password123',
            'admin', 'letmein', 'welcome', 'monkey', 'dragon'
        }
        
        if password.lower() in weak_passwords:
            return ValidationResult(False, "Password is too common, choose a stronger password")
        
        # Note: Sequential patterns are allowed - they're not inherently insecure
        # if cls._contains_sequential_pattern(password):
        #     return ValidationResult(False, "Password contains sequential patterns")
        
        # Check for keyboard patterns (these are more concerning)
        if cls._contains_keyboard_pattern(password):
            return ValidationResult(False, "Password contains keyboard patterns")
        
        # Check character variety
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
        
        if not (has_upper and has_lower and has_digit):
            return ValidationResult(False, "Password must contain uppercase, lowercase, and numeric characters")
        
        # Special characters are recommended but not required for basic validation
        # if not has_special:
        #     return ValidationResult(False, "Password should contain special characters for better security")
        
        return ValidationResult(True)
    
    @classmethod
    def sanitize_input(cls, input_string: str, max_length: int = 1000) -> str:
        """
        Sanitize user input to prevent injection attacks
        
        Args:
            input_string: Input string to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
        """
        if not input_string:
            return ""
        
        # Convert to string if needed
        input_string = str(input_string)
        
        # Trim whitespace
        sanitized = input_string.strip()
        
        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Normalize line endings
        sanitized = sanitized.replace('\r\n', '\n').replace('\r', '\n')
        
        return sanitized
    
    @classmethod
    def _contains_sql_injection(cls, text: str) -> bool:
        """Check if text contains SQL injection patterns"""
        text_lower = text.lower()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def _contains_xss(cls, text: str) -> bool:
        """Check if text contains XSS patterns"""
        text_lower = text.lower()
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def _contains_sequential_pattern(cls, text: str) -> bool:
        """Check if text contains sequential patterns"""
        if len(text) < 3:
            return False
        
        # Check for sequential numbers
        for i in range(len(text) - 2):
            if text[i].isdigit() and text[i+1].isdigit() and text[i+2].isdigit():
                if int(text[i+1]) == int(text[i]) + 1 and int(text[i+2]) == int(text[i+1]) + 1:
                    return True
        
        # Check for sequential letters
        for i in range(len(text) - 2):
            if text[i].isalpha() and text[i+1].isalpha() and text[i+2].isalpha():
                if ord(text[i+1].lower()) == ord(text[i].lower()) + 1 and ord(text[i+2].lower()) == ord(text[i+1].lower()) + 1:
                    return True
        
        return False
    
    @classmethod
    def _contains_keyboard_pattern(cls, text: str) -> bool:
        """Check if text contains keyboard patterns"""
        keyboard_patterns = [
            'qwerty', 'asdf', 'zxcv', '123456', 'abcdef',
            'qaz', 'wsx', 'edc', 'rfv', 'tgb', 'yhn', 'ujm'
        ]
        
        text_lower = text.lower()
        for pattern in keyboard_patterns:
            if pattern in text_lower:
                return True
        
        return False


# Convenience functions for common validations
def validate_email(email: str) -> ValidationResult:
    """Validate email address"""
    return InputValidator.validate_email(email)


def validate_password_hash(password_hash: str) -> ValidationResult:
    """Validate password hash"""
    return InputValidator.validate_password_hash(password_hash)


def validate_password_strength(password: str) -> ValidationResult:
    """Validate password strength"""
    return InputValidator.validate_password_strength(password)


def sanitize_input(input_string: str, max_length: int = 1000) -> str:
    """Sanitize user input"""
    return InputValidator.sanitize_input(input_string, max_length)
