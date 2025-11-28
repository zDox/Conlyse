from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from conlyse.app import App
import json
import os

CONFIG_PATH = "app_data/config.json"

class ConfigManager:
    def __init__(self, app: App):
        self.app = app
        self.config = self.load_config()
        self.set_missing_defaults()  # Ensure defaults are set on initialization

    def load_config(self):
        """Load the config from file or create a default one if it doesn't exist."""
        if not os.path.exists(CONFIG_PATH):
            return self.create_default_config()

        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)

    def create_default_config(self):
        """Create and save a default configuration."""
        default_config = self.app.asset_manager.load_json("default_config", "default_config.json")
        self.save_config(default_config)
        return default_config

    def save_config(self, config=None):
        """Save the current or provided config to file."""
        config = config or self.config
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)

    def get(self, key, default=None):
        """Get a value from the config using dot notation (e.g., 'ui.scaling_factor')."""
        keys = key.split('.')
        value = self.config
        for k in keys:
            value = value.get(k, default)
            if value == default:
                break
        return value

    def set(self, key, value):
        """Set a value in the config using dot notation and save."""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            config = config.setdefault(k, {})
        config[keys[-1]] = value
        self.save_config()

    def set_missing_defaults(self):
        """Set any missing default keys in the current config based on the default config."""
        def merge_defaults(current, defaults):
            """Recursively merge default values into the current config."""
            for key, default_value in defaults.items():
                if key not in current:
                    # If the key is missing, set it to the default value
                    current[key] = default_value
                elif isinstance(default_value, dict) and isinstance(current[key], dict):
                    # If both are dictionaries, recurse to merge nested keys
                    merge_defaults(current[key], default_value)
            return current

        # Get the default config structure
        default_config = self.create_default_config()  # Temporarily used for comparison
        # Merge missing defaults into the current config
        self.config = merge_defaults(self.config, default_config)
        self.save_config()  # Save the updated config