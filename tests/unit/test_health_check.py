"""
Unit tests for HealthCheckService
"""

import pytest
from services.health_check_service import HealthCheckService, get_health_check_service


@pytest.mark.asyncio
async def test_check_database(test_db_session):
    """Test database health check"""
    service = HealthCheckService()
    
    result = service.check_database(test_db_session)
    
    assert "status" in result
    assert "connected" in result
    assert result["connected"] is True
    assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_check_ai_provider():
    """Test AI provider health check"""
    service = HealthCheckService()
    
    result = service.check_ai_provider()
    
    assert "status" in result
    assert "provider" in result


@pytest.mark.asyncio
async def test_check_task_queue(test_db_session):
    """Test task queue health check"""
    service = HealthCheckService()
    
    result = service.check_task_queue(test_db_session)
    
    assert "status" in result
    assert "pending_tasks" in result
    assert "recent_stats" in result


@pytest.mark.asyncio
async def test_get_comprehensive_health(test_db_session):
    """Test comprehensive health check"""
    service = HealthCheckService()
    
    health = service.get_comprehensive_health(test_db_session)
    
    assert "status" in health
    assert "timestamp" in health
    assert "database" in health
    assert "ai_provider" in health
    assert "task_queue" in health


@pytest.mark.asyncio
async def test_get_health_check_service():
    """Test getting health check service instance"""
    service1 = get_health_check_service()
    service2 = get_health_check_service()
    
    # Should return same instance (singleton)
    assert service1 is service2


@pytest.mark.asyncio
async def test_check_database_error():
    """Test database check with invalid session"""
    service = HealthCheckService()
    
    # Create invalid session
    from sqlalchemy.orm import Session
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    invalid_engine = create_engine("sqlite:///./nonexistent.db")
    InvalidSession = sessionmaker(bind=invalid_engine)
    invalid_session = InvalidSession()
    invalid_session.close()
    
    result = service.check_database(invalid_session)
    
    assert result["status"] == "unhealthy"
    assert result["connected"] is False
