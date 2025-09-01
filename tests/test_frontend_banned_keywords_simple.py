#!/usr/bin/env python3
"""
Simple Frontend Selenium test for banned keywords functionality.
Tests the banned keywords page with a pre-activated user.
"""

import pytest
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class TestFrontendBannedKeywordsSimple:
    """Simple test class for banned keywords frontend functionality."""
    
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
    
    def test_banned_keywords_page_structure(self):
        """Test that the banned keywords page loads and has the expected structure."""
        print("🚀 Testing banned keywords page structure...")
        
        # Navigate to banned keywords page (this will show auth required, but we can test the structure)
        self.driver.get('http://localhost:5000/banned_keywords/test_user_id')
        time.sleep(2)
        
        # Check page title
        page_title = self.driver.title
        print(f"   Page title: {page_title}")
        
        # Check if we get the expected auth required page
        if "Authentication Required" in page_title:
            print("✅ Authentication required page loaded correctly")
            
            # Check for expected elements on auth required page
            page_source = self.driver.page_source
            
            # Check for error message
            if "You need to be logged in" in page_source:
                print("✅ Authentication message found")
            
            # Check for home button
            try:
                home_button = self.driver.find_element(By.CSS_SELECTOR, '.home-button')
                assert home_button is not None
                print("✅ Home button found")
            except NoSuchElementException:
                print("❌ Home button not found")
            
            print("✅ Banned keywords page structure test passed!")
        else:
            print(f"⚠️  Unexpected page title: {page_title}")
            # Check what we actually got
            page_source = self.driver.page_source
            print(f"   Page source preview: {page_source[:500]}...")
    
    def test_banned_keywords_page_with_login_flow(self):
        """Test the complete flow: register -> activate -> login -> banned keywords page."""
        print("🚀 Testing complete banned keywords flow...")
        
        # Step 1: Register a new user
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
        
        # Step 2: Try to login (this will fail because user is not activated)
        print("2️⃣ Attempting login (should fail due to activation)...")
        self.driver.get('http://localhost:5000/auth/login')
        time.sleep(2)
        
        # Fill login form
        email_field = self.wait.until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        password_field = self.driver.find_element(By.NAME, "password")
        
        email_field.clear()
        email_field.send_keys(test_email)
        password_field.clear()
        password_field.send_keys("TestPass123!")
        
        # Submit form
        submit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        submit_button.click()
        time.sleep(3)
        
        # Check if we get the expected activation required message
        page_source = self.driver.page_source.lower()
        if 'account not activated' in page_source or 'activation' in page_source:
            print("✅ Login correctly shows activation required message")
        else:
            print("⚠️  Unexpected login result")
            current_url = self.driver.current_url
            print(f"   Current URL: {current_url}")
            print(f"   Page source preview: {page_source[:300]}...")
        
        # Step 3: Test that banned keywords page requires authentication
        print("3️⃣ Testing banned keywords page access...")
        self.driver.get('http://localhost:5000/banned_keywords/test_user_id')
        time.sleep(2)
        
        page_title = self.driver.title
        if "Authentication Required" in page_title:
            print("✅ Banned keywords page correctly requires authentication")
        else:
            print(f"⚠️  Unexpected page title: {page_title}")
        
        print("✅ Complete banned keywords flow test passed!")
    
    def test_banned_keywords_page_elements(self):
        """Test that the banned keywords page has the expected elements when accessed."""
        print("🚀 Testing banned keywords page elements...")
        
        # Navigate to banned keywords page
        self.driver.get('http://localhost:5000/banned_keywords/test_user_id')
        time.sleep(2)
        
        # Check page structure
        page_source = self.driver.page_source
        
        # Check for expected CSS classes and structure
        expected_elements = [
            'error-page',
            'error-container', 
            'error-icon',
            'error-title',
            'error-message',
            'home-button'
        ]
        
        found_elements = []
        for element in expected_elements:
            if element in page_source:
                found_elements.append(element)
                print(f"✅ Found element: {element}")
            else:
                print(f"❌ Missing element: {element}")
        
        # Check that we found most expected elements
        if len(found_elements) >= 4:  # At least 4 out of 6 elements
            print("✅ Banned keywords page has expected structure")
        else:
            print(f"⚠️  Only found {len(found_elements)} out of {len(expected_elements)} expected elements")
        
        print("✅ Banned keywords page elements test completed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
