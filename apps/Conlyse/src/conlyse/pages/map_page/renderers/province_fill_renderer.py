from pathlib import Path

import OpenGL.GL as gl
from conflict_interface.data_types.map_state.static_province import StaticProvince
from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.logger import get_logger
from conlyse.pages.map_page.map_view import MapView

from conlyse.pages.map_page.map_views.map_view import MapViewType
from conlyse.pages.map_page.opengl_wrapper.opengl_types import OpenGLTypes
from conlyse.pages.map_page.opengl_wrapper.shader import Shader
from conlyse.pages.map_page.opengl_wrapper.shader import ShaderType
from conlyse.pages.map_page.opengl_wrapper.shader_program import ShaderProgram
from conlyse.pages.map_page.opengl_wrapper.vertex_array_object import VertexArrayObject
from conlyse.pages.map_page.opengl_wrapper.vertex_buffer_object import BufferUsageType
from conlyse.pages.map_page.opengl_wrapper.vertex_buffer_object import VertexBufferObject
from conlyse.pages.map_page.province_mesh import ProvinceMesh
from conlyse.pages.map_page.province_mesh_builder import prepare_provinces
from conlyse.pages.map_page.province_color_texture import ProvinceColorTexture

logger = get_logger()


class ProvinceFillRenderer:
    def __init__(self, ritf: ReplayInterface, camera):
        self.ritf = ritf
        self.camera = camera
        self.province_mesh = None
        self.map_views: dict[type(MapView), MapView] = {}
        self.active_map_view_type: MapViewType = MapViewType.POLITICAL
        self.program = None

        self.vao = None
        self.province_color_index_vbo = None

    def switch_map_view(self, map_view_type: MapViewType):
        if map_view_type not in self.map_views:
            raise ValueError(f"Map view type {map_view_type} not recognized.")
        self.active_map_view_type = map_view_type


    def initialize(self):
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

        self.province_mesh = ProvinceMesh(self.ritf.game_state.states.map_state.map.static_map_data.locations)

        for map_view in MapView:
            self.map_views[]



        self.vao = VertexArrayObject()
        self.vao.bind()

        self.vertex_data, province_color_index_data, self.province_color_data, max_province_id = prepare_provinces(locations)
        self.positions_vbo = VertexBufferObject(self.vertex_data, BufferUsageType.STATIC_DRAW)
        loc = gl.glGetAttribLocation(self.program.program_id, b"position")
        self.vao.add_vbo(self.positions_vbo, loc, 2, 0, 0)

        self.province_color_index_vbo = VertexBufferObject(province_color_index_data, BufferUsageType.STATIC_DRAW)
        province_color_index_loc = gl.glGetAttribLocation(self.program.program_id, b"province_color_index")
        self.vao.add_vbo(self.province_color_index_vbo, province_color_index_loc, 1, 0, 0,
                         element_type=OpenGLTypes.INT)
        self.province_color_index_vbo.unbind()
        self.t_province_colors = ProvinceColorTexture(self.province_color_data)


        self.vao.unbind()

    def render(self, view: MapView):
        # Render the filled provinces
        self.program.use_program()

        vp = self.camera.get_view_projection_matrix()
        gl.glUniformMatrix3fv(gl.glGetUniformLocation(self.program.program_id, b"uViewProjection"), 1, gl.GL_TRUE, vp)

        gl.glUniform1i(gl.glGetUniformLocation(self.program.program_id, b"uProvinceColorsTex"), 0)
        gl.glUniform1i(gl.glGetUniformLocation(self.program.program_id, b"uNumColors"), len(self.province_color_data) // 3)

        gl.glActiveTexture(gl.GL_TEXTURE0)
        self.t_province_colors.bind()

        self.vao.bind()
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, len(self.vertex_data))
        self.vao.unbind()