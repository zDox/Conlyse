from dataclasses import dataclass

from conflict_interface.utils import GameObject


@dataclass
class QuestState(GameObject):
    STATE_ID = 27