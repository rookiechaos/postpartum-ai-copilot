"""
Unit tests for AuthService
"""

import pytest
from services.auth_service import AuthService
from models.database import UserDB
from exceptions import AuthenticationError, ValidationError


@pytest.fixture
def auth_service():
    """Create AuthService instance"""
    return AuthService()


@pytest.mark.asyncio
async def test_register_user(test_db_session, auth_service):
    """Test user registration"""
    email = "test@example.com"
    password = "testpassword123"
    
    user = auth_service.register_user(
        email=email,
        password=password,
        db=test_db_session
    )
    
    assert user["email"] == email
    assert "user_id" in user
    assert "hashed_password" not in user  # Should not return password


@pytest.mark.asyncio
async def test_register_duplicate_email(test_db_session, auth_service):
    """Test registering with duplicate email"""
    email = "duplicate@example.com"
    password = "password123"
    
    # Register first time
    auth_service.register_user(email, password, db=test_db_session)
    
    # Try to register again
    with pytest.raises(ValidationError):
        auth_service.register_user(email, password, db=test_db_session)


@pytest.mark.asyncio
async def test_authenticate_user(test_db_session, auth_service):
    """Test user authentication"""
    email = "auth@example.com"
    password = "password123"
    
    # Register user
    auth_service.register_user(email, password, db=test_db_session)
    
    # Authenticate
    user = auth_service.authenticate_user(email, password, db=test_db_session)
    
    assert user is not None
    assert user.email == email


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(test_db_session, auth_service):
    """Test authentication with wrong password"""
    email = "wrongpass@example.com"
    password = "password123"
    
    # Register user
    auth_service.register_user(email, password, db=test_db_session)
    
    # Try to authenticate with wrong password
    user = auth_service.authenticate_user(email, "wrongpassword", db=test_db_session)
    
    assert user is None


@pytest.mark.asyncio
async def test_authenticate_user_not_found(test_db_session, auth_service):
    """Test authentication with non-existent user"""
    user = auth_service.authenticate_user(
        "nonexistent@example.com",
        "password",
        db=test_db_session
    )
    
    assert user is None


@pytest.mark.asyncio
async def test_get_user_by_id(test_db_session, auth_service):
    """Test getting user by ID"""
    email = "getbyid@example.com"
    password = "password123"
    
    # Register user
    registered = auth_service.register_user(email, password, db=test_db_session)
    user_id = registered["user_id"]
    
    # Get user by ID
    user = auth_service.get_user_by_id(user_id, db=test_db_session)
    
    assert user is not None
    assert user.user_id == user_id
    assert user.email == email


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(test_db_session, auth_service):
    """Test getting non-existent user by ID"""
    user = auth_service.get_user_by_id("non_existent_id", db=test_db_session)
    
    assert user is None


@pytest.mark.asyncio
async def test_get_user_by_email(test_db_session, auth_service):
    """Test getting user by email"""
    email = "getbyemail@example.com"
    password = "password123"
    
    # Register user
    auth_service.register_user(email, password, db=test_db_session)
    
    # Get user by email
    user = auth_service.get_user_by_email(email, db=test_db_session)
    
    assert user is not None
    assert user.email == email


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(test_db_session, auth_service):
    """Test getting non-existent user by email"""
    user = auth_service.get_user_by_email("nonexistent@example.com", db=test_db_session)
    
    assert user is None


@pytest.mark.asyncio
async def test_create_access_token(auth_service):
    """Test creating access token"""
    user_id = "test_user_123"
    
    token = auth_service.create_access_token(user_id)
    
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


@pytest.mark.asyncio
async def test_verify_token(auth_service):
    """Test verifying access token"""
    user_id = "test_user_123"
    
    # Create token
    token = auth_service.create_access_token(user_id)
    
    # Verify token
    token_data = auth_service.verify_token(token)
    
    assert token_data is not None
    assert token_data.user_id == user_id


@pytest.mark.asyncio
async def test_verify_invalid_token(auth_service):
    """Test verifying invalid token"""
    invalid_token = "invalid.token.here"
    
    token_data = auth_service.verify_token(invalid_token)
    
    assert token_data is None


@pytest.mark.asyncio
async def test_password_hashing(auth_service):
    """Test password hashing"""
    password = "testpassword123"
    
    hashed = auth_service.hash_password(password)
    
    assert hashed != password
    assert len(hashed) > 0
    
    # Verify password
    assert auth_service.verify_password(password, hashed) is True
    assert auth_service.verify_password("wrongpassword", hashed) is False
