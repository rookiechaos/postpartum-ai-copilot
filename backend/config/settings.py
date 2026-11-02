"""
Application Settings - Centralized configuration management
"""

from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict, SecretStr, ValidationInfo, field_validator
from typing import Optional, List
from functools import lru_cache
from urllib.parse import urlsplit
from utils.runtime_paths import PROJECT_ROOT
import warnings


class Settings(BaseSettings):
    """Application settings with validation"""
    
    model_config = ConfigDict(
        env_file=(PROJECT_ROOT / "backend/.env", PROJECT_ROOT / "do-not-upload/local/backend.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )
    
    # Application
    app_name: str = "Postpartum AI Copilot"
    app_version: str = "2.0.0"
    debug: bool = Field(default=False, validation_alias="DEBUG")
    test_mode: bool = Field(default=False, validation_alias="TEST_MODE")
    
    # API Configuration
    api_base_url: str = Field(default="http://localhost:8000", validation_alias="API_BASE_URL")
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:5173", validation_alias="CORS_ORIGINS")
    
    # Database Configuration
    database_url: str = Field(
        default=f"sqlite:///{PROJECT_ROOT / 'do-not-upload/data/postpartum.db'}",
        validation_alias="DATABASE_URL",
    )
    
    # AI Provider Configuration
    ai_provider: str = Field(default="openai", validation_alias="AI_PROVIDER")

    @field_validator("ai_provider")
    @classmethod
    def validate_ai_provider(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"openai", "claude", "gemini", "codex", "claude_code", "agent"}:
            raise ValueError("Select a supported AI provider")
        return value

    openai_api_key: Optional[str] = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", validation_alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-ada-002", validation_alias="OPENAI_EMBEDDING_MODEL")
    anthropic_api_key: Optional[str] = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    claude_model: str = Field(default="claude-3-5-sonnet-20241022", validation_alias="CLAUDE_MODEL")
    google_api_key: Optional[str] = Field(default=None, validation_alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-pro", validation_alias="GEMINI_MODEL")

    # Isolated text runners for optional family AI providers and operator calls.
    agent_enabled: bool = Field(default=False, validation_alias="AGENT_ENABLED")
    agent_codex_runner_url: Optional[str] = Field(default=None, max_length=2048, validation_alias="AGENT_CODEX_RUNNER_URL")
    agent_codex_runner_token: Optional[SecretStr] = Field(default=None, min_length=32, max_length=4096, validation_alias="AGENT_CODEX_RUNNER_TOKEN")
    agent_claude_code_runner_url: Optional[str] = Field(default=None, max_length=2048, validation_alias="AGENT_CLAUDE_CODE_RUNNER_URL")
    agent_claude_code_runner_token: Optional[SecretStr] = Field(default=None, min_length=32, max_length=4096, validation_alias="AGENT_CLAUDE_CODE_RUNNER_TOKEN")
    agent_custom_runner_url: Optional[str] = Field(default=None, max_length=2048, validation_alias="AGENT_CUSTOM_RUNNER_URL")
    agent_custom_runner_token: Optional[SecretStr] = Field(default=None, min_length=32, max_length=4096, validation_alias="AGENT_CUSTOM_RUNNER_TOKEN")
    agent_timeout_seconds: int = Field(default=120, ge=5, le=300, validation_alias="AGENT_TIMEOUT_SECONDS")
    agent_max_output_chars: int = Field(default=20000, ge=100, le=20000, validation_alias="AGENT_MAX_OUTPUT_CHARS")

    @field_validator(
        "agent_codex_runner_url", "agent_claude_code_runner_url", "agent_custom_runner_url",
        "agent_codex_runner_token", "agent_claude_code_runner_token", "agent_custom_runner_token",
        mode="before",
    )
    @classmethod
    def empty_agent_configuration(cls, value):
        return None if value == "" else value

    @field_validator("agent_codex_runner_token", "agent_claude_code_runner_token", "agent_custom_runner_token")
    @classmethod
    def validate_agent_runner_token(cls, value: Optional[SecretStr]) -> Optional[SecretStr]:
        if value is not None and any(not 33 <= ord(character) <= 126 for character in value.get_secret_value()):
            raise ValueError("Agent runner tokens must use printable ASCII without spaces")
        return value

    @field_validator("agent_codex_runner_url", "agent_claude_code_runner_url", "agent_custom_runner_url")
    @classmethod
    def validate_agent_runner_url(cls, value: Optional[str], info: ValidationInfo) -> Optional[str]:
        if value is None:
            return None
        try:
            parts = urlsplit(value)
            _ = parts.port
        except ValueError:
            raise ValueError("Use a valid fixed agent runner endpoint") from None
        loopback_development = info.data.get("debug") is True and parts.scheme == "http" and parts.hostname in {"localhost", "127.0.0.1", "::1"}
        if (not parts.hostname or (parts.scheme != "https" and not loopback_development)
            or parts.username is not None or parts.password is not None or parts.query or parts.fragment
            or any(character.isspace() or ord(character) < 32 for character in value)):
            raise ValueError("Agent runner endpoints require HTTPS without credentials, query or fragment")
        return value
    
    # JWT Authentication
    jwt_secret_key: str = Field(
        default="change-me-in-production-please-use-strong-random-key",
        validation_alias="JWT_SECRET_KEY",
        min_length=32,
        description="JWT secret key (must be at least 32 characters and not use default value in production)"
    )
    algorithm: str = Field(default="HS256", validation_alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=1440, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")  # 24 hours
    refresh_token_expire_days: int = Field(default=30, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")
    
    @field_validator('jwt_secret_key', mode='after')
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        """Validate JWT secret key for production environment"""
        default_secret = "change-me-in-production-please-use-strong-random-key"
        
        # Check if using default value
        if v == default_secret:
            # This will be checked again in get_settings() after all fields are initialized
            # to check debug mode
            warnings.warn(
                "Using default JWT_SECRET_KEY. This is insecure for production. "
                "Please set a strong random secret key.",
                UserWarning
            )
        
        # Length check is already done by Field(min_length=32)
        return v
    
    # Application Settings
    async_mode: bool = Field(default=True, validation_alias="ASYNC_MODE")
    rag_enabled: bool = Field(default=True, validation_alias="RAG_ENABLED")
    vector_db_path: str = Field(default="do-not-upload/vector_db", validation_alias="VECTOR_DB_PATH")
    
    # Worker Configuration
    num_workers: int = Field(default=2, validation_alias="NUM_WORKERS")
    task_queue_workers: int = Field(default=2, validation_alias="TASK_QUEUE_WORKERS")
    
    # Redis (optional)
    redis_url: Optional[str] = Field(default=None, validation_alias="REDIS_URL")
    
    # Payment Webhook Configuration
    stripe_webhook_secret: Optional[str] = Field(default=None, validation_alias="STRIPE_WEBHOOK_SECRET")
    paypal_webhook_id: Optional[str] = Field(default=None, validation_alias="PAYPAL_WEBHOOK_ID")
    paypal_client_id: Optional[str] = Field(default=None, validation_alias="PAYPAL_CLIENT_ID")
    paypal_client_secret: Optional[str] = Field(default=None, validation_alias="PAYPAL_CLIENT_SECRET")
    paypal_environment: str = Field(default="sandbox", pattern="^(sandbox|live)$", validation_alias="PAYPAL_ENVIRONMENT")
    
    # Admin Configuration
    admin_user_ids: Optional[str] = Field(default=None, validation_alias="ADMIN_USER_IDS")
    # Separate from system administration; only manages this pilot's public directory.
    institution_user_ids: Optional[str] = Field(default=None, validation_alias="INSTITUTION_USER_IDS")
    
    # Logging
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_dir: str = Field(default="do-not-upload/logs", validation_alias="LOG_DIR")
    
    # File Upload Configuration
    max_upload_size_mb: int = Field(default=10, validation_alias="MAX_UPLOAD_SIZE_MB")
    
    # NSFW Detection Configuration
    nsfw_detection_enabled: bool = Field(default=True, validation_alias="NSFW_DETECTION_ENABLED")
    nsfw_detection_strict: bool = Field(default=False, validation_alias="NSFW_DETECTION_STRICT")
    
    @field_validator('cors_origins', mode='after')
    @classmethod
    def validate_cors_origins(cls, v: str) -> str:
        """Validate CORS origins configuration format"""
        # Basic format validation - production check will be done in get_cors_origins_list
        if v:
            origins = [origin.strip() for origin in v.split(",") if origin.strip()]
            for origin in origins:
                # Allow wildcard only in development (will be checked in get_cors_origins_list)
                if origin != '*' and not (origin.startswith("http://") or origin.startswith("https://")):
                    raise ValueError(
                        f"Invalid CORS origin format: {origin}. "
                        "Must start with http:// or https://, or be '*' for development only"
                    )
        
        return v
    
    def get_cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list with validation"""
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        
        # Additional runtime check for production
        if not self.debug:
            if '*' in self.cors_origins:
                raise ValueError("CORS wildcard '*' not allowed in production")
        
        return origins
    
    def get_ai_api_key(self) -> Optional[str]:
        """Get API key for current AI provider"""
        if self.ai_provider.lower() == "openai":
            return self.openai_api_key
        elif self.ai_provider.lower() == "claude":
            return self.anthropic_api_key
        elif self.ai_provider.lower() == "gemini":
            return self.google_api_key
        return None
    
    def is_ai_configured(self) -> bool:
        """Check if AI provider is configured"""
        provider = self.ai_provider.lower()
        if provider in {"codex", "claude_code", "agent"}:
            prefix = "agent_custom" if provider == "agent" else f"agent_{provider}"
            return bool(self.agent_enabled and getattr(self, f"{prefix}_runner_url") and
                        getattr(self, f"{prefix}_runner_token"))
        return self.get_ai_api_key() is not None


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    settings = Settings()
    
    # Post-initialization validation for production
    if not settings.debug and not settings.test_mode:
        # Check JWT secret key
        default_secret = "change-me-in-production-please-use-strong-random-key"
        if settings.jwt_secret_key == default_secret:
            raise ValueError(
                "JWT_SECRET_KEY must be changed from default value in production. "
                "Please set a strong random secret key (at least 32 characters)."
            )
        
        # Log security warnings
        from services.logging_service import logger
        logger.log_info(
            "Production mode: Security validations enabled",
            context={"jwt_secret_length": len(settings.jwt_secret_key)}
        )
    
    return settings
