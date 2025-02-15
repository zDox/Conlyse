import os
import sys
import inspect


currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from conflict_interface import ConflictInterface

import creds
from pprint import pprint
from time import sleep, time


if __name__ == "__main__":
    interface = ConflictInterface()
    interface.login(creds.username, creds.password)
    print("Starting example")

    pprint(f"Joining new game:  {9709963}")
    game = interface.join_game(9709963)

    Djibouti = next(iter(game.get_my_provinces(name="Djibouti").values()))
    pprint(Djibouti)
    for upgrade_id, upgrade in game.get_upgrade_types(upgrade_identifier='Arms Industry').items():
        pprint(f"{upgrade.id} {upgrade.tier} {upgrade.upgrade_identifier}")
    arms_lvl_1 = game.get_upgrade_type_by_name_and_tier('Arms Industry', 1)
    game.build_building(Djibouti.province_id, arms_lvl_1.id)
    game.update()
