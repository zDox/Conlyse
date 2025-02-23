from conflict_interface import ConflictInterface

import creds
from pprint import pprint


if __name__ == "__main__":
    interface = ConflictInterface()
    interface.login(creds.username, creds.password)

    print("Starting resource profile example")
    my_games = interface.get_my_games()
    if iter(my_games).__next__() is None:
        print("Account is no game")
        exit(1)

    selected_game = next(iter(my_games.values()))
    game = interface.join_game(selected_game.game_id)

    game.update()
    print(game.get_latest_uptime())
    for category_id, category in game.get_my_resource_profile().categories.items():
        for resource_id, resource in category.resources.items():
            pprint(f"{resource.name}: {game.get_resource_amount(resource_id)}")
            pprint(resource)
