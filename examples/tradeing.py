import logging
from pprint import pprint

from conflict_interface.data_types.resource_state.resource_state_enums import ResourceType
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    username, password, email, proxy_url = load_credentials()

    interface.login(username, password)
    print("Starting example")
    game_id = 9709744
    pprint(f"Joining new game:  {game_id}")
    game = interface.join_game(game_id)

    resource_state = game.game_state.states.resource_state

    print(resource_state.create_ask(ResourceType.SUPPLY, 15, 10000))
    print(resource_state.create_bid(ResourceType.SUPPLY, 15, 10000))
    game.update()

