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
        N = self.idx_counter  # Total number of nodes
        # Preallocate arrays
        self.euler = array('I')  # Euler tour
        self.tin = array('I', [0] * N)  # entry times
        self.tout = array('I', [0] * N)  # exit times
        self.depth = array('I', [0] * N)  # depth of each node

        time = 0
        stack = [(self.root, 0,0)]
        while stack:
            node,d,state = stack.pop()
            if state == 0:
                # Enter Node
                self.tin[node.index] = time
                self.depth[node.index] = d
                self.euler.append(node.index)
                time += 1
                stack.append((node,d,1))  # Add exit state
                for child in reversed(node.children.values()):
                    stack.append((child,d+1,0))  # Add enter state
            else:
                # Exit Node
                self.tout[node.index] = time
                self.euler.append(node.index)
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

    def build_steiner_tree(self, unknown_paths: list[int]) -> dict[int, list[int]]:
        node_indices = unknown_paths
        node_indices.append(self.root.index)  # Ensure root is included for BFS order

        # IMPORTANT TIME WISE K LOG K
        node_indices_sorted = sorted(node_indices, key=lambda x: self.tin[x])
        # ----------------------------

        stack = []
        vt_edges = defaultdict(list)
        all_nodes = set(node_indices)
        for u in node_indices_sorted:
            if not stack:
                stack.append(u)
                continue

            lca = self.lca(u, stack[-1])
            all_nodes.add(lca)

            while len(stack) >= 2 and self.tin[stack[-2]] <= self.tin[lca] <= self.tout[stack[-2]]:
                top = stack.pop()
                vt_edges[top].append(stack[-1])
                vt_edges[stack[-1]].append(top)

            if stack[-1] != lca:
                top = stack.pop()
                vt_edges[top].append(lca)
                vt_edges[lca].append(top)
                stack.append(lca)

            stack.append(u)

        while len(stack) >= 2:
            top = stack.pop()
            vt_edges[top].append(stack[-1])
            vt_edges[stack[-1]].append(top)

        return vt_edges

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



