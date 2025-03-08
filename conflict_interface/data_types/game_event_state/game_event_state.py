from dataclasses import dataclass
from typing import Union

from conflict_interface.data_types.custom_types import ArrayList
from conflict_interface.data_types.game_event_state.game_event import *
from conflict_interface.data_types.state import State

GameEventType = Union[
        ProvinceEnteredEvent, ProvinceLostEvent, NewspaperArticleEvent,
        ArmyDestroyedEvent, ArmyDamageDealtEvent, MilitaryExperienceGainedEvent,
        ArmyAttackedEvent, AirCrashEvent,  MessageReceivedEvent, ProvinceWonEvent,
        RelationChangeEvent, ResourceShortageEvent, SpyInfoEvent,
        TradeOfferEvent, TradeProcessedEvent, UnitProducedEvent, UnitTrainedEvent,
        UnitTrainedEvent, UpgradeBuiltEvent, WarDeclaredEvent, ResearchCompletedEvent,
        ResourcesLootedEvent, ResourcesLostEvent, ArmyDamageReceivedEvent,
        ProvinceDamageReceivedEvent, OwnAllianceMembershipEvent, OtherAllianceMembershipEvent,
        MissileMissedTargetEvent, PatrolCancelledEvent, AircraftRebaseEvent,
        PremiumSpyCatchEvent, PremiumSpyCorruptionMissionEvent, PremiumSpyDamageUpgradeEvent,
        PremiumSpyDecreaseMoralEvent, PremiumSpyDestroyResourceEvent, UpgradeDemolishedEvent,
        ArmyDisbandedEvent, UnitsExpiredEvent, NuclearImpactEvent, QuestDoneEvent,
        CoalitionMessageEvent, MissionEvent
    ]

@dataclass
class GameEventState(State):
    C = "ultshared.gameevents.UltGameEventState"
    STATE_TYPE = 24
    game_events: ArrayList[GameEventType]
    MAPPING = {
        "game_events": "gameEvents",
    }