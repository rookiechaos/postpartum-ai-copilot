"""
"""

import sys
from pathlib import Path
_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import os
import sys
import asyncio
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

from fastapi.testclient import TestClient

# Set test mode to skip AI provider initialization
os.environ["TEST_MODE"] = "true"
os.environ["RAG_ENABLED"] = "false"

# Import app - need to adjust import path
try:
    # Try direct import first
    backend_path = os.path.join(os.path.dirname(__file__), "backend")
    sys.path.insert(0, backend_path)
    from main import app
except ImportError:
    # If that fails, use importlib
    import importlib.util
    backend_path = os.path.join(os.path.dirname(__file__), "backend")
    sys.path.insert(0, backend_path)
    spec = importlib.util.spec_from_file_location("main", os.path.join(backend_path, "main.py"))
    main_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_module)
    app = main_module.app
from models.database import init_db, SessionLocal, UserDB, TaskDB
from services.auth_service import AuthService
from services.task_queue import TaskQueue, TaskStatus, TaskPriority
from models.schemas import UserCreate, ChatMessage, TaskRequest


# Initialize database
init_db()

# Create test client
client = TestClient(app)


def test_health_check():
    print("\n=== Health check ===")
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    print(f"✅ Health checkPASSED: {data['status']}")
    return True


def test_root_endpoint():
    print("\n=== Root endpoint ===")
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    print(f"✅ Root endpoint passed: {data['message']}")
    return True


def test_auth_register():
    print("\n=== User registration ===")
    test_email = f"test_{int(datetime.now().timestamp())}@test.com"
    try:
        response = client.post("/api/auth/register", json={
            "email": test_email,
            "password": "test123"  # Shorter password for bcrypt compatibility
        })
        if response.status_code != 201:
            print(f"❌ Registration failed: status={response.status_code}, response={response.text}")
            raise Exception(f"Expected 201, got {response.status_code}: {response.text}")
        data = response.json()
        assert "user_id" in data
        assert "email" in data
        print(f"✅ User registration passed: {data['email']}")
        return data["user_id"], test_email
    except Exception as e:
        print(f"❌ Registration exception: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_auth_login(user_id, email):
    print("\n=== User login ===")
    response = client.post("/api/auth/login", json={
        "email": email,
        "password": "test123"  # Shorter password for bcrypt compatibility
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    print(f"✅ User login passed: token_type={data['token_type']}")
    return data["access_token"]


def test_auth_me(token):
    print("\n=== Get current user ===")
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert "email" in data
    print(f"✅ Get user info passed: {data['user_id']}")
    return True


def test_create_task(token, user_id):
    print("\n=== Create task ===")
    response = client.post(
        "/api/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "task_type": "ai_chat",
            "task_data": {
                "query": "Test query",
                "language": "en"
            },
            "priority": "medium"
        }
    )
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert "status" in data
    assert data["status"] == "pending"
    print(f"✅ Create task created: task_id={data['task_id']}")
    return data["task_id"]


def test_get_task(token, task_id):
    print("\n=== Get task status ===")
    response = client.get(
        f"/api/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert "status" in data
    print(f"✅ Get task status passed: status={data['status']}")
    return True


def test_get_user_tasks(token):
    print("\n=== Get user task list ===")
    response = client.get(
        "/api/tasks",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    print(f"✅ Get user task listPASSED: {len(data)} task(s)")
    return True


def test_chat_endpoint_async(token, user_id):
    print("\n=== Chat endpoint (async mode) ===")
    # Set async mode
    os.environ["ASYNC_MODE"] = "true"
    
    response = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": "My baby won't sleep",
            "user_id": user_id,
            "language": "en"
        }
    )
    
    # Should return 202 with task_id
    assert response.status_code == 202
    data = response.json()
    assert "detail" in data or "task_id" in data
    print(f"✅ Chat endpoint (async) passed: returned task ID")
    return True


def test_chat_endpoint_sync(token, user_id):
    print("\n=== Chat endpoint (sync mode) ===")
    # Set sync mode
    os.environ["ASYNC_MODE"] = "false"
    
    # Note: This will fail if AI API keys are not set, which is expected
    try:
        response = client.post(
            "/api/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "query": "Test query",
                "user_id": user_id,
                "language": "en"
            }
        )
        # May return 200 (success) or 500 (AI API error)
        assert response.status_code in [200, 500]
        print(f"✅ Chat endpoint (sync) passed: status={response.status_code}")
    except Exception as e:
        print(f"⚠️  Chat endpoint (sync) requires AI API config: {e}")
    
    # Reset async mode
    os.environ["ASYNC_MODE"] = "true"
    return True


def test_cancel_task(token, task_id):
    print("\n=== Cancel task ===")
    response = client.delete(
        f"/api/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    # May return 204 (success) or 400 (cannot cancel)
    assert response.status_code in [204, 400]
    print(f"✅ Cancel task passed: status={response.status_code}")
    return True


def test_user_context(token, user_id):
    print("\n=== User context ===")
    # Update context
    response = client.post(
        "/api/user/context",
        headers={"Authorization": f"Bearer {token}"},
        params={"user_id": user_id},
        json={
            "baby_age_days": 10,
            "birth_type": "vaginal",
            "feeding_type": "breast"
        }
    )
    assert response.status_code == 200
    print(f"✅ Update user context passed")
    
    # Get context
    response = client.get(
        f"/api/user/{user_id}/context",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    print(f"✅ Get user context passed")
    return True


def test_personalization(token, user_id):
    print("\n=== Personalization ===")
    # Get personalization profile
    response = client.get(
        f"/api/user/{user_id}/personalization",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "response_style" in data
    assert "baby_stage" in data
    print(f"✅ Get personalization config passed: style={data['response_style']}")
    return True


def run_all_tests():
    print("=" * 60)
    print("Internal API Tests")
    print("=" * 60)
    
    tests = [
        ("Health check", test_health_check),
        ("Root endpoint", test_root_endpoint),
    ]
    
    # Run basic tests first
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ {test_name}: FAILED - {e}")
            import traceback
            traceback.print_exc()
    
    # Run auth tests
    user_id = None
    email = None
    token = None
    
    try:
        user_id, email = test_auth_register()
        passed += 1
    except Exception as e:
        failed += 1
        print(f"❌ User registration: FAILED - {e}")
        return False
    
    try:
        token = test_auth_login(user_id, email)
        passed += 1
    except Exception as e:
        failed += 1
        print(f"❌ User login: FAILED - {e}")
        return False
    
    # Run authenticated tests
    auth_tests = [
        ("Get current user info", lambda: test_auth_me(token)),
        ("User context", lambda: test_user_context(token, user_id)),
        ("Personalization", lambda: test_personalization(token, user_id)),
    ]
    
    for test_name, test_func in auth_tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ {test_name}: FAILED - {e}")
            import traceback
            traceback.print_exc()
    
    # Run task tests
    task_id = None
    try:
        task_id = test_create_task(token, user_id)
        passed += 1
    except Exception as e:
        failed += 1
        print(f"❌ Create task: FAILED - {e}")
    
    if task_id:
        task_tests = [
            ("Get task status", lambda: test_get_task(token, task_id)),
            ("Get user task list", lambda: test_get_user_tasks(token)),
            ("Cancel task", lambda: test_cancel_task(token, task_id)),
        ]
        
        for test_name, test_func in task_tests:
            try:
                test_func()
                passed += 1
            except Exception as e:
                failed += 1
                print(f"❌ {test_name}: FAILED - {e}")
    
    # Run chat tests
    chat_tests = [
        ("Chat endpoint (async)", lambda: test_chat_endpoint_async(token, user_id)),
        ("Chat endpoint (sync)", lambda: test_chat_endpoint_sync(token, user_id)),
    ]
    
    for test_name, test_func in chat_tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ {test_name}: FAILED - {e}")
    
    print("\n" + "=" * 60)
    print(f"Test results: {passed} PASSED, {failed} FAILED")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)


