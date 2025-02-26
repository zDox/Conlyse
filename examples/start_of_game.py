from pprint import pprint

from conflict_interface import HubInterface
from conflict_interface.data_types.hub_game_info import HubGameState
from examples import creds

if __name__ == "__main__":
    print("Starting start of game example")
    interface = HubInterface()
    interface.login(creds.username, creds.password)
    for game_info in interface.get_global_games().values():
        if game_info.day_of_game != 1:
            continue
        print(f"Game: {game_info.game_id}")
        game = interface.join_game(game_info.game_id, guest=True)
        print(f"Day: {game.game_state.states.game_info_state.day_of_game}")
        print(f"Start: {game.game_state.states.game_info_state.start_of_game}")
        print(f"End: {game.game_state.states.game_info_state.end_of_game}")
        if game.game_state.states.game_info_state.game_ended:
            print(f"Difference between start and end: {game.game_state.states.game_info_state.end_of_game - game.game_state.states.game_info_state.start_of_game}")
        print(f"Open slots: {game.game_state.states.game_info_state.open_slots}")
        print(f"Speed: {1/game.game_state.states.game_info_state.time_scale}")
        print(f"Time: {game.client_time()}")
        print(f"Delta between next_day_time and current time: {game.game_state.states.game_info_state.next_day_time - game.client_time()}")
        print(f"Delta between next_day_time and start time: {game.game_state.states.game_info_state.next_day_time - game.game_state.states.game_info_state.start_of_game}")
        print(f"First day delta {game.game_state.states.game_info_state.next_day_time - game.game_state.states.game_info_state.start_of_game}")
        print(f"Time : {game.game_state.states.game_info_state.get_display_time()}")
        print()
