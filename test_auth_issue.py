#!/usr/bin/env python3
"""
Test the exact authentication issue: after login, accessing /user/{user_id} gives 401
"""
import requests
import json

def test_auth_issue():
    """Test the authentication issue step by step"""
    
    base_url = "http://localhost:5000"
    
    print("🧪 Testing the exact authentication issue you reported...")
    print("=" * 60)
    
    # Step 1: Create a test user
    print("1️⃣ Creating test user...")
    register_data = {
        'email': 'demo@example.com',
        'password': 'DemoPass123!'
    }
    
    response = requests.post(f"{base_url}/auth/register", json=register_data)
    print(f"   Registration: {response.status_code}")
    
    if response.status_code == 201:
        user_data = response.json()
        user_id = user_data['user_id']
        print(f"   ✅ User created: {user_id}")
    else:
        print(f"   ❌ Registration failed: {response.text}")
        return
    
    # Step 2: Try to login (this will fail because account not activated)
    print("\n2️⃣ Attempting login (expected to fail due to activation)...")
    response = requests.post(f"{base_url}/auth/login", json=register_data)
    print(f"   Login: {response.status_code}")
    
    if response.status_code == 200:
        print("   ✅ Login successful!")
        login_data = response.json()
        token = login_data.get('token')
        redirect_url = login_data.get('redirect_url')
        print(f"   Token: {token[:20]}..." if token else "   No token")
        print(f"   Redirect URL: {redirect_url}")
        
        # Step 3: Test the exact issue - access profile page
        print("\n3️⃣ Testing the exact issue - accessing profile page...")
        print(f"   Trying to access: {redirect_url}")
        
        # First, try without token (this should fail)
        print("   Testing WITHOUT token (expected: 401)...")
        response = requests.get(redirect_url)
        print(f"   Response: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Got 401 as expected (no token)")
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
        
        # Now try WITH token (this should work)
        if token:
            print("   Testing WITH token (expected: 200)...")
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(redirect_url, headers=headers)
            print(f"   Response: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Got 200 with token - authentication working!")
            else:
                print(f"   ❌ Got {response.status_code} with token - this is the issue!")
                print(f"   Response: {response.text[:200]}...")
        else:
            print("   ❌ No token received from login!")
            
    else:
        print(f"   ❌ Login failed: {response.text}")
        print("\n   💡 This is expected because the account needs activation.")
        print("   The real issue happens AFTER login succeeds.")
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY:")
    print("   If you see '401' when accessing profile WITH token, that's the issue.")
    print("   If you see '200' with token, the authentication is working.")
    print("   The frontend JavaScript fix should handle this automatically.")

if __name__ == "__main__":
    test_auth_issue()
