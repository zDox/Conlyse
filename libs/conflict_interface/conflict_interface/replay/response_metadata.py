from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ResponseMetadata:
    """
    Cross-language metadata for a single game server response.

    The wire contract is a flat JSON object with the following fields:

        {
            "timestamp": <int>,   # Unix time in milliseconds
            "game_id": <int>,
            "player_id": <int>,
            "client_version": <int>,
            "map_id": <str>
        }
    """

    timestamp: int
    game_id: int
    player_id: int
    client_version: int
    map_id: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResponseMetadata":
        """
        Construct a ResponseMetadata instance from a plain dict.
        """
        map_id_raw = data.get("map_id", "")
        return cls(
            timestamp=int(data["timestamp"]),
            game_id=int(data["game_id"]),
            player_id=int(data["player_id"]),
            client_version=int(data["client_version"]),
            map_id=str(map_id_raw),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert this metadata instance into a plain dict.
        """
        return {
            "timestamp": int(self.timestamp),
            "game_id": int(self.game_id),
            "player_id": int(self.player_id),
            "client_version": int(self.client_version),
            "map_id": self.map_id,
        }

    @classmethod
    def from_string(cls, s: str) -> "ResponseMetadata":
        """
        Parse a JSON string into a ResponseMetadata instance.
        """
        data: Dict[str, Any] = json.loads(s)
        return cls.from_dict(data)

    def to_string(self) -> str:
        """
        Serialize this metadata to a compact JSON string.
        """
        # Use compact separators to minimize payload size.
        return json.dumps(self.to_dict(), separators=(",", ":"))
