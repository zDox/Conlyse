import json
import logging
from pprint import pprint

from conflict_interface import HubInterface
from conflict_interface.data_types import ResourceType
from conflict_interface.logger_config import setup_library_logger

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    with open('../tests/credentials.json') as f:
        creds = json.load(f)


    interface.login(creds["TEST_ACCOUNT_USERNAME"], creds["TEST_ACCOUNT_PASSWORD"])
    print("Starting example")
    game_id = 9709744
    pprint(f"Joining new game:  {game_id}")
    game = interface.join_game(game_id)

    resource_state = game.game_state.states.resource_state

    #print(resource_state.create_ask(ResourceType.SUPPLY, 15, 10000))
    """print(resource_state.cancel_order(resource_state.get_order_id(
        resource_type=ResourceType.SUPPLY,
        piece_price=15,
        amount=10000,
        buy=False
    ), buy=False))"""
    #print(resource_state.create_bid(ResourceType.SUPPLY, 15, 10000))
    print(resource_state.sell(resource_state.get_order_id(
        resource_type=ResourceType.SUPPLY,
        piece_price=4.7,
        amount=1058,
        buy=True
    )))
    game.update()

