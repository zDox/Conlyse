from types import SimpleNamespace
from unittest.mock import MagicMock

from tools.recorder.multi_recorder import MultiRecorder


def test_update_until_end_stops_on_game_end(monkeypatch):
    from tools.recorder.recorder import Recorder

    recorder = Recorder({"actions": []})
    recorder.save_game_states = False
    recorder.storage = None

    game_info_state = SimpleNamespace(game_ended=True)
    states = SimpleNamespace(game_info_state=game_info_state)
    game_state = SimpleNamespace(states=states)

    recorder.game_itf = MagicMock()
    recorder.game_itf.game_state = game_state
    recorder.game_itf.update = MagicMock()

    assert recorder._update_until_game_end({"update_interval": 0}) is True
    recorder.game_itf.update.assert_called_once()


def test_multi_recorder_starts_and_tracks(tmp_path, monkeypatch):
    config = {
        "scenario_ids": [1],
        "record_percentage": 1.0,
        "max_parallel_recordings": 1,
        "scan_interval": 0,
        "actions": [],
        "output_dir": str(tmp_path),
    }

    multi = MultiRecorder(config)

    interface = MagicMock()
    interface.get_global_games.return_value = [SimpleNamespace(game_id=999)]
    multi._get_listing_interface = MagicMock(return_value=interface)

    recorder_mock = MagicMock()
    recorder_mock.run.return_value = True
    multi._build_recorder = MagicMock(return_value=recorder_mock)

    multi.run(iterations=2)

    assert "999" in multi.registry.state["completed"] or "999" in multi.registry.state["recording"]
    multi._build_recorder.assert_called()
