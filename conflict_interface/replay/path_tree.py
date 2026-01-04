from array import array
from collections import defaultdict
from collections import deque
from copy import deepcopy
from logging import getLogger

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.hook_system.replay_hook import ReplayHook
from conflict_interface.replay.apply_replay_helper import get_child_reference
from conflict_interface.replay.path_tree_node import PathTreeNode

logger = getLogger()

class PathTree:
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

    def fill_with_paths(self, operations) -> list[PathTreeNode]:
        added_nodes = []
        for op in operations:
            path = op.path
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
        self.euler = array('I')
        self.tin = array('I', [0] * N)
        self.tout = array('I', [0] * N)
        self.depth = array('I', [0] * N)
        self.parent = array('i', [-1] * N)
        self.first = array('i', [-1] * N)

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
                self.st[k][i] = a if self.depth[self.euler[a]] <= self.depth[self.euler[b]] else b

    def lca(self, u_idx: int, v_idx: int) -> int:
        left = self.first[u_idx]
        right = self.first[v_idx]
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
        Returns adjacency list mapping node_idx -> list[node_idx] (directed edges, parent -> child).
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
        added = set()  # set[(parent, child)] to avoid duplicate directed edges

        def add_directed_edge(parent, child):
            if (parent, child) in added:
                return
            added.add((parent, child))
            adj[parent].append(child)

        for child, parent in compressed_parent.items():
            # walk from child up to parent using self.parent[] and add directed edges (parent -> child direction)
            cur = child
            while cur != parent:
                p = self.parent[cur]
                if p == -1:
                    raise RuntimeError(f"Parent pointer missing when expanding {child} -> {parent}")
                add_directed_edge(p, cur)  # parent -> child direction
                cur = p

        # Ensure all nodes from the full set are keys in adj (even if they have no children)
        for v in full:
            adj.setdefault(v, [])

        # Sort children by tin for deterministic order
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
                    if len(sub_tree.get(v, [])) > 0:
                        try:
                            child_ref = get_child_reference(ref, node.path_element) # TODO optimize reuse set references
                        except Exception as e:
                            raise Exception(e)
                        add((v, child_ref))

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

    def get_old_values(self, changed_paths: list[int], hook_dict: dict[int, list[ReplayHook]]):
        # Here we use a trick.
        # By creating the smallest subtree that contains all paths from the root to each of the changed paths we get a list of nodes
        # that lie before / are parents to changed nodes. now if a hook points to any of these parents one of his children has been updated
        # therefore the hook needs to be queued given that the operation type fits
        steiner_tree = self.build_steiner_tree(changed_paths)
        relevant_nodes = set(steiner_tree.keys())

        # intersect hook_paths and relevant_nodes to get the hooks to keep
        out = []
        for hook_path, hooks in hook_dict.items():
            for hook in hooks:
                if hook_path not in relevant_nodes: continue

                for child in steiner_tree[hook_path]:  # for prov in locations
                    relevant_attribute_changed = False
                    attribute_paths = steiner_tree.get(child)  # attribute nodes of a prov
                    if not attribute_paths:  # no attributes found
                        logger.warning(
                            f"Skipping hook {hook_path} as no attributes were found (Maby full province changed)")
                        continue

                    changed_attributes = {}
                    reference_to_child = None
                    for attribute in attribute_paths:  # for attribute node in attribute nodes of a prov
                        attribute_node = self.idx_to_node[attribute]  # actual node
                        reference_to_child = attribute_node.reference  # ref to holder of attribute of prov aka a province
                        if not reference_to_child:  # Important warning
                            logger.warning(
                                f"Skipping Attribute {attribute_node.path_element} because the reference was not set")
                            continue

                        if hook.attributes is None or attribute_node.path_element in hook.attributes:  # if attribute name in listening hook attribures
                            old_ref = getattr(reference_to_child, attribute_node.path_element,
                                              None)  # copy the attribute by acesssing the province
                            #TODO set_game to None before copying a possible GameObject
                            old_value = deepcopy(old_ref)
                            changed_attributes[attribute_node.path_element] = [old_value, None]
                            relevant_attribute_changed = True

                    if not relevant_attribute_changed:
                        continue

                    assert reference_to_child
                    assert len(changed_attributes) > 0
                    assert hook_path

                    out.append((hook_path, reference_to_child, changed_attributes))

        return out