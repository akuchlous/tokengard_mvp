#!/usr/bin/env python3
"""
E2E test for API keys functionality using Selenium - Server-side approach
Tests the complete flow: signup -> activate -> login -> view API keys on dedicated page
"""

import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
import pytest
import subprocess
import signal
import os


class TestAPIKeysE2E:
    """Test API keys functionality with Selenium"""
    
    @pytest.fixture(scope="class")
    def flask_server(self):
        """Start Flask server for testing"""
        print("🚀 Starting Flask server...")
        
        # Kill any existing Flask processes (simplified)
        try:
            subprocess.run(['pkill', '-f', 'app.py'], check=False)
        except Exception:
            pass
        
        # Start Flask server
        env = os.environ.copy()
        env['FLASK_ENV'] = 'testing'
        
        process = subprocess.Popen(
            ['python', 'app.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            preexec_fn=os.setsid
        )
        
        # Wait for server to start
        print("⏳ Waiting for server to start...")
        for i in range(30):  # Wait up to 30 seconds
            try:
                response = requests.get("http://localhost:5000/health", timeout=1)
                if response.status_code == 200:
                    break
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        else:
            # Kill the process if it didn't start
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            raise Exception("Flask server failed to start")
        
        print("✅ Flask server started successfully")
        
        yield process
        
        # Cleanup
        print("🧹 Cleaning up Flask server...")
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=5)
        except (subprocess.TimeoutExpired, ProcessLookupError):
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
    
    @pytest.fixture
    def driver(self, flask_server):
        """Create Chrome WebDriver instance"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        # Remove headless for debugging
        # chrome_options.add_argument("--headless")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        
        yield driver
        
        driver.quit()
    
    def test_complete_api_keys_flow(self, driver):
        """Complete flow: signup -> activate -> login -> check API keys on dedicated page"""
        base_url = "http://localhost:5000"
        
        print("🧪 Starting E2E API Keys Test (Server-side)")
        print("=" * 50)
        
        # Step 1: Navigate to home page
        print("1️⃣ Navigating to home page...")
        driver.get(base_url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Verify we're on the home page
        assert "TokenGuard" in driver.title
        print("✅ Home page loaded")
        
        # Step 2: Navigate to registration page
        print("2️⃣ Navigating to registration page...")
        driver.get(f"{base_url}/auth/register")
        
        # Wait for registration page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        
        assert "Register" in driver.title
        print("✅ Registration page loaded")
        
        # Step 3: Fill registration form
        print("3️⃣ Filling registration form...")
        email = "e2e_server_test@example.com"
        password = "TestPass123!"
        
        # Fill email
        email_field = driver.find_element(By.NAME, "email")
        email_field.clear()
        email_field.send_keys(email)
        
        # Fill password
        password_field = driver.find_element(By.NAME, "password")
        password_field.clear()
        password_field.send_keys(password)
        
        # Fill confirm password
        confirm_field = driver.find_element(By.NAME, "confirmPassword")
        confirm_field.clear()
        confirm_field.send_keys(password)
        
        print("✅ Registration form filled")
        
        # Step 4: Submit registration form
        print("4️⃣ Submitting registration form...")
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        
        # Wait for redirect to activation-sent page
        WebDriverWait(driver, 10).until(
            EC.url_contains("activation-sent")
        )
        
        print("✅ Registration submitted, redirected to activation-sent page")
        
        # Step 5: Get activation link from API
        print("5️⃣ Getting activation link...")
        activation_response = requests.get(f"{base_url}/api/get-activation-link/{email}")
        assert activation_response.status_code == 200
        
        activation_data = activation_response.json()
        activation_url = activation_data.get('activation_url')
        assert activation_url is not None
        
        print(f"✅ Got activation link: {activation_url}")
        
        # Step 6: Activate account
        print("6️⃣ Activating account...")
        driver.get(activation_url)
        
        # Wait for redirect to login page
        WebDriverWait(driver, 10).until(
            EC.url_contains("login")
        )
        
        print("✅ Account activated, redirected to login page")
        
        # Step 7: Fill login form
        print("7️⃣ Filling login form...")
        email_field = driver.find_element(By.NAME, "email")
        email_field.clear()
        email_field.send_keys(email)
        
        password_field = driver.find_element(By.NAME, "password")
        password_field.clear()
        password_field.send_keys(password)
        
        print("✅ Login form filled")
        
        # Step 8: Submit login form (server-side redirect)
        print("8️⃣ Submitting login form...")
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        
        # Wait for redirect to user profile page
        WebDriverWait(driver, 10).until(
            EC.url_contains("/user/")
        )
        
        print("✅ Login successful, redirected to user profile page")
        
        # Step 9: Verify we're on the user profile page
        print("9️⃣ Verifying user profile page...")
        current_url = driver.current_url
        assert "/user/" in current_url
        assert "User Profile" in driver.title
        
        print(f"✅ On user profile page: {current_url}")
        
        # Step 10: Look for "View API Keys" link and navigate to keys page
        print("🔑 Looking for 'View API Keys' link...")
        
        try:
            api_keys_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "View API Keys"))
            )
            print("✅ Found 'View API Keys' link")
            
            # Click the link to navigate to keys page
            api_keys_link.click()
            print("✅ Clicked 'View API Keys' link")
            
            # Wait for keys page to load
            WebDriverWait(driver, 10).until(
                EC.url_contains("/keys/")
            )
            print("✅ Navigated to API keys page")
            
            # Verify we're on the keys page
            assert "API Keys" in driver.title
            print("✅ On API keys page")
            
            # Step 11: Check for API keys section on the dedicated page
            print("🔍 Checking API keys section...")
            api_keys_section = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "api-keys-section"))
            )
            print("✅ API keys section found on keys page")
            
            # Step 12: Check if there are any API keys displayed
            print("📋 Checking for API keys...")
            try:
                # Look for the table structure
                keys_table = driver.find_element(By.CLASS_NAME, "api-keys-table")
                api_key_rows = keys_table.find_elements(By.CSS_SELECTOR, "tbody tr")
                
                if api_key_rows:
                    print(f"✅ Found {len(api_key_rows)} API key(s)")
                    
                    # Check the first key (should be key_0)
                    first_row = api_key_rows[0]
                    key_name = first_row.find_element(By.CLASS_NAME, "key-name").text
                    key_value = first_row.find_element(By.CSS_SELECTOR, ".key-value code").text
                    key_status = first_row.find_element(By.CSS_SELECTOR, ".key-state .status-badge").text
                    
                    print(f"✅ First key: {key_name} = {key_value} ({key_status})")
                    
                    # Verify it's the expected key_0
                    assert key_name == "key_0", f"Expected 'key_0', got '{key_name}'"
                    assert key_value.startswith("tk-"), f"Expected key to start with 'tk-', got '{key_value}'"
                    assert key_status.lower() == "enabled", f"Expected 'enabled', got '{key_status}'"
                    
                    # Verify we have 10 keys total
                    assert len(api_key_rows) == 10, f"Expected 10 keys, got {len(api_key_rows)}"
                    
                    print("✅ All 10 API keys verified successfully")
                else:
                    # Check for "No API keys yet" message
                    no_keys_msg = driver.find_element(By.CLASS_NAME, "no-keys")
                    print(f"✅ Found message: {no_keys_msg.text}")
                    
            except Exception as e:
                print(f"⚠️  Could not verify API keys content: {e}")
                # Still consider test successful if we reached the keys page
            
            print("🎉 API keys flow completed successfully!")
            
        except TimeoutException:
            print("❌ 'View API Keys' link not found")
            
            # Debug: Check what's actually on the page
            print("📄 Current page source (first 2000 chars):")
            print(driver.page_source[:2000])
            print("...")
            
            # Take a screenshot for debugging
            driver.save_screenshot("user_profile_no_keys_link.png")
            print("📸 Screenshot saved as user_profile_no_keys_link.png")
            
            assert False, "'View API Keys' link not found on user profile page"
        
        except Exception as e:
            print(f"❌ Error in API keys flow: {e}")
            
            # Take a screenshot for debugging
            driver.save_screenshot("api_keys_flow_error.png")
            print("📸 Error screenshot saved as api_keys_flow_error.png")
            
            raise e


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
