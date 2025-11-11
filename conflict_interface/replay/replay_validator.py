from conflict_interface.replay.constants import CorruptReplay
from conflict_interface.replay.constants import REPLAY_VERSION
from conflict_interface.replay.replay_metadata import ReplayMetadata


class ReplayValidator:
    @staticmethod
    def validate_write_mode(mode: str):
        """
        Validate that replay is in write or append mode.

        Raises:
            IOError: If replay is not in write or append mode
        """
        if mode not in ("w", "a"):
            raise IOError("Replay is not in write or append mode")

    @staticmethod
    def validate_game_player_ids(metadata: ReplayMetadata, game_id: int, player_id: int):
        """
        Validate that game and player IDs match the replay's IDs.

        Args:
            game_id: Game ID to validate
            player_id: Player ID to validate (0 is wildcard)

        Raises:
            CorruptReplay: If IDs don't match
        """
        if game_id != metadata.game_id or (metadata.player_id != 0 and metadata.player_id != player_id):
            raise CorruptReplay(f"Game/Player ID mismatch in replay")

    @staticmethod
    def validate_timestamp_order(metadata: ReplayMetadata, time_stamp: int):
        """
        Validate that the new timestamp is after the last recorded timestamp.

        Args:
            time_stamp: Timestamp to validate
            metadata: Replay metadata containing last_time

        Raises:
            CorruptReplay: If timestamp is out of order
        """
        if metadata.last_time and metadata.last_time >= time_stamp:
            raise CorruptReplay(f"Newer patch exists at {metadata.last_time} than {time_stamp}")

    @staticmethod
    def validate_version(version):
        if version != REPLAY_VERSION:
            raise CorruptReplay(f"Replay version mismatch: expected {REPLAY_VERSION}, got {version}")
