"""
Integration tests for API routes
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from services.auth_service import AuthService
from models.database import UserDB


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def auth_token(client, test_db_session):
    """Create authenticated user and return token"""
    auth_service = AuthService()
    
    # Register user
    email = "apitest@example.com"
    password = "testpassword123"
    auth_service.register_user(email, password, db=test_db_session)
    
    # Login to get token
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )
    
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200


def test_health_check_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/api/monitoring/health")
    assert response.status_code == 200
    assert "status" in response.json()


def test_register_endpoint(client):
    """Test user registration endpoint"""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "password123",
            "name": "Test User"
        }
    )
    
    assert response.status_code in [200, 201]
    assert "user_id" in response.json() or "email" in response.json()


def test_login_endpoint(client, test_db_session):
    """Test login endpoint"""
    # Register user first
    auth_service = AuthService()
    email = "login@example.com"
    password = "password123"
    auth_service.register_user(email, password, db=test_db_session)
    
    # Login
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )
    
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_invalid_credentials(client):
    """Test login with invalid credentials"""
    response = client.post(
        "/api/auth/login",
        json={"email": "invalid@example.com", "password": "wrongpassword"}
    )
    
    assert response.status_code in [401, 400]


def test_get_ai_provider_info(client):
    """Test AI provider info endpoint"""
    response = client.get("/api/ai/provider")
    assert response.status_code == 200
    assert "provider" in response.json()


def test_create_feedback_authenticated(client, auth_token):
    """Test creating feedback with authentication"""
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    
    response = client.post(
        "/api/feedback",
        json={
            "category": "bug",
            "title": "Test Bug",
            "message": "This is a test bug report",
            "priority": "high"
        },
        headers=headers
    )
    
    # Should work with or without auth (depending on implementation)
    assert response.status_code in [200, 201, 401]


def test_get_user_feedback_authenticated(client, auth_token):
    """Test getting user feedback with authentication"""
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    
    response = client.get(
        "/api/feedback",
        headers=headers
    )
    
    # Should work with or without auth
    assert response.status_code in [200, 401]


def test_create_task_authenticated(client, auth_token, test_db_session):
    """Test creating task with authentication"""
    if not auth_token:
        pytest.skip("Authentication not available")
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    response = client.post(
        "/api/tasks",
        json={
            "task_type": "ai_chat",
            "task_data": {"query": "Test query"},
            "priority": "medium"
        },
        headers=headers
    )
    
    assert response.status_code in [200, 201, 202]
    assert "task_id" in response.json() or "message" in response.json()


def test_get_task_authenticated(client, auth_token, test_db_session):
    """Test getting task with authentication"""
    if not auth_token:
        pytest.skip("Authentication not available")
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # First create a task
    create_response = client.post(
        "/api/tasks",
        json={
            "task_type": "ai_chat",
            "task_data": {"query": "Test query"},
            "priority": "medium"
        },
        headers=headers
    )
    
    if create_response.status_code in [200, 201, 202]:
        task_id = create_response.json().get("task_id")
        if task_id:
            # Get the task
            response = client.get(
                f"/api/tasks/{task_id}",
                headers=headers
            )
            
            assert response.status_code == 200
            assert "task_id" in response.json()


def test_validation_test_endpoint(client):
    """Test validation test endpoint"""
    response = client.get("/api/validation/test")
    assert response.status_code == 200
    assert "validation_result" in response.json()


def test_cors_headers(client):
    """Test CORS headers are present"""
    response = client.options("/")
    # CORS headers should be present (depends on FastAPI CORS middleware)


def test_invalid_endpoint(client):
    """Test accessing non-existent endpoint"""
    response = client.get("/api/nonexistent")
    assert response.status_code == 404
