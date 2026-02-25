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
    research_type = game.get_research_type_by_name_and_tier("UAV", 1)
    print(research_type.cancel_research())
    game.update()