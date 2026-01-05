"""
Coordinator for recording multiple games concurrently.
"""
from __future__ import annotations

import random
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import sleep
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Set

from conflict_interface.data_types.hub_types.hub_game import HubGameProperties
from conflict_interface.data_types.hub_types.hub_game_state_enum import HubGameState
from conflict_interface.interface.hub_interface import HubInterface
from tools.recorder.account import Account
from tools.recorder.account_pool import AccountPool
from tools.recorder.recorder import Recorder
from tools.recorder.recorder_logger import get_logger
from tools.recorder.recording_registry import RecordingRegistry

logger = get_logger()


class MultiRecorder:
    """
    Manage recording of multiple games concurrently using replay recording.
    """

    def __init__(self, config: dict, account_pool: Optional[AccountPool] = None):
        self.config = config
        self.account_pool = account_pool

        self.scenario_ids: List[int] = config.get("scenario_ids", [])
        self.record_percentage: float = self._normalize_percentage(config.get("record_percentage", 1.0))
        self.max_parallel: int = int(config.get("max_parallel_recordings", 1))
        self.scan_interval: float = float(config.get("scan_interval", 30))

        registry_path = config.get(
            "registry_path",
            Path(config.get("output_dir", "./recordings")) / "recording_registry.json",
        )
        self.registry = RecordingRegistry(Path(registry_path))
        self.executor = ThreadPoolExecutor(max_workers=self.max_parallel)
        self._listing_interface: Optional[HubInterface] = None
        self._running: Dict[Future, int] = {}
        self._running_game_ids: Set[int] = set()

    @staticmethod
    def _normalize_percentage(value) -> float:
        try:
            pct = float(value)
        except (TypeError, ValueError):
            return 1.0
        return pct / 100.0 if pct > 1 else max(0.0, min(1.0, pct))

    def _get_listing_interface(self) -> Optional[HubInterface]:
        if self._listing_interface:
            return self._listing_interface

        try:
            if self.account_pool:
                account = self.account_pool.get_any_account() or self.account_pool.next_free_account()
                if not account:
                    logger.error("No accounts available for listing games")
                    return None
                self._listing_interface = account.get_interface()
                return self._listing_interface

            username = self.config.get("username")
            password = self.config.get("password")
            proxy_url = self.config.get("proxy_url")

            hub_itf = HubInterface()
            if proxy_url:
                hub_itf.set_proxy({"http": proxy_url, "https": proxy_url})
            hub_itf.login(username, password)
            self._listing_interface = hub_itf
            return hub_itf
        except Exception as exc:
            logger.error(f"Failed to prepare listing interface: {exc}")
            return None

    def _select_games(self, interface: HubInterface) -> Iterable[tuple[int, HubGameProperties]]:
        logger.info(f"Scanning for games")
        try:
            games = interface.get_global_games(state=HubGameState.READY_TO_JOIN)
        except Exception as exc:
            logger.warning(f"Failed to list games {exc}")
            return

        logger.info(f"Found {len(games)} games")

        for scenario_id in self.scenario_ids:
            for game in games:
                if game.scenario_id != scenario_id:
                    continue
                if self.registry.is_known(game.game_id):
                    continue
                if random.random() > self.record_percentage:
                    continue
                yield scenario_id, game

    def _build_recorder(self, per_game_config: dict, account: Optional[Account]) -> Recorder:
        if account:
            per_game_config["username"] = account.username
            per_game_config["password"] = account.password
            per_game_config["proxy_url"] = account.proxy_url
        return Recorder(per_game_config, account_pool=None, save_game_states=self.config.get("save_game_states", False))

    def _per_game_config(self, game_id: int, scenario_id: int, replay_path: Optional[str]) -> dict:
        cfg = {k: v for k, v in self.config.items() if k not in ("scenario_ids", "registry_path", "record_percentage", "max_parallel_recordings")}
        cfg["game_id"] = game_id
        cfg["scenario_id"] = scenario_id
        cfg["record_as_replay"] = True
        cfg["join_as_guest"] = True
        cfg.setdefault("recording_name", f"game_{game_id}")
        if replay_path:
            cfg["replay_path"] = replay_path
        return cfg

    def _start_recording(self, game_id: int, scenario_id: int, replay_path: Optional[str] = None):
        account = self.account_pool.next_free_account() if self.account_pool else None
        if self.account_pool and not account:
            logger.error("No free account available to start new recording")
            return
        logger.info(f"Starting recording for game {game_id} with scenario {scenario_id}")

        cfg = self._per_game_config(game_id, scenario_id, replay_path)
        recorder = self._build_recorder(cfg, account)
        replay_file = cfg.get("replay_path") or str(Path(cfg.get("output_dir", "./recordings")) / cfg.get("recording_name") / "replay.db")

        self.registry.mark_recording(game_id, scenario_id, replay_file)
        future = self.executor.submit(self._run_single_recorder, game_id, recorder)
        self._running[future] = game_id
        self._running_game_ids.add(game_id)

    def _run_single_recorder(self, game_id: int, recorder: Recorder) -> bool:
        try:
            return recorder.run()
        except Exception as exc:
            logger.error(f"Recording for game {game_id} failed: {exc}")
            return False

    def _process_finished(self):
        done = [future for future in self._running if future.done()]
        for future in done:
            game_id = self._running.pop(future)
            self._running_game_ids.discard(game_id)
            success = False
            try:
                success = future.result()
            except Exception as exc:
                logger.error(f"Recording for game {game_id} raised: {exc}")
            if success:
                self.registry.mark_completed(game_id)
            else:
                self.registry.mark_failed(game_id, "execution_failed")

    def _resume_active(self):
        for game_id, meta in self.registry.active().items():
            if game_id in self._running_game_ids:
                continue
            self._start_recording(game_id, meta.get("scenario_id"), meta.get("replay_path"))

    def run(self, iterations: Optional[int] = None) -> bool:
        """
        Start the multi-recorder.

        Args:
            iterations: Optional number of discovery cycles to run. If None, loop indefinitely.
        """
        cycle = 0
        try:
            while iterations is None or cycle < iterations:
                self._process_finished()
                self._resume_active()

                interface = self._get_listing_interface()
                if interface:
                    available_slots = self.max_parallel - len(self._running)
                    if available_slots > 0:
                        for scenario_id, game in self._select_games(interface):
                            if available_slots <= 0:
                                break
                            self._start_recording(game.game_id, scenario_id)
                            available_slots -= 1
                cycle += 1
                if iterations is None or cycle < iterations:
                    sleep(self.scan_interval)
            return True
        finally:
            self._process_finished()
            # Allow graceful shutdown
            self.executor.shutdown(wait=True)
