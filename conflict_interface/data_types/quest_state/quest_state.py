from dataclasses import dataclass

from conflict_interface.data_types.state import State


@dataclass
class QuestState(State):
    C = "ultshared.UltQuestState"
    STATE_TYPE = 27
    MAPPING = {}