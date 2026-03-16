from __future__ import annotations
from typing import TYPE_CHECKING

import json
import os
from typing import Any
from typing import Dict
if TYPE_CHECKING:
    from conlyse.app import App

CONFIG_DIR = "app_data"

class ConfigFile:
    """Represents a single configuration file."""

    def __init__(self, filename: str, default_config_key: str, app: App):
        self.filename = filename
        self.filepath = os.path.join(CONFIG_DIR, filename)
        self.default_config_key = default_config_key
        self.app = app
        self.data = self.load()

    def load(self) -> Dict[str, Any]:
        """Load config from file or create default if it doesn't exist."""
        if not os.path.exists(self.filepath):
            return self.create_default()

        try:
            with open(self.filepath, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If file is corrupted, recreate from defaults
            return self.create_default()

    def create_default(self) -> Dict[str, Any]:
        """Create and save a default configuration."""
        default_data = self.app.asset_manager.load_json(self.default_config_key)
        self.save(default_data)
        return default_data

    def save(self, data: Dict[str, Any] = None):
        """Save config to file."""
        data = data or self.data
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(self.filepath, 'w') as f:
            json.dump(data, f, indent=4)

    def get(self, key: str, default=None):
        """Get a value using dot notation (e.g., 'ui.scaling_factor')."""
        keys = key.split('.')
        value = self.data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
            if value == default:
                break
        return value

    def set(self, key: str, value: Any):
        """Set a value using dot notation and save."""
        keys = key.split('.')
        data = self.data
        for k in keys[:-1]:
            data = data.setdefault(k, {})
        data[keys[-1]] = value
        self.save()

    def merge_defaults(self):
        """Merge missing default keys into current config."""
        default_data = self.app.asset_manager.load_json(
            self.default_config_key
        )

        def merge(current, defaults):
            for key, default_value in defaults.items():
                if key not in current:
                    current[key] = default_value
                elif isinstance(default_value, dict) and isinstance(current[key], dict):
                    merge(current[key], default_value)
            return current

        self.data = merge(self.data, default_data)
        self.save()
