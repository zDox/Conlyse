"""
Main entry point for the Replay Debug CLI Tool.
"""
import sys
from tools.replay_debug.cli import ReplayDebugCLI
from tools.replay_debug.shell import run_interactive_shell
from tools.replay_debug.args_parser import MainArgumentParser


def main():
    """Main entry point for the CLI."""
    # Create parser
    parser = MainArgumentParser.create_parser()
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create CLI instance
    cli = ReplayDebugCLI(args.replay_file)
    
    # Open the replay
    if not cli.open_replay():
        return 1
    
    try:
        # Start interactive shell
        run_interactive_shell(cli)
        return 0
    
    finally:
        cli.close_replay()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
