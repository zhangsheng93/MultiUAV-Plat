#!/usr/bin/env python3
"""
MultiUAV-Plat Control System - Session Editor Dialogs

Attribute editing dialogs for drones, targets, and obstacles.

Author: MultiUAV-Plat Control System
Version: Provided by application entrypoint
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any
import uuid
from utils import (
    parse_vertices_from_text,
    format_vertices_to_text,
    format_number,
    get_polygon_center,
    set_window_geometry_and_center,
    validate_polygon_vertices,
)
from shared_dialogs import (
    create_drone_fields,
    validate_drone_data,
    derive_moving_target_mode,
    normalize_moving_target_state,
)


POLYGON_SAMPLE_TEXT = "25, 10\n10, 10\n10, 25\n25, 25"


def ensure_polygon_sample(text_widget: tk.Text) -> None:
    if text_widget.get("1.0", tk.END).strip():
        return
    text_widget.insert("1.0", POLYGON_SAMPLE_TEXT)


def generate_default_name(item_type: str, existing_items: list) -> str:
    """
    Generate a default name with counter for new items.

    Args:
        item_type: Type of item ('Drone', 'Target', 'Obstacle')
        existing_items: List of existing items with 'name' field

    Returns:
        Default name like 'New Drone 1', 'New Target 1', etc.
    """
    existing_names = [item.get('name', '') for item in existing_items]
    counter = 1
    while f"New {item_type} {counter}" in existing_names:
        counter += 1
    return f"New {item_type} {counter}"


def format_moving_path_to_text(moving_path: list) -> str:
    """Format moving path waypoints into multi-line text."""
    if not moving_path:
        return ""
    lines = []
    for point in moving_path:
        x = format_number(point.get('x', 0.0))
        y = format_number(point.get('y', 0.0))
        z = format_number(point.get('z', 0.0))
        lines.append(f"{x}, {y}, {z}")
    return "\n".join(lines)


def parse_moving_path_text(path_text: str, target_altitude: float) -> list:
    """Parse moving path text input into a list of waypoint dicts."""
    path_text = path_text.strip()
    if not path_text:
        return []

    moving_path = []
    lines = path_text.split('\n')
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(',')]
        if len(parts) == 2:
            try:
                x = float(parts[0])
                y = float(parts[1])
                moving_path.append({"x": x, "y": y, "z": target_altitude})
            except ValueError:
                raise ValueError(f"Line {line_num}: Invalid numbers '{line}'")
        elif len(parts) == 3:
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


class AttributeEditorDialog:
    """Base class for attribute editing dialogs driven from the pygame event loop"""

    _root = None

    def __init__(self, title: str, item_data: Dict[str, Any]):
        """Initialize attribute editor dialog

        Args:
            title: Dialog title
            item_data: Item data dictionary to edit
        """
        # Dialog state we expose back to the pygame loop
        self.result = None
        self.item_data = item_data.copy()  # Work on a copy
        self.closed = False
        self.title = title

        # Tk root is a singleton so all dialogs share the same app context
        if AttributeEditorDialog._root is None:
            AttributeEditorDialog._root = tk.Tk()
            AttributeEditorDialog._root.withdraw()
            # Process initial events to ensure root is properly initialized
            AttributeEditorDialog._root.update_idletasks()

        # Create the actual dialog window
        self.dialog = tk.Toplevel(AttributeEditorDialog._root)
        self.dialog.title(self.title)
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)

        # Build UI content in the concrete subclass
        self.create_widgets()

        # Finalize window placement and focus once widgets exist
        set_window_geometry_and_center(
            self.dialog,
            500,
            600,
            None,
            make_transient=False,
            align_to_pointer=True,
            bring_to_front=True
        )

        # Explicitly show the dialog window
        self.dialog.deiconify()

        # Force immediate visibility and bring to front
        self.dialog.update_idletasks()
        self.dialog.update()

        # Bring to front and focus
        self.dialog.lift()
        self.dialog.focus_force()
        self.dialog.attributes('-topmost', True)
        self.dialog.after_idle(lambda: self.dialog.attributes('-topmost', False))

    def create_widgets(self):
        """Create dialog widgets - to be overridden by subclasses"""
        pass

    def create_button_frame(self, parent):
        """Create OK/Cancel button frame"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        ttk.Button(button_frame, text="Save", command=self.on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT)

        return button_frame

    def on_ok(self):
        """Handle OK button - to be overridden by subclasses"""
        self.result = self.item_data
        self.closed = True
        if self.dialog is not None:
            try:
                if self.dialog.winfo_exists():
                    self.dialog.destroy()
            except (tk.TclError, AttributeError):
                pass
            finally:
                self.dialog = None

    def on_cancel(self):
        """Handle Cancel button"""
        self.result = None
        self.closed = True
        if self.dialog is not None:
            try:
                if self.dialog.winfo_exists():
                    self.dialog.destroy()
            except (tk.TclError, AttributeError):
                pass
            finally:
                self.dialog = None

    def poll_events(self):
        """Drive Tk events for the dialog from the pygame loop"""
        if self.dialog is None:
            self.closed = True
            return

        try:
            if self.dialog.winfo_exists():
                self.dialog.update()
            else:
                self.closed = True
                self.dialog = None
        except (tk.TclError, AttributeError):
            # Tk raises when window already destroyed; treat as closed
            self.closed = True
            self.dialog = None

    def is_closed(self) -> bool:
        """Check if dialog has been closed"""
        if self.closed:
            return True
        if self.dialog is None:
            return True
        try:
            return not bool(self.dialog.winfo_exists())
        except (tk.TclError, AttributeError):
            return True


class DroneEditorDialog(AttributeEditorDialog):
    """Dialog for editing drone attributes"""

    def create_widgets(self):
        """Create drone editor widgets using shared function"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollable frame for fields
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Use shared function to create all drone fields
        fields = create_drone_fields(scrollable_frame, self.item_data, show_id=True)

        # Store fields with session_editor naming convention
        self.fields = {
            'name': fields['name'],
            'model': fields['model'],
            'position_x': fields['pos_x'],
            'position_y': fields['pos_y'],
            'position_z': fields['pos_z'],
            'heading': fields['heading'],
            'battery_level': fields['battery_level'],
            'status': fields['status'],
            'max_speed': fields['max_speed'],
            'max_altitude': fields['max_altitude'],
            'battery_capacity': fields['battery_capacity'],
            'perceived_radius': fields['perceived_radius'],
            'task_radius': fields['task_radius']
        }

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        self.create_button_frame(self.dialog)

    def on_ok(self):
        """Validate and save drone data using shared validation"""
        try:
            # Validate and update fields
            self.item_data['name'] = self.fields['name'].get().strip()
            self.item_data['model'] = self.fields['model'].get().strip()

            # Position
            self.item_data['position'] = {
                'x': float(self.fields['position_x'].get()),
                'y': float(self.fields['position_y'].get()),
                'z': float(self.fields['position_z'].get())
            }

            # Other fields
            self.item_data['heading'] = float(self.fields['heading'].get())
            self.item_data['battery_level'] = float(self.fields['battery_level'].get())
            self.item_data['status'] = self.fields['status'].get()
            self.item_data['max_speed'] = float(self.fields['max_speed'].get())
            self.item_data['max_altitude'] = float(self.fields['max_altitude'].get())
            self.item_data['battery_capacity'] = float(self.fields['battery_capacity'].get())
            self.item_data['perceived_radius'] = float(self.fields['perceived_radius'].get())
            self.item_data['task_radius'] = float(self.fields['task_radius'].get())

            # Use shared validation function
            is_valid, error_message = validate_drone_data(self.item_data)
            if not is_valid:
                messagebox.showerror("Validation Error", error_message)
                return

            if self.item_data.get("status") == "emergency":
                messagebox.showinfo(
                    "Emergency Status",
                    "Emergency status will automatically change to idle if battery is enough."
                )

            self.result = self.item_data
            self.closed = True
            try:
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.destroy()
            except (tk.TclError, AttributeError):
                pass
            finally:
                self.dialog = None

        except ValueError as e:
            messagebox.showerror("Validation Error", f"Invalid numeric value: {str(e)}")


class TargetEditorDialog(AttributeEditorDialog):
    """Dialog for editing target attributes"""

    def create_widgets(self):
        """Create target editor widgets"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Edit Target Attributes",
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 10))

        # Scrollable frame for fields
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Fields
        self.fields = {}
        row = 0

        velocity = self.item_data.get('velocity') or {}
        moving_path = self.item_data.get('moving_path') or []
        default_mode = derive_moving_target_mode(self.item_data)

        # Name
        ttk.Label(scrollable_frame, text="Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['name'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['name'].insert(0, self.item_data.get('name', ''))
        self.fields['name'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # ID (read-only)
        ttk.Label(scrollable_frame, text="ID:").grid(row=row, column=0, sticky=tk.W, pady=5)
        id_label = ttk.Label(scrollable_frame, text=self.item_data.get('id', ''),
                            foreground='gray')
        id_label.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        row += 1

        # Type
        ttk.Label(scrollable_frame, text="Type:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['type'] = ttk.Combobox(scrollable_frame, width=28,
                                           values=["fixed", "moving", "waypoint", "circle", "polygon"],
                                           state="readonly")
        self.fields['type'].set(self.item_data.get('type', 'fixed'))
        self.fields['type'].bind('<<ComboboxSelected>>', self.on_type_changed)
        self.fields['type'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Position X
        self.position_x_label = ttk.Label(scrollable_frame, text="Position X (m):")
        self.position_x_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['position_x'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['position_x'].insert(0, format_number(self.item_data.get('position', {}).get('x', 0)))
        self.fields['position_x'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Position Y
        self.position_y_label = ttk.Label(scrollable_frame, text="Position Y (m):")
        self.position_y_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['position_y'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['position_y'].insert(0, format_number(self.item_data.get('position', {}).get('y', 0)))
        self.fields['position_y'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Altitude Z (only for point-based targets: fixed, moving, waypoint)
        self.altitude_z_label = ttk.Label(scrollable_frame, text="Altitude Z (m):")
        self.altitude_z_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['position_z'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['position_z'].insert(0, format_number(self.item_data.get('position', {}).get('z', 0)))
        self.fields['position_z'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Radius (for non-polygon types)
        self.radius_label = ttk.Label(scrollable_frame, text="Radius (m):")
        self.radius_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['radius'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['radius'].insert(0, format_number(self.item_data.get('radius', 10)))
        self.fields['radius'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Duration (moving targets)
        self.moving_duration_label = ttk.Label(scrollable_frame, text="Duration (s):")
        self.moving_duration_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['moving_duration'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['moving_duration'].insert(0, format_number(self.item_data.get('moving_duration', 10.0)))
        self.fields['moving_duration'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Movement Mode (moving targets)
        self.movement_mode_var = tk.StringVar(value=default_mode)
        self.movement_mode_frame = ttk.LabelFrame(scrollable_frame, text="Movement Mode", padding=8)
        self.movement_mode_frame.grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=5)
        ttk.Radiobutton(self.movement_mode_frame, text="Velocity-based (Ping-pong)",
                        variable=self.movement_mode_var, value="velocity",
                        command=self.on_mode_change).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(self.movement_mode_frame, text="Path-based (Waypoints)",
                        variable=self.movement_mode_var, value="path",
                        command=self.on_mode_change).grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(self.movement_mode_frame, text="Stationary (No movement)",
                        variable=self.movement_mode_var, value="stationary",
                        command=self.on_mode_change).grid(row=2, column=0, sticky=tk.W, pady=2)
        row += 1

        # Velocity settings
        self.velocity_frame = ttk.LabelFrame(scrollable_frame, text="Velocity Settings", padding=8)
        self.velocity_frame.grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=5)
        vel_row = 0
        ttk.Label(self.velocity_frame, text="Velocity X (m/s):").grid(row=vel_row, column=0, sticky=tk.W, pady=3)
        self.fields['vel_x'] = ttk.Entry(self.velocity_frame, width=15)
        self.fields['vel_x'].insert(0, format_number(velocity.get('x', 0.0) if velocity else 0.0))
        self.fields['vel_x'].grid(row=vel_row, column=1, sticky=tk.W, pady=3)
        vel_row += 1
        ttk.Label(self.velocity_frame, text="Velocity Y (m/s):").grid(row=vel_row, column=0, sticky=tk.W, pady=3)
        self.fields['vel_y'] = ttk.Entry(self.velocity_frame, width=15)
        self.fields['vel_y'].insert(0, format_number(velocity.get('y', 0.0) if velocity else 0.0))
        self.fields['vel_y'].grid(row=vel_row, column=1, sticky=tk.W, pady=3)
        vel_row += 1
        ttk.Label(self.velocity_frame, text="Velocity Z (m/s):").grid(row=vel_row, column=0, sticky=tk.W, pady=3)
        self.fields['vel_z'] = ttk.Entry(self.velocity_frame, width=15)
        self.fields['vel_z'].insert(0, format_number(velocity.get('z', 0.0) if velocity else 0.0))
        self.fields['vel_z'].grid(row=vel_row, column=1, sticky=tk.W, pady=3)
        row += 1

        # Path settings
        self.path_frame = ttk.LabelFrame(scrollable_frame, text="Path Settings", padding=8)
        self.path_frame.grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=5)
        ttk.Label(self.path_frame, text="Waypoints:").grid(row=0, column=0, sticky=tk.NW, pady=3)

        path_text_frame = ttk.Frame(self.path_frame)
        path_text_frame.grid(row=0, column=1, sticky=tk.EW, pady=3, padx=5)
        self.path_text = tk.Text(path_text_frame, width=30, height=5, wrap=tk.WORD)
        path_scrollbar = ttk.Scrollbar(path_text_frame, orient="vertical", command=self.path_text.yview)
        self.path_text.configure(yscrollcommand=path_scrollbar.set)
        self.path_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        path_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        if moving_path:
            self.path_text.insert('1.0', format_moving_path_to_text(moving_path))

        help_text = "Format: x, y or x, y, z (one per line)"
        self.path_help_label = ttk.Label(self.path_frame, text=help_text,
                                         font=('Arial', 9), foreground='gray')
        self.path_help_label.grid(row=1, column=1, sticky=tk.W, pady=(0, 3), padx=5)
        self.path_frame.columnconfigure(1, weight=1)
        row += 1

        # Polygon vertices (for polygon type) - User-friendly text format
        self.vertices_label = ttk.Label(scrollable_frame, text="Vertices (x, y):")
        self.vertices_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['vertices'] = tk.Text(scrollable_frame, width=30, height=6)
        if self.item_data.get('vertices'):
            self.fields['vertices'].insert('1.0', format_vertices_to_text(self.item_data.get('vertices')))
        else:
            ensure_polygon_sample(self.fields['vertices'])
        self.fields['vertices'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Add help text for vertices
        help_text = "Format: x, y (one point per line)\nExample: 25, 10"
        self.vertices_help_label = ttk.Label(scrollable_frame, text=help_text,
                                            font=('Arial', 9), foreground='gray')
        self.vertices_help_label.grid(row=row, column=1, sticky=tk.W, pady=(0, 5), padx=5)
        row += 1

        scrollable_frame.columnconfigure(1, weight=1)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Update field visibility based on type
        self.on_type_changed(None)

        # Buttons
        self.create_button_frame(self.dialog)

    def on_mode_change(self):
        """Handle movement mode change for moving targets."""
        if self.fields['type'].get() != 'moving':
            self.velocity_frame.grid_remove()
            self.path_frame.grid_remove()
            return
        if self.movement_mode_var.get() == "velocity":
            self.velocity_frame.grid()
            self.path_frame.grid_remove()
        elif self.movement_mode_var.get() == "path":
            self.velocity_frame.grid_remove()
            self.path_frame.grid()
        else:
            self.velocity_frame.grid_remove()
            self.path_frame.grid_remove()

    def on_type_changed(self, event):
        """Handle target type change to show/hide relevant fields"""
        target_type = self.fields['type'].get()

        # Only fixed and moving targets show Altitude Z
        # Waypoint, circle, and polygon targets hide Altitude Z (z=0)
        if target_type in ['fixed', 'moving']:
            # Show Altitude Z for fixed and moving targets
            self.altitude_z_label.grid()
            self.fields['position_z'].grid()
        else:
            # Hide Altitude Z for waypoint, circle, and polygon
            self.altitude_z_label.grid_remove()
            self.fields['position_z'].grid_remove()

        if target_type == 'polygon':
            # Hide radius, show vertices
            self.position_x_label.grid_remove()
            self.fields['position_x'].grid_remove()
            self.position_y_label.grid_remove()
            self.fields['position_y'].grid_remove()
            self.radius_label.grid_remove()
            self.fields['radius'].grid_remove()
            self.vertices_label.grid()
            self.fields['vertices'].grid()
            self.vertices_help_label.grid()
            ensure_polygon_sample(self.fields['vertices'])
        else:
            # Show radius, hide vertices
            self.position_x_label.grid()
            self.fields['position_x'].grid()
            self.position_y_label.grid()
            self.fields['position_y'].grid()
            self.radius_label.grid()
            self.fields['radius'].grid()
            self.vertices_label.grid_remove()
            self.fields['vertices'].grid_remove()
            self.vertices_help_label.grid_remove()

        if target_type == 'moving':
            self.moving_duration_label.grid()
            self.fields['moving_duration'].grid()
            self.movement_mode_frame.grid()
            self.on_mode_change()
        else:
            self.moving_duration_label.grid_remove()
            self.fields['moving_duration'].grid_remove()
            self.movement_mode_frame.grid_remove()
            self.velocity_frame.grid_remove()
            self.path_frame.grid_remove()

    def on_ok(self):
        """Validate and save target data"""
        try:
            # Validate and update fields
            self.item_data['name'] = self.fields['name'].get().strip()
            self.item_data['type'] = self.fields['type'].get()
            if 'description' in self.fields:
                self.item_data['description'] = self.fields['description'].get().strip()

            # Position
            # Only fixed and moving targets have altitude; waypoint, circle, and polygon have z=0
            if self.item_data['type'] in ['fixed', 'moving']:
                z_value = float(self.fields['position_z'].get())
            else:
                z_value = 0.0

            # Type-specific fields
            if self.item_data['type'] == 'polygon':
                vertices_text = self.fields['vertices'].get('1.0', tk.END).strip()
                if not vertices_text:
                    messagebox.showerror("Validation Error", "Please enter at least 3 vertices")
                    return
                # Parse from user-friendly text format
                vertices = parse_vertices_from_text(vertices_text)
                if len(vertices) >= 4 and vertices[0] == vertices[-1]:
                    vertices = vertices[:-1]
                is_valid, error_message = validate_polygon_vertices(vertices)
                if not is_valid:
                    messagebox.showerror("Validation Error", error_message)
                    return
                center_x, center_y = get_polygon_center(vertices)
                self.item_data['position'] = {
                    'x': center_x,
                    'y': center_y,
                    'z': z_value
                }
                self.item_data['vertices'] = vertices
                self.item_data.pop('radius', None)
            else:
                self.item_data['position'] = {
                    'x': float(self.fields['position_x'].get()),
                    'y': float(self.fields['position_y'].get()),
                    'z': z_value
                }
                self.item_data['radius'] = float(self.fields['radius'].get())
                self.item_data.pop('vertices', None)

            if self.item_data['type'] == 'moving':
                duration = float(self.fields['moving_duration'].get())
                velocity = None
                moving_path = []
                movement_mode = self.movement_mode_var.get()
                self.item_data['movement_mode'] = movement_mode

                if movement_mode == "velocity":
                    velocity = {
                        "x": float(self.fields['vel_x'].get()),
                        "y": float(self.fields['vel_y'].get()),
                        "z": float(self.fields['vel_z'].get()),
                    }
                elif movement_mode == "path":
                    moving_path = parse_moving_path_text(
                        self.path_text.get('1.0', tk.END),
                        float(self.fields['position_z'].get())
                    )

                self.item_data.update(
                    normalize_moving_target_state(
                        movement_mode=movement_mode,
                        moving_duration=duration,
                        velocity=velocity,
                        moving_path=moving_path,
                    )
                )
            else:
                self.item_data.pop('movement_mode', None)
                self.item_data.pop('moving_duration', None)
                self.item_data.pop('velocity', None)
                self.item_data.pop('moving_path', None)

            # Validation
            if not self.item_data['name']:
                messagebox.showerror("Validation Error", "Name cannot be empty")
                return

            if self.item_data['type'] != 'polygon' and self.item_data['radius'] <= 0:
                messagebox.showerror("Validation Error", "Radius must be greater than 0")
                return

            self.result = self.item_data
            self.closed = True
            try:
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.destroy()
            except (tk.TclError, AttributeError):
                pass
            finally:
                self.dialog = None

        except ValueError as e:
            messagebox.showerror("Validation Error", f"Invalid numeric value: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving target: {str(e)}")


class ObstacleEditorDialog(AttributeEditorDialog):
    """Dialog for editing obstacle attributes"""

    def create_widgets(self):
        """Create obstacle editor widgets"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Edit Obstacle Attributes",
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 10))

        # Scrollable frame for fields
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Fields
        self.fields = {}
        row = 0

        # Name
        ttk.Label(scrollable_frame, text="Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['name'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['name'].insert(0, self.item_data.get('name', ''))
        self.fields['name'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # ID (read-only)
        ttk.Label(scrollable_frame, text="ID:").grid(row=row, column=0, sticky=tk.W, pady=5)
        id_label = ttk.Label(scrollable_frame, text=self.item_data.get('id', ''),
                            foreground='gray')
        id_label.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        row += 1

        # Type
        ttk.Label(scrollable_frame, text="Type:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['type'] = ttk.Combobox(scrollable_frame, width=28,
                                           values=["point", "circle", "ellipse", "polygon"],
                                           state="readonly")
        self.fields['type'].set(self.item_data.get('type', 'circle'))
        self.fields['type'].bind('<<ComboboxSelected>>', self.on_type_changed)
        self.fields['type'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Position X
        self.position_x_label = ttk.Label(scrollable_frame, text="Position X (m):")
        self.position_x_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['position_x'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['position_x'].insert(0, format_number(self.item_data.get('position', {}).get('x', 0)))
        self.fields['position_x'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Position Y
        self.position_y_label = ttk.Label(scrollable_frame, text="Position Y (m):")
        self.position_y_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['position_y'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['position_y'].insert(0, format_number(self.item_data.get('position', {}).get('y', 0)))
        self.fields['position_y'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Height (physical dimension of obstacle)
        ttk.Label(scrollable_frame, text="Height (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['height'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['height'].insert(0, format_number(self.item_data.get('height', 0)))
        self.fields['height'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Radius (for point/circle)
        self.radius_label = ttk.Label(scrollable_frame, text="Radius (m):")
        self.radius_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['radius'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['radius'].insert(0, format_number(self.item_data.get('radius', 10)))
        self.fields['radius'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Width (for ellipse)
        self.width_label = ttk.Label(scrollable_frame, text="Width (m):")
        self.width_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['width'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['width'].insert(0, format_number(self.item_data.get('width', 10)))
        self.fields['width'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Length (for ellipse)
        self.length_label = ttk.Label(scrollable_frame, text="Length (m):")
        self.length_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['length'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['length'].insert(0, format_number(self.item_data.get('length', 10)))
        self.fields['length'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Polygon vertices (for polygon type) - User-friendly text format
        self.vertices_label = ttk.Label(scrollable_frame, text="Vertices (x, y):")
        self.vertices_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['vertices'] = tk.Text(scrollable_frame, width=30, height=6)
        if self.item_data.get('vertices'):
            self.fields['vertices'].insert('1.0', format_vertices_to_text(self.item_data.get('vertices')))
        else:
            ensure_polygon_sample(self.fields['vertices'])
        self.fields['vertices'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Add help text for vertices
        help_text = "Format: x, y (one point per line)\nExample: 25, 10"
        self.vertices_help_label = ttk.Label(scrollable_frame, text=help_text,
                                            font=('Arial', 9), foreground='gray')
        self.vertices_help_label.grid(row=row, column=1, sticky=tk.W, pady=(0, 5), padx=5)
        row += 1

        scrollable_frame.columnconfigure(1, weight=1)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Update field visibility based on type
        self.on_type_changed(None)

        # Buttons
        self.create_button_frame(self.dialog)

    def on_type_changed(self, event):
        """Handle obstacle type change to show/hide relevant fields"""
        obstacle_type = self.fields['type'].get()

        if obstacle_type == 'polygon':
            # Hide other fields, show vertices
            self.position_x_label.grid_remove()
            self.fields['position_x'].grid_remove()
            self.position_y_label.grid_remove()
            self.fields['position_y'].grid_remove()
            self.radius_label.grid_remove()
            self.fields['radius'].grid_remove()
            self.width_label.grid_remove()
            self.fields['width'].grid_remove()
            self.length_label.grid_remove()
            self.fields['length'].grid_remove()
            self.vertices_label.grid()
            self.fields['vertices'].grid()
            self.vertices_help_label.grid()
            ensure_polygon_sample(self.fields['vertices'])
        elif obstacle_type == 'ellipse':
            # Show width/length, hide others
            self.position_x_label.grid()
            self.fields['position_x'].grid()
            self.position_y_label.grid()
            self.fields['position_y'].grid()
            self.radius_label.grid_remove()
            self.fields['radius'].grid_remove()
            self.width_label.grid()
            self.fields['width'].grid()
            self.length_label.grid()
            self.fields['length'].grid()
            self.vertices_label.grid_remove()
            self.fields['vertices'].grid_remove()
            self.vertices_help_label.grid_remove()
        else:  # point or circle
            # Show radius, hide others
            self.position_x_label.grid()
            self.fields['position_x'].grid()
            self.position_y_label.grid()
            self.fields['position_y'].grid()
            self.radius_label.grid()
            self.fields['radius'].grid()
            self.width_label.grid_remove()
            self.fields['width'].grid_remove()
            self.length_label.grid_remove()
            self.fields['length'].grid_remove()
            self.vertices_label.grid_remove()
            self.fields['vertices'].grid_remove()
            self.vertices_help_label.grid_remove()

    def on_ok(self):
        """Validate and save obstacle data"""
        try:
            # Validate and update fields
            self.item_data['name'] = self.fields['name'].get().strip()
            self.item_data['type'] = self.fields['type'].get()
            if 'description' in self.fields:
                self.item_data['description'] = self.fields['description'].get().strip()

            # Height (physical dimension of obstacle)
            self.item_data['height'] = float(self.fields['height'].get())

            # Type-specific fields
            if self.item_data['type'] == 'polygon':
                vertices_text = self.fields['vertices'].get('1.0', tk.END).strip()
                if not vertices_text:
                    messagebox.showerror("Validation Error", "Please enter at least 3 vertices")
                    return
                # Parse from user-friendly text format
                vertices = parse_vertices_from_text(vertices_text)
                if len(vertices) >= 4 and vertices[0] == vertices[-1]:
                    vertices = vertices[:-1]
                is_valid, error_message = validate_polygon_vertices(vertices)
                if not is_valid:
                    messagebox.showerror("Validation Error", error_message)
                    return
                center_x, center_y = get_polygon_center(vertices)
                self.item_data['position'] = {
                    'x': center_x,
                    'y': center_y,
                    'z': 0.0
                }
                self.item_data['vertices'] = vertices
                self.item_data.pop('radius', None)
                self.item_data.pop('width', None)
                self.item_data.pop('length', None)
            elif self.item_data['type'] == 'ellipse':
                self.item_data['position'] = {
                    'x': float(self.fields['position_x'].get()),
                    'y': float(self.fields['position_y'].get()),
                    'z': 0.0
                }
                self.item_data['width'] = float(self.fields['width'].get())
                self.item_data['length'] = float(self.fields['length'].get())
                self.item_data.pop('radius', None)
                self.item_data.pop('vertices', None)
            else:  # point or circle
                self.item_data['position'] = {
                    'x': float(self.fields['position_x'].get()),
                    'y': float(self.fields['position_y'].get()),
                    'z': 0.0
                }
                self.item_data['radius'] = float(self.fields['radius'].get())
                self.item_data.pop('width', None)
                self.item_data.pop('length', None)
                self.item_data.pop('vertices', None)

            # Validation
            if not self.item_data['name']:
                messagebox.showerror("Validation Error", "Name cannot be empty")
                return

            if self.item_data['type'] in ['point', 'circle'] and self.item_data['radius'] <= 0:
                messagebox.showerror("Validation Error", "Radius must be greater than 0")
                return

            if self.item_data['type'] == 'ellipse':
                if self.item_data['width'] <= 0 or self.item_data['length'] <= 0:
                    messagebox.showerror("Validation Error", "Width and length must be greater than 0")
                    return

            self.result = self.item_data
            self.closed = True
            try:
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.destroy()
            except (tk.TclError, AttributeError):
                pass
            finally:
                self.dialog = None

        except ValueError as e:
            messagebox.showerror("Validation Error", f"Invalid numeric value: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving obstacle: {str(e)}")


class AddDroneDialog(DroneEditorDialog):
    """Dialog for adding a new drone"""

    def __init__(self, session_data=None):
        # Generate default name with counter
        existing_drones = session_data.get('drones', []) if session_data else []
        default_name = generate_default_name('Drone', existing_drones)

        default_data = {
            'id': str(uuid.uuid4())[:8],
            'name': default_name,
            'model': 'Model-A',
            'position': {'x': 0.0, 'y': 0.0, 'z': 0.0},
            'heading': 0.0,
            'battery_level': 100.0,
            'status': 'idle',
            'max_speed': 20.0,
            'max_altitude': 120.0,
            'battery_capacity': 4000.0,
            'perceived_radius': 100.0,
            'task_radius': 10.0
        }
        # Call AttributeEditorDialog's __init__ directly to use the add title
        AttributeEditorDialog.__init__(self, "Add New Drone", default_data)


class AddTargetDialog(AttributeEditorDialog):
    """Dialog for adding a new target"""

    def __init__(self, session_data=None):
        # Generate default name with counter
        existing_targets = session_data.get('targets', []) if session_data else []
        default_name = generate_default_name('Target', existing_targets)

        default_data = {
            'id': str(uuid.uuid4())[:8],
            'name': default_name,
            'type': 'fixed',
            'position': {'x': 0.0, 'y': 0.0, 'z': 0.0},
            'radius': 10.0
        }
        super().__init__("Add New Target", default_data)
        # Store session data for name regeneration
        self.session_data = session_data

    def create_widgets(self):
        """Create target add widgets"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollable frame for fields
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Fields
        self.fields = {}
        row = 0

        velocity = self.item_data.get('velocity') or {}
        moving_path = self.item_data.get('moving_path') or []
        default_mode = derive_moving_target_mode(self.item_data)

        # Name
        ttk.Label(scrollable_frame, text="Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['name'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['name'].insert(0, self.item_data.get('name', ''))
        self.fields['name'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Type
        ttk.Label(scrollable_frame, text="Type:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['type'] = ttk.Combobox(scrollable_frame, width=28,
                                           values=["fixed", "moving", "waypoint", "circle", "polygon"],
                                           state="readonly")
        self.fields['type'].set(self.item_data.get('type', 'fixed'))
        self.fields['type'].bind('<<ComboboxSelected>>', self.on_type_changed)
        self.fields['type'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Description
        ttk.Label(scrollable_frame, text="Description:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['description'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['description'].insert(0, self.item_data.get('description', ''))
        self.fields['description'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Position X
        self.position_x_label = ttk.Label(scrollable_frame, text="Position X (m):")
        self.position_x_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['position_x'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['position_x'].insert(0, format_number(self.item_data.get('position', {}).get('x', 0)))
        self.fields['position_x'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Position Y
        self.position_y_label = ttk.Label(scrollable_frame, text="Position Y (m):")
        self.position_y_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['position_y'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['position_y'].insert(0, format_number(self.item_data.get('position', {}).get('y', 0)))
        self.fields['position_y'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Altitude Z (only for point-based targets: fixed, moving)
        self.altitude_z_label = ttk.Label(scrollable_frame, text="Altitude Z (m):")
        self.altitude_z_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['position_z'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['position_z'].insert(0, format_number(self.item_data.get('position', {}).get('z', 0)))
        self.fields['position_z'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Radius (for non-polygon types)
        self.radius_label = ttk.Label(scrollable_frame, text="Radius (m):")
        self.radius_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['radius'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['radius'].insert(0, format_number(self.item_data.get('radius', 10)))
        self.fields['radius'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Duration (moving targets)
        self.moving_duration_label = ttk.Label(scrollable_frame, text="Duration (s):")
        self.moving_duration_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['moving_duration'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['moving_duration'].insert(0, format_number(self.item_data.get('moving_duration', 10.0)))
        self.fields['moving_duration'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Movement Mode (moving targets)
        self.movement_mode_var = tk.StringVar(value=default_mode)
        self.movement_mode_frame = ttk.LabelFrame(scrollable_frame, text="Movement Mode", padding=8)
        self.movement_mode_frame.grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=5)
        ttk.Radiobutton(self.movement_mode_frame, text="Velocity-based (Ping-pong)",
                        variable=self.movement_mode_var, value="velocity",
                        command=self.on_mode_change).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(self.movement_mode_frame, text="Path-based (Waypoints)",
                        variable=self.movement_mode_var, value="path",
                        command=self.on_mode_change).grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(self.movement_mode_frame, text="Stationary (No movement)",
                        variable=self.movement_mode_var, value="stationary",
                        command=self.on_mode_change).grid(row=2, column=0, sticky=tk.W, pady=2)
        row += 1

        # Velocity settings
        self.velocity_frame = ttk.LabelFrame(scrollable_frame, text="Velocity Settings", padding=8)
        self.velocity_frame.grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=5)
        vel_row = 0
        ttk.Label(self.velocity_frame, text="Velocity X (m/s):").grid(row=vel_row, column=0, sticky=tk.W, pady=3)
        self.fields['vel_x'] = ttk.Entry(self.velocity_frame, width=15)
        self.fields['vel_x'].insert(0, format_number(velocity.get('x', 0.0) if velocity else 0.0))
        self.fields['vel_x'].grid(row=vel_row, column=1, sticky=tk.W, pady=3)
        vel_row += 1
        ttk.Label(self.velocity_frame, text="Velocity Y (m/s):").grid(row=vel_row, column=0, sticky=tk.W, pady=3)
        self.fields['vel_y'] = ttk.Entry(self.velocity_frame, width=15)
        self.fields['vel_y'].insert(0, format_number(velocity.get('y', 0.0) if velocity else 0.0))
        self.fields['vel_y'].grid(row=vel_row, column=1, sticky=tk.W, pady=3)
        vel_row += 1
        ttk.Label(self.velocity_frame, text="Velocity Z (m/s):").grid(row=vel_row, column=0, sticky=tk.W, pady=3)
        self.fields['vel_z'] = ttk.Entry(self.velocity_frame, width=15)
        self.fields['vel_z'].insert(0, format_number(velocity.get('z', 0.0) if velocity else 0.0))
        self.fields['vel_z'].grid(row=vel_row, column=1, sticky=tk.W, pady=3)
        row += 1

        # Path settings
        self.path_frame = ttk.LabelFrame(scrollable_frame, text="Path Settings", padding=8)
        self.path_frame.grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=5)
        ttk.Label(self.path_frame, text="Waypoints:").grid(row=0, column=0, sticky=tk.NW, pady=3)

        path_text_frame = ttk.Frame(self.path_frame)
        path_text_frame.grid(row=0, column=1, sticky=tk.EW, pady=3, padx=5)
        self.path_text = tk.Text(path_text_frame, width=30, height=5, wrap=tk.WORD)
        path_scrollbar = ttk.Scrollbar(path_text_frame, orient="vertical", command=self.path_text.yview)
        self.path_text.configure(yscrollcommand=path_scrollbar.set)
        self.path_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        path_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        if moving_path:
            self.path_text.insert('1.0', format_moving_path_to_text(moving_path))

        help_text = "Format: x, y or x, y, z (one per line)"
        self.path_help_label = ttk.Label(self.path_frame, text=help_text,
                                         font=('Arial', 9), foreground='gray')
        self.path_help_label.grid(row=1, column=1, sticky=tk.W, pady=(0, 3), padx=5)
        self.path_frame.columnconfigure(1, weight=1)
        row += 1

        # Polygon vertices (for polygon type) - User-friendly text format
        self.vertices_label = ttk.Label(scrollable_frame, text="Vertices (x, y):")
        self.vertices_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['vertices'] = tk.Text(scrollable_frame, width=30, height=6)
        if self.item_data.get('vertices'):
            self.fields['vertices'].insert('1.0', format_vertices_to_text(self.item_data.get('vertices')))
        else:
            ensure_polygon_sample(self.fields['vertices'])
        self.fields['vertices'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Add help text for vertices
        help_text = "Format: x, y (one point per line)\nExample: 25, 10"
        self.vertices_help_label = ttk.Label(scrollable_frame, text=help_text,
                                            font=('Arial', 9), foreground='gray')
        self.vertices_help_label.grid(row=row, column=1, sticky=tk.W, pady=(0, 5), padx=5)
        row += 1

        scrollable_frame.columnconfigure(1, weight=1)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Update field visibility based on type
        self.on_type_changed(None)

        # Buttons
        self.create_button_frame(self.dialog)

    def on_mode_change(self):
        """Handle movement mode change for moving targets."""
        if self.fields['type'].get() != 'moving':
            self.velocity_frame.grid_remove()
            self.path_frame.grid_remove()
            return
        if self.movement_mode_var.get() == "velocity":
            self.velocity_frame.grid()
            self.path_frame.grid_remove()
        elif self.movement_mode_var.get() == "path":
            self.velocity_frame.grid_remove()
            self.path_frame.grid()
        else:
            self.velocity_frame.grid_remove()
            self.path_frame.grid_remove()

    def on_type_changed(self, event):
        """Handle target type change to show/hide relevant fields"""
        target_type = self.fields['type'].get()

        # Only fixed and moving targets show Altitude Z
        # Waypoint, circle, and polygon targets hide Altitude Z (z=0)
        if target_type in ['fixed', 'moving']:
            # Show Altitude Z for fixed and moving targets
            self.altitude_z_label.grid()
            self.fields['position_z'].grid()
        else:
            # Hide Altitude Z for waypoint, circle, and polygon
            self.altitude_z_label.grid_remove()
            self.fields['position_z'].grid_remove()

        if target_type == 'polygon':
            # Hide radius, show vertices
            self.position_x_label.grid_remove()
            self.fields['position_x'].grid_remove()
            self.position_y_label.grid_remove()
            self.fields['position_y'].grid_remove()
            self.radius_label.grid_remove()
            self.fields['radius'].grid_remove()
            self.vertices_label.grid()
            self.fields['vertices'].grid()
            self.vertices_help_label.grid()
            ensure_polygon_sample(self.fields['vertices'])
        else:
            # Show radius, hide vertices
            self.position_x_label.grid()
            self.fields['position_x'].grid()
            self.position_y_label.grid()
            self.fields['position_y'].grid()
            self.radius_label.grid()
            self.fields['radius'].grid()
            self.vertices_label.grid_remove()
            self.fields['vertices'].grid_remove()
            self.vertices_help_label.grid_remove()

        if target_type == 'moving':
            self.moving_duration_label.grid()
            self.fields['moving_duration'].grid()
            self.movement_mode_frame.grid()
            self.on_mode_change()
        else:
            self.moving_duration_label.grid_remove()
            self.fields['moving_duration'].grid_remove()
            self.movement_mode_frame.grid_remove()
            self.velocity_frame.grid_remove()
            self.path_frame.grid_remove()

    def on_ok(self):
        """Validate and save target data"""
        try:
            # Validate and update fields
            self.item_data['name'] = self.fields['name'].get().strip()
            self.item_data['type'] = self.fields['type'].get()
            if 'description' in self.fields:
                self.item_data['description'] = self.fields['description'].get().strip()

            # Position
            # Only fixed and moving targets have altitude; waypoint, circle, and polygon have z=0
            if self.item_data['type'] in ['fixed', 'moving']:
                z_value = float(self.fields['position_z'].get())
            else:
                z_value = 0.0

            # Type-specific fields
            if self.item_data['type'] == 'polygon':
                vertices_text = self.fields['vertices'].get('1.0', tk.END).strip()
                if not vertices_text:
                    messagebox.showerror("Validation Error", "Please enter at least 3 vertices")
                    return
                # Parse from user-friendly text format
                vertices = parse_vertices_from_text(vertices_text)
                if len(vertices) >= 4 and vertices[0] == vertices[-1]:
                    vertices = vertices[:-1]
                is_valid, error_message = validate_polygon_vertices(vertices)
                if not is_valid:
                    messagebox.showerror("Validation Error", error_message)
                    return
                center_x, center_y = get_polygon_center(vertices)
                self.item_data['position'] = {
                    'x': center_x,
                    'y': center_y,
                    'z': z_value
                }
                self.item_data['vertices'] = vertices
                self.item_data.pop('radius', None)
            else:
                self.item_data['position'] = {
                    'x': float(self.fields['position_x'].get()),
                    'y': float(self.fields['position_y'].get()),
                    'z': z_value
                }
                self.item_data['radius'] = float(self.fields['radius'].get())
                self.item_data.pop('vertices', None)

            if self.item_data['type'] == 'moving':
                duration = float(self.fields['moving_duration'].get())
                velocity = None
                moving_path = []
                movement_mode = self.movement_mode_var.get()
                self.item_data['movement_mode'] = movement_mode

                if movement_mode == "velocity":
                    velocity = {
                        "x": float(self.fields['vel_x'].get()),
                        "y": float(self.fields['vel_y'].get()),
                        "z": float(self.fields['vel_z'].get()),
                    }
                elif movement_mode == "path":
                    moving_path = parse_moving_path_text(
                        self.path_text.get('1.0', tk.END),
                        float(self.fields['position_z'].get())
                    )

                self.item_data.update(
                    normalize_moving_target_state(
                        movement_mode=movement_mode,
                        moving_duration=duration,
                        velocity=velocity,
                        moving_path=moving_path,
                    )
                )
            else:
                self.item_data.pop('movement_mode', None)
                self.item_data.pop('moving_duration', None)
                self.item_data.pop('velocity', None)
                self.item_data.pop('moving_path', None)

            # Validation
            if not self.item_data['name']:
                messagebox.showerror("Validation Error", "Name cannot be empty")
                return

            if self.item_data['type'] != 'polygon' and self.item_data['radius'] <= 0:
                messagebox.showerror("Validation Error", "Radius must be greater than 0")
                return

            self.result = self.item_data
            self.closed = True
            try:
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.destroy()
            except (tk.TclError, AttributeError):
                pass
            finally:
                self.dialog = None

        except ValueError as e:
            messagebox.showerror("Validation Error", f"Invalid numeric value: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving target: {str(e)}")


class AddObstacleDialog(AttributeEditorDialog):
    """Dialog for adding a new obstacle"""

    def __init__(self, session_data=None):
        # Generate default name with counter
        existing_obstacles = session_data.get('obstacles', []) if session_data else []
        default_name = generate_default_name('Obstacle', existing_obstacles)

        default_data = {
            'id': str(uuid.uuid4())[:8],
            'name': default_name,
            'type': 'circle',
            'position': {'x': 0.0, 'y': 0.0, 'z': 0.0},
            'radius': 10.0
        }
        super().__init__("Add New Obstacle", default_data)
        # Store session data for name regeneration
        self.session_data = session_data

    def create_widgets(self):
        """Create obstacle add widgets"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollable frame for fields
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Fields
        self.fields = {}
        row = 0

        # Name
        ttk.Label(scrollable_frame, text="Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['name'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['name'].insert(0, self.item_data.get('name', ''))
        self.fields['name'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Type
        ttk.Label(scrollable_frame, text="Type:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['type'] = ttk.Combobox(scrollable_frame, width=28,
                                           values=["point", "circle", "ellipse", "polygon"],
                                           state="readonly")
        self.fields['type'].set(self.item_data.get('type', 'circle'))
        self.fields['type'].bind('<<ComboboxSelected>>', self.on_type_changed)
        self.fields['type'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Description
        ttk.Label(scrollable_frame, text="Description:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['description'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['description'].insert(0, self.item_data.get('description', ''))
        self.fields['description'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Position X
        self.position_x_label = ttk.Label(scrollable_frame, text="Position X (m):")
        self.position_x_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['position_x'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['position_x'].insert(0, format_number(self.item_data.get('position', {}).get('x', 0)))
        self.fields['position_x'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Position Y
        self.position_y_label = ttk.Label(scrollable_frame, text="Position Y (m):")
        self.position_y_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['position_y'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['position_y'].insert(0, format_number(self.item_data.get('position', {}).get('y', 0)))
        self.fields['position_y'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Height (physical dimension of obstacle)
        ttk.Label(scrollable_frame, text="Height (m):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['height'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['height'].insert(0, format_number(self.item_data.get('height', 0)))
        self.fields['height'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Radius (for point/circle)
        self.radius_label = ttk.Label(scrollable_frame, text="Radius (m):")
        self.radius_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['radius'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['radius'].insert(0, format_number(self.item_data.get('radius', 10)))
        self.fields['radius'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Width (for ellipse)
        self.width_label = ttk.Label(scrollable_frame, text="Width (m):")
        self.width_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['width'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['width'].insert(0, format_number(self.item_data.get('width', 10)))
        self.fields['width'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Length (for ellipse)
        self.length_label = ttk.Label(scrollable_frame, text="Length (m):")
        self.length_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['length'] = ttk.Entry(scrollable_frame, width=30)
        self.fields['length'].insert(0, format_number(self.item_data.get('length', 10)))
        self.fields['length'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Polygon vertices (for polygon type) - User-friendly text format
        self.vertices_label = ttk.Label(scrollable_frame, text="Vertices (x, y):")
        self.vertices_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fields['vertices'] = tk.Text(scrollable_frame, width=30, height=6)
        if self.item_data.get('vertices'):
            self.fields['vertices'].insert('1.0', format_vertices_to_text(self.item_data.get('vertices')))
        else:
            ensure_polygon_sample(self.fields['vertices'])
        self.fields['vertices'].grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        row += 1

        # Add help text for vertices
        help_text = "Format: x, y (one point per line)\nExample: 25, 10"
        self.vertices_help_label = ttk.Label(scrollable_frame, text=help_text,
                                            font=('Arial', 9), foreground='gray')
        self.vertices_help_label.grid(row=row, column=1, sticky=tk.W, pady=(0, 5), padx=5)
        row += 1

        scrollable_frame.columnconfigure(1, weight=1)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Update field visibility based on type
        self.on_type_changed(None)

        # Buttons
        self.create_button_frame(self.dialog)

    def on_type_changed(self, event):
        """Handle obstacle type change to show/hide relevant fields"""
        obstacle_type = self.fields['type'].get()

        if obstacle_type == 'polygon':
            # Hide other fields, show vertices
            self.position_x_label.grid_remove()
            self.fields['position_x'].grid_remove()
            self.position_y_label.grid_remove()
            self.fields['position_y'].grid_remove()
            self.radius_label.grid_remove()
            self.fields['radius'].grid_remove()
            self.width_label.grid_remove()
            self.fields['width'].grid_remove()
            self.length_label.grid_remove()
            self.fields['length'].grid_remove()
            self.vertices_label.grid()
            self.fields['vertices'].grid()
            self.vertices_help_label.grid()
            ensure_polygon_sample(self.fields['vertices'])
        elif obstacle_type == 'ellipse':
            # Show width/length, hide others
            self.position_x_label.grid()
            self.fields['position_x'].grid()
            self.position_y_label.grid()
            self.fields['position_y'].grid()
            self.radius_label.grid_remove()
            self.fields['radius'].grid_remove()
            self.width_label.grid()
            self.fields['width'].grid()
            self.length_label.grid()
            self.fields['length'].grid()
            self.vertices_label.grid_remove()
            self.fields['vertices'].grid_remove()
            self.vertices_help_label.grid_remove()
        else:  # point or circle
            # Show radius, hide others
            self.position_x_label.grid()
            self.fields['position_x'].grid()
            self.position_y_label.grid()
            self.fields['position_y'].grid()
            self.radius_label.grid()
            self.fields['radius'].grid()
            self.width_label.grid_remove()
            self.fields['width'].grid_remove()
            self.length_label.grid_remove()
            self.fields['length'].grid_remove()
            self.vertices_label.grid_remove()
            self.fields['vertices'].grid_remove()
            self.vertices_help_label.grid_remove()

    def on_ok(self):
        """Validate and save obstacle data"""
        try:
            # Validate and update fields
            self.item_data['name'] = self.fields['name'].get().strip()
            self.item_data['type'] = self.fields['type'].get()
            if 'description' in self.fields:
                self.item_data['description'] = self.fields['description'].get().strip()

            # Height (physical dimension of obstacle)
            self.item_data['height'] = float(self.fields['height'].get())

            # Type-specific fields
            if self.item_data['type'] == 'polygon':
                vertices_text = self.fields['vertices'].get('1.0', tk.END).strip()
                if not vertices_text:
                    messagebox.showerror("Validation Error", "Please enter at least 3 vertices")
                    return
                # Parse from user-friendly text format
                vertices = parse_vertices_from_text(vertices_text)
                if len(vertices) >= 4 and vertices[0] == vertices[-1]:
                    vertices = vertices[:-1]
                is_valid, error_message = validate_polygon_vertices(vertices)
                if not is_valid:
                    messagebox.showerror("Validation Error", error_message)
                    return
                center_x, center_y = get_polygon_center(vertices)
                self.item_data['position'] = {
                    'x': center_x,
                    'y': center_y,
                    'z': 0.0
                }
                self.item_data['vertices'] = vertices
                self.item_data.pop('radius', None)
                self.item_data.pop('width', None)
                self.item_data.pop('length', None)
            elif self.item_data['type'] == 'ellipse':
                self.item_data['position'] = {
                    'x': float(self.fields['position_x'].get()),
                    'y': float(self.fields['position_y'].get()),
                    'z': 0.0
                }
                self.item_data['width'] = float(self.fields['width'].get())
                self.item_data['length'] = float(self.fields['length'].get())
                self.item_data.pop('radius', None)
                self.item_data.pop('vertices', None)
            else:  # point or circle
                self.item_data['position'] = {
                    'x': float(self.fields['position_x'].get()),
                    'y': float(self.fields['position_y'].get()),
                    'z': 0.0
                }
                self.item_data['radius'] = float(self.fields['radius'].get())
                self.item_data.pop('width', None)
                self.item_data.pop('length', None)
                self.item_data.pop('vertices', None)

            # Validation
            if not self.item_data['name']:
                messagebox.showerror("Validation Error", "Name cannot be empty")
                return

            if self.item_data['type'] in ['point', 'circle'] and self.item_data['radius'] <= 0:
                messagebox.showerror("Validation Error", "Radius must be greater than 0")
                return

            if self.item_data['type'] == 'ellipse':
                if self.item_data['width'] <= 0 or self.item_data['length'] <= 0:
                    messagebox.showerror("Validation Error", "Width and length must be greater than 0")
                    return

            self.result = self.item_data
            self.closed = True
            try:
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.destroy()
            except (tk.TclError, AttributeError):
                pass
            finally:
                self.dialog = None

        except ValueError as e:
            messagebox.showerror("Validation Error", f"Invalid numeric value: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving obstacle: {str(e)}")
