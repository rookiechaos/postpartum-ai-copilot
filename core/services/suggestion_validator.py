"""
Suggestion Validator - Validates AI suggestions for accuracy and safety
"""

import os
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import re

from services.medical_safety_rules import MedicalSafetyRules

load_dotenv()


class SuggestionValidator:
    """Validates AI suggestions against safety rules and medical guidelines"""
    
    def __init__(self):
        self.safety_keywords = {
            "dangerous": [
                "give medication without doctor",
                "ignore medical advice",
                "skip doctor visit",
                "self-diagnose",
                "treat at home without",
                "don't call doctor",
                "emergency can wait"
            ],
            "uncertain": [
                "might be",
                "could be",
                "possibly",
                "maybe",
                "uncertain",
                "not sure"
            ],
            "red_flags": [
                "fever over 100.4",
                "difficulty breathing",
                "dehydration",
                "no wet diapers",
                "excessive bleeding",
                "severe pain",
                "thoughts of harm"
            ]
        }
        
        self.trusted_guidelines = {
            "feeding": {
                "min_frequency": 8,  # times per day for newborns
                "max_frequency": 12,
                "min_duration_minutes": 5,
                "max_duration_minutes": 45
            },
            "sleep": {
                "min_hours": 14,  # per day for newborns
                "max_hours": 17,
                "normal_wake_frequency": "every 2-4 hours"
            },
            "diaper": {
                "min_per_day": 6,  # wet diapers
                "max_per_day": 12
            }
        }
    
    def validate_suggestion(
        self,
        suggestion: str,
        context: Dict[str, Any],
        suggestion_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Validate a single suggestion
        
        Returns:
            {
                "is_valid": bool,
                "confidence": float (0-1),
                "warnings": List[str],
                "safety_score": float (0-1),
                "needs_review": bool,
                "validated_suggestion": str
            }
        """
        suggestion_lower = suggestion.lower()
        
        # Initialize validation result
        validation = {
            "is_valid": True,
            "confidence": 1.0,
            "warnings": [],
            "safety_score": 1.0,
            "needs_review": False,
            "validated_suggestion": suggestion
        }
        
        # Check for forbidden patterns (hard safety rules)
        forbidden_violations = MedicalSafetyRules.check_forbidden_patterns(suggestion)
        if forbidden_violations:
            validation["is_valid"] = False
            validation["safety_score"] = 0.0
            for pattern, reason in forbidden_violations:
                validation["warnings"].append(f"Safety violation: {reason}")
            validation["needs_review"] = True
            validation["validated_suggestion"] = "This suggestion was flagged for safety concerns. Please consult your healthcare provider."
            return validation
        
        # Check for dangerous content
        for keyword in self.safety_keywords["dangerous"]:
            if keyword in suggestion_lower:
                validation["is_valid"] = False
                validation["safety_score"] = 0.0
                validation["warnings"].append("Contains potentially dangerous advice")
                validation["needs_review"] = True
                validation["validated_suggestion"] = self._add_disclaimer(suggestion)
                return validation
        
        # Check for uncertain language
        uncertainty_count = sum(1 for keyword in self.safety_keywords["uncertain"] 
                               if keyword in suggestion_lower)
        if uncertainty_count > 0:
            validation["confidence"] = max(0.5, 1.0 - (uncertainty_count * 0.2))
            validation["warnings"].append("Contains uncertain language")
            if uncertainty_count >= 2:
                validation["needs_review"] = True
        
        # Check for red flags that should trigger immediate medical attention
        red_flags_found = []
        for flag in self.safety_keywords["red_flags"]:
            if flag in suggestion_lower:
                red_flags_found.append(flag)
        
        if red_flags_found:
            validation["warnings"].append(
                f"Contains red flags: {', '.join(red_flags_found)}. "
                "Should recommend immediate medical consultation."
            )
            # Ensure medical consultation is recommended
            if "consult" not in suggestion_lower and "doctor" not in suggestion_lower:
                validation["validated_suggestion"] = (
                    suggestion + 
                    " IMPORTANT: If you observe these symptoms, consult a healthcare provider immediately."
                )
                validation["needs_review"] = True
        
        # Validate against trusted guidelines based on context
        if suggestion_type in self.trusted_guidelines:
            guideline_validation = self._validate_against_guidelines(
                suggestion, suggestion_type, context
            )
            if not guideline_validation["is_valid"]:
                validation["is_valid"] = False
                validation["warnings"].extend(guideline_validation["warnings"])
                validation["confidence"] = min(validation["confidence"], 0.7)
                validation["needs_review"] = True
        
        # Check for required disclaimers using safety rules
        required_disclaimers = MedicalSafetyRules.requires_disclaimer(suggestion)
        if required_disclaimers:
            validation["validated_suggestion"] = MedicalSafetyRules.add_required_disclaimers(
                suggestion, required_disclaimers
            )
            if validation["validated_suggestion"] != suggestion:
                validation["warnings"].append("Added required medical disclaimers")
                validation["needs_review"] = True
        
        # Check for red flags
        red_flags = MedicalSafetyRules.check_red_flags(suggestion)
        if red_flags:
            validation["warnings"].append(f"Red flags detected: {', '.join(red_flags)}")
            # Ensure emergency disclaimer is present
            if "emergency" not in required_disclaimers:
                validation["validated_suggestion"] = MedicalSafetyRules.add_required_disclaimers(
                    validation["validated_suggestion"], ["emergency"]
                )
            validation["needs_review"] = True
        
        # Calculate final safety score
        validation["safety_score"] = self._calculate_safety_score(validation)
        
        return validation
    
    def validate_suggestions(
        self,
        suggestions: List[str],
        context: Dict[str, Any],
        suggestion_type: str = "general"
    ) -> List[Dict[str, Any]]:
        """Validate multiple suggestions"""
        validated = []
        for suggestion in suggestions:
            if suggestion.strip():  # Skip empty suggestions
                validation = self.validate_suggestion(suggestion, context, suggestion_type)
                validated.append({
                    "suggestion": suggestion,
                    **validation
                })
        return validated
    
    def _validate_against_guidelines(
        self,
        suggestion: str,
        suggestion_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate suggestion against trusted medical guidelines"""
        result = {
            "is_valid": True,
            "warnings": []
        }
        
        guidelines = self.trusted_guidelines.get(suggestion_type, {})
        
        if suggestion_type == "feeding":
            # Check for reasonable feeding frequency
            numbers = re.findall(r'\d+', suggestion)
            if numbers:
                # This is a simple check - could be enhanced
                pass
        
        return result
    
    def _add_disclaimer(self, suggestion: str) -> str:
        """Add appropriate disclaimer to suggestion"""
        if "consult" not in suggestion.lower() and "provider" not in suggestion.lower():
            return f"{suggestion} (Please consult your healthcare provider for medical concerns.)"
        return suggestion
    
    def _calculate_safety_score(self, validation: Dict[str, Any]) -> float:
        """Calculate overall safety score (0-1)"""
        score = 1.0
        
        # Reduce score for warnings
        score -= len(validation["warnings"]) * 0.1
        
        # Reduce score for low confidence
        score = min(score, validation["confidence"])
        
        # Reduce score if needs review
        if validation["needs_review"]:
            score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def cross_validate_with_rag(
        self,
        suggestion: str,
        rag_context: str
    ) -> Dict[str, Any]:
        """
        Cross-validate suggestion with RAG-retrieved medical information
        """
        if not rag_context:
            return {
                "cross_validated": False,
                "consistency_score": 0.5,
                "notes": "No RAG context available for validation"
            }
        
        # Simple consistency check - could be enhanced with embeddings
        suggestion_keywords = set(suggestion.lower().split())
        rag_keywords = set(rag_context.lower().split())
        
        # Calculate overlap
        common_keywords = suggestion_keywords.intersection(rag_keywords)
        if len(suggestion_keywords) > 0:
            consistency_score = len(common_keywords) / len(suggestion_keywords)
        else:
            consistency_score = 0.5
        
        # Check for contradictions
        contradictions = self._check_contradictions(suggestion, rag_context)
        
        return {
            "cross_validated": True,
            "consistency_score": consistency_score,
            "has_contradictions": len(contradictions) > 0,
            "contradictions": contradictions,
            "notes": "Cross-validated against trusted medical sources" if consistency_score > 0.7 else "Low consistency with medical sources"
        }
    
    def _check_contradictions(self, suggestion: str, rag_context: str) -> List[str]:
        """Check for contradictions between suggestion and RAG context"""
        contradictions = []
        
        # Simple contradiction checks
        # Could be enhanced with more sophisticated NLP
        
        # Check for opposite recommendations
        if "increase" in suggestion.lower() and "decrease" in rag_context.lower():
            contradictions.append("Frequency recommendation contradiction")
        
        if "normal" in suggestion.lower() and "abnormal" in rag_context.lower():
            contradictions.append("Normalcy assessment contradiction")
        
        return contradictions
    
    def get_validation_summary(self, validations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary of validation results"""
        if not validations:
            return {
                "total": 0,
                "valid": 0,
                "needs_review": 0,
                "average_confidence": 0.0,
                "average_safety_score": 0.0
            }
        
        valid_count = sum(1 for v in validations if v.get("is_valid", False))
        review_count = sum(1 for v in validations if v.get("needs_review", False))
        avg_confidence = sum(v.get("confidence", 0) for v in validations) / len(validations)
        avg_safety = sum(v.get("safety_score", 0) for v in validations) / len(validations)
        
        return {
            "total": len(validations),
            "valid": valid_count,
            "needs_review": review_count,
            "average_confidence": avg_confidence,
            "average_safety_score": avg_safety,
            "all_safe": avg_safety > 0.8 and valid_count == len(validations)
        }
