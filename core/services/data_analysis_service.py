"""
Data Analysis Service - Advanced data analysis and visualization
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from collections import defaultdict
import statistics
from models.database import TrackingEntryDB
from services.logging_service import logger
from exceptions import DatabaseError
from utils.locale_loader import load_locale_file


class DataAnalysisService:
    """Service for advanced data analysis"""

    def __init__(self):
        self._locale_cache: Dict[str, Dict[str, Any]] = {}

    def _get_locale(self, language: str) -> Dict[str, Any]:
        lang = language if language in ("en", "ja") else "en"
        if lang not in self._locale_cache:
            self._locale_cache[lang] = load_locale_file(lang, "data_analysis")
        return self._locale_cache[lang]

    def _format_message(self, language: str, key: str, **kwargs: Any) -> str:
        template = self._get_locale(language).get("messages", {}).get(key, "")
        if not template:
            return ""
        try:
            return template.format(**kwargs)
        except KeyError:
            return template
    
    def predict_trends(
        self,
        user_id: str,
        entry_type: str,
        days: int = 30,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Predict future trends based on historical data
        
        Args:
            user_id: User ID
            entry_type: Type of entry (feeding, sleep, etc.)
            days: Number of days of historical data to analyze
            db: Database session
        
        Returns:
            Trend predictions
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            entries = db.query(TrackingEntryDB).filter(
                and_(
                    TrackingEntryDB.user_id == user_id,
                    TrackingEntryDB.entry_type == entry_type,
                    TrackingEntryDB.timestamp >= cutoff_date
                )
            ).order_by(TrackingEntryDB.timestamp).all()
            
            if len(entries) < 3:
                return {
                    "prediction": "insufficient_data",
                    "message": "Not enough data for prediction"
                }
            
            # Simple linear regression for trend prediction
            if entry_type == "feeding":
                # Predict next feeding time
                intervals = []
                for i in range(len(entries) - 1):
                    diff = (entries[i+1].timestamp - entries[i].timestamp).total_seconds() / 3600
                    intervals.append(diff)
                
                if intervals:
                    avg_interval = statistics.mean(intervals)
                    last_entry = entries[-1].timestamp
                    next_predicted = last_entry + timedelta(hours=avg_interval)
                    
                    return {
                        "prediction": "next_feeding",
                        "predicted_time": next_predicted.isoformat(),
                        "average_interval_hours": round(avg_interval, 2),
                        "confidence": "medium" if len(intervals) >= 5 else "low"
                    }
            
            elif entry_type == "sleep":
                # Predict sleep duration
                durations = [e.sleep_duration_minutes for e in entries if e.sleep_duration_minutes]
                if durations:
                    avg_duration = statistics.mean(durations)
                    return {
                        "prediction": "sleep_duration",
                        "predicted_duration_minutes": round(avg_duration),
                        "average_duration": round(avg_duration, 2),
                        "confidence": "medium" if len(durations) >= 5 else "low"
                    }
            
            return {"prediction": "no_prediction_available"}
        except Exception as e:
            logger.log_error(e, context={"action": "predict_trends", "user_id": user_id})
            return {"prediction": "error", "message": str(e)}
    
    def compare_periods(
        self,
        user_id: str,
        entry_type: str,
        period1_days: int = 7,
        period2_days: int = 7,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Compare data between two time periods
        
        Args:
            user_id: User ID
            entry_type: Type of entry
            period1_days: Days for first period (recent)
            period2_days: Days for second period (older)
            db: Database session
        
        Returns:
            Comparison data
        """
        try:
            now = datetime.utcnow()
            period1_start = now - timedelta(days=period1_days)
            period2_start = now - timedelta(days=period1_days + period2_days)
            period2_end = period1_start
            
            # Period 1 (recent)
            period1_entries = db.query(TrackingEntryDB).filter(
                and_(
                    TrackingEntryDB.user_id == user_id,
                    TrackingEntryDB.entry_type == entry_type,
                    TrackingEntryDB.timestamp >= period1_start
                )
            ).all()
            
            # Period 2 (older)
            period2_entries = db.query(TrackingEntryDB).filter(
                and_(
                    TrackingEntryDB.user_id == user_id,
                    TrackingEntryDB.entry_type == entry_type,
                    TrackingEntryDB.timestamp >= period2_start,
                    TrackingEntryDB.timestamp < period2_end
                )
            ).all()
            
            # Calculate metrics
            def calculate_metrics(entries):
                if entry_type == "feeding":
                    return {
                        "count": len(entries),
                        "total_duration": sum(e.duration_minutes or 0 for e in entries),
                        "avg_duration": statistics.mean([e.duration_minutes for e in entries if e.duration_minutes]) if entries else 0,
                        "total_amount": sum(e.amount_ml or 0 for e in entries),
                        "avg_amount": statistics.mean([e.amount_ml for e in entries if e.amount_ml]) if entries else 0
                    }
                elif entry_type == "sleep":
                    return {
                        "count": len(entries),
                        "total_duration": sum(e.sleep_duration_minutes or 0 for e in entries),
                        "avg_duration": statistics.mean([e.sleep_duration_minutes for e in entries if e.sleep_duration_minutes]) if entries else 0
                    }
                elif entry_type == "mood":
                    mood_levels = [e.mood_level for e in entries if e.mood_level]
                    mood_map = {"very_low": 1, "low": 2, "neutral": 3, "good": 4, "very_good": 5}
                    mood_values = [mood_map.get(m, 3) for m in mood_levels]
                    return {
                        "count": len(entries),
                        "avg_mood": statistics.mean(mood_values) if mood_values else 3
                    }
                else:
                    return {"count": len(entries)}
            
            period1_metrics = calculate_metrics(period1_entries)
            period2_metrics = calculate_metrics(period2_entries)
            
            # Calculate changes
            changes = {}
            for key in period1_metrics:
                if key in period2_metrics:
                    old_val = period2_metrics[key]
                    new_val = period1_metrics[key]
                    if old_val > 0:
                        change_percent = ((new_val - old_val) / old_val) * 100
                        changes[key] = {
                            "absolute": round(new_val - old_val, 2),
                            "percent": round(change_percent, 2),
                            "direction": "increase" if change_percent > 0 else "decrease"
                        }
            
            return {
                "period1": {
                    "start": period1_start.isoformat(),
                    "end": now.isoformat(),
                    "metrics": period1_metrics
                },
                "period2": {
                    "start": period2_start.isoformat(),
                    "end": period2_end.isoformat(),
                    "metrics": period2_metrics
                },
                "changes": changes
            }
        except Exception as e:
            logger.log_error(e, context={"action": "compare_periods", "user_id": user_id})
            return {"error": str(e)}
    
    def detect_anomalies(
        self,
        user_id: str,
        entry_type: str,
        days: int = 30,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies in tracking data
        
        Args:
            user_id: User ID
            entry_type: Type of entry
            days: Number of days to analyze
            db: Database session
        
        Returns:
            List of detected anomalies
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            entries = db.query(TrackingEntryDB).filter(
                and_(
                    TrackingEntryDB.user_id == user_id,
                    TrackingEntryDB.entry_type == entry_type,
                    TrackingEntryDB.timestamp >= cutoff_date
                )
            ).order_by(TrackingEntryDB.timestamp).all()
            
            if len(entries) < 5:
                return []
            
            anomalies = []
            
            if entry_type == "feeding":
                # Detect unusually long intervals
                intervals = []
                for i in range(len(entries) - 1):
                    diff = (entries[i+1].timestamp - entries[i].timestamp).total_seconds() / 3600
                    intervals.append(diff)
                
                if intervals:
                    mean_interval = statistics.mean(intervals)
                    std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0
                    
                    for i, interval in enumerate(intervals):
                        if interval > mean_interval + 2 * std_interval:
                            anomalies.append({
                                "type": "long_interval",
                                "entry_id": entries[i].id,
                                "timestamp": entries[i].timestamp.isoformat(),
                                "interval_hours": round(interval, 2),
                                "expected_interval": round(mean_interval, 2),
                                "severity": "medium",
                                "message": f"Unusually long gap between feedings: {round(interval, 1)} hours"
                            })
            
            elif entry_type == "sleep":
                # Detect unusually short or long sleep
                durations = [e.sleep_duration_minutes for e in entries if e.sleep_duration_minutes]
                if durations:
                    mean_duration = statistics.mean(durations)
                    std_duration = statistics.stdev(durations) if len(durations) > 1 else 0
                    
                    for entry in entries:
                        if entry.sleep_duration_minutes:
                            if entry.sleep_duration_minutes < mean_duration - 2 * std_duration:
                                anomalies.append({
                                    "type": "short_sleep",
                                    "entry_id": entry.id,
                                    "timestamp": entry.timestamp.isoformat(),
                                    "duration_minutes": entry.sleep_duration_minutes,
                                    "expected_duration": round(mean_duration, 2),
                                    "severity": "low",
                                    "message": f"Unusually short sleep: {entry.sleep_duration_minutes} minutes"
                                })
                            elif entry.sleep_duration_minutes > mean_duration + 2 * std_duration:
                                anomalies.append({
                                    "type": "long_sleep",
                                    "entry_id": entry.id,
                                    "timestamp": entry.timestamp.isoformat(),
                                    "duration_minutes": entry.sleep_duration_minutes,
                                    "expected_duration": round(mean_duration, 2),
                                    "severity": "low",
                                    "message": f"Unusually long sleep: {entry.sleep_duration_minutes} minutes"
                                })
            
            elif entry_type == "mood":
                # Detect mood drops
                mood_map = {"very_low": 1, "low": 2, "neutral": 3, "good": 4, "very_good": 5}
                mood_values = [mood_map.get(e.mood_level, 3) for e in entries if e.mood_level]
                
                if len(mood_values) >= 3:
                    recent_avg = statistics.mean(mood_values[-3:])
                    previous_avg = statistics.mean(mood_values[:-3]) if len(mood_values) > 3 else recent_avg
                    
                    if recent_avg < previous_avg - 1:
                        anomalies.append({
                            "type": "mood_drop",
                            "timestamp": entries[-1].timestamp.isoformat(),
                            "recent_avg": round(recent_avg, 2),
                            "previous_avg": round(previous_avg, 2),
                            "severity": "high",
                            "message": "Recent mood appears lower than usual. Consider checking in with your wellbeing."
                        })
            
            return anomalies
        except Exception as e:
            logger.log_error(e, context={"action": "detect_anomalies", "user_id": user_id})
            return []
    
    def detect_continuous_anomalies(
        self,
        user_id: str,
        entry_type: str,
        days: int = 7,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """
        Detect continuous anomalies (e.g., "Insufficient sleep for three consecutive days")
        
        Args:
            user_id: User ID
            entry_type: Type of entry
            days: Number of days to analyze
            db: Database session
        
        Returns:
            List of continuous anomalies
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            entries = db.query(TrackingEntryDB).filter(
                and_(
                    TrackingEntryDB.user_id == user_id,
                    TrackingEntryDB.entry_type == entry_type,
                    TrackingEntryDB.timestamp >= cutoff_date
                )
            ).order_by(TrackingEntryDB.timestamp).all()
            
            if len(entries) < 3:
                return []
            
            continuous_anomalies = []
            
            if entry_type == "sleep":
                # Detect consecutive days with insufficient sleep
                consecutive_low_sleep = 0
                min_sleep_threshold = 60  # minutes - threshold for "insufficient"
                
                for entry in entries:
                    if entry.sleep_duration_minutes and entry.sleep_duration_minutes < min_sleep_threshold:
                        consecutive_low_sleep += 1
                    else:
                        if consecutive_low_sleep >= 3:
                            continuous_anomalies.append({
                                "type": "consecutive_low_sleep",
                                "days": consecutive_low_sleep,
                                "severity": "medium",
                                "message": self._format_message(
                                    "en",
                                    "consecutive_low_sleep",
                                    days=consecutive_low_sleep,
                                )
                            })
                        consecutive_low_sleep = 0
                
                # Check if still in anomaly state
                if consecutive_low_sleep >= 3:
                    continuous_anomalies.append({
                        "type": "consecutive_low_sleep",
                        "days": consecutive_low_sleep,
                        "severity": "medium",
                        "message": self._format_message(
                            "en",
                            "consecutive_low_sleep",
                            days=consecutive_low_sleep,
                        )
                    })
            
            elif entry_type == "feeding":
                # Detect consecutive long intervals
                consecutive_long_intervals = 0
                max_interval_threshold = 6  # hours
                
                for i in range(len(entries) - 1):
                    diff = (entries[i+1].timestamp - entries[i].timestamp).total_seconds() / 3600
                    if diff > max_interval_threshold:
                        consecutive_long_intervals += 1
                    else:
                        if consecutive_long_intervals >= 3:
                            continuous_anomalies.append({
                                "type": "consecutive_long_intervals",
                                "days": consecutive_long_intervals,
                                "severity": "medium",
                                "message": self._format_message(
                                    "en",
                                    "consecutive_long_intervals",
                                    count=consecutive_long_intervals,
                                )
                            })
                        consecutive_long_intervals = 0
            
            elif entry_type == "mood":
                # Detect consecutive low mood days
                consecutive_low_mood = 0
                mood_map = {"very_low": 1, "low": 2, "neutral": 3, "good": 4, "very_good": 5}
                
                for entry in entries:
                    mood_value = mood_map.get(entry.mood_level, 3)
                    if mood_value <= 2:  # very_low or low
                        consecutive_low_mood += 1
                    else:
                        if consecutive_low_mood >= 3:
                            continuous_anomalies.append({
                                "type": "consecutive_low_mood",
                                "days": consecutive_low_mood,
                                "severity": "high",
                                "message": self._format_message(
                                    "en",
                                    "consecutive_low_mood",
                                    days=consecutive_low_mood,
                                )
                            })
                        consecutive_low_mood = 0
                
                if consecutive_low_mood >= 3:
                    continuous_anomalies.append({
                        "type": "consecutive_low_mood",
                        "days": consecutive_low_mood,
                        "severity": "high",
                        "message": self._format_message(
                            "en",
                            "consecutive_low_mood",
                            days=consecutive_low_mood,
                        )
                    })
            
            return continuous_anomalies
        except Exception as e:
            logger.log_error(e, context={"action": "detect_continuous_anomalies", "user_id": user_id})
            return []
    
    def detect_pattern_anomalies(
        self,
        user_id: str,
        entry_type: str,
        days: int = 30,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """
        Detect pattern anomalies (e.g., feeding frequency anomalies)
        
        Args:
            user_id: User ID
            entry_type: Type of entry
            days: Number of days to analyze
            db: Database session
        
        Returns:
            List of pattern anomalies
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            entries = db.query(TrackingEntryDB).filter(
                and_(
                    TrackingEntryDB.user_id == user_id,
                    TrackingEntryDB.entry_type == entry_type,
                    TrackingEntryDB.timestamp >= cutoff_date
                )
            ).order_by(TrackingEntryDB.timestamp).all()
            
            if len(entries) < 10:
                return []
            
            pattern_anomalies = []
            
            if entry_type == "feeding":
                # Analyze feeding frequency pattern
                intervals = []
                for i in range(len(entries) - 1):
                    diff = (entries[i+1].timestamp - entries[i].timestamp).total_seconds() / 3600
                    intervals.append(diff)
                
                if intervals:
                    mean_interval = statistics.mean(intervals)
                    # Check if feeding frequency is too high or too low
                    if mean_interval < 1.5:  # Less than 1.5 hours between feedings
                        pattern_anomalies.append({
                            "type": "high_frequency_feeding",
                            "average_interval": round(mean_interval, 2),
                            "severity": "low",
                            "message": self._format_message(
                                "en",
                                "high_feeding_frequency",
                                hours=round(mean_interval, 1),
                            )
                        })
                    elif mean_interval > 5:  # More than 5 hours between feedings
                        pattern_anomalies.append({
                            "type": "low_frequency_feeding",
                            "average_interval": round(mean_interval, 2),
                            "severity": "medium",
                            "message": self._format_message(
                                "en",
                                "low_feeding_frequency",
                                hours=round(mean_interval, 1),
                            )
                        })
            
            return pattern_anomalies
        except Exception as e:
            logger.log_error(e, context={"action": "detect_pattern_anomalies", "user_id": user_id})
            return []
    
    def detect_recovery_anomalies(
        self,
        user_id: str,
        days: int = 30,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """
        Detect recovery anomalies (weight, breast condition)
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            db: Database session
        
        Returns:
            List of recovery anomalies
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            entries = db.query(TrackingEntryDB).filter(
                and_(
                    TrackingEntryDB.user_id == user_id,
                    TrackingEntryDB.timestamp >= cutoff_date
                )
            ).order_by(TrackingEntryDB.timestamp).all()
            
            recovery_anomalies = []
            
            # Check weight trends
            weight_entries = [e for e in entries if e.weight_kg is not None]
            if len(weight_entries) >= 2:
                weights = [e.weight_kg for e in weight_entries]
                first_weight = weights[0]
                last_weight = weights[-1]
                weight_change = last_weight - first_weight
                
                # Detect significant weight loss (more than 5% in short time)
                if first_weight > 0:
                    weight_loss_percentage = (weight_change / first_weight) * 100
                    if weight_loss_percentage < -5:  # More than 5% loss
                        recovery_anomalies.append({
                            "type": "significant_weight_loss",
                            "weight_change_kg": round(weight_change, 2),
                            "weight_loss_percentage": round(abs(weight_loss_percentage), 1),
                            "severity": "medium",
                            "message": self._format_message(
                                "en",
                                "weight_loss",
                                percent=round(abs(weight_loss_percentage), 1),
                            )
                        })
            
            # Check breast condition
            breast_entries = [e for e in entries if e.breast_condition]
            if breast_entries:
                problematic_conditions = ["engorged", "blocked", "painful"]
                problematic_count = sum(1 for e in breast_entries if e.breast_condition in problematic_conditions)
                
                if problematic_count >= len(breast_entries) * 0.5:  # More than 50% problematic
                    recovery_anomalies.append({
                        "type": "frequent_breast_issues",
                        "problematic_entries": problematic_count,
                        "total_entries": len(breast_entries),
                        "severity": "medium",
                        "message": self._format_message("en", "breast_condition")
                    })
            
            return recovery_anomalies
        except Exception as e:
            logger.log_error(e, context={"action": "detect_recovery_anomalies", "user_id": user_id})
            return []
    
    def generate_anomaly_alert(
        self,
        anomaly: Dict[str, Any],
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Generate user-friendly anomaly alert
        
        Args:
            anomaly: Anomaly data
            language: Language code
        
        Returns:
            Alert message with actionable suggestions
        """
        alert = {
            "type": anomaly.get("type"),
            "severity": anomaly.get("severity", "low"),
            "message": anomaly.get("message", ""),
            "timestamp": datetime.utcnow().isoformat(),
            "suggestions": []
        }
        
        locale = self._get_locale(language if language in ("en", "ja") else "en")
        anomaly_type = anomaly.get("type", "")
        message_key_map = {
            "consecutive_low_sleep": ("consecutive_low_sleep", {"days": anomaly.get("days", 3)}),
            "consecutive_long_intervals": ("consecutive_long_intervals", {"count": anomaly.get("days", 3)}),
            "consecutive_low_mood": ("consecutive_low_mood", {"days": anomaly.get("days", 3)}),
            "high_frequency_feeding": ("high_feeding_frequency", {"hours": anomaly.get("average_interval", 0)}),
            "low_frequency_feeding": ("low_feeding_frequency", {"hours": anomaly.get("average_interval", 0)}),
            "significant_weight_loss": (
                "weight_loss",
                {"percent": anomaly.get("weight_loss_percentage", 0)},
            ),
            "frequent_breast_issues": ("breast_condition", {}),
        }
        if anomaly_type in message_key_map:
            key, params = message_key_map[anomaly_type]
            localized = self._format_message(language if language in ("en", "ja") else "en", key, **params)
            if localized:
                alert["message"] = localized
        elif anomaly.get("message"):
            alert["message"] = anomaly.get("message", "")

        suggestion_key_map = {
            "consecutive_low_sleep": "consecutive_low_sleep",
            "consecutive_low_mood": "consecutive_low_mood",
            "significant_weight_loss": "significant_weight_loss",
        }
        suggestion_key = suggestion_key_map.get(anomaly_type)
        if suggestion_key:
            alert["suggestions"] = locale.get("suggestions", {}).get(suggestion_key, [])
        
        return alert
    
    def generate_detailed_report(
        self,
        user_id: str,
        days: int = 30,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Generate detailed data analysis report
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            db: Database session
        
        Returns:
            Detailed analysis report
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            entries = db.query(TrackingEntryDB).filter(
                and_(
                    TrackingEntryDB.user_id == user_id,
                    TrackingEntryDB.timestamp >= cutoff_date
                )
            ).order_by(TrackingEntryDB.timestamp).all()
            
            # Group by entry type
            by_type = defaultdict(list)
            for entry in entries:
                by_type[entry.entry_type].append(entry)
            
            report = {
                "period": {
                    "start": cutoff_date.isoformat(),
                    "end": datetime.utcnow().isoformat(),
                    "days": days
                },
                "summary": {
                    "total_entries": len(entries),
                    "entries_by_type": {k: len(v) for k, v in by_type.items()}
                },
                "analysis": {}
            }
            
            # Analyze each type
            for entry_type, type_entries in by_type.items():
                if entry_type == "feeding":
                    report["analysis"]["feeding"] = {
                        "total_count": len(type_entries),
                        "avg_per_day": round(len(type_entries) / days, 2),
                        "total_duration_minutes": sum(e.duration_minutes or 0 for e in type_entries),
                        "total_amount_ml": sum(e.amount_ml or 0 for e in type_entries),
                        "avg_duration": round(statistics.mean([e.duration_minutes for e in type_entries if e.duration_minutes]), 2) if type_entries else 0,
                        "avg_amount": round(statistics.mean([e.amount_ml for e in type_entries if e.amount_ml]), 2) if type_entries else 0
                    }
                elif entry_type == "sleep":
                    report["analysis"]["sleep"] = {
                        "total_count": len(type_entries),
                        "avg_per_day": round(len(type_entries) / days, 2),
                        "total_duration_minutes": sum(e.sleep_duration_minutes or 0 for e in type_entries),
                        "avg_duration": round(statistics.mean([e.sleep_duration_minutes for e in type_entries if e.sleep_duration_minutes]), 2) if type_entries else 0
                    }
                elif entry_type == "mood":
                    mood_levels = [e.mood_level for e in type_entries if e.mood_level]
                    mood_map = {"very_low": 1, "low": 2, "neutral": 3, "good": 4, "very_good": 5}
                    mood_values = [mood_map.get(m, 3) for m in mood_levels]
                    report["analysis"]["mood"] = {
                        "total_count": len(type_entries),
                        "avg_per_day": round(len(type_entries) / days, 2),
                        "avg_mood_score": round(statistics.mean(mood_values), 2) if mood_values else 3,
                        "mood_distribution": {
                            level: mood_levels.count(level) for level in ["very_low", "low", "neutral", "good", "very_good"]
                        }
                    }
            
            # Add predictions
            if "feeding" in by_type:
                report["predictions"] = {
                    "feeding": self.predict_trends(user_id, "feeding", days, db)
                }
            
            # Add anomalies
            report["anomalies"] = {}
            for entry_type in by_type.keys():
                anomalies = self.detect_anomalies(user_id, entry_type, days, db)
                if anomalies:
                    report["anomalies"][entry_type] = anomalies
            
            return report
        except Exception as e:
            logger.log_error(e, context={"action": "generate_detailed_report", "user_id": user_id})
            raise DatabaseError(f"Failed to generate report: {str(e)}")

