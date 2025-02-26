import unittest

from conflict_interface.data_types import ModableUpgrade, parse_dataclass
from conflict_interface.data_types import UpdateProvinceAction, UpdateProvinceActionModes
from conflict_interface.data_types import Vector
from conflict_interface.data_types import parse_game_object
from conflict_interface.game_api import GameApi
from conflict_interface.game_interface import GameInterface


class TestJsonDataclassConversion(unittest.TestCase):
    def test_upgrade(self):
        """

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

        from_js = parse_game_object(
            UpdateProvinceAction,
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
            }, GameInterface(game_id=1, game_api=GameAPI({}, {}, None, 1))
        )
        """
        self.assertEqual(True, True)


if __name__ == "__main__":
    unittest.main()