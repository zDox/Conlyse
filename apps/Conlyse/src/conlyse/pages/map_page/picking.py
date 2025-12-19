from __future__ import annotations

import numpy as np
from OpenGL import GL as gl
from typing import TYPE_CHECKING

from conlyse.logger import get_logger
from conlyse.pages.map_page.opengl_wrapper.color_palette_texture import ColorPaletteTexture

if TYPE_CHECKING:
    from conlyse.pages.map_page.map import Map
    from conlyse.pages.map_page.renderers.province_fill_renderer import ProvinceFillRenderer

logger = get_logger()

MAX_PICKING_PROVINCE_ID = 0xFFFFFFFE


class ProvincePicker:
    """Handles GPU-based province picking via offscreen rendering."""

    def __init__(self, map_widget: Map, province_fill_renderer: ProvinceFillRenderer):
        self.map_widget = map_widget
        self.camera = map_widget.camera
        self.province_fill_renderer = province_fill_renderer

        self._picking_fbo: int | None = None
        self._picking_texture: int | None = None
        self._picking_depth_rbo: int | None = None
        self._picking_palette_texture: ColorPaletteTexture | None = None
        self._picking_size: tuple[int, int] = (0, 0)

    def get_province_id_at_world_position(self, world_x: float, world_y: float) -> int | None:
        width = self.map_widget.width()
        height = self.map_widget.height()
        if width <= 0 or height <= 0:
            return None
        if self.province_fill_renderer.program is None or self.province_fill_renderer.vao is None:
            return None

        screen_pos = self.camera.world_to_screen(world_x, world_y)
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        if sx < 0 or sy < 0 or sx >= width or sy >= height:
            return None

        self.map_widget.makeCurrent()
        try:
            if not self._ensure_picking_framebuffer(width, height):
                return None
            if not self._ensure_picking_palette_texture():
                return None

            prev_fb = int(gl.glGetIntegerv(gl.GL_FRAMEBUFFER_BINDING))
            prev_viewport = tuple(int(v) for v in gl.glGetIntegerv(gl.GL_VIEWPORT))
            blend_enabled = gl.glIsEnabled(gl.GL_BLEND)
            prev_clear_color = gl.glGetFloatv(gl.GL_COLOR_CLEAR_VALUE)

            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self._picking_fbo)
            gl.glViewport(0, 0, width, height)
            gl.glClearColor(0.0, 0.0, 0.0, 0.0)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
            if blend_enabled:
                gl.glDisable(gl.GL_BLEND)

            self.province_fill_renderer.render_palette(self._picking_palette_texture)

            pixel = gl.glReadPixels(sx, height - sy - 1, 1, 1, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE)

            if blend_enabled:
                gl.glEnable(gl.GL_BLEND)
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, prev_fb)
            gl.glClearColor(prev_clear_color[0], prev_clear_color[1], prev_clear_color[2], prev_clear_color[3])
            gl.glViewport(prev_viewport[0], prev_viewport[1], prev_viewport[2], prev_viewport[3])
        finally:
            self.map_widget.doneCurrent()

        if pixel is None:
            return None

        rgba = np.frombuffer(pixel, dtype=np.uint8, count=4)
        return self._decode_province_id(rgba)

    def cleanup(self):
        self._destroy_picking_resources()

    @staticmethod
    def _encode_province_id(province_id: int) -> tuple[int, int, int, int]:
        encoded = int(np.uint32(province_id + 1))
        return (
            encoded & 0xFF,
            (encoded >> 8) & 0xFF,
            (encoded >> 16) & 0xFF,
            (encoded >> 24) & 0xFF
        )

    @staticmethod
    def _decode_province_id(rgba: np.ndarray) -> int | None:
        if rgba.size < 4:
            return None
        encoded = (
            int(rgba[0])
            | (int(rgba[1]) << 8)
            | (int(rgba[2]) << 16)
            | (int(rgba[3]) << 24)
        )
        if encoded == 0:
            return None
        return encoded - 1

    def _ensure_picking_palette_texture(self) -> bool:
        if self._picking_palette_texture is not None:
            return True
        max_id = self.province_fill_renderer.province_mesh.max_province_id
        if max_id > MAX_PICKING_PROVINCE_ID:
            logger.error(f"Province ID {max_id} exceeds supported range for picking.")
            return False
        encoded = np.arange(max_id + 1, dtype=np.uint32) + 1
        color_data = np.ascontiguousarray(encoded.view(np.uint8).reshape(-1, 4))
        self._picking_palette_texture = ColorPaletteTexture(color_data.flatten())
        return True

    def _ensure_picking_framebuffer(self, width: int, height: int) -> bool:
        if self._picking_fbo is None:
            self._picking_fbo = gl.glGenFramebuffers(1)
            self._picking_texture = gl.glGenTextures(1)
            self._picking_depth_rbo = gl.glGenRenderbuffers(1)

        if self._picking_size == (width, height):
            return True

        gl.glBindTexture(gl.GL_TEXTURE_2D, self._picking_texture)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA8, width, height, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, None)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)

        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, self._picking_depth_rbo)
        gl.glRenderbufferStorage(gl.GL_RENDERBUFFER, gl.GL_DEPTH_COMPONENT24, width, height)

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self._picking_fbo)
        gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, gl.GL_TEXTURE_2D, self._picking_texture, 0)
        gl.glFramebufferRenderbuffer(gl.GL_FRAMEBUFFER, gl.GL_DEPTH_ATTACHMENT, gl.GL_RENDERBUFFER, self._picking_depth_rbo)

        status = gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, 0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

        if status != gl.GL_FRAMEBUFFER_COMPLETE:
            logger.error(f"Province picking framebuffer incomplete: {status}")
            return False

        self._picking_size = (width, height)
        return True

    def _destroy_picking_resources(self):
        if self._picking_palette_texture is not None:
            self._picking_palette_texture.delete()
            self._picking_palette_texture = None
        if self._picking_texture is not None:
            gl.glDeleteTextures(1, [self._picking_texture])
            self._picking_texture = None
        if self._picking_depth_rbo is not None:
            gl.glDeleteRenderbuffers(1, [self._picking_depth_rbo])
            self._picking_depth_rbo = None
        if self._picking_fbo is not None:
            gl.glDeleteFramebuffers(1, [self._picking_fbo])
            self._picking_fbo = None
        self._picking_size = (0, 0)
