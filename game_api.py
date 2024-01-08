from authentification import AuthDetails
from requests import Session


class GameAPI:
    def __init__(self, cookies: dict, headers: dict, auth_details: AuthDetails,
                 game_id: int):
        self.session = Session()
        self.game_id = game_id

        # Set cookies from previous ConflictInterface Session
        for key, value in cookies.items():
            self.session.cookie.set(key, value)

        # Set headers from previous ConflictInterface Session
        self.session.headers = headers

