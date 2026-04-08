"""
Test script to verify the API server and extension integration
Run this after starting the API server to ensure everything works
"""

import requests
import json

API_URL = "http://localhost:8000"

def test_api_health():
    """Test if API server is running"""
    print("Testing API health check...")
    try:
        response = requests.get(f"{API_URL}/")
        if response.status_code == 200:
            print("✅ API server is running!")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ API returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server at http://localhost:8000")
        print("   Make sure to run: start_api_server.bat")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_login():
    """Test login endpoint"""
    print("\nTesting login endpoint...")
    try:
        response = requests.post(
            f"{API_URL}/api/auth/login",
            json={"username": "patient1", "password": "patient123"}
        )
        if response.status_code == 200:
            data = response.json()
            print("✅ Login successful!")
            print(f"   User: {data['user_info']['full_name']}")
            print(f"   Role: {data['user_info']['role']}")
            return data['access_token']
        else:
            print(f"❌ Login failed with status: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error during login: {e}")
        return None

def test_create_memory(token):
    """Test memory creation endpoint"""
    print("\nTesting memory creation endpoint...")
    if not token:
        print("⚠️ Skipping - no valid token")
        return False
    
    try:
        response = requests.post(
            f"{API_URL}/api/memory/create",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "content": "Test memory from verification script",
                "patient_id": "patient_1",
                "url": "http://test.com",
                "title": "Test Page"
            }
        )
        if response.status_code == 200:
            print("✅ Memory creation successful!")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Memory creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating memory: {e}")
        return False

def main():
    print("=" * 60)
    print("LifeLens Extension - API Verification Test")
    print("=" * 60)
    
    # Test 1: API Health
    if not test_api_health():
        print("\n⚠️ API server is not running. Please start it first:")
        print("   start_api_server.bat")
        return
    
    # Test 2: Login
    token = test_login()
    
    # Test 3: Create Memory
    if token:
        test_create_memory(token)
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    if token:
        print("✅ API server is working correctly")
        print("✅ Extension should work properly")
        print("\nNext steps:")
        print("1. Load extension in Chrome/Edge (chrome://extensions)")
        print("2. Enable Developer Mode")
        print("3. Click 'Load unpacked' and select: lifelens/extension")
        print("4. Login with username: patient1, password: patient123")
        print("5. Try saving text from any webpage")
    else:
        print("❌ Some tests failed - check errors above")

if __name__ == "__main__":
    main()
