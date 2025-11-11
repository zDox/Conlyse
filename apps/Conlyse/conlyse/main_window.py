from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QStackedWidget
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from conlyse.pages.header import Header


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.container = QWidget()
        self.main_layout = QVBoxLayout(self.container)
        self.header = Header()
        self.stacked_widget = QStackedWidget() # Holds the Pages but only shows one at a time

        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.stacked_widget)

        self.setCentralWidget(self.container)
