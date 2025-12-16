#version 330 core

// Static quad vertex (per-vertex)
layout (location = 0) in vec2 aQuadVertex;  // {0,0}, {1,0}, {0,1}, {1,1}

// Per-instance attributes
layout (location = 1) in vec2 aAnchorWorld;      // World-space anchor position
layout (location = 2) in vec2 aPixelOffset;      // Screen-space offset in pixels
layout (location = 3) in vec4 aUVRect;           // (u_min, v_min, u_max, v_max)
layout (location = 4) in vec4 aColor;            // RGBA color
layout (location = 5) in vec2 aGlyphSize;        // Glyph size (width, height) in pixels

// Uniforms
uniform mat3 uViewProjection;  // World → NDC
uniform vec2 uViewport;        // Screen dimensions in pixels

// Outputs to fragment shader
out vec2 vTexCoord;
out vec4 vColor;

void main()
{
    // Transform world anchor to NDC
    vec3 ndcAnchor = uViewProjection * vec3(aAnchorWorld, 1.0);
    vec2 ndcPos = ndcAnchor.xy;
    
    // Convert pixel offset to NDC offset
    // In NDC, x ranges from -1 to 1 over viewport width
    // So 1 pixel = 2.0 / viewport_width in NDC
    vec2 ndcPixelSize = 2.0 / uViewport;
    
    // Build the glyph quad in NDC space
    // aQuadVertex is in [0,1] range, scale to pixel size
    vec2 quadOffset = aQuadVertex * aGlyphSize * ndcPixelSize;
    
    // Add pixel offset to position the glyph
    vec2 pixelOffsetNDC = aPixelOffset * ndcPixelSize;
    ndcPos += pixelOffsetNDC + quadOffset;
    
    gl_Position = vec4(ndcPos, 0.0, 1.0);
    
    // Interpolate UV coordinates
    vTexCoord = mix(aUVRect.xy, aUVRect.zw, aQuadVertex);
    vColor = aColor;
}
