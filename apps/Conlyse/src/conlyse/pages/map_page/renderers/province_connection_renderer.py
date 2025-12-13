from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from OpenGL import GL as gl
from conflict_interface.data_types.point import Point

from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.logger import get_logger
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


def build_vertex_data(graph: dict[Point, list[Point]]):
    """Build line segment vertex data for connections (width handled in shader)"""
    logger.debug(f"Building vertex data for province connections")

    vertices = []
    processed_segments = set()

    # Build simple line segments - geometry shader will handle width in screen space
    for origin, points in graph.items():
        for point in points:
            segment = tuple(sorted([(origin.x, origin.y), (point.x, point.y)]))
            if segment in processed_segments:
                continue
            processed_segments.add(segment)

            # Store as simple line segments (2 vertices per line)
            vertices.extend([origin.x, origin.y, point.x, point.y])

    logger.debug(f"Built {len(vertices) // 4} line segments for province connections")
    return np.array(vertices, dtype=np.float32)


class ProvinceConnectionRenderer:
    def __init__(self, map_widget: Map):
        self.map_widget = map_widget
        self.ritf: ReplayInterface = map_widget.ritf
        self.camera: Camera = map_widget.camera
        self.province_mesh = None
        self.program: ShaderProgram | None = None

        # Build simple line segments (no width - handled in shader)
        self.vertices = build_vertex_data(
            self.ritf.game_state.states.map_state.map.static_map_data.graph
        )

        self.num_of_vertices = 0
        self.vao = None
        self.vbo = None
        self.line_width_pixels = 0.5  # Width in screen pixels

    def initialize(self):
        logger.debug("Initializing province connection")
        self.program = ShaderProgram()
        vertex_shader = Shader(ShaderType.VERTEX, script_dir / "shaders/province_connection_vertex.glsl")
        geometry_shader = Shader(ShaderType.GEOMETRY, script_dir / "shaders/province_connection_geometry.glsl")
        fragment_shader = Shader(ShaderType.FRAGMENT, script_dir / "shaders/province_connection_fragment.glsl")

        for shader in (vertex_shader, geometry_shader, fragment_shader):
            shader.compile()
            self.program.attach_shader(shader)

        self.program.link_program()
        self.program.use_program()

        self.num_of_vertices = len(self.vertices)
        self.vao = VertexArrayObject()
        self.vao.bind()
        self.vbo = VertexBufferObject(self.vertices, BufferUsageType.STATIC_DRAW)

        loc = gl.glGetAttribLocation(self.program.program_id, b"position")
        self.vao.add_vbo(self.vbo, loc, 2, 0, 0)

        self.vao.unbind()

    def render(self):
        self.program.use_program()
        self.camera.set_uniforms(self.program)
        self.program.set_uniform_4f("lineColor", *CONNECTION_LINE_COLOR)
        self.program.set_uniform_1f("uWorldWidth", self.map_widget.world_width)
        self.program.set_uniform_1b("uEnableWrapping", self.map_widget.enable_wrapping)

        # Pass screen dimensions for pixel-width calculation
        viewport = gl.glGetIntegerv(gl.GL_VIEWPORT)
        screen_width = viewport[2]
        screen_height = viewport[3]
        self.program.set_uniform_2f("uScreenSize", screen_width, screen_height)
        self.program.set_uniform_1f("uLineWidthPixels", self.line_width_pixels)

        self.vao.bind()
        gl.glDrawArrays(gl.GL_LINES, 0, self.num_of_vertices // 2)
        self.vao.unbind()