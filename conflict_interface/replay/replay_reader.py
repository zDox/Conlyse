import json
import zipfile
from datetime import datetime

import jsonpatch


class ReplayReader:
    def __init__(self, zip_filename: str):
        self.zip_filename = zip_filename
        self.game_state = None
        self.time_stamps = []
        self.current_step = 0
        self._load_replay()

    def _load_replay(self):
        """Loads the replay data from the zip file."""
        with zipfile.ZipFile(self.zip_filename, 'r') as zf:
            if 'initial_state.json' in zf.namelist():
                with zf.open('initial_state.json') as f:
                    self.game_state = parse_any(json.load(f))

            self.patches = sorted([f.removeprefix("patch_") for f in zf.namelist() if f.startswith('patch_')])

    def step_forward(self):
        """Applies the next patch if available."""
        if self.current_step < len(self.patches):
            with zipfile.ZipFile(self.zip_filename, 'r') as zf:
                with zf.open(self.patches[self.current_step]) as f:
                    patch = jsonpatch.JsonPatch.from_string(json.load(f))
                    self.game_state = patch.apply(self.game_state)
                    self.current_step += 1
            return self.game_state
        else:
            raise IndexError("No more steps in replay.")

    def get_game_state(self, time_stamp: datetime):
        """Returns the current gamestate."""
        return self.game_state
