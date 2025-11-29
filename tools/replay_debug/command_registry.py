"""
Command registry and decorator for the Replay Debug CLI Tool.

This module provides a decorator-based system for registering commands
with their argument specifications, eliminating the need for large
if-elif chains in the shell.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union


class ArgType(Enum):
    """Argument type enumeration."""
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"


@dataclass
class Argument:
    """Definition of a command argument.
    
    Attributes:
        name: Name of the argument (used for named arguments, e.g., --limit)
        arg_type: Type of the argument (string, int, float, bool)
        required: Whether the argument is required
        default: Default value if not required
        description: Help text for the argument
        positional: Whether this is a positional argument
        position: Position index for positional arguments (0-based)
    """
    name: str
    arg_type: ArgType = ArgType.STRING
    required: bool = False
    default: Any = None
    description: str = ""
    positional: bool = False
    position: int = 0


@dataclass
class Command:
    """Definition of a CLI command.
    
    Attributes:
        name: Primary name of the command
        aliases: Alternative names for the command
        description: Help text for the command
        arguments: List of argument definitions
        handler: Function to call when command is executed
        usage: Usage string for help text
    """
    name: str
    aliases: List[str] = field(default_factory=list)
    description: str = ""
    arguments: List[Argument] = field(default_factory=list)
    handler: Optional[Callable] = None
    usage: str = ""


class CommandRegistry:
    """Registry for CLI commands."""
    
    _instance: Optional['CommandRegistry'] = None
    
    def __init__(self):
        """Initialize the command registry."""
        self._commands: Dict[str, Command] = {}
        self._aliases: Dict[str, str] = {}
    
    @classmethod
    def get_instance(cls) -> 'CommandRegistry':
        """Get the singleton instance of the registry.
        
        Returns:
            The singleton CommandRegistry instance
        """
        if cls._instance is None:
            cls._instance = CommandRegistry()
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None
    
    def register(self, command: Command) -> None:
        """Register a command.
        
        Args:
            command: Command to register
        """
        self._commands[command.name] = command
        
        # Register aliases
        for alias in command.aliases:
            self._aliases[alias] = command.name
    
    def get_command(self, name: str) -> Optional[Command]:
        """Get a command by name or alias.
        
        Args:
            name: Command name or alias
            
        Returns:
            Command if found, None otherwise
        """
        # Check if it's an alias
        if name in self._aliases:
            name = self._aliases[name]
        
        return self._commands.get(name)
    
    def get_all_commands(self) -> Dict[str, Command]:
        """Get all registered commands.
        
        Returns:
            Dictionary of command names to Command objects
        """
        return dict(self._commands)
    
    def has_command(self, name: str) -> bool:
        """Check if a command exists.
        
        Args:
            name: Command name or alias
            
        Returns:
            True if command exists, False otherwise
        """
        return self.get_command(name) is not None


def command(
    name: str,
    aliases: Optional[List[str]] = None,
    description: str = "",
    usage: str = "",
    arguments: Optional[List[Argument]] = None
) -> Callable:
    """Decorator to register a command with its arguments.
    
    Args:
        name: Primary name of the command
        aliases: Alternative names for the command
        description: Help text for the command
        usage: Usage string for help text
        arguments: List of Argument definitions
        
    Returns:
        Decorator function
        
    Example:
        @command(
            name="view-patch",
            aliases=["vp"],
            description="View operations in a patch by its index",
            arguments=[
                Argument(name="index", arg_type=ArgType.INT, required=True, 
                         positional=True, position=0, description="Patch index"),
                Argument(name="limit", arg_type=ArgType.INT, required=False, 
                         default=20, description="Maximum operations to display"),
            ]
        )
        def cmd_view_patch(cli, index: int, limit: int = 20):
            cli.view_patch_by_index(index, limit)
    """
    def decorator(func: Callable) -> Callable:
        cmd = Command(
            name=name,
            aliases=aliases or [],
            description=description,
            usage=usage,
            arguments=arguments or [],
            handler=func
        )
        
        # Register in the global registry
        registry = CommandRegistry.get_instance()
        registry.register(cmd)
        
        return func
    
    return decorator


def arg(
    name: str,
    arg_type: ArgType = ArgType.STRING,
    required: bool = False,
    default: Any = None,
    description: str = "",
    positional: bool = False,
    position: int = 0
) -> Argument:
    """Helper function to create an Argument.
    
    Args:
        name: Name of the argument
        arg_type: Type of the argument
        required: Whether the argument is required
        default: Default value if not required
        description: Help text for the argument
        positional: Whether this is a positional argument
        position: Position index for positional arguments
        
    Returns:
        Argument instance
    """
    return Argument(
        name=name,
        arg_type=arg_type,
        required=required,
        default=default,
        description=description,
        positional=positional,
        position=position
    )


class CommandExecutor:
    """Executes registered commands with argument parsing."""
    
    def __init__(self, registry: Optional[CommandRegistry] = None):
        """Initialize the executor.
        
        Args:
            registry: CommandRegistry to use (defaults to singleton)
        """
        self.registry = registry or CommandRegistry.get_instance()
    
    def execute(
        self,
        command_name: str,
        positional_args: List[str],
        options: Dict[str, Any],
        context: Any = None
    ) -> bool:
        """Execute a command with parsed arguments.
        
        Args:
            command_name: Name of the command to execute
            positional_args: Positional arguments from command line
            options: Named options from command line
            context: Context object to pass to the command (e.g., cli instance)
            
        Returns:
            True if command was executed successfully, False otherwise
        """
        cmd = self.registry.get_command(command_name)
        
        if cmd is None or cmd.handler is None:
            return False
        
        try:
            # Parse arguments according to command definition
            kwargs = self._parse_arguments(cmd, positional_args, options)
            
            # Execute the command handler
            if context is not None:
                cmd.handler(context, **kwargs)
            else:
                cmd.handler(**kwargs)
            
            return True
            
        except ValueError as e:
            print(f"Error: {e}")
            if cmd.usage:
                print(f"Usage: {cmd.usage}")
            return False
        except Exception as e:
            print(f"Error executing command: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _parse_arguments(
        self,
        cmd: Command,
        positional_args: List[str],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse arguments according to command definition.
        
        Args:
            cmd: Command definition
            positional_args: Positional arguments from command line
            options: Named options from command line
            
        Returns:
            Dictionary of argument name -> parsed value
            
        Raises:
            ValueError: If required argument is missing or type conversion fails
        """
        kwargs = {}
        
        # Separate positional and named arguments from definition
        positional_defs = sorted(
            [arg for arg in cmd.arguments if arg.positional],
            key=lambda a: a.position
        )
        named_defs = [arg for arg in cmd.arguments if not arg.positional]
        
        # Parse positional arguments
        for i, arg_def in enumerate(positional_defs):
            if i < len(positional_args):
                value = self._convert_type(positional_args[i], arg_def.arg_type, arg_def.name)
                kwargs[arg_def.name] = value
            elif arg_def.required:
                raise ValueError(f"Missing required argument: {arg_def.name}")
            else:
                kwargs[arg_def.name] = arg_def.default
        
        # Parse named arguments (options)
        for arg_def in named_defs:
            # Handle hyphenated option names (e.g., full-width -> full_width)
            option_key = arg_def.name.replace('_', '-')
            underscore_key = arg_def.name.replace('-', '_')
            
            if arg_def.name in options:
                value = self._convert_type(options[arg_def.name], arg_def.arg_type, arg_def.name)
                kwargs[underscore_key] = value
            elif option_key in options:
                value = self._convert_type(options[option_key], arg_def.arg_type, arg_def.name)
                kwargs[underscore_key] = value
            elif arg_def.required:
                raise ValueError(f"Missing required option: --{arg_def.name}")
            else:
                kwargs[underscore_key] = arg_def.default
        
        return kwargs
    
    def _convert_type(self, value: Any, arg_type: ArgType, arg_name: str) -> Any:
        """Convert a value to the specified type.
        
        Args:
            value: Value to convert
            arg_type: Target type
            arg_name: Argument name (for error messages)
            
        Returns:
            Converted value
            
        Raises:
            ValueError: If type conversion fails
        """
        if value is None:
            return None
        
        try:
            if arg_type == ArgType.INT:
                return int(value)
            elif arg_type == ArgType.FLOAT:
                return float(value)
            elif arg_type == ArgType.BOOL:
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ('true', 'yes', '1', 'on')
                return bool(value)
            else:  # STRING
                return str(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid value for {arg_name}: expected {arg_type.value}, got '{value}'")
    
    def get_command_help(self, command_name: str) -> Optional[str]:
        """Get help text for a command.
        
        Args:
            command_name: Command name or alias
            
        Returns:
            Help text or None if command not found
        """
        cmd = self.registry.get_command(command_name)
        if cmd is None:
            return None
        
        lines = []
        lines.append(f"\n{cmd.name}")
        
        if cmd.aliases:
            lines.append(f"  Aliases: {', '.join(cmd.aliases)}")
        
        if cmd.description:
            lines.append(f"  {cmd.description}")
        
        if cmd.usage:
            lines.append(f"  Usage: {cmd.usage}")
        
        if cmd.arguments:
            lines.append("\n  Arguments:")
            for arg in cmd.arguments:
                required_str = " (required)" if arg.required else ""
                default_str = f" [default: {arg.default}]" if arg.default is not None else ""
                pos_str = "positional" if arg.positional else "option"
                lines.append(
                    f"    {arg.name} ({arg.arg_type.value}, {pos_str}){required_str}{default_str}"
                )
                if arg.description:
                    lines.append(f"      {arg.description}")
        
        return "\n".join(lines)
