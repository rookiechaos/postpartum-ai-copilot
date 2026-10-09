"""
Milestone Service - User milestone tracking and celebrations
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from models.database import TrackingEntryDB, UserContextDB
from services.logging_service import logger
from exceptions import DatabaseError


class MilestoneService:
    """Service for tracking and celebrating user milestones"""
    
    def check_milestones(
        self,
        user_id: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Check for new milestones achieved
        
        Args:
            user_id: User ID
            db: Database session
        
        Returns:
            List of newly achieved milestones
        """
        try:
            milestones = []
            
            # Count total tracking entries
            total_entries = db.query(func.count(TrackingEntryDB.id)).filter(
                TrackingEntryDB.user_id == user_id
            ).scalar() or 0
            
            # Entry count milestones
            if total_entries == 10:
                milestones.append({
                    "type": "entries",
                    "achievement": "first_10_entries",
                    "title": "🎉 10 Entries Milestone!",
                    "message": "You've tracked 10 activities. Great job staying consistent!",
                    "badge": "tracker_10"
                })
            elif total_entries == 50:
                milestones.append({
                    "type": "entries",
                    "achievement": "50_entries",
                    "title": "🌟 50 Entries Milestone!",
                    "message": "Amazing! You've tracked 50 activities. Your dedication is inspiring!",
                    "badge": "tracker_50"
                })
            elif total_entries == 100:
                milestones.append({
                    "type": "entries",
                    "achievement": "100_entries",
                    "title": "🏆 100 Entries Milestone!",
                    "message": "Incredible! You've tracked 100 activities. You're a tracking champion!",
                    "badge": "tracker_100"
                })
            
            # Consecutive days milestone
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            unique_days = db.query(
                func.date(TrackingEntryDB.timestamp).label('date')
            ).filter(
                and_(
                    TrackingEntryDB.user_id == user_id,
                    TrackingEntryDB.timestamp >= cutoff_date
                )
            ).distinct().count()
            
            if unique_days == 7:
                milestones.append({
                    "type": "streak",
                    "achievement": "7_day_streak",
                    "title": "🔥 7-Day Streak!",
                    "message": "You've been tracking for 7 consecutive days. Keep it up!",
                    "badge": "streak_7"
                })
            elif unique_days == 30:
                milestones.append({
                    "type": "streak",
                    "achievement": "30_day_streak",
                    "title": "💪 30-Day Streak!",
                    "message": "Outstanding! You've tracked for 30 consecutive days. You're unstoppable!",
                    "badge": "streak_30"
                })
            
            # Feature usage milestones
            # Check if user has used chat feature
            from models.database import TaskDB
            chat_tasks = db.query(func.count(TaskDB.id)).filter(
                and_(
                    TaskDB.user_id == user_id,
                    TaskDB.task_type == "ai_chat"
                )
            ).scalar() or 0
            
            if chat_tasks == 1:
                milestones.append({
                    "type": "feature",
                    "achievement": "first_chat",
                    "title": "💬 First Chat!",
                    "message": "You've had your first conversation with the AI assistant!",
                    "badge": "chat_first"
                })
            elif chat_tasks == 10:
                milestones.append({
                    "type": "feature",
                    "achievement": "10_chats",
                    "title": "💬 Chat Enthusiast!",
                    "message": "You've had 10 conversations with the AI. You're making great use of the assistant!",
                    "badge": "chat_10"
                })
            
            return milestones
        except Exception as e:
            logger.log_error(e, context={"action": "check_milestones", "user_id": user_id})
            return []
    
    def get_user_stats(
        self,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Get user statistics for milestone display
        
        Args:
            user_id: User ID
            db: Database session
        
        Returns:
            User statistics
        """
        try:
            # Total entries
            total_entries = db.query(func.count(TrackingEntryDB.id)).filter(
                TrackingEntryDB.user_id == user_id
            ).scalar() or 0
            
            # Consecutive days
            cutoff_date = datetime.utcnow() - timedelta(days=365)
            unique_days = db.query(
                func.date(TrackingEntryDB.timestamp).label('date')
            ).filter(
                and_(
                    TrackingEntryDB.user_id == user_id,
                    TrackingEntryDB.timestamp >= cutoff_date
                )
            ).distinct().count()
            
            # Days since first entry
            first_entry = db.query(TrackingEntryDB).filter(
                TrackingEntryDB.user_id == user_id
            ).order_by(TrackingEntryDB.timestamp).first()
            
            days_since_first = 0
            if first_entry and first_entry.timestamp:
                days_since_first = (datetime.utcnow() - first_entry.timestamp).days
            
            # Feature usage
            from models.database import TaskDB
            chat_count = db.query(func.count(TaskDB.id)).filter(
                and_(
                    TaskDB.user_id == user_id,
                    TaskDB.task_type == "ai_chat"
                )
            ).scalar() or 0
            
            return {
                "total_entries": total_entries,
                "consecutive_days": unique_days,
                "days_since_first": days_since_first,
                "chat_count": chat_count
            }
        except Exception as e:
            logger.log_error(e, context={"action": "get_user_stats", "user_id": user_id})
            return {
                "total_entries": 0,
                "consecutive_days": 0,
                "days_since_first": 0,
                "chat_count": 0
            }

