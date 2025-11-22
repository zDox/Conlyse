import bisect
from datetime import datetime

from conflict_interface.replay.patch_graph_node import PatchGraphNode


class PatchGraph:
    def __init__(self):
        self.nodes = {}
        self.time_stamps_cache: list[int] = []  # Sorted list of time stamps
        self.patches: dict[tuple[int, int], PatchGraphNode] = {}

    def add_patch_node(self, patch_node: PatchGraphNode):
        key = (patch_node.from_timestamp, patch_node.to_timestamp)
        self.patches[key] = patch_node
        if patch_node.from_timestamp not in self.time_stamps_cache:
            bisect.insort(self.time_stamps_cache, patch_node.from_timestamp)
        if patch_node.to_timestamp not in self.time_stamps_cache:
            bisect.insort(self.time_stamps_cache, patch_node.to_timestamp)

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
        pass  # TODO Dijkstra or A* search to find the optimal path
