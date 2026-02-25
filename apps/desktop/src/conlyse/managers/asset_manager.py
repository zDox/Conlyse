from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import qtawesome as qta
from PySide6.QtGui import QAction
from PySide6.QtGui import QIcon
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QPushButton

from conlyse.logger import get_logger

if TYPE_CHECKING:
    from conlyse.app import App

ASSETS_PATH = Path("assets/")

ASSET_NAME_TO_PATH = {
    # Default Configs
    "default_main_config": Path("default_main_config.json"),
    "default_keybindings" : Path("default_keybindings.json"),
    "default_replays_data": Path("default_replays_data.json"),

    # Styles
    "global_style": Path("styles/global_style.qss"),
    "header_style": Path("styles/header.qss"),
    "table_widget_style": Path("styles/table_widget.qss"),
    "dock_style": Path("styles/dock_system.qss"),
    "theme_light": Path("styles/theme_light.json"),
    "theme_dark": Path("styles/theme_dark.json"),

    # Page Styles
    "replay_list_page_style": Path("styles/pages/replay_list_page.qss"),
    "replay_load_page_style": Path("styles/pages/replay_load_page.qss"),
    "player_list_page_style": Path("styles/pages/player_list_page.qss"),
    "map_page_style": Path("styles/pages/map_page.qss"),
    "settings_page_style": Path("styles/pages/settings_page.qss"),
}

logger = get_logger()

def asset_loading_function(func):
    def wrapper(self, asset_name: str):
        path = ASSETS_PATH/ASSET_NAME_TO_PATH.get(asset_name, None)
        if path is None:
            logger.error(f"Asset name '{asset_name}' not found in ASSET_NAME_TO_PATH mapping.")
            return None
        if not path.exists():
            logger.error(f"Asset file not found: {path}")
            return None
        return func(self, asset_name, path)
    return wrapper

class AssetManager:
    def __init__(self, app: App):
        self.app = app
        self.assets = {}

    @asset_loading_function
    def load_string(self, asset_name: str, path: Path):
        with open(path, 'r', encoding='utf-8') as f:
            self.assets[asset_name] = f.read()
            return self.assets[asset_name]

    @asset_loading_function
    def load_json(self, asset_name: str, path: Path):
        with open(path, 'r', encoding='utf-8') as f:
            self.assets[asset_name] = json.load(f)
            return self.assets[asset_name]

    def get_asset(self, asset_name: str):
        return self.assets.get(asset_name, None)

    def is_loaded_asset(self, asset_name: str):
        return asset_name in self.assets

    def unload_asset(self, asset_name: str):
        if asset_name in self.assets:
            del self.assets[asset_name]

    @staticmethod
    def get_icon(name: str, color: str = '#E0E0E0', prefix: str = 'fa5s') -> QIcon:
        """
        Get any Font Awesome icon by name.

        Args:
            name: Icon name (e.g., 'save', 'folder', 'user')
            color: Hex color string (default: '#E0E0E0')
            prefix: Font Awesome prefix (default: 'fa5s' for solid icons)
                   Options: 'fa5s' (solid), 'fa5' (regular), 'fa5b' (brands)

        Returns:
            QIcon object

        Example:
            icon = IconManager.get('save')
            icon = IconManager.get('trash', color='#EF5350')
            icon = IconManager.get('star', prefix='fa5')
        """
        # Build icon code
        icon_code = f"{prefix}.{name.replace('_', '-')}"

        # Create icon
        try:
            return qta.icon(icon_code, color=color)
        except Exception as e:
            logger.warning(f"Icon '{name}' with prefix '{prefix}' not found: {e}")
            # Return a fallback circle icon
            return qta.icon('fa5s.circle', color=color)

    @staticmethod
    def get_icon_pixmap(name: str, size: int = 16, color: str = '#E0E0E0', prefix: str = 'fa5s') -> QPixmap:
        """
        Get an icon as a QPixmap.

        Args:
            name: Icon name
            size: Pixel size
            color: Hex color
            prefix: Font Awesome prefix

        Returns:
            QPixmap object

        Example:
            pixmap = IconManager.get_pixmap('check', size=24, color='#4CAF50')
        """
        icon = AssetManager.get_icon(name, color, prefix)
        return icon.pixmap(size, size)

    @staticmethod
    def set_button_icon(button: QPushButton, icon_name: str, color: str = '#E0E0E0', prefix: str = 'fa5s'):
        """
        Set icon on a QPushButton.
        Example:
            IconManager.set_button_icon(my_button, 'save', '#1976D2')
        """
        button.setIcon(AssetManager.get_icon(icon_name, color, prefix))

    @staticmethod
    def set_action_icon(action: QAction, icon_name: str, color: str = '#E0E0E0', prefix: str = 'fa5s'):
        """
        Set icon on a QAction.

        Example:
            IconManager.set_action_icon(save_action, 'save', '#1976D2')
        """
        action.setIcon(AssetManager.get_icon(icon_name, color, prefix))

    @staticmethod
    def set_label_icon(label: QLabel, icon_name: str, size: int = 16, color: str = '#E0E0E0', prefix: str = 'fa5s'):
        """
        Set icon on a QLabel as pixmap.

        Example:
            IconManager.set_label_icon(status_label, 'check-circle', size=24, color='#4CAF50')
        """
        pixmap = AssetManager.get_icon_pixmap(icon_name, size, color, prefix)
        label.setPixmap(pixmap)
