from dataclasses import dataclass
from typing import Any


@dataclass
class ReplayHookEvent:
    reference: Any
    attributes: dict[str, Any]
    tag: str