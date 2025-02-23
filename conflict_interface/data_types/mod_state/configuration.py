from datetime import date, timedelta
from dataclasses import dataclass

from conflict_interface.utils import JsonMappedClass, \
    unixtimestamp_to_datetime, ConMapping, milliseconds_to_timedelta, HashSet, HashMap, UnmodifiableCollection, \
    LinkedHashMap, GameObject


@dataclass
class SortingConfig(JsonMappedClass):
    sorting_order: int
    MAPPING = {"sorting_order": "sortOrder"}


@dataclass
class SoundConfig(JsonMappedClass):
    pass


@dataclass
class AirplaneConfig(JsonMappedClass):
    spy: bool
    patrol_radius: int
    patrol_target_damage_types: UnmodifiableCollection[int]
    embarkation_time: timedelta
    disembarkation_time: timedelta
    refuel_time: timedelta
    max_flight_time: timedelta

    MAPPING = {
            "spy": "spy",
            "patrol_radius": "patrolRadius",
            "patrol_target_damage_types": "patrolTargetDamageTypes",
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
    slot_config: HashMap[int, int]
    max_capacity: int

    MAPPING = {
            "slot_config": "slotConfig",
            "max_capacity": "maxCapacity"
    }


@dataclass
class AntiAirConfig(JsonMappedClass):
    range: int
    MAPPING = {"range": "range"}


@dataclass
class ScoutConfig(JsonMappedClass):
    stealth_classes: UnmodifiableCollection[int]
    camoflage_classes: UnmodifiableCollection[int]

    MAPPING = {
            "stealth_classes": "stealthClasses",
            "camoflage_classes": "camouflageClasses",
    }


@dataclass
class TokenProducerConfigProduction(JsonMappedClass):
    type: str
    amount: int
    duration: timedelta
    MAPPING = {
            "type": "type",
            "amount": "amount",
            "duration": "duration",
    }


def parse_list_of_production(obj):
    return [TokenProducerConfigProduction.from_dict(elm)
            for elm in obj[1]]


@dataclass
class TokenProducerConfig(JsonMappedClass):
    tokens_on_spawn: UnmodifiableCollection[TokenProducerConfigProduction]
    tokens_provided: UnmodifiableCollection[TokenProducerConfigProduction]

    MAPPING = {
            "tokens_on_spawn": "tokensOnSpawn",
            "tokens_provided": "tokensProvided",
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
    missile_slot_config: LinkedHashMap[int, MissileSlotConfig]

@dataclass
class MissileCarrierFeature:
    missile_carrier_config: MissileCarrierConfig
    inventory: dict[int, int]
    last_missile_spawns: dict[int, date]

    MAPPING = {
        "missileCarrierConfig": "missileCarrierConfig",
        "inventory": "inventory",
        "lastMissileSpawns": "lastMissileSpawns",
    }


@dataclass
class RadarSignatureFeature(GameObject):
    signature_size_map: HashMap[int, int]
    MAPPING = {
        "signature_size_map": "ssm",
    }


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
