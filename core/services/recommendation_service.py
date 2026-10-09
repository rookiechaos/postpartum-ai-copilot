"""
Recommendation Service - Personalized recommendations and smart reminders
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from models.database import TrackingEntryDB, UserContextDB, NotificationDB
from services.logging_service import logger
from exceptions import DatabaseError


class RecommendationService:
    """Service for generating personalized recommendations"""
    
    def get_smart_reminders(
        self,
        user_id: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Generate smart reminders based on user behavior patterns
        
        Args:
            user_id: User ID
            db: Database session
        
        Returns:
            List of smart reminder recommendations
        """
        try:
            reminders = []
            
            # Get user context
            user_context = db.query(UserContextDB).filter(
                UserContextDB.user_id == user_id
            ).first()
            
            # Get recent tracking entries
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            recent_entries = db.query(TrackingEntryDB).filter(
                and_(
                    TrackingEntryDB.user_id == user_id,
                    TrackingEntryDB.timestamp >= cutoff_date
                )
            ).order_by(desc(TrackingEntryDB.timestamp)).all()
            
            # Analyze feeding patterns
            feeding_entries = [e for e in recent_entries if e.entry_type == "feeding"]
            if feeding_entries:
                # Calculate average time between feedings
                if len(feeding_entries) > 1:
                    time_diffs = []
                    for i in range(len(feeding_entries) - 1):
                        diff = (feeding_entries[i].timestamp - feeding_entries[i+1].timestamp).total_seconds() / 3600
                        time_diffs.append(diff)
                    
                    if time_diffs:
                        avg_interval = sum(time_diffs) / len(time_diffs)
                        last_feeding = feeding_entries[0].timestamp
                        next_feeding_time = last_feeding + timedelta(hours=avg_interval)
                        
                        if next_feeding_time > datetime.utcnow():
                            reminders.append({
                                "type": "feeding",
                                "title": "Feeding Reminder",
                                "message": f"Based on your pattern, it's time for the next feeding",
                                "scheduled_time": next_feeding_time.isoformat(),
                                "priority": "high"
                            })
            
            # Analyze sleep patterns
            sleep_entries = [e for e in recent_entries if e.entry_type == "sleep"]
            if sleep_entries:
                # Check if baby hasn't slept in a while
                last_sleep = sleep_entries[0].timestamp
                hours_since_sleep = (datetime.utcnow() - last_sleep).total_seconds() / 3600
                
                if hours_since_sleep > 3:  # More than 3 hours since last sleep
                    reminders.append({
                        "type": "sleep",
                        "title": "Sleep Reminder",
                        "message": "It's been a while since the last sleep. Consider putting baby to sleep.",
                        "scheduled_time": datetime.utcnow().isoformat(),
                        "priority": "medium"
                    })
            
            # Mood check-in reminder (if no mood entry today)
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            mood_entries_today = [e for e in recent_entries if e.entry_type == "mood" and e.timestamp >= today_start]
            
            if not mood_entries_today:
                # Suggest evening mood check-in
                evening_time = datetime.utcnow().replace(hour=18, minute=0, second=0, microsecond=0)
                if datetime.utcnow() < evening_time:
                    reminders.append({
                        "type": "mood_check",
                        "title": "Mood Check-in",
                        "message": "Don't forget to check in with your emotional wellbeing this evening",
                        "scheduled_time": evening_time.isoformat(),
                        "priority": "medium"
                    })
            
            return reminders
        except Exception as e:
            logger.log_error(e, context={"action": "get_smart_reminders", "user_id": user_id})
            return []
    
    def get_content_recommendations(
        self,
        user_id: str,
        db: Session,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get personalized content recommendations based on user context
        
        Args:
            user_id: User ID
            db: Database session
            limit: Maximum number of recommendations
        
        Returns:
            List of content recommendations
        """
        try:
            recommendations = []
            
            # Get user context
            user_context = db.query(UserContextDB).filter(
                UserContextDB.user_id == user_id
            ).first()
            
            if not user_context or not user_context.context:
                return recommendations
            
            context = user_context.context
            baby_age = context.get("babyAge", "")
            
            # Recommend based on baby age
            if "0-7" in baby_age or "1-2" in baby_age:
                recommendations.append({
                    "type": "article",
                    "title": "Newborn Care Basics",
                    "description": "Essential tips for caring for your newborn",
                    "url": "/help/articles/newborn-care",
                    "category": "getting_started"
                })
                recommendations.append({
                    "type": "article",
                    "title": "Understanding Newborn Sleep Patterns",
                    "description": "Learn about normal sleep patterns for newborns",
                    "url": "/help/articles/newborn-sleep",
                    "category": "tracking"
                })
            elif "2-4" in baby_age or "1-2m" in baby_age:
                recommendations.append({
                    "type": "article",
                    "title": "Establishing Feeding Routines",
                    "description": "Tips for creating consistent feeding schedules",
                    "url": "/help/articles/feeding-routines",
                    "category": "tracking"
                })
            
            # Recommend based on feeding type
            feeding_type = context.get("feedingType", "")
            if feeding_type == "breast":
                recommendations.append({
                    "type": "article",
                    "title": "Breastfeeding Support",
                    "description": "Resources and tips for successful breastfeeding",
                    "url": "/help/articles/breastfeeding-support",
                    "category": "tracking"
                })
            
            return recommendations[:limit]
        except Exception as e:
            logger.log_error(e, context={"action": "get_content_recommendations", "user_id": user_id})
            return []
    
    def get_milestone_suggestions(
        self,
        user_id: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Get milestone celebration suggestions
        
        Args:
            user_id: User ID
            db: Database session
        
        Returns:
            List of milestone suggestions
        """
        try:
            milestones = []
            
            # Get user context
            user_context = db.query(UserContextDB).filter(
                UserContextDB.user_id == user_id
            ).first()
            
            if not user_context:
                return milestones
            
            # Count tracking entries
            total_entries = db.query(func.count(TrackingEntryDB.id)).filter(
                TrackingEntryDB.user_id == user_id
            ).scalar() or 0
            
            # Milestone: First 10 entries
            if total_entries >= 10 and total_entries < 20:
                milestones.append({
                    "type": "milestone",
                    "title": "🎉 10 Entries Milestone!",
                    "message": "You've tracked 10 activities. Great job staying consistent!",
                    "achievement": "first_10_entries"
                })
            elif total_entries >= 50:
                milestones.append({
                    "type": "milestone",
                    "title": "🌟 50 Entries Milestone!",
                    "message": "Amazing! You've tracked 50 activities. Your dedication is inspiring!",
                    "achievement": "50_entries"
                })
            
            # Check consecutive days
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            unique_days = db.query(
                func.date(TrackingEntryDB.timestamp).label('date')
            ).filter(
                and_(
                    TrackingEntryDB.user_id == user_id,
                    TrackingEntryDB.timestamp >= cutoff_date
                )
            ).distinct().count()
            
            if unique_days >= 7:
                milestones.append({
                    "type": "milestone",
                    "title": "🔥 7-Day Streak!",
                    "message": "You've been tracking for 7 consecutive days. Keep it up!",
                    "achievement": "7_day_streak"
                })
            
            return milestones
        except Exception as e:
            logger.log_error(e, context={"action": "get_milestone_suggestions", "user_id": user_id})
            return []

