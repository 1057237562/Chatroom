"""
AI Agent module for OpenAI/GLM integration with chatroom system.
Provides async AI client and message processing capabilities.
"""

import asyncio
import json
import logging
from typing import Optional, Any
from datetime import datetime

try:
    from openai import AsyncOpenAI, RateLimitError, APIError, APIConnectionError, Timeout
except ImportError:
    raise ImportError("openai library not found. Install it with: pip install openai")

try:
    from zai import ZhipuAiClient
except ImportError:
    ZhipuAiClient = None

from utils.types import (
    AgentConfig,
    AgentMessage,
    AgentCommand,
    AgentResponse,
    ChatContext
)
from utils.prompts import get_system_prompt, get_command_context_prompt, get_error_recovery_prompt

logger = logging.getLogger(__name__)


class AIAgent:
    """AI Agent for chatroom with OpenAI/GLM integration."""
    
    def __init__(self, config: AgentConfig):
        """
        Initialize AI Agent with configuration.
        
        Args:
            config: AgentConfig instance with AI settings
        """
        self.config = config
        self.client = None
        self.glm_client = None
        self.conversation_history: list[dict[str, str]] = []
        self.current_users: list[str] = []
        self.message_cache: dict[str, str] = {}
        
        if config.ai_provider == "glm":
            if ZhipuAiClient is None:
                raise ImportError("zai-sdk library not found. Install it with: pip install zai-sdk")
            if not config.glm_api_key:
                raise ValueError("GLM API key is required when using GLM provider")
            self.glm_client = ZhipuAiClient(api_key=config.glm_api_key)
            logger.info(f"AIAgent initialized with GLM model: {config.model}")
        else:
            # Default to OpenAI
            if not config.openai_api_key:
                raise ValueError("OpenAI API key is required when using OpenAI provider")
            self.client = AsyncOpenAI(api_key=config.openai_api_key)
            logger.info(f"AIAgent initialized with OpenAI model: {config.model}")
    
    async def process_message(
        self,
        message: AgentMessage,
        current_users: list[str],
        available_commands: list[str]
    ) -> AgentResponse:
        """
        Process a message and generate an AI response.
        
        Args:
            message: The user message to process
            current_users: List of currently online users
            available_commands: Available commands in the system
            
        Returns:
            AgentResponse with the AI's reaction
        """
        logger.info(f"AI processing message from {message.username}: {message.content}")
        
        try:
            self.current_users = current_users
            
            # Determine message type and generate response
            if message.message_type == "command":
                response = await self._handle_command(message, available_commands)
            elif message.message_type == "private":
                response = await self._handle_private_message(message)
            else:
                response = await self._generate_reply(message, current_users)
            
            logger.info(f"AI response generated: {response.message}")
            return response
        
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                message=f"I encountered an error processing that message. Please try again.",
                response_type="error"
            )
    
    async def _generate_reply(
        self,
        message: AgentMessage,
        current_users: list[str]
    ) -> AgentResponse:
        """
        Generate an AI reply to a regular message.
        
        Args:
            message: User message
            current_users: List of online users
            
        Returns:
            AgentResponse with generated reply
        """
        try:
            # Check cache first
            cache_key = f"{message.username}:{message.content}"
            if cache_key in self.message_cache:
                cached_reply = self.message_cache[cache_key]
                logger.debug(f"Using cached reply for message from {message.username}")
                return AgentResponse(
                    success=True,
                    message=cached_reply,
                    response_type="info"
                )
            
            # Build context for the AI
            system_prompt = get_system_prompt(self.config.agent_name, current_users)
            user_content = f"{message.username}: {message.content}"
            
            # Call AI API with retry logic
            reply = await self._call_ai_with_retry(
                system_prompt,
                user_content
            )
            
            logger.info(f"Raw AI reply: '{reply}'")
            
            # Cache the reply (simple caching, not time-based)
            if len(self.message_cache) > 100:
                self.message_cache.clear()
            self.message_cache[cache_key] = reply
            
            logger.info(f"Generated reply to {message.username}")
            
            return AgentResponse(
                success=True,
                message=reply,
                response_type="info"
            )
        
        except Exception as e:
            if self.config.ai_provider == "openai":
                # Handle OpenAI-specific exceptions
                if isinstance(e, (RateLimitError, Timeout)):
                    logger.warning(f"OpenAI API rate limit or timeout: {e}")
                    return AgentResponse(
                        success=False,
                        message="I'm a bit overwhelmed right now. Please try again in a moment.",
                        response_type="info"
                    )
                elif isinstance(e, APIConnectionError):
                    logger.error(f"OpenAI API connection error: {e}")
                    return AgentResponse(
                        success=False,
                        message="Sorry, I'm having connection issues. Please try again later.",
                        response_type="error"
                    )
                elif isinstance(e, APIError):
                    logger.error(f"OpenAI API error: {e}")
                    return AgentResponse(
                        success=False,
                        message="I encountered an error. Please try again.",
                        response_type="error"
                    )
            
            # Handle GLM or other exceptions
            logger.error(f"AI API error: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                message="I encountered an error processing your message.",
                response_type="error"
            )
    
    async def _handle_command(
        self,
        message: AgentMessage,
        available_commands: list[str]
    ) -> AgentResponse:
        """
        Handle command execution requests.
        
        Args:
            message: Command message
            available_commands: List of available commands
            
        Returns:
            AgentResponse with command result
        """
        try:
            # Parse command from message content
            command_text = message.content.strip()
            if not command_text.startswith("/"):
                return AgentResponse(
                    success=False,
                    message="Command must start with /",
                    response_type="error"
                )
            
            # Extract command name
            parts = command_text[1:].split(maxsplit=1)
            command_name = parts[0].lower()
            args_text = parts[1] if len(parts) > 1 else ""
            
            # Validate command exists
            if command_name not in available_commands:
                return AgentResponse(
                    success=False,
                    message=f"Unknown command: /{command_name}. Use /help for available commands.",
                    response_type="error"
                )
            
            # Parse arguments
            args = args_text.split() if args_text else []
            
            # Return command for execution in main.py
            command = AgentCommand(command_name=command_name, args=args)
            
            return AgentResponse(
                success=True,
                message=f"Executing command: /{command_name}",
                response_type="command",
                command=command
            )
        
        except Exception as e:
            logger.error(f"Error handling command: {e}")
            return AgentResponse(
                success=False,
                message=f"Error handling command: {str(e)}",
                response_type="error"
            )
    
    async def _handle_private_message(self, message: AgentMessage) -> AgentResponse:
        """
        Handle private message responses.
        
        Args:
            message: Private message from user
            
        Returns:
            AgentResponse with private reply
        """
        try:
            system_prompt = get_system_prompt(self.config.agent_name, self.current_users)
            user_content = f"[PRIVATE] {message.username}: {message.content}"
            
            reply = await self._call_ai_with_retry(system_prompt, user_content)
            
            return AgentResponse(
                success=True,
                message=reply,
                response_type="private",
                target_user=message.username
            )
        
        except Exception as e:
            logger.error(f"Error handling private message: {e}")
            return AgentResponse(
                success=False,
                message="Sorry, I had an error processing your private message.",
                response_type="error"
            )
    
    async def _call_ai_with_retry(
        self,
        system_prompt: str,
        user_content: str,
        attempt: int = 1
    ) -> str:
        """
        Call AI API (OpenAI or GLM) with exponential backoff retry logic.
        
        Args:
            system_prompt: System prompt for context
            user_content: User message content
            attempt: Current attempt number
            
        Returns:
            Response text from AI API
            
        Raises:
            Various API exceptions after max retries
        """
        try:
            if self.config.ai_provider == "glm":
                return await self._call_glm_with_retry(system_prompt, user_content, attempt)
            else:
                return await self._call_openai_with_retry(system_prompt, user_content, attempt)
        except Exception as e:
            logger.error(f"Error in AI API call: {e}")
            raise
    
    async def _call_openai_with_retry(
        self,
        system_prompt: str,
        user_content: str,
        attempt: int = 1
    ) -> str:
        """
        Call OpenAI API with exponential backoff retry logic.
        
        Args:
            system_prompt: System prompt for context
            user_content: User message content
            attempt: Current attempt number
            
        Returns:
            Response text from OpenAI
            
        Raises:
            Various OpenAI exceptions after max retries
        """
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                ),
                timeout=self.config.timeout
            )
            
            reply = response.choices[0].message.content.strip()
            logger.debug(f"OpenAI response received: {len(reply)} chars")
            return reply
        
        except (RateLimitError, APIConnectionError, Timeout) as e:
            if attempt < self.config.retry_attempts:
                # Exponential backoff
                wait_time = self.config.retry_delay * (2 ** (attempt - 1))
                logger.info(f"Retry attempt {attempt}/{self.config.retry_attempts}, waiting {wait_time}s")
                await asyncio.sleep(wait_time)
                return await self._call_openai_with_retry(
                    system_prompt,
                    user_content,
                    attempt + 1
                )
            else:
                logger.error(f"Max retries exceeded for OpenAI call: {e}")
                raise
        
        except asyncio.TimeoutError:
            logger.error(f"OpenAI API call timeout after {self.config.timeout}s")
            raise Timeout(f"API call timeout after {self.config.timeout}s")
    
    async def _call_glm_with_retry(
        self,
        system_prompt: str,
        user_content: str,
        attempt: int = 1
    ) -> str:
        """
        Call GLM API with exponential backoff retry logic.
        
        Args:
            system_prompt: System prompt for context
            user_content: User message content
            attempt: Current attempt number
            
        Returns:
            Response text from GLM
            
        Raises:
            Various API exceptions after max retries
        """
        try:
            # GLM SDK is synchronous, so we need to run it in a thread pool
            loop = asyncio.get_event_loop()
            
            def call_glm():
                return self.glm_client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
            
            response = await asyncio.wait_for(
                loop.run_in_executor(None, call_glm),
                timeout=self.config.timeout
            )
            
            reply = response.choices[0].message.content.strip()
            logger.debug(f"GLM response received: {len(reply)} chars")
            return reply
        
        except Exception as e:
            if attempt < self.config.retry_attempts:
                # Exponential backoff
                wait_time = self.config.retry_delay * (2 ** (attempt - 1))
                logger.info(f"GLM retry attempt {attempt}/{self.config.retry_attempts}, waiting {wait_time}s")
                await asyncio.sleep(wait_time)
                return await self._call_glm_with_retry(
                    system_prompt,
                    user_content,
                    attempt + 1
                )
            else:
                logger.error(f"Max retries exceeded for GLM call: {e}")
                raise
    
    async def get_users(self) -> list[str]:
        """
        Get list of current online users.
        
        Returns:
            List of usernames
        """
        return self.current_users.copy()
    
    async def update_user_list(self, users: list[str]) -> None:
        """
        Update the current user list.
        
        Args:
            users: New list of online usernames
        """
        self.current_users = users.copy()
        logger.debug(f"User list updated: {len(users)} users")
    
    def clear_cache(self) -> None:
        """Clear message cache."""
        self.message_cache.clear()
        logger.info("Message cache cleared")
    
    async def health_check(self) -> bool:
        """
        Check if the AI API (OpenAI or GLM) is accessible.
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Simple test by calling a lightweight endpoint
            if self.config.ai_provider == "glm":
                # GLM SDK is synchronous, run in thread pool
                loop = asyncio.get_event_loop()
                
                def call_glm_health():
                    return self.glm_client.chat.completions.create(
                        model=self.config.model,
                        messages=[
                            {"role": "user", "content": "Hi"}
                        ],
                        max_tokens=10
                    )
                
                response = await asyncio.wait_for(
                    loop.run_in_executor(None, call_glm_health),
                    timeout=5
                )
            else:
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.config.model,
                        messages=[
                            {"role": "user", "content": "Hi"}
                    ],
                        max_tokens=10
                    ),
                    timeout=5
                )
            logger.info("Health check passed")
            return True
        
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
