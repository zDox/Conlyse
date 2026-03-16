import OpenGL.GL as gl

class ShaderProgram:
    def __init__(self):
        self.program_id = gl.glCreateProgram()
        self.shaders = []

    def attach_shader(self, shader):
        gl.glAttachShader(self.program_id, shader.shader_id)
        self.shaders.append(shader)

    def use_program(self):
        gl.glUseProgram(self.program_id)

    def link_program(self):
        gl.glLinkProgram(self.program_id)
        if not gl.glGetProgramiv(self.program_id, gl.GL_LINK_STATUS):
            error = gl.glGetProgramInfoLog(self.program_id).decode()
            raise RuntimeError(f"Shader program linking error: {error}")

        for shader in self.shaders:
            gl.glDeleteShader(shader.shader_id)

    def set_uniform_matrix3fv(self, param, matrix):
        loc = gl.glGetUniformLocation(self.program_id, param.encode())
        gl.glUniformMatrix3fv(loc, 1, gl.GL_FALSE, matrix.flatten())

    def set_uniform_1b(self, param: str, value: bool):
        loc = gl.glGetUniformLocation(self.program_id, param.encode())
        gl.glUniform1i(loc, int(value))

    def set_uniform_1i(self, param: str, value: int):
        loc = gl.glGetUniformLocation(self.program_id, param.encode())
        gl.glUniform1i(loc, value)

    def set_uniform_2i(self, param: str, v0: int, v1: int):
        loc = gl.glGetUniformLocation(self.program_id, param.encode())
        gl.glUniform2i(loc, v0, v1)

    def set_uniform_3i(self, param: str, v0: int, v1: int, v2: int):
        loc = gl.glGetUniformLocation(self.program_id, param.encode())
        gl.glUniform3i(loc, v0, v1, v2)

    def set_uniform_4i(self, param: str, v0: int, v1: int, v2: int, v3: int):
        loc = gl.glGetUniformLocation(self.program_id, param.encode())
        gl.glUniform4i(loc, v0, v1, v2, v3)

    def set_uniform_1f(self, param: str, value: float):
        loc = gl.glGetUniformLocation(self.program_id, param.encode())
        gl.glUniform1f(loc, value)

    def set_uniform_2f(self, param: str, v0: float, v1: float):
        loc = gl.glGetUniformLocation(self.program_id, param.encode())
        gl.glUniform2f(loc, v0, v1)

    def set_uniform_3f(self, param: str, v0: float, v1: float, v2: float):
        loc = gl.glGetUniformLocation(self.program_id, param.encode())
        gl.glUniform3f(loc, v0, v1, v2)

    def set_uniform_4f(self, param: str, v0: float, v1: float, v2: float, v3: float):
        loc = gl.glGetUniformLocation(self.program_id, param.encode())
        gl.glUniform4f(loc, v0, v1, v2, v3)