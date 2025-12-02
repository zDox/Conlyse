from typing import Union


class PathTreeNode:
    def __init__(self, parent: Union['PathTreeNode', None], path_element: str | int, index: int, reference=None):
        self.path_element: str | int = path_element # Note PathElement is only unique among children of the parent
        self.index: int = index # Unique index in the overall path tree
        self.is_leaf: bool = True
        self.reference = reference # Optional reference to external data
        # NOTE that reference always points to the parent object. For example, if this node represents a list index then reference points to the list object, not the element at that index.
        # Same goes for game object attributes, reference points to the game object, not the attribute value.
        self.children: dict[str, 'PathTreeNode'] = {}
        self.parent = parent

    def set_reference(self, reference):
        self.reference = reference

    def add_child(self, child_node: 'PathTreeNode'):
        self.children[child_node.path_element] = child_node
        self.is_leaf = False

    def add_children(self, child_nodes: list['PathTreeNode']):
        for child_node in child_nodes:
            self.children[child_node.path_element] = child_node
        self.is_leaf = False

    def get_child(self, key: str) -> 'PathTreeNode':
        return self.children.get(key)

    def has_child(self, key: str) -> bool:
        return key in self.children

    def is_leaf_node(self) -> bool:
        return self.is_leaf

    def __repr__(self):
        return f"PathNode(key={self.path_element}, is_leaf={self.is_leaf}, index={self.index}, children_keys={list(self.children.keys())})"



