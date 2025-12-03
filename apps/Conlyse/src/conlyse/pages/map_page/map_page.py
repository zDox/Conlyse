import logging

import OpenGL.GL as gl
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import QApplication

from conlyse.pages.map_page.province_fill_renderer import ProvinceFillRenderer

logger = logging.getLogger(__name__)


class MinimalGLWidget(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.province_fill_renderer = ProvinceFillRenderer()
    def initializeGL(self):
        self.province_fill_renderer.initialize()
        gl.glClearColor(0.1, 0.1, 0.1, 1.0)

    def paintGL(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        self.province_fill_renderer.render()

    def resizeGL(self, w: int, h: int):
        gl.glViewport(0, 0, w, h)
        self.update()  # Force redraw on resize

if __name__ == '__main__':
    from PyQt6.QtGui import QSurfaceFormat

    app = QApplication([])

    fmt = QSurfaceFormat()
    fmt.setVersion(4, 1)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    QSurfaceFormat.setDefaultFormat(fmt)

    widget = MinimalGLWidget()
    widget.resize(600, 600)
    widget.show()
    app.exec()
