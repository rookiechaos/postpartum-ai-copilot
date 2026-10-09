"""
Achievement Service - Badge system and user goals
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from models.database import AchievementDB, UserAchievementDB, UserGoalDB, TrackingEntryDB, TaskDB
from services.logging_service import logger
from exceptions import DatabaseError, NotFoundError


class AchievementService:
    """Service for managing achievements and badges"""
    
    def initialize_achievements(self, db: Session) -> None:
        """Initialize default achievements"""
        try:
            achievements = [
                {
                    "achievement_id": "first_10_entries",
                    "name": "Getting Started",
                    "description": "Track 10 activities",
                    "badge_icon": "🎯",
                    "category": "tracking",
                    "criteria": {"entry_count": 10}
                },
                {
                    "achievement_id": "50_entries",
                    "name": "Consistent Tracker",
                    "description": "Track 50 activities",
                    "badge_icon": "📊",
                    "category": "tracking",
                    "criteria": {"entry_count": 50}
                },
                {
                    "achievement_id": "100_entries",
                    "name": "Tracking Champion",
                    "description": "Track 100 activities",
                    "badge_icon": "🏆",
                    "category": "tracking",
                    "criteria": {"entry_count": 100}
                },
                {
                    "achievement_id": "7_day_streak",
                    "name": "Week Warrior",
                    "description": "Track for 7 consecutive days",
                    "badge_icon": "🔥",
                    "category": "streak",
                    "criteria": {"consecutive_days": 7}
                },
                {
                    "achievement_id": "30_day_streak",
                    "name": "Month Master",
                    "description": "Track for 30 consecutive days",
                    "badge_icon": "💪",
                    "category": "streak",
                    "criteria": {"consecutive_days": 30}
                },
                {
                    "achievement_id": "first_chat",
                    "name": "First Chat",
                    "description": "Have your first conversation with AI",
                    "badge_icon": "💬",
                    "category": "chat",
                    "criteria": {"chat_count": 1}
                },
                {
                    "achievement_id": "10_chats",
                    "name": "Chat Enthusiast",
                    "description": "Have 10 conversations with AI",
                    "badge_icon": "🤖",
                    "category": "chat",
                    "criteria": {"chat_count": 10}
                }
            ]
            
            for ach_data in achievements:
                existing = db.query(AchievementDB).filter(
                    AchievementDB.achievement_id == ach_data["achievement_id"]
                ).first()
                
                if not existing:
                    achievement = AchievementDB(**ach_data)
                    db.add(achievement)
            
            db.commit()
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "initialize_achievements"})
    
    def check_and_unlock_achievements(
        self,
        user_id: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Check and unlock achievements for a user
        
        Args:
            user_id: User ID
            db: Database session
        
        Returns:
            List of newly unlocked achievements
        """
        try:
            # Initialize achievements if needed
            self.initialize_achievements(db)
            
            newly_unlocked = []
            
            # Get all achievements
            all_achievements = db.query(AchievementDB).all()
            
            # Get user's unlocked achievements
            unlocked_ids = {ua.achievement_id for ua in db.query(UserAchievementDB).filter(
                UserAchievementDB.user_id == user_id
            ).all()}
            
            # Check each achievement
            for achievement in all_achievements:
                if achievement.achievement_id in unlocked_ids:
                    continue
                
                # Check criteria
                if self._check_achievement_criteria(user_id, achievement, db):
                    # Unlock achievement
                    user_achievement = UserAchievementDB(
                        user_id=user_id,
                        achievement_id=achievement.achievement_id,
                        unlocked_at=datetime.utcnow()
                    )
                    db.add(user_achievement)
                    
                    newly_unlocked.append({
                        "achievement_id": achievement.achievement_id,
                        "name": achievement.name,
                        "description": achievement.description,
                        "badge_icon": achievement.badge_icon,
                        "category": achievement.category,
                        "unlocked_at": datetime.utcnow().isoformat()
                    })
            
            if newly_unlocked:
                db.commit()
            
            return newly_unlocked
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "check_and_unlock_achievements", "user_id": user_id})
            return []
    
    def _check_achievement_criteria(
        self,
        user_id: str,
        achievement: AchievementDB,
        db: Session
    ) -> bool:
        """Check if user meets achievement criteria"""
        try:
            criteria = achievement.criteria or {}
            
            # Entry count criteria
            if "entry_count" in criteria:
                count = db.query(func.count(TrackingEntryDB.id)).filter(
                    TrackingEntryDB.user_id == user_id
                ).scalar() or 0
                return count >= criteria["entry_count"]
            
            # Consecutive days criteria
            if "consecutive_days" in criteria:
                cutoff_date = datetime.utcnow() - timedelta(days=criteria["consecutive_days"])
                unique_days = db.query(
                    func.date(TrackingEntryDB.timestamp).label('date')
                ).filter(
                    and_(
                        TrackingEntryDB.user_id == user_id,
                        TrackingEntryDB.timestamp >= cutoff_date
                    )
                ).distinct().count()
                return unique_days >= criteria["consecutive_days"]
            
            # Chat count criteria
            if "chat_count" in criteria:
                count = db.query(func.count(TaskDB.id)).filter(
                    and_(
                        TaskDB.user_id == user_id,
                        TaskDB.task_type == "ai_chat"
                    )
                ).scalar() or 0
                return count >= criteria["chat_count"]
            
            return False
        except Exception as e:
            logger.log_error(e, context={"action": "_check_achievement_criteria"})
            return False
    
    def get_user_achievements(
        self,
        user_id: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Get all achievements for a user"""
        try:
            user_achievements = db.query(UserAchievementDB).filter(
                UserAchievementDB.user_id == user_id
            ).order_by(desc(UserAchievementDB.unlocked_at)).all()
            
            result = []
            for ua in user_achievements:
                achievement = db.query(AchievementDB).filter(
                    AchievementDB.achievement_id == ua.achievement_id
                ).first()
                
                if achievement:
                    result.append({
                        "achievement_id": achievement.achievement_id,
                        "name": achievement.name,
                        "description": achievement.description,
                        "badge_icon": achievement.badge_icon,
                        "category": achievement.category,
                        "unlocked_at": ua.unlocked_at.isoformat() if ua.unlocked_at else None
                    })
            
            return result
        except Exception as e:
            logger.log_error(e, context={"action": "get_user_achievements", "user_id": user_id})
            return []
    
    def create_user_goal(
        self,
        user_id: str,
        goal_type: str,
        target_value: Optional[int] = None,
        period: str = "daily",
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Create a user goal
        
        Args:
            user_id: User ID
            goal_type: Type of goal (daily_mood_check, weekly_tracking, etc.)
            target_value: Target value
            period: daily, weekly, monthly
            db: Database session
        
        Returns:
            Created goal
        """
        try:
            goal = UserGoalDB(
                user_id=user_id,
                goal_type=goal_type,
                target_value=target_value,
                period=period,
                is_active=True
            )
            db.add(goal)
            db.commit()
            db.refresh(goal)
            
            return {
                "id": goal.id,
                "user_id": goal.user_id,
                "goal_type": goal.goal_type,
                "target_value": goal.target_value,
                "current_value": goal.current_value,
                "period": goal.period,
                "is_active": goal.is_active,
                "created_at": goal.created_at.isoformat() if goal.created_at else None
            }
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "create_user_goal", "user_id": user_id})
            raise DatabaseError(f"Failed to create goal: {str(e)}")
    
    def get_user_goals(
        self,
        user_id: str,
        db: Session,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get user goals"""
        try:
            query = db.query(UserGoalDB).filter(UserGoalDB.user_id == user_id)
            
            if active_only:
                query = query.filter(UserGoalDB.is_active == True)
            
            goals = query.order_by(desc(UserGoalDB.created_at)).all()
            
            return [{
                "id": g.id,
                "user_id": g.user_id,
                "goal_type": g.goal_type,
                "target_value": g.target_value,
                "current_value": g.current_value,
                "period": g.period,
                "is_active": g.is_active,
                "progress_percentage": (g.current_value / g.target_value * 100) if g.target_value and g.target_value > 0 else 0,
                "created_at": g.created_at.isoformat() if g.created_at else None
            } for g in goals]
        except Exception as e:
            logger.log_error(e, context={"action": "get_user_goals", "user_id": user_id})
            return []
    
    def update_goal_progress(
        self,
        goal_id: int,
        user_id: str,
        increment: int = 1,
        db: Session = None
    ) -> Dict[str, Any]:
        """Update goal progress"""
        try:
            goal = db.query(UserGoalDB).filter(
                and_(
                    UserGoalDB.id == goal_id,
                    UserGoalDB.user_id == user_id
                )
            ).first()
            
            if not goal:
                raise NotFoundError("Goal not found")
            
            goal.current_value += increment
            goal.updated_at = datetime.utcnow()
            
            # Check if goal is completed
            if goal.target_value and goal.current_value >= goal.target_value:
                goal.is_active = False
            
            db.commit()
            db.refresh(goal)
            
            return {
                "id": goal.id,
                "current_value": goal.current_value,
                "target_value": goal.target_value,
                "progress_percentage": (goal.current_value / goal.target_value * 100) if goal.target_value and goal.target_value > 0 else 0,
                "is_completed": not goal.is_active if goal.target_value else False
            }
        except Exception as e:
            db.rollback()
            if isinstance(e, NotFoundError):
                raise
            logger.log_error(e, context={"action": "update_goal_progress"})
            raise DatabaseError(f"Failed to update goal progress: {str(e)}")

