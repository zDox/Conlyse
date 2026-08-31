from dataclasses import dataclass
from typing import Optional

from conflict_interface.game_object.game_object import GameObject
from ..army_state.army import Army
from ..custom_types import ArraysArrayList
from ..custom_types import DateTimeMillisecondsInt
from ..game_event_state.sender import Sender
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from ..mod_state.moddable_upgrade import ModableUpgrade

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class GameEvent(GameObject):
    filter_id: int
    sender_id: int
    produce_push_notification: bool
    output_format: str

    time: DateTimeMillisecondsInt
    event_id: int
    read: bool

    name: str
    key: str

    senders: ArraysArrayList[Sender]
    filter_name: str
    new: bool
    description: str

    notification_type: Optional[str] # TODO could be enum

    MAPPING = {
        "filter_id": "filterID",
        "sender_id": "senderID",
        "produce_push_notification": "producePushNotification",
        "output_format": "outputFormat",
        "time": "time",
        "event_id": "eventID",
        "read": "read",
        "name": "name",
        "key": "key",
        "senders": "senders",
        "filter_name": "filterName",
        "new": "new",
        "description": "description",
        "notification_type": "notificationType",
    }

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ProvinceLostEvent(GameEvent):
    C = "ultshared.gameevents.UltProvinceLostGameEvent"
    province_id: int
    capital: bool

    MAPPING = {
        "province_id": "provinceID",
        "capital": "capital",
    }

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ProvinceEnteredEvent(GameEvent):
    C = "ultshared.gameevents.UltProvinceEnteredGameEvent"
    entering_army: Army
    province_id: int

    MAPPING = {
        "entering_army": "enteringArmy",
        "province_id": "provinceID",
    }

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ArmyDamageDealtEvent(GameEvent):
    C = "ultshared.gameevents.UltArmyDamageDealtGameEvent"
    attacking_army_name: str
    defending_army_name: str
    attacking_army_id: int
    defending_army_id: int

    location_id: int

    MAPPING = {
        "attacking_army_name": "attackingArmyName",
        "defending_army_name": "defendingArmyName",
        "attacking_army_id": "attackingArmyID",
        "defending_army_id": "defendingArmyID",
        "location_id": "locationID",
    }

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class MilitaryExperienceGainedEvent(GameEvent):
    C = "ultshared.gameevents.UltMilitaryExperienceGainedGameEvent"
    xp: int
    unit_type_id: int
    amount: int
    location_id: int


    MAPPING = {
        "xp": "xp",
        "unit_type_id": "unitTypeID",
        "amount": "amount",
        "location_id": "locationID",
    }

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ArmyDestroyedEvent(GameEvent):
    C = "ultshared.gameevents.UltArmyDestroyedGameEvent"
    win: bool
    enemy_army_name: str
    army_id: int
    enemy_army_id: int
    army_name: str
    location_id: int

    MAPPING = {
        "win": "win",
        "enemy_army_name": "enemyArmyName",
        "army_id": "armyID",
        "enemy_army_id": "enemyArmyID",
        "army_name": "armyName",
        "location_id": "locationID",
    }

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class NewspaperArticleEvent(GameEvent):
    C = "ultshared.gameevents.UltNewspaperArticleGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ArmyAttackedEvent(GameEvent):
    C = "ultshared.gameevents.UltArmyAttackedGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class AirCrashEvent(GameEvent):
    C = "ultshared.gameevents.UltAirCrashGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class MessageReceivedEvent(GameEvent):
    C = "ultshared.gameevents.UltMessageReceivedGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ProvinceWonEvent(GameEvent):
    C = "ultshared.gameevents.UltProvinceWonGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class RelationChangeEvent(GameEvent):
    C = "ultshared.gameevents.UltRelationChangeGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ResourceShortageEvent(GameEvent):
    C = "ultshared.gameevents.UltResourceShortageGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class SpyInfoEvent(GameEvent):
    C = "ultshared.gameevents.UltSpyInfoGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class TradeOfferEvent(GameEvent):
    C = "ultshared.gameevents.UltTradeOfferGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class TradeProcessedEvent(GameEvent):
    C = "ultshared.gameevents.UltTradeProcessedGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class UnitProducedEvent(GameEvent):
    C = "ultshared.gameevents.UltUnitProducedGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class UnitTrainedEvent(GameEvent):
    C = "ultshared.gameevents.UltUnitTrainedGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class UpgradeBuiltEvent(GameEvent):
    C = "ultshared.gameevents.UltUpgradeBuiltGameEvent"
    upgrade: Optional[ModableUpgrade]
    location_id: Optional[int]

    MAPPING = {
        "location_id": "locationID",
        "upgrade": "upgrade",
    }

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class WarDeclaredEvent(GameEvent):
    C = "ultshared.gameevents.UltWarDeclaredGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ResearchCompletedEvent(GameEvent):
    C = "ultshared.gameevents.UltResearchCompletedGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ResourcesLootedEvent(GameEvent):
    C = "ultshared.gameevents.UltResourcesLootedGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ResourcesLostEvent(GameEvent):
    C = "ultshared.gameevents.UltResourcesLostGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ArmyDamageReceivedEvent(GameEvent):
    C = "ultshared.gameevents.UltArmyDamageReceivedGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ProvinceDamageReceivedEvent(GameEvent):
    C = "ultshared.gameevents.UltProvinceDamageReceivedGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class OwnAllianceMembershipEvent(GameEvent):
    C = "ultshared.gameevents.UltOwnAllianceMembershipEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class OtherAllianceMembershipEvent(GameEvent):
    C = "ultshared.gameevents.UltOtherAllianceMembershipEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class MissileMissedTargetEvent(GameEvent):
    C = "ultshared.gameevents.UltMissileMissedTargetGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class PatrolCancelledEvent(GameEvent):
    C = "ultshared.gameevents.UltPatrolCancelledGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class AircraftRebaseEvent(GameEvent):
    C = "ultshared.gameevents.UltAircraftRebaseGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class PremiumSpyCatchEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyCatchGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class PremiumSpyCorruptionMissionEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyCorruptionMissionGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class PremiumSpySabotageMissionEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpySabotageMissionGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class PremiumSpyDamageUpgradeEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyDamageUpgradeGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class PremiumSpyDecreaseMoralEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyDecreaseMoralGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class PremiumSpyDestroyResourceEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyDestroyResourceGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class UpgradeDemolishedEvent(GameEvent):
    C = "ultshared.gameevents.UltUpgradeDemolishedGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ArmyDisbandedEvent(GameEvent):
    C = "ultshared.gameevents.UltArmyDisbandedGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class UnitsExpiredEvent(GameEvent):
    C = "ultshared.gameevents.UltUnitsExpiredGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class NuclearImpactEvent(GameEvent):
    C = "ultshared.gameevents.UltNuclearImpactGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class QuestDoneEvent(GameEvent):
    C = "ultshared.gameevents.UltQuestDoneGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class CoalitionMessageEvent(GameEvent):
    C = "ultshared.gameevents.UltCoalitionMessageGameEvent"
    MAPPING = {}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class MissionEvent(GameEvent):
    C = "ultshared.gameevents.UltMissionGameEvent"
    MAPPING = {}

