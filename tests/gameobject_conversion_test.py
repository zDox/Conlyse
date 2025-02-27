import json
import unittest
from pprint import pprint

from deepdiff import DeepDiff

from conflict_interface.data_types import ModableUpgrade, parse_dataclass, GameState, AuthDetails, dump_any, \
    PlayerState, ForeignAffairsState, NewspaperState
from conflict_interface.data_types import UpdateProvinceAction, UpdateProvinceActionModes
from conflict_interface.data_types import Vector
from conflict_interface.data_types import parse_game_object
from conflict_interface.data_types.army_state.army_state import ArmyState
from conflict_interface.data_types.game_state.game_state import States
from conflict_interface.game_interface import GameInterface
from tests.compare_dicts import compare_dicts

class ParseDumpTests(unittest.TestCase):
    test_states = [NewspaperState, PlayerState, ArmyState, ForeignAffairsState]
    test_files = ["full_test_data_1.json"]

    def test_load_json(self):
        for file in ParseDumpTests.test_files:
            with self.subTest(file=file):
                # Read in the json file
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.assertLess(2, len(data["result"]["states"])) # just tests if loading the file throws an error


    def test_convert_states(self):
        for file in ParseDumpTests.test_files:
            with self.subTest(file = file):
                # Read in the json file
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                game = GameInterface(9709744)

                states = data["result"]
                parsed_state = parse_game_object(GameState, states, game)
                self.assertIsInstance(parsed_state, GameState) # Just checks if parsing throws an error


    def test_parse_dump_states(self):
        for file in ParseDumpTests.test_files:
            for state in ParseDumpTests.test_states:
                with self.subTest(file=file, state = state):
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    game = GameInterface(9709744)

                    states = data["result"]["states"][str(state.STATE_ID)]

                    parsed_state = parse_game_object(state, states, game)
                    dumped_states = dump_any(parsed_state)

                    self.assertIsInstance(dumped_states, dict)

                    diff = compare_dicts(states, dumped_states)
                    self.assertEqual(diff, {}, msg=f"Failed for {state}")

if __name__ == "__main__":
    unittest.main()