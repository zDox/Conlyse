import json
import logging

from pprint import pprint

from conflict_interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger


if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    with open('../tests/credentials.json') as f:
        creds = json.load(f)
    proxy = {
        "http": creds["TEST_PROXY_URL"],
        "https": creds["TEST_PROXY_URL"],
    }

    interface = HubInterface()
    print("Ip without proxy: " + interface.get_public_ip())
    interface.set_proxy(proxy)
    print("Ip with proxy: " + interface.get_public_ip())
    interface.login(creds["TEST_ACCOUNT_USERNAME"], creds["TEST_ACCOUNT_PASSWORD"])

    game = interface.join_game(9758559)

    pprint(game.get_my_cities())