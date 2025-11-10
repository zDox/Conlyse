import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QMainWindow

from event_handler import EventHandler
from logger import get_logger
from main_window import MainWindow
from page_manager import PageManager

logger = get_logger()


class App:
    def __init__(self):
        self.event_handler = EventHandler()
        self.q_app = None
        self.q_window = None
        self.page_manager = PageManager()
        

    def start(self):
        logger.debug("Loading application...")
        self.q_app = QApplication(sys.argv)

        # Set application font
        font = QFont("Roboto", 10)
        self.q_app.setFont(font)

        self.q_window = MainWindow()
        self.q_window.show()

        sys.exit(self.q_app.exec())



if __name__ == "__main__":
