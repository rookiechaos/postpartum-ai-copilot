"""
User Health Service - User health scoring and risk detection
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from models.database import TrackingEntryDB, UserContextDB, TaskDB
from models.analytics_models import UserEventDB
from services.logging_service import logger
from exceptions import DatabaseError


class UserHealthService:
    """Service for user health scoring and risk detection"""
    
    def calculate_health_score(
        self,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive user health score
        
        Args:
            user_id: User ID
            db: Database session
        
        Returns:
            Health score and breakdown
        """
        try:
            score_components = {}
            total_score = 0
            max_score = 0
            
            # 1. Usage frequency (0-30 points)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            unique_days = db.query(
                func.date(TrackingEntryDB.timestamp).label('date')
            ).filter(
                and_(
                    TrackingEntryDB.user_id == user_id,
                    TrackingEntryDB.timestamp >= cutoff_date
                )
            ).distinct().count()
            
            usage_score = min(30, (unique_days / 30) * 30)
            score_components["usage_frequency"] = {
                "score": round(usage_score, 2),
                "max": 30,
                "days_active": unique_days
            }
            total_score += usage_score
            max_score += 30
            
            # 2. Feature engagement (0-25 points)
            chat_count = db.query(func.count(TaskDB.id)).filter(
                and_(
                    TaskDB.user_id == user_id,
                    TaskDB.task_type == "ai_chat",
                    TaskDB.created_at >= cutoff_date
                )
            ).scalar() or 0
            
            feature_score = min(25, (chat_count / 10) * 25)  # 10 chats = full score
            score_components["feature_engagement"] = {
                "score": round(feature_score, 2),
                "max": 25,
                "chat_count": chat_count
            }
            total_score += feature_score
            max_score += 25
            
            # 3. Data consistency (0-20 points)
            total_entries = db.query(func.count(TrackingEntryDB.id)).filter(
                and_(
                    TrackingEntryDB.user_id == user_id,
                    TrackingEntryDB.timestamp >= cutoff_date
                )
            ).scalar() or 0
            
            consistency_score = min(20, (total_entries / 50) * 20)  # 50 entries = full score
            score_components["data_consistency"] = {
                "score": round(consistency_score, 2),
                "max": 20,
                "total_entries": total_entries
            }
            total_score += consistency_score
            max_score += 20
            
            # 4. Recent activity (0-15 points)
            recent_cutoff = datetime.utcnow() - timedelta(days=7)
            recent_entries = db.query(func.count(TrackingEntryDB.id)).filter(
                and_(
                    TrackingEntryDB.user_id == user_id,
                    TrackingEntryDB.timestamp >= recent_cutoff
                )
            ).scalar() or 0
            
            recent_score = min(15, (recent_entries / 20) * 15)  # 20 entries in 7 days = full score
            score_components["recent_activity"] = {
                "score": round(recent_score, 2),
                "max": 15,
                "recent_entries": recent_entries
            }
            total_score += recent_score
            max_score += 15
            
            # 5. Mood tracking (0-10 points)
            mood_entries = db.query(func.count(TrackingEntryDB.id)).filter(
                and_(
                    TrackingEntryDB.user_id == user_id,
                    TrackingEntryDB.entry_type == "mood",
                    TrackingEntryDB.timestamp >= cutoff_date
                )
            ).scalar() or 0
            
            mood_score = min(10, (mood_entries / 10) * 10)  # 10 mood entries = full score
            score_components["mood_tracking"] = {
                "score": round(mood_score, 2),
                "max": 10,
                "mood_entries": mood_entries
            }
            total_score += mood_score
            max_score += 10
            
            # Calculate percentage
            health_percentage = (total_score / max_score * 100) if max_score > 0 else 0
            
            # Determine health status
            if health_percentage >= 80:
                status = "excellent"
            elif health_percentage >= 60:
                status = "good"
            elif health_percentage >= 40:
                status = "fair"
            else:
                status = "needs_attention"
            
            return {
                "user_id": user_id,
                "health_score": round(total_score, 2),
                "max_score": max_score,
                "health_percentage": round(health_percentage, 2),
                "status": status,
                "components": score_components,
                "calculated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.log_error(e, context={"action": "calculate_health_score", "user_id": user_id})
            raise DatabaseError(f"Failed to calculate health score: {str(e)}")
    
    def identify_at_risk_users(
        self,
        days: int = 7,
        threshold: float = 40.0,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """
        Identify users at risk of churning
        
        Args:
            days: Days of inactivity to consider
            threshold: Health score threshold
            db: Database session
        
        Returns:
            List of at-risk users
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get all users
            from models.database import UserDB
            all_users = db.query(UserDB.user_id).all()
            
            at_risk_users = []
            
            for (user_id,) in all_users:
                # Check recent activity
                recent_activity = db.query(func.count(TrackingEntryDB.id)).filter(
                    and_(
                        TrackingEntryDB.user_id == user_id,
                        TrackingEntryDB.timestamp >= cutoff_date
                    )
                ).scalar() or 0
                
                # If no recent activity, calculate health score
                if recent_activity == 0:
                    health_score = self.calculate_health_score(user_id, db)
                    if health_score["health_percentage"] < threshold:
                        at_risk_users.append({
                            "user_id": user_id,
                            "health_score": health_score["health_percentage"],
                            "risk_reason": "no_recent_activity",
                            "days_inactive": days
                        })
            
            return at_risk_users
        except Exception as e:
            logger.log_error(e, context={"action": "identify_at_risk_users"})
            return []
    
    def get_intervention_suggestions(
        self,
        user_id: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Get suggestions for improving user health
        
        Args:
            user_id: User ID
            db: Database session
        
        Returns:
            List of intervention suggestions
        """
        try:
            health_score = self.calculate_health_score(user_id, db)
            suggestions = []
            
            # Low usage frequency
            if health_score["components"]["usage_frequency"]["score"] < 15:
                suggestions.append({
                    "type": "increase_usage",
                    "priority": "high",
                    "title": "Start Tracking More",
                    "message": "Try tracking at least one activity per day to build better insights",
                    "action": "track_activity"
                })
            
            # Low feature engagement
            if health_score["components"]["feature_engagement"]["score"] < 12:
                suggestions.append({
                    "type": "use_features",
                    "priority": "medium",
                    "title": "Try the AI Chat",
                    "message": "Chat with the AI assistant to get personalized advice",
                    "action": "use_chat"
                })
            
            # Missing mood tracking
            if health_score["components"]["mood_tracking"]["score"] < 5:
                suggestions.append({
                    "type": "track_mood",
                    "priority": "medium",
                    "title": "Track Your Mood",
                    "message": "Regular mood tracking helps monitor your emotional wellbeing",
                    "action": "track_mood"
                })
            
            # Low recent activity
            if health_score["components"]["recent_activity"]["score"] < 7:
                suggestions.append({
                    "type": "recent_activity",
                    "priority": "high",
                    "title": "Get Back on Track",
                    "message": "You haven't tracked anything recently. Start tracking again to see patterns",
                    "action": "track_now"
                })
            
            return suggestions
        except Exception as e:
            logger.log_error(e, context={"action": "get_intervention_suggestions", "user_id": user_id})
            return []

