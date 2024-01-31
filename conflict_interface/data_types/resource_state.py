from dataclasses import dataclass

from resources import ResourceProfile


@dataclass
class ResourceState:
    STATE_ID = 4
    resource_profiles: dict[int, ResourceProfile]

    # Trading, Own Resources
    @classmethod
    def from_dict(cls, obj):
        resource_profiles = {int(player_id):
                             ResourceProfile.from_dict(resource_profile)
                             for player_id, resource_profile
                             in list(obj["resourceProfs"].items())[1:]}
        return cls(**{
            "resource_profiles": resource_profiles,
            })
