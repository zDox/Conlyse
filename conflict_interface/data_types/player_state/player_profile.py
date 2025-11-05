from typing import Optional

from conflict_interface.data_types.game_object import GameObject

from dataclasses import dataclass

from conflict_interface.data_types.player_state.faction import Faction
from conflict_interface.data_types.point import Point

LAST_LOGIN_INACTIVE = 0
GUEST_PLAYER_ID = 0

@dataclass
class PlayerProfile(GameObject):
    C = "ultshared.UltPlayerProfile"

    player_id: int
    team_id: int
    name: str
    gender: int
    nationality: int
    capital_id: int
    title: str
    nation_name: str
    nation_adjective: str
    average_national_morale: int
    computer_player: bool
    native_computer: bool
    site_user_id: int
    user_name: Optional[str]
    defeated: bool
    retired: bool
    achievement_title_id: int
    passive_ai: bool
    default_nation_name: Optional[str] # TODO check why not playing ai does not have this
    playing: bool
    taken: bool
    faction: Faction
    available: bool
    receive_rewards: bool
    kickable_from_coalition: bool
    nation_label_size: float
    nation_label_coord: Optional[Point]
    primary_color: str # TODO implement Color
    secondary_color: str # TODO implement Color
    premium_build_slot: Optional[bool]
    premium_production_slot: Optional[bool]
    premium_user: Optional[bool]
    activity_state: Optional[str] # TODO make enum ex. "ACTIVE"
    ai_profile: Optional[str] # TODO make enum ex. "major"
    accumulated_victory_points: int
    daily_victory_points: int
    terrorist_country: bool

    banned: bool = False
    mail: str = ""
    full_title: str = ""
    victory_points: int = 0
    player_image_id: int = -1
    flag_image_id: int = -1
    noob_bonus: int = 0


    MAPPING = {
        "player_id": "playerID",
        "team_id": "teamID",
        "name": "name",
        "gender": "gender",
        "victory_points": "vps",
        "nationality": "nationality",
        "capital_id": "capitalID",
        "title": "title",
        "nation_name": "nationName",
        "nation_adjective": "nationAdjective",
        "average_national_morale": "averageNationalMorale",
        "computer_player": "computerPlayer",
        "native_computer": "nativeComputer",
        "site_user_id": "siteUserID",
        "user_name": "userName",
        "defeated": "defeated",
        "retired": "retired",
        "achievement_title_id": "achievementTitleID",
        "passive_ai": "passiveAI",
        "default_nation_name": "defaultNationName",
        "playing": "playing",
        "taken": "taken",
        "faction": "faction",
        "available": "available",
        "receive_rewards": "receiveRewards",
        "kickable_from_coalition": "kickableFromCoalition",
        "nation_label_size": "nationLabelSize",
        "nation_label_coord": "nationLabelCoord",
        "primary_color": "primaryColor",
        "secondary_color": "secondaryColor",
        "player_image_id": "playerImageID",
        "flag_image_id": "flagImageID",
        "premium_build_slot": "premiumBuildSlot",
        "premium_production_slot": "premiumProductionSlot",
        "banned": "banned",
        "premium_user": "premiumUser",
        "noob_bonus": "noobBonus",
        "activity_state": "activityState",
        "ai_profile": "aiProfile",
        "accumulated_victory_points": "accumulatedVps",
        "daily_victory_points": "dailyVictoryPoints",
        "terrorist_country": "terroristCountry",
    }