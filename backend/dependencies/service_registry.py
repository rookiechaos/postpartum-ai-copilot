"""
Service Registry - Centralized service registration
"""

from typing import Optional
from dependencies.container import get_container
from config.settings import get_settings
from services.logging_service import logger


def register_all_services(container=None):
    """
    Register all services in the container
    
    Args:
        container: Service container instance (optional, will get global if not provided)
    """
    if container is None:
        container = get_container()
    
    settings = get_settings()
    
    # Core services
    def create_ai_service():
        from services.ai_service import AIService
        return AIService()
    
    def create_tracking_service():
        from services.tracking_service import TrackingService
        return TrackingService()
    
    def create_personalization_service():
        from services.personalization_service import PersonalizationService
        return PersonalizationService()
    
    def create_task_queue():
        from services.task_queue import TaskQueue
        return TaskQueue()
    
    def create_rag_service():
        from services.rag_service import RAGService
        if not settings.rag_enabled:
            return None
        try:
            return RAGService()
        except Exception as e:
            logger.log_warning("RAG service initialization failed", context={"action": "rag_initialization"})
            return None
    
    def create_community_service():
        from services.community_service import CommunityService
        return CommunityService()
    
    # Auth services
    def create_auth_service():
        from services.auth_service import AuthService
        return AuthService()
    
    def create_two_factor_auth_service():
        from services.two_factor_auth_service import TwoFactorAuthService
        return TwoFactorAuthService()
    
    def create_device_service():
        from services.device_service import DeviceService
        return DeviceService()
    
    # Feature services
    def create_feedback_service():
        from services.feedback_service import FeedbackService
        return FeedbackService()
    
    def create_voice_service():
        from services.voice_service import VoiceService
        return VoiceService()
    
    def create_payment_service():
        from services.payment_service import PaymentService
        return PaymentService()
    
    def create_product_analytics_service():
        from services.product_analytics_service import ProductAnalyticsService
        return ProductAnalyticsService()
    
    def create_help_service():
        from services.help_service import HelpService
        return HelpService()
    
    def create_relaxation_service():
        from services.relaxation_service import RelaxationService
        return RelaxationService()
    
    def create_family_service():
        from services.family_service import FamilyService
        return FamilyService()
    
    def create_notification_service():
        from services.notification_service import NotificationService
        return NotificationService()
    
    def create_referral_service():
        from services.referral_service import ReferralService
        return ReferralService()
    
    def create_data_analysis_service():
        from services.data_analysis_service import DataAnalysisService
        return DataAnalysisService()
    
    def create_achievement_service():
        from services.achievement_service import AchievementService
        return AchievementService()
    
    def create_milestone_service():
        from services.milestone_service import MilestoneService
        return MilestoneService()
    
    def create_recommendation_service():
        from services.recommendation_service import RecommendationService
        return RecommendationService()
    
    def create_onboarding_service():
        from services.onboarding_service import OnboardingService
        return OnboardingService()
    
    def create_data_export_service():
        from services.data_export_service import DataExportService
        return DataExportService()
    
    def create_user_health_service():
        from services.user_health_service import UserHealthService
        return UserHealthService()
    
    def create_analytics_service():
        from services.analytics_service import get_analytics_service
        return get_analytics_service()
    
    def create_health_check_service():
        from services.health_check_service import HealthCheckService
        return HealthCheckService()
    
    # Register all services as singletons
    services_to_register = [
        # Core services
        ("ai_service", create_ai_service),
        ("tracking_service", create_tracking_service),
        ("personalization_service", create_personalization_service),
        ("task_queue", create_task_queue),
        ("rag_service", create_rag_service),
        ("community_service", create_community_service),
        # Auth services
        ("auth_service", create_auth_service),
        ("two_factor_auth_service", create_two_factor_auth_service),
        ("device_service", create_device_service),
        # Feature services
        ("feedback_service", create_feedback_service),
        ("voice_service", create_voice_service),
        ("payment_service", create_payment_service),
        ("product_analytics_service", create_product_analytics_service),
        ("help_service", create_help_service),
        ("relaxation_service", create_relaxation_service),
        ("family_service", create_family_service),
        ("notification_service", create_notification_service),
        ("referral_service", create_referral_service),
        ("data_analysis_service", create_data_analysis_service),
        ("achievement_service", create_achievement_service),
        ("milestone_service", create_milestone_service),
        ("recommendation_service", create_recommendation_service),
        ("onboarding_service", create_onboarding_service),
        ("data_export_service", create_data_export_service),
        ("user_health_service", create_user_health_service),
        ("analytics_service", create_analytics_service),
        ("health_check_service", create_health_check_service),
    ]
    
    for service_name, factory in services_to_register:
        container.register_factory(service_name, factory, singleton=True)
    
    logger.log_info(f"Registered {len(services_to_register)} services in container")


def get_registered_service(service_name: str):
    """
    Get a registered service from container
    
    Args:
        service_name: Name of the service
        
    Returns:
        Service instance
        
    Raises:
        ValueError: If service is not registered
    """
    container = get_container()
    return container.get(service_name)
