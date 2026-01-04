from OpenGL import GL as gl


class Framebuffer:
    """Wrapper class for OpenGL framebuffers managing binding, attachments, completeness checks, and cleanup."""
    def __init__(self):
        self.framebuffer_id = gl.glGenFramebuffers(1)

    def bind(self):
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.framebuffer_id)

    def unbind(self):
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

    def attach_texture2d(self, attachment: int, texture_id: int):
        gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, attachment, gl.GL_TEXTURE_2D, texture_id, 0)

    def attach_renderbuffer(self, attachment: int, renderbuffer_id: int):
        gl.glFramebufferRenderbuffer(gl.GL_FRAMEBUFFER, attachment, gl.GL_RENDERBUFFER, renderbuffer_id)

    def check_complete(self) -> int:
        return gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)

    def delete(self):
        gl.glDeleteFramebuffers(1, [self.framebuffer_id])
