from conflict_interface.replayv2.path_node import PathNode


class PathTree:
    def __init__(self):
        self.root: PathNode = PathNode(key="root", index=0)
        self.idx_counter: int = 1  # Start from 1 since root is 0

    def get_or_add_path_node(self, path: list[str]) -> int:
        current_node = self.root
        for key in path:
            if current_node.has_child(key):
                current_node = current_node.get_child(key)
            else:
                new_node = PathNode(key=key, index=self.idx_counter)
                current_node.add_child(new_node)
                self.idx_counter += 1
                current_node = new_node
        return current_node.index




