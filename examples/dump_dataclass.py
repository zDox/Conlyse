import json
from pprint import pprint

from conflict_interface import HubInterface
from conflict_interface.data_types import dump_dataclass
from examples import creds

if __name__ == "__main__":
    interface = HubInterface()
    interface.login(creds.username, creds.password)
    print("Starting example")

    pprint(f"Joining new game:  {9709744}")
    game = interface.join_game(9709744)
    print("Loaded Game")

    res = dump_dataclass(game.get_players()[1])

    out = json.dumps(res)

    print(out)