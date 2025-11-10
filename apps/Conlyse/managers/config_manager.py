import json
import os


class ConfigManager:
    def __init__(self, config_path='config.json'):
        self.config_path = config_path
        self.config = self.load_config()
        self.set_missing_defaults()  # Ensure defaults are set on initialization

    def load_config(self):
        """Load the config from file or create a default one if it doesn't exist."""
        if not os.path.exists(self.config_path):
            return self.create_default_config()

        with open(self.config_path, 'r') as f:
            return json.load(f)

    def create_default_config(self):
        """Create and save a default configuration."""
        default_config = {
            "ui": {
                "scaling_factor": 1,
                "theme": "dark"
            },
            "credentials": {
                "username": "",
                "password": "",
                "email": "",
                "proxy_url": "",
            },
            "replay_mode": {
                "replay_path": "",
            },
            "online_mode": {
                "record_replay_state": {
                    "recordings": {}
                }
            },
            "debug": {
                "time": False,
                "verbose": False,
                "style_sheet_hot_loading": False
            }
        }
        self.save_config(default_config)
        return default_config

    def save_config(self, config=None):
        """Save the current or provided config to file."""
        config = config or self.config
        with open(self.config_path, 'w') as f:
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