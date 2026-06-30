import pytest
import sys
import math
from pathlib import Path
from shapely.geometry import LineString, Point, Polygon

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from path_planning.path_finder import find_path


def test_no_obstacles_returns_straight_line():
    path = find_path((0, 0), (10, 10))
    assert path == [(0, 0), (10, 10)]


def test_more_waypoints_straight_line_adds_midpoint():
    path = find_path((0, 0), (10, 0), more_waypoints=True)
    assert path == [(0, 0), (5, 0), (10, 0)]


def test_none_obstacles_returns_straight_line():
    path = find_path((0, 0), (5, 5), known_obstacles=None)
    assert path == [(0, 0), (5, 5)]


def test_empty_obstacles_returns_straight_line():
    path = find_path((0, 0), (5, 5), known_obstacles=[])
    assert path == [(0, 0), (5, 5)]


def test_more_waypoints_empty_obstacles_adds_midpoint():
    path = find_path((0, 0), (6, 8), known_obstacles=[], more_waypoints=True)
    assert path == [(0, 0), (3, 4), (6, 8)]


def test_obstacle_not_blocking_returns_straight_line():
    obstacle = [(20, 20), (22, 20), (22, 22), (20, 22)]
    path = find_path((0, 0), (10, 10), known_obstacles=[obstacle])
    assert path == [(0, 0), (10, 10)]


def test_point_obstacle_avoidance():
    path = find_path((0, 5), (10, 5), known_obstacles=[(5, 5)])
    assert len(path) > 2
    assert path[0] == (0, 5)
    assert path[-1] == (10, 5)
    for pt in path[1:-1]:
        assert math.hypot(pt[0] - 5, pt[1] - 5) > 0.3


def test_circle_obstacle_avoidance():
    path = find_path((0, 5), (10, 5), known_obstacles=[(5, 5, 2)])
    assert len(path) > 2
    assert path[0] == (0, 5)
    assert path[-1] == (10, 5)
    for pt in path[1:-1]:
        assert math.hypot(pt[0] - 5, pt[1] - 5) > 1.8


def test_polygon_obstacle_avoidance():
    obstacle = [(3, 3), (7, 3), (7, 7), (3, 7)]
    path = find_path((0, 5), (10, 5), known_obstacles=[obstacle])
    assert len(path) > 2
    assert path[0] == (0, 5)
    assert path[-1] == (10, 5)
    obs_poly = Polygon(obstacle)
    for pt in path[1:-1]:
        assert not obs_poly.contains(Point(pt))


def test_more_waypoints_obstacle_detour_adds_midpoints_to_default_path():
    obstacle = [(3, 3), (7, 3), (7, 7), (3, 7)]
    default_path = find_path((0, 5), (10, 5), known_obstacles=[obstacle])
    expanded_path = find_path(
        (0, 5), (10, 5), known_obstacles=[obstacle], more_waypoints=True
    )

    assert expanded_path[0] == (0, 5)
    assert expanded_path[-1] == (10, 5)
    assert len(expanded_path) == len(default_path) * 2 - 1
    assert len(expanded_path) > len(default_path)

    expected_path = [default_path[0]]
    for p1, p2 in zip(default_path, default_path[1:]):
        expected_path.append(((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2))
        expected_path.append(p2)
    assert expanded_path == expected_path


def test_mixed_obstacle_types():
    obstacles = [
        (5, 5, 1),
        (8, 2),
        [(2, 7), (4, 7), (4, 9), (2, 9)]
    ]
    path = find_path((0, 0), (10, 10), known_obstacles=obstacles)
    assert len(path) >= 2
    assert path[0] == (0, 0)
    assert path[-1] == (10, 10)
    path_line = LineString(path)
    for obs in obstacles:
        if isinstance(obs, tuple) and len(obs) == 3:
            shape = Point(obs[0], obs[1]).buffer(obs[2])
        elif isinstance(obs, tuple) and len(obs) == 2:
            shape = Point(obs[0], obs[1]).buffer(0.5)
        else:
            shape = Polygon(obs)
        buffered = shape.buffer(0.05)
        interior = path_line.intersection(buffered)
        assert _geom_length_safe(interior) < 0.5


def _geom_length_safe(geom):
    if geom.is_empty:
        return 0.0
    if geom.geom_type in ('Point', 'MultiPoint'):
        return 0.0
    if hasattr(geom, 'length'):
        return geom.length
    if geom.geom_type == 'GeometryCollection':
        return sum(_geom_length_safe(g) for g in geom.geoms)
    return 0.0


def test_path_does_not_cross_obstacle():
    obstacle = [(4, 2), (6, 2), (6, 8), (4, 8)]
    path = find_path((0, 5), (10, 5), known_obstacles=[obstacle])
    path_line = LineString(path)
    obs_shape = Polygon(obstacle).buffer(0.05)
    intersection = path_line.intersection(obs_shape)
    assert _geom_length_safe(intersection) < 0.5


def test_start_inside_obstacle_raises():
    obstacle = [(0, 0), (10, 0), (10, 10), (0, 10)]
    with pytest.raises(ValueError, match="Start point"):
        find_path((5, 5), (20, 20), known_obstacles=[obstacle])


def test_destination_inside_obstacle_raises():
    obstacle = [(0, 0), (10, 0), (10, 10), (0, 10)]
    with pytest.raises(ValueError, match="Destination point"):
        find_point = find_path((-5, -5), (5, 5), known_obstacles=[obstacle])


def test_path_length_is_reasonable():
    obstacle = [(4, 2), (6, 2), (6, 8), (4, 8)]
    path = find_path((0, 5), (10, 5), known_obstacles=[obstacle])
    total_length = sum(
        math.hypot(path[i+1][0] - path[i][0], path[i+1][1] - path[i][1])
        for i in range(len(path) - 1)
    )
    assert total_length < 30


def test_multiple_obstacles_create_detour():
    obstacles = [
        (5, 3, 1),
        (5, 7, 1),
    ]
    path = find_path((0, 5), (10, 5), known_obstacles=obstacles)
    assert len(path) >= 2
    assert path[0] == (0, 5)
    assert path[-1] == (10, 5)


def test_api_circle_obstacle_dict_avoidance():
    obstacle = {
        "id": "obstacle-circle",
        "type": "circle",
        "position": {"x": 5.0, "y": 5.0, "z": 0.0},
        "radius": 2.0,
    }

    path = find_path((0, 5), (10, 5), known_obstacles=[obstacle])

    assert len(path) > 2
    assert path[0] == (0, 5)
    assert path[-1] == (10, 5)
    assert not LineString(path).crosses(Point(5, 5).buffer(2.0))


def test_blackboard_obstacle_entry_uses_facts():
    obstacle = {
        "id": "obstacle-poly",
        "category": "obstacle",
        "entity_type": "polygon",
        "facts": {
            "type": "polygon",
            "vertices": [
                {"x": 3.0, "y": 3.0},
                {"x": 7.0, "y": 3.0},
                {"x": 7.0, "y": 7.0},
                {"x": 3.0, "y": 7.0},
            ],
        },
    }

    path = find_path((0, 5), (10, 5), known_obstacles=[obstacle])

    assert len(path) > 2
    assert path[0] == (0, 5)
    assert path[-1] == (10, 5)
    assert not LineString(path).crosses(Polygon([(3, 3), (7, 3), (7, 7), (3, 7)]))


def test_blackboard_obstacle_entry_accepts_compact_position_tuple():
    obstacle = {
        "id": "obstacle-circle",
        "category": "obstacle",
        "entity_type": "circle",
        "facts": {
            "type": "circle",
            "position": (5.0, 5.0, 0.0),
            "radius": 2.0,
        },
    }

    path = find_path((0, 5), (10, 5), known_obstacles=[obstacle])

    assert len(path) > 2
    assert path[0] == (0, 5)
    assert path[-1] == (10, 5)
    assert not LineString(path).crosses(Point(5, 5).buffer(2.0))


def test_api_ellipse_obstacle_dict_avoidance():
    obstacle = {
        "id": "obstacle-ellipse",
        "type": "ellipse",
        "position": {"x": 5.0, "y": 5.0, "z": 0.0},
        "width": 2.0,
        "length": 1.0,
    }

    path = find_path((0, 5), (10, 5), known_obstacles=[obstacle])

    assert len(path) > 2
    assert path[0] == (0, 5)
    assert path[-1] == (10, 5)


def test_max_segment_length_splits_long_clear_path():
    path = find_path((0, 0), (10, 0), max_segment_length=4.0)

    assert path == [(0, 0), (4.0, 0.0), (8.0, 0.0), (10, 0)]
    for p1, p2 in zip(path, path[1:]):
        assert math.hypot(p2[0] - p1[0], p2[1] - p1[1]) <= 4.0
