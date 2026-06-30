from __future__ import annotations

from typing import Any, Iterable, Optional
import html
import io
import math
import time

import pygame
from PIL import Image

from ui.font_utils import safe_sys_font

DEFAULT_UI_FONT = "alibabapuhuiti"

BG_COLOR = (245, 245, 250)
GRID_COLOR = (220, 225, 230)
TEXT_COLOR = (30, 30, 30)
WHITE = (255, 255, 255)
STATUS_OK = (0, 255, 0)
STATUS_WARN = (255, 165, 0)
STATUS_ERROR = (255, 0, 0)
CYAN = (0, 255, 255)
STATUS_BAR_BG = (235, 235, 240)
PANEL_BORDER = (200, 200, 210)
DRONE_PATH_TRAIL_COLOR = (173, 216, 230)

DRONE_COLORS = {
    "idle": (100, 100, 100),
    "ready": (0, 255, 0),
    "taking_off": (0, 255, 255),
    "flying": (0, 0, 255),
    "moving": (255, 165, 0),
    "hovering": (0, 255, 255),
    "landing": (255, 255, 0),
    "emergency": (255, 0, 0),
    "offline": (50, 50, 50),
}

TARGET_COLORS = {
    "fixed": (255, 200, 0),
    "moving": (255, 100, 100),
    "waypoint": (0, 255, 100),
    "circle": (0, 100, 255),
    "polygon": (0, 200, 255),
}

OBSTACLE_COLORS = {
    "point": (21, 21, 30),
    "circle": (139, 69, 19),
    "ellipse": (82, 82, 122),
    "polygon": (105, 105, 105),
}


def format_enum_value(value: str) -> str:
    if not value:
        return value
    return value.replace("_", " ").title()


def _get_attr(obj: Any, name: str, default: Any = None) -> Any:
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default


def _get_position(obj: Any) -> Optional[dict[str, float]]:
    pos = _get_attr(obj, "position")
    if not pos:
        return None
    if isinstance(pos, dict):
        return {
            "x": float(pos.get("x", 0.0)),
            "y": float(pos.get("y", 0.0)),
            "z": float(pos.get("z", 0.0)),
        }
    return {
        "x": float(pos[0]),
        "y": float(pos[1]),
        "z": float(pos[2] if len(pos) > 2 else 0.0),
    }


def _normalize_points(points: Iterable[Any]) -> list[dict[str, float]]:
    normalized = []
    for point in points or []:
        if isinstance(point, dict):
            normalized.append(
                {
                    "x": float(point.get("x", 0.0)),
                    "y": float(point.get("y", 0.0)),
                    "z": float(point.get("z", 0.0)),
                }
            )
        else:
            normalized.append(
                {
                    "x": float(point[0]),
                    "y": float(point[1]),
                    "z": float(point[2] if len(point) > 2 else 0.0),
                }
            )
    return normalized


def _rgb(color: tuple[int, int, int]) -> str:
    return f"rgb({color[0]},{color[1]},{color[2]})"


def _ps_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _measure_text_width(text: str, size: int, font_obj: Any = None) -> int:
    if font_obj is not None:
        try:
            return max(1, int(font_obj.size(text)[0]))
        except Exception:
            pass
    return max(1, int(len(text) * size * 0.68))


def _truncate_text_to_width(text: str, size: int, max_width: int, font_obj: Any = None) -> str:
    if max_width <= 0:
        return ""
    if _measure_text_width(text, size, font_obj) <= max_width:
        return text
    ellipsis = "..."
    if _measure_text_width(ellipsis, size, font_obj) > max_width:
        return ""
    trimmed = text
    while trimmed and _measure_text_width(trimmed + ellipsis, size, font_obj) > max_width:
        trimmed = trimmed[:-1]
    return (trimmed + ellipsis) if trimmed else ellipsis


class SceneBuilder:
    def __init__(self) -> None:
        self.commands: list[dict[str, Any]] = []

    def rect(self, x: float, y: float, width: float, height: float, fill: Optional[tuple[int, int, int]] = None,
             stroke: Optional[tuple[int, int, int]] = None, stroke_width: int = 1) -> None:
        self.commands.append(
            {
                "type": "rect",
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "fill": fill,
                "stroke": stroke,
                "stroke_width": stroke_width,
            }
        )

    def line(self, x1: float, y1: float, x2: float, y2: float, color: tuple[int, int, int], width: int = 1) -> None:
        self.commands.append(
            {"type": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "color": color, "width": width}
        )

    def circle(self, x: float, y: float, radius: float, fill: Optional[tuple[int, int, int]] = None,
               stroke: Optional[tuple[int, int, int]] = None, stroke_width: int = 1) -> None:
        self.commands.append(
            {
                "type": "circle",
                "x": x,
                "y": y,
                "radius": radius,
                "fill": fill,
                "stroke": stroke,
                "stroke_width": stroke_width,
            }
        )

    def ellipse(self, x: float, y: float, radius_x: float, radius_y: float, fill: Optional[tuple[int, int, int]] = None,
                stroke: Optional[tuple[int, int, int]] = None, stroke_width: int = 1) -> None:
        self.commands.append(
            {
                "type": "ellipse",
                "x": x,
                "y": y,
                "radius_x": radius_x,
                "radius_y": radius_y,
                "fill": fill,
                "stroke": stroke,
                "stroke_width": stroke_width,
            }
        )

    def polygon(self, points: list[tuple[float, float]], fill: Optional[tuple[int, int, int]] = None,
                stroke: Optional[tuple[int, int, int]] = None, stroke_width: int = 1) -> None:
        self.commands.append(
            {
                "type": "polygon",
                "points": points,
                "fill": fill,
                "stroke": stroke,
                "stroke_width": stroke_width,
            }
        )

    def text(self, text: str, x: float, y: float, size: int, color: tuple[int, int, int],
             anchor: str = "left") -> None:
        self.commands.append(
            {"type": "text", "text": text, "x": x, "y": y, "size": size, "color": color, "anchor": anchor}
        )


def _compute_viewport(
    drones: list[Any],
    targets: list[Any],
    obstacles: list[Any],
    width: int,
    map_height: int,
    center_x: Optional[float],
    center_y: Optional[float],
    scale_px_per_meter: Optional[float],
) -> tuple[tuple[float, float], float]:
    map_center = (
        (float(center_x), float(center_y))
        if center_x is not None and center_y is not None
        else None
    )
    map_scale = float(scale_px_per_meter) if scale_px_per_meter and scale_px_per_meter > 0 else None

    if map_center is None or map_scale is None:
        bounds: list[tuple[float, float]] = []

        for drone in drones:
            pos = _get_position(drone)
            if pos:
                bounds.extend([(pos["x"], pos["y"]), (pos["x"], pos["y"])])

        for target in targets:
            pos = _get_position(target)
            if not pos:
                continue
            target_type = _get_attr(target, "type")
            if hasattr(target_type, "value"):
                target_type = target_type.value
            radius = float(_get_attr(target, "radius", 0) or 0)
            vertices = _normalize_points(_get_attr(target, "vertices", []) or [])
            if target_type == "polygon" and vertices:
                for vertex in vertices:
                    bounds.append((vertex["x"], vertex["y"]))
            else:
                bounds.extend(
                    [
                        (pos["x"] - radius, pos["y"] - radius),
                        (pos["x"] + radius, pos["y"] + radius),
                    ]
                )

        for obstacle in obstacles:
            pos = _get_position(obstacle)
            if not pos:
                continue
            obstacle_type = _get_attr(obstacle, "type")
            if hasattr(obstacle_type, "value"):
                obstacle_type = obstacle_type.value
            radius = float(_get_attr(obstacle, "radius", 10) or 10)
            vertices = _normalize_points(_get_attr(obstacle, "vertices", []) or [])
            if obstacle_type == "ellipse":
                width_radius = float(_get_attr(obstacle, "width", 10) or 10)
                height_radius = float(_get_attr(obstacle, "length", 10) or 10)
                bounds.extend(
                    [
                        (pos["x"] - width_radius, pos["y"] - height_radius),
                        (pos["x"] + width_radius, pos["y"] + height_radius),
                    ]
                )
            elif obstacle_type == "polygon" and vertices:
                for vertex in vertices:
                    bounds.append((vertex["x"], vertex["y"]))
            else:
                bounds.extend(
                    [
                        (pos["x"] - radius, pos["y"] - radius),
                        (pos["x"] + radius, pos["y"] + radius),
                    ]
                )

        if bounds:
            xs, ys = zip(*bounds)
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            world_w = max(1.0, max_x - min_x) * 1.2
            world_h = max(1.0, max_y - min_y) * 1.2
            if map_center is None:
                map_center = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
            if map_scale is None:
                map_scale = min(width / world_w, map_height / world_h)

        if map_center is None:
            map_center = (0.0, 0.0)
        if map_scale is None:
            map_scale = 5.0

    return map_center, map_scale


def _build_status_entries(
    session: Any,
    drones: list[Any],
    targets: list[Any],
    obstacles: list[Any],
    map_scale: float,
    map_center: tuple[float, float],
    map_height: int,
    width: int,
) -> tuple[list[tuple[str, tuple[int, int, int]]], list[tuple[str, tuple[int, int, int]]]]:
    left_entries: list[tuple[str, tuple[int, int, int]]] = [("System: Ready", STATUS_OK)]
    stats = session.to_dict().get("statistics", {}) if hasattr(session, "to_dict") else {}
    session_time = stats.get("session_time")
    if isinstance(session_time, (int, float)):
        if session_time >= 3600:
            hours = int(session_time // 3600)
            minutes = int((session_time % 3600) // 60)
            seconds = int(session_time % 60)
            left_entries.append((f"Time: {hours:02d}:{minutes:02d}:{seconds:02d}", CYAN))
        else:
            minutes = int(session_time // 60)
            seconds = int(session_time % 60)
            left_entries.append((f"Time: {minutes:02d}:{seconds:02d}", CYAN))

    task_progress = stats.get("task_progress")
    if task_progress and task_progress.get("task_type") != "others":
        if task_progress.get("is_completed"):
            left_entries.append(("Task Finished", STATUS_OK))
        else:
            left_entries.append((f"Task: {task_progress.get('progress_percentage', 0)}%", STATUS_ERROR))

    left_entries.append((f"Dro/Tar/Obs: {len(drones)}/{len(targets)}/{len(obstacles)}", TEXT_COLOR))

    visible_width = width / map_scale if map_scale > 0 else 0.0
    visible_height = map_height / map_scale if map_scale > 0 else 0.0
    lower_left = (map_center[0] - visible_width / 2.0, map_center[1] - visible_height / 2.0)

    right_entries = [
        (f"LowerLeft: ({lower_left[0]:.1f}, {lower_left[1]:.1f})", TEXT_COLOR),
        ("Click: (-, -)", TEXT_COLOR),
        (f"Scale: {round(map_scale, 1)} px/m", TEXT_COLOR),
    ]
    return left_entries, right_entries


def _build_scene(
    session: Any,
    drones: list[Any],
    targets: list[Any],
    obstacles: list[Any],
    width: int,
    height: int,
    center_x: Optional[float],
    center_y: Optional[float],
    scale_px_per_meter: Optional[float],
    show_status: bool,
) -> tuple[SceneBuilder, dict[str, Any]]:
    header_height = 28
    base_width = 1024
    base_height = 768
    scale_factor = min(width / base_width, height / base_height)
    font_size_header = max(10, int(14 * scale_factor))
    font_size_label = max(8, int(10 * scale_factor))
    if not pygame.font.get_init():
        try:
            pygame.font.init()
        except Exception:
            pass
    header_font = safe_sys_font(DEFAULT_UI_FONT, font_size_header)
    label_font = safe_sys_font(DEFAULT_UI_FONT, font_size_label)
    footer_padding = max(6, int(8 * scale_factor))
    footer_height = max(28, header_font.get_linesize() + footer_padding)
    status_bar_height = max(30, label_font.get_linesize() + max(8, int(10 * scale_factor))) if show_status else 0
    map_top = header_height
    map_bottom = height - footer_height - status_bar_height
    map_height = max(1, map_bottom - map_top)

    map_center, map_scale = _compute_viewport(
        drones, targets, obstacles, width, map_height, center_x, center_y, scale_px_per_meter
    )

    label_offset_x = int(5 * scale_factor)
    label_offset_y = int(font_size_label * 0.5)
    line_step = max(int(8 * scale_factor), int(label_font.get_linesize() * 0.75))
    max_text_width = int(150 * scale_factor)

    def world_to_screen(x: float, y: float) -> tuple[int, int]:
        sx = int(width / 2 + (x - map_center[0]) * map_scale)
        sy = int(map_top + map_height / 2 - (y - map_center[1]) * map_scale)
        return sx, sy

    def render_text_safe(builder: SceneBuilder, text: str, x: int, y: int, size: int,
                         color: tuple[int, int, int], max_width: Optional[int] = None) -> None:
        if not text:
            return
        trimmed = text
        if max_width is not None:
            trimmed = _truncate_text_to_width(trimmed, size, max_width, label_font if size == font_size_label else header_font)
        measured_width = _measure_text_width(trimmed, size, label_font if size == font_size_label else header_font)
        approx_height = size + 4
        bounded_x = max(2, min(int(x), max(2, int(width - measured_width - 2))))
        bounded_y = max(map_top + 2, min(int(y), max(map_top + 2, int(map_bottom - approx_height - 2))))
        builder.text(trimmed, bounded_x, bounded_y + size, size, color)

    def render_label_lines(builder: SceneBuilder, lines: list[str], x: int, y: int, max_width: int) -> None:
        for index, text in enumerate(lines):
            render_text_safe(
                builder,
                text,
                x,
                y + index * line_step,
                font_size_label,
                TEXT_COLOR,
                max_width=max_width,
            )

    def get_battery_color(battery_level: float) -> tuple[int, int, int]:
        if battery_level > 40:
            return STATUS_OK
        if battery_level > 10:
            return STATUS_WARN
        return STATUS_ERROR

    def is_target_reached(target: Any) -> bool:
        target_type = _get_attr(target, "type", "fixed")
        if hasattr(target_type, "value"):
            target_type = target_type.value
        if target_type == "moving":
            return _get_attr(target, "tracking_status") == "tracked"
        return bool(_get_attr(target, "is_reached"))

    scene = SceneBuilder()
    scene.rect(0, 0, width, height, fill=BG_COLOR)
    for gx in range(0, width, 20):
        scene.line(gx, map_top, gx, map_bottom, GRID_COLOR, 1)
    for gy in range(map_top, map_bottom, 20):
        scene.line(0, gy, width, gy, GRID_COLOR, 1)

    scene.rect(0, 0, width, header_height, fill=STATUS_BAR_BG)
    scene.line(0, header_height, width, header_height, PANEL_BORDER, 1)
    scene.text(
        f"Session: {getattr(session, 'name', 'Unknown')} • {time.strftime('%Y-%m-%d %H:%M:%S')}",
        10,
        6 + font_size_header,
        font_size_header,
        TEXT_COLOR,
    )

    if show_status:
        path_history = getattr(session, "path_history", {}) or {}
        for drone in drones:
            drone_id = _get_attr(drone, "id")
            positions = _normalize_points(path_history.get(drone_id, []))
            if len(positions) < 2:
                continue
            for start, end in zip(positions[:-1], positions[1:]):
                x1, y1 = world_to_screen(start["x"], start["y"])
                x2, y2 = world_to_screen(end["x"], end["y"])
                scene.line(x1, y1, x2, y2, DRONE_PATH_TRAIL_COLOR, max(1, int(2 * scale_factor)))

    for obstacle in obstacles:
        obstacle_type = _get_attr(obstacle, "type")
        if hasattr(obstacle_type, "value"):
            obstacle_type = obstacle_type.value
        pos = _get_position(obstacle)
        if not pos:
            continue
        sx, sy = world_to_screen(pos["x"], pos["y"])
        color = OBSTACLE_COLORS.get(obstacle_type, (128, 128, 128))
        name = _get_attr(obstacle, "name")
        obstacle_id = _get_attr(obstacle, "id")
        radius = float(_get_attr(obstacle, "radius", 10) or 10)
        vertices = _normalize_points(_get_attr(obstacle, "vertices", []) or [])

        if obstacle_type == "point":
            scene.circle(sx, sy, max(2, int(4 * scale_factor)), fill=color)
            label_x = sx + label_offset_x * 2
            label_y = sy - label_offset_y
        elif obstacle_type == "circle":
            radius_px = max(1, int(radius * map_scale))
            scene.circle(sx, sy, radius_px, fill=color, stroke=WHITE, stroke_width=2)
            label_x = sx + radius_px + label_offset_x
            label_y = sy - label_offset_y
        elif obstacle_type == "ellipse":
            radius_x = max(1, int(float(_get_attr(obstacle, "width", 10) or 10) * map_scale))
            radius_y = max(1, int(float(_get_attr(obstacle, "length", 10) or 10) * map_scale))
            scene.ellipse(
                sx,
                sy,
                radius_x,
                radius_y,
                fill=color,
                stroke=WHITE,
                stroke_width=2,
            )
            label_x = sx + radius_x + label_offset_x
            label_y = sy - label_offset_y
        elif obstacle_type == "polygon" and vertices:
            pts = [world_to_screen(vertex["x"], vertex["y"]) for vertex in vertices]
            if len(pts) >= 3:
                scene.polygon(pts, fill=color, stroke=WHITE, stroke_width=2)
                label_x = max(point[0] for point in pts) + label_offset_x
                label_y = min(point[1] for point in pts) - label_offset_y
            else:
                label_x = sx + label_offset_x * 2
                label_y = sy - label_offset_y
        else:
            size = max(1, int(radius * map_scale))
            scene.rect(sx - size / 2, sy - size / 2, size, size, fill=color)
            label_x = sx + size / 2 + label_offset_x
            label_y = sy - label_offset_y

        if name:
            label_lines = [
                str(name),
                f"Type: {format_enum_value(str(obstacle_type))}",
            ]
            if obstacle_id:
                label_lines.append(f"ID: {obstacle_id}")
            render_label_lines(scene, label_lines, int(label_x), int(label_y), max_text_width)

    area_coverage = getattr(session, "area_coverage", {}) if show_status else {}

    for target in targets:
        target_type = _get_attr(target, "type", "fixed")
        if hasattr(target_type, "value"):
            target_type = target_type.value
        pos = _get_position(target)
        if not pos:
            continue

        sx, sy = world_to_screen(pos["x"], pos["y"])
        radius = float(_get_attr(target, "radius", 0) or 0)
        vertices = _normalize_points(_get_attr(target, "vertices", []) or [])
        name = _get_attr(target, "name") or "Target"
        target_id = _get_attr(target, "id")
        color = TARGET_COLORS.get(target_type, (0, 255, 100))
        if is_target_reached(target) and target_type in ("fixed", "moving"):
            color = STATUS_OK

        if target_type == "fixed":
            size = max(1, int(radius * map_scale))
            scene.rect(sx - size / 2, sy - size / 2, size, size, fill=color)
        elif target_type == "moving":
            size = max(1, int(radius * map_scale))
            scene.polygon([(sx, sy - size), (sx + size, sy), (sx, sy + size), (sx - size, sy)], fill=color)
        elif target_type == "waypoint":
            size = max(1, int(3 * map_scale))
            scene.polygon([(sx, sy - size), (sx + size, sy + size), (sx - size, sy + size)], fill=color)
        elif target_type == "restricted":
            size = max(1, int(radius * map_scale))
            points = []
            for index in range(8):
                angle = index * math.pi / 4
                points.append((sx + size * math.cos(angle), sy + size * math.sin(angle)))
            scene.polygon(points, fill=color)
        elif target_type == "circle":
            scene.circle(sx, sy, max(1, int(radius * map_scale)), fill=color, stroke=WHITE, stroke_width=2)
        elif target_type == "polygon" and vertices:
            pts = [world_to_screen(vertex["x"], vertex["y"]) for vertex in vertices]
            if len(pts) >= 3:
                scene.polygon(pts, fill=color, stroke=WHITE, stroke_width=2)
        else:
            scene.circle(sx, sy, max(1, int(radius * map_scale)), fill=color)

        if show_status and _get_attr(target, "id") in area_coverage:
            coverage_info = area_coverage[_get_attr(target, "id")]
            points = coverage_info.get("covered_points", []) if isinstance(coverage_info, dict) else []
            grid_size = max(2, int(2 * map_scale))
            for point in points:
                px = float(point[0] if not isinstance(point, dict) else point.get("x", 0.0))
                py = float(point[1] if not isinstance(point, dict) else point.get("y", 0.0))
                cx, cy = world_to_screen(px, py)
                scene.rect(cx - grid_size / 2, cy - grid_size / 2, grid_size, grid_size, fill=STATUS_OK)

        target_label_lines = [
            str(name),
            f"Type: {format_enum_value(str(target_type))}",
        ]
        if target_id:
            target_label_lines.append(f"ID: {target_id}")

        if target_type == "polygon" and vertices:
            pts = [world_to_screen(vertex["x"], vertex["y"]) for vertex in vertices]
            if pts:
                render_label_lines(
                    scene,
                    target_label_lines,
                    max(point[0] for point in pts) + label_offset_x,
                    min(point[1] for point in pts) - line_step,
                    max_text_width,
                )
        elif target_type == "circle":
            render_label_lines(
                scene,
                target_label_lines,
                sx + max(1, int(radius * map_scale)) + label_offset_x,
                sy - line_step,
                max_text_width,
            )
        else:
            render_label_lines(
                scene,
                target_label_lines,
                sx + label_offset_x * 2,
                sy - line_step,
                max_text_width,
            )

    for drone in drones:
        pos = _get_position(drone)
        if not pos:
            continue
        sx, sy = world_to_screen(pos["x"], pos["y"])
        status = _get_attr(drone, "status", "idle")
        if hasattr(status, "value"):
            status = status.value
        color = DRONE_COLORS.get(status, (100, 100, 100))
        icon_radius = max(1, int(5 * map_scale))
        scene.circle(sx, sy, icon_radius, fill=color)

        battery_level = float(_get_attr(drone, "battery_level", 100) or 100)
        battery_color = get_battery_color(battery_level)
        ring_width = max(2, int(3 * scale_factor))
        ring_offset = max(3, int(3 * scale_factor))
        scene.circle(sx, sy, icon_radius + ring_offset, stroke=battery_color, stroke_width=ring_width)

        heading_deg = float(_get_attr(drone, "heading", 0) or 0)
        heading_rad = math.radians(heading_deg)
        ind_x = sx + int(icon_radius * 1.5 * math.sin(heading_rad))
        ind_y = sy - int(icon_radius * 1.5 * math.cos(heading_rad))
        scene.line(sx, sy, ind_x, ind_y, WHITE, max(1, int(2 * scale_factor)))

        name = _get_attr(drone, "name") or "Drone"
        render_text_safe(
            scene,
            str(name),
            sx + icon_radius + ring_offset + label_offset_x,
            sy - label_offset_y,
            font_size_label,
            TEXT_COLOR,
            max_width=int(120 * scale_factor),
        )

    summary = f"Drones: {len(drones)} | Targets: {len(targets)} | Obstacles: {len(obstacles)}"
    footer_baseline_y = height - status_bar_height - footer_padding
    scene.text(summary, 10, footer_baseline_y, font_size_header, TEXT_COLOR)

    if show_status:
        left_entries, right_entries = _build_status_entries(
            session, drones, targets, obstacles, map_scale, map_center, map_height, width
        )
        status_y = height - status_bar_height
        scene.rect(0, status_y, width, status_bar_height, fill=STATUS_BAR_BG)
        margin = 10
        gap = 15
        baseline_y = status_y + font_size_label + 8
        available_center_gap = max(80, int(width * 0.12))

        left_width_budget = max(1, (width - available_center_gap) // 2 - margin)
        right_width_budget = max(1, (width - available_center_gap) // 2 - margin)

        left_x = margin
        left_used = 0
        for text, color in left_entries:
            remaining = left_width_budget - left_used
            if remaining <= 0:
                break
            render_text = _truncate_text_to_width(text, font_size_label, remaining, label_font)
            if not render_text:
                break
            text_width = _measure_text_width(render_text, font_size_label, label_font)
            scene.text(render_text, left_x, baseline_y, font_size_label, color)
            left_x += text_width + gap
            left_used += text_width + gap

        right_x = width - margin
        right_used = 0
        for text, color in reversed(right_entries):
            remaining = right_width_budget - right_used
            if remaining <= 0:
                break
            render_text = _truncate_text_to_width(text, font_size_label, remaining, label_font)
            if not render_text:
                break
            text_width = _measure_text_width(render_text, font_size_label, label_font)
            right_x -= text_width
            scene.text(render_text, right_x, baseline_y, font_size_label, color)
            right_x -= gap
            right_used += text_width + gap

    meta = {
        "map_top": map_top,
        "map_bottom": map_bottom,
        "font_size_header": font_size_header,
        "font_size_label": font_size_label,
    }
    return scene, meta


def _render_raster(scene: SceneBuilder, width: int, height: int, meta: dict[str, Any], fmt: str) -> bytes:
    surface = pygame.Surface((width, height))
    surface.fill(BG_COLOR)
    if not pygame.font.get_init():
        try:
            pygame.font.init()
        except Exception:
            pass

    font_cache: dict[int, Any] = {}

    def get_font(size: int):
        if size not in font_cache:
            font_cache[size] = safe_sys_font(DEFAULT_UI_FONT, size)
        return font_cache[size]

    for command in scene.commands:
        cmd_type = command["type"]
        if cmd_type == "rect":
            rect = pygame.Rect(
                int(command["x"]),
                int(command["y"]),
                max(1, int(command["width"])),
                max(1, int(command["height"])),
            )
            if command.get("fill") is not None:
                pygame.draw.rect(surface, command["fill"], rect)
            if command.get("stroke") is not None:
                pygame.draw.rect(surface, command["stroke"], rect, max(1, int(command["stroke_width"])))
        elif cmd_type == "line":
            pygame.draw.line(
                surface,
                command["color"],
                (int(command["x1"]), int(command["y1"])),
                (int(command["x2"]), int(command["y2"])),
                max(1, int(command["width"])),
            )
        elif cmd_type == "circle":
            if command.get("fill") is not None:
                pygame.draw.circle(surface, command["fill"], (int(command["x"]), int(command["y"])), max(1, int(command["radius"])))
            if command.get("stroke") is not None:
                pygame.draw.circle(
                    surface,
                    command["stroke"],
                    (int(command["x"]), int(command["y"])),
                    max(1, int(command["radius"])),
                    max(1, int(command["stroke_width"])),
                )
        elif cmd_type == "ellipse":
            rect = pygame.Rect(
                int(command["x"] - command["radius_x"]),
                int(command["y"] - command["radius_y"]),
                max(1, int(command["radius_x"] * 2)),
                max(1, int(command["radius_y"] * 2)),
            )
            if command.get("fill") is not None:
                pygame.draw.ellipse(surface, command["fill"], rect)
            if command.get("stroke") is not None:
                pygame.draw.ellipse(surface, command["stroke"], rect, max(1, int(command["stroke_width"])))
        elif cmd_type == "polygon":
            points = [(int(x), int(y)) for x, y in command["points"]]
            if command.get("fill") is not None:
                pygame.draw.polygon(surface, command["fill"], points)
            if command.get("stroke") is not None:
                pygame.draw.polygon(surface, command["stroke"], points, max(1, int(command["stroke_width"])))
        elif cmd_type == "text":
            font = get_font(int(command["size"]))
            text_surface = font.render(command["text"], True, command["color"])
            surface.blit(text_surface, (int(command["x"]), int(command["y"] - command["size"])))

    raw = pygame.image.tostring(surface, "RGB")
    img = Image.frombytes("RGB", (width, height), raw)
    buf = io.BytesIO()
    fmt_lower = fmt.lower()
    if fmt_lower in ("jpg", "jpeg"):
        img.save(buf, format="JPEG")
    elif fmt_lower == "png":
        img.save(buf, format="PNG")
    else:
        img.save(buf, format="PDF")
    return buf.getvalue()


def _render_svg(scene: SceneBuilder, width: int, height: int) -> bytes:
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    ]
    for command in scene.commands:
        cmd_type = command["type"]
        if cmd_type == "rect":
            attrs = [
                f'x="{command["x"]:.2f}"',
                f'y="{command["y"]:.2f}"',
                f'width="{command["width"]:.2f}"',
                f'height="{command["height"]:.2f}"',
                f'fill="{_rgb(command["fill"])}"' if command.get("fill") is not None else 'fill="none"',
            ]
            if command.get("stroke") is not None:
                attrs.extend(
                    [
                        f'stroke="{_rgb(command["stroke"])}"',
                        f'stroke-width="{command["stroke_width"]}"',
                    ]
                )
            lines.append(f"  <rect {' '.join(attrs)} />")
        elif cmd_type == "line":
            lines.append(
                "  "
                + f'<line x1="{command["x1"]:.2f}" y1="{command["y1"]:.2f}" '
                + f'x2="{command["x2"]:.2f}" y2="{command["y2"]:.2f}" '
                + f'stroke="{_rgb(command["color"])}" stroke-width="{command["width"]}" />'
            )
        elif cmd_type == "circle":
            attrs = [
                f'cx="{command["x"]:.2f}"',
                f'cy="{command["y"]:.2f}"',
                f'r="{command["radius"]:.2f}"',
                f'fill="{_rgb(command["fill"])}"' if command.get("fill") is not None else 'fill="none"',
            ]
            if command.get("stroke") is not None:
                attrs.extend(
                    [
                        f'stroke="{_rgb(command["stroke"])}"',
                        f'stroke-width="{command["stroke_width"]}"',
                    ]
                )
            lines.append(f"  <circle {' '.join(attrs)} />")
        elif cmd_type == "ellipse":
            attrs = [
                f'cx="{command["x"]:.2f}"',
                f'cy="{command["y"]:.2f}"',
                f'rx="{command["radius_x"]:.2f}"',
                f'ry="{command["radius_y"]:.2f}"',
                f'fill="{_rgb(command["fill"])}"' if command.get("fill") is not None else 'fill="none"',
            ]
            if command.get("stroke") is not None:
                attrs.extend(
                    [
                        f'stroke="{_rgb(command["stroke"])}"',
                        f'stroke-width="{command["stroke_width"]}"',
                    ]
                )
            lines.append(f"  <ellipse {' '.join(attrs)} />")
        elif cmd_type == "polygon":
            points = " ".join(f"{x:.2f},{y:.2f}" for x, y in command["points"])
            attrs = [
                f'points="{points}"',
                f'fill="{_rgb(command["fill"])}"' if command.get("fill") is not None else 'fill="none"',
            ]
            if command.get("stroke") is not None:
                attrs.extend(
                    [
                        f'stroke="{_rgb(command["stroke"])}"',
                        f'stroke-width="{command["stroke_width"]}"',
                    ]
                )
            lines.append(f"  <polygon {' '.join(attrs)} />")
        elif cmd_type == "text":
            lines.append(
                "  "
                + f'<text x="{command["x"]:.2f}" y="{command["y"]:.2f}" '
                + f'font-size="{command["size"]}" font-family="Helvetica, Arial, sans-serif" '
                + f'fill="{_rgb(command["color"])}">{html.escape(command["text"])}</text>'
            )
    lines.append("</svg>")
    return "\n".join(lines).encode("utf-8")


def _render_eps(scene: SceneBuilder, width: int, height: int) -> bytes:
    lines = [
        "%!PS-Adobe-3.0 EPSF-3.0",
        f"%%BoundingBox: 0 0 {width} {height}",
        "1 setlinejoin",
        "1 setlinecap",
    ]

    def y(value: float) -> float:
        return height - value

    def set_color(color: tuple[int, int, int]) -> str:
        return f"{color[0] / 255:.4f} {color[1] / 255:.4f} {color[2] / 255:.4f} setrgbcolor"

    for command in scene.commands:
        cmd_type = command["type"]
        if cmd_type == "rect":
            x = command["x"]
            y0 = y(command["y"] + command["height"])
            w = command["width"]
            h = command["height"]
            if command.get("fill") is not None:
                lines.extend(
                    [
                        "gsave",
                        set_color(command["fill"]),
                        "newpath",
                        f"{x:.2f} {y0:.2f} moveto",
                        f"{w:.2f} 0 rlineto",
                        f"0 {h:.2f} rlineto",
                        f"{-w:.2f} 0 rlineto",
                        "closepath fill",
                        "grestore",
                    ]
                )
            if command.get("stroke") is not None:
                lines.extend(
                    [
                        "gsave",
                        set_color(command["stroke"]),
                        f'{command["stroke_width"]} setlinewidth',
                        "newpath",
                        f"{x:.2f} {y0:.2f} moveto",
                        f"{w:.2f} 0 rlineto",
                        f"0 {h:.2f} rlineto",
                        f"{-w:.2f} 0 rlineto",
                        "closepath stroke",
                        "grestore",
                    ]
                )
        elif cmd_type == "line":
            lines.extend(
                [
                    "gsave",
                    set_color(command["color"]),
                    f'{command["width"]} setlinewidth',
                    "newpath",
                    f'{command["x1"]:.2f} {y(command["y1"]):.2f} moveto',
                    f'{command["x2"]:.2f} {y(command["y2"]):.2f} lineto',
                    "stroke",
                    "grestore",
                ]
            )
        elif cmd_type == "circle":
            if command.get("fill") is not None:
                lines.extend(
                    [
                        "gsave",
                        set_color(command["fill"]),
                        "newpath",
                        f'{command["x"]:.2f} {y(command["y"]):.2f} {command["radius"]:.2f} 0 360 arc fill',
                        "grestore",
                    ]
                )
            if command.get("stroke") is not None:
                lines.extend(
                    [
                        "gsave",
                        set_color(command["stroke"]),
                        f'{command["stroke_width"]} setlinewidth',
                        "newpath",
                        f'{command["x"]:.2f} {y(command["y"]):.2f} {command["radius"]:.2f} 0 360 arc stroke',
                        "grestore",
                    ]
                )
        elif cmd_type == "ellipse":
            lines.extend(["gsave", f'{command["x"]:.2f} {y(command["y"]):.2f} translate'])
            lines.append(f'{command["radius_x"]:.2f} {command["radius_y"]:.2f} scale')
            if command.get("fill") is not None:
                lines.extend(
                    [
                        "gsave",
                        set_color(command["fill"]),
                        "newpath 0 0 1 0 360 arc fill",
                        "grestore",
                    ]
                )
            if command.get("stroke") is not None:
                lines.extend(
                    [
                        "gsave",
                        set_color(command["stroke"]),
                        f'{max(command["stroke_width"] / max(command["radius_x"], command["radius_y"]), 0.1):.4f} setlinewidth',
                        "newpath 0 0 1 0 360 arc stroke",
                        "grestore",
                    ]
                )
            lines.append("grestore")
        elif cmd_type == "polygon":
            points = command["points"]
            if not points:
                continue
            if command.get("fill") is not None:
                lines.extend(["gsave", set_color(command["fill"]), "newpath"])
                first_x, first_y = points[0]
                lines.append(f"{first_x:.2f} {y(first_y):.2f} moveto")
                for px, py in points[1:]:
                    lines.append(f"{px:.2f} {y(py):.2f} lineto")
                lines.extend(["closepath fill", "grestore"])
            if command.get("stroke") is not None:
                lines.extend(
                    ["gsave", set_color(command["stroke"]), f'{command["stroke_width"]} setlinewidth', "newpath"]
                )
                first_x, first_y = points[0]
                lines.append(f"{first_x:.2f} {y(first_y):.2f} moveto")
                for px, py in points[1:]:
                    lines.append(f"{px:.2f} {y(py):.2f} lineto")
                lines.extend(["closepath stroke", "grestore"])
        elif cmd_type == "text":
            lines.extend(
                [
                    "gsave",
                    set_color(command["color"]),
                    f'/Helvetica findfont {command["size"]} scalefont setfont',
                    f'{command["x"]:.2f} {y(command["y"]):.2f} moveto',
                    f'({_ps_escape(command["text"])}) show',
                    "grestore",
                ]
            )

    lines.extend(["showpage", "%%EOF"])
    return "\n".join(lines).encode("utf-8")


def generate_session_screenshot(
    session: Any,
    drones: Iterable[Any],
    targets: Iterable[Any],
    obstacles: Iterable[Any],
    fmt: str = "png",
    width: int = 1024,
    height: int = 768,
    center_x: Optional[float] = None,
    center_y: Optional[float] = None,
    scale_px_per_meter: Optional[float] = None,
    show_status: bool = False,
) -> Optional[bytes]:
    """Render a static image of the current session UI to PNG/JPG/PDF/SVG/EPS bytes."""
    if session is None:
        return None

    drones = list(drones)
    targets = list(targets)
    obstacles = list(obstacles)

    scene, meta = _build_scene(
        session=session,
        drones=drones,
        targets=targets,
        obstacles=obstacles,
        width=width,
        height=height,
        center_x=center_x,
        center_y=center_y,
        scale_px_per_meter=scale_px_per_meter,
        show_status=show_status,
    )

    fmt_lower = fmt.lower()
    if fmt_lower in ("png", "jpg", "jpeg", "pdf"):
        return _render_raster(scene, width, height, meta, fmt_lower)
    if fmt_lower == "svg":
        return _render_svg(scene, width, height)
    if fmt_lower == "eps":
        return _render_eps(scene, width, height)
    return _render_raster(scene, width, height, meta, "png")
