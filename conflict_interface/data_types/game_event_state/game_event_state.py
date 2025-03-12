from typing import Union
from typing import get_type_hints
from typing import override

from conflict_interface.data_types.custom_types import ArrayList
from conflict_interface.data_types.game_event_state.game_event import *
from conflict_interface.data_types.state import State
from conflict_interface.utils.helper import safe_issubclass

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

    _new_game_events: list[GameEventType] = None
    MAPPING = {
        "game_events": "gameEvents",
    }

    @override
    def update(self, other):
        if other is None:
            return
        if not issubclass(type(other), GameEventState):
            raise ValueError(f"Can't update {type(self)} with {type(other)} not a game event state")

        new_game_events = []
        if getattr(other, "game_events") is not None:
            for other_game_event in other.game_events:
                if other_game_event.new:
                    new_game_events.append(other_game_event)

        self.game_events = other.game_events
        self._new_game_events = new_game_events

        self.game.game_event_handler(self.game)

    def get_new_game_events(self):
        return self._new_game_events