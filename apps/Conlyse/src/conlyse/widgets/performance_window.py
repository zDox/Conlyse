from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from conlyse.logger import get_logger
from conlyse.widgets.mui.label import CLabel

if TYPE_CHECKING:
    from conlyse.app import App

logger = get_logger()


class PerformanceWindow(QWidget):
    """
    A floating window that displays performance metrics for rendering.
    
    Tracks and displays:
    - Individual renderer times
    - Total frame time
    - FPS
    
    This window is available globally and can be used by any page.
    """
    
    def __init__(self, app: App, parent=None):
        super().__init__(parent)
        self.app = app
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # Set background color and border via stylesheet
        self.setStyleSheet("""
            QWidget#performance_window { 
                background-color: #2b2b2b;
                border: 1px solid #555555;
                border-radius: 5px;
            }
            QLabel#performance_label {
                color: #ffffff; 
                font-size: 12px;
            }
        """)
        self.setObjectName("performance_window")
        self.setWindowTitle("Performance Metrics")
        
        # Set up the layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Title
        self.title_label = CLabel("Performance Metrics", parent=self)
        self.title_label.setObjectName("panel_title")
        layout.addWidget(self.title_label)
        
        # Page name label
        self.page_label = QLabel("Page: None", self)
        self.page_label.setObjectName("performance_label")
        layout.addWidget(self.page_label)
        
        # FPS Label
        self.fps_label = QLabel("FPS: 0.0", self)
        self.fps_label.setObjectName("performance_label")
        layout.addWidget(self.fps_label)
        
        # Total frame time label
        self.frame_time_label = QLabel("Frame Time: 0.00 ms", self)
        self.frame_time_label.setObjectName("performance_label")
        layout.addWidget(self.frame_time_label)
        
        # Metric labels (for custom performance metrics from pages)
        self.metric_labels = {}
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Set window size
        self.setMinimumWidth(250)
        self.setMaximumWidth(350)
        self.setMinimumHeight(150)
        
        # Hide by default
        self.hide()
    
    def clear_metrics(self) -> None:
        """Clear all custom metrics (called when switching pages)."""
        for label in self.metric_labels.values():
            label.deleteLater()
        self.metric_labels.clear()
    
    def set_page(self, page_name: str) -> None:
        """
        Set the current page name.
        
        Args:
            page_name: Name of the current page
        """
        self.page_label.setText(f"Page: {page_name}")
    
    def add_metric(self, name: str) -> None:
        """
        Add a custom performance metric to track.
        
        Args:
            name: Name of the metric
        """
        if name not in self.metric_labels:
            label = QLabel(f"{name}: 0.00 ms", self)
            label.setObjectName("performance_label")
            # Insert before the stretch at the end
            self.layout().insertWidget(self.layout().count() - 1, label)
            self.metric_labels[name] = label
            logger.debug(f"Added metric '{name}' to performance window")

    def has_metric(self, name: str) -> bool:
        """
        Check if a metric with the given name exists.

        Args:
            name: Name of the metric

        Returns:
            True if the metric exists, False otherwise
        """
        return name in self.metric_labels
    
    def update_metric(self, name: str, value: float, unit: str = "ms") -> None:
        """
        Update a custom performance metric.
        
        Args:
            name: Name of the metric
            value: Value to display
            unit: Unit of measurement (default: "ms")
        """
        if name in self.metric_labels:
            self.metric_labels[name].setText(f"{name}: {value:.2f} {unit}")
        else:
            logger.warning(f"Attempted to update non-existent metric '{name}'. Call add_metric() first.")
    
    def update_frame_time(self, time_ms: float) -> None:
        """
        Update the total frame time.
        
        Args:
            time_ms: Total frame time in milliseconds
        """
        self.frame_time_label.setText(f"Frame Time: {time_ms:.2f} ms")
    
    def update_fps(self, fps: float) -> None:
        """
        Update the FPS display.
        
        Args:
            fps: Frames per second
        """
        self.fps_label.setText(f"FPS: {fps:.1f}")
    
    def toggle_visibility(self) -> None:
        """Toggle the visibility of the performance window."""
        if self.isVisible():
            self.hide()
            logger.debug("Performance window hidden")
        else:
            self.show()
            self.raise_()
            logger.debug("Performance window shown")
