import numpy as np
from OpenGL import GL as gl

from conlyse.logger import get_logger
logger = get_logger()

class ColorPaletteTexture:
    def __init__(self, color_data: np.ndarray):
        self.size = len(color_data) // 4
        self.texture_id = gl.glGenTextures(1)
        self.bind()
        gl.glTexImage1D(gl.GL_TEXTURE_1D, 0, gl.GL_RGBA, len(color_data) // 4, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, color_data)
        gl.glTexParameteri(gl.GL_TEXTURE_1D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_1D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_1D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)

    def bind(self):
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_1D, self.texture_id)

    def update_data(self, color_data: np.ndarray):
        assert len(color_data) // 4 == self.size
        logger.debug(f"Updating ColorPaletteTexture with {self.size} colors.")
        self.bind()
        gl.glTexSubImage1D(gl.GL_TEXTURE_1D, 0, 0, len(color_data) // 4, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, color_data)

    def unbind(self):
        gl.glBindTexture(gl.GL_TEXTURE_1D, 0)