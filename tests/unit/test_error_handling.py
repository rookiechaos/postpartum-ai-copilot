"""
Unit tests for error handling
"""

import pytest
from exceptions import (
    PostpartumException,
    AuthenticationError,
    ValidationError,
    AIServiceError,
    DatabaseError,
    TaskQueueError
)


def test_postpartum_exception():
    """Test base exception"""
    exc = PostpartumException("Test error", "TEST_ERROR", {"key": "value"})
    
    assert str(exc) == "Test error"
    assert exc.error_code == "TEST_ERROR"
    assert exc.details == {"key": "value"}


def test_authentication_error():
    """Test authentication error"""
    exc = AuthenticationError("Auth failed")
    
    assert exc.message == "Auth failed"
    assert exc.error_code == "AUTH_ERROR"


def test_validation_error():
    """Test validation error"""
    exc = ValidationError("Invalid input")
    
    assert exc.message == "Invalid input"
    assert exc.error_code == "VALIDATION_ERROR"


def test_ai_service_error():
    """Test AI service error"""
    exc = AIServiceError("AI service unavailable")
    
    assert exc.message == "AI service unavailable"
    assert exc.error_code == "AI_SERVICE_ERROR"


def test_database_error():
    """Test database error"""
    exc = DatabaseError("Connection failed")
    
    assert exc.message == "Connection failed"
    assert exc.error_code == "DATABASE_ERROR"


def test_task_queue_error():
    """Test task queue error"""
    exc = TaskQueueError("Task creation failed")
    
    assert exc.message == "Task creation failed"
    assert exc.error_code == "TASK_QUEUE_ERROR"
