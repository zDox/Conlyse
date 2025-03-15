import json
import zipfile
import os
from collections import defaultdict
from datetime import datetime
from typing import Literal

import jsonpatch

from conflict_interface.data_types.game_object import dump_date_time_str


class CorruptReplay(Exception):
    pass

INFORMATION_FILE = "information.json"
MANDATORY_KEYS = ["version", "game_id", "player_id"]


class Replay:
    def __init__(self, filename: str, mode: Literal['r', 'w', 'a'], game_id: int = None, player_id: int = None):
        if mode not in ('r', 'w', 'a'):
            raise ValueError("Mode must be 'r' (read), 'w' (write), or 'a' (append)")

        self.filename = filename
        self.mode = mode
        self.initial_filename: str | None = None
        self.game_state: dict = defaultdict()
        self.time_stamps: list[int] = []
        self.game_id = game_id
        self.player_id = player_id
        self.zipfile = None

    def __enter__(self):
        if self.mode == 'w':
            if self.game_id is None or self.player_id is None:
                raise ValueError("Game ID and Player ID must be provided in write mode")
        elif self.mode in ('r', 'a') and not os.path.exists(self.filename):
            raise FileNotFoundError(f"Replay file {self.filename} not found")

        self.zipfile = zipfile.ZipFile(self.filename, self.mode, zipfile.ZIP_DEFLATED)
        if self.mode in ('r', 'a'):
            self._load_existing_replay()
        elif self.mode in 'w':
            self._create_new_replay()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.zipfile:
            self.zipfile.close()

    def _create_new_replay(self):
        with zipfile.ZipFile(self.filename, 'w', zipfile.ZIP_DEFLATED) as zf:
            information = {"version": 1, "game_id": self.game_id, "player_id": self.player_id}
            with zf.open(INFORMATION_FILE, 'w') as f:
                f.write(json.dumps(information, indent=4).encode('utf-8'))

    def _load_information(self):
        if INFORMATION_FILE not in self.zipfile.namelist():
            raise CorruptReplay("Information file is missing")
        with self.zipfile.open(INFORMATION_FILE, 'r') as f:
            content = json.load(f)

        missing_keys = [key for key in MANDATORY_KEYS if key not in content]
        if missing_keys:
            raise CorruptReplay(f"Missing keys in information file: {', '.join(missing_keys)}")

        if content["version"] != 1:
            raise CorruptReplay(f"Unsupported version {content['version']}")

        self.game_id, self.player_id = content["game_id"], content["player_id"]

    def _load_existing_replay(self):
        self._load_information()
        initials = [name for name in self.zipfile.namelist() if name.startswith("initial_state")]
        patches = sorted([f for f in self.zipfile.namelist() if f.startswith('patch_')])

        if len(initials) > 1:
            raise CorruptReplay(f"Multiple initial states detected in {self.filename}")
        if not initials and patches:
            raise CorruptReplay(f"No initial state found in {self.filename}, but patches exist")

        if initials:
            self.initial_filename = initials[0]
            with self.zipfile.open(initials[0]) as f:
                self.game_state = json.load(f)
        self.time_stamps = sorted(int(p.removeprefix("patch_").removesuffix(".json")) for p in patches)

    def load_game_state(self, time_stamp: datetime) -> dict:
        target_time_stamp = int(dump_date_time_str(time_stamp))
        relevant_patch = next((t for t in self.time_stamps if t > target_time_stamp), self.time_stamps[-1] if self.time_stamps else None)

        if relevant_patch is None:
            self.game_state = self._load_file(self.initial_filename)
        else:
            self.game_state = self._load_file(f"patch_{relevant_patch}.json")
        return self.game_state

    def _load_file(self, filename: str) -> dict:
        with self.zipfile.open(filename) as f:
            return json.load(f)

    def record_game_state(self, game_state: dict):
        if self.mode not in ("w", "a"):
            raise IOError("Replay is not in write or append mode")

        if game_state["game_id"] != self.game_id or game_state["player_id"] != self.player_id:
            raise CorruptReplay("Game ID or Player ID mismatch")

        time_stamp = game_state["timeStamp"]
        if self.game_state:
            patch = jsonpatch.make_patch(self.game_state, game_state)
            with self.zipfile.open(f'patch_{time_stamp}.json', 'w') as f:
                f.write(json.dumps(patch.to_string(), indent=4).encode('utf-8'))
        else:
            with self.zipfile.open(f'initial_state_{time_stamp}.json', 'w') as f:
                f.write(json.dumps(game_state, indent=4).encode('utf-8'))
        self.game_state = game_state
