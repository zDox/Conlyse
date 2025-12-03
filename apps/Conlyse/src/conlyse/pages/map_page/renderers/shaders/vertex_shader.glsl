#version 330 core
layout(location = 0) in vec2 position;
layout(location = 1) in int province_color_index;

out vec4 vColor;

uniform mat3 uViewProjection;
uniform vec4 uProvinceColors[2];

void main()
{
    gl_Position = vec4((uViewProjection * vec3(position,1.0)).xy, 0.0, 1.0);
    vColor = uProvinceColors[province_color_index];
}