import ctypes
from pathlib import Path
import mapbox_earcut as earcut
import OpenGL.GL as gl
import numpy as np
from conflict_interface.data_types.map_state.static_province import StaticProvince

from conlyse.logger import get_logger
from conlyse.pages.map_page.opengl_wrapper.opengl_types import OpenGLTypes
from conlyse.pages.map_page.opengl_wrapper.shader import Shader
from conlyse.pages.map_page.opengl_wrapper.shader import ShaderType
from conlyse.pages.map_page.opengl_wrapper.shader_program import ShaderProgram
from conlyse.pages.map_page.opengl_wrapper.vertex_array_object import VertexArrayObject
from conlyse.pages.map_page.opengl_wrapper.vertex_buffer_object import BufferUsageType
from conlyse.pages.map_page.opengl_wrapper.vertex_buffer_object import VertexBufferObject
from conlyse.pages.map_page.province_mesh_builder import prepare_provinces

logger = get_logger()


class ProvinceFillRenderer:
    def __init__(self, camera):
        self.camera = camera
        self.program = None
        self.vertex_data = None

        self.vao = None
        self.positions_vbo = None
        self.u_province_colors = None
        self.province_color_index_vbo = None

    def initialize(self, locations: list[StaticProvince]):
        # Compile shaders and link program
        self.program = ShaderProgram()
        vertex_shader = Shader(ShaderType.VERTEX, Path("renderers/shaders/vertex_shader.glsl"))
        fragment_shader = Shader(ShaderType.FRAGMENT, Path("renderers/shaders/fragment_shader.glsl"))

        vertex_shader.compile()
        fragment_shader.compile()

        self.program.attach_shader(vertex_shader)
        self.program.attach_shader(fragment_shader)
        self.program.link_program()

        self.program.use_program()

        self.vao = VertexArrayObject()
        self.vao.bind()

        print("Preparing province mesh data...")
        self.vertex_data, province_color_index_data, self.u_province_colors, max_province_id = prepare_provinces(locations)

        self.positions_vbo = VertexBufferObject(self.vertex_data, BufferUsageType.STATIC_DRAW)
        loc = gl.glGetAttribLocation(self.program.program_id, b"position")
        self.vao.add_vbo(self.positions_vbo, loc, 2, 0, 0)

        print(self.vertex_data)
        self.province_color_index_vbo = VertexBufferObject(province_color_index_data, BufferUsageType.STATIC_DRAW)
        province_color_index_loc = gl.glGetAttribLocation(self.program.program_id, b"province_color_index")
        self.vao.add_vbo(self.province_color_index_vbo, province_color_index_loc, 1, 0, 0,
                         element_type=OpenGLTypes.INT)
        self.province_color_index_vbo.unbind()

        self.vao.unbind()

    def render(self):
        # Render the filled provinces
        self.program.use_program()

        vp = self.camera.get_view_projection_matrix()
        gl.glUniformMatrix3fv(gl.glGetUniformLocation(self.program.program_id, b"uViewProjection"), 1, gl.GL_TRUE, vp)

        gl.glUniform3fv(gl.glGetUniformLocation(self.program.program_id, b"uProvinceColors"),
                        len(self.u_province_colors) // 3,
                        self.u_province_colors)

        self.vao.bind()
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, len(self.vertex_data))
        self.vao.unbind()