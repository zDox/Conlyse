import logging


from pprint import pprint

from ..custom_types import ArrayList
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)

    interface = HubInterface()
    username, password = "IpXOoCknBFbBKI", "qsubmliInVbgyF"
    interface.login(username, password)

    game = interface.join_game(9926617)

    algiers = game.get_provinces_by_name("Algiers")
    pprint([game.get_upgrade_type(upgrade.id)
           for upgrade in algiers.properties.possible_upgrades])
    algiers.properties.possible_upgrades = ArrayList([])
    algiers.properties.update_possible_upgrades(algiers.id)
    print("Updating possible_upgrades")
    pprint([game.get_upgrade_type(upgrade.id) for upgrade in algiers.properties.possible_upgrades])

