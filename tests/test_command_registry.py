"""
Tests for the command registry and decorator system.
"""
import unittest
from tools.replay_debug.command_registry import (
    CommandRegistry,
    CommandExecutor,
    Command,
    Argument,
    ArgType,
    command,
    arg,
)


class TestCommandRegistry(unittest.TestCase):
    """Tests for CommandRegistry."""
    
    def setUp(self):
        """Reset the registry before each test."""
        CommandRegistry.reset()
    
    def tearDown(self):
        """Reset the registry after each test."""
        CommandRegistry.reset()
    
    def test_singleton_instance(self):
        """Test that get_instance returns the same instance."""
        instance1 = CommandRegistry.get_instance()
        instance2 = CommandRegistry.get_instance()
        self.assertIs(instance1, instance2)
    
    def test_reset(self):
        """Test that reset creates a new instance."""
        instance1 = CommandRegistry.get_instance()
        CommandRegistry.reset()
        instance2 = CommandRegistry.get_instance()
        self.assertIsNot(instance1, instance2)
    
    def test_register_command(self):
        """Test registering a command."""
        registry = CommandRegistry.get_instance()
        
        cmd = Command(
            name="test-cmd",
            aliases=["tc"],
            description="Test command",
            handler=lambda: None
        )
        registry.register(cmd)
        
        self.assertTrue(registry.has_command("test-cmd"))
        self.assertTrue(registry.has_command("tc"))
    
    def test_get_command_by_name(self):
        """Test getting a command by its name."""
        registry = CommandRegistry.get_instance()
        
        cmd = Command(name="my-command", description="My command")
        registry.register(cmd)
        
        retrieved = registry.get_command("my-command")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "my-command")
    
    def test_get_command_by_alias(self):
        """Test getting a command by its alias."""
        registry = CommandRegistry.get_instance()
        
        cmd = Command(name="full-name", aliases=["fn", "short"])
        registry.register(cmd)
        
        # Should find by alias
        retrieved = registry.get_command("fn")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "full-name")
        
        # Should also find by second alias
        retrieved = registry.get_command("short")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "full-name")
    
    def test_get_command_not_found(self):
        """Test getting a non-existent command returns None."""
        registry = CommandRegistry.get_instance()
        
        result = registry.get_command("nonexistent")
        self.assertIsNone(result)
    
    def test_get_all_commands(self):
        """Test getting all registered commands."""
        registry = CommandRegistry.get_instance()
        
        registry.register(Command(name="cmd1"))
        registry.register(Command(name="cmd2"))
        
        all_cmds = registry.get_all_commands()
        self.assertEqual(len(all_cmds), 2)
        self.assertIn("cmd1", all_cmds)
        self.assertIn("cmd2", all_cmds)


class TestCommandDecorator(unittest.TestCase):
    """Tests for the @command decorator."""
    
    def setUp(self):
        """Reset the registry before each test."""
        CommandRegistry.reset()
    
    def tearDown(self):
        """Reset the registry after each test."""
        CommandRegistry.reset()
    
    def test_decorator_registers_command(self):
        """Test that the decorator registers the command."""
        @command(name="decorated-cmd", description="A decorated command")
        def my_handler():
            pass
        
        registry = CommandRegistry.get_instance()
        self.assertTrue(registry.has_command("decorated-cmd"))
    
    def test_decorator_with_aliases(self):
        """Test that the decorator registers aliases."""
        @command(name="full-cmd", aliases=["fc", "f"])
        def handler():
            pass
        
        registry = CommandRegistry.get_instance()
        self.assertTrue(registry.has_command("full-cmd"))
        self.assertTrue(registry.has_command("fc"))
        self.assertTrue(registry.has_command("f"))
    
    def test_decorator_with_arguments(self):
        """Test that the decorator stores arguments."""
        @command(
            name="cmd-with-args",
            arguments=[
                arg(name="path", arg_type=ArgType.STRING, required=True, positional=True),
                arg(name="limit", arg_type=ArgType.INT, default=10),
            ]
        )
        def handler(path, limit=10):
            pass
        
        registry = CommandRegistry.get_instance()
        cmd = registry.get_command("cmd-with-args")
        
        self.assertEqual(len(cmd.arguments), 2)
        self.assertEqual(cmd.arguments[0].name, "path")
        self.assertEqual(cmd.arguments[1].name, "limit")
    
    def test_decorator_preserves_function(self):
        """Test that the decorator returns the original function."""
        @command(name="test")
        def my_func():
            return "hello"
        
        self.assertEqual(my_func(), "hello")


class TestArgHelper(unittest.TestCase):
    """Tests for the arg() helper function."""
    
    def test_create_argument_with_defaults(self):
        """Test creating an argument with defaults."""
        argument = arg(name="test")
        
        self.assertEqual(argument.name, "test")
        self.assertEqual(argument.arg_type, ArgType.STRING)
        self.assertFalse(argument.required)
        self.assertIsNone(argument.default)
        self.assertFalse(argument.positional)
    
    def test_create_argument_with_all_options(self):
        """Test creating an argument with all options."""
        argument = arg(
            name="my-arg",
            arg_type=ArgType.INT,
            required=True,
            default=42,
            description="An integer argument",
            positional=True,
            position=0
        )
        
        self.assertEqual(argument.name, "my-arg")
        self.assertEqual(argument.arg_type, ArgType.INT)
        self.assertTrue(argument.required)
        self.assertEqual(argument.default, 42)
        self.assertEqual(argument.description, "An integer argument")
        self.assertTrue(argument.positional)
        self.assertEqual(argument.position, 0)


class TestCommandExecutor(unittest.TestCase):
    """Tests for CommandExecutor."""
    
    def setUp(self):
        """Reset the registry before each test."""
        CommandRegistry.reset()
    
    def tearDown(self):
        """Reset the registry after each test."""
        CommandRegistry.reset()
    
    def test_execute_simple_command(self):
        """Test executing a simple command with no arguments."""
        result = []
        
        @command(name="simple")
        def simple_handler(context):
            result.append("executed")
        
        executor = CommandExecutor()
        success = executor.execute("simple", [], {}, context="ctx")
        
        self.assertTrue(success)
        self.assertEqual(result, ["executed"])
    
    def test_execute_command_with_positional_args(self):
        """Test executing a command with positional arguments."""
        captured = {}
        
        @command(
            name="pos-cmd",
            arguments=[
                arg(name="name", arg_type=ArgType.STRING, required=True, positional=True, position=0),
                arg(name="count", arg_type=ArgType.INT, required=True, positional=True, position=1),
            ]
        )
        def handler(context, name, count):
            captured['name'] = name
            captured['count'] = count
        
        executor = CommandExecutor()
        success = executor.execute("pos-cmd", ["hello", "42"], {}, context="ctx")
        
        self.assertTrue(success)
        self.assertEqual(captured['name'], "hello")
        self.assertEqual(captured['count'], 42)
    
    def test_execute_command_with_options(self):
        """Test executing a command with named options."""
        captured = {}
        
        @command(
            name="opt-cmd",
            arguments=[
                arg(name="limit", arg_type=ArgType.INT, default=10),
                arg(name="direction", arg_type=ArgType.STRING, default="forward"),
            ]
        )
        def handler(context, limit, direction):
            captured['limit'] = limit
            captured['direction'] = direction
        
        executor = CommandExecutor()
        success = executor.execute("opt-cmd", [], {"limit": "50", "direction": "backward"}, context="ctx")
        
        self.assertTrue(success)
        self.assertEqual(captured['limit'], 50)
        self.assertEqual(captured['direction'], "backward")
    
    def test_execute_command_with_defaults(self):
        """Test that defaults are used when arguments are not provided."""
        captured = {}
        
        @command(
            name="default-cmd",
            arguments=[
                arg(name="value", arg_type=ArgType.INT, default=100),
            ]
        )
        def handler(context, value):
            captured['value'] = value
        
        executor = CommandExecutor()
        success = executor.execute("default-cmd", [], {}, context="ctx")
        
        self.assertTrue(success)
        self.assertEqual(captured['value'], 100)
    
    def test_execute_missing_required_arg(self):
        """Test that missing required argument prints error."""
        @command(
            name="req-cmd",
            arguments=[
                arg(name="required_arg", arg_type=ArgType.STRING, required=True, positional=True, position=0),
            ]
        )
        def handler(context, required_arg):
            pass
        
        executor = CommandExecutor()
        # Should return False and print error (no exception)
        success = executor.execute("req-cmd", [], {}, context="ctx")
        
        self.assertFalse(success)
    
    def test_execute_nonexistent_command(self):
        """Test that non-existent command returns False."""
        executor = CommandExecutor()
        success = executor.execute("does-not-exist", [], {}, context="ctx")
        
        self.assertFalse(success)
    
    def test_execute_by_alias(self):
        """Test executing a command by alias."""
        result = []
        
        @command(name="full-name", aliases=["fn"])
        def handler(context):
            result.append("aliased")
        
        executor = CommandExecutor()
        success = executor.execute("fn", [], {}, context="ctx")
        
        self.assertTrue(success)
        self.assertEqual(result, ["aliased"])
    
    def test_type_conversion_float(self):
        """Test float type conversion."""
        captured = {}
        
        @command(
            name="float-cmd",
            arguments=[
                arg(name="value", arg_type=ArgType.FLOAT, required=True, positional=True, position=0),
            ]
        )
        def handler(context, value):
            captured['value'] = value
        
        executor = CommandExecutor()
        success = executor.execute("float-cmd", ["3.14"], {}, context="ctx")
        
        self.assertTrue(success)
        self.assertAlmostEqual(captured['value'], 3.14)
    
    def test_type_conversion_bool(self):
        """Test bool type conversion."""
        captured = {}
        
        @command(
            name="bool-cmd",
            arguments=[
                arg(name="flag", arg_type=ArgType.BOOL, default=False),
            ]
        )
        def handler(context, flag):
            captured['flag'] = flag
        
        executor = CommandExecutor()
        
        # Test with True value from flag being present
        success = executor.execute("bool-cmd", [], {"flag": True}, context="ctx")
        self.assertTrue(success)
        self.assertTrue(captured['flag'])
    
    def test_hyphenated_option_to_underscore(self):
        """Test that hyphenated options are converted to underscored kwargs."""
        captured = {}
        
        @command(
            name="hyphen-cmd",
            arguments=[
                arg(name="full_width", arg_type=ArgType.BOOL, default=False),
            ]
        )
        def handler(context, full_width):
            captured['full_width'] = full_width
        
        executor = CommandExecutor()
        success = executor.execute("hyphen-cmd", [], {"full-width": True}, context="ctx")
        
        self.assertTrue(success)
        self.assertTrue(captured['full_width'])


class TestArgumentTypes(unittest.TestCase):
    """Tests for argument type enumeration."""
    
    def test_arg_type_values(self):
        """Test that ArgType has expected values."""
        self.assertEqual(ArgType.STRING.value, "string")
        self.assertEqual(ArgType.INT.value, "int")
        self.assertEqual(ArgType.FLOAT.value, "float")
        self.assertEqual(ArgType.BOOL.value, "bool")
        self.assertEqual(ArgType.TIMEDELTA.value, "timedelta")
        self.assertEqual(ArgType.DATETIME.value, "datetime")


class TestTimedeltaParsing(unittest.TestCase):
    """Tests for timedelta parsing."""
    
    def setUp(self):
        """Reset the registry before each test."""
        CommandRegistry.reset()
    
    def tearDown(self):
        """Reset the registry after each test."""
        CommandRegistry.reset()
    
    def test_parse_seconds(self):
        """Test parsing seconds."""
        from tools.replay_debug.command_registry import parse_timedelta
        from datetime import timedelta
        
        result = parse_timedelta("1s")
        self.assertEqual(result, timedelta(seconds=1))
        
        result = parse_timedelta("30s")
        self.assertEqual(result, timedelta(seconds=30))
        
        result = parse_timedelta("1S")  # uppercase
        self.assertEqual(result, timedelta(seconds=1))
    
    def test_parse_minutes(self):
        """Test parsing minutes."""
        from tools.replay_debug.command_registry import parse_timedelta
        from datetime import timedelta
        
        result = parse_timedelta("1m")
        self.assertEqual(result, timedelta(minutes=1))
        
        result = parse_timedelta("5m")
        self.assertEqual(result, timedelta(minutes=5))
    
    def test_parse_hours(self):
        """Test parsing hours."""
        from tools.replay_debug.command_registry import parse_timedelta
        from datetime import timedelta
        
        result = parse_timedelta("1h")
        self.assertEqual(result, timedelta(hours=1))
        
        result = parse_timedelta("24h")
        self.assertEqual(result, timedelta(hours=24))
    
    def test_parse_days(self):
        """Test parsing days."""
        from tools.replay_debug.command_registry import parse_timedelta
        from datetime import timedelta
        
        result = parse_timedelta("1d")
        self.assertEqual(result, timedelta(days=1))
        
        result = parse_timedelta("7d")
        self.assertEqual(result, timedelta(days=7))
    
    def test_parse_weeks(self):
        """Test parsing weeks."""
        from tools.replay_debug.command_registry import parse_timedelta
        from datetime import timedelta
        
        result = parse_timedelta("1w")
        self.assertEqual(result, timedelta(weeks=1))
        
        result = parse_timedelta("2w")
        self.assertEqual(result, timedelta(weeks=2))
    
    def test_parse_negative_timedelta(self):
        """Test parsing negative timedelta."""
        from tools.replay_debug.command_registry import parse_timedelta
        from datetime import timedelta
        
        result = parse_timedelta("-5m")
        self.assertEqual(result, timedelta(minutes=-5))
    
    def test_parse_float_timedelta(self):
        """Test parsing float timedelta."""
        from tools.replay_debug.command_registry import parse_timedelta
        from datetime import timedelta
        
        result = parse_timedelta("1.5h")
        self.assertEqual(result, timedelta(hours=1.5))
    
    def test_invalid_timedelta_format(self):
        """Test that invalid timedelta format raises ValueError."""
        from tools.replay_debug.command_registry import parse_timedelta
        
        with self.assertRaises(ValueError):
            parse_timedelta("invalid")
        
        with self.assertRaises(ValueError):
            parse_timedelta("5x")  # invalid unit
        
        with self.assertRaises(ValueError):
            parse_timedelta("abc")
    
    def test_timedelta_in_command(self):
        """Test using timedelta in command execution."""
        from datetime import timedelta
        captured = {}
        
        @command(
            name="timedelta-cmd",
            arguments=[
                arg(name="duration", arg_type=ArgType.TIMEDELTA, required=True, positional=True, position=0),
            ]
        )
        def handler(context, duration):
            captured['duration'] = duration
        
        executor = CommandExecutor()
        success = executor.execute("timedelta-cmd", ["5m"], {}, context="ctx")
        
        self.assertTrue(success)
        self.assertEqual(captured['duration'], timedelta(minutes=5))


class TestDatetimeParsing(unittest.TestCase):
    """Tests for datetime parsing."""
    
    def setUp(self):
        """Reset the registry before each test."""
        CommandRegistry.reset()
    
    def tearDown(self):
        """Reset the registry after each test."""
        CommandRegistry.reset()
    
    def test_parse_unix_timestamp_seconds(self):
        """Test parsing Unix timestamp in seconds."""
        from tools.replay_debug.command_registry import parse_datetime
        from datetime import datetime, timezone
        
        result = parse_datetime("1764457503")
        expected = datetime.fromtimestamp(1764457503, tz=timezone.utc)
        self.assertEqual(result, expected)
    
    def test_parse_unix_timestamp_milliseconds(self):
        """Test parsing Unix timestamp in milliseconds."""
        from tools.replay_debug.command_registry import parse_datetime
        from datetime import datetime, timezone
        
        result = parse_datetime("1764457503000")
        expected = datetime.fromtimestamp(1764457503, tz=timezone.utc)
        self.assertEqual(result, expected)
    
    def test_parse_unix_timestamp_float(self):
        """Test parsing Unix timestamp as float (with fractional seconds)."""
        from tools.replay_debug.command_registry import parse_datetime
        from datetime import datetime, timezone
        
        result = parse_datetime("1764457503.5")
        expected = datetime.fromtimestamp(1764457503.5, tz=timezone.utc)
        self.assertEqual(result, expected)
    
    def test_parse_american_format(self):
        """Test parsing American format (MM/DD/YYYY)."""
        from tools.replay_debug.command_registry import parse_datetime
        from datetime import datetime, timezone
        
        result = parse_datetime("12/25/2023")
        self.assertEqual(result.month, 12)
        self.assertEqual(result.day, 25)
        self.assertEqual(result.year, 2023)
        
        result = parse_datetime("01/15/2024 14:30:00")
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.hour, 14)
        self.assertEqual(result.minute, 30)
    
    def test_parse_american_format_with_dashes(self):
        """Test parsing American format with dashes (MM-DD-YYYY)."""
        from tools.replay_debug.command_registry import parse_datetime
        
        result = parse_datetime("12-25-2023")
        self.assertEqual(result.month, 12)
        self.assertEqual(result.day, 25)
        self.assertEqual(result.year, 2023)
    
    def test_parse_german_format(self):
        """Test parsing German format (DD.MM.YYYY)."""
        from tools.replay_debug.command_registry import parse_datetime
        from datetime import datetime, timezone
        
        result = parse_datetime("25.12.2023")
        self.assertEqual(result.day, 25)
        self.assertEqual(result.month, 12)
        self.assertEqual(result.year, 2023)
        
        result = parse_datetime("15.01.2024 14:30:00")
        self.assertEqual(result.day, 15)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.hour, 14)
        self.assertEqual(result.minute, 30)
    
    def test_parse_iso_format(self):
        """Test parsing ISO format."""
        from tools.replay_debug.command_registry import parse_datetime
        from datetime import datetime, timezone
        
        result = parse_datetime("2023-12-25T14:30:00")
        self.assertEqual(result.year, 2023)
        self.assertEqual(result.month, 12)
        self.assertEqual(result.day, 25)
        self.assertEqual(result.hour, 14)
        self.assertEqual(result.minute, 30)
        
        result = parse_datetime("2023-12-25")
        self.assertEqual(result.year, 2023)
        self.assertEqual(result.month, 12)
        self.assertEqual(result.day, 25)
    
    def test_invalid_datetime_format(self):
        """Test that invalid datetime format raises ValueError."""
        from tools.replay_debug.command_registry import parse_datetime
        
        with self.assertRaises(ValueError):
            parse_datetime("invalid")
        
        with self.assertRaises(ValueError):
            parse_datetime("not-a-date")
    
    def test_datetime_in_command(self):
        """Test using datetime in command execution."""
        from datetime import datetime, timezone
        captured = {}
        
        @command(
            name="datetime-cmd",
            arguments=[
                arg(name="timestamp", arg_type=ArgType.DATETIME, required=True, positional=True, position=0),
            ]
        )
        def handler(context, timestamp):
            captured['timestamp'] = timestamp
        
        executor = CommandExecutor()
        success = executor.execute("datetime-cmd", ["1764457503"], {}, context="ctx")
        
        self.assertTrue(success)
        expected = datetime.fromtimestamp(1764457503, tz=timezone.utc)
        self.assertEqual(captured['timestamp'], expected)


if __name__ == "__main__":
    unittest.main()
