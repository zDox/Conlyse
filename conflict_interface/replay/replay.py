import json
from collections import defaultdict
from datetime import datetime

import jsonpatch
import zipfile
import os

from conflict_interface.data_types.game_object import dump_date_time_str


class CorruptReplay(Exception):
    pass
INFORMATION_FILE = "information.json"
MANDATORY_KEYS = ["version", "game_id", "player_id"]


class Replay:
    def __init__(self, filename: str):
        self.filename = filename
        self.initial_filename: str | None = None
        self.previous_state = defaultdict()
        self.game_state: dict = defaultdict()
        self.time_stamps: list[int] = []
        self.game_id = None
        self.player_id = None

        # Ensure the zip file exists
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File {filename} not found")
        else:
            self._load_existing_replay()

    @classmethod
    def new_replay(cls, filename: str, game_id: int, player_id: int) -> "Replay":
        if not isinstance(game_id, int):
            raise TypeError("Game ID must be an int")
        if not isinstance(player_id, int):
            raise TypeError("Player ID must be an int")

        information = {
            "version": 1,
            "game_id": game_id,
            "player_id": player_id,
        }
        with zipfile.ZipFile(filename, 'w') as zf:
            with zf.open(INFORMATION_FILE, 'w') as f:
                f.write(json.dumps(information, indent=4).encode("utf-8"))
        instance = cls(filename)
        instance.game_id = game_id
        instance.player_id = player_id
        return instance


    def _load_information(self):
        with zipfile.ZipFile(self.filename, 'r') as zf:
            if not zf.getinfo(INFORMATION_FILE):
                raise CorruptReplay(f"Information file is not contained in replay")

            with zf.open(INFORMATION_FILE, 'r') as f:
                content = json.load(f)
        missing_keys = [key for key in MANDATORY_KEYS
                        if key not in content]
        if len(missing_keys) > 0:
            raise CorruptReplay(f"Missing keys in information file: {', '.join(missing_keys)}")

        self.version = content["version"]
        if self.version != 1:
            raise CorruptReplay(f"Information file version {self.version} is not supported")

        self.game_id = content["game_id"]
        self.player_id = content["player_id"]


    def _load_existing_replay(self):
        """Loads the latest gamestate from an existing replay file."""
        self._load_information()
        with zipfile.ZipFile(self.filename, 'r') as zf:
            initials = [name for name in zf.namelist() if name.startswith("initial_state")]
            patches = sorted([f for f in zf.namelist() if f.startswith('patch_')])

            if len(initials) > 1:
                raise CorruptReplay(f"Detected {len(initials)} initial game states in Replay file {self.filename}")
            elif len(initials) == 0 and len(patches) > 0:
                raise CorruptReplay(
                    f"Detected no initial game states in Replay file {self.filename} but {len(patches)} patches were found.")

            if len(initials) == 1:
                self.initial_filename = initials[0]
                with zf.open(initials[0]) as f:
                    self.previous_state = json.load(f)
            self.time_stamps = sorted([int(patch.removeprefix("patch_")) for patch in patches])



    def load_game_state(self, time_stamp: datetime) -> dict:
        destination_time_stamp = int(dump_date_time_str(time_stamp))
        found_time_stamp = None
        for i, time_stamp in enumerate(self.time_stamps):
            if time_stamp > destination_time_stamp:
                found_time_stamp = time_stamp
                break

        if found_time_stamp is None:
            found_time_stamp = self.time_stamps[-1]

        if found_time_stamp is None:
            self.previous_state = self._load_file(self.initial_filename)
        else:
            self.previous_state = self._load_file("path_" + str(found_time_stamp) + ".json")
        return self.previous_state


    def _load_file(self, filename) -> dict:
        with zipfile.ZipFile(self.filename, 'r') as zf:
            with zf.open(filename) as f:
                return json.loads(f)



    def record_game_state(self, game_id: int, player_id: int, game_state: dict):
        """
        Adds a game_state to the replay, storing only the diff.
        :param game_state:
        :param game_id:
        :param player_id:
        """
        if game_id != self.game_id or player_id != self.player_id:
            raise CorruptReplay(f"Replay {self.filename} is linked to game {self.game_id} and player {self.player_id}. Game {game_id} and player {player_id} are wrong.")
        time_stamp = game_state["timeStamp"]

        with zipfile.ZipFile(self.filename, 'a') as zf:
            if self.previous_state is None:
                # Store the first game_state as the initial state
                with zf.open(f'initial_state_{time_stamp}.json', 'w') as f:
                    f.write(json.dumps(game_state, indent=2).encode('utf-8'))
                self.previous_state = game_state
            else:
                # Store only the difference
                patch = jsonpatch.make_patch(self.previous_state, game_state)
                patch_filename = f'patch_{time_stamp}.json'
                with zf.open(patch_filename, 'w') as f:
                    f.write(json.dumps(patch.to_string(), indent=2).encode('utf-8'))
                self.previous_state = game_state