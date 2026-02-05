from dataclasses import dataclass

from conflict_interface.data_types.action import Action
from conflict_interface.data_types.game_api_types.system_information import SystemInformation
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable


from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class LoginAction(Action):
    C = "ultshared.action.UltLoginAction"
    resolution: str
    system_information: SystemInformation

    MAPPING = {
        **Action.MAPPING,
        "resolution": "resolution",
        "system_information": "sysInfos"
    }

DEFAULT_LOGIN_ACTION = LoginAction(
    resolution="1920x1080",
    system_information=SystemInformation(
        verbose=False,
        client_version="1",
        processors="",
        acc_mem="",
        java_version="",
        os_arch="",
        os_name="UNIX",
        os_version="",
        os_patch_level="",
        user_country="",
        screen_width=1920,
        screen_height=1080
    )
)