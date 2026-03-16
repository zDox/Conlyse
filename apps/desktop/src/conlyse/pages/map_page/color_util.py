def rgba_to_normalized(rgba: tuple[int, int, int, int]) -> tuple[float, float, float, float]:
    """Convert RGBA values from 0-255 range to normalized 0.0-1.0 range"""
    r, g, b, a = rgba
    return r / 255.0, g / 255.0, b / 255.0, a / 255.0