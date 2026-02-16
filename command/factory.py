"""
Command factory for registering and creating commands.
"""

from typing import Type
from command.base import CommandBase


class CommandFactory:
    """Factory for creating and managing commands."""
    
    _commands: dict[str, Type[CommandBase]] = {}
    
    @classmethod
    def register(cls, command_class: Type[CommandBase]) -> None:
        """Register a command class."""
        instance = command_class()
        cls._commands[instance.name] = command_class
    
    @classmethod
    def create(cls, command_name: str) -> CommandBase:
        """
        Create a command instance by name.
        
        Args:
            command_name: Name of the command (without /)
            
        Returns:
            Command instance
            
        Raises:
            KeyError: If command not found
        """
        if command_name not in cls._commands:
            raise KeyError(f"Unknown command: {command_name}")
        return cls._commands[command_name]()
    
    @classmethod
    def get_all_commands(cls) -> dict[str, CommandBase]:
        """Get all registered commands."""
        return {name: cmd_class() for name, cmd_class in cls._commands.items()}


def register_builtin_commands():
    """Register built-in commands with lazy imports to avoid circular imports."""
    from command.commands.help import HelpCommand
    from command.commands.whisper import WhisperCommand
    from command.commands.history import HistoryCommand
    
    CommandFactory.register(HelpCommand)
    CommandFactory.register(WhisperCommand)
    CommandFactory.register(HistoryCommand)
