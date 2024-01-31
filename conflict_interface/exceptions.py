class ConflictWebAPIError(Exception):
    pass


class ConflictJoinError(Exception):
    pass


class UserNotFound(Exception):
    pass


class GameNotFound(Exception):
    pass


class CountrySelectionRequired(Exception):
    pass


class CountrySelectionImpossible(Exception):
    pass


class GameFull(Exception):
    pass


class GameTooOld(Exception):
    pass


class AntiCheatIPConflict(Exception):
    pass
