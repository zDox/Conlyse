from typing import Any


class PatchGraphNode:
    def __init__(self, from_timestamp: int, to_timestamp: int, op_types: list[int], paths: list[int], values: list[Any], cost = None):
        self.from_timestamp = from_timestamp # Seconds since epoch
        self.to_timestamp = to_timestamp # Seconds since epoch
        self.op_types = op_types
        self.paths = paths
        self.values = values
        if not cost:
            self.cost = self.compute_cost()
        else:
            self.cost = cost

    def compute_cost(self) -> int:
        """Compute the cost of this patch node."""
        return len(self.op_types)
