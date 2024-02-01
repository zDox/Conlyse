from dataclasses import dataclass
from math import sqrt


@dataclass
class Position:
    x: float
    y: float

    @classmethod
    def from_dict(cls, obj):
        return cls(x=obj["x"], y=obj["y"])

    def distance(self, other):
        return sqrt((other.x - self.y) ** 2 + (other.y - self.y) ** 2)
