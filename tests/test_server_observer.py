import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from tools.recorder.telemetry import TelemetryRecorder
from tools.server_observer.server_observer import ObservationSession, ServerObserver, StaticMapCache


class DummyStaticMap:
    def __init__(self):
        self.game = None

    def set_game(self, game):
        self.game = game


class TestObservationSession(unittest.TestCase):
    def test_observer_stops_on_game_end(self):
        tmp_path = self._tmp_dir()
        config = {"game_id": 42, "output_dir": tmp_path, "update_interval": 0}
        session = ObservationSession(config, account=None, telemetry=TelemetryRecorder(), map_cache=StaticMapCache(tmp_path))
        session.storage = None

        game_info_state = SimpleNamespace(game_ended=True, map_id=99)
        states = SimpleNamespace(game_info_state=game_info_state)
        game_state = SimpleNamespace(states=states)

        session.game_itf = MagicMock()
        session.game_itf.game_state = game_state
        session.game_itf.update = MagicMock()

        self.assertTrue(session._observe_until_end())
        session.game_itf.update.assert_called_once()

    def _tmp_dir(self):
        import tempfile

        return tempfile.mkdtemp()


class TestServerObserver(unittest.TestCase):
    def test_server_observer_start_and_track(self):
        import tempfile

        tmp_path = tempfile.mkdtemp()
        config = {
            "scenario_ids": [1],
            "record_percentage": 1.0,
            "max_parallel_recordings": 1,
            "scan_interval": 0,
            "output_dir": str(tmp_path),
            "update_interval": 0,
            "max_guest_games_per_account": 1,
        }
        observer = ServerObserver(config)

        interface = MagicMock()
        interface.get_global_games.return_value = [SimpleNamespace(game_id=123, scenario_id=1, open_slots=2)]
        observer._get_listing_interface = MagicMock(return_value=interface)

        built_configs = []
        session_mock = MagicMock()
        session_mock.run.return_value = True

        def build(cfg, account):
            built_configs.append(cfg)
            return session_mock

        observer._build_observer = MagicMock(side_effect=build)

        observer.run(iterations=1)

        self.assertTrue("123" in observer.registry.state["completed"] or "123" in observer.registry.state["recording"])
        self.assertTrue(built_configs and built_configs[0].get("update_interval") == 0)
        observer._build_observer.assert_called()

    def test_static_map_cache_saves_once(self):
        import tempfile

        tmp_path = tempfile.mkdtemp()
        cache = StaticMapCache(tmp_path)

        dummy = DummyStaticMap()
        first_path = cache.save(7, dummy)
        second_path = cache.save(7, dummy)

        self.assertEqual(first_path, second_path)
        self.assertTrue(first_path and first_path.exists())
