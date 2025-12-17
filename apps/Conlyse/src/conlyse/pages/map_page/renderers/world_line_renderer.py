from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from OpenGL import GL as gl
from conflict_interface.data_types.point import Point

from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.logger import get_logger
from conlyse.pages.map_page.color_util import rgba_to_normalized
from conlyse.pages.map_page.constants import CONNECTION_LINE_COLOR
from conlyse.pages.map_page.opengl_wrapper.shader import Shader
from conlyse.pages.map_page.opengl_wrapper.shader import ShaderType
from conlyse.pages.map_page.opengl_wrapper.shader_program import ShaderProgram
from conlyse.pages.map_page.opengl_wrapper.vertex_array_object import VertexArrayObject
from conlyse.pages.map_page.opengl_wrapper.vertex_buffer_object import BufferUsageType
from conlyse.pages.map_page.opengl_wrapper.vertex_buffer_object import VertexBufferObject

if TYPE_CHECKING:
    from conlyse.pages.map_page.camera import Camera
    from conlyse.pages.map_page.map import Map

logger = get_logger()

script_dir = Path(__file__).parent


class WorldLineRenderer(ABC):
    def __init__(self, map_widget: Map):
        self.map_widget = map_widget
        self.ritf: ReplayInterface = map_widget.ritf
        self.camera: Camera = map_widget.camera
        self.program: ShaderProgram | None = None
        self.vertices = np.array([], dtype=np.float32)

        # Build simple line segments (no width - handled in shader)
        self.build_vertex_data(
            self.ritf.game_state.states.map_state.map
        )

        self.num_of_vertices = 0
        self.vao = None
        self.vbo = None

    @abstractmethod
    def build_vertex_data(self, map_data: Map):
        raise NotImplementedError("WorldLineRenderer.build_vertex_data must be implemented in a subclass")

    def initialize(self):
        self.program = ShaderProgram()
        vertex_shader = Shader(ShaderType.VERTEX, script_dir / "shaders/world_line_vertex.glsl")
        geometry_shader = Shader(ShaderType.GEOMETRY, script_dir / "shaders/world_line_geometry.glsl")
        fragment_shader = Shader(ShaderType.FRAGMENT, script_dir / "shaders/world_line_fragment.glsl")

        for shader in (vertex_shader, geometry_shader, fragment_shader):
            shader.compile()
            self.program.attach_shader(shader)

        self.program.link_program()
        self.program.use_program()

        self.vao = VertexArrayObject()
        self.vao.bind()
        self.vbo = VertexBufferObject(self.vertices, BufferUsageType.STATIC_DRAW)

        loc = gl.glGetAttribLocation(self.program.program_id, b"position")
        self.vao.add_vbo(self.vbo, loc, 2, 0, 0)

        self.vao.unbind()

    def update_vertices(self):
        self.vbo.bind()
        self.vbo.update_data(self.vertices)
        self.vbo.unbind()

    def render_lines(self, line_color: tuple[int, int, int, int], line_width_pixels: float):
        self.program.use_program()
        self.camera.set_uniforms(self.program)
        self.program.set_uniform_4f("lineColor", *rgba_to_normalized(line_color))
        self.program.set_uniform_1f("uWorldWidth", self.map_widget.world_width)
        self.program.set_uniform_1b("uEnableWrapping", self.map_widget.enable_wrapping)

        # Pass screen dimensions for pixel-width calculation
        viewport = gl.glGetIntegerv(gl.GL_VIEWPORT)
        screen_width = viewport[2]
        screen_height = viewport[3]
        self.program.set_uniform_2f("uScreenSize", screen_width, screen_height)
        self.program.set_uniform_1f("uLineWidthPixels", line_width_pixels)

        self.vao.bind()
        gl.glDrawArrays(gl.GL_LINES, 0, len(self.vertices) // 2)
        self.vao.unbind()