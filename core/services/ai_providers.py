"""
AI providers for direct model APIs and explicitly configured isolated runners.
"""

from typing import Dict, List, Any, Optional, AsyncGenerator
from abc import ABC, abstractmethod
from config.settings import get_settings
from services.ai_errors import PUBLIC_AI_ERROR
from services.logging_service import logger
from exceptions import AIServiceError


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Generate chat completion"""
        pass
    
    @abstractmethod
    async def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming chat completion"""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI API Provider"""
    
    def __init__(self):
        from openai import AsyncOpenAI
        
        settings = get_settings()
        api_key = settings.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = settings.openai_model
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Generate chat completion using OpenAI"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 500)
            )
            
            return {
                "text": response.choices[0].message.content,
                "model": self.model,
                "provider": "openai"
            }
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming chat completion using OpenAI"""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 500),
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield {
                        "type": "chunk",
                        "content": chunk.choices[0].delta.content
                    }
            
            yield {"type": "done"}
        except Exception as e:
            logger.log_error(e, context={"action": "openai_stream"})
            yield {"type": "error", "content": PUBLIC_AI_ERROR}


class ClaudeProvider(AIProvider):
    """Anthropic Claude API Provider"""
    
    def __init__(self):
        from anthropic import AsyncAnthropic
        
        settings = get_settings()
        api_key = settings.anthropic_api_key
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = settings.claude_model
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Generate chat completion using Claude"""
        try:
            # Convert messages format for Claude
            # Claude expects system message separately
            system_message = None
            conversation_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    # Claude uses "user" and "assistant" roles
                    role = "user" if msg["role"] == "user" else "assistant"
                    conversation_messages.append({
                        "role": role,
                        "content": msg["content"]
                    })
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 500),
                temperature=kwargs.get("temperature", 0.7),
                system=system_message or "",
                messages=conversation_messages
            )
            
            # Extract text from Claude response
            text_content = ""
            if response.content:
                for block in response.content:
                    if block.type == "text":
                        text_content += block.text
            
            return {
                "text": text_content,
                "model": self.model,
                "provider": "claude"
            }
        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")
    
    async def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming chat completion using Claude"""
        try:
            # Convert messages format for Claude
            system_message = None
            conversation_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    role = "user" if msg["role"] == "user" else "assistant"
                    conversation_messages.append({
                        "role": role,
                        "content": msg["content"]
                    })
            
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 500),
                temperature=kwargs.get("temperature", 0.7),
                system=system_message or "",
                messages=conversation_messages
            ) as stream:
                async for text in stream.text_stream:
                    yield {
                        "type": "chunk",
                        "content": text
                    }
            
            yield {"type": "done"}
        except Exception as e:
            logger.log_error(e, context={"action": "claude_stream"})
            yield {"type": "error", "content": PUBLIC_AI_ERROR}


class GeminiProvider(AIProvider):
    """Google Gemini API Provider"""
    
    def __init__(self):
        import google.generativeai as genai
        
        settings = get_settings()
        api_key = settings.google_api_key
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        self.model_name = settings.gemini_model
        self.model = genai.GenerativeModel(self.model_name)
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Generate chat completion using Gemini"""
        try:
            # Convert messages format for Gemini
            # Gemini expects a single prompt or chat history
            prompt_parts = []
            
            for msg in messages:
                if msg["role"] == "system":
                    # Gemini doesn't have separate system messages, prepend to first user message
                    if prompt_parts:
                        prompt_parts[0] = f"{msg['content']}\n\n{prompt_parts[0]}"
                    else:
                        prompt_parts.append(msg["content"])
                elif msg["role"] == "user":
                    prompt_parts.append(msg["content"])
                elif msg["role"] == "assistant":
                    # For chat history, we'd need to use chat session
                    # For now, append as context
                    prompt_parts.append(f"Assistant: {msg['content']}")
            
            # Combine all parts
            full_prompt = "\n\n".join(prompt_parts)
            
            # Generate content - Gemini doesn't have async, use sync with asyncio
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    full_prompt,
                    generation_config={
                        "temperature": kwargs.get("temperature", 0.7),
                        "max_output_tokens": kwargs.get("max_tokens", 500),
                    }
                )
            )
            
            return {
                "text": response.text,
                "model": self.model_name,
                "provider": "gemini"
            }
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    async def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming chat completion using Gemini"""
        try:
            # Convert messages format for Gemini
            prompt_parts = []
            
            for msg in messages:
                if msg["role"] == "system":
                    if prompt_parts:
                        prompt_parts[0] = f"{msg['content']}\n\n{prompt_parts[0]}"
                    else:
                        prompt_parts.append(msg["content"])
                elif msg["role"] == "user":
                    prompt_parts.append(msg["content"])
                elif msg["role"] == "assistant":
                    prompt_parts.append(f"Assistant: {msg['content']}")
            
            full_prompt = "\n\n".join(prompt_parts)
            
            # Stream content - Gemini streaming is synchronous, need to wrap
            import asyncio
            response = self.model.generate_content(
                full_prompt,
                stream=True,
                generation_config={
                    "temperature": kwargs.get("temperature", 0.7),
                    "max_output_tokens": kwargs.get("max_tokens", 500),
                }
            )
            
            for chunk in response:
                if chunk.text:
                    yield {
                        "type": "chunk",
                        "content": chunk.text
                    }
                await asyncio.sleep(0)  # Yield control
            
            yield {"type": "done"}
        except Exception as e:
            logger.log_error(e, context={"action": "gemini_stream"})
            yield {"type": "error", "content": PUBLIC_AI_ERROR}


class AgentRunnerProvider(AIProvider):
    """Use the same household messages with a Codex/Claude Code/custom runner.

    This adapter never loads records, changes consent, launches a CLI in the API
    process, or retries. The caller must provide an authenticated call scope.
    """

    requires_full_response_validation = True
    automatic_retry = False

    def __init__(self, backend: str):
        from services.agent_service import AgentService, BACKENDS

        settings = get_settings()
        if backend not in BACKENDS or not settings.agent_enabled:
            raise AIServiceError("The selected AI runner is unavailable")
        self.backend = backend
        self.service = AgentService(settings)
        configured = any(
            item["backend"] == backend and item["configured"]
            for item in self.service.capabilities()["backends"]
        )
        if not configured:
            raise AIServiceError("The selected AI runner is unavailable")

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        import json
        from services.agent_execution import get_agent_call_context
        from models.database import SessionLocal

        context = get_agent_call_context()
        if context is None:
            raise AIServiceError("An authenticated AI call scope is required")
        if not isinstance(messages, list) or not messages:
            raise AIServiceError("AI messages are unavailable")
        system_messages, conversation = [], []
        for message in messages:
            if not isinstance(message, dict) or set(message) != {"role", "content"} \
                    or message.get("role") not in {"system", "user", "assistant"} \
                    or not isinstance(message.get("content"), str):
                raise AIServiceError("AI messages are unavailable")
            if message["role"] == "system":
                system_messages.append(message["content"])
            else:
                conversation.append({"role": message["role"], "content": message["content"]})
        if not system_messages or not any(message["role"] == "user" for message in conversation):
            raise AIServiceError("AI messages are unavailable")
        # Preserve system text and ordered roles without truncating either safety
        # instructions or explicitly selected context to fit a provider limit.
        instructions = "\n\n".join(system_messages)
        prompt = json.dumps({
            "format": "postpartum.conversation.v1", "messages": conversation,
        }, ensure_ascii=False)
        try:
            with SessionLocal() as db:
                result = await self.service.run(
                    user_id=context.user_id, backend=self.backend,
                    prompt=prompt, instructions=instructions,
                    request_id=context.request_id, db=db,
                )
        except Exception:
            raise AIServiceError("AI response unavailable") from None
        if result.get("status") != "completed" or not isinstance(result.get("output"), str):
            raise AIServiceError("AI response unavailable")
        return {"text": result["output"], "provider": self.backend}

    async def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        # AIService sees requires_full_response_validation and applies its whole
        # answer pipeline before emitting a chunk to the household client.
        try:
            result = await self.chat(messages, **kwargs)
            yield {"type": "chunk", "content": result["text"]}
            yield {"type": "done"}
        except Exception:
            yield {"type": "error", "content": PUBLIC_AI_ERROR}


def get_ai_provider() -> AIProvider:
    """Factory function to get the configured AI provider"""
    settings = get_settings()
    provider_name = settings.ai_provider.lower()
    
    if provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "claude":
        return ClaudeProvider()
    elif provider_name == "gemini":
        return GeminiProvider()
    elif provider_name in {"codex", "claude_code", "agent"}:
        return AgentRunnerProvider(provider_name)
    else:
        raise ValueError("Unknown AI provider. Supported: openai, claude, gemini, codex, claude_code, agent")
