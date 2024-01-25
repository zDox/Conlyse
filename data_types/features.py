from data_types.utils import JsonMappedClass, unixtimestamp_to_datetime

from datetime import date, timedelta
from dataclasses import dataclass


@dataclass
class MissileSlotConfig(JsonMappedClass):
    id: int
    capacity: int
    resupply_time: timedelta
    initial_inventory: int

    mapping = {
        "id": "id",
        "capacity": "capacity",
        "resupply_time": "resupplyTime",
        "initial_inventory": "initialInventory",
    }


@dataclass
class MissileCarrierConfig(JsonMappedClass):
    missile_slot_config: dict[int, MissileSlotConfig]

    @classmethod
    def from_dict(cls, obj):
        missile_slot_config = {int(slot_id): MissileSlotConfig.from_dict(
                                {**slot, "id": slot_id})
                               for slot_id, slot in
                               list(obj["missileSlotConfig"].items())[1:]}
        return cls(**{
            "missile_slot_config": missile_slot_config,
            })


@dataclass
class MissileCarrierFeature:
    missile_carrier_config: MissileCarrierConfig
    inventory: dict[int, int]
    last_missile_spawns: dict[int, date]

    @classmethod
    def from_dict(cls, obj):
        missile_carrier_config = MissileCarrierConfig.from_dict(
                obj["missileCarrierConfig"])

        inventory = {int(slot_id): amount
                     for slot_id, amount in list(obj["inventory"].items())[1:]}

        last_missile_spawns = {int(slot_id):
                               unixtimestamp_to_datetime(spawn_time)
                               for slot_id, spawn_time
                               in list(obj["lastMissileSpawns"].items())[1:]}

        return cls(**{
            "missile_carrier_config": missile_carrier_config,
            "inventory": inventory,
            "last_missile_spawns": last_missile_spawns,
        })


@dataclass
class RadarSignatureFeature:
    signature_size_map: dict[int, int]

    @classmethod
    def from_dict(cls, obj):
        signature_size_map = {int(signature): size
                              for signature, size
                              in list(obj["ssm"].items())[1:]}
        return cls(**{
            "signature_size_map": signature_size_map,
            })


@dataclass
class TokenFeature(JsonMappedClass):
    """
    Not implemented. There exists no knowledge
    about how they work.
    """
    mapping = {}


@dataclass
class CarrierFeature(JsonMappedClass):
    """
    Not implemented. There exists no knowledge
    about how they work.
    """
    mapping = {}
