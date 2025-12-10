#version 330 core

layout(triangles) in;
layout(triangle_strip, max_vertices = 9) out;

in vec2 vPosition[];

uniform mat3 uViewProjection;
uniform float uWorldWidth;
uniform bool uEnableWrapping;

// Emit a single triangle with an offset
void emit_triangle(vec2 offset) {
    for (int i = 0; i < 3; i++) {
        vec3 world_pos = vec3(vPosition[i] + offset, 1.0);
        vec3 clip_pos = uViewProjection * world_pos;
        gl_Position = vec4(clip_pos.xy, 0.0, 1.0);
        EmitVertex();
    }
    EndPrimitive();
}

void main() {
    // Emit original triangle
    emit_triangle(vec2(0.0, 0.0));

    if (!uEnableWrapping) {
        return;
    }

    // Check if triangle crosses left/right seam
    bool crosses_left = false;
    bool crosses_right = false;

    for (int i = 0; i < 3; i++) {
        if (vPosition[i].x < 5000.0) crosses_left = true;
        if (vPosition[i].x > uWorldWidth - 5000.0) crosses_right = true;
    }

    // Emit wrapped duplicates if needed
    if (crosses_left) {
        emit_triangle(vec2(uWorldWidth, 0.0));   // Wrap left → right
    }
    if (crosses_right) {
        emit_triangle(vec2(-uWorldWidth, 0.0));  // Wrap right → left
    }
}