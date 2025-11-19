"""
Main recorder class for game recording.
"""
import os
from datetime import datetime
from time import sleep, time
from typing import Optional

from tools.recorder.storage import RecordingStorage
from tools.recorder.utils import parse_duration
from conflict_interface.data_types.hub_types.hub_game_state_enum import HubGameState
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.interface.online_interface import OnlineInterface
from conflict_interface.logger_config import get_logger

logger = get_logger()


class Recorder:
    """
    Main recorder class that handles game recording independently of replay system.
    """
    
    def __init__(self, config: dict):
        """
        Initialize recorder with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.interface: Optional[HubInterface] = None
        self.game: Optional[OnlineInterface] = None
        self.storage: Optional[RecordingStorage] = None
        
        # Track the last server response for recording
        self._last_response: Optional[dict] = None
    
    def _setup_storage(self):
        """Setup recording storage."""
        output_dir = self.config.get('output_dir', './recordings')
        recording_name = self.config.get('recording_name')
        
        if not recording_name:
            recording_name = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        output_path = os.path.join(output_dir, recording_name)
        self.storage = RecordingStorage(output_path)
        
        # Set up log file recording
        self.storage.setup_logging()
        
        logger.info(f"Recording storage initialized at: {output_path}")
    
    def _monkey_patch_game_api(self):
        """
        Monkey patch the game API to intercept server responses.
        This allows us to capture the raw JSON without affecting replay functionality.
        """
        original_request_method = self.game.game_api.request
        
        def patched_request(*args, **kwargs):
            response = original_request_method(*args, **kwargs)
            self._last_response = response
            return response
        
        self.game.game_api.request = patched_request
        logger.debug("Game API patched to capture responses")
    
    def login(self) -> bool:
        """
        Login to the game using credentials from config.
        
        Returns:
            bool: True if login successful, False otherwise
        """
        username = self.config.get('username')
        password = self.config.get('password')
        proxy_url = self.config.get('proxy_url')
        
        if not username or not password:
            logger.error("Username and password are required")
            return False
        
        try:
            self.interface = HubInterface()
            
            # Set proxy if provided
            if proxy_url:
                proxy = {'http': proxy_url, 'https': proxy_url}
                self.interface.set_proxy(proxy)
            
            self.interface.login(username, password)
            logger.info(f"Successfully logged in as {username}")
            return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def find_and_join_game(self) -> bool:
        """
        Find a game with the specified scenario_id and join it, or join a specific game_id.
        Tries multiple games until country selection succeeds.
        
        Returns:
            bool: True if successfully joined and selected country, False otherwise
        """
        game_id = self.config.get('game_id')
        scenario_id = self.config.get('scenario_id')
        country_name = self.config.get('country_name')
        
        # If game_id is provided, join that specific game directly
        if game_id:
            logger.info(f"Joining existing game: {game_id}")
            try:
                return self._join_game(game_id, country_name)
            except Exception as e:
                logger.error(f"Failed to join game {game_id}: {e}")
                return False
        
        # Otherwise, find and join a new game
        if not scenario_id:
            logger.error("Either game_id or scenario_id is required")
            return False
        
        try:
            # Find games with the scenario
            games = self.interface.get_global_games(
                scenario_id=scenario_id,
                state=HubGameState.READY_TO_JOIN
            )
            
            my_games = self.interface.get_my_games()
            
            # Filter games we haven't joined yet
            available_games = [game for game in games if game.game_id not in my_games]
            
            if not available_games:
                logger.error(f"No available games found for scenario {scenario_id}")
                return False
            
            # Try each game until we successfully select the desired country
            for game_info in available_games:
                logger.info(f"Attempting to join game: {game_info.game_id}")
                
                try:
                    if self._join_game(game_info.game_id, country_name):
                        return True
                except Exception as e:
                    logger.warning(f"Failed to join/select country in game {game_info.game_id}: {e}, trying next game")
                    continue
            
            # If we get here, we tried all games and none worked
            logger.error(f"Could not find a suitable game with available country '{country_name}'")
            return False
            
        except Exception as e:
            logger.error(f"Failed to find and join game: {e}")
            return False
    
    def _join_game(self, game_id: int, country_name: Optional[str]) -> bool:
        """
        Join a specific game and optionally select a country.
        
        Args:
            game_id: The game ID to join
            country_name: Optional country name to select
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Join the game (without replay functionality)
        self.game = self.interface.join_game(game_id, replay_filename=None)
        
        # Patch the game API to capture responses
        self._monkey_patch_game_api()
        
        # Try to select country if specified
        if country_name:
            if not self.game.is_country_selected():
                playable_countries = self.game.get_playable_countries()
                
                # Find country by name
                selected_country = None
                for country_id, country in playable_countries.items():
                    if country.name.lower() == country_name.lower():
                        selected_country = country
                        break
                
                if not selected_country:
                    logger.error(f"Country '{country_name}' not available in game {game_id}")
                    return False
                
                self.game.select_country(country_id=selected_country.player_id)
                logger.info(f"Selected country: {selected_country.name} in game {game_id}")
                
                # Update to apply country selection
                self._update_and_save()
            else:
                logger.info(f"Country already selected in game {game_id}")
        
        # Successfully joined
        logger.info(f"Successfully joined game {game_id}")
        return True
    
    def _save_current_state(self):
        """Save the current game state and last response."""
        if self.game and self.storage and self._last_response:
            timestamp = time()
            self.storage.save_update(
                self.game.game_state,
                self._last_response,
                timestamp
            )
    
    def _update_and_save(self):
        """Update game state and save it. This ensures state is always saved after update."""
        self.game.update()
        self._save_current_state()
    
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
        
        city = next(iter(self.game.get_my_provinces(name=city_name).values()), None)
        if not city:
            logger.error(f"City '{city_name}' not found")
            return False
        
        upgrade_type = self.game.get_upgrade_type_by_name_and_tier(building_name, tier)
        if not upgrade_type:
            logger.error(f"Upgrade type '{building_name}' tier {tier} not found")
            return False
        
        possible_upgrade = city.get_possible_upgrade(id=upgrade_type.id)
        if city.is_upgrade_buildable(possible_upgrade):
            city.build_upgrade(possible_upgrade)
            self._update_and_save()
            return True
        else:
            logger.error(f"Cannot build {building_name} in {city_name}")
            return False
    
    def _cancel_upgrade(self, action: dict) -> bool:
        """Cancel construction in a city."""
        city_name = action.get('city_name')
        
        logger.info(f"Canceling construction in {city_name}")
        
        city = next(iter(self.game.get_my_provinces(name=city_name).values()), None)
        if not city:
            logger.error(f"City '{city_name}' not found")
            return False
        
        city.cancel_construction()
        self._update_and_save()
        return True
    
    def _mobilize_unit(self, action: dict) -> bool:
        """Mobilize a unit in a city."""
        city_name = action.get('city_name')
        unit_name = action.get('unit_name')
        tier = action.get('tier', 1)
        
        logger.info(f"Mobilizing {unit_name} (tier {tier}) in {city_name}")
        
        city = next(iter(self.game.get_my_provinces(name=city_name).values()), None)
        if not city:
            logger.error(f"City '{city_name}' not found")
            return False
        
        unit_type = self.game.get_unit_type_by_name_and_tier(unit_name, tier)
        if not unit_type:
            logger.error(f"Unit type '{unit_name}' tier {tier} not found")
            return False
        
        city.mobilize_unit_by_id(unit_type.id)
        self._update_and_save()
        return True
    
    def _cancel_mobilization(self, action: dict) -> bool:
        """Cancel mobilization in a city."""
        city_name = action.get('city_name')
        
        logger.info(f"Canceling mobilization in {city_name}")
        
        city = next(iter(self.game.get_my_provinces(name=city_name).values()), None)
        if not city:
            logger.error(f"City '{city_name}' not found")
            return False
        
        city.cancel_mobilization()
        self._update_and_save()
        return True
    
    def _research(self, action: dict) -> bool:
        """Start research."""
        research_name = action.get('research_name')
        tier = action.get('tier', 1)
        
        logger.info(f"Researching {research_name} (tier {tier})")
        
        research_type = self.game.get_research_type_by_name_and_tier(research_name, tier)
        if not research_type:
            logger.error(f"Research type '{research_name}' tier {tier} not found")
            return False
        
        research_type.research()
        self._update_and_save()
        return True
    
    def _cancel_research(self, action: dict) -> bool:
        """Cancel research."""
        logger.info(f"Canceling research")
        
        # Get current research state
        if self.game.game_state and self.game.game_state.states.research_state:
            research_state = self.game.game_state.states.research_state
            if research_state.current_research:
                research_id = research_state.current_research.research_type_id
                research_state.cancel_research(research_id)
                self._update_and_save()
                return True
        
        logger.warning("No active research to cancel")
        return False
    
    def _sleep(self, action: dict) -> bool:
        """Sleep without updates."""
        duration_input = action.get('duration', 0)
        duration_seconds = parse_duration(duration_input)
        
        logger.info(f"Sleeping for {duration_seconds} seconds without updates")
        sleep(duration_seconds)
        return True
    
    def _sleep_with_updates(self, action: dict) -> bool:
        """Sleep with periodic updates."""
        duration_input = action.get('duration', 0)
        duration_seconds = parse_duration(duration_input)
        update_interval = action.get('update_interval', 10)
        
        logger.info(f"Sleeping for {duration_seconds} seconds with updates every {update_interval} seconds")
        
        elapsed = 0
        while elapsed < duration_seconds:
            wait_time = min(update_interval, duration_seconds - elapsed)
            sleep(wait_time)
            elapsed += wait_time
            
            if elapsed < duration_seconds:
                self._update_and_save()
        
        return True
    
    def _get_army(self, action: dict):
        """Helper to get army from ID or number."""
        army_id = action.get('army_id')
        army_number = action.get('army_number')
        
        if army_id:
            return self.game.get_army(army_id)
        elif army_number:
            return self.game.get_my_army_by_number(army_number)
        else:
            logger.error("Either army_id or army_number must be specified")
            return None
    
    def _army_patrol(self, action: dict) -> bool:
        """Army patrol over province center."""
        province_name = action.get('province_name')
        
        army = self._get_army(action)
        if not army:
            return False
        
        province = self.game.get_provinces_by_name(province_name)
        if not province:
            logger.error(f"Province '{province_name}' not found")
            return False
        
        target = province.static_data.center_coordinate
        logger.info(f"Army {army.army_number} patrolling to {province_name}")
        
        army.patrol(target)
        self._update_and_save()
        return True
    
    def _army_move(self, action: dict) -> bool:
        """Army move to province center."""
        province_name = action.get('province_name')
        
        army = self._get_army(action)
        if not army:
            return False
        
        province = self.game.get_provinces_by_name(province_name)
        if not province:
            logger.error(f"Province '{province_name}' not found")
            return False
        
        target = province.static_data.center_coordinate
        logger.info(f"Army {army.army_number} moving to {province_name}")
        
        army.set_waypoint(target)
        self._update_and_save()
        return True
    
    def _army_attack(self, action: dict) -> bool:
        """Army attack province center."""
        province_name = action.get('province_name')
        
        army = self._get_army(action)
        if not army:
            return False
        
        province = self.game.get_provinces_by_name(province_name)
        if not province:
            logger.error(f"Province '{province_name}' not found")
            return False
        
        target = province.static_data.center_coordinate
        logger.info(f"Army {army.army_number} attacking {province_name}")
        
        army.attack_point(target)
        self._update_and_save()
        return True
    
    def _army_cancel_commands(self, action: dict) -> bool:
        """Cancel army commands."""
        army = self._get_army(action)
        if not army:
            return False
        
        logger.info(f"Canceling commands for army {army.army_number}")
        
        army.cancel_commands()
        self._update_and_save()
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
            
            # Login
            if not self.login():
                return False
            
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
