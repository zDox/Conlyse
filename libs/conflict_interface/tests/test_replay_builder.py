import json
import tempfile
import unittest
from pathlib import Path

from conflict_interface.data_types.newest.version import VERSION
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.replay.replay_builder import ReplayBuilder
from conflict_interface.replay.response_metadata import ResponseMetadata
from paths import TEST_DATA

TEST_GAME_ID = 1
TEST_PLAYER_ID = 1

NUM_RESPONSES = 10


class ReplayBuilderIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.recording_dir = TEST_DATA / f"recording_v{VERSION}"
        self.response_files = [
            self.recording_dir / f"response_{i:02d}.json" for i in range(1, NUM_RESPONSES + 1)
        ]
        if not all(f.exists() for f in self.response_files):
            self.skipTest(f"Missing recorded response fixtures under {self.recording_dir}")

        static_map_dir = self.recording_dir / "static_map"
        static_map_files = list(static_map_dir.glob("*.json")) if static_map_dir.exists() else []
        if not static_map_files:
            self.skipTest(f"Missing static map data fixture under {static_map_dir}")
        self.static_map_path = static_map_files[0]

    def test_build_and_open_replay(self):
        entries = []
        for path in self.response_files:
            with path.open("r", encoding="utf-8") as f:
                entries.append(json.load(f))

        map_id = entries[0]["map_id"]

        json_responses = [
            (
                ResponseMetadata(
                    timestamp=entry["timestamp"] * 1000,
                    game_id=TEST_GAME_ID,
                    player_id=TEST_PLAYER_ID,
                    client_version=VERSION,
                    map_id=map_id,
                ),
                entry["response"],
            )
            for entry in entries
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            replay_path = Path(tmp_dir) / "test_replay.conrp"

            builder = ReplayBuilder(replay_path, game_id=TEST_GAME_ID, player_id=TEST_PLAYER_ID)
            initial_index = builder.create_replay(json_responses)
            remaining = json_responses[initial_index + 1:]
            if remaining:
                builder.append_json_responses(remaining)

            self.assertTrue(replay_path.exists())

            replay = ReplayInterface(
                replay_path, static_map_data={map_id: self.static_map_path}, player_id=TEST_PLAYER_ID
            )
            try:
                replay.open(mode="r")

                segments_metadata = replay.get_segments_metadata()
                self.assertTrue(segments_metadata)

                self.assertGreater(replay.get_total_patches(), 0)

                timestamps = replay.get_timestamps()
                self.assertTrue(timestamps)
                self.assertEqual(len(timestamps), len(set(timestamps)))
                self.assertEqual(timestamps, sorted(timestamps))

                replay.validate_integrity()
            finally:
                replay.close()


if __name__ == "__main__":
    unittest.main()
