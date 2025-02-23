import unittest

from conflict_interface.data_types import ModableUpgrade
from conflict_interface.data_types import UpdateProvinceAction, UpdateProvinceActionModes
from conflict_interface.utils import Vector


class TestJsonDataclassConversion(unittest.TestCase):
    def test_upgrade(self):
        mod_upgrade = ModableUpgrade(
            id=1,
            enabled=True,
            condition=0,
            constructing=False,
            premium_level=0,
            relative_position=None,
        )

        update_action = UpdateProvinceAction(province_ids=Vector([2]),
                                             mode=UpdateProvinceActionModes.UPGRADE,
                                             slot=0,
                                             upgrade=mod_upgrade)

        from_js = update_action.from_dict(
            {
                "@c": "UpdateProvinceAction",
                "provinceIDs": ["java.util.Vector", [2]],
                "mode": 1,
                "slot": 0,
                "upgrade": {
                    "id": 1,
                    "e": True,
                    "c": 0,
                    "cn": False,
                    "pl": 0,
                }
            }
        )
        print(from_js)
        print(update_action)
        self.assertEqual(from_js, update_action)


if __name__ == "__main__":
    unittest.main()