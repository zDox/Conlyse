from bisect import bisect_right

from scipy.sparse import lil_matrix
from datetime import datetime

from scipy.sparse.csgraph import dijkstra

from conflict_interface.replay.patch_graph_node import PatchGraphNode


class PatchGraph:
    def __init__(self):
        self.time_stamps_cache: list[int] = []  # Sorted list of time stamps
        self.patches: dict[tuple[int, int], PatchGraphNode] = {}
        self._time_stamps: set[int] = set() # For precomputation and later sorting
        self.adj: dict[int, list[int]] = {}

        self.N: int = 0
        self.time_to_dense_idx: dict[int, int] = {} # Lookup table from a timestamp to a dense idx
        self.dense_idx_to_time: dict[int, int] = {} # Lookup table from a dense idx to a timestamp
        self.graph_lil = None # Graph in List to List format
        self.graph_csr = None # Graph in Compressed Sparse row format
        self.graph_is_up_to_date = False # graph csr == graph lil

    @staticmethod
    def cost(patch_path: list[PatchGraphNode]):
        return max(1,sum(x.cost for x in patch_path))

    def find_prev_timestamp(self, target):
        """
        Find the closest cached Unix timestamp less than or equal to the target.

        Parameters
        ----------
        target : int
            Unix timestamp (e.g. seconds since the Unix epoch).

        Returns
        -------
        int | None
            The closest Unix timestamp in ``self.time_stamps_cache`` that is
            less than or equal to ``target``, or ``None`` if no such timestamp
            exists.
        """
        i = bisect_right(self.time_stamps_cache, target)
        return self.time_stamps_cache[i - 1] if i > 0 else None

    def add_edge(self, patch_node: PatchGraphNode):
        """
        Adds an edge to the patch graph
        NOTE: This Requires the indices to already exist
        """
        if patch_node.from_timestamp not in self.time_to_dense_idx:
            raise RuntimeError("Vertex does not exist; call add_edge_and_vertices + finalize")

        if patch_node.to_timestamp not in self.time_to_dense_idx:
            raise RuntimeError("Vertex does not exist; call add_edge_and_vertices + finalize")

        key = (patch_node.from_timestamp, patch_node.to_timestamp)
        self.patches[key] = patch_node

        self.adj[patch_node.from_timestamp].append(patch_node.to_timestamp)

        u = self.time_to_dense_idx[patch_node.from_timestamp]
        v = self.time_to_dense_idx[patch_node.to_timestamp]

        if self.graph_lil is None:
            raise RuntimeError("Graph has not been initialized; call finalize() before add_edge")

        self.graph_lil[u, v] = patch_node.cost
        self.graph_is_up_to_date = False

    def add_edge_and_vertices(self, patch_node: PatchGraphNode):
        """
        This method adds edges and vertices to the patch graph.
        NOTE: This Requires finalize to be called before the graph can be used!
        """
        key = (patch_node.from_timestamp, patch_node.to_timestamp)
        self.patches[key] = patch_node

        if patch_node.from_timestamp not in self._time_stamps:
            self._time_stamps.add(patch_node.from_timestamp)
            self.adj[patch_node.from_timestamp] = []

        if patch_node.to_timestamp not in self._time_stamps:
            self._time_stamps.add(patch_node.to_timestamp)
            self.adj[patch_node.to_timestamp] = []

        self.adj[patch_node.from_timestamp].append(patch_node.to_timestamp)

    def finalize(self):
        self.graph_is_up_to_date = False
        self.time_stamps_cache = sorted(self._time_stamps)
        self._time_stamps.clear()
        self.create_dense_indices()
        self.create_lil_matrix()
        self.update_graph()

    def update_graph(self):
        if self.graph_is_up_to_date: return
        self.graph_csr = self.graph_lil.tocsr()
        self.graph_is_up_to_date = True

    def create_dense_indices(self):
        self.time_to_dense_idx = {t: i for i, t in enumerate(self.time_stamps_cache)}
        self.dense_idx_to_time = self.time_stamps_cache  # indexable list
        self.N = len(self.time_stamps_cache)

    def create_lil_matrix(self):
        self.graph_lil = lil_matrix((self.N, self.N))
        for (from_timestamp, to_timestamp), patch_graph_node in self.patches.items():
            u = self.time_to_dense_idx[from_timestamp]
            v = self.time_to_dense_idx[to_timestamp]
            self.graph_lil[u, v] = patch_graph_node.cost

    def find_patch_path(self, from_time: datetime, to_time: datetime, ) -> list[PatchGraphNode]:
        if not self.time_to_dense_idx:
            raise RuntimeError("Graph not finalized; call finalize() first")

        from_time = int(from_time.timestamp())
        to_time = int(to_time.timestamp())

        from_time_exact = self.find_prev_timestamp(from_time)
        to_time_exact = self.find_prev_timestamp(to_time)
        if from_time_exact is None or to_time_exact is None:
            raise ValueError("No exact patch timestamps found for the given time range.")

        path = self._find_patch_path_exact(from_time_exact, to_time_exact)
        return path

    def _find_patch_path_exact(self, from_time: int, to_time: int) -> list[PatchGraphNode]:
        if from_time == to_time:
            return []
        self.update_graph()
        src = self.time_to_dense_idx[from_time]
        dst = self.time_to_dense_idx[to_time]

        dist,pred = dijkstra(
            self.graph_csr,
            directed=True,
            indices=src,
            return_predecessors=True,
        )

        if pred[dst] == -9999:
            raise ValueError("No path")

        # reconstruct
        path = []
        cur = dst
        while cur != src:
            prev = pred[cur]
            path.append(
                self.patches[(self.dense_idx_to_time[prev], self.dense_idx_to_time[cur])]
            )
            cur = prev

        return path[::-1]



