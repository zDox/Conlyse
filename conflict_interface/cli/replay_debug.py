#!/usr/bin/env python3
"""
Replay Debug CLI Tool - Backward compatibility wrapper.

This module provides backward compatibility by importing from the new modular structure.
The actual implementation is now in the replay_debug package.
"""

# Import everything from the new module structure
from conflict_interface.cli.replay_debug import *
from conflict_interface.cli.replay_debug.__main__ import main

# Maintain backward compatibility
__all__ = ['ReplayDebugCLI', 'run_interactive_shell', 'main']

if __name__ == "__main__":
    import sys
    sys.exit(main())
