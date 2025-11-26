ADD_OPERATION = 1
REPLACE_OPERATION = 2
REMOVE_OPERATION = 3

REPLAY_VERSION = 206
class CorruptReplay(Exception):
    """Raised when a replay file is corrupted or has an invalid format."""
    pass

# Required keys in the information table
MANDATORY_KEYS = ["version", "game_id", "player_id", "start_time"]

# Timestamp conversion factor (milliseconds per second)
OP_TO_INT = {"a": ADD_OPERATION, "p": REPLACE_OPERATION, "r": REMOVE_OPERATION}
INT_TO_OP = {ADD_OPERATION: "a", REPLACE_OPERATION: "p", REMOVE_OPERATION: "r"}