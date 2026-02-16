"""
Base class and data structures for command system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
# No need to import Dict, Set, List for Python 3.9+
# Use built-in generic types directly
from fastapi import WebSocket


@dataclass
class CommandContext:
    """Context passed to commands during execution."""
    websocket: WebSocket | None
    username: str
    user_map: dict[WebSocket, str]
    current_users: set[str]


@dataclass
class CommandResponse:
    """Response returned by command execution."""
    success: bool
    message: str
    response_type: str = "info"  # "info", "error", "private"
    target_user: str | None = None  # For private messages


class CommandBase(ABC):
    """Abstract base class for all commands."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Command name (without leading slash)."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Command description for help text."""
        pass
    
    @property
    @abstractmethod
    def usage(self) -> str:
        """Command usage format."""
        pass
    
    @abstractmethod
    def validate(self, args: list[str]) -> tuple[bool, str]:
        """
        Validate command arguments.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    async def execute(self, context: CommandContext, args: list[str]) -> CommandResponse:
        """
        Execute the command.
        
        Args:
            context: Command execution context
            args: Parsed arguments
            
        Returns:
            CommandResponse with execution result
        """
        pass
