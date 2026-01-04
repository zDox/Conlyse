from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QFrame,
    QGridLayout,
)

from conflict_interface.data_types.map_state.province import Province
from conflict_interface.data_types.map_state.sea_province import SeaProvince
from conflict_interface.hook_system.replay_hook_event import ReplayHookEvent
from conflict_interface.hook_system.replay_hook_tag import ReplayHookTag
from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.widgets.dock_system.docks.dock import Dock

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget as QWidgetType


class ProvinceInfoDock(Dock):
    """Dock displaying information about a selected province.

    This widget provides a detailed view of province attributes including
    ownership, population, morale, terrain, and resource production for
    land provinces, with the appropriate handling for sea provinces.

    Attributes:
        subscribed_events:  Set of ReplayHookTag events this dock subscribes to.
        ritf: Reference to the ReplayInterface for accessing game state.
        selected_province_id: ID of the currently selected province, or None.
    """

    subscribed_events = {ReplayHookTag.ProvinceChanged}

    # Field configuration for province information display
    _LAND_PROVINCE_FIELDS = [
        ("Province", "name"),
        ("Owner", "owner"),
        ("Population", "population"),
        ("Morale", "morale"),
        ("Terrain", "terrain"),
        ("Resources", "resource_production"),
        ("Production Type", "resource_production_type"),
    ]

    _SEA_PROVINCE_HIDDEN_FIELDS = {
        "owner",
        "resource_production",
        "resource_production_type",
        "population",
        "morale",
    }

    def __init__(
            self, ritf: ReplayInterface, parent: QWidgetType | None = None
    ) -> None:
        """Initialize the ProvinceInfoDock.

        Args:
            ritf: ReplayInterface instance for accessing game state.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.ritf = ritf
        self.selected_province_id: int | None = None

        self._value_labels: dict[str, QLabel] = {}
        self.no_selection_label: QLabel | None = None
        self.grid: QGridLayout | None = None

        self.setObjectName("province_info_dock")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._setup_ui()
        self._update_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        title = self._create_title_label()
        layout.addWidget(title)

        # Separator
        separator = self._create_separator()
        layout.addWidget(separator)

        # No selection label
        self.no_selection_label = QLabel("No province selected.")
        self.no_selection_label.setObjectName("dock_info_text")
        layout.addWidget(self.no_selection_label)

        # Info grid
        self.grid = QGridLayout()
        self.grid.setSpacing(12)

        self._populate_info_grid()

        layout.addLayout(self.grid)
        layout.addStretch()

    def _create_title_label(self) -> QLabel:
        """Create and configure the title label.

        Returns:
            Configured QLabel for the dock title.
        """
        title = QLabel("Province Information")
        title.setObjectName("dock_title")
        return title

    def _create_separator(self) -> QFrame:
        """Create a horizontal separator line.

        Returns:
            Configured QFrame separator.
        """
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        return separator

    def _populate_info_grid(self) -> None:
        """Populate the grid layout with province information fields."""
        for row, (label, key) in enumerate(self._LAND_PROVINCE_FIELDS):
            self._add_info_row(row, label, key)

    def _add_info_row(self, row: int, label: str, key: str) -> None:
        """Add a labeled information row to the grid.

        Args:
            row: Grid row index.
            label: Display label for the field.
            key: Internal key for accessing the value label.
        """
        label_widget = QLabel(f"{label}:")
        label_widget.setObjectName("dock_label")

        value_widget = QLabel()
        value_widget.setObjectName("dock_value")

        if self.grid is not None:
            self.grid.addWidget(label_widget, row, 0, Qt.AlignmentFlag.AlignLeft)
            self.grid.addWidget(value_widget, row, 1, Qt.AlignmentFlag.AlignLeft)

        self._value_labels[key] = value_widget

    def _update_ui(self) -> None:
        """Update the UI to reflect the current province selection."""
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

    def _show_no_province(self) -> None:
        """Display the 'no province selected' state."""
        if self.no_selection_label is not None:
            self.no_selection_label.show()
        self._set_grid_visible(False)

    def _show_land_province(self, province: Province) -> None:
        """Display information for a land province.

        Args:
            province: The Province instance to display.
        """
        if self.no_selection_label is not None:
            self.no_selection_label.hide()
        self._set_grid_visible(True)

        self._set_value("name", province.name)

        owner = self.ritf.get_player(province.owner_id)
        self._set_value("owner", owner.nation_name if owner else "Unknown")

        self._set_value("resource_production", str(province.resource_production))
        self._set_value(
            "resource_production_type",
            province.resource_production_type.name.lower().capitalize(),
        )
        self._set_value("morale", f"{province.morale}%")
        self._set_value("terrain", province.terrain_type.name.lower().capitalize())

        # Ensure all land province fields are visible
        for key in self._value_labels:
            self._value_labels[key].show()

    def _show_sea_province(self, province: SeaProvince) -> None:
        """Display information for a sea province.

        Args:
            province: The SeaProvince instance to display.
        """
        if self.no_selection_label is not None:
            self.no_selection_label.hide()
        self._set_grid_visible(True)

        self._set_value("name", province.name)
        self._set_value("terrain", province.terrain_type.name.lower().capitalize())

        # Hide fields not applicable to sea provinces
        for key in self._SEA_PROVINCE_HIDDEN_FIELDS:
            if key in self._value_labels:
                self._value_labels[key].hide()

    def _set_value(self, key: str, value: str) -> None:
        """Set the text value for a specific field.

        Args:
            key: The field key.
            value: The text value to display.
        """
        if key in self._value_labels:
            self._value_labels[key].setText(value)

    def _set_grid_visible(self, visible: bool) -> None:
        """Set visibility for all grid items.

        Args:
            visible: Whether grid items should be visible.
        """
        if self.grid is None:
            return

        for i in range(self.grid.count()):
            item = self.grid.itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.setVisible(visible)

    def set_selected_province_id(self, province_id: int | None) -> None:
        """Set the currently selected province and update the display.

        Args:
            province_id: ID of the province to select, or None to deselect.
        """
        self.selected_province_id = province_id
        self._update_ui()

    def process_events(
            self, events: dict[ReplayHookTag, list[ReplayHookEvent]]
    ) -> None:
        """Process replay hook events to update the display.

        Args:
            events: Dictionary of events grouped by tag.
        """
        province_events = events.get(ReplayHookTag.ProvinceChanged, [])

        for event in province_events:
            province = cast(Province, event.reference)
            if province.id == self.selected_province_id:
                self._update_ui()
                return
