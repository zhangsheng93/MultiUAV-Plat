
import math
import heapq
from typing import Any, List, Mapping, Tuple, Union, Optional
from shapely.affinity import scale
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union
from shapely.prepared import prep


Obstacle = Union[
    Tuple[float, float],
    Tuple[float, float, float],
    List[Tuple[float, float]],
    Mapping[str, Any],
]

_SAFETY_BUFFER = 1.1
_POINT_BUFFER = 0.5
_CIRCLE_SEGMENTS = 6
_SIMPLIFY_TOLERANCE = 1.0
_MAX_VERTICES = 40
_GRID_CELL_SIZE = 2.0


def _xy_from_position(position: Any) -> Tuple[float, float]:
    if isinstance(position, (list, tuple)):
        return float(position[0]), float(position[1])
    return float(position["x"]), float(position["y"])


def _vertices_from_api(vertices: Any) -> List[Tuple[float, float]]:
    result = []
    for vertex in vertices or []:
        if isinstance(vertex, Mapping):
            result.append((float(vertex["x"]), float(vertex["y"])))
        else:
            x, y = vertex
            result.append((float(x), float(y)))
    return result


def _obstacle_facts(obstacle: Mapping[str, Any]) -> Mapping[str, Any]:
    facts = obstacle.get("facts")
    if isinstance(facts, Mapping):
        merged = dict(obstacle)
        merged.update(facts)
        return merged
    return obstacle


def _obstacle_to_shape(obstacle: Obstacle):
    if isinstance(obstacle, Mapping):
        facts = _obstacle_facts(obstacle)
        obstacle_type = str(
            facts.get("type") or facts.get("entity_type") or facts.get("category") or ""
        ).lower()

        if obstacle_type == "polygon" or facts.get("vertices"):
            vertices = _vertices_from_api(facts.get("vertices"))
            if len(vertices) < 3:
                raise ValueError("Polygon obstacle must contain at least 3 vertices")
            return Polygon(vertices)

        x, y = _xy_from_position(facts.get("position") or facts)
        if obstacle_type in {"ellipse", "elliptical"} or facts.get("width") or facts.get("length"):
            width = float(facts.get("width", facts.get("radius", _POINT_BUFFER)))
            length = float(facts.get("length", width))
            return scale(
                Point(x, y).buffer(1.0, quad_segs=_CIRCLE_SEGMENTS),
                xfact=width,
                yfact=length,
                origin=(x, y),
            )

        radius = float(facts.get("radius", _POINT_BUFFER))
        return Point(x, y).buffer(radius, quad_segs=_CIRCLE_SEGMENTS)

    if isinstance(obstacle, tuple) and len(obstacle) == 3:
        cx, cy, r = obstacle
        return Point(cx, cy).buffer(r, quad_segs=_CIRCLE_SEGMENTS)
    elif isinstance(obstacle, tuple) and len(obstacle) == 2:
        x, y = obstacle
        return Point(x, y).buffer(_POINT_BUFFER, quad_segs=_CIRCLE_SEGMENTS)
    else:
        return Polygon(obstacle)


def _geom_length(geom) -> float:
    if geom.is_empty:
        return 0.0
    if geom.geom_type in ('Point', 'MultiPoint'):
        return 0.0
    if hasattr(geom, 'length'):
        return geom.length
    if geom.geom_type == 'GeometryCollection':
        return sum(_geom_length(g) for g in geom.geoms)
    return 0.0


def _line_of_sight(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    obstacles,
    prep_obstacles
) -> bool:
    if p1 == p2:
        return True
    line = LineString([p1, p2])
    if line.length < 1e-9:
        return True
    if obstacles.is_empty:
        return True
    if not prep_obstacles.intersects(line):
        return True
    intersection = line.intersection(obstacles)
    if intersection.is_empty:
        return True
    if intersection.geom_type in ('Point', 'MultiPoint'):
        return True
    int_len = _geom_length(intersection)
    if int_len < 1e-9:
        return True
    boundary_int = intersection.intersection(obstacles.boundary)
    if _geom_length(boundary_int) >= int_len - 1e-9:
        return True
    return False


def _euclidean(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _cross2d(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _convex_vertices(polygon) -> List[Tuple[float, float]]:
    coords = list(polygon.exterior.coords)[:-1]
    n = len(coords)
    if n < 3:
        return list(coords)
    sign = 1 if polygon.exterior.is_ccw else -1
    result = []
    for i in range(n):
        prev = coords[(i - 1) % n]
        curr = coords[i]
        nxt = coords[(i + 1) % n]
        cross = _cross2d(prev, curr, nxt)
        if cross * sign >= 0:
            result.append(curr)
    return result


def _get_convex_vertices(shape) -> List[Tuple[float, float]]:
    vertices = []
    if shape.geom_type == "Polygon":
        vertices.extend(_convex_vertices(shape))
    elif shape.geom_type == "MultiPolygon":
        for poly in shape.geoms:
            vertices.extend(_convex_vertices(poly))
    return vertices


def _build_visibility_graph(
    nodes: List[Tuple[float, float]],
    obstacles,
    prep_obstacles,
    max_edge_length: float
) -> dict:
    graph = {node: [] for node in nodes}
    n = len(nodes)
    node_x = [node[0] for node in nodes]
    node_y = [node[1] for node in nodes]
    for i in range(n):
        xi, yi = node_x[i], node_y[i]
        for j in range(i + 1, n):
            dist = math.hypot(node_x[j] - xi, node_y[j] - yi)
            if dist > max_edge_length:
                continue
            if _line_of_sight(nodes[i], nodes[j], obstacles, prep_obstacles):
                graph[nodes[i]].append((nodes[j], dist))
                graph[nodes[j]].append((nodes[i], dist))
    return graph


def _astar(
    graph: dict,
    start: Tuple[float, float],
    end: Tuple[float, float],
) -> List[Tuple[float, float]]:
    g = {node: float('inf') for node in graph}
    parent = {node: None for node in graph}
    g[start] = 0.0
    pq = [(0.0, start)]
    in_queue = {start: None}
    visited = set()

    def f(node):
        return g[node] + _euclidean(node, end)

    while pq:
        _, node = heapq.heappop(pq)
        if node in visited:
            continue
        in_queue.pop(node, None)
        visited.add(node)
        if node == end:
            break
        for neighbor, edge_cost in graph[node]:
            if neighbor in visited:
                continue
            new_g = g[node] + edge_cost
            if new_g < g[neighbor]:
                g[neighbor] = new_g
                parent[neighbor] = node
                heapq.heappush(pq, (f(neighbor), neighbor))
                in_queue[neighbor] = None

    if g[end] == float('inf'):
        return None
    path = []
    node = end
    while node is not None:
        path.append(node)
        node = parent[node]
    path.reverse()
    return path


def _smooth_path(
    path: List[Tuple[float, float]],
    obstacles,
    prep_obstacles
) -> List[Tuple[float, float]]:
    if len(path) <= 2:
        return path
    smoothed = path[:]
    changed = True
    while changed and len(smoothed) > 2:
        changed = False
        i = 0
        while i < len(smoothed) - 2:
            if _line_of_sight(smoothed[i], smoothed[i + 2], obstacles, prep_obstacles):
                smoothed.pop(i + 1)
                changed = True
            else:
                i += 1
    return smoothed


def _add_midpoints(path: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    if len(path) <= 1:
        return path

    result = [path[0]]
    for i in range(len(path) - 1):
        p1 = path[i]
        p2 = path[i + 1]
        result.append(((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2))
        result.append(p2)
    return result


def _maybe_add_midpoints(
    path: List[Tuple[float, float]],
    more_waypoints: bool
) -> List[Tuple[float, float]]:
    if not more_waypoints:
        return path
    return _add_midpoints(path)


def _limit_segment_length(
    path: List[Tuple[float, float]],
    max_segment_length: Optional[float]
) -> List[Tuple[float, float]]:
    if max_segment_length is None or max_segment_length <= 0 or len(path) <= 1:
        return path

    result = [path[0]]
    for p1, p2 in zip(path, path[1:]):
        distance = _euclidean(p1, p2)
        if distance <= max_segment_length:
            result.append(p2)
            continue

        segments = math.ceil(distance / max_segment_length)
        for idx in range(1, segments):
            ratio = (idx * max_segment_length) / distance
            result.append((
                p1[0] + (p2[0] - p1[0]) * ratio,
                p1[1] + (p2[1] - p1[1]) * ratio,
            ))
        result.append(p2)
    return result


def _finalize_path(
    path: List[Tuple[float, float]],
    more_waypoints: bool,
    max_segment_length: Optional[float],
) -> List[Tuple[float, float]]:
    return _limit_segment_length(
        _maybe_add_midpoints(path, more_waypoints),
        max_segment_length,
    )


def _astar_grid(
    start: Tuple[float, float],
    end: Tuple[float, float],
    merged_obs,
    prep_obs,
    cell_size: float
) -> List[Tuple[float, float]]:
    min_x = min(start[0], end[0]) - 1
    max_x = max(start[0], end[0]) + 1
    min_y = min(start[1], end[1]) - 1
    max_y = max(start[1], end[1]) + 1

    cols = max(2, math.ceil((max_x - min_x) / cell_size))
    rows = max(2, math.ceil((max_y - min_y) / cell_size))

    def cell_idx(col, row):
        return row * cols + col

    blocked = [False] * (rows * cols)
    for row in range(rows):
        for col in range(cols):
            cx = min_x + (col + 0.5) * cell_size
            cy = min_y + (row + 0.5) * cell_size
            if merged_obs.intersects(Point(cx, cy)):
                blocked[cell_idx(col, row)] = True

    start_col = int((start[0] - min_x) / cell_size)
    start_row = int((start[1] - min_y) / cell_size)
    end_col = int((end[0] - min_x) / cell_size)
    end_row = int((end[1] - min_y) / cell_size)
    start_col = max(0, min(cols - 1, start_col))
    start_row = max(0, min(rows - 1, start_row))
    end_col = max(0, min(cols - 1, end_col))
    end_row = max(0, min(rows - 1, end_row))

    if blocked[cell_idx(start_col, start_row)] or blocked[cell_idx(end_col, end_row)]:
        raise ValueError("Start or end point is inside an obstacle")

    def cell_center(col, row):
        return (min_x + (col + 0.5) * cell_size, min_y + (row + 0.5) * cell_size)

    g_grid = {(start_col, start_row): 0.0}
    parent = {}
    pq = [(0.0, start_col, start_row)]
    visited = set()

    def h(col, row):
        return math.hypot((end_col - col) * cell_size, (end_row - row) * cell_size)

    while pq:
        _, col, row = heapq.heappop(pq)
        if (col, row) in visited:
            continue
        visited.add((col, row))
        if col == end_col and row == end_row:
            break
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == 0 and dr == 0:
                    continue
                nc, nr = col + dc, row + dr
                if nc < 0 or nc >= cols or nr < 0 or nr >= rows:
                    continue
                if blocked[cell_idx(nc, nr)]:
                    continue
                move_cost = cell_size if (dc == 0) != (dr == 0) else cell_size * math.sqrt(2)
                new_g = g_grid[(col, row)] + move_cost
                if (nc, nr) not in g_grid or new_g < g_grid[(nc, nr)]:
                    g_grid[(nc, nr)] = new_g
                    parent[(nc, nr)] = (col, row)
                    heapq.heappush(pq, (new_g + h(nc, nr), nc, nr))

    if (end_col, end_row) not in parent and (start_col, start_row) != (end_col, end_row):
        return None

    path = []
    node = (end_col, end_row)
    while node in parent:
        path.append(cell_center(*node))
        node = parent[node]
    path.append(cell_center(start_col, start_row))
    path.reverse()
    return path


_ALGO_VISIBILITY_GRAPH = "visibility_graph"
_ALGO_GRID = "grid"
_ALGO_NONE = "none"


def find_path(
    start_point: Tuple[float, float],
    des_point: Tuple[float, float],
    known_obstacles: Optional[List[Obstacle]] = None,
    more_waypoints: bool = False,
    safety_buffer: float = _SAFETY_BUFFER,
    max_segment_length: Optional[float] = None,
) -> List[Tuple[float, float]]:
    algo_used = _ALGO_NONE

    if known_obstacles is None or len(known_obstacles) == 0:
        return _finalize_path([start_point, des_point], more_waypoints, max_segment_length)

    obstacle_shapes = [_obstacle_to_shape(obs) for obs in known_obstacles]
    buffered = [s.buffer(safety_buffer, quad_segs=_CIRCLE_SEGMENTS) for s in obstacle_shapes]
    merged_obstacles = unary_union(buffered)

    if merged_obstacles.contains(Point(start_point)):
        raise ValueError("Start point is inside an obstacle")
    if merged_obstacles.contains(Point(des_point)):
        raise ValueError("Destination point is inside an obstacle")

    check_obstacles = merged_obstacles.simplify(_SIMPLIFY_TOLERANCE, preserve_topology=True)
    prepared_obstacles = prep(check_obstacles)

    if _line_of_sight(start_point, des_point, check_obstacles, prepared_obstacles):
        return _finalize_path([start_point, des_point], more_waypoints, max_segment_length)

    vertices = _get_convex_vertices(check_obstacles)
    seen = set()
    unique_vertices = []
    for v in vertices:
        if v not in seen:
            seen.add(v)
            unique_vertices.append(v)

    total_verts = len(unique_vertices)
    use_grid = total_verts > _MAX_VERTICES

    if use_grid:
        algo_used = _ALGO_GRID
        path = _astar_grid(start_point, des_point,
                          check_obstacles, prepared_obstacles, _GRID_CELL_SIZE)
        if path is None:
            raise ValueError("No valid path found to destination")
        path = _smooth_path(path, check_obstacles, prepared_obstacles)
        return _finalize_path(path, more_waypoints, max_segment_length)

    if len(unique_vertices) > _MAX_VERTICES:
        step = len(unique_vertices) / _MAX_VERTICES
        unique_vertices = [unique_vertices[int(i * step)] for i in range(_MAX_VERTICES)]

    nodes = [start_point, des_point] + unique_vertices
    direct = _euclidean(start_point, des_point)
    max_edge_length = max(direct * 3.0, 1.0)

    graph = _build_visibility_graph(nodes, check_obstacles, prepared_obstacles, max_edge_length)
    path = _astar(graph, start_point, des_point)

    if path is None:
        algo_used = _ALGO_GRID
        path = _astar_grid(start_point, des_point,
                          check_obstacles, prepared_obstacles, _GRID_CELL_SIZE)
        if path is None:
            raise ValueError("No valid path found to destination")
    else:
        algo_used = _ALGO_VISIBILITY_GRAPH

    path = _smooth_path(path, check_obstacles, prepared_obstacles)
    return _finalize_path(path, more_waypoints, max_segment_length)
