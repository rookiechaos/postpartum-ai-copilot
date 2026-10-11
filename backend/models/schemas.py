"""
Pydantic schemas for API requests and responses
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class EntryType(str, Enum):
    FEEDING = "feeding"
    DIAPER = "diaper"
    SLEEP = "sleep"
    MOOD = "mood"
    PUMPING = "pumping"


class DiaperType(str, Enum):
    WET = "wet"
    DIRTY = "dirty"
    BOTH = "both"


class FeedingType(str, Enum):
    BREAST = "breast"
    FORMULA = "formula"
    MIXED = "mixed"
    PUMPED = "pumped"


class MoodLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    NEUTRAL = "neutral"
    GOOD = "good"
    VERY_GOOD = "very_good"


# Chat Models
class ChatMessage(BaseModel):
    """Chat message model with input validation"""
    
    @validator('query')
    def validate_query_length(cls, v):
        """Validate query length"""
        if not v:
            from exceptions import ValidationError
            raise ValidationError("Query cannot be empty")
        if len(v) > 5000:
            from exceptions import ValidationError
            raise ValidationError("Query is too long (maximum 5000 characters)")
        return v.strip()
    
    @validator('user_id')
    def validate_user_id(cls, v):
        """Validate user ID format"""
        if v:
            from services.security_validator import InputSanitizer
            if not InputSanitizer.validate_user_id(v):
                from exceptions import ValidationError
                raise ValidationError("Invalid user ID format")
        return v
    query: str = Field(..., description="User's question or message")
    user_id: Optional[str] = Field(
        default=None,
        description="Deprecated: user identity comes from JWT when authenticated",
    )
    conversation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    language: Optional[str] = Field(default="en", description="User's preferred language (en, ja)")


class ChatResponse(BaseModel):
    response: str
    suggestions: List[str] = []
    red_flags: List[str] = []
    timestamp: str
    validation: Optional[Dict[str, Any]] = None  # Validation metadata
    personalization_applied: Optional[bool] = Field(default=False, description="Whether personalization was applied")


# Tracking Models
class TrackingEntry(BaseModel):
    user_id: Optional[str] = Field(
        default=None,
        description="Deprecated: user identity comes from JWT when authenticated",
    )
    entry_type: EntryType
    timestamp: Optional[datetime] = None
    
    # Feeding specific
    feeding_type: Optional[FeedingType] = None
    duration_minutes: Optional[int] = None
    amount_ml: Optional[float] = None
    side: Optional[str] = None  # "left", "right", "both"
    
    # Diaper specific
    diaper_type: Optional[DiaperType] = None
    
    # Sleep specific
    sleep_duration_minutes: Optional[int] = None
    sleep_quality: Optional[str] = None  # "restless", "peaceful", "interrupted"
    
    # Mood specific
    mood_level: Optional[MoodLevel] = None
    mood_notes: Optional[str] = None
    
    # Pumping specific
    pumped_amount_ml: Optional[float] = None
    
    # Recovery tracking (postpartum)
    weight_kg: Optional[float] = Field(None, description="Mother's weight in kg")
    breast_condition: Optional[str] = Field(None, description="Breast condition: normal, engorged, blocked, etc.")
    recovery_notes: Optional[str] = Field(None, description="Recovery notes: pain, bleeding, etc.")
    
    # General
    notes: Optional[str] = None


class TrackingSummary(BaseModel):
    patterns: List[str]
    insights: List[str]
    recommendations: List[str]
    normalcy_checks: List[str]
    timestamp: str


class WeightEntry(BaseModel):
    """Weight tracking entry"""
    user_id: str
    weight_kg: float = Field(..., gt=0, description="Weight in kilograms")
    timestamp: Optional[datetime] = None
    notes: Optional[str] = None


class RecoveryEntry(BaseModel):
    """Recovery tracking entry"""
    user_id: str
    breast_condition: Optional[str] = Field(None, description="Breast condition: normal, engorged, blocked, painful, etc.")
    recovery_notes: Optional[str] = Field(None, description="Recovery notes: pain level, bleeding, discomfort, etc.")
    timestamp: Optional[datetime] = None


# Emotional Check-in Models
class EmotionalCheckIn(BaseModel):
    user_id: Optional[str] = Field(
        default=None,
        description="Deprecated: user identity comes from JWT when authenticated",
    )
    overwhelmed_level: int = Field(..., ge=1, le=10, description="1-10 scale")
    anxiety_level: int = Field(..., ge=1, le=10)
    support_level: int = Field(..., ge=1, le=10)
    notes: Optional[str] = None
    timestamp: Optional[datetime] = None


# Crisis Mode Models
class CrisisRequest(BaseModel):
    query: Optional[str] = None
    urgency: str = "high"  # "high", "medium", "low"
    language: Optional[str] = Field(default="en", description="User's preferred language")
    night_mode: bool = Field(default=False, description="Use shorter, gentler night-mode responses")


# Personalization Models
class PersonalizationPreferences(BaseModel):
    """User personalization preferences"""
    response_style: Optional[str] = Field(default=None, description="Response style: brief, detailed, balanced")
    tone_preference: Optional[str] = Field(default=None, description="Tone: warm, professional, casual")
    detail_level: Optional[str] = Field(default=None, description="Detail level: minimal, moderate, comprehensive")
    preferred_topics: Optional[List[str]] = Field(default=None, description="Topics user frequently asks about")
    avoided_topics: Optional[List[str]] = Field(default=None, description="Topics to avoid")
    customizations: Optional[Dict[str, Any]] = Field(default=None, description="Custom preferences")


class PersonalizationRequest(BaseModel):
    """Request to update personalization preferences"""
    user_id: str
    preferences: PersonalizationPreferences


# Task Models
class TaskStatus(str, Enum):
    """Task status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(str, Enum):
    """Task priority enum"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskRequest(BaseModel):
    """Request to create a task"""
    task_type: str = Field(..., description="Type of task (e.g., 'ai_chat', 'tracking_analysis')")
    task_data: Dict[str, Any] = Field(..., description="Task data")
    priority: Optional[TaskPriority] = Field(default=TaskPriority.MEDIUM, description="Task priority")
    timeout: Optional[int] = Field(default=None, description="Task timeout in seconds")

    @validator("task_type")
    def validate_task_type(cls, value: str) -> str:
        allowed = {"ai_chat", "tracking_analysis", "personalized_chat"}
        if value not in allowed:
            from exceptions import ValidationError
            raise ValidationError(
                f"Unsupported task type: {value}. Allowed: {', '.join(sorted(allowed))}"
            )
        return value


class TaskResponse(BaseModel):
    """Task response"""
    task_id: str
    task_type: str
    status: TaskStatus
    priority: TaskPriority
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    updated_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    user_id: str


# User Authentication Models
class UserBase(BaseModel):
    """Base user model"""
    email: str
    user_id: Optional[str] = None


class UserCreate(UserBase):
    """User creation model"""
    user_id: Optional[str] = Field(default=None, description="Deprecated and ignored: the server generates account IDs")
    password: str = Field(..., min_length=8, max_length=128, description="Password must be at least 8 characters")
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password strength"""
        from services.security_validator import PasswordValidator
        
        is_valid, error_msg = PasswordValidator.validate_password(v)
        if not is_valid:
            from exceptions import ValidationError
            raise ValidationError(error_msg)
        return v
    
    @validator('email')
    def validate_email_format(cls, v):
        """Validate email format"""
        from services.security_validator import InputSanitizer
        
        if not InputSanitizer.validate_email(v):
            from exceptions import ValidationError
            raise ValidationError("Invalid email format")
        return v.lower().strip()


class UserLogin(BaseModel):
    """User login model"""
    email: str = Field(..., max_length=255)
    password: str = Field(..., max_length=128)
    verification_token: Optional[str] = Field(default=None, min_length=6, max_length=64)
    
    @validator('email')
    def validate_email_format(cls, v):
        """Validate email format"""
        from services.security_validator import InputSanitizer
        
        if not InputSanitizer.validate_email(v):
            from exceptions import ValidationError
            raise ValidationError("Invalid email format")
        return v.lower().strip()


class User(UserBase):
    """User model"""
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Token response"""
    access_token: Optional[str] = None
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    requires_2fa: Optional[bool] = False


class RefreshTokenRequest(BaseModel):
    """Refresh token request body"""
    refresh_token: Optional[str] = None


class TokenData(BaseModel):
    """Token data"""
    user_id: Optional[str] = None
    email: Optional[str] = None
    mfa_version: Optional[str] = None
