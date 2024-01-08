from dataclasses import dataclass


json_to_auth_details_mapping = {
        "userID": "user_id",
        "authHash": "auth_hash",
        "authTstamp": "auth_tstamp",
        "chatAuth": "chat_auth",
        "chatAuthTstamp": "chat_auth_tstamp",
        "uberAuthHash": "uber_auth_hash",
        "uberAuthTstamp": "uber_auth_tstamp",
        "rights": "rights"
}


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

    @classmethod
    def from_url_parameters(cls, url: str):
        parameters = url.split('&')
        parsed_data = {}
        parsed_data["rights"] = "null"

        for parameter in parameters[1:]:
            key, value = parameter.split("=")
            if key not in json_to_auth_details_mapping.keys():
                continue
            parsed_data[json_to_auth_details_mapping[key]] = value

        return cls(**parsed_data)
