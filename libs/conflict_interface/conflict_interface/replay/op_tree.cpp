#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <vector>
#include <unordered_map>
#include <deque>

namespace py = pybind11;

constexpr int ADD_OPERATION = 1;
constexpr int REPLACE_OPERATION = 2;
constexpr int REMOVE_OPERATION = 3;

struct OpNode {
    int op_type;
    int path;
    int64_t value_composite;  // (patch_idx << 32) | value_idx
    int creation_time;
    int last_changed_time;

    OpNode(int op, int p, int patch_idx, int val_idx, int ct, int lt)
        : op_type(op), path(p),
          value_composite((static_cast<int64_t>(patch_idx) << 32) | val_idx),
          creation_time(ct), last_changed_time(lt) {}
};

py::object build_op_tree_fast(
    const std::vector<std::vector<int>>& ops_per_patch,
    const std::vector<std::vector<int>>& paths_per_patch,
    const std::unordered_map<int, std::vector<int>>& adj,
    int root
) {
    // Initialize with BFS
    std::unordered_map<int, OpNode*> idx_to_opnode;
    std::deque<int> q{root};

    while (!q.empty()) {
        int u = q.front();
        q.pop_front();
        idx_to_opnode[u] = nullptr;

        auto it = adj.find(u);
        if (it != adj.end()) {
            q.insert(q.end(), it->second.begin(), it->second.end());
        }
    }

    // Process operations
    int t = -1;
    for (size_t patch_idx = 0; patch_idx < ops_per_patch.size(); ++patch_idx) {
        const auto& ops = ops_per_patch[patch_idx];
        const auto& paths = paths_per_patch[patch_idx];

        for (size_t i = 0; i < ops.size(); ++i) {
            ++t;
            int op_type = ops[i];
            int path = paths[i];

            OpNode*& slot = idx_to_opnode[path];

            if (!slot) {
                // First operation on this path
                slot = new OpNode(op_type, path, patch_idx, i, t, t);
                continue;
            }

            int old_op = slot->op_type;
            int ct = slot->creation_time;

            // REMOVE + ADD = REPLACE
            if (old_op == REMOVE_OPERATION && op_type == ADD_OPERATION) {
                slot->op_type = REPLACE_OPERATION;
                slot->path = path;
                slot->value_composite = (static_cast<int64_t>(patch_idx) << 32) | i;
                slot->last_changed_time = t;
                // creation_time stays the same
            }
            // ADD + REMOVE = NO OP
            else if (old_op == ADD_OPERATION && op_type == REMOVE_OPERATION) {
                slot->op_type = -1;
                slot->path = -1;
                slot->value_composite = -1;
                // creation_time stays the same
                slot->last_changed_time = t;
            }
            // ADD + REPLACE = ADD
            else if (old_op == ADD_OPERATION && op_type == REPLACE_OPERATION) {
                slot->op_type = ADD_OPERATION;
                slot->path = path;
                slot->value_composite = (static_cast<int64_t>(patch_idx) << 32) | i;
                // creation_time stays the same
                slot->last_changed_time = t;
            }
            // REPLACE + REMOVE = REMOVE
            else if (old_op == REPLACE_OPERATION && op_type == REMOVE_OPERATION) {
                slot->op_type = REMOVE_OPERATION;
                slot->path = path;
                slot->value_composite = (static_cast<int64_t>(patch_idx) << 32) | i;
                slot->creation_time = t;  // NEW creation time
                slot->last_changed_time = t;
            }
            // All other cases: just update to new operation
            else {
                slot->op_type = op_type;
                slot->path = path;
                slot->value_composite = (static_cast<int64_t>(patch_idx) << 32) | i;
                // creation_time stays the same
                slot->last_changed_time = t;
            }
        }
    }
    // Build result dict
    py::dict result;
    for (const auto& [idx, node] : idx_to_opnode) {
        if (!node) {
            result[py::cast(idx)] = py::none();
        } else {
            result[py::cast(idx)] = py::make_tuple(
                node->op_type,
                node->path,
                node->value_composite,
                node->creation_time,
                node->last_changed_time
            );
            delete node;
        }
    }

    return result;
}

PYBIND11_MODULE(op_tree_cpp, m) {
    m.def("build_op_tree_fast", &build_op_tree_fast);
}