from OpenGL import GL as gl
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.pages.map_page.camera import Camera
from conlyse.pages.map_page.renderers.province_fill_renderer import ProvinceFillRenderer


class Map(QOpenGLWidget):
    def __init__(self, ritf: ReplayInterface):
        super().__init__()
        self.camera = Camera(self)
        self.province_fill_renderer = ProvinceFillRenderer(self.camera)
        self.ritf = ritf


    def handle_camera_move(self, dx: int, dy: int):
        self.camera.move(dx, dy)
        self.update()

    def initializeGL(self):
        self.province_fill_renderer.initialize(self.ritf.game_state.states.map_state.map.static_map_data.locations)
        gl.glClearColor(0.1, 0.1, 0.1, 1.0)

    def paintGL(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        self.province_fill_renderer.render()

    def resizeGL(self, w: int, h: int):
        gl.glViewport(0, 0, w, h)
        self.update()  # Force redraw on resize