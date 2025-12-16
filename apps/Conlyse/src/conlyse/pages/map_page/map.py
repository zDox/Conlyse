import time

from OpenGL import GL as gl
from PySide6.QtCore import QSize
from PySide6.QtCore import Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QSizePolicy
from conflict_interface.hook_system.replay_hook_event import ReplayHookEvent
from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.logger import get_logger
from conlyse.pages.map_page.camera import Camera
from conlyse.pages.map_page.map_views.map_view_type import MapViewType
from conlyse.pages.map_page.renderers.province_border_renderer import ProvinceBorderRenderer
from conlyse.pages.map_page.renderers.province_connection_renderer import ProvinceConnectionRenderer
from conlyse.pages.map_page.renderers.province_fill_renderer import ProvinceFillRenderer

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

        self.active_map_view = MapViewType.POLITICAL
        self.render_connections = True

        # Track if we should skip paint events (to avoid double rendering)
        self._manual_render_mode = False
        
        # Performance tracking
        self.performance_metrics = {
            "last_jump_time": 0.0,
            "province_fill": 0.0,
            "province_connections": 0.0,
            "province_borders": 0.0,
            "terrainview_update": 0.0,
            "resourceview_update": 0.0,
            "politicalview_update": 0.0,
            "total_frame": 0.0
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
        if not self._manual_render_mode:
            super().paintEvent(event)

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
        gl.glClearColor(0.1, 0.1, 0.1, 1.0)
        # Enable blending
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        if self.enable_anti_aliasing:
            gl.glEnable(gl.GL_MULTISAMPLE)

    def paintGL(self):
        """Render the map. Called whenever the widget needs to be redrawn."""
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
        
        self.performance_metrics["total_frame"] = (time.perf_counter() - frame_start) * 1000

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

    def apply_hook_events(self, events: dict[str, list[ReplayHookEvent]]):
        if "province_change" in events:
            self.province_fill_renderer.handle_province_change_events(events["province_change"])

    
    def get_performance_metrics(self):
        """
        Get the current performance metrics.
        
        Returns:
            dict: Dictionary containing performance metrics in milliseconds
        """
        return self.performance_metrics.copy()