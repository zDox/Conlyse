
from OpenGL import GL as gl
from PyQt6.QtCore import QSize
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.logger import get_logger
from conlyse.pages.map_page.camera import Camera
from conlyse.pages.map_page.map_views.map_view_type import MapViewType
from conlyse.pages.map_page.renderers.province_connection_renderer import ProvinceConnectionRenderer
from conlyse.pages.map_page.renderers.province_fill_renderer import ProvinceFillRenderer

logger = get_logger()

class Map(QOpenGLWidget):
    def __init__(self, ritf: ReplayInterface, main_config, parent=None):
        super().__init__(parent=parent)
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

        self.camera = Camera(self)
        self.province_fill_renderer = ProvinceFillRenderer(self)
        self.province_connection_renderer = ProvinceConnectionRenderer(self)

        self.active_map_view = MapViewType.POLITICAL
        self.render_connections = True

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

    def handle_camera_move(self, dx: int, dy: int):
        """
        Handle camera movement based on user input.
        Args:
            dx: Horizontal movement in screen pixels
            dy: Vertical movement in screen pixels
        """
        self.camera.move(dx, dy)

    def initializeGL(self):
        """Initialize OpenGL resources. Called once when the widget is first shown."""
        self.province_fill_renderer.initialize()
        self.province_connection_renderer.initialize()
        gl.glClearColor(0.1, 0.1, 0.1, 1.0)
        # Enable blending
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        if self.enable_anti_aliasing:
            gl.glEnable(gl.GL_MULTISAMPLE)

    def paintGL(self):
        """Render the map. Called whenever the widget needs to be redrawn."""
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        self.province_fill_renderer.render(self.active_map_view)

        if self.render_connections:
            self.province_connection_renderer.render()

    def resizeGL(self, w: int, h: int):
        """
        Handle widget resize events.

        Args:
            w: New width in pixels
            h: New height in pixels
        """
        gl.glViewport(0, 0, w, h)

    def sizeHint(self):
        return QSize(800, 600)