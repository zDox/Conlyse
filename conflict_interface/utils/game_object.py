from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from conflict_interface.game_interface import GameInterface
from typing import get_type_hints
from datetime import datetime, timedelta
from .json_mapped_class import JsonMappedClass, DefaultEnumMeta, MappedValue
from .helper import unixtimestamp_to_datetime, seconds_to_timedelta


class GameObject(JsonMappedClass):
    """
    GameObject extends JsonMappedClass to include a reference
    to the central game instance, allowing subclasses to
    interact with game-wide data.
    """

    def __init__(self, game: GameInterface):
        """
        Initializes the GameObject with an optional reference
        to the game instance.

        Args:
            game (optional): The central game instance or None.
        """
        self.game = game  # Reference to the central game instance

    @classmethod
    def from_dict(cls, obj: dict, game: GameInterface = None):
        parsed_data = {}
        resolved = get_type_hints(cls)

        for new_name, mapped_value in cls.MAPPING.items():
            ftype = resolved[new_name]
            if not isinstance(mapped_value, MappedValue):
                # bool should be default False
                if ftype is bool:
                    parsed_data[new_name] = ftype(obj.get(mapped_value))
                elif ftype is datetime:
                    parsed_data[new_name] = unixtimestamp_to_datetime(
                        obj.get(mapped_value))
                elif ftype is timedelta:
                    parsed_data[new_name] = seconds_to_timedelta(
                        obj.get(mapped_value))
                # if type has metaclass DefaultEnumMeta use its default init
                elif obj.get(mapped_value) is None \
                        and type(ftype) is DefaultEnumMeta:
                    parsed_data[new_name] = ftype()
                elif obj.get(mapped_value) is None:
                    parsed_data[new_name] = None

                # If Type has from_dict implemented, use it
                elif issubclass(ftype, GameObject) and hasattr(ftype, "from_dict"):
                    parsed_data[new_name] = ftype.from_dict(
                        obj.get(mapped_value), game=game)
                elif issubclass(ftype, JsonMappedClass) and hasattr(ftype, "from_dict"):
                    parsed_data[new_name] = ftype.from_dict(
                        obj.get(mapped_value))
                else:
                    parsed_data[new_name] = ftype(obj.get(mapped_value))

            elif mapped_value.function:
                if mapped_value.needs_entire_obj:
                    parsed_data[new_name] = mapped_value.function(
                        obj, obj.get(mapped_value.original))
                else:
                    parsed_data[new_name] = mapped_value.function(
                        obj.get(mapped_value.original))
            else:
                parsed_data[new_name] = ftype(
                    obj.get(mapped_value.original))
        instance = cls(**parsed_data)
        instance.game = game
        return instance