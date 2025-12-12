from enum import StrEnum


class KeyAction(StrEnum):
    # ---- Global actions ----
    # Navigation
    TOGGLE_DRAWER = "toggle_drawer"
    # Debug
    RELOAD_STYLES = "reload_styles"
    TOGGLE_THEME = "toggle_theme"



    # ---- ReplayListPage specific ----
    OPEN_REPLAY_FILE_DIALOG = "open_replay_file_dialog"


    # ---- MapPage specific ----
    # Camera controls
    CAMERA_MOVE_UP = "camera_move_up"
    CAMERA_MOVE_DOWN = "camera_move_down"
    CAMERA_MOVE_LEFT = "camera_move_left"
    CAMERA_MOVE_RIGHT = "camera_move_right"
    CAMERA_ZOOM_IN = "camera_zoom_in"
    CAMERA_ZOOM_OUT = "camera_zoom_out"

    # Map View Switches
    SWITCH_TO_POLITICAL_MAP_VIEW = "switch_to_political_map_view"
    SWITCH_TO_TERRAIN_MAP_VIEW = "switch_to_terrain_map_view"

    # Toggle Connections Overlay
    TOGGLE_CONNECTIONS_OVERLAY = "toggle_connections_overlay"
    
    # Performance monitoring
    TOGGLE_PERFORMANCE_WINDOW = "toggle_performance_window"

    # Debug
    DEBUG_TOGGLE_MOUSE_CLICK_LOGGING = "debug_toggle_mouse_click_logging"