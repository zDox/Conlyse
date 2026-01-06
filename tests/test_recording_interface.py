import unittest
from unittest.mock import MagicMock, patch

from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.interface.recording_interface import RecordingInterface


class RecordingInterfaceTests(unittest.TestCase):
    def test_update_without_previous_state_ids(self):
        with patch("conflict_interface.interface.recording_interface.GameApi") as mock_game_api_cls:
            mock_game_api = MagicMock()
            mock_game_api.make_game_server_request.return_value = {"result": {}}
            mock_game_api_cls.return_value = mock_game_api

            interface = RecordingInterface(
                game_id=1,
                session=MagicMock(),
                auth_details=MagicMock(),
                proxy=None,
            )
            response = interface.update()

        mock_game_api.make_game_server_request.assert_called_once()
        payload = mock_game_api.make_game_server_request.call_args.args[0]
        self.assertFalse(payload["addStateIDsOnSent"])
        self.assertIsNone(payload["stateIDs"])
        self.assertIsNone(payload["tstamps"])
        self.assertEqual(response, {"result": {}})

    def test_update_uses_previous_state_metadata(self):
        with patch("conflict_interface.interface.recording_interface.GameApi") as mock_game_api_cls:
            mock_game_api = MagicMock()
            mock_game_api.make_game_server_request.return_value = {"result": {}}
            mock_game_api_cls.return_value = mock_game_api

            interface = RecordingInterface(
                game_id=1,
                session=MagicMock(),
                auth_details=MagicMock(),
                proxy=None,
            )
            interface.last_response = {
                "result": {
                    "states": {
                        "1": {"stateType": 1, "stateID": "abc", "timeStamp": 111},
                        "2": {"stateType": 2, "stateID": "def", "timeStamp": 222},
                    }
                }
            }
            interface.update()

        payload = mock_game_api.make_game_server_request.call_args.args[0]
        self.assertTrue(payload["addStateIDsOnSent"])
        self.assertEqual(payload["stateIDs"]["1"], "abc")
        self.assertEqual(payload["stateIDs"]["2"], "def")
        self.assertEqual(payload["tstamps"]["1"], 111)
        self.assertEqual(payload["tstamps"]["2"], 222)


class HubInterfaceRecordingTests(unittest.TestCase):
    def test_record_game_returns_recording_interface(self):
        with patch("conflict_interface.interface.hub_interface.HubApi") as mock_hub_api:
            mock_api_instance = MagicMock()
            mock_hub_api.return_value = mock_api_instance
            hub = HubInterface()
            hub.auth = True
            hub.api.session = MagicMock()
            hub.api.auth = MagicMock()
            hub.api.proxy = {"http": "proxy"}

            with patch("conflict_interface.interface.hub_interface.RecordingInterface") as mock_recording_cls:
                recording_instance = MagicMock()
                mock_recording_cls.return_value = recording_instance
                result = hub.record_game(42)

        mock_recording_cls.assert_called_once()
        recording_instance.load_game.assert_called_once()
        self.assertIs(result, recording_instance)


if __name__ == "__main__":
    unittest.main()
