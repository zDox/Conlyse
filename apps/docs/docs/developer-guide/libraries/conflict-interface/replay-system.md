---
id: replay-system
title: Replay System
---

The ConflictInterface replay system provides efficient bidirectional recording and playback of game state changes. It enables rewinding and fast-forwarding through game history with minimal storage overhead by storing only the differences (patches) between game states, using a segmented, versioned timeline format.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Core Data Structures](#core-data-structures)
- [Key Algorithms](#key-algorithms)
- [Storage Format](#storage-format)
- [Usage Examples](#usage-examples)
- [Hook System](#hook-system)
- [Performance Considerations](#performance-considerations)

## Architecture Overview

The replay system is organized around a timeline of replay segments stored in a compressed file, plus a high-level interface used for playback:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ReplayTimeline (file)                             │
│  (Zstd-compressed container for multiple ReplaySegment intervals)          │
├─────────────────────────────────────────────────────────────────────────────┤
│                             ReplaySegment                                  │
│  (Owns ReplayStorage, patch graph, and per-segment metadata)               │
├─────────────────────────────────────────────────────────────────────────────┤
│                           ReplayStorage                                    │
│  (Chunked LZ4 layout: metadata, states, PathTree, PatchGraph, patches)     │
├─────────────────────────────────────────────────────────────────────────────┤
│   PathTree / PathTreeNode         │         PatchGraph / PatchGraphNode    │
│  (Deduplicated JSON paths)       │   (Temporal navigation between states)  │
└──────────────────────────────────┴──────────────────────────────────────────┘

High-level APIs:

- ReplayBuilder → produces ReplayTimeline files from JSON responses.
- ReplayInterface → reads ReplayTimeline files and exposes a GameInterface-compatible API with time travel and hooks.
```

### Component Responsibilities

| Component | Purpose |
|-----------|---------|
| **ReplayTimeline** | Timeline-level container for segments, file header, and timeline metadata (zstd-compressed `RPLYZSTD` file) |
| **ReplaySegment** | Segment-level owner of `ReplayStorage`, patch graph, and initial/last game state within a time interval |
| **ReplayStorage** | Serialization, compression (LZ4), and disk I/O for replay files |
| **PathTree** | Manages JSON paths as a tree structure with O(1) path lookups |
| **PatchGraph** | Graph-based navigation between timestamps using Dijkstra's algorithm |
| **BidirectionalReplayPatch** | Contains forward and backward patches for time travel |
| **ReplayBuilder** | High-level builder that converts a stream of API JSON responses into a replay file (`ReplayTimeline`) |
| **ReplayInterface** | High-level read-only interface for replay playback and time travel |
| **ReplayHookSystem** | Dispatches change events while patches are applied during playback |

### Timeline & Segments

The `ReplayTimeline` stores one or more non-overlapping `ReplaySegment` intervals. Each segment:

- Owns its own `ReplayStorage` and patch graph.
- Has a fixed datatype `version` and a `map_id` stored in metadata.
- Covers a continuous time range \([start, end]\), where the last segment may be open-ended during recording.

When recording via `ReplayBuilder`, new segments are created as needed (for example when a full game state arrives, or when a datatype version changes). During playback, `ReplayInterface` locates the correct segment for a requested timestamp and applies patches only within that segment.

**Supported datatype versions:** To see which game/client datatype versions this library supports, use `conflict_interface.versions.get_supported_datatype_versions()`. The latest supported version is `conflict_interface.versions.LATEST_VERSION`.


## Core Data Structures

### PathTree

The PathTree stores all unique paths in the game state as a tree structure. Each path (e.g., `['units', 0, 'health']`) is represented as a series of connected nodes.

```python
class PathTree:
    root: PathTreeNode          # Root node of the tree
    idx_counter: int            # Next available index
    idx_to_node: dict[int, PathTreeNode]  # Fast index-to-node lookup
    
    # Precomputed arrays for LCA queries (see Algorithms section)
    euler: array               # Euler tour traversal
    tin: array                 # Entry times
    tout: array                # Exit times
    depth: array               # Node depths
    st: list[array]            # Sparse table for RMQ
```

**Key Features:**
- Paths are deduplicated - common prefixes share nodes
- O(1) path lookup using index-to-node mapping
- Supports efficient Lowest Common Ancestor (LCA) queries

### PathTreeNode

Represents a single element in a path (e.g., an attribute name or list index).

```python
class PathTreeNode:
    path_element: str | int    # The path segment (attribute name or index)
    index: int                 # Unique identifier in the tree
    is_leaf: bool              # True if no children
    reference: object          # Runtime reference to the actual object
    children: dict[str, PathTreeNode]  # Child nodes
```

**Note:** The `reference` field points to the *parent* object, not the value at this path. For a path like `['units', 0, 'health']`, the node for `'health'` has `reference` pointing to the unit object at index 0, not the health value itself.

### PatchGraph

The PatchGraph manages the temporal relationships between patches. Each patch connects two timestamps, and the graph enables efficient navigation from any timestamp to any other.

```python
class PatchGraph:
    time_stamps_cache: list[int]  # Sorted list of all timestamps
    patches: dict[tuple[int, int], PatchGraphNode]  # (from, to) -> patch
    adj: dict[int, list[int]]    # Adjacency list for pathfinding
```

### PatchGraphNode

Contains the actual patch operations between two timestamps.

```python
class PatchGraphNode:
    from_timestamp: int        # Source timestamp (seconds since epoch)
    to_timestamp: int          # Target timestamp
    op_types: list[int]        # Operation types (ADD=1, REPLACE=2, REMOVE=3)
    paths: list[int]           # Path indices into PathTree
    values: list[Any]          # Values for each operation
    cost: int                  # Cost for pathfinding (currently fixed at 1)
```

### BidirectionalReplayPatch

Holds both forward and backward patches to enable bidirectional navigation.

```python
class BidirectionalReplayPatch:
    forward_patch: ReplayPatch   # Apply to move forward in time
    backward_patch: ReplayPatch  # Apply to move backward in time
```

### Operation Types

The system supports three operation types:

| Type | Key | Constant | Description |
|------|-----|----------|-------------|
| Add | `"a"` | `ADD_OPERATION = 1` | Add a new value to a list or dict |
| Replace | `"p"` | `REPLACE_OPERATION = 2` | Replace an existing value |
| Remove | `"r"` | `REMOVE_OPERATION = 3` | Remove a value from a list, dict, or set to None |

### TimelineMetadata

At the file level, `TimelineMetadata` stores metadata common to the entire replay file:

```python
class TimelineMetadata:
    game_ended: bool
    start_of_game: int   # Unix seconds, 0 if unknown
    end_of_game: int     # Unix seconds, 0 if unknown
    game_id: int
    player_id: int
    scenario_id: int
    day_of_game: int
    speed: int           # integer speed multiplier (e.g. 1, 2, 4)
    segment_count: int   # number of segments in this file
```

`ReplayTimeline` keeps this structure in sync with the current set of segments when writing to disk.

### SegmentMetadata

Each `ReplaySegment` has a `SegmentMetadata` (accessed via `ReplayStorage.metadata`) that holds segment-local information such as:

- `start_time` / `last_time` (Unix seconds for the segment interval).
- `version` (datatype version used in this segment).
- `map_id` (string key referencing external static map data).
- `current_patches` / `max_patches` (how many patches exist and capacity).
- Flags like `is_fragmented` used during append mode.

This metadata is stored inside the segment payload and is loaded lazily as needed.

## Key Algorithms

### 1. Euler Tour for Tree Preprocessing

The PathTree uses an Euler tour to enable efficient Lowest Common Ancestor (LCA) queries. The Euler tour flattens the tree into an array by recording each node when entering and leaving it during a DFS traversal.

```
Tree Structure:          Euler Tour:
      root(0)            [0, 1, 0, 2, 4, 2, 5, 6, 5, 2, 0, 3, 0]
     /  |  \
    1   2   3            Entry times (tin): [0, 1, 3, 11, 4, 5, 8]
       / \               Exit times (tout): [12, 2, 10, 12, 4, 7, 9]
      4   5
          |
          6
```

**Time Complexity:** O(n) preprocessing, where n is the number of nodes.

### 2. LCA using Range Minimum Query (RMQ)

Finding the LCA of two nodes is reduced to a Range Minimum Query on the Euler tour. The system uses a Sparse Table for O(1) RMQ queries after O(n log n) preprocessing.

```python
def lca(u_idx: int, v_idx: int) -> int:
    # Find positions in Euler tour
    left = self.first[u_idx]
    right = self.first[v_idx]
    if left > right:
        left, right = right, left
    
    # Sparse table RMQ for minimum depth
    length = right - left + 1
    k = self.log[length]
    a = self.st[k][left]
    b = self.st[k][right - (1 << k) + 1]
    
    # Return node with minimum depth
    return self.euler[a] if self.depth[self.euler[a]] < self.depth[self.euler[b]] else self.euler[b]
```

**Time Complexity:** O(1) per query after O(n log n) preprocessing.

### 3. Steiner Tree Construction

When applying a patch, the system needs to resolve object references for paths that haven't been accessed yet. It constructs a Steiner tree - the minimal subtree connecting all required nodes - to efficiently traverse only the necessary paths.

**Algorithm Steps:**
1. Sort nodes by entry time (tin)
2. For each consecutive pair, add their LCA
3. Build a virtual tree using a stack-based approach
4. Expand compressed edges to full tree paths

```python
def build_steiner_tree(nodes: list[int]) -> dict[int, list[int]]:
    # Include root and sort by tin
    nodes_sorted = sorted(set(nodes + [root.index]), key=lambda x: tin[x])
    
    # Insert LCAs between consecutive nodes
    full = nodes_sorted[:]
    for i in range(len(nodes_sorted) - 1):
        full.append(lca(nodes_sorted[i], nodes_sorted[i + 1]))
    
    # Build virtual tree and expand to full edges
    ...
```

**Time Complexity:** O(k log k) where k is the number of nodes to connect.

### 4. BFS Reference Resolution

After building the Steiner tree, BFS traversal resolves object references from root to leaves:

```python
def bfs_set_references(sub_tree: dict[int, list[int]], game_state: GameState):
    q = deque([(root.index, game_state)])
    visited = {root.index}
    
    while q:
        u, ref = q.popleft()
        for v in sub_tree.get(u, []):
            if v not in visited:
                visited.add(v)
                node = idx_to_node[v]
                node.set_reference(ref)
                child_ref = get_child_reference(ref, node.path_element)
                q.append((v, child_ref))
```

### 5. Dijkstra's Algorithm for Patch Path Finding

When jumping to a target timestamp, the PatchGraph finds the shortest path of patches to apply using Dijkstra's algorithm:

```python
def find_patch_path(from_time: datetime, to_time: datetime) -> list[PatchGraphNode]:
    heap = [(0, from_time, [])]  # (cost, current_time, path)
    visited = set()
    
    while heap:
        cost, current, path = heappop(heap)
        if current == to_time:
            return path
        if current in visited:
            continue
        visited.add(current)
        
        for neighbor in adj[current]:
            if neighbor not in visited:
                patch = patches[(current, neighbor)]
                heappush(heap, (cost + patch.cost, neighbor, path + [patch]))
```

**Time Complexity:** O((E + V) log V) where E is the number of patches and V is the number of unique timestamps.

### 6. Diff Generation

The `make_bireplay_patch` function recursively compares two game states to generate bidirectional patches:

```python
def make_bireplay_patch(self: Any, other: Any) -> BidirectionalReplayPatch:
    forward = make_replay_patch(self, other)   # Changes from self to other
    backward = make_replay_patch(other, self)  # Changes from other to self
    return BidirectionalReplayPatch.from_existing_patches(forward, backward)
```

The comparison handles:
- **GameObjects**: Compares all mapped attributes recursively
- **Lists**: Handles additions, removals, and modifications element-by-element
- **Dicts**: Detects added, removed, and modified keys
- **Simple types**: Direct equality comparison

These algorithms are used under the hood when `ReplaySegment.apply_patch` is called by `ReplayInterface.jump_to` and related navigation methods.

## Storage Format

Replay segment payloads managed by `ReplayStorage` use a chunked binary format with LZ4 compression:

```
┌─────────────────────────────────────────────────────┐
│  Chunk 1: Metadata (fixed-size header)              │
│  [4 bytes: length][raw bytes]                       │
├─────────────────────────────────────────────────────┤
│  Chunk 2: Initial Game State (pickled / binary)     │
│  [4 bytes: length][compressed data]                 │
├─────────────────────────────────────────────────────┤
│  Chunk 3: PathTree                                  │
│  [4 bytes: length][compressed data]                 │
├─────────────────────────────────────────────────────┤
│  Chunk 4: Patch Graph (compressed)                  │
│  [4 bytes: length][compressed data]                 │
├─────────────────────────────────────────────────────┤
│  Chunk 5: Patch index (uncompressed)                │
│  [4 bytes: length][raw bytes]                       │
├─────────────────────────────────────────────────────┤
│  Chunk 6: Data pool (patch data, uncompressed)      │
│  [4 bytes: length][raw bytes]                       │
├─────────────────────────────────────────────────────┤
│  Chunk 7: Last Game State (pickled / binary)        │
│  [4 bytes: length][compressed data]                 │
└─────────────────────────────────────────────────────┘
```

Static map data is no longer embedded inside replay segments. Instead, each segment's metadata stores a `map_id: str` that can be used to look up `StaticMapData` externally.

### ReplayTimeline file header

Replay files written by `ReplayTimeline` (version 2) are zstd-compressed and have the following header before the per-segment records:

```
┌───────────────────────────────────────────────────────────────┐
│ Magic            8 bytes   ASCII "RPLYZSTD"                   │
├───────────────────────────────────────────────────────────────┤
│ Version          4 bytes   little-endian uint32 (currently 2)│
├───────────────────────────────────────────────────────────────┤
│ TimelineMetadata N bytes   fixed-size struct, see below      │
├───────────────────────────────────────────────────────────────┤
│ Segments         ...       repeated segment records          │
└───────────────────────────────────────────────────────────────┘
```

The `TimelineMetadata` struct is a fixed-size little-endian layout:

```text
bool   game_ended
int32  start_of_game   # Unix seconds, 0 if unknown
int32  end_of_game     # Unix seconds, 0 if unknown
int32  game_id
int32  player_id
int32  scenario_id
int32  day_of_game
int32  speed           # integer speed multiplier (e.g. 1, 2, 4)
int32  segment_count   # number of segments in this file
```

After the header, each segment is stored as:

```text
int64 start_ns    # nanoseconds since epoch
int64 end_ns      # nanoseconds since epoch (can be equal to start_ns)
int32 version     # datatype version for this segment
uint64 size       # number of bytes in the following payload
bytes payload     # raw segment data managed by ReplayStorage
```

Note that there is **no separate segment-count field in the header** anymore; the total number of segments is stored inside `TimelineMetadata.segment_count`.

### Patch Serialization

Individual patches use a columnar storage format for efficiency:

```python
data = {
    "p": path_list,           # Deduplicated path table
    "o": ops_col.tobytes(),   # Operation types (1 byte each)
    "i": path_indices.tobytes(),  # Path references (2 or 4 bytes each)
    "v": values_col,          # Operation values
    "t": index_type           # "H" for 16-bit or "I" for 32-bit indices
}
```

## Usage Examples

### Recording a Replay

```python
from pathlib import Path
from conflict_interface.replay.replay_builder import ReplayBuilder
from conflict_interface.replay.response_metadata import ResponseMetadata

# Assume you have captured a list of (ResponseMetadata, json_response) tuples
json_responses: list[tuple[ResponseMetadata, dict]] = load_recorded_responses()

replay_path = Path("my_replay.conrp")
game_id = 12345
player_id = 67890

builder = ReplayBuilder(replay_path, game_id=game_id, player_id=player_id)

# Create a new replay file from the recorded responses
initial_index = builder.create_replay(json_responses)

# Later, you can append additional responses (for example, from a live game)
more_responses: list[tuple[ResponseMetadata, dict]] = fetch_more_responses()
builder.append_json_responses(more_responses)
```

### Playing Back a Replay

```python
from conflict_interface.interface.replay_interface import ReplayInterface
from datetime import datetime, UTC

# Open an existing replay
replay_interface = ReplayInterface(
    file_path=Path("my_replay.conrp"),
    static_map_data={"my_map_id": Path("static_map_my_map_id.json")},
)
replay_interface.open(mode="r")

# Get available timestamps
timestamps = replay_interface.get_timestamps()
print(f"Replay has {len(timestamps)} states")

# Jump to a specific time
target_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
replay_interface.jump_to(target_time)

# Or navigate sequentially
replay_interface.jump_to_next_patch()

# Access the current game state
current_state = replay_interface.game_state
armies = replay_interface.get_armies()

# Clean up
replay_interface.close()
```

### Metadata-Only Inspection

You can inspect metadata without loading the full game state by opening in `read_metadata` mode:

```python
from conflict_interface.interface.replay_interface import ReplayInterface
from pathlib import Path

replay_interface = ReplayInterface(file_path=Path("my_replay.conrp"))
replay_interface.open(mode="read_metadata")

segments_metadata = replay_interface.get_segments_metadata()
timeline_metadata = replay_interface.get_timeline_metadata()
required_map_ids = replay_interface.get_required_map_ids()
required_versions = replay_interface.get_required_versions()
total_patches = replay_interface.get_total_patches()

replay_interface.close()
```


## Hook System

The replay system includes a hook/event system that can emit structured change events as patches are applied during playback.

- `ReplayHookSystem` is created per `ReplaySegment` and is owned by `ReplayInterface`.
- `ReplayHook` describes a subscription: tag, path index, change types (add/replace/remove), and optional attributes.
- `ReplayHookEvent` is an event payload with a tag, object reference, and changed attributes.
- `ReplayHookTag` is an enum that includes tags like `ProvinceChanged`, `PlayerChanged`, `TeamChanged`, `ArmyChanged`, `GameInfoChanged`, and `SegmentSwitch`.

`ReplayInterface` exposes helpers for working with hooks:

```python
hook_system = replay_interface.get_hook_system()
events_by_tag = replay_interface.poll_events()
replay_interface.unregister_all_hooks()

replay_interface.register_province_trigger(attributes=["owner_id", "resource_production"])
replay_interface.unregister_province_trigger()
replay_interface.register_player_trigger()
replay_interface.unregister_player_trigger()
replay_interface.register_team_trigger()
replay_interface.unregister_team_trigger()
replay_interface.register_army_trigger()
replay_interface.unregister_army_trigger()
replay_interface.register_game_info_trigger()
replay_interface.unregister_game_info_trigger()
```

A typical pattern is:

1. Register triggers and/or hooks.
2. Call `jump_to` or `jump_to_next_patch` on `ReplayInterface`.
3. Call `poll_events()` to retrieve and clear the accumulated events.

## Performance Considerations

1. **Path Deduplication**: Common path prefixes are shared in `PathTree`, reducing memory usage.
2. **Lazy Reference Resolution**: Object references are resolved only when needed using the Steiner tree algorithm and BFS.
3. **LZ4 Compression**: Segment payloads are LZ4-compressed for fast compression/decompression with good compression ratios.
4. **Columnar Storage**: Patches use a columnar format for better compression and faster access.
5. **Bidirectional Patches**: Forward and backward patches allow efficient backward navigation without recomputing diffs.
6. **Segmented Timeline**: Multiple segments in a `ReplayTimeline` allow large games and version transitions to be handled without loading everything at once.