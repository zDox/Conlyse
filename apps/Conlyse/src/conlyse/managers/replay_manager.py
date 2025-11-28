from __future__ import annotations

from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
from typing import TYPE_CHECKING

from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.logger import get_logger
from conlyse.managers.events.replay_load_complete_event import ReplayLoadCompleteEvent
from conlyse.managers.events.replay_load_failed_event import ReplayLoadFailedEvent

if TYPE_CHECKING:
    from conlyse.app import App

logger = get_logger()

class ReplayManager:
    def __init__(self, app : App):
        self.app = app
        self.replays: dict[str, ReplayInterface] = {}
        self.executor = ThreadPoolExecutor(max_workers=1)

        self.active_replay_path: str | None = None
        self.is_loading_replay: bool = False


    def is_valid_replay(self, file_path: str) -> bool:
        if not file_path in self.replays: return False
        if self.replays[file_path] is None: return False
        return True

    def add_replay(self, file_path: str, replay: ReplayInterface):
        self.replays.update({file_path: replay})

    def get_replay(self, file_path: str) -> ReplayInterface | None:
        return self.replays.get(file_path)

    def is_loaded_replay(self, file_path: str) -> bool:
        return self.active_replay_path == file_path

    def _load_replay(self, file_path: str):
        """
        Loads a replay from the given file path.

        :param file_path: Path to the replay file
        :return: Replay object if loaded successfully, None otherwise
        """
        ritf = self.replays[file_path]
        ritf.open()
        self.active_replay_path = file_path


    def load_replay_async(self, file_path: str):
        """
        Loads a replay asynchronously.

        :param file_path: Path to the replay file
        :return: Replay object if loaded successfully, None otherwise
        """
        if self.is_loading_replay:
            logger.warning("A replay is already being loaded.")
            return
        if self.active_replay_path == file_path:
            logger.warning("Replay was already loaded. Someone forgot to close it!")
            self.app.event_handler.publish(ReplayLoadCompleteEvent(file_path))
            return

        self.is_loading_replay = True

        future: Future = self.executor.submit(self._load_replay, file_path)

        # handle result in main thread
        def on_done(fut: Future):
            self.is_loading_replay = False
            try:
                replay = fut.result()  # will raise exception if _load_replay failed
                self.active_replay_path = file_path
                logger.info(f"Loaded replay successfully: {replay}")
                self.app.event_handler.publish(ReplayLoadCompleteEvent(file_path))
            except Exception as e:
                logger.error(f"Failed to load replay: {e}")
                failed_event = ReplayLoadFailedEvent(file_path,
                                                     f"Failed to load replay file: {e}",
                                                     str(e))
                self.app.event_handler.publish(failed_event)
        future.add_done_callback(on_done)

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
            self.add_replay(file_path, ritf)
        except Exception as e:
            logger.warning(f"Failed to open replay: {e}")
            return False

        self.app.config_manager.set("file.default_open_path", file_path)
        return True

    def unload_replay(self, file_path: str):
        if file_path not in self.replays:
            logger.warning(f"Replay {file_path} is not registered.")
            return
        replay = self.replays[file_path]
        replay.close()
        self.active_replay_path = None

    def get_replays(self):
        return self.replays

    def clear_replays(self):
        self.replays = {}

    def remove_replay(self, file_path: str):
        if file_path in self.replays:
            del self.replays[file_path]