"""
Notification Service - Smart reminders and notifications
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from models.database import NotificationDB, TrackingEntryDB, UserContextDB
from services.logging_service import logger
from services.websocket_manager import connection_manager
from utils.locale_loader import load_locale_file
import json


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
    
    def get_pending_notifications(
        self,
        db: Session,
        before_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get notifications that should be sent now"""
        try:
            now = before_time or datetime.utcnow()
            query = db.query(NotificationDB).filter(
                and_(
                    NotificationDB.is_enabled == True,
                    NotificationDB.is_sent == False,
                    NotificationDB.scheduled_time <= now
                )
            )
            
            notifications = query.all()
            return [self._notification_to_dict(n) for n in notifications]
        except Exception as e:
            logger.log_error(e, context={"action": "get_pending_notifications"})
            return []
    
    def mark_notification_sent(
        self,
        notification_id: int,
        db: Session
    ) -> bool:
        """Mark a notification as sent"""
        try:
            notification = db.query(NotificationDB).filter(
                NotificationDB.id == notification_id
            ).first()
            
            if not notification:
                return False
            
            notification.is_sent = True
            notification.sent_at = datetime.utcnow()
            
            # If recurring, create next occurrence
            if notification.is_recurring:
                next_time = self._calculate_next_occurrence(
                    notification.scheduled_time,
                    notification.recurrence_pattern
                )
                if next_time:
                    # Create next notification
                    next_notification = NotificationDB(
                        user_id=notification.user_id,
                        notification_type=notification.notification_type,
                        title=notification.title,
                        message=notification.message,
                        scheduled_time=next_time,
                        is_recurring=True,
                        recurrence_pattern=notification.recurrence_pattern,
                        action_url=notification.action_url,
                        notification_metadata=notification.notification_metadata,
                        is_enabled=True,
                        is_sent=False
                    )
                    db.add(next_notification)
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "mark_notification_sent", "notification_id": notification_id})
            return False
    
    def send_notification(
        self,
        notification: Dict[str, Any],
        db: Session
    ) -> bool:
        """
        Send a notification via WebSocket and mark as sent
        
        Args:
            notification: Notification dictionary
            db: Database session
        
        Returns:
            True if sent successfully
        """
        try:
            user_id = notification["user_id"]
            
            # Send via WebSocket
            message = {
                "type": "notification",
                "notification_id": notification["id"],
                "title": notification["title"],
                "message": notification["message"],
                "notification_type": notification["notification_type"],
                "action_url": notification.get("action_url"),
                "metadata": notification.get("metadata", {}),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to user via WebSocket
            import asyncio
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop.is_running():
                asyncio.create_task(connection_manager.send_to_user(user_id, message))
            else:
                loop.run_until_complete(connection_manager.send_to_user(user_id, message))
            
            # Mark as sent
            self.mark_notification_sent(notification["id"], db)
            
            logger.log_info(
                f"Notification sent: {notification['notification_type']} to user {user_id}",
                context={"notification_id": notification["id"]}
            )
            
            return True
        except Exception as e:
            logger.log_error(e, context={"action": "send_notification", "notification_id": notification.get("id")})
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
            # Schedule for evening by default
            now = datetime.utcnow()
            if time_of_day == "evening":
                scheduled_time = now.replace(hour=20, minute=0, second=0, microsecond=0)
                if scheduled_time < now:
                    scheduled_time += timedelta(days=1)
            elif time_of_day == "morning":
                scheduled_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
                if scheduled_time < now:
                    scheduled_time += timedelta(days=1)
            else:  # afternoon
                scheduled_time = now.replace(hour=14, minute=0, second=0, microsecond=0)
                if scheduled_time < now:
                    scheduled_time += timedelta(days=1)
            
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
        """Disable a notification"""
        try:
            notification = db.query(NotificationDB).filter(
                and_(
                    NotificationDB.id == notification_id,
                    NotificationDB.user_id == user_id
                )
            ).first()
            
            if not notification:
                return False
            
            notification.is_enabled = False
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "disable_notification", "notification_id": notification_id})
            return False
    
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
                # Default to daily at 9 AM
                now = datetime.utcnow()
                scheduled_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
                if scheduled_time <= now:
                    scheduled_time += timedelta(days=1)
            
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
                # Default to daily at 8 PM
                now = datetime.utcnow()
                scheduled_time = now.replace(hour=20, minute=0, second=0, microsecond=0)
                if scheduled_time <= now:
                    scheduled_time += timedelta(days=1)
            
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
                    # Daily summary at end of day (9 PM)
                    now = datetime.utcnow()
                    scheduled_time = now.replace(hour=21, minute=0, second=0, microsecond=0)
                    if scheduled_time <= now:
                        scheduled_time += timedelta(days=1)
                else:
                    # Weekly summary on Sunday evening
                    now = datetime.utcnow()
                    days_until_sunday = (6 - now.weekday()) % 7
                    if days_until_sunday == 0 and now.hour >= 21:
                        days_until_sunday = 7
                    scheduled_time = now + timedelta(days=days_until_sunday)
                    scheduled_time = scheduled_time.replace(hour=21, minute=0, second=0, microsecond=0)
            
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
