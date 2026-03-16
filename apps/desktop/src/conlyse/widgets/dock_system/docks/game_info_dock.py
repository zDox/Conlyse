"""Game information dock for the MapPage left sidebar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QGridLayout
from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.widgets.dock_system.docks.dock import Dock


class GameInfoDock(Dock):
    """Dock displaying general game information."""
    
    def __init__(self, ritf: ReplayInterface, parent=None):
        super().__init__(parent)
        self.ritf = ritf
        self.setObjectName("game_info_dock")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dock UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Game Information")
        title.setObjectName("dock_title")
        layout.addWidget(title)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("dock_separator")
        layout.addWidget(separator)
        
        # Content grid with data
        grid = QGridLayout()
        grid.setSpacing(12)

        game_info_state = self.ritf.get_game_info_state()
        # Game ID
        self._add_info_row(grid, 0, "Game ID:", str(self.ritf.game_id))
        
        # Game Mode
        self._add_info_row(grid, 1, "Scenario ID:", str(game_info_state.scenario_id))
        
        # Game Day
        self._add_info_row(grid, 2, "Current Day:", str(self.ritf.game_day()))
        
        # Game Speed
        self._add_info_row(grid, 3, "Game Speed:", str(self.ritf.speed_modifier))

        # Players
        self._add_info_row(grid, 4, "Players:", f"{game_info_state.number_of_logins}/{game_info_state.number_of_players}")

        # Status
        self._add_info_row(grid, 5, "Status:", f"{'Ended' if game_info_state.game_ended else 'Running'}")
        
        layout.addLayout(grid)
        layout.addStretch()
    
    def _add_info_row(self, grid: QGridLayout, row: int, label: str, value: str):
        """Add an information row to the grid."""
        label_widget = QLabel(label)
        label_widget.setObjectName("dock_label")
        
        value_widget = QLabel(value)
        value_widget.setObjectName("dock_value")
        
        grid.addWidget(label_widget, row, 0, Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(value_widget, row, 1, Qt.AlignmentFlag.AlignLeft)
