"""
Information Buffer Layer - Processes and filters AI responses before showing to users
Acts as a safety and quality control layer
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import re
from services.suggestion_validator import SuggestionValidator
from services.medical_safety_rules import MedicalSafetyRules
from services.companion_layer import CompanionLayer
from utils.locale_loader import load_locale_file


class InformationBuffer:
    """
    Information Buffer Layer - Processes all AI output before user sees it
    
    Functions:
    1. Validate all suggestions and responses
    2. Add safety disclaimers
    3. Format for readability
    4. Add companion layer (empathetic framing)
    5. Filter sensitive information
    6. Ensure compliance with medical guidelines
    """
    
    def __init__(self):
        self.validator = SuggestionValidator()
        self.companion = CompanionLayer()

    def _buffer_locale(self, language: str) -> Dict[str, Any]:
        lang = language if language in ("en", "ja") else "en"
        return load_locale_file(lang, "information_buffer")
    
    def process_chat_response(
        self,
        raw_response: Dict[str, Any],
        context: Dict[str, Any],
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Process raw AI chat response through buffer layer
        
        Returns:
            {
                "response": str (processed),
                "suggestions": List[str] (validated),
                "red_flags": List[str] (validated),
                "safety_metadata": Dict,
                "companion_added": bool
            }
        """
        processed = {
            "response": raw_response.get("text", ""),
            "suggestions": raw_response.get("suggestions", []),
            "red_flags": raw_response.get("red_flags", []),
            "safety_metadata": {},
            "companion_added": False
        }
        
        # Step 1: Validate main response
        response_validation = self._validate_response(
            processed["response"], context, language
        )
        processed["response"] = response_validation["processed_text"]
        processed["safety_metadata"]["response_validation"] = response_validation
        
        # Step 2: Validate and process suggestions
        if processed["suggestions"]:
            validated_suggestions = self.validator.validate_suggestions(
                processed["suggestions"], context, "general"
            )
            
            # Filter and format suggestions
            safe_suggestions = []
            for vs in validated_suggestions:
                if vs["is_valid"] or vs["safety_score"] > 0.5:
                    safe_suggestions.append(vs["validated_suggestion"])
            
            # Add companion transition
            if safe_suggestions:
                safe_suggestions = self.companion.add_transition_phrase(
                    safe_suggestions, language
                )
            
            processed["suggestions"] = safe_suggestions
            processed["safety_metadata"]["suggestions_validation"] = {
                "total": len(validated_suggestions),
                "safe": len(safe_suggestions),
                "filtered": len(validated_suggestions) - len(safe_suggestions)
            }
        
        # Step 3: Validate red flags
        if processed["red_flags"]:
            validated_flags = []
            for flag in processed["red_flags"]:
                # Ensure red flags have proper urgency indicators
                if not any(word in flag.lower() for word in ["emergency", "urgent", "immediately", "call"]):
                    flag = f"⚠️ URGENT: {flag}"
                validated_flags.append(flag)
            processed["red_flags"] = validated_flags
        
        # Step 4: Add companion layer to main response
        if not response_validation.get("has_companion"):
            processed["response"] = self.companion.wrap_response(
                processed["response"], context, language
            )
            processed["companion_added"] = True
        
        # Step 5: Add safety disclaimers if needed
        required_disclaimers = MedicalSafetyRules.requires_disclaimer(processed["response"])
        if required_disclaimers:
            processed["response"] = MedicalSafetyRules.add_required_disclaimers(
                processed["response"], required_disclaimers
            )
        
        # Step 6: Format for readability
        processed["response"] = self._format_for_readability(
            processed["response"], language
        )
        
        return processed
    
    def process_crisis_response(
        self,
        raw_response: Dict[str, Any],
        context: Dict[str, Any],
        language: str = "en"
    ) -> Dict[str, Any]:
        """Process crisis mode response with extra safety checks"""
        processed = self.process_chat_response(raw_response, context, language)
        
        # Crisis mode: extra validation for actions
        if processed.get("actions"):
            validated_actions = self.validator.validate_suggestions(
                processed["actions"], context, "crisis"
            )
            
            # Only keep high-safety actions in crisis mode
            safe_actions = [
                va["validated_suggestion"] for va in validated_actions
                if va["is_valid"] and va["safety_score"] > 0.7
            ]
            
            processed["actions"] = safe_actions
            processed["safety_metadata"]["crisis_actions_validated"] = True
        
        # Ensure emergency contact info is prominent
        if processed.get("red_flags"):
            locale = self._buffer_locale(language)
            processed["red_flags"].insert(0, locale.get(
                "emergency_red_flag",
                "If this is a medical emergency, call emergency services immediately.",
            ))
        
        return processed
    
    def process_tracking_analysis(
        self,
        raw_analysis: Dict[str, Any],
        context: Dict[str, Any],
        language: str = "en"
    ) -> Dict[str, Any]:
        """Process tracking analysis with validation"""
        processed = raw_analysis.copy()
        
        # Validate recommendations
        if processed.get("recommendations"):
            validated = self.validator.validate_suggestions(
                processed["recommendations"], context, "tracking"
            )
            processed["recommendations"] = [
                v["validated_suggestion"] for v in validated
                if v["is_valid"] or v["safety_score"] > 0.6
            ]
        
        # Validate insights
        if processed.get("insights"):
            validated = self.validator.validate_suggestions(
                processed["insights"], context, "general"
            )
            processed["insights"] = [
                v["validated_suggestion"] for v in validated
                if v["is_valid"] or v["safety_score"] > 0.6
            ]
        
        return processed
    
    def _validate_response(
        self,
        text: str,
        context: Dict[str, Any],
        language: str
    ) -> Dict[str, Any]:
        """Validate main response text"""
        result = {
            "processed_text": text,
            "is_safe": True,
            "has_companion": False,
            "warnings": []
        }
        
        # Check for forbidden patterns
        violations = MedicalSafetyRules.check_forbidden_patterns(text)
        if violations:
            result["is_safe"] = False
            result["warnings"].extend([r for _, r in violations])
            locale = self._buffer_locale(language)
            result["processed_text"] = locale.get(
                "medical_advice_blocked",
                "I'm unable to provide specific medical advice. "
                "Please consult your healthcare provider for medical concerns.",
            )
            return result
        
        # Check for required disclaimers
        required = MedicalSafetyRules.requires_disclaimer(text)
        if required:
            result["processed_text"] = MedicalSafetyRules.add_required_disclaimers(
                text, required
            )
        
        # Check if companion layer already present
        locale = self._buffer_locale(language)
        companion_indicators = locale.get("companion_indicators", [
            "I understand", "You're doing", "That sounds", "I hear you"
        ])
        
        result["has_companion"] = any(
            indicator in result["processed_text"] 
            for indicator in companion_indicators
        )
        
        return result
    
    def _format_for_readability(
        self,
        text: str,
        language: str
    ) -> str:
        """Format text for better readability"""
        # Ensure proper spacing
        text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 newlines
        
        # Ensure sentences end properly
        if language == "ja":
            # Japanese doesn't need periods, but ensure proper spacing
            text = re.sub(r'([。！？])([^\s])', r'\1 \2', text)
        else:
            # English: ensure sentences end with punctuation
            text = re.sub(r'([a-z])([A-Z])', r'\1. \2', text)
        
        return text.strip()
    
    def filter_sensitive_info(
        self,
        text: str,
        user_context: Dict[str, Any]
    ) -> str:
        """Filter out any sensitive information that shouldn't be shown"""
        # Remove any potential PII if needed
        # This is a placeholder for future enhancement
        
        # For now, just return as-is
        return text
    
    def add_contextual_notes(
        self,
        response: str,
        context: Dict[str, Any],
        language: str
    ) -> str:
        """Add contextual notes based on user's situation"""
        notes = []
        
        # Baby age context
        if context.get("baby_age_days"):
            days = context["baby_age_days"]
            if days < 7:
                locale = self._buffer_locale(language)
                notes.append(locale.get(
                    "baby_new_note",
                    "Remember, your baby is very new - everything is still adjusting!",
                ))
        
        # Sleep context
        if context.get("sleep_hours_avg") and context["sleep_hours_avg"] < 4:
            locale = self._buffer_locale(language)
            notes.append(locale.get(
                "low_sleep_note",
                "I notice you're getting very little sleep. Please prioritize rest when possible.",
            ))
        
        if notes:
            return f"{response}\n\n💡 {' '.join(notes)}"
        
        return response
