import ctypes

from OpenGL import GL as gl

from conlyse.pages.map_page.opengl_wrapper.opengl_types import OpenGLTypes
from conlyse.pages.map_page.opengl_wrapper.vertex_buffer_object import VertexBufferObject


class VertexArrayObject:
    def __init__(self):
        self.id = gl.glGenVertexArrays(1)
        self.vbos = []

    def add_vbo(self, vbo: VertexBufferObject, index: int, size: int, stride: int, offset: int,
                element_type: OpenGLTypes = OpenGLTypes.FLOAT):
        """Attach a VBO as a vertex attribute."""
        self.bind()
        vbo.bind()
        gl.glEnableVertexAttribArray(index)
        if element_type == OpenGLTypes.INT:
            gl.glVertexAttribIPointer(index, size, element_type.value, stride, ctypes.c_void_p(offset))
        else:
            gl.glVertexAttribPointer(index, size, element_type.value, gl.GL_FALSE, stride, ctypes.c_void_p(offset))
        vbo.unbind()
        self.unbind()
        self.vbos.append(vbo)

    def bind(self):
        gl.glBindVertexArray(self.id)

    def unbind(self):
        gl.glBindVertexArray(0)

    def delete(self):
        for vbo in self.vbos:
            vbo.delete()
        gl.glDeleteVertexArrays(1, [self.id])