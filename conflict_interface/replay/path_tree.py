from array import array
from collections import defaultdict
from collections import deque
from copy import deepcopy
from logging import getLogger

import numpy as np

from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.hook_system.replay_hook import ReplayHook
from conflict_interface.replay.apply_replay_helper import get_reference_from_direct_parent
from conflict_interface.replay.path_tree_node import PathTreeNode
from conflict_interface.steiner_tree_cpp import build_steiner_tree as build_steiner_tree_cpp

logger = getLogger()


class PathTree:
    _PRIMITIVES = frozenset({int, float, str, bool, type(None)})
    def __init__(self):
        self.root: PathTreeNode = PathTreeNode(parent = None, path_element="root", index=0)
        self.idx_counter: int = 1  # Start from 1 since root is 0
        self.idx_to_node: dict[int, PathTreeNode] = {0: self.root}

        self.euler = None
        self.tin = None
        self.tout = None
        self.depth = None
        self.st = None # Sparse Table for RMQ
        self.log = None
        self.parent = None
        self.first = None

    def add_node(self, idx, parent: PathTreeNode, path_element: str | int) -> PathTreeNode:
        new_node = PathTreeNode(parent = parent, path_element=path_element, index=idx)
        parent.add_child(new_node)
        self.idx_to_node[idx] = new_node

        self.idx_counter += 1
        return new_node

    def fill_with_paths(self, paths: list[list[int | str]]) -> list[PathTreeNode]:
        added_nodes = []
        for path in paths:
            current_node = self.root
            for path_element in path:
                if current_node.has_child(path_element):
                    current_node = current_node.get_child(path_element)
                else:
                    current_node = self.add_node(self.idx_counter, current_node, path_element)
                    added_nodes.append(current_node)

        return added_nodes


    def precompute(self):
        self.precompute_euler_tour()
        self.precompute_rmq()

    def precompute_euler_tour(self):
        N = self.idx_counter
        self.euler = array('I')  # empty array of unsigned ints
        self.tin = np.zeros(N, dtype=np.uint32)  # equivalent to [0]*N
        self.tout = np.zeros(N, dtype=np.uint32)
        self.depth = np.zeros(N, dtype=np.uint32)
        self.parent = np.full(N, -1, dtype=np.int32)  # equivalent to [-1]*N
        self.first = np.full(N, -1, dtype=np.int32)

        time = 0
        stack = [(self.root, 0, 0)]
        while stack:
            node, d, state = stack.pop()
            idx = node.index
            if state == 0:
                self.tin[idx] = time
                self.depth[idx] = d
                self.euler.append(idx)
                if self.first[idx] == -1:
                    self.first[idx] = len(self.euler) - 1
                time += 1
                stack.append((node, d, 1))
                children_list = list(node.children.values())
                for i, child in enumerate(reversed(children_list)):
                    self.parent[child.index] = idx
                    stack.append((child, d + 1, 0))
                    # Add parent node after each child except the last
                    if i < len(children_list) - 1:
                        stack.append((node, d, 2))
            elif state == 1:
                self.tout[idx] = time
                time += 1
            else:  # state == 2: revisit parent between children
                self.euler.append(idx)
                time += 1

        self.euler = np.asarray(self.euler, dtype=np.int32)

    def precompute_rmq(self):
        euler_len = len(self.euler)
        self.log = np.zeros(euler_len + 1, dtype=np.uint32)
        for i in range(2, euler_len + 1):
            self.log[i] = self.log[i // 2] + 1

        K = self.log[euler_len] + 1
        self.st = np.zeros((K, euler_len), dtype=np.uint32)

        # initialize Level 0 of Sparse Table
        for i in range(euler_len):
            self.st[0][i] = i

        for k in range(1,K):
            span = 1 << (k - 1)
            for i in range(euler_len - (1 << k) + 1):
                a = self.st[k - 1][i]
                b = self.st[k - 1][i + span]
                self.st[k][i] = a if self.depth[self.euler[a]] <= self.depth[self.euler[b]] else b

    def build_steiner_tree(self, nodes: list[int]) -> dict[int, list[int]]:
        """
        Build a virtual/Steiner tree *expanded* so every edge is an actual original tree edge.
        Returns adjacency list mapping node_idx -> list[node_idx] (directed edges, parent -> child).
        """
        # Pass numpy arrays directly - zero copy!
        return build_steiner_tree_cpp(
            self.parent,  # numpy array
            self.tin,  # numpy array
            self.tout,  # numpy array
            self.root.index,
            nodes,  # just a list
            self.euler,  # numpy array
            self.depth,  # numpy array
            self.st,  # 2D numpy array
            self.log,  # numpy array
            self.first  # numpy array
        )

    def bfs_set_references(self, sub_tree: dict[int, list[int]], game_state: GameState):
        q = deque([])
        pop = q.popleft
        add = q.append

        for child in self.root.children.values():
            child.set_reference(game_state)
            add(child.index)

        while q:
            u = pop()
            for v in sub_tree.get(u, []):
                node = self.idx_to_node[v]
                node.set_reference(get_reference_from_direct_parent(node))
                add(v)

    def reset_child_references(self, start_node_idx: int):
        stack = [start_node_idx]
        while len(stack) > 0:
            node = self.idx_to_node[stack.pop()]
            for c in node.children.values():
                c.reference = None
                stack.append(c.index)

    def validate_idx_to_node_mapping(self):
        for idx, node in self.idx_to_node.items():
            if node.index != idx:
                raise ValueError(f"Index mismatch: {idx} != {node.index}, path element: {node.path_element}")

        # iterate through tree and ensure all nodes are in idx_to_node
        def _validate_node(_node: PathTreeNode):
            if _node.index not in self.idx_to_node:
                raise ValueError(f"Node with index {_node.index} not in idx_to_node mapping.")
            for child in _node.children.values():
                _validate_node(child)

        _validate_node(self.root)

    def validate_tree_structure(self):
        current_node = self.root
        visited: set[int] = {current_node.index}
        q =  deque([current_node])
        known_indexes = []
        while q:
            u = q.pop()
            for path_element, v in u.children.items():
                if v.index in visited: continue

                if v.path_element != path_element:
                    logger.warning(f"Node at path {self.idx_to_path_list(u.index)}, has child at path_elment {path_element} with wrong pathelement {v.path_element}")
                    return False

                if v.index not in known_indexes:
                    known_indexes.append(v.index)
                else:
                    logger.warning(f"Node at path {self.idx_to_path_list(v.index)} has a duplicate index")
                    return False

                if len(v.children) == 0 and not v.is_leaf:
                    logger.warning(f"Node at path {self.idx_to_path_list(v.index)} has no children but is not a leave")
                    return False

                elif len(v.children) != 0 and v.is_leaf:
                    logger.warning(f"Node at path {self.idx_to_path_list(v.index)} has children but is leave")
                    return False

                visited.add(v.index)
                q.append(v)


    def print_tree(self):
        def _print_node(node: PathTreeNode, depth: int):
            print("  " * depth + f"- {node.path_element} (idx: {node.index}, is_leaf: {node.is_leaf})")
            for child in node.children.values():
                _print_node(child, depth + 1)

        _print_node(self.root, 0)

        # print the values of the precomputed arrays
        print("\nPrecomputed Euler Tour:", list(self.euler))
        print("Precomputed tin:", list(self.tin))
        print("Precomputed tout:", list(self.tout))
        print("Precomputed depth:", list(self.depth))
        print("Precomputed parent:", list(self.parent))
        print("Precomputed first occurrence:", list(self.first))
        print("Precomputed Sparse Table:")
        for k, row in enumerate(self.st):
            print(f"  k={k}: {list(row)}")


    def idx_to_path_list(self, node_idx) -> list[int | str]:
        path_sub_tree = self.build_steiner_tree([node_idx])
        current = self.root.index
        old_path = []
        for i in range(len(path_sub_tree) -1):
            current = path_sub_tree[current][0]
            old_path.append(self.idx_to_node[current].path_element)
        return old_path

    def path_list_to_idx(self, path: list[str]) -> int:
        # Traverse the tree according to the path and return the index of the final node
        current = self.root
        for path_element in path:
            current = current.children[path_element]
        return current.index

    def exists(self, path: list[str | int]) -> bool:
        current = self.root
        for path_element in path:
            current = current.children.get(path_element, -1)
            if current == -1:
                return False
        return True

    def get_old_values(self, changed_paths: list[int], hook_dict: dict[int, list[ReplayHook]]) -> dict:
        # Here we use a trick.
        # By creating the smallest subtree that contains all paths from the root to each of the changed paths we get a list of nodes
        # that lie before / are parents to changed nodes. now if a hook points to any of these parents one of his children has been updated
        # therefore the hook needs to be queued given that the operation type fits
        if hook_dict == {}:
            return {}

        steiner_tree = self.build_steiner_tree(changed_paths)
        relevant_nodes = set(steiner_tree.keys())

        # intersect hook_paths and relevant_nodes to get the hooks to keep
        out = defaultdict(lambda: defaultdict(dict))
        for hook_path, hooks in hook_dict.items():
            for hook in hooks:
                if hook_path not in relevant_nodes: continue

                min_depth = hook.search_start_depth
                max_depth = hook.search_end_depth

                start = hook_path
                q = deque([(start, 0)])

                pop = q.popleft
                add = q.append

                while q:
                    u, d = pop()
                    for v in steiner_tree.get(u, []):
                        if d > max_depth != -1: continue

                        add((v, d+1))

                        if d < min_depth: continue

                        attribute_node = self.idx_to_node[v]
                        if hook.attributes is None or attribute_node.path_element in hook.attributes:  # if attribute name in listening hook attribures
                            old_ref = getattr(attribute_node.reference, attribute_node.path_element,
                                              None)  # copy the attribute by acesssing the province
                            if type(old_ref) in self._PRIMITIVES:
                                old_value = old_ref
                            else:
                                old_value = deepcopy(old_ref)
                            out[hook_path][v][attribute_node.path_element] = [old_value, None]

        return out