# resource_view.py

from collections import defaultdict

from conflict_interface.data_types.newest.map_state.map_state_enums import ResourceProductionType
from conflict_interface.data_types.newest.map_state.province import Province
from conflict_interface.data_types.newest.map_state.sea_province import SeaProvince
from conflict_interface.hook_system.replay_hook_event import ReplayHookEvent

from conlyse.logger import get_logger
from conlyse.pages.map_page.map_views.map_view import MapView

logger = get_logger()

RESOURCE_PRODUCTION_COLOR_RANGE = {
    ResourceProductionType.NONE: ((230, 230, 230), (255, 255, 255)),
    ResourceProductionType.SUPPLY: ((120, 220, 120), (60, 120, 60)),
    ResourceProductionType.COMPONENT: ((140, 180, 230), (70, 90, 120)),
    ResourceProductionType.MANPOWER: ((200, 160, 110), (110, 80, 50)),
    ResourceProductionType.RARE_MATERIAL: ((180, 120, 220), (90, 50, 120)),
    ResourceProductionType.FUEL: ((240, 90, 60), (140, 40, 30)),
    ResourceProductionType.ELECTRONIC: ((120, 220, 220), (40, 100, 100)),
    ResourceProductionType.MONEY: ((255, 215, 0), (120, 100, 30)),
}

def interpolate_color(color1, color2, factor):
    r = max(0, min(int(color1[0] + (color2[0] - color1[0]) * factor), 255))
    g = max(0, min(int(color1[1] + (color2[1] - color1[1]) * factor), 255))
    b = max(0, min(int(color1[2] + (color2[2] - color1[2]) * factor), 255))
    return r, g, b

class ResourceView(MapView):
    """
    Resource map view that colors provinces based on their resource production.
    Maintains per-resource province sets for fast incremental updates.
    """
    def __init__(self, ritf, max_province_id: int):
        super().__init__(ritf, max_province_id)
        # min/max and count per resource
        self.min_max_resource_production = {}
        # set of province IDs per resource type
        self.provinces_by_resource = defaultdict(set)

    def build_min_max_resource_production(self):
        self.min_max_resource_production.clear()
        self.provinces_by_resource.clear()

        for province in self.ritf.get_provinces().values():
            if isinstance(province, SeaProvince):
                continue

            rt = province.resource_production_type
            if rt == ResourceProductionType.NONE:
                continue

            prod = province.resource_production
            self.provinces_by_resource[rt].add(province.id)

            if rt not in self.min_max_resource_production:
                self.min_max_resource_production[rt] = {
                    "min": prod, "max": prod
                }
            else:
                self.min_max_resource_production[rt]["min"] = min(
                    self.min_max_resource_production[rt]["min"], prod)
                self.min_max_resource_production[rt]["max"] = max(
                    self.min_max_resource_production[rt]["max"], prod)

    def _build_color_data(self):
        for province in self.ritf.get_provinces().values():
            if isinstance(province, SeaProvince):
                self.color_data[province.id] = (70, 130, 180, 255)
                continue

            rt = province.resource_production_type
            if rt == ResourceProductionType.NONE:
                self.color_data[province.id] = (200, 200, 200, 255)
                continue

            min_color, max_color = RESOURCE_PRODUCTION_COLOR_RANGE.get(rt,
                RESOURCE_PRODUCTION_COLOR_RANGE[ResourceProductionType.NONE])
            min_prod, max_prod = self.min_max_resource_production.get(rt, {"min": 0, "max": 0}).values()

            factor = 1.0 if max_prod == min_prod else \
                (province.resource_production - min_prod) / (max_prod - min_prod)
            r, g, b = interpolate_color(min_color, max_color, factor)
            self.color_data[province.id] = (r, g, b, 255)

    def build_color_data(self):
        self.build_min_max_resource_production()
        self._build_color_data()
        logger.debug(f"ResourceView color data built with {len(self.color_data)} provinces.")

    def _rebuild_min_max_for_resource(self, resource_type):
        min_p = float("inf")
        max_p = float("-inf")
        provinces = self.ritf.get_provinces()
        province_ids = self.provinces_by_resource.get(resource_type, [])
        for pid in province_ids:
            p = provinces[pid]
            prod = p.resource_production
            min_p = min(min_p, prod)
            max_p = max(max_p, prod)
        if province_ids:
            self.min_max_resource_production[resource_type] = {"min": min_p, "max": max_p}
        elif resource_type in self.min_max_resource_production:
            del self.min_max_resource_production[resource_type]
    def _recolor_resource(self, resource_type):
        min_color, max_color = RESOURCE_PRODUCTION_COLOR_RANGE.get(resource_type,
            RESOURCE_PRODUCTION_COLOR_RANGE[ResourceProductionType.NONE])
        min_prod, max_prod = self.min_max_resource_production.get(resource_type, {"min": 0, "max": 0}).values()
        provinces = self.ritf.get_provinces()
        for pid in self.provinces_by_resource.get(resource_type, []):
            p = provinces[pid]
            factor = 1.0 if max_prod == min_prod else \
                (p.resource_production - min_prod) / (max_prod - min_prod)
            r, g, b = interpolate_color(min_color, max_color, factor)
            self.color_data[pid] = (r, g, b, 255)

    def _recolor_single_province(self, province: Province):
        rt = province.resource_production_type
        min_color, max_color = RESOURCE_PRODUCTION_COLOR_RANGE.get(rt,
            RESOURCE_PRODUCTION_COLOR_RANGE[ResourceProductionType.NONE])
        min_prod, max_prod = self.min_max_resource_production.get(rt, {"min": 0, "max": 0}).values()

        factor = 1.0 if max_prod == min_prod else \
            (province.resource_production - min_prod) / (max_prod - min_prod)
        r, g, b = interpolate_color(min_color, max_color, factor)
        self.color_data[province.id] = (r, g, b, 255)

    def update_provinces(self, events: list[ReplayHookEvent]):
        resource_type_rebuild_needed = set()
        for event in events:
            province: Province = event.reference
            changed_attributes: dict = event.attributes

            if "resource_production" not in changed_attributes:
                continue

            old, new = changed_attributes["resource_production"]
            rt = province.resource_production_type
            if rt == ResourceProductionType.NONE:
                continue


            min_prod, max_prod = self.min_max_resource_production.get(rt, {"min": new, "max": new}).values()

            # Rebuild min/max if old was min/max or new breaks the range
            rebuild_needed = old == min_prod or old == max_prod or new < min_prod or new > max_prod
            if rebuild_needed:
                resource_type_rebuild_needed.add(rt)
            else:
                self._recolor_single_province(province)

        for rt in resource_type_rebuild_needed:
            self._rebuild_min_max_for_resource(rt)
            self._recolor_resource(rt)