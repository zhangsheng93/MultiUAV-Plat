
import math
import heapq
from typing import List, Tuple, Union, Optional
from shapely.geometry import Point, Polygon, LineString, MultiPolygon
from shapely.ops import unary_union
from shapely.prepared import prep


Obstacle = Union[Tuple[float, float], Tuple[float, float, float], List[Tuple[float, float]]]

_SAFETY_BUFFER = 1.1
_POINT_BUFFER = 0.5
_CIRCLE_SEGMENTS = 6
_SIMPLIFY_TOLERANCE = 1.0
_MAX_VERTICES = 60


def _obstacle_to_shape(obstacle: Obstacle):
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


def _is_visible(p1: Tuple[float, float], p2: Tuple[float, float], merged_obstacles, prepared_obstacles) -> bool:
    line = LineString([p1, p2])
    if line.length < 1e-9:
        return True
    if merged_obstacles.is_empty:
        return True
    if not prepared_obstacles.intersects(line):
        return True
    intersection = line.intersection(merged_obstacles)
    if intersection.is_empty:
        return True
    if intersection.geom_type in ('Point', 'MultiPoint'):
        return True
    int_len = _geom_length(intersection)
    if int_len < 1e-9:
        return True
    boundary_int = intersection.intersection(merged_obstacles.boundary)
    if _geom_length(boundary_int) >= int_len - 1e-9:
        return True
    return False


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


def _snap_to_boundary(verts, merged_obstacles, snap_dist=0.5):
    result = []
    boundary = merged_obstacles.boundary
    for v in verts:
        pt = Point(v)
        if not merged_obstacles.contains(pt) and boundary.distance(pt) < snap_dist:
            result.append(v)
        elif not merged_obstacles.contains(pt):
            result.append(v)
    return result


def _build_visibility_graph(
    nodes: List[Tuple[float, float]],
    merged_obstacles,
    prepared_obstacles,
    max_edge_length: float
) -> dict:
    graph = {node: [] for node in nodes}
    n = len(nodes)
    for i in range(n):
        for j in range(i + 1, n):
            dist = math.hypot(nodes[i][0] - nodes[j][0], nodes[i][1] - nodes[j][1])
            if dist > max_edge_length:
                continue
            if _is_visible(nodes[i], nodes[j], merged_obstacles, prepared_obstacles):
                graph[nodes[i]].append((nodes[j], dist))
                graph[nodes[j]].append((nodes[i], dist))
    return graph


def _dijkstra(graph: dict, start: Tuple[float, float], end: Tuple[float, float]):
    distances = {node: float('inf') for node in graph}
    distances[start] = 0.0
    previous = {node: None for node in graph}
    pq = [(0.0, start)]
    visited = set()

    while pq:
        dist, node = heapq.heappop(pq)
        if node in visited:
            continue
        visited.add(node)
        if node == end:
            break
        for neighbor, weight in graph[node]:
            if neighbor in visited:
                continue
            new_dist = dist + weight
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                previous[neighbor] = node
                heapq.heappush(pq, (new_dist, neighbor))

    if distances[end] == float('inf'):
        return None

    path = []
    node = end
    while node is not None:
        path.append(node)
        node = previous[node]
    path.reverse()
    return path


def find_path(
    start_point: Tuple[float, float],
    des_point: Tuple[float, float],
    known_obstacles: Optional[List[Obstacle]] = None
) -> List[Tuple[float, float]]:
    if known_obstacles is None or len(known_obstacles) == 0:
        return [start_point, des_point]

    obstacle_shapes = [_obstacle_to_shape(obs) for obs in known_obstacles]
    buffered = [s.buffer(_SAFETY_BUFFER, quad_segs=_CIRCLE_SEGMENTS) for s in obstacle_shapes]
    merged_obstacles = unary_union(buffered)

    if merged_obstacles.contains(Point(start_point)):
        raise ValueError("Start point is inside an obstacle")
    if merged_obstacles.contains(Point(des_point)):
        raise ValueError("Destination point is inside an obstacle")

    check_obstacles = merged_obstacles.simplify(_SIMPLIFY_TOLERANCE, preserve_topology=True)
    prepared_obstacles = prep(check_obstacles)

    if _is_visible(start_point, des_point, check_obstacles, prepared_obstacles):
        return [start_point, des_point]

    vertices = _get_convex_vertices(check_obstacles)
    seen = set()
    unique_vertices = []
    for v in vertices:
        if v not in seen:
            seen.add(v)
            unique_vertices.append(v)

    if len(unique_vertices) > _MAX_VERTICES:
        step = len(unique_vertices) / _MAX_VERTICES
        unique_vertices = [unique_vertices[int(i * step)] for i in range(_MAX_VERTICES)]

    nodes = [start_point, des_point] + unique_vertices

    min_x = min(n[0] for n in nodes)
    max_x = max(n[0] for n in nodes)
    min_y = min(n[1] for n in nodes)
    max_y = max(n[1] for n in nodes)
    direct = math.hypot(des_point[0] - start_point[0], des_point[1] - start_point[1])
    max_edge_length = max(direct * 3.0, (max_x - min_x) + (max_y - min_y))

    graph = _build_visibility_graph(nodes, check_obstacles, prepared_obstacles, max_edge_length)
    path = _dijkstra(graph, start_point, des_point)

    if path is None:
        raise ValueError("No valid path found to destination")

    return path
