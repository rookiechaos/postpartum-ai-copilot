"""
Voice Routes - API endpoints for voice interaction
"""

from fastapi import APIRouter, Depends, status, UploadFile, File, Form
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from dependencies.database import get_db
from middleware.auth import get_current_user
from models.schemas import User
from dependencies.container import get_container
from exceptions import ValidationError, AIServiceError
from config.settings import get_settings
import io

router = APIRouter()
container = get_container()


class TextToSpeechRequest(BaseModel):
    text: str
    language: str = "en"
    voice: Optional[str] = None
    speed: float = 1.0


@router.post("/speech-to-text")
async def speech_to_text(
    audio: UploadFile = File(...),
    language: str = Form("en"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Convert speech to text
    
    Upload an audio file and get transcribed text
    NSFW detection is applied to transcribed text
    """
    try:
        settings = get_settings()
        max_upload_size = settings.max_upload_size_mb * 1024 * 1024  # Convert MB to bytes
        
        voice_service = container.get("voice_service")
        
        # Check file size before reading
        # Note: FastAPI's UploadFile doesn't expose size directly, so we read and check
        # In production, consider using Content-Length header if available
        audio_data = await audio.read()
        
        # Validate file size
        if len(audio_data) > max_upload_size:
            raise ValidationError(
                f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
                details={
                    "file_size": len(audio_data),
                    "max_size": max_upload_size,
                    "max_size_mb": settings.max_upload_size_mb
                }
            )
        
        # Validate audio format
        format = audio.filename.split('.')[-1].lower() if audio.filename else "webm"
        if not voice_service.validate_audio_format(audio_data, format):
            raise ValidationError(
                f"Unsupported audio format: {format}",
                details={"format": format, "filename": audio.filename}
            )
        
        # Convert speech to text
        result = await voice_service.speech_to_text(
            audio_data=audio_data,
            language=language,
            format=format
        )
        
        # NSFW detection on transcribed text
        from services.nsfw_detector import get_nsfw_detector
        nsfw_detector = get_nsfw_detector()
        transcribed_text = result.get("text", "")
        
        if transcribed_text:
            nsfw_check = await nsfw_detector.check(
                transcribed_text,
                language=language,
                check_type="input"
            )
            
            if nsfw_detector.should_block(nsfw_check):
                raise ValidationError(
                    nsfw_detector.get_block_message(language),
                    details={"language": language, "nsfw_check": nsfw_check}
                )
        
        return result
    except (ValidationError, AIServiceError):
        raise
    except Exception as e:
        raise AIServiceError(
            f"Failed to process speech: {str(e)}",
            details={"language": language, "format": format, "original_error": str(e)}
        )


@router.post("/text-to-speech")
async def text_to_speech(
    request: TextToSpeechRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Convert text to speech
    
    Returns audio file (MP3 format)
    NSFW detection is applied to input text
    """
    try:
        # NSFW detection on input text
        from services.nsfw_detector import get_nsfw_detector
        nsfw_detector = get_nsfw_detector()
        nsfw_check = await nsfw_detector.check(
            request.text,
            language=request.language,
            check_type="input"
        )
        
        if nsfw_detector.should_block(nsfw_check):
            raise ValidationError(
                nsfw_detector.get_block_message(request.language),
                details={"language": request.language, "nsfw_check": nsfw_check}
            )
        
        voice_service = container.get("voice_service")
        
        # Validate text length
        if len(request.text) > 5000:
            raise ValidationError(
                "Text too long (maximum 5000 characters)",
                details={"text_length": len(request.text), "max_length": 5000}
            )
        
        # Validate speed
        if not 0.5 <= request.speed <= 2.0:
            raise ValidationError(
                "Speed must be between 0.5 and 2.0",
                details={"speed": request.speed, "min": 0.5, "max": 2.0}
            )
        
        # Convert text to speech
        audio_data = await voice_service.text_to_speech(
            text=request.text,
            language=request.language,
            voice=request.voice,
            speed=request.speed
        )
        
        # Return audio file
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=speech.mp3"
            }
        )
    except (ValidationError, AIServiceError):
        raise
    except Exception as e:
        raise AIServiceError(
            f"Failed to generate speech: {str(e)}",
            details={"language": request.language, "text_length": len(request.text), "original_error": str(e)}
        )


@router.get("/voices")
async def get_voices(
    language: str = "en",
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of supported voices for a language"""
    try:
        voice_service = container.get("voice_service")
        voices = voice_service.get_supported_voices(language)
        return {"language": language, "voices": voices}
    except Exception as e:
        raise AIServiceError(
            f"Failed to get voices: {str(e)}",
            details={"language": language, "original_error": str(e)}
        )

