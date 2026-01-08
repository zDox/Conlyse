"""
ServerObserver tool for lightweight recording of server responses across multiple games.
"""
from __future__ import annotations

import gc
import random
from pathlib import Path
from queue import Empty
from queue import Queue
from threading import Event
from threading import Lock
from threading import Thread
from threading import current_thread
from time import sleep
from time import time
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Set

from httpx import HTTPTransport
from memory_profiler import profile

from tools.server_observer.observation_session import ObservationWorker
from tools.server_observer.static_map_cache import StaticMapCache
from tools.server_observer.recording_registry import RecordingRegistry

from conflict_interface.data_types.hub_types.hub_game import HubGameProperties
from conflict_interface.data_types.hub_types.hub_game_state_enum import HubGameState
from conflict_interface.interface.hub_interface import HubInterface
from tools.server_observer.account import Account
from tools.server_observer.account_pool import AccountPool
from tools.server_observer.recorder_logger import get_logger

logger = get_logger()


class ServerObserver:
    """
    Manage observation of multiple games concurrently, recording server responses.

    Uses an AccountPool to select guest accounts, scans hub listings similar to
    MultiRecorder, and schedules ObservationSessions on a thread pool. Intended
    for lightweight response logging without executing complex Recorder actions.
    """

    def __init__(self, config: dict, account_pool: Optional[AccountPool] = None):
        self.config = config
        self.account_pool = account_pool
        self.http_transport = HTTPTransport(retries=3)

        self.scenario_ids: List[int] = config.get("scenario_ids", [])
        self.record_percentage: float = self._normalize_percentage(config.get("record_percentage", 1.0))
        self.max_parallel: int = int(config.get("max_parallel_recordings", 1))
        self.scan_interval: float = float(config.get("scan_interval", 30))
        self.max_guest_per_account: Optional[int] = config.get("max_guest_games_per_account")
        self.update_interval: float = float(config.get("update_interval", 60.0))
        self.output_dir = Path(config.get("output_dir", "./recordings"))
        self.enabled_scanning = config.get("enabled_scanning", True)

        self.observer_sessions: Dict[int, ObservationWorker] = {}

        registry_path = config.get(
            "registry_path",
            self.output_dir / "server_observer_registry.json",
        )
        self.registry = RecordingRegistry(Path(registry_path))
        self._listing_interface: Optional[HubInterface] = None
        self._listing_account: Optional[Account] = None
        self._active_threads: Set[Thread] = set()
        self._threads_lock = Lock()
        self._stop_event = Event()
        self._update_queue: Queue[ObservationWorker] = Queue()
        self._scan_thread: Optional[Thread] = None
        self._map_cache = StaticMapCache(self.output_dir / "static_maps")
        self._known_games: Set[int] = set()
        self._refresh_known_games_from_registry()

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
            if self.account_pool is None:
                raise Exception("No account pool provided")
            account = self.account_pool.get_any_account() or self.account_pool.next_free_account()
            if not account:
                logger.error("No accounts available for listing games")
                return None
            self._listing_account = account
            self._listing_interface = account.get_interface()
            return self._listing_interface
        except Exception as exc:
            logger.error(f"Failed to prepare listing interface: {exc}")
            return None

    def _select_games(self, interface: HubInterface) -> Iterable[tuple[int, HubGameProperties]]:
        logger.info("Scanning for games")
        games = interface.get_global_games(state=HubGameState.READY_TO_JOIN)
        seen_games: set[int] = set()

        for scenario_id in self.scenario_ids:
            new_candidates = [
                game for game in games
                if game.scenario_id == scenario_id and game.game_id not in self._known_games
            ]
            joinable = [g for g in new_candidates if g.open_slots >= 1]

            logger.info(
                f"Scenario {scenario_id}: {len(new_candidates)} new games, "
                f"{len(joinable)} potentially joinable before sampling"
            )

            for game in joinable:
                if game.game_id in seen_games:
                    continue
                if random.random() >= self.record_percentage:
                    continue
                seen_games.add(game.game_id)
                yield scenario_id, game

    def _build_observer(self, per_game_config: dict, account: Optional[Account]) -> ObservationWorker:
        return ObservationWorker(
            per_game_config,
            transport=self.http_transport,
            account=account,
            map_cache=self._map_cache,
        )

    def _refresh_known_games_from_registry(self):
        self._known_games = {
            int(gid)
            for bucket in self.registry.state.values()
            for gid in bucket.keys()
        }

    def _per_game_config(self, game_id: int, scenario_id: int) -> dict:
        cfg = {
            k: v
            for k, v in self.config.items()
            if k not in ("scenario_ids", "registry_path", "record_percentage", "max_parallel_recordings")
        }
        cfg["game_id"] = game_id
        cfg["scenario_id"] = scenario_id
        cfg["join_as_guest"] = True
        cfg["recording_name"] = cfg.get("recording_name") or f"game_{game_id}"
        cfg["update_interval"] = cfg.get("update_interval", self.update_interval)
        cfg["record_requests"] = True
        cfg.setdefault("output_dir", str(self.output_dir))
        return cfg

    def _pick_account(self) -> Optional[Account]:
        if not self.account_pool:
            return None
        tried = 0
        total = len(self.account_pool.accounts)
        while tried < total:
            account = self.account_pool.next_guest_account(self.max_guest_per_account)
            if account is None:
                return None
            if account != self._listing_account:
                return account
            else:
                self.account_pool.guest_account_pointer += 1
            tried += 1
        logger.error("No non-listing account available to start new observation")
        return None

    def _increment_account(self, account: Optional[Account]):
        if not account:
            return
        if self.account_pool:
            self.account_pool.increment_guest_join(account)

    def _decrement_account(self, account: Optional[Account]):
        if not account:
            return
        if self.account_pool:
            self.account_pool.decrement_guest_join(account)

    def _queue_observation(self, game_id: int, scenario_id: int):
        account = self._pick_account()
        if self.account_pool and not account:
            logger.error("No free account available to start new observation")
            return
        logger.info(f"Starting observation for game {game_id} with scenario {scenario_id}")

        cfg = self._per_game_config(game_id, scenario_id)
        observer = self._build_observer(cfg, account)

        self.registry.mark_recording(game_id, scenario_id, None)
        self._known_games.add(game_id)
        self._increment_account(account)
        self.observer_sessions[game_id] = observer
        observer.next_update_at = time()
        self._update_queue.put(observer)

    def _resume_active(self):
        for game_id, meta in self.registry.active().items():
            scenario_id = meta.get("scenario_id")
            if scenario_id is None:
                logger.warning(f"Skipping resume for game {game_id} without scenario metadata")
                continue
            if game_id in self.observer_sessions:
                continue
            logger.info(f"Resuming observation for game {game_id}")
            self._queue_observation(game_id, scenario_id)

    def _run_single_update(self, observer: ObservationWorker):
        game_id = observer.game_id
        try:
            keep_running = observer.perform_update()
            if keep_running:
                self._update_queue.put(observer)
            else:
                if not observer.fat_session:
                    self.registry.mark_completed(game_id)
                self._decrement_account(observer.account)
                observer.close()
                self.observer_sessions.pop(game_id, None)
                self._known_games.add(game_id)
        except Exception as exc:
            self.registry.mark_failed(game_id, "execution_failed")
            logger.error(f"Observation for game {game_id} failed: {exc}")
            self._decrement_account(observer.account)
            observer.close()
            self.observer_sessions.pop(game_id, None)
            self._known_games.add(game_id)
        finally:
            with self._threads_lock:
                self._active_threads.discard(current_thread())
            gc.collect()

    def _start_due_updates(self):
        now = time()
        deferred: List[ObservationWorker] = []
        while True:
            with self._threads_lock:
                if len(self._active_threads) >= self.max_parallel:
                    break
            try:
                observer = self._update_queue.get_nowait()
            except Empty:
                break
            if not observer.needs_update(now):
                deferred.append(observer)
                continue
            thread = Thread(target=self._run_single_update, args=(observer,), name=f"observer-{observer.game_id}", daemon=True)
            with self._threads_lock:
                self._active_threads.add(thread)
            thread.start()
        for observer in deferred:
            self._update_queue.put(observer)
        if deferred:
            wait_time = min(max(0.0, obs.next_update_at - now) for obs in deferred)
            if wait_time:
                self._stop_event.wait(min(wait_time, self.scan_interval))

    def _clean_finished_threads(self):
        with self._threads_lock:
            finished = [t for t in self._active_threads if not t.is_alive()]
            for thread in finished:
                thread.join(timeout=0.01)
                self._active_threads.discard(thread)

    def _scan_loop(self):
        interface = self._get_listing_interface()
        while not self._stop_event.is_set():
            if interface and self.enabled_scanning:
                for scenario_id, game in self._select_games(interface):
                    if game.game_id in self.observer_sessions:
                        continue
                    self._queue_observation(game.game_id, scenario_id)
            self._stop_event.wait(self.scan_interval)

    def run(self, iterations: Optional[int] = None) -> bool:
        cycle = 0
        self._stop_event.clear()
        self._resume_active()
        self._scan_thread = Thread(target=self._scan_loop, name="observer-scan", daemon=True)
        self._scan_thread.start()
        try:
            while not self._stop_event.is_set() and (iterations is None or cycle < iterations):
                self._clean_finished_threads()
                self._start_due_updates()
                cycle += 1
                if iterations is None or cycle < iterations:
                    self._stop_event.wait(0.1)
            return True
        finally:
            self._stop_event.set()
            if self._scan_thread:
                self._scan_thread.join()
            with self._threads_lock:
                threads = list(self._active_threads)
            for thread in threads:
                thread.join()
            self._clean_finished_threads()
