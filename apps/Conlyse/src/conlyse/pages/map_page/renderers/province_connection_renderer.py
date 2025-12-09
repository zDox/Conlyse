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


logger = get_logger()

script_dir = Path(__file__).parent


def build_vertex_data(graph: dict[Point, list[Point]]) -> np.ndarray:
    logger.debug(f"Building vertex data for province connections")
    vertices = []
    for origin, points in graph.items():
        for point in points:
            # Add line segment (2 vertices per line)
            vertices.extend([origin.x, origin.y])
            vertices.extend([point.x, point.y])
    logger.debug(f"Built {len(vertices) // 4} lines for province connections")
    return np.array(vertices, dtype=np.float32)

class ProvinceConnectionRenderer:
    def __init__(self, ritf: ReplayInterface, camera: Camera):
        self.ritf = ritf
        self.camera = camera
        self.province_mesh = None
        self.program: ShaderProgram | None = None

        self.vertices = build_vertex_data(self.ritf.game_state.states.map_state.map.static_map_data.graph)

        self.num_of_vertices = 0
        self.vao = None
        self.vbo = None



    def initialize(self):
        logger.debug("Initializing province connection")
        self.program = ShaderProgram()
        vertex_shader = Shader(ShaderType.VERTEX, script_dir/"shaders/province_connection_vertex_shader.glsl")
        fragment_shader = Shader(ShaderType.FRAGMENT, script_dir/"shaders/province_connection_fragment_shader.glsl")
        vertex_shader.compile()
        fragment_shader.compile()

        self.program.attach_shader(vertex_shader)
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
        self.program.set_uniform4f("lineColor", *CONNECTION_LINE_COLOR)
        # Enable line smoothing for better quality
        gl.glEnable(gl.GL_LINE_SMOOTH)
        gl.glHint(gl.GL_LINE_SMOOTH_HINT, gl.GL_NICEST)
        gl.glLineWidth(self.camera.zoom * 0.25)

        self.vao.bind()
        gl.glDrawArrays(gl.GL_LINES, 0, self.num_of_vertices // 2)
        self.vao.unbind()

        # Disable line smoothing after rendering
        gl.glDisable(gl.GL_LINE_SMOOTH)
