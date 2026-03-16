# conlyse/pages/replay_list/replay_list_panel.py
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QListWidget
from PySide6.QtWidgets import QListWidgetItem
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget

from conlyse.pages.replay_list_page.replay_list_item import ReplayListItem
from conlyse.widgets.mui.button import CButton

if TYPE_CHECKING:
    from typing import Callable


class ReplayListPanel(QWidget):
    """Panel for displaying the list of replays"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # Callbacks
        self.on_open_callback: Callable | None = None
        self.on_selection_changed_callback: Callable | None = None

        # UI Components
        self.list_title_label = None
        self.badge_label = None
        self.open_replay_btn = None
        self.list_separator = None
        self.replay_list = None

        self.setup_ui()

    def setup_ui(self):
        """Setup the replay list panel UI"""
        self.setObjectName("replay_list_card")
        self.setMinimumWidth(380)
        self.setMaximumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header with title, badge, and open button
        self._setup_header(layout)

        # Separator
        self.list_separator = QFrame()
        self.list_separator.setObjectName("separator")
        self.list_separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.list_separator)

        # List widget
        self.replay_list = QListWidget()
        self.replay_list.setObjectName("replay_list_widget")
        self.replay_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.replay_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.replay_list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self.replay_list)

    def _setup_header(self, parent_layout):
        """Setup the header with title, badge, and button"""
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        self.list_title_label = QLabel("Recorded Replays")
        self.list_title_label.setObjectName("replay_list_card_title")
        header_layout.addWidget(self.list_title_label)

        self.badge_label = QLabel("0")
        self.badge_label.setObjectName("replay_list_badge")
        self.badge_label.setMaximumWidth(50)
        self.badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.badge_label)

        header_layout.addStretch()

        # Open button (primary style)
        self.open_replay_btn = CButton("Open", "contained", "primary", icon_name="mdi.folder-open", parent=self)
        self.open_replay_btn.setMinimumWidth(90)
        self.open_replay_btn.clicked.connect(self._on_open_clicked)
        header_layout.addWidget(self.open_replay_btn)

        parent_layout.addLayout(header_layout)

    def set_callbacks(self, on_open=None, on_selection_changed=None):
        """Set callback functions for actions"""
        self.on_open_callback = on_open
        self.on_selection_changed_callback = on_selection_changed

    def refresh_list(self, replays):
        """Refresh the replay list with current data"""
        # Store current selection
        current_row = self.replay_list.currentRow()

        # Clear and rebuild
        self.replay_list.clear()

        for filepath, replay in replays.items():
            # Metadata is prepared by ReplayManager when the replay is added.
            replay_data = getattr(replay, "list_metadata", {}) or {}
            item = QListWidgetItem(self.replay_list)
            item.setSizeHint(QSize(340, 120))
            widget = ReplayListItem(replay_data)
            self.replay_list.setItemWidget(item, widget)
            item.setData(Qt.ItemDataRole.UserRole, replay)
            item.setData(Qt.ItemDataRole.UserRole + 1, filepath)

        # Update badge
        self.badge_label.setText(str(self.replay_list.count()))

        # Restore selection or select first item
        if self.replay_list.count() > 0:
            if 0 <= current_row < self.replay_list.count():
                self.replay_list.setCurrentRow(current_row)
            else:
                self.replay_list.setCurrentRow(0)

    def get_selected_replay(self):
        """Get the currently selected replay"""
        current = self.replay_list.currentItem()
        if current:
            return current.data(Qt.ItemDataRole.UserRole)
        return None

    def get_replay_count(self):
        """Get the number of replays in the list"""
        return self.replay_list.count()

    def _on_open_clicked(self):
        """Handle open button click"""
        if self.on_open_callback:
            self.on_open_callback()

    def _on_selection_changed(self, current):
        """Handle selection change"""
        if self.on_selection_changed_callback and current:
            replay = current.data(Qt.ItemDataRole.UserRole)
            filepath = current.data(Qt.ItemDataRole.UserRole + 1)
            self.on_selection_changed_callback(replay, filepath)

    def cleanup(self):
        """Cleanup resources"""
        try:
            self.replay_list.currentItemChanged.disconnect(self._on_selection_changed)
        except Exception:
            pass