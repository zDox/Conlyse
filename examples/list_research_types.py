import logging



from pprint import pprint

from conflict_interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    username, password, email, proxy_url = load_credentials()
    interface.login(username, password)

    game = interface.join_game(9709963)
    research_type = game.get_research_type(2300)
    print(research_type)
    pprint(research_type.tier)
    next_research = game.get_research_type(research_type.get_replacing_research())
    pprint(next_research)
    print(next_research.tier)