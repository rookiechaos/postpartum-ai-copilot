"""
Help Models - Help articles and FAQ
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, Index
from datetime import datetime
from models.database import Base


class HelpArticleDB(Base):
    """Help article table"""
    __tablename__ = "help_articles"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    category = Column(String, index=True, nullable=False)  # getting_started, chat, tracking, night_mode, checkin, settings, etc.
    language = Column(String, default="en", index=True)  # en, ja, zh
    tags = Column(JSON, nullable=True)  # Array of tags for search
    view_count = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)
    is_published = Column(Boolean, default=True)
    order = Column(Integer, default=0)  # Display order
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Note: Full-text search index would require PostgreSQL with pg_trgm extension
    # For SQLite, we'll use LIKE queries instead


class FAQDB(Base):
    """FAQ table"""
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, index=True)
    faq_id = Column(String, unique=True, index=True, nullable=False)
    question = Column(String, nullable=False, index=True)
    answer = Column(Text, nullable=False)
    category = Column(String, index=True, nullable=True)
    language = Column(String, default="en", index=True)
    view_count = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)
    is_published = Column(Boolean, default=True)
    order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HelpFeedbackDB(Base):
    """Help article feedback table"""
    __tablename__ = "help_feedback"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(String, index=True, nullable=True)  # null for FAQ feedback
    faq_id = Column(String, index=True, nullable=True)  # null for article feedback
    user_id = Column(String, index=True, nullable=True)
    is_helpful = Column(Boolean, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

