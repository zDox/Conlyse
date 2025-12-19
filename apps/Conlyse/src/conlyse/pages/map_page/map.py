import time

import numpy as np
from OpenGL import GL as gl
from PySide6.QtCore import QSize
from PySide6.QtCore import Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QSizePolicy
from conflict_interface.data_types.map_state.map_state_enums import ProvinceStateID
from conflict_interface.data_types.map_state.sea_province import SeaProvince
from conflict_interface.hook_system.replay_hook_event import ReplayHookEvent
from conflict_interface.hook_system.replay_hook_tag import ReplayHookTag
from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.logger import get_logger
from conlyse.pages.map_page.camera import Camera
from conlyse.pages.map_page.constants import CITY_LABEL_COLOR
from conlyse.pages.map_page.constants import CITY_LABEL_OUTLINE_COLOR
from conlyse.pages.map_page.constants import CITY_LABEL_OUTLINE_WIDTH
from conlyse.pages.map_page.constants import CITY_LABEL_SIZE
from conlyse.pages.map_page.constants import NATION_LABEL_COLOR
from conlyse.pages.map_page.constants import NATION_LABEL_SHADOW_COLOR
from conlyse.pages.map_page.constants import NATION_LABEL_SHADOW_OFFSET
from conlyse.pages.map_page.map_views.map_view_type import MapViewType
from conlyse.pages.map_page.opengl_wrapper.color_palette_texture import ColorPaletteTexture
from conlyse.pages.map_page.renderers.province_border_renderer import ProvinceBorderRenderer
from conlyse.pages.map_page.renderers.province_connection_renderer import ProvinceConnectionRenderer
from conlyse.pages.map_page.renderers.province_fill_renderer import ProvinceFillRenderer
from conlyse.pages.map_page.renderers.world_text_renderer import TextGroup, WorldTextRenderer

logger = get_logger()

class Map(QOpenGLWidget):
    def __init__(self, ritf: ReplayInterface, main_config, parent=None):
        super().__init__(parent=parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.ritf = ritf

        # Determine if the map is wraps around
        self.enable_wrapping = ritf.game_state.states.map_state.map.overlap_x != 0
        self.world_min_x = 0
        self.world_max_x = ritf.game_state.states.map_state.map.width
        self.world_min_y = 0
        self.world_max_y = ritf.game_state.states.map_state.map.height
        self.world_width = self.world_max_x - self.world_min_x
        self.world_height = self.world_max_y - self.world_min_y

        self.enable_anti_aliasing: bool = main_config.get("graphics.anti_aliasing")

        self.disable_pyqt_redraws()

        self.camera = Camera(self)
        self.province_fill_renderer = ProvinceFillRenderer(self)
        self.province_connection_renderer = ProvinceConnectionRenderer(self)
        self.province_border_renderer = ProvinceBorderRenderer(self)
        self.world_text_renderer = WorldTextRenderer(self, font_size=100)
        self.last_render_time = time.perf_counter()

        self.active_map_view = MapViewType.POLITICAL
        self.render_connections = True

        # Track if we should skip paint events (to avoid double rendering)
        self._manual_render_mode = False
        
        # Performance tracking
        self.performance_metrics = {
            "province_fill": 0.0,
            "province_connections": 0.0,
            "province_borders": 0.0,
            "world_text": 0.0,
            "terrainview_update": 0.0,
            "resourceview_update": 0.0,
            "politicalview_update": 0.0,
            "render_frame": 0.0,
            "time_since_last_frame": 0.0,
        }

        # Province picking resources
        self._picking_fbo: int | None = None
        self._picking_texture: int | None = None
        self._picking_depth_rbo: int | None = None
        self._picking_palette_texture: ColorPaletteTexture | None = None
        self._picking_size: tuple[int, int] = (0, 0)

    def disable_pyqt_redraws(self):
        # Prevent Qt automatic redraws
        self.setUpdateBehavior(QOpenGLWidget.UpdateBehavior.NoPartialUpdate)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_PaintOnScreen, False)

    # Ignore Qt paint events
    def paintEvent(self, event):
        # No idea why, but on Linux we need to pass the event to the parent class
        # On Windows this is not necessary
        return super().paintEvent(event)

    def set_active_map_view(self, map_view: MapViewType):
        """
        Set the active map view type.

        Args:
            map_view: The MapViewType to set as active
        """
        self.active_map_view = map_view

    def toggle_render_connections(self):
        """Toggle the rendering of province connections."""
        self.render_connections = not self.render_connections

    def initializeGL(self):
        """Initialize OpenGL resources. Called once when the widget is first shown."""
        self.province_fill_renderer.initialize()
        self.province_connection_renderer.initialize()
        self.province_border_renderer.initialize()
        self.world_text_renderer.initialize()
        gl.glClearColor(0.1, 0.1, 0.1, 1.0)
        # Enable blending
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        if self.enable_anti_aliasing:
            gl.glEnable(gl.GL_MULTISAMPLE)
        self._initialize_world_labels()

    def paintGL(self):
        """Render the map. Called whenever the widget needs to be redrawn."""
        if not self._manual_render_mode:
            return  # Skip automatic paint events
        self.performance_metrics["time_since_last_frame"] = (time.perf_counter() - self.last_render_time) * 1000
        self.last_render_time = time.perf_counter()
        frame_start = time.perf_counter()
        
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        
        # Track province fill renderer time
        render_start = time.perf_counter()
        self.province_fill_renderer.render(self.active_map_view)
        self.performance_metrics["province_fill"] = (time.perf_counter() - render_start) * 1000

        # Track province connection renderer time
        render_start = time.perf_counter()
        if self.render_connections:
            self.province_connection_renderer.render()
        self.performance_metrics["province_connections"] = (time.perf_counter() - render_start) * 1000

        # Track province border renderer time
        render_start = time.perf_counter()
        self.province_border_renderer.render()
        self.performance_metrics["province_borders"] = (time.perf_counter() - render_start) * 1000
        
        # Track world text renderer time
        render_start = time.perf_counter()
        self.world_text_renderer.render()
        self.performance_metrics["world_text"] = (time.perf_counter() - render_start) * 1000
        
        self.performance_metrics["render_frame"] = (time.perf_counter() - frame_start) * 1000

    def resizeGL(self, w: int, h: int):
        """
        Handle widget resize events.

        Args:
            w: New width in pixels
            h: New height in pixels
        """
        gl.glViewport(0, 0, w, h)
        self.render_frame()

    def minimumSizeHint(self) -> QSize:
        return QSize(200, 200)

    def render_frame(self):
        # Render manually
        self._manual_render_mode = True
        self.makeCurrent()
        self.paintGL()
        self.doneCurrent()

        # Blit to widget once
        self.update()
        self._manual_render_mode = False

    def get_province_id_at_world_position(self, world_x: float, world_y: float) -> int | None:
        """
        Determine the province ID at the given world position using GPU color picking.

        Renders the provinces into an offscreen framebuffer where each province has a
        unique color derived from its ID, then reads back the pixel corresponding to
        the provided world coordinates.
        """
        width = self.width()
        height = self.height()
        if width <= 0 or height <= 0:
            return None
        if self.province_fill_renderer.program is None or self.province_fill_renderer.vao is None:
            return None

        screen_pos = self.camera.world_to_screen(world_x, world_y)
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        if sx < 0 or sy < 0 or sx >= width or sy >= height:
            return None

        self.makeCurrent()
        try:
            if not self._ensure_picking_framebuffer(width, height):
                return None
            self._ensure_picking_palette_texture()

            prev_fb = int(gl.glGetIntegerv(gl.GL_FRAMEBUFFER_BINDING))
            prev_viewport = tuple(int(v) for v in gl.glGetIntegerv(gl.GL_VIEWPORT))
            blend_enabled = gl.glIsEnabled(gl.GL_BLEND)

            prev_clear_color = gl.glGetFloatv(gl.GL_COLOR_CLEAR_VALUE)

            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self._picking_fbo)
            gl.glViewport(0, 0, width, height)
            gl.glClearColor(0.0, 0.0, 0.0, 0.0)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
            if blend_enabled:
                gl.glDisable(gl.GL_BLEND)

            self.province_fill_renderer.render_palette(self._picking_palette_texture)

            pixel = gl.glReadPixels(sx, height - sy - 1, 1, 1, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE)

            if blend_enabled:
                gl.glEnable(gl.GL_BLEND)
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, prev_fb)
            gl.glClearColor(prev_clear_color[0], prev_clear_color[1], prev_clear_color[2], prev_clear_color[3])
            gl.glViewport(prev_viewport[0], prev_viewport[1], prev_viewport[2], prev_viewport[3])
        finally:
            self.doneCurrent()

        if pixel is None:
            return None

        rgba = np.frombuffer(pixel, dtype=np.uint8, count=4)
        if rgba.size < 4:
            return None
        encoded = int(rgba[0]) | (int(rgba[1]) << 8) | (int(rgba[2]) << 16)
        if encoded == 0:
            return None
        return encoded - 1

    def apply_hook_events(self, events: dict[ReplayHookTag, list[ReplayHookEvent]]):
        if ReplayHookTag.ProvinceChanged in events:
            self.province_fill_renderer.handle_province_change_events(events[ReplayHookTag.ProvinceChanged])

    def cleanup(self):
        """Clean up OpenGL resources."""
        self.makeCurrent()
        self.world_text_renderer.cleanup()
        self._destroy_picking_resources()
        self.doneCurrent()
    
    def get_performance_metrics(self):
        """
        Get the current performance metrics.
        
        Returns:
            dict: Dictionary containing performance metrics in milliseconds
        """
        return self.performance_metrics.copy()

    def _ensure_picking_palette_texture(self):
        if self._picking_palette_texture is not None:
            return
        max_id = self.province_fill_renderer.province_mesh.max_province_id
        color_data = np.zeros((max_id + 1, 4), dtype=np.uint8)
        for province_id in range(max_id + 1):
            encoded = province_id + 1  # Offset to reserve 0 for 'no hit'
            color_data[province_id] = (
                encoded & 0xFF,
                (encoded >> 8) & 0xFF,
                (encoded >> 16) & 0xFF,
                255
            )
        self._picking_palette_texture = ColorPaletteTexture(color_data.flatten())

    def _ensure_picking_framebuffer(self, width: int, height: int) -> bool:
        if self._picking_fbo is None:
            self._picking_fbo = gl.glGenFramebuffers(1)
            self._picking_texture = gl.glGenTextures(1)
            self._picking_depth_rbo = gl.glGenRenderbuffers(1)

        if self._picking_size == (width, height):
            return True

        gl.glBindTexture(gl.GL_TEXTURE_2D, self._picking_texture)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA8, width, height, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, None)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)

        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, self._picking_depth_rbo)
        gl.glRenderbufferStorage(gl.GL_RENDERBUFFER, gl.GL_DEPTH_COMPONENT24, width, height)

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self._picking_fbo)
        gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, gl.GL_TEXTURE_2D, self._picking_texture, 0)
        gl.glFramebufferRenderbuffer(gl.GL_FRAMEBUFFER, gl.GL_DEPTH_ATTACHMENT, gl.GL_RENDERBUFFER, self._picking_depth_rbo)

        status = gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, 0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

        if status != gl.GL_FRAMEBUFFER_COMPLETE:
            logger.error(f"Province picking framebuffer incomplete: {status}")
            return False

        self._picking_size = (width, height)
        return True

    def _destroy_picking_resources(self):
        if self._picking_palette_texture is not None:
            gl.glDeleteTextures([self._picking_palette_texture.texture_id])
            self._picking_palette_texture = None
        if self._picking_texture is not None:
            gl.glDeleteTextures([self._picking_texture])
            self._picking_texture = None
        if self._picking_depth_rbo is not None:
            gl.glDeleteRenderbuffers(1, [self._picking_depth_rbo])
            self._picking_depth_rbo = None
        if self._picking_fbo is not None:
            gl.glDeleteFramebuffers(1, [self._picking_fbo])
            self._picking_fbo = None
        self._picking_size = (0, 0)

    def _initialize_world_labels(self):
        for province in self.ritf.get_provinces().values():
            if isinstance(province, SeaProvince):
                continue
            if province.province_state_id not in (
                ProvinceStateID.MAINLAND_CITY,
                ProvinceStateID.ANNEXED_CITY,
                ProvinceStateID.OCCUPIED_CITY,
            ):
                continue
            province_center = province.center_coordinate
            self.world_text_renderer.add_text(
                province.name,
                anchor_world=(province_center.x, province_center.y),
                color=CITY_LABEL_COLOR,
                outline_width=CITY_LABEL_OUTLINE_WIDTH,
                outline_color=CITY_LABEL_OUTLINE_COLOR,
                size_world=CITY_LABEL_SIZE,
                group=TextGroup.CITY_LABELS
            )

        for player in self.ritf.get_players().values():
            if player.nation_label_coord is None:
                logger.warning(f"Player {player.nation_name} has no nation label coordinates, skipping label")
                continue
            nation_label_coordinate = player.nation_label_coord.x, player.nation_label_coord.y
            nation_label_size = player.nation_label_size * 100
            self.world_text_renderer.add_text(
                player.nation_name,
                centered=True,
                shadow_offset=NATION_LABEL_SHADOW_OFFSET,
                shadow_color=NATION_LABEL_SHADOW_COLOR,
                anchor_world=nation_label_coordinate,
                color=NATION_LABEL_COLOR,
                size_world=nation_label_size,
                group=TextGroup.NATION_LABELS
            )
