import os

from conflict_interface import HubInterface
from conflict_interface.data_types import GameState
from conflict_interface.data_types.hub_types import HubGameState

TEST_KEYS = ["TEST_ACCOUNT_USERNAME", "TEST_ACCOUNT_PASSWORD", "TEST_ACCOUNT_EMAIL"]

def load_credentials() -> tuple[str, str, str]:


    if all(os.getenv(key) is not None for key in TEST_KEYS):
        # All credential details are already loaded as environment variables
        return os.getenv("TEST_ACCOUNT_USERNAME"), os.getenv("TEST_ACCOUNT_PASSWORD"), os.getenv("TEST_ACCOUNT_EMAIL")

    if not os.path.exists("credentials.json"):
        raise Exception("credentials.json file is missing")
    
    import json

    with open("credentials.json", "r") as file:
        credentials = json.load(file)

    missing_keys = [key for key in TEST_KEYS if key not in credentials]
    if missing_keys:
        raise Exception(f"Missing test keys in credentials.json: {', '.join(missing_keys)}")

    return credentials["TEST_ACCOUNT_USERNAME"], credentials["TEST_ACCOUNT_PASSWORD"], credentials["TEST_ACCOUNT_EMAIL"]

def get_new_game_id(interface: HubInterface) -> int:
    games = interface.get_global_games(state=HubGameState.READY_TO_JOIN,
                                       scenario_id=5975)
    if len(games) == 0:
        raise Exception("No games found")
    return games[0].game_id

def get_test_game_id(interface: HubInterface) -> int:
    my_games = interface.get_my_games(end_of_game=False)
    if len(my_games) == 0:
        return get_new_game_id(interface)

    return my_games[0].game_id