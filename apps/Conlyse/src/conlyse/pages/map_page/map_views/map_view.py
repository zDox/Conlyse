# map_view_base.py
from enum import Enum

import numpy as np
from abc import ABC, abstractmethod
from conflict_interface.data_types.map_state.province import Province
from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.pages.map_page.opengl_wrapper.color_palette_texture import ColorPaletteTexture


class MapView(ABC):
    """Base class for different map visualization modes."""

    def __init__(self, ritf: ReplayInterface, max_province_id: int):
        self.ritf = ritf
        self.max_id = max_province_id
        self.color_data = None
        self.texture = None

    @abstractmethod
    def build_color_data(self):
        """Build the initial color data array. Must be implemented by subclasses."""
        pass

    def initialize(self):
        """Initialize the texture with the color data."""
        if self.color_data is None:
            raise RuntimeError("build_color_data must be called before initialize")
        self.texture = ColorPaletteTexture(self.color_data.flatten())

    def set_province_color(self, province_id: int, rgba: tuple[int, int, int, int]):
        """Update a single province's color."""
        self.color_data[province_id] = rgba
        self.texture.update_data(self.color_data.flatten())

    @abstractmethod
    def update_province(self, province: Province, changed_attributes: dict):
        """Handle province updates. Must be implemented by subclasses."""
        pass

    def _init_color_array(self):
        """Helper to create the base color data array."""
        return np.zeros((self.max_id + 1, 4), dtype=np.uint8)