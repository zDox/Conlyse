from __future__ import annotations

from typing import Any
from typing import TYPE_CHECKING

from conlyse.managers.config_manager.config_file import ConfigFile

if TYPE_CHECKING:
    from conlyse.app import App

class ConfigManager:
    """Manages multiple configuration files."""

    def __init__(self, app: App):
        self.app = app

        # Initialize individual config files
        self.main = ConfigFile("main_config.json", "default_main_config", app)
        self.replays = ConfigFile("replays_data.json", "default_replays_data", app)
        self.keybindings = ConfigFile("keybindings.json", "default_keybindings", app)

        # Ensure all configs have their defaults merged
        self.merge_all_defaults()

    def merge_all_defaults(self):
        """Merge defaults for all config files."""
        self.main.merge_defaults()
        self.replays.merge_defaults()
        self.keybindings.merge_defaults()

    def save_all(self):
        """Save all config files."""
        self.main.save()
        self.replays.save()
        self.keybindings.save()

    # Convenience methods for backward compatibility
    def get(self, key: str, default=None, config_type: str = "main"):
        """Get a value from a specific config file."""
        config_map = {
            "main": self.main,
            "replays": self.replays,
            "keybindings": self.keybindings
        }
        return config_map.get(config_type, self.main).get(key, default)

    def set(self, key: str, value: Any, config_type: str = "main"):
        """Set a value in a specific config file."""
        config_map = {
            "main": self.main,
            "replays": self.replays,
            "keybindings": self.keybindings
        }
        config_map.get(config_type, self.main).set(key, value)