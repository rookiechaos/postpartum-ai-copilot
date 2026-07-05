#!/usr/bin/env python3
"""
Worker Startup Script - Start AI worker processes
"""

import asyncio
import signal
import uuid
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from bootstrap import BACKEND_DIR, setup_backend_path

setup_backend_path()
load_dotenv(BACKEND_DIR.parent / "do-not-upload" / "local" / "backend.env")
load_dotenv(BACKEND_DIR / ".env")

from ai_worker import AIWorker  # noqa: E402
from services.logging_service import logger  # noqa: E402


class WorkerManager:
    """Manages multiple worker processes"""

    def __init__(self, num_workers: int = 1):
        self.num_workers = num_workers
        self.workers: List[AIWorker] = []
        self.running = False

    def start_workers(self):
        """Start all worker processes"""
        logger.log_info(
            f"Starting {self.num_workers} worker(s)...",
            context={"num_workers": self.num_workers},
        )

        for _ in range(self.num_workers):
            worker_id = f"worker-{uuid.uuid4().hex[:8]}"
            self.workers.append(AIWorker(worker_id))

        self.running = True
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        asyncio.run(self._run_all_workers())

    async def _run_all_workers(self):
        """Run all workers concurrently"""
        tasks = [asyncio.create_task(worker.run()) for worker in self.workers]
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.log_info("Shutting down workers...")
            self.running = False
            for task in tasks:
                task.cancel()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.log_info(
            f"Received signal {signum}, shutting down...",
            context={"signal": signum},
        )
        self.running = False
        raise SystemExit(0)


def main():
    """Main entry point"""
    from config.settings import get_settings

    settings = get_settings()
    num_workers = settings.num_workers

    logger.log_info("=" * 50)
    logger.log_info("Postpartum AI Worker")
    logger.log_info("=" * 50)
    logger.log_info(f"Workers: {num_workers}")
    logger.log_info("Async Mode: Enabled")
    logger.log_info("=" * 50)

    WorkerManager(num_workers=num_workers).start_workers()


if __name__ == "__main__":
    main()
