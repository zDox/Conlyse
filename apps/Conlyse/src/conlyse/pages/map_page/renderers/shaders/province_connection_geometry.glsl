#version 330 core

layout(lines) in;
layout(triangle_strip, max_vertices = 24) out;

in vec2 vPosition[];

uniform mat3 uViewProjection;
uniform float uWorldWidth;
uniform bool uEnableWrapping;
uniform vec2 uScreenSize;
uniform float uLineWidthPixels;

// Emit a quad (4 vertices as triangle strip) for a line segment with offset
void emit_line_quad(vec2 p1, vec2 p2, vec2 offset) {
    // Transform to clip space
    vec3 clip1 = uViewProjection * vec3(p1 + offset, 1.0);
    vec3 clip2 = uViewProjection * vec3(p2 + offset, 1.0);

    // Convert to NDC (normalized device coordinates)
    vec2 ndc1 = clip1.xy / clip1.z;
    vec2 ndc2 = clip2.xy / clip2.z;

    // Convert NDC to screen space for width calculation
    vec2 screen1 = (ndc1 * 0.5 + 0.5) * uScreenSize;
    vec2 screen2 = (ndc2 * 0.5 + 0.5) * uScreenSize;

    // Calculate perpendicular direction in screen space
    vec2 dir = screen2 - screen1;
    float len = length(dir);
    if (len < 0.001) {
        return; // Skip degenerate lines
    }
    dir = dir / len;

    vec2 perp = vec2(-dir.y, dir.x) * (uLineWidthPixels * 0.5);

    // Calculate offset vertices in screen space
    vec2 screen_v1 = screen1 + perp;
    vec2 screen_v2 = screen1 - perp;
    vec2 screen_v3 = screen2 + perp;
    vec2 screen_v4 = screen2 - perp;

    // Convert back to NDC
    vec2 ndc_v1 = (screen_v1 / uScreenSize) * 2.0 - 1.0;
    vec2 ndc_v2 = (screen_v2 / uScreenSize) * 2.0 - 1.0;
    vec2 ndc_v3 = (screen_v3 / uScreenSize) * 2.0 - 1.0;
    vec2 ndc_v4 = (screen_v4 / uScreenSize) * 2.0 - 1.0;

    // Emit quad as triangle strip
    gl_Position = vec4(ndc_v1, 0.0, 1.0);
    EmitVertex();
    gl_Position = vec4(ndc_v2, 0.0, 1.0);
    EmitVertex();
    gl_Position = vec4(ndc_v3, 0.0, 1.0);
    EmitVertex();
    gl_Position = vec4(ndc_v4, 0.0, 1.0);
    EmitVertex();

    EndPrimitive();
}

void main() {
    vec2 p1 = vPosition[0];
    vec2 p2 = vPosition[1];

    // Emit original line
    emit_line_quad(p1, p2, vec2(0.0, 0.0));

    if (!uEnableWrapping) {
        return;
    }

    // Check if line crosses left/right seam
    float dx = p2.x - p1.x;
    bool wraps_around = abs(dx) > uWorldWidth * 0.5;

    if (wraps_around) {
        // Line wraps around - emit wrapped versions
        if (dx > 0.0) {
            // Line goes left to right across seam
            emit_line_quad(p1, p2, vec2(-uWorldWidth, 0.0));
        } else {
            // Line goes right to left across seam
            emit_line_quad(p1, p2, vec2(uWorldWidth, 0.0));
        }
    } else {
        // Check if line is near seams and needs duplicate rendering
        bool near_left = (p1.x < 5000.0 || p2.x < 5000.0);
        bool near_right = (p1.x > uWorldWidth - 5000.0 || p2.x > uWorldWidth - 5000.0);

        if (near_left) {
            emit_line_quad(p1, p2, vec2(uWorldWidth, 0.0));
        }
        if (near_right) {
            emit_line_quad(p1, p2, vec2(-uWorldWidth, 0.0));
        }
    }
}