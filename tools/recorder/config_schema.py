"""
Configuration schema for the recorder CLI tool.
"""
from dataclasses import dataclass
from typing import List, Optional, Literal, Union


@dataclass
class BuildUpgradeAction:
    """Build upgrade action configuration."""
    type: Literal["build_upgrade"] = "build_upgrade"
    city_name: str = ""
    building_name: str = ""
    tier: int = 1


@dataclass
class CancelUpgradeAction:
    """Cancel upgrade action configuration."""
    type: Literal["cancel_upgrade"] = "cancel_upgrade"
    city_name: str = ""


@dataclass
class MobilizeUnitAction:
    """Mobilize unit action configuration."""
    type: Literal["mobilize_unit"] = "mobilize_unit"
    city_name: str = ""
    unit_name: str = ""
    tier: int = 1


@dataclass
class CancelMobilizationAction:
    """Cancel mobilization action configuration."""
    type: Literal["cancel_mobilization"] = "cancel_mobilization"
    city_name: str = ""


@dataclass
class ResearchAction:
    """Research action configuration."""
    type: Literal["research"] = "research"
    research_name: str = ""
    tier: int = 1


@dataclass
class CancelResearchAction:
    """Cancel research action configuration."""
    type: Literal["cancel_research"] = "cancel_research"


@dataclass
class SleepAction:
    """Sleep action configuration without updates."""
    type: Literal["sleep"] = "sleep"
    duration: Union[str, int, float] = 0  # Default: seconds. Use suffix for minutes (e.g., "5m")


@dataclass
class SleepWithUpdatesAction:
    """Sleep action configuration with periodic updates."""
    type: Literal["sleep_with_updates"] = "sleep_with_updates"
    duration: Union[str, int, float] = 0  # Default: seconds. Use suffix for minutes (e.g., "5m")
    update_interval: float = 10.0  # in seconds, default 10 seconds


@dataclass
class ArmyPatrolAction:
    """Army patrol action configuration."""
    type: Literal["army_patrol"] = "army_patrol"
    army_id: Optional[int] = None
    army_number: Optional[int] = None
    province_name: str = ""


@dataclass
class ArmyMoveAction:
    """Army move action configuration."""
    type: Literal["army_move"] = "army_move"
    army_id: Optional[int] = None
    army_number: Optional[int] = None
    province_name: str = ""


@dataclass
class ArmyAttackAction:
    """Army attack action configuration."""
    type: Literal["army_attack"] = "army_attack"
    army_id: Optional[int] = None
    army_number: Optional[int] = None
    province_name: str = ""


@dataclass
class ArmyCancelCommandsAction:
    """Army cancel commands action configuration."""
    type: Literal["army_cancel_commands"] = "army_cancel_commands"
    army_id: Optional[int] = None
    army_number: Optional[int] = None


# Type alias for all action types
Action = (BuildUpgradeAction | CancelUpgradeAction | MobilizeUnitAction | 
          CancelMobilizationAction | ResearchAction | CancelResearchAction |
          SleepAction | SleepWithUpdatesAction | ArmyPatrolAction | 
          ArmyMoveAction | ArmyAttackAction | ArmyCancelCommandsAction)


@dataclass
class RecorderConfig:
    """Main configuration for the recorder."""
    # Authentication
    username: str = ""
    password: str = ""
    
    # Game selection
    scenario_id: int = 0
    game_id: Optional[int] = None  # Optional: Join specific game ID instead of finding new one
    country_name: Optional[str] = None
    
    # Output settings
    output_dir: str = "./recordings"
    recording_name: Optional[str] = None
    
    # Proxy settings (optional)
    proxy_url: Optional[str] = None
    
    # Actions to perform
    actions: List[dict] = None
    
    def __post_init__(self):
        if self.actions is None:
            self.actions = []
