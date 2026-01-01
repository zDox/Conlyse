from OpenGL import GL as gl


class Texture2D:
    def __init__(self):
        self.texture_id = gl.glGenTextures(1)

    def bind(self):
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)

    def unbind(self):
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    def set_image(self, width: int, height: int, internal_format=gl.GL_RGBA8,
                  format=gl.GL_RGBA, type=gl.GL_UNSIGNED_BYTE, data=None):
        self.bind()
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, internal_format, width, height, 0, format, type, data)

    def set_parameters(self, params: dict[int, int]):
        self.bind()
        for pname, value in params.items():
            gl.glTexParameteri(gl.GL_TEXTURE_2D, pname, value)

    def delete(self):
        gl.glDeleteTextures(1, [self.texture_id])
