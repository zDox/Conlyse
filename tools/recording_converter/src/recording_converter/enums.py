from enum import Enum


class OperatingMode(Enum):
    gmr = "from_game_state_using_make_bipatch_to_replay"
    rur = "from_json_responses_using_update_to_replay"
    rtj = "from_recording_to_json"

