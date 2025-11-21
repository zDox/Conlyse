class PathNode:
    def __init__(self, path_element: str, index: int, reference=None):
        self.path_element: str = path_element # Note PathElement is only unique among children of the parent
        self.is_leaf: bool = True
        self.index: int = index # Unique index in the overall path tree
        self.reference = reference # Optional reference to external data
        self.children: dict[str, 'PathNode'] = {}

    def set_reference(self, reference):
        self.reference = reference

    def add_child(self, child_node: 'PathNode'):
        self.children[child_node.path_element] = child_node
        self.is_leaf = False

    def add_children(self, child_nodes: list['PathNode']):
        for child_node in child_nodes:
            self.children[child_node.path_element] = child_node
        self.is_leaf = False

    def get_child(self, key: str) -> 'PathNode':
        return self.children.get(key)

    def has_child(self, key: str) -> bool:
        return key in self.children

    def is_leaf_node(self) -> bool:
        return self.is_leaf

    def __repr__(self):
        return f"PathNode(key={self.path_element}, is_leaf={self.is_leaf}, index={self.index}, children_keys={list(self.children.keys())})"



