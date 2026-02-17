"""
Data types and structures for Agent Utils module.
"""

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class AgentConfig:
    """Configuration for AI Agent."""
    
    openai_api_key: str
    model: str = "glm-4-flash"
    agent_name: str = "AI"
    temperature: float = 0.7
    max_tokens: int = 500
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    base_url: str = "https://open.bigmodel.cn/api/paas/v4/"


@dataclass
class AgentMessage:
    """Message structure for Agent communication."""
    
    username: str
    content: str
    message_type: str = "normal"  # normal, command, private
    timestamp: Optional[str] = None
    target_user: Optional[str] = None  # For private messages


@dataclass
class AgentCommand:
    """Command structure for Agent to execute."""
    
    command_name: str
    args: list[str] = field(default_factory=list)


@dataclass
class AgentResponse:
    """Response from Agent processing."""
    
    success: bool
    message: str
    response_type: str = "info"  # info, error, private, command
    command: Optional[AgentCommand] = None
    target_user: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UserInfo:
    """Information about a user in the chatroom."""
    
    username: str
    online: bool = True
    joined_at: Optional[str] = None


@dataclass
class ChatContext:
    """Context information for chat processing."""
    
    current_users: list[str]
    agent_name: str
    available_commands: list[str] = field(default_factory=list)
