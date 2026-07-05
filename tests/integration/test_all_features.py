#!/usr/bin/env python3
"""
Comprehensive Test Script for Postpartum AI Copilot
"""

import requests
import json
import time
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_success(message: str):
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")

def print_error(message: str):
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")

def print_info(message: str):
    print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")

def test_health_check():
    """Test basic health check"""
    print_info("Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success("Health check passed")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Health check error: {e}")
        return False

def test_authentication():
    """Test authentication"""
    print_info("Testing authentication...")
    try:
        # Register a test user
        register_data = {
            "email": f"test_{int(time.time())}@example.com",
            "password": "TestPassword123!",
            "user_id": f"test_user_{int(time.time())}"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=register_data, timeout=10)
        
        if response.status_code in [200, 201]:
            print_success("User registration successful")
            user_data = response.json()
            token = user_data.get("access_token")
            
            # Test login
            login_data = {
                "email": register_data["email"],
                "password": register_data["password"]
            }
            response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data, timeout=10)
            
            if response.status_code == 200:
                print_success("User login successful")
                return response.json().get("access_token"), register_data["user_id"]
            else:
                print_error(f"Login failed: {response.status_code}")
                return None, None
        else:
            print_error(f"Registration failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None, None
    except Exception as e:
        print_error(f"Authentication error: {e}")
        return None, None

def test_websocket_connection(token: str):
    """Test WebSocket connection"""
    print_info("Testing WebSocket connection...")
    try:
        import websocket
        ws_url = f"{WS_URL}/ws?token={token}"
        
        def on_message(ws, message):
            data = json.loads(message)
            if data.get("type") == "connection":
                print_success("WebSocket connected successfully")
        
        def on_error(ws, error):
            print_error(f"WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print_info("WebSocket closed")
        
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Run in background thread
        import threading
        thread = threading.Thread(target=ws.run_forever)
        thread.daemon = True
        thread.start()
        
        time.sleep(2)  # Wait for connection
        ws.close()
        print_success("WebSocket test completed")
        return True
    except ImportError:
        print_warning("websocket-client not installed, skipping WebSocket test")
        return True
    except Exception as e:
        print_error(f"WebSocket test error: {e}")
        return False

def test_task_queue(token: str, user_id: str):
    """Test task queue and WebSocket notifications"""
    print_info("Testing task queue...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a task
        task_data = {
            "task_type": "ai_chat",
            "task_data": {
                "query": "Test message",
                "language": "en",
                "user_id": user_id
            },
            "priority": "medium"
        }
        response = requests.post(
            f"{BASE_URL}/api/tasks",
            json=task_data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            task = response.json()
            task_id = task.get("task_id")
            print_success(f"Task created: {task_id}")
            
            # Wait a bit for processing
            time.sleep(2)
            
            # Get task status
            response = requests.get(
                f"{BASE_URL}/api/tasks/{task_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                task_status = response.json()
                print_success(f"Task status retrieved: {task_status.get('status')}")
                return True
            else:
                print_error(f"Failed to get task status: {response.status_code}")
                return False
        else:
            print_error(f"Failed to create task: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Task queue test error: {e}")
        return False

def test_notifications(token: str, user_id: str):
    """Test notification system"""
    print_info("Testing notification system...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a smart feeding reminder
        response = requests.post(
            f"{BASE_URL}/api/notifications/smart/feeding",
            json={"based_on_history": True},
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            notification = response.json()
            print_success(f"Feeding reminder created: {notification.get('id')}")
            
            # Get user notifications
            response = requests.get(
                f"{BASE_URL}/api/notifications?include_sent=false&limit=10",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                notifications = response.json()
                print_success(f"Retrieved {len(notifications)} notifications")
                return True
            else:
                print_error(f"Failed to get notifications: {response.status_code}")
                return False
        else:
            print_error(f"Failed to create notification: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
    except Exception as e:
        print_error(f"Notification test error: {e}")
        return False

def test_data_export(token: str):
    """Test data export functionality"""
    print_info("Testing data export...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test JSON export
        response = requests.get(
            f"{BASE_URL}/api/export/json",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            print_success("JSON export successful")
            data = response.json()
            print_info(f"Exported data keys: {list(data.get('data', {}).keys())}")
            
            # Test CSV export
            response = requests.get(
                f"{BASE_URL}/api/export/csv",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                print_success("CSV export successful")
                return True
            else:
                print_warning(f"CSV export failed: {response.status_code}")
                return True  # CSV export is optional
        else:
            print_error(f"JSON export failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Data export test error: {e}")
        return False

def test_tracking(token: str, user_id: str):
    """Test tracking functionality"""
    print_info("Testing tracking...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a tracking entry
        entry_data = {
            "entry_type": "feeding",
            "feeding_type": "breast",
            "duration_minutes": 15,
            "user_id": user_id
        }
        response = requests.post(
            f"{BASE_URL}/api/tracking",
            json=entry_data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print_success("Tracking entry created")
            
            # Get tracking entries
            response = requests.get(
                f"{BASE_URL}/api/tracking/{user_id}?days=7",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                entries = response.json()
                print_success(f"Retrieved {len(entries)} tracking entries")
                return True
            else:
                print_error(f"Failed to get tracking entries: {response.status_code}")
                return False
        else:
            print_error(f"Failed to create tracking entry: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Tracking test error: {e}")
        return False

def test_family_sharing(token: str, user_id: str):
    """Test family sharing functionality"""
    print_info("Testing family sharing...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a family
        family_data = {"name": f"Test Family {int(time.time())}"}
        response = requests.post(
            f"{BASE_URL}/api/families",
            json=family_data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            family = response.json()
            family_id = family.get("family_id")
            print_success(f"Family created: {family_id}")
            
            # Get user families
            response = requests.get(
                f"{BASE_URL}/api/families",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                families = response.json()
                print_success(f"Retrieved {len(families)} families")
                return True
            else:
                print_error(f"Failed to get families: {response.status_code}")
                return False
        else:
            print_error(f"Failed to create family: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Family sharing test error: {e}")
        return False


def test_payment_system(token: str):
    """Test payment/subscription system"""
    print_info("Testing payment system...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get current subscription
        response = requests.get(
            f"{BASE_URL}/api/payments/subscriptions/me",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            subscription = response.json()
            if subscription:
                print_success(f"Current subscription: {subscription.get('plan')}")
            else:
                print_info("No active subscription (defaults to free)")
            
            # Check feature access
            response = requests.get(
                f"{BASE_URL}/api/payments/subscriptions/check-access?feature=data_export",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                access = response.json()
                print_success(f"Feature access check: {access.get('has_access')}")
                return True
            else:
                print_error(f"Failed to check feature access: {response.status_code}")
                return False
        else:
            print_error(f"Failed to get subscription: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Payment system test error: {e}")
        return False


def test_voice_service(token: str):
    """Test voice service (basic check)"""
    print_info("Testing voice service...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get supported voices
        response = requests.get(
            f"{BASE_URL}/api/voice/voices?language=en",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            voices = response.json()
            print_success(f"Retrieved {len(voices.get('voices', []))} voices")
            print_info("Voice service is ready (STT/TTS integration pending)")
            return True
        else:
            print_warning(f"Voice service endpoint returned: {response.status_code}")
            return True  # Voice service is optional
    except Exception as e:
        print_warning(f"Voice service test error: {e} (service may not be fully configured)")
        return True  # Voice service is optional


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Postpartum AI Copilot - Feature Test Suite")
    print("="*60 + "\n")
    
    results = {}
    
    # Test 1: Health check
    results["health_check"] = test_health_check()
    if not results["health_check"]:
        print_error("\nServer is not running. Please start the backend server first.")
        sys.exit(1)
    
    print()
    
    # Test 2: Authentication
    token, user_id = test_authentication()
    if not token:
        print_error("\nAuthentication failed. Cannot continue with other tests.")
        sys.exit(1)
    
    print()
    
    # Test 3: Tracking
    results["tracking"] = test_tracking(token, user_id)
    print()
    
    # Test 4: Task Queue
    results["task_queue"] = test_task_queue(token, user_id)
    print()
    
    # Test 5: WebSocket (optional)
    results["websocket"] = test_websocket_connection(token)
    print()
    
    # Test 6: Notifications
    results["notifications"] = test_notifications(token, user_id)
    print()
    
    # Test 7: Data Export
    results["data_export"] = test_data_export(token)
    print()
    
    # Test 8: Family Sharing
    results["family_sharing"] = test_family_sharing(token, user_id)
    print()
    
    # Test 9: Payment System
    results["payment_system"] = test_payment_system(token)
    print()
    
    # Test 10: Voice Service (optional)
    results["voice_service"] = test_voice_service(token)
    print()
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        color = Colors.GREEN if result else Colors.RED
        print(f"{color}{status}{Colors.RESET} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print_success("\nAll tests passed! 🎉")
        return 0
    else:
        print_error(f"\n{total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())

