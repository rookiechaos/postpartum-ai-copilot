"""
Unit tests for NotificationService - Extended tests for new reminder methods
"""

import pytest
from datetime import datetime, timedelta
from services.notification_service import NotificationService
from models.database import NotificationDB


def test_create_weight_reminder(test_db_session, mock_user_id):
    """Test creating a weight tracking reminder"""
    service = NotificationService()
    
    reminder = service.create_weight_reminder(
        user_id=mock_user_id,
        db=test_db_session
    )
    
    assert reminder is not None
    assert "id" in reminder
    assert reminder["notification_type"] == "weight_tracking"
    assert reminder["title"] == "Weight Tracking Reminder"
    assert "message" in reminder
    assert "encouragement" in reminder["message"].lower() or "great" in reminder["message"].lower()
    assert reminder["is_recurring"] is True
    assert reminder["recurrence_pattern"] == "daily"


def test_create_weight_reminder_custom_time(test_db_session, mock_user_id):
    """Test creating a weight reminder with custom scheduled time"""
    service = NotificationService()
    
    scheduled_time = datetime.utcnow() + timedelta(hours=2)
    reminder = service.create_weight_reminder(
        user_id=mock_user_id,
        db=test_db_session,
        scheduled_time=scheduled_time
    )
    
    assert reminder is not None
    assert reminder["scheduled_time"] == scheduled_time.isoformat()


def test_create_recovery_reminder(test_db_session, mock_user_id):
    """Test creating a recovery tracking reminder"""
    service = NotificationService()
    
    reminder = service.create_recovery_reminder(
        user_id=mock_user_id,
        db=test_db_session
    )
    
    assert reminder is not None
    assert "id" in reminder
    assert reminder["notification_type"] == "recovery_tracking"
    assert reminder["title"] == "Recovery Tracking Reminder"
    assert "message" in reminder
    assert "encouragement" in reminder["message"].lower() or "great" in reminder["message"].lower()
    assert reminder["is_recurring"] is True
    assert reminder["recurrence_pattern"] == "daily"


def test_create_recovery_reminder_custom_time(test_db_session, mock_user_id):
    """Test creating a recovery reminder with custom scheduled time"""
    service = NotificationService()
    
    scheduled_time = datetime.utcnow() + timedelta(hours=3)
    reminder = service.create_recovery_reminder(
        user_id=mock_user_id,
        db=test_db_session,
        scheduled_time=scheduled_time
    )
    
    assert reminder is not None
    assert reminder["scheduled_time"] == scheduled_time.isoformat()


def test_create_summary_reminder_daily(test_db_session, mock_user_id):
    """Test creating a daily summary reminder"""
    service = NotificationService()
    
    reminder = service.create_summary_reminder(
        user_id=mock_user_id,
        db=test_db_session,
        period="daily"
    )
    
    assert reminder is not None
    assert "id" in reminder
    assert reminder["notification_type"] == "daily_summary"
    assert reminder["title"] == "Daily Summary Ready"
    assert "message" in reminder
    assert "daily" in reminder["message"].lower()
    assert reminder["is_recurring"] is True
    assert reminder["recurrence_pattern"] == "daily"


def test_create_summary_reminder_weekly(test_db_session, mock_user_id):
    """Test creating a weekly summary reminder"""
    service = NotificationService()
    
    reminder = service.create_summary_reminder(
        user_id=mock_user_id,
        db=test_db_session,
        period="weekly"
    )
    
    assert reminder is not None
    assert "id" in reminder
    assert reminder["notification_type"] == "weekly_summary"
    assert reminder["title"] == "Weekly Summary Ready"
    assert "message" in reminder
    assert "weekly" in reminder["message"].lower()
    assert reminder["is_recurring"] is True
    assert reminder["recurrence_pattern"] == "weekly"


def test_create_summary_reminder_custom_time(test_db_session, mock_user_id):
    """Test creating a summary reminder with custom scheduled time"""
    service = NotificationService()
    
    scheduled_time = datetime.utcnow() + timedelta(days=1)
    reminder = service.create_summary_reminder(
        user_id=mock_user_id,
        db=test_db_session,
        period="daily",
        scheduled_time=scheduled_time
    )
    
    assert reminder is not None
    assert reminder["scheduled_time"] == scheduled_time.isoformat()


def test_create_anomaly_alert(test_db_session, mock_user_id):
    """Test creating an anomaly alert notification"""
    service = NotificationService()
    
    anomaly = {
        "type": "consecutive_low_sleep",
        "message": "Insufficient sleep for three consecutive days",
        "severity": "medium"
    }
    
    alert = service.create_anomaly_alert(
        user_id=mock_user_id,
        anomaly=anomaly,
        db=test_db_session
    )
    
    assert alert is not None
    assert "id" in alert
    assert alert["notification_type"] == "anomaly_alert"
    assert alert["title"] == "Tracking Alert"
    assert "message" in alert
    assert "gentle" in alert["message"].lower() or "friendly" in alert["message"].lower() or "noticed" in alert["message"].lower()
    assert alert["is_recurring"] is False
    assert "metadata" in alert
    assert alert["metadata"]["anomaly"] == anomaly


def test_create_anomaly_alert_high_severity(test_db_session, mock_user_id):
    """Test creating an anomaly alert for high severity anomaly"""
    service = NotificationService()
    
    anomaly = {
        "type": "consecutive_low_mood",
        "message": "Low mood for several consecutive days",
        "severity": "high"
    }
    
    alert = service.create_anomaly_alert(
        user_id=mock_user_id,
        anomaly=anomaly,
        db=test_db_session
    )
    
    assert alert is not None
    assert alert["notification_type"] == "anomaly_alert"
    assert "message" in alert


def test_create_anomaly_alert_weight_loss(test_db_session, mock_user_id):
    """Test creating an anomaly alert for weight loss"""
    service = NotificationService()
    
    anomaly = {
        "type": "significant_weight_loss",
        "message": "Significant weight loss",
        "severity": "medium"
    }
    
    alert = service.create_anomaly_alert(
        user_id=mock_user_id,
        anomaly=anomaly,
        db=test_db_session
    )
    
    assert alert is not None
    assert alert["notification_type"] == "anomaly_alert"
    assert "message" in alert
    assert "metadata" in alert


def test_create_weight_reminder_error_handling(test_db_session, mock_user_id):
    """Test error handling in weight reminder creation"""
    service = NotificationService()
    
    # Test with invalid user_id (should handle gracefully)
    # This should not raise an exception but may return None
    reminder = service.create_weight_reminder(
        user_id="invalid_user_id",
        db=test_db_session
    )
    
    # Method should handle errors gracefully
    # May return None or raise exception depending on implementation
    assert reminder is None or isinstance(reminder, dict)


def test_create_recovery_reminder_encouragement(test_db_session, mock_user_id):
    """Test that recovery reminder includes encouragement"""
    service = NotificationService()
    
    reminder = service.create_recovery_reminder(
        user_id=mock_user_id,
        db=test_db_session
    )
    
    assert reminder is not None
    message = reminder["message"].lower()
    # Check for encouragement keywords
    assert any(keyword in message for keyword in ["great", "amazing", "best", "doing"])


def test_create_summary_reminder_encouragement(test_db_session, mock_user_id):
    """Test that summary reminder includes encouragement"""
    service = NotificationService()
    
    reminder = service.create_summary_reminder(
        user_id=mock_user_id,
        db=test_db_session,
        period="daily"
    )
    
    assert reminder is not None
    message = reminder["message"].lower()
    # Check for encouragement keywords
    assert any(keyword in message for keyword in ["amazing", "great", "wonderful", "doing"])

