import os
import sys
import inspect
from pprint import pprint

from conflict_interface.data_types.province.province import UpdateProvinceAction, ProvinceUpdateActionModes
from conflict_interface.data_types.upgrades.upgrade import ModableUpgrade

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

if __name__ == "__main__":
    mod_upgrade = ModableUpgrade(
        id=2328,
        enabled=True,
        condition=0,
        constructing=False,
        premium_level=0,
        relative_position=0,
        game=None,
    )
    update_action = UpdateProvinceAction(province_ids=[2328],
                                         mode=ProvinceUpdateActionModes.UPGRADE,
                                         slot=0,
                                         upgrade=mod_upgrade,
                                         game=None)
    pprint(update_action.to_dict())