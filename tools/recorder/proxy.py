from dataclasses import dataclass

from requests import Session

WEBSHARE_URL = "https://proxy.webshare.io/api/v2/"


@dataclass
class Proxy:
    id: str
    username: str
    password: str
    address: str
    port: int
    valid: bool
    country_code: str

    @property
    def proxy_url(self) -> str:
        return f"socks5://{self.username}:{self.password}@{self.address}:{self.port}"

    @classmethod
    def from_json(cls, obj) -> 'Proxy':
        return cls(
            id=obj["id"],
            username=obj["username"],
            password=obj["password"],
            address=obj["proxy_address"],
            port=obj["port"],
            valid=obj["valid"],
            country_code=obj["country_code"]
        )

def get_proxies(token: str) -> dict[str, Proxy]:
    if token is None:
        raise Exception("Web share token not set")
    session = Session()
    session.headers.update({"Authorization": f"Token {token}"})
    proxies = {}

    last_page = False
    page = 1
    while not last_page:
        response = session.get(
            WEBSHARE_URL + f"proxy/list/?mode=direct&page={page}&page_size=25",
        )
        response_json = response.json()
        last_page = response_json["next"] is None
        page += 1
        for json_proxy in response_json["results"]:
            proxy = Proxy.from_json(json_proxy)
            proxies[proxy.id] = proxy
    return proxies