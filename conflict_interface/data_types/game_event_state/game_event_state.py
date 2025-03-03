from dataclasses import dataclass
from typing import Union

from conflict_interface.data_types.custom_types import ArrayList
from conflict_interface.data_types.game_event_state.game_event import *
from conflict_interface.data_types.state import State


@dataclass
class GameEventState(State):
    C = "ultshared.gameevents.UltGameEventState"
    STATE_TYPE = 24
    game_events: ArrayList[Union[
        ProvinceEnteredEvent, ProvinceLostEvent, NewspaperArticleEvent,
        ArmyDestroyedEvent, ArmyDamageDealtEvent, MilitaryExperienceGainedEvent
    ]]
    MAPPING = {
        "game_events": "gameEvents",
    }