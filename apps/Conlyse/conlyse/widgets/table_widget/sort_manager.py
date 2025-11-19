"""
Sort Manager
============
Handles column sorting with ASC/DESC toggle functionality.

Author: NikNam3
Date: 2025-11-18
"""

from typing import Any, Dict, List, Optional


class SortManager:
    """Manages sorting state and operations for the data grid."""

    def __init__(self):
        self.current_sort_column: Optional[str] = None
        self.current_sort_order: Optional[str] = None  # "asc" or "desc"

    def toggle_sort(self, column: str) -> str:
        """
        Toggle sort order for a column.

        Args:
            column: Column name to sort by

        Returns:
            New sort order ("asc" or "desc")
        """
        if self.current_sort_column == column:
            # Toggle between asc and desc
            if self.current_sort_order == "asc":
                self.current_sort_order = "desc"
            else:
                self.current_sort_order = "asc"
        else:
            # New column, start with ascending
            self.current_sort_column = column
            self.current_sort_order = "asc"

        return self.current_sort_order

    def sort_data(self, data: List[Dict[str, Any]], column: str, order: str) -> List[Dict[str, Any]]:
        """
        Sort data by column and order.

        Args:
            data: Data to sort
            column: Column to sort by
            order: Sort order ("asc" or "desc")

        Returns:
            Sorted data list
        """
        reverse = (order == "desc")

        try:
            # Try normal sorting (handles None values)
            sorted_data = sorted(
                data,
                key=lambda x: (x.get(column) is None, x.get(column, '')),
                reverse=reverse
            )
        except TypeError:
            # Fall back to string sorting if types are mixed
            sorted_data = sorted(
                data,
                key=lambda x: str(x.get(column, '')),
                reverse=reverse
            )

        return sorted_data

    def reset(self):
        """Reset sorting state."""
        self.current_sort_column = None
        self.current_sort_order = None