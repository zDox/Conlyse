from dataclasses import dataclass

from conflict_interface.utils import GameObject


@dataclass
class UserSMSState(GameObject):
    STATE_ID = 17