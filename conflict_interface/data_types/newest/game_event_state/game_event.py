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

@conflict_serializable(SerializationCategory.DATACLASS)
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

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class ProvinceLostEvent(GameEvent):
    C = "ultshared.gameevents.UltProvinceLostGameEvent"
    province_id: int
    capital: bool

    MAPPING = {
        "province_id": "provinceID",
        "capital": "capital",
    }

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class ProvinceEnteredEvent(GameEvent):
    C = "ultshared.gameevents.UltProvinceEnteredGameEvent"
    entering_army: Army
    province_id: int

    MAPPING = {
        "entering_army": "enteringArmy",
        "province_id": "provinceID",
    }

@conflict_serializable(SerializationCategory.DATACLASS)
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

@conflict_serializable(SerializationCategory.DATACLASS)
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

@conflict_serializable(SerializationCategory.DATACLASS)
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

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class NewspaperArticleEvent(GameEvent):
    C = "ultshared.gameevents.UltNewspaperArticleGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class ArmyAttackedEvent(GameEvent):
    C = "ultshared.gameevents.UltArmyAttackedGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class AirCrashEvent(GameEvent):
    C = "ultshared.gameevents.UltAirCrashGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class MessageReceivedEvent(GameEvent):
    C = "ultshared.gameevents.UltMessageReceivedGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class ProvinceWonEvent(GameEvent):
    C = "ultshared.gameevents.UltProvinceWonGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class RelationChangeEvent(GameEvent):
    C = "ultshared.gameevents.UltRelationChangeGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class ResourceShortageEvent(GameEvent):
    C = "ultshared.gameevents.UltResourceShortageGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class SpyInfoEvent(GameEvent):
    C = "ultshared.gameevents.UltSpyInfoGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class TradeOfferEvent(GameEvent):
    C = "ultshared.gameevents.UltTradeOfferGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class TradeProcessedEvent(GameEvent):
    C = "ultshared.gameevents.UltTradeProcessedGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class UnitProducedEvent(GameEvent):
    C = "ultshared.gameevents.UltUnitProducedGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class UnitTrainedEvent(GameEvent):
    C = "ultshared.gameevents.UltUnitTrainedGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class UpgradeBuiltEvent(GameEvent):
    C = "ultshared.gameevents.UltUpgradeBuiltGameEvent"
    upgrade: Optional[ModableUpgrade]
    location_id: Optional[int]

    MAPPING = {
        "location_id": "locationID",
        "upgrade": "upgrade",
    }

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class WarDeclaredEvent(GameEvent):
    C = "ultshared.gameevents.UltWarDeclaredGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class ResearchCompletedEvent(GameEvent):
    C = "ultshared.gameevents.UltResearchCompletedGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class ResourcesLootedEvent(GameEvent):
    C = "ultshared.gameevents.UltResourcesLootedGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class ResourcesLostEvent(GameEvent):
    C = "ultshared.gameevents.UltResourcesLostGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class ArmyDamageReceivedEvent(GameEvent):
    C = "ultshared.gameevents.UltArmyDamageReceivedGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class ProvinceDamageReceivedEvent(GameEvent):
    C = "ultshared.gameevents.UltProvinceDamageReceivedGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class OwnAllianceMembershipEvent(GameEvent):
    C = "ultshared.gameevents.UltOwnAllianceMembershipEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class OtherAllianceMembershipEvent(GameEvent):
    C = "ultshared.gameevents.UltOtherAllianceMembershipEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class MissileMissedTargetEvent(GameEvent):
    C = "ultshared.gameevents.UltMissileMissedTargetGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class PatrolCancelledEvent(GameEvent):
    C = "ultshared.gameevents.UltPatrolCancelledGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class AircraftRebaseEvent(GameEvent):
    C = "ultshared.gameevents.UltAircraftRebaseGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class PremiumSpyCatchEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyCatchGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class PremiumSpyCorruptionMissionEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyCorruptionMissionGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class PremiumSpySabotageMissionEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpySabotageMissionGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class PremiumSpyDamageUpgradeEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyDamageUpgradeGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class PremiumSpyDecreaseMoralEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyDecreaseMoralGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class PremiumSpyDestroyResourceEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyDestroyResourceGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class UpgradeDemolishedEvent(GameEvent):
    C = "ultshared.gameevents.UltUpgradeDemolishedGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class ArmyDisbandedEvent(GameEvent):
    C = "ultshared.gameevents.UltArmyDisbandedGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class UnitsExpiredEvent(GameEvent):
    C = "ultshared.gameevents.UltUnitsExpiredGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class NuclearImpactEvent(GameEvent):
    C = "ultshared.gameevents.UltNuclearImpactGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class QuestDoneEvent(GameEvent):
    C = "ultshared.gameevents.UltQuestDoneGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class CoalitionMessageEvent(GameEvent):
    C = "ultshared.gameevents.UltCoalitionMessageGameEvent"
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class MissionEvent(GameEvent):
    C = "ultshared.gameevents.UltMissionGameEvent"
    MAPPING = {}

