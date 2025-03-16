import json
import zipfile
import os
from collections import defaultdict
from datetime import UTC
from datetime import datetime
from time import time
from typing import Literal

import jsonpatch
from zipfile import ZipFile

from jsonpatch import JsonPatch

from conflict_interface.data_types.custom_types import DateTimeMillisecondsStr
from conflict_interface.data_types.game_object import dump_date_time_str


class CorruptReplay(Exception):
    pass
VERSION = 3
INFORMATION_FILE = "information.json"
STATIC_MAP_DATA_FILE = "static_map_data.json"
MANDATORY_KEYS = ["version", "game_id", "player_id", "start_time"]
PATCH_FOLDER = "patches"
ACTION_FOLDER = "actions"


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
        self.zipfile: ZipFile | None = None
        self.start_time: datetime | None = None
        self.static_map_data: dict | None = defaultdict()

    def __enter__(self):
        if self.mode == 'w':
            if self.game_id is None or self.player_id is None:
                raise ValueError("Game ID and Player ID must be provided in write mode")
        elif self.mode in ('r', 'a') and not os.path.exists(self.filename):
            raise FileNotFoundError(f"Replay file {self.filename} not found")

        self.zipfile = ZipFile(self.filename, self.mode, zipfile.ZIP_DEFLATED)
        if self.mode == 'a':
            self._load_existing_replay()
            self._load_till_uptodate()
        elif self.mode == 'w':
            self._create_new_replay()
        elif self.mode == 'r':
            self._load_existing_replay()
        return self

    def open(self):
        self.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.zipfile:
            self.zipfile.close()

    def close(self):
        self.__exit__(None, None, None)

    def _write_information(self):
        information = {"version": VERSION,
                       "game_id": self.game_id,
                       "player_id": self.player_id,
                       "start_time": self.start_time,}
        with self.zipfile.open(INFORMATION_FILE, 'w') as f:
            f.write(json.dumps(information, indent=4).encode('utf-8'))

    def _create_new_replay(self):
        self.zipfile.mkdir(PATCH_FOLDER)
        self.zipfile.mkdir(ACTION_FOLDER)
        self._write_information()


    def _has_folder(self, folder_name: str) -> bool:
        """Check if the zip file contains a folder with the given name."""
        return any(name.startswith(f"{folder_name}/") for name in self.zipfile.namelist())

    def _has_patch(self, time_stamp: int) -> bool:
        return any(f"{PATCH_FOLDER}/patch_{time_stamp}.json" == filename for filename in self.zipfile.namelist())

    def _load_information(self):
        if INFORMATION_FILE not in self.zipfile.namelist():
            raise CorruptReplay("Information file is missing")
        with self.zipfile.open(INFORMATION_FILE, 'r') as f:
            content = json.load(f)

        missing_keys = [key for key in MANDATORY_KEYS if key not in content]
        if missing_keys:
            raise CorruptReplay(f"Missing keys in information file: {', '.join(missing_keys)}")

        if content["version"] != VERSION:
            raise CorruptReplay(f"Unsupported version {content['version']}")

        self.game_id, self.player_id = content["game_id"], content["player_id"]
        if content["start_time"]:
            self.start_time = datetime.fromtimestamp(float(content["start_time"]/1000))

    def _load_existing_replay(self):
        self._load_information()
        if not self._has_folder(PATCH_FOLDER):
            raise CorruptReplay(f"Replay file {self.filename} is missing patch folder")
        if not self._has_folder(ACTION_FOLDER):
            raise CorruptReplay(f"Replay file {self.filename} is missing action folder")

        initials = [name for name in self.zipfile.namelist() if name.startswith("initial_state")]
        patches = sorted([f.removeprefix(f"{PATCH_FOLDER}/") for f in self.zipfile.namelist()
                          if f.startswith(f'{PATCH_FOLDER}/patch_')])

        if len(initials) > 1:
            raise CorruptReplay(f"Multiple initial states detected in {self.filename}")
        if len(initials) == 0:
            raise CorruptReplay(f"No initial state found in {self.filename}.")

        self.initial_filename = initials[0]
        self._load_initial_game_state()
        self._load_static_map_data()

        self.time_stamps = sorted(int(p.removeprefix("patch_").removesuffix(".json")) for p in patches)

    def _load_till_uptodate(self):
        for time_stamp in self.time_stamps:
            patch = self._get_patch(time_stamp)
            patch.apply(self.game_state, in_place=True)

    def _load_initial_game_state(self):
        t1 = time()
        with self.zipfile.open(self.initial_filename) as f:
            self.game_state = json.load(f)
        print(f"Loaded {self.initial_filename} in {time() - t1:.4f} seconds")

    def _load_static_map_data(self):
        with self.zipfile.open(STATIC_MAP_DATA_FILE) as f:
            self.static_map_data = json.load(f)

    def set_time_stamp(self, filename: str, time_stamp: datetime):
        file_info = self.zipfile.getinfo(filename)
        file_info.date_time = time_stamp.timetuple()[0:6]
        self.zipfile.getinfo(file_info.filename).date_time = file_info.date_time

    def _write_initial_game_state(self, time_stamp: int, game_state: dict):
        filename = f"initial_state_{time_stamp}.json"
        with self.zipfile.open(filename, 'w') as f:
            f.write(json.dumps(game_state, indent=4).encode('utf-8'))
        self.set_time_stamp(filename, datetime.now())
        self.start_time = time_stamp

    def _get_patch(self, time_stamp: int) -> JsonPatch:
        with self.zipfile.open(f"{PATCH_FOLDER}/patch_{time_stamp}.json") as f:
                return JsonPatch.from_string(json.loads(f.read().decode('utf-8')))

    def _write_patch(self, time_stamp: int, patch: JsonPatch):
        filename = f"{PATCH_FOLDER}/patch_{time_stamp}.json"
        if self._has_patch(time_stamp):
            print(patch)
            return
        with self.zipfile.open(f"{PATCH_FOLDER}/patch_{time_stamp}.json", "w") as f:
            f.write(json.dumps(patch.to_string()).encode('utf-8'))
        self.set_time_stamp(filename, datetime.now())


    def load_game_state(self, time_stamp: datetime) -> dict:
        # TODO Make it working
        target_time_stamp = int(time_stamp.timestamp() * 1000)
        relevant_patch = next((t for t in self.time_stamps if t > target_time_stamp), self.time_stamps[-1] if self.time_stamps else None)

        if relevant_patch is None:
            self._load_initial_game_state()
        else:
            self._load_initial_game_state()
        return self.game_state

    def get_static_map_data(self) -> dict:
        return self.static_map_data

    def record_game_state(self, time_stamp: datetime, game_id: int, player_id: int, game_state: dict):
        if self.mode not in ("w", "a"):
            raise IOError("Replay is not in write or append mode")

        if game_id != self.game_id or player_id != self.player_id:
            raise CorruptReplay(f"Game ID or Player ID do not match to Replay {self.filename}")

        time_stamp = int(time_stamp.timestamp() * 1000)

        if not self.game_state:
            self._write_initial_game_state(time_stamp, game_state)
            self.game_state = game_state
        else:
            patch = jsonpatch.make_patch(self.game_state, game_state)
            self._write_patch(time_stamp, patch)
            patch.apply(self.game_state, in_place=True)

    def record_static_map_data(self, static_map_data: dict, game_id: int, player_id: int,):
        if self.mode not in ("w", "a"):
            raise IOError("Replay is not in write or append mode")

        if game_id != self.game_id or player_id != self.player_id:
            raise CorruptReplay(f"Game ID or Player ID do not match to Replay {self.filename}")
        print("Recording Static Map Data")
        if STATIC_MAP_DATA_FILE in self.zipfile.namelist():
            return

        with self.zipfile.open(STATIC_MAP_DATA_FILE, 'w') as f:
            f.write(json.dumps(static_map_data, indent=4).encode('utf-8'))
        self.set_time_stamp(STATIC_MAP_DATA_FILE, datetime.now())