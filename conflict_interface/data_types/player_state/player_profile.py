from typing import Optional

from conflict_interface.data_types.custom_types import DefaultEnumMeta
from conflict_interface.data_types.game_object import GameObject

from dataclasses import dataclass
from enum import Enum




LAST_LOGIN_INACTIVE = 0
GUEST_PLAYER_ID = 0


class Faction(Enum, metaclass=DefaultEnumMeta):
    NONE = 0
    WESTERN = 1
    EASTERN = 2
    EUROPEAN = 3


"""
Not implemented function (graphics)
getPlayerImageID
getPlayerImageURL
getNameLinked
getNameBanned
getFlagImageID
getFlagImageURL
getCoaFlagImageURL
getBigFlagImageURL
getUserNameLinked
getUserNameBanned
getCowHouseNameLinked
getCowHouseName
getNationNameLinked
getNationAdjective
getPrimaryColor
getAlphaFixedPrimaryColor
getPlayerImage
loadPlayerImage
getPlayerImageTag
getFlagImage
getFlagImageTag
isMessagingAvailable
isTradeAvailable
isBigAIPlayer
isSmallAIPlayer
getPlayerIconImageURL
getPlayerIconImage
getLastLoginAsFormattedDate
isCurrentPlayer
getNationLabelCoord
getNationLabelSize
"""


@dataclass
class PlayerProfile(GameObject):
    C = "ultshared.UltPlayerProfile"
    player_id: int
    team_id: int
    name: str
    gender: int
    victory_points: int
    nationality: int
    capital_id: int
    title: str
    nation_name: str
    nation_adjective: str
    average_national_morale: float
    computer_player: bool
    native_computer: bool
    site_user_id: int
    user_name: Optional[str]
    defeated: bool
    retired: bool
    achievement_title_id: int
    passive_ai: bool
    default_nation_name: str
    playing: bool
    taken: bool
    faction: Faction
    available: bool
    receive_rewards: bool
    kickable_from_coalition: bool
    banned: bool = False
    mail: str = ""
    full_title: str = ""

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
    }

    def get_player_id(self):
        return self.player_id

    def get_name(self):
        return self.name

    def set_name(self, new_name):
        self.name = new_name

    def get_achievement_title_id(self):
        return self.achievement_title_id

    def set_achievement_title_id(self, new_achievement_title_id):
        self.achievement_title_id = new_achievement_title_id

    def set_title(self, new_title):
        self.title = new_title

    def get_title(self):
        return self.title

    def get_full_title(self):
        return self.full_title

    def get_site_user_id(self):
        return self.site_user_id

    def get_banned(self):
        return self.banned

    def get_computer_player(self):
        return self.computer_player

    def get_mail(self):
        return self.mail

    def get_team_id(self):
        return self.team_id

    def get_team(self):
        raise NotImplementedError()

    def is_team_member(self):
        return 0 < self.team_id

    def get_user_name(self):
        return self.user_name

    def get_faction(self):
        return self.faction

    def get_retired(self):
        return self.retired

    def get_nation_name(self):
        return self.nation_name

    def getNationNameUntranslated(self):
        return self.default_nation_name.strip()

    def get_nation_adjective(self):
        return self.nation_adjective

    def get_noob_bonus(self):
        raise NotImplementedError()

    def get_noob_bonus_factor(self):
        raise NotImplementedError()

    def get_capital_id(self):
        return self.capital_id

    def is_game_creator(self):
        raise NotImplementedError()

    def is_defeated(self):
        return self.defeated

    def is_retired(self):
        return self.retired

    def is_premium_user(self):
        raise NotImplementedError()

    def get_coat_of_arms(self):
        raise NotImplementedError()

    def get_premium_end_time(self):
        raise NotImplementedError()

    def has_additional_construction_slot(self):
        raise NotImplementedError()

    def has_additional_production_slot(self):
        raise NotImplementedError()

    def is_playable_computer(self):
        return self.is_computer_player() or self.is_reopened_player() \
                or not self.is_native_computer()

    def is_taken_country(self):
        return self.taken

    def is_available_for_taking(self):
        return self.available

    def is_computer_player(self):
        return not self.is_taken_country()

    def is_reopened_player(self):
        return not self.computer_player and 0 > self.site_user_id

    def is_native_computer(self):
        return self.native_computer

    def is_passive_ai(self):
        return self.passive_ai

    def is_active_player(self):
        return self.is_considered_playing()

    def is_considered_playing(self):
        return self.playing

    def is_inactive_player(self):
        return not self.is_active_player()

    def is_abandoned_player(self):
        return self.is_taken_country() and not self.is_considered_playing()

    def is_kickable_from_coalition(self):
        return self.kickable_from_coalition

    def should_receiver_rewards(self):
        return self.receive_rewards

    def is_playable(self):
        return self.is_available_for_taking() \
            and not self.is_selectable_native_computer()

    def is_selectable_native_computer(self):
        # Not fully implemented
        return self.is_native_computer()

    def is_ai_player(self):
        return self.computer_player or self.last_login == LAST_LOGIN_INACTIVE

    def is_guest_player(self):
        return self.player_id <= GUEST_PLAYER_ID

    def get_last_login(self):
        return self.last_login or 0

    def get_victory_points(self):
        return self.victory_points
