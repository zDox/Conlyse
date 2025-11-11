"""
Replay patch operations for tracking changes to game state.

This module defines the operations used to represent changes between game states
in the replay system. It supports three types of operations: Add, Replace, and Remove.
"""
import json
from dataclasses import dataclass
from typing import Any
from typing import Union

from conflict_interface.data_types.game_object import dump_any
from conflict_interface.logger_config import get_logger
import msgpack
import zstandard as zstd
from array import array

logger = get_logger()

PathNode = Union[str, int]

# Operation type mapping (more compact than strings)
OP_ADD = 0
OP_REPLACE = 1
OP_REMOVE = 2

OP_TO_INT = {"a": OP_ADD, "p": OP_REPLACE, "r": OP_REMOVE}
INT_TO_OP = {OP_ADD: "a", OP_REPLACE: "p", OP_REMOVE: "r"}

# Zstandard compressor (reusable for better performance)
_compressor = zstd.ZstdCompressor(level=3)  # Level 3 is good balance
_decompressor = zstd.ZstdDecompressor()

@dataclass
class AddOperation:
    """
    Represents adding a new value to the game state.
    
    Used when a new element is added to a list or dict, or when a new attribute
    is set on a GameObject.
    
    Attributes:
        Key: Serialization key for this operation type
        path: JSON path to the location where the value should be added
        new_value: The value to be added
    """
    Key = "a"
    path: list[str] = None
    new_value: Any = None

@dataclass
class ReplaceOperation:
    """
    Represents replacing an existing value in the game state.
    
    Used when an attribute value changes or when an element in a list/dict is updated.
    
    Attributes:
        Key: Serialization key for this operation type
        path: JSON path to the location of the value to replace
        new_value: The new value to set at that location
    """
    Key = "p"
    path: list[str] = None
    new_value: Any = None

@dataclass
class RemoveOperation:
    """
    Represents removing a value from the game state.
    
    Used when an element is removed from a list/dict or when an attribute is unset.
    
    Attributes:
        Key: Serialization key for this operation type
        path: JSON path to the location of the value to remove
        new_value: Always None for remove operations
    """
    Key = "r"
    path: list[str] = None
    new_value = None


Operation = Union[AddOperation, ReplaceOperation, RemoveOperation, None]

class ReplayPatch:
    """
    A collection of operations representing changes between two game states.
    
    ReplayPatch tracks the difference between two game states as a sequence of
    add, replace, and remove operations. It can be serialized to/from JSON for
    storage and can be applied to a game state to transition it forward or backward.
    """
    
    def __init__(self):
        """Initialize an empty replay patch."""
        self.operations: list[Union[AddOperation, ReplaceOperation, RemoveOperation]] = []

    def __eq__(self, other):
        """Check equality between two ReplayPatch instances."""
        if not isinstance(other, ReplayPatch):
            return False

        return self.operations == other.operations

    def add_op(self, path: list[str], new_value: Any) -> None:
        """
        Add an AddOperation to this patch.
        
        Args:
            path: JSON path to where the value should be added
            new_value: The value to add
        """
        self.operations.append(AddOperation(path, new_value))

    def replace_op(self, path: list[str], new_value: Any) -> None:
        """
        Add a ReplaceOperation to this patch.
        
        Args:
            path: JSON path to the value to replace
            new_value: The new value to set
        """
        self.operations.append(ReplaceOperation(path=path, new_value=new_value))

    def remove_op(self, path: list[str]) -> None:
        """
        Add a RemoveOperation to this patch.
        
        Args:
            path: JSON path to the value to remove
        """
        self.operations.append(RemoveOperation(path))

    def set_hierarchy(self, higher_class: str) -> None:
        """
        Prepend a class name to all operation paths.
        
        Used to nest patches within a higher-level structure.
        
        Args:
            higher_class: The class name to prepend to all paths
        """
        for op in self.operations:
            op.path.insert(0, higher_class)
            
    def is_empty(self) -> bool:
        """
        Check if this patch contains any operations.
        
        Returns:
            True if there are no operations, False otherwise
        """
        return len(self.operations) == 0

    def merge(self, keys: list[str], other: "ReplayPatch") -> None:
        """
        Merge another patch into this one, prepending keys to all paths.
        
        Args:
            keys: List of keys to prepend to paths from the other patch
            other: The patch to merge into this one
        """
        if other is not None and not other.is_empty():
            for op in other.operations:
                op.path = keys + op.path
                self.operations.append(op)

    def debug_str(self) -> None:
        """Print a human-readable debug representation of this patch."""
        add_str = [f"({op.path}, {op.new_value})" for op in self.operations if isinstance(op, AddOperation)]
        replace_str = [f"({op.path}, {op.new_value})" for op in self.operations if isinstance(op, ReplaceOperation)]
        remove_str = [f"{op.path}" for op in self.operations if isinstance(op, RemoveOperation)]
        print(f"Add: {',\n'.join(add_str)}")
        print(f"Replace: {',\n'.join(replace_str)}")
        print(f"Remove: {',\n'.join(remove_str)}")

    def to_string(self) -> str:
        """
        Serialize this patch to a JSON string.
        
        Returns:
            JSON string representation of all operations
        """

        operations = [(op.Key, op.path, dump_any(op.new_value)) for op in self.operations]
        return json.dumps(operations)

    @classmethod
    def from_string(cls, string: str) -> "ReplayPatch":
        """
        Deserialize a patch from a JSON string.
        
        Args:
            string: JSON string representation of operations
            
        Returns:
            A new ReplayPatch instance with the deserialized operations
        """
        operations = json.loads(string)
        instance = cls()
        for op in operations:
            key, path, new_value = op
            if key == "a":
                instance.add_op(path, new_value)
            elif key == "p":
                instance.replace_op(path, new_value)
            elif key == "r":
                instance.remove_op(path)
        return instance

    def to_bytes(self) -> bytes:
        """
        Serialize the replay patch to compressed bytes with optimized performance.

        Uses a columnar storage format to reduce redundancy:
        - Paths are deduplicated into a lookup table
        - Operations are stored as integers (0-2)
        - Path references use indices into the path table
        - Final data is compressed with zstd for speed

        Returns:
            bytes: Compressed binary representation of the patch
        """
        # Step 1: Build deduplicated path lookup table
        # Maps path tuples to their index in the path list
        path_dict = {}
        path_list = []

        for op in self.operations:
            # Normalize path to tuple for consistent hashing
            path_key = tuple(op.path) if isinstance(op.path, list) else op.path

            # Add new paths to lookup table
            if path_key not in path_dict:
                if not path_key:
                    logger.error("Empty path in replay patch operation.")
                path_dict[path_key] = len(path_list)
                # Store as list for msgpack serialization compatibility
                path_list.append(
                    list(path_key) if isinstance(path_key, tuple) else path_key
                )

        # Step 2: Pre-allocate columnar arrays for efficient storage
        num_ops = len(self.operations)

        # Operation types as unsigned bytes (0=add, 1=replace, 2=remove)
        ops_col = array('B', (0,) * num_ops)

        # Path indices - use 16-bit if possible, otherwise 32-bit
        index_type = 'H' if len(path_list) < 65536 else 'I'
        path_indices_col = array(index_type, (0,) * num_ops)

        # Operation values (kept as list since values are heterogeneous)
        values_col = []

        # Step 3: Populate columnar data
        for i, op in enumerate(self.operations):
            # Get normalized path key
            path_key = tuple(op.path) if isinstance(op.path, list) else op.path

            if not path_key or path_key not in path_dict:
                logger.error("Empty or unknown path in replay patch operation.")
                continue

            # Store operation type as integer
            ops_col[i] = OP_TO_INT.get(op.Key, OP_ADD)

            # Store path reference as index
            path_indices_col[i] = path_dict[path_key]

            # Serialize and store operation value
            values_col.append(dump_any(op.new_value))

        # Step 4: Pack data into compact dictionary format
        # Using single-character keys to reduce serialized size
        data = {
            "p": path_list,  # paths: deduplicated path table
            "o": ops_col.tobytes(),  # ops: operation types as bytes
            "i": path_indices_col.tobytes(),  # indices: path references as bytes
            "v": values_col,  # values: operation values
            "t": index_type  # type: array type for path indices
        }

        # Step 5: Serialize with msgpack (efficient binary format)
        binary = msgpack.packb(data, use_bin_type=True)

        # Step 6: Compress with zstd (faster than lzma, similar compression ratio)
        compressed_data = _compressor.compress(binary)

        return compressed_data

    @classmethod
    def from_bytes(cls, b: bytes) -> "ReplayPatch":
        """
        Deserialize a replay patch from compressed bytes.

        Reverses the serialization process:
        1. Decompress with zstd
        2. Unpack msgpack data
        3. Reconstruct arrays from bytes
        4. Rebuild operations using path lookup table

        Args:
            b: Compressed binary data from to_bytes()

        Returns:
            ReplayPatch: Reconstructed patch object
        """
        # Step 1: Decompress the data
        decompressed_data = _decompressor.decompress(b)

        # Step 2: Unpack msgpack binary format
        data = msgpack.unpackb(decompressed_data, raw=False)

        # Extract columnar data
        path_list = data["p"]  # Deduplicated paths
        ops_bytes = data["o"]  # Operation types as bytes
        path_indices_bytes = data["i"]  # Path indices as bytes
        values_col = data["v"]  # Operation values
        idx_type = data.get("t", "I")  # Array type for indices (H or I)

        # Step 3: Reconstruct arrays from byte data
        # Operation types (unsigned bytes)
        ops_col = array('B')
        ops_col.frombytes(ops_bytes)

        # Path indices (16 or 32-bit unsigned integers)
        path_indices_col = array(idx_type)
        path_indices_col.frombytes(path_indices_bytes)

        # Step 4: Rebuild the patch object
        patch = cls()

        # Iterate through operations and reconstruct each one
        for i in range(len(ops_col)):
            # Get operation components
            op_int = ops_col[i]  # Operation type as integer
            path_idx = path_indices_col[i]  # Path index into lookup table
            value = values_col[i]  # Operation value
            path = path_list[path_idx]  # Resolve path from lookup table

            # Convert operation integer back to character and add to patch
            op_char = INT_TO_OP[op_int]
            if op_char == "a":
                patch.add_op(path, value)
            elif op_char == "p":
                patch.replace_op(path, value)
            elif op_char == "r":
                patch.remove_op(path)

        return patch


class BidirectionalReplayPatch:
    """
    A pair of patches for forward and backward time travel in replays.
    
    This class maintains two patches: one for moving forward in time and one for
    moving backward. This allows efficient bidirectional navigation through replay
    history without storing complete game states at each timestamp.
    """
    
    def __init__(self):
        """Initialize with empty forward and backward patches."""
        self.forward_patch = ReplayPatch()
        self.backward_patch = ReplayPatch()

    @classmethod
    def from_existing_patches(cls, forward: ReplayPatch, backward: ReplayPatch) -> "BidirectionalReplayPatch":
        """
        Create a bidirectional patch from existing forward and backward patches.
        
        Args:
            forward: The patch to apply when moving forward in time
            backward: The patch to apply when moving backward in time
            
        Returns:
            A new BidirectionalReplayPatch instance
        """
        instance = cls()
        instance.forward_patch = forward
        instance.backward_patch = backward
        return instance

    def forward_from_string(self, string: str) -> None:
        """
        Deserialize the forward patch from a JSON string.
        
        Args:
            string: JSON string representation of the forward patch
        """
        self.forward_patch = ReplayPatch.from_string(string)

    def backward_from_string(self, string: str) -> None:
        """
        Deserialize the backward patch from a JSON string.
        
        Args:
            string: JSON string representation of the backward patch
        """
        self.backward_patch = ReplayPatch.from_string(string)

    def forward_to_string(self) -> str:
        """
        Serialize the forward patch to a JSON string.
        
        Returns:
            JSON string representation of the forward patch
        """
        return self.forward_patch.to_string()

    def backward_to_string(self) -> str:
        """
        Serialize the backward patch to a JSON string.
        
        Returns:
            JSON string representation of the backward patch
        """
        return self.backward_patch.to_string()

    def add(self, path: list[str], old_value: Any, new_value: Any) -> None:
        """
        Record an add operation in both directions.
        
        Forward: add new_value, Backward: remove it
        
        Args:
            path: JSON path where the value is added
            old_value: Not used (included for API consistency)
            new_value: The value being added
        """
        self.forward_patch.add_op(path, new_value)
        self.backward_patch.remove_op(path)

    def replace(self, path: list[str], old_value: Any, new_value: Any) -> None:
        """
        Record a replace operation in both directions.
        
        Forward: replace with new_value, Backward: replace with old_value
        
        Args:
            path: JSON path to the value being replaced
            old_value: The current value before replacement
            new_value: The new value after replacement
        """
        self.forward_patch.replace_op(path, new_value)
        self.backward_patch.replace_op(path, old_value)

    def remove(self, path: list[str], old_value: Any) -> None:
        """
        Record a remove operation in both directions.
        
        Forward: remove the value, Backward: add it back
        
        Args:
            path: JSON path to the value being removed
            old_value: The value being removed (needed to restore it when going backward)
        """
        self.forward_patch.remove_op(path)
        self.backward_patch.add_op(path, old_value)