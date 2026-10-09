"""
Service Interfaces - Protocol definitions for services
"""

from typing import Protocol, Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime
from sqlalchemy.orm import Session
from models.schemas import TrackingEntry, ChatMessage, ChatResponse


class ITrackingService(Protocol):
    """Interface for tracking service"""
    
    async def add_entry(
        self,
        entry: TrackingEntry,
        db: Session
    ) -> Dict[str, Any]:
        """Add a new tracking entry"""
        ...
    
    async def get_entries(
        self,
        user_id: str,
        db: Session,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get tracking entries for a user"""
        ...
    
    async def get_user_context(
        self,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """Get user context"""
        ...
    
    async def update_user_context(
        self,
        user_id: str,
        context: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """Update user context"""
        ...


class IAIService(Protocol):
    """Interface for AI service"""
    
    async def chat(
        self,
        query: str,
        context: Dict[str, Any],
        rag_context: str = "",
        user_id: str = "",
        language: str = "en"
    ) -> Dict[str, Any]:
        """Generate AI chat response"""
        ...
    
    async def chat_stream(
        self,
        query: str,
        context: Dict[str, Any],
        rag_context: str = "",
        user_id: str = ""
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming AI chat response"""
        ...
    
    async def crisis_response(
        self,
        query: str,
        context: Dict[str, Any],
        recent_entries: List[Dict[str, Any]],
        language: str = "en"
    ) -> Dict[str, Any]:
        """Generate crisis mode response"""
        ...


class IPersonalizationService(Protocol):
    """Interface for personalization service"""
    
    async def get_personalization_profile(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get user's personalization profile"""
        ...
    
    async def update_personalization_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user's personalization preferences"""
        ...
    
    async def optimize_ai_prompt(
        self,
        user_id: str,
        base_prompt: str,
        query: str
    ) -> str:
        """Optimize AI prompt based on user preferences"""
        ...


class ITaskQueue(Protocol):
    """Interface for task queue service"""
    
    def create_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        user_id: str,
        priority: Any = None,
        timeout: Optional[int] = None
    ) -> str:
        """Create a new task"""
        ...
    
    def get_task(
        self,
        task_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get task by ID"""
        ...
    
    def update_task_status(
        self,
        task_id: str,
        status: Any,
        db: Session,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        worker_id: Optional[str] = None,
        started_at: Optional[datetime] = None,
    ) -> bool:
        """Complete or fail the processing attempt owned by this worker."""
        ...

