from dataclasses import dataclass


@dataclass
class MappedValue:
    original: str
    function: callable = None
    needs_entire_obj: bool = False


class JsonMappedClass:
    @classmethod
    def from_dict(cls, obj: dict):
        parsed_data = {}
        print(obj)
        for new_name, mapped_value in cls.mapping.items():
            print(new_name)
            print(mapped_value)
            if not isinstance(mapped_value, MappedValue):
                if obj.get(mapped_value) is None:
                    parsed_data[new_name] = None
                else:
                    parsed_data[new_name] = cls.__annotations__[new_name](
                            obj.get(mapped_value))
                continue

            if mapped_value.function:
                if mapped_value.needs_entire_obj:
                    parsed_data[new_name] = mapped_value.function(
                            obj, obj.get(mapped_value.original))
                else:
                    parsed_data[new_name] = mapped_value.function(
                            obj.get(mapped_value.original))
            else:
                parsed_data[new_name] = cls.__annotations__[new_name](
                        obj.get(mapped_value.original))
        return cls(**parsed_data)
