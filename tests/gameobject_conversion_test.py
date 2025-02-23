import unittest

from conflict_interface.data_types import ModableUpgrade
from conflict_interface.data_types import UpdateProvinceAction, ProvinceUpdateActionModes

class TestJsonDataclassConversion(unittest.TestCase):
    def test_upgrade(self):
        mod_upgrade = ModableUpgrade(
            id=1,
            enabled=True,
            condition=0,
            constructing=False,
            premium_level=0,
            relative_position=0,
            game=None,
        )

        update_action = UpdateProvinceAction(province_ids=[2],
                                             mode=ProvinceUpdateActionModes.UPGRADE,
                                             slot=0,
                                             upgrade=mod_upgrade,
                                             game=None)

        self.assertEquals(update_action.to_dict(), {
            "province_ids": [2],
            "mode": 1,
            "slot": 0,
            "upgrade": {
                "id": 1,
                "enabled": True,
                "condition": 0,
                "constructing": False,
                "premium_level": 0,
                "relative_position": 0,
            }
        })