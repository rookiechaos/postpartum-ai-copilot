"""
Medical Safety Rules - Hard rules for content safety (avoiding medical advice/diagnosis in AI output).

This module ensures the app does not output medical advice, diagnosis, or treatment.
The product is a companion/support tool, not a medical device.
"""

from typing import Dict, List, Tuple


class MedicalSafetyRules:
    """Hard safety rules that must never be violated (content safety only; not medical certification)."""
    
    FORBIDDEN_PATTERNS = [
        # Medication advice without doctor consultation
        (r"give.*medication", "Never recommend medication without doctor consultation"),
        (r"take.*medicine", "Never recommend medication without doctor consultation"),
        (r"prescribe", "Cannot prescribe medications"),
        
        # Self-diagnosis
        (r"you have.*disease", "Cannot diagnose medical conditions"),
        (r"you are.*sick", "Cannot diagnose medical conditions"),
        (r"diagnosis is", "Cannot provide medical diagnosis"),
        
        # Ignoring medical advice
        (r"ignore.*doctor", "Never suggest ignoring medical advice"),
        (r"don't.*see.*doctor", "Always recommend seeing doctor when needed"),
        (r"skip.*appointment", "Never suggest skipping medical appointments"),
        
        # Dangerous practices
        (r"don't.*call.*emergency", "Always recommend calling emergency when needed"),
        (r"wait.*before.*calling", "Never delay emergency calls"),
        (r"home.*treatment.*only", "Never suggest home treatment for serious conditions"),
    ]
    
    REQUIRED_DISCLAIMERS = {
        "medical": "This is general information, not medical diagnosis. Consult your healthcare provider.",
        "medication": "Do not give any medication without consulting your healthcare provider.",
        "emergency": "If this is a medical emergency, call emergency services immediately.",
        "mental_health": "If you're experiencing thoughts of self-harm, contact emergency services or a mental health professional immediately."
    }
    
    RED_FLAG_TRIGGERS = [
        "fever over 100.4",
        "difficulty breathing",
        "no wet diapers for 6+ hours",
        "excessive bleeding",
        "severe pain",
        "unconscious",
        "seizure",
        "thoughts of harm",
        "thoughts of suicide"
    ]
    
    @classmethod
    def check_forbidden_patterns(cls, text: str) -> List[Tuple[str, str]]:
        """Check for forbidden patterns in text"""
        import re
        violations = []
        text_lower = text.lower()
        
        for pattern, reason in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, text_lower):
                violations.append((pattern, reason))
        
        return violations
    
    @classmethod
    def requires_disclaimer(cls, text: str) -> List[str]:
        """Check which disclaimers are required"""
        text_lower = text.lower()
        required = []
        
        # Check for medical claims
        medical_keywords = ["diagnosis", "treat", "cure", "condition", "disease", "illness"]
        if any(keyword in text_lower for keyword in medical_keywords):
            required.append("medical")
        
        # Check for medication mentions
        medication_keywords = ["medication", "medicine", "drug", "prescription", "pill"]
        if any(keyword in text_lower for keyword in medication_keywords):
            required.append("medication")
        
        # Check for emergency situations
        emergency_keywords = ["emergency", "urgent", "immediately", "call 911", "ambulance"]
        if any(keyword in text_lower for keyword in emergency_keywords):
            required.append("emergency")
        
        # Check for mental health concerns
        mental_health_keywords = ["self-harm", "suicide", "hurt myself", "end it"]
        if any(keyword in text_lower for keyword in mental_health_keywords):
            required.append("mental_health")
        
        return required
    
    @classmethod
    def check_red_flags(cls, text: str) -> List[str]:
        """Check for red flag triggers"""
        text_lower = text.lower()
        found_flags = []
        
        for flag in cls.RED_FLAG_TRIGGERS:
            if flag in text_lower:
                found_flags.append(flag)
        
        return found_flags
    
    @classmethod
    def add_required_disclaimers(cls, text: str, required: List[str]) -> str:
        """Add required disclaimers to text"""
        if not required:
            return text
        
        disclaimers = []
        for req in required:
            if req in cls.REQUIRED_DISCLAIMERS:
                disclaimer = cls.REQUIRED_DISCLAIMERS[req]
                if disclaimer not in text:
                    disclaimers.append(disclaimer)
        
        if disclaimers:
            return f"{text}\n\n{' '.join(disclaimers)}"
        
        return text
