"""
Notification Service - Smart reminders and notifications
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from models.database import NotificationDB, TrackingEntryDB, UserContextDB
from services.logging_service import logger
from services.care_periods import JST
from exceptions import DatabaseError
from utils.locale_loader import load_locale_file
import json


def _next_japan_time(hour: int, weekday: Optional[int] = None) -> datetime:
    """Choose a future Japanese wall-clock time, stored as naive UTC in the DB."""
    now = datetime.now(JST)
    scheduled = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if weekday is not None:
        scheduled += timedelta(days=(weekday - now.weekday()) % 7)
    if scheduled <= now:
        scheduled += timedelta(days=7 if weekday is not None else 1)
    return scheduled.astimezone(timezone.utc).replace(tzinfo=None)


class NotificationService:
    """Service for managing notifications and reminders"""
    
    def create_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        scheduled_time: datetime,
        db: Session,
        is_recurring: bool = False,
        recurrence_pattern: Optional[str] = None,
        action_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a notification/reminder
        
        Args:
            user_id: User ID
            notification_type: Type of notification (feeding, sleep, mood_check, etc.)
            title: Notification title
            message: Notification message
            scheduled_time: When to send the notification
            db: Database session
            is_recurring: Whether this is a recurring notification
            recurrence_pattern: Recurrence pattern (daily, weekly, custom)
            action_url: URL to navigate when clicked
            metadata: Additional metadata
        
        Returns:
            Created notification dictionary
        """
        try:
            notification = NotificationDB(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                scheduled_time=scheduled_time,
                is_recurring=is_recurring,
                recurrence_pattern=recurrence_pattern,
                action_url=action_url,
                notification_metadata=metadata or {},
                is_enabled=True,
                is_sent=False
            )
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            logger.log_info(
                f"Notification created: {notification_type} for user {user_id}",
                context={"notification_id": notification.id, "scheduled_time": scheduled_time.isoformat()}
            )
            
            return self._notification_to_dict(notification)
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "create_notification", "user_id": user_id})
            raise
    
    def get_user_notifications(
        self,
        user_id: str,
        db: Session,
        include_sent: bool = False,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get notifications for a user"""
        try:
            query = db.query(NotificationDB).filter(NotificationDB.user_id == user_id)
            
            if not include_sent:
                query = query.filter(NotificationDB.is_sent == False)
            
            notifications = query.filter(
                NotificationDB.is_enabled == True
            ).order_by(NotificationDB.scheduled_time.asc()).limit(limit).all()
            
            return [self._notification_to_dict(n) for n in notifications]
        except Exception as e:
            logger.log_error(e, context={"action": "get_user_notifications", "user_id": user_id})
            return []
    
    def get_pending_notifications(self, db: Session, before_time: Optional[datetime] = None,
                                  *, user_id: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        """The database is the shared queue; each authenticated browser reads only its owner."""
        if not user_id:
            return []
        try:
            now = before_time or datetime.utcnow()
            rows = db.query(NotificationDB).filter(
                NotificationDB.user_id == user_id,
                NotificationDB.is_enabled.is_(True), NotificationDB.is_sent.is_(False),
                NotificationDB.scheduled_time <= now,
            ).order_by(NotificationDB.scheduled_time, NotificationDB.id).limit(limit).all()
            return [self._notification_to_dict(row) for row in rows]
        except Exception as error:
            logger.log_error(error, context={"action": "get_pending_notifications"})
            raise DatabaseError("Unable to load due reminders") from error

    def mark_notification_sent(self, notification_id: int, db: Session, *, user_id: Optional[str] = None) -> bool:
        """Acknowledge browser acceptance, never an unverified worker send or a user read."""
        if not user_id:
            return False
        try:
            row = db.query(NotificationDB).filter(NotificationDB.id == notification_id,
                NotificationDB.user_id == user_id).with_for_update().first()
            if row is None:
                return False
            if row.is_sent:
                return True  # A lost acknowledgment response may safely be retried.
            now = datetime.utcnow()
            changed = db.query(NotificationDB).filter(NotificationDB.id == notification_id,
                NotificationDB.user_id == user_id, NotificationDB.is_enabled.is_(True),
                NotificationDB.is_sent.is_(False), NotificationDB.scheduled_time <= now,
            ).update({"is_sent": True, "sent_at": now, "updated_at": now}, synchronize_session=False)
            if changed != 1:
                db.rollback()
                return db.query(NotificationDB.id).filter(NotificationDB.id == notification_id,
                    NotificationDB.user_id == user_id, NotificationDB.is_sent.is_(True)).first() is not None
            if row.is_recurring:
                next_time = self._calculate_next_occurrence(row.scheduled_time, row.recurrence_pattern)
                # Skip missed occurrences rather than flooding the browser after an absence.
                interval = timedelta(days=1 if row.recurrence_pattern == "daily" else 7)
                if next_time is not None and next_time <= now:
                    next_time += interval * ((now - next_time) // interval + 1)
                if next_time is not None:
                    db.add(NotificationDB(user_id=user_id, notification_type=row.notification_type,
                        title=row.title, message=row.message, scheduled_time=next_time,
                        is_recurring=True, recurrence_pattern=row.recurrence_pattern,
                        action_url=row.action_url, notification_metadata=row.notification_metadata,
                        is_enabled=True, is_sent=False))
            db.commit()
            return True
        except Exception as error:
            db.rollback()
            logger.log_error(error, context={"action": "acknowledge_notification", "notification_id": notification_id})
            raise DatabaseError("Unable to acknowledge reminder delivery") from error

    def send_notification(self, notification: Dict[str, Any], db: Session) -> bool:
        """Retired worker API: a process-local socket table cannot prove browser delivery."""
        return False

    def create_smart_feeding_reminder(
        self,
        user_id: str,
        db: Session,
        based_on_history: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Create a smart feeding reminder based on user's history
        
        Args:
            user_id: User ID
            db: Database session
            based_on_history: Whether to base reminder on feeding history
        
        Returns:
            Created notification or None
        """
        try:
            # Get recent feeding entries
            if based_on_history:
                recent_feedings = db.query(TrackingEntryDB).filter(
                    and_(
                        TrackingEntryDB.user_id == user_id,
                        TrackingEntryDB.entry_type == "feeding",
                        TrackingEntryDB.timestamp >= datetime.utcnow() - timedelta(days=7)
                    )
                ).order_by(TrackingEntryDB.timestamp.desc()).limit(20).all()
                
                if recent_feedings:
                    # Calculate average interval
                    intervals = []
                    for i in range(len(recent_feedings) - 1):
                        interval = (recent_feedings[i].timestamp - recent_feedings[i + 1].timestamp).total_seconds() / 3600
                        intervals.append(interval)
                    
                    if intervals:
                        avg_interval = sum(intervals) / len(intervals)
                        next_feeding_time = datetime.utcnow() + timedelta(hours=avg_interval)
                    else:
                        # Default to 3 hours if no history
                        next_feeding_time = datetime.utcnow() + timedelta(hours=3)
                else:
                    # Default to 3 hours if no history
                    next_feeding_time = datetime.utcnow() + timedelta(hours=3)
            else:
                next_feeding_time = datetime.utcnow() + timedelta(hours=3)
            
            return self.create_notification(
                user_id=user_id,
                notification_type="feeding",
                title="Feeding Reminder",
                message="It's time for a feeding! 💙",
                scheduled_time=next_feeding_time,
                db=db,
                is_recurring=True,
                recurrence_pattern="daily",
                action_url="/tracking?type=feeding"
            )
        except Exception as e:
            logger.log_error(e, context={"action": "create_smart_feeding_reminder", "user_id": user_id})
            return None
    
    def create_mood_checkin_reminder(
        self,
        user_id: str,
        db: Session,
        time_of_day: str = "evening"  # morning, afternoon, evening
    ) -> Optional[Dict[str, Any]]:
        """Create a mood check-in reminder"""
        try:
            hour = {"evening": 20, "morning": 9}.get(time_of_day, 14)
            scheduled_time = _next_japan_time(hour)
            
            encouragement_messages = [
                "How are you feeling today? Take a moment to check in with yourself. You're doing great! 💚",
                "Daily check-in time! How are you doing? You're doing your best! 💙",
                "Let's check in on how you're feeling. You're doing wonderfully! 🌟"
            ]
            import random
            message = random.choice(encouragement_messages)
            
            return self.create_notification(
                user_id=user_id,
                notification_type="mood_check",
                title="Daily Check-in",
                message=message,
                scheduled_time=scheduled_time,
                db=db,
                is_recurring=True,
                recurrence_pattern="daily",
                action_url="/tracking?type=mood"
            )
        except Exception as e:
            logger.log_error(e, context={"action": "create_mood_checkin_reminder", "user_id": user_id})
            return None
    
    def disable_notification(
        self,
        notification_id: int,
        user_id: str,
        db: Session
    ) -> bool:
        """Stop an owned pending reminder, serialized with browser acknowledgment."""
        try:
            changed = db.query(NotificationDB).filter(
                NotificationDB.id == notification_id, NotificationDB.user_id == user_id,
                NotificationDB.is_sent.is_(False),
            ).update({"is_enabled": False, "updated_at": datetime.utcnow()}, synchronize_session=False)
            db.commit()
            return changed == 1
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "disable_notification", "notification_id": notification_id})
            raise DatabaseError("Unable to stop reminder") from e
    
    def _calculate_next_occurrence(
        self,
        current_time: datetime,
        pattern: Optional[str]
    ) -> Optional[datetime]:
        """Calculate next occurrence for recurring notification"""
        if pattern == "daily":
            return current_time + timedelta(days=1)
        elif pattern == "weekly":
            return current_time + timedelta(weeks=1)
        # Add more patterns as needed
        return None
    
    def _notification_to_dict(self, notification: NotificationDB) -> Dict[str, Any]:
        """Convert database notification to dictionary"""
        return {
            "id": notification.id,
            "user_id": notification.user_id,
            "notification_type": notification.notification_type,
            "title": notification.title,
            "message": notification.message,
            "scheduled_time": notification.scheduled_time.isoformat() if notification.scheduled_time else None,
            "is_recurring": notification.is_recurring,
            "recurrence_pattern": notification.recurrence_pattern,
            "is_enabled": notification.is_enabled,
            "is_sent": notification.is_sent,
            "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
            "action_url": notification.action_url,
            "metadata": notification.notification_metadata or {},
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
            "updated_at": notification.updated_at.isoformat() if notification.updated_at else None
        }
    
    def create_weight_reminder(
        self,
        user_id: str,
        db: Session,
        scheduled_time: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a weight tracking reminder with encouragement"""
        try:
            if not scheduled_time:
                scheduled_time = _next_japan_time(9)
            
            encouragement_messages = [
                "Time to track your weight! You're doing great! 💪",
                "Weight check time! Keep up the amazing work! 🌟",
                "Let's track your progress! You're doing your best! 💙"
            ]
            import random
            message = random.choice(encouragement_messages)
            
            return self.create_notification(
                user_id=user_id,
                notification_type="weight_tracking",
                title="Weight Tracking Reminder",
                message=message,
                scheduled_time=scheduled_time,
                db=db,
                is_recurring=True,
                recurrence_pattern="daily",
                action_url="/tracking?type=recovery"
            )
        except Exception as e:
            logger.log_error(e, context={"action": "create_weight_reminder", "user_id": user_id})
            return None
    
    def create_recovery_reminder(
        self,
        user_id: str,
        db: Session,
        scheduled_time: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a recovery tracking reminder with encouragement"""
        try:
            if not scheduled_time:
                scheduled_time = _next_japan_time(20)
            
            encouragement_messages = [
                "Time to check in on your recovery! You're doing great! 💚",
                "Recovery check-in time! Keep taking care of yourself! 🌸",
                "Let's track your recovery progress! You're doing your best! 💙"
            ]
            import random
            message = random.choice(encouragement_messages)
            
            return self.create_notification(
                user_id=user_id,
                notification_type="recovery_tracking",
                title="Recovery Tracking Reminder",
                message=message,
                scheduled_time=scheduled_time,
                db=db,
                is_recurring=True,
                recurrence_pattern="daily",
                action_url="/tracking?type=recovery"
            )
        except Exception as e:
            logger.log_error(e, context={"action": "create_recovery_reminder", "user_id": user_id})
            return None
    
    def create_summary_reminder(
        self,
        user_id: str,
        db: Session,
        period: str = "daily",  # "daily" or "weekly"
        scheduled_time: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a summary reminder with encouragement"""
        try:
            if not scheduled_time:
                if period == "daily":
                    scheduled_time = _next_japan_time(21)
                else:
                    scheduled_time = _next_japan_time(21, weekday=6)
            
            encouragement_messages = [
                f"Time for your {period} summary! You're doing amazing! 🌟",
                f"Let's review your {period} progress! You're doing great! 💙",
                f"Check out your {period} summary! Keep up the wonderful work! 💪"
            ]
            import random
            message = random.choice(encouragement_messages)
            
            return self.create_notification(
                user_id=user_id,
                notification_type=f"{period}_summary",
                title=f"{period.capitalize()} Summary Ready",
                message=message,
                scheduled_time=scheduled_time,
                db=db,
                is_recurring=True,
                recurrence_pattern="daily" if period == "daily" else "weekly",
                action_url=f"/dashboard?summary={period}"
            )
        except Exception as e:
            logger.log_error(e, context={"action": "create_summary_reminder", "user_id": user_id})
            return None
    
    def create_anomaly_alert(
        self,
        user_id: str,
        anomaly: Dict[str, Any],
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """Create an anomaly alert notification with gentle encouragement"""
        try:
            anomaly_type = anomaly.get("type", "unknown")
            anomaly_message = anomaly.get("message", "")
            
            # Gentle, supportive messages
            encouragement_prefixes = [
                "Just a gentle reminder:",
                "We noticed something:",
                "Here's a friendly heads-up:"
            ]
            import random
            prefix = random.choice(encouragement_prefixes)
            
            message = f"{prefix} {anomaly_message}. You're doing great, and we're here to help! 💙"
            
            return self.create_notification(
                user_id=user_id,
                notification_type="anomaly_alert",
                title="Tracking Alert",
                message=message,
                scheduled_time=datetime.utcnow(),
                db=db,
                is_recurring=False,
                action_url="/dashboard",
                metadata={"anomaly": anomaly}
            )
        except Exception as e:
            logger.log_error(e, context={"action": "create_anomaly_alert", "user_id": user_id})
            return None
    
    def _add_encouragement_to_message(
        self,
        message: str,
        language: str = "en"
    ) -> str:
        """Add encouragement to notification message"""
        encouragement_phrases = {
            "en": [
                "You're doing great!",
                "Keep up the amazing work!",
                "You're doing your best!",
                "You've got this!",
                "You're doing wonderfully!"
            ],
        }
        ja_encouragement = load_locale_file("ja", "notification_encouragement")
        if ja_encouragement.get("phrases"):
            encouragement_phrases["ja"] = ja_encouragement["phrases"]
        
        phrases = encouragement_phrases.get(language, encouragement_phrases["en"])
        import random
        encouragement = random.choice(phrases)
        
        # Add encouragement if not already present
        if encouragement.lower() not in message.lower():
            return f"{message} {encouragement}"
        return message
