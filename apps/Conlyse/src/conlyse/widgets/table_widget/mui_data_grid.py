"""
MUI Data Grid Widget - Main Component
======================================
Feature-rich data grid with filtering, sorting, column management, and pagination.

Author: NikNam3
Date: 2025-11-18
"""

from typing import Any, Callable, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
)

from conlyse.widgets.mui.icon_button import CIconButton
from conlyse.widgets.table_widget.cell_helpers import CellHelpers
from conlyse.widgets.table_widget.data_manager import DataManager
from conlyse.widgets.table_widget.column_panel import ColumnPanel
from conlyse.widgets.table_widget.filter_panel import FilterPanel
from conlyse.widgets.table_widget.sort_manager import SortManager


class MUIDataGrid(QWidget):
    """
    MUI-style Data Grid widget with advanced features.

    Features:
    - Custom cell renderers (images, buttons, links, widgets)
    - Advanced filtering with multiple conditions (filters ALL columns)
    - Global search (searches VISIBLE columns only)
    - Column visibility management (can hide any/all columns)
    - Sorting by clicking column headers (toggles ASC/DESC)
    - Pagination with configurable rows per page
    - Integrated dropdown panels (no popup dialogs)

    Signals:
    - rowSelectionChanged(list): Emitted when row selection changes
    - cellButtonClicked(int, str, dict): Emitted when a cell button is clicked
    - cellLinkClicked(int, str, str): Emitted when a cell link is clicked
    """

    # ===== Signals =====
    rowSelectionChanged = pyqtSignal(list)
    cellButtonClicked = pyqtSignal(int, str, object)
    cellLinkClicked = pyqtSignal(int, str, str)

    def __init__(self, parent=None):
        """Initialize the data grid widget."""
        super().__init__(parent)
        self.setObjectName("MUIDataGrid")

        # ===== Managers =====
        self.data_manager = DataManager()
        self.sort_manager = SortManager()
        self.cell_helpers = CellHelpers(self)

        # ===== Pagination State =====
        self.current_page = 0
        self.rows_per_page = 10

        # ===== UI State =====
        self.search_visible = False
        self.filter_panel_visible = False
        self.column_panel_visible = False

        # ===== Panel References =====
        self.filter_panel: Optional[FilterPanel] = None
        self.column_panel: Optional[ColumnPanel] = None

        self._setup_ui()

    def _setup_ui(self):
        """Build the main data grid UI structure."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # Top Toolbar
        self.toolbar = self._create_toolbar()
        main_layout.addWidget(self.toolbar)

        # Panel Container
        self.panel_container = QWidget()
        self.panel_container.setObjectName("data_grid_panel_container")
        self.panel_layout = QVBoxLayout(self.panel_container)
        self.panel_layout.setContentsMargins(0, 0, 0, 0)
        self.panel_layout.setSpacing(0)
        main_layout.addWidget(self.panel_container)
        self.panel_container.setVisible(False)

        # Data Table
        self.table = QTableWidget()
        self.table.setObjectName("data_grid_table")
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.table.verticalHeader().setVisible(False)
        main_layout.addWidget(self.table)

        # Bottom Pagination Bar
        self.pagination_bar = self._create_pagination_bar()
        main_layout.addWidget(self.pagination_bar)

    def _create_toolbar(self) -> QWidget:
        """Create the top toolbar with column/filter/search controls."""
        toolbar = QWidget()
        toolbar.setObjectName("data_grid_toolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 8, 8, 8)
        toolbar_layout.setSpacing(8)

        toolbar_layout.addStretch()

        # Columns Button
        self.columns_button = CIconButton("fa6s.table-columns", "primary", 30, parent=self)
        self.columns_button.setObjectName("toolbar_columns_button")
        self.columns_button.setToolTip("Show/Hide Columns")
        self.columns_button.clicked.connect(self._toggle_column_panel)
        toolbar_layout.addWidget(self.columns_button)

        # Filter Button
        self.filter_button = CIconButton("fa6s.filter", "primary", 30, parent=self)
        self.filter_button.setObjectName("toolbar_filter_button")
        self.filter_button.setToolTip("Add Filters")
        self.filter_button.clicked.connect(self._toggle_filter_panel)
        toolbar_layout.addWidget(self.filter_button)

        # Search Button
        self.search_button = CIconButton("fa5s.search", "primary", 30, parent=self)
        self.search_button.setObjectName("toolbar_search_button")
        self.search_button.setToolTip("Search")
        self.search_button.clicked.connect(self._toggle_search)
        toolbar_layout.addWidget(self.search_button)

        # Search Input
        self.search_input = QLineEdit()
        self.search_input.setObjectName("toolbar_search_input")
        self.search_input.setPlaceholderText("Search...")
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.setMinimumWidth(200)
        self.search_input.setVisible(False)
        toolbar_layout.addWidget(self.search_input)

        return toolbar

    def _create_pagination_bar(self) -> QWidget:
        """Create the bottom pagination bar."""
        pagination = QWidget()
        pagination.setObjectName("data_grid_pagination")
        pagination_layout = QHBoxLayout(pagination)
        pagination_layout.setContentsMargins(8, 8, 8, 8)
        pagination_layout.setSpacing(8)

        rows_label = QLabel("Rows per page:")
        rows_label.setObjectName("pagination_rows_per_page_label")
        pagination_layout.addWidget(rows_label)

        self.rows_combo = QComboBox()
        self.rows_combo.setObjectName("pagination_rows_combo")
        self.rows_combo.addItems(["5", "10", "25", "50", "100"])
        self.rows_combo.setCurrentText(str(self.rows_per_page))
        self.rows_combo.currentTextChanged.connect(self._on_rows_per_page_changed)
        pagination_layout.addWidget(self.rows_combo)

        pagination_layout.addStretch()

        self.page_info_label = QLabel()
        self.page_info_label.setObjectName("pagination_info_label")
        self._update_page_info()
        pagination_layout.addWidget(self.page_info_label)

        self.prev_button = CIconButton("ei.caret-left", "primary", 30, parent=self)
        self.prev_button.setToolTip("Previous Page")
        self.prev_button.clicked.connect(self._prev_page)
        pagination_layout.addWidget(self.prev_button)

        self.next_button = CIconButton("ei.caret-right", "primary", 30, parent=self)
        self.next_button.setToolTip("Next Page")
        self.next_button.clicked.connect(self._next_page)
        pagination_layout.addWidget(self.next_button)

        return pagination

    # ==========================================================================
    # PUBLIC API - Data Management
    # ==========================================================================

    def set_data(self, data: List[Dict[str, Any]], columns: Optional[List[str]] = None):
        """Set the data for the grid."""
        self.data_manager.set_data(data, columns)
        self.current_page = 0
        self._clear_panels()
        self.sort_manager.reset()
        self._apply_filters()

    def get_selected_rows(self) -> List[Dict[str, Any]]:
        """Get the data for currently selected rows."""
        selected_indices = set(item.row() for item in self.table.selectedItems())
        start_idx = self.current_page * self.rows_per_page
        return [
            self.data_manager.filtered_data[start_idx + idx]
            for idx in selected_indices
        ]

    def get_all_filtered_data(self) -> List[Dict[str, Any]]:
        """Get all data after filters and search are applied."""
        return self.data_manager.filtered_data.copy()

    # ==========================================================================
    # PUBLIC API - Custom Cell Renderers
    # ==========================================================================

    def set_cell_renderer(self, column: str, renderer: Callable):
        """Set a custom renderer function for a specific column."""
        self.data_manager.set_cell_renderer(column, renderer)

    def set_filter_value_extractor(self, column: str, extractor: Callable):
        """Set a custom function to extract the filterable value for a column."""
        self.data_manager.set_filter_value_extractor(column, extractor)

    def set_search_value_extractor(self, column: str, extractor: Callable):
        """Set a custom function to extract the searchable value for a column."""
        self.data_manager.set_search_value_extractor(column, extractor)

    # ==========================================================================
    # PUBLIC API - Helper Methods (delegate to CellHelpers)
    # ==========================================================================

    def create_button_cell(self, text: str, row_data: Dict, row_index: int,
                           column: str, icon_path: Optional[str] = None,
                           style: Optional[str] = None):
        """Helper to create a button for a cell."""
        return self.cell_helpers.create_button_cell(text, row_data, row_index, column, icon_path, style)

    def create_link_cell(self, text: str, url: str, row_index: int, column: str):
        """Helper to create a clickable link for a cell."""
        return self.cell_helpers.create_link_cell(text, url, row_index, column)

    def create_image_cell(self, image_path: str, width: int = 50, height: int = 50):
        """Helper to create an image cell."""
        return self.cell_helpers.create_image_cell(image_path, width, height)

    def create_multi_widget_cell(self, widgets: List[QWidget]):
        """Helper to create a cell with multiple widgets."""
        return self.cell_helpers.create_multi_widget_cell(widgets)

    # ==========================================================================
    # INTERNAL - Panel Management
    # ==========================================================================

    def _toggle_filter_panel(self):
        """Toggle the filter panel visibility."""
        self.filter_panel_visible = not self.filter_panel_visible

        if self.filter_panel_visible and self.column_panel_visible:
            self.column_panel_visible = False
            if self.column_panel:
                self.column_panel.setVisible(False)

        if self.filter_panel_visible:
            if not self.filter_panel:
                self.filter_panel = FilterPanel(self.data_manager.columns, self)
                self.filter_panel.filtersApplied.connect(self._on_filters_applied)
                self.panel_layout.addWidget(self.filter_panel)

            if self.data_manager.filters:
                self.filter_panel.set_filters(self.data_manager.filters)

            self.filter_panel.setVisible(True)
            self.panel_container.setVisible(True)
        else:
            if self.filter_panel:
                self.filter_panel.setVisible(False)
            self.panel_container.setVisible(self.column_panel_visible)

    def _toggle_column_panel(self):
        """Toggle the column panel visibility."""
        self.column_panel_visible = not self.column_panel_visible

        if self.column_panel_visible and self.filter_panel_visible:
            self.filter_panel_visible = False
            if self.filter_panel:
                self.filter_panel.setVisible(False)

        if self.column_panel_visible:
            if not self.column_panel or self.column_panel.columns != self.data_manager.columns:
                if self.column_panel:
                    self.panel_layout.removeWidget(self.column_panel)
                    self.column_panel.deleteLater()

                self.column_panel = ColumnPanel(
                    self.data_manager.columns,
                    self.data_manager.visible_columns,
                    self
                )
                self.column_panel.columnsChanged.connect(self._on_columns_changed)
                self.panel_layout.addWidget(self.column_panel)

            self.column_panel.setVisible(True)
            self.panel_container.setVisible(True)
        else:
            if self.column_panel:
                self.column_panel.setVisible(False)
            self.panel_container.setVisible(self.filter_panel_visible)

    def _on_filters_applied(self, filters: List[Dict[str, str]]):
        """Handle filters applied from filter panel."""
        self.data_manager.filters = filters
        self._apply_filters()

    def _on_columns_changed(self, visible_columns: List[str]):
        """Handle column visibility changes."""
        self.data_manager.visible_columns = visible_columns
        self._refresh_table()

    def _clear_panels(self):
        """Remove and cleanup filter and column panels."""
        if self.filter_panel:
            self.panel_layout.removeWidget(self.filter_panel)
            self.filter_panel.deleteLater()
            self.filter_panel = None

        if self.column_panel:
            self.panel_layout.removeWidget(self.column_panel)
            self.column_panel.deleteLater()
            self.column_panel = None

    # ==========================================================================
    # INTERNAL - Filtering and Refresh
    # ==========================================================================

    def _apply_filters(self):
        """Apply all filters and search to the data."""
        self.data_manager.apply_filters(self.search_input.text())
        self.current_page = 0
        self._refresh_table()

    def _refresh_table(self):
        """Refresh the table display with current page data."""
        start_idx = self.current_page * self.rows_per_page
        end_idx = start_idx + self.rows_per_page
        page_data = self.data_manager.filtered_data[start_idx:end_idx]

        self.table.setRowCount(len(page_data) if self.data_manager.visible_columns else 0)
        self.table.setColumnCount(len(self.data_manager.visible_columns))
        self.table.setHorizontalHeaderLabels(self.data_manager.visible_columns)

        if self.data_manager.visible_columns:
            for row_idx, row_data in enumerate(page_data):
                actual_row_index = start_idx + row_idx

                for col_idx, column in enumerate(self.data_manager.visible_columns):
                    value = row_data.get(column, '')

                    if column in self.data_manager.cell_renderers:
                        widget = self.data_manager.cell_renderers[column](value, row_data, actual_row_index)
                        self.table.setCellWidget(row_idx, col_idx, widget)
                    else:
                        item = QTableWidgetItem(str(value))
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        self.table.setItem(row_idx, col_idx, item)

            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            self.table.resizeColumnsToContents()
            self.table.resizeRowsToContents()

        self._update_page_info()
        self._update_navigation_buttons()

    # ==========================================================================
    # INTERNAL - Sorting (FIXED)
    # ==========================================================================

    def _on_header_clicked(self, logical_index: int):
        """Handle column header click for sorting."""
        if logical_index >= len(self.data_manager.visible_columns):
            return

        column = self.data_manager.visible_columns[logical_index]

        # Toggle sort order for this column
        new_order = self.sort_manager.toggle_sort(column)

        # Sort the data
        self.data_manager.filtered_data = self.sort_manager.sort_data(
            self.data_manager.filtered_data,
            column,
            new_order
        )

        # Update the visual indicator
        qt_order = Qt.SortOrder.AscendingOrder if new_order == "asc" else Qt.SortOrder.DescendingOrder
        self.table.horizontalHeader().setSortIndicator(logical_index, qt_order)

        # Reset to first page and refresh
        self.current_page = 0
        self._refresh_table()

    # ==========================================================================
    # INTERNAL - Pagination
    # ==========================================================================

    def _update_page_info(self):
        """Update the page information label."""
        if not self.data_manager.filtered_data:
            self.page_info_label.setText("0-0 of 0")
            return

        start = self.current_page * self.rows_per_page + 1
        end = min((self.current_page + 1) * self.rows_per_page, len(self.data_manager.filtered_data))
        total = len(self.data_manager.filtered_data)

        self.page_info_label.setText(f"{start}-{end} of {total}")

    def _update_navigation_buttons(self):
        """Enable/disable pagination navigation buttons."""
        self.prev_button.setEnabled(self.current_page > 0)

        max_page = (len(self.data_manager.filtered_data) - 1) // self.rows_per_page if self.data_manager.filtered_data else 0
        self.next_button.setEnabled(self.current_page < max_page)

    def _on_rows_per_page_changed(self, text: str):
        """Handle rows per page selection change."""
        self.rows_per_page = int(text)
        self.current_page = 0
        self._refresh_table()

    def _prev_page(self):
        """Navigate to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._refresh_table()

    def _next_page(self):
        """Navigate to next page."""
        max_page = (len(self.data_manager.filtered_data) - 1) // self.rows_per_page if self.data_manager.filtered_data else 0
        if self.current_page < max_page:
            self.current_page += 1
            self._refresh_table()

    # ==========================================================================
    # INTERNAL - Search
    # ==========================================================================

    def _toggle_search(self):
        """Toggle search input visibility."""
        self.search_visible = not self.search_visible
        self.search_input.setVisible(self.search_visible)

        if self.search_visible:
            self.search_input.setFocus()
        else:
            self.search_input.clear()

    def _on_search_changed(self, text: str):
        """Handle search text change."""
        self._apply_filters()