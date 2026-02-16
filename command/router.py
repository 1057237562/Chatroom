"""
Command router and parser for message handling.
"""

class CommandParser:
    """Parse message to extract command and arguments."""
    
    @staticmethod
    def is_command(message: str) -> bool:
        """Check if message is a command (starts with /)."""
        return message.strip().startswith("/")
    
    @staticmethod
    def parse(message: str) -> tuple[str, list]:
        """
        Parse command message into command name and arguments.
        
        Args:
            message: Message starting with /
            
        Returns:
            Tuple of (command_name, args_list)
            
        Example:
            "/t @alice hello world" -> ("t", ["@alice", "hello", "world"])
            "/help" -> ("help", [])
        """
        # Remove leading slash and strip whitespace
        command_text = message[1:].strip()
        
        if not command_text:
            return "", []
        
        # Split into command and arguments
        parts = command_text.split(maxsplit=1)
        command_name = parts[0].lower()
        
        # Parse arguments
        args = []
        if len(parts) > 1:
            args = parts[1].split()
        
        return command_name, args
