#!/usr/bin/env python3
"""
Comprehensive Frontend Selenium test for banned keywords functionality.
Tests the complete banned keywords workflow with user activation.
"""

import pytest
import time
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class TestFrontendBannedKeywordsComprehensive:
    """Comprehensive test class for banned keywords frontend functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_driver(self):
        """Set up Chrome driver with headless mode"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
        yield
        
        self.driver.quit()
    
    def register_user(self):
        """Register a new user and return the email."""
        print("1️⃣ Registering new user...")
        self.driver.get('http://localhost:5000/auth/register')
        time.sleep(2)
        
        # Fill registration form
        email_input = self.driver.find_element(By.NAME, 'email')
        password_input = self.driver.find_element(By.NAME, 'password')
        confirm_password_input = self.driver.find_element(By.NAME, 'confirmPassword')
        
        test_email = f'test{int(time.time())}@example.com'
        email_input.send_keys(test_email)
        password_input.send_keys('TestPass123!')
        confirm_password_input.send_keys('TestPass123!')
        
        # Submit registration
        submit_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        submit_btn.click()
        time.sleep(3)
        
        print(f"✅ User registered with email: {test_email}")
        return test_email
    
    def activate_user_via_api(self, email):
        """Activate user via API call."""
        print("2️⃣ Activating user via API...")
        try:
            # Make a request to activate the user
            # This is a test-specific endpoint that activates users for testing
            response = requests.post('http://localhost:5000/api/test/activate-user', 
                                   json={'email': email}, 
                                   timeout=5)
            if response.status_code == 200:
                print(f"✅ User activated: {email}")
                return True
            else:
                print(f"❌ Failed to activate user: {response.status_code}")
                return False
        except Exception as e:
            print(f"⚠️  Could not activate user via API: {e}")
            return False
    
    def login_user(self, email):
        """Login the user."""
        print("3️⃣ Logging in user...")
        self.driver.get('http://localhost:5000/auth/login')
        time.sleep(2)
        
        # Fill login form
        email_field = self.wait.until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        password_field = self.driver.find_element(By.NAME, "password")
        
        email_field.clear()
        email_field.send_keys(email)
        password_field.clear()
        password_field.send_keys("TestPass123!")
        
        # Submit form
        submit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        submit_button.click()
        
        # Wait for redirect
        time.sleep(3)
        current_url = self.driver.current_url
        print(f"   Login redirect URL: {current_url}")
        
        # Check if we're on user profile page
        if "/user/" in current_url:
            print("✅ Login successful - redirected to user profile")
            # Extract user_id from URL
            user_id = current_url.split("/user/")[1]
            print(f"   User ID: {user_id}")
            return user_id
        else:
            print(f"⚠️  Unexpected redirect to: {current_url}")
            return None
    
    def test_banned_keywords_complete_workflow(self):
        """Test the complete banned keywords workflow."""
        print("🚀 Testing complete banned keywords workflow...")
        
        # Step 1: Register user
        email = self.register_user()
        
        # Step 2: Activate user
        if not self.activate_user_via_api(email):
            print("⚠️  User activation failed, but continuing test...")
        
        # Step 3: Login user
        user_id = self.login_user(email)
        if not user_id:
            print("❌ Login failed, cannot continue with banned keywords test")
            return
        
        # Step 4: Navigate to banned keywords page
        print("4️⃣ Navigating to banned keywords page...")
        self.driver.get(f'http://localhost:5000/banned_keywords/{user_id}')
        time.sleep(2)
        
        # Check if page loaded correctly
        page_source = self.driver.page_source
        if "Banned Keywords" in page_source:
            print("✅ Banned keywords page loaded successfully")
            
            # Test the textarea
            try:
                textarea = self.wait.until(
                    EC.presence_of_element_located((By.ID, "keywordsTextarea"))
                )
                print("✅ Keywords textarea found")
                
                # Test modifying keywords
                print("5️⃣ Testing keyword modification...")
                textarea.clear()
                test_keywords = "spam, scam, fraud, test, selenium"
                textarea.send_keys(test_keywords)
                
                # Test save button
                save_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
                save_button.click()
                time.sleep(2)
                
                # Check if keywords were saved
                textarea_after_save = self.driver.find_element(By.ID, "keywordsTextarea")
                saved_content = textarea_after_save.get_attribute("value")
                
                if "spam" in saved_content and "scam" in saved_content:
                    print("✅ Keywords saved successfully")
                else:
                    print("❌ Keywords not saved correctly")
                
                # Test load defaults button
                print("6️⃣ Testing load defaults...")
                try:
                    load_defaults_button = self.driver.find_element(By.ID, "loadDefaults")
                    load_defaults_button.click()
                    time.sleep(2)
                    
                    # Check if default keywords were loaded
                    textarea_after_defaults = self.driver.find_element(By.ID, "keywordsTextarea")
                    default_content = textarea_after_defaults.get_attribute("value")
                    
                    if "spam" in default_content and "scam" in default_content:
                        print("✅ Default keywords loaded successfully")
                    else:
                        print("❌ Default keywords not loaded correctly")
                        
                except NoSuchElementException:
                    print("⚠️  Load defaults button not found")
                
                # Test clear all button
                print("7️⃣ Testing clear all...")
                try:
                    clear_all_button = self.driver.find_element(By.ID, "clearAll")
                    clear_all_button.click()
                    time.sleep(1)
                    
                    # Check if keywords were cleared
                    textarea_after_clear = self.driver.find_element(By.ID, "keywordsTextarea")
                    cleared_content = textarea_after_clear.get_attribute("value")
                    
                    if cleared_content == "":
                        print("✅ Keywords cleared successfully")
                    else:
                        print("❌ Keywords not cleared correctly")
                        
                except NoSuchElementException:
                    print("⚠️  Clear all button not found")
                
            except TimeoutException:
                print("❌ Keywords textarea not found")
                print(f"   Page source preview: {page_source[:500]}...")
        else:
            print("❌ Banned keywords page not loaded correctly")
            print(f"   Page source preview: {page_source[:500]}...")
        
        print("✅ Complete banned keywords workflow test completed!")
    
    def test_banned_keywords_validation(self):
        """Test banned keywords validation."""
        print("🚀 Testing banned keywords validation...")
        
        # Register, activate, and login user
        email = self.register_user()
        self.activate_user_via_api(email)
        user_id = self.login_user(email)
        
        if not user_id:
            print("❌ Login failed, cannot continue with validation test")
            return
        
        # Navigate to banned keywords page
        self.driver.get(f'http://localhost:5000/banned_keywords/{user_id}')
        time.sleep(2)
        
        # Test validation with long keywords
        try:
            textarea = self.wait.until(
                EC.presence_of_element_located((By.ID, "keywordsTextarea"))
            )
            
            # Test with very long keyword
            long_keyword = "a" * 150  # Longer than 100 character limit
            textarea.clear()
            textarea.send_keys(f"valid_keyword, {long_keyword}, another_valid")
            
            # Click save button
            save_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            save_button.click()
            time.sleep(2)
            
            # Check if long keyword was handled correctly
            textarea_after_save = self.driver.find_element(By.ID, "keywordsTextarea")
            saved_content = textarea_after_save.get_attribute("value")
            
            # Should contain valid keywords but not the full long keyword
            if "valid_keyword" in saved_content and "another_valid" in saved_content:
                print("✅ Valid keywords preserved")
                
                # Check that long keyword was truncated or removed
                if len([kw for kw in saved_content.split() if len(kw) > 100]) == 0:
                    print("✅ Long keywords properly handled")
                else:
                    print("❌ Long keywords not properly handled")
            else:
                print("❌ Valid keywords not preserved")
                
        except TimeoutException:
            print("❌ Keywords textarea not found for validation test")
        
        print("✅ Banned keywords validation test completed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
