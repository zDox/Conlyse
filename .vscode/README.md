# VS Code Configuration

This directory contains pre-configured VS Code settings for developing ConflictInterface.

## Files

- **launch.json** - Debug configurations for Server Converter and Observer
- **tasks.json** - Build and infrastructure management tasks
- **settings.json** - Workspace settings (Python, C++, file exclusions)
- **extensions.json** - Recommended extensions

## Quick Start

1. Open the workspace in VS Code
2. Install recommended extensions (VS Code will prompt)
3. Run the task "start-dev-infrastructure" (Ctrl+Shift+P → Tasks: Run Task)
4. Press F5 to start debugging

## Launch Configurations

### Server Converter (Local Dev)
- Runs the converter with local development config
- Full debugging support
- Breakpoints, variable inspection, etc.

### Server Converter (Verbose)
- Same as above but with verbose logging
- Useful for troubleshooting

### Server Observer (C++ Debug)
- Debugs the C++ observer application
- Requires building first (use "build-server-observer-debug" task)
- GDB integration

## Tasks

### build-server-observer-debug
Builds the Server Observer in debug mode with CMake.

### start-dev-infrastructure
Starts PostgreSQL, Redis, and MinIO in Docker.
Equivalent to: `./stack.sh start-dev`

### stop-dev-infrastructure
Stops the development infrastructure.

### test-dev-environment
Runs the verification script to check all services.

## Usage Tips

1. **Start infrastructure first**: Run the "start-dev-infrastructure" task before debugging
2. **Verify setup**: Run "test-dev-environment" task to ensure everything is working
3. **Set breakpoints**: Click in the gutter to the left of line numbers
4. **Debug panel**: View variables, call stack, and breakpoints in the left sidebar
5. **Integrated terminal**: Use Ctrl+` to open terminal for additional commands

## Customization

Feel free to modify these files for your workflow:
- Add new launch configurations
- Create custom tasks
- Adjust workspace settings

## See Also

- [DEVELOPMENT.md](../DEVELOPMENT.md) - Complete development guide
- [DOCKER.md](../DOCKER.md) - Docker deployment guide
