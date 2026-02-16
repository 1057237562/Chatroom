"""
Whisper (private message) command implementation.
"""

from command.base import CommandBase, CommandContext, CommandResponse


class WhisperCommand(CommandBase):
    """Send private message to another user."""
    
    @property
    def name(self) -> str:
        return "t"
    
    @property
    def description(self) -> str:
        return "Send a private message to a user"
    
    @property
    def usage(self) -> str:
        return "/t @username <message>"
    
    def validate(self, args: list) -> tuple[bool, str]:
        """Validate whisper command arguments."""
        # Need at least 2 parts: username and message
        if len(args) < 2:
            return False, f"Invalid format. Usage: {self.usage}"
        
        # First arg is username (may have @ prefix)
        username = args[0]
        if not username:
            return False, "Username cannot be empty"
        
        # Remove @ prefix if present
        if username.startswith("@"):
            username = username[1:]
        
        if not username:
            return False, "Username cannot be empty"
        
        # Message is the rest
        message = " ".join(args[1:])
        if not message or not message.strip():
            return False, "Message cannot be empty"
        
        return True, ""
    
    async def execute(self, context: CommandContext, args: list) -> CommandResponse:
        """Execute private message sending."""
        try:
            # Parse arguments
            target_username = args[0]
            if target_username.startswith("@"):
                target_username = target_username[1:]
            
            message = " ".join(args[1:]).strip()
            
            # Validation checks
            if target_username == context.username:
                return CommandResponse(
                    success=False,
                    message="You cannot send a private message to yourself",
                    response_type="error"
                )
            
            if target_username not in context.current_users:
                return CommandResponse(
                    success=False,
                    message=f"User '{target_username}' is not online",
                    response_type="error"
                )
            
            # Find target user's websocket
            target_websocket = None
            for ws, username in context.user_map.items():
                if username == target_username:
                    target_websocket = ws
                    break
            
            if target_websocket is None:
                return CommandResponse(
                    success=False,
                    message=f"User '{target_username}' not found",
                    response_type="error"
                )
            
            # Send private message to target user
            import json
            private_message = {
                "type": "private",
                "from": context.username,
                "text": message
            }
            await target_websocket.send_text(json.dumps(private_message))
            
            # Send confirmation to sender
            return CommandResponse(
                success=True,
                message=f"Private message sent to {target_username}",
                response_type="info"
            )
        
        except Exception as e:
            return CommandResponse(
                success=False,
                message=f"Error sending private message: {str(e)}",
                response_type="error"
            )
