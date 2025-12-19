from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QGridLayout
)

from conflict_interface.data_types.map_state.sea_province import SeaProvince
from conflict_interface.interface.replay_interface import ReplayInterface


class ProvinceInfoDock(QWidget):
    """Dock displaying information about a selected province."""

    def __init__(self, ritf: ReplayInterface, parent=None):
        super().__init__(parent)
        self.ritf = ritf
        self.selected_province_id: int | None = None

        self._value_labels: dict[str, QLabel] = {}

        self.setObjectName("province_info_dock")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.setup_ui()
        self.update_ui()

    # ------------------------------------------------------------------

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        title = QLabel("Province Information")
        title.setObjectName("dock_title")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)

        # No selection label
        self.no_selection_label = QLabel("No province selected.")
        self.no_selection_label.setObjectName("dock_info_text")
        layout.addWidget(self.no_selection_label)

        # Info grid
        self.grid = QGridLayout()
        self.grid.setSpacing(12)

        self._add_row(0, "Province", "name")
        self._add_row(1, "Owner", "owner")
        self._add_row(2, "Population", "population")
        self._add_row(3, "Morale", "morale")
        self._add_row(4, "Terrain", "terrain")
        self._add_row(5, "Resources", "resource_production")
        self._add_row(6, "Production Type", "resource_production_type")

        layout.addLayout(self.grid)
        layout.addStretch()

    # ------------------------------------------------------------------

    def update_ui(self):
        """Render the UI according to the current selection."""
        if self.selected_province_id is None:
            self._show_no_province()
            return

        province = self.ritf.get_province(self.selected_province_id)
        if province is None:
            self._show_no_province()
            return

        if isinstance(province, SeaProvince):
            self._show_sea_province(province)
        else:
            self._show_land_province(province)

    # ------------------------------------------------------------------
    # Render states
    # ------------------------------------------------------------------

    def _show_no_province(self):
        self.no_selection_label.show()
        self._set_grid_visible(False)

    def _show_land_province(self, province):
        self.no_selection_label.hide()
        self._set_grid_visible(True)

        self._set("name", province.name)
        self._set(
            "owner",
            self.ritf.get_player(province.owner_id).nation_name,
        )
        self._set("resource_production", province.resource_production)
        self._set("resource_production_type", province.resource_production_type.name.lower().capitalize())
        self._set("morale", f"{province.morale}%")
        self._set("terrain", province.terrain_type.name.lower().capitalize())

        self._value_labels["owner"].show()

    def _show_sea_province(self, province):
        self.no_selection_label.hide()
        self._set_grid_visible(True)

        self._set("name", province.name)
        self._set("terrain", province.terrain_type.name.lower().capitalize())

        # Hide irrelevant fields
        self._value_labels["owner"].hide()
        self._value_labels["resource_production"].hide()
        self._value_labels["resource_production_type"].hide()
        self._value_labels["population"].hide()
        self._value_labels["morale"].hide()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _add_row(self, row: int, label: str, key: str):
        label_widget = QLabel(f"{label}:")
        label_widget.setStyleSheet("color: #888;")

        value_widget = QLabel()
        value_widget.setStyleSheet("font-weight: 500;")

        self.grid.addWidget(label_widget, row, 0, Qt.AlignLeft)
        self.grid.addWidget(value_widget, row, 1, Qt.AlignLeft)

        self._value_labels[key] = value_widget

    def _set(self, key: str, value: str):
        self._value_labels[key].setText(value)

    def _set_grid_visible(self, visible: bool):
        for i in range(self.grid.count()):
            self.grid.itemAt(i).widget().setVisible(visible)

    # ------------------------------------------------------------------

    def set_selected_province_id(self, province_id: int | None):
        self.selected_province_id = province_id
        self.update_ui()
