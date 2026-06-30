import pytest
import sys
from pathlib import Path
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

# Add the parent directory to the Python path so that path_planning is found
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from path_planning.coverage_planner import (
    calculate_coverage_percentage,
    generate_coverage_path,
    generate_single_coverage_path,
)


def missed_area(path, target, task_radius):
    return Polygon(target).difference(LineString(path).buffer(task_radius)).area


def combined_coverage_percentage(paths, target, task_radius):
    target_shape = (
        Point(target[0], target[1]).buffer(target[2])
        if isinstance(target, tuple)
        else Polygon(target)
    )
    path_buffers = [
        LineString(path).buffer(task_radius)
        for path in paths
        if len(path) >= 2
    ]
    if not path_buffers:
        return 0.0
    covered_area = unary_union(path_buffers).intersection(target_shape).area
    return covered_area / target_shape.area * 100 if target_shape.area > 1e-9 else 0.0


def path_length(path):
    return LineString(path).length if len(path) >= 2 else 0.0


def lane_connector_lengths(path):
    return [
        LineString([path[index], path[index + 1]]).length
        for index in range(2, len(path) - 1, 2)
    ]


def total_waypoint_count(paths):
    return sum(len(path) for path in paths)


def target_shape(target):
    return (
        Point(target[0], target[1]).buffer(target[2])
        if isinstance(target, tuple)
        else Polygon(target)
    )


def assert_non_start_waypoints_are_inside_target(path, target):
    shape = target_shape(target).buffer(1e-8)
    for point in path[1:]:
        assert shape.covers(Point(point))


def assert_all_non_start_waypoints_are_inside_target(paths, target):
    for path in paths:
        assert_non_start_waypoints_are_inside_target(path, target)


def test_zigzag_covers_square_boundary_strip_at_small_radius():
    target = [(0, 0), (10, 0), (10, 10), (0, 10)]
    task_radius = 0.5

    path = generate_single_coverage_path((0, 0), target, task_radius, point_spacing=0.5)

    assert calculate_coverage_percentage(path, target, task_radius) == pytest.approx(100.0)
    assert missed_area(path, target, task_radius) < 1e-9
    assert_non_start_waypoints_are_inside_target(path, target)


def test_zigzag_covers_concave_polygon_corners():
    target = [(0, 0), (10, 0), (10, 4), (6, 4), (6, 10), (0, 10)]
    task_radius = 0.5

    path = generate_single_coverage_path((0, 0), target, task_radius, point_spacing=0.5)

    assert calculate_coverage_percentage(path, target, task_radius) == pytest.approx(100.0)
    assert missed_area(path, target, task_radius) < 1e-9
    assert_non_start_waypoints_are_inside_target(path, target)


def test_zigzag_covers_angled_polygon_corners():
    target = [(5, 0), (10, 5), (5, 10), (0, 5)]
    task_radius = 0.5

    path = generate_single_coverage_path((0, 0), target, task_radius, point_spacing=0.5)

    assert calculate_coverage_percentage(path, target, task_radius) == pytest.approx(100.0)
    assert missed_area(path, target, task_radius) < 1e-9
    assert_non_start_waypoints_are_inside_target(path, target)


def test_zigzag_stays_inside_circle_target():
    target = (10, 10, 8)
    task_radius = 0.8

    path = generate_single_coverage_path((0, 0), target, task_radius, point_spacing=0.5)

    path_line = LineString(path[1:])

    assert path_line.difference(target_shape(target)).length < 1e-9
    assert calculate_coverage_percentage(path, target, task_radius) == pytest.approx(100.0)
    assert_non_start_waypoints_are_inside_target(path, target)


def test_zigzag_enters_polygon_from_near_side_of_start():
    target = [(0, 0), (15, 0), (18, 10), (10, 15), (-3, 12)]
    task_radius = 0.8

    path = generate_single_coverage_path((-2, -2), target, task_radius, point_spacing=0.5)

    assert path[1][0] < 5.0


def test_multi_uav_covers_square_and_preserves_start_order():
    target = [(0, 0), (12, 0), (12, 8), (0, 8)]
    starts = [(-2, -2), (14, -2)]
    task_radius = 0.5

    paths = generate_coverage_path(starts, target, task_radius, point_spacing=0.5)

    assert len(paths) == len(starts)
    assert [path[0] for path in paths] == starts
    assert combined_coverage_percentage(paths, target, task_radius) == pytest.approx(100.0)
    assert_all_non_start_waypoints_are_inside_target(paths, target)


def test_multi_uav_covers_circle_with_three_drones():
    target = (10, 10, 6)
    starts = [(0, 0), (20, 0), (10, 20)]
    task_radius = 0.8

    paths = generate_coverage_path(starts, target, task_radius, point_spacing=0.5)

    assert len(paths) == len(starts)
    assert [path[0] for path in paths] == starts
    assert combined_coverage_percentage(paths, target, task_radius) == pytest.approx(100.0)
    assert_all_non_start_waypoints_are_inside_target(paths, target)


def test_multi_uav_covers_concave_polygon():
    target = [(0, 0), (10, 0), (10, 4), (6, 4), (6, 10), (0, 10)]
    starts = [(-2, -2), (12, -2), (-2, 12)]
    task_radius = 0.5

    paths = generate_coverage_path(starts, target, task_radius, point_spacing=0.5)

    assert combined_coverage_percentage(paths, target, task_radius) == pytest.approx(100.0)
    assert_all_non_start_waypoints_are_inside_target(paths, target)


def test_multi_uav_balances_rectangular_workload_reasonably():
    target = [(0, 0), (30, 0), (30, 10), (0, 10)]
    starts = [(-2, -2), (32, -2), (15, 14)]
    task_radius = 0.5

    paths = generate_coverage_path(starts, target, task_radius, point_spacing=0.5)
    lengths = [path_length(path) for path in paths]
    active_lengths = [length for length in lengths if length > 0]

    assert len(active_lengths) == len(starts)
    assert max(active_lengths) / min(active_lengths) < 1.75
    assert_all_non_start_waypoints_are_inside_target(paths, target)


def test_multi_uav_uses_turning_points_instead_of_dense_lane_samples():
    target = [(0, 0), (40, 0), (40, 12), (0, 12)]
    starts = [(-2, -2), (42, -2)]
    task_radius = 0.5

    paths = generate_coverage_path(starts, target, task_radius, point_spacing=0.5)

    assert combined_coverage_percentage(paths, target, task_radius) == pytest.approx(100.0)
    assert total_waypoint_count(paths) < 80
    assert_all_non_start_waypoints_are_inside_target(paths, target)


def test_multi_uav_connects_adjacent_lanes_on_near_side():
    target = (0, 0, 10)
    starts = [(-12, 8), (12, 8), (-12, -8), (12, -8)]
    task_radius = 0.8

    paths = generate_coverage_path(starts, target, task_radius, point_spacing=0.8)
    connectors = [
        connector
        for path in paths
        for connector in lane_connector_lengths(path)
    ]

    assert connectors
    assert max(connectors) < 3 * task_radius
    assert combined_coverage_percentage(paths, target, task_radius) == pytest.approx(100.0)
    assert_all_non_start_waypoints_are_inside_target(paths, target)


def test_multi_uav_circle_plan_reduces_z_style_route_length():
    target = (0, 0, 10)
    starts = [(-12, 8), (12, 8), (-12, -8), (12, -8)]
    task_radius = 0.8

    paths = generate_coverage_path(starts, target, task_radius, point_spacing=0.8)
    total_length = sum(path_length(path) for path in paths)

    assert [path[0] for path in paths] == starts
    assert total_length < 500.0
    assert combined_coverage_percentage(paths, target, task_radius) == pytest.approx(100.0)
    assert_all_non_start_waypoints_are_inside_target(paths, target)


def test_multi_uav_extra_drones_keep_start_only_when_lanes_are_exhausted():
    target = (0, 0, 0.1)
    starts = [(-1, 0), (1, 0), (0, 1), (0, -1)]
    task_radius = 10.0

    paths = generate_coverage_path(starts, target, task_radius, point_spacing=1.0)

    assert len(paths) == len(starts)
    assert sum(1 for path in paths if len(path) == 1) == 3
    assert [path[0] for path in paths] == starts
    assert_all_non_start_waypoints_are_inside_target(paths, target)


def test_multi_uav_rejects_invalid_inputs():
    target = [(0, 0), (1, 0), (1, 1), (0, 1)]

    with pytest.raises(ValueError, match="starts"):
        generate_coverage_path([], target, 0.5)
    with pytest.raises(ValueError, match="task_radius"):
        generate_coverage_path([(0, 0)], target, 0)
    with pytest.raises(ValueError, match="point_spacing"):
        generate_coverage_path([(0, 0)], target, 0.5, point_spacing=0)
