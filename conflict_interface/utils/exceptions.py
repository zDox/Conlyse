from enum import Enum

from conflict_interface.data_types.hub_types.hub_result_code import HubResultCode


class SessionExpired(Exception):
    pass

class AuthenticationFailed(Exception):
    pass

class RestrictedAction(Exception):
    pass

class MissingParameter(Exception):
    pass

class JoiningGameFailed(Exception):
    pass

class GameFull(Exception):
    pass

class IncorrectPassword(Exception):
    pass

class InvalidCountry(Exception):
    pass

class InvalidParameterValue(Exception):
    pass

class MaxJoinedGamesExceeded(Exception):
    pass

class TooManyMessage(Exception):
    pass

class GameJoiningFailedOldGame(Exception):
    pass

class FeatureRestrictedForUser(Exception):
    pass

class TooManyGameJoinsTooFrequently(Exception):
    pass

class NotEnoughTickets(Exception):
    pass

class AuthenticationException(Exception):
    pass

class GameJoinException(Exception):
    pass

class CountryUnselectedException(Exception):
    pass

class GameActivationErrorCodes(Enum):
    USER_NOT_FOUND = -3
    GAME_NOT_FOUND = -4
    USER_EXISTED = -5
    COUNTRY_SELECTION_REQUESTED = -6
    COUNTRY_SELECTION_IMPOSSIBLE = -7
    VACATION_MODE_ACTIVE = -8
    GAME_FULL = -9
    GAME_TOO_OLD = -10
    ANTI_CHEAT_IP_CONFLICT = -11


class GameActivationException(Exception):
    def __init__(self, error_code: GameActivationErrorCodes, message: str = None):
        super().__init__(message or error_code.name)
        self.error_code = error_code

    @classmethod
    def from_error_code(cls, error_code: int):
        # Attempt to find the corresponding Enum item
        try:
            error_enum = GameActivationErrorCodes(error_code)
        except ValueError:
            raise ValueError(f"Invalid error code: {error_code}")

        # Construct and return the exception
        return cls(error_enum)
