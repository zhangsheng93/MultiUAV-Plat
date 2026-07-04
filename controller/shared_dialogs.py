#!/usr/bin/env python3
"""
MultiUAV-Plat Control System - Shared Dialog Classes

Reusable dialog classes for both session editor and GUI controller.
Provides consistent UI/UX across different interfaces.

Author: MultiUAV-Plat Control System
Version: Provided by application entrypoint
"""

import tkinter as tk
from tkinter import ttk, messagebox
from api_server import APIServer
import os
import platform
import webbrowser
from typing import Any, Callable, Dict, List, Optional
from utils import (
    parse_vertices_from_text,
    format_vertices_to_text,
    format_number,
    get_polygon_center,
    set_window_geometry_and_center,
    create_new_name,
    validate_polygon_vertices,
)


def create_drone_fields(scrollable_frame, initial_data, show_id=False):
    """
    Shared function to create drone fields for both GUI Controller and Session Editor.

    Args:
        scrollable_frame: The frame to add widgets to
        initial_data: Dictionary with initial drone data
        show_id: Whether to show the ID field (read-only)

    Returns:
        Dictionary mapping field names to their StringVar/widget instances
    """
    pos = initial_data.get('position', {})
    fields = {}
    row = 0

    # ID (read-only, only for session editor)
    if show_id:
        ttk.Label(scrollable_frame, text="ID:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
        id_label = ttk.Label(scrollable_frame, text=initial_data.get('id', ''),
                            foreground='gray')
        id_label.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        row += 1

    # Name
    ttk.Label(scrollable_frame, text="Name:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
    fields['name'] = tk.StringVar(master=scrollable_frame, value=initial_data.get('name', ''))
    ttk.Entry(scrollable_frame, textvariable=fields['name'], width=30).grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
    row += 1

    # Model
    ttk.Label(scrollable_frame, text="Model:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
    fields['model'] = tk.StringVar(master=scrollable_frame, value=initial_data.get('model', 'Model-A'))
    ttk.Entry(scrollable_frame, textvariable=fields['model'], width=30).grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
    row += 1

    # Position X
    ttk.Label(scrollable_frame, text="Position X (m):").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
    fields['pos_x'] = tk.StringVar(master=scrollable_frame, value=format_number(pos.get('x', 0.0)))
    ttk.Entry(scrollable_frame, textvariable=fields['pos_x'], width=30).grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
    row += 1

    # Position Y
    ttk.Label(scrollable_frame, text="Position Y (m):").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
    fields['pos_y'] = tk.StringVar(master=scrollable_frame, value=format_number(pos.get('y', 0.0)))
    ttk.Entry(scrollable_frame, textvariable=fields['pos_y'], width=30).grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
    row += 1

    # Position Z (Altitude)
    ttk.Label(scrollable_frame, text="Altitude (m):").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
    fields['pos_z'] = tk.StringVar(master=scrollable_frame, value=format_number(pos.get('z', 0.0)))
    ttk.Entry(scrollable_frame, textvariable=fields['pos_z'], width=30).grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
    row += 1

    # Heading
    ttk.Label(scrollable_frame, text="Heading (degrees):").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
    fields['heading'] = tk.StringVar(master=scrollable_frame, value=format_number(initial_data.get('heading', 0.0)))
    ttk.Entry(scrollable_frame, textvariable=fields['heading'], width=30).grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
    row += 1

    # Battery Level
    ttk.Label(scrollable_frame, text="Battery Level (%):").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
    fields['battery_level'] = tk.StringVar(master=scrollable_frame, value=format_number(initial_data.get('battery_level', 100.0)))
    ttk.Entry(scrollable_frame, textvariable=fields['battery_level'], width=30).grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
    row += 1

    # Status
    ttk.Label(scrollable_frame, text="Status:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
    fields['status'] = tk.StringVar(master=scrollable_frame, value=initial_data.get('status', 'idle'))
    status_combo = ttk.Combobox(
        scrollable_frame,
        textvariable=fields['status'],
        width=28,
        values=["idle", "hovering", "emergency", "offline"],
        state="readonly"
    )
    status_combo.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
    row += 1

    # Max Speed
    ttk.Label(scrollable_frame, text="Max Speed:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
    fields['max_speed'] = tk.StringVar(master=scrollable_frame, value=format_number(initial_data.get('max_speed', 20.0)))
    ttk.Entry(scrollable_frame, textvariable=fields['max_speed'], width=30).grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
    row += 1

    # Max Altitude
    ttk.Label(scrollable_frame, text="Max Altitude (m):").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
    fields['max_altitude'] = tk.StringVar(master=scrollable_frame, value=format_number(initial_data.get('max_altitude', 120.0)))
    ttk.Entry(scrollable_frame, textvariable=fields['max_altitude'], width=30).grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
    row += 1

    # Battery Capacity
    ttk.Label(scrollable_frame, text="Battery Capacity (mAh):").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
    fields['battery_capacity'] = tk.StringVar(master=scrollable_frame, value=format_number(initial_data.get('battery_capacity', 4000.0)))
    ttk.Entry(scrollable_frame, textvariable=fields['battery_capacity'], width=30).grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
    row += 1

    # Perceived Radius
    ttk.Label(scrollable_frame, text="Perceived Radius (m):").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
    fields['perceived_radius'] = tk.StringVar(master=scrollable_frame, value=format_number(initial_data.get('perceived_radius', 100.0)))
    ttk.Entry(scrollable_frame, textvariable=fields['perceived_radius'], width=30).grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
    row += 1

    # Task Radius
    ttk.Label(scrollable_frame, text="Task Radius (m):").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
    fields['task_radius'] = tk.StringVar(master=scrollable_frame, value=format_number(initial_data.get('task_radius', 10.0)))
    ttk.Entry(scrollable_frame, textvariable=fields['task_radius'], width=30).grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
    row += 1

    scrollable_frame.columnconfigure(1, weight=1)

    return fields


def validate_drone_data(data):
    """
    Shared validation logic for drone data.

    Args:
        data: Dictionary with drone data to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not data.get('name'):
        return False, "Name cannot be empty"

    battery_level = data.get('battery_level', 0)
    if not (0 <= battery_level <= 100):
        return False, "Battery level must be between 0 and 100"

    heading = data.get('heading', 0)
    if not (0 <= heading < 360):
        return False, "Heading must be between 0 and 360"

    if data.get('max_speed', 0) <= 0:
        return False, "Max speed must be greater than 0"

    if data.get('max_altitude', 0) <= 0:
        return False, "Max altitude must be greater than 0"

    if data.get('battery_capacity', 0) <= 0:
        return False, "Battery capacity must be greater than 0"

    if data.get('perceived_radius', 0) <= 0:
        return False, "Perceived radius must be greater than 0"

    if data.get('task_radius', 0) <= 0:
        return False, "Task radius must be greater than 0"

    status = (data.get('status') or '').lower()
    allowed_statuses = {"idle", "hovering", "emergency", "offline"}
    if status not in allowed_statuses:
        return False, "Status must be idle, hovering, emergency, or offline"

    position = data.get('position') or {}
    z = position.get('z', 0)
    if status == "hovering" and z <= 0:
        return False, "Status cannot be hovering when altitude is 0"
    if status == "idle" and z > 0:
        return False, "Status cannot be idle when altitude is above 0"
    if status == "emergency" and z > 0:
        return False, "Status cannot be emergency when altitude is above 0"

    return True, ""


def generate_item_name(item_type: str, api_endpoint: str) -> str:
    """
    Generate default name with auto-incrementing counter for any item type.

    Args:
        item_type: Type of item (e.g., 'Target', 'Obstacle')
        api_endpoint: API endpoint to fetch existing items (e.g., '/targets', '/obstacles')

    Returns:
        Default name like 'New Target 1', 'New Obstacle 1', etc.
    """
    try:
        server = APIServer()
        existing_items = server.api_get_list(api_endpoint, show_error=False)
        
        existing_names = []
        if existing_items is not None:
            existing_names = [item.get('name', '') for item in existing_items]
            
        return create_new_name(f"New {item_type}", exist_list=existing_names)

    except Exception:
        pass
    return f"New {item_type} 1"


def show_about_dialog(
    parent,
    *,
    version: str,
    build: str,
    api_base_url: str,
    api_connected: Optional[bool],
    set_icon: Optional[Callable[[tk.Toplevel], None]] = None,
):
    """Show the shared About dialog used across the application."""
    dialog = tk.Toplevel(parent)
    if set_icon is not None:
        set_icon(dialog)
    dialog.title("About MultiUAV-Plat Control System")
    set_window_geometry_and_center(dialog, 600, 680, parent)
    dialog.resizable(False, False)

    main_frame = ttk.Frame(dialog, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)

    title_frame = ttk.Frame(main_frame)
    title_frame.pack(fill=tk.X, pady=(0, 15))

    ttk.Label(
        title_frame,
        text="MultiUAV-Plat Control System",
        font=("Arial", 18, "bold"),
    ).pack()
    ttk.Label(
        title_frame,
        text="Multi-UAV Coordination & Management Platform",
        font=("Arial", 12),
        foreground="gray",
    ).pack(pady=(5, 0))

    # ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

    info_frame = ttk.LabelFrame(main_frame, text="Version Information", padding="15")
    info_frame.pack(fill=tk.X, pady=(0, 10))
    info_frame.columnconfigure(1, weight=1)

    if api_connected is True:
        api_status = "Connected ✓"
        status_color = "green"
    elif api_connected is False:
        api_status = "Disconnected ✗"
        status_color = "red"
    else:
        api_status = "Status unknown"
        status_color = "gray"

    version_info = [
        ("Version:", version),
        ("Build:", build),
        ("Python Version:", platform.python_version()),
        ("Platform:", f"{platform.system()} {platform.release()}"),
    ]

    for i, (label, value) in enumerate(version_info):
        ttk.Label(info_frame, text=label, font=("Arial", 12, "bold")).grid(
            row=i, column=0, sticky=tk.W, padx=5, pady=3
        )
        ttk.Label(info_frame, text=value, font=("Arial", 12)).grid(
            row=i, column=1, sticky=tk.W, padx=5, pady=3
        )

    api_row = len(version_info)
    ttk.Label(info_frame, text="API Server:", font=("Arial", 12, "bold")).grid(
        row=api_row, column=0, sticky=tk.W, padx=5, pady=3
    )
    api_frame = ttk.Frame(info_frame)
    api_frame.grid(row=api_row, column=1, sticky=tk.W, padx=5, pady=3)
    ttk.Label(api_frame, text=api_base_url, font=("Arial", 12)).pack(side=tk.LEFT)
    ttk.Label(
        api_frame,
        text=api_status,
        font=("Arial", 12),
        foreground=status_color,
    ).pack(side=tk.LEFT, padx=(8, 0))

    features_frame = ttk.LabelFrame(main_frame, text="Key Features", padding="10")
    features_frame.pack(fill=tk.X, pady=(0, 10))

    features = [
        "• Session-based multi-UAV coordination",
        "• Real-time drone monitoring and control",
        "• Dynamic target and obstacle management",
        "• Visual session editor with drag-and-drop",
        "• Task planning and execution tracking",
        "• Environment simulation (weather, terrain)",
        "• JSON-based session import/export",
        "• RESTful API integration",
    ]

    features_text = tk.Text(
        features_frame,
        height=8,
        width=50,
        wrap=tk.WORD,
        bg="#f5f5f5",
        relief=tk.FLAT,
        font=("Arial", 12),
    )
    features_text.pack(fill=tk.X)
    features_text.insert("1.0", "\n".join(features))
    features_text.config(state="disabled")

    references_frame = ttk.LabelFrame(main_frame, text="Copyright & References", padding="10")
    references_frame.pack(fill=tk.X, pady=(10, 0))
    references_frame.columnconfigure(1, weight=1)

    reference_links = [
        ("Paper:", "https://arxiv.org/abs/2606.31073"),
        ("Project:", "https://github.com/zhangsheng93/MultiUAV-Plat"),
        ("Website:", "https://zhangsheng93.github.io/multiuavweb/"),
    ]

    def open_reference_link(url: str):
        try:
            webbrowser.open_new_tab(url)
        except Exception as exc:
            messagebox.showerror("Open Link Failed", f"Could not open link:\n{url}\n\n{exc}", parent=dialog)

    for row, (label, url) in enumerate(reference_links):
        ttk.Label(references_frame, text=label, font=("Arial", 11, "bold")).grid(
            row=row, column=0, sticky=tk.W, padx=(0, 8), pady=2
        )
        link_label = ttk.Label(
            references_frame,
            text=url,
            font=("Arial", 11, "underline"),
            foreground="#0645AD",
            cursor="hand2",
        )
        link_label.grid(row=row, column=1, sticky=tk.W, pady=2)
        link_label.bind("<Button-1>", lambda _event, link=url: open_reference_link(link))

    credits_frame = ttk.Frame(main_frame)
    credits_frame.pack(fill=tk.X, pady=(10, 0))

    ttk.Label(
        credits_frame,
        text="© 2025 MultiUAV-Plat Control System",
        font=("Arial", 12),
        foreground="gray",
    ).pack()
    ttk.Label(
        credits_frame,
        text="Built with Python, Tkinter, and FastAPI",
        font=("Arial", 12),
        foreground="gray",
    ).pack()

    button_frame = ttk.Frame(main_frame)
    button_frame.pack(pady=(15, 0))
    ttk.Button(button_frame, text="Close", command=dialog.destroy, width=15).pack()

    return dialog


MOVING_TARGET_MODES = {"velocity", "path", "stationary"}


def moving_target_has_velocity(velocity: Dict[str, Any] | None) -> bool:
    """Return True when the provided velocity contains any non-zero component."""
    if not isinstance(velocity, dict):
        return False
    return any((velocity.get(axis) or 0) != 0 for axis in ("x", "y", "z"))


def has_duplicate_consecutive_waypoints(moving_path: List[Dict[str, Any]]) -> bool:
    """Detect consecutive duplicate waypoints before the request reaches the server."""
    if len(moving_path) < 2:
        return False

    for previous, current in zip(moving_path, moving_path[1:]):
        if (
            (previous.get("x") == current.get("x")) and
            (previous.get("y") == current.get("y")) and
            (previous.get("z") == current.get("z"))
        ):
            return True
    return False


def derive_moving_target_mode(target_data: Dict[str, Any] | None) -> str:
    """Determine the moving-target mode, preferring the server's canonical field."""
    target_data = target_data or {}
    movement_mode = target_data.get("movement_mode")
    if movement_mode in MOVING_TARGET_MODES:
        return movement_mode

    duration = target_data.get("moving_duration")
    try:
        duration = float(duration)
    except (TypeError, ValueError):
        duration = 10.0

    if duration == 0:
        return "stationary"
    if moving_target_has_velocity(target_data.get("velocity")):
        return "velocity"
    if target_data.get("moving_path"):
        return "path"
    return "velocity"


def normalize_moving_target_state(
    movement_mode: str,
    moving_duration: float,
    velocity: Dict[str, float] | None,
    moving_path: List[Dict[str, float]] | None,
) -> Dict[str, Any]:
    """Normalize moving-target request fields according to the server contract."""
    if movement_mode not in MOVING_TARGET_MODES:
        raise ValueError(f"Unknown movement mode '{movement_mode}'")
    if moving_duration < 0:
        raise ValueError("Duration must be greater than or equal to 0")

    moving_path = list(moving_path or [])

    if has_duplicate_consecutive_waypoints(moving_path):
        raise ValueError("Path cannot contain consecutive duplicate waypoints")

    if movement_mode == "stationary":
        if moving_duration != 0:
            raise ValueError("Stationary mode requires duration to be 0")
        return {
            "moving_duration": 0.0,
            "velocity": None,
            "moving_path": [],
        }

    if moving_duration == 0:
        return {
            "moving_duration": 0.0,
            "velocity": None,
            "moving_path": [],
        }

    if movement_mode == "velocity":
        if not moving_target_has_velocity(velocity):
            raise ValueError("Velocity cannot be zero in velocity-based mode")
        return {
            "moving_duration": moving_duration,
            "velocity": {
                "x": float((velocity or {}).get("x", 0.0)),
                "y": float((velocity or {}).get("y", 0.0)),
                "z": float((velocity or {}).get("z", 0.0)),
            },
            "moving_path": [],
        }

    if not moving_path:
        raise ValueError("Please add at least one waypoint for path-based mode")

    return {
        "moving_duration": moving_duration,
        "velocity": None,
        "moving_path": moving_path,
    }


def format_moving_target_runtime(target_data: Dict[str, Any] | None) -> str:
    """Build a compact runtime summary for moving targets in list displays."""
    target_data = target_data or {}
    if target_data.get("type") != "moving":
        return ""

    movement_mode = derive_moving_target_mode(target_data)
    tracking_status = target_data.get("tracking_status") or "unknown"
    return f"Mode: {movement_mode} | Tracking: {tracking_status}"


class BaseDialog:
    """Base class for all dialogs with common functionality"""

    def __init__(self, parent, title: str, width: int = 400, height: int = 300):
        self.result = None
        self.parent = parent

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        set_window_geometry_and_center(self.dialog, width, height, parent)

    def create_button_frame(self, parent_frame, ok_text="OK", ok_command=None):
        """Create standard button frame and return the OK button for focus"""
        button_frame = ttk.Frame(parent_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ok_button = ttk.Button(button_frame, text=ok_text, command=ok_command or self.on_ok)
        ok_button.pack(side=tk.RIGHT, padx=5)

        return ok_button


class DroneEditDialog(BaseDialog):
    """Shared dialog for adding/editing drones"""

    def __init__(self, parent, edit_mode=False, initial_data=None, show_id=False, show_title=True):
        self.edit_mode = edit_mode
        self.initial_data = initial_data or {}
        self.show_id = show_id
        self.show_title = show_title

        title = "" if not show_title else ("Edit Drone" if edit_mode else "Add New Drone")
        super().__init__(parent, title, width=500, height=650)

        self.create_widgets()
        self.dialog.wait_window()

    def generate_default_name(self):
        """Generate default drone name with auto-incrementing number"""
        try:
            # Try to get existing drones from the parent
            # Parent could be the root window from GUI controller or session editor
            server = APIServer()
            existing_drones = server.api_get_drones(show_error=False)
            
            existing_ids = []
            if existing_drones is not None:
                existing_names = [drone.get('name', '') for drone in existing_drones]

            return create_new_name("New Drone", exist_list=existing_names)

        except Exception:
            pass
        return "New Drone 1"

    def create_widgets(self):
        # Main container with scrollbar support
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create canvas and scrollbar for scrollable content
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Prepare initial data with default name if needed
        data_with_defaults = self.initial_data.copy()
        if not data_with_defaults.get('name') and not self.edit_mode:
            data_with_defaults['name'] = self.generate_default_name()

        # Create all drone fields using shared function
        fields = create_drone_fields(scrollable_frame, data_with_defaults, show_id=self.show_id)

        # Store fields as instance variables for compatibility
        self.name_var = fields['name']
        self.model_var = fields['model']
        self.pos_x_var = fields['pos_x']
        self.pos_y_var = fields['pos_y']
        self.pos_z_var = fields['pos_z']
        self.heading_var = fields['heading']
        self.battery_level_var = fields['battery_level']
        self.status_var = fields['status']
        self.max_speed_var = fields['max_speed']
        self.max_altitude_var = fields['max_altitude']
        self.battery_capacity_var = fields['battery_capacity']
        self.perceived_radius_var = fields['perceived_radius']
        self.task_radius_var = fields['task_radius']

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        button_text = "Save Changes" if self.edit_mode else "Add Drone"
        ok_button = self.create_button_frame(self.dialog, ok_text=button_text)

        # Set focus on OK button
        ok_button.focus_set()

    def on_ok(self):
        """Validate and return results"""
        try:
            self.result = {
                "name": self.name_var.get().strip(),
                "model": self.model_var.get().strip(),
                "position": {
                    "x": float(self.pos_x_var.get()),
                    "y": float(self.pos_y_var.get()),
                    "z": float(self.pos_z_var.get())
                },
                "heading": float(self.heading_var.get()),
                "battery_level": float(self.battery_level_var.get()),
                "status": self.status_var.get(),
                "max_speed": float(self.max_speed_var.get()),
                "max_altitude": float(self.max_altitude_var.get()),
                "battery_capacity": float(self.battery_capacity_var.get()),
                "perceived_radius": float(self.perceived_radius_var.get()),
                "task_radius": float(self.task_radius_var.get())
            }

            # Use shared validation function
            is_valid, error_message = validate_drone_data(self.result)
            if not is_valid:
                messagebox.showerror("Validation Error", error_message)
                return

            if self.result.get("status") == "emergency":
                messagebox.showinfo(
                    "Emergency Status",
                    "Emergency status will automatically change to idle if battery is enough."
                )

            self.dialog.destroy()
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please enter valid numeric values:\n{str(e)}")


class PolygonDialog(BaseDialog):
    """Shared dialog for adding polygon targets or obstacles"""

    def __init__(self, parent, item_type="target", edit_mode=False, initial_data=None):
        self.edit_mode = edit_mode
        self.initial_data = initial_data or {}
        self.item_type = item_type  # "target" or "obstacle"

        title = f"Edit Polygon {item_type.title()}" if edit_mode else f"Add Polygon {item_type.title()}"
        super().__init__(parent, title, width=500, height=500)

        self.create_widgets()
        self.dialog.wait_window()

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        row = 0

        # Name
        ttk.Label(main_frame, text="Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        if not self.edit_mode:
            endpoint = '/targets' if self.item_type == 'target' else '/obstacles'
            item_name = 'Polygon Target' if self.item_type == 'target' else 'Polygon Obstacle'
            default_name = generate_item_name(item_name, endpoint)
        else:
            default_name = self.initial_data.get('name', '')
        self.name_var = tk.StringVar(value=default_name)
        ttk.Entry(main_frame, textvariable=self.name_var, width=35).grid(row=row, column=1, sticky=tk.EW, pady=5)
        row += 1

        # Description
        ttk.Label(main_frame, text="Description:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.description_var = tk.StringVar(value=self.initial_data.get('description', ''))
        ttk.Entry(main_frame, textvariable=self.description_var, width=35).grid(row=row, column=1, sticky=tk.EW, pady=5)
        row += 1

        # Position is auto-calculated from vertices (hidden in UI)

        # Height (only for obstacles, not for targets)
        if self.item_type == "obstacle":
            ttk.Label(main_frame, text="Height (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
            height_value = self.initial_data.get('height', 0.0)
            self.height_var = tk.StringVar(value=format_number(height_value))
            ttk.Entry(main_frame, textvariable=self.height_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
            row += 1
        else:
            # For targets, z is always 0 (not shown)
            self.height_var = None

        # Vertices - User-friendly text format
        vertices_row = row
        ttk.Label(main_frame, text="Vertices (x, y):").grid(row=row, column=0, sticky=tk.NW, pady=5)

        # Create text widget with scrollbar
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=row, column=1, sticky=tk.NSEW, pady=5)

        self.vertices_text = tk.Text(text_frame, width=35, height=10, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.vertices_text.yview)
        self.vertices_text.configure(yscrollcommand=scrollbar.set)

        # Pre-populate with existing data or example
        if self.initial_data.get('vertices'):
            self.vertices_text.insert("1.0", format_vertices_to_text(self.initial_data['vertices']))
        else:
            self.vertices_text.insert("1.0", "25, 10\n10, 10\n10, 25\n25, 25")

        self.vertices_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        row += 1

        # Help text
        help_text = "Format: x, y (one point per line)\nMinimum 3 vertices required\nExample: 25, 10"
        help_label = ttk.Label(main_frame, text=help_text, font=('Arial', 9), foreground='gray')
        help_label.grid(row=row, column=1, sticky=tk.W, pady=(0, 10))
        row += 1

        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(vertices_row, weight=1)  # Make vertices text area expandable

        # Buttons
        button_text = "Save Changes" if self.edit_mode else f"Add {self.item_type.title()}"
        ok_button = self.create_button_frame(self.dialog, ok_text=button_text)

        # Set focus on OK button
        ok_button.focus_set()

    def on_ok(self):
        """Validate and return results"""
        try:
            # Validate name
            name = self.name_var.get().strip()
            if not name:
                messagebox.showerror("Validation Error", "Name cannot be empty")
                return

            # Parse and validate vertices
            vertices_text = self.vertices_text.get("1.0", tk.END).strip()
            if not vertices_text:
                messagebox.showerror("Validation Error", "Please enter at least 3 vertices")
                return

            vertices = parse_vertices_from_text(vertices_text)

            if len(vertices) >= 4 and vertices[0] == vertices[-1]:
                vertices = vertices[:-1]

            is_valid, error_message = validate_polygon_vertices(vertices)
            if not is_valid:
                messagebox.showerror("Validation Error", error_message)
                return

            center_x, center_y = get_polygon_center(vertices)

            # Build result
            self.result = {
                "name": name,
                "description": self.description_var.get().strip(),
                "x": float(center_x),
                "y": float(center_y),
                "vertices": vertices,
            }

            # For obstacles: z=0, height field separate
            # For targets: z=0 (ground level, no height)
            if self.item_type == "obstacle":
                self.result["z"] = 0.0
                self.result["height"] = float(self.height_var.get())
            else:  # target
                self.result["z"] = 0.0

            self.dialog.destroy()

        except ValueError as e:
            messagebox.showerror("Validation Error",
                               f"Invalid input:\n{str(e)}\n\nPlease check your values and vertices format.")


class CircleDialog(BaseDialog):
    """Shared dialog for adding circle targets or obstacles"""

    def __init__(self, parent, item_type="target", edit_mode=False, initial_data=None):
        self.edit_mode = edit_mode
        self.initial_data = initial_data or {}
        self.item_type = item_type  # "target" or "obstacle"

        title = f"Edit Circle {item_type.title()}" if edit_mode else f"Add Circle {item_type.title()}"
        super().__init__(parent, title, width=400, height=350)

        self.create_widgets()
        self.dialog.wait_window()

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Get default values
        pos = self.initial_data.get('position', {})

        row = 0

        # Name
        ttk.Label(main_frame, text="Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        if not self.edit_mode:
            endpoint = '/targets' if self.item_type == 'target' else '/obstacles'
            item_name = 'Circle Target' if self.item_type == 'target' else 'Circle Obstacle'
            default_name = generate_item_name(item_name, endpoint)
        else:
            default_name = self.initial_data.get('name', '')
        self.name_var = tk.StringVar(value=default_name)
        ttk.Entry(main_frame, textvariable=self.name_var, width=30).grid(row=row, column=1, sticky=tk.EW, pady=5)
        row += 1

        # Description
        ttk.Label(main_frame, text="Description:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.description_var = tk.StringVar(value=self.initial_data.get('description', ''))
        ttk.Entry(main_frame, textvariable=self.description_var, width=30).grid(row=row, column=1, sticky=tk.EW, pady=5)
        row += 1

        # Position X
        ttk.Label(main_frame, text="Position X (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.pos_x_var = tk.StringVar(value=format_number(pos.get('x', 0.0)))
        ttk.Entry(main_frame, textvariable=self.pos_x_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Position Y
        ttk.Label(main_frame, text="Position Y (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.pos_y_var = tk.StringVar(value=format_number(pos.get('y', 0.0)))
        ttk.Entry(main_frame, textvariable=self.pos_y_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Height (only for obstacles, not for targets)
        if self.item_type == "obstacle":
            ttk.Label(main_frame, text="Height (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
            height_value = self.initial_data.get('height', 0.0)
            self.height_var = tk.StringVar(value=format_number(height_value))
            ttk.Entry(main_frame, textvariable=self.height_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
            row += 1
        else:
            # For targets, z is always 0 (not shown)
            self.height_var = None

        # Radius
        ttk.Label(main_frame, text="Radius (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.radius_var = tk.StringVar(value=format_number(self.initial_data.get('radius', 10.0)))
        ttk.Entry(main_frame, textvariable=self.radius_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Configure grid
        main_frame.columnconfigure(1, weight=1)

        # Buttons
        button_text = "Save Changes" if self.edit_mode else f"Add {self.item_type.title()}"
        ok_button = self.create_button_frame(self.dialog, ok_text=button_text)

        # Set focus on OK button
        ok_button.focus_set()

    def on_ok(self):
        """Validate and return results"""
        try:
            # Validate name
            name = self.name_var.get().strip()
            if not name:
                messagebox.showerror("Validation Error", "Name cannot be empty")
                return

            # Validate radius
            radius = float(self.radius_var.get())
            if radius <= 0:
                messagebox.showerror("Validation Error", "Radius must be greater than 0")
                return

            # Build result
            self.result = {
                "name": name,
                "description": self.description_var.get().strip(),
                "x": float(self.pos_x_var.get()),
                "y": float(self.pos_y_var.get()),
                "radius": radius,
            }

            # For obstacles: z=0, height field separate
            # For targets: z=0 (ground level, no height)
            if self.item_type == "obstacle":
                self.result["z"] = 0.0
                self.result["height"] = float(self.height_var.get())
            else:  # target
                self.result["z"] = 0.0

            self.dialog.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input",
                               f"Please enter valid numeric values:\n{str(e)}")


class EllipseObstacleDialog(BaseDialog):
    """Shared dialog for adding ellipse obstacles"""

    def __init__(self, parent, edit_mode=False, initial_data=None):
        self.edit_mode = edit_mode
        self.initial_data = initial_data or {}

        title = "Edit Ellipse Obstacle" if edit_mode else "Add Ellipse Obstacle"
        super().__init__(parent, title, width=400, height=400)

        self.create_widgets()
        self.dialog.wait_window()

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Get default values
        pos = self.initial_data.get('position', {})

        row = 0

        # Name
        ttk.Label(main_frame, text="Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        default_name = generate_item_name('Ellipse Obstacle', '/obstacles') if not self.edit_mode else self.initial_data.get('name', '')
        self.name_var = tk.StringVar(value=default_name)
        ttk.Entry(main_frame, textvariable=self.name_var, width=30).grid(row=row, column=1, sticky=tk.EW, pady=5)
        row += 1

        # Description
        ttk.Label(main_frame, text="Description:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.description_var = tk.StringVar(value=self.initial_data.get('description', ''))
        ttk.Entry(main_frame, textvariable=self.description_var, width=30).grid(row=row, column=1, sticky=tk.EW, pady=5)
        row += 1

        # Position X
        ttk.Label(main_frame, text="Position X (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.pos_x_var = tk.StringVar(value=format_number(pos.get('x', 0.0)))
        ttk.Entry(main_frame, textvariable=self.pos_x_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Position Y
        ttk.Label(main_frame, text="Position Y (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.pos_y_var = tk.StringVar(value=format_number(pos.get('y', 0.0)))
        ttk.Entry(main_frame, textvariable=self.pos_y_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Height
        ttk.Label(main_frame, text="Height (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        # For ellipse obstacles, always use 'height' field
        height_value = self.initial_data.get('height', 0.0)
        self.height_var = tk.StringVar(value=format_number(height_value))
        ttk.Entry(main_frame, textvariable=self.height_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Width
        ttk.Label(main_frame, text="Width (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.width_var = tk.StringVar(value=format_number(self.initial_data.get('width', 10.0)))
        ttk.Entry(main_frame, textvariable=self.width_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Length
        ttk.Label(main_frame, text="Length (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.length_var = tk.StringVar(value=format_number(self.initial_data.get('length', 15.0)))
        ttk.Entry(main_frame, textvariable=self.length_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Configure grid
        main_frame.columnconfigure(1, weight=1)

        # Buttons
        button_text = "Save Changes" if self.edit_mode else "Add Obstacle"
        ok_button = self.create_button_frame(self.dialog, ok_text=button_text)

        # Set focus on OK button
        ok_button.focus_set()

    def on_ok(self):
        """Validate and return results"""
        try:
            # Validate name
            name = self.name_var.get().strip()
            if not name:
                messagebox.showerror("Validation Error", "Name cannot be empty")
                return

            # Validate dimensions
            width = float(self.width_var.get())
            length = float(self.length_var.get())
            if width <= 0 or length <= 0:
                messagebox.showerror("Validation Error", "Width and length must be greater than 0")
                return

            # Build result (Ellipse obstacles only)
            self.result = {
                "name": name,
                "description": self.description_var.get().strip(),
                "x": float(self.pos_x_var.get()),
                "y": float(self.pos_y_var.get()),
                "z": 0.0,  # Z position always 0 for obstacles
                "height": float(self.height_var.get()),
                "width": width,
                "length": length,
            }

            self.dialog.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input",
                               f"Please enter valid numeric values:\n{str(e)}")

class PointObstacleDialog(BaseDialog):
    """Shared dialog for adding point obstacles"""

    def __init__(self, parent, edit_mode=False, initial_data=None):
        self.edit_mode = edit_mode
        self.initial_data = initial_data or {}

        title = "Edit Point Obstacle" if edit_mode else "Add Point Obstacle"
        super().__init__(parent, title, width=400, height=350)

        self.create_widgets()
        self.dialog.wait_window()

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Get default values
        pos = self.initial_data.get('position', {})

        row = 0

        # Name
        ttk.Label(main_frame, text="Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        default_name = generate_item_name('Point Obstacle', '/obstacles') if not self.edit_mode else self.initial_data.get('name', '')
        self.name_var = tk.StringVar(value=default_name)
        ttk.Entry(main_frame, textvariable=self.name_var, width=30).grid(row=row, column=1, sticky=tk.EW, pady=5)
        row += 1

        # Description
        ttk.Label(main_frame, text="Description:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.description_var = tk.StringVar(value=self.initial_data.get('description', ''))
        ttk.Entry(main_frame, textvariable=self.description_var, width=30).grid(row=row, column=1, sticky=tk.EW, pady=5)
        row += 1

        # Position X
        ttk.Label(main_frame, text="Position X (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.pos_x_var = tk.StringVar(value=format_number(pos.get('x', 0.0)))
        ttk.Entry(main_frame, textvariable=self.pos_x_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Position Y
        ttk.Label(main_frame, text="Position Y (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.pos_y_var = tk.StringVar(value=format_number(pos.get('y', 0.0)))
        ttk.Entry(main_frame, textvariable=self.pos_y_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Height
        ttk.Label(main_frame, text="Height (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        # For point obstacles, always use 'height' field
        height_value = self.initial_data.get('height', 0.0)
        self.height_var = tk.StringVar(value=format_number(height_value))
        ttk.Entry(main_frame, textvariable=self.height_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Radius (optional for point obstacles)
        ttk.Label(main_frame, text="Radius (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.radius_var = tk.StringVar(value=format_number(self.initial_data.get('radius', 1.0)))
        ttk.Entry(main_frame, textvariable=self.radius_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Configure grid
        main_frame.columnconfigure(1, weight=1)

        # Buttons
        button_text = "Save Changes" if self.edit_mode else "Add Obstacle"
        ok_button = self.create_button_frame(self.dialog, ok_text=button_text)

        # Set focus on OK button
        ok_button.focus_set()

    def on_ok(self):
        """Validate and return results"""
        try:
            # Validate name
            name = self.name_var.get().strip()
            if not name:
                messagebox.showerror("Validation Error", "Name cannot be empty")
                return

            # Validate radius
            radius = float(self.radius_var.get())
            if radius <= 0:
                messagebox.showerror("Validation Error", "Radius must be greater than 0")
                return

            # Build result (Point obstacles only)
            self.result = {
                "name": name,
                "description": self.description_var.get().strip(),
                "x": float(self.pos_x_var.get()),
                "y": float(self.pos_y_var.get()),
                "z": 0.0,  # Z position always 0 for obstacles
                "height": float(self.height_var.get()),
                "radius": radius,
            }

            self.dialog.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input",
                               f"Please enter valid numeric values:\n{str(e)}")


class FixedTargetDialog(BaseDialog):
    """Shared dialog for adding fixed targets (simple point targets)"""

    def __init__(self, parent, edit_mode=False, initial_data=None):
        self.edit_mode = edit_mode
        self.initial_data = initial_data or {}

        title = "Edit Fixed Target" if edit_mode else "Add Fixed Target"
        super().__init__(parent, title, width=400, height=350)

        self.create_widgets()
        self.dialog.wait_window()

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Get default values
        pos = self.initial_data.get('position', {})

        row = 0

        # Name
        ttk.Label(main_frame, text="Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        default_name = generate_item_name('Fixed Target', '/targets') if not self.edit_mode else self.initial_data.get('name', '')
        self.name_var = tk.StringVar(value=default_name)
        ttk.Entry(main_frame, textvariable=self.name_var, width=30).grid(row=row, column=1, sticky=tk.EW, pady=5)
        row += 1

        # Description
        ttk.Label(main_frame, text="Description:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.description_var = tk.StringVar(value=self.initial_data.get('description', ''))
        ttk.Entry(main_frame, textvariable=self.description_var, width=30).grid(row=row, column=1, sticky=tk.EW, pady=5)
        row += 1

        # Position X
        ttk.Label(main_frame, text="Position X (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.pos_x_var = tk.StringVar(value=format_number(pos.get('x', 0.0)))
        ttk.Entry(main_frame, textvariable=self.pos_x_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Position Y
        ttk.Label(main_frame, text="Position Y (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.pos_y_var = tk.StringVar(value=format_number(pos.get('y', 0.0)))
        ttk.Entry(main_frame, textvariable=self.pos_y_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Altitude Z (z position for targets)
        ttk.Label(main_frame, text="Altitude Z (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.altitude_var = tk.StringVar(value=format_number(pos.get('z', 0.0)))
        ttk.Entry(main_frame, textvariable=self.altitude_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Radius
        ttk.Label(main_frame, text="Radius (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.radius_var = tk.StringVar(value=format_number(self.initial_data.get('radius', 10.0)))
        ttk.Entry(main_frame, textvariable=self.radius_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Configure grid
        main_frame.columnconfigure(1, weight=1)

        # Buttons
        button_text = "Save Changes" if self.edit_mode else "Add Target"
        ok_button = self.create_button_frame(self.dialog, ok_text=button_text)

        # Set focus on OK button
        ok_button.focus_set()

    def on_ok(self):
        """Validate and return results"""
        try:
            # Validate name
            name = self.name_var.get().strip()
            if not name:
                messagebox.showerror("Validation Error", "Name cannot be empty")
                return

            # Validate radius
            radius = float(self.radius_var.get())
            if radius <= 0:
                messagebox.showerror("Validation Error", "Radius must be greater than 0")
                return

            # Build result (Fixed targets - use altitude as z position)
            self.result = {
                "name": name,
                "description": self.description_var.get().strip(),
                "x": float(self.pos_x_var.get()),
                "y": float(self.pos_y_var.get()),
                "z": float(self.altitude_var.get()),
                "radius": radius,
            }

            self.dialog.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input",
                               f"Please enter valid numeric values:\n{str(e)}")


class MovingTargetDialog(BaseDialog):
    """Shared dialog for adding moving targets with velocity-based and path-based modes"""

    def __init__(self, parent, edit_mode=False, initial_data=None):
        self.edit_mode = edit_mode
        self.initial_data = initial_data or {}

        title = "Edit Moving Target" if edit_mode else "Add Moving Target"
        super().__init__(parent, title, width=550, height=650)

        self.create_widgets()
        self.dialog.wait_window()

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Get default values
        pos = self.initial_data.get('position', {})
        velocity = self.initial_data.get('velocity') or {}
        moving_path = self.initial_data.get('moving_path') or []
        default_mode = derive_moving_target_mode(self.initial_data)

        row = 0

        # Name
        ttk.Label(main_frame, text="Name:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
        default_name = generate_item_name('Moving Target', '/targets') if not self.edit_mode else self.initial_data.get('name', '')
        self.name_var = tk.StringVar(value=default_name)
        ttk.Entry(main_frame, textvariable=self.name_var, width=40).grid(row=row, column=1, columnspan=2, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Description
        ttk.Label(main_frame, text="Description:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
        self.description_var = tk.StringVar(value=self.initial_data.get('description', ''))
        ttk.Entry(main_frame, textvariable=self.description_var, width=40).grid(row=row, column=1, columnspan=2, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Position X
        ttk.Label(main_frame, text="Position X (m):").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
        self.pos_x_var = tk.StringVar(value=format_number(pos.get('x', 0.0)))
        ttk.Entry(main_frame, textvariable=self.pos_x_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        row += 1

        # Position Y
        ttk.Label(main_frame, text="Position Y (m):").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
        self.pos_y_var = tk.StringVar(value=format_number(pos.get('y', 0.0)))
        ttk.Entry(main_frame, textvariable=self.pos_y_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        row += 1

        # Altitude Z
        ttk.Label(main_frame, text="Altitude Z (m):").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
        self.altitude_var = tk.StringVar(value=format_number(pos.get('z', 0.0)))
        ttk.Entry(main_frame, textvariable=self.altitude_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        row += 1

        # Radius
        ttk.Label(main_frame, text="Radius (m):").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
        self.radius_var = tk.StringVar(value=format_number(self.initial_data.get('radius', 2.0)))
        ttk.Entry(main_frame, textvariable=self.radius_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        row += 1

        # Duration (outside mode-specific frames)
        ttk.Label(main_frame, text="Duration (s):").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
        self.duration_var = tk.StringVar(value=format_number(self.initial_data.get('moving_duration', 10.0)))
        ttk.Entry(main_frame, textvariable=self.duration_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Label(main_frame, text="Time before reversing (velocity) / completing path", font=('TkDefaultFont', 8, 'italic')).grid(row=row, column=2, sticky=tk.W, pady=5, padx=5)
        row += 1

        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=10)
        row += 1

        # Movement Mode Selection
        mode_frame = ttk.LabelFrame(main_frame, text="Movement Mode", padding=10)
        mode_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=5, padx=5)
        row += 1

        self.movement_mode = tk.StringVar(value=default_mode)
        ttk.Radiobutton(mode_frame, text="Velocity-based (Ping-pong movement)", variable=self.movement_mode,
                       value="velocity", command=self.on_mode_change).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(mode_frame, text="Path-based (Follow waypoints)", variable=self.movement_mode,
                       value="path", command=self.on_mode_change).grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(mode_frame, text="Stationary (No movement)", variable=self.movement_mode,
                       value="stationary", command=self.on_mode_change).grid(row=2, column=0, sticky=tk.W, pady=2)

        # Velocity-based settings frame
        self.velocity_frame = ttk.LabelFrame(main_frame, text="Velocity Settings (Priority 1)", padding=10)
        self.velocity_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=5, padx=5)
        row += 1

        vel_row = 0
        ttk.Label(self.velocity_frame, text="Velocity X (m/s):").grid(row=vel_row, column=0, sticky=tk.W, pady=3)
        self.vel_x_var = tk.StringVar(value=format_number(velocity.get('x', 0.0) if velocity else 0.0))
        ttk.Entry(self.velocity_frame, textvariable=self.vel_x_var, width=15).grid(row=vel_row, column=1, sticky=tk.W, pady=3)
        vel_row += 1

        ttk.Label(self.velocity_frame, text="Velocity Y (m/s):").grid(row=vel_row, column=0, sticky=tk.W, pady=3)
        self.vel_y_var = tk.StringVar(value=format_number(velocity.get('y', 0.0) if velocity else 0.0))
        ttk.Entry(self.velocity_frame, textvariable=self.vel_y_var, width=15).grid(row=vel_row, column=1, sticky=tk.W, pady=3)
        vel_row += 1

        ttk.Label(self.velocity_frame, text="Velocity Z (m/s):").grid(row=vel_row, column=0, sticky=tk.W, pady=3)
        self.vel_z_var = tk.StringVar(value=format_number(velocity.get('z', 0.0) if velocity else 0.0))
        ttk.Entry(self.velocity_frame, textvariable=self.vel_z_var, width=15).grid(row=vel_row, column=1, sticky=tk.W, pady=3)

        # Path-based settings frame
        self.path_frame = ttk.LabelFrame(main_frame, text="Path Settings (Priority 2)", padding=10)
        self.path_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=5, padx=5)
        row += 1

        path_row = 0
        # Path points input (comma-separated text)
        ttk.Label(self.path_frame, text="Waypoints:").grid(row=path_row, column=0, sticky=tk.NW, pady=3)

        # Create a text widget for path input
        path_text_frame = ttk.Frame(self.path_frame)
        path_text_frame.grid(row=path_row, column=1, columnspan=2, sticky=tk.EW, pady=3)

        self.path_text = tk.Text(path_text_frame, height=5, width=40, wrap=tk.WORD)
        path_scrollbar = ttk.Scrollbar(path_text_frame, orient="vertical", command=self.path_text.yview)
        self.path_text.configure(yscrollcommand=path_scrollbar.set)

        self.path_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        path_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Load existing path if in edit mode
        if moving_path:
            path_lines = []
            for point in moving_path:
                x = format_number(point.get('x', 0.0))
                y = format_number(point.get('y', 0.0))
                z = format_number(point.get('z', 0.0))
                path_lines.append(f"{x}, {y}, {z}")
            self.path_text.insert('1.0', '\n'.join(path_lines))

        path_row += 1

        # Help text for path input
        help_text = "Enter waypoints, one per line:\n• Two numbers (x, y) - uses target altitude\n• Three numbers (x, y, z) - custom altitude\nExample: 100, 200  or  100, 200, 15"
        help_label = ttk.Label(self.path_frame, text=help_text, font=('TkDefaultFont', 8, 'italic'), foreground='gray')
        help_label.grid(row=path_row, column=1, columnspan=2, sticky=tk.W, pady=3)

        # Configure grid
        main_frame.columnconfigure(1, weight=1)

        # Buttons
        button_text = "Save Changes" if self.edit_mode else "Add Target"
        ok_button = self.create_button_frame(self.dialog, ok_text=button_text)

        # Set focus on OK button
        ok_button.focus_set()

        # Initial mode visibility
        self.on_mode_change()

    def on_mode_change(self):
        """Handle movement mode change"""
        mode = self.movement_mode.get()
        if mode == "velocity":
            # Show velocity frame, hide path frame
            self.velocity_frame.grid()
            self.path_frame.grid_remove()
        elif mode == "path":
            # Show path frame, hide velocity frame
            self.velocity_frame.grid_remove()
            self.path_frame.grid()
        else:
            self.velocity_frame.grid_remove()
            self.path_frame.grid_remove()

    def parse_path_text(self):
        """Parse the path text input into a list of points"""
        path_text = self.path_text.get('1.0', 'end-1c').strip()
        if not path_text:
            return []

        target_altitude = float(self.altitude_var.get())
        moving_path = []
        lines = path_text.split('\n')

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue

            # Split by comma
            parts = [p.strip() for p in line.split(',')]

            if len(parts) == 2:
                # Two numbers: x, y (use target altitude)
                try:
                    x = float(parts[0])
                    y = float(parts[1])
                    moving_path.append({"x": x, "y": y, "z": target_altitude})
                except ValueError:
                    raise ValueError(f"Line {line_num}: Invalid numbers '{line}'")
            elif len(parts) == 3:
                # Three numbers: x, y, z
                try:
                    x = float(parts[0])
                    y = float(parts[1])
                    z = float(parts[2])
                    moving_path.append({"x": x, "y": y, "z": z})
                except ValueError:
                    raise ValueError(f"Line {line_num}: Invalid numbers '{line}'")
            else:
                raise ValueError(f"Line {line_num}: Expected 2 or 3 numbers, got {len(parts)}")

        return moving_path

    def on_ok(self):
        """Validate and return results"""
        try:
            # Validate name
            name = self.name_var.get().strip()
            if not name:
                messagebox.showerror("Validation Error", "Name cannot be empty")
                return

            # Validate radius
            radius = float(self.radius_var.get())
            if radius <= 0:
                messagebox.showerror("Validation Error", "Radius must be greater than 0")
                return

            # Validate duration
            duration = float(self.duration_var.get())
            if duration < 0:
                messagebox.showerror("Validation Error", "Duration must be greater than or equal to 0")
                return

            # Build result based on movement mode
            self.result = {
                "name": name,
                "description": self.description_var.get().strip(),
                "x": float(self.pos_x_var.get()),
                "y": float(self.pos_y_var.get()),
                "z": float(self.altitude_var.get()),
                "radius": radius,
            }

            mode = self.movement_mode.get()
            self.result["movement_mode"] = mode
            velocity = None
            moving_path = []
            if mode == "velocity":
                velocity = {
                    "x": float(self.vel_x_var.get()),
                    "y": float(self.vel_y_var.get()),
                    "z": float(self.vel_z_var.get()),
                }
            elif mode == "path":
                moving_path = self.parse_path_text()

            self.result.update(
                normalize_moving_target_state(
                    movement_mode=mode,
                    moving_duration=duration,
                    velocity=velocity,
                    moving_path=moving_path,
                )
            )

            self.dialog.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input",
                               f"Please enter valid values:\n{str(e)}")


class WaypointTargetDialog(BaseDialog):
    """Shared dialog for adding waypoint targets"""

    def __init__(self, parent, edit_mode=False, initial_data=None):
        self.edit_mode = edit_mode
        self.initial_data = initial_data or {}

        title = "Edit Waypoint Target" if edit_mode else "Add Waypoint Target"
        super().__init__(parent, title, width=500, height=500)

        self.create_widgets()
        self.dialog.wait_window()

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Get default values
        pos = self.initial_data.get('position', {})

        row = 0

        # Name
        ttk.Label(main_frame, text="Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        default_name = generate_item_name('Waypoint Target', '/targets') if not self.edit_mode else self.initial_data.get('name', '')
        self.name_var = tk.StringVar(value=default_name)
        ttk.Entry(main_frame, textvariable=self.name_var, width=35).grid(row=row, column=1, sticky=tk.EW, pady=5)
        row += 1

        # Description
        ttk.Label(main_frame, text="Description:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.description_var = tk.StringVar(value=self.initial_data.get('description', ''))
        ttk.Entry(main_frame, textvariable=self.description_var, width=35).grid(row=row, column=1, sticky=tk.EW, pady=5)
        row += 1

        # Position X (first waypoint)
        ttk.Label(main_frame, text="Position X (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.pos_x_var = tk.StringVar(value=format_number(pos.get('x', 0.0)))
        ttk.Entry(main_frame, textvariable=self.pos_x_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Position Y
        ttk.Label(main_frame, text="Position Y (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.pos_y_var = tk.StringVar(value=format_number(pos.get('y', 0.0)))
        ttk.Entry(main_frame, textvariable=self.pos_y_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Radius
        ttk.Label(main_frame, text="Radius (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.radius_var = tk.StringVar(value=format_number(self.initial_data.get('radius', 10.0)))
        ttk.Entry(main_frame, textvariable=self.radius_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Charge Amount (for charging stations)
        ttk.Label(main_frame, text="Charge Amount:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.charge_amount_var = tk.StringVar(value=format_number(self.initial_data.get('charge_amount', 30.0)))
        ttk.Entry(main_frame, textvariable=self.charge_amount_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        ttk.Label(main_frame, text="Battery charge per use", font=('TkDefaultFont', 8, 'italic')).grid(row=row, column=2, sticky=tk.W, pady=5, padx=5)
        row += 1

        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)

        # Buttons
        button_text = "Save Changes" if self.edit_mode else "Add Target"
        ok_button = self.create_button_frame(self.dialog, ok_text=button_text)

        # Set focus on OK button
        ok_button.focus_set()

    def on_ok(self):
        """Validate and return results"""
        try:
            # Validate name
            name = self.name_var.get().strip()
            if not name:
                messagebox.showerror("Validation Error", "Name cannot be empty")
                return

            # Validate radius
            radius = float(self.radius_var.get())
            if radius <= 0:
                messagebox.showerror("Validation Error", "Radius must be greater than 0")
                return

            # Validate charge amount
            charge_amount = float(self.charge_amount_var.get())
            if charge_amount <= 0:
                messagebox.showerror("Validation Error", "Charge amount must be greater than 0")
                return

            # Build result (Waypoint targets - ground level charging station)
            self.result = {
                "name": name,
                "description": self.description_var.get().strip(),
                "x": float(self.pos_x_var.get()),
                "y": float(self.pos_y_var.get()),
                "z": 0.0,  # Ground level
                "radius": radius,
                "charge_amount": charge_amount
            }

            self.dialog.destroy()

        except ValueError as e:
            messagebox.showerror("Validation Error",
                               f"Invalid input: {str(e)}\n\nPlease check your values.")
