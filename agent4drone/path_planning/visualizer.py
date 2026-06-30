
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import List, Tuple, Union, Optional
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union
from path_planning.coverage_planner import calculate_coverage_percentage
from path_planning.path_finder import Obstacle, _obstacle_to_shape


def visualize_coverage(
    start: Tuple[float, float],
    target: Union[Tuple[float, float, float], List[Tuple[float, float]]],
    path: List[Tuple[float, float]],
    task_radius: float,
    title: str = "Area Coverage Path Planning",
    grid_step: float = 0.5
):
    fig, ax = plt.subplots(figsize=(10, 10))

    # First, determine target shape and bounds
    if isinstance(target, tuple) and len(target) == 3:
        cx, cy, r = target
        target_shape = Point(cx, cy).buffer(r)
        circle = patches.Circle((cx, cy), r, facecolor='lightblue', alpha=0.3, edgecolor='blue', linewidth=2)
        ax.add_patch(circle)
        min_x, max_x = cx - r - 2, cx + r + 2
        min_y, max_y = cy - r - 2, cy + r + 2
    else:
        target_shape = Polygon(target)
        poly = patches.Polygon(target, facecolor='lightgreen', alpha=0.3, edgecolor='green', linewidth=2)
        ax.add_patch(poly)
        xs, ys = zip(*target)
        min_x, max_x = min(xs) - 2, max(xs) + 2
        min_y, max_y = min(ys) - 2, max(ys) + 2

    # Create a buffer along the path to represent covered area
    if len(path) >= 2:
        path_line = LineString(path)
        path_buffer = path_line.buffer(task_radius)
        # Intersect buffer with target to get covered area
        covered_area = path_buffer.intersection(target_shape)
        
        # Plot the covered area
        if not covered_area.is_empty:
            if covered_area.geom_type == "Polygon":
                x, y = covered_area.exterior.xy
                ax.fill(x, y, color='orange', alpha=0.4, label='Covered Area')
            elif covered_area.geom_type == "MultiPolygon":
                for poly in covered_area.geoms:
                    x, y = poly.exterior.xy
                    ax.fill(x, y, color='orange', alpha=0.4)

    # Plot path
    if path:
        path_x, path_y = zip(*path)
        ax.plot(path_x, path_y, color='red', linewidth=1.5, label='Planned Path', zorder=3)
        ax.scatter(path_x, path_y, color='darkred', s=10, zorder=5)

    # Plot start point
    ax.scatter(start[0], start[1], color='lime', s=100, marker='X', zorder=10, label='Start Point')

    # Calculate and display coverage percentage
    coverage = calculate_coverage_percentage(path, target, task_radius, grid_step=grid_step)
    ax.set_title(f"{title}\nCoverage: {coverage:.2f}%", fontsize=14, pad=20)
    ax.set_xlabel("X Coordinate", fontsize=12)
    ax.set_ylabel("Y Coordinate", fontsize=12)
    ax.set_xlim(min_x, max_x)
    ax.set_ylim(min_y, max_y)
    ax.set_aspect('equal', adjustable='box')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    plt.tight_layout()
    plt.show()
    return coverage


def visualize_path(
    start_point: Tuple[float, float],
    des_point: Tuple[float, float],
    path: List[Tuple[float, float]],
    known_obstacles: Optional[List[Obstacle]] = None,
    title: str = "Path Planning with Obstacle Avoidance"
):
    fig, ax = plt.subplots(figsize=(10, 10))

    all_x = [start_point[0], des_point[0]]
    all_y = [start_point[1], des_point[1]]

    if known_obstacles:
        for obs in known_obstacles:
            shape = _obstacle_to_shape(obs)
            if isinstance(obs, tuple) and len(obs) == 3:
                cx, cy, r = obs
                circle = patches.Circle((cx, cy), r, facecolor='salmon', alpha=0.4,
                                        edgecolor='red', linewidth=2)
                ax.add_patch(circle)
                all_x.extend([cx - r, cx + r])
                all_y.extend([cy - r, cy + r])
            elif isinstance(obs, tuple) and len(obs) == 2:
                x, y = obs
                ax.scatter(x, y, color='red', s=80, marker='o', zorder=6)
                circle_vis = patches.Circle((x, y), 0.5, facecolor='salmon', alpha=0.3,
                                            edgecolor='red', linewidth=1, linestyle='--')
                ax.add_patch(circle_vis)
                all_x.extend([x - 1, x + 1])
                all_y.extend([y - 1, y + 1])
            else:
                poly = patches.Polygon(obs, facecolor='salmon', alpha=0.4,
                                       edgecolor='red', linewidth=2)
                ax.add_patch(poly)
                xs, ys = zip(*obs)
                all_x.extend(xs)
                all_y.extend(ys)

    if path:
        path_x, path_y = zip(*path)
        ax.plot(path_x, path_y, color='blue', linewidth=2, label='Path', zorder=4)
        ax.scatter(path_x, path_y, color='navy', s=15, zorder=5)

    ax.scatter(start_point[0], start_point[1], color='lime', s=120, marker='*',
               zorder=10, label='Start')
    ax.scatter(des_point[0], des_point[1], color='gold', s=120, marker='*',
               zorder=10, label='Destination')

    margin = 2
    ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
    ax.set_ylim(min(all_y) - margin, max(all_y) + margin)
    ax.set_aspect('equal', adjustable='box')
    ax.set_title(title, fontsize=14, pad=20)
    ax.set_xlabel("X Coordinate", fontsize=12)
    ax.set_ylabel("Y Coordinate", fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    plt.tight_layout()
    plt.show()
