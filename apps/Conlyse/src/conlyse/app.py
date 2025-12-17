import sys

from PySide6.QtCore import QElapsedTimer
from PySide6.QtWidgets import QApplication

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
from conlyse.widgets.performance_window import PerformanceWindow

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

        self.logic_rate = self.config_manager.main.get("simulation.ups")
        self.logic_dt = 1.0 / self.logic_rate if self.logic_rate > 0 else 0.0

        self.render_rate = self.config_manager.main.get("graphics.frame_rate_limit")
        self.render_dt = 1.0 / self.render_rate if self.render_rate > 0 else 0.0

        # accumulators
        self.logic_acc = 0.0
        self.render_acc = 0.0
        self.last_time = 0

        self.clock = QElapsedTimer()
        self.clock.start()

        # Global performance window
        self.performance_window : PerformanceWindow = PerformanceWindow(self, parent=self.main_window)

    def start(self):
        # Setup pages
        self.page_manager.register_page(PageType.ReplayListPage, ReplayListPage)
        self.page_manager.register_page(PageType.ReplayLoadPage, ReplayLoadPage)
        self.page_manager.register_page(PageType.PlayerListPage, PlayerListPage)
        self.page_manager.register_page(PageType.MapPage, MapPage)

        # Setup drawer and keybindings
        self.main_window.drawer.register_entry("Replays", lambda: self.page_manager.switch_to(PageType.ReplayListPage))
        self.keybinding_manager.register_action(KeyAction.TOGGLE_DRAWER, self.main_window.toggle_drawer)
        self.keybinding_manager.register_action(KeyAction.TOGGLE_PERFORMANCE_WINDOW, self.performance_window.toggle_visibility)

        # Start with home
        self.page_manager.switch_to(PageType.ReplayListPage)
        self.page_manager.update(self.logic_dt)

        self.main_window.show()

        # --- Main loop ---
        self.run_loop()


    def run_loop(self):
        self.clock.start()
        self.last_time = self.clock.nsecsElapsed()  # store in nanoseconds
        while True:
            # Measure elapsed time since last loop
            current_time = self.clock.nsecsElapsed()
            elapsed = (current_time - self.last_time) / 1_000_000_000.0  # seconds
            self.last_time = current_time

            self.logic_acc += elapsed
            self.render_acc += elapsed

            # --- Fixed-step logic ---
            if self.logic_acc >= self.logic_dt:
                self.page_manager.update(self.logic_acc)
                self.logic_acc = 0

            # --- Rendering ---
            if self.render_rate == 0 or self.render_acc >= self.render_dt:
                # Compute interpolation fraction for smooth rendering
                self.page_manager.render(self.render_acc)
                if self.render_rate != 0:
                    self.render_acc -= self.render_dt

            # Process Qt events to keep UI responsive
            self.q_app.processEvents()
            if not self.main_window.isVisible():
                break