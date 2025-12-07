from pathlib import Path

import OpenGL.GL as gl
from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.logger import get_logger
from conlyse.pages.map_page.map_views.map_view import MapView
from conlyse.pages.map_page.map_views.map_view_type import MAPVIEWTYPE_TO_CLASS
from conlyse.pages.map_page.map_views.map_view_type import MapViewType
from conlyse.pages.map_page.map_views.political_view import PoliticalView
from conlyse.pages.map_page.map_views.terrain_view import TerrainView
from conlyse.pages.map_page.opengl_wrapper.opengl_types import OpenGLTypes
from conlyse.pages.map_page.opengl_wrapper.shader import Shader
from conlyse.pages.map_page.opengl_wrapper.shader import ShaderType
from conlyse.pages.map_page.opengl_wrapper.shader_program import ShaderProgram
from conlyse.pages.map_page.opengl_wrapper.vertex_array_object import VertexArrayObject
from conlyse.pages.map_page.province_mesh import ProvinceMesh

logger = get_logger()


class ProvinceFillRenderer:
    def __init__(self, ritf: ReplayInterface, camera):
        self.ritf = ritf
        self.camera = camera
        self.province_mesh = None
        self.map_views: dict[MapViewType, MapView | None] = {
            MapViewType.POLITICAL: None,
            MapViewType.TERRAIN: None
        }
        self.program = None

        self.vao = None


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
        self.province_mesh.initialize()

        for map_view_type in self.map_views.keys():
            logger.debug(f"Initializing map view: {map_view_type}")
            map_view_class = MAPVIEWTYPE_TO_CLASS[map_view_type]
            self.map_views[map_view_type] = map_view_class(self.ritf, self.province_mesh.max_province_id)
            self.map_views[map_view_type].build_color_data()
            self.map_views[map_view_type].initialize()


        self.vao = VertexArrayObject()
        self.vao.bind()
        loc = gl.glGetAttribLocation(self.program.program_id, b"position")
        self.vao.add_vbo(self.province_mesh.vertex_vbo, loc, 2, 0, 0)

        province_color_index_loc = gl.glGetAttribLocation(self.program.program_id, b"province_color_index")
        self.vao.add_vbo(self.province_mesh.province_color_index_vbo, province_color_index_loc, 1, 0, 0,
                         element_type=OpenGLTypes.INT)

        self.vao.unbind()

    def render(self, map_view_type: MapViewType):
        # Render the filled provinces
        self.program.use_program()

        vp = self.camera.get_view_projection_matrix()
        gl.glUniformMatrix3fv(gl.glGetUniformLocation(self.program.program_id, b"uViewProjection"), 1, gl.GL_TRUE, vp)

        gl.glUniform1i(gl.glGetUniformLocation(self.program.program_id, b"uProvinceColorsTex"), 0)
        gl.glUniform1i(gl.glGetUniformLocation(self.program.program_id, b"uNumColors"), self.province_mesh.max_province_id + 1)

        gl.glActiveTexture(gl.GL_TEXTURE0)
        self.map_views[map_view_type].texture.bind()

        self.vao.bind()
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, len(self.province_mesh._vertex_data) // 2)
        self.vao.unbind()