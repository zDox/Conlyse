"""
Main recorder class for game recording.
"""
import os
from copy import deepcopy
from datetime import datetime
from time import time
from time import sleep
from typing import Optional

from conflict_interface.data_types.map_state.province_action_result import UpdateProvinceActionResult
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.interface.online_interface import OnlineInterface
from conflict_interface.utils.helper import datetime_to_unix_ms
from tools.recorder.account import Account
from tools.recorder.account_pool import AccountPool
from tools.recorder.find_game_logic import GameFinder
from tools.recorder.recorder_logger import get_logger
from tools.recorder.storage import RecordingStorage
from tools.recorder.utils import format_duration
from tools.recorder.utils import parse_duration

logger = get_logger()


class Recorder:
    """
    Main recorder class that handles game recording independently of replay system.
    """
    
    def __init__(self, config: dict, account_pool: Optional[AccountPool] = None, save_game_states: bool = False):
        """
        Initialize recorder with configuration.
        
        Args:
            config: Configuration dictionary
            account_pool: Optional AccountPool for multi-account support
        """
        self.config = config
        self.hub_itf: Optional[HubInterface] = None
        self.game_itf: Optional[OnlineInterface] = None
        self.storage: Optional[RecordingStorage] = None
        self.account_pool: Optional[AccountPool] = account_pool
        self.current_account: Optional[Account] = None
        self.save_game_states: bool = save_game_states
        
        # Track the last server request and response for recording
        self._last_request: Optional[dict] = None
        self._last_response: Optional[dict] = None
    
    def _setup_storage(self):
        """Setup recording storage."""
        output_dir = self.config.get('output_dir', './recordings')
        recording_name = self.config.get('recording_name')
        
        if not recording_name:
            recording_name = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        output_path = os.path.join(output_dir, recording_name)
        self.storage = RecordingStorage(output_path, self.save_game_states)
        
        # Set up log file recording
        self.storage.setup_logging()
        
        logger.info(f"Recording storage initialized at: {output_path}")

    def login(self, account: Optional[Account] = None) -> bool:
        """
        Login to the game using credentials from config or account.

        Args:
            account: Optional Account object to use for login (for account pool mode)

        Returns:
            bool: True if login successful, False otherwise
        """
        if account:
            return self._login_with_account(account)
        else:
            return self._login_with_config()

    def _login_with_account(self, account: Account) -> bool:
        """Login using an Account object from the account pool."""
        try:
            self.hub_itf = account.get_interface()
            self.current_account = account
            logger.info(f"Successfully logged in with account: {account.username}")
            return True
        except Exception as e:
            logger.error(f"Login failed with account {account.username}: {e}")
            return False

    def _login_with_config(self) -> bool:
        """Login using credentials from the configuration."""
        username = self.config.get('username')
        password = self.config.get('password')
        proxy_url = self.config.get('proxy_url')

        if not username or not password:
            logger.error("Username and password are required")
            return False

        try:
            self.hub_itf = HubInterface()

            if proxy_url:
                proxy = {'http': proxy_url, 'https': proxy_url}
                self.hub_itf.set_proxy(proxy)

            self.hub_itf.login(username, password)
            logger.info(f"Successfully logged in as {username}")
            return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def find_and_join_game(self) -> bool:
        """
        Find a game and join it using the GameFinder logic.

        Returns:
            bool: True if successfully joined and selected country, False otherwise
        """
        game_finder = GameFinder(
            config=self.config,
            interface=self.hub_itf,
            account_pool=self.account_pool,
            current_account=self.current_account,
            join_game_callback=self._join_game,
            login_callback=self.login
        )
        
        result = game_finder.find_and_join_game()
        
        # Update current_account if it changed during the process
        if game_finder.current_account:
            self.current_account = game_finder.current_account
            
        return result

    def _join_game(self, game_id: int, country_name: Optional[str]) -> bool:
        """
        Join a specific game and optionally select a country.

        This method patches the game API to capture all server responses.

        Args:
            game_id: The game ID to join
            country_name: Optional country name to select

        Returns:
            bool: True if successful, False otherwise
        """
        # Patch and join the game
        self.hub_itf.join_game = self._create_patched_join_game()
        self.game_itf = self.hub_itf.join_game(game_id, replay_filename=None)

        # Save initial game state and static map data
        self._save_static_map_data(self.game_itf.static_map_data)

        # Select country if specified
        if country_name:
            if not self._select_country(country_name, game_id):
                return False

        logger.info(f"Successfully joined game {game_id}")
        return True

    def _create_patched_join_game(self):
        """Create a patched version of join_game that captures API responses."""

        def patched_join_game(game_id: int, guest=False, replay_filename: str = None):
            # Request first join if needed
            if not self.hub_itf.is_in_game(game_id) and not guest:
                logger.info(f"User is not in game {game_id}. Requesting first join...")
                self.hub_itf.api.request_first_join(game_id)

            logger.info(f"Joining game {game_id} as guest={guest}...")

            # Create the game interface
            game_interface = OnlineInterface(
                game_id=game_id,
                session=self.hub_itf.api.session,
                auth_details=deepcopy(self.hub_itf.api.auth),
                proxy=self.hub_itf.api.proxy,
                guest=guest,
                replay_filename=replay_filename
            )

            # Patch the game API to capture responses
            original_request_method = game_interface.game_api.make_game_server_request

            def patched_request(*args, **kwargs):

                self.storage.save_game_state(time(),
                                             game_interface.game_state)
                # Capture the request parameters
                if args:
                    original_request = args[0]  # parameters is the first argument
                else:
                    original_request = kwargs.get('parameters', {})
                self._last_request = {**original_request, "game_api_request_id": game_interface.game_api.request_id}

                response = original_request_method(*args, **kwargs)
                self._last_response = {**response, "game_api_request_id": game_interface.game_api.request_id}
                self.storage.save_request_response(time(), self._last_request, self._last_response)
                return response

            game_interface.game_api.make_game_server_request = patched_request
            logger.debug("Game API patched to capture requests and responses")

            # Load the game
            game_interface.load_game()
            return game_interface

        return patched_join_game

    def _save_static_map_data(self, static_map_data):
        """Save static map data after joining."""
        if not static_map_data:
            return
        self.storage.save_static_map_data(static_map_data)

    def _select_country(self, country_name: str, game_id: int) -> bool:
        """Select a country in the game."""
        if self.game_itf.is_country_selected():
            logger.info(f"Country already selected in game {game_id}")
            return True

        playable_countries = self.game_itf.get_playable_countries()

        # Find country by name
        selected_country = None
        for country_id, country in playable_countries.items():
            if country.nation_name.lower() == country_name.lower():
                selected_country = country
                break

        if not selected_country:
            logger.error(f"Country '{country_name}' not available in game {game_id}")
            return False

        self.game_itf.select_country(country_id=selected_country.player_id)
        logger.info(f"Selected country: {selected_country.nation_name} in game {game_id}")

        return True
    
    def execute_action(self, action: dict) -> bool:
        """
        Execute a single action based on configuration.
        
        Args:
            action: Action configuration dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        action_type = action.get('type')
        
        if not action_type:
            logger.error("Action type not specified")
            return False
        
        try:
            if action_type == 'build_upgrade':
                return self._build_upgrade(action)
            elif action_type == 'cancel_upgrade':
                return self._cancel_upgrade(action)
            elif action_type == 'mobilize_unit':
                return self._mobilize_unit(action)
            elif action_type == 'cancel_mobilization':
                return self._cancel_mobilization(action)
            elif action_type == 'research':
                return self._research(action)
            elif action_type == 'cancel_research':
                return self._cancel_research(action)
            elif action_type == 'sleep':
                return self._sleep(action)
            elif action_type == 'sleep_with_updates':
                return self._sleep_with_updates(action)
            elif action_type == 'army_patrol':
                return self._army_patrol(action)
            elif action_type == 'army_move':
                return self._army_move(action)
            elif action_type == 'army_attack':
                return self._army_attack(action)
            elif action_type == 'army_cancel_commands':
                return self._army_cancel_commands(action)
            else:
                logger.error(f"Unknown action type: {action_type}")
                return False
        except Exception as e:
            logger.error(f"Error executing action {action_type}: {e}")
            return False
    
    def _build_upgrade(self, action: dict) -> bool:
        """Build an upgrade in a city."""
        city_name = action.get('city_name')
        building_name = action.get('building_name')
        tier = action.get('tier', 1)
        
        logger.info(f"Building {building_name} (tier {tier}) in {city_name}")
        
        city = next(iter(self.game_itf.get_my_provinces(name=city_name).values()), None)
        if not city:
            logger.error(f"City '{city_name}' not found")
            return False
        
        upgrade_type = self.game_itf.get_upgrade_type_by_name_and_tier(building_name, tier)
        if not upgrade_type:
            logger.error(f"Upgrade type '{building_name}' tier {tier} not found")
            return False
        
        possible_upgrade = city.get_possible_upgrade(id=upgrade_type.id)
        if city.is_upgrade_buildable(possible_upgrade):
            city.build_upgrade(possible_upgrade)
            self.game_itf.update()
            return True
        else:
            logger.error(f"Cannot build {building_name} in {city_name}")
            return False
    
    def _cancel_upgrade(self, action: dict) -> bool:
        """Cancel construction in a city."""
        city_name = action.get('city_name')
        
        logger.info(f"Canceling construction in {city_name}")
        
        city = next(iter(self.game_itf.get_my_provinces(name=city_name).values()), None)
        if not city:
            logger.error(f"City '{city_name}' not found")
            return False
        
        city.cancel_construction()
        self.game_itf.update()
        return True
    
    def _mobilize_unit(self, action: dict) -> bool:
        """Mobilize a unit in a city."""
        city_name = action.get('city_name')
        unit_name = action.get('unit_name')
        tier = action.get('tier', 1)
        
        logger.info(f"Mobilizing {unit_name} (tier {tier}) in {city_name}")
        
        city = next(iter(self.game_itf.get_my_provinces(name=city_name).values()), None)
        if not city:
            logger.error(f"City '{city_name}' not found")
            return False
        
        unit_type = self.game_itf.get_unit_type_by_name_and_tier(unit_name, tier)
        if not unit_type:
            logger.error(f"Unit type '{unit_name}' tier {tier} not found")
            return False
        
        _, action_result = city.mobilize_unit_by_id(unit_type.id)
        if action_result != UpdateProvinceActionResult.Ok:
            logger.error(f"Could not mobilize unit {unit_name} (tier {tier}) in {city_name} reason: {action_result}")
        self.game_itf.update()
        return True
    
    def _cancel_mobilization(self, action: dict) -> bool:
        """Cancel mobilization in a city."""
        city_name = action.get('city_name')
        
        logger.info(f"Canceling mobilization in {city_name}")
        
        city = next(iter(self.game_itf.get_my_provinces(name=city_name).values()), None)
        if not city:
            logger.error(f"City '{city_name}' not found")
            return False
        
        city.cancel_mobilization()
        self.game_itf.update()
        return True
    
    def _research(self, action: dict) -> bool:
        """Start research."""
        research_name = action.get('research_name')
        tier = action.get('tier', 1)
        
        logger.info(f"Researching {research_name} (tier {tier})")
        
        research_type = self.game_itf.get_research_type_by_name_and_tier(research_name, tier)
        if not research_type:
            logger.error(f"Research type '{research_name}' tier {tier} not found")
            return False
        
        research_type.research()
        self.game_itf.update()
        return True
    
    def _cancel_research(self, action: dict) -> bool:
        """Cancel research."""
        research_name = action.get('research_name')
        tier = action.get('tier')
        logger.info(f"Canceling research {research_name} (tier {tier})")
        
        # Get current research state
        if self.game_itf.game_state and self.game_itf.game_state.states.research_state:
            research_state = self.game_itf.game_state.states.research_state
            research_id = self.game_itf.get_research_type_by_name_and_tier(research_name, tier)
            research_state.cancel_research(research_id)
            self.game_itf.update()
            return True
        
        logger.warning("No active research to cancel")
        return False
    
    def _sleep(self, action: dict) -> bool:
        """Sleep without updates."""
        duration_input = action.get('duration', 0)
        duration_seconds = parse_duration(duration_input)
        
        logger.info(f"Sleeping for {format_duration(duration_seconds)} without updates")
        sleep(duration_seconds)
        return True
    
    def _sleep_with_updates(self, action: dict) -> bool:
        """Sleep with periodic updates."""
        duration_input = action.get('duration', 0)
        duration_seconds = parse_duration(duration_input)
        update_interval = action.get('update_interval', 10.0)
        
        logger.info(f"Sleeping for {format_duration(duration_seconds)} with updates every {format_duration(update_interval)}")

        start_time = time()
        elapsed = 0.0

        while elapsed < duration_seconds:
            # Determine next sleep chunk
            wait_time = min(update_interval, duration_seconds - elapsed)
            sleep(wait_time)
            elapsed = time() - start_time

            # Only update if we're not done
            if elapsed < duration_seconds:
                self.game_itf.update()

            # Print progress
            progress = min(100.0, 100.0 * elapsed / duration_seconds)
            print(f"Sleeping with updates: {progress:.1f}% ({format_duration(elapsed)} / {format_duration(duration_seconds)})")
        
        return True
    
    def _get_army(self, action: dict):
        """Helper to get army from ID or number."""
        army_id = action.get('army_id')
        army_number = action.get('army_number')
        
        if army_id:
            return self.game_itf.get_army(army_id)
        elif army_number:
            return self.game_itf.get_my_army_by_number(army_number)
        else:
            logger.error("Either army_id or army_number must be specified")
            return None
    
    def _army_patrol(self, action: dict) -> bool:
        """Army patrol over province center."""
        province_name = action.get('province_name')
        
        army = self._get_army(action)
        if not army:
            return False
        
        province = self.game_itf.get_provinces_by_name(province_name)
        if not province:
            logger.error(f"Province '{province_name}' not found")
            return False
        
        target = province.static_data.center_coordinate
        logger.info(f"Army {army.army_number} patrolling to {province_name}")
        
        army.patrol(target)
        self.game_itf.update()
        return True
    
    def _army_move(self, action: dict) -> bool:
        """Army move to province center."""
        province_name = action.get('province_name')
        
        army = self._get_army(action)
        if not army:
            return False
        
        province = self.game_itf.get_provinces_by_name(province_name)
        if not province:
            logger.error(f"Province '{province_name}' not found")
            return False
        
        target = province.static_data.center_coordinate
        logger.info(f"Army {army.army_number} moving to {province_name}")
        
        army.set_waypoint(target)
        self.game_itf.update()
        return True
    
    def _army_attack(self, action: dict) -> bool:
        """Army attack province center."""
        province_name = action.get('province_name')
        
        army = self._get_army(action)
        if not army:
            return False
        
        province = self.game_itf.get_provinces_by_name(province_name)
        if not province:
            logger.error(f"Province '{province_name}' not found")
            return False
        
        target = province.static_data.center_coordinate
        logger.info(f"Army {army.army_number} attacking {province_name}")
        
        army.attack_point(target)
        self.game_itf.update()
        return True
    
    def _army_cancel_commands(self, action: dict) -> bool:
        """Cancel army commands."""
        army = self._get_army(action)
        if not army:
            return False
        
        logger.info(f"Canceling commands for army {army.army_number}")
        
        army.cancel_commands()
        self.game_itf.update()
        return True
    
    def run(self) -> bool:
        """
        Run the recorder with the configured actions.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Setup storage
            self._setup_storage()
            
            # Login (if not using account pool, login with config credentials)
            # If using account pool, login happens during join attempt
            if not self.account_pool:
                if not self.login():
                    return False
            else:
                # Get a main account from the pool for listing all games
                account = self.account_pool.next_free_account()
                if not account:
                    logger.error("No accounts available in pool")
                    return False
                self.hub_itf = account.get_interface()
            # Find and join game
            if not self.find_and_join_game():
                return False
            
            # Execute actions
            actions = self.config.get('actions', [])
            logger.info(f"Executing {len(actions)} actions")
            
            for i, action in enumerate(actions):
                logger.info(f"Executing action {i+1}/{len(actions)}: {action.get('type')}")
                if not self.execute_action(action):
                    logger.warning(f"Action {i+1} failed, continuing...")
            
            logger.info("Recording completed successfully")
            return True
        finally:
            # Always teardown logging, even if there was an error
            if self.storage:
                self.storage.teardown_logging()
            return False
