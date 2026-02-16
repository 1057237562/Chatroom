"""
History command - retrieve and display chat history.
"""

from command.base import CommandBase, CommandContext, CommandResponse
import logging

logger = logging.getLogger(__name__)


class HistoryCommand(CommandBase):
    """Command to retrieve chat history with optional filters."""
    
    @property
    def name(self) -> str:
        return "history"
    
    @property
    def description(self) -> str:
        return "View chat history with optional filters"
    
    @property
    def usage(self) -> str:
        return "/history [limit] [@username] [keyword]\nExamples:\n  /history 10\n  /history 20 @alice\n  /history 15 @bob hello"
    
    def validate(self, args: list[str]) -> tuple[bool, str]:
        """Validate history command arguments."""
        if not args:
            return True, ""
        
        # First arg should be a number (limit)
        if args:
            try:
                limit = int(args[0])
                if limit <= 0 or limit > 100:
                    return False, "Limit must be between 1 and 100"
            except ValueError:
                # First arg might be username, that's ok
                pass
        
        return True, ""
    
    async def execute(self, context: CommandContext, args: list[str]) -> CommandResponse:
        """Execute history command."""
        try:
            from db import get_history
            
            # Parse arguments
            limit = 20
            username = None
            keyword = None
            
            if args:
                arg_idx = 0
                # Check if first arg is a number
                try:
                    limit = min(int(args[0]), 100)
                    arg_idx = 1
                except (ValueError, IndexError):
                    pass
                
                # Check for @username
                if arg_idx < len(args) and args[arg_idx].startswith("@"):
                    username = args[arg_idx][1:]
                    arg_idx += 1
                
                # Remaining args are keyword
                if arg_idx < len(args):
                    keyword = " ".join(args[arg_idx:])
            
            # Get history
            messages, total = await get_history(
                limit=limit,
                offset=0,
                username=username,
                keyword=keyword
            )
            
            if not messages:
                return CommandResponse(
                    success=True,
                    message=f"No messages found.",
                    response_type="info"
                )
            
            # Format history for display (limit to prevent huge responses)
            display_count = min(len(messages), 10)
            history_lines = [f"Recent {display_count} messages (total: {total}):"]
            
            for msg in messages[-display_count:]:
                timestamp = msg.get('timestamp', '')
                sender = msg.get('username', 'Unknown')
                content = msg.get('content', '')
                # Truncate long messages
                if len(content) > 60:
                    content = content[:60] + "..."
                history_lines.append(f"[{timestamp}] {sender}: {content}")
            
            return CommandResponse(
                success=True,
                message="\n".join(history_lines),
                response_type="info"
            )
        
        except Exception as e:
            logger.error(f"Error executing history command: {e}")
            return CommandResponse(
                success=False,
                message=f"Error retrieving history: {str(e)}",
                response_type="error"
            )
