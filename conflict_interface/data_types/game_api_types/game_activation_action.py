from dataclasses import dataclass

@dataclass
class GameActivationAction:
    C = "ultshared.action.UltActivateGameAction"
    selected_player_id: int
    selected_team_id: int
    random_team_country_selection: bool
    os: str
    device: str

    MAPPING = {
        "selected_player_id": "selectedPlayerID",
        "selected_team_id": "selectedTeamID",
        "random_team_country_selection": "randomTeamAndCountrySelection",
        "os": "os",
        "device": "device"
    }