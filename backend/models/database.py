"""
Database models and initialization
"""

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, JSON, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from pathlib import Path
from sqlalchemy.engine import make_url
from config.settings import get_settings
from utils.runtime_paths import PROJECT_ROOT

# Get database URL from settings
settings = get_settings()
DATABASE_URL = settings.database_url

# Configure engine based on database type
if DATABASE_URL.startswith("postgresql"):
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
else:
    # SQLite configuration
    sqlite_url = make_url(DATABASE_URL)
    database_path = sqlite_url.database
    if database_path and database_path != ":memory:":
        # Existing examples used a path relative to backend/. Normalize it for workers too.
        if database_path.startswith("../do-not-upload/"):
            database_path = database_path[3:]
        resolved_path = Path(database_path)
        if not resolved_path.is_absolute():
            resolved_path = PROJECT_ROOT / resolved_path
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        sqlite_url = sqlite_url.set(database=str(resolved_path))
    engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_engine():
    """Get database engine"""
    return engine


class TrackingEntryDB(Base):
    __tablename__ = "tracking_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    entry_type = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Feeding
    feeding_type = Column(String, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    amount_ml = Column(Float, nullable=True)
    side = Column(String, nullable=True)
    
    # Diaper
    diaper_type = Column(String, nullable=True)
    
    # Sleep
    sleep_duration_minutes = Column(Integer, nullable=True)
    sleep_quality = Column(String, nullable=True)
    
    # Mood
    mood_level = Column(String, nullable=True)
    mood_notes = Column(Text, nullable=True)
    
    # Pumping
    pumped_amount_ml = Column(Float, nullable=True)
    
    # Recovery tracking (postpartum)
    weight_kg = Column(Float, nullable=True)  # Mother's weight
    breast_condition = Column(String, nullable=True)  # normal, engorged, blocked, etc.
    recovery_notes = Column(Text, nullable=True)  # Pain, bleeding, etc.
    
    # General
    notes = Column(Text, nullable=True)
    
    # Composite indexes for common query patterns
    __table_args__ = (
        Index('idx_tracking_user_timestamp', 'user_id', 'timestamp'),
    )


class UserContextDB(Base):
    __tablename__ = "user_context"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    context = Column(JSON)  # Store baby age, birth type, preferences, etc.
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserDB(Base):
    """User authentication table"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaskDB(Base):
    """Task queue table"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True, nullable=False)
    task_type = Column(String, nullable=False, index=True)
    task_data = Column(Text)  # JSON string
    user_id = Column(String, index=True, nullable=False)
    status = Column(String, index=True, nullable=False)  # pending, processing, completed, failed, cancelled
    priority = Column(String, default="medium")  # high, medium, low
    worker_id = Column(String, nullable=True)
    result = Column(Text)  # JSON string
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    timeout_seconds = Column(Integer, default=300)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite indexes for common query patterns
    __table_args__ = (
        Index('idx_task_user_status_created', 'user_id', 'status', 'created_at'),
    )


class FeedbackDB(Base):
    """User feedback table"""
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    category = Column(String, nullable=False)  # bug, feature, question, other
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(String, default="medium")  # low, medium, high
    status = Column(String, default="open")  # open, in_progress, resolved, closed
    response = Column(Text, nullable=True)
    extra_metadata = Column(JSON, nullable=True)  # Additional metadata as JSON (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationDB(Base):
    """Notification and reminder table"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    notification_type = Column(String, nullable=False, index=True)  # feeding, sleep, mood_check, medical_appointment, custom
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    scheduled_time = Column(DateTime, nullable=False, index=True)
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String, nullable=True)  # daily, weekly, custom cron
    is_enabled = Column(Boolean, default=True)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    action_url = Column(String, nullable=True)  # URL to navigate when notification is clicked
    notification_metadata = Column(JSON, nullable=True)  # Additional data (e.g., feeding amount, sleep duration) (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite indexes for common query patterns
    __table_args__ = (
        Index('idx_notification_user_scheduled', 'user_id', 'scheduled_time'),
    )


class FamilyDB(Base):
    """Family group table"""
    __tablename__ = "families"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    created_by = Column(String, index=True, nullable=False)  # user_id of creator
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FamilyMemberDB(Base):
    """Family member table"""
    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False, default="member")  # owner, admin, member, viewer
    invited_by = Column(String, nullable=True)  # user_id of inviter
    status = Column(String, default="pending")  # pending, active, inactive
    permissions = Column(JSON, nullable=True)  # Custom permissions
    joined_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite indexes for common query patterns
    __table_args__ = (
        Index('idx_family_member_family_user', 'family_id', 'user_id'),
    )


class SubscriptionDB(Base):
    """Subscription table"""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    plan = Column(String, nullable=False)  # free, premium, enterprise
    status = Column(String, default="active")  # active, cancelled, expired, trial
    payment_provider = Column(String, nullable=True)  # stripe, paypal
    payment_provider_id = Column(String, nullable=True)  # Subscription ID from provider
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    cancelled_at = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    subscription_metadata = Column(JSON, nullable=True)  # Additional subscription data (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OnboardingProgressDB(Base):
    """Onboarding progress tracking table"""
    __tablename__ = "onboarding_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False, unique=True)
    completed_steps = Column(JSON, nullable=True)  # List of completed step IDs
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, default=7)
    is_completed = Column(Boolean, default=False)
    is_skipped = Column(Boolean, default=False)
    completion_percentage = Column(Float, default=0.0)
    personalization_data = Column(JSON, nullable=True)  # Baby age, feeding type, etc.
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NPSSurveyDB(Base):
    """NPS (Net Promoter Score) Survey table"""
    __tablename__ = "nps_surveys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    score = Column(Integer, nullable=False)  # 0-10
    comment = Column(Text, nullable=True)
    survey_type = Column(String, default="nps")  # nps, satisfaction, feature_request
    context = Column(JSON, nullable=True)  # Additional context (feature used, page, etc.)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class FeatureRequestDB(Base):
    """Feature request voting table"""
    __tablename__ = "feature_requests"

    id = Column(Integer, primary_key=True, index=True)
    feature_name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)  # ui, functionality, performance, etc.
    vote_count = Column(Integer, default=0, index=True)
    status = Column(String, default="open")  # open, in_progress, completed, rejected
    created_by = Column(String, nullable=True)  # user_id of creator
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FeatureVoteDB(Base):
    """Feature request votes table"""
    __tablename__ = "feature_votes"

    id = Column(Integer, primary_key=True, index=True)
    feature_request_id = Column(Integer, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AchievementDB(Base):
    """Achievement/Badge table"""
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    achievement_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    badge_icon = Column(String, nullable=True)  # Icon identifier
    category = Column(String, nullable=True)  # tracking, chat, streak, etc.
    criteria = Column(JSON, nullable=True)  # Criteria to unlock
    created_at = Column(DateTime, default=datetime.utcnow)


class UserAchievementDB(Base):
    """User achievement tracking table"""
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    achievement_id = Column(String, index=True, nullable=False)
    unlocked_at = Column(DateTime, default=datetime.utcnow, index=True)
    progress = Column(JSON, nullable=True)  # Progress towards achievement


class UserGoalDB(Base):
    """User goal setting table"""
    __tablename__ = "user_goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    goal_type = Column(String, nullable=False)  # daily_mood_check, weekly_tracking, etc.
    target_value = Column(Integer, nullable=True)  # Target number
    current_value = Column(Integer, default=0)
    period = Column(String, default="daily")  # daily, weekly, monthly
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TwoFactorAuthDB(Base):
    """Two-factor authentication table"""
    __tablename__ = "two_factor_auth"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    is_enabled = Column(Boolean, default=False)
    secret_key = Column(String, nullable=True)  # TOTP secret key
    backup_codes = Column(JSON, nullable=True)  # Backup codes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LoginHistoryDB(Base):
    """Login history table"""
    __tablename__ = "login_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    device_info = Column(JSON, nullable=True)  # Device type, OS, browser
    login_method = Column(String, default="password")  # password, 2fa, oauth
    success = Column(Boolean, default=True)
    failure_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class DeviceDB(Base):
    """Device management table"""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    device_id = Column(String, unique=True, index=True, nullable=False)
    device_name = Column(String, nullable=True)  # User-friendly name
    device_type = Column(String, nullable=True)  # mobile, desktop, tablet
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    last_used = Column(DateTime, default=datetime.utcnow, index=True)
    is_trusted = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


def init_db():
    """Initialize database tables"""
    # Import all models to ensure they're registered
    from models.help_models import HelpArticleDB, FAQDB, HelpFeedbackDB
    from models.analytics_models import UserEventDB, UserSessionDB, ProductMetricsDB
    from models.community_models import (
        PostDB, CommentDB, PostLikeDB, CommentLikeDB, 
        PostFavoriteDB, UserFollowDB, TopicDB, PostTopicDB, PostReportDB
    )
    
    Base.metadata.create_all(bind=engine)
