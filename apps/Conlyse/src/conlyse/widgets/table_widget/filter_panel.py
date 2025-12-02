from typing import Dict
from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtWidgets import QFrame
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QScrollArea
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from conlyse.widgets.mui.button import CButton


class FilterPanel(QFrame):
    """
    Integrated filter panel that slides down from toolbar.
    Allows users to add multiple filter conditions with various operators.

    Object Names for Styling:
    - FilterPanel (QFrame)
    - filter_panel_title (QLabel)
    - filter_panel_scroll (QScrollArea)
    - filter_add_button (QPushButton)
    - filter_clear_button (QPushButton)
    - filter_apply_button (QPushButton)
    - filter_row_container (QWidget) - each filter row
    - filter_column_combo (QComboBox)
    - filter_operator_combo (QComboBox)
    - filter_value_input (QLineEdit)
    - filter_delete_button (QPushButton)
    """

    # Signal emitted when filters are applied
    filtersApplied = pyqtSignal(list)

    def __init__(self, columns: List[str], parent=None):
        """
        Initialize the filter panel.

        Args:
            columns: List of column names available for filtering
            parent: Parent widget
        """
        super().__init__(parent)
        self.columns = columns
        self.filter_rows = []  # List of filter row widgets and their controls

        # Set object name for styling
        self.setObjectName("FilterPanel")
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setLineWidth(2)

        self._setup_ui()

    def _setup_ui(self):
        """Build the filter panel UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # ===== Title Section =====
        title_layout = QHBoxLayout()

        title_label = QLabel("Filters")
        title_label.setObjectName("panel_title")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        main_layout.addLayout(title_layout)

        # ===== Separator =====
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.Shape.HLine)
        main_layout.addWidget(separator)

        # ===== Scrollable Filter Rows Section =====
        scroll = QScrollArea()
        scroll.setObjectName("filter_panel_scroll")
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(300)

        scroll_content = QWidget()
        scroll_content.setObjectName("filter_panel_scroll_content")
        self.filters_layout = QVBoxLayout(scroll_content)
        self.filters_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.filters_layout.setSpacing(8)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # ===== Separator =====
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.Shape.HLine)
        main_layout.addWidget(separator)

        # ===== Action Buttons Section =====
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        # Add filter button
        add_button = CButton("Add Filter", "contained", "primary", "mdi.plus")
        add_button.setObjectName("filter_add_button")
        add_button.clicked.connect(self._add_filter_row)
        buttons_layout.addWidget(add_button)

        buttons_layout.addStretch()

        # Clear all button
        clear_button = CButton("Clear All", "contained", "secondary", "mdi.close-circle")
        clear_button.setObjectName("filter_clear_button")
        clear_button.clicked.connect(self._clear_all_filters)
        buttons_layout.addWidget(clear_button)

        # Apply button
        apply_button = CButton("Apply", "contained", "primary", "mdi.check")
        apply_button.setObjectName("filter_apply_button")
        apply_button.clicked.connect(self._apply_filters)
        buttons_layout.addWidget(apply_button)


        main_layout.addLayout(buttons_layout)

        # Add initial filter row
        self._add_filter_row()

    def _add_filter_row(self):
        """Add a new filter row with column, operator, and value controls."""
        # Container for this filter row
        row_container = QWidget()
        row_container.setObjectName("filter_row_container")
        row_layout = QHBoxLayout(row_container)
        row_layout.setContentsMargins(0, 5, 0, 5)
        row_layout.setSpacing(8)

        # Column selector
        column_label = QLabel("Column:")
        column_combo = QComboBox()
        column_combo.setObjectName("filter_column_combo")
        column_combo.addItems(self.columns)
        column_combo.setMinimumWidth(150)

        # Operator selector
        operator_label = QLabel("Operator:")
        operator_combo = QComboBox()
        operator_combo.setObjectName("filter_operator_combo")
        operator_combo.addItems([
            "contains",
            "equals",
            "starts with",
            "ends with",
            "is empty",
            "is not empty",
            ">",
            ">=",
            "<",
            "<=",
            "!="
        ])
        operator_combo.setMinimumWidth(120)

        # Value input
        value_label = QLabel("Value:")
        value_input = QLineEdit()
        value_input.setObjectName("filter_value_input")
        value_input.setPlaceholderText("Filter value...")
        value_input.setMinimumWidth(200)

        # Delete button
        delete_button = QPushButton("✕")
        delete_button.setObjectName("filter_delete_button")
        delete_button.setMaximumWidth(30)
        delete_button.setToolTip("Remove this filter")
        delete_button.clicked.connect(lambda: self._remove_filter_row(row_container))

        # Add widgets to row layout
        row_layout.addWidget(column_label)
        row_layout.addWidget(column_combo)
        row_layout.addWidget(operator_label)
        row_layout.addWidget(operator_combo)
        row_layout.addWidget(value_label)
        row_layout.addWidget(value_input)
        row_layout.addWidget(delete_button)
        row_layout.addStretch()

        # Add row to filters layout
        self.filters_layout.addWidget(row_container)

        # Store reference to controls
        self.filter_rows.append({
            'container': row_container,
            'column_combo': column_combo,
            'operator_combo': operator_combo,
            'value_input': value_input
        })

    def _remove_filter_row(self, row_container: QWidget):
        """
        Remove a filter row.

        Args:
            row_container: The container widget to remove
        """
        # Keep at least one row
        if len(self.filter_rows) <= 1:
            return

        # Find and remove the row
        for i, row_data in enumerate(self.filter_rows):
            if row_data['container'] == row_container:
                self.filters_layout.removeWidget(row_container)
                row_container.deleteLater()
                self.filter_rows.pop(i)
                break

    def _clear_all_filters(self):
        """Clear all filter rows except one empty row."""
        # Remove all but the first row
        while len(self.filter_rows) > 1:
            row_data = self.filter_rows[-1]
            self.filters_layout.removeWidget(row_data['container'])
            row_data['container'].deleteLater()
            self.filter_rows.pop()

        # Clear the remaining row's value
        if self.filter_rows:
            self.filter_rows[0]['value_input'].clear()

    def get_filters(self) -> List[Dict[str, str]]:
        """
        Get all current filter configurations.

        Returns:
            List of filter dictionaries with keys: column, operator, value
        """
        filters = []
        for row_data in self.filter_rows:
            filters.append({
                'column': row_data['column_combo'].currentText(),
                'operator': row_data['operator_combo'].currentText(),
                'value': row_data['value_input'].text()
            })
        return filters

    def set_filters(self, filters: List[Dict[str, str]]):
        """
        Set filter configurations programmatically.

        Args:
            filters: List of filter dictionaries with keys: column, operator, value
        """
        # Clear existing rows
        while len(self.filter_rows) > 0:
            row_data = self.filter_rows[-1]
            self.filters_layout.removeWidget(row_data['container'])
            row_data['container'].deleteLater()
            self.filter_rows.pop()

        # Add rows for each filter
        for filter_config in filters:
            self._add_filter_row()
            row_data = self.filter_rows[-1]
            row_data['column_combo'].setCurrentText(filter_config['column'])
            row_data['operator_combo'].setCurrentText(filter_config['operator'])
            row_data['value_input'].setText(filter_config['value'])

        # Ensure at least one row
        if not filters:
            self._add_filter_row()

    def _apply_filters(self):
        """Apply the current filters and emit signal."""
        # Get valid filters (non-empty or special operators)
        filters = [
            f for f in self.get_filters()
            if f['column'] and (f['value'] or f['operator'] in ['is empty', 'is not empty'])
        ]
        self.filtersApplied.emit(filters)

