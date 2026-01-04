from __future__ import annotations

from typing import TYPE_CHECKING
from string import Template

from conlyse.logger import get_logger
from conlyse.managers.keybinding_manager.key_action import KeyAction
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

        self.page_styles: dict[(Theme, PageType), str] = {}
        self.global_style: str = ""
        self.header_style: str = ""
        self.table_widget_style: str = ""
        self.dock_style: str = ""

        self.current_theme: Theme = Theme.LIGHT # Asset loader is not available yet
        self.themes: dict[Theme, dict] = {}
        if self.app.config_manager.get("ui.theme", Theme.LIGHT.name) == "LIGHT":
            self.current_theme = Theme.LIGHT
        else:
            self.current_theme = Theme.DARK
        self.load_themes()

        self.app.keybinding_manager.register_action(KeyAction.RELOAD_STYLES, self.reload_all_styles)
        self.app.keybinding_manager.register_action(KeyAction.TOGGLE_THEME, self.toggle_theme)

    def load_themes(self):
        self.global_style = self.app.asset_manager.load_string("global_style")
        self.header_style = self.app.asset_manager.load_string("header_style")
        self.table_widget_style = self.app.asset_manager.load_string("table_widget_style")
        self.dock_style = self.app.asset_manager.load_string("dock_style")
        self.app.asset_manager.load_json("theme_light")
        self.app.asset_manager.load_json("theme_dark")
        self.themes[Theme.LIGHT] = self.app.asset_manager.get_asset("theme_light")
        self.themes[Theme.DARK] = self.app.asset_manager.get_asset("theme_dark")

    def unload_themes(self):
        self.app.asset_manager.unload_asset("global_style")
        self.app.asset_manager.unload_asset("header_style")
        self.app.asset_manager.unload_asset("table_widget_style")
        self.app.asset_manager.unload_asset("dock_style")
        self.app.asset_manager.unload_asset("theme_light")
        self.app.asset_manager.unload_asset("theme_dark")
        self.global_style = ""
        self.header_style = ""
        self.table_widget_style = ""
        self.dock_style = ""
        del self.themes[Theme.LIGHT]
        del self.themes[Theme.DARK]

    def get_page_style(self, page_type: PageType) -> str:
        if (self.current_theme, page_type) not in self.page_styles:
            self.load_page_style(page_type)
        return self.page_styles.get((self.current_theme, page_type), "")

    def load_page_style(self, page_type: PageType):
        asset_name = camel_to_snake(page_type.name)
        style_raw = self.app.asset_manager.load_string(
            asset_name + "_style"
        )
        if style_raw is None:
            logger.error(f"Could not load style for page {page_type.name}")
            return
        try:
            page_style = DollarTemplate(style_raw).substitute(self.themes[self.current_theme])
            self.page_styles[(self.current_theme, page_type)] = page_style
        except KeyError as e:
            logger.error(f"StyleManager: Missing key({e.args}) in theme for page {page_type.name}")

    def unload_page_style(self, page_type: PageType):
        for theme in Theme:
            if (theme, page_type) in self.page_styles:
                del self.page_styles[(theme, page_type)]
        asset_name = camel_to_snake(page_type.name)
        self.app.asset_manager.unload_asset(asset_name)

    def unload_all_page_styles(self):
        for (theme, page_type) in list(self.page_styles.keys()):
            self.unload_page_style(page_type)

    def update_style(self):
        page_type = self.app.page_manager.get_current_page_type()
        global_style = ""
        header_style = ""
        table_widget_style = ""
        try:
            page_style = self.get_page_style(page_type)
        except KeyError as e:
            page_style = ""
            logger.error(f"StyleManager: Missing key({e.args}) in theme for page {page_type.name}")
        try:
            global_style = DollarTemplate(self.global_style).substitute(self.themes[self.current_theme])
        except KeyError as e:
            logger.error(f"StyleManager: Missing key({e.args}) in global style for theme {self.current_theme.name}")
        try:
            header_style = DollarTemplate(self.header_style).substitute(self.themes[self.current_theme])
        except KeyError as e:
            logger.error(f"StyleManager: Missing key({e.args}) in header style for theme {self.current_theme.name}")
        try:
            table_widget_style = DollarTemplate(self.table_widget_style).substitute(self.themes[self.current_theme])
        except KeyError as e:
            logger.error(f"StyleManager: Missing key({e.args}) in table widget style for theme {self.current_theme.name}")
        dock_style = ""
        current_page = self.app.page_manager.current_page
        if current_page and getattr(current_page, "use_dock_system", False):
            dock_style = self.dock_style or ""
        self.page_styles[(self.current_theme, page_type)] = page_style

        final_style = global_style + "\n" + header_style + "\n" + table_widget_style + "\n" + dock_style + "\n" + page_style
        self.app.q_app.setStyleSheet(final_style)

    def toggle_theme(self):
        if self.current_theme == Theme.LIGHT:
            self.current_theme = Theme.DARK
        else:
            self.current_theme = Theme.LIGHT
        self.update_style()
        self.app.config_manager.set("ui.theme", self.current_theme.name)

    def set_theme(self, theme: Theme):
        logger.debug(f"Setting theme to {theme.name}")
        self.current_theme = theme
        self.update_style()

    def get_current_theme(self) -> Theme:
        return self.current_theme

    def reload_all_styles(self):
        logger.debug(f"Reloading all styles")
        self.unload_themes()
        self.unload_all_page_styles()
        self.load_themes()
        self.update_style()

