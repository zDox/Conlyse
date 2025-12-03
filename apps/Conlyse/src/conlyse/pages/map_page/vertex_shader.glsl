#version 330 core
layout(location = 0) in vec2 position;
layout(location = 1) in vec4 aColor;

out vec4 vColor;

uniform mat3 uViewProjection;

void main()
{
    gl_Position = vec4((uViewProjection * vec3(position,1.0)).xy, 0.0, 1.0);
    vColor = aColor;
}