from dataclasses import dataclass

from .province import StaticProvince


@dataclass
class StaticMapData():
    provinces: list[StaticProvince]

    @classmethod
    def from_dict(cls, obj):
        provinces = []
        for province in obj["locations"][1]:
            provinces.append(StaticProvince.from_dict(province))

        return cls(**{
            "provinces": provinces,
            })
