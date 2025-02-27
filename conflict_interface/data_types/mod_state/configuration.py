from datetime import date, timedelta
from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.custom_types import UnmodifiableCollection, HashMap, HashSet
from conflict_interface.data_types.game_object import GameObject, parse_any


@dataclass
class SortingConfig(GameObject):
    C = "ultshared.modding.configuration.UltSortingConfig"
    sorting_order: int
    MAPPING = {"sorting_order": "sortOrder"}


@dataclass
class SoundConfig(GameObject):
    C = "ultshared.modding.configuration.UltSoundConfig"
    MAPPING = {}


@dataclass
class AirplaneConfig(GameObject):
    C = "ultshared.modding.configuration.UltAirplaneConfig"
    spy: bool
    patrol_radius: int
    patrol_target_damage_types: UnmodifiableCollection[int]
    embarkation_time: timedelta
    disembarkation_time: timedelta
    refuel_time: timedelta
    max_flight_time: Optional[timedelta]

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
class ControllableConfig(GameObject):
    controllable: bool
    MAPPING = {"controllable": "controllable"}


def parse_dict_of_ints(obj):
    obj.pop("@")
    return {int(key): val for key, val in obj.items()}


@dataclass
class CarrierConfig(GameObject):
    slot_config: HashMap[int, int]
    max_capacity: int

    MAPPING = {
            "slot_config": "slotConfig",
            "max_capacity": "maxCapacity"
    }


@dataclass
class AntiAirConfig(GameObject):
    C = "ultshared.modding.configuration.UltAntiAirConfig"
    range: int
    MAPPING = {"range": "range"}


@dataclass
class ScoutConfig(GameObject):
    C = "ultshared.modding.configuration.UltScoutConfig$DummyScoutConfig"
    stealth_classes: UnmodifiableCollection[int]
    camoflage_classes: UnmodifiableCollection[int]

    MAPPING = {
            "stealth_classes": "stealthClasses",
            "camoflage_classes": "camouflageClasses",
    }


@dataclass
class TokenProducerConfigProduction(GameObject):
    C = "ultshared.modding.configuration.UltTokenProducerConfig$TokenProduction"
    type_id: int
    amount: int
    duration: timedelta = timedelta(0)
    MAPPING = {
            "type_id": "typeID",
            "amount": "amount",
            "duration": "duration",
    }


def parse_list_of_production(obj):
    return [parse_any(TokenProducerConfigProduction, elm) for elm in obj[1]]


@dataclass
class TokenProducerConfig(GameObject):
    C = "ultshared.modding.configuration.UltTokenProducerConfig"
    tokens_on_spawn: UnmodifiableCollection[TokenProducerConfigProduction]
    tokens_provided: UnmodifiableCollection[TokenProducerConfigProduction]

    MAPPING = {
            "tokens_on_spawn": "tokensOnSpawn",
            "tokens_provided": "tokensProvided",
    }


@dataclass
class TokenConsumerConfig(GameObject):
    C = "ultshared.modding.configuration.UltTokenConsumerConfig"
    MAPPING = {}


@dataclass
class MissileConfig(GameObject):
    C = "ultshared.modding.configuration.UltMissileConfig$DummyMissileConfig"
    missile_slot: int
    stacking_limit: int
    launch_behaviour: str = ""

    MAPPING = {
        "launch_behaviour": "launchBehaviour",
        "missile_slot": "missileSlot",
        "stacking_limit": "stackingLimit",
    }


@dataclass
class MissileSlotConfig(GameObject):
    capacity: int
    resupply_time: timedelta
    initial_inventory: int

    MAPPING = {
        "capacity": "capacity",
        "resupply_time": "resupplyTime",
        "initial_inventory": "initialInventory",
    }


@dataclass
class MissileCarrierConfig(GameObject):
    missile_slot_config: HashMap[int, MissileSlotConfig]

    MAPPING = {
        "missile_slot_config": "missileSlotConfig",
    }

@dataclass
class MissileCarrierFeature(GameObject):
    missile_carrier_config: MissileCarrierConfig
    inventory: HashMap[int, int]
    last_missile_spawns: HashMap[int, date]

    MAPPING = {
        "missile_carrier_config": "missileCarrierConfig",
        "inventory": "inventory",
        "last_missile_spawns": "lastMissileSpawns",
    }


@dataclass
class RadarSignatureFeature(GameObject):
    C = "ultshared.warfare.UltRadarSignatureFeature"
    signature_size_map: HashMap[int, int]
    MAPPING = {
        "signature_size_map": "ssm",
    }


@dataclass
class TokenFeature(GameObject):
    """
    Not implemented. There exists no knowledge
    about how they work.
    """
    C = "ultshared.warfare.UltTokenFeature"
    tokens: HashSet[int] # TODO no idea if its int int (no examples in data1)
    MAPPING = {
        "tokens": "tokens",
    }


@dataclass
class CarrierFeature(GameObject):
    """
    Not implemented. There exists no knowledge
    about how they work.
    """
    MAPPING = {}
