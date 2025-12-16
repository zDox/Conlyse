# WorldTextRenderer Usage Example

This example demonstrates how to use the `WorldTextRenderer` to add text labels to the map.

## Basic Usage

```python
from conlyse.pages.map_page.renderers.world_text_renderer import WorldTextRenderer

# The renderer is automatically initialized in the Map class
# Access it via: map_widget.world_text_renderer

# Add a text label at world coordinates (100, 50)
text_id = map_widget.world_text_renderer.add_text(
    text="Hello World",
    anchor_world=(100.0, 50.0),
    color=(1.0, 1.0, 1.0, 1.0),  # White, fully opaque
    size_px=16.0  # 16 pixels tall
)

# Update the text
map_widget.world_text_renderer.update_text(
    text_id,
    text="Updated Text",
    color=(1.0, 0.0, 0.0, 1.0)  # Red
)

# Remove the text
map_widget.world_text_renderer.remove_text(text_id)
```

## Integration Example

To add city labels to provinces:

```python
def add_province_labels(map_widget):
    """Add text labels for all provinces."""
    ritf = map_widget.ritf
    text_renderer = map_widget.world_text_renderer
    
    for province_id, location in ritf.game_state.states.map_state.map.static_map_data.locations.items():
        # Get province center
        center_x = location.center.x
        center_y = location.center.y
        
        # Add label
        text_id = text_renderer.add_text(
            text=str(province_id),
            anchor_world=(center_x, center_y),
            color=(1.0, 1.0, 1.0, 0.8),  # Semi-transparent white
            size_px=12.0
        )
```

## Features

### Screen-Space Stability
Text size remains constant in pixels regardless of zoom level:
- When zoomed in, text doesn't get larger
- When zoomed out, text doesn't get smaller
- Only the position moves with the world anchor

### Batched Rendering
All text is rendered in a single draw call:
- Efficient GPU usage
- Minimal CPU overhead
- Scales well with many text labels

### Dynamic Updates
Text can be added, updated, or removed at any time:
- Changes are buffered on the CPU
- GPU buffer is updated only when needed (dirty flag)
- Uses buffer orphaning for efficient updates

## Performance

The renderer tracks its performance metrics in `map_widget.performance_metrics["world_text"]`.
You can view this in the Performance Window when enabled.

## Font Customization

The renderer uses system fonts in the following order:
1. Liberation Sans (Linux)
2. DejaVu Sans (Linux fallback)
3. Helvetica (macOS)
4. Arial (Windows)

To use a different font size, modify the `font_size` parameter when creating the renderer
(default: 48px for the atlas, scaled at runtime via `size_px`).

## Technical Details

- **Rendering method**: Instanced drawing with `glDrawArraysInstanced`
- **Shader approach**: Vertex shader transforms world anchor to NDC, adds pixel offsets
- **Atlas**: Single 1024x1024 texture containing all ASCII glyphs
- **Buffer management**: Dynamic VBO with orphaning for efficient updates
- **Text layout**: Left-aligned, baseline-aligned, horizontal only

## Limitations

- Only supports ASCII printable characters (32-126)
- No line wrapping (single-line text only)
- No right-to-left or bidirectional text
- No font fallback for missing glyphs
- Horizontal layout only (no vertical text)

## Cleanup

The renderer automatically cleans up its OpenGL resources when the Map widget is destroyed.
No manual cleanup is required in normal usage.
