from conflict_interface import ConflictInterface
import creds
from pprint import pprint


if __name__ == "__main__":
    interface = ConflictInterface()
    interface.login(creds.username, creds.password)
    res = interface.get_my_games(True)
    pprint(res)
