from typing import Union

from .land_province import LandProvince
from .sea_province import SeaProvince

Province = Union[LandProvince, SeaProvince]