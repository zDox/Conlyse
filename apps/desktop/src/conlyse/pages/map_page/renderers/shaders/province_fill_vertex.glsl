#version 410 core

layout(location = 0) in vec2 position;
layout(location = 1) in int province_color_index;

out vec2 vPosition;
flat out int vProvinceColorIndex;

void main() {
    vPosition = position;
    vProvinceColorIndex = province_color_index;
}