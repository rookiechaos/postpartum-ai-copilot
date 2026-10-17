"""
NSFW Detector - Content moderation and safety filtering
"""

import os
from typing import Dict, Any, Optional, List
from enum import Enum
from config.settings import get_settings
from services.logging_service import logger
from utils.locale_loader import load_locale_file


class NSFWLevel(str, Enum):
    """NSFW detection levels"""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    UNSAFE = "unsafe"


class NSFWDetector:
    """Service for detecting NSFW and inappropriate content"""
    
    def __init__(self):
        settings = get_settings()
        self.provider = settings.ai_provider.lower()
        
        # Configuration - use settings instead of os.getenv()
        self.enabled = settings.nsfw_detection_enabled
        self.strict_mode = settings.nsfw_detection_strict
        
        # Initialize provider-specific clients
        self._openai_client = None
        if self.provider == "openai":
            try:
                from openai import AsyncOpenAI
                api_key = settings.openai_api_key
                if api_key:
                    self._openai_client = AsyncOpenAI(api_key=api_key)
            except (ImportError, AttributeError):
                logger.log_warning("OpenAI not available for NSFW detection")
        
        # Basic keyword list (as fallback)
        self._unsafe_keywords = self._load_keywords()
    
    def _load_keywords(self) -> List[str]:
        """Load unsafe keywords (basic fallback)"""
        # Basic inappropriate content keywords
        # In production, rely primarily on AI-based detection
        return [
            # Explicit content (basic list - AI moderation is preferred)
            # This is a minimal fallback list
        ]
    
    async def check(
        self,
        text: str,
        language: Optional[str] = None,
        check_type: str = "input"  # "input" or "output"
    ) -> Dict[str, Any]:
        """
        Check if text contains NSFW or inappropriate content
        
        Args:
            text: Text to check
            language: Optional language code for better detection
            check_type: Type of check ("input" for user input, "output" for AI response)
        
        Returns:
            Dict with detection results:
            {
                "safe": bool,
                "level": "safe" | "suspicious" | "unsafe",
                "reason": str,
                "blocked": bool,
                "categories": dict,  # Detailed category flags
                "confidence": float
            }
        """
        if not self.enabled:
            return {
                "safe": True,
                "level": NSFWLevel.SAFE.value,
                "reason": "NSFW detection disabled",
                "blocked": False,
                "categories": {},
                "confidence": 1.0
            }
        
        if not text or not text.strip():
            return {
                "safe": True,
                "level": NSFWLevel.SAFE.value,
                "reason": "Empty text",
                "blocked": False,
                "categories": {},
                "confidence": 1.0
            }
        
        # Try AI-based detection first (most reliable)
        if self.provider == "openai" and self._openai_client:
            try:
                result = await self._check_openai_moderation(text)
                return result
            except Exception as e:
                logger.log_warning("OpenAI moderation failed; using keyword checks", context={"action": "input_check"})
        
        # Fallback to keyword-based detection
        return await self._check_keywords(text, check_type)
    
    async def _check_openai_moderation(self, text: str) -> Dict[str, Any]:
        """Check using OpenAI Moderation API"""
        try:
            response = await self._openai_client.moderations.create(input=text)
            result = response.results[0]
            
            # Map OpenAI categories to our levels
            flagged = result.flagged
            
            # Get categories (handle both dict and object access)
            if hasattr(result.categories, 'model_dump'):
                categories = result.categories.model_dump()
            elif hasattr(result.categories, '__dict__'):
                categories = {k: getattr(result.categories, k, False) for k in dir(result.categories) if not k.startswith('_')}
            else:
                categories = {}
            
            if hasattr(result.category_scores, 'model_dump'):
                category_scores = result.category_scores.model_dump()
            elif hasattr(result.category_scores, '__dict__'):
                category_scores = {k: getattr(result.category_scores, k, 0.0) for k in dir(result.category_scores) if not k.startswith('_')}
            else:
                category_scores = {}
            
            # Determine level
            if flagged:
                # Check severity of flags
                high_severity = any([
                    categories.get("sexual", False),
                    categories.get("violence", False),
                    categories.get("self-harm", False),
                    categories.get("hate", False)
                ])
                
                level = NSFWLevel.UNSAFE if high_severity else NSFWLevel.SUSPICIOUS
                reason = "Content flagged by moderation API"
            else:
                level = NSFWLevel.SAFE
                reason = "Content passed moderation check"
            
            # Calculate confidence from category scores
            max_score = max(category_scores.values()) if category_scores else 0.0
            confidence = 1.0 - max_score
            
            return {
                "safe": not flagged or (not self.strict_mode and level == NSFWLevel.SUSPICIOUS),
                "level": level.value,
                "reason": reason,
                "blocked": flagged and (self.strict_mode or level == NSFWLevel.UNSAFE),
                "categories": categories,
                "category_scores": category_scores,
                "confidence": confidence
            }
        except Exception as e:
            logger.log_error(e, context={"action": "openai_moderation_check"})
            # Fallback to keyword check
            return await self._check_keywords(text, "input")
    
    async def _check_keywords(
        self,
        text: str,
        check_type: str = "input"
    ) -> Dict[str, Any]:
        """Fallback keyword-based detection"""
        text_lower = text.lower()
        
        # Check against unsafe keywords
        found_keywords = []
        for keyword in self._unsafe_keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
        
        if found_keywords:
            return {
                "safe": False,
                "level": NSFWLevel.UNSAFE.value,
                "reason": f"Inappropriate content detected: {', '.join(found_keywords[:3])}",
                "blocked": True,
                "categories": {"inappropriate": True},
                "confidence": 0.8
            }
        
        # Basic heuristics for suspicious content
        suspicious_patterns = [
            len(text) > 10000,  # Very long text might be spam
            text.count('http://') > 5 or text.count('https://') > 5,  # Too many links
        ]
        
        if any(suspicious_patterns):
            return {
                "safe": True,
                "level": NSFWLevel.SUSPICIOUS.value,
                "reason": "Content shows suspicious patterns",
                "blocked": False,
                "categories": {},
                "confidence": 0.6
            }
        
        # Default: safe
        return {
            "safe": True,
            "level": NSFWLevel.SAFE.value,
            "reason": "Content appears safe",
            "blocked": False,
            "categories": {},
            "confidence": 0.9
        }
    
    def should_block(self, result: Dict[str, Any]) -> bool:
        """Determine if content should be blocked based on result"""
        if not self.enabled:
            return False
        
        if result.get("blocked", False):
            return True
        
        if self.strict_mode and result.get("level") == NSFWLevel.SUSPICIOUS.value:
            return True
        
        return result.get("level") == NSFWLevel.UNSAFE.value
    
    def get_block_message(self, language: str = "en") -> str:
        """Get user-friendly block message"""
        lang = language if language in ("en", "ja") else "en"
        locale = load_locale_file(lang, "nsfw_detector")
        return locale.get(
            "block_message",
            "Your message contains inappropriate content and cannot be processed. "
            "Please ensure your message is appropriate and try again.",
        )


# Global detector instance
_nsfw_detector: Optional[NSFWDetector] = None


def get_nsfw_detector() -> NSFWDetector:
    """Get global NSFW detector instance"""
    global _nsfw_detector
    if _nsfw_detector is None:
        _nsfw_detector = NSFWDetector()
    return _nsfw_detector
