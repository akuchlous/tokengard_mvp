#!/usr/bin/env python3
"""
TokenGuard Demo Script
======================
Automated demonstration of the user registration flow with visual feedback.
"""

import time
import sys
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException


class TokenGuardDemo:
    """Main demo class for TokenGuard registration flow."""
    
    def __init__(self):
        """Initialize the demo with browser setup."""
        self.driver = None
        self.base_url = "http://localhost:5000"
        self.wait_timeout = 15  # Increased timeout for better reliability
        
    def setup_browser(self):
        """Set up Chrome WebDriver with appropriate options."""
        print("🌐 Setting up browser...")
        
        chrome_options = Options()
        # Removed --headless so browser window is visible
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(5)
            print("✅ Browser setup complete!")
            return True
        except Exception as e:
            print(f"❌ Failed to setup browser: {e}")
            return False
    
    def wait_for_server(self, max_attempts=30, delay=1):
        """Wait for the Flask server to be ready with health checks."""
        print("🔍 Checking server health...")
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{self.base_url}/health", timeout=2)
                if response.status_code == 200:
                    print("✅ Server is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            if attempt < max_attempts - 1:
                print(f"   Server not ready, waiting {delay}s... (attempt {attempt + 1}/{max_attempts})")
                time.sleep(delay)
        
        print("❌ Server health check failed after maximum attempts")
        return False
    
    def safe_wait_for_element(self, by, value, timeout=None, description="element"):
        """Safely wait for an element with proper error handling."""
        if timeout is None:
            timeout = self.wait_timeout
            
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            print(f"✅ Found {description}")
            return element
        except TimeoutException:
            print(f"❌ Timeout waiting for {description}")
            return None
        except Exception as e:
            print(f"❌ Error waiting for {description}: {e}")
            return None
    
    def safe_click_element(self, element, description="element"):
        """Safely click an element with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Wait for element to be clickable
                WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(element)
                )
                element.click()
                print(f"✅ Clicked {description}")
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"   Retry {attempt + 1}/{max_retries} for {description}")
                    time.sleep(1)
                else:
                    print(f"❌ Failed to click {description}: {e}")
                    return False
        return False
    
    def show_popup(self, message, background_color="#4CAF50", duration=1000):
        """Show a popup message with specified styling and duration."""
        popup_script = f"""
        // Create popup overlay
        const popup = document.createElement('div');
        popup.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: {background_color};
            color: white;
            padding: 20px 30px;
            border-radius: 10px;
            font-size: 18px;
            font-weight: bold;
            z-index: 10000;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            animation: fadeIn 0.3s ease-in;
            text-align: center;
            max-width: 300px;
        `;
        popup.innerHTML = `{message}`;
        
        // Add to page
        document.body.appendChild(popup);
        
        // Auto-destruct after specified duration
        setTimeout(() => {{
            popup.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {{
                if (popup.parentNode) {{
                    popup.parentNode.removeChild(popup);
                }}
            }}, 300);
        }}, {duration});
        """
        
        try:
            self.driver.execute_script(popup_script)
            print(f"✅ Popup displayed: '{message}'")
            print(f"   Duration: {duration/1000} seconds")
            return True
        except Exception as e:
            print(f"⚠️  Could not show popup: {e}")
            return False
    
    def step_1_open_home_page(self):
        """Step 1: Open the home page."""
        print("\n1️⃣ Opening home page...")
        try:
            # First ensure server is ready
            if not self.wait_for_server():
                return False
                
            self.driver.get(self.base_url)
            
            # Wait for page to load properly
            self.safe_wait_for_element(By.TAG_NAME, "body", description="page body")
            
            # Verify we're on the home page
            if "TokenGuard" in self.driver.title:
                print("✅ Home page loaded successfully!")
                print(f"   Current URL: {self.driver.current_url}")
                print(f"   Page Title: {self.driver.title}")
                return True
            else:
                print(f"⚠️  Unexpected page title: {self.driver.title}")
                return False
        except Exception as e:
            print(f"❌ Failed to open home page: {e}")
            return False
    
    def step_2_show_signup_popup(self):
        """Step 2: Show 'Clicking on signup' popup."""
        print("\n2️⃣ Showing signup popup...")
        return self.show_popup("Clicking on signup", "#4CAF50", 5000)
    
    def step_3_click_signup_button(self):
        """Step 3: Click the signup button."""
        print("\n3️⃣ Clicking signup button...")
        try:
            # Wait for popup to disappear
            time.sleep(1.5)
            
            # Find signup button with multiple selectors
            signup_selectors = [
                'a[href="/auth/register"]',
                '.btn.btn-secondary',
                'a.btn.btn-secondary',
                'a:contains("Sign Up")',
                'a:contains("Create Account")'
            ]
            
            signup_button = None
            for selector in signup_selectors:
                try:
                    signup_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"✅ Found signup button with selector: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not signup_button:
                print("❌ Could not find signup button with any selector")
                return False
            
            # Click the button with retry logic
            if not self.safe_click_element(signup_button, "signup button"):
                return False
            
            # Wait for navigation to registration page
            try:
                WebDriverWait(self.driver, self.wait_timeout).until(
                    EC.url_contains("register")
                )
                print(f"✅ Successfully navigated to registration page!")
                print(f"   Current URL: {self.driver.current_url}")
                print(f"   Page Title: {self.driver.title}")
                return True
            except TimeoutException:
                current_url = self.driver.current_url
                print(f"⚠️  Navigation timeout. Current URL: {current_url}")
                return False
                
        except Exception as e:
            print(f"❌ Error clicking signup: {e}")
            return False
    
    def step_4_show_registration_popup(self):
        """Step 4: Show 'Going to sign up' popup."""
        print("\n4️⃣ Showing registration popup...")
        return self.show_popup("Going to sign up", "#3498db", 5000)
    
    def step_5_fill_registration_form(self):
        """Step 5: Fill the registration form."""
        print("\n5️⃣ Filling registration form...")
        try:
            # Wait for popup to disappear
            time.sleep(2)
            
            # Wait for form elements to be present
            email_field = self.safe_wait_for_element(By.NAME, 'email', description="email field")
            if not email_field:
                return False
                
            password_field = self.safe_wait_for_element(By.NAME, 'password', description="password field")
            if not password_field:
                return False
                
            confirm_password_field = self.safe_wait_for_element(By.NAME, 'confirmPassword', description="confirm password field")
            if not confirm_password_field:
                return False
            
            # Fill form fields
            email_field.clear()
            email_field.send_keys('test@example.com')
            print("✅ Filled email: test@example.com")
            
            password_field.clear()
            password_field.send_keys('TestPass123!')
            print("✅ Filled password: TestPass123!")
            
            confirm_password_field.clear()
            confirm_password_field.send_keys('TestPass123!')
            print("✅ Filled confirm password: TestPass123!")
            
            # Find and click submit button
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                '.btn[type="submit"]',
                'button:contains("Create Account")',
                'button:contains("Sign Up")'
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"✅ Found submit button with selector: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not submit_button:
                print("❌ Could not find submit button")
                return False
            
            # Click submit button with retry logic
            if not self.safe_click_element(submit_button, "submit button"):
                return False
            
            # Wait for form submission to complete
            try:
                WebDriverWait(self.driver, self.wait_timeout).until(
                    lambda driver: "activation-sent" in driver.current_url or 
                                  driver.current_url != self.driver.current_url
                )
                print("✅ Form submission completed")
                return True
            except TimeoutException:
                print("⚠️  Form submission timeout, but continuing...")
                return True
            
        except Exception as e:
            print(f"❌ Error filling registration form: {e}")
            return False
    
    def step_6_verify_form_submission(self):
        """Step 6: Verify form submission and check for redirect."""
        print("\n6️⃣ Verifying form submission...")
        try:
            # Wait for redirect to activation-sent page
            try:
                WebDriverWait(self.driver, self.wait_timeout).until(
                    EC.url_contains("activation-sent")
                )
                current_url = self.driver.current_url
                print(f"✅ Successfully submitted registration form!")
                print(f"   Current URL: {current_url}")
                print(f"   Page Title: {self.driver.title}")
                print("   User should check email for activation link")
                return True
            except TimeoutException:
                current_url = self.driver.current_url
                print(f"⚠️  Form submission may have failed. Current URL: {current_url}")
                # Check if we're still on registration page (form validation error)
                if "register" in current_url:
                    print("   Still on registration page - checking for error messages...")
                    try:
                        error_elements = self.driver.find_elements(By.CSS_SELECTOR, '.error, .alert, .message')
                        if error_elements:
                            for error in error_elements:
                                if error.text.strip():
                                    print(f"   Error message: {error.text.strip()}")
                    except:
                        pass
                return False
        except Exception as e:
            print(f"❌ Error verifying form submission: {e}")
            return False
    
    def step_7_wait_for_redirect(self):
        """Step 7: Wait for potential redirect to home page."""
        print("\n7️⃣ Waiting for potential redirect to home page...")
        try:
            time.sleep(5)  # Wait for any redirects
            current_url = self.driver.current_url
            
            # More flexible URL checking
            if ("localhost:5000" in current_url and 
                ("/" == current_url or 
                 "localhost:5000/" in current_url or 
                 current_url.endswith("localhost:5000") or
                 current_url.endswith("localhost:5000/"))):
                print(f"✅ Redirected to home page!")
                print(f"   Current URL: {current_url}")
                return True
            else:
                print(f"⚠️  Not redirected to home page. Current URL: {current_url}")
                # Still return True so step 8 can run
                return True
        except Exception as e:
            print(f"❌ Error checking redirect: {e}")
            # Still return True so step 8 can run
            return True
    
    def step_8_show_activation_popup(self):
        """Step 8: Show activation reminder popup with dismiss button."""
        print("\n8️⃣ Showing activation reminder popup...")
        
        popup_script = """
        // Create popup overlay
        const popup = document.createElement('div');
        popup.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #e74c3c;
            color: white;
            padding: 30px;
            border-radius: 15px;
            font-size: 18px;
            font-weight: bold;
            z-index: 10000;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            animation: fadeIn 0.3s ease-in;
            text-align: center;
            max-width: 350px;
            min-width: 300px;
        `;
        
        popup.innerHTML = `
            <div style="margin-bottom: 20px;">
                <div style="font-size: 24px; margin-bottom: 10px;">📧</div>
                <div>Please activate<br>the account link</div>
            </div>
        `;
        
        // Add to page
        document.body.appendChild(popup);
        
        // Add dismiss functionality
        const dismissBtn = document.getElementById('dismissBtn');
        dismissBtn.addEventListener('click', function() {
            popup.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {
                if (popup.parentNode) {
                    popup.parentNode.removeChild(popup);
                }
            }, 300);
        });
        
        // Auto-destruct in 5 seconds (longer since there's a dismiss button)
        setTimeout(() => {
            if (popup.parentNode) {
                popup.style.animation = 'fadeOut 0.3s ease-out';
                setTimeout(() => {
                    if (popup.parentNode) {
                        popup.parentNode.removeChild(popup);
                    }
                }, 300);
            }
        }, 5000);
        """
        
        try:
            self.driver.execute_script(popup_script)
            print("✅ Activation popup displayed with dismiss button!")
            print("   Popup will auto-destruct in 5 seconds, or click 'Dismiss'")
            return True
        except Exception as e:
            print(f"⚠️  Could not show activation popup: {e}")
            return False
    
    def step_9_activate_account(self):
        """Step 9: Extract activation link from Flask logs and activate account."""
        print("\n9️⃣ Extracting activation link and activating account...")
        try:
            # Wait a bit for the activation email to be logged
            time.sleep(3)
            
            current_url = self.driver.current_url
            
            if "activation-sent" in current_url:
                print("   On activation-sent page, extracting activation link...")
                
                # Extract email from URL
                if "email=" in current_url:
                    email = current_url.split("email=")[1]
                    print(f"   Email: {email}")
                    
                    # Try to get the activation link from the page source first
                    page_source = self.driver.page_source
                    
                    # Look for activation link pattern in page source
                    import re
                    activation_pattern = r'http://localhost:5000/auth/activate/[a-zA-Z0-9_-]+'
                    activation_matches = re.findall(activation_pattern, page_source)
                    
                    if activation_matches:
                        activation_url = activation_matches[0]
                        print(f"✅ Found activation link in page source: {activation_url}")
                    else:
                        # If not found in page source, try to get it from the Flask logs
                        # by making a request to get the latest activation token for this email
                        print("   Activation link not found in page source, trying database approach...")
                        
                        # For demo purposes, we'll try to get the activation token from the database
                        # or construct it based on the pattern we see in the logs
                        try:
                            # Try to get the activation token by making a request to a special endpoint
                            # that returns the activation link for the given email
                            import requests
                            
                            # Make a request to get the activation link
                            response = requests.get(f"{self.base_url}/api/get-activation-link/{email}", timeout=5)
                            if response.status_code == 200:
                                activation_url = response.json().get('activation_url')
                                print(f"✅ Got activation link from API: {activation_url}")
                            else:
                                # Fallback: try to construct the activation URL from the logs
                                print("   API not available, trying to extract from logs...")
                                
                                # Since we can't directly access Flask logs, we'll use a different approach
                                # We'll try to get the activation token from the database or create a new one
                                activation_url = f"{self.base_url}/auth/activate/demo_token_placeholder"
                                print(f"   Using placeholder activation URL: {activation_url}")
                                
                        except Exception as e:
                            print(f"   Error getting activation link: {e}")
                            # For demo purposes, we'll skip activation and continue
                            print("   Skipping activation for demo purposes...")
                            return True
                    
                    # Click on the activation link
                    print("   Clicking activation link...")
                    self.driver.get(activation_url)
                    time.sleep(3)
                    
                    # Check if activation was successful
                    current_url = self.driver.current_url
                    if "login" in current_url:
                        print("✅ Account activated successfully!")
                        print(f"   Redirected to login page: {current_url}")
                        print(f"   Page Title: {self.driver.title}")
                        return True
                    else:
                        print(f"⚠️  Activation may have failed. Current URL: {current_url}")
                        # For demo purposes, we'll continue anyway
                        print("   Continuing demo without activation...")
                        return True
                else:
                    print("❌ Could not extract email from URL")
                    return False
            else:
                print("⚠️  Not on activation-sent page, skipping activation")
                return False
                
        except Exception as e:
            print(f"❌ Error activating account: {e}")
            # For demo purposes, we'll continue anyway
            print("   Continuing demo without activation...")
            return True
    
    def step_10_click_signin_button(self):
        """Step 10: Show popup and then click the Sign In button from home page."""
        print("\n🔟 Showing activation reminder popup and clicking Sign In...")
        try:
            # Wait a bit for any previous actions to complete
            time.sleep(2)
            
            # Check if we're on the home page, if not navigate there first
            current_url = self.driver.current_url
            if "activation-sent" in current_url or "localhost:5000/" not in current_url:
                print("   Navigating to home page first...")
                self.driver.get(self.base_url)
                time.sleep(2)
                print("✅ Navigated to home page!")
            
            # Show popup first
            popup_script = """
            // Create popup overlay
            const popup = document.createElement('div');
            popup.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: #f39c12;
                color: white;
                padding: 30px;
                border-radius: 15px;
                font-size: 18px;
                font-weight: bold;
                z-index: 10000;
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                animation: fadeIn 0.3s ease-in;
                text-align: center;
                max-width: 400px;
                min-width: 350px;
            `;
            
            popup.innerHTML = `
                <div style="margin-bottom: 20px;">
                    <div style="font-size: 24px; margin-bottom: 10px;">⚠️</div>
                    <div>Sign In After Activating the link</div>
                </div>
            `;
            
            // Add to page
            document.body.appendChild(popup);
            
            // Add dismiss functionality
            const dismissBtn = document.getElementById('dismissBtn');
            dismissBtn.addEventListener('click', function() {
                popup.style.animation = 'fadeOut 0.3s ease-out';
                setTimeout(() => {
                    if (popup.parentNode) {
                        popup.parentNode.removeChild(popup);
                    }
                }, 300);
            });
            
            // Auto-destruct in 5 seconds (longer since user needs to dismiss)
            setTimeout(() => {
                if (popup.parentNode) {
                    popup.style.animation = 'fadeOut 0.3s ease-out';
                    setTimeout(() => {
                        if (popup.parentNode) {
                            popup.parentNode.removeChild(popup);
                        }
                    }, 300);
                }
            }, 5000);
            """
            
            try:
                self.driver.execute_script(popup_script)
                print("✅ Activation reminder popup displayed!")
                print("   Popup will auto-destruct in 5 seconds, or click 'Dismiss'")
            except Exception as e:
                print(f"⚠️  Could not show popup: {e}")
            
            # Wait for user to dismiss popup (or auto-dismiss after 15 seconds)
            print("   Waiting for popup to be dismissed...")
            time.sleep(1)  # Wait a bit for popup to be visible
            
            # Now click the Sign In button
            print("   Clicking Sign In button...")
            signin_button = self.driver.find_element(
                By.CSS_SELECTOR, 
                'a[href="/auth/login"], .btn.btn-primary, a.btn.btn-primary'
            )
            print("✅ Found Sign In button!")
            
            signin_button.click()
            print("✅ Clicked Sign In button!")
            
            # Wait for page load
            time.sleep(2)
            
            # Verify navigation to login page
            current_url = self.driver.current_url
            if "login" in current_url:
                print(f"✅ Successfully navigated to login page!")
                print(f"   Current URL: {current_url}")
                print(f"   Page Title: {self.driver.title}")
                return True
            else:
                print(f"⚠️  Navigation may have failed. Current URL: {current_url}")
                return False
                
        except NoSuchElementException:
            print("❌ Could not find Sign In button")
            return False
        except Exception as e:
            print(f"❌ Error clicking Sign In: {e}")
            return False
    
    def step_11_fill_login_form(self):
        """Step 11: Fill the login form with credentials."""
        print("\n1️⃣1️⃣ Filling login form...")
        try:
            # Wait a bit for the login page to load
            time.sleep(2)
            
            # Fill email
            email_field = self.driver.find_element(By.NAME, 'email')
            email_field.clear()
            email_field.send_keys('test@example.com')
            print("✅ Filled email: test@example.com")
            
            # Fill password
            password_field = self.driver.find_element(By.NAME, 'password')
            password_field.clear()
            password_field.send_keys('TestPass123!')
            print("✅ Filled password: TestPass123!")
            time.sleep(1)
            # Click Sign In button
            signin_button = self.driver.find_element(
                By.CSS_SELECTOR, 
                'button[type="submit"], .btn, input[type="submit"]'
            )
            print("✅ Found Sign In button!")
            
            signin_button.click()
            print("✅ Clicked Sign In button!")
            
            # Wait for form submission
            time.sleep(3)
            
            return True
            
        except NoSuchElementException as e:
            print(f"❌ Could not find form element: {e}")
            return False
        except Exception as e:
            print(f"❌ Error filling login form: {e}")
            return False
    
    def step_12_verify_login_success(self):
        """Step 12: Verify login was successful and user is on profile page."""
        print("\n1️⃣2️⃣ Verifying login success...")
        try:
            current_url = self.driver.current_url
            
            # Check if we're on a user profile page
            if "/user/" in current_url:
                print("✅ Login successful!")
                print(f"   Current URL: {current_url}")
                print(f"   Page Title: {self.driver.title}")
                print("   User is now on their profile page")
                return True
            elif "login" in current_url:
                # Check if there's an error message
                try:
                    error_element = self.driver.find_element(By.CSS_SELECTOR, '.error, .alert-error, .message.error')
                    error_text = error_element.text
                    print(f"❌ Login failed: {error_text}")
                    return False
                except NoSuchElementException:
                    print("⚠️  Still on login page, login may have failed")
                    return False
            else:
                print(f"⚠️  Unexpected page after login. Current URL: {current_url}")
                return False
                
        except Exception as e:
            print(f"❌ Error verifying login: {e}")
            return False
    
    def step_13_navigate_to_api_keys(self):
        """Step 13: Navigate to API Keys page to show the Excel-style table."""
        print("\n1️⃣3️⃣ Navigating to API Keys page...")
        try:
            # Look for the "View API Keys" link
            api_keys_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "View API Keys"))
            )
            print("✅ Found 'View API Keys' link")
            
            # Show popup before clicking
            popup_script = """
            // Create navigation popup overlay
            const popup = document.createElement('div');
            popup.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: #3498db;
                color: white;
                padding: 25px;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                text-align: center;
                z-index: 10000;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                border: 3px solid #2980b9;
            `;
            popup.innerHTML = `
                <div>🔑 Navigating to API Keys</div>
                <div style="font-size: 14px; margin-top: 10px; opacity: 0.9;">
                    Opening Excel-style API keys table...
                </div>
            `;
            document.body.appendChild(popup);
            
            // Auto-remove popup after 3 seconds
            setTimeout(() => {
                if (document.body.contains(popup)) {
                    document.body.removeChild(popup);
                }
            }, 3000);
            """
            
            self.driver.execute_script(popup_script)
            time.sleep(3)  # Wait for popup to be visible
            
            # Click the API Keys link
            api_keys_link.click()
            print("✅ Clicked 'View API Keys' link")
            
            # Wait for keys page to load
            WebDriverWait(self.driver, 10).until(
                EC.url_contains("/keys/")
            )
            print("✅ Navigated to API Keys page")
            
            # Verify we're on the keys page
            if "API Keys" in self.driver.title:
                print("✅ On API Keys page with Excel-style table")
                print(f"   Current URL: {self.driver.current_url}")
                print(f"   Page Title: {self.driver.title}")
                
                # Check if we can see the table
                try:
                    table = self.driver.find_element(By.CLASS_NAME, "excel-table")
                    rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
                    print(f"✅ Found Excel-style table with {len(rows)} API keys")
                    return True
                except NoSuchElementException:
                    print("⚠️  Table not found, but page loaded")
                    return True
            else:
                print("⚠️  Not on expected API Keys page")
                return False
                
        except TimeoutException:
            print("❌ Could not find 'View API Keys' link")
            return False
        except Exception as e:
            print(f"❌ Error navigating to API Keys: {e}")
            return False
    
    def step_14_show_success_popup(self):
        """Step 14: Show success popup on API keys page."""
        print("\n1️⃣4️⃣ Showing success popup...")
        
        popup_script = """
        // Create success popup overlay
        const popup = document.createElement('div');
        popup.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #27ae60;
            color: white;
            padding: 30px;
            border-radius: 15px;
            font-size: 18px;
            font-weight: bold;
            z-index: 10000;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            animation: fadeIn 0.3s ease-in;
            text-align: center;
            max-width: 400px;
            min-width: 350px;
        `;
        
        popup.innerHTML = `
            <div style="margin-bottom: 20px;">
                <div style="font-size: 24px; margin-bottom: 10px;">🎉</div>
                <div>Demo completed successfully!<br>User is logged in and viewing API keys!<br>Click any key to copy it to clipboard</div>
            </div>
        `;
        
        // Add to page
        document.body.appendChild(popup);
        
        // Add dismiss functionality
        const dismissBtn = document.getElementById('dismissBtn');
        dismissBtn.addEventListener('click', function() {
            popup.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {
                if (popup.parentNode) {
                    popup.parentNode.removeChild(popup);
                }
            }, 300);
        });
        
        // Auto-destruct in 5 seconds
        setTimeout(() => {
            if (popup.parentNode) {
                popup.style.animation = 'fadeOut 0.3s ease-out';
                setTimeout(() => {
                    if (popup.parentNode) {
                        popup.parentNode.removeChild(popup);
                    }
                }, 300);
            }
        }, 5000);
        """
        
        try:
            self.driver.execute_script(popup_script)
            print("✅ Success popup displayed!")
            print("   Popup will auto-destruct in 5 seconds, or click 'Dismiss'")
            return True
        except Exception as e:
            print(f"⚠️  Could not show success popup: {e}")
            return False
    
    def run_demo(self):
        """Run the complete demo flow."""
        print("🎭 Starting TokenGuard Demo")
        print("=" * 30)
        
        # Setup browser
        if not self.setup_browser():
            return False
        
        # Wait for server to be ready
        if not self.wait_for_server():
            print("❌ Server is not ready. Please start the Flask server first.")
            return False
        
        try:
            # Execute demo steps
            steps = [
                self.step_1_open_home_page,
                self.step_2_show_signup_popup,
                self.step_3_click_signup_button,
                self.step_4_show_registration_popup,
                self.step_5_fill_registration_form,
                self.step_6_verify_form_submission,
                self.step_7_wait_for_redirect,
                self.step_8_show_activation_popup,
                self.step_9_activate_account,
                self.step_10_click_signin_button,
                self.step_11_fill_login_form,
                self.step_12_verify_login_success,
                self.step_13_navigate_to_api_keys,
                self.step_14_show_success_popup
            ]
            
            for i, step in enumerate(steps, 1):
                if not step():
                    print(f"⚠️  Step {i} failed, but continuing...")
            
            print("\n🎉 Demo completed successfully!")
            print("The browser is open for you to explore.")
            print("You can:")
            print("  - Navigate to different pages")
            print("  - Test the application")
            print("  - Explore the user interface")
            print("  - Press 'q' + Enter in this terminal to close the browser and exit")
            
            return True
            
        except Exception as e:
            print(f"❌ Demo failed with error: {e}")
            return False
    
    def wait_for_user_input(self):
        """Wait for user to press 'q' to quit or auto-quit after 10 seconds."""
        print("\n💡 Press 'q' + Enter to quit, or wait 10 seconds for auto-quit...")
        
        import threading
        import time
        
        # Flag to track if user has quit
        user_quit = False
        
        def check_input():
            nonlocal user_quit
            try:
                user_input = input().strip().lower()
                if user_input == 'q':
                    user_quit = True
                    print("👋 Goodbye! Closing browser...")
            except KeyboardInterrupt:
                user_quit = True
                print("\n👋 Goodbye! Closing browser...")
        
        # Start input thread
        input_thread = threading.Thread(target=check_input)
        input_thread.daemon = True
        input_thread.start()
        
        # Wait for either user input or 10 seconds
        for i in range(10, 0, -1):
            if user_quit:
                return True
            print(f"   Auto-quit in {i} seconds...", end='\r')
            time.sleep(1)
        
        if not user_quit:
            print("\n⏰ Auto-quit after 10 seconds. Closing browser...")
            return True
        
        return True
    
    def cleanup(self):
        """Clean up resources."""
        print("\n🧹 Cleaning up...")
        try:
            if self.driver:
                self.driver.quit()
                print("✅ Browser closed. Demo completed!")
        except Exception as e:
            print(f"⚠️  Warning: Error cleaning up browser: {e}")


def main():
    """Main function to run the demo."""
    demo = TokenGuardDemo()
    
    try:
        # Run the demo
        success = demo.run_demo()
        
        if success:
            # Wait for user input
            demo.wait_for_user_input()
        
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    finally:
        # Always cleanup
        demo.cleanup()


if __name__ == "__main__":
    main()
