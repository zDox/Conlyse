import ctypes

import OpenGL.GL as gl
import numpy as np

from conlyse.logger import get_logger
from conlyse.pages.map_page.opengl_types import OpenGLTypes
from conlyse.pages.map_page.shader import Shader
from conlyse.pages.map_page.shader import ShaderType
from conlyse.pages.map_page.shader_program import ShaderProgram
from conlyse.pages.map_page.vertex_array_object import VertexArrayObject
from conlyse.pages.map_page.vertex_buffer_object import BufferUsageType
from conlyse.pages.map_page.vertex_buffer_object import VertexBufferObject

logger = get_logger()

VERTEX_DATA = np.array([
            # Triangle 1
            [100, 100],
            [200, 100],
            [150, 200],
            # Triangle 2
            [300, 300],
            [400, 300],
            [350, 400],
        ], dtype=np.float32)
PROVINCE_COLOR_DATA = np.array([
    1.0, 0.0, 0.0, 1.0,
    0.0, 1.0, 0.0, 1.0,
], dtype=np.float32)

PROVINCE_COLOR_INDEX_DATA = np.array([
    0,
    0,
    0,
    1,
    1,
    1,
], dtype=np.int32)

class ProvinceFillRenderer:
    def __init__(self, camera):
        self.camera = camera
        self.program = None
        self.vao = None
        self.positions_vbo = None
        self.u_province_colors = None
        self.province_color_index_vbo = None

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

        self.vao = VertexArrayObject()
        self.vao.bind()

        self.positions_vbo = VertexBufferObject(VERTEX_DATA, BufferUsageType.STATIC_DRAW)
        loc = gl.glGetAttribLocation(self.program.program_id, b"position")
        self.vao.add_vbo(self.positions_vbo, loc, 2, 0, 0)


        self.province_color_index_vbo = VertexBufferObject(PROVINCE_COLOR_INDEX_DATA, BufferUsageType.STATIC_DRAW)
        province_color_index_loc = gl.glGetAttribLocation(self.program.program_id, b"province_color_index")
        self.vao.add_vbo(self.province_color_index_vbo, province_color_index_loc, 2, 0, 0,
                         element_type=OpenGLTypes.INT)
        self.province_color_index_vbo.unbind()

        self.vao.unbind()

    def render(self):
        # Render the filled provinces
        self.program.use_program()

        vp = self.camera.get_view_projection_matrix()
        gl.glUniformMatrix3fv(gl.glGetUniformLocation(self.program.program_id, b"uViewProjection"), 1, gl.GL_TRUE, vp)

        gl.glUniform4fv(gl.glGetUniformLocation(self.program.program_id, b"uProvinceColors"),
                        len(PROVINCE_COLOR_DATA) // 4,
                        PROVINCE_COLOR_DATA)

        self.vao.bind()
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, len(VERTEX_DATA))
        self.vao.unbind()