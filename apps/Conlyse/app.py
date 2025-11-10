import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QMainWindow

from event_handler import EventHandler
from logger import get_logger
from main_window import MainWindow
from page_manager import PageManager
from page_type import PageType
from pages.replay_list_page_test import ReplayListPage

logger = get_logger()


class App:
    def __init__(self):
        self.event_handler = EventHandler()
        self.q_app = None
        self.q_window = None
        self.page_manager = None
        

    def start(self):
        logger.debug("Loading application...")
        self.q_app = QApplication(sys.argv)

        # Set application font
        font = QFont("Roboto", 10)
        self.q_app.setFont(font)

        self.q_window = MainWindow()

        # Initialize StateManager
        self.page_manager = PageManager(self)

        # Register pages
        self.page_manager.register_page(PageType.ReplayListPage, ReplayListPage)

        # Connect buttons

        # Start with home
        self.page_manager.switch_to(PageType.ReplayListPage)

        # Start the application by showing the main window
        self.q_window.show()

        sys.exit(self.q_app.exec())



if __name__ == "__main__":
    app = App()
    app.start()