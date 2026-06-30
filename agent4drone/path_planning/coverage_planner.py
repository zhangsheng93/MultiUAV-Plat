
import itertools
import math
from typing import List, Sequence, Tuple, Union
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import nearest_points


Target = Union[Tuple[float, float, float], List[Tuple[float, float]]]
Point2D = Tuple[float, float]
Lane = Tuple[Point2D, Point2D]


def _target_to_shape(target: Target):
    if isinstance(target, tuple) and len(target) == 3:
        cx, cy, r = target
        return Point(cx, cy).buffer(r)
    return Polygon(target)


def _validate_planner_inputs(task_radius: float, point_spacing: float) -> None:
    if task_radius <= 0:
        raise ValueError("task_radius must be positive")
    if point_spacing <= 0:
        raise ValueError("point_spacing must be positive")


def _lane_length(lane: Lane) -> float:
    (x1, y1), (x2, y2) = lane
    return math.hypot(x2 - x1, y2 - y1)


def _distance(a: Point2D, b: Point2D) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _path_length(path: Sequence[Point2D]) -> float:
    return sum(
        _distance(previous, current)
        for previous, current in zip(path, path[1:])
    )


def _sample_lane(lane: Lane, point_spacing: float) -> List[Point2D]:
    (x1, y1), (x2, y2) = lane
    segment_length = _lane_length(lane)
    num_points = max(2, int(segment_length / point_spacing) + 1)
    return [
        (
            x1 + (i / (num_points - 1)) * (x2 - x1),
            y1 + (i / (num_points - 1)) * (y2 - y1),
        )
        for i in range(num_points)
    ]


def _append_lane_points(path: List[Point2D], lane: Lane, point_spacing: float) -> None:
    points = _sample_lane(lane, point_spacing)
    if path and points and _distance(path[-1], points[0]) < 1e-9:
        path.extend(points[1:])
    else:
        path.extend(points)


def _append_lane_endpoints(path: List[Point2D], lane: Lane) -> None:
    for point in lane:
        if path and _distance(path[-1], point) < 1e-9:
            continue
        path.append(point)


def _add_start_transition(
    start: Point2D,
    path: List[Point2D],
) -> List[Point2D]:
    if not path:
        return [start]

    if _distance(start, path[0]) <= 1e-6:
        return path

    return [start] + path


def _dedupe_sorted_values(values: Sequence[float]) -> List[float]:
    sorted_values = sorted(values)
    deduped: List[float] = []
    for value in sorted_values:
        if deduped and abs(deduped[-1] - value) < 1e-9:
            continue
        deduped.append(value)
    return deduped


def _sweep_y_values(min_y: float, max_y: float, task_radius: float) -> List[float]:
    height = max_y - min_y
    if height <= 1e-9:
        return [min_y]

    line_spacing = task_radius
    values = [min_y, max_y]

    if height <= 2 * task_radius:
        values.append((min_y + max_y) / 2)
        return _dedupe_sorted_values(values)

    first_interior = min_y + task_radius
    last_interior = max_y - task_radius
    y = first_interior
    while y <= last_interior + 1e-9:
        values.append(min(y, last_interior))
        y += line_spacing
    values.append(last_interior)

    return _dedupe_sorted_values(values)


def _generate_sweep_lanes(
    sweep_shape,
    task_radius: float,
    initial_direction: int = 1,
) -> List[Lane]:
    min_x, min_y, max_x, max_y = sweep_shape.bounds
    lanes: List[Lane] = []

    direction = initial_direction
    for y in _sweep_y_values(min_y, max_y, task_radius):
        x_start = min_x if direction == 1 else max_x
        x_end = max_x if direction == 1 else min_x
        scan_line = LineString([(x_start, y), (x_end, y)])
        intersection = sweep_shape.intersection(scan_line)

        if not intersection.is_empty:
            segments = []
            if intersection.geom_type == "LineString":
                segments = [intersection]
            elif intersection.geom_type == "MultiLineString":
                segments = list(intersection.geoms)

            for segment in segments:
                if len(segment.coords) < 2:
                    continue
                (x1, y1), (x2, y2) = segment.coords[0], segment.coords[-1]
                if direction == 1 and x1 > x2:
                    x1, y1, x2, y2 = x2, y2, x1, y1
                elif direction == -1 and x1 < x2:
                    x1, y1, x2, y2 = x2, y2, x1, y1
                lanes.append(((x1, y1), (x2, y2)))

        direction *= -1

    return lanes


def _linear_partition_lanes(lanes: Sequence[Lane], num_partitions: int) -> List[List[Lane]]:
    if not lanes:
        return []

    partition_count = min(num_partitions, len(lanes))
    if partition_count <= 1:
        return [list(lanes)]
    if partition_count == len(lanes):
        return [[lane] for lane in lanes]

    weights = [_lane_length(lane) for lane in lanes]
    n = len(weights)
    prefix = [0.0]
    for weight in weights:
        prefix.append(prefix[-1] + weight)

    dp = [[0.0] * (partition_count + 1) for _ in range(n + 1)]
    split = [[0] * (partition_count + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        dp[i][1] = prefix[i]

    for k in range(2, partition_count + 1):
        for i in range(k, n + 1):
            best_cost = math.inf
            best_j = k - 1
            for j in range(k - 1, i):
                cost = max(dp[j][k - 1], prefix[i] - prefix[j])
                if cost < best_cost:
                    best_cost = cost
                    best_j = j
            dp[i][k] = best_cost
            split[i][k] = best_j

    partitions: List[List[Lane]] = []
    i = n
    k = partition_count
    while k > 1:
        j = split[i][k]
        partitions.append(list(lanes[j:i]))
        i = j
        k -= 1
    partitions.append(list(lanes[:i]))
    partitions.reverse()
    return partitions


def _entry_cost(start: Point2D, lanes: Sequence[Lane]) -> float:
    if not lanes:
        return 0.0
    first_start, first_end = lanes[0]
    return min(_distance(start, first_start), _distance(start, first_end))


def _assign_partitions_to_starts(
    starts: Sequence[Point2D],
    partitions: Sequence[Sequence[Lane]],
) -> List[int]:
    num_starts = len(starts)
    num_partitions = len(partitions)
    assignments = [-1] * num_starts

    if num_partitions == 0:
        return assignments

    if num_starts <= 8:
        best_cost = math.inf
        best_perm = None
        for start_indices in itertools.permutations(range(num_starts), num_partitions):
            cost = sum(
                _entry_cost(starts[start_idx], partitions[partition_idx])
                for partition_idx, start_idx in enumerate(start_indices)
            )
            if cost < best_cost:
                best_cost = cost
                best_perm = start_indices
        if best_perm is not None:
            for partition_idx, start_idx in enumerate(best_perm):
                assignments[start_idx] = partition_idx
        return assignments

    candidates = sorted(
        (
            (_entry_cost(start, partition), start_idx, partition_idx)
            for start_idx, start in enumerate(starts)
            for partition_idx, partition in enumerate(partitions)
        ),
        key=lambda item: (item[0], item[1], item[2]),
    )
    used_starts = set()
    used_partitions = set()
    for _, start_idx, partition_idx in candidates:
        if start_idx in used_starts or partition_idx in used_partitions:
            continue
        assignments[start_idx] = partition_idx
        used_starts.add(start_idx)
        used_partitions.add(partition_idx)
        if len(used_partitions) == num_partitions:
            break

    return assignments


def _build_partition_path(
    start: Point2D,
    lanes: Sequence[Lane],
    sweep_shape,
    point_spacing: float,
) -> List[Point2D]:
    if not lanes:
        return [start]

    candidate_paths: List[List[Point2D]] = []
    lane_orders = [list(lanes)]
    reversed_lanes = list(reversed(lanes))
    if reversed_lanes != lane_orders[0]:
        lane_orders.append(reversed_lanes)

    for lane_order in lane_orders:
        path: List[Point2D] = []
        current = start
        for lane in lane_order:
            lane_start, lane_end = lane
            if _distance(current, lane_start) <= _distance(current, lane_end):
                oriented_lane = lane
            else:
                oriented_lane = (lane_end, lane_start)
            _append_lane_endpoints(path, oriented_lane)
            current = oriented_lane[1]
        candidate_paths.append(_add_start_transition(start, path))

    return min(candidate_paths, key=_path_length)


def generate_single_coverage_path(
    start: Point2D,
    target: Target,
    task_radius: float,
    point_spacing: float = 0.5
) -> List[Point2D]:
    _validate_planner_inputs(task_radius, point_spacing)
    target_shape = _target_to_shape(target)
    if target_shape.is_empty or target_shape.area <= 1e-9:
        return [start]

    sweep_shape = target_shape
    nearest_on_sweep = nearest_points(Point(start), sweep_shape)[1]
    initial_direction = 1 if start[0] <= nearest_on_sweep.x else -1
    lanes = _generate_sweep_lanes(sweep_shape, task_radius, initial_direction)
    path: List[Point2D] = []
    for lane in lanes:
        _append_lane_endpoints(path, lane)
    return _add_start_transition(start, path)


def generate_coverage_path(
    starts: List[Point2D],
    target: Target,
    task_radius: float,
    point_spacing: float = 0.5
) -> List[List[Point2D]]:
    _validate_planner_inputs(task_radius, point_spacing)
    if not starts:
        raise ValueError("starts must contain at least one start point")

    target_shape = _target_to_shape(target)
    if target_shape.is_empty or target_shape.area <= 1e-9:
        return [[start] for start in starts]

    sweep_shape = target_shape
    lanes = _generate_sweep_lanes(sweep_shape, task_radius)
    partitions = _linear_partition_lanes(lanes, min(len(starts), len(lanes)))
    assignments = _assign_partitions_to_starts(starts, partitions)

    paths: List[List[Point2D]] = []
    for start, partition_idx in zip(starts, assignments):
        partition = partitions[partition_idx] if partition_idx >= 0 else []
        paths.append(_build_partition_path(start, partition, sweep_shape, point_spacing))

    return paths


def calculate_coverage_percentage(
    path: List[Tuple[float, float]],
    target: Target,
    task_radius: float,
    grid_step: float = 0.25
) -> float:
    if task_radius <= 0:
        raise ValueError("task_radius must be positive")

    target_shape = _target_to_shape(target)

    if len(path) < 2:
        return 0.0

    path_line = LineString(path)
    path_buffer = path_line.buffer(task_radius)
    covered_area = path_buffer.intersection(target_shape)

    total_area = target_shape.area
    covered_area_value = covered_area.area

    return (covered_area_value / total_area * 100) if total_area > 1e-9 else 0.0
