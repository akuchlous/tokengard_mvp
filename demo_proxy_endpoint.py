#!/usr/bin/env python3
"""
Demo script showing how to use the /api/proxy endpoint
"""

import requests
import json

def demo_proxy_endpoint():
    """Demonstrate the proxy endpoint functionality"""
    base_url = "http://localhost:5000"
    
    print("🔑 TokenGuard Proxy Endpoint Demo")
    print("=" * 40)
    
    # Test cases
    test_cases = [
        {
            "name": "Valid API Key",
            "payload": {
                "api_key": "tk-validkey123456789012345678901234",  # This would be a real key
                "text": "Hello, world! This is a test message."
            },
            "expected": "key_pass"
        },
        {
            "name": "Invalid API Key",
            "payload": {
                "api_key": "tk-invalidkey123456789012345678901",
                "text": "This should fail"
            },
            "expected": "key_error"
        },
        {
            "name": "Missing API Key",
            "payload": {
                "text": "No API key provided"
            },
            "expected": "key_error"
        },
        {
            "name": "Empty API Key",
            "payload": {
                "api_key": "",
                "text": "Empty key test"
            },
            "expected": "key_error"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}️⃣ Test: {test_case['name']}")
        print(f"   Payload: {json.dumps(test_case['payload'], indent=2)}")
        
        try:
            response = requests.post(
                f"{base_url}/api/proxy",
                json=test_case['payload'],
                headers={'Content-Type': 'application/json'}
            )
            
            print(f"   Status Code: {response.status_code}")
            
            if response.headers.get('content-type', '').startswith('application/json'):
                result = response.json()
                print(f"   Response: {json.dumps(result, indent=2)}")
                
                if result.get('status') == test_case['expected']:
                    print("   ✅ Expected result")
                else:
                    print(f"   ❌ Unexpected result (expected {test_case['expected']})")
            else:
                print(f"   Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("   ❌ Connection failed - make sure Flask server is running")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 40)
    print("📋 Usage Instructions:")
    print("1. Start the Flask server: python app.py")
    print("2. Register a new user and activate the account")
    print("3. Get a valid API key from the /keys/<user_id> page")
    print("4. Use the API key in your requests to /api/proxy")
    print("\n📝 Example curl command:")
    print('curl -X POST http://localhost:5000/api/proxy \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"api_key": "tk-your-actual-key-here", "text": "Hello World"}\'')

if __name__ == "__main__":
    demo_proxy_endpoint()
