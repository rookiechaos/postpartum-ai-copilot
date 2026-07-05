"""
Unit tests for Settings configuration
"""

import pytest
import os
from config.settings import Settings, get_settings


def test_settings_defaults():
    """Test default settings values"""
    settings = Settings()
    
    assert settings.app_name == "Postpartum AI Copilot"
    assert settings.app_version == "2.0.0"
    assert settings.debug is False
    assert settings.test_mode is False
    assert settings.async_mode is True
    assert settings.rag_enabled is True


def test_settings_from_env(monkeypatch):
    """Test loading settings from environment variables"""
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("TEST_MODE", "true")
    monkeypatch.setenv("ASYNC_MODE", "false")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    
    # Clear cache to force reload
    get_settings.cache_clear()
    
    settings = get_settings()
    
    assert settings.debug is True
    assert settings.test_mode is True
    assert settings.async_mode is False
    assert settings.database_url == "postgresql://test:test@localhost/test"
    
    # Restore cache
    get_settings.cache_clear()


def test_get_cors_origins_list():
    """Test CORS origins list parsing"""
    settings = Settings(cors_origins="http://localhost:3000,http://localhost:5173,https://example.com")
    
    origins = settings.get_cors_origins_list()
    
    assert len(origins) == 3
    assert "http://localhost:3000" in origins
    assert "http://localhost:5173" in origins
    assert "https://example.com" in origins


def test_get_ai_api_key_openai(monkeypatch):
    """Test getting OpenAI API key"""
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
    
    get_settings.cache_clear()
    settings = get_settings()
    
    api_key = settings.get_ai_api_key()
    
    assert api_key == "test_openai_key"
    
    get_settings.cache_clear()


def test_get_ai_api_key_claude(monkeypatch):
    """Test getting Claude API key"""
    monkeypatch.setenv("AI_PROVIDER", "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_claude_key")
    
    get_settings.cache_clear()
    settings = get_settings()
    
    api_key = settings.get_ai_api_key()
    
    assert api_key == "test_claude_key"
    
    get_settings.cache_clear()


def test_get_ai_api_key_gemini(monkeypatch):
    """Test getting Gemini API key"""
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "test_gemini_key")
    
    get_settings.cache_clear()
    settings = get_settings()
    
    api_key = settings.get_ai_api_key()
    
    assert api_key == "test_gemini_key"
    
    get_settings.cache_clear()


def test_is_ai_configured(monkeypatch):
    """Test checking if AI is configured"""
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    
    get_settings.cache_clear()
    settings = get_settings()
    
    assert settings.is_ai_configured() is True
    
    get_settings.cache_clear()


def test_is_ai_configured_not_configured(monkeypatch):
    """Test checking when AI is not configured"""
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    get_settings.cache_clear()
    settings = get_settings()
    
    assert settings.is_ai_configured() is False
    
    get_settings.cache_clear()


def test_settings_caching():
    """Test that settings are cached"""
    settings1 = get_settings()
    settings2 = get_settings()
    
    # Should be the same instance due to caching
    assert settings1 is settings2


def test_settings_model_config():
    """Test that model_config is properly set"""
    settings = Settings()
    
    assert hasattr(settings, "model_config")
    assert settings.model_config.get("env_file") == ".env"
    assert settings.model_config.get("case_sensitive") is False
