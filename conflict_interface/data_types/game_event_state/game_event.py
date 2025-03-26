from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.army_state.army import Army
from conflict_interface.data_types.custom_types import ArraysArrayList
from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.game_event_state.sender import Sender
from conflict_interface.data_types.mod_state.moddable_upgrade import ModableUpgrade


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

@dataclass
class ProvinceLostEvent(GameEvent):
    C = "ultshared.gameevents.UltProvinceLostGameEvent"
    province_id: int
    capital: bool

    MAPPING = {
        "province_id": "provinceID",
        "capital": "capital",
    }

@dataclass
class ProvinceEnteredEvent(GameEvent):
    C = "ultshared.gameevents.UltProvinceEnteredGameEvent"
    entering_army: Army
    province_id: int

    MAPPING = {
        "entering_army": "enteringArmy",
        "province_id": "provinceID",
    }

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

@dataclass
class NewspaperArticleEvent(GameEvent):
    C = "ultshared.gameevents.UltNewspaperArticleGameEvent"
    MAPPING = {}

@dataclass
class ArmyAttackedEvent(GameEvent):
    C = "ultshared.gameevents.UltArmyAttackedGameEvent"
    MAPPING = {}

@dataclass
class AirCrashEvent(GameEvent):
    C = "ultshared.gameevents.UltAirCrashGameEvent"
    MAPPING = {}

@dataclass
class MessageReceivedEvent(GameEvent):
    C = "ultshared.gameevents.UltMessageReceivedGameEvent"
    MAPPING = {}

@dataclass
class ProvinceWonEvent(GameEvent):
    C = "ultshared.gameevents.UltProvinceWonGameEvent"
    MAPPING = {}

@dataclass
class RelationChangeEvent(GameEvent):
    C = "ultshared.gameevents.UltRelationChangeGameEvent"
    MAPPING = {}

@dataclass
class ResourceShortageEvent(GameEvent):
    C = "ultshared.gameevents.UltResourceShortageGameEvent"
    MAPPING = {}

@dataclass
class SpyInfoEvent(GameEvent):
    C = "ultshared.gameevents.UltSpyInfoGameEvent"
    MAPPING = {}

@dataclass
class TradeOfferEvent(GameEvent):
    C = "ultshared.gameevents.UltTradeOfferGameEvent"
    MAPPING = {}

@dataclass
class TradeProcessedEvent(GameEvent):
    C = "ultshared.gameevents.UltTradeProcessedGameEvent"
    MAPPING = {}

@dataclass
class UnitProducedEvent(GameEvent):
    C = "ultshared.gameevents.UltUnitProducedGameEvent"
    MAPPING = {}

@dataclass
class UnitTrainedEvent(GameEvent):
    C = "ultshared.gameevents.UltUnitTrainedGameEvent"
    MAPPING = {}

@dataclass
class UpgradeBuiltEvent(GameEvent):
    C = "ultshared.gameevents.UltUpgradeBuiltGameEvent"
    upgrade: Optional[ModableUpgrade]
    location_id: Optional[int]

    MAPPING = {
        "location_id": "locationID",
        "upgrade": "upgrade",
    }

@dataclass
class WarDeclaredEvent(GameEvent):
    C = "ultshared.gameevents.UltWarDeclaredGameEvent"
    MAPPING = {}

@dataclass
class ResearchCompletedEvent(GameEvent):
    C = "ultshared.gameevents.UltResearchCompletedGameEvent"
    MAPPING = {}

@dataclass
class ResourcesLootedEvent(GameEvent):
    C = "ultshared.gameevents.UltResourcesLootedGameEvent"
    MAPPING = {}

@dataclass
class ResourcesLostEvent(GameEvent):
    C = "ultshared.gameevents.UltResourcesLostGameEvent"
    MAPPING = {}

@dataclass
class ArmyDamageReceivedEvent(GameEvent):
    C = "ultshared.gameevents.UltArmyDamageReceivedGameEvent"
    MAPPING = {}

@dataclass
class ProvinceDamageReceivedEvent(GameEvent):
    C = "ultshared.gameevents.UltProvinceDamageReceivedGameEvent"
    MAPPING = {}

@dataclass
class OwnAllianceMembershipEvent(GameEvent):
    C = "ultshared.gameevents.UltOwnAllianceMembershipEvent"
    MAPPING = {}

@dataclass
class OtherAllianceMembershipEvent(GameEvent):
    C = "ultshared.gameevents.UltOtherAllianceMembershipEvent"
    MAPPING = {}

@dataclass
class MissileMissedTargetEvent(GameEvent):
    C = "ultshared.gameevents.UltMissileMissedTargetGameEvent"
    MAPPING = {}

@dataclass
class PatrolCancelledEvent(GameEvent):
    C = "ultshared.gameevents.UltPatrolCancelledGameEvent"
    MAPPING = {}

@dataclass
class AircraftRebaseEvent(GameEvent):
    C = "ultshared.gameevents.UltAircraftRebaseGameEvent"
    MAPPING = {}

@dataclass
class PremiumSpyCatchEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyCatchGameEvent"
    MAPPING = {}

@dataclass
class PremiumSpyCorruptionMissionEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyCorruptionMissionGameEvent"
    MAPPING = {}

@dataclass
class PremiumSpySabotageMissionEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpySabotageMissionGameEvent"
    MAPPING = {}

@dataclass
class PremiumSpyDamageUpgradeEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyDamageUpgradeGameEvent"
    MAPPING = {}

@dataclass
class PremiumSpyDecreaseMoralEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyDecreaseMoralGameEvent"
    MAPPING = {}

@dataclass
class PremiumSpyDestroyResourceEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyDestroyResourceGameEvent"
    MAPPING = {}

@dataclass
class UpgradeDemolishedEvent(GameEvent):
    C = "ultshared.gameevents.UltUpgradeDemolishedGameEvent"
    MAPPING = {}

@dataclass
class ArmyDisbandedEvent(GameEvent):
    C = "ultshared.gameevents.UltArmyDisbandedGameEvent"
    MAPPING = {}

@dataclass
class UnitsExpiredEvent(GameEvent):
    C = "ultshared.gameevents.UltUnitsExpiredGameEvent"
    MAPPING = {}

@dataclass
class NuclearImpactEvent(GameEvent):
    C = "ultshared.gameevents.UltNuclearImpactGameEvent"
    MAPPING = {}

@dataclass
class QuestDoneEvent(GameEvent):
    C = "ultshared.gameevents.UltQuestDoneGameEvent"
    MAPPING = {}

@dataclass
class CoalitionMessageEvent(GameEvent):
    C = "ultshared.gameevents.UltCoalitionMessageGameEvent"
    MAPPING = {}

@dataclass
class MissionEvent(GameEvent):
    C = "ultshared.gameevents.UltMissionGameEvent"
    MAPPING = {}

