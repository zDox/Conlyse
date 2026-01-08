import threading
import time
from tempfile import TemporaryDirectory

from tools.server_observer.server_observer import ServerObserver


class DummyWorker:
    def __init__(self, game_id: int):
        self.game_id = game_id
        self.account = None
        self.fat_session = False
        self.closed = False
        self.next_update_at = time.time()
        self._updates = 0

    def needs_update(self, now: float) -> bool:
        return now >= self.next_update_at

    def perform_update(self) -> bool:
        self._updates += 1
        self.next_update_at = time.time() + 100
        return False

    def close(self):
        self.closed = True


def _observer_for_tests(tmp_path: str, max_parallel: int = 1) -> ServerObserver:
    config = {
        "scenario_ids": [1],
        "record_percentage": 1.0,
        "max_parallel_recordings": max_parallel,
        "scan_interval": 0.01,
        "output_dir": str(tmp_path),
        "update_interval": 0,
        "enabled_scanning": False,
    }
    observer = ServerObserver(config)
    observer._get_listing_interface = lambda: None
    return observer


def test_single_worker_runs_and_closes():
    with TemporaryDirectory() as tmp_path:
        observer = _observer_for_tests(tmp_path)

        workers = {}

        def build(cfg, account):
            worker = DummyWorker(cfg["game_id"])
            workers[worker.game_id] = worker
            return worker

        observer._build_observer = build
        observer._queue_observation(10, 1)

        observer.run(iterations=5)

        worker = workers[10]
        assert worker.closed
        assert worker._updates == 1
        assert "10" in observer.registry.state["completed"]


def test_max_parallel_is_respected():
    with TemporaryDirectory() as tmp_path:
        observer = _observer_for_tests(tmp_path, max_parallel=1)

        running = 0
        max_seen = 0
        lock = threading.Lock()
        workers = {}

        class SlowWorker(DummyWorker):
            def perform_update(self) -> bool:
                nonlocal running, max_seen
                with lock:
                    running += 1
                    max_seen = max(max_seen, running)
                time.sleep(0.05)
                with lock:
                    running -= 1
                self.next_update_at = time.time() + 100
                return False

        def build(cfg, account):
            worker = SlowWorker(cfg["game_id"])
            workers[worker.game_id] = worker
            return worker

        observer._build_observer = build
        observer._queue_observation(20, 1)
        observer._queue_observation(21, 1)

        observer.run(iterations=10)

        assert max_seen == 1
        assert workers[20].closed
        assert workers[21].closed
