from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable

from ..version import VERSION

@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class SystemInformation(GameObject):
    C = "ultshared.action.UltSystemInfos"
    verbose: bool
    client_version: str
    processors: str
    acc_mem: str
    java_version: str
    os_arch: str
    os_name: str
    os_version: str
    os_patch_level: str
    user_country: str
    screen_width: int
    screen_height: int

    MAPPING = {
        "verbose": "verbose",
        "client_version": "clientVersion",
        "processors": "processors",
        "acc_mem": "accMem",
        "java_version": "javaVersion",
        "os_arch": "osArch",
        "os_name": "osName",
        "os_version": "osVersion",
        "os_patch_level": "osPatchLevel",
        "user_country": "userCountry",
        "screen_width": "screenWidth",
        "screen_height": "screenHeight",
    }