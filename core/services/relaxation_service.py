"""
Relaxation Service - Provides relaxation guides, breathing exercises, and calm tips
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import random

from utils.locale_loader import load_locale_file, load_locale_text


class RelaxationService:
    """
    Service for providing relaxation and calming resources
    
    This service provides:
    - Relaxation guides with step-by-step instructions
    - Breathing exercises for stress relief
    - Quick calm tips for immediate relief
    - Safety tips for postpartum mothers
    
    All content is available in multiple languages (English, Japanese).
    """
    
    def __init__(self):
        """
        Initialize the RelaxationService
        
        Sets up relaxation guides, breathing exercises, and calm tips
        in multiple languages.
        """
        self.relaxation_guides = {
            "en": [
                {
                    "title": "Quick Calm",
                    "steps": [
                        "Find a comfortable position",
                        "Close your eyes or soften your gaze",
                        "Take 3 deep breaths",
                        "Notice how your body feels",
                        "Release any tension you notice",
                        "Take 3 more deep breaths",
                        "Open your eyes when ready"
                    ],
                    "duration": "2-3 minutes"
                },
                {
                    "title": "Body Scan",
                    "steps": [
                        "Lie down or sit comfortably",
                        "Start by noticing your toes",
                        "Slowly move your attention up your body",
                        "Notice any tension or discomfort",
                        "Breathe into those areas",
                        "Release tension as you exhale",
                        "Continue up to your head",
                        "Take a moment to feel your whole body"
                    ],
                    "duration": "5-10 minutes"
                }
            ]
        }
        
        self.breathing_exercises = {
            "en": [
                {
                    "name": "4-7-8 Breathing",
                    "description": "Calming breathing technique",
                    "steps": [
                        "Inhale through your nose for 4 counts",
                        "Hold your breath for 7 counts",
                        "Exhale through your mouth for 8 counts",
                        "Repeat 3-4 times"
                    ],
                    "benefits": "Reduces anxiety, promotes relaxation"
                },
                {
                    "name": "Box Breathing",
                    "description": "Simple and effective breathing pattern",
                    "steps": [
                        "Inhale for 4 counts",
                        "Hold for 4 counts",
                        "Exhale for 4 counts",
                        "Hold for 4 counts",
                        "Repeat 4-5 times"
                    ],
                    "benefits": "Calms nervous system, improves focus"
                },
                {
                    "name": "Deep Belly Breathing",
                    "description": "Basic relaxation breathing",
                    "steps": [
                        "Place one hand on your chest, one on your belly",
                        "Breathe in slowly through your nose",
                        "Feel your belly rise",
                        "Exhale slowly through your mouth",
                        "Feel your belly fall",
                        "Repeat 5-10 times"
                    ],
                    "benefits": "Activates relaxation response"
                }
            ]
        }
        
        self.quick_calm_tips = {
            "en": [
                "Take 3 deep breaths right now",
                "Place your hand on your heart and breathe",
                "Name 5 things you can see around you",
                "Drink a glass of water slowly",
                "Stretch your arms up and take a deep breath",
                "Close your eyes and count to 10",
                "Put on calming music",
                "Step outside for fresh air if possible",
                "Remind yourself: 'This moment will pass'",
                "You're doing your best, and that's enough"
            ]
        }

        self._ja_safety_tips: List[str] = []
        self._ja_emergency_message = ""

        ja_content = load_locale_file("ja", "relaxation")
        if ja_content.get("relaxation_guides"):
            self.relaxation_guides["ja"] = ja_content["relaxation_guides"]
        if ja_content.get("breathing_exercises"):
            self.breathing_exercises["ja"] = ja_content["breathing_exercises"]
        if ja_content.get("quick_calm_tips"):
            self.quick_calm_tips["ja"] = ja_content["quick_calm_tips"]
        self._ja_safety_tips = ja_content.get("safety_tips", [])
        self._ja_emergency_message = ja_content.get(
            "emergency_message",
            "If this is a medical emergency, call emergency services immediately.",
        )
    
    def get_relaxation_guide(
        self,
        language: str = "en",
        guide_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a relaxation guide
        
        Args:
            language: Language code
            guide_type: Specific guide type (optional)
        
        Returns:
            Relaxation guide with steps
        """
        guides = self.relaxation_guides.get(language, self.relaxation_guides["en"])
        
        if guide_type:
            # Find specific guide
            for guide in guides:
                if guide["title"].lower() == guide_type.lower():
                    return {
                        "guide": guide,
                        "timestamp": datetime.utcnow().isoformat()
                    }
        
        # Return random guide
        guide = random.choice(guides)
        return {
            "guide": guide,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_breathing_exercise(
        self,
        language: str = "en",
        exercise_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a breathing exercise
        
        Args:
            language: Language code
            exercise_type: Specific exercise type (optional)
        
        Returns:
            Breathing exercise with steps
        """
        exercises = self.breathing_exercises.get(language, self.breathing_exercises["en"])
        
        if exercise_type:
            # Find specific exercise
            for exercise in exercises:
                if exercise["name"].lower() == exercise_type.lower():
                    return {
                        "exercise": exercise,
                        "timestamp": datetime.utcnow().isoformat()
                    }
        
        # Return random exercise
        exercise = random.choice(exercises)
        return {
            "exercise": exercise,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_quick_calm_tips(
        self,
        language: str = "en",
        count: int = 3
    ) -> Dict[str, Any]:
        """
        Get quick calm tips
        
        Args:
            language: Language code
            count: Number of tips to return
        
        Returns:
            List of quick calm tips
        """
        tips = self.quick_calm_tips.get(language, self.quick_calm_tips["en"])
        
        # Return random selection
        selected_tips = random.sample(tips, min(count, len(tips)))
        
        return {
            "tips": selected_tips,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_safety_tips(
        self,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Get safety tips for postpartum mothers
        
        Args:
            language: Language code
        
        Returns:
            Safety tips
        """
        safety_tips = {
            "en": [
                "If you experience heavy bleeding (soaking a pad in less than an hour), contact your healthcare provider immediately",
                "If you have a fever above 100.4°F (38°C), seek medical attention",
                "If you experience severe abdominal pain, contact your healthcare provider",
                "If you notice signs of infection (redness, warmth, pus), seek medical help",
                "If you have thoughts of harming yourself or your baby, seek immediate help",
                "If you experience severe mood changes or depression, reach out for support",
                "If your baby has a fever, difficulty breathing, or won't wake up, seek emergency care",
                "If your baby shows signs of dehydration (dry mouth, no tears, fewer wet diapers), contact pediatrician"
            ],
        }
        if self._ja_safety_tips:
            safety_tips["ja"] = self._ja_safety_tips
        
        tips = safety_tips.get(language, safety_tips["en"])
        emergency_message = load_locale_text(
            language if language in ("en", "ja") else "en",
            "safety_reminder",
        ) or "If this is a medical emergency, call emergency services immediately."
        if language == "ja" and self._ja_emergency_message:
            emergency_message = self._ja_emergency_message
        
        return {
            "tips": tips,
            "timestamp": datetime.utcnow().isoformat(),
            "emergency_message": emergency_message,
        }

