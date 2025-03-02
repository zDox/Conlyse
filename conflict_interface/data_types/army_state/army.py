from dataclasses import dataclass
from enum import Enum
from typing import Optional

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.custom_types import DefaultEnumMeta, LinkedList, UnitList
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.mod_state.configuration import \
        CarrierFeature, MissileCarrierFeature, RadarSignatureFeature, \
        TokenFeature
from conflict_interface.data_types.mod_state.commands import Command
from conflict_interface.data_types.mod_state.air_parameters import AirParameters
from conflict_interface.data_types.mod_state.anti_air_parameters import AntiAirParameters

from conflict_interface.data_types.army_state.unit import Unit

from conflict_interface.data_types.map_state.terrain_type import TerrainType, TerrainTypeStr
from conflict_interface.data_types.point import Point

ARMY_CLOSE_COMBAT_RANGE = 5

@dataclass
class Battle(GameObject):
    C = "ultshared.warfare.UltBattle"
    attacker_ids: list[int]

    MAPPING = {
        "attacker_ids": "a"
    }


class FightStatus(Enum, metaclass=DefaultEnumMeta):
    """
    Status of an army.
    """
    IDLE = 0
    FIGHTING = 1
    BOMBARDING = 2
    PATROLLING = 3
    APPROACH_PATROL = 4
    SIEGING = 5
    ANTI_AIR = 6
    BOMBING = 7


class Aggressiveness(Enum, metaclass=DefaultEnumMeta):
    """
    Represents under which situations a unit would engage an enemy.
    """
    DEFAULT = 0
    HOLD_FIRE = 1
    RETURN_FIRE = 2
    NORMAL = 3
    AGGRESSIVE = 4


class ForcedMarch(Enum, metaclass=DefaultEnumMeta):
    """
    ForcedMarch is the march where a unit gets a bit of damage
    but in turn is a little bit faster.
    """
    DEACTIVE = 0
    ACTIVE = 1
    PREMIUM = 2


@dataclass
class Army(GameObject):
    """
    Represents an army.

    ATTRIBUTES:
        id: Identifier for the army.
        size: Number of units in the army.
        health: Health of the army in percent of the maximum.
        kills: How many units were killed by the army
        owner_id: Identifier for the owner of the army. Contains a player_id
        army_number:
        location_id: The identifier for the province the army is located in.
        position: Position of the army.
        last_direction: Direction of where the army is heading.
        on_sea: If the army is on sea.
        at_airfield: If the army is on airfield.
        units: LinkedList of the units that the army is made of.
        commands: LinkedList of the commands that the army has to follow.
        fight_status: Status of the army.
        battle: The battle that the army is currently in.
        attack_unit_id: The unit_id of the attacker.
        attack_position: The position of the attacker.
        next_attack_time: The time when the army will perform the next attack.
        estimated_arrival_time: The estimated arrival time of the army.
        needs_rail: If the army needs rail.
        needs_water: If the army needs water e.g if it is a ship.
        has_stealth: If the army is stealth.
        airplane: If the army is an airplane.
        pre_fight_size: The size of the before the fight.
        pre_fight_type: The type of before the fight.
        range: The range from which it can attack other armies.
        base_speed: The base speed of the army.
        spy_reveal_time: The time when the spy revealed the army.
        view_width: How far away the unit can view other armies.
        detailed_view_width: How far away the unit can view other armies.
        aggressiveness: The aggressiveness of the army.
        forced_march: If the army is in forced march or premium forced march.
        removed: If the army should be removed from the game state.
                removed is true if the game server thinks the client
                should not display the army anymore.
        terrain_type: The terrain type of the province that the army is in.
        air_parameters: The air parameters the army.
        anti_air_parameters: The anti air parameters the army.
        carriable: If the army can be stationed on an Aircraft/Helicopter carrier.
        carrier_feature: Further information about the Aircraft/Helicopter carrier.
        last_location_ids: Unknown
        end_of_unit_walk: Unknown
        hit_points: Number of hit points the army has.
        max_hit_points: Maximum number of hit_points the army has.
        missile_carrier_feature: Which types of missiles and how many missiles the army has loaded.
        entrenched: If the army is entrenched.
        next_anti_air_attack: Next time the army can perform a anti-air attack.
        last_anti_air_attack: Last time the army performed a anti-air attack.
        last_anti_air_attack_distance: Distance to the target of the last anti-air attack.
        last_damage_taken_time: The last time damage was taken.
        strength: Strength of the army.
        defence: Defence value of the army
        army_moral: The moral of the army.
        radar_signature_feature: How the army shows up on radar.
        token_feature: How the army consumes tokens on mobilization.
    """
    C = "a"
    next_attack_time: Optional[DateTimeMillisecondsInt]
    estimated_arrival_time: Optional[DateTimeMillisecondsInt]
    spy_reveal_time: Optional[DateTimeMillisecondsInt]
    last_damage_taken_time: Optional[DateTimeMillisecondsInt]

    patrol_radius: int = -1
    id: int = None
    size: int = 1
    health: float = 1.0
    kills: int = 0
    owner_id: int = None
    army_number: int = None
    location_id: int = None
    position: Point = None
    last_direction: Point = None
    on_sea: bool = False
    at_airfield: bool = False
    units: UnitList[Unit] = None


    commands: LinkedList[Command] = None
    fight_status: FightStatus = FightStatus.IDLE
    battle: Battle = None
    attack_unit_id: int = None
    attack_position: Point = None



    # I do not now any unit which needs rail but whatever
    needs_rail: bool = False
    needs_water: bool = False
    has_stealth: bool = False
    airplane: bool = False

    pre_fight_size: int = None
    pre_fight_type: int = None

    range: int = ARMY_CLOSE_COMBAT_RANGE
    base_speed: float = None


    view_width: int = None
    detailed_view_width: int = None
    aggressiveness: Aggressiveness = Aggressiveness.DEFAULT
    forced_march: ForcedMarch = ForcedMarch.DEACTIVE
    removed: bool = False
    terrain_type: TerrainType = None
    terrain_type_str: TerrainTypeStr = None

    air_parameters: AirParameters = None
    anti_air_parameters: AntiAirParameters = None

    carriable: bool = False
    carrier_feature: CarrierFeature = None

    last_location_ids: list[int] = None
    end_of_unit_walk: bool = False

    hit_points: float = None
    max_hit_points: int = None

    missile_carrier_feature: MissileCarrierFeature = None
    entrenched: bool = False

    next_anti_air_attack: int = None
    last_anti_air_attack: int = None
    last_anti_air_attack_distance: float = None
    strength: float = None

    defence: float = None
    army_moral: float = None

    radar_signature_feature: RadarSignatureFeature = None
    token_feature: TokenFeature = None

    MAPPING = {
        "id": "id",
        "size": "s",
        "health": "h",
        "kills": "k",
        "owner_id": "o",
        "army_number": "an",
        "location_id": "l",
        "position": "p",
        "last_direction": "ld",
        "on_sea": "os",
        "at_airfield": "aa",
        "units": "u",
        "commands": "c",
        "fight_status": "fs",
        "battle": "b",
        "attack_unit_id": "au",
        "attack_position": "ap",
        "next_attack_time": "na",
        "estimated_arrival_time": "at",
        "needs_rail": "nr",
        "needs_water": "nw",
        "has_stealth": "hs",
        "airplane": "a",
        "pre_fight_size": "ps",
        "pre_fight_type": "pt",
        "range": "r",
        "base_speed": "bs",
        "spy_reveal_time": "st",
        "view_width": "vw",
        "detailed_view_width": "dvw",
        "aggressiveness": "ag",
        "forced_march": "fm",
        "removed": "rm",
        "terrain_type_str": "terrainType",
        "terrain_type": "tt", # TODO confirm this is a terrain type (another similar exists)
        "air_parameters": "aip",
        "anti_air_parameters": "aap",
        "carriable": "ca",
        "carrier_feature": "cf",
        "last_location_ids": "ll",
        "end_of_unit_walk": "uw",
        "hit_points": "hp",
        "max_hit_points": "mhp",
        "missile_carrier_feature": "mc",
        "entrenched": "en",
        "next_anti_air_attack": "naa",
        "last_anti_air_attack": "laa",
        "last_anti_air_attack_distance": "laadist",
        "last_damage_taken_time": "ldt",
        "strength": "str",
        "defence": "def",
        "army_moral": "m",
        "radar_signature_feature": "rs",
        "token_feature": "tok",
        "patrol_radius": "patrolRadius"
    }

    def find_path(self, position: Point) -> [Command]:
        # Find Path for an army in the current game to a position
        raise NotImplementedError

    def find_path_to_province(self, province_id: int) -> [Command]:
        # Find path for an army in the current game to a province
        raise NotImplementedError

    def command_army(self, command: list[Command]):
        raise NotImplementedError