from OpenGL import GL as gl


class Renderbuffer:
    def __init__(self):
        self.renderbuffer_id = gl.glGenRenderbuffers(1)

    def bind(self):
        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, self.renderbuffer_id)

    def unbind(self):
        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, 0)

    def storage(self, internal_format, width: int, height: int):
        self.bind()
        gl.glRenderbufferStorage(gl.GL_RENDERBUFFER, internal_format, width, height)

    def delete(self):
        gl.glDeleteRenderbuffers(1, [self.renderbuffer_id])
