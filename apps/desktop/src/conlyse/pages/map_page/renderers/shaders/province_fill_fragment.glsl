#version 410 core

out vec4 FragColor;

flat in int gProvinceColorIndex;

uniform sampler1D uProvinceColorsTex;
uniform int uNumColors;

void main() {
    float index = float(gProvinceColorIndex) / float(uNumColors - 1);
    FragColor = texture(uProvinceColorsTex, index);
}
