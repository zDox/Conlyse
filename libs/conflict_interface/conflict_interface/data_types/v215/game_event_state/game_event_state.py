from dataclasses import field
from typing import Union

from ..custom_types import ArrayList
from ..custom_types import EmptyList
from ..game_event_state.game_event import *
from ..state import State
from ..update_helpers import state_update
from ..version import VERSION
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.constants import PathNode

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
        PremiumSpyCatchEvent, PremiumSpyCorruptionMissionEvent, PremiumSpySabotageMissionEvent,
        PremiumSpyDamageUpgradeEvent, PremiumSpyDecreaseMoralEvent, PremiumSpyDestroyResourceEvent,
        UpgradeDemolishedEvent,
        ArmyDisbandedEvent, UnitsExpiredEvent, NuclearImpactEvent, QuestDoneEvent,
        CoalitionMessageEvent, MissionEvent
    ]

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class GameEventState(State):
    C = "ultshared.gameevents.UltGameEventState"
    STATE_TYPE = 24
    game_events: Union[EmptyList[GameEventType],ArrayList[GameEventType]] = field(default_factory=list)

    _new_game_events: list[GameEventType] = None
    MAPPING = {
        "game_events": "gameEvents",
    }

    def update(self, other: "GameEventState", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        if other is None:
            return
        if not issubclass(type(other), GameEventState):
            raise ValueError(f"Can't update {type(self)} with {type(other)} not a game event state")
        state_update(self, other, path=path, rp=rp)

        new_game_events = []
        if getattr(other, "game_events") is not None:
            for other_game_event in other.game_events:
                if other_game_event.new:
                    new_game_events.append(other_game_event)


        if rp:
            rp.replace(path + ["game_events"], self.game_events, other.game_events)

        self.game_events = other.game_events
        self._new_game_events = new_game_events


    def get_new_game_events(self):
        return self._new_game_events