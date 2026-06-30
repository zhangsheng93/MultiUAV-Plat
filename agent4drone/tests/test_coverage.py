
import math
import random
import sys
from pathlib import Path

import pytest
from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.ops import unary_union

# Add the parent directory to the Python path so that path_planning is found
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from path_planning import (
    calculate_coverage_percentage,
    generate_coverage_path,
    generate_single_coverage_path,
    visualize_coverage
)

RANDOM_POLYGON_SEEDS = [7, 11, 23, 47, 89, 101, 131, 173, 211, 257]
RANDOM_CIRCLE_SEEDS = [3, 5, 13, 29, 37, 53, 71, 97]
RANDOM_MULTI_POLYGON_CASES = [(2, 17), (2, 43), (3, 19), (3, 67), (4, 31), (4, 109)]
RANDOM_MULTI_CIRCLE_CASES = [(2, 41), (3, 59), (4, 83)]


def _generate_random_convex_polygon(seed: int, center=(10.0, 10.0), base_radius: float = 8.0):
    rng = random.Random(seed)
    cx, cy = center
    point_count = rng.randint(12, 20)
    samples = []

    for _ in range(point_count):
        angle = rng.uniform(0.0, 2.0 * math.pi)
        radius = base_radius * rng.uniform(0.55, 1.0)
        samples.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))

    hull = MultiPoint(samples).convex_hull
    return list(hull.exterior.coords)[:-1]


def _generate_random_circle(seed: int):
    rng = random.Random(seed)
    return (
        rng.uniform(3.0, 18.0),
        rng.uniform(3.0, 18.0),
        rng.uniform(3.0, 8.0),
    )


def _generate_drone_starts(seed: int, drone_count: int, center=(10.0, 10.0), radius: float = 16.0):
    rng = random.Random(seed)
    cx, cy = center
    angle_offset = rng.uniform(0.0, 2.0 * math.pi)
    return [
        (
            cx + radius * math.cos(angle_offset + i * 2.0 * math.pi / drone_count),
            cy + radius * math.sin(angle_offset + i * 2.0 * math.pi / drone_count),
        )
        for i in range(drone_count)
    ]


def _target_to_shape(target):
    if isinstance(target, tuple) and len(target) == 3:
        return Point(target[0], target[1]).buffer(target[2])
    return Polygon(target)


def _combined_coverage_percentage(paths, target, task_radius):
    target_shape = _target_to_shape(target)
    buffers = [
        LineString(path).buffer(task_radius)
        for path in paths
        if len(path) >= 2
    ]
    if not buffers:
        return 0.0
    covered_area = unary_union(buffers).intersection(target_shape).area
    return covered_area / target_shape.area * 100 if target_shape.area > 1e-9 else 0.0


def _plot_multi_drone_coverage(starts, target, paths, task_radius, title):
    import matplotlib.patches as patches
    import matplotlib.pyplot as plt

    target_shape = _target_to_shape(target)
    coverage = _combined_coverage_percentage(paths, target, task_radius)
    fig, ax = plt.subplots(figsize=(10, 10))

    if isinstance(target, tuple) and len(target) == 3:
        cx, cy, radius = target
        ax.add_patch(
            patches.Circle(
                (cx, cy),
                radius,
                facecolor="lightblue",
                alpha=0.3,
                edgecolor="blue",
                linewidth=2,
            )
        )
    else:
        ax.add_patch(
            patches.Polygon(
                target,
                facecolor="lightgreen",
                alpha=0.3,
                edgecolor="green",
                linewidth=2,
            )
        )

    path_buffers = [
        LineString(path).buffer(task_radius)
        for path in paths
        if len(path) >= 2
    ]
    if path_buffers:
        covered = unary_union(path_buffers).intersection(target_shape)
        polygons = [covered] if covered.geom_type == "Polygon" else list(getattr(covered, "geoms", []))
        for poly in polygons:
            if poly.geom_type != "Polygon" or poly.is_empty:
                continue
            x, y = poly.exterior.xy
            ax.fill(x, y, color="orange", alpha=0.35)

    colors = ["red", "purple", "darkorange", "teal", "brown", "magenta"]
    all_x = [start[0] for start in starts]
    all_y = [start[1] for start in starts]

    for index, path in enumerate(paths):
        color = colors[index % len(colors)]
        if len(path) >= 2:
            xs, ys = zip(*path)
            ax.plot(xs, ys, color=color, linewidth=1.5, label=f"Drone {index + 1}", zorder=3)
            ax.scatter(xs, ys, color=color, s=8, zorder=4)
            all_x.extend(xs)
            all_y.extend(ys)
        ax.scatter(
            starts[index][0],
            starts[index][1],
            color=color,
            s=120,
            marker="X",
            edgecolor="black",
            linewidth=0.8,
            zorder=10,
        )

    min_x, min_y, max_x, max_y = target_shape.bounds
    all_x.extend([min_x, max_x])
    all_y.extend([min_y, max_y])
    margin = max(task_radius * 2.5, 2.0)

    ax.set_title(f"{title}\nCombined Coverage: {coverage:.2f}%", fontsize=14, pad=20)
    ax.set_xlabel("X Coordinate", fontsize=12)
    ax.set_ylabel("Y Coordinate", fontsize=12)
    ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
    ax.set_ylim(min(all_y) - margin, max(all_y) + margin)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)
    plt.tight_layout()
    plt.show()
    return coverage


def test_circle_coverage():
    print("\n🚀 Testing Circle Coverage (Zigzag)...")
    start = (0, 0)
    circle_target = (10, 10, 8)  # (cx, cy, radius)
    task_radius = 0.8

    path = generate_single_coverage_path(start, circle_target, task_radius)

    coverage = visualize_coverage(
        start=start,
        target=circle_target,
        path=path,
        task_radius=task_radius,
        title="Circle Target Coverage - Zigzag Path"
    )

    print(f"✅ Circle Coverage: {coverage:.2f}%")


def test_polygon_coverage():
    print("\n🚀 Testing Polygon Coverage (Zigzag)...")
    start = (-2, -2)
    polygon_target = [
        (0, 0), (15, 0), (18, 10), (10, 15), (-3, 12)
    ]
    task_radius = 0.8

    path = generate_single_coverage_path(start, polygon_target, task_radius)

    coverage = visualize_coverage(
        start=start,
        target=polygon_target,
        path=path,
        task_radius=task_radius,
        title="Polygon Target Coverage - Zigzag Path"
    )

    print(f"✅ Polygon Coverage: {coverage:.2f}%")


@pytest.mark.parametrize("seed", RANDOM_POLYGON_SEEDS)
def test_random_polygon_coverage(seed):
    start = (-3, -3)
    polygon_target = _generate_random_convex_polygon(seed)
    task_radius = 0.8

    path = generate_single_coverage_path(start, polygon_target, task_radius)
    coverage = calculate_coverage_percentage(path, polygon_target, task_radius)

    assert coverage == pytest.approx(100.0)


@pytest.mark.parametrize("seed", RANDOM_CIRCLE_SEEDS)
def test_random_circle_coverage(seed):
    target = _generate_random_circle(seed)
    start = (target[0] - target[2] - 4.0, target[1] - target[2] - 4.0)
    task_radius = 0.8

    path = generate_single_coverage_path(start, target, task_radius)
    coverage = calculate_coverage_percentage(path, target, task_radius)

    assert coverage == pytest.approx(100.0)


@pytest.mark.parametrize("drone_count,seed", RANDOM_MULTI_POLYGON_CASES)
def test_random_polygon_multi_drone_coverage(drone_count, seed):
    target = _generate_random_convex_polygon(seed)
    starts = _generate_drone_starts(seed + 1000, drone_count)
    task_radius = 0.8

    paths = generate_coverage_path(starts, target, task_radius)

    assert len(paths) == drone_count
    assert [path[0] for path in paths] == starts
    assert _combined_coverage_percentage(paths, target, task_radius) == pytest.approx(100.0)


@pytest.mark.parametrize("drone_count,seed", RANDOM_MULTI_CIRCLE_CASES)
def test_random_circle_multi_drone_coverage(drone_count, seed):
    target = _generate_random_circle(seed)
    starts = _generate_drone_starts(
        seed + 2000,
        drone_count,
        center=(target[0], target[1]),
        radius=target[2] + 10.0,
    )
    task_radius = 0.8

    paths = generate_coverage_path(starts, target, task_radius)

    assert len(paths) == drone_count
    assert [path[0] for path in paths] == starts
    assert _combined_coverage_percentage(paths, target, task_radius) == pytest.approx(100.0)


if __name__ == "__main__":
    test_circle_coverage()
    test_polygon_coverage()
    print("\n🚀 Testing Random Polygon Coverage (Zigzag)...")
    for seed in RANDOM_POLYGON_SEEDS:
        polygon_target = _generate_random_convex_polygon(seed)
        path = generate_single_coverage_path((-3, -3), polygon_target, 0.8)
        coverage = visualize_coverage(
            start=(-3, -3),
            target=polygon_target,
            path=path,
            task_radius=0.8,
            title=f"Random Polygon Coverage - Seed {seed}"
        )
        print(f"✅ Random Polygon Seed {seed}: {coverage:.2f}%")
    print("\n🚀 Testing Random Circle Coverage (Zigzag)...")
    for seed in RANDOM_CIRCLE_SEEDS:
        circle_target = _generate_random_circle(seed)
        start = (circle_target[0] - circle_target[2] - 4.0, circle_target[1] - circle_target[2] - 4.0)
        path = generate_single_coverage_path(start, circle_target, 0.8)
        coverage = visualize_coverage(
            start=start,
            target=circle_target,
            path=path,
            task_radius=0.8,
            title=f"Random Circle Coverage - Seed {seed}"
        )
        print(f"✅ Random Circle Seed {seed}: {coverage:.2f}%")
    print("\n🚀 Testing Multi-Drone Random Coverage Samples...")
    for drone_count, seed in RANDOM_MULTI_POLYGON_CASES:
        polygon_target = _generate_random_convex_polygon(seed)
        starts = _generate_drone_starts(seed + 1000, drone_count)
        paths = generate_coverage_path(starts, polygon_target, 0.8)
        coverage = _plot_multi_drone_coverage(
            starts=starts,
            target=polygon_target,
            paths=paths,
            task_radius=0.8,
            title=f"{drone_count}-Drone Random Polygon Coverage - Seed {seed}",
        )
        path_lengths = [LineString(path).length if len(path) >= 2 else 0.0 for path in paths]
        print(
            f"✅ {drone_count}-Drone Polygon Seed {seed}: "
            f"coverage {coverage:.2f}%, path lengths {[round(length, 2) for length in path_lengths]}"
        )
    for drone_count, seed in RANDOM_MULTI_CIRCLE_CASES:
        circle_target = _generate_random_circle(seed)
        starts = _generate_drone_starts(
            seed + 2000,
            drone_count,
            center=(circle_target[0], circle_target[1]),
            radius=circle_target[2] + 10.0,
        )
        paths = generate_coverage_path(starts, circle_target, 0.8)
        coverage = _plot_multi_drone_coverage(
            starts=starts,
            target=circle_target,
            paths=paths,
            task_radius=0.8,
            title=f"{drone_count}-Drone Random Circle Coverage - Seed {seed}",
        )
        path_lengths = [LineString(path).length if len(path) >= 2 else 0.0 for path in paths]
        print(
            f"✅ {drone_count}-Drone Circle Seed {seed}: "
            f"coverage {coverage:.2f}%, path lengths {[round(length, 2) for length in path_lengths]}"
        )
    print("\n🎉 All tests complete!")
