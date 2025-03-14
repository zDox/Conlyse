import logging

from conflict_interface.interface.hub_interface import HubInterface

from pprint import pprint

from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    username, password, email, proxy_url = load_credentials()
    interface.login(username, password)

    print("Starting resource profile example")
    my_games = interface.get_my_games()
    if iter(my_games).__next__() is None:
        print("Account is in no game")
        exit(1)

    game = interface.join_game(9759068)

    game.update()
    print(game.client_time())
    for category_id, category in game.get_my_resource_profile().categories.items():
        for resource_id, resource in category.resources.items():
            pprint(f"{resource.name} at {resource.time_zero}: {resource.get_resource_amount()}")
