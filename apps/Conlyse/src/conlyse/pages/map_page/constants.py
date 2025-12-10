"""Constants for the map page module."""

from PyQt6.QtCore import Qt

# Camera constants
MIN_ZOOM = 3
INITIAL_ZOOM = 3
MAX_ZOOM = 20.0

# World boundaries (example world dimensions)
WORLD_MIN_X = 0
WORLD_MIN_Y = 0
WORLD_MAX_X = 15393
WORLD_MAX_Y = 6566

# Connection Line Color
CONNECTION_LINE_COLOR = (100/255, 100/255, 100/255, 0.5)

# Input constants
CAMERA_MOVEMENT_STEP = 10
UPDATE_FRAME_INTERVAL_MS = 16  # ~60 FPS

# Mouse constants
ZOOM_FACTOR_IN = 1.1
ZOOM_FACTOR_OUT = 0.9

# OpenGL configuration
OPENGL_VERSION_MAJOR = 4
OPENGL_VERSION_MINOR = 1