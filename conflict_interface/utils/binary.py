from __future__ import annotations

import struct
from io import BytesIO
from typing import TypeVar

T = TypeVar('T')


class BinaryReader:
    """
    Binary reader using struct and memoryview for efficient I/O.

    Uses zero-copy memoryview for data access and struct for parsing.
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
    # Single Value Reads
    # ─────────────────────────────────────────────────────────

    def read_uint8(self) -> int:
        result = self.data[self.pos]
        self.pos += 1
        return result

    def read_int8(self) -> int:
        result = struct.unpack_from('b', self.data, self.pos)[0]
        self.pos += 1
        return result

    def read_uint16(self) -> int:
        result = struct.unpack_from('<H', self.data, self.pos)[0]
        self.pos += 2
        return result

    def read_int16(self) -> int:
        result = struct.unpack_from('<h', self.data, self.pos)[0]
        self.pos += 2
        return result

    def read_uint32(self) -> int:
        result = struct.unpack_from('<I', self.data, self.pos)[0]
        self.pos += 4
        return result

    def read_int32(self) -> int:
        result = struct.unpack_from('<i', self.data, self.pos)[0]
        self.pos += 4
        return result

    def read_uint64(self) -> int:
        result = struct.unpack_from('<Q', self.data, self.pos)[0]
        self.pos += 8
        return result

    def read_int64(self) -> int:
        result = struct.unpack_from('<q', self.data, self.pos)[0]
        self.pos += 8
        return result

    def read_float(self) -> float:
        result = struct.unpack_from('<f', self.data, self.pos)[0]
        self.pos += 4
        return result

    def read_double(self) -> float:
        result = struct.unpack_from('<d', self.data, self.pos)[0]
        self.pos += 8
        return result

    # ─────────────────────────────────────────────────────────
    # Array Reads
    # ─────────────────────────────────────────────────────────

    def read_uint8_array(self, count: int) -> list[int]:
        result = list(self.data[self.pos:self.pos + count])
        self.pos += count
        return result

    def read_int8_array(self, count: int) -> list[int]:
        result = list(struct.unpack_from(f'{count}b', self.data, self.pos))
        self.pos += count
        return result

    def read_uint16_array(self, count: int) -> list[int]:
        result = list(struct.unpack_from(f'<{count}H', self.data, self.pos))
        self.pos += count * 2
        return result

    def read_int16_array(self, count: int) -> list[int]:
        result = list(struct.unpack_from(f'<{count}h', self.data, self.pos))
        self.pos += count * 2
        return result

    def read_uint32_array(self, count: int) -> list[int]:
        result = list(struct.unpack_from(f'<{count}I', self.data, self.pos))
        self.pos += count * 4
        return result

    def read_int32_array(self, count: int) -> list[int]:
        result = list(struct.unpack_from(f'<{count}i', self.data, self.pos))
        self.pos += count * 4
        return result

    def read_uint64_array(self, count: int) -> list[int]:
        result = list(struct.unpack_from(f'<{count}Q', self.data, self.pos))
        self.pos += count * 8
        return result

    def read_int64_array(self, count: int) -> list[int]:
        result = list(struct.unpack_from(f'<{count}q', self.data, self.pos))
        self.pos += count * 8
        return result

    def read_float_array(self, count: int) -> list[float]:
        result = list(struct.unpack_from(f'<{count}f', self.data, self.pos))
        self.pos += count * 4
        return result

    def read_double_array(self, count: int) -> list[float]:
        result = list(struct.unpack_from(f'<{count}d', self.data, self.pos))
        self.pos += count * 8
        return result

    # ─────────────────────────────────────────────────────────
    # Structured Reads
    # ─────────────────────────────────────────────────────────

    def read_struct(self, fmt: str) -> tuple:
        """
        Read structured data using format string.

        Example: read_struct('<IHH') reads uint32, uint16, uint16
        """
        size = struct.calcsize(fmt)
        result = struct.unpack_from(fmt, self.data, self.pos)
        self.pos += size
        return result

    def read_struct_into(self, fmt: str, buffer: bytearray, offset: int = 0) -> None:
        """Read structured data directly into a buffer."""
        size = struct.calcsize(fmt)
        struct.unpack_from(fmt, self.data, self.pos)
        buffer[offset:offset + size] = self.data[self.pos:self.pos + size]
        self.pos += size

    # ─────────────────────────────────────────────────────────
    # Variable-Length Data
    # ─────────────────────────────────────────────────────────

    def read_bytes(self, size: int) -> bytes:
        """Read bytes (creates a copy)."""
        result = bytes(self.data[self.pos:self.pos + size])
        self.pos += size
        return result

    def read_bytes_view(self, size: int) -> memoryview:
        """Read bytes without copying (returns view)."""
        result = self.data[self.pos:self.pos + size]
        self.pos += size
        return result

    def read_string(self, size: int, encoding: str = 'utf-8') -> str:
        """Read a fixed-size string."""
        data = self.data[self.pos:self.pos + size]
        self.pos += size
        return bytes(data).decode(encoding)

    def read_cstring(self, encoding: str = 'utf-8') -> str:
        """Read a null-terminated string."""
        start = self.pos
        while self.pos < self.size and self.data[self.pos] != 0:
            self.pos += 1
        result = bytes(self.data[start:self.pos]).decode(encoding)
        self.pos += 1  # skip null terminator
        return result

    # ─────────────────────────────────────────────────────────
    # Navigation
    # ─────────────────────────────────────────────────────────

    def skip(self, n: int) -> None:
        """Skip n bytes forward."""
        self.pos += n

    def seek(self, pos: int) -> None:
        """Seek to absolute position."""
        self.pos = pos

    def tell(self) -> int:
        """Return current position."""
        return self.pos

    def remaining(self) -> int:
        """Return number of bytes remaining."""
        return self.size - self.pos

    def at_end(self) -> bool:
        """Check if at end of data."""
        return self.pos >= self.size

    def align(self, alignment: int) -> None:
        """Align position to next multiple of alignment."""
        remainder = self.pos % alignment
        if remainder:
            self.pos += alignment - remainder

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
            offsets: list[int],
            total_size: int
    ) -> list[memoryview]:
        """
        Read variable-length items given their offsets.
        Returns list of memoryview slices.
        """
        items = []
        data_start = self.pos

        for i in range(len(offsets)):
            start = offsets[i]
            end = offsets[i + 1] if i + 1 < len(offsets) else total_size
            items.append(self.data[data_start + start:data_start + end])

        self.pos += total_size
        return items


class BinaryWriter:
    """
    Binary writer using struct for efficient serialization.

    Supports deferred writes for filling in sizes/offsets later.
    """

    __slots__ = ('buffer',)

    def __init__(self):
        self.buffer = BytesIO()

    # ─────────────────────────────────────────────────────────
    # Single Value Writes
    # ─────────────────────────────────────────────────────────

    def write_uint8(self, value: int) -> None:
        self.buffer.write(struct.pack('B', value))

    def write_int8(self, value: int) -> None:
        self.buffer.write(struct.pack('b', value))

    def write_uint16(self, value: int) -> None:
        self.buffer.write(struct.pack('<H', value))

    def write_int16(self, value: int) -> None:
        self.buffer.write(struct.pack('<h', value))

    def write_uint32(self, value: int) -> None:
        self.buffer.write(struct.pack('<I', value))

    def write_int32(self, value: int) -> None:
        self.buffer.write(struct.pack('<i', value))

    def write_uint64(self, value: int) -> None:
        self.buffer.write(struct.pack('<Q', value))

    def write_int64(self, value: int) -> None:
        self.buffer.write(struct.pack('<q', value))

    def write_float(self, value: float) -> None:
        self.buffer.write(struct.pack('<f', value))

    def write_double(self, value: float) -> None:
        self.buffer.write(struct.pack('<d', value))

    # ─────────────────────────────────────────────────────────
    # Array Writes
    # ─────────────────────────────────────────────────────────

    def write_uint8_array(self, arr: list[int] | bytes) -> None:
        if isinstance(arr, bytes):
            self.buffer.write(arr)
        else:
            self.buffer.write(struct.pack(f'{len(arr)}B', *arr))

    def write_int8_array(self, arr: list[int]) -> None:
        self.buffer.write(struct.pack(f'{len(arr)}b', *arr))

    def write_uint16_array(self, arr: list[int]) -> None:
        self.buffer.write(struct.pack(f'<{len(arr)}H', *arr))

    def write_int16_array(self, arr: list[int]) -> None:
        self.buffer.write(struct.pack(f'<{len(arr)}h', *arr))

    def write_uint32_array(self, arr: list[int]) -> None:
        self.buffer.write(struct.pack(f'<{len(arr)}I', *arr))

    def write_int32_array(self, arr: list[int]) -> None:
        self.buffer.write(struct.pack(f'<{len(arr)}i', *arr))

    def write_uint64_array(self, arr: list[int]) -> None:
        self.buffer.write(struct.pack(f'<{len(arr)}Q', *arr))

    def write_int64_array(self, arr: list[int]) -> None:
        self.buffer.write(struct.pack(f'<{len(arr)}q', *arr))

    def write_float_array(self, arr: list[float]) -> None:
        self.buffer.write(struct.pack(f'<{len(arr)}f', *arr))

    def write_double_array(self, arr: list[float]) -> None:
        self.buffer.write(struct.pack(f'<{len(arr)}d', *arr))

    # ─────────────────────────────────────────────────────────
    # Structured Writes
    # ─────────────────────────────────────────────────────────

    def write_struct(self, fmt: str, *values) -> None:
        """
        Write structured data using format string.

        Example: write_struct('<IHH', 42, 10, 20)
        """
        self.buffer.write(struct.pack(fmt, *values))

    # ─────────────────────────────────────────────────────────
    # Variable-Length Data
    # ─────────────────────────────────────────────────────────

    def write_bytes(self, data: bytes | memoryview) -> None:
        """Write raw bytes."""
        self.buffer.write(data)

    def write_string(self, s: str, encoding: str = 'utf-8') -> None:
        """Write a string (without length prefix or null terminator)."""
        self.buffer.write(s.encode(encoding))

    def write_cstring(self, s: str, encoding: str = 'utf-8') -> None:
        """Write a null-terminated string."""
        self.buffer.write(s.encode(encoding))
        self.buffer.write(b'\x00')

    def write_zeros(self, n: int) -> None:
        """Write n zero bytes."""
        self.buffer.write(b'\x00' * n)

    def write_padding(self, alignment: int) -> None:
        """Write padding bytes to align to next multiple of alignment."""
        pos = self.buffer.tell()
        remainder = pos % alignment
        if remainder:
            self.write_zeros(alignment - remainder)

    # ─────────────────────────────────────────────────────────
    # Navigation
    # ─────────────────────────────────────────────────────────

    def tell(self) -> int:
        """Return current write position."""
        return self.buffer.tell()

    def seek(self, pos: int) -> None:
        """Seek to absolute position."""
        self.buffer.seek(pos)

    def getvalue(self) -> bytes:
        """Get the complete buffer as bytes."""
        return self.buffer.getvalue()

    def getbuffer(self) -> memoryview:
        """Get a memoryview of the buffer."""
        return self.buffer.getbuffer()

    def __len__(self) -> int:
        """Return current size of buffer."""
        return self.buffer.tell()

    # ─────────────────────────────────────────────────────────
    # Deferred Writes
    # ─────────────────────────────────────────────────────────

    def reserve_uint8(self) -> int:
        """Reserve 1 byte, return position to fill later."""
        pos = self.buffer.tell()
        self.buffer.write(b'\x00')
        return pos

    def reserve_uint16(self) -> int:
        """Reserve 2 bytes, return position to fill later."""
        pos = self.buffer.tell()
        self.buffer.write(b'\x00\x00')
        return pos

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

    def fill_uint8(self, pos: int, value: int) -> None:
        """Fill a previously reserved uint8."""
        current = self.buffer.tell()
        self.buffer.seek(pos)
        self.buffer.write(struct.pack('B', value))
        self.buffer.seek(current)

    def fill_uint16(self, pos: int, value: int) -> None:
        """Fill a previously reserved uint16."""
        current = self.buffer.tell()
        self.buffer.seek(pos)
        self.buffer.write(struct.pack('<H', value))
        self.buffer.seek(current)

    def fill_uint32(self, pos: int, value: int) -> None:
        """Fill a previously reserved uint32."""
        current = self.buffer.tell()
        self.buffer.seek(pos)
        self.buffer.write(struct.pack('<I', value))
        self.buffer.seek(current)

    def fill_uint64(self, pos: int, value: int) -> None:
        """Fill a previously reserved uint64."""
        current = self.buffer.tell()
        self.buffer.seek(pos)
        self.buffer.write(struct.pack('<Q', value))
        self.buffer.seek(current)

    # ─────────────────────────────────────────────────────────
    # High-Level Patterns
    # ─────────────────────────────────────────────────────────

    def write_with_offsets(
            self,
            items: list[bytes],
    ) -> tuple[list[int], int]:
        """
        Write variable-length items, return offsets array and total size.

        Returns:
            offsets: List of start offsets for each item
            total_size: Total bytes written
        """
        offsets = []
        offset = 0

        # Calculate offsets
        for item in items:
            offsets.append(offset)
            offset += len(item)

        # Write offsets
        self.write_uint32_array(offsets)

        # Write data
        for item in items:
            self.buffer.write(item)

        return offsets, offset