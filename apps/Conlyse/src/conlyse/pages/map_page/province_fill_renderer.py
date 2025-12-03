import ctypes

import OpenGL.GL as gl
import numpy as np

from conlyse.logger import get_logger
from conlyse.pages.map_page.shader import Shader
from conlyse.pages.map_page.shader import ShaderType
from conlyse.pages.map_page.shader_program import ShaderProgram

logger = get_logger()


class ProvinceFillRenderer:
    def __init__(self, camera):
        self.camera = camera
        # Prepare vertex data
        self.vertex_data = np.array([
            # Triangle 1
            [100, 100],
            [200, 100],
            [150, 200],
            # Triangle 2
            [300, 300],
            [400, 300],
            [350, 400],
        ], dtype=np.float32)
        self.color_data = np.array([
            1.0, 0.0, 0.0, 1.0,
            0.0, 1.0, 0.0, 1.0,
            0.0, 0.0, 1.0, 1.0,
            1.0, 0.0, 0.0, 1.0,
            0.0, 1.0, 0.0, 1.0,
            0.0, 0.0, 1.0, 1.0,
        ], dtype=np.float32)
        self.program = None
        self.vao = None
        self.positions_vbo = None
        self.colors_vbo = None

    def initialize(self):
        # Compile shaders and link program
        self.program = ShaderProgram()
        vertex_shader = Shader(ShaderType.VERTEX, "vertex_shader.glsl")
        fragment_shader = Shader(ShaderType.FRAGMENT, "fragment_shader.glsl")

        vertex_shader.compile()
        fragment_shader.compile()

        self.program.attach_shader(vertex_shader)
        self.program.attach_shader(fragment_shader)
        self.program.link_program()

        self.program.use_program()

        self.vao = gl.glGenVertexArrays(1)
        gl.glBindVertexArray(self.vao)

        self.positions_vbo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.positions_vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, self.vertex_data.nbytes, self.vertex_data, gl.GL_DYNAMIC_DRAW)

        loc = gl.glGetAttribLocation(self.program.program_id, b"position")
        gl.glEnableVertexAttribArray(loc)
        gl.glVertexAttribPointer(loc, 2, gl.GL_FLOAT, False, 0, ctypes.c_void_p(0))

        self.colors_vbo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.colors_vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, self.color_data.nbytes, self.color_data, gl.GL_DYNAMIC_DRAW)

        gl.glEnableVertexAttribArray(1)
        gl.glVertexAttribPointer(1, 4, gl.GL_FLOAT, False, 0, ctypes.c_void_p(0))

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glBindVertexArray(0)

    def render(self):
        # Render the filled provinces
        self.program.use_program()

        vp = self.camera.get_view_projection_matrix()
        gl.glUniformMatrix3fv(gl.glGetUniformLocation(self.program.program_id, "uViewProjection"), 1, gl.GL_TRUE, vp)

        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, len(self.vertex_data))
        gl.glBindVertexArray(0)