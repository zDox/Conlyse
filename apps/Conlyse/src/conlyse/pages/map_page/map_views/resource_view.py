# political_view.py
from conflict_interface.data_types.map_state.map_state_enums import ResourceProductionType
from conflict_interface.data_types.map_state.province import Province
from conflict_interface.data_types.map_state.sea_province import SeaProvince


from conlyse.logger import get_logger
from conlyse.pages.map_page.map_views.map_view import MapView

logger = get_logger()

RESOURCE_PRODUCTION_COLOR_RANGE = {
    # neutral / no production
    ResourceProductionType.NONE: (
        (230, 230, 230),  # light gray (min)
        (255, 255, 255),  # white (max)
    ),

    # food / logistics → green
    ResourceProductionType.SUPPLY: (
        (120, 220, 120),  # bright green
        (60, 120, 60),    # dark green
    ),

    # industrial parts → steel blue / gray-blue
    ResourceProductionType.COMPONENT: (
        (140, 180, 230),  # light blue
        (70, 90, 120),  # dark steel blue
    ),

    # people / workforce → earthy brown
    ResourceProductionType.MANPOWER: (
        (200, 160, 110),  # sand / skin-tone
        (110, 80, 50),  # dark brown
    ),

    # rare resources → purple-magenta (valuable, exotic)
    ResourceProductionType.RARE_MATERIAL: (
        (180, 120, 220),  # vivid purple
        (90, 50, 120),  # dark purple
    ),

    # fuel / oil → red-orange
    ResourceProductionType.FUEL: (
        (240, 90, 60),    # bright red-orange
        (140, 40, 30),  # dark red
    ),

    # electronics → cyan / teal
    ResourceProductionType.ELECTRONIC: (
        (120, 220, 220),  # bright cyan
        (40, 100, 100),  # dark teal
    ),

    # money → gold
    ResourceProductionType.MONEY: (
        (255, 215, 0),    # classic gold
        (120, 100, 30),  # dark gold
    ),
}

def interpolate_color(color1, color2, factor):
    r = int(color1[0] + (color2[0] - color1[0]) * factor)
    g = int(color1[1] + (color2[1] - color1[1]) * factor)
    b = int(color1[2] + (color2[2] - color1[2]) * factor)
    return r, g, b

class ResourceView(MapView):
    """
    Resource map view that colors provinces based on their resource production.
    """
    def __init__(self, ritf, max_province_id: int):
        super().__init__(ritf, max_province_id)
        self.min_max_resource_production = {}

    def build_min_max_resource_production(self):
        for province in self.ritf.get_provinces().values():
            if isinstance(province, SeaProvince):
                continue
            resource_type = province.resource_production_type
            production_amount = province.resource_production
            if resource_type == ResourceProductionType.NONE:
                continue
            if resource_type not in self.min_max_resource_production:
                self.min_max_resource_production[resource_type] = [production_amount, production_amount]
            else:
                current_min, current_max = self.min_max_resource_production[resource_type]
                self.min_max_resource_production[resource_type][0] = min(current_min, production_amount)
                self.min_max_resource_production[resource_type][1] = max(current_max, production_amount)

    def _build_color_data(self):
        for province in self.ritf.get_provinces().values():
            if isinstance(province, SeaProvince):
                self.color_data[province.id] = (70, 130, 180, 255)
                continue

            if province.resource_production_type == ResourceProductionType.NONE:
                self.color_data[province.id] = (200, 200, 200, 255)
                continue

            min_color, max_color = RESOURCE_PRODUCTION_COLOR_RANGE.get(province.resource_production_type,
                                                                      RESOURCE_PRODUCTION_COLOR_RANGE[ResourceProductionType.NONE])
            min_prod, max_prod = self.min_max_resource_production.get(province.resource_production_type, (0, 0))
            if max_prod == min_prod:
                factor = 1.0
            else:
                factor = (province.resource_production - min_prod) / (max_prod - min_prod)
            r, g, b = interpolate_color(min_color, max_color, factor)
            self.color_data[province.id] = (r, g, b, 255)

    def build_color_data(self):
        self.build_min_max_resource_production()
        self._build_color_data()

        logger.debug(f"ResourceView color data built with {len(self.color_data)} provinces.")


    def update_province(self, province: Province, changed_attributes: dict):
        if "resource_production" not in changed_attributes:
            return

        if province.resource_production_type == ResourceProductionType.NONE:
            return
        logger.debug(f"Updating province {province.id} in due to resource production change.")

        min_prod, max_prod = self.min_max_resource_production.get(province.resource_production_type, (0, 0))
        # If the changed production is outside the current min/max, rebuild everything
        if not (min_prod <= province.resource_production <= max_prod):
            self.build_min_max_resource_production()
            self._build_color_data()
            return

        min_color, max_color = RESOURCE_PRODUCTION_COLOR_RANGE.get(province.resource_production_type,
                                                                   RESOURCE_PRODUCTION_COLOR_RANGE[
                                                                       ResourceProductionType.NONE])

        if max_prod == min_prod:
            factor = 1.0
        else:
            factor = (province.resource_production - min_prod) / (max_prod - min_prod)
        r, g, b = interpolate_color(min_color, max_color, factor)
        self.color_data[province.id] = (r, g, b, 255)