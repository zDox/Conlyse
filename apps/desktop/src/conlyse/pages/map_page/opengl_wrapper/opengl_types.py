from enum import Enum
from OpenGL import GL as gl

class OpenGLTypes(Enum):
    FLOAT = gl.GL_FLOAT
    INT = gl.GL_INT
    UNSIGNED_INT = gl.GL_UNSIGNED_INT
    DOUBLE = gl.GL_DOUBLE
    BYTE = gl.GL_BYTE
    UNSIGNED_BYTE = gl.GL_UNSIGNED_BYTE
    SHORT = gl.GL_SHORT
    UNSIGNED_SHORT = gl.GL_UNSIGNED_SHORT