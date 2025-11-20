from typing import Any


class PatchGraphNode:
    def __init__(self, from_timestamp: int, to_timestamp: int, op_types: list[int], paths: list[int], values: list[Any]):
        self.from_timestamp = from_timestamp
        self.to_timestamp = to_timestamp
        self.op_types = op_types
        self.paths = paths
        self.values = values
        self.cost = self.compute_cost()

    def compute_cost(self) -> int:
        """Compute the cost of this patch node."""
        return 1 # TODO
