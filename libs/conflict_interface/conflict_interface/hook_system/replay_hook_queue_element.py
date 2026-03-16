from dataclasses import dataclass
from typing import Any


@dataclass
class ReplayHookQueueElement:
    path: int
    reference: Any
    changed_data: dict