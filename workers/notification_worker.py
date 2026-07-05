"""
Notification Worker - Background worker for sending notifications
"""

import time

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from bootstrap import BACKEND_DIR, setup_backend_path

setup_backend_path()
load_dotenv(BACKEND_DIR.parent / "do-not-upload" / "local" / "backend.env")
load_dotenv(BACKEND_DIR / ".env")

from dependencies.database import SessionLocal  # noqa: E402
from services.notification_service import NotificationService  # noqa: E402
from services.logging_service import logger  # noqa: E402


class NotificationWorker:
    """Background worker for processing and sending notifications"""

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.running = False
        self.notification_service = NotificationService()

    def start(self):
        """Start the notification worker"""
        self.running = True
        logger.log_info("Notification worker started")

        while self.running:
            try:
                self._process_pending_notifications()
            except Exception as e:
                logger.log_error(e, context={"action": "notification_worker_process"})
            time.sleep(self.check_interval)

    def stop(self):
        """Stop the notification worker"""
        self.running = False
        logger.log_info("Notification worker stopped")

    def _process_pending_notifications(self):
        """Process and send pending notifications"""
        db: Session = SessionLocal()
        try:
            pending = self.notification_service.get_pending_notifications(db)
            if not pending:
                return

            logger.log_info(
                f"Processing {len(pending)} pending notifications",
                context={"count": len(pending)},
            )

            for notification in pending:
                try:
                    self.notification_service.send_notification(notification, db)
                except Exception as e:
                    logger.log_error(
                        e,
                        context={
                            "action": "send_notification",
                            "notification_id": notification.get("id"),
                        },
                    )
        finally:
            db.close()


def run_notification_worker():
    """Run notification worker (entry point for separate process)"""
    worker = NotificationWorker(check_interval=60)
    try:
        worker.start()
    except KeyboardInterrupt:
        worker.stop()


if __name__ == "__main__":
    run_notification_worker()
