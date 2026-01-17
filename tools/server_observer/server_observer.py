"""
ServerObserver tool for lightweight recording of server responses across multiple games.
"""
from __future__ import annotations

import gc
from copy import deepcopy
from pathlib import Path
from queue import Empty
from queue import Queue
from threading import Event
from threading import Lock
from threading import Thread
from threading import current_thread
from time import time
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Set

from conflict_interface.data_types.hub_types.hub_game import HubGameProperties
from conflict_interface.data_types.hub_types.hub_game_state_enum import HubGameState
from conflict_interface.interface.hub_interface import HubInterface
from tools.server_observer.account import Account
from tools.server_observer.account_pool import AccountPool
from tools.server_observer.observation_session import ObservationSession
from tools.server_observer.recorder_logger import get_logger
from tools.server_observer.recording_registry import RecordingRegistry
from tools.server_observer.static_map_cache import StaticMapCache

logger = get_logger()
THREAD_JOIN_TIMEOUT = 1.0
MAX_UPDATE_RETRIES = 3


class ServerObserver:
    """
    Manage observation of multiple games concurrently, recording server responses.

    Uses an AccountPool to select guest accounts, scans hub listings similar to
    MultiRecorder, and schedules ObservationSessions on a thread pool. Intended
    for lightweight response logging without executing complex Recorder actions.
    """

    def __init__(self, config: dict, account_pool: AccountPool):
        self.config = config
        self.account_pool = account_pool

        self.scenario_ids: List[int] = config.get("scenario_ids", [])
        self.max_parallel_recordings: int = int(config.get("max_parallel_recordings", 1))
        self.max_parallel_updates: int = int(config.get("max_parallel_updates", 1))
        self.max_parallel_first_updates: int = int(config.get("max_parallel_first_updates", 1))
        self.scan_interval: float = float(config.get("scan_interval", 30))
        self.max_guest_per_account: Optional[int] = config.get("max_guest_games_per_account")
        self.update_interval: float = float(config.get("update_interval", 60.0))
        self.output_dir = Path(config.get("output_dir", "./recordings"))
        # Optional separate directory for metadata
        self.output_metadata_dir = config.get("output_metadata_dir")
        if self.output_metadata_dir is not None:
            self.output_metadata_dir = Path(self.output_metadata_dir)
        self.enabled_scanning = config.get("enabled_scanning", True)
        
        # Long-term storage configuration
        self.long_term_storage_path = config.get("long_term_storage_path")
        if self.long_term_storage_path is not None:
            self.long_term_storage_path = Path(self.long_term_storage_path)
        self.file_size_threshold = config.get("file_size_threshold")

        self.observer_sessions: Dict[int, ObservationSession] = {}

        # Use metadata directory for registry if configured
        registry_default_dir = self.output_metadata_dir if self.output_metadata_dir else self.output_dir
        registry_path = config.get(
            "registry_path",
            registry_default_dir / "server_observer_registry.json",
        )
        self.registry = RecordingRegistry(Path(registry_path))
        self._listing_interface: Optional[HubInterface] = None
        self._listing_account: Optional[Account] = None
        self._active_threads: Set[Thread] = set()
        self._first_update_sessions: Set[int] = set()
        self._threads_lock = Lock()
        self._stop_event = Event()
        self._update_queue: Queue[ObservationSession] = Queue()
        self._scan_thread: Optional[Thread] = None
        self._map_cache = StaticMapCache(self.output_dir / "static_maps")
        self._known_games: Set[int] = set()
        self._refresh_known_games_from_registry()

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
        games = interface.get_global_games()
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
                seen_games.add(game.game_id)
                yield scenario_id, game

    def _refresh_known_games_from_registry(self):
        self._known_games = {
            int(gid)
            for bucket in self.registry.state.values()
            for gid in bucket.keys()
        }

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

    def _start_observation_session(self, game_id: int, scenario_id: int):
        account = self._pick_account()
        if self.account_pool and not account:
            logger.error("No free account available to start new observation")
            return
        logger.info(f"Starting observation session for game {game_id} with scenario {scenario_id}")

        # Determine metadata path for this game
        metadata_path = None
        if self.output_metadata_dir is not None:
            metadata_path = self.output_metadata_dir / f"game_{game_id}"

        observer = ObservationSession(
            game_id,
            account,
            self._map_cache,
            self.output_dir/f"game_{game_id}",
            metadata_path=metadata_path,
            long_term_storage_path=self.long_term_storage_path,
            file_size_threshold=self.file_size_threshold
        )
        self.registry.mark_recording(game_id, scenario_id, None)
        self._known_games.add(game_id)
        self.account_pool.increment_guest_join(account)
        self.observer_sessions[game_id] = observer
        observer.next_update_at = time()
        with self._threads_lock:
            self._first_update_sessions.add(game_id)
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
            if len(self.observer_sessions) >= self.max_parallel_recordings:
                logger.warning(f"Skipping resume for game {game_id} due to max parallel limit")
                continue
            self._start_observation_session(game_id, scenario_id)

    def _run_single_update(self, session: ObservationSession):
        game_id = session.game_id
        attempt = 1
        while True:
            try:
                with session.create_worker() as worker:
                    keep_running = worker.run()
                    session.update_package(deepcopy(worker.package))

                    if keep_running:
                        session.next_update_at = time() + self.update_interval
                        self._update_queue.put(session)
                    else:
                        self.registry.mark_completed(game_id)
                        self.account_pool.decrement_guest_join(session.account)
                        self.observer_sessions.pop(game_id, None)
                        self._known_games.add(game_id)
                with self._threads_lock:
                    self._first_update_sessions.discard(game_id)
                break  # Success, exit the retry loop
            except Exception as e:
                if attempt < MAX_UPDATE_RETRIES:
                    logger.exception(f"Observation for game {game_id} failed, retrying attempt {attempt}/{MAX_UPDATE_RETRIES}...")
                    attempt += 1
                    continue

                logger.exception(f"Observation for game {game_id} failed after {MAX_UPDATE_RETRIES} retries, marking as failed.")
                self.registry.mark_failed(game_id, str(e))
                self.account_pool.decrement_guest_join(session.account)
                self.observer_sessions.pop(game_id, None)
                self._known_games.add(game_id)
                with self._threads_lock:
                    self._first_update_sessions.discard(game_id)
                break  # Exit the retry loop
            finally:
                with self._threads_lock:
                    self._active_threads.discard(current_thread())
                gc.collect()

    def _start_due_updates(self):
        now = time()
        deferred: List[ObservationSession] = []
        while True:
            with self._threads_lock:
                if len(self._active_threads) >= self.max_parallel_updates:
                    break
            try:
                observer = self._update_queue.get_nowait()
            except Empty:
                break
            if not observer.needs_update(now):
                deferred.append(observer)
                continue

            # Check if this is a first-update and if we've hit the first-update limit
            with self._threads_lock:
                is_first_update = observer.game_id in self._first_update_sessions
                # Create a snapshot to avoid "set changed size during iteration" error
                first_update_snapshot = set(self._first_update_sessions)
                active_thread_names = {t.name for t in self._active_threads}

            if is_first_update:
                active_first_updates = sum(
                    1 for gid in first_update_snapshot
                    if self.observer_sessions.get(gid) and f"observer-{gid}" in active_thread_names
                )
                if active_first_updates >= self.max_parallel_first_updates:
                    deferred.append(observer)
                    continue

            thread = Thread(target=self._run_single_update, args=(observer,), name=f"observer-{observer.game_id}", daemon=True)
            logger.info(f"Starting ObserverWorker thread for game {observer.game_id}")
            with self._threads_lock:
                self._active_threads.add(thread)
            thread.start()
        for observer in deferred:
            self._update_queue.put(observer)
        if deferred:
            wait_times = [max(0.0, obs.next_update_at - now) for obs in deferred]
            wait_time = min(wait_times) if wait_times else 0.0
            if wait_time:
                self._stop_event.wait(min(wait_time, self.scan_interval))

    def _clean_finished_threads(self):
        with self._threads_lock:
            finished = [t for t in self._active_threads if not t.is_alive()]
            for thread in finished:
                thread.join(timeout=THREAD_JOIN_TIMEOUT)
                self._active_threads.discard(thread)

    def _scan_loop(self):
        interface = self._get_listing_interface()
        while not self._stop_event.is_set():
            if interface and self.enabled_scanning:
                for scenario_id, game in self._select_games(interface):
                    if game.game_id in self.observer_sessions:
                        continue
                    if len(self.observer_sessions) >= self.max_parallel_recordings:
                        continue
                    self._start_observation_session(game.game_id, scenario_id)
            self._stop_event.wait(self.scan_interval)

    def run(self) -> bool:
        self._stop_event.clear()
        self._resume_active()
        self._scan_thread = Thread(target=self._scan_loop, name="observer-scan", daemon=True)
        self._scan_thread.start()
        try:
            while not self._stop_event.is_set():
                self._clean_finished_threads()
                self._start_due_updates()
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
