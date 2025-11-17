from __future__ import annotations

from typing import TYPE_CHECKING

from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.replay.replay import Replay

from conlyse.logger import get_logger

if TYPE_CHECKING:
    from conlyse.app import App

logger = get_logger()

class ReplayManager:
    def __init__(self, app : App):
        self.app = app
        self.replays: dict[str, Replay] = {}

    def add_replay(self, file_path: str, replay: Replay):
        self.replays.update({file_path: replay})
        pass

    def open_new_replay(self, file_path: str) -> bool:
        """
        Opens a new replay file.
        Checks if the file is valid and adds it to the list of replays.
        Updates the default path in the config.

        :param file_path: Path to the replay file
        :return: Success (if the replay was opened successfully)
        """

        ritf = ReplayInterface(file_path)
        try:
            ritf.open()
            self.add_replay(file_path, ritf.replay)
            ritf.close()
        except Exception as e:
            logger.warning(f"Failed to open replay: {e}")
            return False

        self.app.config_manager.set("file.default_open_path", file_path)
        return True

    def get_replays(self):
        return self.replays

    def clear_replays(self):
        self.replays = []