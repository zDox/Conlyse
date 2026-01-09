from conflict_interface.data_types.hub_types.hub_game import HubGameProperties
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.interface.online_interface import OnlineInterface
from tools.server_observer.proxy import Proxy

MAXIMUM_NUMBER_OF_GAMES = 10

def ensure_games_loaded(func):
    def wrapper(self, *args, **kwargs):
        if self.games is None:
            self.get_my_games()
        return func(self, *args, **kwargs)

    return wrapper

class Account:
    username: str
    password: str
    email: str
    proxy_id: str
    proxy_url: str
    hub_itf: HubInterface = None
    games: list[HubGameProperties] = None

    def __repr__(self):
        return f"Account(username={self.username}, proxy_id={self.proxy_id})"

    def to_dict(self):
        return {
            "username": self.username,
            "password": self.password,
            "email": self.email,
            "proxy_id": self.proxy_id,
            "proxy_url": self.proxy_url
        }

    @classmethod
    def from_dict(cls, obj):
        return cls(
            username=obj["username"],
            password=obj["password"],
            email=obj["email"],
            proxy_id=obj["proxy_id"],
            proxy_url=obj["proxy_url"]
        )

    def __init__(self, username, password, email, proxy_id, proxy_url):
        self.username = username
        self.password = password
        self.email = email
        self.proxy_id = proxy_id
        self.proxy_url = proxy_url
        self.hub_itf = HubInterface({
            "http": proxy_url,
            "https": proxy_url,
        })

    def login(self) -> bool:
        if not self.hub_itf.auth:
            return self.hub_itf.login(self.username, self.password)
        return True

    def get_interface(self) -> HubInterface:
        if not self.hub_itf.auth:
            self.hub_itf.login(self.username, self.password)
        return self.hub_itf

    def reset_interface(self):
        self.hub_itf = HubInterface({
            "http": self.proxy_url,
            "https": self.proxy_url,
        })
        self.games = None
        self.hub_itf.login(self.username, self.password)


    def set_proxy(self, proxy: Proxy):
        self.proxy_id = proxy.id
        self.proxy_url = proxy.proxy_url

        self.hub_itf.set_proxy({
            "http": self.proxy_url,
            "https": self.proxy_url,
        })

    @ensure_games_loaded
    def has_maximum_games(self) -> bool:
        """
        Returns True if the account has the maximum number of games assigned to it.
        Hence, it cannot join new games until some old games are finished.
    
        :return: If the account has the maximum number of games assigned to it.
        """
        return len(self.games) >= MAXIMUM_NUMBER_OF_GAMES

    @ensure_games_loaded
    def open_game_slots(self) -> int:
        return MAXIMUM_NUMBER_OF_GAMES - len(self.games)

    def get_my_games(self) -> list[HubGameProperties]:
        if self.games is None:
            if not self.hub_itf.auth:
                self.login()
            self.games = self.hub_itf.get_my_games()
        return self.games

    def has_game(self, game_id: int) -> bool:
        return any([game_id == my_game.game_id for my_game in self.get_my_games()])


    @ensure_games_loaded
    def join_game(self, game_id: int, guest: bool = False, replay_filename: str = None) -> OnlineInterface:
        game_itf = self.hub_itf.join_game(game_id, guest, replay_filename)
        self.games = self.hub_itf.get_my_games()
        return game_itf
