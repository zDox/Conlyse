from datetime import timedelta
from typing import Union

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.game_object import GameObject

from dataclasses import dataclass

from conflict_interface.data_types.state import State


@dataclass
class GameFeatures(GameObject):
    C = "ultshared.gamefeatures.UltGameFeatures"
    """
    Represents a collection of game features mapped by their identifiers.
    """
    id_features: HashMap[int, dict[str, Union[str, int ,bool]]]

    MAPPING = {
        "id_features": "idFeatures",
    }

@dataclass
class GameInfoState(State):
    """
    Represents the state of a game with detailed information about the game.

    The GameInfoState encapsulates all the critical information and parameters
    pertaining to the state of a game. It provides attributes for tracking game
    progress, features, and settings, including game scores, timings, and conditions.
    The class is specifically designed to assist in managing game state data and its
    mapping for various operations.

    Attributes:
        STATE_TYPE (int): Identifier for the current state of the game.
        day_of_game: Current day within the game.
        start_of_game: Starting date and time of the game.
        next_day_time: Date and time when the next game day begins.
        next_heal_time: Date and time when the next healing event occurs.
        gold_round: Indicates whether the game is a gold round.
        demo_game: Indicates if the game is a demo version.
        password: Access password for securing the game.
        open_slots: Number of open player slots remaining in the game.
        team_settings: Configuration for game teams.
        country_selection: Configuration for country selection.
        number_of_teams: Total number of teams in the game.
        number_of_players: Total number of players in the game.
        number_of_logins: Number of logins registered in the game.
        scenario_id: Identifier for the game scenario being played.
        map_id: Identifier of the map used in the game.
        alliance_game: Indicates if the game is based on alliances.
        alliance_a: Information about alliance A.
        alliance_b: Information about alliance B.
        ai_level: AI difficulty level used in the game.
        ranked: Indicates if the game is a ranked game.
        game_features: Features and settings specific to the game.
        time_scale: Scaling factor for in-game time progression.
        economy_score: Economy score achieved in the game.
        economy_boost_score: Boosted economy score during the game.
        military_score: Military performance score in the game.
        military_boost_score: Boosted military score during the game.
        game_image_path: Path to the image representing the game.
        end_of_game: Date and time when the game ends.
        game_ended: Boolean indicating whether the game has ended.
        victory_points_modifier: Modifier for victory points calculation.
        coalition_victory_points_modifier: Modifier for coalition victory points.
        admin_time_forward_allowed: Boolean indicating if admin can forward time.
    """
    C = "ultshared.UltGameInfoState"
    STATE_TYPE = 12
    day_of_game: int
    start_of_game: int
    next_day_time: DateTimeMillisecondsInt
    next_heal_time: DateTimeMillisecondsInt
    gold_round: bool
    demo_game: bool
    password: str
    open_slots: int
    team_settings: int
    country_selection: int
    number_of_teams: int
    number_of_players: int
    number_of_logins: int
    scenario_id: int
    map_id: int
    alliance_game: int
    alliance_a: int
    alliance_b: int
    ai_level: int
    ranked: int
    game_features: GameFeatures
    time_scale: float
    economy_score: int
    economy_boost_score: int
    military_score: int
    military_boost_score: int
    game_image_path: str
    end_of_game: DateTimeMillisecondsInt
    game_ended: bool
    victory_points_modifier: int
    coalition_victory_points_modifier: int
    admin_time_forward_allowed: bool

    MAPPING = {
        "day_of_game": "dayOfGame",
        "start_of_game": "startOfGame",
        "next_day_time": "nextDayTime",
        "next_heal_time": "nextHealTime",
        "gold_round": "goldRound",
        "demo_game": "demoGame",
        "password": "password",
        "open_slots": "openSlots",
        "team_settings": "teamSettings",
        "country_selection": "countrySelection",
        "number_of_teams": "numberOfTeams",
        "number_of_players": "numberOfPlayers",
        "number_of_logins": "numberOfLogins",
        "scenario_id": "scenarioID",
        "map_id": "mapID",
        "alliance_game": "allianceGame",
        "alliance_a": "allianceA",
        "alliance_b": "allianceB",
        "ai_level": "aiLevel",
        "ranked": "ranked",
        "game_features": "gameFeatures",
        "time_scale": "timeScale",
        "economy_score": "ecoScore",
        "economy_boost_score": "ecoBoostScore",
        "military_score": "milScore",
        "military_boost_score": "milBoostScore",
        "game_image_path": "gameImagePath",
        "end_of_game": "endOfGame",
        "game_ended": "gameEnded",
        "victory_points_modifier": "victoryPointsMod",
        "coalition_victory_points_modifier": "coalitionVictoryPointsMod",
        "admin_time_forward_allowed": "adminTimeFwdAllowed",
    }

    def get_remaining_timedelta(self) -> timedelta:
        """
        Calculate the remaining time until the next day.

        Returns:
            timedelta: The duration representing the remaining time until the next day.
        """
        return self.next_day_time - self.game.client_time()

    def get_display_time(self) -> timedelta:
        """
        Calculates the hour, minutes and seconds that are displayed in the game.

        Returns:
            timedelta: Display time in the format of hours, minutes and seconds.
        """
        remaining_timedelta = self.get_remaining_timedelta()
        hours = 23 - remaining_timedelta.seconds // 3600
        minutes = 59 - (remaining_timedelta.seconds % 3600) // 60
        seconds = 59 - remaining_timedelta.seconds % 60
        return timedelta(hours=hours, minutes=minutes, seconds=seconds)

    """
    # Mock methods for `format_timer` and `format_timer_tiny`
    def format_timer(self, time, is_formatted, precision):
        # Placeholder for formatting function
        return str(time)  # Implement actual formatting logic as needed
    """