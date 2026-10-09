"""
Analytics Models - User behavior tracking and product metrics
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, Float, Index
from datetime import datetime
from models.database import Base


class UserEventDB(Base):
    """User event tracking table"""
    __tablename__ = "user_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=True)  # null for anonymous events
    session_id = Column(String, index=True, nullable=True)
    event_type = Column(String, index=True, nullable=False)  # page_view, click, action, conversion, etc.
    event_name = Column(String, index=True, nullable=False)  # Event name
    event_category = Column(String, index=True, nullable=True)  # Event category
    event_data = Column(JSON, nullable=True)  # Event data
    properties = Column(JSON, nullable=True)  # Event properties
    page_url = Column(String, nullable=True)
    referrer = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class UserSessionDB(Base):
    """User session table"""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    page_views = Column(Integer, default=0)
    events_count = Column(Integer, default=0)
    referrer = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)


class ProductMetricsDB(Base):
    """Daily product metrics table"""
    __tablename__ = "product_metrics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, unique=True, index=True, nullable=False)
    dau = Column(Integer, default=0)  # Daily Active Users
    mau = Column(Integer, default=0)  # Monthly Active Users
    new_users = Column(Integer, default=0)
    returning_users = Column(Integer, default=0)
    total_sessions = Column(Integer, default=0)
    avg_session_duration = Column(Float, default=0.0)
    total_events = Column(Integer, default=0)
    feature_usage = Column(JSON, nullable=True)  # Feature usage counts
    conversion_funnel = Column(JSON, nullable=True)  # Conversion funnel data
    retention_rate = Column(Float, default=0.0)  # Day N retention rate
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

