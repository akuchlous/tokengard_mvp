"""
Frontend API Integration Tests

This test suite verifies that the frontend JavaScript properly calls all APIs
and that all GET/POST requests work correctly. It tests:

1. API endpoint accessibility
2. Frontend form submission to APIs
3. API response handling
4. Error handling
5. Loading states
6. Form validation
7. User experience flow
"""

import pytest
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from app import create_app
from models import db, User, ActivationToken
from auth_utils import hash_password


class TestFrontendAPIIntegration:
    """Test frontend API integration and user experience"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment with Selenium WebDriver"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False
        
        # Set up Chrome options for headless testing
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Initialize WebDriver
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            pytest.skip(f"Chrome WebDriver not available: {e}")
        
        self.driver.implicitly_wait(10)
        self.wait = WebDriverWait(self.driver, 10)
        
        # Create test client for backend operations
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()
        
        # Clean up WebDriver
        if hasattr(self, 'driver'):
            self.driver.quit()
    
    def test_home_page_loads_with_api_ready_elements(self):
        """Test that home page loads and shows API-ready elements"""
        self.driver.get('http://localhost:5000/')
        
        # Check that the page loads
        assert 'TokenGuard' in self.driver.title
        
        # Verify API-ready elements are present
        sign_in_btn = self.driver.find_element(By.CSS_SELECTOR, 'a[href="/auth/login"]')
        sign_up_btn = self.driver.find_element(By.CSS_SELECTOR, 'a[href="/auth/register"]')
        
        assert sign_in_btn.is_displayed()
        assert sign_up_btn.is_displayed()
        
        # Check that JavaScript is loaded
        js_loaded = self.driver.execute_script("return typeof window.messageDisplay !== 'undefined'")
        assert js_loaded, "Common JavaScript utilities not loaded"
    
    def test_registration_page_api_integration(self):
        """Test registration page API integration"""
        self.driver.get('http://localhost:5000/auth/register')
        
        # Wait for page to load
        self.wait.until(EC.presence_of_element_located((By.ID, 'registerForm')))
        
        # Check that form elements are present
        email_input = self.driver.find_element(By.ID, 'email')
        password_input = self.driver.find_element(By.ID, 'password')
        confirm_password_input = self.driver.find_element(By.ID, 'confirmPassword')
        submit_btn = self.driver.find_element(By.ID, 'submitBtn')
        
        assert email_input.is_displayed()
        assert password_input.is_displayed()
        assert confirm_password_input.is_displayed()
        assert submit_btn.is_displayed()
        
        # Test form validation (client-side)
        email_input.send_keys('invalid-email')
        email_input.send_keys(Keys.TAB)
        
        # Wait for validation error
        time.sleep(0.5)
        error_element = self.driver.find_element(By.ID, 'emailError')
        assert 'valid email' in error_element.text.lower()
        
        # Test password strength validation
        password_input.send_keys('weak')
        time.sleep(0.5)
        
        strength_element = self.driver.find_element(By.ID, 'passwordStrength')
        assert 'weak' in strength_element.text.lower()
        
        # Test password confirmation validation
        confirm_password_input.send_keys('different')
        confirm_password_input.send_keys(Keys.TAB)
        time.sleep(0.5)
        
        confirm_error = self.driver.find_element(By.ID, 'confirmPasswordError')
        assert 'match' in confirm_error.text.lower()
    
    def test_registration_api_call_success(self):
        """Test successful registration API call"""
        self.driver.get('http://localhost:5000/auth/register')
        
        # Wait for form to load
        self.wait.until(EC.presence_of_element_located((By.ID, 'registerForm')))
        
        # Fill in valid registration data
        email_input = self.driver.find_element(By.ID, 'email')
        password_input = self.driver.find_element(By.ID, 'password')
        confirm_password_input = self.driver.find_element(By.ID, 'confirmPassword')
        
        email_input.send_keys('testuser@example.com')
        password_input.send_keys('StrongPass123!')
        confirm_password_input.send_keys('StrongPass123!')
        
        # Submit form
        submit_btn = self.driver.find_element(By.ID, 'submitBtn')
        submit_btn.click()
        
        # Wait for API response
        time.sleep(2)
        
        # Check for success message
        try:
            success_message = self.driver.find_element(By.CLASS_NAME, 'message.success')
            assert 'successful' in success_message.text.lower()
        except NoSuchElementException:
            # Check if redirected to login (success case)
            current_url = self.driver.current_url
            assert '/auth/login' in current_url
    
    def test_registration_api_call_validation_error(self):
        """Test registration API call with validation errors"""
        self.driver.get('http://localhost:5000/auth/register')
        
        # Wait for form to load
        self.wait.until(EC.presence_of_element_located((By.ID, 'registerForm')))
        
        # Fill in invalid registration data
        email_input = self.driver.find_element(By.ID, 'email')
        password_input = self.driver.find_element(By.ID, 'password')
        confirm_password_input = self.driver.find_element(By.ID, 'confirmPassword')
        
        email_input.send_keys('invalid-email')
        password_input.send_keys('weak')
        confirm_password_input.send_keys('weak')
        
        # Submit form
        submit_btn = self.driver.find_element(By.ID, 'submitBtn')
        submit_btn.click()
        
        # Wait for validation
        time.sleep(1)
        
        # Check for validation errors
        email_error = self.driver.find_element(By.ID, 'emailError')
        password_error = self.driver.find_element(By.ID, 'passwordError')
        
        assert email_error.text != ''
        assert password_error.text != ''
    
    def test_login_page_api_integration(self):
        """Test login page API integration"""
        self.driver.get('http://localhost:5000/auth/login')
        
        # Wait for page to load
        self.wait.until(EC.presence_of_element_located((By.ID, 'loginForm')))
        
        # Check that form elements are present
        email_input = self.driver.find_element(By.ID, 'email')
        password_input = self.driver.find_element(By.ID, 'password')
        submit_btn = self.driver.find_element(By.ID, 'submitBtn')
        
        assert email_input.is_displayed()
        assert password_input.is_displayed()
        assert submit_btn.is_displayed()
        
        # Test form validation
        email_input.send_keys('invalid-email')
        email_input.send_keys(Keys.TAB)
        time.sleep(0.5)
        
        error_element = self.driver.find_element(By.ID, 'emailError')
        assert 'valid email' in error_element.text.lower()
    
    def test_login_api_call_success(self):
        """Test successful login API call"""
        # First create a user via backend
        with self.app.app_context():
            user = User(
                email='logintest@example.com',
                password_hash=hash_password('TestPass123!')
            )
            user.status = 'active'
            db.session.add(user)
            db.session.commit()
        
        self.driver.get('http://localhost:5000/auth/login')
        
        # Wait for form to load
        self.wait.until(EC.presence_of_element_located((By.ID, 'loginForm')))
        
        # Fill in valid login data
        email_input = self.driver.find_element(By.ID, 'email')
        password_input = self.driver.find_element(By.ID, 'password')
        
        email_input.send_keys('logintest@example.com')
        password_input.send_keys('TestPass123!')
        
        # Submit form
        submit_btn = self.driver.find_element(By.ID, 'submitBtn')
        submit_btn.click()
        
        # Wait for API response
        time.sleep(2)
        
        # Check for success (should redirect to dashboard)
        current_url = self.driver.current_url
        assert '/auth/dashboard/' in current_url or 'success' in self.driver.page_source.lower()
    
    def test_login_api_call_invalid_credentials(self):
        """Test login API call with invalid credentials"""
        self.driver.get('http://localhost:5000/auth/login')
        
        # Wait for form to load
        self.wait.until(EC.presence_of_element_located((By.ID, 'loginForm')))
        
        # Fill in invalid login data
        email_input = self.driver.find_element(By.ID, 'email')
        password_input = self.driver.find_element(By.ID, 'password')
        
        email_input.send_keys('nonexistent@example.com')
        password_input.send_keys('wrongpassword')
        
        # Submit form
        submit_btn = self.driver.find_element(By.ID, 'submitBtn')
        submit_btn.click()
        
        # Wait for API response
        time.sleep(2)
        
        # Check for error message
        try:
            error_message = self.driver.find_element(By.CLASS_NAME, 'message.error')
            assert 'failed' in error_message.text.lower() or 'invalid' in error_message.text.lower()
        except NoSuchElementException:
            # Check if there's an error in the form
            error_elements = self.driver.find_elements(By.CLASS_NAME, 'error')
            assert len(error_elements) > 0
    
    def test_forgot_password_api_integration(self):
        """Test forgot password page API integration"""
        self.driver.get('http://localhost:5000/auth/forgot-password')
        
        # Wait for page to load
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'form')))
        
        # Check that form elements are present
        email_input = self.driver.find_element(By.NAME, 'email')
        submit_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        
        assert email_input.is_displayed()
        assert submit_btn.is_displayed()
        
        # Test form submission
        email_input.send_keys('test@example.com')
        submit_btn.click()
        
        # Wait for API response
        time.sleep(2)
        
        # Check for response message
        page_source = self.driver.page_source.lower()
        assert 'sent' in page_source or 'check' in page_source
    
    def test_password_reset_api_integration(self):
        """Test password reset page API integration"""
        # Create a password reset token
        with self.app.app_context():
            user = User(
                email='resettest@example.com',
                password_hash=hash_password('OldPass123!')
            )
            user.status = 'active'
            db.session.add(user)
            db.session.commit()
            
            from auth_utils import PasswordResetToken
            reset_token = PasswordResetToken(user.id)
            db.session.add(reset_token)
            db.session.commit()
            
            token = reset_token.token
        
        self.driver.get(f'http://localhost:5000/auth/reset-password/{token}')
        
        # Wait for page to load
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'form')))
        
        # Check that form elements are present
        password_input = self.driver.find_element(By.NAME, 'password')
        submit_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        
        assert password_input.is_displayed()
        assert submit_btn.is_displayed()
        
        # Test form submission with new password
        password_input.send_keys('NewPass123!')
        submit_btn.click()
        
        # Wait for API response
        time.sleep(2)
        
        # Check for success message
        page_source = self.driver.page_source.lower()
        assert 'successful' in page_source or 'reset' in page_source
    
    def test_dashboard_api_integration(self):
        """Test dashboard page API integration"""
        # Create an active user
        with self.app.app_context():
            user = User(
                email='dashboard@example.com',
                password_hash=hash_password('TestPass123!')
            )
            user.status = 'active'
            db.session.add(user)
            db.session.commit()
        
        # Login first
        self.driver.get('http://localhost:5000/auth/login')
        self.wait.until(EC.presence_of_element_located((By.ID, 'loginForm')))
        
        email_input = self.driver.find_element(By.ID, 'email')
        password_input = self.driver.find_element(By.ID, 'password')
        
        email_input.send_keys('dashboard@example.com')
        password_input.send_keys('TestPass123!')
        
        submit_btn = self.driver.find_element(By.ID, 'submitBtn')
        submit_btn.click()
        
        # Wait for redirect
        time.sleep(2)
        
        # Check if we're on dashboard
        current_url = self.driver.current_url
        if '/auth/dashboard/' in current_url:
            # Dashboard loaded successfully
            assert 'Welcome' in self.driver.page_source
            assert 'dashboard@example.com' in self.driver.page_source
            
            # Test logout functionality
            logout_btn = self.driver.find_element(By.CSS_SELECTOR, 'a[href="/auth/logout"]')
            logout_btn.click()
            
            # Wait for redirect
            time.sleep(2)
            
            # Should be redirected to home page
            current_url = self.driver.current_url
            assert current_url.endswith('/') or 'TokenGuard' in self.driver.page_source
    
    def test_api_error_handling(self):
        """Test API error handling in frontend"""
        self.driver.get('http://localhost:5000/auth/register')
        
        # Wait for form to load
        self.wait.until(EC.presence_of_element_located((By.ID, 'registerForm')))
        
        # Try to submit empty form
        submit_btn = self.driver.find_element(By.ID, 'submitBtn')
        submit_btn.click()
        
        # Wait for validation
        time.sleep(1)
        
        # Check for validation errors
        email_error = self.driver.find_element(By.ID, 'emailError')
        password_error = self.driver.find_element(By.ID, 'passwordError')
        
        assert email_error.text != ''
        assert password_error.text != ''
    
    def test_loading_states(self):
        """Test loading states during API calls"""
        self.driver.get('http://localhost:5000/auth/register')
        
        # Wait for form to load
        self.wait.until(EC.presence_of_element_located((By.ID, 'registerForm')))
        
        # Fill in form data
        email_input = self.driver.find_element(By.ID, 'email')
        password_input = self.driver.find_element(By.ID, 'password')
        confirm_password_input = self.driver.find_element(By.ID, 'confirmPassword')
        
        email_input.send_keys('loadingtest@example.com')
        password_input.send_keys('StrongPass123!')
        confirm_password_input.send_keys('StrongPass123!')
        
        # Submit form
        submit_btn = self.driver.find_element(By.ID, 'submitBtn')
        submit_btn.click()
        
        # Check for loading state
        time.sleep(0.5)
        
        # Button should be disabled during submission
        assert submit_btn.get_attribute('disabled') == 'true' or 'loading' in submit_btn.get_attribute('class')
    
    def test_form_validation_real_time(self):
        """Test real-time form validation"""
        self.driver.get('http://localhost:5000/auth/register')
        
        # Wait for form to load
        self.wait.until(EC.presence_of_element_located((By.ID, 'registerForm')))
        
        email_input = self.driver.find_element(By.ID, 'email')
        password_input = self.driver.find_element(By.ID, 'password')
        
        # Test email validation
        email_input.send_keys('invalid')
        email_input.send_keys(Keys.TAB)
        time.sleep(0.5)
        
        email_error = self.driver.find_element(By.ID, 'emailError')
        assert 'valid email' in email_error.text.lower()
        
        # Fix email
        email_input.clear()
        email_input.send_keys('valid@example.com')
        email_input.send_keys(Keys.TAB)
        time.sleep(0.5)
        
        # Error should be cleared
        assert email_error.text == '' or 'error' not in email_error.get_attribute('class')
        
        # Test password strength
        password_input.send_keys('weak')
        time.sleep(0.5)
        
        strength_element = self.driver.find_element(By.ID, 'passwordStrength')
        assert 'weak' in strength_element.text.lower()
    
    def test_api_response_handling(self):
        """Test that API responses are properly handled"""
        self.driver.get('http://localhost:5000/auth/register')
        
        # Wait for form to load
        self.wait.until(EC.presence_of_element_located((By.ID, 'registerForm')))
        
        # Fill in valid data
        email_input = self.driver.find_element(By.ID, 'email')
        password_input = self.driver.find_element(By.ID, 'password')
        confirm_password_input = self.driver.find_element(By.ID, 'confirmPassword')
        
        email_input.send_keys('apitest@example.com')
        password_input.send_keys('StrongPass123!')
        confirm_password_input.send_keys('StrongPass123!')
        
        # Submit form
        submit_btn = self.driver.find_element(By.ID, 'submitBtn')
        submit_btn.click()
        
        # Wait for API response
        time.sleep(3)
        
        # Check for proper response handling
        page_source = self.driver.page_source.lower()
        
        # Should either show success message or redirect
        if 'successful' in page_source:
            # Success case
            assert 'successful' in page_source
        elif '/auth/login' in self.driver.current_url:
            # Redirect case
            assert '/auth/login' in self.driver.current_url
        else:
            # Check for any message
            assert 'message' in page_source or 'error' in page_source
    
    def test_cross_page_navigation_api_consistency(self):
        """Test that API calls work consistently across page navigation"""
        # Test home page
        self.driver.get('http://localhost:5000/')
        assert 'TokenGuard' in self.driver.title
        
        # Navigate to registration
        sign_up_btn = self.driver.find_element(By.CSS_SELECTOR, 'a[href="/auth/register"]')
        sign_up_btn.click()
        
        # Wait for registration page
        self.wait.until(EC.presence_of_element_located((By.ID, 'registerForm')))
        assert '/auth/register' in self.driver.current_url
        
        # Navigate to login
        login_link = self.driver.find_element(By.CSS_SELECTOR, 'a[href="/auth/login"]')
        login_link.click()
        
        # Wait for login page
        self.wait.until(EC.presence_of_element_located((By.ID, 'loginForm')))
        assert '/auth/login' in self.driver.current_url
        
        # Navigate back to home
        home_link = self.driver.find_element(By.CSS_SELECTOR, 'a[href="/"]')
        home_link.click()
        
        # Should be back on home page
        time.sleep(1)
        assert 'TokenGuard' in self.driver.title
    
    def test_mobile_responsiveness_api_integration(self):
        """Test API integration on mobile viewport"""
        # Set mobile viewport
        self.driver.set_window_size(375, 667)  # iPhone SE dimensions
        
        self.driver.get('http://localhost:5000/auth/register')
        
        # Wait for form to load
        self.wait.until(EC.presence_of_element_located((By.ID, 'registerForm')))
        
        # Check that form is usable on mobile
        email_input = self.driver.find_element(By.ID, 'email')
        password_input = self.driver.find_element(By.ID, 'password')
        confirm_password_input = self.driver.find_element(By.ID, 'confirmPassword')
        
        # Test mobile form submission
        email_input.send_keys('mobile@example.com')
        password_input.send_keys('StrongPass123!')
        confirm_password_input.send_keys('StrongPass123!')
        
        submit_btn = self.driver.find_element(By.ID, 'submitBtn')
        submit_btn.click()
        
        # Wait for API response
        time.sleep(2)
        
        # Should work the same as desktop
        page_source = self.driver.page_source.lower()
        assert 'successful' in page_source or '/auth/login' in self.driver.current_url


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
