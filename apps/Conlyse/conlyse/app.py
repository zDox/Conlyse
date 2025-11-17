import logging
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QMainWindow

from conlyse.managers.replay_manager import ReplayManager
from logger import setup_logger
from managers.config_manager import ConfigManager
from managers.event_manager import EventManager
from managers.style_manager import StyleManager
from managers.asset_manager import AssetManager
from logger import get_logger
from main_window import MainWindow
from managers.page_manager import PageManager
from utils.enums import PageType
from pages.replay_list_page import ReplayListPage

logger = get_logger()


class App:
    def __init__(self):
        self.q_app : QApplication = QApplication(sys.argv)
        self.q_window : MainWindow = MainWindow()

        self.asset_manager = AssetManager(self)
        self.config_manager = ConfigManager(self)
        self.event_handler : EventManager = EventManager(self)
        self.style_manager = StyleManager(self)
        self.page_manager : PageManager = PageManager(self)
        self.replay_manager : ReplayManager = ReplayManager(self)

        self.frame_timer : QTimer = QTimer()



        

    def start(self):
        logger.debug("Loading application...")
        # Register pages
        self.page_manager.register_page(PageType.ReplayListPage, ReplayListPage)

        # Connect buttons

        # Start with home
        self.page_manager.switch_to(PageType.ReplayListPage)
        self.page_manager.update()

        # Frame update timer (~60 FPS)
        self.frame_timer.setInterval(16)  # ms
        self.frame_timer.timeout.connect(self.update_frame)
        self.frame_timer.start()

        # Start the application by showing the main window
        self.q_window.show()

        sys.exit(self.q_app.exec())

    def update_frame(self):
        # Per-frame logic
        self.page_manager.update()
        # Trigger repaint if needed
        self.q_window.update()



if __name__ == "__main__":
    setup_logger(logging.DEBUG)
    app = App()
    app.start()