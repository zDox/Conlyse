#version 330 core

in vec2 vTexCoord;
in vec4 vColor;

uniform sampler2D uAtlasTexture;

out vec4 FragColor;

void main()
{
    // Sample the glyph atlas (single-channel)
    float alpha = texture(uAtlasTexture, vTexCoord).r;
    
    // Apply color and alpha
    FragColor = vec4(vColor.rgb, vColor.a * alpha);
    
    // Discard fully transparent fragments
    if (FragColor.a < 0.01) {
        discard;
    }
}
