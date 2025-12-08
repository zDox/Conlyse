from OpenGL import GL as gl
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.pages.map_page.camera import Camera
from conlyse.pages.map_page.map_views.map_view_type import MapViewType
from conlyse.pages.map_page.renderers.province_fill_renderer import ProvinceFillRenderer


class Map(QOpenGLWidget):
    def __init__(self, ritf: ReplayInterface):
        super().__init__()
        self.ritf = ritf
        self.camera = Camera(self)
        self.province_fill_renderer = ProvinceFillRenderer(ritf, self.camera)
        self.active_map_view = MapViewType.POLITICAL


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
        gl.glClearColor(0.1, 0.1, 0.1, 1.0)

    def paintGL(self):
        """Render the map. Called whenever the widget needs to be redrawn."""
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        self.province_fill_renderer.render(self.active_map_view)

    def resizeGL(self, w: int, h: int):
        """
        Handle widget resize events.

        Args:
            w: New width in pixels
            h: New height in pixels
        """
        gl.glViewport(0, 0, w, h)
        self.update()  # Force redraw on resize