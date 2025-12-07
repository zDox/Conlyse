import numpy as np
from conflict_interface.data_types.map_state.province import Province
from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.pages.map_page.province_color_texture import ProvinceColorTexture


def id_to_rgb(n, max_n=160):
    # Generate hue between 0 and 1
    h = n / max_n
    s = 1.0
    v = 1.0

    h_i = int(h * 6)
    f = (h * 6) - h_i
    p = int(255 * v * (1 - s))
    q = int(255 * v * (1 - f * s))
    t = int(255 * v * (1 - (1 - f) * s))
    v = int(255 * v)

    h_i = h_i % 6
    r, g, b = 0, 0, 0
    if h_i == 0:
        r, g, b = v, t, p
    elif h_i == 1:
        r, g, b = q, v, p
    elif h_i == 2:
        r, g, b = p, v, t
    elif h_i == 3:
        r, g, b = p, q, v
    elif h_i == 4:
        r, g, b = t, p, v
    elif h_i == 5:
        r, g, b = v, p, q

    return r, g, b


class PoliticalView:
    def __init__(self, ritf: ReplayInterface, max_province_id: int):
        self.ritf = ritf
        self.max_id = max_province_id

        self.color_data = None
        self.texture = None

    def build_color_data(self):
        owner_color_data = {}
        self.color_data = np.zeros((self.max_id+1, 4), dtype=np.uint8)

        for province in self.ritf.get_provinces().values():
            r, g, b = id_to_rgb(province.owner_id)
            rgba = (r, g, b, 255)
            if province.owner_id not in owner_color_data:
                owner_color_data[province.owner_id] = rgba
            self.color_data[province.id] = rgba


    def initialize(self):
        # Each MapView owns its own colors
        self.texture = ProvinceColorTexture(self.color_data.flatten())

    def set_province_color(self, province_id: int, rgba: tuple[int, int, int, int]):
        self.color_data[province_id] = rgba
        self.texture.update_data(self.color_data.flatten())

    def update_province(self, province: Province, changed_attributes: dict):
        raise NotImplementedError("Subclasses must implement update_province method.")
