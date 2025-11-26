import math
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Optional
from typing import Tuple

from conflict_interface.data_types.army_state.army_action import ArmyAction
from conflict_interface.data_types.army_state.army_action_result import ArmyActionResult
from conflict_interface.data_types.army_state.army_enums import Aggressiveness
from conflict_interface.data_types.army_state.army_enums import FightStatus
from conflict_interface.data_types.army_state.army_enums import ForcedMarch
from conflict_interface.data_types.army_state.commands import AttackCommand
from conflict_interface.data_types.army_state.commands import Command
from conflict_interface.data_types.army_state.commands import GotoCommand
from conflict_interface.data_types.army_state.commands import PatrolCommand
from conflict_interface.data_types.army_state.commands import PatrolType
from conflict_interface.data_types.army_state.commands import SplitArmyCommand
from conflict_interface.data_types.army_state.commands import WaitCommand
from conflict_interface.data_types.army_state.unit import Unit
from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.custom_types import LinkedList
from conflict_interface.data_types.custom_types import UnitList
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.map_state.map_state_enums import TerrainType
from conflict_interface.data_types.map_state.map_state_enums import TerrainTypeStr
from conflict_interface.data_types.mod_state.air_parameters import AirParameters
from conflict_interface.data_types.mod_state.anti_air_parameters import AntiAirParameters
from conflict_interface.data_types.mod_state.configuration import CarrierFeature
from conflict_interface.data_types.mod_state.configuration import MissileCarrierFeature
from conflict_interface.data_types.mod_state.configuration import RadarSignatureFeature
from conflict_interface.data_types.mod_state.configuration import TokenFeature
from conflict_interface.data_types.mod_state.mod_state_enums import UnitFeature
from conflict_interface.data_types.point import Point
from conflict_interface.logger_config import get_logger

logger = get_logger()

@dataclass
class Battle(GameObject):
    C = "ultshared.warfare.UltBattle"
    attacker_ids: list[int]

    MAPPING = {
        "attacker_ids": "a"
    }

DEFAULT_ARMY_ANGLE = 2.199114857512855


@dataclass
class Army(GameObject):
    """
    Represents an army.

    ATTRIBUTES:
        id: Identifier for the army.
        size: Number of units in the army.
        health: Health of the army in percent of the maximum.
        kills: How many units were killed by the army
        owner_id: Identifier for the owner of the army. Contains a player_id
        army_number:
        location_id: The identifier for the province the army is located in.
        position: Position of the army.
        last_direction: Direction of where the army is heading.
        on_sea: If the army is on sea.
        at_airfield: If the army is on airfield.
        units: LinkedList of the units that the army is made of.
        commands: LinkedList of the commands that the army has to follow.
        fight_status: Status of the army.
        battle: The battle that the army is currently in.
        attack_unit_id: The unit_id of the attacker.
        attack_position: The position of the attacker.
        next_attack_time: The time when the army will perform the next attack.
        estimated_arrival_time: The estimated arrival time of the army.
        needs_rail: If the army needs rail.
        needs_water: If the army needs water e.g if it is a ship.
        has_stealth: If the army is stealth.
        airplane: If the army is an airplane.
        pre_fight_size: The size of the before the fight.
        pre_fight_type: The type of before the fight.
        range: The range from which it can attack other armies.
        base_speed: The base speed of the army.
        spy_reveal_time: The time when the spy revealed the army.
        view_width: How far away the unit can view other armies.
        detailed_view_width: How far away the unit can view other armies.
        aggressiveness: The aggressiveness of the army.
        forced_march: If the army is in forced march or premium forced march.
        removed: If the army should be removed from the game state.
                removed is true if the game server thinks the client
                should not display the army anymore.
        terrain_type: The terrain type of the province that the army is in.
        air_parameters: The air parameters the army.
        anti_air_parameters: The anti air parameters the army.
        carriable: If the army can be stationed on an Aircraft/Helicopter carrier.
        carrier_feature: Further information about the Aircraft/Helicopter carrier.
        last_location_ids: Unknown
        end_of_unit_walk: Unknown
        hit_points: Number of hit points the army has.
        max_hit_points: Maximum number of hit_points the army has.
        missile_carrier_feature: Which types of missiles and how many missiles the army has loaded.
        entrenched: If the army is entrenched.
        next_anti_air_attack: Next time the army can perform a anti-air attack.
        last_anti_air_attack: Last time the army performed a anti-air attack.
        last_anti_air_attack_distance: Distance to the target of the last anti-air attack.
        last_damage_taken_time: The last time damage was taken.
        strength: Strength of the army.
        defence: Defence value of the army
        army_moral: The moral of the army.
        radar_signature_feature: How the army shows up on radar.
        token_feature: How the army consumes tokens on mobilization.
    """
    C = "a"
    next_attack_time: Optional[DateTimeMillisecondsInt] = None
    estimated_arrival_time: Optional[DateTimeMillisecondsInt] = None
    spy_reveal_time: Optional[DateTimeMillisecondsInt] = None
    last_damage_taken_time: Optional[DateTimeMillisecondsInt] = None

    patrol_radius: float = -1
    id: int = None
    size: int = 1
    health: float = 1.0
    kills: int = 0
    owner_id: int = None
    army_number: int = None
    location_id: int = None
    position: Point = None
    last_direction: Point = None
    on_sea: bool = False
    at_airfield: bool = False
    units: UnitList[Unit] = field(default_factory=UnitList)

    commands: LinkedList[Command] = field(default_factory=LinkedList)
    fight_status: FightStatus = FightStatus.IDLE
    battle: Battle = None
    attack_unit_id: int = None
    attack_position: Point = None

    # I do not now any unit which needs rail but whatever
    needs_rail: bool = False
    needs_water: bool = False
    has_stealth: bool = False
    airplane: bool = False

    pre_fight_size: int = None
    pre_fight_type: int = None

    range: int = 5
    base_speed: float = None

    view_width: int = None
    detailed_view_width: int = None
    aggressiveness: Aggressiveness = Aggressiveness.DEFAULT
    forced_march: ForcedMarch = ForcedMarch.DEACTIVE
    removed: bool = False
    terrain_type: TerrainType = None
    terrain_type_str: TerrainTypeStr = None

    air_parameters: Optional[AirParameters] = None
    anti_air_parameters: Optional[AntiAirParameters] = None

    carriable: bool = False
    carrier_feature: Optional[CarrierFeature] = None

    last_location_ids: list[int] = None
    end_of_unit_walk: bool = None  # No idea what this is. Might be a boolean.

    hit_points: float = None
    max_hit_points: int = None

    missile_carrier_feature: Optional[MissileCarrierFeature] = None
    entrenched: bool = False

    next_anti_air_attack: DateTimeMillisecondsInt = None
    last_anti_air_attack: DateTimeMillisecondsInt = None
    last_anti_air_attack_distance: float = None
    strength: float = None

    defence: float = None
    army_moral: float = None

    radar_signature_feature: Optional[RadarSignatureFeature] = None
    token_feature: Optional[TokenFeature] = None

    _angle: int | None = None

    MAPPING = {
        "id": "id",
        "size": "s",
        "health": "h",
        "kills": "k",
        "owner_id": "o",
        "army_number": "an",
        "location_id": "l",
        "position": "p",
        "last_direction": "ld",
        "on_sea": "os",
        "at_airfield": "aa",
        "units": "u",
        "commands": "c",
        "fight_status": "fs",
        "battle": "b",
        "attack_unit_id": "au",
        "attack_position": "ap",
        "next_attack_time": "na",
        "estimated_arrival_time": "at",
        "needs_rail": "nr",
        "needs_water": "nw",
        "has_stealth": "hs",
        "airplane": "a",
        "pre_fight_size": "ps",
        "pre_fight_type": "pt",
        "range": "r",
        "base_speed": "bs",
        "spy_reveal_time": "st",
        "view_width": "vw",
        "detailed_view_width": "dvw",
        "aggressiveness": "ag",
        "forced_march": "fm",
        "removed": "rm",
        "terrain_type_str": "terrainType",
        "terrain_type": "tt",  # TODO confirm this is a terrain type (another similar exists)
        "air_parameters": "aip",
        "anti_air_parameters": "aap",
        "carriable": "ca",
        "carrier_feature": "cf",
        "last_location_ids": "ll",
        "end_of_unit_walk": "uw",
        "hit_points": "hp",
        "max_hit_points": "mhp",
        "missile_carrier_feature": "mc",
        "entrenched": "en",
        "next_anti_air_attack": "naa",
        "last_anti_air_attack": "laa",
        "last_anti_air_attack_distance": "laadist",
        "last_damage_taken_time": "ldt",
        "strength": "str",
        "defence": "def",
        "army_moral": "m",
        "radar_signature_feature": "rs",
        "token_feature": "tok",
        "patrol_radius": "patrolRadius"
    }

    def action_copy(self) -> "Army":
        return Army(
            id = self.id,
            size = self.size,
            owner_id = self.owner_id,
            location_id = self.location_id,
            position = self.position,
            last_direction = self.last_direction,
            on_sea = self.on_sea,
            units = UnitList([unit.action_copy() for unit in self.units]),
            commands = LinkedList([command.action_copy() for command in self.commands]),
            attack_unit_id=self.attack_unit_id,
            attack_position=self.attack_position,
            aggressiveness=self.aggressiveness,
            forced_march=self.forced_march,
        )


    def set_command(self, command: Command) -> int:
        """
        Sets a single command for further processing. Converts the provided command
        into a list and delegates the operation to set_commands for execution.

        Args:
            command (Command): The command to be processed.

        Returns:
            int: Unique action id.
        """
        return self.set_commands([command])

    def set_commands(self, commands: list[Command]) -> int:
        """
        Update the commands for the current instance and trigger the necessary updates.

        Parameters:
            commands (list[Command]): A list of Command objects to be assigned.

        Returns:
            int: Unique action id.
        """
        self.commands = LinkedList(commands)
        return self.game.online.do_action(ArmyAction(LinkedList([self.action_copy()])))

    def add_command(self, command: Command) -> int:
        """
        Add a command to the command queue, associates it with the game's action list,
        and returns the unique action id.

        Args:
            command (Command): The command to be added to the command queue.

        Returns:
            int: Unique action id.
        """
        self.commands.append(command)
        return self.game.online.do_action(ArmyAction(LinkedList([self.action_copy()])))

    def patrol(self, target: Point) -> tuple[Optional[int], ArmyActionResult]:
        """
        Patrols a specified target point using an aircraft. Function is only available for aircraft.
        Returns ArmyActionResult.Ok if successful, otherwise ArmyActionResult.NotAircraft if the current
        Army is not an aircraft or ArmyActionResult.OutOfRange if the target is outside the range of the aircraft.

        Parameters:
            target (Point): The target location that the aircraft should patrol.

        Returns:
        tuple[Optional[int], ArmyActionResult]
            A tuple containing an optional unique action id and the result of the operation
            (ArmyActionResult).
        """
        if self.airplane:
            if self.is_in_range(target):
                return self.set_command(PatrolCommand(target, True, PatrolType.guard, None)), ArmyActionResult.Ok
            else:
                return None, ArmyActionResult.OutOfRange
        else:
            return None, ArmyActionResult.InvalidCommandForUnitTypes

    def is_in_range(self, point: Point) -> bool:
        """
        Determines whether a given point is within the range of the current army.

        For objects such as airplanes, this method checks if the distance between
        the current position and the specified point is within the specified range.
        For non-airplane armies, the range check is ignored, and returns True.

        Args:
            point (Point): The point to be checked against the current position.

        Returns:
            bool: True if the point is within range, False otherwise.
        """
        if self.airplane:
            return self.position.distance(point) <= self.range
        else:
            return True

    def set_waypoint(self, point: Point) -> tuple[Optional[int], ArmyActionResult]:
        """
        Sets a waypoint for the army unit to move to.

        Parameters:
            point (Point): The target waypoint to navigate to.

        Returns:
            tuple[Optional[int], ArmyActionResult]: A tuple containing an optional unique action id
            and result status. Returns ArmyActionResult.Ok if successful, otherwise ArmyActionResult.OutOfRange if
            the army is an airplane and the target point is outside the range of the aircraft.
        """
        if self.airplane:
            if self.is_in_range(point):
                return self.set_command(GotoCommand(start_position=self.position,
                                                    target_position=point)), ArmyActionResult.Ok
            else:
                return None, ArmyActionResult.OutOfRange
        else:
            return self.set_commands([
                GotoCommand(start_position=self.position,
                            target_position=self.position,
                            speed=self.base_speed,
                            on_water=self.on_sea),
                GotoCommand(start_position=self.position,
                            target_position=point,
                            speed=self.base_speed,
                            on_water=self.on_sea)]), ArmyActionResult.Ok

    def add_waypoint(self, point: Point):
        """
        Adds a waypoint to the current command queue. This method modifies the command
        queue by appending a new GotoCommand if the last command in the queue is a
        GotoCommand. If the last command is not a GotoCommand and not a SplitCommand, it does not modify the
        queue and returns an indication of an invalid command queue.

        Parameters:
            point (Point): The target waypoint to be added to the command queue.

        Returns:
            Tuple[None, ArmyActionResult]:
        """
        if self.commands:
            last_command = self.commands[-1]
            if isinstance(last_command, GotoCommand):
                return self.add_command(GotoCommand(start_position=last_command.target_position,
                                                    target_position=point,
                                                    speed=self.base_speed,
                                                    on_water=self.on_sea,
                                                    )), ArmyActionResult.Ok
            else:
                return None, ArmyActionResult.InvalidCommandQueue
        else:
            return self.set_waypoint(point)

    def attack_point(self, point: Point) -> tuple[Optional[int], ArmyActionResult]:
        """
        Attacks a specified point via the current army.

        Args:
            point (Point): The target location on the grid or map to be attacked.

        Returns:
            tuple[Optional[int], ArmyActionResult]: A tuple consisting of:
                - An integer identifier for the unique action if applicable, or None
                  if the action cannot proceed.
                - An ArmyActionResult enum value indicating the result of the action,
                  such as if it was successful or if the point is out of range.

        Raises:
            None
        """
        if self.airplane:
            if self.is_in_range(point):
                return self.set_command(AttackCommand(None, point, True)), ArmyActionResult.Ok
            else:
                return None, ArmyActionResult.OutOfRange
        else:
            return self.set_command(AttackCommand(None, point, True)), ArmyActionResult.Ok

    def attack_army(self, army: "Army") -> tuple[Optional[int], ArmyActionResult]:
        """
        Attacks an enemy army. One needs to specify the target army.

        Args:
            army (Army): The target army.

        Returns:
            tuple[Optional[int], ArmyActionResult]: A tuple containing an optional integer representing the
                unique action id and a corresponding ArmyActionResult indicating success or failure.
        """
        if self.airplane:
            if self.is_in_range(army.position):
                return self.set_command(AttackCommand(army.id, None, True)), ArmyActionResult.Ok
            else:
                return None, ArmyActionResult.OutOfRange
        else:
            return self.set_command(AttackCommand(army.id, None, True)), ArmyActionResult.Ok

    def split_army(self, point: Point, split_units_count: list[tuple[int, int]]) -> tuple[
        Optional[int], ArmyActionResult]:
        """
        Splits the current army and assigns a new command to the newly created army.

        This function manages splitting specified units from the current army and
        delegating their movement via a new command. Units will only be split if
        they are present in the current army and if they meet the required count.
        The result includes the updated command and a result status indicating
        success or error in operations.

        Args:
            split_units_count: List of tuples, where each tuple
                contains the unit type ID at index 0 and the count of units to split at index 1.
            point (Point): Destination point for the new army's movement.

        Returns:
            tuple[Optional[int], ArmyActionResult]: A tuple containing optional
                unique action ID (can be None if the operation fails) and a
                corresponding ArmyActionResult.
        """

        split_units = []
        for unit_id, unit_count in split_units_count:
            for my_unit in self.units:
                if my_unit.unit_type_id == unit_id:
                    if my_unit.size >= unit_count:
                        split_units.append(Unit(0, unit_id, size=unit_count))

        goto_command = GotoCommand(self.position, point)
        new_army = Army(units=UnitList(split_units), owner_id=self.owner_id, position=self.position,
                        commands=LinkedList([goto_command]))
        split_command = SplitArmyCommand(splitted_army=new_army)
        return self.set_command(split_command), ArmyActionResult.Ok

    def split_and_move_unit(self, unit_type_name: str, amount: int, target_province_name: str) -> tuple[
        int | None, ArmyActionResult]:
        type_ids = [x.unit_type_id for x in self.units]
        amounts = [x.size for x in self.units]

        tuples = []
        for i in range(len(type_ids)):
            if self.game.get_unit_type(type_ids[i]).type_name == unit_type_name:
                if amounts[i] >= amount:
                    tuples.append((type_ids[i], amount))
                else:
                    return None, ArmyActionResult.InvalidCommandForUnitTypes
            else:
                tuples.append((type_ids[i], 0))

        result = self.split_army(
            self.game.get_provinces_by_name(target_province_name).static_data.center_coordinate,
            tuples
        )
        return result

    def cancel_commands(self) -> tuple[Optional[int], ArmyActionResult]:
        """
        Cancels the current active commands for the army.

        Returns:
            tuple[Optional[int], ArmyActionResult]
                A tuple where the first element is the optional unique action id, or None if there were
                no active commands. The second element indicates the ArmyActionResult.
        """
        if self.commands:
            return self.set_commands([]), ArmyActionResult.Ok
        else:
            return None, ArmyActionResult.NoActiveCommand

    def get_next_connections(self) -> list[Point]:
        map_ = self.game.game_state.states.map_state.map
        relevant_points = map_.static_map_data.get_points(map_.get_province_id_from_point(self.position))
        adj = map_.static_map_data.graph

        for point in relevant_points:
            if point.distance(self.position) <= 0.1:
                return adj[point]

        for point in relevant_points:
            for adj_point in adj[point]:
                vector_pos_to_point = self.position - point
                vector_a_to_b = adj_point - point
                if vector_pos_to_point.cross(vector_a_to_b) <= 0.1:
                    if 0 < vector_pos_to_point.dot(vector_a_to_b) < vector_a_to_b.dot(vector_a_to_b):
                        return [adj_point, point]

    @staticmethod
    def linear_interpolate(start: datetime, end: datetime, current: datetime, start_pos: Point, end_pos: Point):
        if start == end:
            return start_pos
        delta = (end - start).total_seconds()
        elapsed_time = (current - start).total_seconds()
        fraction = elapsed_time / delta
        interpolated_x = start_pos.x + fraction * (end_pos.x - start_pos.x)
        interpolated_y = start_pos.y + fraction * (end_pos.y - start_pos.y)
        return Point(interpolated_x, interpolated_y)

    def get_next_command(self) -> Command | None:
        if self.commands:
            return self.commands[0]
        return None

    def get_position(self, timestamp: Optional[datetime] = None) -> Point:
        if self.is_flying() and self.attack_position is not None:
            return self.get_air_position(timestamp)
        return self.get_land_position(timestamp)

    def get_target_position(self):
        if self.commands:
            # Iterate over commands in reverse order
            for command in reversed(self.commands):
                # Check if command is a goto or a relocating patrol command
                if (isinstance(command, GotoCommand) or
                        (isinstance(command, PatrolCommand) and command.is_relocation())):
                    return command.target_position
        # Default to current position if no valid command is found
        return self.get_position()

    def get_land_position(self, timestamp: Optional[datetime] = None) -> Point:
        """
        Calculate the army's current position based on its movement status and commands.

        Args:
            timestamp (datetime, optional): The specific time to calculate position for.
                                          Defaults to current time if None.
        Returns:
            Point: The calculated position of the army.
        """
        # If army has air parameters and is at an airfield, return airfield position
        if self.air_parameters and self.air_parameters.air_field:
            return self.air_parameters.get_airfield_position()

        # If no commands or not moving, return static position
        if not self.commands or not self.is_moving():
            return self.position

        # Get current time in milliseconds if not provided
        current_time = timestamp if timestamp else self.game.client_time()

        # Use existing position or create new one based on force_update
        result_pos = Point(0, 0)

        # Get first command
        command = self.commands[0]
        if not command.arrival_time:
            logger.debug(f"Command {self} has no arrival time")
            return self.position

        if current_time >= command.arrival_time:
            # If past arrival time, use target position
            result_pos.x = command.target_position.x
            result_pos.y = command.target_position.y
        else:
            # Calculate interpolated position between start and target
            time_progress = ((current_time- command.start_time) / (command.arrival_time - command.start_time))
            result_pos.x = command.start_position.x + (
                    command.target_position.x - command.start_position.x) * time_progress
            result_pos.y = command.start_position.y + (
                    command.target_position.y - command.start_position.y) * time_progress

        return result_pos

    def get_air_position(self, timestamp: Optional[datetime] = None) -> Point | None:
        """
        Calculate the army's current air position based on its flight status and timing.

        Args:
            timestamp (datetime, optional): The specific time to calculate position for.
                                          Defaults to current time if None.

        Returns:
            Point: The calculated air position of the army.
        """
        # Use current time if timestamp not provided
        current_time = timestamp if timestamp else self.game.client_time()
        current_time_ms = int(current_time.timestamp() * 1000)

        if self.is_flying() and self.attack_position is not None:
            if self.fight_status == FightStatus.PATROLLING:
                # For patrolling, use attack position directly
                return Point(self.attack_position.x, self.attack_position.y)
            else:
                if not self.next_attack_time:
                    return self.position
                # Calculate interpolated position
                next_attack_time = int(self.next_attack_time.timestamp() * 1000)
                last_air_action_time = int(
                    self.air_parameters.last_air_action_time.timestamp() * 1000) if self.air_parameters else 0

                # Calculate progress (0 to 1) between last action and next attack
                denominator = next_attack_time - last_air_action_time
                if denominator == 0:
                    progress = 0
                else:
                    progress = max(0.0, 1 - (next_attack_time - current_time_ms) / denominator)

                # Determine start and end points based on direction
                start_pos = self.air_parameters.last_air_position
                end_pos = self.get_land_position(current_time) if self.is_airplane_returning() else self.attack_position
                # Interpolate between start and end positions
                return Point(
                    start_pos.x + (end_pos.x - start_pos.x) * progress,
                    start_pos.y + (end_pos.y - start_pos.y) * progress
                )

        return None

    def is_moving(self) -> bool:
        """
        Is only working for ships and ground units
        """
        return (
                self.commands is not None and
                len(self.commands) > 0 and
                isinstance(self.commands[0], GotoCommand) and
                self.commands[0].arrival_time != 0
        )

    def is_flying(self) -> bool:
        """
        Determine if the army is currently flying based on its status and capabilities.

        Returns:
            bool: True if the army is flying, False otherwise.
        """
        # Calculate and cache the flying status if not already set
        if self.is_fighting():
            return False
        else:
            return (
                    (self.airplane and self.is_patrolling()) or
                    (self.airplane and self.is_airplane_returning()) or
                    (self.airplane and self.is_bombing()) or
                    self.is_relocating() or
                    self.is_doing_air_mobile_relocation()
            )

    def is_fighting(self) -> bool:
        """
        Determine if the army is currently engaged in direct combat.

        Returns:
            bool: True if fighting or has attackers, False otherwise.
        """
        return (
            self.fight_status == FightStatus.FIGHTING or
            self.get_attacker_count() > 0 if self.battle else False
        )

    def get_attacker_count(self) -> int:
        return len(self.battle.attacker_ids)

    def is_bombarding(self) -> bool:
        """
        Determine if the army is currently bombarding.

        Returns:
            bool: True if bombarding, False otherwise.
        """
        return self.fight_status == FightStatus.BOMBARDING

    def is_bombing(self) -> bool:
        """
        Determine if the army is currently bombing.

        Returns:
            bool: True if bombing, False otherwise.
        """
        return self.fight_status == FightStatus.BOMBING

    def is_airplane(self) -> bool:
        return self.airplane

    def is_at_airfield(self) -> bool:
        return self.at_airfield

    def is_on_sea(self) -> bool:
        return self.on_sea

    def is_patrolling(self) -> bool:
        """
        Determine if the army is currently patrolling or approaching a patrol position.

        Returns:
            bool: True if patrolling or approaching patrol, False otherwise.
        """
        return (
                self.fight_status == FightStatus.PATROLLING or
                self.fight_status == FightStatus.APPROACH_PATROL
        )

    def is_attacking(self) -> bool:
        """
        Determine if the army is currently engaged in any form of attack.

        Returns:
            bool: True if bombarding, bombing, or fighting, False otherwise.
        """
        return (
                self.is_bombarding() or
                self.is_bombing() or
                self.is_fighting()
        )

    def is_airplane_returning(self) -> bool:
        if self.get_next_command():
            if isinstance(self.get_next_command(), WaitCommand):
                return self.get_next_command().is_returning()
        return False

    def is_relocating(self) -> bool:
        if self.commands and len(self.commands) > 0:
            next_command = self.get_next_command()
            return isinstance(next_command, PatrolCommand) and next_command.is_relocation()
        else:
            return False

    def is_doing_air_mobile_relocation(self) -> bool:
        if not self.is_air_mobile():
            return False
        else:
            next_command = self.get_next_command()
            return (
                    isinstance(next_command, PatrolCommand) and
                    next_command.patrol_type == PatrolType.air_mobile_relocation
            )

    def is_air_mobile(self) -> bool:
        if not self.units:
            return False
        return all(unit.has_feature(UnitFeature.UNITFEATURE_AIR_MOBILE) for unit in self.units)

    def is_ship(self) -> bool:
        # Check if ship status is not yet determined
        # Iterate over units in reverse order
        for unit in reversed(self.units):
            if unit and unit.get_unit_type().is_ship():
                return True
        return False


    def get_image(self) -> Tuple[str, str]:
        """
        Returns a tuple of paths to the image of the army.
        First path is the image best representing the current state of the army.
        Not every unit type has that 'optimal' image implemented.
        Second path is a default path that simple shows the unit standing still while
        be correctly rotated.
        """
        status = None

        if self.is_fighting() or self.is_flying():
            status = 'fighting'

        if self.is_flying():
            status = 'air'

        if self.is_fighting() and self.get_attacker_count() > 0:
            status = 'defending'

        angle_index = self.get_discrete_angle_index()
        if not self.units:
            if self.is_on_sea():
                return 'images/warfare/unit_Fleet1.jpg', "images/warfare/unit_Fleet1.jpg"
            elif self.size > 0 and self.health < 0.5:
                return 'images/warfare/unit_Army2.jpg', 'images/warfare/unit_Army2.jpg'
            else:
                return 'images/warfare/unit_Army.jpg', 'images/warfare/unit_Army.jpg'

        for unit_index in range(len(self.units) - 1, -1, -1):
            current_unit = self.units[unit_index]
            if current_unit and (not self.is_on_sea() or current_unit.is_ship()):
                unit_type = current_unit.get_unit_type()
                return (current_unit.get_image(unit_type, status, self.is_moving(), angle_index),
                        current_unit.get_image(unit_type, None, False, angle_index))
            elif current_unit and self.is_on_sea() and not current_unit.is_ship():
                transport_ship_option = self.game.game_state.states.mod_state.get_transport_ship_id()
                if transport_ship_option and self.is_on_sea() and not self.is_ship():
                    unit_type = self.game.get_unit_type(transport_ship_option)
                    return (current_unit.get_image(unit_type, status, self.is_moving(), angle_index),
                            current_unit.get_image(unit_type, None, False, angle_index))

        if self.is_on_sea():
            return 'images/warfare/unit_Fleet1.jpg', "images/warfare/unit_Fleet1.jpg"
        elif self.size > 0 and self.health < 0.5:
            return 'images/warfare/unit_Army2.jpg', 'images/warfare/unit_Army2.jpg'
        else:
            return 'images/warfare/unit_Army.jpg', 'images/warfare/unit_Army.jpg'

    def get_next_target_position(self) -> Point | None:
        for command in self.commands:
            if command.target_position:
                return command.target_position


    def get_discrete_angle_index(self):
        raw_angle = self.calculate_raw_angle()
        angle_step = 2 * math.pi / 12
        return int((raw_angle + math.pi + angle_step / 2) // angle_step) % 12

    def calculate_raw_angle(self):
        next_command = self.get_next_command()
        if self.is_moving():
            if next_command:
                return next_command.get_direction() + math.pi
            current_position = self.get_position()
            target_position = self.get_next_target_position()
            if current_position != target_position:
                return math.atan2(-target_position.x + current_position.x, target_position.y - current_position.y) + math.pi
        elif self.is_flying():
            current_position = self.get_position()
            target_position = self.get_target_position()
            if current_position != target_position:
                return math.atan2(-target_position.x + current_position.x, target_position.y - current_position.y) + math.pi
        return math.atan2(-self.last_direction.x, self.last_direction.y) + math.pi \
                if (self.last_direction and self.last_direction.get_length(True) > 0) else DEFAULT_ARMY_ANGLE