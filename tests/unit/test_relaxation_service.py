"""
Unit tests for RelaxationService
"""

import pytest
from services.relaxation_service import RelaxationService


def test_get_relaxation_guide_default():
    """Test getting default relaxation guide"""
    service = RelaxationService()
    result = service.get_relaxation_guide()
    
    assert "guide" in result
    assert "timestamp" in result
    assert "title" in result["guide"]
    assert "steps" in result["guide"]
    assert isinstance(result["guide"]["steps"], list)
    assert len(result["guide"]["steps"]) > 0


def test_get_relaxation_guide_specific():
    """Test getting specific relaxation guide"""
    service = RelaxationService()
    result = service.get_relaxation_guide(guide_type="Quick Calm")
    
    assert "guide" in result
    assert result["guide"]["title"] == "Quick Calm"
    assert "steps" in result["guide"]


def test_get_relaxation_guide_japanese():
    """Test getting relaxation guide in Japanese"""
    service = RelaxationService()
    result = service.get_relaxation_guide(language="ja")
    
    assert "guide" in result
    assert "title" in result["guide"]
    # Title should be in Japanese
    assert result["guide"]["title"] in ["クイックカーム", "ボディスキャン"]


def test_get_breathing_exercise_default():
    """Test getting default breathing exercise"""
    service = RelaxationService()
    result = service.get_breathing_exercise()
    
    assert "exercise" in result
    assert "timestamp" in result
    assert "name" in result["exercise"]
    assert "steps" in result["exercise"]
    assert isinstance(result["exercise"]["steps"], list)
    assert len(result["exercise"]["steps"]) > 0


def test_get_breathing_exercise_specific():
    """Test getting specific breathing exercise"""
    service = RelaxationService()
    result = service.get_breathing_exercise(exercise_type="4-7-8 Breathing")
    
    assert "exercise" in result
    assert result["exercise"]["name"] == "4-7-8 Breathing"
    assert "steps" in result["exercise"]


def test_get_quick_calm_tips():
    """Test getting quick calm tips"""
    service = RelaxationService()
    result = service.get_quick_calm_tips(count=3)
    
    assert "tips" in result
    assert "timestamp" in result
    assert isinstance(result["tips"], list)
    assert len(result["tips"]) == 3
    assert all(isinstance(tip, str) for tip in result["tips"])


def test_get_quick_calm_tips_max():
    """Test getting maximum number of tips"""
    service = RelaxationService()
    result = service.get_quick_calm_tips(count=20)  # More than available
    
    assert "tips" in result
    assert len(result["tips"]) <= 10  # Should not exceed available tips


def test_get_safety_tips():
    """Test getting safety tips"""
    service = RelaxationService()
    result = service.get_safety_tips()
    
    assert "tips" in result
    assert "timestamp" in result
    assert "emergency_message" in result
    assert isinstance(result["tips"], list)
    assert len(result["tips"]) > 0
    assert all(isinstance(tip, str) for tip in result["tips"])


def test_get_safety_tips_japanese():
    """Test getting safety tips in Japanese"""
    service = RelaxationService()
    result = service.get_safety_tips(language="ja")
    
    assert "tips" in result
    assert "emergency_message" in result
    # Emergency message should be in Japanese
    assert "緊急" in result["emergency_message"] or "医療" in result["emergency_message"]


def test_get_relaxation_guide_invalid_language():
    """Test getting relaxation guide with invalid language (should default to English)"""
    service = RelaxationService()
    result = service.get_relaxation_guide(language="invalid")
    
    assert "guide" in result
    # Should default to English
    assert result["guide"]["title"] in ["Quick Calm", "Body Scan"]


def test_get_breathing_exercise_invalid_language():
    """Test getting breathing exercise with invalid language (should default to English)"""
    service = RelaxationService()
    result = service.get_breathing_exercise(language="invalid")
    
    assert "exercise" in result
    # Should default to English
    assert result["exercise"]["name"] in ["4-7-8 Breathing", "Box Breathing", "Deep Belly Breathing"]
