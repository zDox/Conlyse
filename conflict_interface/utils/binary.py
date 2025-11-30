from __future__ import annotations

from io import BytesIO
from typing import TypeVar

import numpy as np
from numpy.typing import NDArray

T = TypeVar('T')


class BinaryReader:
    """
    Binary reader using NumPy for structured data.

    All fixed-layout structures are read as numpy structured arrays (zero-copy).
    Variable-length data (strings, values) use explicit methods.
    """

    __slots__ = ('data', 'pos', 'size')

    def __init__(self, data: bytes | memoryview, offset: int = 0):
        if isinstance(data, memoryview):
            self.data = data
        else:
            self.data = memoryview(data)
        self.pos = offset
        self.size = len(data)

    # ─────────────────────────────────────────────────────────
    # Structured Array Reads (zero-copy)
    # ─────────────────────────────────────────────────────────

    def read_struct(self, dtype: np.dtype) -> np.void:
        """Read a single structured element."""
        result = np.frombuffer(self.data, dtype=dtype, count=1, offset=self.pos)[0]
        self.pos += dtype.itemsize
        return result

    def read_struct_array(self, dtype: np.dtype, count: int) -> NDArray:
        """Read an array of structured elements."""
        result = np.frombuffer(self.data, dtype=dtype, count=count, offset=self.pos)
        self.pos += dtype.itemsize * count
        return result

    # ─────────────────────────────────────────────────────────
    # Primitive Array Reads (zero-copy)
    # ─────────────────────────────────────────────────────────

    def read_int8_array(self, count: int) -> NDArray[np.int8]:
        result = np.frombuffer(self.data, dtype=np.int8, count=count, offset=self.pos)
        self.pos += count
        return result

    def read_uint8_array(self, count: int) -> NDArray[np.uint8]:
        result = np.frombuffer(self.data, dtype=np.uint8, count=count, offset=self.pos)
        self.pos += count
        return result

    def read_int32_array(self, count: int) -> NDArray[np.int32]:
        result = np.frombuffer(self.data, dtype=np.int32, count=count, offset=self.pos)
        self.pos += count * 4
        return result

    def read_uint32_array(self, count: int) -> NDArray[np.uint32]:
        result = np.frombuffer(self.data, dtype=np.uint32, count=count, offset=self.pos)
        self.pos += count * 4
        return result

    def read_int64_array(self, count: int) -> NDArray[np.int64]:
        result = np.frombuffer(self.data, dtype=np.int64, count=count, offset=self.pos)
        self.pos += count * 8
        return result

    def read_uint64_array(self, count: int) -> NDArray[np.uint64]:
        result = np.frombuffer(self.data, dtype=np.uint64, count=count, offset=self.pos)
        self.pos += count * 8
        return result

    # ─────────────────────────────────────────────────────────
    # Single Value Reads (for counts, sizes, etc.)
    # ─────────────────────────────────────────────────────────

    def read_uint8(self) -> int:
        result = self.data[self.pos]
        self.pos += 1
        return result

    def read_uint16(self) -> int:
        result = int(np.frombuffer(self.data, dtype=np.uint16, count=1, offset=self.pos)[0])
        self.pos += 2
        return result

    def read_uint32(self) -> int:
        result = int(np.frombuffer(self.data, dtype=np.uint32, count=1, offset=self.pos)[0])
        self.pos += 4
        return result

    def read_int32(self) -> int:
        result = int(np.frombuffer(self.data, dtype=np.int32, count=1, offset=self.pos)[0])
        self.pos += 4
        return result

    def read_uint64(self) -> int:
        result = int(np.frombuffer(self.data, dtype=np.uint64, count=1, offset=self.pos)[0])
        self.pos += 8
        return result

    def read_int64(self) -> int:
        result = int(np.frombuffer(self.data, dtype=np.int64, count=1, offset=self.pos)[0])
        self.pos += 8
        return result

    # ─────────────────────────────────────────────────────────
    # Variable-Length Data
    # ─────────────────────────────────────────────────────────

    def read_bytes(self, size: int) -> bytes:
        result = bytes(self.data[self.pos:self.pos + size])
        self.pos += size
        return result

    def read_bytes_view(self, size: int) -> memoryview:
        """Read bytes without copying."""
        result = self.data[self.pos:self.pos + size]
        self.pos += size
        return result

    def read_string(self, size: int) -> str:
        return self.read_bytes(size).decode('utf-8')

    # ─────────────────────────────────────────────────────────
    # Navigation
    # ─────────────────────────────────────────────────────────

    def skip(self, n: int) -> None:
        self.pos += n

    def seek(self, pos: int) -> None:
        self.pos = pos

    def tell(self) -> int:
        return self.pos

    def remaining(self) -> int:
        return self.size - self.pos

    def at_end(self) -> bool:
        return self.pos >= self.size

    def slice_from(self, start: int, size: int) -> memoryview:
        """Get a slice from absolute position (doesn't change pos)."""
        return self.data[start:start + size]

    def fork(self, offset: int | None = None) -> 'BinaryReader':
        """Create a new reader sharing the same data."""
        return BinaryReader(self.data, offset if offset is not None else self.pos)

    # ─────────────────────────────────────────────────────────
    # High-Level Patterns
    # ─────────────────────────────────────────────────────────

    def read_array_with_offsets(
            self,
            offsets: NDArray[np.uint32],
            total_size: int
    ) -> list[memoryview]:
        """
        Read variable-length items given their offsets.
        Returns list of memoryview slices.
        """
        items = []
        data_start = self.pos

        for i in range(len(offsets)):
            start = int(offsets[i])
            end = int(offsets[i + 1]) if i + 1 < len(offsets) else total_size
            items.append(self.data[data_start + start:data_start + end])

        self.pos += total_size
        return items


class BinaryWriter:
    """
    Binary writer using NumPy for structured data.

    All fixed-layout structures are written via numpy tobytes().
    Includes support for deferred writes (fill in sizes later).
    """

    __slots__ = ('buffer',)

    def __init__(self):
        self.buffer = BytesIO()

    # ─────────────────────────────────────────────────────────
    # Structured Array Writes
    # ─────────────────────────────────────────────────────────

    def write_struct(self, value: np.void) -> None:
        """Write a single structured element."""
        self.buffer.write(value.tobytes())

    def write_struct_array(self, arr: NDArray) -> None:
        """Write an array of structured elements."""
        self.buffer.write(arr.tobytes())

    # ─────────────────────────────────────────────────────────
    # Primitive Array Writes
    # ─────────────────────────────────────────────────────────

    def write_int8_array(self, arr: NDArray | list) -> None:
        self.buffer.write(np.asarray(arr, dtype=np.int8).tobytes())

    def write_uint8_array(self, arr: NDArray | list) -> None:
        self.buffer.write(np.asarray(arr, dtype=np.uint8).tobytes())

    def write_int32_array(self, arr: NDArray | list) -> None:
        self.buffer.write(np.asarray(arr, dtype=np.int32).tobytes())

    def write_uint32_array(self, arr: NDArray | list) -> None:
        self.buffer.write(np.asarray(arr, dtype=np.uint32).tobytes())

    def write_int64_array(self, arr: NDArray | list) -> None:
        self.buffer.write(np.asarray(arr, dtype=np.int64).tobytes())

    def write_uint64_array(self, arr: NDArray | list) -> None:
        self.buffer.write(np.asarray(arr, dtype=np.uint64).tobytes())

    # ─────────────────────────────────────────────────────────
    # Single Value Writes
    # ─────────────────────────────────────────────────────────

    def write_uint8(self, value: int) -> None:
        self.buffer.write(np.array([value], dtype=np.uint8).tobytes())

    def write_uint16(self, value: int) -> None:
        self.buffer.write(np.array([value], dtype=np.uint16).tobytes())

    def write_uint32(self, value: int) -> None:
        self.buffer.write(np.array([value], dtype=np.uint32).tobytes())

    def write_int32(self, value: int) -> None:
        self.buffer.write(np.array([value], dtype=np.int32).tobytes())

    def write_uint64(self, value: int) -> None:
        self.buffer.write(np.array([value], dtype=np.uint64).tobytes())

    def write_int64(self, value: int) -> None:
        self.buffer.write(np.array([value], dtype=np.int64).tobytes())

    # ─────────────────────────────────────────────────────────
    # Variable-Length Data
    # ─────────────────────────────────────────────────────────

    def write_bytes(self, data: bytes | memoryview) -> None:
        self.buffer.write(data)

    def write_string(self, s: str) -> None:
        self.buffer.write(s.encode('utf-8'))

    def write_zeros(self, n: int) -> None:
        self.buffer.write(b'\x00' * n)

    # ─────────────────────────────────────────────────────────
    # Navigation
    # ─────────────────────────────────────────────────────────

    def tell(self) -> int:
        return self.buffer.tell()

    def seek(self, pos: int) -> None:
        self.buffer.seek(pos)

    def getvalue(self) -> bytes:
        return self.buffer.getvalue()

    def getbuffer(self) -> memoryview:
        return self.buffer.getbuffer()

    def __len__(self) -> int:
        return self.buffer.tell()

    # ─────────────────────────────────────────────────────────
    # Deferred Writes
    # ─────────────────────────────────────────────────────────

    def reserve_uint32(self) -> int:
        """Reserve 4 bytes, return position to fill later."""
        pos = self.buffer.tell()
        self.buffer.write(b'\x00\x00\x00\x00')
        return pos

    def reserve_uint64(self) -> int:
        """Reserve 8 bytes, return position to fill later."""
        pos = self.buffer.tell()
        self.buffer.write(b'\x00\x00\x00\x00\x00\x00\x00\x00')
        return pos

    def fill_uint32(self, pos: int, value: int) -> None:
        """Fill a previously reserved uint32."""
        current = self.buffer.tell()
        self.buffer.seek(pos)
        self.buffer.write(np.array([value], dtype=np.uint32).tobytes())
        self.buffer.seek(current)

    def fill_uint64(self, pos: int, value: int) -> None:
        """Fill a previously reserved uint64."""
        current = self.buffer.tell()
        self.buffer.seek(pos)
        self.buffer.write(np.array([value], dtype=np.uint64).tobytes())
        self.buffer.seek(current)

    # ─────────────────────────────────────────────────────────
    # High-Level Patterns
    # ─────────────────────────────────────────────────────────

    def write_with_offsets(
            self,
            items: list[bytes],
    ) -> tuple[NDArray[np.uint32], int]:
        """
        Write variable-length items, return offsets array and total size.

        Returns:
            offsets: Array of start offsets for each item
            total_size: Total bytes written
        """
        offsets = []
        offset = 0

        for item in items:
            offsets.append(offset)
            offset += len(item)

        # Write offsets
        offsets_arr = np.array(offsets, dtype=np.uint32)
        self.buffer.write(offsets_arr.tobytes())

        # Write data
        for item in items:
            self.buffer.write(item)

        return offsets_arr, offset