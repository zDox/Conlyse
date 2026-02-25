"""City list dock for the MapPage right sidebar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QScrollArea, QGridLayout
from conflict_interface.data_types.newest.map_state.province import Province
from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.widgets.dock_system.docks.dock import Dock


class CityListDock(Dock):
    """Dock displaying a list of cities."""

    def __init__(self, ritf: ReplayInterface, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ritf = ritf
        self.setObjectName("city_list_dock")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setup_ui()

    def setup_ui(self):
        """Setup the dock UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        title = QLabel("Cities")
        title.setObjectName("dock_title")
        layout.addWidget(title)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("dock_separator")
        layout.addWidget(separator)

        # Scroll area for cities
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(8)

        if not self.ritf.is_country_selected():
            layout.addWidget(QLabel("No country selected!"))
        else:
            for city in self.ritf.get_my_cities().values():
                city_widget = self._create_city_item(city)
                content_layout.addWidget(city_widget)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_city_item(self, city: Province) -> QWidget:
        """Create a city item widget."""
        widget = QWidget()
        widget.setObjectName("city_item")

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # City name
        name_label = QLabel(city.name)
        name_label.setObjectName("dock_item_title")
        layout.addWidget(name_label)

        # Grid for details
        grid = QGridLayout()
        grid.setSpacing(4)

        # Owner
        owner_label = QLabel("Owner:")
        owner_label.setObjectName("dock_item_meta")
        owner_value = QLabel(city.owner.nation_name)
        owner_value.setObjectName("dock_item_value")
        grid.addWidget(owner_label, 0, 0)
        grid.addWidget(owner_value, 0, 1)

        # Population
        pop_label = QLabel("Population:")
        pop_label.setObjectName("dock_item_meta")
        pop_value = QLabel(str(city.population))
        pop_value.setObjectName("dock_item_value")
        grid.addWidget(pop_label, 1, 0)
        grid.addWidget(pop_value, 1, 1)

        # Morale
        morale_label = QLabel("Morale:")
        morale_label.setObjectName("dock_item_meta")
        morale_value = QLabel(f"{city.morale}%")
        morale_value.setObjectName("dock_item_value")
        grid.addWidget(morale_label, 2, 0)
        grid.addWidget(morale_value, 2, 1)

        layout.addLayout(grid)

        return widget
