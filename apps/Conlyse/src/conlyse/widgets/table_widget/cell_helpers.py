"""
Cell Helpers
============
Helper methods for creating common cell types.

Author: NikNam3
Date: 2025-11-18
"""

from typing import Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel, QPushButton, QWidget

# ==============================================================================
# CELL WIDGET CONTAINER
# ==============================================================================

class CellWidgetContainer(QWidget):
    """
    Container widget for custom cell content with multiple widgets.
    Used internally by create_multi_widget_cell().

    Object Names for Styling:
    - CellWidgetContainer (QWidget)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CellWidgetContainer")

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(4, 2, 4, 2)
        self.layout.setSpacing(4)

class CellHelpers:
    """Helper methods for creating custom cell widgets."""

    def __init__(self, parent_grid):
        """
        Initialize cell helpers.

        Args:
            parent_grid: Reference to parent MUIDataGrid for signal emission
        """
        self.parent_grid = parent_grid

    def create_button_cell(self, text: str, row_data: Dict, row_index: int,
                           column: str, icon_path: Optional[str] = None,
                           style: Optional[str] = None) -> QPushButton:
        """Helper to create a button for a cell."""
        btn = QPushButton(text)
        btn.setObjectName("cell_button")

        if icon_path:
            btn.setIcon(QIcon(icon_path))
        if style:
            btn.setStyleSheet(style)

        btn.clicked.connect(
            lambda checked, rd=row_data, ri=row_index, col=column:
            self.parent_grid.cellButtonClicked.emit(ri, col, rd)
        )
        return btn

    def create_link_cell(self, text: str, url: str, row_index: int, column: str) -> QLabel:
        """Helper to create a clickable link for a cell."""
        label = QLabel(f'<a href="{url}">{text}</a>')
        label.setObjectName("cell_link")
        label.setOpenExternalLinks(False)
        label.linkActivated.connect(
            lambda u, ri=row_index, col=column:
            self.parent_grid.cellLinkClicked.emit(ri, col, u)
        )
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        return label

    def create_image_cell(self, image_path: str, width: int = 50, height: int = 50) -> QLabel:
        """Helper to create an image cell."""
        label = QLabel()
        label.setObjectName("cell_image")

        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            label.setPixmap(
                pixmap.scaled(width, height,
                              Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
            )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def create_multi_widget_cell(self, widgets: List[QWidget]) -> QWidget:
        """Helper to create a cell with multiple widgets."""
        container = CellWidgetContainer()
        for widget in widgets:
            container.layout.addWidget(widget)
        container.layout.addStretch()
        return container