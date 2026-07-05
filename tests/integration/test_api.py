#!/usr/bin/env python3
"""
Postpartum AI Copilot - API test script
Usage: python test_api.py
"""

import requests
import json
import time
from datetime import datetime

def test_task_api():
    print("\n=== Task API ===")
    
    # First register and login
    register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": f"test_task_{int(time.time())}@test.com",
        "password": "test123456"
    })
    
    if register_response.status_code not in [201, 400]:  # 400 if user exists
        print_test("Task API - register", False, f"Status code: {register_response.status_code}")
        return False
    
    email = register_response.json().get("email") or f"test_task_{int(time.time())}@test.com"
    
    login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "password": "test123456"
    })
    
    if login_response.status_code != 200:
        print_test("Task API - login", False, f"Status code: {login_response.status_code}")
        return False
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create task
    task_response = requests.post(
        f"{BASE_URL}/api/tasks",
        headers=headers,
        json={
            "task_type": "ai_chat",
            "task_data": {"query": "Test task", "language": "en"},
            "priority": "medium"
        }
    )
    
    if task_response.status_code != 202:
        print_test("Task API - create task", False, f"Status code: {task_response.status_code}")
        return False
    
    task_id = task_response.json()["task_id"]
    print_test("Task API - create task", True, f"Task ID: {task_id}")
    
    # Get task status
    status_response = requests.get(
        f"{BASE_URL}/api/tasks/{task_id}",
        headers=headers
    )
    
    if status_response.status_code != 200:
        print_test("Task API - get task status", False, f"Status code: {status_response.status_code}")
        return False
    
    print_test("Task API - get task status", True, f"Status: {status_response.json()['status']}")
    return True

BASE_URL = "http:localhost:8000"
TEST_USER_ID = f"test_user_{int(time.time())}"

def print_test(name, passed, message=""):
    status = "✓" if passed else "✗"
    color = "\033[92m" if passed else "\033[91m"
    reset = "\033[0m"
    print(f"{color}{status}{reset} {name}")
    if message:
        print(f"    {message}")

def test_health_check():
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_test("Health check", True, f"Status: {data.get('status')}")
            return True
        else:
            print_test("Health check", False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_test("Health check", False, f"Error: {str(e)}")
        return False

def test_chat():
    try:
        payload = {
            "query": "My baby is 2 weeks old and won't sleep. Is this normal?",
            "user_id": TEST_USER_ID
        }
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json=payload,
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if "response" in data:
                print_test("Chat API", True, f"Response length: {len(data['response'])} chars")
                return True
        print_test("Chat API", False, f"Status code: {response.status_code}")
        return False
    except Exception as e:
        print_test("Chat API", False, f"Error: {str(e)}")
        return False

def test_add_tracking():
    try:
        payload = {
            "user_id": TEST_USER_ID,
            "entry_type": "feeding",
            "feeding_type": "breast",
            "duration_minutes": 20,
            "amount_ml": 50,
            "timestamp": datetime.utcnow().isoformat()
        }
        response = requests.post(
            f"{BASE_URL}/api/tracking",
            json=payload,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "id" in data:
                print_test("Add tracking entry", True, f"Entry ID: {data['id']}")
                return data['id']
        print_test("Add tracking entry", False, f"Status code: {response.status_code}")
        return None
    except Exception as e:
        print_test("Add tracking entry", False, f"Error: {str(e)}")
        return None

def test_get_tracking():
    try:
        response = requests.get(
            f"{BASE_URL}/api/tracking/{TEST_USER_ID}?days=7",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print_test("Get tracking entries", True, f"Entry count: {len(data)}")
            return True
        print_test("Get tracking entries", False, f"Status code: {response.status_code}")
        return False
    except Exception as e:
        print_test("Get tracking entries", False, f"Error: {str(e)}")
        return False

def test_tracking_summary():
    try:
        response = requests.get(
            f"{BASE_URL}/api/tracking/{TEST_USER_ID}/summary?days=7",
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if "patterns" in data:
                print_test("Get summary", True, f"Pattern count: {len(data.get('patterns', []))}")
                return True
        print_test("Get summary", False, f"Status code: {response.status_code}")
        return False
    except Exception as e:
        print_test("Get summary", False, f"Error: {str(e)}")
        return False

def test_emotional_checkin():
    try:
        payload = {
            "user_id": TEST_USER_ID,
            "overwhelmed_level": 5,
            "anxiety_level": 4,
            "support_level": 6,
            "notes": "Feeling okay today"
        }
        response = requests.post(
            f"{BASE_URL}/api/emotional-checkin",
            json=payload,
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if "assessment" in data:
                risk_level = data.get("risk_level", "unknown")
                print_test("Emotional check-in", True, f"Risk level: {risk_level}")
                return True
        print_test("Emotional check-in", False, f"Status code: {response.status_code}")
        return False
    except Exception as e:
        print_test("Emotional check-in", False, f"Error: {str(e)}")
        return False

def test_crisis_mode():
    try:
        payload = {
            "user_id": TEST_USER_ID,
            "query": "Baby won't stop crying and I'm exhausted",
            "urgency": "high"
        }
        response = requests.post(
            f"{BASE_URL}/api/crisis",
            json=payload,
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if "response" in data:
                print_test("Crisis mode", True, f"Response length: {len(data['response'])} chars")
                return True
        print_test("Crisis mode", False, f"Status code: {response.status_code}")
        return False
    except Exception as e:
        print_test("Crisis mode", False, f"Error: {str(e)}")
        return False

def test_user_context():
    try:
        payload = {
            "user_id": TEST_USER_ID,
            "context": {
                "babyName": "Test Baby",
                "babyAge": "1-2 weeks",
                "birthType": "vaginal",
                "feedingType": "breast"
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/user/context",
            json=payload,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "message" in data:
                print_test("User context", True, "Context updated successfully")
                return True
        print_test("User context", False, f"Status code: {response.status_code}")
        return False
    except Exception as e:
        print_test("User context", False, f"Error: {str(e)}")
        return False

def test_task_api():
    print("\n=== Task API ===")
    
    # First register and login
    register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": f"test_task_{int(time.time())}@test.com",
        "password": "test123456"
    })
    
    if register_response.status_code not in [201, 400]:  # 400 if user exists
        print(f"❌ Registration failed: {register_response.status_code}")
        return False
    
    email = register_response.json().get("email") or f"test_task_{int(time.time())}@test.com"
    
    login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "password": "test123456"
    })
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return False
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create task
    task_response = requests.post(
        f"{BASE_URL}/api/tasks",
        headers=headers,
        json={
            "task_type": "ai_chat",
            "task_data": {"query": "Test task", "language": "en"},
            "priority": "medium"
        }
    )
    
    if task_response.status_code != 202:
        print(f"❌ Create task failed: {task_response.status_code}")
        return False
    
    task_id = task_response.json()["task_id"]
    print(f"✅ Task created: {task_id}")
    
    # Get task status
    status_response = requests.get(
        f"{BASE_URL}/api/tasks/{task_id}",
        headers=headers
    )
    
    if status_response.status_code != 200:
        print(f"❌ Get task status failed: {status_response.status_code}")
        return False
    
    print(f"✅ Get task status succeeded: {status_response.json()['status']}")
    
    # Get user tasks
    tasks_response = requests.get(
        f"{BASE_URL}/api/tasks",
        headers=headers
    )
    
    if tasks_response.status_code != 200:
        print(f"❌ Get user task listFAILED: {tasks_response.status_code}")
        return False
    
    print(f"✅ Get user task list succeeded: {len(tasks_response.json())} task(s)")
    
    return True


def main():
    print("\n" + "="*50)
    print("Postpartum AI Copilot - API Tests")
    print("="*50 + "\n")
    
    print(f"Test user ID: {TEST_USER_ID}\n")
    
    tests = [
        ("Health check", test_health_check),
        ("Chat API", test_chat),
        ("Add tracking entry", test_add_tracking),
        ("Get tracking entries", test_get_tracking),
        ("Get summary", test_tracking_summary),
        ("Emotional check-in", test_emotional_checkin),
        ("Crisis mode", test_crisis_mode),
        ("User context", test_user_context),
        ("Task API", test_task_api),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result is not False and result is not None))
        except Exception as e:
            print(f"✗ {name} - exception: {str(e)}")
            results.append((name, False))
        print()
    
    print("="*50)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"Test results: {passed}/{total} PASSED")
    print("="*50 + "\n")
    
    if passed == total:
        print("\033[92mAll tests passed!\033[0m\n")
        return 0
    else:
        print("\033[91mSome tests failed; see errors above\033[0m\n")
        return 1

if __name__ == "__main__":
    exit(main())

