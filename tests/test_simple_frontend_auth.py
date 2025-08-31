"""
Simple Frontend Authentication Test
Tests the core authentication functionality without complex setup
"""
import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class TestSimpleFrontendAuth:
    """Simple frontend authentication tests"""
    
    def test_direct_profile_access_requires_auth(self, browser_driver):
        """Test that direct access to profile requires authentication"""
        print("🔒 Testing direct profile access without authentication...")
        
        # Try to access a user profile directly without authentication
        browser_driver.get('http://localhost:5000/user/test123')
        time.sleep(3)
        
        page_source = browser_driver.page_source.lower()
        current_url = browser_driver.current_url
        
        print(f"   Current URL: {current_url}")
        print(f"   Page contains 'authentication': {'authentication' in page_source}")
        print(f"   Page contains '401': {'401' in page_source}")
        
        # Should show authentication required or redirect to login
        assert any([
            'authentication required' in page_source,
            'unauthorized' in page_source,
            '401' in page_source,
            '/auth/login' in current_url
        ]), "Direct access to profile should require authentication"
        
        print("✅ Authentication required for direct profile access - PASSED")
    
    def test_login_page_loads_correctly(self, browser_driver):
        """Test that login page loads correctly"""
        print("🔐 Testing login page loads correctly...")
        
        browser_driver.get('http://localhost:5000/auth/login')
        time.sleep(2)
        
        page_source = browser_driver.page_source.lower()
        current_url = browser_driver.current_url
        
        print(f"   Current URL: {current_url}")
        print(f"   Page contains login form: {'form' in page_source}")
        print(f"   Page contains email input: {'email' in page_source}")
        print(f"   Page contains password input: {'password' in page_source}")
        
        # Should be on login page with form elements
        assert '/auth/login' in current_url
        assert 'form' in page_source
        assert 'email' in page_source
        assert 'password' in page_source
        
        print("✅ Login page loads correctly - PASSED")
    
    def test_register_page_loads_correctly(self, browser_driver):
        """Test that register page loads correctly"""
        print("📝 Testing register page loads correctly...")
        
        browser_driver.get('http://localhost:5000/auth/register')
        time.sleep(2)
        
        page_source = browser_driver.page_source.lower()
        current_url = browser_driver.current_url
        
        print(f"   Current URL: {current_url}")
        print(f"   Page contains register form: {'form' in page_source}")
        print(f"   Page contains email input: {'email' in page_source}")
        print(f"   Page contains password input: {'password' in page_source}")
        print(f"   Page contains confirm password: {'confirmpassword' in page_source}")
        
        # Should be on register page with form elements
        assert '/auth/register' in current_url
        assert 'form' in page_source
        assert 'email' in page_source
        assert 'password' in page_source
        assert 'confirmpassword' in page_source
        
        print("✅ Register page loads correctly - PASSED")
    
    def test_home_page_loads_correctly(self, browser_driver):
        """Test that home page loads correctly"""
        print("🏠 Testing home page loads correctly...")
        
        browser_driver.get('http://localhost:5000/')
        time.sleep(2)
        
        page_source = browser_driver.page_source.lower()
        current_url = browser_driver.current_url
        
        print(f"   Current URL: {current_url}")
        print(f"   Page contains welcome content: {'welcome' in page_source or 'home' in page_source}")
        print(f"   Page contains navigation: {'nav' in page_source or 'menu' in page_source}")
        
        # Should be on home page
        assert current_url == 'http://localhost:5000/' or current_url == 'http://localhost:5000'
        
        print("✅ Home page loads correctly - PASSED")
    
    def test_navigation_between_pages(self, browser_driver):
        """Test navigation between different pages"""
        print("�� Testing navigation between pages...")
        
        # Start at home page
        browser_driver.get('http://localhost:5000/')
        time.sleep(2)
        home_url = browser_driver.current_url
        print(f"   Started at: {home_url}")
        
        # Navigate to register page
        browser_driver.get('http://localhost:5000/auth/register')
        time.sleep(2)
        register_url = browser_driver.current_url
        print(f"   Navigated to: {register_url}")
        
        # Navigate to login page
        browser_driver.get('http://localhost:5000/auth/login')
        time.sleep(2)
        login_url = browser_driver.current_url
        print(f"   Navigated to: {login_url}")
        
        # Navigate back to home
        browser_driver.get('http://localhost:5000/')
        time.sleep(2)
        final_url = browser_driver.current_url
        print(f"   Back to: {final_url}")
        
        # Verify all navigations worked
        assert '/auth/register' in register_url
        assert '/auth/login' in login_url
        assert final_url == home_url or final_url == 'http://localhost:5000/'
        
        print("✅ Navigation between pages works correctly - PASSED")
    
    def test_form_elements_are_present(self, browser_driver):
        """Test that form elements are present and functional"""
        print("📋 Testing form elements are present...")
        
        # Test register form
        browser_driver.get('http://localhost:5000/auth/register')
        time.sleep(2)
        
        try:
            email_input = browser_driver.find_element(By.NAME, 'email')
            password_input = browser_driver.find_element(By.NAME, 'password')
            confirm_password_input = browser_driver.find_element(By.NAME, 'confirmPassword')
            submit_btn = browser_driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            
            print("   ✅ All register form elements found")
            
            # Test that inputs are editable
            email_input.send_keys('test@example.com')
            password_input.send_keys('TestPass123!')
            confirm_password_input.send_keys('TestPass123!')
            
            print("   ✅ Form inputs are editable")
            
        except Exception as e:
            print(f"   ❌ Register form elements not found: {e}")
            assert False, f"Register form elements missing: {e}"
        
        # Test login form
        browser_driver.get('http://localhost:5000/auth/login')
        time.sleep(2)
        
        try:
            email_input = browser_driver.find_element(By.NAME, 'email')
            password_input = browser_driver.find_element(By.NAME, 'password')
            submit_btn = browser_driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            
            print("   ✅ All login form elements found")
            
            # Test that inputs are editable
            email_input.send_keys('test@example.com')
            password_input.send_keys('TestPass123!')
            
            print("   ✅ Form inputs are editable")
            
        except Exception as e:
            print(f"   ❌ Login form elements not found: {e}")
            assert False, f"Login form elements missing: {e}"
        
        print("✅ Form elements are present and functional - PASSED")


if __name__ == "__main__":
    # Run the test directly
    test = TestSimpleFrontendAuth()
    
    # Manually set up the driver for direct execution
    # This section is no longer needed as browser_driver is now a fixture
    # chrome_options = Options()
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--no-sandbox")
    # chrome_options.add_argument("--disable-dev-shm-usage")
    # chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument("--window-size=1920,1080")
    
    # test.driver = webdriver.Chrome(options=chrome_options)
    # test.wait = WebDriverWait(test.driver, 10)
    
    try:
        print("🧪 Testing Simple Frontend Authentication\n")
        
        print("Testing direct profile access requires auth...")
        test.test_direct_profile_access_requires_auth()
        print("✅ Direct access test PASSED")
        
        print("\nTesting login page loads correctly...")
        test.test_login_page_loads_correctly()
        print("✅ Login page test PASSED")
        
        print("\nTesting register page loads correctly...")
        test.test_register_page_loads_correctly()
        print("✅ Register page test PASSED")
        
        print("\nTesting home page loads correctly...")
        test.test_home_page_loads_correctly()
        print("✅ Home page test PASSED")
        
        print("\nTesting navigation between pages...")
        test.test_navigation_between_pages()
        print("✅ Navigation test PASSED")
        
        print("\nTesting form elements are present...")
        test.test_form_elements_are_present()
        print("✅ Form elements test PASSED")
        
        print("\n🎉 All simple frontend auth tests PASSED!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # This section is no longer needed as browser_driver is now a fixture
        # test.driver.quit()
        pass
