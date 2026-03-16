import logging

from conflict_interface.interface.hub_interface import HubInterface

from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    username, password, email, proxy_url = load_credentials()
    interface.login(username, password)
    game = interface.join_game(9709744)
    city = next(iter(game.get_my_provinces(name="Rabat").values()))
    motorized_infantry_lvl_1 = game.get_unit_type_by_name_and_tier("Motorized Infantry", 4)

    city.mobilize_unit_by_id(motorized_infantry_lvl_1.id)
    game.update()