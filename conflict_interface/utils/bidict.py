from typing import Generic, TypeVar, Dict, Optional

# Define generic types for the dictionary keys and values
TKey = TypeVar('TKey')
TValue = TypeVar('TValue')


class Bidict(Generic[TKey, TValue]):
    def __init__(self) -> None:
        self.forward: Dict[TKey, TValue] = {}  # Maps keys to values
        self.reverse: Dict[TValue, TKey] = {}  # Maps values to keys

    def __setitem__(self, key: TKey, value: TValue) -> None:
        """
        Add a mapping from key to value. Ensures the key and value are unique.
        """
        if key in self.forward or value in self.reverse:
            raise ValueError("Key or Value already exists in the dictionary")
        self.forward[key] = value
        self.reverse[value] = key

    def remove_by_key(self, key: TKey) -> None:
        """
        Remove an entry by its key.
        """
        if key not in self.forward:
            raise KeyError("Key not found")
        value = self.forward.pop(key)
        self.reverse.pop(value)

    def remove_by_value(self, value: TValue) -> None:
        """
        Remove an entry by its value.
        """
        if value not in self.reverse:
            raise KeyError("Value not found")
        key = self.reverse.pop(value)
        self.forward.pop(key)

    def get_key(self, value: TValue) -> Optional[TKey]:
        """
        Retrieve a key given its value.
        """
        return self.reverse.get(value)

    def get_value(self, key: TKey) -> Optional[TValue]:
        """
        Retrieve a value given its key.
        """
        return self.forward.get(key)


    def __repr__(self) -> str:
        return f"Forward: {self.forward}\nReverse: {self.reverse}"