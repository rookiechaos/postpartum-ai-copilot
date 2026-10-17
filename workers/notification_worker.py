"""Compatibility entry point: browser polling now owns reminder delivery."""

from dotenv import load_dotenv
from bootstrap import BACKEND_DIR, setup_backend_path

setup_backend_path()
load_dotenv(BACKEND_DIR.parent / "do-not-upload" / "local" / "backend.env")
load_dotenv(BACKEND_DIR / ".env")

from services.logging_service import logger  # noqa: E402


class NotificationWorker:
    """Retired: do not consume reminders using an empty process-local socket table."""

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.running = False

    def start(self):
        logger.log_info("Standalone notification delivery is retired; authenticated browsers poll due reminders")

    def stop(self):
        self.running = False


def run_notification_worker():
    NotificationWorker().start()


if __name__ == "__main__":
    run_notification_worker()
