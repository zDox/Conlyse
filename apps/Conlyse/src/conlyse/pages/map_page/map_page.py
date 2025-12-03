import ctypes
import logging

import numpy as np
import OpenGL.GL as gl
from PyQt6.QtWidgets import QApplication
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

logger = logging.getLogger(__name__)

vertex_code = '''
#version 410 core
layout(location = 0) in vec2 position;
void main()
{
  gl_Position = vec4(position, 0.0, 1.0);
}
'''

fragment_code = '''
#version 410 core
out vec4 fragColor;
void main()
{
  fragColor = vec4(1.0, 0.0, 0.0, 1.0);
}
'''

class MinimalGLWidget(QOpenGLWidget):
    def initializeGL(self):
        # Compile shaders and link program
        self.program = gl.glCreateProgram()
        vertex = gl.glCreateShader(gl.GL_VERTEX_SHADER)
        fragment = gl.glCreateShader(gl.GL_FRAGMENT_SHADER)

        gl.glShaderSource(vertex, vertex_code)
        gl.glCompileShader(vertex)
        if not gl.glGetShaderiv(vertex, gl.GL_COMPILE_STATUS):
            error = gl.glGetShaderInfoLog(vertex).decode()
            logger.error("Vertex shader compilation error: %s", error)

        gl.glShaderSource(fragment, fragment_code)
        gl.glCompileShader(fragment)
        if not gl.glGetShaderiv(fragment, gl.GL_COMPILE_STATUS):
            error = gl.glGetShaderInfoLog(fragment).decode()
            raise RuntimeError(f"Fragment shader compilation error: {error}")

        gl.glAttachShader(self.program, vertex)
        gl.glAttachShader(self.program, fragment)
        gl.glLinkProgram(self.program)

        if not gl.glGetProgramiv(self.program, gl.GL_LINK_STATUS):
            raise RuntimeError(gl.glGetProgramInfoLog(self.program))

        gl.glDeleteShader(vertex)
        gl.glDeleteShader(fragment)

        gl.glUseProgram(self.program)

        # Prepare vertex data
        self.data = np.array([
            -1.0,  1.0,
             1.0, -1.0,
            -1.0, -1.0,
             1.0, -1.0
        ], dtype=np.float32)

        self.vao = gl.glGenVertexArrays(1)
        gl.glBindVertexArray(self.vao)

        self.vbo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, self.data.nbytes, self.data, gl.GL_DYNAMIC_DRAW)

        loc = gl.glGetAttribLocation(self.program, b"position")
        gl.glEnableVertexAttribArray(loc)
        gl.glVertexAttribPointer(loc, 2, gl.GL_FLOAT, False, 0, ctypes.c_void_p(0))

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glBindVertexArray(0)

        gl.glClearColor(0.1, 0.1, 0.1, 1.0)

    def paintGL(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glUseProgram(self.program)
        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, 4)
        gl.glBindVertexArray(0)

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
