import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from api_server import APIServer
import json
from datetime import datetime
import logging
import threading
import time
import subprocess
import sys
import tempfile
import platform
import os
import signal
import importlib
import copy
import random
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
from app_settings import get_settings
from utils import (
    setup_shared_logger,
    extract_session_metadata,
    format_number,
    normalize_session_canvas_fields,
    sanitize_filename,
    load_session_from_file,
    save_current_session_to_file,
    save_session_to_file,
    _clean_session_data_for_export,
    set_window_geometry_and_center,
    to_int,
    to_float,
    format_timestamp,
    create_new_name,
)
from shared_dialogs import (
    DroneEditDialog,
    PolygonDialog,
    CircleDialog,
    EllipseObstacleDialog,
    PointObstacleDialog,
    FixedTargetDialog,
    MovingTargetDialog,
    WaypointTargetDialog,
    format_moving_target_runtime,
    normalize_moving_target_state,
    show_about_dialog,
)
# Main task dialog
from task_dialog import TaskDialog
from task_template_manager import TaskTemplateManager
from task_template_dialog import TemplateBrowserDialog
from task_auto_generator import auto_create_tasks_for_session
from detail_panel import DetailPanel
from check_ui.agent_client import AgentClient
from task_agent_utils import extract_original_task_command

SESSION_EDITOR_IMPORT_ERROR = None
start_session_editor = None
try:
    start_session_editor = importlib.import_module("session_editor").start_session_editor
except ImportError as exc:
    SESSION_EDITOR_IMPORT_ERROR = exc

@dataclass
class SessionStats:
    name: str
    status: str
    created: str
    updated: str
    task_type: str
    task_count: str
    task_status_summary: str
    task_progress_text: str
    task_completed_text: str
    drone_count: str
    target_count: str
    obstacle_count: str
    commands_executed: str
    total_flight_time: str
    total_distance: str
    command_history_size: str
    target_reach_log_size: str
    total_target_reaches: str
    drones_with_target_reaches: str
    unique_targets_reached: str
    session_time: str
    drones_by_status: str
    drones_avg_speed: str
    drones_avg_battery: str
    targets_by_type: str
    obstacles_by_type: str


SCREENSHOT_SCALE_PRESETS = {
    "1x": 1,
    "2x": 2,
    "4x": 4,
}


class UAVControllerGUI:
    def __init__(
        self,
        root,
        initial_data: Optional[Dict[str, Any]] = None,
        *,
        version: str,
        build: str,
    ):
        self.root = root
        parent_anchor = getattr(self.root, "master", None)
        if parent_anchor is self.root:
            parent_anchor = None
        set_window_geometry_and_center(
            self.root,
            880,
            650,
            parent_anchor,
            make_transient=False,
            grab=False,
            withdraw_first=True,
            align_to_pointer=True,
            bring_to_front=True
        )
        self._icon_image = None
        self.app_closing = False
        self.version = version
        self.build = build
        self.is_modified = False

        # Setup logging
        self.setup_logging()
        self._set_window_icon()

        # API Authentication - SYSTEM role required for drone/resource management
        # Load from environment variable or use default (change in production!)
        
        self.api_server = APIServer(
            logger=self.logger,
            error_handler=lambda title, msg: messagebox.showerror(title, msg),
        )

        # Current-session HTTP request history storage
        self.command_history = []

        # Task data storage
        self.task_data = []

        # Track imported session filename for save/auto-save
        self.imported_session_filepath = None
        # Extract filepath from initial_data if provided
        if initial_data and isinstance(initial_data, dict):
            self.imported_session_filepath = initial_data.get('_imported_filepath')
        # Cache the prefetched current-session payload so we don't re-fetch immediately
        self._cached_current_session_payload = None
        if initial_data and isinstance(initial_data, dict) and initial_data.get('session'):
            self._cached_current_session_payload = initial_data.get('session')

        # Track if session has unsaved modifications
        # Cache current session info to avoid repetitive API calls
        self.current_session_id = None
        self.current_session_name = None

        # Track active session editor processes
        self.active_editor_processes = []  # List of subprocess.Popen objects

        # Track background monitors watching for session editor save events
        self.editor_save_monitors = {}

        # Load user settings (username, etc.)
        self.app_settings = get_settings()
        self.username = self.app_settings.get('username', 'SYSTEM')
        self.template_storage_path = self.app_settings.get('template_storage_path', './templates')
        self.agent_client = AgentClient(
            base_url=self.app_settings.get('agent_base_url', 'http://localhost:18000'),
            logger=self.logger,
        )
        self.is_sending_task_to_agent = False
        self.stop_agent_send_requested = False
        try:
            Path(self.template_storage_path).mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            print(f"Failed to create template storage dir {self.template_storage_path}: {exc}")

        # Initialize task template manager
        self.template_manager = TaskTemplateManager(template_dir=self.template_storage_path)

        # Create the main interface
        self.create_widgets()

        # Setup window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        # Set initial window title
        self._update_window_title()

        # Refresh data on startup
        self.refresh_all_data(prefetched_data=initial_data)

    def setup_logging(self):
        """Setup logging configuration"""
        # Setup shared logging
        self.logger = setup_shared_logger('UAVController', logging.DEBUG)

        # Log startup information
        self.logger.info("UAV Controller GUI started")

    def _set_window_icon(self):
        """Apply the controller icon to the main window when available."""
        try:
            icon_path = Path(__file__).resolve().parent / "img" / "controller.png"
            if icon_path.exists():
                self._icon_image = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, self._icon_image)
                setattr(self.root, "_uav_icon_image", self._icon_image)
            else:
                self.logger.debug(f"Icon file not found at {icon_path}")
        except Exception as exc:
            self.logger.debug(f"Failed to set GUI icon: {exc}")

    def create_menu_bar(self):
        """Create the menu bar with all menus"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Session Menu (combined File and Session)
        session_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Session", menu=session_menu)
        session_menu.add_command(label="Export Session", command=self.export_current_session)
        save_accelerator = "Cmd+S" if platform.system() == 'Darwin' else "Ctrl+S"
        save_as_accelerator = "Cmd+Shift+S" if platform.system() == 'Darwin' else "Ctrl+Shift+S"
        session_menu.add_command(label="Save Session", command=self.save_session, accelerator=save_accelerator)
        session_menu.add_command(label="Save Session As...", command=self.save_session_as, accelerator=save_as_accelerator)
        session_menu.add_separator()
        session_info_accelerator = "Cmd+I" if platform.system() == 'Darwin' else "Ctrl+I"
        session_menu.add_command(label="Session Info", command=self.show_session_info, accelerator=session_info_accelerator)
        session_menu.add_command(label="Edit Session", command=self.edit_current_session_visually)
        session_menu.add_separator()
        session_menu.add_command(label="Take Screenshot", command=self.save_session_screenshot)
        session_menu.add_separator()
        close_accelerator = "Cmd+W" if platform.system() == 'Darwin' else "Ctrl+W"
        session_menu.add_command(label="Exit", command=self.on_closing, accelerator=close_accelerator)

        # Drones Menu
        drones_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Drones", menu=drones_menu)
        drones_menu.add_command(label="Add Drone", command=self.add_drone, accelerator="Ctrl+D")
        drones_menu.add_command(label="Edit Drone", command=self.edit_drone)
        drones_menu.add_command(label="Take Off", command=self.drone_takeoff)
        drones_menu.add_command(label="Move To", command=self.drone_move_to)
        drones_menu.add_command(label="Control", command=self.open_realtime_control)
        drones_menu.add_command(label="Delete Drone", command=self.delete_drone)
        drones_menu.add_separator()
        drones_menu.add_command(label="Refresh Drones", command=lambda: self.refresh_drones())

        # Targets Menu
        targets_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Targets", menu=targets_menu)
        targets_menu.add_command(label="Add Waypoint Target", command=self.add_waypoint_target)
        targets_menu.add_command(label="Add Moving Target", command=self.add_moving_target)
        targets_menu.add_command(label="Add Fixed Target", command=self.add_fixed_target)
        targets_menu.add_command(label="Add Circle Target", command=self.add_circle_target)
        targets_menu.add_command(label="Add Polygon Target", command=self.add_polygon_target)
        targets_menu.add_separator()
        targets_menu.add_command(label="Edit Target", command=self.edit_target)
        targets_menu.add_command(label="Delete Target", command=self.delete_target)
        targets_menu.add_separator()
        targets_menu.add_command(label="Refresh Targets", command=lambda: self.refresh_targets())

        # Obstacles Menu
        obstacles_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Obstacles", menu=obstacles_menu)
        obstacles_menu.add_command(label="Add Point Obstacle", command=self.add_point_obstacle)
        obstacles_menu.add_command(label="Add Circle Obstacle", command=self.add_circle_obstacle)
        obstacles_menu.add_command(label="Add Ellipse Obstacle", command=self.add_ellipse_obstacle)
        obstacles_menu.add_command(label="Add Polygon Obstacle", command=self.add_polygon_obstacle)
        obstacles_menu.add_separator()
        obstacles_menu.add_command(label="Edit Obstacle", command=self.edit_obstacle)
        obstacles_menu.add_command(label="Delete Obstacle", command=self.delete_obstacle)
        obstacles_menu.add_separator()
        obstacles_menu.add_command(label="Refresh Obstacles", command=lambda: self.refresh_obstacles())

        # Environment Menu (moved before Tasks)
        environment_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Environment", menu=environment_menu)
        environment_menu.add_command(label="Create Environment", command=self.create_environment)
        environment_menu.add_command(label="Edit Environment", command=self.edit_environment)
        environment_menu.add_command(label="Set as Current", command=self.set_current_environment)
        environment_menu.add_command(label="Delete Environment", command=self.delete_environment)
        environment_menu.add_separator()
        environment_menu.add_command(label="Refresh Environment", command=lambda: self.refresh_environments())

        # Tasks Menu (moved after Environment)
        tasks_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tasks", menu=tasks_menu)
        tasks_menu.add_command(label="Add Task", command=self.add_task, accelerator="Ctrl+T")
        tasks_menu.add_command(label="Edit Task", command=self.edit_task)
        tasks_menu.add_command(label="Duplicate Task", command=self.duplicate_task)
        tasks_menu.add_command(label="Move Up", command=self.move_task_up)
        tasks_menu.add_command(label="Move Down", command=self.move_task_down)
        tasks_menu.add_command(label="Toggle Done/Undone", command=self.toggle_task_status)
        tasks_menu.add_command(label="Delete Task", command=self.delete_task)
        tasks_menu.add_separator()
        tasks_menu.add_command(label="Refresh Tasks", command=lambda: self.refresh_tasks())
        tasks_menu.add_separator()
        copy_accelerator = "Cmd+C" if platform.system() == 'Darwin' else "Ctrl+C"
        random_copy_accelerator = "Cmd+Shift+C" if platform.system() == 'Darwin' else "Ctrl+Shift+C"
        tasks_menu.add_command(label="Copy Original Command", command=self.copy_original_command, accelerator=copy_accelerator)
        tasks_menu.add_command(label="Copy Command", command=self.copy_random_command, accelerator=random_copy_accelerator)

        # History Menu
        history_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="History", menu=history_menu)
        history_menu.add_command(label="View History", command=self.switch_to_history_tab)
        history_menu.add_command(label="Export History", command=self.save_history_to_json)
        history_menu.add_command(label="Export Filtered", command=self.save_filtered_history_to_json)
        history_menu.add_command(label="Export Selected", command=self.save_selected_history_to_json)
        history_menu.add_separator()
        history_menu.add_command(label="Load & Run", command=self.load_history_and_run)
        history_menu.add_command(label="Clear Filters", command=self.clear_history_filters)

        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh All", command=lambda: self.refresh_all_data(), accelerator="F5")
        view_menu.add_separator()
        view_menu.add_command(label="Statistics", command=self.switch_to_statistics_tab)
        view_menu.add_command(label="Drones", command=self.switch_to_drones_tab)
        view_menu.add_command(label="Targets", command=self.switch_to_targets_tab)
        view_menu.add_command(label="Obstacles", command=self.switch_to_obstacles_tab)
        view_menu.add_command(label="Environment", command=self.switch_to_environment_tab)
        view_menu.add_command(label="Tasks", command=self.switch_to_tasks_tab)
        view_menu.add_command(label="History", command=self.switch_to_history_tab)

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_keyboard_shortcuts)

    def create_widgets(self):
        """Create the main GUI widgets"""
        # Create menu bar
        self.create_menu_bar()

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Status bar (must be initialized before any refresh/update calls)
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Create tabs
        # Insert Statistics before the Drones tab
        self.create_statistics_tab(self.notebook)
        self.create_drone_tab(self.notebook)
        self.create_target_tab(self.notebook)
        self.create_obstacles_tab(self.notebook)
        self.create_environment_tab(self.notebook)
        self.create_task_tab(self.notebook)
        self.create_history_tab(self.notebook)
        
        # Auto-refresh Statistics when the tab becomes active
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # Setup global keyboard bindings
        self.setup_global_keyboard_bindings()
        
        # Track active detail dialog
        self.active_detail_dialog = None

    def _build_list_tab(self, parent, frame_title: str, on_double_click, selectmode=tk.EXTENDED):
        """Shared factory to build a labeled listbox with scrollbar."""
        list_frame = ttk.LabelFrame(parent, text=frame_title)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        listbox = tk.Listbox(listbox_frame, selectmode=selectmode)
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        if on_double_click:
            listbox.bind('<Double-Button-1>', on_double_click)

        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        return list_frame, listbox

    def _is_gui_available(self) -> bool:
        """Return True if the Tk root/window is still alive and not closing."""
        if getattr(self, 'app_closing', False):
            return False
        try:
            return bool(self.root and self.root.winfo_exists())
        except tk.TclError:
            return False

    def on_tab_changed(self, event):
        """Refresh data associated with the newly selected tab."""
        try:
            selected = event.widget.select()
            tab_text = event.widget.tab(selected, "text")
            if tab_text == "Statistics":
                # Refresh statistics when switching to Statistics tab
                self.refresh_statistics()
            elif tab_text == "History":
                self.refresh_request_history()
        except Exception as e:
            logging.warning(f"Failed to handle tab change: {e}")

    def create_history_tab(self, notebook):
        """Create the History tab for current-session HTTP requests."""
        history_frame = ttk.Frame(notebook)
        notebook.add(history_frame, text="History")
        # One-column, three-row layout: Entries (top), Filters (middle, single row), Details (bottom)
        history_frame.grid_columnconfigure(0, weight=1)
        history_frame.grid_rowconfigure(0, weight=1)  # Entries should expand
        history_frame.grid_rowconfigure(2, weight=1)  # Details should expand

        # Entries (row 0)
        list_frame = ttk.LabelFrame(history_frame, text="History Entries")
        list_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=5, pady=5)

        # Filters (row 1) — single horizontal row
        filter_frame = ttk.LabelFrame(history_frame, text="Filters")
        filter_frame.grid(row=1, column=0, sticky=tk.EW, padx=5, pady=(0, 5))
        filter_frame.grid_columnconfigure(5, weight=1)

        ttk.Label(filter_frame, text="Method:").grid(row=0, column=0, sticky=tk.W, padx=(5, 2), pady=4)
        self.history_method_filter_var = tk.StringVar(value="All")
        method_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.history_method_filter_var,
            values=["All", "GET", "POST", "PUT", "DELETE", "PATCH"],
            state="readonly",
            width=6,
        )
        method_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 10), pady=4)
        method_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_history_tree())

        ttk.Label(filter_frame, text="Privilege:").grid(row=0, column=2, sticky=tk.W, padx=(0, 2), pady=4)
        self.history_privilege_filter_var = tk.StringVar(value="All")
        privilege_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.history_privilege_filter_var,
            values=["All", "ADMIN", "SYSTEM+", "SYSTEM", "USER+", "USER", "AGENT"],
            state="readonly",
            width=7,
        )
        privilege_combo.grid(row=0, column=3, sticky=tk.W, padx=(0, 10), pady=4)
        privilege_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_history_tree())

        ttk.Label(filter_frame, text="Endpoint:").grid(row=0, column=4, sticky=tk.W, padx=(0, 2), pady=4)
        self.history_endpoint_filter_var = tk.StringVar(value="")
        endpoint_entry = ttk.Entry(filter_frame, textvariable=self.history_endpoint_filter_var, width=26)
        endpoint_entry.grid(row=0, column=5, sticky=tk.EW, padx=(0, 10), pady=4)
        endpoint_entry.bind("<KeyRelease>", lambda e: self.refresh_history_tree())

        ttk.Label(filter_frame, text="Success:").grid(row=0, column=6, sticky=tk.W, padx=(0, 2), pady=4)
        self.history_success_filter_var = tk.StringVar(value="All")
        success_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.history_success_filter_var,
            values=["All", "Success", "Failure"],
            state="readonly",
            width=6,
        )
        success_combo.grid(row=0, column=7, sticky=tk.W, padx=(0, 10), pady=4)
        success_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_history_tree())

        clear_btn = ttk.Button(filter_frame, text="Clear", command=self.clear_history_filters)
        clear_btn.grid(row=0, column=8, sticky=tk.E, padx=5, pady=4)

        columns = ("time", "method", "privilege", "endpoint", "status", "success")
        # Enable multi-selection in history tree
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="extended")
        self.history_tree.heading("time", text="Time")
        self.history_tree.heading("method", text="Method")
        self.history_tree.heading("privilege", text="Privilege")
        self.history_tree.heading("endpoint", text="Endpoint")
        self.history_tree.heading("status", text="Status")
        self.history_tree.heading("success", text="Success")

        self.history_tree.column("time", width=160)
        self.history_tree.column("method", width=60)
        self.history_tree.column("privilege", width=70)
        self.history_tree.column("endpoint", width=250)
        self.history_tree.column("status", width=55)
        self.history_tree.column("success", width=60)

        scrollbar_hist = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar_hist.set)

        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_hist.pack(side=tk.RIGHT, fill=tk.Y)

        self.history_tree.bind("<<TreeviewSelect>>", self.on_history_select)
        select_all_sequence = (
            "<Command-a>"
            if self._shortcut_modifier() == "Command"
            else "<Control-a>"
        )
        self.history_tree.bind(select_all_sequence, self.handle_history_select_all)

        bottom_frame = ttk.Frame(history_frame)
        bottom_frame.grid(row=2, column=0, sticky=tk.NSEW, padx=5, pady=(0,5))

        # Details panel inside the bottom container
        details_frame = ttk.LabelFrame(bottom_frame, text="Details")
        details_frame.pack(fill=tk.BOTH, expand=True)

        self.history_detail_text = tk.Text(details_frame, height=10)
        self.history_detail_text.pack(fill=tk.BOTH, expand=True)

        # Action buttons below (outside) the Details box
        button_frame = ttk.Frame(bottom_frame)
        button_frame.pack(fill=tk.X, padx=0, pady=5)

        ttk.Button(button_frame, text="Refresh", command=self.refresh_request_history).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Save", command=self.save_selected_history_to_json).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Save Filtered", command=self.save_filtered_history_to_json).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Save All", command=self.save_history_to_json).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Clear History", command=self.clear_request_history).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Load & Run", command=self.load_history_and_run).pack(side=tk.LEFT, padx=2)

        # Initial population respecting filters
        self.refresh_history_tree()

    def refresh_request_history(self):
        """Load current-session HTTP request history from the API."""
        if not self._is_gui_available():
            return

        try:
            response = self.api_server.api_get_current_session_request_history(
                limit=1000,
                show_error=False,
            )
            history = response.get('request_history') if isinstance(response, dict) else None
            if not isinstance(history, list) or not all(isinstance(entry, dict) for entry in history):
                self.command_history = []
                self._clear_history_selection_and_details()
                self.refresh_history_tree()
                self.logger.warning(
                    "Could not load current-session request history: missing or invalid request_history"
                )
                self.update_status("No current session or request history is unavailable")
                return

            self.command_history = history
            self._clear_history_selection_and_details()
            self.refresh_history_tree()
            self.update_status(f"Loaded {len(history)} request history entr{'y' if len(history) == 1 else 'ies'}")
        except Exception as e:
            self.command_history = []
            self._clear_history_selection_and_details()
            self.refresh_history_tree()
            self.logger.error(f"Failed to refresh request history: {str(e)}")
            self.update_status("Failed to load request history")

    def _clear_history_selection_and_details(self):
        """Clear stale history selection and details after replacing the dataset."""
        try:
            self.history_tree.selection_remove(self.history_tree.selection())
        except Exception:
            pass
        try:
            self.history_detail_text.delete('1.0', tk.END)
        except Exception:
            pass

    def clear_request_history(self):
        """Clear current-session runtime request history through the API."""
        if not self._is_gui_available():
            return

        confirmed = messagebox.askyesno(
            "Clear History",
            "Clear all runtime request history for the current session?\n\n"
            "This does not reset the session or clear command/status/path history."
        )
        if not confirmed:
            return

        try:
            response = self.api_server.api_clear_current_session_request_history(show_error=False)
            if not isinstance(response, dict) or response.get('cleared') is not True:
                self.logger.warning(f"Failed to clear request history: unexpected response {response!r}")
                messagebox.showerror("Clear History Failed", "Failed to clear request history.")
                self.update_status("Failed to clear request history")
                return

            cleared_count = response.get('cleared_count')
            self.command_history = []
            self._clear_history_selection_and_details()
            self.refresh_history_tree()
            if isinstance(cleared_count, int):
                self.update_status(
                    f"Cleared {cleared_count} request history entr{'y' if cleared_count == 1 else 'ies'}"
                )
            else:
                self.update_status("Request history cleared")
        except Exception as e:
            self.logger.error(f"Failed to clear request history: {str(e)}")
            messagebox.showerror("Clear History Failed", f"Failed to clear request history: {str(e)}")
            self.update_status("Failed to clear request history")

    def clear_history_filters(self):
        """Reset all history filters and refresh the tree"""
        try:
            self.history_method_filter_var.set("All")
            self.history_privilege_filter_var.set("All")
            self.history_endpoint_filter_var.set("")
            self.history_success_filter_var.set("All")
        except Exception:
            pass
        self.refresh_history_tree()

    def refresh_history_tree(self):
        """Rebuild the history treeview applying current filters"""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        # Reset index mapping
        self.history_index_by_iid = {}
        method_filter, privilege_filter, endpoint_query, success_filter = self._get_history_filters()

        # Apply filters and insert
        for index, entry in enumerate(self.command_history):
            method = str(entry.get('method') or '').upper()
            endpoint = str(entry.get('path') or '')
            success = bool(entry.get('success'))

            if not self._history_entry_matches_filters(
                entry,
                method_filter,
                privilege_filter,
                endpoint_query,
                success_filter,
            ):
                continue

            iid = str(entry.get('request_id') or f"request_{index}")
            success_display = '🟢 Yes' if success else '🔴 No'
            try:
                self.history_tree.insert(
                    '', tk.END, iid=iid,
                    values=(
                        self._format_history_timestamp(entry.get('timestamp')),
                        method or '-',
                        str(entry.get('client_privilege') or '-'),
                        endpoint or '-',
                        str(entry.get('status_code', '-')),
                        success_display,
                    )
                )
            except Exception:
                # Ensure a unique IID if insertion fails
                iid = f"request_{index}_{len(self.history_tree.get_children())}"
                self.history_tree.insert(
                    '', tk.END, iid=iid,
                    values=(
                        self._format_history_timestamp(entry.get('timestamp')),
                        method or '-',
                        str(entry.get('client_privilege') or '-'),
                        endpoint or '-',
                        str(entry.get('status_code', '-')),
                        success_display,
                    )
                )
            # Map iid to entry for quick lookup on selection
            self.history_index_by_iid[iid] = entry

    def _get_history_filters(self):
        """Return current history filter values in normalized form."""
        method_filter_var = getattr(self, 'history_method_filter_var', None)
        privilege_filter_var = getattr(self, 'history_privilege_filter_var', None)
        endpoint_filter_var = getattr(self, 'history_endpoint_filter_var', None)
        success_filter_var = getattr(self, 'history_success_filter_var', None)
        method_filter = method_filter_var.get() if method_filter_var else "All"
        privilege_filter = privilege_filter_var.get() if privilege_filter_var else "All"
        endpoint_query = endpoint_filter_var.get().strip().lower() if endpoint_filter_var else ""
        success_filter = success_filter_var.get() if success_filter_var else "All"
        return method_filter, privilege_filter, endpoint_query, success_filter

    def _get_filtered_history_entries(self):
        """Return loaded history entries matching the current filters."""
        method_filter, privilege_filter, endpoint_query, success_filter = self._get_history_filters()
        return [
            entry
            for entry in self.command_history
            if self._history_entry_matches_filters(
                entry,
                method_filter,
                privilege_filter,
                endpoint_query,
                success_filter,
            )
        ]

    @staticmethod
    def _history_entry_matches_filters(
        entry,
        method_filter: str,
        privilege_filter: str,
        endpoint_query: str,
        success_filter: str,
    ) -> bool:
        """Return whether a request-history entry matches all filters."""
        if not isinstance(entry, dict):
            return False
        method = str(entry.get('method') or '').upper()
        privilege = str(entry.get('client_privilege') or '').upper()
        endpoint = str(entry.get('path') or '').lower()
        success = bool(entry.get('success'))
        return (
            (method_filter == "All" or method == method_filter)
            and (privilege_filter == "All" or privilege == privilege_filter.upper())
            and (not endpoint_query or endpoint_query in endpoint)
            and (success_filter != "Success" or success)
            and (success_filter != "Failure" or not success)
        )

    @staticmethod
    def _format_history_timestamp(value) -> str:
        """Format history timestamps as YYYY-MM-DD HH:MM:SS.mmm."""
        if value is None:
            return '-'
        try:
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                parsed = datetime.fromtimestamp(float(value))
            elif isinstance(value, str):
                trimmed = value.strip()
                if not trimmed:
                    return '-'
                try:
                    normalized = trimmed[:-1] + '+00:00' if trimmed.endswith('Z') else trimmed
                    parsed = datetime.fromisoformat(normalized)
                except ValueError:
                    parsed = datetime.fromtimestamp(float(trimmed))
            else:
                return str(value)
            return parsed.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        except (TypeError, ValueError, OSError, OverflowError):
            return str(value)

    def save_session_screenshot(self):
        """Open a single options dialog, then save current session screenshot to disk"""
        try:
            self.logger.info("Starting screenshot save process")
            options = self.prompt_screenshot_options()
            if not options:
                self.logger.info("Screenshot save cancelled by user (no options selected)")
                return
            fmt = options.get('format', 'png')
            width = int(options.get('width', 1280))
            height = int(options.get('height', 720))
            show_status = bool(options.get('show_status', False))
            show_label = bool(options.get('show_label', True))
            self.logger.info(
                "Screenshot options selected: format=%s, width=%s, height=%s, show_status=%s, show_label=%s",
                fmt,
                width,
                height,
                show_status,
                show_label
            )

            # Ensure the chosen format drives the default extension and filetype order
            ext_by_fmt = {
                "png": ".png",
                "jpg": ".jpg",
                "jpeg": ".jpeg",
                "pdf": ".pdf",
                "svg": ".svg",
                "eps": ".eps",
            }
            default_ext = ext_by_fmt.get(fmt, ".png")

            filetype_map = {
                "png": ("PNG Image", "*.png"),
                "jpg": ("JPEG Image", "*.jpg"),
                "jpeg": ("JPEG Image", "*.jpeg"),
                "pdf": ("PDF Document", "*.pdf"),
                "svg": ("SVG Image", "*.svg"),
                "eps": ("EPS Document", "*.eps"),
            }
            # Put selected format first to avoid some platforms defaulting to the first filetype (PNG)
            ordered_keys = [fmt] + [k for k in ["png", "jpg", "jpeg", "pdf", "svg", "eps"] if k != fmt]
            filetypes = [filetype_map[k] for k in ordered_keys] + [("All Files", "*.*")]

            # Generate filename from session name and ID
            session_id = self.get_current_session_id()
            session_name = self.current_session_name or "unknown"

            # Sanitize session name for use in filename
            safe_session_name = sanitize_filename(session_name)
            safe_session_id = sanitize_filename(session_id) if session_id else "unknown"

            # Create filename in format: sessionname-id-screenshot.ext
            suggested_name = f"{safe_session_name}-{safe_session_id}-screenshot{default_ext}"
            self.logger.info(f"Suggested filename: {suggested_name}")

            file_path = filedialog.asksaveasfilename(
                defaultextension=default_ext,
                filetypes=filetypes,
                initialfile=suggested_name,
                title="Save Session Screenshot"
            )
            if not file_path:
                self.logger.info("Screenshot save cancelled by user (no file path selected)")
                return

            self.logger.info(f"User selected save path: {file_path}")

            content = self.fetch_session_screenshot(
                fmt=fmt,
                width=width,
                height=height,
                show_status=show_status,
                show_label=show_label
            )
            if content:
                # Ensure directory exists
                file_dir = os.path.dirname(file_path)
                if file_dir and not os.path.exists(file_dir):
                    self.logger.info(f"Creating directory: {file_dir}")
                    os.makedirs(file_dir, exist_ok=True)
                    self.logger.info(f"Directory created successfully: {file_dir}")

                # Write file with proper error handling
                self.logger.info(f"Writing screenshot to file: {file_path} ({len(content)} bytes)")
                with open(file_path, 'wb') as f:
                    f.write(content)

                # Verify file was written successfully
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    file_size = os.path.getsize(file_path)
                    self.logger.info(
                        "Screenshot saved successfully to local folder: %s (size: %s bytes, format: %s, dimensions: %sx%s, show_status=%s, show_label=%s)",
                        file_path,
                        file_size,
                        fmt,
                        width,
                        height,
                        show_status,
                        show_label
                    )
                    messagebox.showinfo("Saved", f"Screenshot saved to:\n{file_path}")
                else:
                    raise IOError("File was not saved correctly")
            else:
                self.logger.warning("No screenshot content received from server")
        except Exception as e:
            self.logger.error(f"Failed to save screenshot to local folder: {str(e)}", exc_info=True)
            messagebox.showerror("Screenshot Error", f"Failed to save screenshot:\n{str(e)}")

    def prompt_screenshot_options(self):
        """Show a single dialog to choose format and scale preset."""
        session_id = self.get_current_session_id()
        canvas_width, canvas_height = self._get_current_session_canvas_dimensions(session_id)
        default_scale_label = self._get_default_screenshot_scale_label(canvas_width, canvas_height)
        scale_options = self._build_screenshot_scale_options(canvas_width, canvas_height)

        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Screenshot Options")
        set_window_geometry_and_center(dialog, 340, 225, self.root)
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding="16")
        frame.pack(fill=tk.BOTH, expand=True)

        # Format
        ttk.Label(frame, text="Format:").grid(row=0, column=0, sticky=tk.W)
        fmt_var = tk.StringVar(value="png")
        fmt_combo = ttk.Combobox(
            frame,
            textvariable=fmt_var,
            values=["png", "jpg", "jpeg", "pdf", "svg", "eps"],
            state="readonly",
            width=10
        )
        fmt_combo.grid(row=0, column=1, sticky=tk.W, padx=(8, 0))

        # Scale preset
        ttk.Label(frame, text="Scale:").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        default_scale_display = scale_options.get(default_scale_label, default_scale_label)
        display_to_scale = {display: label for label, display in scale_options.items()}
        scale_var = tk.StringVar(value=default_scale_display)
        scale_combo = ttk.Combobox(
            frame,
            textvariable=scale_var,
            values=list(scale_options.values()),
            state="readonly",
            width=20
        )
        scale_combo.grid(row=1, column=1, sticky=tk.W, padx=(8, 0), pady=(8, 0))

        ttk.Label(frame, text="Include Status:").grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
        show_status_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, variable=show_status_var).grid(row=2, column=1, sticky=tk.W, padx=(8, 0), pady=(8, 0))

        ttk.Label(frame, text="Show Labels:").grid(row=3, column=0, sticky=tk.W, pady=(8, 0))
        show_label_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, variable=show_label_var).grid(row=3, column=1, sticky=tk.W, padx=(8, 0), pady=(8, 0))

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=4, column=0, columnspan=2, sticky=tk.E, pady=(16, 0))

        result = {
            'format': None,
            'width': None,
            'height': None,
            'scale': None,
            'show_status': False,
            'show_label': True,
        }

        def on_ok():
            fmt = fmt_var.get().strip().lower()
            if fmt not in ["png", "jpg", "jpeg", "pdf", "svg", "eps"]:
                messagebox.showerror("Invalid Format", "Choose from png, jpg, jpeg, pdf, svg, eps", parent=dialog)
                return
            scale_label = display_to_scale.get(scale_var.get().strip())
            if scale_label not in SCREENSHOT_SCALE_PRESETS:
                messagebox.showerror("Invalid Scale", "Choose from 1x, 2x, 4x", parent=dialog)
                return
            multiplier = SCREENSHOT_SCALE_PRESETS[scale_label]
            width = canvas_width * multiplier
            height = canvas_height * multiplier
            result.update({
                'format': fmt,
                'width': width,
                'height': height,
                'scale': scale_label,
                'show_status': bool(show_status_var.get()),
                'show_label': bool(show_label_var.get()),
            })
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=6)
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.RIGHT)

        fmt_combo.focus_set()
        dialog.bind('<Return>', lambda e: on_ok())

        self.root.wait_window(dialog)
        if result['format'] is None:
            return None
        return result

    def _get_current_session_canvas_dimensions(self, session_id: Optional[str]) -> Tuple[int, int]:
        """Return current session canvas dimensions as integers."""
        default_width = 1024
        default_height = 768

        if not session_id:
            return default_width, default_height

        session_data = self.api_server.api_get_session_data(session_id, show_error=False) or {}

        try:
            width = int(round(float(session_data.get('canvas_width', default_width))))
        except (TypeError, ValueError):
            width = default_width

        raw_height = session_data.get('canvas_length')
        if raw_height is None:
            raw_height = session_data.get('canvas_height', default_height)

        try:
            height = int(round(float(raw_height)))
        except (TypeError, ValueError):
            height = default_height

        return max(1, width), max(1, height)

    def _get_default_screenshot_scale_label(self, canvas_width: int, canvas_height: int) -> str:
        """Use 2x for the base map size and 1x for larger maps."""
        if canvas_width <= 1024 and canvas_height <= 768:
            return "2x"
        return "1x"

    def _build_screenshot_scale_options(self, canvas_width: int, canvas_height: int) -> Dict[str, str]:
        """Build preset labels that include the resulting export resolution."""
        return {
            label: f"{label} ({canvas_width * factor} x {canvas_height * factor})"
            for label, factor in SCREENSHOT_SCALE_PRESETS.items()
        }

    def fetch_session_screenshot(
        self,
        fmt: str = "png",
        width: int = 1024,
        height: int = 768,
        show_status: bool = False,
        show_label: bool = True
    ) -> Optional[bytes]:
        """Download a screenshot of the current session from the server.

        Returns binary content on success, None on failure.
        """
        return self.api_server.api_get_session_screenshot(
            fmt=fmt,
            width=width,
            height=height,
            show_status=show_status,
            show_label=show_label,
            show_error=True
        )

    def on_history_select(self, event=None):
        """Show request details while preserving additional server fields."""
        selection = self.history_tree.selection()
        if not selection:
            return

        details = [
            self._format_request_history_details(self.history_index_by_iid[iid])
            for iid in selection
            if iid in self.history_index_by_iid
        ]
        details = details[0] if len(details) == 1 else details
        self.history_detail_text.delete('1.0', tk.END)
        try:
            self.history_detail_text.insert(tk.END, json.dumps(details, indent=2, ensure_ascii=False))
        except Exception:
            self.history_detail_text.insert(tk.END, str(details))

    def handle_history_select_all(self, event=None):
        """Select every currently displayed row in the history tree."""
        items = self.history_tree.get_children()
        if items:
            self.history_tree.selection_set(items)
        return "break"

    @staticmethod
    def _format_request_history_details(entry):
        """Return original labeled details plus any additional server fields."""
        if not isinstance(entry, dict):
            return entry
        known_fields = {
            'request_id',
            'timestamp',
            'method',
            'path',
            'url',
            'status_code',
            'success',
            'duration_sec',
            'request_body',
            'response_body',
            'error',
        }
        details = {
            'Request ID': entry.get('request_id'),
            'Time': UAVControllerGUI._format_history_timestamp(entry.get('timestamp')),
            'Method': entry.get('method'),
            'Path': entry.get('path'),
            'URL': entry.get('url'),
            'Status Code': entry.get('status_code'),
            'Success': entry.get('success'),
            'Duration (s)': entry.get('duration_sec'),
            'Request Body': entry.get('request_body'),
            'Response Body': entry.get('response_body'),
            'Error': entry.get('error'),
        }
        details.update({
            key: value
            for key, value in entry.items()
            if key not in known_fields
        })
        return details

    def _save_history_entries(self, entries, suggested_name: str) -> Optional[str]:
        """Save provided history entries to JSONL/JSON and return the chosen path."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".jsonl",
            filetypes=[("JSONL Files", "*.jsonl"), ("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Save History",
            initialfile=suggested_name
        )
        if not file_path:
            return None

        if file_path.endswith('.jsonl.jsonl'):
            file_path = file_path[:-len('.jsonl')]
        elif not file_path.endswith('.jsonl') and not file_path.endswith('.json'):
            file_path += '.jsonl'

        with open(file_path, 'w', encoding='utf-8') as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        return file_path

    def save_history_to_json(self):
        """Save request history to a JSONL file (one JSON per line)."""
        try:
            # Generate safe filename from session info (without extension, let the dialog handle it)
            session_name = self.current_session_name or "session"
            safe_name = sanitize_filename(session_name)
            file_path = self._save_history_entries(self.command_history, f"{safe_name}-history")
            if file_path:
                messagebox.showinfo("Saved", f"History saved to {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save history: {str(e)}")
            messagebox.showerror("Save Error", f"Failed to save history: {str(e)}")

    def save_filtered_history_to_json(self):
        """Save currently filtered request history to a JSONL file."""
        try:
            filtered_entries = self._get_filtered_history_entries()
            if not filtered_entries:
                messagebox.showwarning("No Matching Entries", "No history entries match the current filters.")
                return

            session_name = self.current_session_name or "session"
            safe_name = sanitize_filename(session_name)
            file_path = self._save_history_entries(filtered_entries, f"{safe_name}-filtered_entries")
            if file_path:
                messagebox.showinfo("Saved", f"Filtered history saved to {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save filtered history entries: {str(e)}")
            messagebox.showerror("Save Error", f"Failed to save filtered history entries: {str(e)}")

    def save_selected_history_to_json(self):
        """Save selected entries to JSONL file (one JSON per line)"""
        try:
            selection = self.history_tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select one or more history entries to save.")
                return
            selected_entries = []
            for iid in selection:
                entry = self.history_index_by_iid.get(iid)
                if entry:
                    selected_entries.append(entry)
            if not selected_entries:
                messagebox.showerror("Save Error", "Could not find selected history entries.")
                return
            # Suggest safe filename (without extension, let the dialog handle it)
            if len(selected_entries) == 1:
                # Use request ID or endpoint for a single entry.
                entry = selected_entries[0]
                entry_name = entry.get('request_id') or entry.get('path') or 'entry'
                safe_name = sanitize_filename(entry_name)
                initial_name = safe_name
            else:
                session_name = self.current_session_name or "session"
                safe_name = sanitize_filename(session_name)
                initial_name = f"{safe_name}-selected_entries"

            file_path = self._save_history_entries(selected_entries, initial_name)
            if file_path:
                messagebox.showinfo("Saved", f"Selected entries saved to {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save selected history entries: {str(e)}")
            messagebox.showerror("Save Error", f"Failed to save selected history entries: {str(e)}")

    def load_history_and_run(self):
        """Load history from JSON or JSONL file and run commands sequentially"""
        try:
            file_path = filedialog.askopenfilename(
                filetypes=[("JSONL Files", "*.jsonl"), ("JSON Files", "*.json"), ("All Files", "*.*")],
                title="Load History"
            )
            if not file_path:
                return

            # Determine file format and load accordingly
            loaded_entries = []
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.endswith('.jsonl'):
                    # JSONL format: one JSON object per line
                    for line in f:
                        line = line.strip()
                        if line:  # Skip empty lines
                            loaded_entries.append(json.loads(line))
                else:
                    # Regular JSON format
                    loaded = json.load(f)
                    # Support a single command object or a list of commands
                    if isinstance(loaded, dict):
                        loaded_entries = [loaded]
                    elif isinstance(loaded, list):
                        loaded_entries = loaded
                    else:
                        raise ValueError("History file must contain a command object or a list of entries")

            if not loaded_entries:
                messagebox.showwarning("Empty File", "No entries found in the history file")
                return

            normalized_entries = []
            for index, entry in enumerate(loaded_entries, start=1):
                normalized = self._normalize_request_history_entry_for_replay(entry)
                if normalized is None:
                    raise ValueError(f"History entry {index} must include method and path")
                normalized_entries.append(normalized)

            # Run loaded commands in a background thread
            def runner():
                total = len(normalized_entries)
                for idx, entry in enumerate(normalized_entries, start=1):
                    try:
                        self.root.after(0, lambda i=idx, t=total: self.update_status(f"Running loaded history {i}/{t}"))
                        self.api_server.api_generic_request(
                            entry['method'],
                            entry['endpoint'],
                            entry.get('payload'),
                            params=entry['params'],
                        )
                    except Exception as e:
                        self.logger.error(f"Failed to run loaded entry: {str(e)}")
                self.root.after(0, lambda: self.update_status("Ready"))
                self.root.after(0, lambda: messagebox.showinfo("Done", f"Loaded and executed {total} commands."))

            threading.Thread(target=runner, daemon=True).start()

        except Exception as e:
            self.logger.error(f"Failed to load and run history: {str(e)}")
            messagebox.showerror("Load Error", f"Failed to load and run history: {str(e)}")

    @staticmethod
    def _normalize_request_history_entry_for_replay(entry):
        """Normalize a request-history entry for generic API replay."""
        if not isinstance(entry, dict):
            return None
        method = entry.get('method')
        endpoint = entry.get('path') or entry.get('endpoint')
        if not method or not endpoint:
            return None
        return {
            'method': str(method),
            'endpoint': str(endpoint),
            'payload': entry.get('request_body', entry.get('payload')),
            'params': entry.get('query_params') or {},
        }

    def setup_global_keyboard_bindings(self):
        """Setup global keyboard bindings for the main GUI."""
        self.root.focus_set()
        self.global_shortcuts = {}

        def bind(sequence, handler):
            self.root.bind_all(sequence, handler)
            self.global_shortcuts[sequence] = handler

        bind('<space>', self.handle_spacebar)

        shortcut_modifier = self._shortcut_modifier()

        # Cmd/Ctrl+S to save session, Cmd/Ctrl+Shift+S to save session as
        if shortcut_modifier == 'Command':  # macOS
            bind('<Command-s>', lambda event: self.save_session())
            bind('<Command-Shift-s>', lambda event: self.save_session_as())
            bind('<Command-Shift-S>', lambda event: self.save_session_as())
            bind('<Command-c>', self.handle_tasks_copy_shortcut)
            bind('<Command-Shift-c>', self.handle_tasks_random_copy_shortcut)
            bind('<Command-Shift-C>', self.handle_tasks_random_copy_shortcut)
            bind('<Command-i>', lambda event: self.show_session_info())
            bind('<Command-w>', self.handle_close_shortcut)
        else:  # Windows/Linux
            bind('<Control-s>', lambda event: self.save_session())
            bind('<Control-Shift-s>', lambda event: self.save_session_as())
            bind('<Control-Shift-S>', lambda event: self.save_session_as())
            bind('<Control-c>', self.handle_tasks_copy_shortcut)
            bind('<Control-Shift-c>', self.handle_tasks_random_copy_shortcut)
            bind('<Control-Shift-C>', self.handle_tasks_random_copy_shortcut)
            bind('<Control-i>', lambda event: self.show_session_info())
            bind('<Control-w>', self.handle_close_shortcut)
        self.global_shortcuts_enabled = True

    @staticmethod
    def _shortcut_modifier():
        """Return the Tk modifier used for primary app shortcuts on this platform."""
        return 'Command' if platform.system() == 'Darwin' else 'Control'
    
    def disable_global_shortcuts(self):
        """Disable all global shortcuts while a dialog is open."""
        if getattr(self, 'global_shortcuts_enabled', True):
            for sequence in getattr(self, 'global_shortcuts', {}).keys():
                self.root.unbind_all(sequence)
            self.global_shortcuts_enabled = False

    def enable_global_shortcuts(self):
        """Re-enable all global shortcuts."""
        if not getattr(self, 'global_shortcuts_enabled', False):
            for sequence, handler in getattr(self, 'global_shortcuts', {}).items():
                self.root.bind_all(sequence, handler)
            self.global_shortcuts_enabled = True

    def handle_tasks_copy_shortcut(self, event):
        """Copy original command when Cmd/Ctrl+C is pressed on the Tasks tab."""
        if not hasattr(self, 'notebook'):
            return None

        current_tab = self.notebook.tab(self.notebook.select(), "text")
        if current_tab != "Tasks":
            return None

        if not getattr(self, 'task_listbox', None) or not self.task_listbox.curselection():
            return "break"

        self.copy_original_command()
        return "break"

    def handle_tasks_random_copy_shortcut(self, event):
        """Copy a random command when Ctrl/Cmd+Shift+C is pressed on the Tasks tab."""
        if not hasattr(self, 'notebook'):
            return None

        current_tab = self.notebook.tab(self.notebook.select(), "text")
        if current_tab != "Tasks":
            return None

        if not getattr(self, 'task_listbox', None) or not self.task_listbox.curselection():
            return "break"

        self.copy_random_command()
        return "break"

    def _has_open_popout(self) -> bool:
        """Return True when any visible child dialog is open."""
        try:
            for child in self.root.winfo_children():
                if isinstance(child, tk.Toplevel):
                    try:
                        if child.winfo_exists() and child.winfo_viewable():
                            return True
                    except tk.TclError:
                        continue
        except tk.TclError:
            return False
        return False

    def _maybe_enable_global_shortcuts(self):
        """Enable global shortcuts only when no popout windows are visible."""
        if not self._has_open_popout():
            self.enable_global_shortcuts()

    def handle_close_shortcut(self, event):
        """Close the GUI controller window with Ctrl/Cmd+W."""
        if self._has_open_popout():
            self.update_status("Close shortcut disabled while a dialog is open")
            return "break"
        self.on_closing()
        return "break"

    def handle_spacebar(self, event):
        """Handle spacebar key press to show/close detail dialogs"""
        # If there's an active detail dialog, close it
        if self.active_detail_dialog:
            self.active_detail_dialog.destroy()
            self.active_detail_dialog = None
            return

        # Determine which tab is currently active
        notebook = getattr(self, 'notebook', None)
        if notebook is None or not notebook.winfo_exists():
            return
        try:
            current_tab = notebook.select()
            if not current_tab:
                return
            tab_text = notebook.tab(current_tab, "text")
        except tk.TclError:
            return

        # Show detail dialog based on current tab and selection
        if tab_text == "Drones":
            selection = self.drone_listbox.curselection()
            if selection:
                self.show_drone_details(None)
        elif tab_text == "Targets":
            selection = self.target_listbox.curselection()
            if selection:
                self.show_target_details(None)
        elif tab_text == "Obstacles":
            selection = self.obstacles_listbox.curselection()
            if selection:
                self.show_obstacle_details(None)
        elif tab_text == "Environment":
            selection = self.env_listbox.curselection()
            if selection:
                self.show_environment_details(None)
        elif tab_text == "Tasks":
            selection = self.task_listbox.curselection()
            if selection:
                self.show_task_details(None)
        elif tab_text == "Statistics":
            self.view_current_session_data()
    
    def create_drone_tab(self, notebook):
        """Create the drone management tab"""
        drone_frame = ttk.Frame(notebook)
        notebook.add(drone_frame, text="Drones")

        _, self.drone_listbox = self._build_list_tab(
            drone_frame, "Registered Drones", self.show_drone_details
        )
        self.drone_listbox.bind('<<ListboxSelect>>', lambda _: self.update_takeoff_land_button())

        # Drone control buttons
        button_frame = ttk.Frame(drone_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(button_frame, text="Add", command=self.add_drone).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="Edit", command=self.edit_drone).pack(side=tk.LEFT, padx=1)
        self.takeoff_land_button = ttk.Button(button_frame, text="Take Off", command=self.toggle_takeoff_land)
        self.takeoff_land_button.pack(side=tk.LEFT, padx=1)
        self.move_to_button = ttk.Button(button_frame, text="Move To", command=self.drone_move_to)
        self.move_to_button.pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="Control", command=self.open_realtime_control).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="Delete", command=self.delete_drone).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="Refresh", command=self.refresh_drones).pack(side=tk.RIGHT, padx=1)

    def create_statistics_tab(self, notebook):
        """Create the Statistics tab to show session overview and stats"""
        stats_frame = ttk.Frame(notebook)
        notebook.add(stats_frame, text="Statistics")

        # Overview section
        overview = ttk.LabelFrame(stats_frame, text="Session Overview")
        overview.pack(fill=tk.X, padx=5, pady=(5, 0))

        self.stats_session_name_var = tk.StringVar(value="-")
        self.stats_status_var = tk.StringVar(value="-")
        self.stats_created_var = tk.StringVar(value="-")
        self.stats_updated_var = tk.StringVar(value="-")
        self.stats_task_type_var = tk.StringVar(value="-")
        self.stats_task_count_var = tk.StringVar(value="-")
        self.stats_task_status_summary_var = tk.StringVar(value="-")

        for col in range(4):
            overview.grid_columnconfigure(col, weight=1)

        ttk.Label(overview, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(overview, textvariable=self.stats_session_name_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(overview, text="Task Type:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(overview, textvariable=self.stats_task_type_var).grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)

        ttk.Label(overview, text="Created:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(overview, textvariable=self.stats_created_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(overview, text="Last Updated:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(overview, textvariable=self.stats_updated_var).grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
        ttk.Label(overview, text="Status:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(overview, textvariable=self.stats_status_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)


        # Statistics section
        stats_box = ttk.LabelFrame(stats_frame, text="Statistics")
        stats_box.pack(fill=tk.X, padx=5, pady=5)

        self.stats_drone_count_var = tk.StringVar(value="0")
        self.stats_target_count_var = tk.StringVar(value="0")
        self.stats_obstacle_count_var = tk.StringVar(value="0")
        self.stats_commands_executed_var = tk.StringVar(value="0")
        self.stats_total_flight_time_var = tk.StringVar(value="0.0 s")
        self.stats_total_distance_var = tk.StringVar(value="0.0")

        for col in range(6):
            stats_box.grid_columnconfigure(col, weight=1)

        ttk.Label(stats_box, text="Drones:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_box, textvariable=self.stats_drone_count_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_box, text="Targets:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_box, textvariable=self.stats_target_count_var).grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_box, text="Obstacles:").grid(row=0, column=4, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_box, textvariable=self.stats_obstacle_count_var).grid(row=0, column=5, sticky=tk.W, padx=5, pady=2)

        ttk.Label(stats_box, text="Tasks:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_box, textvariable=self.stats_task_count_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_box, text="Task Status:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_box, textvariable=self.stats_task_status_summary_var).grid(row=1, column=3, columnspan=3, sticky=tk.W, padx=5, pady=2)

        ttk.Label(stats_box, text="Commands Executed:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_box, textvariable=self.stats_commands_executed_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_box, text="Total Flight Time:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_box, textvariable=self.stats_total_flight_time_var).grid(row=2, column=3, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_box, text="Total Distance:").grid(row=2, column=4, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_box, textvariable=self.stats_total_distance_var).grid(row=2, column=5, sticky=tk.W, padx=5, pady=2)

        # Session tracking section
        tracking_box = ttk.LabelFrame(stats_frame, text="Session Tracking")
        tracking_box.pack(fill=tk.X, padx=5, pady=(0, 5))

        # API reference-aligned tracking stats
        self.stats_command_history_size_var = tk.StringVar(value='-')
        self.stats_target_reach_log_size_var = tk.StringVar(value='-')
        self.stats_total_target_reaches_var = tk.StringVar(value='-')
        self.stats_drones_with_target_reaches_var = tk.StringVar(value='-')
        self.stats_unique_targets_reached_var = tk.StringVar(value='-')
        self.stats_session_time_var = tk.StringVar(value='-')
        self.stats_task_progress_var = tk.StringVar(value="-")
        self.stats_task_completed_var = tk.StringVar(value="-")

        for col in range(6):
            tracking_box.grid_columnconfigure(col, weight=1)

        ttk.Label(tracking_box, text="Command History Size:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(tracking_box, textvariable=self.stats_command_history_size_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(tracking_box, text="Target Reach Log Size:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(tracking_box, textvariable=self.stats_target_reach_log_size_var).grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        ttk.Label(tracking_box, text="Total Target Reaches:").grid(row=0, column=4, sticky=tk.W, padx=5, pady=2)
        ttk.Label(tracking_box, textvariable=self.stats_total_target_reaches_var).grid(row=0, column=5, sticky=tk.W, padx=5, pady=2)

        ttk.Label(tracking_box, text="Drones With Target Reaches:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(tracking_box, textvariable=self.stats_drones_with_target_reaches_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(tracking_box, text="Unique Targets Reached:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(tracking_box, textvariable=self.stats_unique_targets_reached_var).grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
        ttk.Label(tracking_box, text="Session Time:").grid(row=1, column=4, sticky=tk.W, padx=5, pady=2)
        ttk.Label(tracking_box, textvariable=self.stats_session_time_var).grid(row=1, column=5, sticky=tk.W, padx=5, pady=2)

        ttk.Label(tracking_box, text="Task Progress:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(tracking_box, textvariable=self.stats_task_progress_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(tracking_box, text="Task Completed:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(tracking_box, textvariable=self.stats_task_completed_var).grid(row=2, column=3, sticky=tk.W, padx=5, pady=2)

        # Drones breakdown section
        drones_box = ttk.LabelFrame(stats_frame, text="Drones Summary")
        drones_box.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.stats_drones_by_status_var = tk.StringVar(value="-")
        self.stats_drones_avg_speed_var = tk.StringVar(value="-")
        self.stats_drones_avg_battery_var = tk.StringVar(value="-")

        ttk.Label(drones_box, text="By Status:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(drones_box, textvariable=self.stats_drones_by_status_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(drones_box, text="Avg Speed:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(drones_box, textvariable=self.stats_drones_avg_speed_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(drones_box, text="Avg Battery:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(drones_box, textvariable=self.stats_drones_avg_battery_var).grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)

        # Targets breakdown section
        targets_box = ttk.LabelFrame(stats_frame, text="Targets Summary")
        targets_box.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.stats_targets_by_type_var = tk.StringVar(value="-")
        ttk.Label(targets_box, text="By Type:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(targets_box, textvariable=self.stats_targets_by_type_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        # Obstacles breakdown section
        obstacles_box = ttk.LabelFrame(stats_frame, text="Obstacles Summary")
        obstacles_box.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.stats_obstacles_by_type_var = tk.StringVar(value="-")
        ttk.Label(obstacles_box, text="By Type:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(obstacles_box, textvariable=self.stats_obstacles_by_type_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        # Controls
        controls = ttk.Frame(stats_frame)
        controls.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(controls, text="Reset", command=self.reset_session_from_statistics).pack(side=tk.RIGHT, padx=2)
        ttk.Button(controls, text="Refresh", command=self.refresh_statistics).pack(side=tk.RIGHT, padx=2)
        ttk.Button(controls, text="Screenshot", command=self.save_session_screenshot).pack(side=tk.RIGHT, padx=2)
        ttk.Button(controls, text="Save Session", command=self.save_session).pack(side=tk.RIGHT, padx=2)
        ttk.Button(controls, text="View Full Data", command=self.view_current_session_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls, text="Visually Edit Session", command=self.edit_current_session_visually).pack(side=tk.LEFT, padx=2)
    
    def create_target_tab(self, notebook):
        """Create the target management tab"""
        target_frame = ttk.Frame(notebook)
        notebook.add(target_frame, text="Targets")

        _, self.target_listbox = self._build_list_tab(
            target_frame, "Targets", self.show_target_details
        )

        # Target control buttons
        button_frame = ttk.Frame(target_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(button_frame, text="+Waypoint", command=self.add_waypoint_target).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="+Moving", command=self.add_moving_target).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="+Fixed", command=self.add_fixed_target).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="+Circle", command=self.add_circle_target).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="+Polygon", command=self.add_polygon_target).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="Edit", command=self.edit_target).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="Delete", command=self.delete_target).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="Refresh", command=self.refresh_targets).pack(side=tk.RIGHT, padx=1)
    
    def create_obstacles_tab(self, notebook):
        """Create the obstacles management tab"""
        obstacles_frame = ttk.Frame(notebook)
        notebook.add(obstacles_frame, text="Obstacles")

        _, self.obstacles_listbox = self._build_list_tab(
            obstacles_frame, "Obstacles", self.show_obstacle_details
        )

        # Obstacles control buttons
        button_frame = ttk.Frame(obstacles_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(button_frame, text="+Point", command=self.add_point_obstacle).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="+Circle", command=self.add_circle_obstacle).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="+Ellipse", command=self.add_ellipse_obstacle).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="+Polygon", command=self.add_polygon_obstacle).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="Edit", command=self.edit_obstacle).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="Delete", command=self.delete_obstacle).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="Refresh", command=self.refresh_obstacles).pack(side=tk.RIGHT, padx=1)
    
    def create_environment_tab(self, notebook):
        """Create the environment management tab"""
        env_frame = ttk.Frame(notebook)
        notebook.add(env_frame, text="Environment")

        _, self.env_listbox = self._build_list_tab(
            env_frame, "Environments", self.show_environment_details
        )

        # Hint label
        hint_frame = ttk.Frame(env_frame)
        hint_frame.pack(fill=tk.X, padx=5, pady=(2, 0))
        hint_label = ttk.Label(hint_frame, text="💡 Hint: Only one environment will be saved, please set the environment you want to save as current.",
                              foreground='#666666', font=('Arial', 9, 'italic'))
        hint_label.pack(side=tk.LEFT, padx=5)

        # Environment control buttons
        button_frame = ttk.Frame(env_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(button_frame, text="Create Environment", command=self.create_environment).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="Edit", command=self.edit_environment).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="Set as Current", command=self.set_current_environment).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="Delete Environment", command=self.delete_environment).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="Refresh", command=self.refresh_environments).pack(side=tk.RIGHT, padx=1)

    def create_task_tab(self, notebook):
        """Create the task management tab"""
        task_frame = ttk.Frame(notebook)
        notebook.add(task_frame, text="Tasks")

        is_macos = platform.system() == "Darwin"

        def create_task_button(parent, **kwargs):
            if is_macos:
                # padding = kwargs.pop("padding", (0, 0))
                # padx, pady = padding
                width = kwargs.get("width")
                if isinstance(width, int):
                    kwargs["width"] = max(width - 1, 1)
                return tk.Button(
                    parent,
                    padx=-10,
                    **kwargs,
                )
            return ttk.Button(parent, **kwargs)

        # Task list frame
        list_frame = ttk.LabelFrame(task_frame, text="Tasks in Current Session")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Task listbox with scrollbar
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.task_listbox = tk.Listbox(listbox_frame, selectmode=tk.EXTENDED)
        scrollbar_task = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.task_listbox.yview)
        self.task_listbox.configure(yscrollcommand=scrollbar_task.set)
        self.task_listbox.bind('<Double-Button-1>', self.show_task_details)

        self.task_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_task.pack(side=tk.RIGHT, fill=tk.Y)

        # Task control buttons - First row
        button_frame_1 = ttk.Frame(task_frame)
        button_frame_1.pack(fill=tk.X, padx=4, pady=2)

        # Left side: Main operations
        create_task_button(button_frame_1, text="Add", command=self.create_task, width=4).pack(side=tk.LEFT, padx=1)
        create_task_button(button_frame_1, text="Edit", command=self.edit_task, width=4).pack(side=tk.LEFT, padx=1)
        create_task_button(button_frame_1, text="Duplicate", command=self.duplicate_task, width=8).pack(side=tk.LEFT, padx=1)
        create_task_button(button_frame_1, text="Delete", command=self.delete_task, width=6).pack(side=tk.LEFT, padx=1)

        # Move buttons
        create_task_button(button_frame_1, text="↑", command=self.move_task_up, width=2).pack(side=tk.LEFT, padx=1)
        create_task_button(button_frame_1, text="↓", command=self.move_task_down, width=2).pack(side=tk.LEFT, padx=1)

        # Right side: Template and refresh
        create_task_button(button_frame_1, text="Refresh", command=self.refresh_tasks, width=8).pack(side=tk.RIGHT, padx=1)
        create_task_button(button_frame_1, text="RandomGen", command=self.random_generate_tasks, width=10).pack(side=tk.RIGHT, padx=1)
        create_task_button(button_frame_1, text="From Template", command=self.create_task_from_template, width=14).pack(side=tk.RIGHT, padx=1)

        # Task control buttons - Second row
        button_frame_2 = ttk.Frame(task_frame)
        button_frame_2.pack(fill=tk.X, padx=4, pady=2)

        # Copy buttons
        create_task_button(button_frame_2, text="Copy Original Command", command=self.copy_original_command, width=22).pack(side=tk.LEFT, padx=1)
        create_task_button(button_frame_2, text="Copy Command", command=self.copy_random_command, width=14).pack(side=tk.LEFT, padx=1)

        # Status toggle button
        self.task_toggle_button = create_task_button(button_frame_2, text="Done", command=self.toggle_task_status, width=6)
        self.task_toggle_button.pack(side=tk.LEFT, padx=1)

        # Check buttons
        create_task_button(button_frame_2, text="Check", command=self.check_task_completion, width=5).pack(side=tk.LEFT, padx=1)
        create_task_button(button_frame_2, text="Export Results", command=self.export_check_results, width=12).pack(side=tk.LEFT, padx=1)

        # Task control buttons - Third row
        button_frame_3 = ttk.Frame(task_frame)
        button_frame_3.pack(fill=tk.X, padx=4, pady=2)

        create_task_button(button_frame_3, text="Land all Drones", command=self.land_all_drones, width=16).pack(side=tk.LEFT, padx=1)
        create_task_button(button_frame_3, text="Charge all Drones", command=self.charge_all_drones, width=18).pack(side=tk.LEFT, padx=1)
        self.send_task_to_agent_button = create_task_button(
            button_frame_3,
            text="Send Task to Agent",
            command=self.send_selected_task_to_agent,
            width=20,
        )
        self.send_task_to_agent_button.pack(side=tk.LEFT, padx=1)

        # Bind selection change to update button text
        self.task_listbox.bind('<<ListboxSelect>>', self.on_task_selection_changed)

    def format_delete_id_list(self, ids: list, max_items: int = 8) -> str:
        """Format an ID list for delete confirmation dialogs."""
        if not ids:
            return ""
        if len(ids) <= max_items:
            return ", ".join(ids)
        visible = ", ".join(ids[:max_items])
        return f"{visible}, etc ({len(ids)} total)"

    def ask_delete_confirmation(self, title: str, message: str) -> bool:
        """Show delete confirmation dialog with Cancel button focused

        Args:
            title: Dialog title
            message: Confirmation message

        Returns:
            True if user confirms deletion, False otherwise
        """
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        width = 400
        height = 150
        set_window_geometry_and_center(dialog, width, height, self.root)

        result = [False]

        # Message
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=message, wraplength=350).pack(pady=(0, 20))

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack()

        def on_delete():
            result[0] = True
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        delete_button = ttk.Button(button_frame, text="Delete", command=on_delete)
        delete_button.pack(side=tk.LEFT, padx=5)
        cancel_button = ttk.Button(button_frame, text="Cancel", command=on_cancel)
        cancel_button.pack(side=tk.LEFT, padx=5)

        # Focus on Cancel button for safety
        cancel_button.focus_set()

        # Bind Escape to cancel
        dialog.bind('<Escape>', lambda _: on_cancel())

        self.root.wait_window(dialog)
        return result[0]

    def _compose_window_title(self) -> str:
        """Build the window title with session context and unsaved indicator."""
        base_title = "MultiUAV-Plat Control System - GUI Controller"
        session_bits = []
        if self.current_session_name:
            session_bits.append(self.current_session_name)
        if self.current_session_id:
            session_bits.append(f"({self.current_session_id})")
        if session_bits:
            base_title = f"{base_title} - {' '.join(session_bits)}"
        if self.is_modified:
            return f"*{base_title}"
        return base_title

    def _update_window_title(self):
        """Apply the composed title to the window."""
        self.root.title(self._compose_window_title())

    def set_modified(self, modified: bool = True):
        """Mark the session as modified (having unsaved changes).

        Args:
            modified: True to mark as modified, False to mark as saved
        """
        self.is_modified = modified
        # Invalidate cached session payload when we know local state changed
        if modified:
            self._cached_current_session_payload = None
        self._update_window_title()

    def save_session(self):
        """Manual save session triggered by user (button or Cmd/Ctrl+S)."""
        self.logger.info("User triggered manual save session")
        self.update_status("Saving session...")

        saved_path = save_current_session_to_file(
            self._get_cached_or_remote_session,
            target_filepath=self.imported_session_filepath,
            logger=self.logger
        )

        if saved_path:
            self.imported_session_filepath = saved_path
            self.set_modified(False)
            messagebox.showinfo("Success", "Session saved successfully")
            self.update_status("Session saved")
        else:
            messagebox.showerror("Error", "Failed to save session")
            self.update_status("Failed to save session")

    def reset_session_from_statistics(self):
        """Reset the current session via file reload or reset endpoint."""
        confirm = messagebox.askyesno(
            "Reset Session",
            "Reset the current session?\n\n"
            "If a session JSON file exists, it will be reloaded.\n"
            "Otherwise, the session will be reset on the server."
        )
        if not confirm:
            return

        session_id = self.get_current_session_id()
        if not session_id:
            messagebox.showerror("Reset Failed", "Could not determine the current session ID.")
            return

        identifier = self.imported_session_filepath or session_id
        reloaded = False

        try:
            payload, resolved_path = load_session_from_file(identifier)
            request_data = normalize_session_canvas_fields(payload)
            response = self.api_server.api_new_session_with_id(session_id, request_data)
            if not response:
                raise RuntimeError("Failed to reload session data on the server.")
            self.imported_session_filepath = str(resolved_path)
            self.set_modified(False)
            self.update_status("Session reloaded from file")
            reloaded = True
        except FileNotFoundError:
            self.logger.info("No session file found; using reset endpoint.")
        except Exception as exc:
            self.logger.error(f"Failed to reload session from file: {exc}")
            messagebox.showerror("Reset Failed", f"Failed to reload session from file: {exc}")
            self.update_status("Failed to reload session from file")
            return

        if not reloaded:
            self.update_status("Resetting session...")
            response = self.api_server.api_reset_session()
            if not response:
                messagebox.showerror("Reset Failed", "Failed to reset session.")
                self.update_status("Failed to reset session")
                return
            self.set_modified(False)
            self.update_status("Session reset")

        # Check results reflect pre-reset runtime state and can override fresh
        # task is_done values in refresh_tasks(), so clear them before repainting.
        if hasattr(self, 'task_check_results'):
            self.task_check_results.clear()
        self._cached_current_session_payload = None
        self.refresh_all_data()

    def export_current_session(self):
        """Export the active session to a JSON file."""
        try:
            session_id = self.get_current_session_id()

            session_name = self.current_session_name or session_id
            self.update_status("Exporting session...")

            session_data = self.api_server.api_get_session_data(session_id)
            if not session_data:
                self.update_status("Failed to load session data for export")
                return

            safe_name = sanitize_filename(session_name)
            safe_id = sanitize_filename(session_id)
            suggested_filename = f"{safe_name}-{safe_id}-export.json"

            filename = filedialog.asksaveasfilename(
                title="Export Session",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile=suggested_filename
            )

            if not filename:
                self.update_status("Export cancelled")
                return

            cleaned_session_data = _clean_session_data_for_export(session_data)
            server_version = None
            try:
                server_version = self.api_server.api_get_server_version(show_error=False)
            except Exception as exc:
                self.logger.debug(f"Failed to fetch server version for export: {exc}")
            export_data = {
                "export_info": {
                    "exported_at": datetime.now().isoformat(),
                    "exported_by": "MultiUAV-Plat Controller",
                    "version": self.version,
                    "server_version": server_version
                },
                **cleaned_session_data
            }

            with open(filename, "w", encoding="utf-8") as export_file:
                json.dump(export_data, export_file, indent=2, ensure_ascii=False)

            stats = session_data.get("statistics", {}) or {}
            messagebox.showinfo(
                "Success",
                f"Session exported successfully to:\n{filename}\n\n"
                f"Export contains:\n"
                f"• {stats.get('drone_count', 0)} drones\n"
                f"• {stats.get('target_count', 0)} targets\n"
                f"• {stats.get('obstacle_count', 0)} obstacles\n"
                f"• Environment: {'Yes' if session_data.get('environment') else 'No'}"
            )
            self.update_status("Session exported successfully")
        except Exception as exc:
            self.logger.error(f"Failed to export session: {exc}")
            messagebox.showerror("Export Error", f"Failed to export session: {exc}")
            self.update_status("Failed to export session")

    def get_current_session_id(self) -> Optional[str]:
        """Get the current session ID from cache or API.

        Returns the cached session ID if available, otherwise fetches from server.
        """
        if self.current_session_id:
            return self.current_session_id

        # Fetch from server if not cached
        session_data = self.api_server.api_get_current_session()
        if session_data and 'id' in session_data:
            self.current_session_id = session_data['id']
            self.current_session_name = session_data.get('name', self.current_session_id)
            self._update_window_title()
            return self.current_session_id

        return None

    def update_session_cache(self, session_id: str, session_name: Optional[str] = None):
        """Update the cached session ID and name."""
        self.current_session_id = session_id
        if session_name:
            self.current_session_name = session_name
        self._update_window_title()
        self._cached_current_session_payload = None

    def update_status(self, message: str):
        """Update the status bar"""
        self.status_var.set(message)
        self.root.update_idletasks()

    def _summarize_tasks(self, tasks=None) -> tuple[str, str]:
        """Return total task count and a compact done/pending summary."""
        if tasks is None:
            tasks = self.task_data
        tasks = tasks if isinstance(tasks, list) else []

        total_tasks = len(tasks)
        done_tasks = sum(1 for task in tasks if task.get('is_done', False))
        pending_tasks = total_tasks - done_tasks

        if total_tasks == 0:
            return "0", "-"
        return str(total_tasks), f"Done: {done_tasks}, Pending: {pending_tasks}"

    def _build_session_stats(self, session: dict, drones=None, targets=None, obstacles=None, tasks=None) -> SessionStats:
        """Normalize session statistics into a UI-friendly structure."""
        stats = session.get('statistics') or {}
        task_type = session.get('task_type') or stats.get('task_type') or '-'

        drone_count = to_int(stats.get('drone_count'))
        target_count = to_int(stats.get('target_count'))
        obstacle_count = to_int(stats.get('obstacle_count'))
        commands_executed = to_int(stats.get('total_commands_executed'))
        total_flight_time = to_float(stats.get('total_flight_time'))
        total_distance = to_float(stats.get('total_distance_traveled'))

        command_history_size = to_int(stats.get('command_history_size'))
        target_reach_log_size = to_int(stats.get('target_reach_log_size'))
        total_target_reaches = to_int(stats.get('total_target_reaches'))
        drones_with_target_reaches = to_int(stats.get('drones_with_target_reaches'))
        unique_targets_reached = to_int(stats.get('unique_targets_reached'))
        session_time = to_float(stats.get('session_time'))

        # Task progress
        task_progress_payload = session.get('task_progress') or stats.get('task_progress')
        progress_pct = None
        progress_complete = None
        if isinstance(task_progress_payload, dict):
            progress_pct = to_int(task_progress_payload.get('progress_percentage'))
            progress_complete = task_progress_payload.get('is_completed')
        else:
            progress_pct = to_int(stats.get('progress_percentage'))
            progress_complete = stats.get('is_completed')

        progress_text = f"{progress_pct}%" if progress_pct is not None else '-'
        progress_complete_text = '-' if progress_complete is None else ('Yes' if bool(progress_complete) else 'No')
        task_count_text, task_status_summary = self._summarize_tasks(
            tasks if tasks is not None else session.get('tasks')
        )

        # Drones summary
        if drones is None:
            drones = self.api_server.api_get_drones()
        drones = drones or []
        status_counts: Dict[str, int] = {}
        speeds = []
        batteries = []
        for d in drones:
            status = (d.get('status') or 'unknown').lower()
            status_counts[status] = status_counts.get(status, 0) + 1
            spd = d.get('speed')
            if isinstance(spd, (int, float)):
                speeds.append(float(spd))
            bat = d.get('battery_level')
            if isinstance(bat, (int, float)):
                batteries.append(float(bat))

        if status_counts:
            sorted_items = sorted(status_counts.items(), key=lambda kv: (-kv[1], kv[0]))
            drones_by_status = ", ".join([f"{name}: {cnt}" for name, cnt in sorted_items[:6]])
        else:
            drones_by_status = '-'

        avg_speed = sum(speeds) / len(speeds) if speeds else None
        avg_battery = sum(batteries) / len(batteries) if batteries else None

        # Targets summary
        if targets is None:
            targets = self.api_server.api_get_targets()
        targets = targets or []
        type_counts: Dict[str, int] = {}
        for t in targets:
            ttype = t.get('type') or 'unknown'
            ttype = str(ttype).lower()
            type_counts[ttype] = type_counts.get(ttype, 0) + 1
        if type_counts:
            sorted_items = sorted(type_counts.items(), key=lambda kv: (-kv[1], kv[0]))
            targets_by_type = ", ".join([f"{name}: {cnt}" for name, cnt in sorted_items[:6]])
        else:
            targets_by_type = '-'

        # Obstacles summary
        if obstacles is None:
            obstacles = self.api_server.api_get_obstacles()
        obstacles = obstacles or []
        obst_counts: Dict[str, int] = {}
        for o in obstacles:
            otype = o.get('type') or 'unknown'
            otype = str(otype).lower()
            obst_counts[otype] = obst_counts.get(otype, 0) + 1
        if obst_counts:
            sorted_items = sorted(obst_counts.items(), key=lambda kv: (-kv[1], kv[0]))
            obstacles_by_type = ", ".join([f"{name}: {cnt}" for name, cnt in sorted_items[:6]])
        else:
            obstacles_by_type = '-'

        return SessionStats(
            name=str(session.get('name') or session.get('id') or '-'),
            status=str(session.get('status') or 'unknown'),
            created=format_timestamp(session.get('created_at')),
            updated=format_timestamp(session.get('last_updated')),
            task_type=str(task_type).replace('_', ' ').title() if task_type else '-',
            task_count=task_count_text,
            task_status_summary=task_status_summary,
            task_progress_text=progress_text,
            task_completed_text=progress_complete_text,
            drone_count=str(drone_count if drone_count is not None else '-'),
            target_count=str(target_count if target_count is not None else '-'),
            obstacle_count=str(obstacle_count if obstacle_count is not None else '-'),
            commands_executed=str(commands_executed if commands_executed is not None else '-'),
            total_flight_time=f'{format_number(total_flight_time)} s' if total_flight_time is not None else '-',
            total_distance=f'{format_number(total_distance)}' if total_distance is not None else '-',
            command_history_size=str(command_history_size) if command_history_size is not None else '-',
            target_reach_log_size=str(target_reach_log_size) if target_reach_log_size is not None else '-',
            total_target_reaches=str(total_target_reaches) if total_target_reaches is not None else '-',
            drones_with_target_reaches=str(drones_with_target_reaches) if drones_with_target_reaches is not None else '-',
            unique_targets_reached=str(unique_targets_reached) if unique_targets_reached is not None else '-',
            session_time=f"{format_number(session_time)} s" if session_time is not None else '-',
            drones_by_status=drones_by_status,
            drones_avg_speed=f"{format_number(avg_speed)}" if avg_speed is not None else '-',
            drones_avg_battery=f"{format_number(avg_battery)}%" if avg_battery is not None else '-',
            targets_by_type=targets_by_type,
            obstacles_by_type=obstacles_by_type,
        )

    # Statistics methods
    def refresh_statistics(self, session=None, drones=None, targets=None, obstacles=None, tasks=None):
        """Refresh current session statistics and overview.

        Optional datasets let callers reuse existing API responses to limit duplicate traffic.
        """
        try:
            self.update_status("Refreshing session statistics...")
            response = session if session is not None else self._get_cached_or_remote_session()
            if not response:
                self.update_status("Failed to refresh statistics")
                return

            session_metadata = extract_session_metadata(response) or {}

            if drones is None and 'drones' in response:
                drones = response.get('drones')
            if targets is None and 'targets' in response:
                targets = response.get('targets')
            if obstacles is None and 'obstacles' in response:
                obstacles = response.get('obstacles')
            if tasks is None and 'tasks' in response:
                tasks = response.get('tasks')

            session_payload = session_metadata or response
            session_id = session_payload.get('id')
            session_name = session_payload.get('name') or session_id or '-'
            if session_id:
                self.update_session_cache(session_id, session_name if session_name != '-' else None)

            stats = self._build_session_stats(
                session_payload,
                drones=drones,
                targets=targets,
                obstacles=obstacles,
                tasks=tasks,
            )

            self.stats_session_name_var.set(stats.name)
            self.stats_status_var.set(stats.status)
            self.stats_created_var.set(stats.created)
            self.stats_updated_var.set(stats.updated)
            self.stats_task_type_var.set(stats.task_type if stats.task_type else '-')
            self.stats_task_count_var.set(stats.task_count)
            self.stats_task_status_summary_var.set(stats.task_status_summary)

            self.stats_drone_count_var.set(stats.drone_count)
            self.stats_target_count_var.set(stats.target_count)
            self.stats_obstacle_count_var.set(stats.obstacle_count)
            self.stats_commands_executed_var.set(stats.commands_executed)
            self.stats_total_flight_time_var.set(stats.total_flight_time)
            self.stats_total_distance_var.set(stats.total_distance)
            self.stats_task_progress_var.set(stats.task_progress_text)
            self.stats_task_completed_var.set(stats.task_completed_text)
            self.stats_command_history_size_var.set(stats.command_history_size)
            self.stats_target_reach_log_size_var.set(stats.target_reach_log_size)
            self.stats_total_target_reaches_var.set(stats.total_target_reaches)
            self.stats_drones_with_target_reaches_var.set(stats.drones_with_target_reaches)
            self.stats_unique_targets_reached_var.set(stats.unique_targets_reached)
            self.stats_session_time_var.set(stats.session_time)
            self.stats_drones_by_status_var.set(stats.drones_by_status)
            self.stats_drones_avg_speed_var.set(stats.drones_avg_speed)
            self.stats_drones_avg_battery_var.set(stats.drones_avg_battery)
            self.stats_targets_by_type_var.set(stats.targets_by_type)
            self.stats_obstacles_by_type_var.set(stats.obstacles_by_type)

            self.update_status("Session statistics updated")
        except Exception as e:
            self.logger.error(f"Failed to refresh statistics: {e}")
            self.update_status("Failed to refresh statistics")

    def view_current_session_data(self):
        """Open a detail dialog with full session data using /sessions/{id}/data"""
        try:
            # Get current session ID from cache
            session_id = self.get_current_session_id()
            
            data = self.api_server.api_get_session_data(session_id)
            if data:
                self.active_detail_dialog = DetailDialog(self.root, "Session Data", data, self)
        except Exception as e:
            self.logger.error(f"Failed to open session data: {e}")
            messagebox.showerror("Error", f"Failed to load session data: {e}")

    def edit_current_session_visually(self):
        """Open the visual session editor for the current session

        Launches the session editor in a separate process, allowing both
        the GUI controller and session editor to operate simultaneously.
        This approach works reliably on both macOS and Windows.
        """
        try:
            # Get current session ID and name from cache
            session_id = self.get_current_session_id()

            session_name = self.current_session_name or session_id

            # Get complete session data
            session_data = self.api_server.api_get_session_data(session_id)

            if session_data:
                session_metadata = extract_session_metadata(session_data) or {}

                # Try to launch editor in separate process (recommended for cross-platform)
                success = self._launch_editor_separate_process(
                    session_id, session_name, session_metadata
                )

                if not success:
                    # Fallback to in-process mode if separate process fails
                    self.logger.warning("Separate process launch failed, using in-process mode")
                    self._launch_editor_in_process(
                        session_id, session_name, session_metadata
                    )
            else:
                self.update_status("Failed to load session data for editing")

        except Exception as e:
            self.logger.error(f"Error opening session editor: {str(e)}")
            messagebox.showerror("Editor Error", f"Failed to open session editor: {str(e)}")
            self.update_status("Failed to open session editor")

    def _launch_editor_separate_process(self, session_id: str, session_name: str,
                                       session_metadata: dict) -> bool:
        """Launch session editor in a separate process (recommended)

        This allows both windows to operate simultaneously without threading issues.
        Works reliably on both macOS and Windows.

        Returns:
            bool: True if launch succeeded, False otherwise
        """
        try:
            running_frozen = getattr(sys, 'frozen', False)
            main_entry = Path(__file__).parent / 'main.py'

            if not running_frozen and not main_entry.exists():
                self.logger.error(f"Main entry point not found: {main_entry}")
                return False

            # Create temporary config file
            config_data = {
                'session_id': session_id,
                'session_data': session_metadata
            }

            save_signal_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.signal',
                    prefix='session_editor_save_',
                    delete=False
                ) as signal_file:
                    signal_file.write("0")
                    save_signal_path = signal_file.name
            except Exception as signal_exc:
                self.logger.warning(f"Failed to prepare session editor save signal file: {signal_exc}")

            if save_signal_path:
                config_data['save_signal_file'] = save_signal_path

            # Write config to temp file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json',
                delete=False,
                prefix='session_editor_config_'
            ) as f:
                json.dump(config_data, f, indent=2)
                temp_config_path = f.name

            self.logger.info(f"Launching session editor in separate process for '{session_name}'")
            self.logger.debug(f"Config file: {temp_config_path}")

            # Launch subprocess
            # Use CREATE_NO_WINDOW on Windows to avoid console popup
            creation_flags = 0
            if platform.system() == 'Windows':
                creation_flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0

            if running_frozen:
                launch_cmd = [sys.executable, '--launch-session-editor', temp_config_path]
            else:
                launch_cmd = [sys.executable, str(main_entry), '--launch-session-editor', temp_config_path]

            self.logger.debug(f"Session editor launch command: {launch_cmd}")

            process = subprocess.Popen(
                launch_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creation_flags
            )

            # Track this process for cleanup
            self.active_editor_processes.append(process)

            self.logger.info(f"Session editor process started (PID: {process.pid})")
            self.update_status(f"Session editor opened - both windows are now operable")

            if save_signal_path:
                monitor_info = self._start_editor_save_monitor(process.pid, save_signal_path)
                if monitor_info:
                    self.editor_save_monitors[process.pid] = monitor_info
                else:
                    try:
                        Path(save_signal_path).unlink(missing_ok=True)
                    except TypeError:
                        try:
                            if Path(save_signal_path).exists():
                                Path(save_signal_path).unlink()
                        except Exception:
                            pass
            # Schedule a background check to see when editor closes
            def check_editor_closed():
                """Background thread to monitor editor process and refresh when it closes"""
                try:
                    # Wait for process to complete
                    _, stderr = process.communicate()

                    if process.returncode == 0:
                        self.logger.info("Session editor closed normally")
                    else:
                        self.logger.warning(f"Session editor exited with code {process.returncode}")
                        if stderr:
                            self.logger.error(f"Session editor stderr: {stderr.decode('utf-8', errors='ignore')}")

                    # Remove from active processes list
                    try:
                        self.active_editor_processes.remove(process)
                    except ValueError:
                        pass  # Already removed

                    self._stop_editor_save_monitor(process.pid)

                    # Schedule refresh on main thread
                    self.root.after(100, self._on_editor_closed)

                except Exception as e:
                    self.logger.error(f"Error monitoring editor process: {e}")

            # Start monitoring thread
            monitor_thread = threading.Thread(target=check_editor_closed, daemon=True)
            monitor_thread.start()

            return True

        except Exception as e:
            self.logger.error(f"Failed to launch editor in separate process: {e}", exc_info=True)
            # Clean up temp file if it exists
            try:
                if 'temp_config_path' in locals() and Path(temp_config_path).exists():
                    Path(temp_config_path).unlink()
            except:
                pass
            try:
                if 'save_signal_path' in locals() and save_signal_path:
                    Path(save_signal_path).unlink(missing_ok=True)
            except TypeError:
                try:
                    if 'save_signal_path' in locals() and save_signal_path and Path(save_signal_path).exists():
                        Path(save_signal_path).unlink()
                except Exception:
                    pass
            return False

    def _start_editor_save_monitor(self, pid: int, signal_file: str):
        """Start background monitor that watches for session editor save events."""
        try:
            stop_event = threading.Event()
            thread = threading.Thread(
                target=self._monitor_editor_save_signal,
                args=(pid, signal_file, stop_event),
                daemon=True
            )
            thread.start()
            return {
                'stop_event': stop_event,
                'thread': thread,
                'file': signal_file
            }
        except Exception as exc:
            self.logger.warning(f"Failed to start save monitor for editor PID {pid}: {exc}")
            return None

    def _monitor_editor_save_signal(self, pid: int, signal_file: str, stop_event: threading.Event):
        """Watch the signal file for changes and refresh GUI when saves happen."""
        last_contents = None
        initialized = False
        while not stop_event.is_set():
            try:
                with open(signal_file, 'r', encoding='utf-8') as f:
                    contents = f.read().strip()
            except FileNotFoundError:
                break
            except Exception as exc:
                self.logger.debug(f"Save signal monitor read error for PID {pid}: {exc}")
                contents = None

            if contents:
                if not initialized:
                    last_contents = contents
                    initialized = True
                elif contents != last_contents:
                    last_contents = contents
                    self.logger.info(f"Detected save signal from session editor (PID: {pid})")
                    if self._is_gui_available():
                        self.root.after(0, self._on_editor_saved)

            stop_event.wait(1.0)

    def _stop_editor_save_monitor(self, pid: int):
        """Stop and clean up the save signal monitor for the given editor PID."""
        monitor_info = self.editor_save_monitors.pop(pid, None)
        if not monitor_info:
            return

        stop_event = monitor_info.get('stop_event')
        if stop_event:
            stop_event.set()

        thread = monitor_info.get('thread')
        if thread and thread.is_alive():
            thread.join(timeout=2)

        signal_file = monitor_info.get('file')
        if signal_file:
            try:
                Path(signal_file).unlink(missing_ok=True)
            except TypeError:
                try:
                    if Path(signal_file).exists():
                        Path(signal_file).unlink()
                except Exception:
                    pass

    def _stop_all_editor_save_monitors(self):
        """Stop all active save monitors."""
        for pid in list(self.editor_save_monitors.keys()):
            self._stop_editor_save_monitor(pid)

    def _launch_editor_in_process(self, session_id: str, session_name: str,
                                  session_metadata: dict):
        """Launch session editor in-process (fallback mode)

        This is the fallback if separate process launch fails.
        The GUI controller window will be hidden while editor is open.
        """
        try:
            if start_session_editor is None:
                raise ImportError(SESSION_EDITOR_IMPORT_ERROR or "Session editor unavailable")
            # Hide the GUI Controller window
            self.logger.info("Using in-process mode - hiding GUI Controller window")
            self.root.withdraw()

            # Launch the session editor (this blocks until editor closes)
            self.logger.info(f"Launching session editor for '{session_name}'")
            try:
                start_session_editor(
                    session_id=session_id,
                    session_data=session_metadata,
                    on_saved=self._on_editor_saved
                )
                self.logger.info("Session editor returned normally")
            except Exception as editor_error:
                self.logger.error(f"Session editor raised exception: {editor_error}")
                raise

            # Show the GUI Controller window again
            self.logger.info("Showing GUI Controller window again")
            self.root.deiconify()
            self.root.update()
            self.root.lift()
            self.root.focus_force()

            # Refresh GUI data after editor closes
            self._on_editor_closed()

        except ImportError as e:
            self.logger.error(f"Failed to import session editor: {e}")
            # Show window again on error
            self.root.deiconify()
            messagebox.showerror("Import Error",
                               f"Failed to load session editor.\n\n"
                               f"Make sure pygame is installed:\n"
                               f"pip install pygame\n\n"
                               f"Error: {str(e)}")
            self.update_status("Failed to open session editor")

        except Exception as e:
            self.logger.error(f"Error in session editor: {str(e)}", exc_info=True)
            # Show window again on error
            self.root.deiconify()
            messagebox.showerror("Editor Error", f"Error in session editor: {str(e)}")
            self.update_status("Session editor error")

    def _on_editor_saved(self):
        """Callback when session is saved in editor - refresh data immediately"""
        if not self._is_gui_available():
            self.logger.debug("GUI destroyed or closing; skipping editor save refresh")
            return
        self.logger.info("Refreshing GUI data after session saved in editor")
        self.refresh_all_data()
        self.update_status("Session saved - data refreshed")

    def _on_editor_closed(self):
        """Callback when session editor closes - refresh data"""
        if not self._is_gui_available():
            self.logger.debug("GUI destroyed or closing; skipping editor close refresh")
            return
        self.logger.info("Refreshing GUI data after session editor closed")
        self.refresh_all_data()
        self.update_status("Session editor closed - data refreshed")

    # Drone management methods
    def refresh_drones(self, drones=None):
        """Refresh the drone list.

        Optional `drones` lets callers reuse already-fetched data.
        """
        self.logger.info("Refreshing drone list")
        self.update_status("Refreshing drones...")
        drones_data = drones if drones is not None else self.api_server.api_get_drones()
        if drones_data is not None:
            if drones is None:
                self.logger.info(f"Successfully retrieved {len(drones_data)} drones from API")
            else:
                self.logger.debug(f"Using prefetched drone payload with {len(drones_data)} entries")
            self.drone_listbox.delete(0, tk.END)
            for i, drone in enumerate(drones_data):
                status = drone.get('status', 'unknown')
                battery = drone.get('battery_level', 0)
                pos = drone.get('position', {})
                x, y, z = pos.get('x', 0), pos.get('y', 0), pos.get('z', 0)
                display_text = f"{drone['name']} ({drone['id']}) - {status} - Battery: {format_number(battery)}% - Pos: ({format_number(x)}, {format_number(y)}, {format_number(z)})"
                self.drone_listbox.insert(tk.END, display_text)
                self.logger.debug(f"Drone {i+1}: {drone.get('name', 'Unknown')} (ID: {drone.get('id', 'Unknown')}) - Status: {status}, Battery: {battery}%")
            self.update_status(f"Found {len(drones_data)} drones")
            self.logger.info("Drone list refresh completed successfully")
        else:
            self.logger.error("Failed to refresh drone list - API request unsuccessful")
            self.update_status("Failed to refresh drones")

    def update_drone_list_item(self, drone_id: str, drone_data=None):
        """Refresh just one drone's line in the Drones tab listbox.

        Fetches latest data for `drone_id` and updates the existing list item
        if present. This avoids reloading the entire list and keeps UI snappy.

        Args:
            drone_id: ID of the drone to update
            drone_data: Optional pre-fetched drone data to avoid duplicate API call
        """
        try:
            # Use provided data or fetch if not provided
            if drone_data is None:
                drone_data = self.api_server.api_get_drone(drone_id)
            if not drone_data:
                return

            status = drone_data.get('status', 'unknown')
            battery = drone_data.get('battery_level', 0)
            pos = drone_data.get('position', {})
            x, y, z = pos.get('x', 0), pos.get('y', 0), pos.get('z', 0)
            display_text = f"{drone_data.get('name', 'Unknown')} ({drone_id}) - {status} - Battery: {format_number(battery)}% - Pos: ({format_number(x)}, {format_number(y)}, {format_number(z)})"

            # Find existing index by matching '(ID)'
            items = self.drone_listbox.get(0, tk.END)
            target_index = None
            id_marker = f"({drone_id})"
            for idx, text in enumerate(items):
                if id_marker in text:
                    target_index = idx
                    break

            if target_index is not None:
                # Replace the line at the same index
                self.drone_listbox.delete(target_index)
                self.drone_listbox.insert(target_index, display_text)
            else:
                # If not found, append (list may be empty or filtered)
                self.drone_listbox.insert(tk.END, display_text)
        except Exception as e:
            self.logger.debug(f"Non-fatal: could not update drone list item {drone_id}: {e}")
    
    def get_selected_drone_id(self, silent: bool = False) -> Optional[str]:
        """Get the ID of the currently selected drone (first selection)

        Args:
            silent: If True, don't show warning dialog when no selection
        """
        selection = self.drone_listbox.curselection()
        if not selection:
            if not silent:
                messagebox.showwarning("No Selection", "Please select a drone first")
            return None

        drone_text = self.drone_listbox.get(selection[0])
        # Extract drone ID from the display text (format: "Name (ID) - ...")
        try:
            drone_id = drone_text.split('(')[1].split(')')[0]
            return drone_id
        except IndexError:
            if not silent:
                messagebox.showerror("Error", "Could not parse drone ID")
            return None
    
    def get_selected_drone_ids(self) -> list:
        """Get the IDs of all selected drones"""
        selection = self.drone_listbox.curselection()
        if not selection:
            return []
        
        drone_ids = []
        for index in selection:
            drone_text = self.drone_listbox.get(index)
            try:
                drone_id = drone_text.split('(')[1].split(')')[0]
                drone_ids.append(drone_id)
            except IndexError:
                continue
        return drone_ids
    
    def get_drone_current_position(self, drone_id: str) -> tuple:
        """Get current position of a drone"""
        drone_data = self.api_server.api_get_drone(drone_id)
        if drone_data and 'position' in drone_data:
            pos = drone_data['position']
            return (pos.get('x', 0.0), pos.get('y', 0.0), pos.get('z', 0.0))
        return (0.0, 0.0, 0.0)
    
    def add_drone(self):
        """Add a new drone"""
        self.logger.info("User initiated add drone operation")
        self.disable_global_shortcuts()
        dialog = DroneEditDialog(self.root, edit_mode=False)
        self.enable_global_shortcuts()
        if dialog.result:
            self.logger.info(f"User provided drone data: {json.dumps(dialog.result, indent=2)}")
            self.update_status("Adding drone...")

            # Build payload with proper structure
            payload = {
                "name": dialog.result.get("name"),
                "model": dialog.result.get("model"),
                "position": dialog.result.get("position"),
                "heading": dialog.result.get("heading"),
                "battery_level": dialog.result.get("battery_level"),
                "status": dialog.result.get("status"),
                "max_speed": dialog.result.get("max_speed"),
                "max_altitude": dialog.result.get("max_altitude"),
                "battery_capacity": dialog.result.get("battery_capacity"),
                "perceived_radius": dialog.result.get("perceived_radius"),
                "task_radius": dialog.result.get("task_radius")
            }

            result = self.api_server.api_create_drone(payload)
            if result:
                drone_id = result.get('id', 'Unknown')
                self.logger.info(f"Drone successfully added with ID: {drone_id}")
                # Mark session as modified
                self.set_modified()
                messagebox.showinfo("Success", f"Drone added with ID: {drone_id}")
                self.refresh_drones()
            else:
                self.logger.warning("Failed to add drone - API request unsuccessful")
                self.update_status("Failed to add drone")
        else:
            self.logger.info("User cancelled add drone operation")

    def edit_drone(self):
        """Edit selected drone"""
        drone_id = self.get_selected_drone_id()
        if not drone_id:
            return

        self.logger.info(f"User initiated edit drone operation for drone {drone_id}")
        self.update_status(f"Fetching drone {drone_id} data...")

        # Fetch current drone data
        drone_data = self.api_server.api_get_drone(drone_id)
        if not drone_data:
            messagebox.showerror("Error", f"Failed to fetch data for drone {drone_id}")
            return

        # Open edit dialog with current data
        self.disable_global_shortcuts()
        dialog = DroneEditDialog(self.root, edit_mode=True, initial_data=drone_data)
        self.enable_global_shortcuts()
        if dialog.result:
            self.logger.info(f"User updated drone data: {json.dumps(dialog.result, indent=2)}")
            self.update_status(f"Updating drone {drone_id}...")

            # Build payload with proper structure for updated API
            # Only include non-null values to avoid validation errors
            payload = {}

            if dialog.result.get("name") is not None:
                payload["name"] = dialog.result.get("name")
            if dialog.result.get("model") is not None:
                payload["model"] = dialog.result.get("model")
            if dialog.result.get("position") is not None:
                payload["position"] = dialog.result.get("position")
            if dialog.result.get("heading") is not None:
                payload["heading"] = dialog.result.get("heading")
            if dialog.result.get("battery_level") is not None:
                payload["battery_level"] = dialog.result.get("battery_level")
            if dialog.result.get("status") is not None:
                payload["status"] = dialog.result.get("status")
            if dialog.result.get("max_speed") is not None:
                payload["max_speed"] = dialog.result.get("max_speed")
            if dialog.result.get("max_altitude") is not None:
                payload["max_altitude"] = dialog.result.get("max_altitude")
            if dialog.result.get("battery_capacity") is not None:
                payload["battery_capacity"] = dialog.result.get("battery_capacity")
            if dialog.result.get("perceived_radius") is not None:
                payload["perceived_radius"] = dialog.result.get("perceived_radius")
            if dialog.result.get("task_radius") is not None:
                payload["task_radius"] = dialog.result.get("task_radius")

            # Update via API
            result = self.api_server.api_update_drone(drone_id, payload)
            if result:
                self.logger.info(f"Drone {drone_id} successfully updated")
                # Mark session as modified
                self.set_modified()
                messagebox.showinfo("Success", f"Drone {drone_id} updated successfully")
                self.refresh_drones()
            else:
                self.logger.warning(f"Failed to update drone {drone_id}")
                messagebox.showerror("Error", f"Failed to update drone {drone_id}")
        else:
            self.logger.info("User cancelled edit drone operation")

    def drone_takeoff(self):
        """Make selected drone take off"""
        self.logger.info("User initiated drone takeoff operation")
        drone_id = self.get_selected_drone_id()
        if not drone_id:
            self.logger.warning("Takeoff operation cancelled - no drone selected")
            return
        
        self.logger.info(f"Selected drone for takeoff: {drone_id}")
        
        # Create a custom dialog instead of using simpledialog.askfloat
        takeoff_dialog = tk.Toplevel(self.root)
        takeoff_dialog.title("Take Off")
        set_window_geometry_and_center(takeoff_dialog, 300, 150, self.root)
        
        # Create dialog contents
        frame = ttk.Frame(takeoff_dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Enter altitude (meters):").pack(pady=(0, 10))
        
        altitude_var = tk.StringVar(value=format_number(10))
        altitude_entry = ttk.Spinbox(
            frame, 
            from_=1.0, 
            to=400.0, 
            textvariable=altitude_var, 
            width=10,
            increment=1
        )
        altitude_entry.pack(pady=(0, 20))
        
        # Result variable
        result = [None]
        
        def on_ok():
            try:
                value = float(altitude_var.get())
                if 1.0 <= value <= 120.0:
                    result[0] = value
                    takeoff_dialog.destroy()
                else:
                    messagebox.showerror("Invalid Value", "Altitude must be between 1.0 and 120.0 meters")
            except ValueError:
                messagebox.showerror("Invalid Value", "Please enter a valid number")
        
        def on_cancel():
            takeoff_dialog.destroy()
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.RIGHT)
        
        # Set focus to entry and select all text for easy editing
        altitude_entry.focus_set()
        altitude_entry.selection_range(0, 'end')
        
        # Bind Enter key to OK button
        takeoff_dialog.bind('<Return>', lambda event: on_ok())
        
        # Wait for dialog to close
        self.root.wait_window(takeoff_dialog)
        
        # Process result
        if result[0] is not None:
            altitude = result[0]
            command_data = {
                'command': 'take_off',
                'parameters': {'altitude': altitude}
            }
            self.logger.info(f"User specified takeoff altitude: {altitude}m for drone {drone_id}")
            self.update_status(f"Sending take off command to {drone_id}...")
            result = self.api_server.api_send_drone_command(drone_id, command_data)
            if result:
                command_id = result.get('command_id', 'N/A')
                self.logger.info(f"Takeoff command successfully sent to drone {drone_id}, command ID: {command_id}")
                messagebox.showinfo("Success", f"Take off command sent. Command ID: {command_id}")
                self.refresh_drones()
            else:
                self.logger.error(f"Failed to send takeoff command to drone {drone_id}")
                self.update_status("Failed to send take off command")
        else:
            self.logger.info(f"User cancelled takeoff operation for drone {drone_id}")
    
    def drone_land(self):
        """Make selected drone land"""
        drone_id = self.get_selected_drone_id()
        if not drone_id:
            return

        self.update_status(f"Sending land command to {drone_id}...")
        result = self.api_server.api_send_drone_command(drone_id, {
            'command': 'land',
            'parameters': {}
        })
        if result:
            messagebox.showinfo("Success", f"Land command sent. Command ID: {result.get('command_id', 'N/A')}")
            self.refresh_drones()
        else:
            self.update_status("Failed to send land command")

    def land_all_drones(self):
        """Land all drones immediately (SYSTEM+ permission required)"""
        confirm = messagebox.askyesno(
            "Land All Drones",
            "Force all drones to land now?\n\n"
            "This will land every drone in the system immediately."
        )
        if not confirm:
            return

        self.update_status("Sending land-all command...")
        result = self.api_server.api_land_all_drones()
        if result:
            message = result.get("message", "Land-all command completed.")
            messagebox.showinfo("Land All Drones", message)
            self.refresh_drones()
            self.update_status("Land-all command completed")
        else:
            self.update_status("Failed to land all drones")

    def charge_all_drones(self):
        """Fully charge all drones immediately (SYSTEM+ permission required)"""
        confirm = messagebox.askyesno(
            "Charge All Drones",
            "Fully charge all drones now?\n\n"
            "This will set every drone's battery to 100% immediately."
        )
        if not confirm:
            return

        self.update_status("Sending charge-all command...")
        result = self.api_server.api_charge_all_drones()
        if result:
            message = result.get("message", "Charge-all command completed.")
            messagebox.showinfo("Charge All Drones", message)
            self.refresh_drones()
            self.update_status("Charge-all command completed")
        else:
            self.update_status("Failed to charge all drones")

    def _set_send_task_to_agent_running(self, is_running: bool):
        """Update Send Task to Agent state from the Tk main thread."""
        self.is_sending_task_to_agent = is_running
        if not is_running:
            self.stop_agent_send_requested = False
        if hasattr(self, 'send_task_to_agent_button'):
            text = "Stop Agent Running" if is_running else "Send Task to Agent"
            self.send_task_to_agent_button.config(text=text, state=tk.NORMAL)

    def _find_cached_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Return a task from the current task list cache."""
        for task in self.task_data:
            if task.get('id') == task_id:
                return task
        return None

    def send_selected_task_to_agent(self):
        """Send the selected task's original command to the agent service."""
        if self.is_sending_task_to_agent:
            self.stop_agent_send_requested = True
            self.update_status("Stopping agent task monitor...")
            self.logger.info("User requested stop for active agent task monitor")
            return

        task_id = self.get_selected_task_id()
        if not task_id:
            return

        session_id = self.get_current_session_id()
        if not session_id:
            messagebox.showerror("No Session", "Could not determine the current session.")
            return

        task_data = self.api_server.api_get_session_task(session_id, task_id)
        if not task_data:
            task_data = self._find_cached_task(task_id)
        if not task_data:
            messagebox.showwarning("No Task", "Could not find selected task")
            return

        command = extract_original_task_command(task_data)
        if not command:
            messagebox.showinfo("No Content", "This task has no original command to send.")
            return

        task_name = task_data.get('name') or task_data.get('title') or task_id
        self.stop_agent_send_requested = False
        self._set_send_task_to_agent_running(True)
        self.update_status(f"Sending task '{task_name}' to agent...")
        self.logger.info("Sending task '%s' (%s) to agent", task_name, task_id)

        worker = threading.Thread(
            target=self._send_task_to_agent_worker,
            args=(task_id, task_name, command),
            daemon=True,
        )
        worker.start()

    def _send_task_to_agent_worker(self, task_id: str, task_name: str, command: str):
        """Submit a task command to the agent and poll completion in the background."""
        try:
            self.root.after(0, lambda: self.update_status("Checking agent server..."))
            if not self.agent_client.check_health():
                self.root.after(0, lambda: messagebox.showerror(
                    "Agent Server Unavailable",
                    "Cannot connect to agent server. Please ensure it's running on port 18000."
                ))
                self.root.after(0, lambda: self.update_status("Agent server unavailable"))
                return

            self.root.after(0, lambda: self.update_status(f"Agent running task '{task_name}'..."))

            def status_callback(status, elapsed):
                if self.stop_agent_send_requested:
                    self.root.after(
                        0,
                        lambda: self.update_status(f"Stopped waiting for agent task '{task_name}'")
                    )
                    return False
                self.root.after(
                    0,
                    lambda s=status, e=elapsed: self.update_status(
                        f"Agent task '{task_name}': {s} ({e:.1f}s)"
                    )
                )
                return True

            success, result = self.agent_client.submit_and_wait(
                command,
                poll_interval=5.0,
                timeout=300.0,
                status_callback=status_callback,
            )

            if not success or not result:
                if self.stop_agent_send_requested:
                    self.logger.info("Stopped monitoring agent task '%s' (%s)", task_name, task_id)
                    self.root.after(
                        0,
                        lambda: self.update_status(f"Stopped waiting for agent task '{task_name}'")
                    )
                    return
                self.logger.warning("Agent task '%s' (%s) failed or timed out", task_name, task_id)
                self.root.after(
                    0,
                    lambda: self.update_status(f"Agent task '{task_name}' failed or timed out")
                )
                return

            agent_result = result.get('result', {}) if isinstance(result, dict) else {}
            agent_success = agent_result.get('success', True)
            agent_output = agent_result.get('output') or agent_result.get('message') or ''
            if agent_output:
                self.logger.info("Agent output for task '%s' (%s): %s", task_name, task_id, agent_output)

            if agent_success:
                self.root.after(
                    0,
                    lambda: self.update_status(f"Agent completed task '{task_name}'")
                )
            else:
                error = agent_result.get('error') or "Agent reported failure"
                self.logger.warning("Agent reported failure for task '%s' (%s): %s", task_name, task_id, error)
                self.root.after(
                    0,
                    lambda: self.update_status(f"Agent task '{task_name}' failed")
                )
        except Exception as exc:
            self.logger.error("Error sending task '%s' (%s) to agent: %s", task_name, task_id, exc, exc_info=True)
            self.root.after(
                0,
                lambda: self.update_status(f"Error sending task '{task_name}' to agent")
            )
        finally:
            self.root.after(0, lambda: self._set_send_task_to_agent_running(False))

    def toggle_takeoff_land(self):
        """Toggle between take off and land based on current drone state"""
        drone_id = self.get_selected_drone_id()
        if not drone_id:
            return

        # Get current drone data to check status
        drone_data = self.api_server.api_get_drone(drone_id)
        if not drone_data:
            return

        status = drone_data.get('status', 'unknown').lower()

        # If hovering, land; otherwise, take off
        if status == 'hovering':
            self.drone_land()
        else:
            self.drone_takeoff()

    def update_takeoff_land_button(self, drone_data=None):
        """Update the take off/land button text and Move To button state based on selected drone's state

        Args:
            drone_data: Optional drone data to avoid redundant API calls
        """
        selection = self.drone_listbox.curselection()
        if not selection:
            self.takeoff_land_button.config(text="Take Off")
            self.move_to_button.config(state='disabled')
            return

        # Get status directly from the listbox text to avoid API call
        # Format: "Name (ID) - {status} - Battery: ..."
        if drone_data is None:
            try:
                drone_text = self.drone_listbox.get(selection[0])
                # Extract status from display text
                parts = drone_text.split(' - ')
                if len(parts) >= 2:
                    status = parts[1].strip().lower()
                else:
                    status = 'unknown'
            except (IndexError, AttributeError):
                status = 'unknown'
        else:
            status = drone_data.get('status', 'unknown').lower()

        # Update button text and state based on status
        if status == 'hovering':
            self.takeoff_land_button.config(text="Land")
            self.move_to_button.config(state='normal')
        else:
            self.takeoff_land_button.config(text="Take Off")
            self.move_to_button.config(state='disabled')

    def drone_move_to(self):
        """Move selected drone to specified coordinates"""
        drone_id = self.get_selected_drone_id()
        if not drone_id:
            return
        
        # Get current position as default
        current_pos = self.get_drone_current_position(drone_id)
        dialog = MoveToDialog(self.root, current_pos)
        if dialog.result:
            self.update_status(f"Sending move command to {drone_id}...")
            result = self.api_server.api_send_drone_command(drone_id, {
                'command': 'move_to',
                'parameters': dialog.result
            })
            if result:
                messagebox.showinfo("Success", f"Move command sent. Command ID: {result.get('command_id', 'N/A')}")
                self.refresh_drones()
            else:
                self.update_status("Failed to send move command")
    
    def delete_drone(self):
        """Delete selected drone(s)"""
        selected_ids = self.get_selected_drone_ids()
        if not selected_ids:
            messagebox.showwarning("No Selection", "Please select one or more drones to delete")
            return
        
        drone_list = self.format_delete_id_list(selected_ids)
        if self.ask_delete_confirmation("Delete Drones", f"Delete the following drone(s)?\n{drone_list}"):
            deleted_count = 0
            for drone_id in selected_ids:
                self.update_status(f"Deleting drone {drone_id}...")
                result = self.api_server.api_delete_drone(drone_id)
                if result is not None:
                    deleted_count += 1
            
            if deleted_count > 0:
                # Mark session as modified
                self.set_modified()
                messagebox.showinfo("Success", f"Successfully deleted {deleted_count} drone(s)")
                self.refresh_drones()
            else:
                self.update_status("Failed to delete drones")
    
    def open_realtime_control(self):
        """Open real-time control dialog for selected drone"""
        drone_id = self.get_selected_drone_id()
        if not drone_id:
            return
        
        self.logger.info(f"Opening real-time control for drone {drone_id}")
        RealtimeControlDialog(self.root, drone_id, self)
    
    # Target management methods
    def refresh_targets(self, targets=None):
        """Refresh the target list.

        Optional `targets` lets callers reuse prefetched data.
        """
        self.update_status("Refreshing targets...")
        targets_data = targets if targets is not None else self.api_server.api_get_targets()
        if targets_data is not None:
            self.target_listbox.delete(0, tk.END)
            for target in targets_data:
                pos = target.get('position', {})
                x, y, z = pos.get('x', 0), pos.get('y', 0), pos.get('z', 0)
                # API uses canonical `type` in target payloads and responses.
                target_type = target.get('type') or 'unknown'
                runtime_text = format_moving_target_runtime(target)
                if runtime_text:
                    display_text = (
                        f"{target['name']} ({target['id']}) - {target_type} - "
                        f"Pos: ({format_number(x)}, {format_number(y)}, {format_number(z)}) - {runtime_text}"
                    )
                else:
                    display_text = (
                        f"{target['name']} ({target['id']}) - {target_type} - "
                        f"Pos: ({format_number(x)}, {format_number(y)}, {format_number(z)})"
                    )
                self.target_listbox.insert(tk.END, display_text)
            self.update_status(f"Found {len(targets_data)} targets")
        else:
            self.update_status("Failed to refresh targets")
    
    def get_selected_target_id(self) -> Optional[str]:
        """Get the ID of the currently selected target"""
        selection = self.target_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a target first")
            return None
        
        target_text = self.target_listbox.get(selection[0])
        try:
            target_id = target_text.split('(')[1].split(')')[0]
            return target_id
        except IndexError:
            messagebox.showerror("Error", "Could not parse target ID")
            return None

    def get_selected_target_ids(self) -> list:
        """Get the IDs of all selected targets"""
        selection = self.target_listbox.curselection()
        if not selection:
            return []

        target_ids = []
        for index in selection:
            target_text = self.target_listbox.get(index)
            try:
                target_id = target_text.split('(')[1].split(')')[0]
                target_ids.append(target_id)
            except IndexError:
                continue
        return target_ids

    def _build_target_payload(self, target_type: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Convert target dialog result into API payload."""
        payload = {
            "name": result.get("name"),
            "type": target_type,
            "position": {
                "x": result.get("x"),
                "y": result.get("y"),
                "z": result.get("z"),
            },
            "description": result.get("description", ""),
        }

        if target_type in {"waypoint", "fixed", "moving", "circle"}:
            payload["radius"] = result.get("radius")

        if target_type == "moving":
            payload.update(
                normalize_moving_target_state(
                    movement_mode=result.get("movement_mode", "velocity"),
                    moving_duration=float(result.get("moving_duration", 10.0)),
                    velocity=result.get("velocity"),
                    moving_path=result.get("moving_path", []),
                )
            )
        elif target_type == "polygon":
            payload["vertices"] = result.get("vertices", [])

        # Optional charge amount for waypoint targets
        if target_type == "waypoint" and "charge_amount" in result:
            payload["charge_amount"] = result.get("charge_amount")

        return payload

    def _create_target_from_dialog(self, target_type: str, dialog_cls, dialog_kwargs: Optional[Dict[str, Any]] = None):
        """Generic target creation flow to reduce duplication."""
        display_name = target_type.replace("_", " ").title()
        self.logger.info(f"User initiated add {display_name.lower()} target operation")

        dialog_kwargs = dialog_kwargs or {}
        self.disable_global_shortcuts()
        try:
            dialog = dialog_cls(self.root, **dialog_kwargs)
        finally:
            self.enable_global_shortcuts()

        if not getattr(dialog, "result", None):
            self.logger.info(f"User cancelled add {display_name.lower()} target operation")
            return

        self.logger.info(f"User provided {display_name.lower()} target data")
        self.update_status(f"Adding {display_name.lower()} target...")

        payload = self._build_target_payload(target_type, dialog.result)
        result = self.api_server.api_create_target(payload)
        if result:
            target_id = result.get('id', 'Unknown')
            self.logger.info(f"{display_name} target successfully added with ID: {target_id}")
            self.set_modified()
            messagebox.showinfo("Success", f"{display_name} target added with ID: {target_id}")
            self.refresh_targets()
        else:
            self.logger.warning(f"Failed to add {display_name.lower()} target - API request unsuccessful")
            self.update_status(f"Failed to add {display_name.lower()} target")

    def add_moving_target(self):
        """Add a moving target with velocity-based or path-based movement"""
        self._create_target_from_dialog("moving", MovingTargetDialog, {"edit_mode": False})

    def add_fixed_target(self):
        """Add a fixed target"""
        self._create_target_from_dialog("fixed", FixedTargetDialog, {"edit_mode": False})

    def add_waypoint_target(self):
        """Add a fixed target"""
        self._create_target_from_dialog("waypoint", WaypointTargetDialog, {"edit_mode": False})
   
    def add_circle_target(self):
        """Add a circle target per latest API (type=circle)."""
        self._create_target_from_dialog("circle", CircleDialog, {"item_type": "target", "edit_mode": False})

    def add_polygon_target(self):
        """Add a polygon target per latest API (type=polygon)."""
        self._create_target_from_dialog("polygon", PolygonDialog, {"item_type": "target", "edit_mode": False})

    def delete_target(self):
        """Delete selected target(s)"""
        selected_ids = self.get_selected_target_ids()
        if not selected_ids:
            messagebox.showwarning("No Selection", "Please select one or more targets to delete")
            return

        target_list = self.format_delete_id_list(selected_ids)
        if self.ask_delete_confirmation("Delete Targets", f"Delete the following target(s)?\n{target_list}"):
            deleted_count = 0
            for target_id in selected_ids:
                self.update_status(f"Deleting target {target_id}...")
                result = self.api_server.api_delete_target(target_id)
                if result is not None:
                    deleted_count += 1

            if deleted_count > 0:
                # Mark session as modified
                self.set_modified()
                messagebox.showinfo("Success", f"Successfully deleted {deleted_count} target(s)")
                self.refresh_targets()
            else:
                self.update_status("Failed to delete targets")

    def edit_target(self):
        """Edit selected target"""
        target_id = self.get_selected_target_id()
        if not target_id:
            return

        self.logger.info(f"User initiated edit target operation for target {target_id}")
        self.update_status(f"Fetching target {target_id} data...")

        # Fetch current target data
        target_data = self.api_server.api_get_target(target_id)
        if not target_data:
            messagebox.showerror("Error", f"Failed to fetch data for target {target_id}")
            return

        target_type = target_data.get('type', 'fixed')

        # Choose appropriate dialog based on target type
        self.disable_global_shortcuts()
        dialog = None
        if target_type == 'polygon':
            # Use shared polygon dialog
            dialog = PolygonDialog(self.root, item_type="target", edit_mode=True, initial_data=target_data)
        elif target_type == 'circle':
            # Use shared circle dialog
            dialog = CircleDialog(self.root, item_type="target", edit_mode=True, initial_data=target_data)
        elif target_type == 'fixed':
            # Use fixed target dialog
            dialog = FixedTargetDialog(self.root, edit_mode=True, initial_data=target_data)
        elif target_type == 'moving':
            # Use moving target dialog
            dialog = MovingTargetDialog(self.root, edit_mode=True, initial_data=target_data)
        elif target_type == 'waypoint':
            # Use waypoint target dialog
            dialog = WaypointTargetDialog(self.root, edit_mode=True, initial_data=target_data)
        else:
            self.enable_global_shortcuts()
            messagebox.showerror("Error", f"Unknown target type: {target_type}")
            return
        self.enable_global_shortcuts()

        if dialog and dialog.result:
            self.logger.info(f"User updated target data")
            self.update_status(f"Updating target {target_id}...")

            payload = self._build_target_payload(target_type, dialog.result)
            if target_type == 'moving':
                moving_duration = dialog.result.get("moving_duration")
                if moving_duration is not None:
                    payload["moving_duration"] = moving_duration

            # Update via API
            result = self.api_server.api_update_target(target_id, payload)
            if result:
                self.logger.info(f"Target {target_id} successfully updated")
                # Mark session as modified
                self.set_modified()
                messagebox.showinfo("Success", f"Target {target_id} updated successfully")
                self.refresh_targets()
            else:
                self.logger.warning(f"Failed to update target {target_id}")
                messagebox.showerror("Error", f"Failed to update target {target_id}")
        else:
            self.logger.info("User cancelled edit target operation")

    # Environment management methods
    def refresh_environments(self, environments=None):
        """Refresh the environment list.

        Optional `environments` lets callers reuse prefetched data.
        """
        self.update_status("Refreshing environments...")
        environments_data = environments if environments is not None else self.api_server.api_get_environments()
        if environments_data is not None:
            self.env_listbox.delete(0, tk.END)
            for env in environments_data:
                # API responses use 'weather'; accept legacy 'weather_condition' as fallback
                weather = env.get('weather') or env.get('weather_condition') or 'unknown'
                temp = env.get('temperature', 0.0)
                wind = env.get('wind_speed', 0.0)
                # Format numeric values without unnecessary decimals
                display_text = f"{env['name']} ({env['id']}) - {weather} - {format_number(temp)}°C - Wind: {format_number(wind)}"
                self.env_listbox.insert(tk.END, display_text)
            self.update_status(f"Found {len(environments_data)} environments")
        else:
            self.update_status("Failed to refresh environments")
    
    def get_selected_environment_id(self) -> Optional[str]:
        """Get the ID of the currently selected environment"""
        selection = self.env_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an environment first")
            return None
        
        env_text = self.env_listbox.get(selection[0])
        try:
            env_id = env_text.split('(')[1].split(')')[0]
            return env_id
        except IndexError:
            messagebox.showerror("Error", "Could not parse environment ID")
            return None
    
    def create_environment(self):
        """Create a new environment"""
        self.disable_global_shortcuts()
        dialog = EnvironmentDialog(self.root)
        self.enable_global_shortcuts()
        if dialog.result:
            self.update_status("Creating environment...")
            result = self.api_server.api_create_environment(dialog.result)
            if result:
                messagebox.showinfo("Success", f"Environment created with ID: {result['id']}")
                self.refresh_environments()
            else:
                self.update_status("Failed to create environment")
    
    def set_current_environment(self):
        """Set selected environment as current"""
        env_id = self.get_selected_environment_id()
        if not env_id:
            return
        
        self.update_status(f"Setting environment {env_id} as current...")
        result = self.api_server.api_set_environment_current(env_id)
        if result:
            messagebox.showinfo("Success", f"Environment {env_id} set as current")
            self.refresh_environments()
        else:
            self.update_status("Failed to set current environment")
    
    def delete_environment(self):
        """Delete selected environment"""
        env_id = self.get_selected_environment_id()
        if not env_id:
            return

        if self.ask_delete_confirmation("Delete Environment", f"Delete environment {env_id}?"):
            self.update_status(f"Deleting environment {env_id}...")
            result = self.api_server.api_delete_environment(env_id)
            if result is not None:
                messagebox.showinfo("Success", "Environment deleted successfully")
                self.refresh_environments()
            else:
                self.update_status("Failed to delete environment")

    def edit_environment(self):
        """Edit selected environment"""
        env_id = self.get_selected_environment_id()
        if not env_id:
            return

        self.logger.info(f"User initiated edit environment operation for environment {env_id}")
        self.update_status(f"Fetching environment {env_id} data...")

        # Fetch current environment data
        env_data = self.api_server.api_get_environment(env_id)
        if not env_data:
            messagebox.showerror("Error", f"Failed to fetch data for environment {env_id}")
            return

        # Open edit dialog with current data
        self.disable_global_shortcuts()
        dialog = EnvironmentDialog(self.root, edit_mode=True, initial_data=env_data)
        self.enable_global_shortcuts()
        if dialog.result:
            self.logger.info(f"User updated environment data: {json.dumps(dialog.result, indent=2)}")
            self.update_status(f"Updating environment {env_id}...")

            # Update via API
            result = self.api_server.api_update_environment(env_id, dialog.result)
            if result:
                self.logger.info(f"Environment {env_id} successfully updated")
                messagebox.showinfo("Success", f"Environment {env_id} updated successfully")
                self.refresh_environments()
            else:
                self.logger.warning(f"Failed to update environment {env_id}")
                messagebox.showerror("Error", f"Failed to update environment {env_id}")
        else:
            self.logger.info("User cancelled edit environment operation")

    # Task management methods
    def refresh_tasks(self, tasks=None):
        """Refresh the task list.

        Optional `tasks` lets callers reuse prefetched data.
        """
        self.update_status("Refreshing tasks...")
        tasks_data = tasks if tasks is not None else self.api_server.api_get_current_session_tasks()

        if tasks_data is not None:
            self.task_listbox.delete(0, tk.END)
            # Store task data for later retrieval
            self.task_data = tasks_data if isinstance(tasks_data, list) else []

            # Initialize task_check_results if not exists
            if not hasattr(self, 'task_check_results'):
                self.task_check_results = {}

            for idx, task in enumerate(self.task_data):
                task_id = task['id']
                is_done = task.get('is_done', False)

                # Determine status indicator based on check results or done status
                if task_id in self.task_check_results:
                    check_data = self.task_check_results[task_id]
                    # Handle both old (string) and new (dict) formats
                    check_result = check_data if isinstance(check_data, str) else check_data.get('status')
                    
                    if check_result == 'passed':
                        status_indicator = "✓"
                    elif check_result == 'failed':
                        status_indicator = "✗"
                    else:
                        status_indicator = "✓" if is_done else "○"
                else:
                    status_indicator = "✓" if is_done else "○"

                title = task.get('title', task.get('name', 'Untitled'))

                # Add content preview
                content = task.get('content', '')
                if content:
                    # Truncate content to first 50 characters and remove newlines
                    content_preview = content.replace('\n', ' ').replace('\r', ' ')
                    if len(content_preview) > 50:
                        content_preview = content_preview[:50] + "..."
                    display_text = f"{status_indicator} {title} ({task_id}) - {content_preview}"
                else:
                    display_text = f"{status_indicator} {title} ({task_id})"

                self.task_listbox.insert(tk.END, display_text)

                # Apply color-coding based on check results
                if task_id in self.task_check_results:
                    check_data = self.task_check_results[task_id]
                    # Handle both old (string) and new (dict) formats
                    check_result = check_data if isinstance(check_data, str) else check_data.get('status')
                    
                    if check_result == 'passed':
                        # Green for passed checks
                        self.task_listbox.itemconfig(idx, foreground='green')
                    elif check_result == 'failed':
                        # Brown for failed checks
                        self.task_listbox.itemconfig(idx, foreground='#8B4513')  # SaddleBrown

            self.update_status(f"Found {len(self.task_data)} tasks")
            task_count_text, task_status_summary = self._summarize_tasks(self.task_data)
            self.stats_task_count_var.set(task_count_text)
            self.stats_task_status_summary_var.set(task_status_summary)

            # Update toggle button text based on current selection
            self.on_task_selection_changed()
        else:
            self.update_status("Failed to refresh tasks")

    def get_selected_task_id(self) -> Optional[str]:
        """Get the ID of the currently selected task"""
        selection = self.task_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a task first")
            return None

        # Use index to get task from stored data (more reliable than parsing)
        index = selection[0]
        if 0 <= index < len(self.task_data):
            return self.task_data[index]['id']
        else:
            messagebox.showerror("Error", "Could not retrieve task ID")
            return None

    def get_selected_task_ids(self) -> list:
        """Get the IDs of all selected tasks"""
        selection = self.task_listbox.curselection()
        if not selection:
            return []

        task_ids = []
        for index in selection:
            if 0 <= index < len(self.task_data):
                task_ids.append(self.task_data[index]['id'])
        return task_ids

    def get_selected_task_index(self) -> Optional[int]:
        """Get the index of the currently selected task"""
        selection = self.task_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a task first")
            return None
        return selection[0]

    def create_task_from_template(self):
        """Create a new task from a template"""
        # Get available drones from current session
        session_id = self.get_current_session_id()

        # Fetch current session data to get entities
        session_response = self.api_server.api_get_current_session_with_data()
        available_drones = []
        available_targets = []
        available_obstacles = []
        existing_task_names = []
        if session_response:
            available_drones = session_response.get('drones', []) or []
            available_targets = session_response.get('targets', []) or []
            available_obstacles = session_response.get('obstacles', []) or []
            if 'tasks' in session_response:
                existing_task_names = [t.get('name', '') for t in session_response['tasks']]
        current_task_type = (session_response or {}).get('task_type')


        # Open template browser
        self.disable_global_shortcuts()
        template_dialog = TemplateBrowserDialog(
            self.root,
            self.template_manager,
            available_drones,
            available_targets,
            available_obstacles,
            username=self.username,
            existing_task_names=existing_task_names,
            current_task_type=current_task_type
        )
        self.enable_global_shortcuts()

        if template_dialog.result:
            if template_dialog.result == 'CREATE_NEW':
                # User chose to create from scratch instead
                self.create_task()
                return

            # Check if it's batch task generation
            if isinstance(template_dialog.result, dict) and template_dialog.result.get('type') == 'batch':
                # Batch task creation - need to instantiate each task from parameters
                task_params_list = template_dialog.result['tasks']
                self.update_status(f"Creating {len(task_params_list)} tasks from template...")

                # Get template_id from the template dialog (we need to extract it)
                # Since we're in batch mode, we need to instantiate each set of parameters
                success_count = 0
                failed_count = 0

                for i, params in enumerate(task_params_list, 1):
                    self.update_status(f"Creating task {i}/{len(task_params_list)}...")

                    result = self.api_server.api_create_task(session_id, params)
                    if result:
                        success_count += 1
                    else:
                        failed_count += 1

                # Mark session as modified if any succeeded
                if success_count > 0:
                    self.set_modified()

                # Show summary
                if failed_count == 0:
                    messagebox.showinfo("Success",
                                       f"All {success_count} tasks created successfully!")
                else:
                    messagebox.showwarning("Partial Success",
                                          f"{success_count} tasks created successfully\n"
                                          f"{failed_count} tasks failed")

                self.refresh_tasks()
                self.update_status(f"Batch task creation complete: {success_count} succeeded, {failed_count} failed")

            else:
                # Single template was instantiated with parameters
                task_data = template_dialog.result

                # Create the task via API
                self.update_status("Creating task from template...")
                result = self.api_server.api_create_task(session_id, task_data)
                if result:
                    # Mark session as modified
                    self.set_modified()
                    messagebox.showinfo("Success", f"Task created from template with ID: {result['id']}")
                    self.refresh_tasks()
                else:
                    self.update_status("Failed to create task from template")

    def random_generate_tasks(self):
        """Generate random tasks from compatible templates for the current session."""
        session_id = self.get_current_session_id()
        if not session_id:
            messagebox.showwarning("No Session", "No current session is available.")
            return

        task_count = self._prompt_random_task_count()
        if not task_count:
            return

        self.update_status(f"Generating {task_count} random task(s)...")
        session_data = self.api_server.api_get_session_data(session_id, show_error=False) or {}
        if not session_data:
            messagebox.showwarning("No Session Data", "Could not load current session data.")
            self.update_status("Failed to generate random tasks")
            return

        session_name = session_data.get('name') or self.current_session_name or session_id
        session_task_type = session_data.get('task_type') or 'others'
        result = auto_create_tasks_for_session(
            api_server=self.api_server,
            template_manager=self.template_manager,
            session_id=session_id,
            session_data=session_data,
            session_name=session_name,
            session_task_type=session_task_type,
            task_count=task_count,
            username=self.username,
            logger=self.logger,
        )

        if result.created_count > 0:
            self.set_modified()
            self.refresh_tasks()

        if result.reason == 'no_suitable_templates':
            messagebox.showwarning(
                "No Suitable Templates",
                f"No task templates are suitable for session task type '{session_task_type}'."
            )
            self.update_status("Random task generation skipped: no suitable templates")
        elif result.reason == 'no_compatible_templates':
            messagebox.showwarning(
                "No Compatible Templates",
                "Suitable templates were found, but none can be filled with the current "
                "session drones, targets, and obstacles."
            )
            self.update_status("Random task generation skipped: no compatible templates")
        elif result.created_count == task_count:
            messagebox.showinfo("Success", f"Generated {result.created_count} random task(s).")
            self.update_status(f"Generated {result.created_count} random task(s)")
        elif result.created_count > 0:
            messagebox.showwarning(
                "Partial Success",
                f"Generated {result.created_count}/{task_count} random task(s)."
            )
            self.update_status(f"Random task generation partial: {result.created_count}/{task_count}")
        else:
            messagebox.showerror("Error", "Failed to generate random tasks.")
            self.update_status("Failed to generate random tasks")

    def _prompt_random_task_count(self) -> Optional[int]:
        result = {'value': None}
        dialog = tk.Toplevel(self.root)
        if self._icon_image is not None:
            dialog.iconphoto(False, self._icon_image)
            setattr(dialog, "_uav_icon_image", self._icon_image)
        dialog.title("Random Task Generation")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        set_window_geometry_and_center(dialog, 330, 130, self.root)

        frame = ttk.Frame(dialog, padding="16")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Number of tasks to generate:").grid(row=0, column=0, columnspan=2, pady=(0, 2))

        count_var = tk.IntVar(value=3)
        spinbox = ttk.Spinbox(frame, from_=1, to=100, textvariable=count_var, width=8, justify='center')
        spinbox.grid(row=1, column=0, columnspan=2, pady=(10, 0))

        def submit():
            try:
                value = int(count_var.get())
            except (TypeError, ValueError):
                messagebox.showerror("Error", "Please enter a valid task count.", parent=dialog)
                return
            if value < 1 or value > 100:
                messagebox.showerror("Error", "Task count must be between 1 and 100.", parent=dialog)
                return
            result['value'] = value
            dialog.destroy()

        def cancel():
            dialog.destroy()

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(14, 0), sticky=tk.E)
        ttk.Button(button_frame, text="OK", command=submit, width=10).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(button_frame, text="Cancel", command=cancel, width=10).pack(side=tk.LEFT)

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        dialog.bind("<Return>", lambda event: submit())
        dialog.bind("<Escape>", lambda event: cancel())
        spinbox.focus_set()
        spinbox.selection_range(0, tk.END)
        self.root.wait_window(dialog)
        return result['value']

    def create_task(self):
        """Create a new task"""
        self.disable_global_shortcuts()
        dialog = TaskDialog(self.root, username=self.username, task_count=len(self.task_data))
        self.enable_global_shortcuts()
        if dialog.result:
            self.update_status("Creating task...")
            # Get current session ID from cache
            session_id = self.get_current_session_id()

            result = self.api_server.api_create_task(session_id, dialog.result)
            if result:
                self.set_modified()
                messagebox.showinfo("Success", f"Task created with ID: {result['id']}")
                self.refresh_tasks()
            else:
                self.update_status("Failed to create task")

    def edit_task(self):
        """Edit selected task"""
        task_id = self.get_selected_task_id()
        if not task_id:
            return

        self.logger.info(f"User initiated edit task operation for task {task_id}")
        self.update_status(f"Fetching task {task_id} data...")

        # Get current session ID from cache
        session_id = self.get_current_session_id()

        task_data = self.api_server.api_get_session_task(session_id, task_id)
        if not task_data:
            messagebox.showerror("Error", f"Failed to fetch data for task {task_id}")
            return

        # Open edit dialog with current data
        self.disable_global_shortcuts()
        dialog = TaskDialog(self.root, edit_mode=True, initial_data=task_data, username=self.username, task_count=len(self.task_data))
        self.enable_global_shortcuts()
        if dialog.result:
            self.logger.info(f"User updated task data: {json.dumps(dialog.result, indent=2)}")
            self.update_status(f"Updating task {task_id}...")

            # Update via API
            result = self.api_server.api_update_task(session_id, task_id, dialog.result)
            if result:
                self.logger.info(f"Task {task_id} successfully updated")
                # Mark session as modified
                self.set_modified()
                messagebox.showinfo("Success", f"Task {task_id} updated successfully")
                self.refresh_tasks()
            else:
                self.logger.warning(f"Failed to update task {task_id}")
                messagebox.showerror("Error", f"Failed to update task {task_id}")
        else:
            self.logger.info("User cancelled edit task operation")

    def delete_task(self):
        """Delete selected task(s)"""
        selected_ids = self.get_selected_task_ids()
        if not selected_ids:
            messagebox.showwarning("No Selection", "Please select one or more tasks to delete")
            return

        task_list = self.format_delete_id_list(selected_ids)
        if self.ask_delete_confirmation("Delete Tasks", f"Delete the following task(s)?\n{task_list}"):
            # Get current session ID from cache
            session_id = self.get_current_session_id()

            deleted_count = 0
            for task_id in selected_ids:
                self.update_status(f"Deleting task {task_id}...")
                result = self.api_server.api_delete_task(session_id, task_id)
                if result is not None:
                    deleted_count += 1

            if deleted_count > 0:
                # Mark session as modified
                self.set_modified()
                messagebox.showinfo("Success", f"Successfully deleted {deleted_count} task(s)")
                self.refresh_tasks()
            else:
                self.update_status("Failed to delete tasks")

    def duplicate_task(self):
        """Duplicate selected task"""
        task_id = self.get_selected_task_id()
        if not task_id:
            return

        self.logger.info(f"User initiated duplicate task operation for task {task_id}")
        self.update_status(f"Fetching task {task_id} data...")

        # Get current session ID from cache
        session_id = self.get_current_session_id()
        task_data = self.api_server.api_get_session_task(session_id, task_id)

        # Create a copy of the task data for duplication
        # Remove fields that shouldn't be duplicated (id, timestamps, etc.)
        duplicate_data = copy.deepcopy(task_data)
        fields_to_remove = ['id', 'created_at', 'updated_at', 'session_id']
        for field in fields_to_remove:
            duplicate_data.pop(field, None)

        # Update name to indicate it's a copy
        if 'name' in duplicate_data:
            duplicate_data['name'] = f"{duplicate_data['name']} (copy)"

        # Reset the task status to pending (not done)
        duplicate_data['is_done'] = False

        self.logger.info(f"Creating duplicate task with data: {json.dumps(duplicate_data, indent=2)}")
        self.update_status("Creating duplicate task...")

        # Create the duplicate task via API
        result = self.api_server.api_create_task(session_id, duplicate_data)
        if result:
            self.logger.info(f"Duplicate task created successfully with ID: {result.get('id')}")
            # Mark session as modified
            self.set_modified()
            messagebox.showinfo("Success", f"Task duplicated successfully with ID: {result.get('id')}")
            self.refresh_tasks()
        else:
            self.logger.warning(f"Failed to duplicate task {task_id}")
            messagebox.showerror("Error", f"Failed to duplicate task {task_id}")

    def on_task_selection_changed(self, event=None):
        """Update toggle button text when task selection changes"""
        # Get selection without showing error dialog
        selection = self.task_listbox.curselection()
        if not selection:
            # No selection - default to "Done"
            self.task_toggle_button.config(text="Done")
            return

        # Extract task ID from selected text
        task_text = self.task_listbox.get(selection[0])
        try:
            # Extract ID from the format: "status title (task-id)"
            task_id = task_text.split('(')[1].split(')')[0]
        except IndexError:
            self.task_toggle_button.config(text="Done")
            return

        # Find the selected task
        task = None
        for t in self.task_data:
            if t.get('id') == task_id:
                task = t
                break

        if task:
            is_done = task.get('is_done', False)
            # Update button text based on current status
            if is_done:
                self.task_toggle_button.config(text="Undone")
            else:
                self.task_toggle_button.config(text="Done")
        else:
            self.task_toggle_button.config(text="Done")

    def toggle_task_status(self):
        """Toggle selected task between done and undone"""
        task_id = self.get_selected_task_id()
        if not task_id:
            return

        # Find the task to check current status
        task = None
        for t in self.task_data:
            if t.get('id') == task_id:
                task = t
                break

        if not task:
            messagebox.showwarning("No Task", "Could not find selected task")
            return

        is_done = task.get('is_done', False)

        # Get current session ID from cache
        session_id = self.get_current_session_id()

        # Toggle the status
        if is_done:
            # Mark as undone (pending)
            self.update_status(f"Marking task as undone...")
            result = self.api_server.api_mark_task_pending(session_id, task_id)
            if result:
                # Mark session as modified
                self.set_modified()
                # Remove check result for this task to reset color
                if hasattr(self, 'task_check_results') and task_id in self.task_check_results:
                    del self.task_check_results[task_id]
                self.update_status(f"Task marked as undone")
                self.refresh_tasks()
            else:
                self.update_status("Failed to mark task as undone")
        else:
            # Mark as done
            self.update_status(f"Marking task as done...")
            result = self.api_server.api_mark_task_done(session_id, task_id)
            if result:
                # Mark session as modified
                self.set_modified()
                self.update_status(f"Task marked as done")
                self.refresh_tasks()
            else:
                self.update_status("Failed to mark task as done")


    def move_task_up(self):
        """Move selected task up in the list"""
        index = self.get_selected_task_index()
        if index is None or index == 0:
            return

        # Get current session ID from cache
        session_id = self.get_current_session_id()

        # Get task IDs for swapping
        task_id_1 = self.task_data[index]['id']
        task_id_2 = self.task_data[index - 1]['id']

        # Call swap API
        swap_data = {
            "task_id_1": task_id_1,
            "task_id_2": task_id_2
        }

        result = self.api_server.api_swap_tasks(session_id, swap_data)
        if result:
            # Mark session as modified
            self.set_modified()

            # Refresh tasks with the new order from server
            self.refresh_tasks(result)

            # Reselect the moved item at new position
            self.task_listbox.selection_set(index - 1)

            self.update_status("Task moved up")
        else:
            messagebox.showerror("Error", "Failed to swap tasks")
            self.update_status("Failed to move task up")

    def move_task_down(self):
        """Move selected task down in the list"""
        index = self.get_selected_task_index()
        if index is None or index >= len(self.task_data) - 1:
            return

        # Get current session ID from cache
        session_id = self.get_current_session_id()

        # Get task IDs for swapping
        task_id_1 = self.task_data[index]['id']
        task_id_2 = self.task_data[index + 1]['id']

        # Call swap API
        swap_data = {
            "task_id_1": task_id_1,
            "task_id_2": task_id_2
        }

        result = self.api_server.api_swap_tasks(session_id, swap_data)
        if result:
            # Mark session as modified
            self.set_modified()

            # Refresh tasks with the new order from server
            self.refresh_tasks(result)

            # Reselect the moved item at new position
            self.task_listbox.selection_set(index + 1)

            self.update_status("Task moved down")
        else:
            messagebox.showerror("Error", "Failed to swap tasks")
            self.update_status("Failed to move task down")

    def check_task_completion(self):
        """Check if the selected task is completed by evaluating execution_check_apis"""
        task_id = self.get_selected_task_id()
        if not task_id:
            return

        # Get current session ID
        session_id = self.get_current_session_id()

        # Fetch full task data including execution_check_apis
        task_data = self.api_server.api_get_session_task(session_id, task_id)
        if not task_data:
            messagebox.showerror("Error", "Failed to retrieve task data")
            return

        task_name = task_data.get('name', 'Unnamed Task')
        execution_check_apis = task_data.get('execution_check_apis')

        # Check if execution_check_apis exists
        if not execution_check_apis or not isinstance(execution_check_apis, dict):
            messagebox.showinfo(
                "No Checks Defined",
                f"Task '{task_name}' has no execution check APIs defined.\n\n"
                "To define completion checks, edit the task and add execution check APIs."
            )
            return

        self.update_status(f"Checking task '{task_name}'...")
        self.logger.info(f"User initiated check for task '{task_name}' (ID: {task_id})")

        # Evaluate the execution check tree
        try:
            result, details = self._evaluate_execution_check_node(execution_check_apis, session_id)

            # Display results in a dialog
            self._show_check_results_dialog(task_name, result, details)

            # Prepare result record
            check_record = {
                'status': 'passed' if result else 'failed',
                'details': details,
                'timestamp': datetime.now().isoformat()
            }

            if not hasattr(self, 'task_check_results'):
                self.task_check_results = {}
            
            self.task_check_results[task_id] = check_record

            self.logger.info(f"Task '{task_name}' check completed. Result: {'Passed' if result else 'Failed'}")

            # Auto-mark task as done regardless of check result
            mark_result = self.api_server.api_mark_task_done(session_id, task_id)
            if mark_result:
                self.set_modified()
                # Refresh tasks to update display
                self.refresh_tasks()
                status_suffix = "Marked as done"
            else:
                # Refresh tasks to update display even if marking failed
                self.refresh_tasks()
                status_suffix = "Failed to mark as done"

            if result:
                self.update_status(f"Task '{task_name}' check: PASSED ✓ - {status_suffix}")
            else:
                self.update_status(f"Task '{task_name}' check: FAILED ✗ - {status_suffix}")

        except Exception as e:
            self.logger.error(f"Error evaluating task checks: {e}", exc_info=True)
            messagebox.showerror(
                "Check Error",
                f"An error occurred while checking task completion:\n\n{str(e)}"
            )
            self.update_status(f"Error checking task '{task_name}'")

    def _evaluate_execution_check_node(self, node, session_id, depth=0):
        """
        Recursively evaluate an execution check node (group or leaf).

        Returns:
            tuple: (result: bool, details: list of dict)
                - result: True if check passes, False otherwise
                - details: List of check details for display
        """
        if not isinstance(node, dict):
            return False, [{"error": "Invalid node structure", "depth": depth}]

        # Check if this is a group node (has 'checks' array)
        if 'checks' in node:
            logic = node.get('logic', 'and').lower()
            checks = node.get('checks') or []

            details = []
            results = []

            # Add group header to details
            details.append({
                "type": "group",
                "logic": logic.upper(),
                "depth": depth,
                "count": len(checks)
            })

            # Evaluate each child check
            for check in checks:
                child_result, child_details = self._evaluate_execution_check_node(check, session_id, depth + 1)
                results.append(child_result)
                details.extend(child_details)

            # Apply logical operator
            if logic == 'and':
                final_result = all(results) if results else True
            elif logic == 'or':
                final_result = any(results) if results else False
            elif logic == 'not':
                final_result = not all(results) if results else True
            else:
                final_result = False
                details.append({
                    "type": "error",
                    "message": f"Unknown logic operator: {logic}",
                    "depth": depth
                })

            return final_result, details

        # This is a leaf node - make API call
        endpoint = node.get('endpoint') or node.get('path', '')
        parameters = node.get('parameters', {})
        expect = node.get('expect', True)  # Default expectation is True

        # Ensure expect is boolean
        if isinstance(expect, dict) and 'result' in expect:
            expect = bool(expect.get('result'))
        elif not isinstance(expect, bool):
            expect = True

        # Make the check API call
        try:
            # Add session_id to parameters if not already present
            params_with_session = dict(parameters)
            if 'session_id' not in params_with_session and session_id:
                params_with_session['session_id'] = session_id

            # Make GET request to check endpoint using the api_check_execution wrapper
            response = self.api_server.api_check_execution(endpoint, params_with_session, show_error=False)

            if response is None:
                # API call failed
                return False, [{
                    "type": "leaf",
                    "endpoint": endpoint,
                    "parameters": parameters,
                    "expect": expect,
                    "actual": None,
                    "result": False,
                    "error": "API call failed or returned None",
                    "depth": depth
                }]

            # Extract the 'result' field from response
            actual_result = response.get('result', False) if isinstance(response, dict) else False

            # Compare with expected value
            check_passed = (actual_result == expect)

            return check_passed, [{
                "type": "leaf",
                "endpoint": endpoint,
                "parameters": parameters,
                "expect": expect,
                "actual": actual_result,
                "result": check_passed,
                "response": response,
                "depth": depth
            }]

        except Exception as e:
            self.logger.error(f"Error calling check endpoint {endpoint}: {e}")
            return False, [{
                "type": "leaf",
                "endpoint": endpoint,
                "parameters": parameters,
                "expect": expect,
                "actual": None,
                "result": False,
                "error": str(e),
                "depth": depth
            }]

    def _show_check_results_dialog(self, task_name, overall_result, details):
        """Display check results in a dialog with hierarchical structure"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Task Check Results: {task_name}")
        set_window_geometry_and_center(dialog, 700, 600, self.root)

        # Calculate statistics
        leaf_details = [d for d in details if d.get('type') == 'leaf']
        total_checks = len(leaf_details)
        passed_checks = sum(1 for d in leaf_details if d.get('result', False))
        failed_checks = total_checks - passed_checks
        pass_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0.0

        # Overall result frame
        result_frame = ttk.Frame(dialog, padding="10")
        result_frame.pack(fill=tk.X)

        if overall_result:
            result_text = f"✓ Task Completed - All {total_checks} checks passed"
            result_color = "green"
        else:
            result_text = f"✗ Task Not Completed - {failed_checks} checks failed"
            result_color = "red"

        result_label = ttk.Label(
            result_frame,
            text=result_text,
            font=('Arial', 16, 'bold'),
            foreground=result_color
        )
        result_label.pack()

        # Statistics Label
        stats_text = f"Total Checks: {total_checks} | Passed: {passed_checks} | Pass Rate: {pass_rate:.1f}%"
        stats_label = ttk.Label(
            result_frame,
            text=stats_text,
            font=('Arial', 12),
            padding=(0, 5, 0, 0)
        )
        stats_label.pack()

        # Details frame with scrollbar
        details_frame = ttk.LabelFrame(dialog, text="Check Details", padding="10")
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Create text widget with scrollbar
        text_frame = ttk.Frame(details_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        details_text = tk.Text(text_frame, wrap=tk.WORD, height=20, width=80, font=('Arial', 12))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=details_text.yview)
        details_text.configure(yscrollcommand=scrollbar.set)

        details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Format and insert details
        for detail in details:
            indent = "  " * detail.get('depth', 0)

            if detail.get('type') == 'group':
                logic = detail.get('logic', 'AND')
                count = detail.get('count', 0)
                details_text.insert(tk.END, f"{indent}[{logic} Group - {count} checks]\n", 'group')

            elif detail.get('type') == 'leaf':
                endpoint = detail.get('endpoint', '')
                parameters = detail.get('parameters', {})
                expect = detail.get('expect', True)
                actual = detail.get('actual', None)
                result = detail.get('result', False)
                error = detail.get('error')

                status_icon = "✓" if result else "✗"
                status_tag = 'pass' if result else 'fail'

                details_text.insert(tk.END, f"{indent}{status_icon} ", status_tag)
                details_text.insert(tk.END, f"{endpoint}\n")

                # Show parameters if any
                if parameters:
                    params_str = ", ".join([f"{k}={v}" for k, v in parameters.items()])
                    details_text.insert(tk.END, f"{indent}   Parameters: {params_str}\n", 'params')

                # Show expected vs actual
                details_text.insert(tk.END, f"{indent}   Expected: {expect}, Actual: {actual}\n", 'result')

                # Show error if any
                if error:
                    details_text.insert(tk.END, f"{indent}   Error: {error}\n", 'error')

                # Show additional metadata from response
                response_data = detail.get('response')
                if response_data and isinstance(response_data, dict):
                    # Extract metadata fields (excluding 'result' which is already shown)
                    metadata = {k: v for k, v in response_data.items() if k != 'result'}
                    if metadata:
                        details_text.insert(tk.END, f"{indent}   Metadata: {json.dumps(metadata)}\n", 'metadata')

                details_text.insert(tk.END, "\n")

            elif detail.get('type') == 'error':
                message = detail.get('message', 'Unknown error')
                details_text.insert(tk.END, f"{indent}ERROR: {message}\n", 'error')

        # Configure tags for colors
        details_text.tag_config('group', font=('Arial', 12, 'bold'))
        details_text.tag_config('pass', foreground='green', font=('Arial', 12, 'bold'))
        details_text.tag_config('fail', foreground='red', font=('Arial', 12, 'bold'))
        details_text.tag_config('params', foreground='blue')
        details_text.tag_config('result', foreground='gray')
        details_text.tag_config('error', foreground='orange')
        details_text.tag_config('metadata', foreground='purple')

        details_text.config(state='disabled')

        # Close/Stay buttons with auto-close timer
        button_frame = ttk.Frame(dialog, padding="10")
        button_frame.pack(fill=tk.X)

        remaining_seconds = 5
        timer_state = {"after_id": None, "stopped": False}

        def update_close_text():
            if timer_state["stopped"]:
                return
            nonlocal remaining_seconds
            if remaining_seconds <= 0:
                dialog.destroy()
                return
            close_button.config(text=f"Close ({remaining_seconds}s)")
            remaining_seconds -= 1
            timer_state["after_id"] = dialog.after(1000, update_close_text)

        def stop_timer():
            timer_state["stopped"] = True
            after_id = timer_state.get("after_id")
            if after_id is not None:
                dialog.after_cancel(after_id)
                timer_state["after_id"] = None

        def on_stay():
            stop_timer()
            stay_button.config(state=tk.DISABLED)
            close_button.config(text="Close")

        def on_close():
            stop_timer()
            dialog.destroy()

        close_button = ttk.Button(button_frame, text="Close", command=on_close)
        close_button.pack(side=tk.RIGHT)
        stay_button = ttk.Button(button_frame, text="Stay", command=on_stay)
        stay_button.pack(side=tk.RIGHT, padx=(0, 8))

        dialog.protocol("WM_DELETE_WINDOW", on_close)
        dialog.bind("<Return>", lambda _event: on_close())
        close_button.focus_set()
        update_close_text()

    def copy_original_command(self):
        """Copy the original content of the selected task to clipboard"""
        task_id = self.get_selected_task_id()
        if not task_id:
            return

        # Find the task in task_data
        task = None
        for t in self.task_data:
            if t.get('id') == task_id:
                task = t
                break

        if not task:
            messagebox.showwarning("No Task", "Could not find selected task")
            return

        content = task.get('content', '')
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            task_title = task.get('name') or task.get('title') or 'Unnamed Task'
            self.update_status(f"Original command copied to clipboard: {task_title}")
        else:
            messagebox.showinfo("No Content", "This task has no content to copy")

    def copy_random_command(self):
        """Copy a random command from content + content_aliases of the selected task"""
        task_id = self.get_selected_task_id()
        if not task_id:
            return

        # Find the task in task_data
        task = None
        for t in self.task_data:
            if t.get('id') == task_id:
                task = t
                break

        if not task:
            messagebox.showwarning("No Task", "Could not find selected task")
            return

        # Collect all available commands
        commands = []
        content = task.get('content', '')
        if content:
            commands.append(content)

        content_aliases = task.get('content_aliases', [])
        if content_aliases and isinstance(content_aliases, list):
            commands.extend(content_aliases)

        if commands:
            selected_command = random.choice(commands)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_command)
            task_title = task.get('name') or task.get('title') or 'Unnamed Task'
            self.update_status(f"Random command copied to clipboard: {task_title}")
        else:
            messagebox.showinfo("No Content", "This task has no content or aliases to copy")

    def _count_expected_checks(self, node):
        """Recursively count the number of leaf checks in an execution check structure."""
        if not isinstance(node, dict):
            return 0
        
        if 'checks' in node and isinstance(node['checks'], list):
            return sum(self._count_expected_checks(c) for c in node['checks'])
        
        # It's a leaf if it has 'endpoint' or 'path'
        if 'endpoint' in node or 'path' in node:
            return 1
        return 0

    def export_check_results(self):
        """Export the checking results of all tasks in JSON format with detailed statistics."""
        if not self.task_data:
            messagebox.showinfo("No Tasks", "No tasks available to export.")
            return

        session_id = self.get_current_session_id()
        session_name = self.current_session_name or session_id or "Unknown Session"
        
        # Initialize statistics accumulators
        passed_tasks_count = 0
        failed_tasks_count = 0
        total_failed_tasks_count = 0
        total_checks_count = 0
        passed_checks_count = 0
        sum_task_pass_rates = 0.0
        
        task_results = []
        total_tasks_count = len(self.task_data)

        self.logger.info("User initiated export of task check results")
        self.update_status("Preparing export data...")

        # Iterate over all tasks
        for idx, task in enumerate(self.task_data):
            task_id = task['id']
            task_name = task.get('name', 'Unnamed')
            
            # Update status for potentially slow operations (fetching unchecked tasks)
            self.update_status(f"Processing task export {idx + 1}/{total_tasks_count}...")

            # 1. Determine Check Data
            if hasattr(self, 'task_check_results') and task_id in self.task_check_results:
                # Result exists in memory
                check_data = self.task_check_results[task_id]
                
                # Handle legacy string format
                if isinstance(check_data, str):
                    status = check_data or 'failed'
                    timestamp = datetime.now().isoformat() # approximate
                    error = None
                    details = []
                    # Cannot calculate detailed stats from string only without re-fetching
                    # But if we have string, we likely ran check_all which stores detailed now.
                    # Fallback to fetching if details missing?
                    # Let's assume if it's passed/failed string, it was from old version check.
                    # To satisfy "total checks", we might need to fetch. 
                    # But let's rely on what we have or fetch if detail is missing.
                    total_checks = 0
                    passed_checks = 0
                    failed_checks = 0
                else:
                    status = check_data.get('status') or 'failed'
                    timestamp = check_data.get('timestamp')
                    error = check_data.get('error')
                    details = check_data.get('details', [])
                    
                    # Calculate stats from details
                    leaf_details = [d for d in details if d.get('type') == 'leaf']
                    total_checks = len(leaf_details)
                    passed_checks = sum(1 for d in leaf_details if d.get('result', False))
                    failed_checks = total_checks - passed_checks
            else:
                # Unchecked task - regard as failed per requirement
                status = 'failed'
                timestamp = None
                error = "Unchecked task exported as failed"
                details = []
                
                # We need to know total potential checks to populate statistics
                # Check if we have execution_check_apis in local task object
                execution_check_apis = task.get('execution_check_apis')
                
                if not execution_check_apis:
                    # Fetch full task details from API to get check definitions
                    try:
                        full_task = self.api_server.api_get_session_task(session_id, task_id)
                        if full_task:
                            execution_check_apis = full_task.get('execution_check_apis')
                    except Exception as e:
                        self.logger.error(f"Failed to fetch details for unchecked task {task_id}: {e}")
                
                total_checks = self._count_expected_checks(execution_check_apis)
                passed_checks = 0
                failed_checks = total_checks
            
            # 2. Calculate Task Rates
            pass_rate = (passed_checks / total_checks) if total_checks > 0 else 0.0
            total_checks_count += total_checks
            passed_checks_count += passed_checks
            
            # 3. Update Session Accumulators
            if status == 'passed':
                passed_tasks_count += 1
            else:
                failed_tasks_count += 1
                # Check for "all wrong" (completely failed)
                # If total_checks > 0 and passed == 0, it is completely failed
                if total_checks > 0 and passed_checks == 0:
                    total_failed_tasks_count += 1
                elif total_checks == 0:
                    # Tasks with no checks defined that are not passed are considered failed
                    total_failed_tasks_count += 1

            sum_task_pass_rates += pass_rate
            
            # 4. Build Task Record
            task_record = {
                "session_id": session_id,
                "session_name": session_name,
                "task_id": task_id,
                "task_name": task_name,
                "status": status,
                "timestamp": timestamp,
                "error": error,
                "statistics": {
                     "total_checks_apis": total_checks,
                     "passed_checks_apis": passed_checks,
                     "failed_checks_apis": failed_checks,
                     "pass_rate": round(pass_rate, 4)
                },
                "details": details
            }
            task_results.append(task_record)

        # 5. Calculate Session Statistics
        session_task_pass_rate = passed_tasks_count / total_tasks_count if total_tasks_count > 0 else 0.0
        total_failed_task_rate = total_failed_tasks_count / total_tasks_count if total_tasks_count > 0 else 0.0
        check_pass_rate = passed_checks_count / total_checks_count if total_checks_count > 0 else 0.0
        average_check_pass_rate = sum_task_pass_rates / total_tasks_count if total_tasks_count > 0 else 0.0

        # 6. Construct Export Data (ID first)
        server_version = None
        try:
            server_version = self.api_server.api_get_server_version(show_error=False)
        except Exception as e:
            self.logger.debug(f"Failed to fetch server version for export: {e}")

        export_data = {
            "id": "calculating...", # Placeholder to ensure order
            "export_timestamp": datetime.now().isoformat(),
            "tool": "MultiUAV-Plat GUI Controller",
            "version": self.version,
            "server_version": server_version,
            "statistics": {
                "total_tasks": total_tasks_count,
                "passed_tasks_count": passed_tasks_count,
                "failed_tasks_count": failed_tasks_count,
                "total_failed_task_count": total_failed_tasks_count,
                "task_pass_rate": round(session_task_pass_rate, 4),
                "total_failed_task_rate": round(total_failed_task_rate, 4),
                "average_check_pass_rate": round(average_check_pass_rate, 4),
                "total_checks": total_checks_count,
                "passed_checks": passed_checks_count,
                "failed_checks": total_checks_count - passed_checks_count,
                "check_pass_rate": round(check_pass_rate, 4)
            },
            "results": task_results
        }

        # 7. Calculate MD5 Hash
        try:
            import hashlib
            # Serialize the data excluding the ID itself
            data_to_hash = copy.deepcopy(export_data)
            data_to_hash.pop("id", None)
            
            results_json = json.dumps(data_to_hash, sort_keys=True)
            md5_hash = hashlib.md5(results_json.encode('utf-8')).hexdigest()
            export_data["id"] = md5_hash
        except Exception as e:
            self.logger.error(f"Failed to calculate MD5: {e}")
            export_data["id"] = "error_calculating_hash"

        # 8. Save to File
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested_filename = f"agent_check_results_{timestamp_str}.json"

        filename = filedialog.asksaveasfilename(
            title="Export Task Results",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=suggested_filename
        )

        if not filename:
            self.update_status("Export cancelled")
            return

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            stats = export_data["statistics"]
            self.logger.info(f"Task check results exported successfully to {filename}. exported json ID: {export_data['id']}")
            messagebox.showinfo(
                "Success", 
                f"Task results exported to:\n{filename}\n\n"
                f"Summary:\n"
                f"• Passed Tasks: {stats['passed_tasks_count']}/{stats['total_tasks']}\n"
                f"• Task Pass Rate: {stats['task_pass_rate']:.2%}\n"
                f"• Avg Check Pass Rate: {stats['average_check_pass_rate']:.2%}"
            )
            self.update_status("Task results exported")
        except Exception as e:
            self.logger.error(f"Failed to export results: {e}")
            messagebox.showerror("Export Error", f"Failed to export results: {str(e)}")
            self.update_status("Failed to export results")

    def show_task_details(self, event=None):
        """Show detailed information about selected task"""
        selection = self.task_listbox.curselection()
        if not selection:
            return

        task_id = self.get_selected_task_id()
        if task_id:
            # Get current session ID from cache
            session_id = self.get_current_session_id()

            task_data = self.api_server.api_get_session_task(session_id, task_id)
            if task_data:
                self.active_detail_dialog = DetailDialog(self.root, "Task Details", task_data, self)

    def _prefetch_dashboard_data(self) -> Dict[str, Any]:
        """Fetch shared datasets needed across multiple refreshers.

        Returns a dict containing any successfully retrieved payloads.
        """
        datasets: Dict[str, Any] = {}

        # Fetch session with complete data including tasks
        session = self._get_cached_or_remote_session()
        if session:
            datasets['session'] = session  # Keep full session data (includes tasks)

        drones = self.api_server.api_get_drones()
        if drones is not None:
            datasets['drones'] = drones

        targets = self.api_server.api_get_targets()
        if targets is not None:
            datasets['targets'] = targets

        obstacles = self.api_server.api_get_obstacles()
        if obstacles is not None:
            datasets['obstacles'] = obstacles

        environments = self.api_server.api_get_environments()
        if environments is not None:
            datasets['environments'] = environments

        return datasets

    def _get_cached_or_remote_session(self):
        """Return cached /sessions/current?data=true response if available."""
        if self._cached_current_session_payload:
            self.logger.debug("Using cached /sessions/current?data=true payload")
            return self._cached_current_session_payload
        response = self.api_server.api_get_current_session_with_data()
        if isinstance(response, dict):
            self._cached_current_session_payload = response
        return response
    
    def refresh_all_data(self, prefetched_data: Optional[Dict[str, Any]] = None):
        """Refresh all data in all tabs.

        If `prefetched_data` is provided, reuse it to avoid immediate duplicate API calls.
        """
        if not self._is_gui_available():
            self.logger.debug("Skipping refresh_all_data because GUI is closing or destroyed")
            return
        if prefetched_data:
            # self.logger.info(f"Using prefetched data with {len(prefetched_data)} datasets: {list(prefetched_data.keys())}")
            datasets = prefetched_data
            if isinstance(prefetched_data.get('session'), dict):
                self._cached_current_session_payload = prefetched_data.get('session')
        else:
            self.logger.info("No prefetched data provided, fetching from API")
            self._cached_current_session_payload = None
            datasets = self._prefetch_dashboard_data()

        self.refresh_statistics(
            session=datasets.get('session'),
            drones=datasets.get('drones'),
            targets=datasets.get('targets'),
            obstacles=datasets.get('obstacles'),
            tasks=(datasets.get('session') or {}).get('tasks') if isinstance(datasets.get('session'), dict) else None,
        )
        self.refresh_drones(drones=datasets.get('drones'))
        self.refresh_targets(targets=datasets.get('targets'))
        self.refresh_obstacles(obstacles=datasets.get('obstacles'))
        self.refresh_environments(environments=datasets.get('environments'))

        # Refresh tasks - use tasks from prefetched data if available
        # The /sessions/current?data=true response includes tasks in the session object
        tasks = None
        if datasets.get('session'):
            # Try to get tasks from the session data (if it was fetched with ?data=true)
            session_data = datasets.get('session')
            # Tasks might be at the root level of the response or nested
            if 'tasks' in session_data:
                tasks = session_data.get('tasks')

        self.refresh_tasks(tasks=tasks)
    
    # Detail dialog methods for double-click functionality
    def show_drone_details(self, event=None):
        """Show detailed information about selected drone"""
        selection = self.drone_listbox.curselection()
        if not selection:
            return
        
        drone_id = self.get_selected_drone_id()
        if drone_id:
            drone_data = self.api_server.api_get_drone(drone_id)
            if drone_data:
                self.active_detail_dialog = DetailDialog(self.root, "Drone Details", drone_data, self)

    def show_target_details(self, event=None):
        """Show detailed information about selected target"""
        selection = self.target_listbox.curselection()
        if not selection:
            return
        
        target_id = self.get_selected_target_id()
        if target_id:
            target_data = self.api_server.api_get_target(target_id)
            if target_data:
                self.active_detail_dialog = DetailDialog(self.root, "Target Details", target_data, self)

    def show_environment_details(self, event=None):
        """Show detailed information about selected environment"""
        selection = self.env_listbox.curselection()
        if not selection:
            return
        
        env_id = self.get_selected_environment_id()
        if env_id:
            env_data = self.api_server.api_get_environment(env_id)
            if env_data:
                self.active_detail_dialog = DetailDialog(self.root, "Environment Details", env_data, self)
    
    # Obstacles management methods
    def refresh_obstacles(self, obstacles=None):
        """Refresh the obstacles list.

        Optional `obstacles` lets callers reuse prefetched data.
        """
        self.update_status("Refreshing obstacles...")
        obstacles_data = obstacles if obstacles is not None else self.api_server.api_get_obstacles()
        if obstacles_data is not None:
            self.obstacles_listbox.delete(0, tk.END)
            for obstacle in obstacles_data:
                obstacle_type = obstacle.get('type', 'unknown')
                pos = obstacle.get('position', {})
                x, y, z = pos.get('x', 0), pos.get('y', 0), pos.get('z', 0)
                display_text = f"{obstacle['name']} ({obstacle['id']}) - {obstacle_type} - Pos: ({format_number(x)}, {format_number(y)}, {format_number(z)})"
                self.obstacles_listbox.insert(tk.END, display_text)
            self.update_status(f"Found {len(obstacles_data)} obstacles")
        else:
            self.update_status("Failed to refresh obstacles")
    
    def get_selected_obstacle_id(self) -> Optional[str]:
        """Get the ID of the currently selected obstacle"""
        selection = self.obstacles_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an obstacle first")
            return None
        
        obstacle_text = self.obstacles_listbox.get(selection[0])
        try:
            obstacle_id = obstacle_text.split('(')[1].split(')')[0]
            return obstacle_id
        except IndexError:
            messagebox.showerror("Error", "Could not parse obstacle ID")
            return None
    
    def get_selected_obstacle_ids(self) -> list:
        """Get the IDs of all selected obstacles"""
        selection = self.obstacles_listbox.curselection()
        if not selection:
            return []
        
        obstacle_ids = []
        for index in selection:
            obstacle_text = self.obstacles_listbox.get(index)
            try:
                obstacle_id = obstacle_text.split('(')[1].split(')')[0]
                obstacle_ids.append(obstacle_id)
            except IndexError:
                continue
        return obstacle_ids
    
    ''' UNUSED - obstacle creation dialogs slated for removal
    def add_static_obstacle(self):
        """Add a static obstacle"""
        self.disable_global_shortcuts()
        dialog = StaticObstacleDialog(self.root)
        self.enable_global_shortcuts()
        if dialog.result:
            self.update_status("Adding static obstacle...")
            result = self.api_server.api_create_obstacle(dialog.result)
            if result:
                # Mark session as modified
                self.set_modified()
                messagebox.showinfo("Success", f"Static obstacle added with ID: {result['id']}")
                self.refresh_obstacles()
            else:
                self.update_status("Failed to add static obstacle")
    
    def add_dynamic_obstacle(self):
        """Add a dynamic obstacle"""
        self.disable_global_shortcuts()
        dialog = DynamicObstacleDialog(self.root)
        self.enable_global_shortcuts()
        if dialog.result:
            self.update_status("Adding dynamic obstacle...")
            result = self.api_server.api_create_obstacle(dialog.result)
            if result:
                # Mark session as modified
                self.set_modified()
                messagebox.showinfo("Success", f"Dynamic obstacle added with ID: {result['id']}")
                self.refresh_obstacles()
            else:
                self.update_status("Failed to add dynamic obstacle")
    
    def add_no_fly_zone(self):
        """Add a no-fly zone"""
        self.disable_global_shortcuts()
        dialog = NoFlyZoneDialog(self.root)
        self.enable_global_shortcuts()
        if dialog.result:
            self.update_status("Adding no-fly zone...")
            result = self.api_server.api_create_obstacle(dialog.result)
            if result:
                messagebox.showinfo("Success", f"No-fly zone added with ID: {result['id']}")
                self.refresh_obstacles()
            else:
                self.update_status("Failed to add no-fly zone")
    '''
    
    def delete_obstacle(self):
        """Delete selected obstacle(s)"""
        selected_ids = self.get_selected_obstacle_ids()
        if not selected_ids:
            messagebox.showwarning("No Selection", "Please select one or more obstacles to delete")
            return

        obstacle_list = self.format_delete_id_list(selected_ids)
        if self.ask_delete_confirmation("Delete Obstacles", f"Delete the following obstacle(s)?\n{obstacle_list}"):
            deleted_count = 0
            for obstacle_id in selected_ids:
                self.update_status(f"Deleting obstacle {obstacle_id}...")
                result = self.api_server.api_delete_obstacle(obstacle_id)
                if result is not None:
                    deleted_count += 1

            if deleted_count > 0:
                # Mark session as modified
                self.set_modified()
                messagebox.showinfo("Success", f"Successfully deleted {deleted_count} obstacle(s)")
                self.refresh_obstacles()
            else:
                self.update_status("Failed to delete obstacles")

    def edit_obstacle(self):
        """Edit selected obstacle"""
        obstacle_id = self.get_selected_obstacle_id()
        if not obstacle_id:
            return

        self.logger.info(f"User initiated edit obstacle operation for obstacle {obstacle_id}")
        self.update_status(f"Fetching obstacle {obstacle_id} data...")

        # Fetch current obstacle data
        obstacle_data = self.api_server.api_get_obstacle(obstacle_id)
        if not obstacle_data:
            messagebox.showerror("Error", f"Failed to fetch data for obstacle {obstacle_id}")
            return

        obstacle_type = obstacle_data.get('type', 'point')

        # Choose appropriate dialog based on obstacle type
        self.disable_global_shortcuts()
        dialog = None
        if obstacle_type == 'polygon':
            # Use shared polygon dialog
            dialog = PolygonDialog(self.root, item_type="obstacle", edit_mode=True, initial_data=obstacle_data)
        elif obstacle_type == 'circle':
            # Use shared circle dialog
            dialog = CircleDialog(self.root, item_type="obstacle", edit_mode=True, initial_data=obstacle_data)
        elif obstacle_type == 'ellipse':
            # Use ellipse obstacle dialog
            dialog = EllipseObstacleDialog(self.root, edit_mode=True, initial_data=obstacle_data)
        elif obstacle_type == 'point':
            # Use point obstacle dialog
            dialog = PointObstacleDialog(self.root, edit_mode=True, initial_data=obstacle_data)
        else:
            self.enable_global_shortcuts()
            messagebox.showerror("Unknown Type", f"Unknown obstacle type: {obstacle_type}")
            return
        self.enable_global_shortcuts()

        if dialog and dialog.result:
            self.logger.info(f"User updated obstacle data")
            self.update_status(f"Updating obstacle {obstacle_id}...")

            # Build payload based on obstacle type
            if obstacle_type == 'polygon':
                payload = {
                    "name": dialog.result.get("name", "Polygon Obstacle"),
                    "type": "polygon",
                    "position": {
                        "x": float(dialog.result.get("x", 0.0)),
                        "y": float(dialog.result.get("y", 0.0)),
                        "z": float(dialog.result.get("z", 0.0)),
                    },
                    "description": dialog.result.get("description", ""),
                    "vertices": dialog.result.get("vertices", []),
                }
                height = dialog.result.get("height")
                if height is not None:
                    payload["height"] = float(height)
            elif obstacle_type == 'circle':
                payload = {
                    "name": dialog.result.get("name", "Circle Obstacle"),
                    "type": "circle",
                    "position": {
                        "x": float(dialog.result.get("x", 0.0)),
                        "y": float(dialog.result.get("y", 0.0)),
                        "z": float(dialog.result.get("z", 0.0)),
                    },
                    "description": dialog.result.get("description", ""),
                    "radius": float(dialog.result.get("radius", 10.0)),
                }
                height = dialog.result.get("height")
                if height is not None:
                    payload["height"] = float(height)
            elif obstacle_type == 'ellipse':
                payload = {
                    "name": dialog.result.get("name", "Ellipse Obstacle"),
                    "type": "ellipse",
                    "position": {
                        "x": float(dialog.result.get("x", 0.0)),
                        "y": float(dialog.result.get("y", 0.0)),
                        "z": float(dialog.result.get("z", 0.0)),
                    },
                    "description": dialog.result.get("description", ""),
                    "width": float(dialog.result.get("width", 10.0)),
                    "length": float(dialog.result.get("length", 15.0)),
                }
                height = dialog.result.get("height")
                if height is not None:
                    payload["height"] = float(height)
            elif obstacle_type == 'point':
                payload = {
                    "name": dialog.result.get("name", "Point Obstacle"),
                    "type": "point",
                    "position": {
                        "x": float(dialog.result.get("x", 0.0)),
                        "y": float(dialog.result.get("y", 0.0)),
                        "z": float(dialog.result.get("z", 0.0)),
                    },
                    "description": dialog.result.get("description", ""),
                    "radius": float(dialog.result.get("radius", 1.0)),
                }
                height = dialog.result.get("height")
                if height is not None:
                    payload["height"] = float(height)

            # Update via API
            result = self.api_server.api_update_obstacle(obstacle_id, payload)
            if result:
                self.logger.info(f"Obstacle {obstacle_id} successfully updated")
                # Mark session as modified
                self.set_modified()
                messagebox.showinfo("Success", f"Obstacle {obstacle_id} updated successfully")
                self.refresh_obstacles()
            else:
                self.logger.warning(f"Failed to update obstacle {obstacle_id}")
                messagebox.showerror("Error", f"Failed to update obstacle {obstacle_id}")
        else:
            self.logger.info("User cancelled edit obstacle operation")

    def show_obstacle_details(self, event=None):
        """Show detailed information about selected obstacle"""
        selection = self.obstacles_listbox.curselection()
        if not selection:
            return
        
        obstacle_id = self.get_selected_obstacle_id()
        if obstacle_id:
            obstacle_data = self.api_server.api_get_obstacle(obstacle_id)
            if obstacle_data:
                self.active_detail_dialog = DetailDialog(self.root, "Obstacle Details", obstacle_data, self)
    
    def _build_obstacle_payload(self, obstacle_type: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Convert obstacle dialog result into API payload."""
        payload = {
            "name": result.get("name", f"{obstacle_type.title()} Obstacle"),
            "type": obstacle_type,
            "position": {
                "x": float(result.get("x", 0.0)),
                "y": float(result.get("y", 0.0)),
                "z": float(result.get("z", 0.0)),
            },
            "description": result.get("description", ""),
        }

        if obstacle_type == "circle":
            payload["radius"] = float(result.get("radius", 10.0))
        elif obstacle_type == "ellipse":
            payload["width"] = float(result.get("width", 10.0))
            payload["length"] = float(result.get("length", 15.0))
        elif obstacle_type == "polygon":
            payload["vertices"] = result.get("vertices", [])
        elif obstacle_type == "point":
            radius = result.get("radius")
            if radius is not None:
                payload["radius"] = float(radius)

        height = result.get("height")
        if height is not None:
            payload["height"] = float(height)

        return payload

    def _create_obstacle_from_dialog(self, obstacle_type: str, dialog_cls, dialog_kwargs: Optional[Dict[str, Any]] = None):
        """Generic obstacle creation flow to reduce duplication."""
        display_name = obstacle_type.replace("_", " ").title()
        self.logger.info(f"User initiated add {display_name.lower()} obstacle operation")

        dialog_kwargs = dialog_kwargs or {}
        self.disable_global_shortcuts()
        try:
            dialog = dialog_cls(self.root, **dialog_kwargs)
        finally:
            self.enable_global_shortcuts()

        if not getattr(dialog, "result", None):
            self.logger.info(f"User cancelled add {display_name.lower()} obstacle operation")
            return

        self.logger.info(f"User provided {display_name.lower()} obstacle data")
        self.update_status(f"Adding {display_name.lower()} obstacle...")

        payload = self._build_obstacle_payload(obstacle_type, dialog.result)
        result = self.api_server.api_create_obstacle(payload)
        if result:
            obstacle_id = result.get('id', 'Unknown')
            self.logger.info(f"{display_name} obstacle successfully added with ID: {obstacle_id}")
            # Mark session as modified
            self.set_modified()
            messagebox.showinfo("Success", f"{display_name} obstacle added with ID: {obstacle_id}")
            self.refresh_obstacles()
        else:
            self.logger.warning(f"Failed to add {display_name.lower()} obstacle - API request unsuccessful")
            self.update_status(f"Failed to add {display_name.lower()} obstacle")

    def add_point_obstacle(self):
        """Add a point obstacle"""
        self._create_obstacle_from_dialog("point", PointObstacleDialog, {"edit_mode": False})
    
    def add_ellipse_obstacle(self):
        """Add an ellipse obstacle"""
        self._create_obstacle_from_dialog("ellipse", EllipseObstacleDialog, {"edit_mode": False})

    def add_circle_obstacle(self):
        """Add a circle obstacle"""
        self._create_obstacle_from_dialog("circle", CircleDialog, {"item_type": "obstacle", "edit_mode": False})
    
    def add_polygon_obstacle(self):
        """Add a polygon obstacle"""
        self._create_obstacle_from_dialog("polygon", PolygonDialog, {"item_type": "obstacle", "edit_mode": False})

    def ask_save_reload_leave_cancel(self):
        """Show a custom dialog with Save, Reload, Leave buttons.

        Returns:
            'save': User wants to save
            'reload': User wants to reload from disk
            'leave': User wants to close without changes
            'cancel': User wants to cancel the operation
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Unsaved Changes")
        dialog.resizable(False, False)
        set_window_geometry_and_center(dialog, 370, 150, self.root)

        # Store result
        result = {'action': 'cancel'}

        # Message
        message_frame = ttk.Frame(dialog, padding=20)
        message_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            message_frame,
            text="You have unsaved changes.\n\nWhat would you like to do?",
            justify=tk.CENTER
        ).pack(expand=True)

        # Buttons
        button_frame = ttk.Frame(dialog, padding=(20, 0, 20, 20))
        button_frame.pack(fill=tk.X)
        buttons_container = ttk.Frame(button_frame)
        buttons_container.pack()

        def on_save():
            result['action'] = 'save'
            dialog.destroy()

        def on_reload():
            result['action'] = 'reload'
            dialog.destroy()

        def on_leave():
            result['action'] = 'leave'
            dialog.destroy()

        ttk.Button(buttons_container, text="Save", command=on_save, width=6).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_container, text="Reload", command=on_reload, width=6).pack(side=tk.LEFT, padx=5)
        leave_button = ttk.Button(buttons_container, text="Leave", command=on_leave, width=6)
        leave_button.pack(side=tk.LEFT, padx=5)

        # Handle window close as cancel
        dialog.protocol("WM_DELETE_WINDOW", lambda: result.update(action='cancel') or dialog.destroy())

        # Default focus to Leave (close without changes)
        leave_button.focus_set()
        dialog.wait_window()

        return result['action']

    def _reload_session_from_file_on_close(self) -> bool:
        """Reload the last saved/imported session (or current snapshot) before closing."""
        try:
            session_id = self.get_current_session_id()
            if not session_id:
                messagebox.showerror("Reload Failed", "Could not determine the current session ID.")
                return False

            identifier = self.imported_session_filepath or session_id
            payload, resolved_path = load_session_from_file(identifier)
            if not isinstance(payload, dict):
                messagebox.showerror("Reload Failed", "Invalid session file format.")
                return False

            request_data = normalize_session_canvas_fields(payload)
            response = self.api_server.api_new_session_with_id(session_id, request_data)
            if not response:
                messagebox.showerror("Reload Failed", "Failed to reload session data on the server.")
                return False

            self.imported_session_filepath = str(resolved_path)
            self.set_modified(False)
            return True
        except Exception as exc:
            self.logger.error(f"Failed to reload session from file: {exc}")
            messagebox.showerror("Reload Failed", f"Failed to reload session from file: {exc}")
            return False

    def on_closing(self):
        """Handle window close event - check for unsaved changes and cleanup session editor processes"""
        if getattr(self, 'app_closing', False):
            return

        # Check for unsaved changes first
        if self.is_modified:
            self.logger.info("Detected unsaved changes on close")
            response = self.ask_save_reload_leave_cancel()

            if response == 'cancel':
                self.logger.info("User cancelled close operation")
                return
            elif response == 'save':
                self.logger.info("User chose to save before closing")
                saved_path = save_current_session_to_file(
                    self._get_cached_or_remote_session,
                    target_filepath=self.imported_session_filepath,
                    logger=self.logger
                )

                if saved_path:
                    self.imported_session_filepath = saved_path
                    self.set_modified(False)
                else:
                    # Save failed, ask if they want to continue closing anyway
                    continue_anyway = messagebox.askyesno(
                        "Save Failed",
                        "Failed to save session.\n\n"
                        "Do you want to close anyway and lose your changes?",
                        icon='error'
                    )
                    if not continue_anyway:
                        self.logger.info("User cancelled close after failed save")
                        return
            elif response == 'reload':
                self.logger.info("User chose to reload from disk before closing")
                if not self._reload_session_from_file_on_close():
                    self.logger.info("User aborted close after reload failure")
                    return
            elif response == 'leave':
                self.logger.info("User chose to leave without saving; closing without changes")

        # Check if any session editor processes are still running
        active_processes = [p for p in self.active_editor_processes if p.poll() is None]
        proceed_with_close = True

        if active_processes:
            self.logger.info(f"Found {len(active_processes)} active session editor process(es)")

            # Ask user for confirmation
            response = messagebox.askyesno(
                "Session Editors Open",
                f"There are {len(active_processes)} session editor window(s) still open.\n\n"
                "Closing the GUI Controller will also close all session editors.\n"
                "Any unsaved changes will trigger save prompts in the editor windows.\n\n"
                "Do you want to continue?",
                icon='warning'
            )

            if not response:
                self.logger.info("User cancelled GUI close operation")
                proceed_with_close = False

        if not proceed_with_close:
            return

        self.app_closing = True
        self._stop_all_editor_save_monitors()

        if active_processes:
            # Send termination signal to all editor processes
            self.logger.info("Terminating all session editor processes...")
            for process in active_processes:
                try:
                    # Send SIGTERM (graceful shutdown) on Unix, CTRL_C on Windows
                    if platform.system() == 'Windows':
                        # On Windows, use terminate() which sends SIGTERM
                        process.terminate()
                    else:
                        # On Unix (macOS, Linux), send SIGTERM for graceful shutdown
                        process.send_signal(signal.SIGTERM)

                    self.logger.info(f"Sent termination signal to editor process (PID: {process.pid})")
                except Exception as e:
                    self.logger.error(f"Failed to terminate process {process.pid}: {e}")

            # Wait for processes to close gracefully
            # Give more time on macOS as Tkinter dialogs may need user interaction
            self.logger.info("Waiting for editor processes to close gracefully...")
            max_wait = 10  # seconds (increased from 5 to give user time for save dialogs)
            start_time = time.time()

            last_count = len(active_processes)
            while active_processes and (time.time() - start_time) < max_wait:
                active_processes = [p for p in active_processes if p.poll() is None]
                current_count = len(active_processes)

                # If count changed, reset timer a bit (user is interacting with dialogs)
                if current_count < last_count:
                    self.logger.info(f"Editor process closed, {current_count} remaining...")
                    last_count = current_count
                    # Give a bit more time when user is actively closing editors
                    start_time = time.time() - (max_wait / 2)

                if active_processes:
                    time.sleep(0.1)
                    try:
                        self.root.update()  # Keep GUI responsive
                    except tk.TclError:
                        # GUI might be closing, ignore
                        pass

            # Force kill any processes that didn't close gracefully
            still_running = [p for p in active_processes if p.poll() is None]
            if still_running:
                self.logger.warning(f"{len(still_running)} process(es) did not close gracefully after {max_wait}s, force killing...")
                for process in still_running:
                    try:
                        process.kill()
                        self.logger.warning(f"Force killed editor process (PID: {process.pid})")
                    except Exception as e:
                        self.logger.error(f"Failed to kill process {process.pid}: {e}")

        # Close the GUI
        self.logger.info("Closing GUI Controller")
        self.root.destroy()

    

    def save_session_as(self):
        """Duplicate the current session with a new name using the session API."""
        try:
            session_id = self.get_current_session_id()

            current_info = self.api_server.api_get_current_session() or {}
            current_name = current_info.get('name') or self.current_session_name or session_id
            suggested_name = f"{current_name} (Copy)"

            new_name = simpledialog.askstring(
                "Save Session As",
                "Enter name for the duplicated session:",
                initialvalue=suggested_name,
                parent=self.root
            )

            if not new_name:
                return  # User cancelled

            new_name = new_name.strip()
            if not new_name:
                messagebox.showwarning("Invalid Name", "Session name cannot be empty")
                return

            self.update_status(f"Duplicating session as '{new_name}'...")
            self.logger.info(f"Duplicating current session {session_id} as '{new_name}'")

            session_data_response = self.api_server.api_get_session_data(session_id)
            if not session_data_response:
                raise Exception("Failed to retrieve current session data from API")

            drones_copy = []
            for drone in session_data_response.get('drones', []) or []:
                drone_copy = copy.deepcopy(drone)
                drone_copy.pop('id', None)
                drone_copy['session_id'] = None
                drones_copy.append(drone_copy)

            targets_copy = []
            for target in session_data_response.get('targets', []) or []:
                target_copy = copy.deepcopy(target)
                target_copy.pop('id', None)
                target_copy['session_id'] = None
                targets_copy.append(target_copy)

            obstacles_copy = []
            for obstacle in session_data_response.get('obstacles', []) or []:
                obstacle_copy = copy.deepcopy(obstacle)
                obstacle_copy.pop('id', None)
                obstacle_copy['session_id'] = None
                obstacles_copy.append(obstacle_copy)

            tasks_copy = []
            for task in session_data_response.get('tasks', []) or []:
                task_copy = copy.deepcopy(task)
                task_copy.pop('id', None)
                task_copy['session_id'] = None
                tasks_copy.append(task_copy)

            description = current_info.get('description', '') or session_data_response.get('description', '')
            task_type = current_info.get('task_type', session_data_response.get('task_type', 'others'))
            task_description = current_info.get('task_description', session_data_response.get('task_description', ''))

            save_payload = {
                'name': new_name,
                'description': description + ' (duplicated copy)',
                'status': 'active',
                'task_type': task_type,
                'task_description': task_description,
                'creator': self.username,
                'drones': drones_copy,
                'targets': targets_copy,
                'obstacles': obstacles_copy,
                'tasks': tasks_copy,
                'environment': session_data_response.get('environment'),
                'canvas_width': session_data_response.get('canvas_width'),
                'canvas_length': session_data_response.get('canvas_length'),
                'canvas_height': session_data_response.get('canvas_height'),
                'area_width': session_data_response.get('area_width'),
                'area_height': session_data_response.get('area_height'),
            }
            save_payload = normalize_session_canvas_fields(save_payload)

            self.logger.info(
                "Creating duplicated session payload (drones=%d, targets=%d, obstacles=%d, tasks=%d)",
                len(drones_copy), len(targets_copy), len(obstacles_copy), len(tasks_copy)
            )

            response = self.api_server.api_new_session(save_payload)
            if not response:
                raise Exception("Failed to create duplicated session")

            new_session_id = response.get('id')
            if not new_session_id:
                raise Exception("API did not return a new session ID")

            self.logger.info(f"Successfully created duplicated session: {new_session_id}")

            # Activate the new session
            self.api_server.api_set_session_as_current(new_session_id)

            # Save to storage for local reference
            storage_result = None
            storage_snapshot = self.api_server.api_get_session_data(new_session_id)
            if storage_snapshot:
                try:
                    saved_path = save_session_to_file(storage_snapshot)
                    storage_result = str(saved_path)
                    self.logger.info(f"Duplicated session saved to storage file: {saved_path}")
                except Exception as exc:
                    self.logger.warning(f"Failed to save duplicated session to storage: {exc}")
            else:
                self.logger.warning("Could not fetch snapshot for duplicated session storage")

            # Update local state/caches
            self.current_session_id = new_session_id
            self.current_session_name = new_name
            self.imported_session_filepath = None
            self.is_modified = False
            self._cached_current_session_payload = storage_snapshot

            self.refresh_all_data()

            messagebox.showinfo(
                "Success",
                f"Session duplicated successfully as '{new_name}'!\n\n"
                f"New Session ID: {new_session_id}\n"
                f"Drones: {len(drones_copy)}\n"
                f"Targets: {len(targets_copy)}\n"
                f"Obstacles: {len(obstacles_copy)}\n"
                f"Tasks: {len(tasks_copy)}\n"
                f"Storage: {storage_result or 'Not saved to file'}"
            )
            self.update_status(f"Session duplicated successfully as '{new_name}'")

        except Exception as exc:
            self.logger.error(f"Failed to duplicate session: {exc}")
            messagebox.showerror("Error", f"Failed to duplicate session: {exc}")
            self.update_status("Failed to duplicate session")

    def show_session_info(self):
        """Show information about the current session"""
        try:
            session = self.api_server.api_get_session_info()
            if session:
                info = f"Session ID: {session.get('id', 'N/A')}\n"
                info += f"Name: {session.get('name', 'N/A')}\n"
                info += f"Description: {session.get('description', 'N/A')}\n"
                info += f"Status: {session.get('status', 'N/A')}\n"
                info += f"Created: {session.get('created_at', 'N/A')}\n"
                info += f"Modified: {session.get('updated_at', 'N/A')}\n"

                if self.imported_session_filepath:
                    info += f"\nFile: {self.imported_session_filepath}"

                messagebox.showinfo("Session Information", info)
            else:
                messagebox.showerror("Error", "Failed to get session info")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get session info: {str(e)}")


    def add_task(self):
        """Add a new task"""
        dialog = TaskDialog(self.root, edit_mode=False, username=self.username, task_count=len(self.task_data))
        if dialog.result:
            try:
                result = self.api_server.api_add_task_current(dialog.result)
                if result is not None:
                    self.is_modified = True
                    self.refresh_tasks()
                    messagebox.showinfo("Success", "Task added successfully!")
                else:
                    messagebox.showerror("Error", "Failed to add task")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add task: {str(e)}")

    # Tab switching methods
    def switch_to_statistics_tab(self):
        """Switch to Statistics tab"""
        for i in range(self.notebook.index("end")):
            if self.notebook.tab(i, "text") == "Statistics":
                self.notebook.select(i)
                break

    def switch_to_drones_tab(self):
        """Switch to Drones tab"""
        for i in range(self.notebook.index("end")):
            if self.notebook.tab(i, "text") == "Drones":
                self.notebook.select(i)
                break

    def switch_to_targets_tab(self):
        """Switch to Targets tab"""
        for i in range(self.notebook.index("end")):
            if self.notebook.tab(i, "text") == "Targets":
                self.notebook.select(i)
                break

    def switch_to_obstacles_tab(self):
        """Switch to Obstacles tab"""
        for i in range(self.notebook.index("end")):
            if self.notebook.tab(i, "text") == "Obstacles":
                self.notebook.select(i)
                break

    def switch_to_environment_tab(self):
        """Switch to Environment tab"""
        for i in range(self.notebook.index("end")):
            if self.notebook.tab(i, "text") == "Environment":
                self.notebook.select(i)
                break

    def switch_to_tasks_tab(self):
        """Switch to Tasks tab"""
        for i in range(self.notebook.index("end")):
            if self.notebook.tab(i, "text") == "Tasks":
                self.notebook.select(i)
                break

    def switch_to_history_tab(self):
        """Switch to History tab"""
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        for i in range(self.notebook.index("end")):
            if self.notebook.tab(i, "text") == "History":
                self.notebook.select(i)
                if current_tab == "History":
                    self.refresh_request_history()
                break

    def show_about(self):
        """Show About dialog with system information"""
        show_about_dialog(
            self.root,
            version=self.version,
            build=self.build,
            api_base_url=self.api_server.api_base_url,
            api_connected=None,
            set_icon=lambda dialog: (
                dialog.iconphoto(False, self._icon_image),
                setattr(dialog, "_uav_icon_image", self._icon_image),
            ) if self._icon_image else None,
        )

    def show_keyboard_shortcuts(self):
        """Show keyboard shortcuts dialog"""
        save_shortcut = "Cmd+S" if platform.system() == 'Darwin' else "Ctrl+S"
        save_as_shortcut = "Cmd+Shift+S" if platform.system() == 'Darwin' else "Ctrl+Shift+S"
        session_info_shortcut = "Cmd+I" if platform.system() == 'Darwin' else "Ctrl+I"
        close_shortcut = "Cmd+W" if platform.system() == 'Darwin' else "Ctrl+W"
        shortcuts = f"""Keyboard Shortcuts:

{save_shortcut} - Save Session
{save_as_shortcut} - Save Session As
{session_info_shortcut} - Session Info
{close_shortcut} - Close Window
Ctrl+D - Add Drone
Ctrl+T - Add Task
F5 - Refresh All Data

Double-click on list items to view details.
"""
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)


class MoveToDialog:
    """Dialog for moving drone to coordinates"""
    def __init__(self, parent, current_position=(0.0, 0.0, 10.0)):
        self.result = None
        self.current_position = current_position
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Move Drone To")
        set_window_geometry_and_center(self.dialog, 300, 200, parent)
        
        self.create_widgets()
        self.dialog.wait_window()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Heading (use grid to avoid mixing pack and grid in the same frame)
        ttk.Label(
            main_frame,
            text="Move Drone To",
            font=("TkDefaultFont", 12, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 8))
        
        ttk.Label(main_frame, text="X Coordinate:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.x_var = tk.StringVar(value=format_number(self.current_position[0]))
        ttk.Entry(main_frame, textvariable=self.x_var, width=20).grid(row=1, column=1, pady=2)

        ttk.Label(main_frame, text="Y Coordinate:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.y_var = tk.StringVar(value=format_number(self.current_position[1]))
        ttk.Entry(main_frame, textvariable=self.y_var, width=20).grid(row=2, column=1, pady=2)

        ttk.Label(main_frame, text="Z Coordinate:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.z_var = tk.StringVar(value=format_number(self.current_position[2]))
        ttk.Entry(main_frame, textvariable=self.z_var, width=20).grid(row=3, column=1, pady=2)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)

        move_button = ttk.Button(button_frame, text="Move", command=self.ok_clicked)
        move_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.LEFT, padx=5)

        # Set focus on Move button
        move_button.focus_set()
    
    def ok_clicked(self):
        try:
            self.result = {
                "x": float(self.x_var.get()),
                "y": float(self.y_var.get()),
                "z": float(self.z_var.get())
            }
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric values")
    
    def cancel_clicked(self):
        self.dialog.destroy()


class EnvironmentDialog:
    """Dialog for creating or editing environments"""
    def __init__(self, parent, edit_mode=False, initial_data=None):
        self.result = None
        self.edit_mode = edit_mode
        self.initial_data = initial_data or {}

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Edit Environment" if edit_mode else "Create Environment")
        set_window_geometry_and_center(self.dialog, 430, 330, parent)

        self.create_widgets()
        self.dialog.wait_window()

    def create_widgets(self):
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        
        default_name = self.initial_data.get('name')
        if not default_name:
            try:
                server = APIServer()
                existing_envs = server.api_get_environments(show_error=False)
                
                existing_names = []
                existing_names = [e.get('name', '') for e in existing_envs] if existing_envs else []
                default_name = create_new_name("New Environment", exist_list=existing_names)
            except Exception:
                default_name = "New Environment"
                
        self.name_var = tk.StringVar(value=default_name)
        ttk.Entry(main_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, pady=2)

        ttk.Label(main_frame, text="Description:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.desc_var = tk.StringVar(value=self.initial_data.get('description', ""))
        ttk.Entry(main_frame, textvariable=self.desc_var, width=30).grid(row=1, column=1, pady=2)

        ttk.Label(main_frame, text="Weather Condition:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.weather_var = tk.StringVar(value=self.initial_data.get('weather', "clear"))
        weather_combo = ttk.Combobox(main_frame, textvariable=self.weather_var, width=27)
        weather_combo['values'] = ('clear', 'partly_cloudy', 'cloudy', 'rain', 'heavy_rain', 'snow', 'fog', 'windy', 'storm')
        weather_combo.grid(row=2, column=1, pady=2)

        ttk.Label(main_frame, text="Temperature (°C):").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.temp_var = tk.StringVar(value=format_number(self.initial_data.get('temperature', 22.0)))
        ttk.Entry(main_frame, textvariable=self.temp_var, width=30).grid(row=3, column=1, pady=2)

        ttk.Label(main_frame, text="Humidity (%):").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.humidity_var = tk.StringVar(value=format_number(self.initial_data.get('humidity', 50.0)))
        ttk.Entry(main_frame, textvariable=self.humidity_var, width=30).grid(row=4, column=1, pady=2)

        ttk.Label(main_frame, text="Wind Speed:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.wind_speed_var = tk.StringVar(value=format_number(self.initial_data.get('wind_speed', 5.0)))
        ttk.Entry(main_frame, textvariable=self.wind_speed_var, width=30).grid(row=5, column=1, pady=2)

        ttk.Label(main_frame, text="Wind Direction:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.wind_dir_var = tk.StringVar(value=self.initial_data.get('wind_direction', "north"))
        wind_combo = ttk.Combobox(main_frame, textvariable=self.wind_dir_var, width=27)
        wind_combo['values'] = ('north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest')
        wind_combo.grid(row=6, column=1, pady=2)

        ttk.Label(main_frame, text="Visibility (m):").grid(row=7, column=0, sticky=tk.W, pady=2)
        self.visibility_var = tk.StringVar(value=format_number(self.initial_data.get('visibility', 10000.0)))
        ttk.Entry(main_frame, textvariable=self.visibility_var, width=30).grid(row=7, column=1, pady=2)

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=8, column=0, columnspan=2, pady=20)

        button_text = "Save Changes" if self.edit_mode else "Create"
        ok_button = ttk.Button(button_frame, text=button_text, command=self.ok_clicked)
        ok_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.LEFT, padx=5)

        # Set focus on OK button
        ok_button.focus_set()
    
    def ok_clicked(self):
        try:
            self.result = {
                "name": self.name_var.get(),
                "description": self.desc_var.get(),
                "weather": self.weather_var.get(),
                "temperature": float(self.temp_var.get()),
                "humidity": float(self.humidity_var.get()),
                "wind_speed": float(self.wind_speed_var.get()),
                "wind_direction": self.wind_dir_var.get(),
                "visibility": float(self.visibility_var.get())
            }
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric values")
    
    def cancel_clicked(self):
        self.dialog.destroy()

class RealtimeControlDialog:
    """Dialog for real-time drone control"""
    def __init__(self, parent, drone_id, controller):
        self.drone_id = drone_id
        self.controller = controller
        self.parent = parent
        self.manual_editing = False  # Track if user is manually editing position fields
        self.edit_reset_timer = None  # Track delayed reset callback
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Real-time Control - Drone {drone_id}")
        # Make the panel longer for better visibility
        set_window_geometry_and_center(self.dialog, 400, 720, parent)
        
        # Create widgets
        self.create_widgets()

        # Load initial status (one-time, no automatic refresh)
        self.refresh_status()

        # Wait for dialog to close
        self.dialog.wait_window()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Drone status section with refresh button
        self.status_frame = ttk.LabelFrame(main_frame, text="Drone Status")
        self.status_frame.pack(fill=tk.X, pady=(0, 3))

        # Add refresh button for manual status updates
        refresh_btn_frame = ttk.Frame(self.status_frame)
        refresh_btn_frame.pack(fill=tk.X, padx=5, pady=(3, 0))
        ttk.Button(refresh_btn_frame, text="🔄 Refresh Status", command=self.refresh_status, width=20).pack(side=tk.LEFT)

        # Increase height to accommodate extra status lines (heading, height)
        self.status_text = tk.Text(self.status_frame, height=6, state=tk.DISABLED)
        self.status_text.pack(fill=tk.X, padx=5, pady=3)

        # Nearby info section
        nearby_frame = ttk.LabelFrame(main_frame, text="Nearby")
        nearby_frame.pack(fill=tk.X, pady=(0, 3))
        self.nearby_text = tk.Text(nearby_frame, height=5, state=tk.DISABLED)
        self.nearby_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Basic controls section
        basic_frame = ttk.LabelFrame(main_frame, text="Basic Controls")
        basic_frame.pack(fill=tk.X, pady=(0, 2))
        
        # First line of basic controls
        basic_buttons_frame = ttk.Frame(basic_frame)
        basic_buttons_frame.pack(pady=2)
        
        ttk.Button(basic_buttons_frame, text="Take Off", command=self.takeoff, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(basic_buttons_frame, text="Land", command=self.land, width=12).pack(side=tk.LEFT, padx=5)
        
        # Second line of basic controls
        basic_buttons_frame2 = ttk.Frame(basic_frame)
        basic_buttons_frame2.pack(pady=2)
        
        ttk.Button(basic_buttons_frame2, text="Charge", command=self.charge, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(basic_buttons_frame2, text="Return Home", command=self.return_home, width=12).pack(side=tk.LEFT, padx=5)
        
        # Movement controls section
        movement_frame = ttk.LabelFrame(main_frame, text="Movement Controls")
        movement_frame.pack(fill=tk.X, pady=(0, 2))
        
        # Movement distance setting
        distance_frame = ttk.Frame(movement_frame)
        distance_frame.pack(pady=2)
        
        ttk.Label(distance_frame, text="Movement Distance (m):").pack(side=tk.LEFT)
        self.distance_var = tk.StringVar(value="1.0")
        ttk.Entry(distance_frame, textvariable=self.distance_var, width=8).pack(side=tk.LEFT, padx=5)
        
        # 3x3 Directional movement buttons grid
        direction_frame = ttk.Frame(movement_frame)
        direction_frame.pack(pady=2)
        
        # Configure grid weights for centering
        for i in range(3):
            direction_frame.grid_columnconfigure(i, weight=1)
            direction_frame.grid_rowconfigure(i, weight=1)
        
        # Store button references to enable/disable based on drone status
        self.movement_buttons = []

        # Row 0: Up, Forward, Down
        btn_up = ttk.Button(direction_frame, text="↑ Up", command=self.move_up, width=10)
        btn_up.grid(row=0, column=0, padx=5, pady=5)
        self.movement_buttons.append(btn_up)

        btn_forward = ttk.Button(direction_frame, text="↑ Forward", command=self.move_forward, width=10)
        btn_forward.grid(row=0, column=1, padx=5, pady=5)
        self.movement_buttons.append(btn_forward)

        btn_down = ttk.Button(direction_frame, text="↓ Down", command=self.move_down, width=10)
        btn_down.grid(row=0, column=2, padx=5, pady=5)
        self.movement_buttons.append(btn_down)

        # Row 1: Left, Blank, Right
        btn_left = ttk.Button(direction_frame, text="← Left", command=self.move_left, width=10)
        btn_left.grid(row=1, column=0, padx=5, pady=5)
        self.movement_buttons.append(btn_left)

        # Middle position intentionally left blank

        btn_right = ttk.Button(direction_frame, text="→ Right", command=self.move_right, width=10)
        btn_right.grid(row=1, column=2, padx=5, pady=5)
        self.movement_buttons.append(btn_right)

        # Row 2: Blank, Backward, Blank
        # Left and right positions intentionally left blank
        btn_backward = ttk.Button(direction_frame, text="↓ Backward", command=self.move_backward, width=10)
        btn_backward.grid(row=2, column=1, padx=5, pady=5)
        self.movement_buttons.append(btn_backward)
        
        # Manual position control
        manual_frame = ttk.LabelFrame(main_frame, text="Manual Position Control")
        manual_frame.pack(fill=tk.X, pady=(0, 10))
        
        pos_frame = ttk.Frame(manual_frame)
        pos_frame.pack(pady=5)
        
        ttk.Label(pos_frame, text="X:").grid(row=0, column=0, padx=2)
        self.x_var = tk.StringVar(value="0.0")
        self.x_entry = ttk.Entry(pos_frame, textvariable=self.x_var, width=8)
        self.x_entry.grid(row=0, column=1, padx=2)
        self.x_entry.bind('<FocusIn>', self.on_manual_edit_start)
        self.x_entry.bind('<FocusOut>', self.on_manual_edit_end)
        self.x_entry.bind('<KeyPress>', self.on_manual_edit_keypress)
        
        ttk.Label(pos_frame, text="Y:").grid(row=0, column=2, padx=2)
        self.y_var = tk.StringVar(value="0.0")
        self.y_entry = ttk.Entry(pos_frame, textvariable=self.y_var, width=8)
        self.y_entry.grid(row=0, column=3, padx=2)
        self.y_entry.bind('<FocusIn>', self.on_manual_edit_start)
        self.y_entry.bind('<FocusOut>', self.on_manual_edit_end)
        self.y_entry.bind('<KeyPress>', self.on_manual_edit_keypress)
        
        ttk.Label(pos_frame, text="Z:").grid(row=0, column=4, padx=2)
        self.z_var = tk.StringVar(value="10.0")
        self.z_entry = ttk.Entry(pos_frame, textvariable=self.z_var, width=8)
        self.z_entry.grid(row=0, column=5, padx=2)
        self.z_entry.bind('<FocusIn>', self.on_manual_edit_start)
        self.z_entry.bind('<FocusOut>', self.on_manual_edit_end)
        self.z_entry.bind('<KeyPress>', self.on_manual_edit_keypress)
        
        self.move_to_position_btn = ttk.Button(manual_frame, text="Move to Position", command=self.move_to_position)
        self.move_to_position_btn.pack(pady=5)

        # Close button
        ttk.Button(main_frame, text="Close", command=self.close_dialog).pack(pady=10)

        # Track keyboard binding state
        self.keyboard_bindings_active = False

        # Keyboard bindings will be enabled/disabled dynamically based on drone status
        # Initial binding state will be set after first status refresh
    
    def on_manual_edit_start(self, event):
        """Called when user starts editing position fields"""
        self.manual_editing = True
        # Cancel any pending reset
        if self.edit_reset_timer is not None:
            self.dialog.after_cancel(self.edit_reset_timer)
    
    def on_manual_edit_end(self, event):
        """Called when user stops editing position fields"""
        # Delay resetting manual_editing to allow for quick re-focus
        self.edit_reset_timer = self.dialog.after(1000, self.reset_manual_editing)
    
    def on_manual_edit_keypress(self, event):
        """Called when user types in position fields"""
        self.manual_editing = True
        # Cancel any pending reset since user is actively typing
        if self.edit_reset_timer is not None:
            self.dialog.after_cancel(self.edit_reset_timer)
    
    def reset_manual_editing(self):
        """Reset manual editing flag after delay"""
        self.manual_editing = False
    
    def enable_keyboard_bindings(self):
        """Enable keyboard bindings for movement controls"""
        if not self.keyboard_bindings_active:
            # Bind movement keys
            self.dialog.bind('<Left>', lambda e: self.move_left())  # Left arrow -> move left
            self.dialog.bind('<Right>', lambda e: self.move_right())  # Right arrow -> move right
            self.dialog.bind('<Up>', lambda e: self.move_forward())  # Up arrow -> move forward
            self.dialog.bind('<Down>', lambda e: self.move_backward())  # Down arrow -> move backward
            self.dialog.bind('<apostrophe>', lambda e: self.move_up())  # ' key -> move up
            self.dialog.bind('<slash>', lambda e: self.move_down())  # / key -> move down
            self.keyboard_bindings_active = True

    def disable_keyboard_bindings(self):
        """Disable keyboard bindings for movement controls"""
        if self.keyboard_bindings_active:
            # Unbind movement keys
            self.dialog.unbind('<Left>')
            self.dialog.unbind('<Right>')
            self.dialog.unbind('<Up>')
            self.dialog.unbind('<Down>')
            self.dialog.unbind('<apostrophe>')
            self.dialog.unbind('<slash>')
            self.keyboard_bindings_active = False
    
    def update_movement_controls_state(self, drone_status):
        """Enable or disable movement controls based on drone status"""
        # Only enable movement controls when drone is hovering
        is_hovering = drone_status.lower() == 'hovering'

        # Enable/disable directional movement buttons
        state = 'normal' if is_hovering else 'disabled'
        for btn in self.movement_buttons:
            btn.config(state=state)

        # Enable/disable manual position control button
        self.move_to_position_btn.config(state=state)

        # Enable/disable keyboard shortcuts based on drone status
        if is_hovering:
            self.enable_keyboard_bindings()
        else:
            self.disable_keyboard_bindings()

    def close_dialog(self):
        """Clean up and close the dialog"""
        # Close the dialog
        self.dialog.destroy()
    
    def refresh_status(self):
        """Manually refresh drone status display (called by user or after commands)"""
        try:
            drone_data = self.controller.api_server.api_get_drone(self.drone_id)
            if drone_data:
                status = drone_data.get('status', 'unknown')
                battery = drone_data.get('battery_level', 0)
                speed = drone_data.get('speed', 0.0)
                direction = drone_data.get('heading')
                pos = drone_data.get('position', {})
                x, y, z = pos.get('x', 0), pos.get('y', 0), pos.get('z', 0)
                # Altitude/height: prefer explicit field, else use Z from position
                height = drone_data.get('altitude', z)

                # Get the actual last_updated timestamp from server data
                last_updated = drone_data.get('last_updated')
                last_updated_str = datetime.fromtimestamp(last_updated).strftime('%H:%M:%S')

                self.status_frame.config(text="Drone Status")

                status_text = f"Status: {status}\n"
                status_text += f"Battery: {format_number(battery)}%\n"
                status_text += f"Position: ({format_number(x)}, {format_number(y)}, {format_number(z)})\n"
                # Add Height line after Position
                try:
                    status_text += f"Height: {format_number(float(height))} m\n"
                except Exception:
                    status_text += f"Height: {height} m\n"
                if direction is not None:
                    try:
                        status_text += f"Heading: {format_number(float(direction))}°\n"
                    except Exception:
                        # If formatting fails, show raw value
                        status_text += f"Heading: {direction}\n"
                status_text += f"Last Updated: {last_updated_str}"

                self.status_text.config(state=tk.NORMAL)
                self.status_text.delete(1.0, tk.END)
                self.status_text.insert(tk.END, status_text)
                self.status_text.config(state=tk.DISABLED)

                # Update manual position fields with current position only if not being edited
                if not self.manual_editing:
                    self.x_var.set(format_number(x))
                    self.y_var.set(format_number(y))
                    self.z_var.set(format_number(z))

                # Enable/disable movement controls based on drone status
                self.update_movement_controls_state(status)

                # Keep the main Drones tab in sync while this dialog is open
                # Pass the drone_data we already fetched to avoid duplicate API call
                try:
                    self.controller.update_drone_list_item(self.drone_id, drone_data)
                except Exception as e:
                    self.controller.logger.debug(f"Skip Drones tab sync: {e}")

                # Update nearby information
                try:
                    self.update_nearby_info(x, y, z)
                except Exception as ne:
                    self.controller.logger.debug(f"Nearby info update skipped: {ne}")

        except Exception as e:
            self.controller.logger.error(f"Error refreshing drone status: {e}")

    def update_nearby_info(self, x: float, y: float, z: float):
        """Fetch and display nearby entities around the drone.

        Uses the aggregated endpoint per latest API docs: GET /drones/{id}/nearby
        """
        nearby = self.controller.api_server.api_get_nearby_drones(self.drone_id)
        if nearby:
            targets = nearby.get('targets', []) or []
            drones = nearby.get('drones', []) or []
            obstacles = nearby.get('obstacles', []) or []

            def nearest_text(items):
                if items:
                    item = min(items, key=lambda i: i.get('distance', float('inf')))
                    name = item.get('name') or item.get('id', '-')
                    dist = item.get('distance', 0.0)
                    return f"{name} - {format_number(dist)} m"
                return "None"

            text = (
                f"Nearest target: {nearest_text(targets)}\n"
                f"Nearby drones: {len(drones)}\n"
                f"Nearest obstacle: {nearest_text(obstacles)}\n"
            )
            self.nearby_text.config(state=tk.NORMAL)
            self.nearby_text.delete(1.0, tk.END)
            self.nearby_text.insert(tk.END, text)
            self.nearby_text.config(state=tk.DISABLED)
    
    def send_command(self, command, parameters):
        """Send command to drone"""
        command_data = {
            'command': command,
            'parameters': parameters
        }
        result = self.controller.api_server.api_send_drone_command(self.drone_id, command_data)
        if result:
            self.controller.logger.info(f"Command {command} sent to drone {self.drone_id}")
            # Update status after command execution
            self.dialog.after(500, self.refresh_status)
        return result
    
    def takeoff(self):
        """Take off drone"""
        # Create a custom dialog instead of using simpledialog.askfloat
        takeoff_dialog = tk.Toplevel(self.dialog)
        takeoff_dialog.title("Take Off")
        set_window_geometry_and_center(takeoff_dialog, 300, 150, self.dialog)
        
        # Create dialog contents
        frame = ttk.Frame(takeoff_dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Enter altitude (meters):").pack(pady=(0, 10))
        
        altitude_var = tk.StringVar(value=format_number(10.0))
        altitude_entry = ttk.Spinbox(
            frame, 
            from_=1.0, 
            to=120.0, 
            textvariable=altitude_var, 
            width=10,
            increment=0.5
        )
        altitude_entry.pack(pady=(0, 20))
        
        # Result variable
        result = [None]
        
        def on_ok():
            try:
                value = float(altitude_var.get())
                if 1.0 <= value <= 120.0:
                    result[0] = value
                    takeoff_dialog.destroy()
                else:
                    messagebox.showerror("Invalid Value", "Altitude must be between 1.0 and 120.0 meters")
            except ValueError:
                messagebox.showerror("Invalid Value", "Please enter a valid number")
        
        def on_cancel():
            takeoff_dialog.destroy()
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.RIGHT)
        
        # Set focus to entry and select all text for easy editing
        altitude_entry.focus_set()
        altitude_entry.selection_range(0, 'end')
        
        # Bind Enter key to OK button
        takeoff_dialog.bind('<Return>', lambda event: on_ok())
        
        # Wait for dialog to close
        self.dialog.wait_window(takeoff_dialog)
        
        # Process result
        if result[0] is not None:
            self.send_command('take_off', {'altitude': result[0]})
    
    def land(self):
        """Land drone"""
        self.send_command('land', {})
    
    def emergency(self):
        """Emergency landing"""
        if messagebox.askyesno("Emergency", "Execute emergency landing?"):
            self.send_command('emergency', {})
    
    def charge(self):
        """Charge drone battery"""
        # Use the dedicated charge command endpoint with charge_amount parameter
        result = self.controller.api_server.api_charge_drone(self.drone_id)
        if result:
            self.controller.logger.info(f"Charge command sent to drone {self.drone_id}")
            # Update status after command execution
            self.dialog.after(500, self.refresh_status)
        return result
    
    def return_home(self):
        """Return drone to home position"""
        # Use the dedicated return_home command endpoint
        result = self.controller.api_server.api_return_drone_home(self.drone_id)
        if result:
            self.controller.logger.info(f"Return home command sent to drone {self.drone_id}")
            # Update status after command execution
            self.dialog.after(500, self.refresh_status)
        return result
    
    def get_movement_distance(self):
        """Get movement distance from input"""
        try:
            return float(self.distance_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid movement distance")
            return None
    
    def get_current_position(self):
        """Get current drone position from UI fields (no API call needed)"""
        try:
            # Get position from the UI fields which are kept up-to-date by refresh_status
            x = float(self.x_var.get())
            y = float(self.y_var.get())
            z = float(self.z_var.get())
            return x, y, z
        except (ValueError, AttributeError) as e:
            self.controller.logger.error(f"Error getting position from UI fields: {e}")
            return 0, 0, 0
    
    def move_up(self):
        """Move drone up"""
        distance = self.get_movement_distance()
        if distance is not None:
            x, y, z = self.get_current_position()
            self.send_command('move_to', {'x': x, 'y': y, 'z': z + distance})
    
    def move_down(self):
        """Move drone down"""
        distance = self.get_movement_distance()
        if distance is not None:
            x, y, z = self.get_current_position()
            self.send_command('move_to', {'x': x, 'y': y, 'z': max(0, z - distance)})
    
    def move_forward(self):
        """Move drone forward (positive Y)"""
        distance = self.get_movement_distance()
        if distance is not None:
            x, y, z = self.get_current_position()
            self.send_command('move_to', {'x': x, 'y': y + distance, 'z': z})
    
    def move_backward(self):
        """Move drone backward (negative Y)"""
        distance = self.get_movement_distance()
        if distance is not None:
            x, y, z = self.get_current_position()
            self.send_command('move_to', {'x': x, 'y': y - distance, 'z': z})
    
    def move_left(self):
        """Move drone left (negative X)"""
        distance = self.get_movement_distance()
        if distance is not None:
            x, y, z = self.get_current_position()
            self.send_command('move_to', {'x': x - distance, 'y': y, 'z': z})
    
    def move_right(self):
        """Move drone right (positive X)"""
        distance = self.get_movement_distance()
        if distance is not None:
            x, y, z = self.get_current_position()
            self.send_command('move_to', {'x': x + distance, 'y': y, 'z': z})
    
    def move_to_position(self):
        """Move drone to specified position"""
        try:
            x = float(self.x_var.get())
            y = float(self.y_var.get())
            z = float(self.z_var.get())
            
            # Reset manual editing flag after successful command
            result = self.send_command('move_to', {'x': x, 'y': y, 'z': z})
            if result:
                # Allow position fields to be updated after command execution
                self.manual_editing = False
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values for position")


class DetailDialog:
    """Dialog for showing detailed information about items"""
    def __init__(self, parent, title, data, controller):
        self.controller = controller
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        set_window_geometry_and_center(self.dialog, 500, 400, parent)
        if self.controller:
            self.controller.disable_global_shortcuts()

        # Bind close event to reset active dialog
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
        self.dialog.bind("<Escape>", lambda event: self.on_close())
        self.dialog.bind("<space>", self._handle_space_close)

        # Store navigation info (current tab and listbox)
        self.current_tab = None
        self.current_listbox = None
        self.current_index = None
        self._determine_current_context()

        # Note: Arrow key navigation is handled by DetailPanel internally
        # via the on_prev_item/on_next_item callbacks

        self.create_widgets(data)
        # Remove wait_window() to prevent blocking

    def _get_tab_config_map(self):
        """Get the mapping of tab names to their configuration"""
        return {
            "Drones": {
                "listbox": "drone_listbox",
                "get_id": self.controller.get_selected_drone_id,
                "get_data": self.controller.api_server.api_get_drone,
                "title": "Drone Details",
                "requires_session": False
            },
            "Targets": {
                "listbox": "target_listbox",
                "get_id": self.controller.get_selected_target_id,
                "get_data": self.controller.api_server.api_get_target,
                "title": "Target Details",
                "requires_session": False
            },
            "Obstacles": {
                "listbox": "obstacles_listbox",
                "get_id": self.controller.get_selected_obstacle_id,
                "get_data": self.controller.api_server.api_get_obstacle,
                "title": "Obstacle Details",
                "requires_session": False
            },
            "Environment": {
                "listbox": "env_listbox",
                "get_id": self.controller.get_selected_environment_id,
                "get_data": self.controller.api_server.api_get_environment,
                "title": "Environment Details",
                "requires_session": False
            },
            "Tasks": {
                "listbox": "task_listbox",
                "get_id": self.controller.get_selected_task_id,
                "get_data": self.controller.api_server.api_get_session_task,
                "title": "Task Details",
                "requires_session": True
            },
        }

    def _determine_current_context(self):
        """Determine which tab and listbox are currently active"""
        if not self.controller:
            return

        notebook = getattr(self.controller, 'notebook', None)
        if not notebook or not notebook.winfo_exists():
            return

        try:
            current_tab = notebook.select()
            if not current_tab:
                return
            tab_text = notebook.tab(current_tab, "text")
        except tk.TclError:
            return

        # Get tab configuration map
        tab_listbox_map = self._get_tab_config_map()

        if tab_text in tab_listbox_map:
            tab_info = tab_listbox_map[tab_text]
            self.current_tab = tab_text
            self.current_listbox = getattr(self.controller, tab_info["listbox"], None)
            self.get_id_func = tab_info["get_id"]
            self.get_data_func = tab_info["get_data"]
            self.detail_title = tab_info["title"]
            self.requires_session = tab_info["requires_session"]

            # Get current selection index
            if self.current_listbox:
                selection = self.current_listbox.curselection()
                if selection:
                    self.current_index = selection[0]

    def navigate_previous(self, event=None):
        """Navigate to the previous item in the list"""
        if not self.current_listbox or self.current_index is None:
            return

        # Check if there's a previous item
        if self.current_index > 0:
            new_index = self.current_index - 1
            self._navigate_to_index(new_index)

    def navigate_next(self, event=None):
        """Navigate to the next item in the list"""
        if not self.current_listbox or self.current_index is None:
            return

        # Check if there's a next item
        listbox_size = self.current_listbox.size()
        if self.current_index < listbox_size - 1:
            new_index = self.current_index + 1
            self._navigate_to_index(new_index)

    def _navigate_to_index(self, new_index):
        """Navigate to a specific index in the listbox"""
        # Update the listbox selection
        self.current_listbox.selection_clear(0, tk.END)
        self.current_listbox.selection_set(new_index)
        self.current_listbox.see(new_index)
        self.current_listbox.activate(new_index)

        # Update current index
        self.current_index = new_index

        # Fetch new data for the selected item
        if hasattr(self, 'get_id_func') and hasattr(self, 'get_data_func'):
            item_id = self.get_id_func()
            if item_id:
                # Handle tasks which require session_id parameter
                if hasattr(self, 'requires_session') and self.requires_session:
                    session_id = self.controller.get_current_session_id()
                    if session_id:
                        new_data = self.get_data_func(session_id, item_id)
                    else:
                        return  # Can't fetch task data without session_id
                else:
                    new_data = self.get_data_func(item_id)

                if new_data:
                    # Update dialog title
                    if hasattr(self, 'detail_title'):
                        self.dialog.title(self.detail_title)

                    # Update the displayed data without closing the dialog
                    self.display_data(new_data)
    
    def on_close(self):
        """Handle dialog close event"""
        if self.controller:
            self.controller.active_detail_dialog = None
        self.dialog.destroy()
        if self.controller:
            self.controller.root.after(0, self.controller._maybe_enable_global_shortcuts)
    
    def destroy(self):
        """Destroy the dialog"""
        self.on_close()
    
    def create_widgets(self, data):
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create DetailPanel widget with navigation callbacks
        # Pass navigation callbacks if we have a valid navigation context
        prev_callback = self.navigate_previous if self.current_listbox else None
        next_callback = self.navigate_next if self.current_listbox else None

        self.detail_panel = DetailPanel(
            main_frame,
            data=data,
            view_raw_data_title=f"{self.dialog.title()} - Raw Data",
            on_close=self.on_close,
            on_prev_item=prev_callback,
            on_next_item=next_callback
        )
        self.detail_panel.pack(fill=tk.BOTH, expand=True)

    def _handle_space_close(self, event):
        """Close on space unless focus is in a text input."""
        focus_widget = self.dialog.focus_get()
        if focus_widget is not None:
            widget_class = focus_widget.winfo_class()
            if widget_class in ("Entry", "TEntry", "Text", "TCombobox"):
                return
        self.on_close()
        return "break"
    
    def display_data(self, data):
        """Load new data into the DetailPanel"""
        if hasattr(self, 'detail_panel'):
            self.detail_panel.load_data(data)
