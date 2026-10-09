"""
Personalization Service - Customizes AI responses based on user data
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from services.tracking_service import TrackingService
import json


class PersonalizationService:
    """
    Service for personalizing AI responses based on user data
    
    Features:
    - Learning user preferences from interactions
    - Adapting response style based on user behavior
    - Customizing suggestions based on baby age and patterns
    - Personalizing companion layer tone
    - Optimizing response length and detail level
    """
    
    def __init__(self):
        self.tracking_service = TrackingService()
    
    async def get_personalization_profile(
        self,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Get comprehensive personalization profile for a user
        
        Args:
            user_id: User identifier
            db: Database session
        
        Returns:
            {
                "response_style": str,  # "brief", "detailed", "balanced"
                "tone_preference": str,  # "warm", "professional", "casual"
                "detail_level": str,  # "minimal", "moderate", "comprehensive"
                "preferred_topics": List[str],
                "avoided_topics": List[str],
                "interaction_patterns": Dict,
                "baby_stage": str,
                "customizations": Dict
            }
        """
        # Try cache first
        from services.cache_service import get_cache
        cache = get_cache()
        cache_key = f"personalization:{user_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Get user context
        context = await self.tracking_service.get_user_context(user_id, db)
        
        # Get interaction history
        entries = await self.tracking_service.get_entries(user_id, db, days=30)
        
        # Analyze patterns
        patterns = self._analyze_interaction_patterns(entries, context)
        
        # Build personalization profile
        profile = {
            "response_style": self._determine_response_style(entries, context),
            "tone_preference": self._determine_tone_preference(context),
            "detail_level": self._determine_detail_level(entries, context),
            "preferred_topics": self._extract_preferred_topics(entries),
            "avoided_topics": self._extract_avoided_topics(entries),
            "interaction_patterns": patterns,
            "baby_stage": self._determine_baby_stage(context),
            "customizations": self._get_customizations(context),
            "language": context.get("language", "en"),
            "timezone": context.get("timezone", "UTC"),
            "notification_preferences": context.get("notifications", {})
        }
        
        # Cache profile for 30 minutes
        cache.set(cache_key, profile, ttl=1800)
        
        return profile
    
    async def optimize_ai_prompt(
        self,
        user_id: str,
        base_prompt: str,
        query: str,
        db: Session
    ) -> str:
        """
        Optimize AI prompt based on user personalization
        
        Args:
            user_id: User identifier
            base_prompt: Base system prompt
            query: User's query
            db: Database session
            
        Returns:
            Optimized prompt with personalization
        """
        profile = await self.get_personalization_profile(user_id, db)
        context = await self.tracking_service.get_user_context(user_id, db)
        
        # Build personalization instructions
        personalization_instructions = self._build_personalization_instructions(
            profile, context, query
        )
        
        # Combine with base prompt
        optimized_prompt = f"""{base_prompt}

PERSONALIZATION INSTRUCTIONS:
{personalization_instructions}

Remember to adapt your response style and content based on these personalization preferences."""
        
        return optimized_prompt
    
    async def optimize_response_context(
        self,
        user_id: str,
        base_context: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """
        Enhance context with personalization data
        
        Args:
            user_id: User identifier
            base_context: Base context dictionary
            db: Database session
            
        Returns:
            Enhanced context with personalization
        """
        profile = await self.get_personalization_profile(user_id, db)
        context = await self.tracking_service.get_user_context(user_id, db)
        
        # Add personalization data
        entries = await self.tracking_service.get_entries(user_id, db, days=30)
        
        enhanced_context = {
            **base_context,
            "personalization": {
                "response_style": profile["response_style"],
                "tone_preference": profile["tone_preference"],
                "detail_level": profile["detail_level"],
                "baby_stage": profile["baby_stage"]
            },
            "user_preferences": {
                "preferred_topics": profile["preferred_topics"],
                "avoided_topics": profile["avoided_topics"],
                "customizations": profile["customizations"]
            },
            "interaction_history": {
                "total_interactions": len(entries),
                "active_days": profile["interaction_patterns"].get("active_days", 0),
                "preferred_time": profile["interaction_patterns"].get("preferred_time", "unknown")
            }
        }
        
        return enhanced_context
    
    def _analyze_interaction_patterns(
        self,
        entries: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze user interaction patterns"""
        if not entries:
            return {
                "active_days": 0,
                "preferred_time": "unknown",
                "interaction_frequency": "low"
            }
        
        # Count active days
        unique_days = set()
        for entry in entries:
            if entry.get("timestamp"):
                day = entry["timestamp"][:10] if isinstance(entry["timestamp"], str) else entry["timestamp"].date()
                unique_days.add(str(day))
        
        # Determine preferred time (simplified)
        preferred_time = "unknown"
        if entries:
            # Could analyze timestamps here
            preferred_time = "varied"
        
        # Interaction frequency
        days_count = len(unique_days)
        if days_count >= 20:
            frequency = "high"
        elif days_count >= 10:
            frequency = "medium"
        else:
            frequency = "low"
        
        return {
            "active_days": days_count,
            "preferred_time": preferred_time,
            "interaction_frequency": frequency,
            "total_entries": len(entries)
        }
    
    def _determine_response_style(
        self,
        entries: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """Determine preferred response style"""
        # Check if user has explicit preference
        if context.get("response_style"):
            return context["response_style"]
        
        # Analyze from interaction patterns
        if len(entries) < 5:
            return "detailed"  # New users get more detailed responses
        elif len(entries) > 50:
            return "brief"  # Experienced users prefer brief responses
        else:
            return "balanced"
    
    def _determine_tone_preference(
        self,
        context: Dict[str, Any]
    ) -> str:
        """Determine tone preference"""
        # Check explicit preference
        if context.get("tone_preference"):
            return context["tone_preference"]
        
        # Default based on context
        if context.get("baby_age_days") and context["baby_age_days"] < 7:
            return "warm"  # Very new mothers need warm support
        else:
            return "warm"  # Default to warm for postpartum support
    
    def _determine_detail_level(
        self,
        entries: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """Determine preferred detail level"""
        if context.get("detail_level"):
            return context["detail_level"]
        
        # New users need more detail
        if len(entries) < 10:
            return "comprehensive"
        elif len(entries) > 30:
            return "minimal"
        else:
            return "moderate"
    
    def _extract_preferred_topics(
        self,
        entries: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract topics user frequently asks about"""
        topic_counts = {}
        
        for entry in entries:
            entry_type = entry.get("entry_type", "")
            if entry_type:
                topic_counts[entry_type] = topic_counts.get(entry_type, 0) + 1
        
        # Return top 3 topics
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        return [topic for topic, _ in sorted_topics[:3]]
    
    def _extract_avoided_topics(
        self,
        entries: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract topics user rarely interacts with"""
        # This would require more sophisticated tracking
        # For now, return empty list
        return []
    
    def _determine_baby_stage(
        self,
        context: Dict[str, Any]
    ) -> str:
        """Determine baby's developmental stage"""
        baby_age_days = context.get("baby_age_days")
        
        if not baby_age_days:
            return "unknown"
        
        if baby_age_days <= 7:
            return "newborn_week1"
        elif baby_age_days <= 14:
            return "newborn_week2"
        elif baby_age_days <= 30:
            return "newborn_month1"
        elif baby_age_days <= 90:
            return "infant_month2_3"
        elif baby_age_days <= 180:
            return "infant_month4_6"
        else:
            return "infant_6plus"
    
    def _get_customizations(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get user-specific customizations"""
        return {
            "baby_name": context.get("babyName"),
            "feeding_preferences": context.get("feedingType"),
            "birth_experience": context.get("birthType"),
            "cultural_preferences": context.get("culturalPreferences", {}),
            "medical_guidelines": context.get("medicalGuidelines", {}),
            "doctor_notes": context.get("doctorNotes", "")
        }
    
    def _build_personalization_instructions(
        self,
        profile: Dict[str, Any],
        context: Dict[str, Any],
        query: str
    ) -> str:
        """Build personalization instructions for AI prompt"""
        instructions = []
        
        # Response style
        style = profile["response_style"]
        if style == "brief":
            instructions.append("- Keep responses concise and to the point (2-3 sentences max)")
        elif style == "detailed":
            instructions.append("- Provide comprehensive, detailed responses with explanations")
        else:
            instructions.append("- Provide balanced responses with key information")
        
        # Tone
        tone = profile["tone_preference"]
        if tone == "warm":
            instructions.append("- Use warm, empathetic, and supportive language")
        elif tone == "professional":
            instructions.append("- Use professional but friendly language")
        else:
            instructions.append("- Use casual, friendly language")
        
        # Detail level
        detail = profile["detail_level"]
        if detail == "minimal":
            instructions.append("- Focus on essential information only")
        elif detail == "comprehensive":
            instructions.append("- Include comprehensive information and context")
        
        # Baby stage
        baby_stage = profile["baby_stage"]
        if baby_stage != "unknown":
            stage_info = {
                "newborn_week1": "Baby is in first week - focus on immediate needs and reassurance",
                "newborn_week2": "Baby is in second week - focus on establishing routines",
                "newborn_month1": "Baby is in first month - focus on growth and development",
                "infant_month2_3": "Baby is 2-3 months - focus on emerging patterns",
                "infant_month4_6": "Baby is 4-6 months - focus on milestones",
                "infant_6plus": "Baby is 6+ months - focus on continued development"
            }
            if baby_stage in stage_info:
                instructions.append(f"- {stage_info[baby_stage]}")
        
        # Preferred topics
        if profile["preferred_topics"]:
            topics = ", ".join(profile["preferred_topics"])
            instructions.append(f"- User frequently asks about: {topics}")
        
        # Customizations
        customizations = profile["customizations"]
        if customizations.get("baby_name"):
            instructions.append(f"- Use baby's name: {customizations['baby_name']} when appropriate")
        
        if customizations.get("doctor_notes"):
            instructions.append(f"- Consider doctor's guidance: {customizations['doctor_notes'][:100]}")
        
        return "\n".join(instructions)
    
    async def update_personalization_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """
        Update user's personalization preferences
        
        Args:
            user_id: User identifier
            preferences: Dictionary of preferences to update
                {
                    "response_style": "brief" | "detailed" | "balanced",
                    "tone_preference": "warm" | "professional" | "casual",
                    "detail_level": "minimal" | "moderate" | "comprehensive",
                    "preferred_topics": List[str],
                    "customizations": Dict
                }
        """
        # Get current context
        context = await self.tracking_service.get_user_context(user_id, db)
        
        # Update with new preferences
        updated_context = {
            **context,
            **preferences
        }
        
        # Save updated context
        result = await self.tracking_service.update_user_context(user_id, updated_context, db)
        
        return {
            "message": "Personalization preferences updated",
            "preferences": preferences,
            "updated_at": datetime.utcnow().isoformat()
        }
