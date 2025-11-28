from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from conlyse.app import App

ASSETS_PATH = "assets/"


class AssetManager:
    def __init__(self, app: App):
        self.app = app
        self.assets = {}

    def load_string(self, asset_name: str, file_path: str):
        with open(ASSETS_PATH+file_path, 'r', encoding='utf-8') as f:
            self.assets[asset_name] = f.read()
            return self.assets[asset_name]

    def load_json(self, asset_name: str, file_path: str):
        import json
        with open(ASSETS_PATH+file_path, 'r', encoding='utf-8') as f:
            self.assets[asset_name] = json.load(f)
            return self.assets[asset_name]

    def get_asset(self, asset_name: str):
        return self.assets.get(asset_name, None)

    def is_loaded_asset(self, asset_name: str):
        return asset_name in self.assets

    def unload_asset(self, asset_name: str):
        if asset_name in self.assets:
            del self.assets[asset_name]