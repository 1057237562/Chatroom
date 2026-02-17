"""
AI command implementation for direct AI interaction.
"""

from command.base import CommandBase, CommandContext, CommandResponse


class AICommand(CommandBase):
    """Send a direct message to AI assistant."""
    
    @property
    def name(self) -> str:
        return "ai"
    
    @property
    def description(self) -> str:
        return "Send a direct message to the AI assistant"
    
    @property
    def usage(self) -> str:
        return "/ai <message>"
    
    def validate(self, args: list) -> tuple[bool, str]:
        """Validate AI command arguments."""
        if not args:
            return False, "Message cannot be empty. Usage: /ai <message>"
        
        message = " ".join(args).strip()
        if not message:
            return False, "Message cannot be empty. Usage: /ai <message>"
        
        return True, ""
    
    async def execute(self, context: CommandContext, args: list) -> CommandResponse:
        """Execute AI message sending."""
        try:
            message = " ".join(args).strip()
            
            if context.websocket is None:
                return CommandResponse(
                    success=False,
                    message="AI command requires an active connection",
                    response_type="error"
                )
            
            import asyncio
            from main import ai_agent, ai_enabled, AGENT_NAME, broadcast_message
            
            if not ai_enabled or ai_agent is None:
                return CommandResponse(
                    success=False,
                    message="AI assistant is not available. Please check API configuration.",
                    response_type="error"
                )
            
            from utils.types import AgentMessage
            from command.factory import CommandFactory
            
            user_message = AgentMessage(
                username=context.username,
                content=message,
                message_type="normal",
                timestamp=None
            )
            
            available_commands = list(CommandFactory.get_all_commands().keys())
            
            ai_response = await ai_agent.process_message(
                user_message,
                list(context.current_users),
                available_commands
            )
            
            if ai_response.success:
                return CommandResponse(
                    success=True,
                    message=ai_response.message,
                    response_type="info"
                )
            else:
                return CommandResponse(
                    success=False,
                    message=ai_response.message or "AI processing failed",
                    response_type="error"
                )
        
        except Exception as e:
            return CommandResponse(
                success=False,
                message=f"Error communicating with AI: {str(e)}",
                response_type="error"
            )
