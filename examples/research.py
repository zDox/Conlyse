import logging
from pprint import pprint

from conflict_interface import HubInterface

import creds

from conflict_interface.logger_config import setup_library_logger

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    interface.login(creds.username, creds.password)
    game = interface.join_game(9709744)
    research_type = game.get_research_type_by_name_and_tier("UAV", 1)
    pprint(research_type)
    print(research_type.research())
    game.update()