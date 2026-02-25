#version 330 core

layout(triangles) in;
layout(triangle_strip, max_vertices = 9) out;  // Use triangle_strip instead

in vec2 vPosition[];
flat in int vProvinceColorIndex[];

out vec2 gPosition;
flat out int gProvinceColorIndex;

uniform mat3 uViewProjection; // 3x3 for 2D
uniform float uWorldWidth;
uniform float uWorldHeight;
uniform bool uEnableWrapping;  // Toggle wrapping on/off

// Emit a single triangle with an offset
void emit_triangle(vec2 offset) {
    for (int i = 0; i < 3; i++) {
        vec3 world_pos = vec3(vPosition[i] + offset, 1.0);
        vec3 clip_pos = uViewProjection * world_pos;

        gProvinceColorIndex = vProvinceColorIndex[i];
        gPosition = vPosition[i] + offset;
        gl_Position = vec4(clip_pos.xy, 0.0, 1.0);

        EmitVertex();
    }
    EndPrimitive();
}

void main() {
    // Emit original triangle
    emit_triangle(vec2(0.0, 0.0));


    // Only do wrapping if enabled
    if (!uEnableWrapping) {
        return;
    }

    // Check if triangle is near left/right seam
    bool crosses_left = false;
    bool crosses_right = false;

    for (int i = 0; i < 3; i++) {
        if (vPosition[i].x < 5000.0) crosses_left = true;               // threshold
        if (vPosition[i].x > uWorldWidth - 5000.0) crosses_right = true;
    }

    // Emit duplicates if needed
    if (crosses_left) {
        emit_triangle(vec2(uWorldWidth, 0.0));   // wrap left → right
    }
    if (crosses_right) {
        emit_triangle(vec2(-uWorldWidth, 0.0));  // wrap right → left
    }
}