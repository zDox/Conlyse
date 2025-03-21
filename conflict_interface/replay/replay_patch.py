import json
from dataclasses import dataclass
from typing import Any
from typing import Union

from conflict_interface.data_types.game_object import dump_any
from conflict_interface.logger_config import get_logger

logger = get_logger()

PathNode = Union[str, int]

@dataclass
class AddOperation:
    Key = "a"
    path: list[str] = None
    new_value: Any = None

@dataclass
class ReplaceOperation:
    Key = "p"
    path: list[str] = None
    new_value: Any = None

@dataclass
class RemoveOperation:
    Key = "r"
    path: list[str] = None
    new_value = None


Operation = Union[AddOperation, ReplaceOperation, RemoveOperation, None]

class ReplayPatch:
    def __init__(self):
        self.operations: list[Union[AddOperation, ReplaceOperation, RemoveOperation]] = []

    def add_op(self, path: list[str], new_value: Any):
        self.operations.append(AddOperation(path, new_value))

    def replace_op(self, path: list[str], new_value: Any):
        self.operations.append(ReplaceOperation(path=path, new_value=new_value))

    def remove_op(self, path: list[str]):
        self.operations.append(RemoveOperation(path))

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
        print(f"Add: {',\n'.join(add_str)}")
        print(f"Replace: {',\n'.join(replace_str)}")
        print(f"Remove: {',\n'.join(remove_str)}")

    def to_string(self) -> str:
        operations = [(op.Key, op.path, dump_any(op.new_value)) for op in self.operations]
        return json.dumps(operations)

    @classmethod
    def from_string(cls, string: str):
        operations = json.loads(string)
        instance = cls()
        for op in operations:
            key, path, new_value = op
            if key == "a":
                instance.add_op(path, new_value)
            elif key == "p":
                instance.replace_op(path, new_value)
            elif key == "r":
                instance.remove_op(path)
        return instance


class BidirectionalReplayPatch:
    def __init__(self):
        self.forward_patch = ReplayPatch()
        self.backward_patch = ReplayPatch()

    @classmethod
    def from_existing_patches(cls, forward: ReplayPatch, backward: ReplayPatch):
        instance = cls()
        instance.forward_patch = forward
        instance.backward_patch = backward
        return instance

    def forward_from_string(self, string: str):
        self.forward_patch = ReplayPatch.from_string(string)

    def backward_from_string(self, string: str):
        self.backward_patch = ReplayPatch.from_string(string)

    def forward_to_string(self):
        return self.forward_patch.to_string()

    def backward_to_string(self):
        return self.backward_patch.to_string()

    def add(self, path: list[str], old_value: Any, new_value: Any):
        self.forward_patch.add_op(path, new_value)
        self.backward_patch.remove_op(path)

    def replace(self, path: list[str], old_value: Any, new_value: Any):
        self.forward_patch.replace_op(path, new_value)
        self.backward_patch.replace_op(path, old_value)

    def remove(self, path: list[str], old_value: Any):
        self.forward_patch.remove_op(path)
        self.backward_patch.add_op(path, old_value)