import time

from OpenGL import GL as gl
from PySide6.QtCore import QSize
from PySide6.QtCore import Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QSizePolicy
from conflict_interface.data_types.map_state.map_state_enums import ProvinceStateID
from conflict_interface.data_types.map_state.sea_province import SeaProvince
from conflict_interface.hook_system.replay_hook_event import ReplayHookEvent
from conflict_interface.hook_system.replay_hook_tag import ReplayHookTag
from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.logger import get_logger
from conlyse.pages.map_page.camera import Camera
from conlyse.pages.map_page.constants import CITY_LABEL_COLOR
from conlyse.pages.map_page.constants import CITY_LABEL_OUTLINE_COLOR
from conlyse.pages.map_page.constants import CITY_LABEL_OUTLINE_WIDTH
from conlyse.pages.map_page.constants import CITY_LABEL_SIZE
from conlyse.pages.map_page.constants import NATION_LABEL_COLOR
from conlyse.pages.map_page.constants import NATION_LABEL_SHADOW_COLOR
from conlyse.pages.map_page.constants import NATION_LABEL_SHADOW_OFFSET
from conlyse.pages.map_page.map_views.map_view_type import MapViewType
from conlyse.pages.map_page.picking import ProvincePicker
from conlyse.pages.map_page.renderers.province_border_renderer import ProvinceBorderRenderer
from conlyse.pages.map_page.renderers.province_connection_renderer import ProvinceConnectionRenderer
from conlyse.pages.map_page.renderers.province_fill_renderer import ProvinceFillRenderer
from conlyse.pages.map_page.renderers.world_text_renderer import TextGroup, WorldTextRenderer

logger = get_logger()

class Map(QOpenGLWidget):
    def __init__(self, ritf: ReplayInterface, main_config, parent=None):
        super().__init__(parent=parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.ritf = ritf

        # Determine if the map is wraps around
        self.enable_wrapping = ritf.game_state.states.map_state.map.overlap_x != 0
        self.world_min_x = 0
        self.world_max_x = ritf.game_state.states.map_state.map.width
        self.world_min_y = 0
        self.world_max_y = ritf.game_state.states.map_state.map.height
        self.world_width = self.world_max_x - self.world_min_x
        self.world_height = self.world_max_y - self.world_min_y

        self.enable_anti_aliasing: bool = main_config.get("graphics.anti_aliasing")

        self.disable_pyqt_redraws()

        self.camera = Camera(self)
        self.province_fill_renderer = ProvinceFillRenderer(self)
        self.province_connection_renderer = ProvinceConnectionRenderer(self)
        self.province_border_renderer = ProvinceBorderRenderer(self)
        self.world_text_renderer = WorldTextRenderer(self, font_size=100)
        self.province_picker = ProvincePicker(self, self.province_fill_renderer)
        self.last_render_time = time.perf_counter()

        self.active_map_view = MapViewType.POLITICAL
        self.render_connections = True

        # Track if we should skip paint events (to avoid double rendering)
        self._manual_render_mode = False
        
        # Performance tracking
        self.performance_metrics = {
            "province_fill": 0.0,
            "province_connections": 0.0,
            "province_borders": 0.0,
            "world_text": 0.0,
            "terrainview_update": 0.0,
            "resourceview_update": 0.0,
            "politicalview_update": 0.0,
            "render_frame": 0.0,
            "time_since_last_frame": 0.0,
        }

    def disable_pyqt_redraws(self):
        # Prevent Qt automatic redraws
        self.setUpdateBehavior(QOpenGLWidget.UpdateBehavior.NoPartialUpdate)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_PaintOnScreen, False)

    # Ignore Qt paint events
    def paintEvent(self, event):
        # No idea why, but on Linux we need to pass the event to the parent class
        # On Windows this is not necessary
        return super().paintEvent(event)

    def set_active_map_view(self, map_view: MapViewType):
        """
        Set the active map view type.

        Args:
            map_view: The MapViewType to set as active
        """
        self.active_map_view = map_view

    def toggle_render_connections(self):
        """Toggle the rendering of province connections."""
        self.render_connections = not self.render_connections

    def initializeGL(self):
        """Initialize OpenGL resources. Called once when the widget is first shown."""
        self.province_fill_renderer.initialize()
        self.province_connection_renderer.initialize()
        self.province_border_renderer.initialize()
        self.world_text_renderer.initialize()
        gl.glClearColor(0.1, 0.1, 0.1, 1.0)
        # Enable blending
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        if self.enable_anti_aliasing:
            gl.glEnable(gl.GL_MULTISAMPLE)
        self._initialize_world_labels()

    def paintGL(self):
        """Render the map. Called whenever the widget needs to be redrawn."""
        if not self._manual_render_mode:
            return  # Skip automatic paint events
        self.performance_metrics["time_since_last_frame"] = (time.perf_counter() - self.last_render_time) * 1000
        self.last_render_time = time.perf_counter()
        frame_start = time.perf_counter()
        
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        
        # Track province fill renderer time
        render_start = time.perf_counter()
        self.province_fill_renderer.render(self.active_map_view)
        self.performance_metrics["province_fill"] = (time.perf_counter() - render_start) * 1000

        # Track province connection renderer time
        render_start = time.perf_counter()
        if self.render_connections:
            self.province_connection_renderer.render()
        self.performance_metrics["province_connections"] = (time.perf_counter() - render_start) * 1000

        # Track province border renderer time
        render_start = time.perf_counter()
        self.province_border_renderer.render()
        self.performance_metrics["province_borders"] = (time.perf_counter() - render_start) * 1000
        
        # Track world text renderer time
        render_start = time.perf_counter()
        self.world_text_renderer.render()
        self.performance_metrics["world_text"] = (time.perf_counter() - render_start) * 1000
        
        self.performance_metrics["render_frame"] = (time.perf_counter() - frame_start) * 1000

    def resizeGL(self, w: int, h: int):
        """
        Handle widget resize events.

        Args:
            w: New width in pixels
            h: New height in pixels
        """
        gl.glViewport(0, 0, w, h)
        self.render_frame()

    def minimumSizeHint(self) -> QSize:
        return QSize(200, 200)

    def render_frame(self):
        # Render manually
        self._manual_render_mode = True
        self.makeCurrent()
        self.paintGL()
        self.doneCurrent()

        # Blit to widget once
        self.update()
        self._manual_render_mode = False

    def get_province_id_at_world_position(self, world_x: float, world_y: float) -> int | None:
        """Delegate province picking to the picker helper."""
        return self.province_picker.get_province_id_at_world_position(world_x, world_y)

    def apply_hook_events(self, events: dict[ReplayHookTag, list[ReplayHookEvent]]):
        if ReplayHookTag.ProvinceChanged in events:
            self.province_fill_renderer.handle_province_change_events(events[ReplayHookTag.ProvinceChanged])

    def cleanup(self):
        """Clean up OpenGL resources."""
        self.makeCurrent()
        self.world_text_renderer.cleanup()
        self.province_picker.cleanup()
        self.doneCurrent()
    
    def get_performance_metrics(self):
        """
        Get the current performance metrics.
        
        Returns:
            dict: Dictionary containing performance metrics in milliseconds
        """
        return self.performance_metrics.copy()


    def _initialize_world_labels(self):
        for province in self.ritf.get_provinces().values():
            if isinstance(province, SeaProvince):
                continue
            if province.province_state_id not in (
                ProvinceStateID.MAINLAND_CITY,
                ProvinceStateID.ANNEXED_CITY,
                ProvinceStateID.OCCUPIED_CITY,
            ):
                continue
            province_center = province.center_coordinate
            self.world_text_renderer.add_text(
                province.name,
                anchor_world=(province_center.x, province_center.y),
                color=CITY_LABEL_COLOR,
                outline_width=CITY_LABEL_OUTLINE_WIDTH,
                outline_color=CITY_LABEL_OUTLINE_COLOR,
                size_world=CITY_LABEL_SIZE,
                group=TextGroup.CITY_LABELS
            )

        for player in self.ritf.get_players().values():
            if player.nation_label_coord is None:
                logger.warning(f"Player {player.nation_name} has no nation label coordinates, skipping label")
                continue
            nation_label_coordinate = player.nation_label_coord.x, player.nation_label_coord.y
            nation_label_size = player.nation_label_size * 100
            self.world_text_renderer.add_text(
                player.nation_name,
                centered=True,
                shadow_offset=NATION_LABEL_SHADOW_OFFSET,
                shadow_color=NATION_LABEL_SHADOW_COLOR,
                anchor_world=nation_label_coordinate,
                color=NATION_LABEL_COLOR,
                size_world=nation_label_size,
                group=TextGroup.NATION_LABELS
            )
