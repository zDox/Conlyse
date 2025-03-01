import json
import unittest

from requests import Session

from conflict_interface.data_types import GameState, dump_any, \
    PlayerState, ForeignAffairsState, NewspaperState, MapState
from conflict_interface.data_types import ResourceState
from conflict_interface.data_types import parse_game_object
from conflict_interface.data_types.army_state.army_state import ArmyState
from conflict_interface.game_interface import GameInterface
from tests.compare_dicts import compare_dicts, deepdiff


class ParseDumpTests(unittest.TestCase):
    test_states = [ResourceState, MapState, NewspaperState, PlayerState, ArmyState, ForeignAffairsState]
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

                game = GameInterface(9709744, False, Session(), None)

                states = data["result"]
                parsed_state = parse_game_object(GameState, states, game)
                self.assertIsInstance(parsed_state, GameState) # Just checks if parsing throws an error


    def test_parse_dump_states(self):
        for file in ParseDumpTests.test_files:
            for state in ParseDumpTests.test_states:
                with self.subTest(file=file, state = state):
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    game = GameInterface(9709744, False, Session(), None)

                    states = data["result"]["states"][str(state.STATE_ID)]

                    parsed_state = parse_game_object(state, states, game)
                    dumped_states = dump_any(parsed_state)


                    self.assertIsInstance(dumped_states, dict)

                    # covert both states, dumped_state back to json and then back to dict
                    dumped_states = json.loads(json.dumps(dumped_states))
                    states = json.loads(json.dumps(states))

                    errors = compare_dicts(states, dumped_states)
                    self.assertTrue(errors, msg=f"Failed for {state}")

    """
    def test_deep_compare(self):
     for file in ParseDumpTests.test_files:
         for state in ParseDumpTests.test_states:
             with self.subTest(file=file, state = state):
                 with open(file, "r", encoding="utf-8") as f:
                     data = json.load(f)

                 game = GameInterface(9709744, False, Session(), None)

                 states = data["result"]["states"][str(state.STATE_ID)]

                 parsed_state = parse_game_object(state, states, game)
                 dumped_states = dump_any(parsed_state)

                 self.assertEqual(deepdiff(states, dumped_states), {}, msg=f"Deepdiff Failed for {state}")
"""

if __name__ == "__main__":
    unittest.main()