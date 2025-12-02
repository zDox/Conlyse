from __future__ import annotations
from typing import TYPE_CHECKING
from PyQt6.QtCore import QPoint, QPropertyAnimation, Qt, QTimer, QEvent
from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QWidget, QSizePolicy
import traceback

if TYPE_CHECKING:
    from conlyse.app import App

class Drawer(QWidget):
    def __init__(self, app: App, parent=None, width=200):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(width)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        self.visible = False
        self.app = app
        self.anim = None

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        # Buttons will be inserted before this stretch; the stretch keeps them at the top
        layout.addStretch()
        self.setLayout(layout)

        # If parent exists, listen for its resize so we can match its height
        if parent is not None:
            try:
                parent.installEventFilter(self)
            except Exception:
                traceback.print_exc()

    def eventFilter(self, obj, event):
        # Update geometry when the parent widget is resized/moved
        if event.type() == QEvent.Type.Resize:
            self._update_geometry()
        return super().eventFilter(obj, event)

    def _stop_anim_if_running(self):
        if self.anim is not None:
            try:
                self.anim.stop()
            except Exception:
                # ensure we don't crash if stopping fails
                traceback.print_exc()
            self.anim = None

    def _update_geometry(self):
        """
        Ensure the drawer matches the parent's height and is positioned
        either just off-screen (-width, 0) or on-screen (0, 0) depending
        on self.visible.
        """
        parent = self.parent()
        w = self.width()
        if parent is None:
            # If there's no parent, keep current geometry height
            h = self.height()
        else:
            h = parent.height()
        try:
            if self.visible:
                self.setGeometry(0, 0, w, h)
            else:
                self.setGeometry(-w, 0, w, h)
        except Exception:
            # Geometry changes can occasionally raise on exotic platforms; ignore but log
            traceback.print_exc()

    def showEvent(self, event):
        # Ensure geometry is correct whenever the widget is shown
        self._update_geometry()
        super().showEvent(event)

    def show_drawer(self):
        if self.visible:
            return
        self.visible = True

        # ensure geometry is correct with parent's current height
        self._update_geometry()

        # Ensure the widget is shown and on top before animating
        self.show()
        self.raise_()

        # Stop any running animation first
        self._stop_anim_if_running()

        # Animate sliding in (pos is relative to parent because this is a child widget)
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(100)
        anim.setStartValue(QPoint(-self.width(), 0))
        anim.setEndValue(QPoint(0, 0))
        # cleanup reference when done
        anim.finished.connect(lambda: setattr(self, "anim", None))
        anim.start()
        self.anim = anim  # keep reference

    def hide_drawer(self):
        if not self.visible:
            return
        self.visible = False

        # Stop any running animation first
        self._stop_anim_if_running()

        # Ensure geometry uses current parent height (so the end position is correct)
        self._update_geometry()

        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(100)
        anim.setStartValue(QPoint(0, 0))
        anim.setEndValue(QPoint(-self.width(), 0))
        # hide the widget after the animation completes and cleanup the anim ref
        def _on_finished():
            try:
                self.hide()
            finally:
                self.anim = None
        anim.finished.connect(_on_finished)
        anim.start()
        self.anim = anim

    def toggle_drawer(self):
        if self.app.page_manager.out_replay:
            # Don't allow drawer toggling during replay playback
            return
        if self.visible:
            self.hide_drawer()
        else:
            self.show_drawer()

    def register_entry(self, name: str, callback):
        btn = QPushButton(name)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(50)
        btn.setObjectName("drawer_entry_button")
        # Run callback synchronously but schedule hide_drawer for the next event loop
        # iteration to avoid re-entrancy and nested animations causing issues.
        def _on_clicked(_=None):
            try:
                callback()
            except Exception:
                traceback.print_exc()
            # schedule hide on next loop cycle
            QTimer.singleShot(0, self.hide_drawer)

        btn.clicked.connect(_on_clicked)
        self.layout().insertWidget(self.layout().count() - 1, btn)