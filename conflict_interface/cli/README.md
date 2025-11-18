# Replay Debug CLI Tool

A command-line tool for debugging and inspecting Conflict Interface replay files.

## Overview

The Replay Debug CLI Tool provides commands to analyze replay files (.db), including:
- Listing all patches (forward and backward)
- Viewing specific patch operations
- Viewing all operations that start with a specific path
- Counting operations across all patches
- Counting operations by path prefix

## Installation

The CLI tool is installed as part of the conflict-interface package. After installation, you can run it using:

```bash
replay-debug <replay_file> <command> [options]
```

Or directly via Python module:

```bash
python -m conflict_interface.cli.replay_debug <replay_file> <command> [options]
```

## Commands

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
- `states/map_state/province/1` - A province in the map state
- `states/player_state/gold` - Player's gold amount
- `game_info/turn` - Current turn number

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

## See Also

- [Replay Interface Documentation](../../interface/replay_interface.py)
- [Replay Patch Format](../../replay/replay_patch.py)
- [Replay Database Schema](../../replay/replay_database.py)
