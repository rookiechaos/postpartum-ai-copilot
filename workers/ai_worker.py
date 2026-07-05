"""
AI Worker - processes AI-related tasks from the queue
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

from dotenv import load_dotenv

from bootstrap import BACKEND_DIR, setup_backend_path

setup_backend_path()
load_dotenv(BACKEND_DIR.parent / "do-not-upload" / "local" / "backend.env")
load_dotenv(BACKEND_DIR / ".env")

from services.task_queue import TaskQueue, TaskStatus  # noqa: E402
from services.ai_service import AIService  # noqa: E402
from services.tracking_service import TrackingService  # noqa: E402
from services.rag_service import RAGService  # noqa: E402
from services.personalization_service import PersonalizationService  # noqa: E402
from services.logging_service import logger  # noqa: E402
from models.database import SessionLocal  # noqa: E402


class AIWorker:
    """
    Worker for processing AI tasks

    Handles:
    - ai_chat: Chat requests
    - tracking_analysis: Tracking data analysis
    - personalized_chat: Personalized chat requests
    """

    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self.task_queue = TaskQueue()
        self.ai_service = AIService()
        self.tracking_service = TrackingService()
        self.personalization_service = PersonalizationService()
        from config.settings import get_settings

        settings = get_settings()
        self.rag_service = RAGService() if settings.rag_enabled else None
        self._rag_initialized = False

    async def initialize(self):
        """Initialize async resources after the event loop is running."""
        if self.rag_service and not self._rag_initialized:
            await self._init_rag()
            self._rag_initialized = True

    async def _init_rag(self):
        """Initialize RAG service"""
        try:
            await self.rag_service.initialize()
        except Exception as e:
            logger.log_warning(
                f"RAG initialization failed: {e}",
                context={"worker_id": self.worker_id},
            )

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single task"""
        task_id = task["task_id"]
        task_type = task["task_type"]
        task_data = task["task_data"]
        user_id = task["user_id"]

        db = SessionLocal()
        try:
            if not self.task_queue.claim_task(task_id, self.worker_id, db):
                return {"error": "Failed to claim task"}

            if task_type == "ai_chat":
                result = await self._process_chat_task(task_data, user_id, db)
            elif task_type == "tracking_analysis":
                result = await self._process_tracking_analysis(task_data, user_id, db)
            elif task_type == "personalized_chat":
                result = await self._process_personalized_chat(task_data, user_id, db)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

            self.task_queue.update_task_status(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                db=db,
                result=result,
            )
            return result

        except Exception as e:
            error_message = str(e)
            try:
                self.task_queue.update_task_status(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    db=db,
                    error=error_message,
                )
            except Exception:
                pass
            logger.log_error(
                Exception(error_message),
                context={
                    "worker_id": self.worker_id,
                    "task_id": task_id,
                    "task_type": task_type,
                    "user_id": user_id,
                },
            )
            raise
        finally:
            db.close()

    async def _process_chat_task(
        self,
        task_data: Dict[str, Any],
        user_id: str,
        db,
    ) -> Dict[str, Any]:
        """Process AI chat task with NSFW detection"""
        query = task_data.get("query", "")
        language = task_data.get("language", "en")

        from services.nsfw_detector import get_nsfw_detector

        nsfw_detector = get_nsfw_detector()
        input_check = await nsfw_detector.check(query, language=language, check_type="input")

        if nsfw_detector.should_block(input_check):
            from exceptions import ValidationError

            raise ValidationError(nsfw_detector.get_block_message(language))

        context = await self.tracking_service.get_user_context(user_id, db)

        rag_context = ""
        if self.rag_service and query:
            try:
                rag_context = await self.rag_service.search(query)
            except Exception as e:
                logger.log_warning(
                    f"RAG search failed: {e}",
                    context={"user_id": user_id, "query_preview": query[:50]},
                )

        response = await self.ai_service.chat(
            query=query,
            context=context,
            rag_context=rag_context,
            user_id=user_id,
            language=language,
        )

        return {
            "response": response["text"],
            "suggestions": response.get("suggestions", []),
            "red_flags": response.get("red_flags", []),
            "validation": response.get("validation"),
            "timestamp": datetime.now().isoformat(),
        }

    async def _process_tracking_analysis(
        self,
        task_data: Dict[str, Any],
        user_id: str,
        db,
    ) -> Dict[str, Any]:
        """Process tracking analysis task"""
        days = task_data.get("days", 7)

        entries = await self.tracking_service.get_entries(user_id, db, days=days)
        context = await self.tracking_service.get_user_context(user_id, db)
        language = context.get("language", "en") or "en"

        summary = await self.ai_service.analyze_tracking(
            entries=entries,
            context=context,
            language=language,
        )

        return {
            "patterns": summary.get("patterns", []),
            "insights": summary.get("insights", []),
            "recommendations": summary.get("recommendations", []),
            "normalcy_checks": summary.get("normalcy_checks", []),
            "timestamp": datetime.now().isoformat(),
        }

    async def _process_personalized_chat(
        self,
        task_data: Dict[str, Any],
        user_id: str,
        db,
    ) -> Dict[str, Any]:
        """Process personalized chat task"""
        query = task_data.get("query", "")
        language = task_data.get("language", "en")

        context = await self.tracking_service.get_user_context(user_id, db)
        profile = await self.personalization_service.get_personalization_profile(user_id, db)
        enhanced_context = await self.personalization_service.optimize_response_context(
            user_id, context, db
        )

        rag_context = ""
        if self.rag_service and query:
            try:
                rag_context = await self.rag_service.search(query)
            except Exception as e:
                logger.log_warning(
                    f"RAG search failed: {e}",
                    context={"user_id": user_id, "query_preview": query[:50]},
                )

        language = language or profile.get("language", "en")
        base_prompt = self.ai_service._get_system_prompt(language)
        optimized_prompt = await self.personalization_service.optimize_ai_prompt(
            user_id, base_prompt, query, db
        )

        response = await self.ai_service.chat(
            query=query,
            context=enhanced_context,
            rag_context=rag_context,
            user_id=user_id,
            language=language,
            system_prompt=optimized_prompt,
        )

        return {
            "response": response["text"],
            "suggestions": response.get("suggestions", []),
            "red_flags": response.get("red_flags", []),
            "validation": response.get("validation"),
            "personalization_applied": True,
            "timestamp": datetime.now().isoformat(),
        }

    async def run(self, poll_interval: float = 1.0):
        """Main worker loop - continuously poll for and process tasks"""
        logger.log_info(
            f"Worker {self.worker_id} started",
            context={"worker_id": self.worker_id},
        )

        await self.initialize()

        while True:
            db = SessionLocal()
            try:
                self.task_queue.check_timeout_tasks(db)
                pending_tasks = self.task_queue.get_pending_tasks(db, limit=1)

                if pending_tasks:
                    task = pending_tasks[0]
                    logger.log_info(
                        f"Worker {self.worker_id} processing task {task['task_id']}",
                        context={
                            "worker_id": self.worker_id,
                            "task_id": task["task_id"],
                        },
                    )

                    try:
                        result = await self.process_task(task)
                        if result.get("error"):
                            logger.log_warning(
                                f"Worker {self.worker_id} failed to claim task {task['task_id']}",
                                context={
                                    "worker_id": self.worker_id,
                                    "task_id": task["task_id"],
                                    "error": result["error"],
                                },
                            )
                        else:
                            logger.log_info(
                                f"Worker {self.worker_id} completed task {task['task_id']}",
                                context={
                                    "worker_id": self.worker_id,
                                    "task_id": task["task_id"],
                                },
                            )
                    except Exception as e:
                        logger.log_error(
                            e,
                            context={
                                "worker_id": self.worker_id,
                                "task_id": task["task_id"],
                                "action": "process_task",
                            },
                        )
                else:
                    await asyncio.sleep(poll_interval)

            except KeyboardInterrupt:
                logger.log_info(
                    f"Worker {self.worker_id} shutting down...",
                    context={"worker_id": self.worker_id},
                )
                break
            except Exception as e:
                logger.log_error(
                    e,
                    context={"worker_id": self.worker_id, "action": "worker_loop"},
                )
                await asyncio.sleep(poll_interval)
            finally:
                db.close()
