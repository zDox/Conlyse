from dataclasses import dataclass


@dataclass
class Action:
    language: str
    action_request_id: str

    MAPPING = {
        "language": "language",
        "action_request_id": "action_request_id"
    }