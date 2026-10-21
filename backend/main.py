"""
Postpartum AI Copilot - Backend API
Provides AI-powered support for new mothers
"""

import sys
from pathlib import Path

_CORE_DIR = Path(__file__).resolve().parent.parent / "core"
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from dotenv import load_dotenv

from models.database import init_db
from dependencies.container import get_container
from config.settings import get_settings
from middleware.admin import require_admin
from models.schemas import User
from api.auth_routes import router as auth_router
from api.task_routes import router as task_router
from api.monitoring_routes import router as monitoring_router
from api.feedback_routes import router as feedback_router
from api.onboarding_routes import router as onboarding_router
from api.recommendation_routes import router as recommendation_router
from api.milestone_routes import router as milestone_router
from api.achievement_routes import router as achievement_router
from api.data_analysis_routes import router as data_analysis_router
from api.referral_routes import router as referral_router
from api.user_health_routes import router as user_health_router
from api.security_routes import router as security_router
from api.night_mode_routes import router as night_mode_router
from api.chat_routes import router as chat_router
from api.tracking_routes import router as tracking_router
from api.personalization_routes import router as personalization_router
from middleware.performance import PerformanceMonitoringMiddleware
from middleware.error_handler import (
    postpartum_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from exceptions import PostpartumException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

load_dotenv()

# Load settings
settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)

# Rate limiting (slowapi)
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from middleware.rate_limit import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration
origins = settings.get_cors_origins_list()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Performance monitoring middleware
app.add_middleware(PerformanceMonitoringMiddleware)

# Security headers middleware
from middleware.security import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)

# Exception handlers
app.add_exception_handler(PostpartumException, postpartum_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Initialize service container
container = get_container()

# Register all services using service registry
from dependencies.service_registry import register_all_services
register_all_services(container)

# Get RAG service for startup initialization
rag_service = container.get("rag_service")

# Register API routers
app.include_router(auth_router)
app.include_router(task_router)
app.include_router(monitoring_router)
app.include_router(feedback_router)
app.include_router(onboarding_router)
app.include_router(recommendation_router)
app.include_router(milestone_router)
app.include_router(achievement_router)
app.include_router(data_analysis_router)
app.include_router(referral_router)
app.include_router(user_health_router)
app.include_router(security_router)
app.include_router(night_mode_router)
app.include_router(chat_router)
app.include_router(tracking_router)
app.include_router(personalization_router)

from api.pilot_routes import router as pilot_router
app.include_router(pilot_router)

# WebSocket routes
from api.websocket_routes import router as websocket_router
app.include_router(websocket_router)

# Notification routes
from api.notification_routes import router as notification_router
app.include_router(notification_router, prefix="/api/notifications", tags=["notifications"])

# Data export routes
from api.data_export_routes import router as data_export_router
app.include_router(data_export_router, prefix="/api/export", tags=["data-export"])

# Voice routes
from api.voice_routes import router as voice_router
app.include_router(voice_router, prefix="/api/voice", tags=["voice"])

# Family routes
from api.family_routes import router as family_router
app.include_router(family_router, prefix="/api/families", tags=["families"])
from api.care_flow_routes import router as care_flow_router
app.include_router(care_flow_router)
from api.care_subject_routes import router as care_subject_router
app.include_router(care_subject_router)
from api.record_organization_routes import router as record_organization_router
app.include_router(record_organization_router)
from api.consultation_routes import router as consultation_router
app.include_router(consultation_router)

# Payment routes
from api.payment_routes import router as payment_router
app.include_router(payment_router, prefix="/api/payments", tags=["payments"])

# Community routes
from api.community_routes import router as community_router
app.include_router(community_router, tags=["community"])

# Help routes
from api.help_routes import router as help_router
app.include_router(help_router, prefix="/api/help", tags=["help"])

# Product analytics routes
from api.product_analytics_routes import router as product_analytics_router
app.include_router(product_analytics_router, prefix="/api/analytics/product", tags=["product-analytics"])

from api.account_request_routes import router as account_request_router
app.include_router(account_request_router)
from api.draft_routes import router as draft_router
app.include_router(draft_router)

# Initialize database
init_db()


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    if rag_service:
        await rag_service.initialize()


@app.get("/")
async def root():
    return {
        "message": "Postpartum AI Copilot API",
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Public liveness probe. Database readiness is /api/monitoring/health."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/metrics")
async def get_metrics(current_user: User = Depends(require_admin)):
    """Get performance metrics (basic endpoint)"""
    from middleware.performance import performance_metrics
    return performance_metrics.get_stats()

@app.get("/api/ai/provider")
async def get_ai_provider_info():
    """Get current AI provider information"""
    provider_name = settings.ai_provider.lower()
    return {
        "provider": provider_name,
        "supported_providers": ["openai", "claude", "gemini"],
        "configured": settings.is_ai_configured()
    }

@app.get("/api/validation/test")
async def test_validation():
    """Test endpoint for validation system"""
    from services.suggestion_validator import SuggestionValidator
    from services.medical_safety_rules import MedicalSafetyRules
    
    validator = SuggestionValidator()
    
    test_suggestion = "Give your baby medication for fever"
    validation = validator.validate_suggestion(test_suggestion, {}, "general")
    
    return {
        "test_suggestion": test_suggestion,
        "validation_result": validation,
        "forbidden_patterns": MedicalSafetyRules.check_forbidden_patterns(test_suggestion),
        "required_disclaimers": MedicalSafetyRules.requires_disclaimer(test_suggestion)
    }




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
