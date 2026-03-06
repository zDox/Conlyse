import logging
from pprint import pprint

from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials


if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    username, password, email, proxy_url = load_credentials()


    interface.login(username, password)
    print("Starting example")
    game_id = 9758559
    pprint(f"Joining new game:  {game_id}")
    game = interface.join_game(game_id)
    city = game.get_provinces_by_name("Johannesburg")
    army = game.get_my_army_by_number(14)
    unit_type = game.get_unit_type_by_name_and_tier("Motorized Infantry", 1)

    split_units = [(unit_type.id, 1)]
    target = city.center_coordinate
    army.split_army(target, split_units)
    game.update()