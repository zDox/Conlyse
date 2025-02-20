from datetime import date, timedelta
from dataclasses import dataclass

from conflict_interface.utils import JsonMappedClass, \
        unixtimestamp_to_datetime, ConMapping, milliseconds_to_timedelta


@dataclass
class SortingConfig(JsonMappedClass):
    sorting_order: int
    MAPPING = {"sorting_order": "sortOrder"}


@dataclass
class SoundConfig(JsonMappedClass):
    pass


def parse_list_of_ints(obj):
    return obj[1]


@dataclass
class AirplaneConfig(JsonMappedClass):
    spy: bool
    patrol_radius: int
    patrol_target_damage_types: list[int]
    embarkation_time: timedelta
    disembarkation_time: timedelta
    refuel_time: timedelta
    max_flight_time: timedelta

    MAPPING = {
            "spy": "spy",
            "patrol_radius": "patrolRadius",
            "patrol_target_damage_types": ConMapping(
                "patrolTargetDamageTypes", parse_list_of_ints),
            "embarkation_time": "embarkationTime",
            "disembarkation_time": "disembarkationTime",
            "refuel_time": "refuelTime",
            "max_flight_time": "maxFlightTime",
    }


@dataclass
class ControllableConfig(JsonMappedClass):
    controllable: bool
    MAPPING = {"controllable": "controllable"}


def parse_dict_of_ints(obj):
    obj.pop("@")
    return {int(key): val for key, val in obj.items()}


@dataclass
class CarrierConfig(JsonMappedClass):
    slot_config: dict[int, int]
    max_capacity: int

    MAPPING = {
            "slot_config": ConMapping("slotConfig", parse_dict_of_ints),
            "max_capacity": "maxCapacity"
    }


@dataclass
class AntiAirConfig(JsonMappedClass):
    range: int
    MAPPING = {"range": "range"}


@dataclass
class ScoutConfig(JsonMappedClass):
    stealth_classes: list[int]
    camoflage_classes: list[int]

    MAPPING = {
            "stealth_classes": ConMapping("stealthClasses",
                                          parse_list_of_ints),
            "camoflage_classes": ConMapping("camouflageClasses",
                                            parse_list_of_ints),
    }


@dataclass
class TokenProducerConfigProduction(JsonMappedClass):
    type: str
    amount: int
    duration: timedelta
    MAPPING = {
            "type": "type",
            "amount": "amount",
            "duration": ConMapping("duration", milliseconds_to_timedelta),
    }


def parse_list_of_production(obj):
    return [TokenProducerConfigProduction.from_dict(elm)
            for elm in obj[1]]


@dataclass
class TokenProducerConfig(JsonMappedClass):
    tokens_on_spawn: list[TokenProducerConfigProduction]
    tokens_provided: list[TokenProducerConfigProduction]

    MAPPING = {
            "tokens_on_spawn": ConMapping("tokensOnSpawn",
                                          parse_list_of_production),
            "tokens_provided": ConMapping("tokensProvided",
                                          parse_list_of_production),
    }


@dataclass
class TokenConsumerConfig(JsonMappedClass):
    pass


@dataclass
class MissileConfig(JsonMappedClass):
    launch_behaviour: str
    missile_slot: int
    stacking_limit: int

    MAPPING = {
        "launch_behaviour": "launchBehaviour",
        "missile_slot": "missileSlot",
        "stacking_limit": "stackingLimit",
    }


@dataclass
class MissileSlotConfig(JsonMappedClass):
    id: int
    capacity: int
    resupply_time: timedelta
    initial_inventory: int

    MAPPING = {
        "province_id": "province_id",
        "capacity": "capacity",
        "resupply_time": "resupplyTime",
        "initial_inventory": "initialInventory",
    }


@dataclass
class MissileCarrierConfig():
    missile_slot_config: dict[int, MissileSlotConfig]

    @classmethod
    def from_dict(cls, obj):
        missile_slot_config = {int(slot_id): MissileSlotConfig.from_dict(
                                {**slot, "province_id": slot_id})
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
    MAPPING = {}


@dataclass
class CarrierFeature(JsonMappedClass):
    """
    Not implemented. There exists no knowledge
    about how they work.
    """
    MAPPING = {}
