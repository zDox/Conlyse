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
    arms_lvl_1 = game.get_upgrade_type_by_name_and_tier('Arms Industry', 3)
    city.demolish_upgrade(arms_lvl_1.id)
    game.update()