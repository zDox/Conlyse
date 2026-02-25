from dataclasses import dataclass
from typing import Any

from conflict_interface.hook_system.replay_hook_tag import ReplayHookTag


@dataclass
class ReplayHookEvent:
    reference: Any
    attributes: dict[str, Any]
    tag: ReplayHookTag