from dataclasses import dataclass


@dataclass
class ReplayHookEvent:
    reference: any
    attributes: dict[str, any]