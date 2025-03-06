import logging

from conflict_interface import HubInterface

import creds

from conflict_interface.logger_config import setup_library_logger

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    interface.login(creds.username, creds.password)
    game = interface.join_game(9709744)
    city = next(iter(game.get_my_provinces(name="Rabat").values()))
    arms_lvl_1 = game.get_upgrade_type_by_name_and_tier('Arms Industry', 3)
    city.demolish_upgrade(arms_lvl_1.id)
    game.update()