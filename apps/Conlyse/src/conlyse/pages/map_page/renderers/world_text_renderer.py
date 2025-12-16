"""
WorldTextRenderer - Renders world-anchored text with screen-space sized glyphs.

This renderer batches all active strings into a single instanced draw call,
maintaining constant pixel size when zooming while text anchors move with world coordinates.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import TYPE_CHECKING

import freetype
import numpy as np
from OpenGL import GL as gl

from conlyse.logger import get_logger
from conlyse.pages.map_page.opengl_wrapper.shader import Shader, ShaderType
from conlyse.pages.map_page.opengl_wrapper.shader_program import ShaderProgram
from conlyse.pages.map_page.opengl_wrapper.vertex_array_object import VertexArrayObject
from conlyse.pages.map_page.opengl_wrapper.vertex_buffer_object import (
    BufferUsageType,
    VertexBufferObject,
)

if TYPE_CHECKING:
    from conlyse.pages.map_page.map import Map

logger = get_logger()
script_dir = Path(__file__).parent


class GlyphInfo:
    """Information about a single glyph in the atlas."""

    def __init__(self, char: str, width: int, height: int, bearing_x: int, bearing_y: int, advance: int):
        self.char = char
        self.width = width
        self.height = height
        self.bearing_x = bearing_x
        self.bearing_y = bearing_y
        self.advance = advance
        # UV coordinates (set when atlas is built)
        self.u_min = 0.0
        self.v_min = 0.0
        self.u_max = 0.0
        self.v_max = 0.0


class TextString:
    """Represents a text string to be rendered."""

    def __init__(
        self,
        text: str,
        anchor_world: tuple[float, float],
        color: tuple[float, float, float, float],
        size_px: float,
    ):
        self.text = text
        self.anchor_world = anchor_world
        self.color = color
        self.size_px = size_px
        # Range of glyph instances in the VBO (start_idx, count)
        self.glyph_range = (0, 0)


class WorldTextRenderer:
    """
    Renders world-anchored text with screen-space sized glyphs in a single instanced draw call.
    
    Features:
    - Batched rendering: all visible text rendered in one draw call
    - World-anchored: text positions follow world coordinates
    - Screen-sized: glyphs maintain constant pixel size under zoom/pan
    - Dynamic updates: efficient add/edit/remove of strings
    """

    def __init__(self, map_widget: Map, font_size: int = 48, atlas_size: int = 1024):
        """
        Initialize the WorldTextRenderer.
        
        Args:
            map_widget: The Map widget this renderer is attached to
            font_size: Base font size for glyph generation
            atlas_size: Size of the square glyph atlas texture
        """
        self.map_widget = map_widget
        self.camera = map_widget.camera
        self.font_size = font_size
        self.atlas_size = atlas_size

        # Shader program
        self.program: ShaderProgram | None = None

        # OpenGL resources
        self.vao: VertexArrayObject | None = None
        self.quad_vbo: VertexBufferObject | None = None  # Static quad vertices
        self.instance_vbo: VertexBufferObject | None = None  # Dynamic instance data
        self.atlas_texture_id: int = 0

        # Glyph data
        self.glyphs: dict[str, GlyphInfo] = {}

        # Text string management
        self.strings: dict[int, TextString] = {}  # string_id -> TextString
        self.next_string_id: int = 0

        # Instance data tracking
        self.instance_data: np.ndarray = np.array([], dtype=np.float32)
        self.instance_count: int = 0
        self.dirty: bool = False

    def initialize(self):
        """Initialize OpenGL resources."""
        # Load font and build glyph atlas
        self._load_font_and_build_atlas()

        # Compile shaders
        self.program = ShaderProgram()
        vertex_shader = Shader(ShaderType.VERTEX, script_dir / "shaders/world_text_vertex.glsl")
        fragment_shader = Shader(ShaderType.FRAGMENT, script_dir / "shaders/world_text_fragment.glsl")

        for shader in (vertex_shader, fragment_shader):
            shader.compile()
            self.program.attach_shader(shader)

        self.program.link_program()

        # Create static quad VBO (shared by all glyph instances)
        # Quad vertices: (0,0), (1,0), (0,1), (1,0), (1,1), (0,1) for two triangles
        quad_vertices = np.array(
            [0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0], dtype=np.float32
        )
        self.quad_vbo = VertexBufferObject(quad_vertices, BufferUsageType.STATIC_DRAW)

        # Create dynamic instance VBO (initially empty)
        self.instance_vbo = VertexBufferObject(
            np.array([], dtype=np.float32), BufferUsageType.DYNAMIC_DRAW
        )

        # Set up VAO
        self.vao = VertexArrayObject()
        self.vao.bind()

        # Attribute 0: Quad vertex (per-vertex, not instanced)
        loc = gl.glGetAttribLocation(self.program.program_id, b"aQuadVertex")
        self.vao.add_vbo(self.quad_vbo, loc, 2, 0, 0)
        gl.glVertexAttribDivisor(loc, 0)  # Per-vertex

        # Bind instance VBO for instanced attributes
        self.instance_vbo.bind()

        # Per-instance attributes (stride = 14 floats per instance)
        stride = 14 * 4  # 14 floats * 4 bytes

        # Attribute 1: aAnchorWorld (vec2)
        loc = gl.glGetAttribLocation(self.program.program_id, b"aAnchorWorld")
        gl.glEnableVertexAttribArray(loc)
        gl.glVertexAttribPointer(loc, 2, gl.GL_FLOAT, gl.GL_FALSE, stride, gl.ctypes.c_void_p(0))
        gl.glVertexAttribDivisor(loc, 1)

        # Attribute 2: aPixelOffset (vec2)
        loc = gl.glGetAttribLocation(self.program.program_id, b"aPixelOffset")
        gl.glEnableVertexAttribArray(loc)
        gl.glVertexAttribPointer(loc, 2, gl.GL_FLOAT, gl.GL_FALSE, stride, gl.ctypes.c_void_p(8))
        gl.glVertexAttribDivisor(loc, 1)

        # Attribute 3: aUVRect (vec4)
        loc = gl.glGetAttribLocation(self.program.program_id, b"aUVRect")
        gl.glEnableVertexAttribArray(loc)
        gl.glVertexAttribPointer(loc, 4, gl.GL_FLOAT, gl.GL_FALSE, stride, gl.ctypes.c_void_p(16))
        gl.glVertexAttribDivisor(loc, 1)

        # Attribute 4: aColor (vec4)
        loc = gl.glGetAttribLocation(self.program.program_id, b"aColor")
        gl.glEnableVertexAttribArray(loc)
        gl.glVertexAttribPointer(loc, 4, gl.GL_FLOAT, gl.GL_FALSE, stride, gl.ctypes.c_void_p(32))
        gl.glVertexAttribDivisor(loc, 1)

        # Attribute 5: aGlyphSize (vec2)
        loc = gl.glGetAttribLocation(self.program.program_id, b"aGlyphSize")
        gl.glEnableVertexAttribArray(loc)
        gl.glVertexAttribPointer(loc, 2, gl.GL_FLOAT, gl.GL_FALSE, stride, gl.ctypes.c_void_p(48))
        gl.glVertexAttribDivisor(loc, 1)

        self.instance_vbo.unbind()
        self.vao.unbind()

        logger.info("WorldTextRenderer initialized")

    def _load_font_and_build_atlas(self):
        """Load a font using FreeType and build the glyph atlas texture."""
        # Try to find a FreeFont font (common on Linux systems)
        # Fallback to system fonts
        font_paths = [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",  # macOS
            "C:/Windows/Fonts/arial.ttf",  # Windows
        ]

        face = None
        for font_path in font_paths:
            if Path(font_path).exists():
                try:
                    face = freetype.Face(font_path)
                    logger.info(f"Loaded font: {font_path}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to load font {font_path}: {e}")

        if face is None:
            # Fallback: create a simple error message
            logger.error("No suitable font found, text rendering will be limited")
            # Create a minimal atlas with a placeholder
            self._create_placeholder_atlas()
            return

        # Set font size
        face.set_pixel_sizes(0, self.font_size)

        # ASCII printable characters
        characters = [chr(c) for c in range(32, 127)]

        # First pass: render all glyphs and collect dimensions
        glyph_bitmaps = []
        for char in characters:
            face.load_char(char, freetype.FT_LOAD_RENDER)
            bitmap = face.glyph.bitmap
            glyph_info = GlyphInfo(
                char=char,
                width=bitmap.width,
                height=bitmap.rows,
                bearing_x=face.glyph.bitmap_left,
                bearing_y=face.glyph.bitmap_top,
                advance=face.glyph.advance.x >> 6,  # Convert from 1/64 pixels
            )
            self.glyphs[char] = glyph_info
            # Store bitmap data
            if bitmap.width > 0 and bitmap.rows > 0:
                glyph_bitmaps.append((char, np.array(bitmap.buffer, dtype=np.uint8).reshape(bitmap.rows, bitmap.width)))
            else:
                glyph_bitmaps.append((char, np.zeros((1, 1), dtype=np.uint8)))

        # Pack glyphs into atlas (simple row packing)
        atlas = np.zeros((self.atlas_size, self.atlas_size), dtype=np.uint8)
        x_offset = 0
        y_offset = 0
        row_height = 0

        for char, bitmap in glyph_bitmaps:
            glyph = self.glyphs[char]
            h, w = bitmap.shape

            # Check if we need to move to next row
            if x_offset + w > self.atlas_size:
                x_offset = 0
                y_offset += row_height + 1  # +1 for padding
                row_height = 0

            if y_offset + h > self.atlas_size:
                logger.warning(f"Glyph atlas overflow, some glyphs may not render correctly")
                break

            # Copy glyph bitmap to atlas
            atlas[y_offset : y_offset + h, x_offset : x_offset + w] = bitmap

            # Store UV coordinates (normalized to [0, 1])
            glyph.u_min = x_offset / self.atlas_size
            glyph.v_min = y_offset / self.atlas_size
            glyph.u_max = (x_offset + w) / self.atlas_size
            glyph.v_max = (y_offset + h) / self.atlas_size

            x_offset += w + 1  # +1 for padding
            row_height = max(row_height, h)

        # Create OpenGL texture
        self.atlas_texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.atlas_texture_id)
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D,
            0,
            gl.GL_RED,
            self.atlas_size,
            self.atlas_size,
            0,
            gl.GL_RED,
            gl.GL_UNSIGNED_BYTE,
            atlas,
        )
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

        logger.info(f"Glyph atlas created with {len(self.glyphs)} glyphs")

    def _create_placeholder_atlas(self):
        """Create a minimal placeholder atlas when no font is available."""
        # Create a simple white square
        atlas = np.full((64, 64), 255, dtype=np.uint8)
        self.atlas_texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.atlas_texture_id)
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D, 0, gl.GL_RED, 64, 64, 0, gl.GL_RED, gl.GL_UNSIGNED_BYTE, atlas
        )
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

        # Create a basic glyph for all characters
        for c in [chr(i) for i in range(32, 127)]:
            self.glyphs[c] = GlyphInfo(c, 8, 8, 0, 8, 8)
            self.glyphs[c].u_min = 0.0
            self.glyphs[c].v_min = 0.0
            self.glyphs[c].u_max = 1.0
            self.glyphs[c].v_max = 1.0

    def add_text(
        self,
        text: str,
        anchor_world: tuple[float, float],
        color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
        size_px: float = 16.0,
    ) -> int:
        """
        Add a text string to be rendered.
        
        Args:
            text: The text string to render
            anchor_world: World coordinates (x, y) for the text anchor
            color: RGBA color tuple (values in [0, 1])
            size_px: Size of the text in screen pixels
            
        Returns:
            String ID for later updates/removal
        """
        string_id = self.next_string_id
        self.next_string_id += 1

        text_string = TextString(text, anchor_world, color, size_px)
        self.strings[string_id] = text_string
        self.dirty = True

        return string_id

    def update_text(
        self,
        string_id: int,
        text: str | None = None,
        anchor_world: tuple[float, float] | None = None,
        color: tuple[float, float, float, float] | None = None,
        size_px: float | None = None,
    ):
        """
        Update an existing text string.
        
        Args:
            string_id: ID of the string to update
            text: New text (optional)
            anchor_world: New world anchor (optional)
            color: New color (optional)
            size_px: New size (optional)
        """
        if string_id not in self.strings:
            logger.warning(f"Attempted to update non-existent string ID: {string_id}")
            return

        text_string = self.strings[string_id]
        if text is not None:
            text_string.text = text
        if anchor_world is not None:
            text_string.anchor_world = anchor_world
        if color is not None:
            text_string.color = color
        if size_px is not None:
            text_string.size_px = size_px

        self.dirty = True

    def remove_text(self, string_id: int):
        """
        Remove a text string.
        
        Args:
            string_id: ID of the string to remove
        """
        if string_id in self.strings:
            del self.strings[string_id]
            self.dirty = True
        else:
            logger.warning(f"Attempted to remove non-existent string ID: {string_id}")

    def _rebuild_instance_data(self):
        """Rebuild the instance VBO data from all active strings."""
        if not self.dirty:
            return

        instances = []

        for string_id, text_string in self.strings.items():
            start_idx = len(instances)

            # Layout text glyphs
            x_cursor = 0.0
            for char in text_string.text:
                if char not in self.glyphs:
                    continue  # Skip unknown characters

                glyph = self.glyphs[char]

                # Scale factor for this text size
                scale = text_string.size_px / self.font_size

                # Calculate pixel offset for this glyph
                # X offset: cursor position + bearing (scaled)
                # Y offset: baseline adjustment based on bearing_y (scaled)
                pixel_offset_x = x_cursor + glyph.bearing_x * scale
                pixel_offset_y = -glyph.bearing_y * scale  # Negative because Y axis points down in screen space

                # Instance data: (anchor_world_x, anchor_world_y, pixel_offset_x, pixel_offset_y,
                #                 u_min, v_min, u_max, v_max, color_r, color_g, color_b, color_a, 
                #                 glyph_width_px, glyph_height_px)
                scaled_width = glyph.width * scale
                scaled_height = glyph.height * scale
                
                instance = [
                    text_string.anchor_world[0],  # anchor_world x
                    text_string.anchor_world[1],  # anchor_world y
                    pixel_offset_x,  # pixel offset x
                    pixel_offset_y,  # pixel offset y
                    glyph.u_min,  # u_min
                    glyph.v_min,  # v_min
                    glyph.u_max,  # u_max
                    glyph.v_max,  # v_max
                    text_string.color[0],  # color r
                    text_string.color[1],  # color g
                    text_string.color[2],  # color b
                    text_string.color[3],  # color a
                    scaled_width,  # glyph width in pixels
                    scaled_height,  # glyph height in pixels
                ]
                instances.append(instance)

                # Advance cursor (scaled)
                x_cursor += glyph.advance * scale

            # Store glyph range for this string
            text_string.glyph_range = (start_idx, len(instances) - start_idx)

        # Convert to numpy array
        if instances:
            self.instance_data = np.array(instances, dtype=np.float32).flatten()
            self.instance_count = len(instances)
        else:
            self.instance_data = np.array([], dtype=np.float32)
            self.instance_count = 0

        # Upload to GPU using orphaning for efficiency
        if self.instance_vbo:
            self.instance_vbo.bind()
            # Orphan old buffer
            gl.glBufferData(gl.GL_ARRAY_BUFFER, self.instance_data.nbytes, None, gl.GL_DYNAMIC_DRAW)
            # Upload new data
            if self.instance_data.size > 0:
                gl.glBufferData(
                    gl.GL_ARRAY_BUFFER,
                    self.instance_data.nbytes,
                    self.instance_data,
                    gl.GL_DYNAMIC_DRAW,
                )
            self.instance_vbo.unbind()

        self.dirty = False

    def render(self, viewport_px: tuple[int, int] | None = None):
        """
        Render all text strings in a single draw call.
        
        Args:
            viewport_px: Viewport dimensions (width, height) in pixels. If None, queried from OpenGL.
        """
        if self.instance_count == 0:
            return

        # Rebuild instance data if dirty
        self._rebuild_instance_data()

        if self.instance_count == 0:
            return

        # Use shader program
        self.program.use_program()

        # Set uniforms
        self.camera.set_uniforms(self.program)

        if viewport_px is None:
            viewport = gl.glGetIntegerv(gl.GL_VIEWPORT)
            viewport_px = (viewport[2], viewport[3])

        self.program.set_uniform_2f("uViewport", float(viewport_px[0]), float(viewport_px[1]))

        # Bind atlas texture
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.atlas_texture_id)
        self.program.set_uniform_1i("uAtlasTexture", 0)

        # Draw instanced
        self.vao.bind()
        gl.glDrawArraysInstanced(gl.GL_TRIANGLES, 0, 6, self.instance_count)
        self.vao.unbind()

        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    def cleanup(self):
        """Clean up OpenGL resources."""
        if self.atlas_texture_id:
            gl.glDeleteTextures([self.atlas_texture_id])
        if self.vao:
            self.vao.delete()
        logger.info("WorldTextRenderer cleaned up")
