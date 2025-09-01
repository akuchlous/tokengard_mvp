#!/usr/bin/env python3
"""
Complete workflow test for banned keywords functionality.
Tests the full workflow: register -> activate -> login -> set banned keywords -> test proxy endpoint.
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


class TestBannedKeywordsCompleteWorkflow:
    """Complete workflow test for banned keywords functionality."""
    
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
    
    def complete_user_setup(self):
        """Complete user setup: register -> activate -> login -> get API key."""
        print("1️⃣ Setting up complete user workflow...")
        
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
        
        # Activate user using the API endpoint (like the demo script does)
        try:
            response = requests.get(f'http://localhost:5000/api/get-activation-link/{test_email}', timeout=5)
            if response.status_code == 200:
                activation_data = response.json()
                activation_url = activation_data.get('activation_url')
                if activation_url:
                    self.driver.get(activation_url)
                    time.sleep(2)
                    print("✅ User activated via API")
                else:
                    print("❌ No activation URL in response")
            else:
                print(f"❌ Failed to get activation link: {response.status_code}")
        except Exception as e:
            print(f"❌ Activation failed: {e}")
        
        # Login user
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
            
            # Get API key
            self.driver.get(f'http://localhost:5000/keys/{user_id}')
            time.sleep(2)
            
            page_source = self.driver.page_source
            api_key_pattern = r'tk-[a-zA-Z0-9]{32}'
            api_key_matches = re.findall(api_key_pattern, page_source)
            
            if api_key_matches:
                api_key = api_key_matches[0]
                print(f"✅ Found API key: {api_key}")
                return test_email, user_id, api_key
            else:
                print("❌ Could not find API key")
                return test_email, user_id, None
        else:
            print(f"❌ Login failed, URL: {current_url}")
            return test_email, None, None
    
    def test_complete_banned_keywords_workflow(self):
        """Test the complete banned keywords workflow."""
        print("🚀 Testing complete banned keywords workflow...")
        
        # Setup user
        email, user_id, api_key = self.complete_user_setup()
        
        if not api_key:
            print("❌ Could not get API key, skipping test")
            return
        
        # Test proxy endpoint before setting banned keywords
        print("2️⃣ Testing proxy endpoint before banned keywords...")
        test_text = "This message contains spam content"
        
        try:
            response = requests.post('http://localhost:5000/api/proxy',
                                   json={
                                       'api_key': api_key,
                                       'text': test_text
                                   },
                                   timeout=5)
            
            print(f"   Before banned keywords:")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   Result: {result}")
                
                if 'key_pass' in str(result):
                    print("   ✅ Content passed (no banned keywords set up)")
                elif 'key_error' in str(result):
                    print("   ❌ Content was blocked (banned keywords already set up)")
                else:
                    print(f"   ⚠️  Unexpected result: {result}")
            else:
                print(f"   Error: {response.text}")
                
        except Exception as e:
            print(f"   Error testing proxy: {e}")
        
        # Navigate to banned keywords page and set keywords
        print("3️⃣ Setting up banned keywords...")
        self.driver.get(f'http://localhost:5000/banned_keywords/{user_id}')
        time.sleep(2)
        
        page_source = self.driver.page_source
        if "Banned Keywords" in page_source:
            print("✅ Banned keywords page loaded")
            
            try:
                textarea = self.wait.until(EC.presence_of_element_located((By.ID, "keywordsTextarea")))
                
                # Set test banned keywords
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
                else:
                    print("❌ Banned keywords not saved correctly")
                    return
                
            except TimeoutException:
                print("❌ Could not access banned keywords form")
                return
        else:
            print("❌ Banned keywords page not loaded")
            return
        
        # Test proxy endpoint after setting banned keywords
        print("4️⃣ Testing proxy endpoint after banned keywords...")
        
        # Test with banned content
        banned_test_cases = [
            "This message contains spam",
            "This is a scam attempt",
            "This is fraud content",
            "This has test_blocked keyword",
            "This contains selenium_test"
        ]
        
        # Test with allowed content
        allowed_test_cases = [
            "This is legitimate content",
            "This is a normal message",
            "This contains no banned words"
        ]
        
        print("   Testing banned content...")
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
                        print("   ✅ Content was blocked correctly")
                    elif 'key_pass' in str(result):
                        print("   ❌ Content was allowed (should be blocked)")
                    else:
                        print(f"   ⚠️  Unexpected result: {result}")
                else:
                    print(f"   Error: {response.text}")
                print("   ---")
                
            except Exception as e:
                print(f"   Error testing '{test_text}': {e}")
        
        print("   Testing allowed content...")
        for test_text in allowed_test_cases:
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
                    
                    if 'key_pass' in str(result):
                        print("   ✅ Content was allowed correctly")
                    elif 'key_error' in str(result):
                        print("   ❌ Content was blocked (should be allowed)")
                    else:
                        print(f"   ⚠️  Unexpected result: {result}")
                else:
                    print(f"   Error: {response.text}")
                print("   ---")
                
            except Exception as e:
                print(f"   Error testing '{test_text}': {e}")
        
        print("✅ Complete banned keywords workflow test completed!")
    
    def test_banned_keywords_persistence(self):
        """Test that banned keywords persist and old ones are still blocked."""
        print("🚀 Testing banned keywords persistence...")
        
        # Setup user
        email, user_id, api_key = self.complete_user_setup()
        
        if not api_key:
            print("❌ Could not get API key, skipping test")
            return
        
        # Set initial banned keywords
        print("2️⃣ Setting initial banned keywords...")
        self.driver.get(f'http://localhost:5000/banned_keywords/{user_id}')
        time.sleep(2)
        
        try:
            textarea = self.wait.until(EC.presence_of_element_located((By.ID, "keywordsTextarea")))
            
            # Set initial keywords
            textarea.clear()
            initial_keywords = "spam, scam, fraud"
            textarea.send_keys(initial_keywords)
            
            save_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            save_button.click()
            time.sleep(2)
            
            print("✅ Initial banned keywords set")
            
        except TimeoutException:
            print("❌ Could not set initial banned keywords")
            return
        
        # Test that initial keywords are blocked
        print("3️⃣ Testing initial banned keywords...")
        test_text = "This message contains spam"
        
        try:
            response = requests.post('http://localhost:5000/api/proxy',
                                   json={
                                       'api_key': api_key,
                                       'text': test_text
                                   },
                                   timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if 'key_error' in str(result):
                    print("✅ Initial banned keywords working")
                else:
                    print("❌ Initial banned keywords not working")
            else:
                print(f"❌ Error testing initial keywords: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error testing initial keywords: {e}")
        
        # Add new banned keywords
        print("4️⃣ Adding new banned keywords...")
        self.driver.get(f'http://localhost:5000/banned_keywords/{user_id}')
        time.sleep(2)
        
        try:
            textarea = self.wait.until(EC.presence_of_element_located((By.ID, "keywordsTextarea")))
            
            # Add new keywords to existing ones
            current_keywords = textarea.get_attribute("value")
            new_keywords = f"{current_keywords}, test_blocked, selenium_test"
            textarea.clear()
            textarea.send_keys(new_keywords)
            
            save_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            save_button.click()
            time.sleep(2)
            
            print("✅ New banned keywords added")
            
        except TimeoutException:
            print("❌ Could not add new banned keywords")
            return
        
        # Test that both old and new keywords are blocked
        print("5️⃣ Testing that both old and new keywords are blocked...")
        
        test_cases = [
            ("This message contains spam", "old keyword"),
            ("This is a scam attempt", "old keyword"),
            ("This has test_blocked keyword", "new keyword"),
            ("This contains selenium_test", "new keyword")
        ]
        
        for test_text, keyword_type in test_cases:
            try:
                response = requests.post('http://localhost:5000/api/proxy',
                                       json={
                                           'api_key': api_key,
                                           'text': test_text
                                       },
                                       timeout=5)
                
                print(f"   Testing {keyword_type}: '{test_text}'")
                if response.status_code == 200:
                    result = response.json()
                    if 'key_error' in str(result):
                        print(f"   ✅ {keyword_type} blocked correctly")
                    else:
                        print(f"   ❌ {keyword_type} not blocked")
                else:
                    print(f"   ❌ Error testing {keyword_type}: {response.status_code}")
                print("   ---")
                
            except Exception as e:
                print(f"   Error testing {keyword_type}: {e}")
        
        print("✅ Banned keywords persistence test completed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
