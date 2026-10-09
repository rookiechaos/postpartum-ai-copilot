"""
AI Provider Implementations - Support for OpenAI, Claude, and Gemini
"""

from typing import Dict, List, Any, Optional, AsyncGenerator
from abc import ABC, abstractmethod
from config.settings import get_settings
from services.ai_errors import PUBLIC_AI_ERROR
from services.logging_service import logger


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
    else:
        raise ValueError(f"Unknown AI provider: {provider_name}. Supported: openai, claude, gemini")
