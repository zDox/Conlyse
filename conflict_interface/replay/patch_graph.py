import bisect
import heapq
from datetime import datetime

from conflict_interface.replay.patch_graph_node import PatchGraphNode


class PatchGraph:
    def __init__(self):
        self.nodes = {}
        self.time_stamps_cache: list[int] = []  # Sorted list of time stamps
        self.patches: dict[tuple[int, int], PatchGraphNode] = {}
        self._time_stamps: set[int] = set() # For precomputation and later sorting
        self.adj: dict[int, list[int]] = {}

    def add_patch_node(self, patch_node: PatchGraphNode):
        key = (patch_node.from_timestamp, patch_node.to_timestamp)
        self.patches[key] = patch_node

        if patch_node.from_timestamp not in self.time_stamps_cache:
            bisect.insort(self.time_stamps_cache, patch_node.from_timestamp)
            self.adj[patch_node.from_timestamp] = []

        if patch_node.to_timestamp not in self.time_stamps_cache:
            bisect.insort(self.time_stamps_cache, patch_node.to_timestamp)
            self.adj[patch_node.to_timestamp] = []

        self.adj[patch_node.from_timestamp].append(patch_node.to_timestamp)
        self.adj[patch_node.to_timestamp].append(patch_node.from_timestamp)

    def add_patch_node_fast(self, patch_node: PatchGraphNode):
        key = (patch_node.from_timestamp, patch_node.to_timestamp)
        self.patches[key] = patch_node

        if patch_node.from_timestamp not in self.time_stamps_cache:
            self._time_stamps.add(patch_node.from_timestamp)
            self.adj[patch_node.from_timestamp] = []

        if patch_node.to_timestamp not in self.time_stamps_cache:
            self._time_stamps.add(patch_node.to_timestamp)
            self.adj[patch_node.to_timestamp] = []

        self.adj[patch_node.from_timestamp].append(patch_node.to_timestamp)
        self.adj[patch_node.to_timestamp].append(patch_node.from_timestamp)

    def finalize(self):
        self.time_stamps_cache = sorted(self._time_stamps)
        self._time_stamps.clear()

    def validate_cached_time_stamps(self):
        for patch in self.patches.keys():
            from_time, to_time = patch
            if from_time not in self.time_stamps_cache:
                bisect.insort(self.time_stamps_cache, from_time)
            if to_time not in self.time_stamps_cache:
                bisect.insort(self.time_stamps_cache, to_time)

    def find_patch_path(self, from_time: datetime, to_time: datetime, ) -> list[PatchGraphNode]:
        from_time = int(from_time.timestamp())
        to_time = int(to_time.timestamp())

        # bisect to find closest timestamps
        from_index = bisect.bisect_left(self.time_stamps_cache, from_time)
        to_index = bisect.bisect_left(self.time_stamps_cache, to_time)
        if from_index < len(self.time_stamps_cache) and to_index < len(self.time_stamps_cache):
            from_time_exact = self.time_stamps_cache[from_index]
            to_time_exact = self.time_stamps_cache[to_index]
            return self._find_patch_path_exact(from_time_exact, to_time_exact)

        raise ValueError("No exact patch timestamps found for the given time range.")

    def _find_patch_path_exact(self, from_time: int, to_time: int) -> list[PatchGraphNode]:
        heap = [(0, from_time, [])]  # (cost, current_time, path)
        visited = set()

        while heap:
            current_cost, current_time, path = heapq.heappop(heap)

            if current_time == to_time:
                return path

            if current_time in visited:
                continue

            visited.add(current_time)

            for neighbor in self.adj.get(current_time, []):
                if neighbor not in visited:
                    patch_node = self.patches.get((current_time, neighbor))
                    if not patch_node:
                        raise ValueError(f"No patch found between {current_time} and {neighbor}")
                    edge_cost = patch_node.cost
                    new_path_edges = path + [patch_node]
                    heapq.heappush(heap, (current_cost + edge_cost, neighbor, new_path_edges))

        raise ValueError(f"No path found from {from_time} to {to_time}")
