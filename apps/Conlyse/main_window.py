from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QStackedWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.stacked_widget = QStackedWidget() # Holds the Pages but only shows one at a time
        self.setCentralWidget(self.stacked_widget) # Set the stacked widget as the central widget of the main window
