"""
Chat Routes - API endpoints for AI chat functionality
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import json

from dependencies.database import get_db
from middleware.auth import get_current_user
from middleware.rate_limit import rate_limit, RATE_LIMITS
from models.schemas import User, ChatMessage, ChatResponse, CrisisRequest
from services.tracking_service import TrackingService
from services.rag_service import RAGService
from services.personalization_service import PersonalizationService
from services.task_queue import TaskQueue, TaskPriority
from services.nsfw_detector import get_nsfw_detector
from services.ai_data_scope import profile_for_ai, records_for_ai, previous_exchange_for_ai
from exceptions import (
    PostpartumException,
    AIServiceError,
    TaskQueueError,
    ValidationError
)
from config.settings import get_settings
from dependencies.container import get_container

router = APIRouter(tags=["chat"])

container = get_container()
settings = get_settings()


async def _check_nsfw_input(query: str, language: str) -> None:
    """Block inappropriate user input before AI processing."""
    nsfw_detector = get_nsfw_detector()
    input_check = await nsfw_detector.check(
        query,
        language=language or "en",
        check_type="input",
    )
    if nsfw_detector.should_block(input_check):
        raise ValidationError(nsfw_detector.get_block_message(language or "en"))


@router.post("/api/chat", response_model=ChatResponse)
@rate_limit(RATE_LIMITS["chat"])
async def chat(
    request: Request,
    message: ChatMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Main chat endpoint for AI copilot.

    Requires authentication. user_id is always taken from the JWT token.
    """
    language = message.language or "en"
    previous_exchange = previous_exchange_for_ai(
        message.previous_exchange.model_dump() if message.previous_exchange else None, message.include_previous,
    )
    await _check_nsfw_input(message.query, language)

    ai_service = container.get("ai_service")
    tracking_service = container.get("tracking_service")
    rag_service = container.get("rag_service")
    task_queue = container.get("task_queue")

    user_id = current_user.user_id
    async_mode = settings.async_mode

    if not async_mode:
        try:
            context = profile_for_ai(await tracking_service.get_user_context(user_id, db), message.include_profile)
            rag_context = ""
            if rag_service and message.query:
                rag_context = await rag_service.search(message.query)

            language = message.language or "en"

            response = await ai_service.chat(
                query=message.query,
                context=context,
                rag_context=rag_context,
                user_id=user_id,
                language=language,
                previous_exchange=previous_exchange,
            )
            if response.get("error"):
                raise AIServiceError("AI response unavailable")

            return ChatResponse(
                response=response["text"],
                suggestions=response.get("suggestions", []),
                red_flags=response.get("red_flags", []),
                timestamp=datetime.now().isoformat(),
                validation=response.get("validation"),
            )
        except PostpartumException:
            raise
        except Exception as e:
            raise AIServiceError(f"Failed to process chat request: {str(e)}")

    try:
        task_data = {
            "query": message.query,
            "language": message.language or "en",
            "conversation_id": message.conversation_id,
            "include_profile": message.include_profile,
            "include_previous": message.include_previous,
            "previous_exchange": previous_exchange,
        }

        priority = TaskPriority.MEDIUM
        if any(keyword in message.query.lower() for keyword in ["urgent", "emergency", "help", "crisis"]):
            priority = TaskPriority.HIGH

        task_id = task_queue.create_task(
            task_type="ai_chat",
            task_data=task_data,
            user_id=user_id,
            db=db,
            priority=priority,
            timeout=300,
        )

        raise HTTPException(
            status_code=202,
            detail={
                "message": "Task created, please poll /api/tasks/{task_id} for result",
                "task_id": task_id,
                "status": "pending",
            },
        )
    except HTTPException:
        raise
    except PostpartumException:
        raise
    except Exception as e:
        raise TaskQueueError(f"Failed to create chat task: {str(e)}")


@router.post("/api/chat/stream")
@rate_limit(RATE_LIMITS["chat"])
async def chat_stream(
    request: Request,
    message: ChatMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Streaming chat endpoint for real-time responses (authenticated)."""
    language = message.language or "en"
    previous_exchange = previous_exchange_for_ai(
        message.previous_exchange.model_dump() if message.previous_exchange else None, message.include_previous,
    )
    await _check_nsfw_input(message.query, language)

    tracking_service = container.get("tracking_service")
    rag_service = container.get("rag_service")
    ai_service = container.get("ai_service")
    user_id = current_user.user_id
    language = message.language or "en"

    async def generate():
        try:
            context = profile_for_ai(await tracking_service.get_user_context(user_id, db), message.include_profile)
            rag_context = ""
            if rag_service and message.query:
                rag_context = await rag_service.search(message.query)

            async for chunk in ai_service.chat_stream(
                query=message.query,
                context=context,
                rag_context=rag_context,
                user_id=user_id,
                language=language,
                previous_exchange=previous_exchange,
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception:
            yield f"data: {json.dumps({'error': 'Failed to stream response'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/api/crisis")
@rate_limit(RATE_LIMITS["chat"])
async def crisis_mode(
    request: Request,
    crisis_request: CrisisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Night Mode / Crisis Mode - One-tap urgent support (authenticated)."""
    tracking_service = container.get("tracking_service")
    ai_service = container.get("ai_service")
    user_id = current_user.user_id
    language = getattr(crisis_request, "language", "en") or "en"
    crisis_query = crisis_request.query or "Help, I need immediate support"
    await _check_nsfw_input(crisis_query, language)

    try:
        context = profile_for_ai(await tracking_service.get_user_context(user_id, db), crisis_request.include_profile)
        recent_entries = records_for_ai(await tracking_service.get_recent_entries(user_id, db, hours=6)) if crisis_request.include_records else []

        response = await ai_service.crisis_response(
            query=crisis_query,
            context=context,
            recent_entries=recent_entries,
            language=language,
            night_mode=crisis_request.night_mode,
        )
        if response.get("error"):
            raise AIServiceError("AI response unavailable")

        return {
            "response": response["text"],
            "actions": response.get("actions", []),
            "red_flags": response.get("red_flags", []),
            "timestamp": datetime.now().isoformat(),
        }
    except PostpartumException:
        raise
    except Exception as e:
        raise AIServiceError(f"Failed to process crisis request: {str(e)}")


@router.post("/api/chat/personalized", response_model=ChatResponse)
@rate_limit(RATE_LIMITS["chat"])
async def personalized_chat(
    request: Request,
    message: ChatMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Personalized chat endpoint - uses personalization to optimize AI responses.
    Requires authentication; user_id is taken from the JWT token only.
    """
    user_id = current_user.user_id
    language = message.language or "en"
    await _check_nsfw_input(message.query, language)

    tracking_service = container.get("tracking_service")
    rag_service = container.get("rag_service")
    ai_service = container.get("ai_service")

    try:
        context = profile_for_ai(await tracking_service.get_user_context(user_id, db), message.include_profile)

        rag_context = ""
        if rag_service and message.query:
            rag_context = await rag_service.search(message.query)

        language = message.language or "ja"
        base_prompt = ai_service._get_system_prompt(language)
        optimized_prompt = base_prompt

        response = await ai_service.chat(
            query=message.query,
            context=context,
            rag_context=rag_context,
            user_id=user_id,
            language=language,
            system_prompt=optimized_prompt,
            previous_exchange=previous_exchange_for_ai(
                message.previous_exchange.model_dump() if message.previous_exchange else None, message.include_previous,
            ),
        )
        if response.get("error"):
            raise AIServiceError("AI response unavailable")

        return ChatResponse(
            response=response["text"],
            suggestions=response.get("suggestions", []),
            red_flags=response.get("red_flags", []),
            timestamp=datetime.now().isoformat(),
            validation=response.get("validation"),
            personalization_applied=message.include_profile,
        )
    except PostpartumException:
        raise
    except Exception as e:
        raise AIServiceError(f"Failed to process personalized chat: {str(e)}")
