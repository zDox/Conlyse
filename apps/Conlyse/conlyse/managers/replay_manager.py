from __future__ import annotations

from threading import Thread
from typing import TYPE_CHECKING

from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.logger import get_logger
from conlyse.managers.events.ReplayLoadCompleteEvent import ReplayLoadCompleteEvent

if TYPE_CHECKING:
    from conlyse.app import App

logger = get_logger()

class ReplayManager:
    def __init__(self, app : App):
        self.app = app
        self.replays: dict[str, ReplayInterface] = {}
        self.active_replay_path: str | None = None

    def is_valid_replay(self, file_path: str) -> bool:
        if not file_path in self.replays: return False
        if self.replays[file_path] is None: return False
        return True

    def add_replay(self, file_path: str, replay: ReplayInterface):
        self.replays.update({file_path: replay})
        pass

    def _load_replay(self, file_path: str):
        """
        Loads a replay from the given file path.

        :param file_path: Path to the replay file
        :return: Replay object if loaded successfully, None otherwise
        """
        ritf = ReplayInterface(file_path)
        try:
            ritf.open()
            ritf.replay.load_patches_from_disk_into_cache()
            self.active_replay_path = file_path
            self.app.event_handler.publish_async(ReplayLoadCompleteEvent(file_path, ritf))
        except Exception as e:
            logger.warning(f"Failed to load replay: {e}")

    def load_replay_async(self, file_path: str):
        """
        Loads a replay asynchronously.

        :param file_path: Path to the replay file
        :return: Replay object if loaded successfully, None otherwise
        """

        thread = Thread(target=self._load_replay, args=(file_path,))
        thread.start()

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
            self.add_replay(file_path, ritf)
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

    def remove_replay(self, file_path: str):
        if file_path in self.replays:
            del self.replays[file_path]