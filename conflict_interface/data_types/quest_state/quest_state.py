from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class QuestState(GameObject):
    C = "ultshared.UltQuestState"
    STATE_ID = 27