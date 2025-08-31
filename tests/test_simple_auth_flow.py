"""
Simple Authentication Flow Test
Tests the core authentication issue: login redirect to profile page
"""
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


def test_login_to_profile_flow():
    """Test the core issue: login redirect to profile page"""
    
    # Set up Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("🚀 Starting authentication flow test...")
        
        # Step 1: Create a test user via API
        print("📝 Creating test user...")
        register_data = {
            'email': f'test{int(time.time())}@example.com',
            'password': 'TestPass123!'
        }
        
        response = requests.post('http://localhost:5000/auth/register', json=register_data)
        print(f"Registration response: {response.status_code}")
        
        if response.status_code == 201:
            user_data = response.json()
            user_id = user_data['user_id']
            print(f"✅ User created: {user_id}")
        else:
            print(f"❌ Registration failed: {response.text}")
            return False
        
        # Step 2: Login via API to get JWT token
        print("🔐 Logging in via API...")
        login_data = {
            'email': register_data['email'],
            'password': register_data['password']
        }
        
        response = requests.post('http://localhost:5000/auth/login', json=login_data)
        print(f"Login response: {response.status_code}")
        
        if response.status_code == 200:
            login_response = response.json()
            token = login_response.get('token')
            redirect_url = login_response.get('redirect_url')
            print(f"✅ Login successful!")
            print(f"   Token: {token[:20]}..." if token else "   No token")
            print(f"   Redirect URL: {redirect_url}")
        else:
            print(f"❌ Login failed: {response.text}")
            return False
        
        # Step 3: Test direct access to profile page with token
        print("🔒 Testing direct profile access with token...")
        headers = {'Authorization': f'Bearer {token}'} if token else {}
        response = requests.get(redirect_url, headers=headers)
        print(f"Profile access response: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Profile page accessible with token!")
            return True
        else:
            print(f"❌ Profile access failed: {response.text}")
            return False
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        driver.quit()


def test_browser_navigation_issue():
    """Test the specific browser navigation issue"""
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("\n🌐 Testing browser navigation issue...")
        
        # Step 1: Create and login user via API
        register_data = {
            'email': f'browser{int(time.time())}@example.com',
            'password': 'TestPass123!'
        }
        
        response = requests.post('http://localhost:5000/auth/register', json=register_data)
        if response.status_code != 201:
            print(f"❌ Registration failed: {response.text}")
            return False
        
        user_data = response.json()
        user_id = user_data['user_id']
        
        response = requests.post('http://localhost:5000/auth/login', json=register_data)
        if response.status_code != 200:
            print(f"❌ Login failed: {response.text}")
            return False
        
        login_response = response.json()
        redirect_url = login_response.get('redirect_url')
        
        print(f"✅ User ready: {user_id}")
        print(f"   Redirect URL: {redirect_url}")
        
        # Step 2: Navigate to profile page in browser
        print("🔍 Navigating to profile page in browser...")
        driver.get(redirect_url)
        time.sleep(3)
        
        current_url = driver.current_url
        page_source = driver.page_source.lower()
        
        print(f"   Current URL: {current_url}")
        print(f"   Page contains 'welcome': {'welcome' in page_source}")
        print(f"   Page contains 'authentication': {'authentication' in page_source}")
        print(f"   Page contains '401': {'401' in page_source}")
        
        # Check if we're on the profile page or getting auth error
        if 'welcome' in page_source or 'profile' in page_source:
            print("✅ Browser successfully loaded profile page!")
            return True
        elif 'authentication required' in page_source or '401' in page_source:
            print("❌ Browser getting authentication error - this is the issue!")
            return False
        else:
            print("❓ Unexpected page content")
            return False
        
    except Exception as e:
        print(f"❌ Browser test error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        driver.quit()


if __name__ == "__main__":
    print("🧪 Testing Authentication Flow\n")
    
    # Test 1: API-based authentication
    api_success = test_login_to_profile_flow()
    
    # Test 2: Browser navigation
    browser_success = test_browser_navigation_issue()
    
    print("\n" + "="*50)
    print("📊 TEST RESULTS:")
    print(f"   API Authentication: {'✅ PASS' if api_success else '❌ FAIL'}")
    print(f"   Browser Navigation: {'✅ PASS' if browser_success else '❌ FAIL'}")
    
    if api_success and browser_success:
        print("\n🎉 All tests PASSED! Authentication flow is working.")
    elif api_success and not browser_success:
        print("\n⚠️  API works but browser navigation fails - this is the issue we're fixing!")
    else:
        print("\n❌ Both tests failed - there's a deeper issue.")
    
    print("="*50)
