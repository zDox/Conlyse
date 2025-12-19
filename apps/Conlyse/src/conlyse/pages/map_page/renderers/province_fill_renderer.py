from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

import OpenGL.GL as gl
from conflict_interface.hook_system.replay_hook_event import ReplayHookEvent

from conlyse.logger import get_logger
from conlyse.pages.map_page.map_views.map_view import MapView
from conlyse.pages.map_page.map_views.map_view_type import MapViewType
from conlyse.pages.map_page.opengl_wrapper.color_palette_texture import ColorPaletteTexture
from conlyse.pages.map_page.opengl_wrapper.opengl_types import OpenGLTypes
from conlyse.pages.map_page.opengl_wrapper.shader import Shader
from conlyse.pages.map_page.opengl_wrapper.shader import ShaderType
from conlyse.pages.map_page.opengl_wrapper.shader_program import ShaderProgram
from conlyse.pages.map_page.opengl_wrapper.vertex_array_object import VertexArrayObject
from conlyse.pages.map_page.province_mesh import ProvinceMesh

if TYPE_CHECKING:
    from conlyse.pages.map_page.map import Map

logger = get_logger()

script_dir = Path(__file__).parent

class ProvinceFillRenderer:
    """
    Handles rendering of province polygons with color fills.

    This renderer manages the OpenGL resources needed to draw provinces on the map,
    including shaders, vertex buffers, and textures for different visualization modes.
    """
    def __init__(self, map_widget: Map):
        self.map_widget = map_widget
        self.ritf = map_widget.ritf
        self.camera = map_widget.camera
        self.province_mesh = None
        self.map_views: dict[MapViewType, MapView | None] = {
            MapViewType.POLITICAL: None,
            MapViewType.TERRAIN: None,
            MapViewType.RESOURCE: None,
        }
        self.program: ShaderProgram | None = None

        self.vao: VertexArrayObject | None = None

        self.province_mesh = ProvinceMesh(self.ritf.game_state.states.map_state.map.static_map_data.locations)

        for map_view_type in self.map_views.keys():
            logger.debug(f"Initializing map view: {map_view_type}")
            map_view_class = map_view_type.value
            self.map_views[map_view_type] = map_view_class(self.ritf, self.province_mesh.max_province_id)
            self.map_views[map_view_type].build_color_data()


    def initialize(self):
        # Compile shaders and link program
        self.program = ShaderProgram()
        vertex_shader = Shader(ShaderType.VERTEX, script_dir/"shaders/province_fill_vertex.glsl")
        geometry_shader = Shader(ShaderType.GEOMETRY, script_dir/"shaders/province_geometry.glsl")
        fragment_shader = Shader(ShaderType.FRAGMENT, script_dir/"shaders/province_fill_fragment.glsl")

        for shader in (vertex_shader, geometry_shader, fragment_shader):
            shader.compile()
            self.program.attach_shader(shader)

        self.program.link_program()
        self.program.use_program()

        self.province_mesh.initialize()

        for map_view in self.map_views.values():
            map_view.initialize()


        self.vao = VertexArrayObject()
        self.vao.bind()
        loc = gl.glGetAttribLocation(self.program.program_id, b"position")
        self.vao.add_vbo(self.province_mesh.vertex_vbo, loc, 2, 0, 0)

        province_color_index_loc = gl.glGetAttribLocation(self.program.program_id, b"province_color_index")
        self.vao.add_vbo(self.province_mesh.province_color_index_vbo, province_color_index_loc, 1, 0, 0,
                         element_type=OpenGLTypes.INT)

        self.vao.unbind()

    def render(self, map_view_type: MapViewType):
        map_view = self.map_views.get(map_view_type)
        if map_view is None:
            logger.error(f"Map view {map_view_type} not found")
            return
        # Render the filled provinces
        self.program.use_program()
        self.camera.set_uniforms(self.program)

        # Camera / world uniforms
        self.program.set_uniform_1b("uEnableWrapping", self.map_widget.enable_wrapping)
        self.program.set_uniform_1f("uWorldWidth", self.map_widget.world_max_x - self.map_widget.world_min_x)
        self.program.set_uniform_1f("uWorldHeight", self.map_widget.world_max_y - self.map_widget.world_min_y)


        # Province color texture
        self.program.set_uniform_1i("uProvinceColorsTex", 0)
        self.program.set_uniform_1i("uNumColors", self.province_mesh.max_province_id + 1)

        gl.glActiveTexture(gl.GL_TEXTURE0)
        map_view.texture.bind()
        map_view.texture.upload_data_if_dirty()

        self.vao.bind()
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, len(self.province_mesh._vertex_data) // 2)
        map_view.texture.unbind()
        self.vao.unbind()

    def handle_province_change_events(self, events: list[ReplayHookEvent]):
        for map_view in self.map_views.values():
            t1 = time.perf_counter()
            map_view.update_provinces(events)
            t2 = time.perf_counter()
            self.map_widget.performance_metrics[f"{map_view.__class__.__name__.lower()}_update"] = (t2 - t1) * 1000
            map_view.update_texture()

    def render_palette(self, palette_texture: ColorPaletteTexture):
        """Render provinces using the provided palette texture (used for picking)."""
        self.program.use_program()
        self.camera.set_uniforms(self.program)

        self.program.set_uniform_1b("uEnableWrapping", self.map_widget.enable_wrapping)
        self.program.set_uniform_1f("uWorldWidth", self.map_widget.world_max_x - self.map_widget.world_min_x)
        self.program.set_uniform_1f("uWorldHeight", self.map_widget.world_max_y - self.map_widget.world_min_y)

        self.program.set_uniform_1i("uProvinceColorsTex", 0)
        self.program.set_uniform_1i("uNumColors", self.province_mesh.max_province_id + 1)

        gl.glActiveTexture(gl.GL_TEXTURE0)
        palette_texture.bind()
        palette_texture.upload_data_if_dirty()

        self.vao.bind()
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, len(self.province_mesh._vertex_data) // 2)
        palette_texture.unbind()
        self.vao.unbind()
