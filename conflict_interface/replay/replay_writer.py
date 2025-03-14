import json
from datetime import datetime

import jsonpatch
import zipfile
import os

from conflict_interface.data_types.game_object import dump_any
from conflict_interface.data_types.game_state.game_state import GameState

class CorruptReplay(Exception):
    pass

class Replay:
    def __init__(self, filename: str):
        self.zip_filename = filename
        self.previous_state = None
        self.change_count = 0
        self.game_state = None
        self.time_stamps = []

        # Ensure the zip file exists
        if not os.path.exists(filename):
            with zipfile.ZipFile(filename, 'w') as _:
                pass
        else:
            self._load_existing_replay()

    def _load_existing_replay(self):
        """Loads the latest gamestate from an existing replay file."""
        with zipfile.ZipFile(self.zip_filename, 'r') as zf:
            initials = [name for name in zf.namelist() if name.startswith("initial_state")]
            if len(intials) > 1:
                raise CorruptReplay(f"Detected {len(intials)} initial game states in Replay file {self.filename}")
            if len(initials()     patches = sorted([f for f in zf.namelist() if f.startswith('patch_')])

            if if len:
                with zf.open(initial_state) as f:
                    self.previous_state = json.load(f)
                self.change_count = 0

    def add_game_state(self, game_state: dict):
        """
        Adds a game_state to the replay, storing only the diff.
        :param game_state:
        """

        with zipfile.ZipFile(self.zip_filename, 'a') as zf:
            if self.previous_state is None:
                # Store the first gamestate as the initial state
                with zf.open('initial_state.json', 'w') as f:
                    f.write(json.dumps(game_state, indent=2).encode('utf-8'))
                self.previous_state = game_state
            else:
                # Store only the diff
                patch = jsonpatch.make_patch(self.previous_state, game_state)
                patch_filename = f'patch_{self.change_count}.json'
                with zf.open(patch_filename, 'w') as f:
                    f.write(json.dumps(patch.to_string(), indent=2).encode('utf-8'))
                self.previous_state = game_state

            self.change_count += 1
