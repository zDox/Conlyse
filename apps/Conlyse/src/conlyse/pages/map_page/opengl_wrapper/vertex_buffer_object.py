from enum import Enum

import numpy
from OpenGL import GL as gl

class BufferUsageType(Enum):
    STATIC_DRAW = gl.GL_STATIC_DRAW
    DYNAMIC_DRAW = gl.GL_DYNAMIC_DRAW
    STREAM_DRAW = gl.GL_STREAM_DRAW

class VertexBufferObject:
    def __init__(self, data: numpy.ndarray, usage=BufferUsageType.DYNAMIC_DRAW):
        self.usage: BufferUsageType = usage
        self.buffer_id = gl.glGenBuffers(1)
        self.bind()
        gl.glBufferData(gl.GL_ARRAY_BUFFER, data.nbytes, data, usage.value)
        self.unbind()

    def update_data(self, data: numpy.ndarray, offset=0):
        self.bind()
        gl.glBufferSubData(gl.GL_ARRAY_BUFFER, offset, data.nbytes, data)
        self.unbind()

    def bind(self):
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffer_id)

    def unbind(self):
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)