"""
ServerObserver tool for lightweight recording of server responses across multiple games.
"""
from __future__ import annotations

import json
import pickle
import random
import threading
import sys
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import sleep, time
from typing import Dict, Iterable, List, Optional, Set

import zstandard as zstd

from conflict_interface.data_types.hub_types.hub_game import HubGameProperties
from conflict_interface.data_types.hub_types.hub_game_state_enum import HubGameState
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.interface.recording_interface import RecordingInterface
from tools.recorder.account import Account
from tools.recorder.account_pool import AccountPool
from tools.recorder.recorder_logger import get_logger
from tools.recorder.recording_registry import RecordingRegistry
from tools.recorder.storage import RecordingStorage
from tools.recorder.telemetry import TelemetryRecorder

logger = get_logger()


class StaticMapCache:
    """
    Cache static map data per map_id to avoid duplicate downloads.
    """

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._saved_ids: Set[int] = set()
        self._lock = threading.Lock()
        self._compressor = zstd.ZstdCompressor(level=3)

        for file in self.cache_dir.glob("map_*.bin"):
            try:
                map_id = int(file.stem.replace("map_", ""))
                self._saved_ids.add(map_id)
            except ValueError:
                continue

    def save(self, map_id: Optional[int], static_map_data) -> Optional[Path]:
        if map_id is None or static_map_data is None:
            return None
        with self._lock:
            path = self.cache_dir / f"map_{map_id}.bin"
            if map_id in self._saved_ids and path.exists():
                return path
            original_game = getattr(static_map_data, "game", None) if hasattr(static_map_data, "game") else None
            try:
                if hasattr(static_map_data, "set_game"):
                    static_map_data.set_game(None)
                data = pickle.dumps(static_map_data)
                compressed = self._compressor.compress(data)
                with path.open("wb") as f:
                    f.write(compressed)
                self._saved_ids.add(map_id)
                logger.info(f"Cached static map data for map_id {map_id} at {path}")
                return path
            except Exception as exc:
                logger.warning(f"Failed to cache static map data for map_id {map_id}: {exc}")
                return None
            finally:
                try:
                    if hasattr(static_map_data, "set_game"):
                        static_map_data.set_game(original_game)
                except Exception:
                    pass


class ObservationSession:
    """
    Per-game observer that records server responses until game end.

    It patches the game API to persist responses via RecordingStorage, records
    telemetry for each update, and optionally saves game states. Static map data
    is cached once per map_id to avoid duplicate downloads during the session.
    """

    def __init__(
        self,
        config: dict,
        account: Optional[Account],
        telemetry: TelemetryRecorder,
        map_cache: StaticMapCache,
    ):
        self.config = config
        self.account = account
        self.telemetry = telemetry
        self.map_cache = map_cache
        self.hub_itf: Optional[HubInterface] = None
        self.game_itf = None
        self.storage: Optional[RecordingStorage] = None
        self.game_id = config.get("game_id")
        self.update_interval: float = float(config.get("update_interval", 60.0))
        self.save_game_states: bool = False
        self.max_updates = config.get("max_updates")
        self.max_duration = config.get("max_duration")

    def _setup_storage(self):
        output_dir = self.config.get("output_dir", "./recordings")
        recording_name = self.config.get("recording_name") or f"game_{self.game_id}"
        output_path = Path(output_dir) / recording_name
        self.storage = RecordingStorage(str(output_path), self.save_game_states)
        self.storage.setup_logging()
        self.telemetry.on_start()
        logger.info(f"ServerObserver storage initialized at {output_path}")

    def _get_hub_interface(self) -> Optional[HubInterface]:
        if self.account:
            return self.account.get_interface()

        username = self.config.get("username")
        password = self.config.get("password")
        proxy_url = self.config.get("proxy_url")
        if not username or not password:
            logger.error("Username and password are required when no account pool is provided")
            return None
        hub_itf = HubInterface()
        if proxy_url:
            hub_itf.set_proxy({"http": proxy_url, "https": proxy_url})
        hub_itf.login(username, password)
        return hub_itf

    def _on_request_response(self, request_payload: dict, response: dict, elapsed_ms: float):
        if self.storage:
            ts = time()
            self.storage.save_request_response(ts, request_payload or {}, response)
            approx_bytes = sys.getsizeof(request_payload or {}) + sys.getsizeof(response)
            self.telemetry.record_update(elapsed_ms, approx_bytes)
            if elapsed_ms > 2000:
                self.telemetry.log_anomaly(f"Slow update {elapsed_ms:.1f}ms for game {self.game_id}")

    def _save_static_map_data(self):
        if not self.game_itf or not getattr(self.game_itf, "static_map_data", None):
            return
        map_id = getattr(self.game_itf.game_api, "map_id", None)

        self.map_cache.save(map_id, self.game_itf.static_map_data)
        if self.storage and hasattr(self.game_itf.static_map_data, "set_game"):
            self.storage.save_static_map_data(self.game_itf.static_map_data)

    def _prepare(self) -> bool:
        self.hub_itf = self._get_hub_interface()
        if not self.hub_itf:
            return False
        guest = bool(self.config.get("join_as_guest", True))
        if not guest and not self.hub_itf.is_in_game(self.game_id):
            try:
                self.hub_itf.api.request_first_join(self.game_id)
            except Exception as exc:
                logger.debug(f"request_first_join failed for game {self.game_id}: {exc}")
        self.game_itf = RecordingInterface(
            game_id=self.game_id,
            session=self.hub_itf.api.session,
            auth_details=self.hub_itf.api.auth,
            proxy=self.hub_itf.api.proxy,
            guest=guest,
            replay_filepath=self.config.get("replay_path"),
        )
        self.game_itf.load_game()
        self.game_itf.set_request_response_callback(self._on_request_response)
        self.game_itf.set_update_callback(lambda elapsed_ms: self.telemetry.record_update(elapsed_ms, 0))
        self._save_static_map_data()
        return True

    def _update_once(self):
        if self.game_itf is None:
            logger.error("No game interface available for observer update")
            return None

        return self.game_itf.update()

    def _observe_until_end(self) -> bool:
        updates_done = 0
        start_time = time()
        while True:
            state = self._update_once()
            updates_done += 1
            if self._is_game_ended(state):
                logger.info(f"Game {self.game_id} ended, stopping observation.")
                return True
            if self.max_updates is not None and updates_done >= self.max_updates:
                logger.info("Reached configured maximum number of updates, stopping observation.")
                return True
            if self.max_duration is not None and (time() - start_time) >= self.max_duration:
                logger.info("Reached configured maximum observation duration, stopping.")
                return True
            sleep(self.update_interval)

    @staticmethod
    def _is_game_ended(response: Optional[dict]) -> bool:
        if not isinstance(response, dict):
            return False
        result = response.get("result")
        if not isinstance(result, dict):
            return False
        states = result.get("states", {})
        if not isinstance(states, dict):
            return False
        for state in states.values():
            if isinstance(state, dict) and state.get("gameEnded"):
                return True
        return False

    def run(self) -> bool:
        try:
            self._setup_storage()
            if not self._prepare():
                return False
            return self._observe_until_end()
        except Exception as exc:
            logger.error(f"Observation for game {self.game_id} failed: {exc}")
            self.telemetry.on_failure(str(exc))
            return False
        finally:
            if self.storage:
                self.storage.teardown_logging()
            if self.telemetry:
                self.telemetry.on_stop()


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

        self.scenario_ids: List[int] = config.get("scenario_ids", [])
        self.record_percentage: float = self._normalize_percentage(config.get("record_percentage", 1.0))
        self.max_parallel: int = int(config.get("max_parallel_recordings", 1))
        self.scan_interval: float = float(config.get("scan_interval", 30))
        self.max_guest_per_account: Optional[int] = config.get("max_guest_games_per_account")
        self.update_interval: float = float(config.get("update_interval", 60.0))
        self.output_dir = Path(config.get("output_dir", "./recordings"))

        registry_path = config.get(
            "registry_path",
            self.output_dir / "server_observer_registry.json",
        )
        self.registry = RecordingRegistry(Path(registry_path))
        self.executor = ThreadPoolExecutor(max_workers=self.max_parallel)
        self._listing_interface: Optional[HubInterface] = None
        self._running: Dict[Future, int] = {}
        self._running_game_ids: Set[int] = set()
        self.telemetry = TelemetryRecorder()
        self._map_cache = StaticMapCache(self.output_dir / "static_maps")
        self._known_games: Set[int] = set()
        self._refresh_known_games_from_registry()
        self._update_account_metrics()

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
        logger.info("Scanning for games")
        try:
            games = interface.get_global_games(state=HubGameState.READY_TO_JOIN)
        except Exception as exc:
            logger.warning(f"Failed to list games {exc}")
            return
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

    def _build_observer(self, per_game_config: dict, account: Optional[Account]) -> ObservationSession:
        return ObservationSession(
            per_game_config,
            account=account,
            telemetry=self.telemetry,
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
        return self.account_pool.next_guest_account(self.max_guest_per_account)

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

    def _start_observation(self, game_id: int, scenario_id: int):
        account = self._pick_account()
        if self.account_pool and not account:
            logger.error("No free account available to start new observation")
            return
        logger.info(f"Starting observation for game {game_id} with scenario {scenario_id}")

        cfg = self._per_game_config(game_id, scenario_id)
        observer = self._build_observer(cfg, account)

        self.registry.mark_recording(game_id, scenario_id, None)
        self._known_games.add(game_id)
        try:
            future = self.executor.submit(self._run_single_observer, game_id, observer, account)
            self._increment_account(account)
        except RuntimeError as exc:
            self.registry.mark_failed(game_id, "submission_failed")
            logger.error(f"Failed to submit observation for game {game_id}: {exc}")
            return
        self._running[future] = game_id
        self._running_game_ids.add(game_id)
        self._update_account_metrics()

    def _run_single_observer(self, game_id: int, observer: ObservationSession, account: Optional[Account]) -> bool:
        try:
            return observer.run()
        except Exception as exc:
            logger.error(f"Observation for game {game_id} failed: {exc}")
            return False
        finally:
            self._decrement_account(account)
            self._update_account_metrics()

    def _process_finished(self):
        done = [future for future in self._running if future.done()]
        for future in done:
            game_id = self._running.pop(future)
            self._running_game_ids.discard(game_id)
            success = False
            try:
                success = future.result()
            except Exception as exc:
                logger.error(f"Observation for game {game_id} raised: {exc}")
            if success:
                self.registry.mark_completed(game_id)
            else:
                self.registry.mark_failed(game_id, "execution_failed")
            self._known_games.add(game_id)
        if done:
            self._update_account_metrics()

    def _update_account_metrics(self):
        total_accounts = len(self.account_pool.accounts) if self.account_pool else 0
        accounts_in_use = len(self._running_game_ids)
        self.telemetry.update_account_usage(accounts_in_use, total_accounts)

    def _resume_active(self):
        for game_id, meta in self.registry.active().items():
            if game_id in self._running_game_ids:
                continue
            scenario_id = meta.get("scenario_id")
            if scenario_id is None:
                logger.warning(f"Skipping resume for game {game_id} without scenario metadata")
                continue
            logger.info(f"Resuming observation for game {game_id}")
            self._start_observation(game_id, scenario_id)

    def run(self, iterations: Optional[int] = None) -> bool:
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
                            self._start_observation(game.game_id, scenario_id)
                            available_slots -= 1
                cycle += 1
                if iterations is None or cycle < iterations:
                    sleep(self.scan_interval)
            return True
        finally:
            self._process_finished()
            self.executor.shutdown(wait=True)
