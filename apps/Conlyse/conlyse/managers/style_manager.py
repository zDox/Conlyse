from __future__ import annotations

from typing import TYPE_CHECKING
from string import Template

from conlyse.logger import get_logger
from conlyse.utils.enums import PageType
from conlyse.utils.enums import Theme
from conlyse.utils.string_manipulation import camel_to_snake

if  TYPE_CHECKING:
    from conlyse.app import App

logger = get_logger()


class DollarTemplate(Template):
    delimiter = '$'

class StyleManager:
    def __init__(self, app: App):
        self.app = app

        self.styles: dict[PageType, str] = {}
        self.global_style: str = ""

        self.current_theme: Theme = Theme.LIGHT # Asset loader is not available yet
        self.themes: dict[Theme, dict] = {}

        # Load global style and themes from assets
        self.global_style = self.app.asset_manager.load_string("global_style", "styles/global_style.qss")
        if self.app.config_manager.get("ui.theme", Theme.LIGHT.name) == "LIGHT":
            self.current_theme = Theme.LIGHT
        else:
            self.current_theme = Theme.DARK

        self.app.asset_manager.load_json("theme_light", "styles/theme_light.json")
        self.app.asset_manager.load_json("theme_dark", "styles/theme_dark.json")
        self.themes[Theme.LIGHT] = self.app.asset_manager.get_asset("theme_light")
        self.themes[Theme.DARK] = self.app.asset_manager.get_asset("theme_dark")

    def update_style(self):
        logger.debug(f"Updating style to {self.current_theme}")
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
                    f"styles/{asset_name}.qss"
                )
            try:
                page_style = DollarTemplate(style_raw).substitute(self.themes[self.current_theme])
            except KeyError as e:
                page_style = ""
                logger.error(f"StyleManager: Missing key({e.args}) in theme for page {page_type.name}")

        final_style = self.global_style + "\n" + page_style
        logger.debug(f"Applying final style sheet. {final_style}")
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

    def get_current_theme(self) -> Theme:
        return self.current_theme

    def reload_all_styles(self):
        self.global_style = self.app.asset_manager.load_string("global_style", "styles/global_style.qss")
        for theme in [Theme.LIGHT, Theme.DARK]:
            asset_name = "light_theme" if theme == Theme.LIGHT else "dark_theme"
            self.app.asset_manager.load_json(asset_name, f"styles/{asset_name}.json")
            self.themes[theme] = self.app.asset_manager.get_asset(asset_name)
        self.styles.clear()
        self.update_style()

