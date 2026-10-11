"""
AI Service - Handles all AI interactions via external API
Supports multiple providers: OpenAI, Claude, Gemini
"""

from typing import Dict, List, Any, Optional, AsyncGenerator
import json
import asyncio
from datetime import datetime

from services.ai_providers import get_ai_provider, AIProvider
from services.suggestion_validator import SuggestionValidator
from services.information_buffer import InformationBuffer
from services.companion_layer import CompanionLayer
from services.nsfw_detector import get_nsfw_detector
from config.settings import get_settings
from exceptions import AIServiceError, ValidationError
from services.logging_service import logger
from services.ai_errors import PUBLIC_AI_ERROR
from utils.locale_loader import load_locale_file, load_locale_text


class AIService:
    """Service for AI interactions with multi-provider support"""
    
    def __init__(self):
        settings = get_settings()
        
        # Allow test mode to skip AI provider initialization
        if settings.test_mode:
            # In test mode, create a mock provider
            self.provider = None
            self.provider_name = "test"
            self._base_system_prompt = self._get_system_prompt()
            self.system_prompt = self._base_system_prompt
            self.validator = SuggestionValidator()
            self.buffer = InformationBuffer()
            self.companion = CompanionLayer()
        else:
            try:
                self.provider: AIProvider = get_ai_provider()
                self.provider_name = settings.ai_provider.lower()
                self._base_system_prompt = self._get_system_prompt()
                self.system_prompt = self._base_system_prompt
                self.validator = SuggestionValidator()
                self.buffer = InformationBuffer()
                self.companion = CompanionLayer()
            except Exception as e:
                raise AIServiceError(f"Failed to initialize AI provider: {str(e)}")
    
    def _get_system_prompt(self, language: str = "en") -> str:
        """Get the system prompt for postpartum AI copilot"""
        language = language or "ja"
        if language.startswith("ja"):
            ja_prompt = load_locale_text("ja", "system_prompt")
            if ja_prompt:
                return ja_prompt

        return """You support postpartum families in Japan with everyday care records and preparing questions for human support.
Use plain language and short responses. Offer up to three practical next steps; ask one clarifying question at a time when needed.
Respect different feeding choices and family arrangements. Do not pressure users to keep records or praise them automatically.
Do not infer that everything is normal from incomplete records. State uncertainty plainly.
Do not diagnose, prescribe, assess clinical risk, give medical certainty percentages, or imply clinician review.
For medical concerns, encourage contacting an appropriate care professional.
In Japan, ambulance emergencies use 119. Do not delay urgent human help while asking questions or generating explanations.
Child telephone advice #8000 has prefecture-specific hours. #7119 coverage, eligible ages and hours vary; never claim it is universally available.
Do not invent local service names, fees, subsidy eligibility, hours, source links or review dates.
Do not claim that the app automatically alerts an organization, monitors a family, books an appointment or contacts emergency services.
Distinguish provided source information from your own explanation. Ask only for information necessary for the current question.
Keep health records, mental health notes and identity information private unless the user explicitly chooses what to share."""
    

    def _resolve_system_prompt(
        self,
        language: str = "en",
        system_prompt: Optional[str] = None,
    ) -> str:
        """Return per-request system prompt without mutating instance state."""
        if system_prompt is not None:
            return system_prompt
        return self._get_system_prompt(language)
    
    async def chat(
        self,
        query: str,
        context: Dict[str, Any],
        rag_context: str = "",
        user_id: str = "",
        language: str = "en",
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate AI response for chat with NSFW detection
        
        Checks both user input and AI response for inappropriate content
        """
        # NSFW detection on user input
        nsfw_detector = get_nsfw_detector()
        input_check = await nsfw_detector.check(query, language=language, check_type="input")
        
        if nsfw_detector.should_block(input_check):
            from exceptions import ValidationError
            raise ValidationError(nsfw_detector.get_block_message(language))
        
        # Get system prompt in user's language (per-request override supported)
        effective_prompt = self._resolve_system_prompt(language, system_prompt)
        
        # Build context-aware prompt
        user_context_str = self._format_user_context(context)
        
        # Language-specific instruction
        lang_instruction = ""
        if language == "ja":
            lang_instruction = "Please respond in Japanese."
        else:
            lang_instruction = "Please respond in English."
        
        messages = [
            {"role": "system", "content": effective_prompt + "\n\n" + lang_instruction},
            {
                "role": "user",
                "content": f"""Context about this mother and baby:
{user_context_str}

{('Relevant medical information: ' + rag_context) if rag_context else ''}

User's question: {query}

Please provide a helpful, empathetic response. Include:
1. Direct answer to the question
2. Step-by-step suggestions if applicable
3. Reassurance if appropriate
4. Red flags if relevant
5. Reminder to consult healthcare professionals if medical concern"""
            }
        ]
        
        try:
            # In test mode, return mock response
            if self.provider is None:
                return {
                    "text": "This is a test response. AI provider is not initialized in test mode.",
                    "suggestions": ["Test suggestion 1", "Test suggestion 2"],
                    "red_flags": [],
                    "provider": "test",
                    "validation": {
                        "suggestions_validated": 2,
                        "summary": {"all_safe": True, "average_confidence": 0.9},
                        "buffer_processed": True,
                        "companion_added": True
                    }
                }
            
            response = await self.provider.chat(
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            text = response["text"]
            
            # NSFW detection on AI response
            output_check = await nsfw_detector.check(text, language=language, check_type="output")
            
            if nsfw_detector.should_block(output_check):
                # If AI response contains inappropriate content, return safe fallback
                logger.log_warning(
                    f"AI response flagged as inappropriate for user {user_id}",
                    context={"level": output_check.get("level"), "reason": output_check.get("reason")}
                )
                text = "I apologize, but I cannot provide that type of response. How else can I help you with your postpartum journey?"
            
            # Parse response for suggestions and red flags
            suggestions = self._extract_suggestions(text)
            red_flags = self._extract_red_flags(text)
            
            # Process through information buffer layer
            raw_response = {
                "text": text,
                "suggestions": suggestions,
                "red_flags": red_flags
            }
            
            processed = self.buffer.process_chat_response(
                raw_response, context, language
            )
            
            # Get validation summary
            validation_summary = self.validator.get_validation_summary(
                processed.get("safety_metadata", {}).get("suggestions_validation", {})
            )
            
            return {
                "text": processed["response"],
                "suggestions": processed["suggestions"],
                "red_flags": processed["red_flags"],
                "provider": response.get("provider", self.provider_name),
                "validation": {
                    "suggestions_validated": processed.get("safety_metadata", {}).get("suggestions_validation", {}).get("total", 0),
                    "summary": validation_summary,
                    "buffer_processed": True,
                    "companion_added": processed.get("companion_added", False),
                    "nsfw_check": {
                        "input_safe": input_check.get("safe", True),
                        "output_safe": output_check.get("safe", True)
                    }
                }
            }
        except Exception as e:
            logger.log_error(e, context={"action": "ai_chat"})
            return {
                "text": "I'm having trouble connecting right now. Please try again or consult your healthcare provider for urgent concerns.",
                "suggestions": [],
                "red_flags": ["If this is a medical emergency, please contact emergency services immediately."],
                "error": PUBLIC_AI_ERROR,
                "provider": self.provider_name
            }
    
    async def chat_stream(
        self,
        query: str,
        context: Dict[str, Any],
        rag_context: str = "",
        user_id: str = "",
        language: str = "en",
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream AI response for real-time chat"""
        
        user_context_str = self._format_user_context(context)
        effective_prompt = self._resolve_system_prompt(language, system_prompt)
        
        messages = [
            {"role": "system", "content": effective_prompt},
            {
                "role": "user",
                "content": f"""Context about this mother and baby:
{user_context_str}

{('Relevant medical information: ' + rag_context) if rag_context else ''}

User's question: {query}"""
            }
        ]
        
        try:
            async for chunk in self.provider.chat_stream(
                messages=messages,
                temperature=0.7,
                max_tokens=500
            ):
                if chunk.get("type") == "error":
                    yield {"type": "error", "content": PUBLIC_AI_ERROR}
                else:
                    yield chunk
        except Exception as e:
            logger.log_error(e, context={"action": "ai_chat_stream"})
            yield {"type": "error", "content": PUBLIC_AI_ERROR}
    
    async def crisis_response(
        self,
        query: str,
        context: Dict[str, Any],
        recent_entries: List[Dict[str, Any]],
        language: str = "en",
        night_mode: bool = False,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate concise crisis mode response with night mode support"""
        
        user_context_str = self._format_user_context(context)
        recent_summary = self._format_recent_entries(recent_entries)
        base_prompt = self._resolve_system_prompt(language, system_prompt)
        
        # Night mode: even shorter, more gentle
        if night_mode:
            system_prompt_extra = "\n\nNIGHT MODE: Keep responses VERY SHORT (2-3 sentences), GENTLE, and CALM. Provide brief step-by-step guidance. Add safety reminder if needed."
        else:
            system_prompt_extra = "\n\nCRISIS MODE: Keep responses SHORT, ACTIONABLE, and CALM. Maximum 3-4 sentences."
        
        messages = [
            {"role": "system", "content": base_prompt + system_prompt_extra},
            {
                "role": "user",
                "content": f"""URGENT REQUEST - Keep response brief and actionable:

Context: {user_context_str}
Recent activity: {recent_summary}

Situation: {query}

Provide immediate, concise help. What should they try RIGHT NOW?
{"(Night mode: Keep it very brief and gentle)" if night_mode else ""}"""
            }
        ]
        
        try:
            response = await self.provider.chat(
                messages=messages,
                temperature=0.5,
                max_tokens=200
            )
            
            text = response["text"]
            
            # Extract actionable steps
            actions = self._extract_actions(text)
            red_flags = self._extract_red_flags(text)
            
            # Process through crisis buffer layer (extra safety)
            raw_crisis = {
                "text": text,
                "actions": actions,
                "red_flags": red_flags
            }
            
            processed = self.buffer.process_crisis_response(
                raw_crisis, context, language
            )
            
            # Add safety reminder for night mode
            safety_reminder = ""
            if night_mode:
                reminder = load_locale_text(language if language in ("en", "ja") else "en", "safety_reminder")
                if reminder:
                    safety_reminder = f"\n\n{reminder}"
            
            # Format actions as step-by-step for night mode
            formatted_actions = processed.get("actions", [])
            if night_mode and formatted_actions:
                # Make actions more concise for night mode
                formatted_actions = [f"{i+1}. {action}" for i, action in enumerate(formatted_actions[:3])]  # Max 3 steps
            
            return {
                "text": processed["response"] + safety_reminder,
                "actions": formatted_actions,
                "red_flags": processed["red_flags"],
                "provider": response.get("provider", self.provider_name),
                "night_mode": night_mode,
                "validation": {
                    "actions_validated": processed.get("safety_metadata", {}).get("crisis_actions_validated", False),
                    "buffer_processed": True
                }
            }
        except Exception as e:
            logger.log_error(e, context={"action": "ai_crisis_response"})
            return {
                "text": "I'm here to help. For immediate concerns, try: 1) Check if baby needs feeding/diaper change, 2) Try gentle rocking or swaddling, 3) If urgent medical concern, contact healthcare provider.",
                "actions": ["Check feeding/diaper", "Try calming techniques", "Contact healthcare if urgent"],
                "red_flags": ["If this is a medical emergency, call emergency services"],
                "error": PUBLIC_AI_ERROR,
                "provider": self.provider_name
            }
    
    async def analyze_tracking(
        self,
        entries: List[Dict[str, Any]],
        context: Dict[str, Any],
        anomalies: Optional[List[Dict[str, Any]]] = None,
        language: str = "en",
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze tracking data and provide insights with enhanced anomaly detection"""
        
        user_context_str = self._format_user_context(context)
        entries_summary = self._summarize_entries(entries)
        effective_prompt = self._resolve_system_prompt(language, system_prompt)
        
        # Include anomalies in the analysis if provided
        anomalies_text = ""
        if anomalies:
            anomalies_text = "\n\nDetected Anomalies:\n"
            for anomaly in anomalies:
                anomalies_text += f"- {anomaly.get('message', '')}\n"
        
        messages = [
            {"role": "system", "content": effective_prompt},
            {
                "role": "user",
                "content": f"""Analyze this tracking data and provide insights:

Context: {user_context_str}

Tracking Data (last 7 days):
{entries_summary}
{anomalies_text}

Please identify:
1. Patterns (e.g., feeding frequency, sleep patterns)
2. Insights (what's normal, what might need attention)
3. Recommendations (actionable suggestions)
4. Normalcy checks (reassurance about what's typical for this stage)
5. Specific anomaly alerts if any anomalies are detected

Always start with encouragement and positive reinforcement. Acknowledge the mother's efforts."""
            }
        ]
        
        try:
            response = await self.provider.chat(
                messages=messages,
                temperature=0.7,
                max_tokens=600
            )
            
            text = response["text"]
            
            # Parse structured response
            parsed = self._parse_analysis(text)
            
            # Add anomaly alerts if provided
            if anomalies:
                anomaly_alerts = []
                for anomaly in anomalies:
                    alert = self._get_anomaly_alert(anomaly.get("type"), language)
                    if alert:
                        anomaly_alerts.append(alert)
                
                if "insights" not in parsed:
                    parsed["insights"] = []
                parsed["insights"].extend(anomaly_alerts)
            
            return {
                **parsed,
                "provider": response.get("provider", self.provider_name)
            }
        except Exception as e:
            logger.log_error(e, context={"action": "ai_analyze_tracking"})
            return {
                "patterns": [],
                "insights": ["Unable to analyze data at this time. Please try again."],
                "recommendations": [],
                "normalcy_checks": [],
                "error": PUBLIC_AI_ERROR,
                "provider": self.provider_name
            }
    
    def _get_anomaly_alert(self, anomaly_type: Optional[str], language: str) -> Optional[str]:
        """Return localized anomaly alert message for the given type."""
        key_map = {
            "consecutive_low_sleep": "consecutive_low_sleep",
            "consecutive_low_mood": "consecutive_low_mood",
            "significant_weight_loss": "weight_loss",
        }
        if not anomaly_type or anomaly_type not in key_map:
            return None
        lang = language if language in ("en", "ja") else "en"
        locale = load_locale_file(lang, "data_analysis")
        template = locale.get("messages", {}).get(key_map[anomaly_type], "")
        if not template:
            return None
        return template.format(days=3, count=3, percent=5, hours=0)
    
    async def generate_tracking_summary(
        self,
        entries: List[Dict[str, Any]],
        context: Dict[str, Any],
        period: str = "daily",  # "daily" or "weekly"
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Generate AI-powered tracking summary
        
        Args:
            entries: Tracking entries
            context: User context
            period: "daily" or "weekly"
            language: Language code
        
        Returns:
            Summary with patterns, insights, encouragement, and anomalies
        """
        user_context_str = self._format_user_context(context)
        entries_summary = self._summarize_entries(entries)
        effective_prompt = self._resolve_system_prompt(language)
        
        period_text = "today" if period == "daily" else "this week"
        if language == "ja":
            period_text = "today" if period == "daily" else "this week"
        
        messages = [
            {"role": "system", "content": effective_prompt},
            {
                "role": "user",
                "content": f"""Generate a {period} summary for this mother's tracking data.

Context: {user_context_str}

Tracking Data ({period_text}):
{entries_summary}

Please provide:
1. Patterns identified (what's working well, what patterns you see)
2. Positive insights (acknowledge what's going well)
3. Gentle observations (things to watch, but frame positively)
4. Encouragement (specific positive reinforcement about their efforts)
5. Actionable suggestions (if any, keep them simple and supportive)

Always start with encouragement: "You're doing great!" or similar.
Be warm, supportive, and acknowledge their efforts.
If you notice any concerns, frame them gently and suggest when to consult healthcare providers."""
            }
        ]
        
        try:
            response = await self.provider.chat(
                messages=messages,
                temperature=0.7,
                max_tokens=800
            )
            
            text = response["text"]
            
            # Parse the summary
            return {
                "summary_text": text,
                "period": period,
                "timestamp": datetime.now().isoformat(),
                "provider": response.get("provider", self.provider_name)
            }
        except Exception as e:
            logger.log_error(e, context={"action": "ai_tracking_summary"})
            return {
                "summary_text": f"Unable to generate {period} summary at this time. You're doing great, keep tracking!",
                "period": period,
                "timestamp": datetime.now().isoformat(),
                "error": PUBLIC_AI_ERROR,
                "provider": self.provider_name
            }
    
    async def analyze_emotional_state(
        self,
        current_checkin: Dict[str, Any],
        mood_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze emotional check-in for risk detection"""
        
        mood_summary = self._summarize_mood_history(mood_history)
        language = current_checkin.get("language", "ja")
        base_prompt = self._resolve_system_prompt(language)
        
        messages = [
            {"role": "system", "content": base_prompt + "\n\nHelp the user reflect on their feelings and prepare questions for a professional. Do not diagnose or claim to determine clinical risk. Be gentle and supportive."},
            {
                "role": "user",
                "content": f"""Current emotional check-in:
- Overwhelmed: {current_checkin.get('overwhelmed_level', 'N/A')}/10
- Anxiety: {current_checkin.get('anxiety_level', 'N/A')}/10
- Support: {current_checkin.get('support_level', 'N/A')}/10
- Notes: {current_checkin.get('notes', 'None')}

Recent mood history:
{mood_summary}

Offer a short supportive reflection and up to three practical next steps.
Encourage contacting a trusted person or care professional when support is needed.
Use Japanese for Japanese-language requests. The user is in Japan; never invent local contacts, fees or service hours."""
            }
        ]
        
        try:
            response = await self.provider.chat(
                messages=messages,
                temperature=0.5,
                max_tokens=400
            )
            
            text = response["text"]
            
            parsed = self._parse_emotional_analysis(text, current_checkin)
            
            # Validate suggestions
            validated_suggestions = []
            if parsed.get("suggestions"):
                validated_suggestions = self.validator.validate_suggestions(
                    parsed["suggestions"], {}, suggestion_type="mental_health"
                )
                parsed["suggestions"] = [
                    vs["validated_suggestion"] for vs in validated_suggestions
                    if vs["is_valid"] or vs["safety_score"] > 0.5
                ]
            
            return {
                **parsed,
                "provider": response.get("provider", self.provider_name),
                "validation": {
                    "suggestions_validated": len(validated_suggestions),
                    "risk_assessment_validated": False
                },
                "analysis_available": True,
            }
        except Exception as e:
            logger.log_error(e, context={"action": "ai_emotional_state"})
            return {
                "assessment": "現在、回答を取得できません。必要なときは身近な人や専門家に相談してください。" if language.startswith("ja") else "A reflection response is unavailable. Please try again or contact a care professional for support.",
                "risk_level": "unknown",
                "analysis_available": False,
                "suggestions": [],
                "escalation_needed": None,
                "resources": ["かかりつけの医療機関・市区町村の保健相談窓口", "日本で救急車が必要な場合は119"] if language.startswith("ja") else ["Your usual care provider or municipal health support service", "In Japan, call 119 if you need an ambulance"],
                "error": PUBLIC_AI_ERROR,
                "provider": self.provider_name
            }
    
    def _format_user_context(self, context: Dict[str, Any]) -> str:
        """Format user context for prompts"""
        parts = []
        if context.get("baby_age_days"):
            parts.append(f"Baby age: {context['baby_age_days']} days old")
        elif context.get("babyAge"):
            ranges = {"0-7": "0–7 days", "1-2": "1–2 weeks", "2-4": "2–4 weeks", "1-2m": "1–2 months", "2-3m": "2–3 months", "3+": "3 months or older"}
            parts.append(f"Baby age range (not an exact age): {ranges.get(context['babyAge'], context['babyAge'])}")
        birth_type = context.get("birth_type") or context.get("birthType")
        feeding_type = context.get("feeding_type") or context.get("feedingType")
        if birth_type:
            parts.append(f"Birth type: {birth_type}")
        if feeding_type:
            parts.append(f"Feeding: {feeding_type}")
        if context.get("sleep_hours_avg"):
            parts.append(f"Average sleep: {context['sleep_hours_avg']} hours")
        return "\n".join(parts) if parts else "No specific context available"
    
    def _format_recent_entries(self, entries: List[Dict[str, Any]]) -> str:
        """Format recent tracking entries"""
        if not entries:
            return "No recent entries"
        summary = []
        for entry in entries[-5:]:  # Last 5 entries
            entry_type = entry.get("entry_type", "")
            timestamp = entry.get("timestamp", "")
            summary.append(f"- {entry_type} at {timestamp}")
        return "\n".join(summary)
    
    def _summarize_entries(self, entries: List[Dict[str, Any]]) -> str:
        """Summarize tracking entries for analysis"""
        if not entries:
            return "No tracking data available"
        
        # Count by type
        counts = {}
        for entry in entries:
            entry_type = entry.get("entry_type", "unknown")
            counts[entry_type] = counts.get(entry_type, 0) + 1
        
        summary = f"Total entries: {len(entries)}\n"
        for entry_type, count in counts.items():
            summary += f"- {entry_type}: {count} entries\n"
        
        return summary
    
    def _summarize_mood_history(self, mood_history: List[Dict[str, Any]]) -> str:
        """Summarize mood history"""
        if not mood_history:
            return "No mood history available"
        
        moods = [entry.get("mood_level", "unknown") for entry in mood_history]
        return f"Recent moods: {', '.join(moods[-7:])}"  # Last 7 moods
    
    def _extract_suggestions(self, text: str) -> List[str]:
        """Extract actionable suggestions from response"""
        suggestions = []
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith(("1.", "2.", "3.", "-", "•")) and len(line) > 3:
                suggestions.append(line.lstrip("1234567890.-• ").strip())
        return suggestions[:5]  # Max 5 suggestions
    
    def _extract_red_flags(self, text: str) -> List[str]:
        """Extract red flags from response"""
        red_flags = []
        text_lower = text.lower()
        red_flag_keywords = ["emergency", "urgent", "immediately", "call", "seek", "danger", "warning", "緊急", "救急", "119", "すぐに受診", "至急", "意識がない", "呼吸困難"]
        
        import re
        sentences = re.split(r"[。.!?\n]", text)
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in red_flag_keywords):
                red_flags.append(sentence.strip())
        
        return red_flags[:3]  # Max 3 red flags
    
    def _extract_actions(self, text: str) -> List[str]:
        """Extract immediate actions from crisis response"""
        return self._extract_suggestions(text)
    
    def _parse_analysis(self, text: str) -> Dict[str, Any]:
        """Parse analysis response into structured format"""
        return {
            "patterns": self._extract_suggestions(text),
            "insights": self._extract_suggestions(text),
            "recommendations": self._extract_suggestions(text),
            "normalcy_checks": self._extract_suggestions(text)
        }
    
    def _parse_emotional_analysis(self, text: str, checkin: Dict[str, Any]) -> Dict[str, Any]:
        """Parse emotional analysis response"""
        overwhelmed = checkin.get("overwhelmed_level", 5)
        anxiety = checkin.get("anxiety_level", 5)
        
        # Determine risk level
        if overwhelmed >= 8 or anxiety >= 8:
            risk_level = "high"
            escalation_needed = True
        elif overwhelmed >= 6 or anxiety >= 6:
            risk_level = "medium"
            escalation_needed = False
        else:
            risk_level = "low"
            escalation_needed = False
        
        return {
            "assessment": text,
            "risk_level": risk_level,
            "suggestions": self._extract_suggestions(text),
            "escalation_needed": escalation_needed,
            "resources": ["かかりつけの医療機関・市区町村の保健相談窓口", "日本で救急車が必要な場合は119"]
            if checkin.get("language", "ja").startswith("ja") else ["Your usual care provider or municipal health support service", "In Japan, call 119 if you need an ambulance"]
        }
