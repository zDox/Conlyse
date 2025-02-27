from dataclasses import dataclass
from typing import Optional


class Action:
    language = "en"
    action_request_id = ""

    MAPPING = {
        "language": "language",
        "action_request_id": "requestID"
    }