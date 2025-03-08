import base64
from collections import defaultdict
from typing import Union

from conflict_interface.data_types.point import Point


def int_from_bytes(data: bytes, start: int, end: int) -> int:
    result = 0
    for i in range(start, end):
        result = (result << 8) + data[i]
    return result


def decode_base64(data: str) -> bytes:
    key_str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
    data = data.rstrip('=')
    decoded_bytes = bytearray()

    for i in range(0, len(data), 4):
        e = key_str.index(data[i])
        k = key_str.index(data[i + 1])
        f = key_str.index(data[i + 2]) if i + 2 < len(data) else 64
        l = key_str.index(data[i + 3]) if i + 3 < len(data) else 64

        byte1 = (e << 2) | (k >> 4)
        byte2 = ((k & 15) << 4) | (f >> 2) if f != 64 else None
        byte3 = ((f & 3) << 6) | l if l != 64 else None

        decoded_bytes.append(byte1)
        if byte2 is not None:
            decoded_bytes.append(byte2)
        if byte3 is not None:
            decoded_bytes.append(byte3)

    return bytes(decoded_bytes)


def decode_border(data: str) -> list[Point]:
    decoded_data = decode_base64(data)
    points = []
    for i in range(0, len(decoded_data), 4):
        x = int_from_bytes(decoded_data, i, i + 2)
        y = int_from_bytes(decoded_data, i + 2, i + 4)
        points.append(Point(x, y))

    return points


def decode_connections(encoded_str: str) -> list[dict[str, Union[int, Point]]]:
    decoded_bytes: bytes = base64.b64decode(encoded_str)
    connections: list[dict[str, Union[int, Point]]] = []

    for i in range(0, len(decoded_bytes), 20):
        p: int = int_from_bytes(decoded_bytes, i, i + 4)
        p1_x: float = int_from_bytes(decoded_bytes, i + 4, i + 8) / 100
        p1_y: float = int_from_bytes(decoded_bytes, i + 8, i + 12) / 100
        p2_x: float = int_from_bytes(decoded_bytes, i + 12, i + 16) / 100
        p2_y: float = int_from_bytes(decoded_bytes, i + 16, i + 20) / 100

        connection: dict[str, Union[int, Point]] = {
            "province": p,
            "p1": Point(p1_x, p1_y),
            "p2": Point(p2_x, p2_y)
        }
        connections.append(connection)

    return connections


def graph(connections: list[dict[str, Union[int, Point]]]) -> (
        tuple)[dict[Point, list[Point]], dict[int, list[Point]], dict[Point, int]]:

    adjacency_list = defaultdict(list)
    province_to_point: dict[int, list[Point]] = {}
    point_to_province: dict[Point, int] = {}

    for connection in connections:
        p1 = connection["p1"]
        p2 = connection["p2"]
        province = connection["province"]

        adjacency_list[p1].append(p2)
        adjacency_list[p2].append(p1)

        # add p1,p2 to province_to_point
        if province not in province_to_point:
            province_to_point[province] = []
        province_to_point[province].append(p1)
        province_to_point[province].append(p2)


        point_to_province[p1] = province
        point_to_province[p2] = province

    return adjacency_list, province_to_point, point_to_province

