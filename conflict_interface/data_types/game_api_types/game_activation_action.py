from dataclasses import dataclass
from typing import get_type_hints

from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class GameActivationAction:
    C = "ultshared.action.UltActivateGameAction"
    selected_player_id: int
    selected_team_id: int
    random_team_country_selection: bool
    os: str
    device: str

    MAPPING = {
        "selected_player_id": "selectedPlayerID",
        "selected_team_id": "selectedTeamID",
        "random_team_country_selection": "randomTeamAndCountrySelection",
        "os": "os",
        "device": "device"
    }

    _type_hints = None

    @classmethod
    def get_type_hints_cached(cls):
        if cls._type_hints is None:
            cls._type_hints = get_type_hints(cls)
        return cls._type_hints