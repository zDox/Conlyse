from typing import get_type_hints
from dataclasses import dataclass


class UpdatableClass:
    def update(self, new_class):
        for field in self.__annotations__.keys():
            if not callable(getattr(field, "update", None)):
                continue

            self[field].update(new_class[field])


@dataclass
class MappedValue:
    """
    Attributes
    ----------
    original : str
        the sound that the animal makes
    function : callable
        a function which needs to be called to convert
        between the conflict of nations value and python representation
    needs_entire_obj : bool
        the function needs the entire json object
    """

    original: str
    function: callable = None
    needs_entire_obj: bool = False


class JsonMappedClass:
    """
    JsonMappedClass is a class which should be inhereted by
    a dataclass, which should have a mapping between
    the field from the conflict of nations server and the
    python representation. A mapping is a dict where the keys
    are the field name and the value is a MappedValue.
    """
    @classmethod
    def from_dict(cls, obj: dict):
        parsed_data = {}
        resolved = get_type_hints(cls)

        for new_name, mapped_value in cls.mapping.items():
            ftype = resolved[new_name]
            if not isinstance(mapped_value, MappedValue):
                if obj.get(mapped_value) is None:
                    parsed_data[new_name] = None
                else:
                    parsed_data[new_name] = ftype(obj.get(mapped_value))
                continue

            if mapped_value.function:
                if mapped_value.needs_entire_obj:
                    parsed_data[new_name] = mapped_value.function(
                            obj, obj.get(mapped_value.original))
                else:
                    parsed_data[new_name] = mapped_value.function(
                            obj.get(mapped_value.original))
            else:
                parsed_data[new_name] = ftype(
                        obj.get(mapped_value.original))
        return cls(**parsed_data)
