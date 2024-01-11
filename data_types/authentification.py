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
    rights: str

    mapping = {
            "userID": "user_id",
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
        parsed_data["rights"] = "null"

        for parameter in parameters[1:]:
            key, value = parameter.split("=")
            if key not in cls.mapping.keys():
                continue
            parsed_data[cls.mapping[key]] = value

        return cls(**parsed_data)
