from time import sleep

from OpenGL import GL as gl
from PyQt6.QtCore import QSize
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.pages.map_page.camera import Camera
from conlyse.pages.map_page.map_views.map_view_type import MapViewType
from conlyse.pages.map_page.renderers.province_connection_renderer import ProvinceConnectionRenderer
from conlyse.pages.map_page.renderers.province_fill_renderer import ProvinceFillRenderer


class Map(QOpenGLWidget):
    def __init__(self, ritf: ReplayInterface, parent=None):
        super().__init__(parent=parent)
        self.ritf = ritf
        self.camera = Camera(self)
        self.province_fill_renderer = ProvinceFillRenderer(ritf, self.camera)
        self.province_connection_renderer = ProvinceConnectionRenderer(ritf, self.camera)

        self.active_map_view = MapViewType.POLITICAL
        self.render_connections = True

    def set_active_map_view(self, map_view: MapViewType):
        """
        Set the active map view type.

        Args:
            map_view: The MapViewType to set as active
        """
        self.active_map_view = map_view
        self.update()

    def handle_camera_move(self, dx: int, dy: int):
        """
        Handle camera movement based on user input.
        Args:
            dx: Horizontal movement in screen pixels
            dy: Vertical movement in screen pixels
        """
        self.camera.move(dx, dy)
        self.update()

    def initializeGL(self):
        """Initialize OpenGL resources. Called once when the widget is first shown."""
        self.province_fill_renderer.initialize()
        self.province_connection_renderer.initialize()
        gl.glClearColor(0.1, 0.1, 0.1, 1.0)
        # Enable blending
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

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