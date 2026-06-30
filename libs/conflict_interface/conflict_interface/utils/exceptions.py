from enum import Enum

class ActionException(Exception):
    pass

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
    USER_NOT_FOUND = -3 # Joined to many games in a short time
    GAME_NOT_FOUND = -4
    USER_EXISTED = -5
    COUNTRY_SELECTION_REQUESTED = -6
    COUNTRY_SELECTION_IMPOSSIBLE = -7
    VACATION_MODE_ACTIVE = -8
    GAME_FULL = -9
    GAME_TOO_OLD = -10
    ANTI_CHEAT_IP_CONFLICT = -11


class UnsupportedDatatypeVersionError(Exception):
    """Raised when a game state uses a datatype version not supported by this build."""

    def __init__(self, version: int, available_versions=None):
        self.version = version
        self.available_versions = sorted(available_versions) if available_versions else []
        msg = f"Unsupported datatype version {version}"
        if self.available_versions:
            msg += f". Available versions: {self.available_versions}"
        super().__init__(msg)


class MissingFullStateSnapshotError(Exception):
    """
    Raised when an incremental (AUTO_STATE_TYPE) response's datatype version
    differs from the currently-tracked game state's version, with no full
    (FULL_STATE_TYPE) snapshot in between to mark the transition.

    Incremental updates are applied via GameState.update(), which requires
    both states to be the exact same class. A datatype version change can
    only be applied safely starting from a full snapshot (see
    ReplayBuilder.append_json_responses/build_from_stream, which route a
    version change to a new replay segment only when the response is full).
    Without that snapshot, the old- and new-version state objects are
    different classes and cannot be diffed against each other.

    This almost always means the observer/publisher missed publishing the
    full game state at the moment the client's datatype version changed -
    the recording has a genuine gap, not a bug in this code path.
    """

    def __init__(self, old_version, new_version, game_id: int = None, player_id: int = None):
        self.old_version = old_version
        self.new_version = new_version
        self.game_id = game_id
        self.player_id = player_id
        ctx = f" (game_id={game_id}, player_id={player_id})" if game_id is not None else ""
        super().__init__(
            f"Datatype version changed from {old_version} to {new_version} between two "
            f"incremental updates with no full state snapshot in between{ctx}. The observer "
            f"likely missed publishing the full game state when the client updated; this "
            f"recording has a gap and cannot be incrementally patched across the transition."
        )


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
