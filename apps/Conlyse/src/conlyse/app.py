import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from conlyse.logger import get_logger
from conlyse.main_window import MainWindow
from conlyse.managers.asset_manager import AssetManager
from conlyse.managers.config_manager.config_manager import ConfigManager
from conlyse.managers.event_manager import EventManager
from conlyse.managers.keybinding_manager.key_action import KeyAction
from conlyse.managers.keybinding_manager.keybinding_manager import KeybindingManager
from conlyse.managers.page_manager import PageManager
from conlyse.managers.replay_manager import ReplayManager
from conlyse.managers.style_manager import StyleManager
from conlyse.pages.map_page.map_page import MapPage
from conlyse.pages.player_list_page import PlayerListPage
from conlyse.pages.replay_list_page.replay_list_page import ReplayListPage
from conlyse.pages.replay_load_page import ReplayLoadPage
from conlyse.utils.enums import PageType

logger = get_logger()


class App:
    def __init__(self):
        self.q_app : QApplication = QApplication(sys.argv)
        self.main_window : MainWindow = MainWindow(self)

        self.asset_manager      = AssetManager(self)
        self.config_manager     = ConfigManager(self)
        self.keybinding_manager = KeybindingManager(self)
        self.event_handler      = EventManager(self)
        self.style_manager      = StyleManager(self)
        self.page_manager       = PageManager(self)
        self.replay_manager: ReplayManager     = ReplayManager(self)

        self.frame_timer : QTimer = QTimer()



        

    def start(self):
        logger.debug("Loading application...")
        # Register pages
        self.page_manager.register_page(PageType.ReplayListPage, ReplayListPage)
        self.page_manager.register_page(PageType.ReplayLoadPage, ReplayLoadPage)
        self.page_manager.register_page(PageType.PlayerListPage, PlayerListPage)
        self.page_manager.register_page(PageType.MapPage, MapPage)

        # Setting up drawer
        self.main_window.drawer.register_entry("Replays", lambda: self.page_manager.switch_to(PageType.ReplayListPage))
        self.keybinding_manager.register_action(KeyAction.TOGGLE_DRAWER, self.main_window.toggle_drawer)
        # Connect buttons

        # Start with home
        self.page_manager.switch_to(PageType.ReplayListPage)
        self.page_manager.update()

        # Frame update timer (~60 FPS)
        self.frame_timer.setInterval(int(1/self.config_manager.main.get("graphics.frame_rate_limit") * 1000))  # ms
        self.frame_timer.timeout.connect(self.update_frame)
        self.frame_timer.start()

        # Start the application by showing the main window
        self.main_window.show()

        sys.exit(self.q_app.exec())

    def update_frame(self):
        # Per-frame logic
        self.page_manager.update()
        # Trigger repaint if needed
        self.main_window.update()