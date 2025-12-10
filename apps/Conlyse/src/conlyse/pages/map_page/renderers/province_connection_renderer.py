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

def normalize_vec2(v):
    """Normalize a 2D vector"""
    length = np.sqrt(v[0] ** 2 + v[1] ** 2)
    if length < 1e-6:
        return np.array([0.0, 0.0])
    return v / length


def build_line_segment_triangles(p1, p2, width):
    """Build quad triangles for a line segment from p1 to p2"""
    direction = np.array([p2[0] - p1[0], p2[1] - p1[1]])
    direction = normalize_vec2(direction)

    perpendicular = np.array([-direction[1], direction[0]]) * (width / 2.0)

    v1 = [p1[0] + perpendicular[0], p1[1] + perpendicular[1]]
    v2 = [p1[0] - perpendicular[0], p1[1] - perpendicular[1]]
    v3 = [p2[0] + perpendicular[0], p2[1] + perpendicular[1]]
    v4 = [p2[0] - perpendicular[0], p2[1] - perpendicular[1]]

    return [
        *v1, *v2, *v3,
        *v2, *v4, *v3
    ]


def build_vertex_data(graph: dict[Point, list[Point]], width=3.0):
    """Build triangle vertex data for connections"""
    logger.debug(f"Building vertex data for province connections")

    vertices = []
    processed_segments = set()

    # Build line segments only - geometry shader will handle wrapping
    for origin, points in graph.items():
        for point in points:
            segment = tuple(sorted([(origin.x, origin.y), (point.x, point.y)]))
            if segment in processed_segments:
                continue
            processed_segments.add(segment)

            p1 = np.array([origin.x, origin.y])
            p2 = np.array([point.x, point.y])

            # Build line segment as-is, no wrapping logic here
            vertices.extend(build_line_segment_triangles(p1, p2, width))

    logger.debug(f"Built {len(vertices) // 6} triangles for province connections")
    return np.array(vertices, dtype=np.float32)


class ProvinceConnectionRenderer:
    def __init__(self, map_widget: Map):
        self.map_widget = map_widget
        self.ritf: ReplayInterface = map_widget.ritf
        self.camera: Camera = map_widget.camera
        self.province_mesh = None
        self.program: ShaderProgram | None = None

        # Build with base width (will be scaled by zoom in shader)
        self.vertices = build_vertex_data(
            self.ritf.game_state.states.map_state.map.static_map_data.graph,
            width=5.0
        )

        self.num_of_vertices = 0
        self.vao = None
        self.vbo = None

    def initialize(self):
        logger.debug("Initializing province connection")
        self.program = ShaderProgram()
        vertex_shader = Shader(ShaderType.VERTEX, script_dir / "shaders/province_connection_vertex.glsl")
        geometry_shader = Shader(ShaderType.GEOMETRY, script_dir / "shaders/province_connection_geometry.glsl")
        fragment_shader = Shader(ShaderType.FRAGMENT, script_dir / "shaders/province_connection_fragment.glsl")

        vertex_shader.compile()
        geometry_shader.compile()
        fragment_shader.compile()

        self.program.attach_shader(vertex_shader)
        self.program.attach_shader(geometry_shader)
        self.program.attach_shader(fragment_shader)
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

        self.vao.bind()
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, self.num_of_vertices // 2)
        self.vao.unbind()
