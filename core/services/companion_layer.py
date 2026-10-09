"""
AI Companion Layer - Provides empathetic, warm interaction layer
Acts as a buffer between raw AI responses and users
"""

from typing import Dict, List, Any, Optional

from utils.locale_loader import load_locale_file
from datetime import datetime
import re


class CompanionLayer:
    """Adds empathetic, warm tone to AI responses"""
    
    def __init__(self):
        self.companion_phrases = {
            "en": {
                "greeting": [
                    "Hi there! 💙",
                    "Hello! I'm here for you.",
                    "Hey! How can I help you today?"
                ],
                "acknowledgment": [
                    "I understand that can be really tough.",
                    "That sounds challenging. You're doing great.",
                    "I hear you. Let's work through this together.",
                    "That must be really hard. You're not alone."
                ],
                "reassurance": [
                    "You're doing an amazing job, mama.",
                    "Remember, you're stronger than you think.",
                    "It's okay to feel overwhelmed. That's normal.",
                    "You're not failing - you're learning and adapting.",
                    "You're doing great. Every day you're doing your best.",
                    "You're handling this beautifully. Give yourself credit.",
                    "You're doing everything you can, and that's enough.",
                    "You're a wonderful mother. Trust yourself.",
                    "You're doing your best, and that's all that matters.",
                    "You're stronger than you know. Keep going."
                ],
                "positive_feedback": [
                    "You're doing great!",
                    "You're doing your best, and that's enough.",
                    "You're handling this so well.",
                    "You're doing everything right.",
                    "You're a wonderful mother.",
                    "You're doing an incredible job.",
                    "You're doing perfectly fine.",
                    "You're doing better than you think.",
                    "You're doing exactly what you need to do.",
                    "You're doing great, mama. Keep it up."
                ],
                "transition": [
                    "Here's what might help:",
                    "Let me share some things that could help:",
                    "Here are some suggestions:",
                    "Based on what you've told me:"
                ],
                "closing": [
                    "Take care of yourself too, okay? 💚",
                    "Remember to breathe. You've got this.",
                    "You're doing great. One step at a time.",
                    "I'm here whenever you need me."
                ]
            }
        }
        ja_phrases = load_locale_file("ja", "companion_phrases")
        if ja_phrases:
            self.companion_phrases["ja"] = ja_phrases
    
    def wrap_response(
        self,
        raw_response: str,
        context: Dict[str, Any],
        language: str = "en"
    ) -> str:
        """
        Wrap AI response with companion layer - adds empathetic framing
        """
        phrases = self.companion_phrases.get(language, self.companion_phrases["en"])
        
        # Detect emotional tone of the query/response
        is_urgent = self._detect_urgency(raw_response)
        is_emotional = self._detect_emotional_content(raw_response, context)
        
        # Build companion-wrapped response
        wrapped_parts = []
        
        # Add acknowledgment if emotional
        if is_emotional:
            import random
            wrapped_parts.append(random.choice(phrases["acknowledgment"]))
        
        # Add reassurance if needed
        if is_urgent or is_emotional:
            import random
            wrapped_parts.append(random.choice(phrases["reassurance"]))
        
        # Add positive feedback based on context
        mood_level = context.get("mood_level", "")
        if mood_level in ["very_low", "low"]:
            import random
            if "positive_feedback" in phrases:
                wrapped_parts.append(random.choice(phrases["positive_feedback"]))
        
        # Add the actual response
        wrapped_parts.append(raw_response)
        
        # Add closing with encouragement if needed
        import random
        closing = random.choice(phrases["closing"])
        if is_emotional or mood_level in ["very_low", "low"]:
            # Use more encouraging closing
            if "positive_feedback" in phrases:
                closing = random.choice(phrases["positive_feedback"]) + " " + closing
        wrapped_parts.append(closing)
        
        return "\n\n".join(wrapped_parts)
    
    def add_transition_phrase(
        self,
        suggestions: List[str],
        language: str = "en"
    ) -> List[str]:
        """Add transition phrases to suggestions"""
        phrases = self.companion_phrases.get(language, self.companion_phrases["en"])
        transition = phrases["transition"][0]
        
        if suggestions:
            return [transition] + suggestions
        return suggestions
    
    def _detect_urgency(self, text: str) -> bool:
        """Detect if response contains urgent content"""
        urgent_keywords = ["emergency", "urgent", "immediately", "call", "seek", "danger"]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in urgent_keywords)
    
    def _detect_emotional_content(self, text: str, context: Dict[str, Any]) -> bool:
        """Detect if response is addressing emotional concerns"""
        emotional_keywords = ["overwhelmed", "anxious", "worried", "scared", "tired", "exhausted", "difficult", "hard", "struggling"]
        text_lower = text.lower()
        
        # Check text
        if any(keyword in text_lower for keyword in emotional_keywords):
            return True
        
        # Check context for emotional indicators
        if context.get("mood_level") in ["very_low", "low"]:
            return True
        
        return False
    
    def get_encouragement_phrase(self, language: str = "en", intensity: str = "normal") -> str:
        """
        Get encouragement phrase based on intensity
        
        Args:
            language: Language code
            intensity: "low", "normal", "high" - based on user's emotional state
        
        Returns:
            Encouragement phrase
        """
        phrases = self.companion_phrases.get(language, self.companion_phrases["en"])
        import random
        
        if intensity == "high" and "positive_feedback" in phrases:
            return random.choice(phrases["positive_feedback"])
        elif intensity == "low" and "reassurance" in phrases:
            return random.choice(phrases["reassurance"])
        else:
            # Normal intensity - mix of both
            if "positive_feedback" in phrases:
                return random.choice(phrases["positive_feedback"])
            elif "reassurance" in phrases:
                return random.choice(phrases["reassurance"])
            else:
                return ""