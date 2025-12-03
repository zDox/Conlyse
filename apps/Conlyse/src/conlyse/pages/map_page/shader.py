import OpenGL.GL as gl

from conlyse.logger import get_logger

logger = get_logger()

class ShaderType:
    VERTEX = gl.GL_VERTEX_SHADER
    FRAGMENT = gl.GL_FRAGMENT_SHADER

class Shader:
    def __init__(self, shader_type: ShaderType, shader_name: str):
        self.shader_type: ShaderType = shader_type
        self.shader_id = None
        self.shader_code = None
        self.shader_name: str = shader_name

        with open(shader_name, "r") as f:
            self.shader_code = f.read()

    def compile(self):
        self.shader_id = gl.glCreateShader(self.shader_type)
        gl.glShaderSource(self.shader_id, self.shader_code)
        gl.glCompileShader(self.shader_id)

        if not gl.glGetShaderiv(self.shader_id, gl.GL_COMPILE_STATUS):
            error = gl.glGetShaderInfoLog(self.shader_id).decode()
            logger.error(f"Shader({self.shader_name}) compilation error: {error}")
            raise RuntimeError(f"Shader compilation error: {error}")