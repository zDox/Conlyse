from dataclasses import dataclass
from typing import Any
from typing import Union


from conflict_interface.logger_config import get_logger

logger = get_logger()

@dataclass
class AddOperation:
    path: list[str] = None
    new_value: Any = None

@dataclass
class ReplaceOperation:
    path: list[str] = None
    new_value: Any = None

@dataclass
class RemoveOperation:
    path: list[str] = None


Operation = Union[AddOperation, ReplaceOperation, RemoveOperation, None]

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
    def is_empty(self):
        return len(self.operations) == 0

    def merge(self, keys: list[str], other: "ReplayPatch"):
        if other is not None and not other.is_empty():
            for op in other.operations:
                op.path = keys + op.path
                self.operations.append(op)
    def debug_str(self):
        add_str = [f"({op.path}, {op.new_value})" for op in self.operations if isinstance(op, AddOperation)]
        replace_str = [f"({op.path}, {op.new_value})" for op in self.operations if isinstance(op, ReplaceOperation)]
        remove_str = [f"{op.path}" for op in self.operations if op is isinstance(op, RemoveOperation)]
        print(f"Add: {','.join(add_str)}")
        print(f"Replace: {','.join(replace_str)}")
        print(f"Remove: {','.join(remove_str)}")
