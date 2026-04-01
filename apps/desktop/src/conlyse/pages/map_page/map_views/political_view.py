# political_view.py

from conflict_interface.data_types.newest.map_state.land_province import LandProvince
from conflict_interface.data_types.newest.map_state.sea_province import SeaProvince
from conflict_interface.hook_system.replay_hook_event import ReplayHookEvent

from conlyse.logger import get_logger
from conlyse.pages.map_page.map_views.map_view import MapView

logger = get_logger()

def id_to_rgb(n, max_n=160):
    """Convert ID to RGB color using HSV color space."""
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
    else:  # h_i == 5
        r, g, b = v, p, q

    return r, g, b


class PoliticalView(MapView):
    """
    Political map view that colors provinces based on their owner.

    Each nation is assigned a distinct color, and all provinces owned by
    that nation are shown in that color. Sea provinces are shown in blue.
    """
    def build_color_data(self):
        owner_color_data = {}

        for province in self.ritf.get_provinces().values():
            if province.C == "ultshared.UltSeaProvince":
                self.color_data[province.id] = (70, 130, 180, 255)
                continue

            r, g, b = id_to_rgb(province.owner_id)
            rgba = (r, g, b, 255)
            if province.owner_id not in owner_color_data:
                owner_color_data[province.owner_id] = rgba
            self.color_data[province.id] = rgba

        logger.debug(f"Built political view color data for {len(owner_color_data)} owners.")

    def update_provinces(self, events: list[ReplayHookEvent]):
        for event in events:
            province: LandProvince = event.reference
            changed_attributes: dict = event.attributes
            if 'owner_id' not in changed_attributes:
                continue
            r, g, b = id_to_rgb(province.owner_id)
            self.set_province_color(province.id, (r, g, b, 255))