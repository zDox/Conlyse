from dataclasses import dataclass


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

    MAPPING = {
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

    @classmethod
    def from_url_parameters(cls, url: str):
        parameters = url.split('&')
        parsed_data = {}

        for parameter in parameters[1:]:
            key, value = parameter.split("=")
            if key not in cls.MAPPING.keys():
                continue
            parsed_data[cls.MAPPING[key]] = cls.__annotations__[
                    cls.MAPPING[key]](value)

        return cls(**parsed_data)
