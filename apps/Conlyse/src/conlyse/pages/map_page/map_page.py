"""
Map Page
========
Main page for displaying the map with OpenGL rendering.

Author: Copilot
Date: 2025-12-02
"""

from __future__ import annotations

from typing import Optional
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QVBoxLayout

from conlyse.logger import get_logger
from conlyse.pages.map_page.map_gl_widget import MapGLWidget
from conlyse.pages.map_page.province_renderer import ProvinceRenderer
from conlyse.pages.map_page.province_renderer import get_distinct_color
from conlyse.pages.page import Page
from conlyse.widgets.mui.label import CLabel

if TYPE_CHECKING:
    from conlyse.app import App
    from conlyse.managers.replay_manager import ReplayInterface

logger = get_logger()


class MapPage(Page):
    """
    Page for displaying the game map with OpenGL rendering.
    
    Features:
    - OpenGL-based rendering for performance
    - Camera controls (pan, zoom)
    - Province visualization with colors
    - Extensible renderer system for different entity types
    """

    HEADER = True

    def __init__(self, app, parent=None):
        """
        Initialize the map page.

        Args:
            app: Application instance
            parent: Parent widget
        """
        super().__init__(parent)

        self.app: App = app
        self.replay_interface: Optional[ReplayInterface] = None

        # UI Components
        self.map_widget: Optional[MapGLWidget] = None
        self.info_label: Optional[CLabel] = None
        self.province_count_label: Optional[CLabel] = None

        # Renderers
        self.province_renderer: Optional[ProvinceRenderer] = None

        # Track if UI has been set up
        self._ui_initialized = False

    def setup(self, context):
        """
        Called when page is opened - initialize with replay data.

        Args:
            context: Dictionary containing 'replay_path' key
        """
        replay_path = context.get("replay_path", None)

        if not replay_path:
            logger.error("No replay path provided to MapPage")
            from conlyse.utils.enums import PageType
            self.app.page_manager.switch_to(PageType.ReplayListPage)
            return

        self.replay_interface = self.app.replay_manager.get_replay(replay_path)

        if not self.replay_interface or not self.app.replay_manager.is_active_replay(replay_path):
            logger.error(f"Replay not loaded for path: {replay_path}")
            from conlyse.utils.enums import PageType
            self.app.page_manager.switch_to(
                PageType.ReplayListPage,
                error_message=f"Failed to load replay: {replay_path}"
            )
            return

        # Initialize UI if first time
        if not self._ui_initialized:
            self._setup_ui()
            self._ui_initialized = True

        # Load map data
        self._load_map_data()

        logger.info("MapPage setup complete")

    def _setup_ui(self):
        """One-time UI initialization."""
        # Set widget attributes
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # ===== Header Section =====
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # Title
        title_label = CLabel("Map View")
        title_label.setObjectName("map_page_title")
        header_layout.addWidget(title_label)

        # Info labels
        self.info_label = CLabel("Loading...")
        self.info_label.setObjectName("map_page_info")
        header_layout.addWidget(self.info_label)

        self.province_count_label = CLabel("")
        self.province_count_label.setObjectName("map_page_province_count")
        header_layout.addWidget(self.province_count_label)

        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # ===== OpenGL Map Widget =====
        self.map_widget = MapGLWidget()
        self.map_widget.setObjectName("map_gl_widget")
        self.map_widget.setMinimumHeight(400)

        # Create and set province renderer
        self.province_renderer = ProvinceRenderer()
        self.map_widget.set_province_renderer(self.province_renderer)

        main_layout.addWidget(self.map_widget, stretch=1)

        # ===== Instructions =====
        instructions = CLabel(
            "Controls: Left-click and drag to pan | Mouse wheel to zoom"
        )
        instructions.setObjectName("map_page_instructions")
        instructions.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(instructions)

        logger.debug("Map page UI setup complete")

    def _load_map_data(self):
        """Load map data from replay interface and prepare rendering."""
        if not self.replay_interface:
            return

        try:
            # Get provinces from replay interface
            provinces = self.replay_interface.get_provinces()

            if not provinces:
                logger.warning("No provinces found in replay")
                self.info_label.set_text("No map data available")
                return

            # Update province count
            self.province_count_label.set_text(f"{len(provinces)} provinces")

            # Set province colors based on ownership
            owner_ids = set()
            for province in provinces.values():
                if hasattr(province, 'owner_id') and province.owner_id is not None:
                    owner_ids.add(province.owner_id)

            # Create color mapping for owners
            owner_colors = {}
            for i, owner_id in enumerate(sorted(owner_ids)):
                owner_colors[owner_id] = get_distinct_color(i, len(owner_ids))

            # Assign colors to provinces
            province_colors = {}
            for province_id, province in provinces.items():
                if hasattr(province, 'owner_id') and province.owner_id is not None:
                    color = owner_colors[province.owner_id]
                else:
                    # Neutral/unowned provinces - gray
                    color = (0.7, 0.7, 0.7, 0.3)
                
                province_colors[province_id] = color

            # Update renderer with provinces and colors
            self.province_renderer.update_provinces(provinces, province_colors)

            # Set provinces to map widget
            self.map_widget.set_provinces(provinces)

            # Update info label
            self.info_label.set_text(f"Loaded map | {len(owner_ids)} owners")

            logger.info(f"Loaded {len(provinces)} provinces with {len(owner_ids)} owners")

        except Exception as e:
            logger.error(f"Error loading map data: {e}", exc_info=True)
            self.info_label.set_text("Error loading map data")

    def update(self):
        """
        Called every frame - trigger map widget update if needed.
        
        Note: For province changes, call self.map_widget.on_province_changed(province_id)
        when a province's ownership or attributes change to efficiently update only
        the affected province's GPU buffers via shaders.
        """
        # The map widget handles its own rendering via OpenGL with shaders
        # Province data is stored on GPU and only updated when marked dirty
        pass

    def clean_up(self):
        """Called when page is closed - cleanup resources."""
        logger.debug("Cleaning up MapPage")

        if self.map_widget:
            self.map_widget.cleanup()

        self.replay_interface = None

        logger.debug("MapPage cleanup complete")
