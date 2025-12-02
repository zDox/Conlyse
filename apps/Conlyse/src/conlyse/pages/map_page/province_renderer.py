"""
Province Renderer
=================
Renders provinces on the map using OpenGL shaders with GPU-stored data.

Author: Copilot
Date: 2025-12-02
"""

from __future__ import annotations

from typing import Any
from typing import Dict
from typing import List
from typing import Set
from typing import TYPE_CHECKING
from typing import Tuple

import numpy as np
from OpenGL.GL import GL_ARRAY_BUFFER
from OpenGL.GL import GL_BLEND
from OpenGL.GL import GL_COMPILE_STATUS
from OpenGL.GL import GL_FALSE
from OpenGL.GL import GL_FLOAT
from OpenGL.GL import GL_FRAGMENT_SHADER
from OpenGL.GL import GL_LINK_STATUS
from OpenGL.GL import GL_ONE_MINUS_SRC_ALPHA
from OpenGL.GL import GL_SRC_ALPHA
from OpenGL.GL import GL_STATIC_DRAW
from OpenGL.GL import GL_TRIANGLES
from OpenGL.GL import GL_VERTEX_SHADER
from OpenGL.GL import glAttachShader
from OpenGL.GL import glBindBuffer
from OpenGL.GL import glBindVertexArray
from OpenGL.GL import glBlendFunc
from OpenGL.GL import glBufferData
from OpenGL.GL import glCompileShader
from OpenGL.GL import glCreateProgram
from OpenGL.GL import glCreateShader
from OpenGL.GL import glDeleteBuffers
from OpenGL.GL import glDeleteProgram
from OpenGL.GL import glDeleteShader
from OpenGL.GL import glDeleteVertexArrays
from OpenGL.GL import glDrawArrays
from OpenGL.GL import glEnable
from OpenGL.GL import glEnableVertexAttribArray
from OpenGL.GL import glGenBuffers
from OpenGL.GL import glGenVertexArrays
from OpenGL.GL import glGetAttribLocation
from OpenGL.GL import glGetProgramInfoLog
from OpenGL.GL import glGetProgramiv
from OpenGL.GL import glGetShaderInfoLog
from OpenGL.GL import glGetShaderiv
from OpenGL.GL import glGetUniformLocation
from OpenGL.GL import glIsBuffer
from OpenGL.GL import glLinkProgram
from OpenGL.GL import glShaderSource
from OpenGL.GL import glUniform4f
from OpenGL.GL import glUniformMatrix4fv
from OpenGL.GL import glUseProgram
from OpenGL.GL import glVertexAttribPointer

from conlyse.logger import get_logger
from conlyse.pages.map_page.entity_renderer import EntityRenderer

if TYPE_CHECKING:
    from conlyse.pages.map_page.camera import Camera

logger = get_logger()


# Vertex shader: transforms world coordinates to screen coordinates
VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec2 position;
layout(location = 1) in vec4 color;

out vec4 fragColor;

uniform mat4 transform;

void main() {
    vec4 worldPos = vec4(position, 0.0, 1.0);
    gl_Position = transform * worldPos;
    fragColor = color;
}
"""

# Fragment shader: outputs the color
FRAGMENT_SHADER = """
#version 330 core
in vec4 fragColor;
out vec4 outColor;

void main() {
    outColor = fragColor;
}
"""


class ProvinceGPUData:
    """Stores GPU buffer data for a single province."""
    
    def __init__(self, province_id: int):
        self.province_id = province_id
        self.bounds = (0.0, 0.0, 0.0, 0.0)  # min_x, max_x, min_y, max_y (world space)
        self.vao = None  # Vertex Array Object
        self.vbo = None  # Vertex Buffer Object
        self.vertex_count = 0
        self.color = (0.8, 0.8, 0.8, 0.4)  # RGBA color
        

class ProvinceRenderer(EntityRenderer):
    """
    Renders provinces with their borders and colors using OpenGL shaders.
    
    This renderer uploads province geometry to GPU and uses shaders for
    efficient rendering with transformation matrices.
    """

    def __init__(self):
        """Initialize the province renderer."""
        super().__init__()
        self.province_data: Dict[int, ProvinceGPUData] = {}
        self.dirty_provinces: Set[int] = set()
        self._needs_full_rebuild = False
        
        # Shader program and uniform locations
        self.shader_program = None
        self.transform_loc = None
        
        # Pre-allocated matrix for performance
        self._transform_matrix = np.eye(4, dtype=np.float32)

    def _compile_shader(self, source: str, shader_type) -> int:
        """
        Compile a shader from source code.

        Args:
            source: Shader source code
            shader_type: GL_VERTEX_SHADER or GL_FRAGMENT_SHADER

        Returns:
            Compiled shader handle

        Raises:
            RuntimeError: If compilation fails
        """
        shader = glCreateShader(shader_type)
        glShaderSource(shader, source)
        glCompileShader(shader)
        
        # Check compilation status
        if glGetShaderiv(shader, GL_COMPILE_STATUS) == GL_FALSE:
            error = glGetShaderInfoLog(shader).decode()
            glDeleteShader(shader)
            raise RuntimeError(f"Shader compilation failed: {error}")
        
        return shader

    def _create_shader_program(self) -> int:
        """
        Create and link the shader program.

        Returns:
            Shader program handle

        Raises:
            RuntimeError: If linking fails
        """
        vertex_shader = self._compile_shader(VERTEX_SHADER, GL_VERTEX_SHADER)
        fragment_shader = self._compile_shader(FRAGMENT_SHADER, GL_FRAGMENT_SHADER)
        
        program = glCreateProgram()
        glAttachShader(program, vertex_shader)
        glAttachShader(program, fragment_shader)
        glLinkProgram(program)
        
        # Check link status
        if glGetProgramiv(program, GL_LINK_STATUS) == GL_FALSE:
            error = glGetProgramInfoLog(program).decode()
            glDeleteProgram(program)
            glDeleteShader(vertex_shader)
            glDeleteShader(fragment_shader)
            raise RuntimeError(f"Shader linking failed: {error}")
        
        # Shaders can be deleted after linking
        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)
        
        return program

    def initialize(self):
        """Initialize OpenGL resources for province rendering."""
        try:
            # Check OpenGL version
            from OpenGL.GL import glGetString, GL_VERSION
            version = glGetString(GL_VERSION)
            logger.info(f"OpenGL version: {version}")
            
            # Enable blending for transparency
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            # Create shader program
            self.shader_program = self._create_shader_program()
            
            # Get uniform locations
            self.transform_loc = glGetUniformLocation(self.shader_program, "transform")
            
            self._initialized = True
            logger.info("Province renderer initialized with shaders")
        except Exception as e:
            logger.error(f"Failed to initialize province renderer: {e}", exc_info=True)
            self._initialized = False
            raise

    def set_province_color(self, province_id: int, color: Tuple[float, float, float, float]):
        """
        Set the color for a specific province and mark it as dirty.

        Args:
            province_id: Province ID
            color: RGBA color (values 0-1)
        """
        if province_id in self.province_data:
            old_color = self.province_data[province_id].color
            if old_color != color:
                self.province_data[province_id].color = color
        self.dirty_provinces.add(province_id)

    def mark_province_dirty(self, province_id: int):
        """
        Mark a province as dirty, requiring GPU buffer rebuild.
        
        This should be called when a province changes ownership or attributes.

        Args:
            province_id: Province ID that changed
        """
        self.dirty_provinces.add(province_id)
        logger.debug(f"Province {province_id} marked as dirty")

    def _calculate_bounds(self, border_points: List[Tuple[float, float]]) -> Tuple[float, float, float, float]:
        """
        Calculate bounding box for a list of points.

        Args:
            border_points: List of (x, y) points

        Returns:
            Tuple of (min_x, max_x, min_y, max_y)
        """
        if not border_points:
            return (0, 0, 0, 0)
        
        x_coords, y_coords = zip(*border_points)
        return (min(x_coords), max(x_coords), min(y_coords), max(y_coords))

    def _triangulate_polygon(self, coords: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        Triangulate a polygon using simple fan triangulation.
        
        Note: This uses fan triangulation which works for convex polygons.
        For complex/concave polygons, a more robust triangulation algorithm
        would be needed (e.g., ear clipping or Delaunay triangulation).
        
        Args:
            coords: List of (x, y) coordinates forming a polygon
            
        Returns:
            List of vertices for triangles
        """
        if len(coords) < 3:
            return []
        
        # Simple fan triangulation from first vertex
        triangles = []
        for i in range(1, len(coords) - 1):
            triangles.extend([coords[0], coords[i], coords[i + 1]])
        
        return triangles

    def _build_province_gpu_data(self, province_id: int, province: Any, color: Tuple[float, float, float, float]):
        """
        Build GPU data for a single province and upload to GPU.
        
        Creates VAO and VBO with province geometry stored on GPU.

        Args:
            province_id: Province ID
            province: Province object with static_data.borders
            color: RGBA color for the province
        """
        if not hasattr(province, 'static_data') or not hasattr(province.static_data, 'borders'):
            return

        # Get world coordinates
        world_coords = [(point.x, point.y) for point in province.static_data.borders]
        if not world_coords:
            return

        # Calculate bounds in world space
        bounds = self._calculate_bounds(world_coords)

        # Get or create province data
        if province_id not in self.province_data:
            self.province_data[province_id] = ProvinceGPUData(province_id)
        
        pdata = self.province_data[province_id]
        pdata.bounds = bounds
        pdata.color = color

        # Triangulate the polygon for GPU rendering
        triangulated = self._triangulate_polygon(world_coords)
        if not triangulated:
            return

        # Create vertex data: position (x, y) + color (r, g, b, a)
        vertices = []
        for x, y in triangulated:
            vertices.extend([x, y, color[0], color[1], color[2], color[3]])
        
        vertex_data = np.array(vertices, dtype=np.float32)

        # Delete old GPU buffers if they exist
        if pdata.vbo is not None and glIsBuffer(pdata.vbo):
            glDeleteBuffers(1, [pdata.vbo])
        if pdata.vao is not None:
            try:
                glDeleteVertexArrays(1, [pdata.vao])
            except:
                pass  # Ignore errors if context is invalid

        # Create VAO
        try:
            pdata.vao = glGenVertexArrays(1)
            if pdata.vao == 0:
                logger.error("Failed to generate VAO (returned 0)")
                return
            glBindVertexArray(pdata.vao)
        except Exception as e:
            logger.error(f"Error creating VAO: {e}")
            return

        # Create VBO and upload data
        pdata.vbo = glGenBuffers(1)
        if pdata.vbo == 0:
            logger.error("Failed to generate VBO (returned 0)")
            glBindVertexArray(0)
            return
            
        glBindBuffer(GL_ARRAY_BUFFER, pdata.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data, GL_STATIC_DRAW)

        # Set up vertex attributes
        # Position attribute (location = 0)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, False, 6 * 4, None)  # 6 floats per vertex, stride 24 bytes
        
        # Color attribute (location = 1)
        glEnableVertexAttribArray(1)
        from ctypes import c_void_p
        glVertexAttribPointer(1, 4, GL_FLOAT, False, 6 * 4, c_void_p(8))  # offset 8 bytes

        pdata.vertex_count = len(triangulated)

        # Unbind
        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def _rebuild_dirty_provinces(self, provinces: Dict[int, Any], province_colors: Dict[int, Tuple[float, float, float, float]]):
        """
        Rebuild GPU data for provinces that have changed.

        Args:
            provinces: Dictionary of province_id -> province object
            province_colors: Dictionary of province_id -> color
        """
        if not self.dirty_provinces:
            return

        for province_id in list(self.dirty_provinces):
            if province_id in provinces:
                color = province_colors.get(province_id, (0.8, 0.8, 0.8, 0.4))
                self._build_province_gpu_data(province_id, provinces[province_id], color)
        
        self.dirty_provinces.clear()
        logger.debug(f"Rebuilt GPU data for dirty provinces")

    def _build_all_data(self, provinces: Dict[int, Any], province_colors: Dict[int, Tuple[float, float, float, float]]):
        """
        Build GPU data for all provinces (initial load or full rebuild).

        Args:
            provinces: Dictionary of province_id -> province object
            province_colors: Dictionary of province_id -> color
        """
        logger.info(f"Building GPU data for {len(provinces)} provinces")
        for province_id, province in provinces.items():
            color = province_colors.get(province_id, (0.8, 0.8, 0.8, 0.4))
            self._build_province_gpu_data(province_id, province, color)
        self._needs_full_rebuild = False
        logger.info("Province GPU data upload complete")

    def update_provinces(self, provinces: Dict[int, Any], province_colors: Dict[int, Tuple[float, float, float, float]]):
        """
        Update province data - call this when provinces are first loaded or change.

        Args:
            provinces: Dictionary of province_id -> province object
            province_colors: Dictionary of province_id -> color
        """
        if self._needs_full_rebuild or not self.province_data:
            self._build_all_data(provinces, province_colors)
        else:
            self._rebuild_dirty_provinces(provinces, province_colors)

    def _create_transform_matrix(self, camera: Camera) -> np.ndarray:
        """
        Create transformation matrix from world space to screen space.
        
        Args:
            camera: Camera for coordinate transformations
            
        Returns:
            4x4 transformation matrix (updates pre-allocated matrix)
        """
        # Create transformation matrix that converts world coordinates to screen coordinates
        # This combines translation, scaling (zoom), and projection
        
        # Calculate scale factors
        scale_x = camera.zoom * camera.scale_factor
        scale_y = camera.zoom * camera.scale_factor * 0.8  # VERTICAL_ANGLE_SCALE
        
        # Calculate translation
        # Screen center is at (screen_width/2, screen_height/2)
        # World point (camera.x, camera.y) should map to screen center
        translate_x = camera.screen_width / 2 - camera.x * scale_x
        translate_y = camera.screen_height / 2 - camera.y * scale_y
        
        # Create transformation matrix (column-major for OpenGL)
        # This transforms world coordinates to screen pixel coordinates
        transform = np.array([
            [scale_x, 0, 0, 0],
            [0, scale_y, 0, 0],
            [0, 0, 1, 0],
            [translate_x, translate_y, 0, 1]
        ], dtype=np.float32)
        
        # Convert screen coordinates to NDC (Normalized Device Coordinates) for OpenGL
        # NDC range is -1 to 1 for both x and y
        ndc_matrix = np.array([
            [2.0 / camera.screen_width, 0, 0, 0],
            [0, -2.0 / camera.screen_height, 0, 0],  # Flip Y axis
            [0, 0, 1, 0],
            [-1, 1, 0, 1]
        ], dtype=np.float32)
        
        # Combine transformations into pre-allocated matrix
        np.dot(ndc_matrix, transform, out=self._transform_matrix)
        
        return self._transform_matrix

    def render(self, camera: Camera, provinces: Dict[int, Any]):
        """
        Render provinces using GPU-stored data and shaders.
        
        Province geometry is stored on GPU. Only transformation matrix is updated per frame.

        Args:
            camera: Camera for coordinate transformations
            provinces: Dictionary of province_id -> province object (only needed for initial load)
        """
        if not self._initialized or self.shader_program is None:
            return

        visible_rect = camera.get_visible_rect()

        # Use shader program
        glUseProgram(self.shader_program)
        
        # Create and set transformation matrix
        transform = self._create_transform_matrix(camera)
        glUniformMatrix4fv(self.transform_loc, 1, False, transform)

        # Render each province
        for province_id, pdata in self.province_data.items():
            # Frustum culling in world space
            min_x, max_x, min_y, max_y = pdata.bounds
            if (max_x < visible_rect[0] or min_x > visible_rect[2] or
                max_y < visible_rect[1] or min_y > visible_rect[3]):
                continue

            if pdata.vao is None or pdata.vao == 0 or pdata.vertex_count == 0:
                continue

            try:
                # Bind VAO and draw
                glBindVertexArray(pdata.vao)
                glDrawArrays(GL_TRIANGLES, 0, pdata.vertex_count)
            except Exception as e:
                logger.error(f"Error rendering province {province_id}: {e}")
                continue

        # Unbind
        glBindVertexArray(0)
        glUseProgram(0)

    def cleanup(self):
        """Clean up GPU resources."""
        try:
            # Delete all GPU buffers
            for pdata in self.province_data.values():
                try:
                    if pdata.vbo is not None and glIsBuffer(pdata.vbo):
                        glDeleteBuffers(1, [pdata.vbo])
                except:
                    pass  # Ignore errors if context is invalid
                
                try:
                    if pdata.vao is not None:
                        glDeleteVertexArrays(1, [pdata.vao])
                except:
                    pass  # Ignore errors if context is invalid
            
            # Delete shader program
            if self.shader_program is not None:
                try:
                    glDeleteProgram(self.shader_program)
                except:
                    pass  # Ignore errors if context is invalid
                self.shader_program = None
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
        finally:
            self.province_data.clear()
            self.dirty_provinces.clear()
            self._initialized = False
            logger.info("Province renderer cleaned up")


def get_distinct_color(index: int, total: int) -> Tuple[float, float, float, float]:
    """
    Generate a distinct color for a given index.

    Args:
        index: Index of the color
        total: Total number of colors needed

    Returns:
        RGBA color tuple (values 0-1)
    """
    if total == 0:
        return (0.5, 0.5, 0.5, 0.4)
    
    # Use golden ratio for good color distribution
    golden_ratio = 0.618033988749895
    hue = (index * golden_ratio) % 1.0
    
    # Convert HSV to RGB (S=0.7, V=0.9 for nice colors)
    h = hue * 6.0
    c = 0.7 * 0.9
    x = c * (1 - abs((h % 2) - 1))
    m = 0.9 - c
    
    if h < 1:
        r, g, b = c, x, 0
    elif h < 2:
        r, g, b = x, c, 0
    elif h < 3:
        r, g, b = 0, c, x
    elif h < 4:
        r, g, b = 0, x, c
    elif h < 5:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    
    return (r + m, g + m, b + m, 0.6)
