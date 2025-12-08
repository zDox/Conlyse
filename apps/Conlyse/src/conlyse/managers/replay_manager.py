from __future__ import annotations

import threading
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from PyQt6.QtCore import QMetaObject
from PyQt6.QtCore import QTimer
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.logger import get_logger
from conlyse.managers.events.replay_load_complete_event import ReplayOpenCompleteEvent
from conlyse.managers.events.replay_load_failed_event import ReplayOpenFailedEvent

if TYPE_CHECKING:
    from conlyse.app import App

logger = get_logger()

class ReplayManager:
    def __init__(self, app : App):
        self.app = app
        self.replays: dict[str, ReplayInterface] = {}
        self.executor = ThreadPoolExecutor(max_workers=1)

        self.active_replay_path: str | None = None
        self.is_opening_replay: bool = False

    def is_valid_replay(self, file_path: str) -> bool:
        if not file_path in self.replays: return False
        if self.replays[file_path] is None: return False
        return True

    def add_replay(self, file_path: str) -> bool:
        if file_path in self.replays:
            return True
        self.replays.update({file_path: ReplayInterface(file_path)})
        return True

    def get_replay(self, file_path: str) -> ReplayInterface | None:
        return self.replays.get(file_path)

    def is_active_replay(self, file_path: str) -> bool:
        return self.active_replay_path == file_path

    def _open_replay(self, file_path: str):
        """
        Loads a replay from the given file path.

        :param file_path: Path to the replay file
        :return: Replay object if opened successfully, None otherwise
        """
        ritf = self.replays[file_path]
        ritf.open()
        self.active_replay_path = file_path

    def open_replay_async(self, file_path: str):
        """
        Opens a replay asynchronously.

        :param file_path: Path to the replay file
        """
        if self.is_opening_replay:
            logger.warning("A replay is already being opened.")
            return
        if self.active_replay_path == file_path:
            logger.warning("Replay was already open. Someone forgot to close it!")
            self.app.event_handler.publish(ReplayOpenCompleteEvent(file_path))
            return

        self.is_opening_replay = True

        future: Future = self.executor.submit(self._open_replay, file_path)

        def on_done(fut: Future):
            self.is_opening_replay = False
            try:
                replay = fut.result()  # raises if _open_replay failed
                self.active_replay_path = file_path
                logger.info(f"Opened replay successfully from {file_path}")
                self.app.event_handler.publish(ReplayOpenCompleteEvent(file_path))
            except Exception as e:
                logger.error(f"Failed to open replay: {e}")
                failed_event = ReplayOpenFailedEvent(file_path,
                                                     f"Failed to open replay file: {e}",
                                                     str(e))
                self.app.event_handler.publish(failed_event)
        future.add_done_callback(on_done)


    def close_replay(self, file_path: str):
        if file_path not in self.replays:
            logger.warning(f"Replay {file_path} is not registered.")
            return
        replay = self.replays[file_path]
        replay.close()
        self.active_replay_path = None

    def close_active_replay(self):
        if not self.active_replay_path:
            logger.warning(f"No active replay to close.")
            return
        self.close_replay(self.active_replay_path)

    def get_active_replay(self) -> ReplayInterface | None:
        if not self.active_replay_path:
            return None
        return self.replays.get(self.active_replay_path, None)

    def get_replays(self):
        return self.replays

    def clear_replays(self):
        self.replays = {}

    def remove_replay(self, file_path: str):
        if file_path in self.replays:
            del self.replays[file_path]