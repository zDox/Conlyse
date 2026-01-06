from __future__ import annotations

from copy import deepcopy
from dataclasses import fields
from dataclasses import is_dataclass
from typing import Any
from typing import TYPE_CHECKING
from typing import get_type_hints

if TYPE_CHECKING: # The one place where this is needed for type hinting
    from conflict_interface.interface.game_interface import GameInterface

class GameObject:
    """
    Base class for all game objects.
    """
    _type_hints = None
    def __init__(self, game: GameInterface):
        """
        Initializes the GameObject with an optional reference
        to the game instance.

        Args:
            game (optional): The central game instance or None.
        """
        self.game = game  # Reference to the central game instance
        
    def __hash__(self):
        if not hasattr(self, "MAPPING"):
            raise ValueError(f"{type(self).__name__} has no MAPPING implemented")
        return hash(tuple(self.__getattribute__(key) for key in self.get_mapping().keys()))

    _mapping = {}
    @classmethod
    def get_mapping(cls):
        if not hasattr(cls, "MAPPING"):
            raise ValueError(f"{cls.__name__} has no MAPPING implemented")

        cls._mapping = cls.MAPPING
        for c in cls.__bases__:
            if c is GameObject:
                continue
            if issubclass(c, GameObject):
                cls._mapping = {**cls._mapping,
                                **c.get_mapping()}
        return cls._mapping

    @classmethod
    def get_type_hints_cached(cls):
        if cls._type_hints is None:
            cls._type_hints = get_type_hints(cls)
        return cls._type_hints

    def set_game(self, game: GameInterface | None):
        """
        Sets the game instance for this object and all nested GameObjects.

        Args:
            game: The central game instance.
        """
        self.game = game
        for f in fields(self):
            value = getattr(self, f.name)
            GameObject.set_game_recursive(value, game)

    @staticmethod
    def set_game_recursive(value: Any, game: GameInterface | None):
        """
        Iteratively sets the game instance for nested GameObjects using a stack.

        Args:
            value: The value to traverse.
            game: The central game instance.
        """
        if value is None:
            return

        stack = [value]
        seen = set()  # Track visited objects to avoid cycles and duplicates
        seen_add = seen.add
        id_func = id

        while stack:
            current = stack.pop()

            if current is None:
                continue

            # Skip if we've already processed this object
            obj_id = id_func(current)
            if obj_id in seen:
                continue
            seen_add(obj_id)

            if isinstance(current, GameObject):
                current.game = game  # Direct assignment instead of recursive call
                # Add this GameObject's fields to the stack
                for f in fields(current):
                    stack.append(getattr(current, f.name))
            elif is_dataclass(current):
                mapping = getattr(type(current), "MAPPING", None)
                if mapping is not None:
                    for python_var_name in mapping:
                        stack.append(getattr(current, python_var_name))
            elif isinstance(current, list):
                stack.extend(current)
            elif isinstance(current, dict):
                stack.extend(current.values())
                # Only add keys if they might be GameObjects
                # stack.extend(current.keys())  # Consider if keys can be GameObjects

    def __deepcopy__(self, memo):
        cls = self.__class__

        # Check memo to avoid cycles
        if id(self) in memo:
            return memo[id(self)]

        # Create uninitialized instance
        new = cls.__new__(cls)
        memo[id(self)] = new

        # Copy attributes
        for key, value in self.__dict__.items():
            if key == "game":
                setattr(new, key, None)
            else:
                setattr(new, key, deepcopy(value, memo))

        return new