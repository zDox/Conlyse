from array import array
from collections import defaultdict
from collections import deque

from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.replay.apply_replay_helper import get_child_reference
from conflict_interface.replay.path_tree_node import PathNode


class PathTree:
    def __init__(self):
        self.root: PathNode = PathNode(path_element="root", index=0)
        self.idx_counter: int = 1  # Start from 1 since root is 0
        self.idx_to_node: dict[int, PathNode] = {0: self.root}

        self.euler = None
        self.tin = None
        self.tout = None
        self.depth = None
        self.st = None # Sparse Table for RMQ
        self.log = None
        self.parent = None

    def add_node(self, parent: PathNode, path_element: str | int ) -> PathNode:
        new_node = PathNode(path_element=path_element, index=self.idx_counter)
        parent.add_child(new_node)
        self.idx_to_node[self.idx_counter] = new_node
        self.idx_counter += 1
        return new_node

    def get_or_add_path_node(self, path: list[str | int]) -> int:
        current_node = self.root
        for path_element in path:
            if current_node.has_child(path_element):
                current_node = current_node.get_child(path_element)
            else:
                current_node = self.add_node(current_node, path_element)
        return current_node.index

    def precompute(self):
        self.precompute_euler_tour()
        self.precompute_rmq()

    def precompute_euler_tour(self):
        N = self.idx_counter  # total number of nodes (indices 0..N-1)
        self.euler = array('I')
        self.tin = array('I', [0] * N)
        self.tout = array('I', [0] * N)
        self.depth = array('I', [0] * N)
        self.parent = array('i', [-1] * N)  # parent[i] = parent index, -1 for root

        time = 0
        stack = [(self.root, 0, 0)]  # node_obj, depth, state
        while stack:
            node, d, state = stack.pop()
            idx = node.index
            if state == 0:
                self.tin[idx] = time
                self.depth[idx] = d
                self.euler.append(idx)
                time += 1
                stack.append((node, d, 1))
                # push children; set parent for each child
                # reversed to preserve original order
                for child in reversed(node.children.values()):
                    self.parent[child.index] = idx
                    stack.append((child, d + 1, 0))
            else:
                self.tout[idx] = time
                self.euler.append(idx)
                time += 1

    def precompute_rmq(self):
        euler_len = len(self.euler)
        self.log = array('I', [0] * (euler_len + 1))
        for i in range(2, euler_len + 1):
            self.log[i] = self.log[i // 2] + 1

        K = self.log[euler_len] + 1
        self.st = [array('I', [0] * euler_len) for _ in range(K)]

        # initialize Level 0 of Sparse Table
        for i in range(euler_len):
            self.st[0][i] = i

        for k in range(1,K):
            span = 1 << (k - 1)
            for i in range(euler_len - (1 << k) + 1):
                a = self.st[k - 1][i]
                b = self.st[k - 1][i + span]
                self.st[k][i] = a if self.depth[self.euler[a]] < self.depth[self.euler[b]] else b

    def lca(self, u_idx: int, v_idx: int) -> int:
        left = self.tin[u_idx]
        right = self.tin[v_idx]
        if left > right:
            left, right = right, left
        length = right - left + 1
        k = self.log[length]
        a = self.st[k][left]
        b = self.st[k][right - (1 << k) + 1]
        return self.euler[a] if self.depth[self.euler[a]] < self.depth[self.euler[b]] else self.euler[b]

    def build_steiner_tree(self, nodes: list[int]) -> dict[int, list[int]]:
        """
        Build a virtual/Steiner tree *expanded* so every edge is an actual original tree edge.
        Returns adjacency list mapping node_idx -> list[node_idx] (real edges only).
        """
        # ensure root included
        if self.root.index not in nodes:
            nodes = nodes + [self.root.index]

        # sort input nodes by tin
        nodes_sorted = sorted(set(nodes), key=lambda x: self.tin[x])

        # insert LCAs between consecutive nodes
        full = nodes_sorted[:]
        for i in range(len(nodes_sorted) - 1):
            full.append(self.lca(nodes_sorted[i], nodes_sorted[i + 1]))

        # deduplicate and sort by tin again
        full = sorted(set(full), key=lambda x: self.tin[x])

        # Build compressed virtual tree using stack (parent-child in 'full')
        st = []
        compressed_parent = {}  # child -> parent (in 'full' set)
        for v in full:
            if not st:
                st.append(v)
                continue
            # pop until stack top is ancestor of v
            while not (self.tin[st[-1]] <= self.tin[v] <= self.tout[st[-1]]):
                st.pop()
            parent = st[-1]
            compressed_parent[v] = parent
            st.append(v)

        # Now expand each compressed edge parent <- child into real edges along child -> ... -> parent
        adj = defaultdict(list)
        added = set()  # set[(min,max)] to avoid duplicate inserts

        def add_edge(u, v):
            a, b = (u, v) if u <= v else (v, u)
            if (a, b) in added:
                return
            added.add((a, b))
            adj[u].append(v)
            adj[v].append(u)

        for child, parent in compressed_parent.items():
            # walk from child up to parent using self.parent[] and add real edges
            cur = child
            while cur != parent:
                p = self.parent[cur]
                if p == -1:
                    # should not happen if parent is ancestor
                    raise RuntimeError(f"Parent pointer missing when expanding {child} -> {parent}")
                add_edge(cur, p)
                cur = p

        # Optionally ensure all nodes from the original 'nodes' set are keys in adj (even if isolated)
        for v in full:
            adj.setdefault(v, [])

        # Convert to lists (already lists) and optionally sort neighbors by tin for deterministic/DFS-like order
        for v in adj:
            adj[v].sort(key=lambda x: self.tin[x])

        return dict(adj)

    def bfs_set_references(self, sub_tree: dict[int, list[int]], game_state: GameState):
        start = self.root.index
        visited: set[int] = {start}
        q = deque([(start, game_state)])

        pop = q.popleft
        add = q.append
        visited_add = visited.add

        while q:
            u, ref = pop()
            for v in sub_tree.get(u, []):
                if v not in visited:
                    visited_add(v)

                    node = self.idx_to_node[v]
                    node.set_reference(ref)
                    child_ref = get_child_reference(ref, node.path_element) # TODO optimize reuse set references
                    add((v, child_ref))

    def validate_idx_to_node_mapping(self):
        for idx, node in self.idx_to_node.items():
            if node.index != idx:
                raise ValueError(f"Index mismatch: {idx} != {node.index}, path element: {node.path_element}")

        # iterate through tree and ensure all nodes are in idx_to_node
        def _validate_node(_node: PathNode):
            if _node.index not in self.idx_to_node:
                raise ValueError(f"Node with index {_node.index} not in idx_to_node mapping.")
            for child in _node.children.values():
                _validate_node(child)

        _validate_node(self.root)

    def validate_tree_structure(self):
        pass # TODO Implement tree structure validation logic



