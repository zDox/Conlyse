from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QVBoxLayout, QWidget
from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QSizePolicy

from conlyse.constants import APPLICATION_NAME
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

        self.header = Header(app, APPLICATION_NAME, parent=self.container)
        self.stacked_widget = QStackedWidget(self.container)  # Holds the Pages but only shows one at a time
        self.stacked_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Create the drawer as a child of the container so its 'pos' is container-relative
        self.drawer = Drawer(app, parent=self.container, width=240)
        self.drawer.hide()  # start hidden

        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.stacked_widget)

        self.setCentralWidget(self.container)

        self.header.set_drawer_toggle_function(self.toggle_drawer)
        app.q_app.installEventFilter(self)

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

    def eventFilter(self, obj, event):
        # ATTENTION: This event filter is installed on the entire application,
        # so it will see all events for all widgets.
        # This function gets called single/multiple time/times per click!
        # It gets called for every widget that does not consume the event.
        if event.type() == QEvent.Type.MouseButtonPress:
            if self.drawer.visible:
                # map the global mouse position into container coordinates
                global_pt = event.globalPosition().toPoint()
                pt_in_container = self.container.mapFromGlobal(global_pt)
                if not self.drawer.geometry().contains(pt_in_container):
                    self.drawer.hide_drawer()
        # Pass the event on to the parent class
        return super().eventFilter(obj, event)