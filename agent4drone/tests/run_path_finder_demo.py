
import sys
import math
import time
import random
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from path_planning import find_path as find_path_current, visualize_path
from path_planning.path_finder_original import find_path as find_path_original


def _path_total(path):
    return sum(
        math.hypot(path[i+1][0]-path[i][0], path[i+1][1]-path[i][1])
        for i in range(len(path)-1)
    )


def _path_preview(path):
    if len(path) <= 10:
        return f"Path: {path}"
    return f"Path (first 5): {path[:5]} ... (last 2): {path[-2:]}"


def _run_planner(label, planner, start, des, obstacles=None, **kwargs):
    t0 = time.perf_counter()
    try:
        path = planner(start, des, known_obstacles=obstacles, **kwargs)
        elapsed = time.perf_counter() - t0
        total = _path_total(path)
        direct = math.hypot(des[0]-start[0], des[1]-start[1])
        avg_seg = total / max(1, len(path) - 1)
        overhead = (total / direct - 1) * 100 if direct > 1e-9 else 0.0
        print(f"\n  {label}")
        print(f"    Status: OK")
        print(f"    Solution time:  {elapsed*1000:.1f} ms")
        print(f"    Direct distance: {direct:.2f}  |  Path distance: {total:.2f}  |  Overhead: {overhead:.1f}%")
        print(f"    Waypoints: {len(path)}  |  Avg segment: {avg_seg:.1f}")
        print(f"    {_path_preview(path)}")
        return {
            "ok": True,
            "elapsed": elapsed,
            "path": path,
            "distance": total,
            "waypoints": len(path),
        }
    except ValueError as e:
        elapsed = time.perf_counter() - t0
        print(f"\n  {label}")
        print(f"    Status: ValueError")
        print(f"    Solution time:  {elapsed*1000:.1f} ms")
        print(f"    Error: {e}")
        return {
            "ok": False,
            "elapsed": elapsed,
            "path": None,
            "error": str(e),
        }


def test_case(name, start, des, obstacles=None, show_viz=True, more_waypoints=False):
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"  Start: {start}  Destination: {des}")
    print(f"  Obstacles: {len(obstacles) if obstacles else 0} item(s)")
    print(f"  Current more_waypoints: {more_waypoints}")

    current = _run_planner(
        "Current: Visibility Graph + A* + Smoothing + Grid Fallback",
        find_path_current,
        start,
        des,
        obstacles=obstacles,
        more_waypoints=more_waypoints,
    )
    original = _run_planner(
        "Original: Visibility Graph + Dijkstra",
        find_path_original,
        start,
        des,
        obstacles=obstacles,
    )

    if current["ok"] and original["ok"]:
        distance_delta = current["distance"] - original["distance"]
        waypoint_delta = current["waypoints"] - original["waypoints"]
        time_delta_ms = (current["elapsed"] - original["elapsed"]) * 1000
        print("\n  Comparison")
        print(f"    Current - Original distance: {distance_delta:+.2f}")
        print(f"    Current - Original waypoints: {waypoint_delta:+d}")
        print(f"    Current - Original time: {time_delta_ms:+.1f} ms")
    elif current["ok"] != original["ok"]:
        print("\n  Comparison")
        print("    Different outcome: one planner found a path and the other raised ValueError")

    if show_viz:
        viz_path = current["path"] or original["path"]
        if viz_path:
            viz_label = "Current" if current["path"] else "Original"
            visualize_path(start, des, viz_path, known_obstacles=obstacles, title=f"{name} ({viz_label})")

    print(f"  DONE")
    return current["elapsed"], original["elapsed"]


def _point_to_line_distance(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    proj_x, proj_y = x1 + t * dx, y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def generate_random_obstacles(n, area_size=50, seed=42, start=None, des=None,
                               path_fraction=0.7, path_width=None, min_radius=1.5, max_radius=4.0):
    rng = random.Random(seed)
    obstacles = []
    sx, sy = start if start else (5, 5)
    ex, ey = des if des else (area_size - 5, area_size - 5)
    corridor_w = path_width if path_width else (math.hypot(ex - sx, ey - sy) * 0.15)
    path_biased = int(n * path_fraction)
    safe_zone = min_radius * 2.5 + max_radius

    def too_close_to_endpoints(x, y):
        if math.hypot(x - sx, y - sy) < safe_zone:
            return True
        if math.hypot(x - ex, y - ey) < safe_zone:
            return True
        return False

    attempts = 0
    while len(obstacles) < n and attempts < n * 50:
        attempts += 1
        if len(obstacles) < path_biased:
            t = rng.uniform(0.05, 0.95)
            x = sx + (ex - sx) * t + rng.uniform(-corridor_w, corridor_w)
            y = sy + (ey - sy) * t + rng.uniform(-corridor_w, corridor_w)
            x = max(1, min(area_size - 1, x))
            y = max(1, min(area_size - 1, y))
        else:
            x = rng.uniform(1, area_size - 1)
            y = rng.uniform(1, area_size - 1)

        if too_close_to_endpoints(x, y):
            continue

        kind = rng.choice(["circle", "polygon"])
        if kind == "circle":
            r = rng.uniform(min_radius, max_radius)
            obstacles.append((x, y, r))
        else:
            n_verts = rng.randint(4, 7)
            angle_step = 2 * math.pi / n_verts
            base_angle = rng.uniform(0, 2 * math.pi)
            r_poly = rng.uniform(min_radius * 0.8, max_radius * 0.8)
            verts = []
            for j in range(n_verts):
                a = base_angle + j * angle_step + rng.uniform(-angle_step * 0.3, angle_step * 0.3)
                vx = x + r_poly * math.cos(a)
                vy = y + r_poly * math.sin(a)
                verts.append((vx, vy))
            verts = list(dict.fromkeys(verts))
            if len(verts) >= 3:
                cx = sum(v[0] for v in verts) / len(verts)
                cy = sum(v[1] for v in verts) / len(verts)
                verts.sort(key=lambda v: math.atan2(v[1] - cy, v[0] - cx))
                if too_close_to_endpoints(cx, cy):
                    continue
                obstacles.append(verts)
    return obstacles


if __name__ == "__main__":
    print("Path Finder - Test & Visualization Demo")
    print("=" * 60)
    timings = []

    # --- Basic tests ---
    timings.append(test_case(
        "1. No obstacles - straight line",
        start=(0, 0), des=(10, 10), obstacles=None
    ))

    timings.append(test_case(
        "2. No obstacles - straight line with more waypoints",
        start=(0, 0), des=(10, 0), obstacles=None, more_waypoints=True
    ))

    timings.append(test_case(
        "3. Point obstacle avoidance",
        start=(0, 5), des=(10, 5), obstacles=[(5, 5)]
    ))

    timings.append(test_case(
        "4. Circle obstacle avoidance",
        start=(0, 5), des=(10, 5), obstacles=[(5, 5, 2)]
    ))

    timings.append(test_case(
        "5. Polygon obstacle avoidance",
        start=(0, 5), des=(10, 5),
        obstacles=[[(3, 3), (7, 3), (7, 7), (3, 7)]]
    ))

    timings.append(test_case(
        "6. Mixed obstacle types",
        start=(0, 0), des=(12, 12),
        obstacles=[(5, 5, 1), (9, 3), [(2, 8), (4, 8), (4, 10), (2, 10)]]
    ))

    # --- Intermediate tests ---
    timings.append(test_case(
        "7. Multiple circle obstacles corridor",
        start=(0, 5), des=(15, 5),
        obstacles=[(4, 3, 1.5), (8, 7, 1.5), (12, 3, 1.5)]
    ))

    timings.append(test_case(
        "8. L-shaped polygon obstacle",
        start=(0, 0), des=(10, 10),
        obstacles=[[(3, 3), (7, 3), (7, 6), (5, 6), (5, 9), (3, 9)]]
    ))

    timings.append(test_case(
        "9. Start inside obstacle (error case)",
        start=(5, 5), des=(20, 20),
        obstacles=[[(0, 0), (10, 0), (10, 10), (0, 10)]]
    ))

    # --- Complex: structured obstacle patterns ---
    timings.append(test_case(
        "10. Dense wall of 15 circles",
        start=(0, 25), des=(50, 25),
        obstacles=[(i * 3 + 3, 25, 1.2) for i in range(15)]
    ))

    timings.append(test_case(
        "11. Zigzag corridor of polygon barriers",
        start=(0, 2), des=(30, 2),
        obstacles=[
            [(3, 0), (5, 0), (5, 4), (3, 4)],
            [(7, 3), (9, 3), (9, 8), (7, 8)],
            [(11, 0), (13, 0), (13, 4), (11, 4)],
            [(15, 3), (17, 3), (17, 8), (15, 8)],
            [(19, 0), (21, 0), (21, 4), (19, 4)],
            [(23, 3), (25, 3), (25, 8), (23, 8)],
            [(27, 0), (29, 0), (29, 4), (27, 4)],
        ]
    ))

    timings.append(test_case(
        "12. Grid of point obstacles (5x5)",
        start=(-1, -1), des=(13, 13),
        obstacles=[(i * 2.5 + 1, j * 2.5 + 1) for i in range(5) for j in range(5)]
    ))

    timings.append(test_case(
        "13. Concentric ring of circles",
        start=(0, 25), des=(50, 25),
        obstacles=[(25 + 15*math.cos(a), 25 + 15*math.sin(a), 2.0)
                    for a in [i * math.pi / 6 for i in range(12)]]
    ))

    timings.append(test_case(
        "14. Diamond formation of polygons",
        start=(0, 15), des=(30, 15),
        obstacles=[
            [(7, 10), (10, 15), (7, 20), (4, 15)],
            [(14, 5), (17, 10), (14, 15), (11, 10)],
            [(14, 15), (17, 20), (14, 25), (11, 20)],
            [(21, 10), (24, 15), (21, 20), (18, 15)],
        ]
    ))

    # --- Complex: random obstacle sets ---
    timings.append(test_case(
        "15. 15 random obstacles (60x60) near path",
        start=(3, 3), des=(57, 57),
        obstacles=generate_random_obstacles(15, area_size=60, seed=10,
                                           start=(3, 3), des=(57, 57),
                                           path_fraction=0.8, path_width=14,
                                           min_radius=2.0, max_radius=5.0)
    ))

    timings.append(test_case(
        "16. 30 random obstacles (80x80) near path",
        start=(3, 3), des=(77, 77),
        obstacles=generate_random_obstacles(30, area_size=80, seed=25,
                                           start=(3, 3), des=(77, 77),
                                           path_fraction=0.85, path_width=16,
                                           min_radius=2.0, max_radius=5.5)
    ))

    timings.append(test_case(
        "17. 60 random obstacles (120x120) near path",
        start=(4, 4), des=(116, 116),
        obstacles=generate_random_obstacles(60, area_size=120, seed=50,
                                           start=(4, 4), des=(116, 116),
                                           path_fraction=0.85, path_width=20,
                                           min_radius=2.5, max_radius=6.0)
    ))

    timings.append(test_case(
        "18. 120 random obstacles (200x200) near path",
        start=(6, 6), des=(194, 194),
        obstacles=generate_random_obstacles(120, area_size=200, seed=100,
                                           start=(6, 6), des=(194, 194),
                                           path_fraction=0.85, path_width=28,
                                           min_radius=2.5, max_radius=6.5)
    ))

    timings.append(test_case(
        "19. 200 random obstacles (350x350) near path",
        start=(8, 8), des=(342, 342),
        obstacles=generate_random_obstacles(200, area_size=350, seed=200,
                                           start=(8, 8), des=(342, 342),
                                           path_fraction=0.85, path_width=35,
                                           min_radius=3.0, max_radius=7.5)
    ))

    # --- Summary ---
    print(f"\n{'='*60}")
    print("Summary - Solution Times")
    print("-"*60)
    print(f"  {'Test':>4}  {'Current':>10}  {'Original':>10}")
    current_total = 0.0
    original_total = 0.0
    for i, (current_t, original_t) in enumerate(timings, 1):
        current_total += current_t
        original_total += original_t
        print(f"  {i:4d}  {current_t*1000:10.1f}  {original_t*1000:10.1f}")
    print("-"*60)
    print(f"  {'Total':>4}  {current_total*1000:10.1f}  {original_total*1000:10.1f}")
    print(f"\nAll tests completed!")
