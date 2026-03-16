"""
WorldTextRenderer - Renders world-anchored text with world-space sized glyphs.

This renderer batches all active strings into a single instanced draw call,
with text that scales with the camera zoom level.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import freetype
import numpy as np
from OpenGL import GL as gl

from conlyse.logger import get_logger
from conlyse.pages.map_page.color_util import rgba_to_normalized
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


class TextGroup(Enum):
    """Text group categories for efficient activation/deactivation."""
    GLOBAL = "global"
    NATION_LABELS = "nation_labels"
    PROVINCE_LABELS = "province_labels"
    CITY_LABELS = "city_labels"


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
        size_world: float,
        group: TextGroup,
        centered: bool = False,
        outline_width: float = 0.0,
        outline_color: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0),
        shadow_offset: tuple[float, float] = (0.0, 0.0),
        shadow_color: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.5),
    ):
        self.text = text
        self.anchor_world = anchor_world
        self.color = color
        self.size_world = size_world  # Size in world units
        self.group = group  # Text group for activation/deactivation
        self.centered = centered  # Whether to center text around anchor
        self.outline_width = outline_width  # Outline width in world units
        self.outline_color = outline_color  # Outline color RGBA
        self.shadow_offset = shadow_offset  # Shadow offset (x, y) in world units
        self.shadow_color = shadow_color  # Shadow color RGBA
        # Range of glyph instances in the VBO (start_idx, count)
        self.glyph_range = (0, 0)
        # Total width for centering calculation
        self.total_width = 0.0


class WorldTextRenderer:
    """
    Renders world-anchored text with world-space sized glyphs in a single instanced draw call.
    
    Features:
    - Batched rendering: all visible text rendered in one draw call
    - World-anchored: text positions follow world coordinates
    - World-sized: glyphs scale with camera zoom
    - Dynamic updates: efficient add/edit/remove of strings
    - Group management: efficiently activate/deactivate groups of text
    """
    
    # Outline sampling directions (normalized, scale by outline_width at runtime)
    OUTLINE_OFFSETS = [
        (-1.0, 0.0), (1.0, 0.0), (0.0, -1.0), (0.0, 1.0),  # Cardinal
        (-0.707, -0.707), (0.707, -0.707), (-0.707, 0.707), (0.707, 0.707),  # Diagonal
    ]

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

        # Group management - all groups active by default
        self.active_groups: set[TextGroup] = set(TextGroup)
        
        # Per-string visibility tracking (string_id -> visible)
        self.string_visibility: dict[int, bool] = {}

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
        self.vao.bind()
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

        # Attribute 2: aWorldOffset (vec2)
        loc = gl.glGetAttribLocation(self.program.program_id, b"aWorldOffset")
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
            "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf",
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
            raise Exception(f"No suitable font found for WorldTextRenderer")

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

        self.font_max_bearing_y = max(g.bearing_y for g in self.glyphs.values())
        logger.info(f"Glyph atlas created with {len(self.glyphs)} glyphs")


    def add_text(
        self,
        text: str,
        anchor_world: tuple[float, float],
        color: tuple[int, int, int, int] = (255, 255, 255, 255),
        size_world: float = 10,
        group: TextGroup = TextGroup.GLOBAL,
        centered: bool = False,
        outline_width: float = 0.0,
        outline_color: tuple[int, int, int, int] = (0, 0, 0, 255),
        shadow_offset: tuple[float, float] = (0.0, 0.0),
        shadow_color: tuple[int, int, int, int] = (0, 0, 0, 128),
    ) -> int:
        """
        Add a text string to be rendered.
        
        Args:
            text: The text string to render
            anchor_world: World coordinates (x, y) for the text anchor
            color: RGBA color tuple (values in [0, 255])
            size_world: Size of the text in world units
            group: Text group for activation/deactivation (default: TextGroup.GLOBAL)
            centered: Whether to center the text around the anchor (default: False)
            outline_width: Width of outline effect in world units (default: 0.0, disabled)
            outline_color: RGBA color for outline (default: black)
            shadow_offset: Shadow offset (x, y) in world units (default: (0, 0), disabled)
            shadow_color: RGBA color for shadow (default: semi-transparent black)
            
        Returns:
            String ID for later updates/removal
        """
        string_id = self.next_string_id
        self.next_string_id += 1

        text_string = TextString(
            text, anchor_world, rgba_to_normalized(color), size_world, group,
            centered, outline_width, rgba_to_normalized(outline_color), shadow_offset, rgba_to_normalized(shadow_color)
        )
        self.strings[string_id] = text_string
        self.string_visibility[string_id] = group in self.active_groups
        self.dirty = True

        return string_id

    def update_text(
        self,
        string_id: int,
        text: str | None = None,
        anchor_world: tuple[float, float] | None = None,
        color: tuple[int, int, int, int] | None = None,
        size_world: float | None = None,
        group: TextGroup | None = None,
    ):
        """
        Update an existing text string.
        
        Args:
            string_id: ID of the string to update
            text: New text (optional)
            anchor_world: New world anchor (optional)
            color: New color (optional)
            size_world: New size in world units (optional)
            group: New text group (optional)
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
            text_string.color = rgba_to_normalized(color)
        if size_world is not None:
            text_string.size_world = size_world
        if group is not None:
            text_string.group = group

        self.dirty = True

    def remove_text(self, string_id: int):
        """
        Remove a text string.
        
        Args:
            string_id: ID of the string to remove
        """
        if string_id in self.strings:
            del self.strings[string_id]
            if string_id in self.string_visibility:
                del self.string_visibility[string_id]
            self.dirty = True
        else:
            logger.warning(f"Attempted to remove non-existent string ID: {string_id}")

    def activate_group(self, group: TextGroup):
        """
        Activate a text group, making all strings in that group visible.
        Triggers a lightweight rebuild of instance data.
        
        Args:
            group: The TextGroup to activate
        """
        was_inactive = group not in self.active_groups
        self.active_groups.add(group)
        if was_inactive:
            # Update visibility for all strings in this group
            for string_id, text_string in self.strings.items():
                if text_string.group == group:
                    self.string_visibility[string_id] = True
            # Mark dirty to rebuild only visible instances
            self.dirty = True
            logger.debug(f"Activated text group: {group.value}")

    def deactivate_group(self, group: TextGroup):
        """
        Deactivate a text group, hiding all strings in that group.
        Triggers a lightweight rebuild of instance data.
        
        Args:
            group: The TextGroup to deactivate
        """
        was_active = group in self.active_groups
        self.active_groups.discard(group)  # discard doesn't raise KeyError
        if was_active:
            # Update visibility for all strings in this group
            for string_id, text_string in self.strings.items():
                if text_string.group == group:
                    self.string_visibility[string_id] = False
            # Mark dirty to rebuild only visible instances
            self.dirty = True
            logger.debug(f"Deactivated text group: {group.value}")

    def toggle_group(self, group: TextGroup):
        """
        Toggle a text group's visibility.
        
        Args:
            group: The TextGroup to toggle
        """
        if group in self.active_groups:
            self.deactivate_group(group)
        else:
            self.activate_group(group)

    def is_group_active(self, group: TextGroup) -> bool:
        """
        Check if a text group is currently active.
        
        Args:
            group: The TextGroup to check
            
        Returns:
            True if the group is active, False otherwise
        """
        return group in self.active_groups

    def get_active_groups(self) -> set[TextGroup]:
        """
        Get the set of currently active text groups.
        
        Returns:
            Set of active TextGroup enums
        """
        return self.active_groups.copy()

    def set_active_groups(self, groups: set[TextGroup]):
        """
        Set which text groups are active.
        
        Args:
            groups: Set of TextGroup enums to activate (all others will be deactivated)
        """
        self.active_groups = groups.copy()
        self.dirty = True
        logger.debug(f"Set active groups: {[g.value for g in groups]}")

    def _rebuild_instance_data(self):
        """Rebuild the instance VBO data from visible strings only (optimized)."""
        if not self.dirty:
            return
        logger.debug(f"Rebuilding instance data for visible strings")

        instances = []

        for string_id, text_string in self.strings.items():
            # Skip invisible strings - this is the optimization!
            if not self.string_visibility.get(string_id, False):
                continue

            start_idx = len(instances)

            # First pass: calculate total text width for centering
            scale = text_string.size_world / self.font_size
            total_width = 0.0
            for char in text_string.text:
                if char in self.glyphs:
                    total_width += self.glyphs[char].advance * scale
            text_string.total_width = total_width

            # Calculate centering offset
            center_offset_x = -total_width / 2.0 if text_string.centered else 0.0

            # Add shadow layer if enabled
            has_shadow = text_string.shadow_offset != (0.0, 0.0)
            if has_shadow:
                x_cursor = 0.0
                for char in text_string.text:
                    if char not in self.glyphs:
                        continue

                    glyph = self.glyphs[char]
                    world_offset_x = center_offset_x + x_cursor + glyph.bearing_x * scale + text_string.shadow_offset[0]
                    world_offset_y = (self.font_max_bearing_y - glyph.bearing_y) * scale + text_string.shadow_offset[1]
                    scaled_width = glyph.width * scale
                    scaled_height = glyph.height * scale

                    instance = [
                        text_string.anchor_world[0], text_string.anchor_world[1],
                        world_offset_x, world_offset_y,
                        glyph.u_min, glyph.v_min, glyph.u_max, glyph.v_max,
                        text_string.shadow_color[0], text_string.shadow_color[1],
                        text_string.shadow_color[2], text_string.shadow_color[3],
                        scaled_width, scaled_height,
                    ]
                    instances.append(instance)
                    x_cursor += glyph.advance * scale

            # Add outline layer if enabled
            has_outline = text_string.outline_width > 0.0
            if has_outline:
                # Render outline by drawing text multiple times with slight offsets
                for norm_x, norm_y in self.OUTLINE_OFFSETS:
                    offset_x = norm_x * text_string.outline_width
                    offset_y = norm_y * text_string.outline_width
                    x_cursor = 0.0
                    for char in text_string.text:
                        if char not in self.glyphs:
                            continue

                        glyph = self.glyphs[char]
                        world_offset_x = center_offset_x + x_cursor + glyph.bearing_x * scale + offset_x
                        world_offset_y = (self.font_max_bearing_y - glyph.bearing_y) * scale + offset_y
                        scaled_width = glyph.width * scale
                        scaled_height = glyph.height * scale

                        instance = [
                            text_string.anchor_world[0], text_string.anchor_world[1],
                            world_offset_x, world_offset_y,
                            glyph.u_min, glyph.v_min, glyph.u_max, glyph.v_max,
                            text_string.outline_color[0], text_string.outline_color[1],
                            text_string.outline_color[2], text_string.outline_color[3],
                            scaled_width, scaled_height,
                        ]
                        instances.append(instance)
                        x_cursor += glyph.advance * scale

            # Add main text layer
            x_cursor = 0.0
            for char in text_string.text:
                if char not in self.glyphs:
                    continue

                glyph = self.glyphs[char]
                world_offset_x = center_offset_x + x_cursor + glyph.bearing_x * scale
                world_offset_y = (self.font_max_bearing_y - glyph.bearing_y) * scale
                scaled_width = glyph.width * scale
                scaled_height = glyph.height * scale

                instance = [
                    text_string.anchor_world[0], text_string.anchor_world[1],
                    world_offset_x, world_offset_y,
                    glyph.u_min, glyph.v_min, glyph.u_max, glyph.v_max,
                    text_string.color[0], text_string.color[1],
                    text_string.color[2], text_string.color[3],
                    scaled_width, scaled_height,
                ]
                instances.append(instance)

                # Advance cursor in world units
                x_cursor += glyph.advance * scale

            # Store glyph range for this string
            text_string.glyph_range = (start_idx, len(instances) - start_idx)

        # Convert to numpy array
        if instances:
            self.instance_data = np.array(instances, dtype=np.float32).flatten()
            self.instance_count = len(instances)
            logger.debug(f"Rebuilt instance data with {self.instance_count} glyphs")
        else:
            self.instance_data = np.array([], dtype=np.float32)
            self.instance_count = 0

        # Upload to GPU using orphaning for efficiency
        if self.instance_vbo:
            self.instance_vbo.bind()
            # Orphan old buffer by allocating with NULL data
            gl.glBufferData(gl.GL_ARRAY_BUFFER, self.instance_data.nbytes, None, gl.GL_DYNAMIC_DRAW)
            # Upload new data
            if self.instance_data.size > 0:
                gl.glBufferSubData(gl.GL_ARRAY_BUFFER, 0, self.instance_data.nbytes, self.instance_data)
            self.instance_vbo.unbind()

        self.dirty = False

    def render(self):
        """Render visible text strings in a single draw call."""
        if self.map_widget.camera.zoom > 20:
            self.deactivate_group(TextGroup.NATION_LABELS)
            self.activate_group(TextGroup.CITY_LABELS)
        else:
            self.activate_group(TextGroup.NATION_LABELS)
            self.deactivate_group(TextGroup.CITY_LABELS)
        
        # Rebuild instance data if dirty (only includes visible strings now)
        self._rebuild_instance_data()

        if self.instance_count == 0:
            return

        # Use shader program
        self.program.use_program()

        # Set camera uniforms
        self.camera.set_uniforms(self.program)

        # Bind atlas texture
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.atlas_texture_id)
        self.program.set_uniform_1i("uAtlasTexture", 0)

        # Draw all visible instances in one call
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
