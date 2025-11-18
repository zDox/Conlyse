REPLAY_VERSION = 206
class CorruptReplay(Exception):
    """Raised when a replay file is corrupted or has an invalid format."""
    pass

# Required keys in the information table
MANDATORY_KEYS = ["version", "game_id", "player_id", "start_time"]

# Timestamp conversion factor (milliseconds per second)
