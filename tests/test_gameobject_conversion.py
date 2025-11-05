import json
import unittest

from conflict_interface.data_types.army_state.army_state import ArmyState
from conflict_interface.data_types.foreign_affairs_state.foreign_affairs_state import ForeignAffairsState
from conflict_interface.data_types.game_event_state.game_event_state import GameEventState
from conflict_interface.data_types.game_info_state.game_info_state import GameInfoState
from conflict_interface.data_types.game_object import dump_any
from conflict_interface.data_types.game_object import parse_game_object
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.map_state.map_state import MapState
from conflict_interface.data_types.mod_state.mod_state import ModState
from conflict_interface.data_types.newspaper_state.newspaper_state import NewspaperState
from conflict_interface.data_types.player_state.player_state import PlayerState
from conflict_interface.data_types.research_state.research_state import ResearchState
from conflict_interface.data_types.resource_state.resource_state import ResourceState
from conflict_interface.interface.game_interface import GameInterface
from tests.compare_dicts import compare_dicts


class ParseDumpTests(unittest.TestCase):
    test_states = [ModState, ResourceState, MapState, NewspaperState, PlayerState, ArmyState, ForeignAffairsState,
                   ResearchState, GameInfoState, GameEventState]
    test_files = ["full_test_data_1_v206.json"]

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

                game = GameInterface()

                states = data["result"]
                parsed_state = parse_game_object(GameState, states, game)
                self.assertIsInstance(parsed_state, GameState) # Just checks if parsing throws an error


    def test_parse_dump_states(self):
        for file in ParseDumpTests.test_files:
            for state in ParseDumpTests.test_states:
                with self.subTest(file=file, state = state):
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    game = GameInterface()

                    states = data["result"]["states"][str(state.STATE_TYPE)]

                    parsed_state = parse_game_object(state, states, game)
                    dumped_states = dump_any(parsed_state)


                    self.assertIsInstance(dumped_states, dict)

                    # covert both states, dumped_state back to json and then back to dict
                    dumped_states = json.loads(json.dumps(dumped_states))
                    states = json.loads(json.dumps(states))

                    errors = compare_dicts(states, dumped_states)
                    self.assertTrue(errors, msg=f"Failed for {state}")

if __name__ == "__main__":
    unittest.main()