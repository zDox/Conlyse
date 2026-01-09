import threading
import time
from tempfile import TemporaryDirectory

from tools.server_observer.server_observer import ServerObserver


class DummySession:
    def __init__(self, game_id: int):
        self.game_id = game_id
        self.account = None
        self.fat_session = False
        self.closed = False
        self.next_update_at = time.time()
        self._updates = 0

    def needs_update(self, now: float) -> bool:
        return now >= self.next_update_at

    def create_worker(self):
        return DummyWorker(self)

    def close(self):
        self.closed = True


class DummyWorker:
    def __init__(self, session: DummySession):
        self.session = session

    def run(self) -> bool:
        self.session._updates += 1
        self.session.next_update_at = time.time() + 100
        return False


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

        sessions = {}

        def build(cfg, account):
            session = DummySession(cfg["game_id"])
            sessions[session.game_id] = session
            return session

        observer._build_observer = build
        observer._start_observation_session(10, 1)

        observer.run(iterations=5)

        session = sessions[10]
        assert session.closed
        assert session._updates == 1
        assert "10" in observer.registry.state["completed"]


def test_max_parallel_is_respected():
    with TemporaryDirectory() as tmp_path:
        observer = _observer_for_tests(tmp_path, max_parallel=1)

        running = 0
        max_seen = 0
        lock = threading.Lock()
        sessions = {}

        class SlowSession(DummySession):
            def create_worker(self):
                return SlowWorker(self)

        class SlowWorker(DummyWorker):
            def run(self) -> bool:
                nonlocal running, max_seen
                with lock:
                    running += 1
                    max_seen = max(max_seen, running)
                time.sleep(0.05)
                with lock:
                    running -= 1
                self.session.next_update_at = time.time() + 100
                return False

        def build(cfg, account):
            session = SlowSession(cfg["game_id"])
            sessions[session.game_id] = session
            return session

        observer._build_observer = build
        observer._start_observation_session(20, 1)
        observer._start_observation_session(21, 1)

        observer.run(iterations=10)

        assert max_seen == 1
        assert sessions[20].closed
        assert sessions[21].closed
