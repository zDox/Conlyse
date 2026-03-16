import sys
import time

from PySide6.QtCore import QElapsedTimer
from PySide6.QtWidgets import QApplication

from conlyse.logger import get_logger
from conlyse.api import ApiClient, ApiConfig
from conlyse.managers.auth_manager import AuthManager
from conlyse.managers.update_manager import UpdateManager
from conlyse.main_window import MainWindow
from conlyse.managers.asset_manager import AssetManager
from conlyse.managers.config_manager.config_manager import ConfigManager
from conlyse.managers.event_manager import EventManager
from conlyse.managers.keybinding_manager.key_action import KeyAction
from conlyse.managers.keybinding_manager.keybinding_manager import KeybindingManager
from conlyse.managers.page_manager import PageManager
from conlyse.managers.replay_manager import ReplayManager
from conlyse.managers.style_manager import StyleManager
from conlyse.pages.auth_page import AuthPage
from conlyse.pages.map_page.map_page import MapPage
from conlyse.pages.player_list_page import PlayerListPage
from conlyse.pages.replay_list_page.replay_list_page import ReplayListPage
from conlyse.pages.replay_load_page import ReplayLoadPage
from conlyse.pages.settings_page.settings_page import SettingsPage
from conlyse.utils.enums import PageType
from conlyse.widgets.performance_window import PerformanceWindow

logger = get_logger()


class App:
    def __init__(self):
        self.q_app : QApplication = QApplication(sys.argv)
        self.main_window : MainWindow = MainWindow(self)

        self.asset_manager      = AssetManager(self)
        self.config_manager     = ConfigManager(self)
        # API client for talking to the Conlyse backend (services/api).
        api_base_url = self.config_manager.get("api.base_url", "http://localhost:8000/api/v1")
        api_timeout = float(self.config_manager.get("api.timeout_seconds", 10))
        self.api_client        = ApiClient(ApiConfig(base_url=api_base_url, timeout_seconds=api_timeout))
        self.auth_manager      = AuthManager(self)
        self.update_manager    = UpdateManager(self)
        self.keybinding_manager = KeybindingManager(self)
        self.event_handler      = EventManager(self)
        self.style_manager      = StyleManager(self)
        self.page_manager       = PageManager(self)
        self.replay_manager: ReplayManager     = ReplayManager(self)
        self.update_simulation_rate()
        self.update_frame_rate_limit()

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
        self.page_manager.register_page(PageType.AuthPage, AuthPage)
        self.page_manager.register_page(PageType.ReplayListPage, ReplayListPage)
        self.page_manager.register_page(PageType.ReplayLoadPage, ReplayLoadPage)
        self.page_manager.register_page(PageType.PlayerListPage, PlayerListPage)
        self.page_manager.register_page(PageType.SettingsPage, SettingsPage)
        self.page_manager.register_page(PageType.MapPage, MapPage)

        # Setup drawer and keybindings
        self.main_window.drawer.register_entry("Replays", lambda: self.page_manager.switch_to(PageType.ReplayListPage))
        self.keybinding_manager.register_action(KeyAction.TOGGLE_DRAWER, self.main_window.toggle_drawer)
        self.keybinding_manager.register_action(KeyAction.TOGGLE_PERFORMANCE_WINDOW, self.performance_window.toggle_visibility)

        # Start with authentication page if not logged in; otherwise go straight to home.
        if self.auth_manager.is_authenticated:
            self.page_manager.switch_to(PageType.ReplayListPage)
        else:
            self.page_manager.switch_to(PageType.AuthPage)
        self.page_manager.update(self.logic_dt)

        self.toggle_fullscreen()
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

            # Update API/auth status indicator in the header.
            self._update_api_status_indicator()

            # Process Qt events to keep UI responsive
            self.q_app.processEvents()
            if not self.main_window.isVisible():
                break

            # Sleep until the next scheduled event to avoid busy-waiting
            if self.logic_rate > 0 and self.render_rate > 0:
                time_to_logic  = self.logic_dt  - self.logic_acc
                time_to_render = self.render_dt - self.render_acc
                sleep_time = max(0.0, min(time_to_logic, time_to_render))
                if sleep_time > 0.0:
                    time.sleep(sleep_time)
            elif self.logic_rate > 0:
                sleep_time = max(0.0, self.logic_dt - self.logic_acc)
                if sleep_time > 0.0:
                    time.sleep(sleep_time)
            elif self.render_rate > 0:
                sleep_time = max(0.0, self.render_dt - self.render_acc)
                if sleep_time > 0.0:
                    time.sleep(sleep_time)

    def _update_api_status_indicator(self):
        """Refresh the header status label based on API connectivity and auth state."""
        api = self.api_client
        auth = self.auth_manager

        if api.last_ok is False:
            status = "API: Offline"
        elif api.last_ok is True:
            status = "API: Online"
        else:
            status = "API: Unknown"

        if auth.is_authenticated and auth.current_user:
            user = auth.current_user
            tier = auth.subscription_tier or "free"
            status += f" | {user.email} ({tier})"

        self.main_window.header.set_api_status(status)

    def update_simulation_rate(self):
        self.logic_rate = self.config_manager.get("simulation.ups")
        self.logic_dt = 1.0 / self.logic_rate if self.logic_rate > 0 else 0.0
        logger.debug(f"Simulation rate updated to {self.logic_rate} UPS")

    def update_frame_rate_limit(self):
        self.render_rate = self.config_manager.get("graphics.frame_rate_limit")
        self.render_dt = 1.0 / self.render_rate if self.render_rate > 0 else 0.0
        logger.debug(f"Frame rate limit updated to {self.render_rate} FPS")

    def toggle_fullscreen(self):
        is_fullscreen = self.config_manager.get("graphics.fullscreen")
        if is_fullscreen:
            self.main_window.showFullScreen()
        else:
            self.main_window.showNormal()
        logger.debug(f"Fullscreen toggled to {is_fullscreen}")
