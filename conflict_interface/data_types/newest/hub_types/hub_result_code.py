from enum import Enum

from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from conflict_interface.data_types.version import VERSION
@conflict_serializable(SerializationCategory.ENUM, version = VERSION)
class HubResultCode(Enum):
    OK = 0
    UnknownError = -1
    EmailFormatInvalid = -11
    PasswordFormatInvalid = -13
    SessionExpired = -17
    AuthenticationFailed = -18
    RestrictedAction = -19
    MissingParameter = -20
    PaymentFailed = -22
    AllianceDoesNotExist = -23
    DuplicateEmail = -25
    GameCreationFailed = -27
    JoiningGameFailed = -28
    GameFull = -39
    NotEnoughPremiumCurrency = -40
    MismatchedPasswords = -44
    IncorrectPassword = -45
    MailAlreadyConfirmed = -46
    InvalidAllianceTag = -47
    UserInOtherAlliance = -48
    InvalidCountry = -49
    InvalidAllianceName = -50
    AllianceFull = -51
    InvalidAllianceJoinMode = -52
    AllianceLeaderMayNotLeave = -53
    AllianceJoinModeFreeNotAllowed = -54
    PlayerCountDoesNotMatchScenario = -55
    NotAvailableForLeague = -56
    UserHasNoAlliance = -57
    NonExistentAllianceSeason = -58
    NonExistentAllianceLeague = -59
    NonExistentAllianceDivision = -60
    NonExistentPendingGame = -61
    PlayerCannotBeReplaced = -62
    TooManyPlayersInLeague = -63
    OfferRequiresItem = -64
    ItemNotTradable = -65
    ItemMustBeUnlocked = -66
    NotEnoughRealFunds = -67
    NotAvailableForTitle = -68
    AchievementNotAvailable = -69
    InvalidParameterValue = -70
    AllianceTooManyOpenApplications = -71
    MaxJoinedGamesExceeded = -72
    BetaRightsNeeded = -73
    TooManyMessage = -74
    GameCreationFailedDuplicateGame = -75
    GameCreationFailedMustWait = -76
    GameCreationFailedUserLimitExceeded = -77
    GameCreationFailedScenarioLimitExceeded = -78
    GameJoiningFailedOldGame = -82
    FeatureRestrictedForUser = -83
    SeasonApiRequestFailed = -87
    TooManyGameJoinsTooFrequently = -94
    NotEnoughTickets = -96