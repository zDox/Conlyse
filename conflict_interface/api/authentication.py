from dataclasses import dataclass

from conflict_interface.game_object.decorators import conflict_serializable
from conflict_interface.game_object.game_object_binary import SerializationCategory


@conflict_serializable(SerializationCategory.DATACLASS, version=-1)
@dataclass
class AuthDetails:
    user_id: int
    auth_hash: str
    auth_tstamp: int
    chat_auth: str
    chat_auth_tstamp: int
    uber_auth_hash: str
    uber_auth_tstamp: int
    auth: str = None
    session_token: str = None
    rights: str = None

    url_param_to_variable_name = {
            "userID": "user_id",
            "auth": "auth",
            "authHash": "auth_hash",
            "authTstamp": "auth_tstamp",
            "chatAuth": "chat_auth",
            "chatAuthTstamp": "chat_auth_tstamp",
            "uberAuthHash": "uber_auth_hash",
            "uberAuthTstamp": "uber_auth_tstamp",
            "rights": "rights"
    }
    MAPPING = {
        "user_id": "userID",
        "auth": "auth",
        "auth_hash": "authHash",
        "chat_auth": "chatAuth",
        "chat_auth_tstamp": "chatAuthTstamp",
        "uber_auth_hash": "uberAuthHash",
        "uber_auth_tstamp": "uberAuthTstamp",
        "rights": "rights"
    }

    @classmethod
    def from_url_parameters(cls, url: str):
        parameters = url.split('&')
        parsed_data = {}

        for parameter in parameters[1:]:
            key, value = parameter.split("=")
            if key not in cls.url_param_to_variable_name.keys():
                continue
            parsed_data[cls.url_param_to_variable_name[key]] = cls.__annotations__[
                    cls.url_param_to_variable_name[key]](value)

        return cls(**parsed_data)
