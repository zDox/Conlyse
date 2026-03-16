"""
Data Manager
============
Handles data storage, filtering, and search for MUI Data Grid.

Author: NikNam3
Date: 2025-11-18
"""

from typing import Any, Callable, Dict, List, Optional


class DataManager:
    """Manages data, filters, and search for the data grid."""

    def __init__(self):
        self.all_data: List[Dict[str, Any]] = []
        self.filtered_data: List[Dict[str, Any]] = []
        self.columns: List[str] = []
        self.visible_columns: List[str] = []
        self.filters: List[Dict[str, str]] = []

        self.cell_renderers: Dict[str, Callable] = {}
        self.filter_value_extractors: Dict[str, Callable] = {}
        self.search_value_extractors: Dict[str, Callable] = {}

    def set_data(self, data: List[Dict[str, Any]], columns: Optional[List[str]] = None):
        """Set the data for the grid."""
        self.all_data = data

        if columns:
            self.columns = columns
        elif data:
            self.columns = list(data[0].keys())
        else:
            self.columns = []

        self.visible_columns = self.columns.copy()

    def set_cell_renderer(self, column: str, renderer: Callable):
        """Set a custom renderer function for a column."""
        self.cell_renderers[column] = renderer

    def set_filter_value_extractor(self, column: str, extractor: Callable):
        """Set a custom filter value extractor for a column."""
        self.filter_value_extractors[column] = extractor

    def set_search_value_extractor(self, column: str, extractor: Callable):
        """Set a custom search value extractor for a column."""
        self.search_value_extractors[column] = extractor

    def get_filter_value(self, column: str, value: Any, row_data: Dict) -> str:
        """Get the filterable value for a cell."""
        if column in self.filter_value_extractors:
            return str(self.filter_value_extractors[column](value, row_data))
        return str(value)

    def get_search_value(self, column: str, value: Any, row_data: Dict) -> str:
        """Get the searchable value for a cell."""
        if column in self.search_value_extractors:
            return str(self.search_value_extractors[column](value, row_data))
        return str(value)

    def apply_filters(self, search_text: str = ""):
        """Apply all filters and search to the data."""
        self.filtered_data = self.all_data.copy()

        # Apply global search (visible columns only)
        if search_text:
            self.filtered_data = [
                row for row in self.filtered_data
                if any(
                    search_text.lower() in
                    self.get_search_value(col, row.get(col, ''), row).lower()
                    for col in self.visible_columns
                )
            ]

        # Apply column filters (all columns)
        for filter_config in self.filters:
            if not filter_config['column']:
                continue

            column = filter_config['column']
            operator = filter_config['operator']
            value = filter_config['value']

            self.filtered_data = [
                row for row in self.filtered_data
                if self._apply_single_filter(
                    self.get_filter_value(column, row.get(column, ''), row),
                    operator,
                    value,
                    row.get(column, '')
                )
            ]

    def _apply_single_filter(self, cell_value: Any, operator: str,
                             filter_value: str, raw_value: Any = None) -> bool:
        """Apply a single filter condition."""
        cell_str = str(cell_value).lower()
        filter_str = filter_value.lower()

        if operator == "contains":
            return filter_str in cell_str
        elif operator == "equals":
            return cell_str == filter_str
        elif operator == "starts with":
            return cell_str.startswith(filter_str)
        elif operator == "ends with":
            return cell_str.endswith(filter_str)
        elif operator == "is empty":
            return cell_str == "" or cell_str == "none"
        elif operator == "is not empty":
            return cell_str != "" and cell_str != "none"
        elif operator in [">", ">=", "<", "<=", "!="]:
            try:
                value_to_compare = raw_value if raw_value is not None else cell_value
                cell_num = float(value_to_compare)
                filter_num = float(filter_value)

                if operator == ">":
                    return cell_num > filter_num
                elif operator == ">=":
                    return cell_num >= filter_num
                elif operator == "<":
                    return cell_num < filter_num
                elif operator == "<=":
                    return cell_num <= filter_num
                elif operator == "!=":
                    return cell_num != filter_num
            except (ValueError, TypeError):
                return False

        return True