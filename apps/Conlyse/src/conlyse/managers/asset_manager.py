from __future__ import annotations
from typing import TYPE_CHECKING

import qtawesome as qta
from PyQt6.QtGui import QAction
from PyQt6.QtGui import QIcon
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QPushButton

from conlyse.logger import get_logger

if TYPE_CHECKING:
    from conlyse.app import App

ASSETS_PATH = "../assets/"

logger = get_logger()

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