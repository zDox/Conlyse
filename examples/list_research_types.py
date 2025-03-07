import logging

from conflict_interface import HubInterface

import creds
from pprint import pprint

from conflict_interface.logger_config import setup_library_logger

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    interface.login(creds.username, creds.password)

    game = interface.join_game(9709963)
    research_type = game.get_research_type(2300)
    print(research_type)
    pprint(research_type.tier)
    next_research = game.get_research_type(research_type.get_replacing_research())
    pprint(next_research)
    print(next_research.tier)