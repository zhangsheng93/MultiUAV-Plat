from __future__ import annotations

import uuid
from math import sqrt
from collections.abc import Iterable, Mapping, Sequence
from typing import Tuple

from shapely.geometry import LineString, Point, Polygon
from shapely.validation import explain_validity


def _coerce_point(point: Iterable[float] | Mapping[str, float]) -> Tuple[float, ...]:
    """Convert a point representation into a tuple of floats.

    Supports:
    - Mappings containing 'x'/'y' keys and optional 'z'
    - Sequences/iterables of numeric coordinates
    """
    if isinstance(point, Mapping):
        if "x" not in point or "y" not in point:
            raise ValueError("Point mappings must include at least 'x' and 'y' keys.")
        coords = [
            float(point["x"]),
            float(point["y"]),
        ]
        if "z" in point:
            coords.append(float(point["z"]))
        return tuple(coords)

    if isinstance(point, Sequence) and not isinstance(point, (str, bytes)):
        return tuple(float(value) for value in point)

    if isinstance(point, Iterable):
        return tuple(float(value) for value in point)

    raise TypeError(f"Unsupported point type: {type(point)!r}")


def distance(
    point_a: Iterable[float] | Mapping[str, float],
    point_b: Iterable[float] | Mapping[str, float],
) -> float:
    """Return the Euclidean distance between two points."""
    coords_a = _coerce_point(point_a)
    coords_b = _coerce_point(point_b)

    if not coords_a or not coords_b:
        raise ValueError("Points must contain at least one coordinate.")

    max_dim = max(len(coords_a), len(coords_b))

    def _pad(coords: Tuple[float, ...]) -> Tuple[float, ...]:
        if len(coords) == max_dim:
            return coords
        return coords + (0.0,) * (max_dim - len(coords))

    padded_a = _pad(coords_a)
    padded_b = _pad(coords_b)

    return sqrt(sum((a - b) ** 2 for a, b in zip(padded_a, padded_b)))


def distance_2d(
    point_a: Iterable[float] | Mapping[str, float],
    point_b: Iterable[float] | Mapping[str, float],
) -> float:
    """Return the 2D Euclidean distance between two points (X,Y coordinates only, ignoring Z).

    This function is useful for horizontal distance calculations where altitude should be ignored,
    such as drone perception radius checks.

    Args:
        point_a: First point as dict with 'x','y' keys or iterable of coordinates
        point_b: Second point as dict with 'x','y' keys or iterable of coordinates

    Returns:
        The 2D Euclidean distance between the two points

    Example:
        >>> distance_2d({'x': 0, 'y': 0, 'z': 100}, {'x': 3, 'y': 4, 'z': 200})
        5.0  # Only considers x,y; ignores z difference
    """
    coords_a = _coerce_point(point_a)
    coords_b = _coerce_point(point_b)

    if not coords_a or not coords_b:
        raise ValueError("Points must contain at least one coordinate.")

    # Only use first 2 dimensions (X, Y)
    x1, y1 = coords_a[0], coords_a[1] if len(coords_a) > 1 else 0.0
    x2, y2 = coords_b[0], coords_b[1] if len(coords_b) > 1 else 0.0

    return sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def point_to_line_distance(
    point: Mapping[str, float],
    line_start: Mapping[str, float],
    line_end: Mapping[str, float],
) -> float:
    """Return the shortest distance between a point and a line segment."""
    x0, y0 = float(point["x"]), float(point["y"])
    x1, y1 = float(line_start["x"]), float(line_start["y"])
    x2, y2 = float(line_end["x"]), float(line_end["y"])

    line = LineString([(x1, y1), (x2, y2)])
    return line.distance(Point(x0, y0))


def is_point_in_polygon(px: float, py: float, vertices: Sequence[Mapping[str, float]]) -> bool:
    """Return True when the 2D point lies inside the given polygon vertices."""
    if len(vertices) < 3:
        return False

    inside = False
    j = len(vertices) - 1
    for i, vertex in enumerate(vertices):
        xi = float(vertex["x"])
        yi = float(vertex["y"])
        xj = float(vertices[j]["x"])
        yj = float(vertices[j]["y"])

        intersects = ((yi > py) != (yj > py)) and (
            px
            < (xj - xi) * (py - yi) / (yj - yi + 1e-9) + xi
        )
        if intersects:
            inside = not inside
        j = i

    return inside


def polygon_area(vertices: Sequence[Mapping[str, float]]) -> float:
    """Return the area of a simple polygon defined by vertices."""
    if len(vertices) < 3:
        return 0.0

    area = 0.0
    for i in range(len(vertices)):
        j = (i + 1) % len(vertices)
        xi = float(vertices[i]["x"])
        yi = float(vertices[i]["y"])
        xj = float(vertices[j]["x"])
        yj = float(vertices[j]["y"])
        area += xi * yj - xj * yi

    return abs(area) / 2.0


def validate_polygon_vertices(vertices: Sequence[Mapping[str, float]]) -> Tuple[bool, str]:
    """Validate if the given vertices form a valid polygon using Shapely.

    Checks:
    1. At least 3 vertices.
    2. Valid polygon construction (no self-intersection, etc.).
    3. Non-zero area.

    Args:
        vertices: Sequence of points (mappings with 'x' and 'y')

    Returns:
        Tuple (is_valid, reason_message)
    """
    if not vertices or len(vertices) < 3:
        return False, "Polygon must have at least 3 vertices"

    try:
        # Extract coords
        coords = []
        for v in vertices:
            if "x" not in v or "y" not in v:
                return False, "All vertices must have 'x' and 'y' coordinates"
            coords.append((float(v["x"]), float(v["y"])))

        # Create polygon
        poly = Polygon(coords)

        if not poly.is_valid:
            return False, f"Invalid polygon: {explain_validity(poly)}"

        if poly.area <= 1e-9:  # Allow for floating point epsilon
            return False, "Polygon must have non-zero area"

        return True, "Valid polygon"
    except Exception as e:
        return False, f"Error validating polygon: {str(e)}"


def normalize_polygon_vertices(vertices: Sequence[Mapping[str, float]]) -> List[Dict[str, float]]:
    """Remove the last vertex if it is identical to the first one (closed polygon representation).

    Args:
        vertices: Sequence of points (mappings with 'x' and 'y')

    Returns:
        A new list of vertices with the redundant last point removed if applicable.
    """
    if not vertices or len(vertices) < 2:
        return [dict(v) for v in vertices]

    v_list = [dict(v) for v in vertices]
    first = v_list[0]
    last = v_list[-1]

    # Check if first and last points are the same (x and y)
    if (abs(float(first.get("x", 0)) - float(last.get("x", 0))) < 1e-9 and
        abs(float(first.get("y", 0)) - float(last.get("y", 0))) < 1e-9):
        return v_list[:-1]

    return v_list


def generate_random_id(length: int = 8) -> str:
    """Return a short random identifier composed of hexadecimal characters."""
    if length <= 0:
        raise ValueError("length must be positive")

    # Concatenate UUID4 hex chunks until we have enough characters.
    identifier = ""
    while len(identifier) < length:
        identifier += uuid.uuid4().hex

    return identifier[:length]
