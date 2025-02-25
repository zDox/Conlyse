from dataclasses import dataclass
from math import ceil

from conflict_interface.data_types.point import Point


@dataclass
class Rect:
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0

    def get_location(self):
        return Point(self.x, self.y)

    def init(self, b, a, c, e):
        self.x = b
        self.y = a
        self.width = c
        self.height = e
        return self

    def contains(self, point: Point):
        return not (
                point.x > self.x + self.width
                or point.x < self.x
                or point.y > self.y + self.height
                or point.y < self.y
            )

    def to_integer_values(self):
        b = self.x + self.width
        a = self.y + self.height

        self.x >>= 0
        self.y >>= 0

        self.height = ceil(self.height)
        self.width = ceil(self.width)

        if b > self.x + self.width:
            self.width += 1
        if a > self.y + self.height:
            self.height += 1

    def intersection(self, other):
        a = max(self.x, other.x)
        c = min(self.x + self.width, other.x + other.width)
        if a <= c:
            e = max(self.y, other.y)
            b = min(self.y + self.height, other.y + other.height)
            if e <= b:
                return Rect(a, e, c - a, b - e)

    def difference(self, b):
        if b.width <= 0 or b.height <= 0 or not self.intersects(b):
            return [self]
        a = []
        c = self.y
        e = self.height
        d = self.x + self.width
        g = self.y + self.height
        h = b.x + b.width
        f = b.y + b.height
        if b.y > self.y:
            a.append(Rect(self.x, self.y, self.width, b.y - self.y))
            c = b.y
            e -= b.y - self.y
        if f < g:
            a.append(Rect(self.x, f, self.width, g - f))
            e = f - c
        if b.x > self.x:
            a.append(Rect(self.x, c, b.x - self.x, e))
        if h < d:
            a.append(Rect(h, c, d - h, e))
        return a

    def intersects(self, other):
        return not (
                other.x > self.x + self.width
                or other.x + other.width < self.x
                or other.y > self.y + self.height
                or other.y + other.height < self.y
            )

    def union(self, other):
        if other:
            if self.width == 0 or self.height == 0:
                self.set_rect(other)
            elif other.width > 0 and other.height > 0:
                a = max(self.x + self.width, other.x + other.width)
                c = max(self.y + self.height, other.y + other.height)
                self.x = min(self.x, other.x)
                self.y = min(self.y, other.y)
                self.width = a - self.x
                self.height = c - self.y
        return self

    def set_rect(self, other):
        self.x = other.x
        self.y = other.y
        self.width = other.width
        self.height = other.height
        return self

    def reset(self):
        self.x = self.y = self.width = self.height = 0
        return self

    def clone(self):
        b = Rect()
        b.set_rect(self)
        return b

    def add_point(self, b, a):
        if self.x == 0 and self.width == 0:
            self.x = b
        elif b < self.x:
            self.width += self.x - b
            self.x = b
        elif b > self.x + self.width:
            self.width = b - self.x
        if self.y == 0 and self.height == 0:
            self.y = a
        elif a < self.y:
            self.height += self.y - a
            self.y = a
        elif a > self.y + self.height:
            self.height = a - self.y
        return self

    def pad(self, b, a):
        self.x -= b
        self.y -= a
        self.width += b + b
        self.height += a + a
        return self

    def equals(self, other):
        if other:
            return self.x == other.x \
                    and self.y == other.y \
                    and self.width == other.width \
                    and self.height == other.height
        return False

    def scale(self, x_scale, y_scale=None):
        if y_scale is None:
            x_scale = y_scale
        self.x *= x_scale
        self.y *= y_scale
        self.width *= x_scale
        self.height *= y_scale
        return self

    def translate(self, x_translation=0, y_translation=0):
        self.x += x_translation
        self.y += y_translation
        return self

    def get_center(self):
        return Point(self.x + self.width / 2, self.y + self.height / 2)

    def is_empty(self):
        return self.width <= 0 or self.height <= 0
