from exceptions import UserNotFound, GameNotFound, CountrySelectionRequired, \
        CountrySelectionImpossible, GameFull, GameTooOld, AntiCheatIPConflict
from enum import Enum


class GameActivationResult(Enum):
    SUCCESS = 34
    USER_NOT_FOUND = -3
    GAME_NOT_FOUND = -4
    USER_EXISTED = -5
    COUNTRY_SELECTION_REQUESTED = -6
    COUNTRY_SELECTION_IMPOSSIBLE = -7
    VACATION_MODE_ACTIVE = -8
    GAME_FULL = -9
    GAME_TOO_OLD = -10
    ANTI_CHEAT_IP_CONFLICT = -11
    SEASON_API_FAILED = 87


def GameActivationResult_to_exception(result):
    match result:
        case GameActivationResult.USER_NOT_FOUND:
            return UserNotFound()
        case GameActivationResult.GAME_NOT_FOUND:
            return GameNotFound()
        case GameActivationResult.COUNTRY_SELECTION_REQUESTED:
            return CountrySelectionRequired()
        case GameActivationResult.COUNTRY_SELECTION_IMPOSSIBLE:
            return CountrySelectionImpossible()
        case GameActivationResult.GAME_FULL:
            return GameFull()
        case GameActivationResult.GAME_TOO_OLD:
            return GameTooOld()
        case GameActivationResult.ANTI_CHEAT_IP_CONFLICT:
            return AntiCheatIPConflict()
        case GameActivationResult.VACATION_MODE_ACTIVE:
            return ValueError("Vacation Mode is active")
