import unittest
from types import MethodType

import conflict_interface.replay.path_tree as tree_module


# Assume your Tree class code is in a module named `tree_module`
# from tree_module import Tree, Node

# --- Minimal Node class for testing ---
class Node:
    def __init__(self, index):
        self.index = index
        self.children = {}


class TestTreeAlgorithms(unittest.TestCase):

    def setUp(self):
        # Build a small tree
        #
        #        0
        #      / | \
        #     1  2  3
        #       / \
        #      4   5
        #          |
        #          6
        #
        self.nodes = [Node(i) for i in range(7)]
        self.nodes[0].children = {1: self.nodes[1], 2: self.nodes[2], 3: self.nodes[3]}
        self.nodes[2].children = {4: self.nodes[4], 5: self.nodes[5]}
        self.nodes[5].children = {6: self.nodes[6]}

        # Minimal Tree class implementation using your methods
        class Tree:
            def __init__(self, root, nodes):
                self.root = root
                self.nodes = nodes
                self.idx_counter = len(nodes)

            # Attach your original methods here
            precompute_euler_tour = None
            precompute_rmq = None
            lca = None
            build_steiner_tree = None

        self.tree = Tree(self.nodes[0], self.nodes)

        # Attach your actual methods from your original code
        self.tree.precompute_euler_tour = MethodType(tree_module.PathTree.precompute_euler_tour, self.tree)
        self.tree.precompute_rmq = MethodType(tree_module.PathTree.precompute_rmq, self.tree)
        self.tree.lca = MethodType(tree_module.PathTree.lca, self.tree)
        self.tree.build_steiner_tree = MethodType(tree_module.PathTree.build_steiner_tree, self.tree)

        # Precompute structures
        self.tree.precompute_euler_tour()
        self.tree.precompute_rmq()
    # --- Euler tour & LCA tests ---
    def test_euler_tour_length(self):
        # Euler tour should have length = 2 * nodes - 1 (basic tree property)
        euler_len = len(self.tree.euler)
        self.assertTrue(euler_len >= 7)  # Some nodes revisited multiple times
        self.assertIn(0, self.tree.euler)
        self.assertIn(6, self.tree.euler)

    def test_lca_basic(self):
        # Known LCAs
        self.assertEqual(self.tree.lca(1, 4), 0)
        self.assertEqual(self.tree.lca(4, 6), 2)
        self.assertEqual(self.tree.lca(3, 6), 0)
        self.assertEqual(self.tree.lca(5, 6), 5)
        self.assertEqual(self.tree.lca(0, 6), 0)

    def test_first_and_depth_arrays(self):
        for i, node in enumerate(self.tree.nodes):
            self.assertTrue(self.tree.first[i] >= 0)
            self.assertTrue(self.tree.depth[i] >= 0)
        # Depth of root = 0
        self.assertEqual(self.tree.depth[0], 0)
        # Depth of node 6 = 3
        self.assertEqual(self.tree.depth[6], 3)

    # --- Steiner tree tests ---
    def test_steiner_tree_basic(self):
        nodes_to_connect = [4, 6]
        adj = self.tree.build_steiner_tree(nodes_to_connect)
        # Must include LCA (2) in the tree
        self.assertIn(2, adj)
        # Directed edges follow parent -> child
        # Verify path from 2 -> 5 -> 6
        self.assertIn(5, adj[2])
        self.assertIn(6, adj[5])

    def test_steiner_tree_multiple_nodes(self):
        nodes_to_connect = [1, 4, 6]
        adj = self.tree.build_steiner_tree(nodes_to_connect)
        # LCA nodes should be included
        self.assertIn(0, adj)
        self.assertIn(2, adj)
        # Paths should exist
        self.assertIn(1, adj[0])
        self.assertIn(2, adj[0])
        self.assertIn(4, adj[2])
        self.assertIn(5, adj[2])
        self.assertIn(6, adj[5])

    def test_steiner_tree_all_nodes(self):
        nodes_to_connect = list(range(7))
        adj = self.tree.build_steiner_tree(nodes_to_connect)
        # Tree should include all nodes and match original parent-child relations
        for node in self.tree.nodes:
            idx = node.index
            children = sorted([c.index for c in node.children.values()])
            self.assertEqual(sorted(adj[idx]), children)

    def test_euler_tour_complete(self):
        # Euler tour should include each node at least once
        for i in range(len(self.tree.nodes)):
            self.assertIn(i, self.tree.euler)

    def test_entry_exit_times(self):
        # tin[node] < tout[node] for all nodes
        for i in range(len(self.tree.nodes)):
            self.assertLess(self.tree.tin[i], self.tree.tout[i])

    def test_ancestor_property(self):
        # Check that parent is ancestor of child in tin/tout times
        for child in self.tree.nodes:
            idx = child.index
            p = getattr(self.tree, "parent", [None] * len(self.tree.nodes))[idx]
            if p != -1:
                self.assertTrue(self.tree.tin[p] < self.tree.tin[idx])
                self.assertTrue(self.tree.tout[idx] < self.tree.tout[p])

    def test_lca_same_node(self):
        # LCA of a node with itself is the node
        for i in range(len(self.tree.nodes)):
            self.assertEqual(self.tree.lca(i, i), i)

    def test_lca_root_involved(self):
        # LCA with root is root if other node is not root
        for i in range(1, len(self.tree.nodes)):
            self.assertEqual(self.tree.lca(0, i), 0)

    def test_lca_exhaustive(self):
        # Check all pairs in small tree for expected LCAs
        expected = {
            (1, 4): 0, (1, 5): 0, (1, 6): 0,
            (4, 5): 2, (4, 6): 2, (5, 6): 5,
            (2, 3): 0, (0, 6): 0
        }
        for (u, v), lca_expected in expected.items():
            self.assertEqual(self.tree.lca(u, v), lca_expected)
            self.assertEqual(self.tree.lca(v, u), lca_expected)

    def test_steiner_tree_single_node(self):
        # Steiner tree with one node returns node only
        node = [3]
        adj = self.tree.build_steiner_tree(node)
        self.assertIn(3, adj)
        self.assertEqual(adj[3], [])

    def test_steiner_tree_empty_list(self):
        # Steiner tree with empty list should at least include root
        adj = self.tree.build_steiner_tree([])
        self.assertIn(self.tree.root.index, adj)
        # Root may have children if algorithm inserts it

    def test_steiner_tree_path_edges(self):
        # All edges in Steiner tree must correspond to original tree edges
        nodes_to_connect = [1, 4, 6]
        adj = self.tree.build_steiner_tree(nodes_to_connect)

        def path_exists(parent, child):
            # Check parent -> child path exists in original tree
            cur = child
            while cur != parent:
                cur_p = self.tree.parent[cur]
                if cur_p == -1:
                    return False
                cur = cur_p
            return True

        for p, children in adj.items():
            for c in children:
                self.assertTrue(path_exists(p, c))

    def test_lca_ancestor_property(self):
        # LCA(u,v) must be ancestor of both u and v
        for u in range(len(self.tree.nodes)):
            for v in range(len(self.tree.nodes)):
                lca_node = self.tree.lca(u, v)
                self.assertTrue(self.tree.tin[lca_node] <= self.tree.tin[u] <= self.tree.tout[lca_node])
                self.assertTrue(self.tree.tin[lca_node] <= self.tree.tin[v] <= self.tree.tout[lca_node])


    def test_steiner_tree_ordering(self):
        nodes_to_connect = [1,4,6]
        adj = self.tree.build_steiner_tree(nodes_to_connect)
        for p, children in adj.items():
            tin_values = [self.tree.tin[c] for c in children]
            self.assertEqual(tin_values, sorted(tin_values))


# --- Run tests ---
if __name__ == "__main__":
    unittest.main()
