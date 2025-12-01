from typing import List, Optional
import math

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtWidgets import QFrame
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QScrollArea
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QGridLayout

from conlyse.widgets.mui.button import CButton


class ColumnPanel(QFrame):
    """
    Integrated column selector panel that slides down from toolbar.
    Allows users to show/hide columns via checkboxes.

    Object Names for Styling:
    - ColumnPanel (QFrame)
    - column_panel_title (QLabel)
    - column_panel_scroll (QScrollArea)
    - column_panel_scroll_content (QWidget)
    - column_checkbox (QCheckBox) - each column checkbox
    - column_select_all_button (QPushButton)
    - column_deselect_all_button (QPushButton)
    - column_apply_button (QPushButton)

    Changes:
    - Checkboxes are arranged in a grid using QGridLayout to save vertical space.
    - Optional parameter `columns_per_row` lets callers control the grid width.
      If not provided, the panel computes a near-square grid based on number of columns.
    """

    # Signal emitted when column visibility changes
    columnsChanged = pyqtSignal(list)

    def __init__(
        self,
        columns: List[str],
        visible_columns: List[str],
        parent=None,
        columns_per_row: Optional[int] = None,
    ):
        """
        Initialize the column selector panel.

        Args:
            columns: List of all available column names
            visible_columns: List of currently visible column names
            parent: Parent widget
            columns_per_row: Optional number of checkbox columns per grid row.
                             If None, a near-square grid is chosen automatically.
        """
        super().__init__(parent)
        self.columns = columns
        self.visible_columns = visible_columns.copy()
        self.checkboxes = []  # List of QCheckBox widgets

        # determine columns per row (grid width)
        self.columns_per_row = (
            columns_per_row
            if columns_per_row is not None and columns_per_row >= 1
            else max(1, math.ceil(math.sqrt(len(self.columns) or 1)))
        )

        # Set object name for styling
        self.setObjectName("ColumnPanel")
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setLineWidth(2)

        self._setup_ui()

    def _setup_ui(self):
        """Build the column panel UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # ===== Title Section =====
        title_layout = QHBoxLayout()

        title_label = QLabel("Show/Hide Columns")
        title_label.setObjectName("panel_title")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        main_layout.addLayout(title_layout)

        # ===== Seperator =====
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.Shape.HLine)
        main_layout.addWidget(separator)

        # ===== Scrollable Checkboxes Section =====
        scroll = QScrollArea()
        scroll.setObjectName("column_panel_scroll")
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(300)

        scroll_content = QWidget()
        scroll_content.setObjectName("column_panel_scroll_content")

        # Use a grid layout to arrange checkboxes in rows/columns
        columns_layout = QGridLayout(scroll_content)
        columns_layout.setHorizontalSpacing(12)
        columns_layout.setVerticalSpacing(6)
        columns_layout.setContentsMargins(6, 6, 6, 6)

        # Create checkbox for each column and place in grid
        for idx, column in enumerate(self.columns):
            checkbox = QCheckBox(column)
            checkbox.setObjectName("column_checkbox")
            checkbox.setChecked(column in self.visible_columns)
            self.checkboxes.append(checkbox)

            row = idx // self.columns_per_row
            col = idx % self.columns_per_row
            # Align left so checkboxes cluster to the left in each grid cell
            columns_layout.addWidget(checkbox, row, col, alignment=Qt.AlignmentFlag.AlignLeft)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # ===== Seperator =====
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.Shape.HLine)
        main_layout.addWidget(separator)

        # ===== Action Buttons Section =====
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        # Select all button
        select_all_button = CButton("Select All", "contained", "primary")
        select_all_button.setObjectName("column_select_all_button")
        select_all_button.clicked.connect(self._select_all)
        buttons_layout.addWidget(select_all_button)

        # Deselect all button
        deselect_all_button = CButton("Deselect All", "contained", "secondary")
        deselect_all_button.setObjectName("column_deselect_all_button")
        deselect_all_button.clicked.connect(self._deselect_all)
        buttons_layout.addWidget(deselect_all_button)

        buttons_layout.addStretch()

        # Apply button
        apply_button = CButton("Apply", "contained", "success")
        apply_button.setObjectName("column_apply_button")
        apply_button.clicked.connect(self._apply_columns)
        buttons_layout.addWidget(apply_button)

        main_layout.addLayout(buttons_layout)

    def _select_all(self):
        """Check all column checkboxes."""
        for checkbox in self.checkboxes:
            checkbox.setChecked(True)

    def _deselect_all(self):
        """Uncheck all column checkboxes."""
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)

    def get_visible_columns(self) -> List[str]:
        """
        Get list of selected (visible) columns.

        Returns:
            List of column names that are checked
        """
        return [
            self.columns[i] for i, checkbox in enumerate(self.checkboxes)
            if checkbox.isChecked()
        ]

    def _apply_columns(self):
        """Apply column visibility changes and emit signal."""
        visible = self.get_visible_columns()
        # Allow empty list (no columns selected = show nothing)
        self.columnsChanged.emit(visible)