from enum import Enum
from enum import auto
from typing import TYPE_CHECKING
from page_type import PageType
from utils.string_manipulation import camel_to_snake

if  TYPE_CHECKING:
    from app import App

class Theme(Enum):
    LIGHT = auto()
    DARK = auto()

class StyleManager:
    def __init__(self, app: App):
        self.app = app

        self.styles: dict[PageType, str] = {}
        self.global_style: str = ""

        self.current_theme: Theme = Theme.LIGHT # Asset loader is not available yet
        self.themes: dict[Theme, dict] = {}

    def setup(self):
        self.global_style = self.app.asset_manager.load_string("global_style", "assets/styles/global_style.qss")
        if self.app.config_manager.get("ui.theme", Theme.LIGHT.name) == "LIGHT":
            self.current_theme = Theme.LIGHT
        else:
            self.current_theme = Theme.DARK

        self.app.asset_manager.load_json("light_theme", "assets/styles/light_theme.json")
        self.app.asset_manager.load_json("dark_theme", "assets/styles/dark_theme.json")
        self.themes[Theme.LIGHT] = self.app.asset_manager.get_asset("light_theme")
        self.themes[Theme.DARK] = self.app.asset_manager.get_asset("dark_theme")

    def update_style(self):
        page_type = self.app.page_manager.get_current_page_type()
        if page_type in self.styles:
            page_style = self.styles[page_type]
        else:
            asset_name = camel_to_snake(page_type.name)
            if self.app.asset_manager.is_loaded_asset(asset_name):
                style_raw = self.app.asset_manager.get_asset(asset_name)
            else:
                style_raw = self.app.asset_manager.load_string(
                    asset_name,
                    f"assets/styles/{asset_name}.qss"
                )
            page_style = style_raw.format(**self.themes[self.current_theme])

        final_style = self.global_style + "\n" + page_style
        self.app.q_app.setStyleSheet(final_style)

    def toggle_theme(self):
        if self.current_theme == Theme.LIGHT:
            self.current_theme = Theme.DARK
        else:
            self.current_theme = Theme.LIGHT
        self.update_style()

    def set_theme(self, theme: Theme):
        self.current_theme = theme
        self.update_style()


