#version 330 core

// Static quad vertex (per-vertex)
layout (location = 0) in vec2 aQuadVertex;  // {0,0}, {1,0}, {0,1}, {1,1}

// Per-instance attributes
layout (location = 1) in vec2 aAnchorWorld;      // World-space anchor position
layout (location = 2) in vec2 aWorldOffset;      // World-space offset
layout (location = 3) in vec4 aUVRect;           // (u_min, v_min, u_max, v_max)
layout (location = 4) in vec4 aColor;            // RGBA color
layout (location = 5) in vec2 aGlyphSize;        // Glyph size in world space

// Uniforms
uniform mat3 uViewProjection;  // World → NDC

// Outputs to fragment shader
out vec2 vTexCoord;
out vec4 vColor;

void main()
{
    // Calculate world position: anchor + offset + quad corner
    vec2 worldPos = aAnchorWorld + aWorldOffset + (aQuadVertex * aGlyphSize);
    
    // Transform to NDC
    vec3 ndcPos = uViewProjection * vec3(worldPos, 1.0);
    
    gl_Position = vec4(ndcPos.xy, 0.0, 1.0);

    // Calculate texture coordinates
    vec2 uv = aQuadVertex;
    vTexCoord = mix(aUVRect.xy, aUVRect.zw, uv);
    vColor = aColor;
}
