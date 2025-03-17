from dataclasses import dataclass
from typing import Any
from typing import Union


@dataclass
class AddOperation:
    path: list[str] = None
    key: Any = None
    new_value: Any = None

@dataclass
class ReplaceOperation:
    path: list[str] = None
    new_value: Any = None

@dataclass
class RemoveOperation:
    path: list[str] = None


class ReplayPatch:
    def __init__(self):
        self.operations: list[Union[AddOperation, ReplaceOperation, RemoveOperation]] = []

    def add_op(self, add_op: AddOperation):
        self.operations.append(add_op)

    def replace_op(self, replace_op: ReplaceOperation):
        self.operations.append(replace_op)

    def remove_op(self, remove_op: RemoveOperation):
        self.operations.append(remove_op)

    def set_hierarchy(self, higher_class: str):
        for op in self.operations:
            op.path.insert(0, higher_class)
    def merge(self, key: str, other: "ReplayPatch"):
        if other is not None:
            for op in other.operations:
                op.path.insert(0, key)
                self.operations.append(op)
    def debug_str(self):
        add_str = [f"({op.path}, {op.new_value})" for op in self.operations if isinstance(op, AddOperration)]
        replace_str = [f"({op.path}, {op.new_value})" for op in self.operations if isinstance(op, ReplaceOperation)]
        remove_str = [f"{op.path}" for op in self.operations if op is isinstance(op, RemoveOperation)]
        print(f"Add: {','.join(add_str)}")
        print(f"Replace: {','.join(replace_str)}")
        print(f"Remove: {','.join(remove_str)}")