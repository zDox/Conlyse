"""
Find game logic for the recorder.
This module handles finding and joining games based on different parameter combinations.
"""
from time import sleep, time
from typing import Optional, Set

from conflict_interface.data_types.hub_types.hub_game import HubGameProperties
from conflict_interface.utils.exceptions import GameActivationException, GameActivationErrorCodes
from conflict_interface.data_types.hub_types.hub_game_state_enum import HubGameState
from tools.recorder.account_pool import AccountPool
from tools.recorder.account import Account
from tools.recorder.recorder_logger import get_logger

logger = get_logger()


class GameFinder:
    """
    Handles finding and joining games based on different parameter combinations.
    """

    def __init__(
        self,
        config: dict,
        interface,
        account_pool: Optional[AccountPool] = None,
        current_account: Optional[Account] = None,
        join_game_callback=None,
        login_callback=None
    ):
        """
        Initialize the GameFinder.

        Args:
            config: Configuration dictionary
            interface: HubInterface instance for listing games
            account_pool: Optional AccountPool for multi-account support
            current_account: Current account being used
            join_game_callback: Callback function to join a game (game_id, country_name) -> bool
            login_callback: Callback function to login with an account (account) -> bool
        """
        self.config = config
        self.interface = interface
        self.account_pool = account_pool
        self.current_account = current_account
        self.join_game_callback = join_game_callback
        self.login_callback = login_callback

    def find_and_join_game(self) -> bool:
        """
        Find a game and join it based on the configuration.
        
        Logic:
        - If game_id specified and account: Join that game, if it doesn't work we're done
        - If game_id specified and account_pool: Not supported
        - If scenario_id and account_pool: Loop with max_time, try accounts and games
        - If scenario_id and account: Not supported

        Returns:
            bool: True if successfully joined a game, False otherwise
        """
        game_id = self.config.get('game_id')
        scenario_id = self.config.get('scenario_id')
        country_name = self.config.get('country_name')

        # Validate configuration
        if not game_id and not scenario_id:
            logger.error("Either game_id or scenario_id is required")
            return False

        # If game_id specified and account
        if game_id and not self.account_pool:
            return self._join_specific_game_with_account(game_id, country_name)

        # If game_id specified and account_pool
        if game_id and self.account_pool:
            logger.error("Joining specific game_id is not supported with account pool")
            return False

        # If scenario_id and account_pool
        if scenario_id and self.account_pool:
            return self._find_and_join_with_account_pool(scenario_id, country_name)

        # If scenario_id and account
        if scenario_id and not self.account_pool:
            logger.error("Joining by scenario_id is not supported without account pool")
            return False

        logger.error("Invalid configuration combination")
        return False

    def _join_specific_game_with_account(self, game_id: int, country_name: Optional[str]) -> bool:
        """
        Join a specific game by ID with a single account.
        If it doesn't work, we're done (no retries).
        
        Args:
            game_id: The game ID to join
            country_name: Optional country name to select
            
        Returns:
            bool: True if successfully joined, False otherwise
        """
        logger.info(f"Joining existing game: {game_id}")

        try:
            if self.join_game_callback:
                return self.join_game_callback(game_id, country_name)
            else:
                logger.error("Join game callback not configured")
                return False
        except Exception as e:
            logger.error(f"Failed to join game {game_id}: {e}")
            return False

    def _find_and_join_with_account_pool(self, scenario_id: int, country_name: Optional[str]) -> bool:
        """
        Find and join a game with scenario_id using account pool.
        Loop through accounts and games until max_time is reached or successfully joined.
        
        Logic:
        - While max_time not reached:
          - Take account
          - List all global games with scenario_id
          - If we have not tried to join that game:
            - Join it
            - If Join is successful: Done
            - If USER_NOT_FOUND: Continue with next account from account pool
            - If Country was taken: Mark game as already tried
        
        Args:
            scenario_id: The scenario ID to find games for
            country_name: Optional country name to select
            
        Returns:
            bool: True if successfully joined, False otherwise
        """
        if not self.account_pool:
            logger.error("Account pool not configured")
            return False

        max_wait = self.config.get('max_wait')
        poll_interval = self.config.get('poll_interval', 30)
        start_time = time()
        
        # Track games we've already tried to join
        tried_games: Set[int] = set()

        while True:
            # Check if max_time reached
            if max_wait is not None and (time() - start_time) >= max_wait:
                logger.error(f"Timed out waiting for available game for scenario {scenario_id}")
                return False

            # Take account from pool
            account = self.account_pool.next_free_account()
            if not account:
                logger.error("No more available accounts in pool")
                return False

            logger.info(f"Trying with account: {account.username}")

            # Login with this account if not already using it
            if self.current_account != account:
                if not self.login_callback or not self.login_callback(account):
                    logger.warning(f"Failed to login with account {account.username}, trying next account")
                    continue
                self.current_account = account

            # List all global games with scenario_id
            try:
                games: list[HubGameProperties] = self.interface.get_global_games(
                    scenario_id=scenario_id,
                    state=HubGameState.READY_TO_JOIN
                )
                my_games = self.interface.get_my_games()

                # Filter games we haven't joined yet and haven't tried
                available_games = [
                    game for game in games
                    if not any(my_game.game_id == game.game_id for my_game in my_games)
                       and game.game_id not in tried_games
                       and game.open_slots >= 10
                       and game.day_of_game <= 2
                ]

                if not available_games:
                    logger.info(f"No new games to try for scenario {scenario_id}, waiting {poll_interval}s")
                    sleep(poll_interval)
                    continue

                # Try each available game
                for game_info in available_games:
                    logger.info(f"Attempting to join game: {game_info.game_id}")

                    # If we have not tried to join that game

                    try:
                        # Join it
                        if self.join_game_callback and self.join_game_callback(game_info.game_id, country_name):
                            # If Join is successful: Done
                            logger.info(f"Successfully joined game {game_info.game_id}")
                            return True
                    except GameActivationException as e:
                        # If USER_NOT_FOUND: Continue with next account from account pool
                        if e.error_code == GameActivationErrorCodes.USER_NOT_FOUND:
                            logger.warning(
                                f"Account {account.username} got USER_NOT_FOUND error "
                                f"(too many recent joins), skipping to next account"
                            )
                            self.account_pool.skip_free_account()
                            break  # Break inner loop to get next account
                        else:
                            logger.error(f"Game activation failed with error {e.error_code}: {e}")
                            # If Country was taken: Mark game as already tried
                            tried_games.add(game_info.game_id)
                            continue
                    except Exception as e:
                        logger.warning(f"Failed to join game {game_info.game_id}: {e}")
                        # If Country was taken or other error: Mark game as already tried
                        tried_games.add(game_info.game_id)
                        continue

            except Exception as e:
                logger.error(f"Failed to list games: {e}")
                sleep(poll_interval)
                continue
