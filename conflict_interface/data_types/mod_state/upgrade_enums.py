from enum import Enum


class UpgradeFeature(Enum):
    FORTRESS = 0
    HARBOUR = 1
    RAILROAD = 2
    FACTORY = 3
    CAPITAL = 4
    MORALE_BONUS = 5
    RECRUIT = 6
    FACTORY_TECH = 7
    AIRFIELD = 8
    INDESTRUCTIBLE = 9
    PUBLIC = 10
    UNKNOWN_11 = 11  # Not known what this feature does
    CONSTRUCTION_SLOTS = 12
    PRODUCTION_SLOTS = 13
    INVISIBLE = 14
    NO_SPEED_UP = 15
    INDESTRUCTABLE = 16
    STATUS_CHANGE = 17
    REPORT_PROGRESS = 18
    VICTORY_POINTS = 19
    SIEGE_DELAY = 20
    MINIMUM_SIEGE = 21
    UNKNOWN_22 = 22  # Not known what this feature does
    RESEARCH_LIMIT_LEVEL = 23
    MAX_MANPOWER = 24
    STACKABLE = 25
    SHOW_IN_NEWSPAPER = 26
    BUILDING_PLOTS = 27
    USED_BUILDING_PLOTS = 28
    UNKNOWN_29 = 29  # Not known what this feature does
    UNKNOWN_30 = 30  # Not known what this feature does
    CAN_SPEEDUP_CONSTRUCTION = 31
    CONSTRUCTION_CLASS = 32
    UNKNOWN_33 = 33  # Not known what this feature does
    CAN_HEAL_ARMIES = 34
    UNKNOWN_35 = 35  # Not known what this feature does
    UNKNOWN_36 = 36  # Not known what this feature does
    UNKNOWN_37 = 37  # Not known what this feature does
    DEMOLISHABLE = 38
    NOT_ADDED_TO_PROVINCE = 39
    INVISIBLE_FROM_STATS = 40


class ValueFunction(Enum):
    VALUE_FUNCTION_LINEAR = 0,
    VALUE_FUNCTION_SQRT = 1,
    VALUE_FUNCTION_PANZERWARS = 2,
    VALUE_FUNCTION_STEP = 3


