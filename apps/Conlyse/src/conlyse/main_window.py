from __future__ import annotations
from typing import TYPE_CHECKING
from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QVBoxLayout, QWidget
from PyQt6.QtCore import QPoint

from conlyse.widgets.drawer import Drawer
from conlyse.widgets.header import Header

if TYPE_CHECKING:
    from conlyse.app import App

class MainWindow(QMainWindow):
    def __init__(self, app: App):
        super().__init__()
        # central container - parent for layout and drawer
        self.container = QWidget(self)
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.header = Header(app, "Conlyse")
        self.stacked_widget = QStackedWidget()  # Holds the Pages but only shows one at a time

        # Create the drawer as a child of the container so its 'pos' is container-relative
        self.drawer = Drawer(app, parent=self.container, width=240)
        self.drawer.hide()  # start hidden

        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.stacked_widget)

        self.setCentralWidget(self.container)

        self.header.set_drawer_toggle_function(self.toggle_drawer)

    def toggle_drawer(self):
        self.drawer.toggle_drawer()

    def resizeEvent(self, event):
        # Keep the drawer sized to the container's height and positioned off-screen when hidden
        super().resizeEvent(event)
        w = self.drawer.width()
        h = self.container.height()
        if self.drawer.visible:
            self.drawer.setGeometry(0, 0, w, h)
        else:
            # keep it just off the left edge
            self.drawer.setGeometry(-w, 0, w, h)

    def mousePressEvent(self, event):
        # If the drawer is visible and the click is outside its rect, hide it.
        if self.drawer.visible:
            # map the global mouse position into container coordinates
            global_pt = event.globalPosition().toPoint()
            pt_in_container = self.container.mapFromGlobal(global_pt)
            if not self.drawer.geometry().contains(pt_in_container):
                self.drawer.hide_drawer()
        super().mousePressEvent(event)