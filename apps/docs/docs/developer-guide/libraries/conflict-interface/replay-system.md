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
- [Hook System](#hook-system)
- [Performance Considerations](#performance-considerations)
    - [Long Patches](#long-patches)

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

`PathTree.precompute()` builds an Euler tour over the deduplicated PathTree so later LCA queries can be answered via RMQ.

During preprocessing, the tree is traversed once and the following arrays are produced:
- `tin[node_idx]`: entry time (first time the node is visited)
- `tout[node_idx]`: exit time
- `euler`: the flattened traversal sequence of node indices (including re-visits when the traversal backtracks)
- `first[node_idx]`: index of the first occurrence of `node_idx` inside `euler`
- `depth[node_idx]`: depth (distance from `root`)

These arrays (especially `euler`, `first`, `depth`, plus the Range Minimum Query(RMQ) sparse table built from them) are later passed into `steiner_tree_cpp.build_steiner_tree(...)`, where Least Commen Ancestor(LCA) is computed to construct the expanded Steiner subtree.

**Time Complexity:** O(n) preprocessing, where n is the number of nodes.

### 2. LCA using Range Minimum Query (RMQ)

Finding the LCA of two nodes is reduced to a Range Minimum Query (RMQ) on the Euler tour.

`PathTree.precompute_rmq()` builds a sparse table (`st`) where each entry stores the Euler-tour position with the minimum depth in an interval. `steiner_tree_cpp` then uses that RMQ to compute LCA(u, v).

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

When applying a patch, we may need to resolve `PathTreeNode.reference` values for paths that were never accessed earlier. To do that efficiently, the replay builds an *expanded Steiner subtree* connecting all required path nodes (and the root), but expanded so every edge corresponds to a real edge in the underlying PathTree.

In practice:
- `ReplaySegment.apply_patch()` collects `unknown_paths` for patch operations whose `PathTreeNode.reference` is missing.
- `PathTree.build_steiner_tree()` delegates to the C++ routine `steiner_tree_cpp.build_steiner_tree(...)`, using the PathTree’s `parent`, `tin`, `tout`, and RMQ/LCA helpers.

**Algorithm Steps:**
1. Ensure `root_idx` is included; deduplicate input nodes.
2. Sort nodes by `tin`.
3. For each consecutive pair in this sorted order, compute `LCA(u, v)` via RMQ over the Euler tour and add those LCAs to the working set.
4. Sort+deduplicate the full set again (original nodes + LCAs).
5. Build a compressed virtual tree using a stack:
   - pop until the current stack top is an ancestor of `v` (checked via `tin/tout`)
   - record the compressed parent of `v`
6. Expand each compressed edge into real PathTree edges by walking `parent[]` pointers from child up to compressed parent, emitting directed edges `p -> child`.
7. Return an adjacency list `adj[node_idx] = [child_idx, ...]` (children are ordered by `tin` for deterministic output).

```python
def build_steiner_tree(nodes: list[int]) -> dict[int, list[int]]:
    nodes = deduplicate(nodes + [root])
    nodes.sort(key=tin)

    # Insert LCAs between consecutive nodes (sorted by tin)
    full = nodes.copy()
    for i in range(len(nodes) - 1):
        full.append(LCA(nodes[i], nodes[i+1]))  # via RMQ over euler/st/log

    # Build compressed virtual tree (stack) and then expand edges to real edges
    compressed_parent = build_virtual_tree_stack(full, tin, tout)
    adj = expand_edges_to_real_path(compressed_parent, parent)
    return adj
```

**Time Complexity:** O(k log k) where k is the number of nodes to connect.

### 4. BFS Reference Resolution

Given the expanded Steiner subtree adjacency list, reference resolution is done with a BFS over the subtree:

- Direct children of `PathTree.root` are seeded with `reference = game_state`.
- Each subsequent node’s `reference` is derived from its direct parent via `get_reference_from_direct_parent(node)` (i.e., look up the attribute/index/key described by the parent path element).

```python
def bfs_set_references(sub_tree: dict[int, list[int]], game_state: GameState):
    q = deque([])

    # Seed: first-level nodes point at the game_state root.
    for child in root.children.values():
        child.set_reference(game_state)
        q.append(child.index)

    while q:
        u = q.popleft()
        for v in sub_tree.get(u, []):
            node = idx_to_node[v]
            node.set_reference(get_reference_from_direct_parent(node))
            q.append(v)
```

### 5. Dijkstra's Algorithm for Patch Path Finding

When jumping to a target timestamp, the `ReplayInterface` asks the segment’s `PatchGraph` for the shortest patch sequence.

`PatchGraph.find_patch_path()`:
- snaps both endpoints to the closest cached patch timestamps less than or equal to the requested times (`find_prev_timestamp`)
- runs SciPy’s `scipy.sparse.csgraph.dijkstra` over the CSR graph with directed edges weighted by `PatchGraphNode.cost`
- reconstructs the patch sequence by following SciPy’s predecessor array (`return_predecessors=True`)

```python
def find_patch_path(from_time: datetime, to_time: datetime) -> list[PatchGraphNode]:
    from_exact = find_prev_timestamp(int(from_time.timestamp()))
    to_exact = find_prev_timestamp(int(to_time.timestamp()))
    if from_exact is None or to_exact is None:
        raise ValueError("No exact patch timestamps found for the given time range.")

    if from_exact == to_exact:
        return []

    src = time_to_dense_idx[from_exact]
    dst = time_to_dense_idx[to_exact]
    _, pred = scipy_dijkstra(graph_csr, directed=True, indices=src, return_predecessors=True)

    if pred[dst] == -9999:
        raise ValueError("No path")

    path = []
    cur = dst
    while cur != src:
        prev = pred[cur]
        path.append(patches[(dense_idx_to_time[prev], dense_idx_to_time[cur])])
        cur = prev
    return path[::-1]
```

**Time Complexity:** O((E + V) log V) where E is the number of patches and V is the number of unique timestamps.

### 6. Diff Generation

Diff generation happens during recording in `ReplayBuilder`, while it mutates the “current” game state toward the “new” game state while simultaneously recording the operations into a `BidirectionalReplayPatch`.

Concretely:
- For each JSON response, `ReplayBuilder._create_patch_from_json(...)` decides whether it is an incremental update (`full == False`) or a full replacement (`full == True`).
- Incremental updates generate patches by calling `current_state.update(new_state, path=[], rp=bipatch)`.
- The `update(...)` call mutates `current_state` by iterating over its nested state attributes and invoking their `update(...)` methods; when those nested updates detect changes and `rp` is provided, they emit the corresponding `rp.add(...)`, `rp.replace(...)`, and `rp.remove(...)` operations at the computed JSON paths.
- For full replacements, the patch returned is an empty `BidirectionalReplayPatch()`. In this case the new state becomes the segment base (the replay starts applying patches from the new baseline in the next segment).


During playback, `ReplaySegment.apply_patch(...)` applies the recorded `BidirectionalReplayPatch` operations, using the `PathTree` (reference resolution) and `PatchGraph` (timestamp navigation) described above.

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

### Long Patches

For large jumps, applying the patch path step-by-step can become expensive because you may need to apply many intermediate patches. As an optimization, `ReplayInterface.jump_to()` can create an on-demand "long patch" that collapses the net effect of a whole interval into a single patch`.

#### When long patches are created

A long patch is created automatically inside `ReplayInterface.jump_to(...)` when the 
`PatchGraph.cost(patches)` is greater than `LONG_PATCH_THRESHOLD` and the patch path
contains at least 1 patch.


#### What a long patch contains

Long patches are created via `conflict_interface.replay.long_patch.create_long_patch(...)` and represent the consolidated effect of changes from `from_time` to `to_time`:

- find the shortest patch path between the timestamps (`PatchGraph.find_patch_path`)
- build the required sub-structure over that path (adjacency + op-tree)
- collapse operations to preserve the same end-state semantics
- create a single `PatchGraphNode(from_timestamp, to_timestamp, *operations)`

The new edge is added to the loaded segment's in-memory `PatchGraph`, so subsequent jumps can reuse it while the replay is open.