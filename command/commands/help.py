"""
Help command implementation.
"""

from command.base import CommandBase, CommandContext, CommandResponse
from command.factory import CommandFactory


class HelpCommand(CommandBase):
    """Display help information about available commands."""
    
    @property
    def name(self) -> str:
        return "help"
    
    @property
    def description(self) -> str:
        return "Show help information about available commands"
    
    @property
    def usage(self) -> str:
        return "/help"
    
    def validate(self, args: list) -> tuple[bool, str]:
        """Help command takes no arguments."""
        if args:
            return False, "The /help command takes no arguments"
        return True, ""
    
    async def execute(self, context: CommandContext, args: list) -> CommandResponse:
        """Generate help message listing all available commands."""
        try:
            commands = CommandFactory.get_all_commands()
            
            help_lines = ["=== Available Commands ==="]
            for cmd_name in sorted(commands.keys()):
                cmd = commands[cmd_name]
                help_lines.append(f"\n{cmd.usage}")
                help_lines.append(f"  {cmd.description}")
            
            help_text = "\n".join(help_lines)
            
            return CommandResponse(
                success=True,
                message=help_text,
                response_type="info"
            )
        except Exception as e:
            return CommandResponse(
                success=False,
                message=f"Error generating help: {str(e)}",
                response_type="error"
            )
