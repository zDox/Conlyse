# Replay System Documentation

The ConflictInterface replay system provides efficient bidirectional recording and playback of game state changes. It enables rewinding and fast-forwarding through game history with minimal storage overhead by storing only the differences (patches) between game states.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Core Data Structures](#core-data-structures)
- [Key Algorithms](#key-algorithms)
- [Storage Format](#storage-format)
- [Usage Examples](#usage-examples)
- [API Reference](#api-reference)

## Architecture Overview

The replay system consists of several interconnected components:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Replay                                   │
│  (Main interface for recording and playback)                    │
├─────────────────────────────────────────────────────────────────┤
│                      ReplayStorage                               │
│  (Handles file I/O, compression, and data persistence)          │
├─────────────────────────────────────────────────────────────────┤
│           PathTree                │           PatchGraph         │
│  (Efficient path management       │  (Temporal navigation        │
│   using tree algorithms)          │   between states)            │
├───────────────────────────────────┼──────────────────────────────┤
│         PathTreeNode              │        PatchGraphNode        │
│  (Individual path elements)       │  (Single patch with ops)     │
└───────────────────────────────────┴──────────────────────────────┘
```

### Component Responsibilities

| Component | Purpose |
|-----------|---------|
| **Replay** | High-level API for recording game state changes and applying patches during playback |
| **ReplayStorage** | Serialization, compression (LZ4), and disk I/O for replay files |
| **PathTree** | Manages JSON paths as a tree structure with O(1) path lookups |
| **PatchGraph** | Graph-based navigation between timestamps using Dijkstra's algorithm |
| **BidirectionalReplayPatch** | Contains forward and backward patches for time travel |

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

## Key Algorithms

### 1. Euler Tour for Tree Preprocessing

The PathTree uses an Euler tour to enable efficient Lowest Common Ancestor (LCA) queries. The Euler tour flattens the tree into an array by recording each node when entering and leaving it during a DFS traversal.

```
Tree Structure:          Euler Tour:
      root(0)            [0, 1, 0, 2, 4, 2, 5, 6, 5, 2, 0, 3, 0]
     /  |  \
    1   2   3            Entry times (tin): [0, 1, 3, 11, 4, 6, 7]
       / \               Exit times (tout): [12, 2, 9, 12, 5, 8, 8]
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

## Storage Format

Replay files use a chunked binary format with LZ4 compression:

```
┌─────────────────────────────────────────────────────┐
│  Chunk 1: Metadata (pickled)                        │
│  [4 bytes: length][compressed data]                 │
├─────────────────────────────────────────────────────┤
│  Chunk 2: Initial Game State (pickled bytes)        │
│  [4 bytes: length][compressed data]                 │
├─────────────────────────────────────────────────────┤
│  Chunk 3: Static Map Data (pickled bytes)           │
│  [4 bytes: length][compressed data]                 │
├─────────────────────────────────────────────────────┤
│  Chunk 4: PathTree (pickled)                        │
│  [4 bytes: length][compressed data]                 │
├─────────────────────────────────────────────────────┤
│  Chunk 5: PatchGraph (pickled)                      │
│  [4 bytes: length][compressed data]                 │
└─────────────────────────────────────────────────────┘
```

Each chunk is independently compressed, allowing partial reads (e.g., reading only metadata without loading the entire file).

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
from datetime import datetime, UTC
from conflict_interface.replay.replay import Replay
from conflict_interface.replay.make_bipatch_between_gamestates import make_bireplay_patch

# Create a new replay file
replay_path = Path("my_replay.bin")
game_id = 12345
player_id = 67890

with Replay(replay_path, mode='w', game_id=game_id, player_id=player_id) as replay:
    # Record the initial game state
    replay.record_initial_game_state(
        game_state=initial_state,
        time_stamp=datetime.now(UTC),
        game_id=game_id,
        player_id=player_id
    )

    # Record static map data
    replay.record_static_map_data(
        static_map_data=map_data,
        game_id=game_id,
        player_id=player_id
    )

    # For each state change, create and record a bidirectional patch
    previous_state = initial_state
    for new_state, timestamp in state_changes:
        bi_patch = make_bireplay_patch(previous_state, new_state)
        replay.record_patch(
            time_stamp=timestamp,
            game_id=game_id,
            player_id=player_id,
            replay_patch=bi_patch
        )
        previous_state = new_state
```

### Playing Back a Replay

```python
from conflict_interface.interface.replay_interface import ReplayInterface
from datetime import datetime, UTC

# Open an existing replay
replay_interface = ReplayInterface(Path("my_replay.bin"))
replay_interface.open()

# Get available timestamps
timestamps = replay_interface.get_timestamps()
print(f"Replay has {len(timestamps)} states")

# Load the initial state
game_state = replay_interface.storage.initial_game_state

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

### Appending to an Existing Replay

```python
# Open in append mode
with Replay(replay_path, mode='a') as replay:
    # Record additional patches
    bi_patch = make_bireplay_patch(current_state, new_state)
    replay.record_patch(
        time_stamp=datetime.now(UTC),
        game_id=replay.game_id,
        player_id=replay.player_id,
        replay_patch=bi_patch
    )
```

## API Reference

### Replay Class

```python
class Replay:
    def __init__(self, file_path: Path, mode: Literal['r', 'w', 'a'] = 'r',
                 game_id: int = None, player_id: int = None)
    
    def open(self) -> Replay
    def close(self) -> None
    
    # Recording methods (mode='w' or 'a')
    def record_initial_game_state(self, game_state: GameState, time_stamp: datetime,
                                   game_id: int, player_id: int) -> None
    def record_static_map_data(self, static_map_data: StaticMapData,
                                game_id: int, player_id: int) -> None
    def record_bipatch(self, time_stamp: datetime, game_id: int, player_id: int,
                       replay_patch: BidirectionalReplayPatch) -> None
    
    # Playback methods (mode='r')
    def load_initial_game_state(self) -> GameState
    def load_static_map_data(self) -> StaticMapData
    def apply_patch(self, patch: PatchGraphNode, game_state: GameState,
                    game_interface: ReplayInterface) -> None
    
    # Utility methods
    def get_start_time(self) -> datetime
    def get_last_time(self) -> datetime
```

### ReplayInterface Class

The ReplayInterface provides a higher-level API for replay playback:

```python
class ReplayInterface:
    def __init__(self, replay_path: Path)
    
    def open(self) -> None
    def close(self) -> None
    
    def jump_to(self, target_time: datetime) -> list[PatchGraphNode]
    def jump_to_next_patch(self) -> PatchGraphNode | None
    
    def get_timestamps(self) -> list[datetime]
    def get_armies(self) -> list[Army]
    
    @property
    def game_state(self) -> GameState
```

### Patch Generation

```python
from conflict_interface.replay.make_bipatch_between_gamestates import make_bireplay_patch

# Generate bidirectional patch between two states
bi_patch: BidirectionalReplayPatch = make_bireplay_patch(old_state, new_state)

# Access individual patches
forward_operations = bi_patch.forward_patch.operations
backward_operations = bi_patch.backward_patch.operations
```

## Performance Considerations

1. **Path Deduplication**: Common path prefixes are shared, reducing memory usage
2. **Lazy Reference Resolution**: Object references are resolved only when needed using the Steiner tree algorithm
3. **LZ4 Compression**: Fast compression/decompression with good compression ratios
4. **Columnar Storage**: Patches use columnar format for better compression and faster access
5. **Bidirectional Patches**: Enables efficient backward navigation without recomputing diffs

## File Requirements

Before saving a replay file to disk, ensure both `initial_game_state_b` and `static_map_data_b` are set (they can be empty bytes `b''` if not applicable):

```python
replay.storage._initial_game_state_b = pickle.dumps(game_state)  # or b''
replay.storage._static_map_data_b = pickle.dumps(static_map_data)  # or b''
```
