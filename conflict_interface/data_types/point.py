from dataclasses import dataclass
from math import sqrt, atan2
from copy import deepcopy

from conflict_interface.data_types.game_object import GameObject


@dataclass
class Point(GameObject):
    x: float
    y: float

    MAPPING = {
        "x": "x",
        "y": "y",
    }

    def get_x(self):
        return self.x

    def get_y(self):
        return self.y

    @staticmethod
    def distance(point1, point2):
        dx = point1.x - point2.x
        dy = point1.y - point2.y
        return sqrt(dx**2 + dy**2)

    @staticmethod
    def angle_between(point1, point2):
        return atan2(point2.y - point1.y, point2.x - point1.x)

    @staticmethod
    def direction_vector(point1, point2):
        if point1 and point2:
            if point1 == point2:
                return Point(1, 0)
            else:
                direction = Point(point2.x - point1.x, point2.y - point1.y)
                return direction.normalize(1)
        return None

    @staticmethod
    def has_same_direction(point1, point2):
        if point1 and point2:
            epsilon = 5E-4
            angle_diff = abs(atan2(point1.x, point1.y)
                             -
                             atan2(point2.x, point2.y))
            return angle_diff < epsilon
        return False

    @classmethod
    def to_point(cls, point):
        if point:
            if isinstance(point, cls):
                return point
            elif isinstance(point.x, (int, float)) \
                    and isinstance(point.y, (int, float)):
                return cls(point.x, point.y)
            elif isinstance(point.x, str):
                try:
                    x = float(point.x)
                    y = float(point.y)
                    return cls(x, y)
                except ValueError:
                    pass
        return None

    def translate(self, dx=0, dy=0):
        self.x += dx
        self.y += dy
        return self

    def add(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def subtract(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def multiply(self, other):
        return Point(self.x * other.x, self.y * other.y)

    def divide(self, other):
        return Point(self.x / other.x, self.y / other.y)

    def dot(self, other):
        return self.x * other.x + self.y * other.y

    def scale(self, factor):
        self.x *= factor
        self.y *= factor

    def get_distance(self, other, use_squared=False):
        distance_sq = self.get_distance_sq(other.x, other.y)
        return distance_sq if use_squared else sqrt(distance_sq)

    def get_distance_sq(self, x, y):
        dx = x - self.x
        dy = y - self.y
        return dx**2 + dy**2

    def get_length(self, squared=False):
        length_sq = self.x**2 + self.y**2
        return length_sq if squared else sqrt(length_sq)

    def get_long_axis_movement(self):
        return max(self.x, self.y)

    def normalize(self, length=1):
        current_length = self.get_length()
        factor = length / current_length if current_length != 0 else 0
        return Point(self.x * factor, self.y * factor)

    def point_dist_sq(self, x, y):
        return (self.x - x)**2 + (self.y - y)**2

    def line_dist_sq(self, x1, y1, x2, y2):
        dx = self.x - x1
        dy = self.y - y1
        line_length_sq = (x2 - x1)**2 + (y2 - y1)**2
        t = max(0, min(1, (dx * (x2 - x1) + dy * (y2 - y1)) / line_length_sq))
        projection_x = x1 + t * (x2 - x1)
        projection_y = y1 + t * (y2 - y1)
        return self.get_distance_sq(projection_x, projection_y)

    def line_dist(self, x1, y1, x2, y2):
        return sqrt(self.line_dist_sq(x1, y1, x2, y2))

    def closest_line_point(self, x1, y1, x2, y2):
        result = Point(0, 0)
        if x1 == x2 and y1 == y2:
            result.x, result.y = x1, y1
            return result

        if x1 == x2:
            result.x, result.y = x1, self.y
        elif y1 == y2:
            result.x, result.y = self.x, y1
        else:
            slope = (y2 - y1) / (x2 - x1)
            perpendicular_slope = -1 / slope
            perpendicular_intercept = (-1 * perpendicular_slope * self.x +
                                       (self.y - y1 + slope * x1)
                                       /
                                       (slope - perpendicular_slope))
            result.x = perpendicular_intercept
            result.y = slope * (perpendicular_intercept - x1) + y1

        if 0.1 < result.line_dist(x1, y1, x2, y2):
            if result.point_dist_sq(x1, y1) < result.point_dist_sq(x2, y2):
                result.x, result.y = x1, y1
            else:
                result.x, result.y = x2, y2

        return result

    def equals(self, other):
        return other and isinstance(other, Point) \
            and self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))

    def set_location(self, other):
        self.x = other.x
        self.y = other.y

    def to_integer_values(self):
        self.x = int(self.x + 0.5)
        self.y = int(self.y + 0.5)
        return self

    def to_string(self):
        return "[{0},{1}]".format(self.x, self.y)

    def to_reference_system(self, reference_width):
        raise NotImplementedError()

    def get_closest_equivalent(self, other, threshold):
        raise NotImplementedError()

    def cache_key(self):
        return "{},{}".format(int(10 * self.x), int(10 * self.y))

    def clone(self):
        return deepcopy(self)
