from conflict_interface import HubInterface

import creds
from pprint import pprint


if __name__ == "__main__":
    interface = HubInterface()
    interface.login(creds.username, creds.password)

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
