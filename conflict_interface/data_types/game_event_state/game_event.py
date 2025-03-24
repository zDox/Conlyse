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
    pass

@dataclass
class ArmyAttackedEvent(GameEvent):
    C = "ultshared.gameevents.UltArmyAttackedGameEvent"
    pass

@dataclass
class AirCrashEvent(GameEvent):
    C = "ultshared.gameevents.UltAirCrashGameEvent"
    pass

@dataclass
class MessageReceivedEvent(GameEvent):
    C = "ultshared.gameevents.UltMessageReceivedGameEvent"
    pass

@dataclass
class ProvinceWonEvent(GameEvent):
    C = "ultshared.gameevents.UltProvinceWonGameEvent"
    pass

@dataclass
class RelationChangeEvent(GameEvent):
    C = "ultshared.gameevents.UltRelationChangeGameEvent"
    pass

@dataclass
class ResourceShortageEvent(GameEvent):
    C = "ultshared.gameevents.UltResourceShortageGameEvent"
    pass

@dataclass
class SpyInfoEvent(GameEvent):
    C = "ultshared.gameevents.UltSpyInfoGameEvent"
    pass

@dataclass
class TradeOfferEvent(GameEvent):
    C = "ultshared.gameevents.UltTradeOfferGameEvent"
    pass

@dataclass
class TradeProcessedEvent(GameEvent):
    C = "ultshared.gameevents.UltTradeProcessedGameEvent"
    pass

@dataclass
class UnitProducedEvent(GameEvent):
    C = "ultshared.gameevents.UltUnitProducedGameEvent"
    pass

@dataclass
class UnitTrainedEvent(GameEvent):
    C = "ultshared.gameevents.UltUnitTrainedGameEvent"
    pass

@dataclass
class UpgradeBuiltEvent(GameEvent):
    C = "ultshared.gameevents.UltUpgradeBuiltGameEvent"
    upgrade: ModableUpgrade
    location_id: int

    MAPPING = {
        "location_id": "locationID",
        "upgrade": "upgrade",
    }

@dataclass
class WarDeclaredEvent(GameEvent):
    C = "ultshared.gameevents.UltWarDeclaredGameEvent"
    pass

@dataclass
class ResearchCompletedEvent(GameEvent):
    C = "ultshared.gameevents.UltResearchCompletedGameEvent"
    pass

@dataclass
class ResourcesLootedEvent(GameEvent):
    C = "ultshared.gameevents.UltResourcesLootedGameEvent"
    pass

@dataclass
class ResourcesLostEvent(GameEvent):
    C = "ultshared.gameevents.UltResourcesLostGameEvent"
    pass

@dataclass
class ArmyDamageReceivedEvent(GameEvent):
    C = "ultshared.gameevents.UltArmyDamageReceivedGameEvent"
    pass

@dataclass
class ProvinceDamageReceivedEvent(GameEvent):
    C = "ultshared.gameevents.UltProvinceDamageReceivedGameEvent"
    pass

@dataclass
class OwnAllianceMembershipEvent(GameEvent):
    C = "ultshared.gameevents.UltOwnAllianceMembershipEvent"
    pass

@dataclass
class OtherAllianceMembershipEvent(GameEvent):
    C = "ultshared.gameevents.UltOtherAllianceMembershipEvent"
    pass

@dataclass
class MissileMissedTargetEvent(GameEvent):
    C = "ultshared.gameevents.UltMissileMissedTargetGameEvent"
    pass

@dataclass
class PatrolCancelledEvent(GameEvent):
    C = "ultshared.gameevents.UltPatrolCancelledGameEvent"
    pass

@dataclass
class AircraftRebaseEvent(GameEvent):
    C = "ultshared.gameevents.UltAircraftRebaseGameEvent"
    pass

@dataclass
class PremiumSpyCatchEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyCatchGameEvent"
    pass

@dataclass
class PremiumSpyCorruptionMissionEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyCorruptionMissionGameEvent"
    pass

@dataclass
class PremiumSpySabotageMissionEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpySabotageMissionGameEvent"
    pass

@dataclass
class PremiumSpyDamageUpgradeEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyDamageUpgradeGameEvent"
    pass

@dataclass
class PremiumSpyDecreaseMoralEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyDecreaseMoralGameEvent"
    pass

@dataclass
class PremiumSpyDestroyResourceEvent(GameEvent):
    C = "ultshared.gameevents.UltPremiumSpyDestroyResourceGameEvent"
    pass

@dataclass
class UpgradeDemolishedEvent(GameEvent):
    C = "ultshared.gameevents.UltUpgradeDemolishedGameEvent"
    pass

@dataclass
class ArmyDisbandedEvent(GameEvent):
    C = "ultshared.gameevents.UltArmyDisbandedGameEvent"
    pass

@dataclass
class UnitsExpiredEvent(GameEvent):
    C = "ultshared.gameevents.UltUnitsExpiredGameEvent"
    pass

@dataclass
class NuclearImpactEvent(GameEvent):
    C = "ultshared.gameevents.UltNuclearImpactGameEvent"
    pass

@dataclass
class QuestDoneEvent(GameEvent):
    C = "ultshared.gameevents.UltQuestDoneGameEvent"
    pass

@dataclass
class CoalitionMessageEvent(GameEvent):
    C = "ultshared.gameevents.UltCoalitionMessageGameEvent"
    pass

@dataclass
class MissionEvent(GameEvent):
    C = "ultshared.gameevents.UltMissionGameEvent"
    pass

