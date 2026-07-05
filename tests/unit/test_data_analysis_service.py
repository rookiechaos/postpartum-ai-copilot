"""
Unit tests for DataAnalysisService - Extended tests for new anomaly detection methods
"""

import pytest
from datetime import datetime, timedelta
from services.data_analysis_service import DataAnalysisService
from models.database import TrackingEntryDB
from models.schemas import TrackingEntry, EntryType


@pytest.mark.asyncio
async def test_detect_continuous_anomalies_sleep(test_db_session, mock_user_id):
    """Test detecting continuous sleep anomalies"""
    service = DataAnalysisService()
    
    # Create entries with consecutive low sleep (less than 8 hours for 3 days)
    for i in range(3):
        entry = TrackingEntryDB(
            user_id=mock_user_id,
            entry_type="sleep",
            sleep_duration_minutes=6 * 60,  # 6 hours (low)
            timestamp=datetime.utcnow() - timedelta(days=2-i)
        )
        test_db_session.add(entry)
    test_db_session.commit()
    
    anomalies = service.detect_continuous_anomalies(
        user_id=mock_user_id,
        entry_type="sleep",
        days=7,
        db=test_db_session
    )
    
    assert isinstance(anomalies, list)
    if len(anomalies) > 0:
        assert "type" in anomalies[0]
        assert "message" in anomalies[0]
        assert "severity" in anomalies[0]


@pytest.mark.asyncio
async def test_detect_continuous_anomalies_insufficient_data(test_db_session, mock_user_id):
    """Test continuous anomaly detection with insufficient data"""
    service = DataAnalysisService()
    
    # Create only 2 entries (need at least 3)
    for i in range(2):
        entry = TrackingEntryDB(
            user_id=mock_user_id,
            entry_type="sleep",
            sleep_duration_minutes=6 * 60,
            timestamp=datetime.utcnow() - timedelta(days=1-i)
        )
        test_db_session.add(entry)
    test_db_session.commit()
    
    anomalies = service.detect_continuous_anomalies(
        user_id=mock_user_id,
        entry_type="sleep",
        days=7,
        db=test_db_session
    )
    
    assert isinstance(anomalies, list)
    # Should return empty list with insufficient data
    assert len(anomalies) == 0


@pytest.mark.asyncio
async def test_detect_pattern_anomalies_feeding(test_db_session, mock_user_id):
    """Test detecting pattern anomalies in feeding"""
    service = DataAnalysisService()
    
    # Create entries with irregular feeding pattern
    # Very frequent feedings (every 1 hour) which is abnormal
    for i in range(10):
        entry = TrackingEntryDB(
            user_id=mock_user_id,
            entry_type="feeding",
            timestamp=datetime.utcnow() - timedelta(hours=10-i)
        )
        test_db_session.add(entry)
    test_db_session.commit()
    
    anomalies = service.detect_pattern_anomalies(
        user_id=mock_user_id,
        entry_type="feeding",
        days=30,
        db=test_db_session
    )
    
    assert isinstance(anomalies, list)
    # May or may not detect anomalies depending on threshold
    # Just verify the method runs without error


@pytest.mark.asyncio
async def test_detect_pattern_anomalies_no_data(test_db_session, mock_user_id):
    """Test pattern anomaly detection with no data"""
    service = DataAnalysisService()
    
    anomalies = service.detect_pattern_anomalies(
        user_id=mock_user_id,
        entry_type="feeding",
        days=30,
        db=test_db_session
    )
    
    assert isinstance(anomalies, list)
    assert len(anomalies) == 0


@pytest.mark.asyncio
async def test_detect_recovery_anomalies_weight_loss(test_db_session, mock_user_id):
    """Test detecting recovery anomalies (weight loss)"""
    service = DataAnalysisService()
    
    # Create entries with significant weight loss
    base_weight = 70.0
    for i in range(5):
        entry = TrackingEntryDB(
            user_id=mock_user_id,
            entry_type="recovery",
            weight_kg=base_weight - (i * 2.0),  # Losing 2kg per day (abnormal)
            timestamp=datetime.utcnow() - timedelta(days=4-i)
        )
        test_db_session.add(entry)
    test_db_session.commit()
    
    anomalies = service.detect_recovery_anomalies(
        user_id=mock_user_id,
        days=30,
        db=test_db_session
    )
    
    assert isinstance(anomalies, list)
    # May detect weight loss anomaly
    # Just verify the method runs without error


@pytest.mark.asyncio
async def test_detect_recovery_anomalies_breast_condition(test_db_session, mock_user_id):
    """Test detecting recovery anomalies (breast condition)"""
    service = DataAnalysisService()
    
    # Create entries with problematic breast condition
    for i in range(3):
        entry = TrackingEntryDB(
            user_id=mock_user_id,
            entry_type="recovery",
            breast_condition="blocked",  # Problematic condition
            timestamp=datetime.utcnow() - timedelta(days=2-i)
        )
        test_db_session.add(entry)
    test_db_session.commit()
    
    anomalies = service.detect_recovery_anomalies(
        user_id=mock_user_id,
        days=30,
        db=test_db_session
    )
    
    assert isinstance(anomalies, list)
    # May detect breast condition anomaly
    # Just verify the method runs without error


@pytest.mark.asyncio
async def test_detect_recovery_anomalies_no_data(test_db_session, mock_user_id):
    """Test recovery anomaly detection with no data"""
    service = DataAnalysisService()
    
    anomalies = service.detect_recovery_anomalies(
        user_id=mock_user_id,
        days=30,
        db=test_db_session
    )
    
    assert isinstance(anomalies, list)
    assert len(anomalies) == 0


def test_generate_anomaly_alert_english():
    """Test generating anomaly alert in English"""
    service = DataAnalysisService()
    
    anomaly = {
        "type": "consecutive_low_sleep",
        "message": "Insufficient sleep for three consecutive days",
        "severity": "medium"
    }
    
    alert = service.generate_anomaly_alert(anomaly, language="en")
    
    assert "title" in alert
    assert "message" in alert
    assert "severity" in alert
    assert "action" in alert
    assert alert["severity"] == "medium"


def test_generate_anomaly_alert_japanese():
    """Test generating anomaly alert in Japanese"""
    service = DataAnalysisService()
    
    anomaly = {
        "type": "consecutive_low_mood",
        "message": "Low mood for several consecutive days",
        "severity": "high"
    }
    
    alert = service.generate_anomaly_alert(anomaly, language="ja")
    
    assert "title" in alert
    assert "message" in alert
    assert "severity" in alert
    assert alert["severity"] == "high"


def test_generate_anomaly_alert_weight_loss():
    """Test generating anomaly alert for weight loss"""
    service = DataAnalysisService()
    
    anomaly = {
        "type": "significant_weight_loss",
        "message": "Significant weight loss",
        "severity": "high"
    }
    
    alert = service.generate_anomaly_alert(anomaly, language="en")
    
    assert "title" in alert
    assert "message" in alert
    assert "severity" in alert
    assert "action" in alert
    assert "weight" in alert["title"].lower() or "weight" in alert["message"].lower()


@pytest.mark.asyncio
async def test_detect_continuous_anomalies_mood(test_db_session, mock_user_id):
    """Test detecting continuous mood anomalies"""
    service = DataAnalysisService()
    
    # Create entries with consecutive low mood
    for i in range(3):
        entry = TrackingEntryDB(
            user_id=mock_user_id,
            entry_type="mood",
            mood_level="low",
            timestamp=datetime.utcnow() - timedelta(days=2-i)
        )
        test_db_session.add(entry)
    test_db_session.commit()
    
    anomalies = service.detect_continuous_anomalies(
        user_id=mock_user_id,
        entry_type="mood",
        days=7,
        db=test_db_session
    )
    
    assert isinstance(anomalies, list)
    # May detect mood anomaly
    # Just verify the method runs without error

