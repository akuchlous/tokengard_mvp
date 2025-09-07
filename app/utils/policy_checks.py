"""
Policy checks for proxy requests.

Provides `PolicyChecker`, which aggregates validations:
- API key existence, format, and active state.
- User active status linked to the API key.
- Banned keyword scanning of user-managed keyword lists.
- External safety checks (length limits, repetition, basic heuristics).

The checker returns structured results suitable for API response formatting.
"""
"""
Policy Checks Module

FLOW OVERVIEW
- validate_api_key(api_key, client_ip)
  • Syntactic checks → DB lookup → key state and user status verification.
- check_banned_keywords(user_id, text, client_ip)
  • Consult user-specific banned keywords and fail if any match.
- check_external_security(text, client_ip)
  • Length checks, placeholder external moderation simulation.
- run_all_checks(api_key, text, client_ip)
  • Orchestrates the above, returning a unified PolicyCheckResult with details.

This module handles all policy validation for the LLM proxy including:
- API key validation
- Banned keywords checking
- Default security checks
- External service validation

Can be called directly by API endpoints or from the proxy.
"""

import logging
from typing import Dict, Tuple, Optional, Any
from flask import current_app
from ..models import APIKey, BannedKeyword, User, db


class PolicyCheckResult:
    """Result of a policy check operation."""
    
    def __init__(self, passed: bool, error_code: Optional[str] = None, 
                 message: Optional[str] = None, details: Optional[Dict] = None):
        self.passed = passed
        self.error_code = error_code
        self.message = message
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            'passed': self.passed,
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details
        }


class PolicyChecker:
    """Main policy checker class."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_api_key(self, api_key: str, client_ip: str = None) -> PolicyCheckResult:
        """
        Validate API key format and existence.
        
        Args:
            api_key: The API key to validate
            client_ip: Client IP for logging
            
        Returns:
            PolicyCheckResult with validation status
        """
        try:
            # Format validation
            if not api_key or not isinstance(api_key, str):
                self.logger.warning(f"Empty or invalid API key from {client_ip}")
                return PolicyCheckResult(
                    passed=False,
                    error_code='MISSING_API_KEY',
                    message='API key is required.'
                )
            
            api_key = api_key.strip()
            
            # Length validation
            if len(api_key) < 10 or len(api_key) > 200:
                self.logger.warning(f"Invalid API key length from {client_ip}: {len(api_key)}")
                return PolicyCheckResult(
                    passed=False,
                    error_code='INVALID_API_KEY_FORMAT',
                    message='API key format is invalid.'
                )
            
            # Character validation
            if any(char in api_key for char in ['<', '>', '"', "'", '&', ';', '(', ')']):
                self.logger.warning(f"Suspicious API key pattern from {client_ip}")
                return PolicyCheckResult(
                    passed=False,
                    error_code='INVALID_API_KEY_CHARS',
                    message='API key contains invalid characters.'
                )
            
            # Database lookup
            key_record = APIKey.query.filter_by(key_value=api_key).first()
            if not key_record:
                self.logger.warning(f"API key not found from {client_ip}: {api_key[:10]}...")
                return PolicyCheckResult(
                    passed=False,
                    error_code='API_KEY_NOT_FOUND',
                    message='API key not found.'
                )
            
            # State validation
            if key_record.state.lower() != 'enabled':
                self.logger.warning(f"Inactive API key used from {client_ip}: {api_key[:10]}...")
                return PolicyCheckResult(
                    passed=False,
                    error_code='API_KEY_INACTIVE',
                    message='API key is inactive.'
                )
            
            # User account validation
            user = key_record.user
            if user.status != 'active':
                self.logger.warning(f"Inactive user account from {client_ip}: user_id={user.id}")
                return PolicyCheckResult(
                    passed=False,
                    error_code='USER_ACCOUNT_INACTIVE',
                    message='User account is inactive.'
                )
            
            return PolicyCheckResult(
                passed=True,
                details={
                    'api_key_record': key_record,
                    'user': user,
                    'key_name': key_record.key_name
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error validating API key: {str(e)}")
            return PolicyCheckResult(
                passed=False,
                error_code='API_KEY_VALIDATION_ERROR',
                message='API key validation failed.'
            )
    
    def check_banned_keywords(self, user_id: int, text: str, client_ip: str = None) -> PolicyCheckResult:
        """
        Check if text contains banned keywords for the user.
        
        Args:
            user_id: User ID to check keywords for
            text: Text content to check
            client_ip: Client IP for logging
            
        Returns:
            PolicyCheckResult with keyword check status
        """
        try:
            if not text or not isinstance(text, str):
                return PolicyCheckResult(passed=True)
            
            # Check banned keywords
            is_banned, banned_keyword = BannedKeyword.check_banned(user_id, text)
            
            if is_banned:
                self.logger.info(f"Banned keyword detected from {client_ip}: '{banned_keyword}'")
                return PolicyCheckResult(
                    passed=False,
                    error_code='BANNED_KEYWORD',
                    message=f'Content contains banned keyword: {banned_keyword}',
                    details={'banned_keyword': banned_keyword}
                )
            
            return PolicyCheckResult(passed=True)
            
        except Exception as e:
            self.logger.error(f"Error checking banned keywords: {str(e)}")
            return PolicyCheckResult(
                passed=False,
                error_code='KEYWORD_CHECK_ERROR',
                message='Keyword validation failed.'
            )
    
    def check_external_security(self, text: str, client_ip: str = None) -> PolicyCheckResult:
        """
        Check text against external security services.
        
        Args:
            text: Text content to check
            client_ip: Client IP for logging
            
        Returns:
            PolicyCheckResult with external check status
        """
        try:
            if not text or not isinstance(text, str):
                return PolicyCheckResult(passed=True)
            
            # Text length check
            if len(text) > 10000:  # 10KB text limit
                self.logger.warning(f"Text too long from {client_ip}: {len(text)} characters")
                return PolicyCheckResult(
                    passed=False,
                    error_code='TEXT_TOO_LONG',
                    message='Text content too long. Maximum 10,000 characters allowed.'
                )
            
            # Simulate external API call (placeholder)
            external_result = self._simulate_external_check(text)
            
            if external_result['blocked']:
                self.logger.info(f"External API blocked content from {client_ip}: {external_result['reason']}")
                return PolicyCheckResult(
                    passed=False,
                    error_code='EXTERNAL_API_BLOCKED',
                    message=f'Content blocked by external service: {external_result["reason"]}',
                    details={'external_reason': external_result['reason']}
                )
            
            return PolicyCheckResult(
                passed=True,
                details={'external_check': external_result}
            )
            
        except Exception as e:
            self.logger.error(f"Error in external security check: {str(e)}")
            return PolicyCheckResult(
                passed=False,
                error_code='EXTERNAL_API_ERROR',
                message='External content check failed. Please try again.'
            )
    
    def _simulate_external_check(self, text: str) -> Dict[str, Any]:
        """
        Simulate external API check (placeholder implementation).
        
        Args:
            text: Text to check
            
        Returns:
            Dict with check results
        """
        # Simulate blocking very long text (over 1000 characters)
        if len(text) > 1000:
            return {
                'blocked': True,
                'reason': 'Content too long',
                'confidence': 0.8,
                'service': 'placeholder'
            }
        
        # Simulate blocking text with excessive repetition
        words = text.lower().split()
        if len(words) > 10:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            max_repetition = max(word_counts.values()) if word_counts else 0
            if max_repetition > len(words) * 0.3:  # More than 30% repetition
                return {
                    'blocked': True,
                    'reason': 'Excessive word repetition detected',
                    'confidence': 0.7,
                    'service': 'placeholder'
                }
        
        # If all checks pass
        return {
            'blocked': False,
            'reason': 'Content passed external checks',
            'confidence': 0.9,
            'service': 'placeholder'
        }
    
    def run_all_checks(self, api_key: str, text: str = None, client_ip: str = None) -> PolicyCheckResult:
        """
        Run all policy checks in sequence.
        
        Args:
            api_key: API key to validate
            text: Text content to check (optional)
            client_ip: Client IP for logging
            
        Returns:
            PolicyCheckResult with overall check status
        """
        try:
            # 1. API Key validation
            key_result = self.validate_api_key(api_key, client_ip)
            if not key_result.passed:
                return key_result
            
            # Get user info from key validation
            user = key_result.details['user']
            api_key_record = key_result.details['api_key_record']
            
            # 2. Banned keywords check (if text provided)
            if text:
                # Ensure defaults exist for new users with no keywords configured
                try:
                    existing_keywords = BannedKeyword.get_user_keywords(user.id)
                    if not existing_keywords:
                        BannedKeyword.populate_default_keywords(user.id)
                except Exception:
                    pass
                keyword_result = self.check_banned_keywords(user.id, text, client_ip)
                if not keyword_result.passed:
                    return keyword_result
                
                # 3. External security check
                external_result = self.check_external_security(text, client_ip)
                if not external_result.passed:
                    return external_result
                
                # Combine details
                combined_details = {
                    'api_key_record': api_key_record,
                    'user': user,
                    'key_name': api_key_record.key_name,
                    'text_length': len(text),
                    'external_check': external_result.details.get('external_check', {})
                }
            else:
                combined_details = {
                    'api_key_record': api_key_record,
                    'user': user,
                    'key_name': api_key_record.key_name,
                    'text_length': 0
                }
            
            return PolicyCheckResult(
                passed=True,
                message='All policy checks passed.',
                details=combined_details
            )
            
        except Exception as e:
            self.logger.error(f"Error running policy checks: {str(e)}")
            return PolicyCheckResult(
                passed=False,
                error_code='POLICY_CHECK_ERROR',
                message='Policy validation failed.'
            )


# Global instance
policy_checker = PolicyChecker()
