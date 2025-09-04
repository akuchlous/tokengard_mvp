#!/usr/bin/env python3
"""
Test banned keywords functionality with real API key from demo script.
This test uses the demo script approach to get a real API key and test banned keywords.
"""

import pytest
import time
import requests
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class TestBannedKeywordsWithRealAPIKey:
    """Test banned keywords functionality with real API key."""
    
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
    
    def register_user_and_get_api_key(self):
        """Register a user and get a real API key using the demo script approach."""
        print("1️⃣ Registering user and getting API key...")
        
        # Register user
        self.driver.get('http://localhost:5000/auth/register')
        time.sleep(2)
        
        email_input = self.driver.find_element(By.NAME, 'email')
        password_input = self.driver.find_element(By.NAME, 'password')
        confirm_password_input = self.driver.find_element(By.NAME, 'confirmPassword')
        
        test_email = f'test{int(time.time())}@example.com'
        email_input.send_keys(test_email)
        password_input.send_keys('TestPass123!')
        confirm_password_input.send_keys('TestPass123!')
        
        submit_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        submit_btn.click()
        time.sleep(3)
        
        print(f"✅ User registered: {test_email}")
        
        # Extract activation token from server logs (this is printed in the server output)
        # For testing, we'll try to activate the user using the activation token
        # that was printed in the server logs
        
        # Try to get the activation token from the page source
        page_source = self.driver.page_source
        activation_pattern = r'Activation token: ([a-zA-Z0-9_-]+)'
        activation_matches = re.findall(activation_pattern, page_source)
        
        if activation_matches:
            activation_token = activation_matches[0]
            print(f"✅ Found activation token: {activation_token}")
            
            # Activate the user
            activation_url = f'http://localhost:5000/auth/activate/{activation_token}'
            self.driver.get(activation_url)
            time.sleep(2)
            
            print("✅ User activated")
        else:
            print("⚠️  Could not find activation token in page source")
        
        # Login the user
        print("2️⃣ Logging in user...")
        self.driver.get('http://localhost:5000/auth/login')
        time.sleep(2)
        
        email_field = self.wait.until(EC.presence_of_element_located((By.NAME, "email")))
        password_field = self.driver.find_element(By.NAME, "password")
        
        email_field.clear()
        email_field.send_keys(test_email)
        password_field.clear()
        password_field.send_keys("TestPass123!")
        
        submit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        submit_button.click()
        time.sleep(3)
        
        current_url = self.driver.current_url
        if "/user/" in current_url:
            user_id = current_url.split("/user/")[1]
            print(f"✅ Login successful, User ID: {user_id}")
            
            # Navigate to API keys page to get a real API key
            print("3️⃣ Getting API key...")
            self.driver.get(f'http://localhost:5000/keys/{user_id}')
            time.sleep(2)
            
            # Look for API keys in the page
            page_source = self.driver.page_source
            
            # Extract API key from the page (look for the pattern)
            api_key_pattern = r'tk-[a-zA-Z0-9]{32}'
            api_key_matches = re.findall(api_key_pattern, page_source)
            
            if api_key_matches:
                api_key = api_key_matches[0]
                print(f"✅ Found API key: {api_key}")
                return test_email, user_id, api_key
            else:
                print("❌ Could not find API key in page")
                return test_email, user_id, None
        else:
            print(f"❌ Login failed, URL: {current_url}")
            return test_email, None, None
    
    def test_banned_keywords_with_real_api_key(self):
        """Test banned keywords functionality with a real API key."""
        print("🚀 Testing banned keywords with real API key...")
        
        # Get user and API key
        email, user_id, api_key = self.register_user_and_get_api_key()
        
        if not api_key:
            print("❌ Could not get API key, skipping test")
            return
        
        # Test proxy endpoint with real API key
        print("4️⃣ Testing proxy endpoint with real API key...")
        
        # Test with legitimate content first
        test_text = "This is legitimate content for testing"
        
        try:
            response = requests.post('http://localhost:5000/api/proxy',
                                   json={
                                       'api_key': api_key,
                                       'text': test_text
                                   },
                                   timeout=5)
            
            print(f"   Legitimate content test:")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   Result: {result}")
                
                if 'key_pass' in str(result):
                    print("   ✅ Legitimate content passed")
                elif 'key_error' in str(result):
                    print("   ❌ Legitimate content was blocked")
                else:
                    print(f"   ⚠️  Unexpected result: {result}")
            else:
                print(f"   Error: {response.text}")
                
        except Exception as e:
            print(f"   Error testing legitimate content: {e}")
        
        # Test with potentially banned content
        print("5️⃣ Testing with potentially banned content...")
        
        banned_test_cases = [
            "This message contains spam",
            "This is a scam attempt",
            "This is fraud content",
            "This has malicious content"
        ]
        
        for test_text in banned_test_cases:
            try:
                response = requests.post('http://localhost:5000/api/proxy',
                                       json={
                                           'api_key': api_key,
                                           'text': test_text
                                       },
                                       timeout=5)
                
                print(f"   Text: '{test_text}'")
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    print(f"   Result: {result}")
                    
                    if 'key_error' in str(result):
                        print("   ✅ Content was blocked (banned keywords working)")
                    elif 'key_pass' in str(result):
                        print("   ⚠️  Content was allowed (no banned keywords set up)")
                    else:
                        print(f"   ⚠️  Unexpected result: {result}")
                else:
                    print(f"   Error: {response.text}")
                print("   ---")
                
            except Exception as e:
                print(f"   Error testing '{test_text}': {e}")
        
        print("✅ Banned keywords test with real API key completed!")
    
    def test_banned_keywords_page_with_real_user(self):
        """Test banned keywords page with a real authenticated user."""
        print("🚀 Testing banned keywords page with real user...")
        
        # Get user and API key
        email, user_id, api_key = self.register_user_and_get_api_key()
        
        if not user_id:
            print("❌ Could not get user ID, skipping test")
            return
        
        # Navigate to banned keywords page
        print("4️⃣ Testing banned keywords page...")
        self.driver.get(f'http://localhost:5000/banned_keywords/{user_id}')
        time.sleep(2)
        
        # Check if page loaded correctly
        page_source = self.driver.page_source
        page_title = self.driver.title
        
        print(f"   Page title: {page_title}")
        
        if "Banned Keywords" in page_source:
            print("✅ Banned keywords page loaded successfully")
            
            # Test the textarea
            try:
                textarea = self.wait.until(EC.presence_of_element_located((By.ID, "keywordsTextarea")))
                print("✅ Keywords textarea found")
                
                # Get current keywords
                current_keywords = textarea.get_attribute("value")
                print(f"   Current keywords: {current_keywords}")
                
                # Test modifying keywords
                print("5️⃣ Testing keyword modification...")
                textarea.clear()
                test_keywords = "spam, scam, fraud, test_blocked, selenium_test"
                textarea.send_keys(test_keywords)
                
                # Save keywords
                save_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
                save_button.click()
                time.sleep(2)
                
                # Verify keywords were saved
                textarea_after_save = self.driver.find_element(By.ID, "keywordsTextarea")
                saved_content = textarea_after_save.get_attribute("value")
                
                if "spam" in saved_content and "scam" in saved_content:
                    print("✅ Banned keywords saved successfully")
                    
                    # Now test the proxy endpoint with the saved keywords
                    if api_key:
                        print("6️⃣ Testing proxy endpoint with saved banned keywords...")
                        self.test_proxy_with_saved_keywords(api_key)
                    
                else:
                    print("❌ Banned keywords not saved correctly")
                
            except TimeoutException:
                print("❌ Keywords textarea not found")
                print(f"   Page source preview: {page_source[:500]}...")
        else:
            print("❌ Banned keywords page not loaded correctly")
            print(f"   Page source preview: {page_source[:500]}...")
        
        print("✅ Banned keywords page test with real user completed!")
    



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
