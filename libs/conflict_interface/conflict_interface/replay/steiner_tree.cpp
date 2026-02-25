// conflict_interface/replay/steiner_tree.cpp
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <algorithm>

namespace py = pybind11;

struct PairHash {
    std::size_t operator()(const std::pair<int, int>& p) const {
        return std::hash<int>()(p.first) ^ (std::hash<int>()(p.second) << 1);
    }
};

py::dict build_steiner_tree(
    py::array_t<int> parent_arr,
    py::array_t<int> tin_arr,
    py::array_t<int> tout_arr,
    int root_idx,
    const std::vector<int>& nodes_input,
    py::array_t<int> euler_arr,
    py::array_t<int> depth_arr,
    py::array_t<int> st_arr,
    py::array_t<int> log_arr,
    py::array_t<int> first_arr
) {
    // Get direct pointers to numpy data (zero-copy)
    auto parent = parent_arr.unchecked<1>();
    auto tin = tin_arr.unchecked<1>();
    auto tout = tout_arr.unchecked<1>();
    auto euler = euler_arr.unchecked<1>();
    auto depth = depth_arr.unchecked<1>();
    auto st = st_arr.unchecked<2>();
    auto log_table = log_arr.unchecked<1>();
    auto first = first_arr.unchecked<1>();

    // Ensure root included
    std::vector<int> nodes = nodes_input;
    if (std::find(nodes.begin(), nodes.end(), root_idx) == nodes.end()) {
        nodes.push_back(root_idx);
    }

    // Sort input nodes by tin and deduplicate
    std::sort(nodes.begin(), nodes.end(),
        [&tin](int a, int b) { return tin[a] < tin[b]; });
    nodes.erase(std::unique(nodes.begin(), nodes.end()), nodes.end());

    // Insert LCAs between consecutive nodes
    std::vector<int> full = nodes;  // Start with nodes_sorted
    for (size_t i = 0; i < nodes.size() - 1; ++i) {
        int u = nodes[i];
        int v = nodes[i + 1];

        // Compute LCA(u, v)
        int left = first[u];
        int right = first[v];
        if (left > right) {
            std::swap(left, right);
        }
        int length = right - left + 1;
        int k = log_table[length];
        int a = st(k, left);
        int b = st(k, right - (1 << k) + 1);
        int lca = (depth[euler[a]] < depth[euler[b]]) ? euler[a] : euler[b];

        full.push_back(lca);
    }

    // Deduplicate and sort by tin again
    std::sort(full.begin(), full.end(),
        [&tin](int a, int b) { return tin[a] < tin[b]; });
    full.erase(std::unique(full.begin(), full.end()), full.end());

    // Build compressed virtual tree using stack
    std::vector<int> stack;
    std::unordered_map<int, int> compressed_parent;  // child -> parent

    for (int v : full) {
        if (stack.empty()) {
            stack.push_back(v);
            continue;
        }

        // Pop until stack top is ancestor of v
        while (!stack.empty()) {
            int top = stack.back();
            if (tin[top] <= tin[v] && tin[v] <= tout[top]) {
                break;
            }
            stack.pop_back();
        }

        if (!stack.empty()) {
            compressed_parent[v] = stack.back();
        }
        stack.push_back(v);
    }

    // Expand each compressed edge into real edges
    std::unordered_map<int, std::vector<int>> adj;
    std::unordered_set<std::pair<int, int>, PairHash> added;

    // Ensure all nodes from full set are keys
    for (int v : full) {
        adj[v] = {};
    }

    // Expand compressed edges
    for (const auto& [child, compressed_parent_node] : compressed_parent) {
        // Walk from child up to compressed_parent_node
        int cur = child;
        while (cur != compressed_parent_node) {
            int p = parent[cur];
            if (p == -1) {
                // This should not happen if tree is valid
                throw std::runtime_error("Parent pointer missing when expanding");
            }

            // Add directed edge p -> cur
            if (added.insert({p, cur}).second) {
                adj[p].push_back(cur);
            }

            cur = p;
        }
    }

    // Sort children by tin for deterministic order
    for (auto& [v, children] : adj) {
        std::sort(children.begin(), children.end(),
            [&tin](int a, int b) { return tin[a] < tin[b]; });
    }

    // Convert to Python dict
    py::dict result;
    for (const auto& [node, children] : adj) {
        result[py::cast(node)] = py::cast(children);
    }

    return result;
}

PYBIND11_MODULE(steiner_tree_cpp, m) {
    m.doc() = "Fast C++ implementation of Steiner tree building";
    m.def("build_steiner_tree", &build_steiner_tree,
          "Build a Steiner tree from nodes",
          py::arg("parent"),
          py::arg("tin"),
          py::arg("tout"),
          py::arg("root_idx"),
          py::arg("nodes"),
          py::arg("euler"),
          py::arg("depth"),
          py::arg("st"),
          py::arg("log"),
          py::arg("first"));
}