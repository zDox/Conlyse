# Performance Window

## Overview

The Performance Window is a global floating widget that displays performance metrics for the application. It can be toggled on/off using the `F3` key (by default) and is available across all pages.

## Features

- **Global Availability**: The performance window is accessible from any page in the application
- **Page-Specific Metrics**: Each page can register and update its own custom performance metrics
- **Real-time Updates**: Displays FPS, frame time, and custom metrics in real-time
- **Floating Window**: Stays on top of the application window for easy monitoring

## Usage

### For Users

1. Press `F3` (default keybinding, configurable in keybindings.json) to toggle the performance window visibility
2. The window will display:
   - Current page name
   - FPS (Frames Per Second)
   - Frame Time (in milliseconds)
   - Page-specific performance metrics

### For Developers

#### Accessing the Performance Window

The performance window is available globally through the `App` instance:

```python
self.app.performance_window
```

#### Setting Up Metrics for a Page

When a page is initialized or setup, clear existing metrics and add new ones:

```python
def setup(self, context):
    # Clear any existing metrics from previous page
    self.app.performance_window.clear_metrics()
    
    # Set the current page name
    self.app.performance_window.set_page("My Page")
    
    # Add custom metrics
    self.app.performance_window.add_metric("Renderer A")
    self.app.performance_window.add_metric("Renderer B")
    self.app.performance_window.add_metric("Data Processing")
```

#### Updating Metrics

In your page's `update()` method or wherever performance data is collected:

```python
def update(self):
    # Only update if the window is visible (for performance)
    if self.app.performance_window.isVisible():
        # Update custom metrics
        self.app.performance_window.update_metric("Renderer A", 2.5)  # 2.5 ms
        self.app.performance_window.update_metric("Renderer B", 1.8)  # 1.8 ms
        
        # Update frame time
        self.app.performance_window.update_frame_time(total_time)
        
        # Update FPS (typically calculated over time)
        self.app.performance_window.update_fps(fps)
```

#### API Reference

**PerformanceWindow Methods:**

- `clear_metrics()` - Clear all custom metrics (call when switching pages)
- `set_page(page_name: str)` - Set the current page name
- `add_metric(name: str)` - Add a new performance metric to track
- `update_metric(name: str, value: float, unit: str = "ms")` - Update a metric value
- `update_frame_time(time_ms: float)` - Update total frame time
- `update_fps(fps: float)` - Update FPS display
- `toggle_visibility()` - Toggle window visibility

## Example: MapPage Implementation

The MapPage demonstrates how to use the performance window:

1. **Setup** - Registers "Province Fill" and "Province Connections" metrics
2. **Performance Tracking** - The Map widget tracks renderer times using `time.perf_counter()`
3. **Update** - MapPage updates the performance window with timing data every frame
4. **FPS Calculation** - Calculates FPS over a 0.5 second interval

```python
# In MapPage.setup()
self.app.performance_window.clear_metrics()
self.app.performance_window.set_page("Map Page")
self.app.performance_window.add_metric("Province Fill")
self.app.performance_window.add_metric("Province Connections")

# In MapPage.update()
if self.app.performance_window.isVisible():
    metrics = self.map_widget.get_performance_metrics()
    self.app.performance_window.update_metric("Province Fill", metrics["province_fill"])
    self.app.performance_window.update_metric("Province Connections", metrics["province_connections"])
    self.app.performance_window.update_frame_time(metrics["total_frame"])
```

## Keybinding

The default keybinding is `F3` and can be customized in the keybindings configuration:

```json
{
    "actions": {
        "toggle_performance_window": "F3"
    }
}
```

## Styling

The performance window can be styled using QSS. Key object names:

- `#performance_window` - The window container
- `#performance_label` - Individual metric labels
- `#panel_title` - The window title

Example styling (in `global_style.qss`):

```css
#performance_window {
    background-color: $surface;
    border: 1px solid $border;
    border-radius: 4px;
}

#performance_label {
    color: $text;
    padding: 2px;
    font-family: "Consolas", "Courier New", monospace;
}
```
