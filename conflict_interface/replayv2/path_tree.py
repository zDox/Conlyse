from conflict_interface.replayv2.path_tree_node import PathNode


class PathTree:
    def __init__(self):
        self.root: PathNode = PathNode(path_element="root", index=0)
        self.idx_counter: int = 1  # Start from 1 since root is 0

    def get_or_add_path_node(self, path: list[str]) -> int:
        current_node = self.root
        for path_element in path:
            if current_node.has_child(path_element):
                current_node = current_node.get_child(path_element)
            else:
                new_node = PathNode(path_element=path_element, index=self.idx_counter)
                current_node.add_child(new_node)
                self.idx_counter += 1
                current_node = new_node
        return current_node.index




