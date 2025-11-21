# Replay Debug CLI Tool

A command-line tool for debugging and inspecting Conflict Interface replay files.

## Overview

The Replay Debug CLI Tool provides two modes of operation:

### Original Mode (Patch Analysis)
- Listing all patches (forward and backward)
- Viewing all operations in a specific patch
- Viewing all operations that start with a specific path
- Operations overview showing statistics grouped by state
- Counting operations across all patches
- Counting operations by path prefix

### Enhanced Mode (Live State Inspection)
- Jump navigation through replay timeline:
  - Jump by relative time (e.g., +60 seconds, -5 minutes)
  - Jump by absolute time (specific timestamp)
  - Jump by number of patches (e.g., +5 patches forward, -3 patches backward)
  - Jump by timestamp index
- View game state at any point:
  - Navigate to specific paths in the game state
  - Pretty print values using recur_path
  - Search for attributes
  - List available state categories
- Direct access to ReplayInterface (ritf) object for advanced usage
- Python REPL with ritf available for interactive scripting

## Installation

The CLI tool is installed as part of the conflict-interface package. After installation, you can run it using:

```bash
replay-debug <replay_file> [--enhanced] [command] [options]
```

Or directly via Python module:

```bash
python -m tools.replay_debug <replay_file> [--enhanced] [command] [options]
```

## Usage

### Interactive Mode (Recommended)

Start the interactive shell to explore a replay file:

```bash
# Original mode (patch analysis)
replay-debug replay.db

# Enhanced mode (with navigation and state inspection)
replay-debug replay.db --enhanced
```

### Single Command Mode

Run a single command and exit (original mode only):

```bash
replay-debug replay.db list-patches
replay-debug replay.db view-operations-by-path "states/map_state"
```

## Commands

### Original Mode Commands (Patch Analysis)

### 1. list-patches

Lists all patches in the replay with timestamps, including both forward and backward patches.

**Usage:**
```bash
replay-debug replay.db list-patches
```

**Output:**
```
Replay file: replay.db
Total patches: 10
Start time: 2023-01-01 12:00:00+00:00
End time: 2023-01-01 12:05:00+00:00

All patches (including forward and backward):
----------------------------------------------------------------------------------------------------
#     From Timestamp       To Timestamp         Direction  Ops     
----------------------------------------------------------------------------------------------------
1     2023-01-01T12:00:00+00:00 2023-01-01T12:01:00+00:00 Forward    4       
2     2023-01-01T12:01:00+00:00 2023-01-01T12:00:00+00:00 Backward   4
...
```

### 2. view-patch

Views operations in a specific patch.

**Usage:**
```bash
replay-debug replay.db view-patch <from_timestamp> <to_timestamp>
```

**Example:**
```bash
replay-debug replay.db view-patch 1672574400000 1672574460000
```

**Output:**
```
Patch: 1672574400000 -> 1672574460000 (Forward)
From: 2023-01-01T12:00:00+00:00
To:   2023-01-01T12:01:00+00:00
Total operations: 4

Operations by type:
--------------------------------------------------------------------------------
  Add:     2
  Replace: 2
  Remove:  0

First 20 operations:
--------------------------------------------------------------------------------
   1. a       states/map_state/province/0              -> province_data_0
   2. p       states/player_state/gold                 -> 0
...
```

### 3. view-operations-by-path

Views all operations that start with a specific path across all patches (both forward and backward).

**Usage:**
```bash
replay-debug replay.db view-operations-by-path <path_prefix> [--limit N]
```

**Examples:**
```bash
# View all operations on map state
replay-debug replay.db view-operations-by-path "states/map_state"

# View first 10 operations on player state
replay-debug replay.db view-operations-by-path "states/player_state" --limit 10

# View all operations (empty path)
replay-debug replay.db view-operations-by-path "" --limit 50
```

**Output:**
```
Operations with path starting with: 'states/map_state'
Total matching operations: 18
Showing first 10 operations:
----------------------------------------------------------------------------------------------------
#     Patch                     Dir      Type     Path                                Value          
----------------------------------------------------------------------------------------------------
1     ...74400000→1672574460000 Forward  a        states/map_state/province/0         province_data_0
2     ...74460000→1672574400000 Backward r        states/map_state/province/0         None
...
```

### 4. count-operations

Counts the total number of operations across all patches, including forward and backward patches.

**Usage:**
```bash
replay-debug replay.db count-operations
```

**Output:**
```
Total patches: 10
  Forward patches:  5
  Backward patches: 5

Total operations: 48
  Forward operations:  24
  Backward operations: 24

Average operations per patch: 4.80
```

### 5. count-operations-by-path

Counts operations that start with a specific path prefix, across both forward and backward patches.

**Usage:**
```bash
replay-debug replay.db count-operations-by-path <path_prefix>
```

**Examples:**
```bash
# Count operations on map state
replay-debug replay.db count-operations-by-path "states/map_state"

# Count operations on player state
replay-debug replay.db count-operations-by-path "states/player_state"
```

**Output:**
```
Path prefix: 'states/map_state'
Total patches analyzed: 10
Total operations: 48
Matching operations: 18
  In forward patches:  9
  In backward patches: 9
Percentage: 37.50%
```

### Enhanced Mode Commands (Navigation & State Inspection)

#### Navigation Commands

##### info
Display current replay position and metadata.

**Usage:**
```bash
replay-debug> info
```

**Output:**
```
Replay Information
================================================================================
File:        replay.db
Game ID:     12345
Player ID:   67890

Start Time:  2023-01-01T00:00:00+00:00
End Time:    2023-01-01T23:59:59+00:00
Duration:    86399.00 seconds

Current Position:
  Time:      2023-01-01T12:00:00+00:00
  Index:     50
  Progress:  50.0%

Total Timestamps: 100
```

##### jump-relative (jr)
Jump by relative time from current position.

**Usage:**
```bash
replay-debug> jump-relative <seconds>
replay-debug> jr <seconds>
```

**Examples:**
```bash
replay-debug> jr 60          # Jump forward 60 seconds
replay-debug> jr -300        # Jump backward 5 minutes
replay-debug> jr 3600        # Jump forward 1 hour
```

##### jump-absolute (ja)
Jump to an absolute timestamp (ISO format).

**Usage:**
```bash
replay-debug> jump-absolute <timestamp>
replay-debug> ja <timestamp>
```

**Examples:**
```bash
replay-debug> ja 2023-01-01T15:30:00+00:00
replay-debug> ja "2023-01-01 15:30:00"
```

##### jump-patches (jp)
Jump forward or backward by a number of patches.

**Usage:**
```bash
replay-debug> jump-patches <num>
replay-debug> jp <num>
```

**Examples:**
```bash
replay-debug> jp 5           # Jump forward 5 patches
replay-debug> jp -3          # Jump backward 3 patches
```

##### jump-index (ji)
Jump to a specific timestamp by its index.

**Usage:**
```bash
replay-debug> jump-index <index>
replay-debug> ji <index>
```

**Examples:**
```bash
replay-debug> ji 42          # Jump to timestamp at index 42
replay-debug> ji 0           # Jump to first timestamp
```

##### list-timestamps (lt)
List all timestamps with their indices.

**Usage:**
```bash
replay-debug> list-timestamps [--limit N]
replay-debug> lt [--limit N]
```

**Examples:**
```bash
replay-debug> lt             # List first 50 timestamps
replay-debug> lt --limit 100 # List first 100 timestamps
```

**Output:**
```
Total timestamps: 100
Current index: 50
Showing first 50 timestamps:

Index    Timestamp                      Current 
--------------------------------------------------
0        2023-01-01T00:00:00+00:00             
1        2023-01-01T00:10:00+00:00             
...
50       2023-01-01T08:20:00+00:00      >>>    
...
```

#### State Viewing Commands

##### view-state (vs)
View the game state value at a specific path.

**Usage:**
```bash
replay-debug> view-state <path> [--depth N]
replay-debug> vs <path> [--depth N]
```

**Examples:**
```bash
replay-debug> vs states/map_state
replay-debug> vs states/player_state/gold
replay-debug> vs states/map_state/provinces/0 --depth 3
```

**Output:**
```
Path: states/player_state/gold
Type: int
Value Type Hint: <class 'int'>
--------------------------------------------------------------------------------
1500
```

##### list-states (ls)
List available state categories.

**Usage:**
```bash
replay-debug> list-states
replay-debug> ls
```

**Output:**
```
Available state categories:
--------------------------------------------------------------------------------
  states/admin_state - AdminState
  states/map_state - MapState
  states/player_state - PlayerState
  ...

Other game state attributes:
  game_id - int
  timestamp - datetime
```

##### search-paths (sp)
Search for paths containing a specific term.

**Usage:**
```bash
replay-debug> search-paths <term>
replay-debug> sp <term>
```

**Examples:**
```bash
replay-debug> sp "player"    # Search for paths with "player"
replay-debug> sp "gold"      # Search for paths with "gold"
```

**Output:**
```
Found 5 paths containing 'player':
--------------------------------------------------------------------------------
  states/player_state
  states/player_state/player_id
  states/player_state/gold
  states/player_state/resources
  states/players/0/player_id
```

#### Advanced Commands

##### ritf
Display information about the ReplayInterface object.

**Usage:**
```bash
replay-debug> ritf
```

**Output:**
```
ReplayInterface object is available as 'ritf'
Type: <class 'conflict_interface.interface.replay_interface.ReplayInterface'>
Current time: 2023-01-01T12:00:00+00:00
Game ID: 12345
Player ID: 67890

You can access:
  ritf.game_state - Current game state
  ritf.jump_to(datetime) - Jump to timestamp
  ritf.jump_to_next_patch() - Jump forward
  ritf.jump_to_previous_patch() - Jump backward
  ritf.get_timestamps() - Get all timestamps
```

##### python
Enter a Python REPL with the ritf object available.

**Usage:**
```bash
replay-debug> python
```

**Examples:**
```python
>>> ritf.current_time
datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

>>> ritf.game_state.states.player_state.gold
1500

>>> ritf.jump_to_next_patch()
True

>>> ritf.current_time
datetime.datetime(2023, 1, 1, 12, 10, 0, tzinfo=datetime.timezone.utc)

>>> # Exit with Ctrl-D (Unix) or Ctrl-Z (Windows)
```

## Understanding Replay Patches

### Forward and Backward Patches

Replay files contain **bidirectional patches** for efficient time travel:

- **Forward patches**: Move state forward in time (e.g., from timestamp 1000 to 2000)
- **Backward patches**: Move state backward in time (e.g., from timestamp 2000 to 1000)

For each state transition, there are typically two patches:
1. A forward patch to apply changes when moving forward
2. A backward patch to undo changes when moving backward

### Operation Types

Each patch contains three types of operations:

- **Add (a)**: Adds a new value to the game state
- **Replace (p)**: Replaces an existing value with a new one
- **Remove (r)**: Removes a value from the game state

### Path Format

Operations use a path-based system to identify locations in the game state:
- `states/map_state/map/locations/1` - A province in the map state

## Troubleshooting

### File Not Found
```
Error: Replay file 'replay.db' not found.
```
Make sure the replay file path is correct and the file exists.

### No Patches Found
```
No patches found in replay.
```
The replay file may be corrupted or empty. Try with a different replay file.

### Database Error
If you encounter database errors, the replay file may be from a different version or corrupted.
## Example Workflows

### Workflow 1: Exploring Patch Changes
```bash
# Start in original mode to analyze patches
replay-debug replay.db

# List all patches
replay-debug> lp

# View a specific patch
replay-debug> vp 42

# View operations on a specific path
replay-debug> vop "states/map_state" --limit 20 --direction forward
```

### Workflow 2: Time Travel and State Inspection
```bash
# Start in enhanced mode
replay-debug replay.db --enhanced

# Check current position
replay-debug> info

# Jump to a specific time
replay-debug> jr 300           # Jump forward 5 minutes

# View game state
replay-debug> vs states/player_state/gold

# List available states
replay-debug> ls

# Search for specific paths
replay-debug> sp "gold"

# Jump through timestamps
replay-debug> lt --limit 20    # List timestamps
replay-debug> ji 10            # Jump to timestamp 10
```

### Workflow 3: Advanced Analysis with Python REPL
```bash
# Start in enhanced mode
replay-debug replay.db --enhanced

# Enter Python REPL
replay-debug> python

# In Python REPL:
>>> # Get all player IDs
>>> players = ritf.game_state.states.player_state
>>> print(f"Gold: {players.gold}")

>>> # Jump forward and compare
>>> ritf.jump_to_next_patch()
>>> print(f"Gold after patch: {players.gold}")

>>> # Access the navigator directly
>>> from tools.replay_debug import ReplayNavigator
>>> nav = ReplayNavigator(ritf)
>>> nav.jump_by_relative_time(600)  # Jump 10 minutes

>>> # Exit with Ctrl-D
```

## Module Structure

The replay debug tool is now organized into multiple modules for better maintainability:

- `cli.py` - Original CLI for patch analysis
- `enhanced_cli.py` - Enhanced CLI with ReplayInterface integration
- `navigation.py` - Navigation utilities for time travel
- `state_viewer.py` - Game state inspection and pretty printing
- `shell.py` - Original interactive shell
- `enhanced_shell.py` - Enhanced interactive shell with both modes
- `formatters.py` - Output formatting utilities
- `constants.py` - Constants and configuration

## Understanding Replay Patches

### Forward and Backward Patches

Replay files contain **bidirectional patches** for efficient time travel:

- **Forward patches**: Move state forward in time (e.g., from timestamp 1000 to 2000)
- **Backward patches**: Move state backward in time (e.g., from timestamp 2000 to 1000)

For each state transition, there are typically two patches:
1. A forward patch to apply changes when moving forward
2. A backward patch to undo changes when moving backward

### Operation Types

Each patch contains three types of operations:

- **Add (a)**: Adds a new value to the game state
- **Replace (p)**: Replaces an existing value with a new one
- **Remove (r)**: Removes a value from the game state

### Path Format

Operations use a path-based system to identify locations in the game state:
- `states/map_state/map/locations/1` - A province in the map state
- `states/player_state/gold` - Player's gold amount
- `states/admin_state/game_id` - Game ID

## Troubleshooting

### File Not Found
```
Error: Replay file 'replay.db' not found.
```
Make sure the replay file path is correct and the file exists.

### No Patches Found
```
No patches found in replay.
```
The replay file may be corrupted or empty. Try with a different replay file.

### Database Error
If you encounter database errors, the replay file may be from a different version or corrupted.

### Enhanced Mode Requirements
Enhanced mode requires a valid replay file with game state data. If the replay file only contains patches without initial state, enhanced mode may not work properly.

## Performance Notes

- Original mode loads all patches into memory for quick access
- Enhanced mode uses ReplayInterface for live state inspection
- For very large replays, listing all timestamps may take a moment
- Jumping backward requires reloading from initial state and is slower than jumping forward
- Use `--limit` parameters to control output size for large datasets
