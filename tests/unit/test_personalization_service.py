"""
Unit tests for PersonalizationService
"""

import pytest
from services.personalization_service import PersonalizationService
from exceptions import DatabaseError


@pytest.mark.asyncio
async def test_get_personalization_profile(test_db_session, mock_user_id):
    """Test getting personalization profile"""
    service = PersonalizationService()
    
    profile = await service.get_personalization_profile(mock_user_id, test_db_session)
    
    assert isinstance(profile, dict)
    assert "user_id" in profile
    assert "response_style" in profile
    assert "tone_preference" in profile
    assert profile["user_id"] == mock_user_id


@pytest.mark.asyncio
async def test_update_personalization_preferences(test_db_session, mock_user_id):
    """Test updating personalization preferences"""
    service = PersonalizationService()
    
    preferences = {
        "response_style": "detailed",
        "tone_preference": "warm",
        "detail_level": "comprehensive"
    }
    
    result = await service.update_personalization_preferences(
        mock_user_id,
        preferences,
        test_db_session
    )
    
    assert result["message"] == "Preferences updated successfully"
    assert result["preferences"]["response_style"] == "detailed"


@pytest.mark.asyncio
async def test_optimize_ai_prompt(test_db_session, mock_user_id):
    """Test optimizing AI prompt with personalization"""
    service = PersonalizationService()
    
    # Set preferences first
    preferences = {
        "response_style": "brief",
        "tone_preference": "professional"
    }
    await service.update_personalization_preferences(
        mock_user_id,
        preferences,
        test_db_session
    )
    
    base_prompt = "You are a helpful assistant."
    query = "How do I feed my baby?"
    
    optimized = await service.optimize_ai_prompt(
        mock_user_id,
        base_prompt,
        query,
        test_db_session
    )
    
    assert isinstance(optimized, str)
    assert len(optimized) > len(base_prompt)


@pytest.mark.asyncio
async def test_optimize_response_context(test_db_session, mock_user_id):
    """Test optimizing response context"""
    service = PersonalizationService()
    
    context = {
        "baby_age_days": 10,
        "feeding_type": "breast"
    }
    
    optimized = await service.optimize_response_context(
        mock_user_id,
        context,
        test_db_session
    )
    
    assert isinstance(optimized, dict)
    assert "baby_age_days" in optimized
    # Should have additional personalization data
    assert len(optimized) >= len(context)


@pytest.mark.asyncio
async def test_get_personalization_profile_new_user(test_db_session):
    """Test getting profile for new user (should create default)"""
    service = PersonalizationService()
    new_user_id = "new_user_123"
    
    profile = await service.get_personalization_profile(new_user_id, test_db_session)
    
    assert profile["user_id"] == new_user_id
    # Should have default values
    assert "response_style" in profile
    assert "tone_preference" in profile
