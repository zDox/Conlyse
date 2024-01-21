from data_types.province import StaticProvince

from dataclasses import dataclass


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
