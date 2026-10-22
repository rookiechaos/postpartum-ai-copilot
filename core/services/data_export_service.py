"""
Data Export Service - Export user data in various formats (GDPR compliant)
Data export service - export user data in multiple formats (GDPR compliant)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import json
import csv
import io
from models.database import TrackingEntryDB, UserContextDB, TaskDB, FeedbackDB, NotificationDB
from services.logging_service import logger


# One owner-record contract for both JSON and the CSV Value column. Keep nulls
# and zero values; an export must not drop recovery data or retry identities.
TRACKING_EXPORT_FIELDS = (
    "id", "record_key", "revision", "user_id", "entry_type", "timestamp",
    "end_timestamp", "subject_id", "family_shared", "feeding_type",
    "duration_minutes", "amount_ml", "side", "diaper_type",
    "sleep_duration_minutes", "sleep_quality", "mood_level", "mood_notes",
    "pumped_amount_ml", "weight_kg", "breast_condition", "recovery_notes", "notes",
)


class DataExportService:
    """Service for exporting user data"""
    
    def export_user_data_json(
        self,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Export all user data as JSON (GDPR compliant)
        
        Args:
            user_id: User ID
            db: Database session
        
        Returns:
            Dictionary containing all user data
        """
        try:
            data = {
                "export_date": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "data": {
                    "tracking_entries": self._export_tracking_entries(user_id, db),
                    "user_context": self._export_user_context(user_id, db),
                    "tasks": self._export_tasks(user_id, db),
                    "feedback": self._export_feedback(user_id, db),
                    "notifications": self._export_notifications(user_id, db)
                }
            }
            
            logger.log_info(f"User data exported (JSON) for user {user_id}")
            return data
        except Exception as e:
            logger.log_error(e, context={"action": "export_user_data_json", "user_id": user_id})
            raise
    
    def export_user_data_csv(
        self,
        user_id: str,
        db: Session
    ) -> str:
        """
        Export user data as CSV
        
        Args:
            user_id: User ID
            db: Database session
        
        Returns:
            CSV string
        """
        try:
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(["Data Type", "Field", "Value", "Timestamp"])
            
            # Export tracking entries
            for entry in self._export_tracking_entries(user_id, db):
                writer.writerow([
                    "tracking",
                    entry["entry_type"],
                    json.dumps(entry, ensure_ascii=False),
                    entry["timestamp"] or ""
                ])
            
            # Export tasks
            tasks = db.query(TaskDB).filter(TaskDB.user_id == user_id).all()
            for task in tasks:
                writer.writerow([
                    "task",
                    task.task_type,
                    json.dumps({
                        "status": task.status,
                        "priority": task.priority,
                        "result": task.result,
                        "error": task.error
                    }),
                    task.created_at.isoformat() if task.created_at else ""
                ])
            
            # Export feedback
            feedbacks = db.query(FeedbackDB).filter(FeedbackDB.user_id == user_id).all()
            for feedback in feedbacks:
                writer.writerow([
                    "feedback",
                    feedback.category,
                    json.dumps({
                        "title": feedback.title,
                        "message": feedback.message,
                        "priority": feedback.priority,
                        "status": feedback.status
                    }),
                    feedback.created_at.isoformat() if feedback.created_at else ""
                ])
            
            csv_string = output.getvalue()
            output.close()
            
            logger.log_info(f"User data exported (CSV) for user {user_id}")
            return csv_string
        except Exception as e:
            logger.log_error(e, context={"action": "export_user_data_csv", "user_id": user_id})
            raise
    
    def export_user_data_pdf(
        self,
        user_id: str,
        db: Session
    ) -> bytes:
        """
        Export user data as PDF (requires reportlab)
        
        Args:
            user_id: User ID
            db: Database session
        
        Returns:
            PDF bytes
        """
        try:
            # Try to import reportlab
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
                from reportlab.lib.styles import getSampleStyleSheet
                from reportlab.lib import colors
            except ImportError:
                raise ImportError("reportlab is required for PDF export. Install with: pip install reportlab")
            
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title = Paragraph(f"Data Export for User: {user_id}", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Export date
            date_text = Paragraph(f"Export Date: {datetime.utcnow().isoformat()}", styles['Normal'])
            story.append(date_text)
            story.append(Spacer(1, 12))
            
            # Tracking entries summary
            entries = db.query(TrackingEntryDB).filter(
                TrackingEntryDB.user_id == user_id
            ).count()
            
            story.append(Paragraph(f"Tracking Entries: {entries}", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            # Tasks summary
            tasks = db.query(TaskDB).filter(TaskDB.user_id == user_id).count()
            story.append(Paragraph(f"Tasks: {tasks}", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            # Feedback summary
            feedbacks = db.query(FeedbackDB).filter(FeedbackDB.user_id == user_id).count()
            story.append(Paragraph(f"Feedback Entries: {feedbacks}", styles['Heading2']))
            
            doc.build(story)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            logger.log_info(f"User data exported (PDF) for user {user_id}")
            return pdf_bytes
        except Exception as e:
            logger.log_error(e, context={"action": "export_user_data_pdf", "user_id": user_id})
            raise
    
    def _export_tracking_entries(self, user_id: str, db: Session) -> List[Dict[str, Any]]:
        """Export tracking entries"""
        entries = db.query(TrackingEntryDB).filter(
            TrackingEntryDB.user_id == user_id
        ).all()
        
        return [self._tracking_entry_to_dict(entry) for entry in entries]

    @staticmethod
    def _tracking_entry_to_dict(entry: TrackingEntryDB) -> Dict[str, Any]:
        record = {field: getattr(entry, field) for field in TRACKING_EXPORT_FIELDS}
        for field in ("timestamp", "end_timestamp"):
            value = record[field]
            record[field] = value.isoformat() if value is not None else None
        return record
    
    def _export_user_context(self, user_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """Export user context"""
        context = db.query(UserContextDB).filter(
            UserContextDB.user_id == user_id
        ).first()
        
        if context:
            return {
                "user_id": context.user_id,
                "context": context.context,
                "updated_at": context.updated_at.isoformat() if context.updated_at else None
            }
        return None
    
    def _export_tasks(self, user_id: str, db: Session) -> List[Dict[str, Any]]:
        """Export tasks"""
        tasks = db.query(TaskDB).filter(TaskDB.user_id == user_id).all()
        
        return [{
            "task_id": task.task_id,
            "task_type": task.task_type,
            "status": task.status,
            "priority": task.priority,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "result": json.loads(task.result) if task.result else None,
            "error": task.error
        } for task in tasks]
    
    def _export_feedback(self, user_id: str, db: Session) -> List[Dict[str, Any]]:
        """Export feedback"""
        feedbacks = db.query(FeedbackDB).filter(FeedbackDB.user_id == user_id).all()
        
        return [{
            "id": feedback.id,
            "category": feedback.category,
            "title": feedback.title,
            "message": feedback.message,
            "priority": feedback.priority,
            "status": feedback.status,
            "response": feedback.response,
            "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
            "updated_at": feedback.updated_at.isoformat() if feedback.updated_at else None
        } for feedback in feedbacks]
    
    def _export_notifications(self, user_id: str, db: Session) -> List[Dict[str, Any]]:
        """Export notifications"""
        notifications = db.query(NotificationDB).filter(NotificationDB.user_id == user_id).all()
        
        return [{
            "id": notification.id,
            "notification_type": notification.notification_type,
            "title": notification.title,
            "message": notification.message,
            "scheduled_time": notification.scheduled_time.isoformat() if notification.scheduled_time else None,
            "is_recurring": notification.is_recurring,
            "recurrence_pattern": notification.recurrence_pattern,
            "is_enabled": notification.is_enabled,
            "is_sent": notification.is_sent,
            "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
            "created_at": notification.created_at.isoformat() if notification.created_at else None
        } for notification in notifications]
