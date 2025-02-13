from enum import Enum


class ConflictWebAPIError(Exception):
    pass


class ConflictJoinError(Exception):
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
