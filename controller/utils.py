#!/usr/bin/env python3
"""
General utility helpers shared throughout the MultiUAV-Plat Control System.

This module combines helper functions that previously lived in several
separate *_utils.py files to make centralized reuse easier.
"""

import json
import logging
import math
import os
import platform
import re
import ctypes
import copy
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from collections.abc import Mapping, Sequence


def calculate_export_id(export_data: Dict[str, Any]) -> str:
    """Calculate the export content id using the shared export hash contract."""
    data_to_hash = copy.deepcopy(export_data)
    data_to_hash.pop("id", None)
    results_json = json.dumps(data_to_hash, sort_keys=True)
    return hashlib.md5(results_json.encode("utf-8")).hexdigest()


def is_export_id_valid(export_data: Dict[str, Any]) -> bool:
    """Return True when an export payload id matches its content."""
    if not isinstance(export_data, dict):
        return False

    export_id = export_data.get("id")
    if not export_id or export_id == "error_calculating_hash":
        return False

    try:
        return calculate_export_id(export_data) == export_id
    except Exception:
        return False


# ============================================================================
# Dialog helpers (formerly dialog_utils.py)
# ============================================================================


_MONITOR_DEFAULTTONEAREST = 2


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", _RECT),
        ("rcWork", _RECT),
        ("dwFlags", ctypes.c_ulong),
    ]


def _clamp_to_bounds(origin: int, size: int, minimum: int, maximum: int) -> int:
    """Clamp a window origin within the provided work area while preserving negative coordinates."""
    available = maximum - minimum
    if available <= size:
        return minimum
    return max(minimum, min(origin, maximum - size))


def _get_windows_monitor_work_area_from_rect(left: int, top: int, right: int, bottom: int) -> Optional[Tuple[int, int, int, int]]:
    """Return monitor work area for the rectangle on Windows, or None on failure."""
    if platform.system() != "Windows":
        return None

    try:
        user32 = ctypes.windll.user32
        rect = _RECT(left, top, right, bottom)
        monitor = user32.MonitorFromRect(ctypes.byref(rect), _MONITOR_DEFAULTTONEAREST)
        if not monitor:
            return None
        info = _MONITORINFO()
        info.cbSize = ctypes.sizeof(_MONITORINFO)
        if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return None
        return (info.rcWork.left, info.rcWork.top, info.rcWork.right, info.rcWork.bottom)
    except Exception:
        return None


def _get_windows_monitor_work_area_from_point(x: int, y: int) -> Optional[Tuple[int, int, int, int]]:
    """Return monitor work area for the point on Windows, or None on failure."""
    if platform.system() != "Windows":
        return None

    try:
        user32 = ctypes.windll.user32
        point = _POINT(x, y)
        monitor = user32.MonitorFromPoint(point, _MONITOR_DEFAULTTONEAREST)
        if not monitor:
            return None
        info = _MONITORINFO()
        info.cbSize = ctypes.sizeof(_MONITORINFO)
        if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return None
        return (info.rcWork.left, info.rcWork.top, info.rcWork.right, info.rcWork.bottom)
    except Exception:
        return None


def parse_vertices_from_text(text: str) -> List[Dict[str, float]]:
    """Parse vertices from user text."""
    vertices: List[Dict[str, float]] = []
    lines = text.strip().split('\n')

    for line_num, line in enumerate(lines, 1):
        line = line.split('#')[0].strip()
        if not line:
            continue

        if ',' in line:
            parts = [part.strip() for part in line.split(',')]
            separator_hint = "Format: 'x, y' (one point per line)"
        else:
            parts = [part for part in line.split() if part.strip()]
            separator_hint = "Format: 'x y' (one point per line)"

        if len(parts) != 2:
            raise ValueError(
                f"Line {line_num}: Expected 2 values (x, y), got {len(parts)}. "
                f"{separator_hint}"
            )

        try:
            x = float(parts[0].strip())
            y = float(parts[1].strip())
        except ValueError as exc:
            raise ValueError(
                f"Line {line_num}: Invalid number format. "
                f"Both x and y must be valid numbers. Error: {exc}"
            ) from exc

        vertices.append({'x': x, 'y': y})

    return vertices


def format_vertices_to_text(vertices: List[Dict[str, float]]) -> str:
    """Format vertices to user-friendly text format."""
    if not vertices:
        return ""

    lines = []
    for vertex in vertices:
        x = vertex.get('x', 0)
        y = vertex.get('y', 0)
        lines.append(f"{format_number(x)}, {format_number(y)}")

    return '\n'.join(lines)


def set_window_geometry_and_center(
    window,
    width: int,
    height: int,
    parent=None,
    *,
    make_transient: bool = True,
    force_transient_on_macos: bool = False,
    grab: bool = True,
    withdraw_first: bool = True,
    show_after: bool = True,
    align_to_pointer: bool = False,
    bring_to_front: bool = False,
) -> None:
    """
    Convenience wrapper to size, (optionally) transient/grab, and center a Tk window.

    Args:
        window: Tk or Toplevel instance.
        width: Desired window width.
        height: Desired window height.
        parent: Optional parent for centering and transient.
        make_transient: If True, call window.transient(parent).
        force_transient_on_macos: If True, allow transient on macOS even when Spaces can hide the dialog.
        grab: If True, call window.grab_set() for modal behavior.
        withdraw_first: If True, hide the window before sizing/centering to avoid flicker.
        show_after: If True, deiconify the window after placement when withdraw_first is used.
        align_to_pointer: If True and no parent, center around current pointer location.
        bring_to_front: If True, lift and briefly set topmost to avoid being hidden.
    """
    should_show_after = False
    if withdraw_first:
        try:
            was_withdrawn = window.state() == 'withdrawn'
            if not was_withdrawn:
                window.withdraw()
            should_show_after = show_after
        except Exception:
            pass

    parent_visible = False
    if parent is not None:
        try:
            parent_visible = bool(parent.winfo_viewable()) and parent.state() != 'withdrawn'
        except Exception:
            parent_visible = False

    allow_transient = make_transient and parent is not None and parent_visible
    if platform.system() == "Darwin" and not force_transient_on_macos:
        allow_transient = False
    if allow_transient:
        try:
            window.transient(parent)
        except Exception:
            pass

    try:
        window.geometry(f"{width}x{height}")
    except Exception:
        # Fall back to centering without resizing
        pass

    if grab:
        try:
            window.grab_set()
        except Exception:
            pass

    # Compute placement
    win_width = width or window.winfo_width() or window.winfo_reqwidth()
    win_height = height or window.winfo_height() or window.winfo_reqheight()
    monitor_work_area = None
    if parent is not None and parent_visible:
        try:
            parent.update_idletasks()
            parent_left = parent.winfo_rootx()
            parent_top = parent.winfo_rooty()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()
            x = parent_left + (parent_width - win_width) // 2
            y = parent_top + (parent_height - win_height) // 2
            monitor_work_area = _get_windows_monitor_work_area_from_rect(
                parent_left,
                parent_top,
                parent_left + parent_width,
                parent_top + parent_height,
            )
        except Exception:
            x = (window.winfo_screenwidth() - win_width) // 2
            y = (window.winfo_screenheight() - win_height) // 2
    else:
        if align_to_pointer or (parent is not None and not parent_visible):
            try:
                pointer_x = window.winfo_pointerx()
                pointer_y = window.winfo_pointery()
                x = pointer_x - win_width // 2
                y = pointer_y - win_height // 2
                monitor_work_area = _get_windows_monitor_work_area_from_point(pointer_x, pointer_y)
            except Exception:
                x = (window.winfo_screenwidth() - win_width) // 2
                y = (window.winfo_screenheight() - win_height) // 2
        else:
            x = (window.winfo_screenwidth() - win_width) // 2
            y = (window.winfo_screenheight() - win_height) // 2

    if platform.system() == "Windows" and monitor_work_area is not None:
        try:
            monitor_left, monitor_top, monitor_right, monitor_bottom = monitor_work_area
            x = _clamp_to_bounds(x, win_width, monitor_left, monitor_right)
            y = _clamp_to_bounds(y, win_height, monitor_top, monitor_bottom)
        except Exception:
            pass

    window.geometry(f"{win_width}x{win_height}+{x}+{y}")

    if withdraw_first and should_show_after:
        try:
            window.deiconify()
        except Exception:
            pass

    if bring_to_front:
        try:
            window.lift()
            if platform.system() != "Darwin":
                window.attributes('-topmost', True)
                window.after_idle(lambda: window.attributes('-topmost', False))
        except Exception:
            pass


# ============================================================================
# Logging helpers (formerly logging_utils.py)
# ============================================================================

_shared_log_file: Optional[str] = None
_shared_handlers: Optional[Tuple[logging.Handler, logging.Handler]] = None


def _get_shared_log_file() -> str:
    """Get or create the shared log file path."""
    global _shared_log_file
    if _shared_log_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        _shared_log_file = f'logs/uav_system_{timestamp}.log'
    return _shared_log_file


def _get_shared_handlers() -> Tuple[logging.Handler, logging.Handler]:
    """Get or create shared handlers for all loggers."""
    global _shared_handlers
    if _shared_handlers is None:
        if not os.path.exists('logs'):
            os.makedirs('logs')

        log_file = _get_shared_log_file()

        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(name)s:%(funcName)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        _shared_handlers = (file_handler, console_handler)

    return _shared_handlers


def setup_shared_logger(module_name: str, log_level: int = logging.INFO) -> logging.Logger:
    """Set up a shared logger that writes to the same log file for all modules."""
    logger = logging.getLogger(module_name)

    if not logger.handlers:
        logger.setLevel(log_level)

        file_handler, console_handler = _get_shared_handlers()

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        logger.info(f"Logger initialized for {module_name}")
        logger.info(f"Shared log file: {_get_shared_log_file()}")

    return logger


# ============================================================================
# Session API helpers (formerly session_api_utils.py)
# ============================================================================

SESSION_COLLECTION_KEYS = {
    "drones",
    "targets",
    "obstacles",
    "environment",
    "command_history",
    "status_history",
    "target_reaches",
    "target_reach_log",
    "area_coverage",
}


def extract_session_metadata(payload: Any) -> Dict[str, Any]:
    """Extract only the session metadata (without large collections)."""
    if not isinstance(payload, dict):
        return {}

    return {
        key: value
        for key, value in payload.items()
        if key not in SESSION_COLLECTION_KEYS
    }


def extract_session_collections(payload: Any) -> Dict[str, Any]:
    """Extract session-related collections (drones, targets, etc.)."""
    if not isinstance(payload, dict):
        return {}

    return {
        key: payload[key]
        for key in SESSION_COLLECTION_KEYS
        if key in payload
    }


def normalize_session_canvas_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize canvas dimensions to canvas_width/canvas_length for API requests."""
    if not isinstance(payload, dict):
        return payload

    normalized = dict(payload)

    def _coerce_number(value: Any) -> Any:
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return value
        return value

    width = normalized.get('canvas_width')
    if width is None:
        width = normalized.get('area_width')
    width = _coerce_number(width)

    length = normalized.get('canvas_length')
    if length is None:
        length = normalized.get('canvas_height')
    if length is None:
        length = normalized.get('area_height')
    length = _coerce_number(length)

    if width is None:
        normalized.pop('canvas_width', None)
    else:
        normalized['canvas_width'] = width

    if length is None:
        normalized.pop('canvas_length', None)
    else:
        normalized['canvas_length'] = length

    normalized.pop('canvas_height', None)
    normalized.pop('area_width', None)
    normalized.pop('area_height', None)

    return normalized


# ============================================================================
# Filename sanitization helpers
# ============================================================================

def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing/replacing unsafe characters.

    Args:
        filename: The filename to sanitize

    Returns:
        Safe filename string suitable for use across different operating systems

    Examples:
        >>> sanitize_filename("My Session: Test/2024")
        'My_Session__Test_2024'
        >>> sanitize_filename("  ..test..  ")
        'test'
        >>> sanitize_filename("New Session 1")
        'New_Session_1'
    """
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')

    # Replace unsafe characters with underscores
    # Covers Windows, Linux, and macOS unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')

    # Remove control characters (ASCII < 32)
    filename = ''.join(char for char in filename if ord(char) >= 32)

    # Limit length (leave room for extension and path components)
    if len(filename) > 200:
        filename = filename[:200]

    # Remove leading/trailing underscores and dots
    filename = filename.strip('._')

    # Ensure we have something left
    if not filename:
        filename = 'file'

    return filename


def create_new_names(name_prefix: str, n: int = 1, exist_list: Optional[List[str]] = None) -> List[str]:
    """Generate n new names based on name_prefix, incrementing from the highest existing index.

    Args:
        name_prefix: The base name to use.
        n: Number of new names to generate.
        exist_list: List of existing names to check against.

    Returns:
        A list of n new names with incremented suffixes.
    """
    prefix = (name_prefix or "").strip()
    explicit_match = re.match(r"^(.*?)(?:\s+(\d+))$", prefix)
    if explicit_match:
        base_prefix = explicit_match.group(1).strip()
        explicit_start = int(explicit_match.group(2))
    else:
        base_prefix = prefix
        explicit_start = 1

    pattern = re.compile(rf"^{re.escape(base_prefix)}(?:\s+(\d+))?$")
    max_existing = 0

    if exist_list:
        for name in exist_list:
            match = pattern.match(name)
            if match:
                num_str = match.group(1)
                if num_str:
                    max_existing = max(max_existing, int(num_str))

    start_num = max(explicit_start, max_existing + 1)
    new_names = []
    for i in range(1, n + 1):
        new_names.append(f"{base_prefix} {start_num + i - 1}")

    return new_names


def create_new_name(name_prefix: str, exist_list: Optional[List[str]] = None) -> str:
    """Generate a single new name based on name_prefix.

    Args:
        name_prefix: The base name to use.
        exist_list: List of existing names to check against.

    Returns:
        A single new name string.
    """
    return create_new_names(name_prefix, n=1, exist_list=exist_list)[0]


# ============================================================================
# Session storage helpers
# ============================================================================

StoragePathLike = Optional[Union[str, Path]]


def _resolve_storage_dir(storage_dir: StoragePathLike, ensure_exists: bool = True) -> Path:
    """Resolve the session storage directory, defaulting to settings."""
    if storage_dir:
        directory = Path(storage_dir).expanduser()
    else:
        from app_settings import DEFAULT_STORAGE_PATH, get_settings

        settings = get_settings()
        configured = settings.get('session_storage_path') or DEFAULT_STORAGE_PATH
        directory = Path(configured).expanduser()

    if ensure_exists:
        directory.mkdir(parents=True, exist_ok=True)

    return directory


def _sanitize_session_name(name: Optional[str]) -> str:
    safe = re.sub(r'[^A-Za-z0-9_-]+', '_', name or '').strip('_')
    return safe or 'session'


def _clean_session_data_for_export(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """Reset runtime/progress tracking fields in session data before export.

    This function creates a clean copy of session data by resetting fields that:
    - Are calculated at runtime (task_progress, coverage statistics)
    - Can be very large (covered_points arrays)
    - Should be recalculated when the session is reloaded

    Args:
        session_data: Original session data dictionary

    Returns:
        Cleaned session data suitable for export/storage
    """
    import copy

    # Create a deep copy to avoid modifying the original
    cleaned = copy.deepcopy(session_data)

    # Define fields and their empty/default states
    runtime_fields_to_reset = {
        'task_progress': None,
        'area_coverage_summary': None,
        'recent_commands': [],
    }

    for field, default_value in runtime_fields_to_reset.items():
        if field in cleaned:
            cleaned[field] = default_value

    # Clean area_coverage data - reset covered_points arrays and covered_area
    if 'area_coverage' in cleaned and isinstance(cleaned['area_coverage'], dict):
        for target_id, coverage_data in cleaned['area_coverage'].items():
            if isinstance(coverage_data, dict):
                # Reset the large covered_points array and runtime stats
                if 'covered_points' in coverage_data:
                    coverage_data['covered_points'] = []
                if 'num_covered_points' in coverage_data:
                    coverage_data['num_covered_points'] = 0
                if 'covered_area' in coverage_data:
                    coverage_data['covered_area'] = 0.0
                if 'coverage_percentage' in coverage_data:
                    coverage_data['coverage_percentage'] = 0.0

    return cleaned


def save_session_to_file(session_data: Dict[str, Any],
                         storage_dir: StoragePathLike = None,
                         target_filepath: Optional[Path] = None) -> Path:
    """Persist a full session payload to disk and return the saved path.

    Args:
        session_data: Session data dictionary to save
        storage_dir: Directory to save in (if target_filepath not specified)
        target_filepath: Specific file path to save to (overrides auto-naming)
    """
    if not isinstance(session_data, dict):
        raise ValueError("session_data must be a dictionary payload")

    session_id = session_data.get('id') or session_data.get('session_id')
    if not session_id:
        raise ValueError("Session data is missing an 'id' field")

    # Clean the session data by removing runtime/progress tracking fields
    cleaned_data = _clean_session_data_for_export(session_data)

    # If target_filepath is provided, use it directly
    if target_filepath:
        target_path = Path(target_filepath)
        # Ensure parent directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        # Use auto-naming based on session name and ID
        session_name = session_data.get('name', 'session')
        target_dir = _resolve_storage_dir(storage_dir)
        safe_name = _sanitize_session_name(session_name)
        target_path = target_dir / f"{safe_name}_{session_id}.json"

        # Remove stale files for the same session id but different names
        for existing in target_dir.glob(f"*_{session_id}.json"):
            if existing != target_path:
                try:
                    existing.unlink()
                except OSError:
                    pass

    with target_path.open('w', encoding='utf-8') as fh:
        json.dump(cleaned_data, fh, indent=2, ensure_ascii=False)

    return target_path


def load_session_from_file(identifier: Union[str, Path],
                           storage_dir: StoragePathLike = None) -> Tuple[Dict[str, Any], Path]:
    """Load a session payload from disk using either a path or session id."""
    candidate_path = Path(identifier)
    resolved_path: Optional[Path] = None

    if candidate_path.exists() and candidate_path.is_file():
        resolved_path = candidate_path
    else:
        session_id = str(identifier).strip()
        if not session_id:
            raise FileNotFoundError("Missing session identifier to load file")
        directory = _resolve_storage_dir(storage_dir, ensure_exists=False)
        matches = sorted(directory.glob(f"*_{session_id}.json"))
        if not matches:
            raise FileNotFoundError(f"No session file found for id '{session_id}' in {directory}")
        resolved_path = matches[-1]

    with resolved_path.open('r', encoding='utf-8') as fh:
        data = json.load(fh)

    if not isinstance(data, dict):
        raise ValueError(f"Session file {resolved_path} does not contain a JSON object")

    return data, resolved_path


def save_current_session_to_file(fetch_session_callback: Callable[[], Optional[Dict[str, Any]]],
                                 storage_dir: StoragePathLike = None,
                                 target_filepath: Optional[Path] = None,
                                 logger: Optional[logging.Logger] = None) -> Optional[Path]:
    """Fetch the current session via callback and persist it using shared settings.

    Args:
        fetch_session_callback: Callback to fetch current session data
        storage_dir: Directory to save in (if target_filepath not specified)
        target_filepath: Specific file path to save to (overrides auto-naming)
        logger: Logger instance for messages
    """
    try:
        session_data = fetch_session_callback()
    except Exception as exc:
        if logger:
            logger.error(f"Failed to fetch current session for saving: {exc}")
        return None

    if not session_data:
        if logger:
            logger.warning("fetch_session_callback returned no data; nothing saved")
        return None

    try:
        saved_path = save_session_to_file(session_data, storage_dir, target_filepath)
        if logger:
            logger.info(f"Session saved successfully to {saved_path}")
        return saved_path
    except Exception as exc:
        if logger:
            logger.error(f"Failed to persist session to file: {exc}")
        return None


def format_number(value: float) -> str:
    if isinstance(value, (int, float)) and value == int(value):
        return str(int(value))
    if isinstance(value, (int, float)):
        return f"{value:.1f}"
    return str(value)

def format_enum_value(value: str) -> str:
    if not value:
        return value
    return value.replace('_', ' ').title()

def distance_point_to_point(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def is_point_in_circle(px: float, py: float, cx: float, cy: float, radius: float) -> bool:
    return distance_point_to_point(px, py, cx, cy) <= radius

def is_point_in_ellipse(px: float, py: float, cx: float, cy: float, width: float, height: float) -> bool:
    if width <= 0 or height <= 0:
        return False
    dx = (px - cx) / width
    dy = (py - cy) / height
    return (dx * dx + dy * dy) <= 1.0

def is_point_in_polygon(px: float, py: float, vertices: List[Dict[str, float]]) -> bool:
    num_vertices = len(vertices)
    if num_vertices < 3:
        return False
    inside = False
    j = num_vertices - 1
    for i in range(num_vertices):
        xi, yi = vertices[i]['x'], vertices[i]['y']
        xj, yj = vertices[j]['x'], vertices[j]['y']
        intersects = ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-9) + xi)
        if intersects:
            inside = not inside
        j = i
    return inside

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
    try:
        from shapely.geometry import Polygon
        from shapely.validation import explain_validity
    except ImportError:
        return False, "Polygon validation requires shapely to be installed"

    if not vertices or len(vertices) < 3:
        return False, "Polygon must have at least 3 vertices"

    try:
        # Extract coords
        coords = []
        for v in vertices:
            if "x" not in v or "y" not in v:
                return False, "All vertices must have 'x' and 'y' coordinates"
            x = float(v["x"])
            y = float(v["y"])
            if not math.isfinite(x) or not math.isfinite(y):
                return False, "All vertices must be finite numbers"
            coords.append((x, y))

        if len(coords) >= 4 and coords[0] == coords[-1]:
            coords = coords[:-1]

        if len(set(coords)) < 3:
            return False, "Polygon must have at least 3 unique vertices"

        for idx in range(1, len(coords)):
            if coords[idx] == coords[idx - 1]:
                return False, "Polygon cannot contain consecutive duplicate vertices"

        # Create polygon
        poly = Polygon(coords)

        if not poly.is_valid:
            return False, f"Invalid polygon: {explain_validity(poly)}"

        if poly.area <= 1e-9:  # Allow for floating point epsilon
            return False, "Polygon must have non-zero area"

        return True, "Valid polygon"
    except Exception as e:
        return False, f"Error validating polygon: {str(e)}"

def get_polygon_bounds(vertices: List[Dict[str, float]]) -> Tuple[float, float, float, float]:
    if not vertices:
        return (0.0, 0.0, 0.0, 0.0)
    min_x = min(v['x'] for v in vertices)
    max_x = max(v['x'] for v in vertices)
    min_y = min(v['y'] for v in vertices)
    max_y = max(v['y'] for v in vertices)
    return (min_x, max_x, min_y, max_y)

def get_polygon_center(vertices: List[Dict[str, float]]) -> Tuple[float, float]:
    if not vertices:
        return (0.0, 0.0)
    cx = sum(v['x'] for v in vertices) / len(vertices)
    cy = sum(v['y'] for v in vertices) / len(vertices)
    return (cx, cy)

def get_polygon_centroid(vertices: List[Dict[str, float]]) -> Tuple[float, float]:
    area = 0.0
    centroid_x = 0.0
    centroid_y = 0.0
    num_vertices = len(vertices)
    for i in range(num_vertices):
        j = (i + 1) % num_vertices
        x_i = vertices[i]['x']
        y_i = vertices[i]['y']
        x_j = vertices[j]['x']
        y_j = vertices[j]['y']
        cross_product = x_i * y_j - x_j * y_i
        area += cross_product
        centroid_x += (x_i + x_j) * cross_product
        centroid_y += (y_i + y_j) * cross_product
    area *= 0.5
    if abs(area) < 1e-9:
        return vertices[0]['x'], vertices[0]['y']
    centroid_x /= (6.0 * area)
    centroid_y /= (6.0 * area)
    return centroid_x, centroid_y

def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))

def distance_point_to_line(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    line_mag = distance_point_to_point(x1, y1, x2, y2)
    if line_mag < 1e-9:
        return distance_point_to_point(px, py, x1, y1)
    u = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (line_mag ** 2)
    u = clamp(u, 0, 1)
    closest_x = x1 + u * (x2 - x1)
    closest_y = y1 + u * (y2 - y1)
    return distance_point_to_point(px, py, closest_x, closest_y)

def snap_value_to_grid(value: float, grid_size: float) -> float:
    if grid_size <= 0:
        return value
    return round(value / grid_size) * grid_size

def snap_to_grid(value: float, grid_size: float) -> float:
    return snap_value_to_grid(value, grid_size)


def to_int(value: Any) -> Optional[int]:
    """Convert to int, returning None on failure or boolean inputs."""
    try:
        if isinstance(value, bool):
            return None
        return int(value)
    except Exception:
        return None


def to_float(value: Any) -> Optional[float]:
    """Convert to float, returning None on failure or boolean inputs."""
    try:
        if isinstance(value, bool):
            return None
        return float(value)
    except Exception:
        return None


def format_timestamp(value: Any) -> str:
    """Format various timestamp types into a readable string."""
    if value is None:
        return '-'
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value)).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            return '-'
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return '-'
        try:
            cleaned = trimmed.replace('Z', '+00:00') if trimmed.endswith('Z') else trimmed
            return datetime.fromisoformat(cleaned).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                return datetime.fromtimestamp(float(trimmed)).strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OSError):
                return trimmed
    return str(value)
