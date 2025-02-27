from copy import deepcopy
from functools import wraps
from typing import cast

from conflict_interface.data_types import HubGame, parse_any
from conflict_interface.data_types.hub_types.hub_game import HubGameProperties
from conflict_interface.game_interface import GameInterface
from conflict_interface.hub_api import HubApi
from conflict_interface.utils.exceptions import AuthenticationException


# Decorator to check if the user is authenticated
def protected(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.auth:
            raise AuthenticationException("Client is not authenticated. Please login first.")
        return func(self, *args, **kwargs)

    return wrapper



class HubInterface:
    def __init__(self):
        self.api: HubApi = HubApi()
        self.auth = False

    def login(self, username: str, password: str):
        """
        Logs in a user to the system using the provided username and password.

        This method communicates with the backend API to authenticate the user
        credentials. If the login fails, an exception is raised with an appropriate
        error message indicating invalid credentials.

        Parameters
        ----------
        username : The username of the user attempting to log in.
        password : The password associated with the username for authentication.

        Raises
        ------
        AuthenticationException
            Raised when the login attempt fails, indicating that the username or
            password provided is incorrect.

        """
        if self.auth:
            raise AuthenticationException("Client is already authenticated. Please logout first.")

        result = self.api.login(username, password)
        if not result:
            raise AuthenticationException("Login for user " + username + " failed. Check username and password.")
        else:
            self.auth = True

    @protected
    def logout(self):
        self.api.logout()
        self.auth = False

    def register(self, username, email, password):
        """
        Registers a new user with the specified username, email, and password.

        This method interacts with the API to register a user in the system.
        The user must provide a unique username, a valid email address, and
        a secure password.

        Parameters:
            username: The desired username for the new user.
            email: The email address associated with the user.
            password: The password to secure the user account.

        Raises:
            AuthenticationException: If the registration fails, indicating that the username or email is already taken.
        """
        if self.auth:
            raise AuthenticationException("Client is already authenticated. Please logout first.")

        result = self.api.register_user(username, email, password)
        if not result:
            raise Exception(f"Registration failed. Check {username} or {email} is already taken.")

    @protected
    def get_my_games(self, archived: bool = False, **filters) -> list[HubGameProperties]:
        """
        Retrieve the games associated with the current user, with optional filters and
        archived status.
    
        Args:
            archived: If set to True, retrieves only archived games. Defaults to False.
            filters: Key-value pairs representing the attributes and their expected values
                to filter games.
    
        Returns:
            A list of HubGameProperties, each representing the properties of games that
            match the filtering criteria and archived state.
        """
        data = cast(list[HubGame], parse_any(list[HubGame], self.api.get_my_games(archived)))
        return [
            game.properties for game in data
            if all(getattr(game.properties, key) == value for key, value in filters.items())
        ]

    @protected
    def get_global_games(self, **filters) -> list[HubGameProperties]:
        """
        Retrieve a list of global games filtered by specified criteria. The function
        retrieves data from an external API, parses it into a list of `HubGame` objects,
        and applies the provided filters to extract games that match the given
        conditions.
    
        Arguments:
            filters: Arbitrary keyword arguments specifying the filter criteria
                     for the games. Each key corresponds to a property in
                     `HubGameProperties` and must match exactly for the game to
                     be included.
    
        Returns:
            list[HubGameProperties]: A list of properties for global games that
                                     satisfy the provided filters.
        """
        data = cast(list[HubGame], parse_any(list[HubGame], self.api.get_global_games()))
        return [
            game.properties for game in data
            if all(getattr(game.properties, key) == value for key, value in filters.items())
        ]

    def first_join(self, game_id: int):
        self.api.request_first_join(game_id)

    @protected
    def join_game(self, game_id: int, guest=False) -> GameInterface:
        # If user is not already in first game join it the first time
        if not self.is_in_game(game_id) and not guest:
            self.api.request_first_join(game_id)

        game_interface = GameInterface(game_id)
        game_interface.init_api(deepcopy(self.api.session), deepcopy(self.api.auth))
        game_interface.join_game(guest)
        return game_interface

    def is_in_game(self, game_id: int) -> bool:
        return any(game.game_id == game_id for game in self.get_my_games())
