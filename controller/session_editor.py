#!/usr/bin/env python3
"""
MultiUAV-Plat Control System - Session Editor

Interactive visual editor for editing session items (drones, targets, obstacles).
Supports drag-and-drop, double-click editing, pan/zoom, and more.

Author: MultiUAV-Plat Control System
Version: Provided by application entrypoint
"""

import warnings

warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API.*",
    category=UserWarning,
    module="pygame.pkgdata",
)

import pygame
import math
from api_server import APIServer
import os
import time
import json
import signal
import threading
import subprocess
import ctypes
import tkinter as tk
import uuid
from tkinter import simpledialog
from typing import Dict, List, Tuple, Optional, Any
from copy import deepcopy
import logging
import platform
from utils import set_window_geometry_and_center


# Dialogs for attribute editing and adding
from session_editor_dialogs import (
    AttributeEditorDialog,
    DroneEditorDialog,
    TargetEditorDialog,
    ObstacleEditorDialog,
    AddDroneDialog,
    AddTargetDialog,
    AddObstacleDialog
)


from utils import (
    setup_shared_logger,
    extract_session_metadata,
    normalize_session_canvas_fields,
    save_session_to_file,
    format_number,
    format_enum_value,
    distance_point_to_point,
    is_point_in_circle,
    is_point_in_ellipse,
    is_point_in_polygon,
    get_polygon_bounds,
    get_polygon_center,
    get_polygon_centroid,
    create_new_name,
    clamp,
    distance_point_to_line,
    snap_value_to_grid,
    snap_to_grid
)

# ============================================================================
# Session editor helpers (formerly in utils.py)
# ============================================================================

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800

UI_RADIUS_MIN = 5  # Minimum radius for displaying items in the editor (even if actual radius is smaller)

# UI colors
BG_COLOR = (245, 245, 250)
GRID_COLOR = (220, 225, 230)
TEXT_COLOR = (30, 30, 30)
WHITE = (255, 255, 255)
TEXT_DISABLED = (120, 120, 120)

STATUS_OK = (0, 255, 0)
STATUS_WARN = (255, 165, 0)
STATUS_ERROR = (255, 0, 0)
CYAN = (0, 255, 255)
GRAY = (128, 128, 128)

BUTTON_BG = (235, 235, 240)
BUTTON_BORDER = (200, 200, 210)
ACTIVE_BUTTON_BG = (220, 245, 220)
ACTIVE_BUTTON_BORDER = (190, 220, 190)
DISABLED_BUTTON_BG = (230, 230, 230)
DISABLED_BUTTON_BORDER = (200, 200, 200)
HOVER_BUTTON_BG = (225, 235, 245)

CANVAS_BUTTON_BG = (235, 235, 240)
CANVAS_BUTTON_BORDER = (200, 200, 210)
SLIDER_TRACK = (230, 230, 230)
SLIDER_BORDER = (200, 200, 210)
SLIDER_HANDLE = (180, 180, 180)
SLIDER_HANDLE_BORDER = (120, 120, 120)

PANEL_BG = (235, 235, 240)
PANEL_BORDER = (200, 200, 210)
STATUS_BAR_BG = (235, 235, 240)
TOOLBAR_BG = (240, 240, 245)

SELECT_BORDER = (0, 120, 255)
SELECT_FILL = (0, 120, 255, 80)

DRAG_COLOR = (100, 150, 255)
DRAG_GHOST = (100, 150, 255, 128)

DRONE_COLORS = {
    "idle": (100, 100, 100),
    "ready": (0, 255, 0),
    "taking_off": (0, 255, 255),
    "flying": (0, 0, 255),
    "moving": (255, 165, 0),
    "hovering": (0, 255, 255),
    "landing": (255, 255, 0),
    "emergency": (255, 0, 0),
    "offline": (50, 50, 50)
}

TARGET_COLORS = {
    "fixed": (255, 200, 0),
    "moving": (255, 100, 100),
    "waypoint": (0, 255, 100),
    "circle": (0, 100, 255),
    "polygon": (0, 200, 255)
}

OBSTACLE_COLORS = {
    "point": (60, 60, 60),
    "circle": (139, 69, 19),
    "ellipse": (82, 82, 122),
    "polygon": (105, 105, 105),
}

class CoordinateTransform:
    """Handle world-to-screen and screen-to-world coordinate transformations."""
    def __init__(self, margin_x: int = 60, margin_y: int = 80):
        self.margin_x = margin_x
        self.margin_y = margin_y
        self.lower_left_corner = (0.0, 0.0)
        self.map_scale = 1.0

    def world_to_screen(self, x: float, y: float) -> Tuple[int, int]:
        screen_x = int(self.margin_x + (x - self.lower_left_corner[0]) * self.map_scale)
        screen_y = int(SCREEN_HEIGHT - self.margin_y - (y - self.lower_left_corner[1]) * self.map_scale)
        return screen_x, screen_y

    def screen_to_world(self, screen_x: int, screen_y: int) -> Tuple[float, float]:
        world_x = self.lower_left_corner[0] + (screen_x - self.margin_x) / self.map_scale
        world_y = self.lower_left_corner[1] + (SCREEN_HEIGHT - self.margin_y - screen_y) / self.map_scale
        return world_x, world_y

class SessionEditor:

    """Interactive session editor with pygame canvas"""

    _shared_tk_root = None
    _tk_root_lock = threading.Lock()

    @classmethod
    def _initialize_shared_tk_root(cls):
        """Create (if needed) and return the shared hidden Tk root"""
        if cls._shared_tk_root is not None:
            return cls._shared_tk_root

        with cls._tk_root_lock:
            if cls._shared_tk_root is not None:
                return cls._shared_tk_root
            try:
                root = tk.Tk()
                root.withdraw()
                root.update_idletasks()
                cls._shared_tk_root = root

                # Ensure attribute editor dialogs reuse this root instead of making new ones
                try:
                    AttributeEditorDialog._root = root
                except Exception:
                    pass
            except Exception as exc:
                logging.getLogger('SessionEditor').warning(
                    "Failed to initialize shared Tk root: %s", exc
                )
                cls._shared_tk_root = None

        return cls._shared_tk_root

    def _get_tk_root(self):
        """Return shared Tk root (initializing if necessary)"""
        if SessionEditor._shared_tk_root is None:
            self._owns_tk_root = True
        root = SessionEditor._initialize_shared_tk_root()
        self.tk_root = root
        return root

    def _prepare_tk_dialog(self):
        """Ensure Tk root exists and refresh it before showing a dialog"""
        root = self._get_tk_root()
        if root:
            try:
                root.update_idletasks()
                root.withdraw()
            except tk.TclError:
                pass
        return root

    def _reset_mouse_state(self):
        """Clear mouse/drag state so stray events after dialogs don't start panning."""
        self.mouse_down_pos = None
        self.dragging_canvas = False
        self.dragging_slider = False
        try:
            pygame.event.clear([pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION])
        except Exception:
            try:
                pygame.event.clear()
            except Exception:
                pass

    def _has_open_tk_dialog(self) -> bool:
        """Return True when any visible Tk dialog is open."""
        root = getattr(self, 'tk_root', None)
        if not root:
            return False
        try:
            for child in root.winfo_children():
                if isinstance(child, tk.Toplevel):
                    try:
                        if child.winfo_exists() and child.winfo_viewable():
                            return True
                    except tk.TclError:
                        continue
        except tk.TclError:
            return False
        return False

    def _show_info_dialog(self, title: str, message: str):
        """Display an informational dialog without exposing the Tk root."""
        self._show_modal_alert(title or "Info", message or "", kind='info')

    def _show_error_dialog(self, title: str, message: str):
        """Display an error dialog without exposing the Tk root."""
        self._show_modal_alert(title or "Error", message or "", kind='error')

    def _show_modal_alert(self, title: str, message: str, kind: str = 'info'):
        """Generic modal alert dialog (OK button)."""
        root = self._prepare_tk_dialog()
        if not root:
            if getattr(self, 'logger', None):
                log_fn = self.logger.error if kind == 'error' else self.logger.info
                log_fn("%s - %s", title, message)
            return

        dialog = tk.Toplevel(root)
        dialog.title(title)
        dialog.resizable(False, False)
        if title == "No Changes":
            dialog_width, dialog_height = 300, 100
        else:
            dialog_width, dialog_height = 440, 240
        set_window_geometry_and_center(
            dialog,
            dialog_width,
            dialog_height,
            None,
            make_transient=False,
            align_to_pointer=True,
            bring_to_front=True
        )

        color_map = {
            'info': '#1d4ed8',
            'success': '#15803d',
            'error': '#b91c1c',
            'warning': '#b45309'
        }
        fg_color = color_map.get(kind, '#1f2937')

        container = tk.Frame(dialog, padx=20, pady=15)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text=message, justify=tk.LEFT, wraplength=450,
                 fg=fg_color).pack(fill=tk.X)

        button = tk.Button(container, text="OK", width=10, command=dialog.destroy)
        button.pack(pady=(15, 0))

        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.attributes('-topmost', True)
        dialog.update_idletasks()
        dialog.deiconify()
        dialog.grab_set()
        dialog.lift()
        button.focus_set()

        while True:
            try:
                if not dialog.winfo_exists():
                    break
                dialog.update()
                pygame.time.wait(10)
            except tk.TclError:
                break

        try:
            root.withdraw()
        except tk.TclError:
            pass
        self._reset_mouse_state()

    def _ask_yes_no_dialog(self, title: str, message: str, default: bool = False) -> bool:
        """Show Yes/No confirmation dialog using custom modal window."""
        root = self._prepare_tk_dialog()
        if not root:
            if getattr(self, 'logger', None):
                self.logger.warning("Cannot display confirmation dialog '%s'; defaulting to %s", title, default)
            return default

        dialog = tk.Toplevel(root)
        dialog.title(title or "Confirm")
        dialog.resizable(False, False)
        set_window_geometry_and_center(
            dialog,
            420,
            160,
            None,
            make_transient=False,
            align_to_pointer=True,
            bring_to_front=True
        )

        result = {'value': default}

        container = tk.Frame(dialog, padx=20, pady=15)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text=message or "", justify=tk.LEFT, wraplength=450).pack(fill=tk.X)

        button_frame = tk.Frame(container)
        button_frame.pack(pady=(15, 0))

        def on_yes(event=None):
            result['value'] = True
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            dialog.destroy()

        def on_no(event=None):
            result['value'] = False
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            dialog.destroy()

        yes_btn = tk.Button(button_frame, text="Yes", width=10, command=on_yes)
        yes_btn.pack(side=tk.LEFT, padx=8)
        no_btn = tk.Button(button_frame, text="No", width=10, command=on_no)
        no_btn.pack(side=tk.LEFT, padx=8)

        dialog.protocol("WM_DELETE_WINDOW", on_no)
        dialog.attributes('-topmost', True)
        dialog.update_idletasks()
        dialog.deiconify()
        dialog.grab_set()
        dialog.lift()
        yes_btn.focus_set()

        while True:
            try:
                if not dialog.winfo_exists():
                    break
                dialog.update()
                pygame.time.wait(10)
            except tk.TclError:
                break

        try:
            root.withdraw()
        except tk.TclError:
            pass
        self._reset_mouse_state()

        return bool(result['value'])

    def _prompt_text_dialog(
        self,
        title: str,
        message: str,
        initialvalue: Optional[str] = None,
        *,
        force_custom: bool = False
    ) -> Optional[str]:
        """Prompt user for text input via a custom Tk dialog with manual event pumping."""
        embedded_root = getattr(self, '_embedded_default_root', None)
        embedded_visible = False
        if embedded_root is not None:
            try:
                embedded_visible = bool(embedded_root.winfo_viewable()) and embedded_root.state() != 'withdrawn'
            except Exception:
                embedded_visible = False
        if not force_custom and embedded_root is not None and embedded_visible:
            try:
                value = simpledialog.askstring(
                    title or "Input",
                    message or "",
                    initialvalue=initialvalue or "",
                    parent=embedded_root
                )
            except Exception as exc:
                if getattr(self, 'logger', None):
                    self.logger.warning(f"Embedded askstring failed: {exc}")
                return None
            if value is None:
                return None
            stripped = value.strip()
            cleaned = stripped or None
            self._reset_mouse_state()
            return cleaned

        root = self._prepare_tk_dialog()
        if not root:
            if getattr(self, 'logger', None):
                self.logger.warning("Cannot display text prompt '%s'; returning None", title)
            return None

        dialog = tk.Toplevel(root)
        dialog.title(title or "Input")
        dialog.resizable(False, False)
        set_window_geometry_and_center(
            dialog,
            300,
            150,
            None,
            make_transient=False,
            align_to_pointer=True,
            bring_to_front=True
        )
        

        result = {'value': None}

        content = tk.Frame(dialog, padx=20, pady=15)
        content.pack(fill=tk.BOTH, expand=True)

        tk.Label(content, text=message or "Enter value:", anchor=tk.W, justify=tk.LEFT).pack(fill=tk.X)

        initial_value = "" if initialvalue is None else str(initialvalue)
        entry_var = tk.StringVar(value=initial_value)
        entry = tk.Entry(content, textvariable=entry_var, width=40)
        entry.pack(fill=tk.X, pady=(10, 5))

        button_frame = tk.Frame(content)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        def on_ok(event=None):
            result['value'] = entry_var.get()
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            dialog.destroy()

        def on_cancel(event=None):
            result['value'] = None
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            dialog.destroy()

        tk.Button(button_frame, text="OK", width=10, command=on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", width=10, command=on_cancel).pack(side=tk.LEFT, padx=5)

        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        entry.bind("<Return>", on_ok)
        entry.bind("<Escape>", on_cancel)

        dialog.attributes('-topmost', True)
        dialog.update_idletasks()
        dialog.deiconify()
        dialog.grab_set()
        dialog.lift()
        entry.delete(0, tk.END)
        entry.insert(0, initial_value)
        entry.focus_set()
        entry.icursor(tk.END)

        while True:
            try:
                if not dialog.winfo_exists():
                    break
                dialog.update()
                pygame.time.wait(10)
            except tk.TclError:
                break

        try:
            root.withdraw()
        except tk.TclError:
            pass
        self._reset_mouse_state()

        value = result['value']
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    def _shutdown_tk_subsystem(self):
        """Close any remaining Tk dialogs and destroy the shared root safely."""
        # Cancel active dialog if one is present
        if getattr(self, 'active_dialog', None):
            dialog_wrapper = self.active_dialog
            dialog = dialog_wrapper.get('dialog')
            try:
                if dialog and hasattr(dialog, 'on_cancel'):
                    dialog.on_cancel()
            except Exception:
                pass
            self.active_dialog = None

        # Clean up shared root (which is also used by attribute dialogs)
        shared_root = SessionEditor._shared_tk_root
        if shared_root is not None and self._owns_tk_root:
            try:
                shared_root.update_idletasks()
                shared_root.withdraw()
                shared_root.destroy()
            except Exception as exc:
                if getattr(self, 'logger', None):
                    self.logger.warning(f"Error cleaning up Tk root: {exc}")
            finally:
                AttributeEditorDialog._root = None
                SessionEditor._shared_tk_root = None
                self.tk_root = None
                self._owns_tk_root = False

    def _bring_window_to_front(self):
        """Best-effort attempt to bring the pygame window to the foreground."""
        system = platform.system()

        if system == 'Darwin':
            try:
                cmd = f'tell application "System Events" to set frontmost of first process whose unix id is {os.getpid()} to true'
                subprocess.run(
                    ['osascript', '-e', cmd],
                    check=False,
                    capture_output=True,
                    timeout=1
                )
            except Exception as exc:
                if getattr(self, 'logger', None):
                    self.logger.debug("Unable to focus window via osascript: %s", exc)
        elif system == 'Windows':
            try:
                hwnd = pygame.display.get_wm_info().get('window')
                if hwnd:
                    user32 = ctypes.windll.user32
                    SW_SHOW = 5
                    user32.ShowWindow(hwnd, SW_SHOW)
                    user32.SetForegroundWindow(hwnd)
            except Exception as exc:
                if getattr(self, 'logger', None):
                    self.logger.debug("Unable to focus window via user32: %s", exc)
        else:
            # Other platforms usually honor SDL_RAISE automatically; nothing to do
            pass

    def __init__(self, session_id: str, session_data: Dict[str, Any], 
                 on_saved: Optional[callable] = None,
                 save_signal_file: Optional[str] = None):
        """Initialize session editor

        Args:
            session_id: Session ID to edit
            session_data: Initial session data
            on_saved: Optional callback function to call when session is saved
            save_signal_file: Optional path used to notify GUI controller about saves
        """
        self._embedded_default_root = getattr(tk, '_default_root', None)
        self.tk_root = None
        self._owns_tk_root = False
        self._get_tk_root()

        pygame.init()

        self.session_id = session_id
        normalized_metadata = extract_session_metadata(session_data)
        if normalized_metadata:
            self.session_data = normalized_metadata
        elif isinstance(session_data, dict):
            self.session_data = dict(session_data)
        else:
            self.session_data = {}

        if not self.session_data.get('name'):
            nested_session = self.session_data.get('session')
            if isinstance(nested_session, dict) and nested_session.get('name'):
                self.session_data['name'] = nested_session['name']
       
        self.on_saved = on_saved  # Callback to refresh GUI Controller when session is saved
        self.save_signal_file = save_signal_file

        # Logging
        self.logger = None
        self.setup_logging()
        
        self.api_server = APIServer(logger=self.logger, error_handler=self._show_error_dialog)

        # Note: Session manager already activated this session before launching editor
        # No need to call _activate_session() here to avoid redundant API calls

        # Window setup
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(f"MultiUAV-Plat Control System - Session Editor - {self.session_data.get('name', session_id)}")

        # Set window icon
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'img', 'editor.png')
            if os.path.exists(icon_path):
                icon = pygame.image.load(icon_path)
                pygame.display.set_icon(icon)
        except Exception as e:
            self.logger.warning("Could not load editor icon: %s", e)

        self._bring_window_to_front()

        self.clock = pygame.time.Clock()

        # Fonts
        self.font = pygame.font.SysFont('Arial', 14)
        self.small_font = pygame.font.SysFont('Arial', 11)
        self.title_font = pygame.font.SysFont('Arial', 18, bold=True)
        self.canvas_label_font = pygame.font.SysFont('Arial', 10)

        # Coordinate transformer
        self.transform = CoordinateTransform(margin_x=60, margin_y=80)

        # Data
        self.drones = []
        self.targets = []
        self.obstacles = []
        self.pending_deletions = []
        self.baseline_data = {
            'drones': [],
            'targets': [],
            'obstacles': []
        }
        self.load_data()

        # State
        self.running = True
        self.dirty = False  # Track unsaved changes
        self.snap_to_grid_enabled = False
        self.grid_size = 10.0  # meters

        # Zoom levels
        self.zoom_levels = [0.1, 0.3, 0.5, 0.7, 0.8, 1, 1.2, 1.5, 2, 3, 5, 10, 20, 50, 100]
        self.current_zoom_index = 5  # Start at 1.0
        self.transform.map_scale = self.zoom_levels[self.current_zoom_index]

        # Selection
        self.selected_item = None  # {'type': 'drone'|'target'|'obstacle', 'data': {...}}
        self.selected_item_world_pos = None  # (world_x, world_y) where the item was selected

        # Move mode (for moving items with M key/button)
        self.move_mode = False  # Whether in move mode
        self.move_mode_item = None  # Item being moved in move mode

        # Active attribute editor dialog (handled alongside pygame loop)
        self.active_dialog = None

        # Mouse interaction
        self.dragging_canvas = False
        self.dragging_slider = False
        self.last_mouse_pos = (0, 0)
        self.mouse_down_pos = None
        self.last_click_world_pos = None  # Track last click in world coordinates

        # Minimap
        self.minimap_visible = True
        self.last_minimap_click_time = 0
        self.minimap_double_click_threshold = 0.3  # seconds
        self._minimap_mini_rect = None
        self._minimap_content_rect = None

        # UI elements
        self.create_ui_elements()

        # Auto-fit view
        self.auto_fit_view()

        # Undo/Redo stacks
        self.undo_stack = []
        self.redo_stack = []

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown from parent process"""
        # Flag to track if shutdown was requested via signal
        self.signal_shutdown_requested = False

        def signal_handler(signum, frame):
            """Handle termination signal from parent process

            IMPORTANT: On macOS, we cannot create Tkinter dialogs in signal handlers
            because Cocoa requires GUI operations on the main thread. We just set a flag
            and let the main event loop handle it.
            """
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.signal_shutdown_requested = True
            # Don't post pygame.QUIT here - just set the flag
            # The main event loop will check this flag and handle shutdown

        # Register signal handlers (Unix/macOS and Windows compatible)
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            self.logger.info("Registered SIGTERM handler for graceful shutdown")
        except (AttributeError, ValueError) as e:
            # SIGTERM might not be available on some platforms
            self.logger.warning(f"Could not register SIGTERM handler: {e}")

        # Windows-specific: SIGBREAK
        if platform.system() == 'Windows':
            try:
                signal.signal(signal.SIGBREAK, signal_handler)
                self.logger.info("Registered SIGBREAK handler for graceful shutdown (Windows)")
            except (AttributeError, ValueError) as e:
                self.logger.warning(f"Could not register SIGBREAK handler: {e}")

    def setup_logging(self):
        """Configure shared logger for session editor"""
        if getattr(self, 'logger', None) is None:
            self.logger = setup_shared_logger('SessionEditor', logging.INFO)
        self.logger.info("============================================================")
        self.logger.info("Session Editor initialized")
        self.logger.info(f"Session ID: {self.session_id}")
        self.logger.info(f"API Base URL: http://127.0.0.1:8000")
        self.logger.info("============================================================")

    def _activate_session(self):
        """Activate this session as the current session"""
        try:
            response = self.api_server.api_set_session_as_current(self.session_id)
            if response:
                self.logger.info("Successfully activated session %s", self.session_id)
            else:
                self.logger.warning("Failed to activate session %s", self.session_id)
        except Exception as e:
            self.logger.exception("Error activating session %s: %s", self.session_id, e)

    def load_data(self):
        """Load drones, targets, and obstacles from session data"""
        try:
            self.logger.info("Loading data for session %s", self.session_id)

            # Fetch existing items for this session
            drones_response = self.api_server.api_get_drones(session_id=self.session_id)
            if drones_response:
                # API returns list directly
                self.drones = drones_response
            
            targets_response = self.api_server.api_get_targets(session_id=self.session_id)
            if targets_response:
                 # API returns list directly
                self.targets = targets_response

            obstacles_response = self.api_server.api_get_obstacles(session_id=self.session_id)
            if obstacles_response:
                 # API returns list directly
                self.obstacles = obstacles_response

            self._snapshot_baseline()

        except Exception as e:
            self.logger.exception("Error loading data for session %s: %s", self.session_id, e)

    def _snapshot_baseline(self):
        """Store a copy of the current session entities to support rollback."""
        self.baseline_data = {
            'drones': deepcopy(self.drones),
            'targets': deepcopy(self.targets),
            'obstacles': deepcopy(self.obstacles)
        }
        self.pending_deletions = []
        self.dirty = False
        self.logger.debug(
            "Baseline snapshot captured (drones=%d, targets=%d, obstacles=%d)",
            len(self.baseline_data['drones']),
            len(self.baseline_data['targets']),
            len(self.baseline_data['obstacles'])
        )

    def revert_to_baseline(self):
        """Revert local changes back to the last saved session snapshot."""
        if not self.baseline_data:
            self.logger.warning("No baseline data available to revert to.")
            return

        self.drones = deepcopy(self.baseline_data.get('drones', []))
        self.targets = deepcopy(self.baseline_data.get('targets', []))
        self.obstacles = deepcopy(self.baseline_data.get('obstacles', []))
        self.pending_deletions = []
        self.selected_item = None
        self.selected_item_world_pos = None

        if self.move_mode:
            self.exit_move_mode()

        self.dirty = False
        self.update_button_states()

        self.logger.info(
            "Reverted session to baseline snapshot (drones=%d, targets=%d, obstacles=%d)",
            len(self.drones),
            len(self.targets),
            len(self.obstacles)
        )

    def create_ui_elements(self):
        """Create UI buttons and controls"""
        # Top toolbar buttons
        button_y = 10
        button_x = 10
        button_width = 100
        button_height = 30
        button_spacing = 5

        self.toolbar_buttons = [
            {
                "text": "Save",
                "action": self.save_changes,
                "rect": pygame.Rect(button_x, button_y, button_width, button_height),
                "enabled": True
            },
            {
                "text": "Save As",
                "action": self.save_as_session,
                "rect": pygame.Rect(button_x + (button_width + button_spacing), button_y, button_width, button_height),
                "enabled": True
            },
            {
                "text": "Add Drone",
                "action": self.add_drone,
                "rect": pygame.Rect(button_x + 2 * (button_width + button_spacing), button_y, button_width, button_height),
                "enabled": True
            },
            {
                "text": "Add Target",
                "action": self.add_target,
                "rect": pygame.Rect(button_x + 3 * (button_width + button_spacing), button_y, button_width, button_height),
                "enabled": True
            },
            {
                "text": "Add Obstacle",
                "action": self.add_obstacle,
                "rect": pygame.Rect(button_x + 4 * (button_width + button_spacing), button_y, button_width, button_height),
                "enabled": True
            },
            {
                "text": "Move",
                "action": self.toggle_move_mode,
                "rect": pygame.Rect(button_x + 5 * (button_width + button_spacing), button_y, button_width, button_height),
                "enabled": False,
                "toggle_active": False
            },
            {
                "text": "Edit",
                "action": self.edit_selected_item,
                "rect": pygame.Rect(button_x + 6 * (button_width + button_spacing), button_y, button_width, button_height),
                "enabled": False
            },
            {
                "text": "Duplicate",
                "action": self.duplicate_selected_item,
                "rect": pygame.Rect(button_x + 7 * (button_width + button_spacing), button_y, button_width, button_height),
                "enabled": False
            },
            {
                "text": "Delete",
                "action": self.delete_selected,
                "rect": pygame.Rect(button_x + 8 * (button_width + button_spacing), button_y, button_width, button_height),
                "enabled": False
            },
            {
                "text": "Selection",
                "action": self.change_selected,
                "rect": pygame.Rect(button_x + 9 * (button_width + button_spacing), button_y, button_width, button_height),
                "enabled": False
            },
            {
                "text": "Snap to Grid",
                "action": self.toggle_snap_to_grid,
                "rect": pygame.Rect(button_x + 10 * (button_width + button_spacing), button_y, button_width, button_height),
                "enabled": True,
                "toggle": True
            },
            {
                "text": "Close",
                "action": self.close_editor,
                "rect": pygame.Rect(SCREEN_WIDTH - button_width - 10, button_y, button_width, button_height),
                "enabled": True
            }
        ]

        # Canvas control buttons (bottom-right)
        button_size = 35
        margin = 5
        edge_margin = 30

        buttons_width = button_size * 3 + margin * 2
        buttons_height = button_size * 2 + margin * 2

        start_x = SCREEN_WIDTH - buttons_width - edge_margin
        start_y = SCREEN_HEIGHT - buttons_height - edge_margin * 3

        self.canvas_buttons = [
            {"text": "↑", "action": self.move_up, "rect": pygame.Rect(start_x + button_size + margin, start_y, button_size, button_size)},
            {"text": "←", "action": self.move_left, "rect": pygame.Rect(start_x, start_y + button_size + margin, button_size, button_size)},
            {"text": "↓", "action": self.move_down, "rect": pygame.Rect(start_x + button_size + margin, start_y + button_size + margin, button_size, button_size)},
            {"text": "→", "action": self.move_right, "rect": pygame.Rect(start_x + (button_size + margin) * 2, start_y + button_size + margin, button_size, button_size)},
        ]

        # Zoom slider
        slider_width = buttons_width
        slider_height = 18
        slider_x = start_x
        slider_y = start_y + buttons_height + margin * 2

        self.zoom_slider = {
            "rect": pygame.Rect(slider_x, slider_y, slider_width, slider_height),
            "handle_rect": pygame.Rect(0, 0, 10, slider_height - 4),
            "dragging": False
        }
        self.update_slider_position()

    def update_slider_position(self):
        """Update zoom slider handle position based on current zoom"""
        slider = self.zoom_slider
        t = self.current_zoom_index / (len(self.zoom_levels) - 1)
        handle_x = slider["rect"].x + int(t * (slider["rect"].width - 10))
        slider["handle_rect"].x = handle_x
        slider["handle_rect"].y = slider["rect"].y + 2

    def auto_fit_view(self):
        """Auto-fit view to show all items"""
        if not self.drones and not self.targets and not self.obstacles:
            return

        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')

        # Compute bounds
        for drone in self.drones:
            x, y = drone['position']['x'], drone['position']['y']
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

        for target in self.targets:
            x, y = target['position']['x'], target['position']['y']
            r = target.get('radius', 0) or 0
            min_x = min(min_x, x - r)
            max_x = max(max_x, x + r)
            min_y = min(min_y, y - r)
            max_y = max(max_y, y + r)

        for obstacle in self.obstacles:
            x, y = obstacle['position']['x'], obstacle['position']['y']
            r = obstacle.get('radius', 10) or 10
            min_x = min(min_x, x - r)
            max_x = max(max_x, x + r)
            min_y = min(min_y, y - r)
            max_y = max(max_y, y + r)

        if min_x == float('inf'):
            return

        # Add padding
        width = max_x - min_x
        height = max_y - min_y
        padding = 0.1
        min_x -= width * padding
        max_x += width * padding
        min_y -= height * padding
        max_y += height * padding

        # Find best zoom level with maximum initial scale limit
        viewable_width = SCREEN_WIDTH - self.transform.margin_x
        viewable_height = SCREEN_HEIGHT - self.transform.margin_y
        max_initial_scale = 5.0  # Limit initial auto-fit scale to 5x maximum

        for i in reversed(range(len(self.zoom_levels))):
            scale = self.zoom_levels[i]
            # Skip scales that exceed the maximum initial scale
            if scale > max_initial_scale:
                continue
            if (max_x - min_x) * scale <= viewable_width and (max_y - min_y) * scale <= viewable_height:
                self.current_zoom_index = i
                self.transform.map_scale = scale
                break

        # Set origin
        self.transform.lower_left_corner = (min_x - self.transform.margin_x / self.transform.map_scale,
                                            min_y - self.transform.margin_y / self.transform.map_scale)
        self.update_slider_position()

    def draw_grid(self):
        """Draw grid on canvas"""
        grid_spacing = 20  # pixels

        visible_width = (SCREEN_WIDTH - self.transform.margin_x) / self.transform.map_scale
        visible_height = (SCREEN_HEIGHT - self.transform.margin_y) / self.transform.map_scale

        start_x = int(self.transform.lower_left_corner[0] - self.transform.margin_x / self.transform.map_scale)
        end_x = int(self.transform.lower_left_corner[0] + visible_width)
        start_y = int(self.transform.lower_left_corner[1] - self.transform.margin_y / self.transform.map_scale)
        end_y = int(self.transform.lower_left_corner[1] + visible_height)

        grid_world_spacing = grid_spacing / self.transform.map_scale
        start_x = math.floor(start_x / grid_world_spacing) * grid_world_spacing
        start_y = math.floor(start_y / grid_world_spacing) * grid_world_spacing

        # Draw vertical lines
        x = start_x
        while x <= end_x:
            start_point = self.transform.world_to_screen(x, start_y)
            end_point = self.transform.world_to_screen(x, end_y)
            pygame.draw.line(self.screen, GRID_COLOR, start_point, end_point, 1)
            x += grid_world_spacing

        # Draw horizontal lines
        y = start_y
        while y <= end_y:
            start_point = self.transform.world_to_screen(start_x, y)
            end_point = self.transform.world_to_screen(end_x, y)
            pygame.draw.line(self.screen, GRID_COLOR, start_point, end_point, 1)
            y += grid_world_spacing

    def draw_drone(self, drone: Dict):
        """Draw drone on canvas"""
        x, y = drone['position']['x'], drone['position']['y']
        screen_x, screen_y = self.transform.world_to_screen(x, y)

        color = DRONE_COLORS.get(drone.get('status', 'idle'), WHITE)
        radius = int(UI_RADIUS_MIN * self.transform.map_scale)

        # Draw drone body
        pygame.draw.circle(self.screen, color, (screen_x, screen_y), radius)

        # Draw battery ring
        battery = drone.get('battery_level', 100)
        battery_color = STATUS_OK if battery > 40 else (STATUS_WARN if battery > 10 else STATUS_ERROR)
        pygame.draw.circle(self.screen, battery_color, (screen_x, screen_y), radius + 3, 2)

        # Draw heading indicator
        heading = math.radians(drone.get('heading', 0))
        indicator_x = screen_x + int(radius * 1.5 * math.sin(heading))
        indicator_y = screen_y - int(radius * 1.5 * math.cos(heading))
        pygame.draw.line(self.screen, WHITE, (screen_x, screen_y), (indicator_x, indicator_y), 2)

        # Selection indicator
        if self.selected_item and self.selected_item['type'] == 'drone' and self.selected_item['data']['id'] == drone['id']:
            pygame.draw.circle(self.screen, SELECT_BORDER, (screen_x, screen_y), radius + 8, 3)

        # Label
        label = self.canvas_label_font.render(f"{drone['name']}", True, TEXT_COLOR)
        self.screen.blit(label, (screen_x + radius + 5, screen_y - 10))

    def draw_target(self, target: Dict):
        """Draw target on canvas"""
        x, y = target['position']['x'], target['position']['y']
        screen_x, screen_y = self.transform.world_to_screen(x, y)

        color = TARGET_COLORS.get(target.get('type', 'fixed'), WHITE)

        # Draw based on type
        target_type = target.get('type', 'fixed')
        if target_type == 'fixed':
            size = int(max(UI_RADIUS_MIN, (target.get('radius') or 10)) * self.transform.map_scale)
            rect = pygame.Rect(screen_x - size // 2, screen_y - size // 2, size, size)
            pygame.draw.rect(self.screen, color, rect)
        elif target_type == 'circle':
            radius = int((target.get('radius') or 10) * self.transform.map_scale)
            pygame.draw.circle(self.screen, color, (screen_x, screen_y), radius)
            pygame.draw.circle(self.screen, WHITE, (screen_x, screen_y), radius, 2)
        elif target_type == 'polygon' and target.get('vertices'):
            points = [(self.transform.world_to_screen(v['x'], v['y'])) for v in target['vertices']]
            if len(points) >= 3:
                pygame.draw.polygon(self.screen, color, points)
                pygame.draw.polygon(self.screen, WHITE, points, 2)
        elif target_type == 'waypoint':
            size = int(max(UI_RADIUS_MIN, (target.get('radius') or 10)) * self.transform.map_scale)
            pygame.draw.circle(self.screen, color, (screen_x, screen_y), size)
        elif target_type == 'moving':
            size = int(max(UI_RADIUS_MIN, (target.get('radius') or 10)) * self.transform.map_scale)
            pygame.draw.circle(self.screen, color, (screen_x, screen_y), size)
        else:
            # Fallback for any unknown target types
            size = int(max(UI_RADIUS_MIN, (target.get('radius') or 10)) * self.transform.map_scale)
            pygame.draw.circle(self.screen, color, (screen_x, screen_y), size)

        # Selection indicator
        if self.selected_item and self.selected_item['type'] == 'target' and self.selected_item['data']['id'] == target['id']:
            if target_type == 'circle':
                radius = int((target.get('radius') or 10) * self.transform.map_scale)
                pygame.draw.circle(self.screen, SELECT_BORDER, (screen_x, screen_y), radius + 5, 3)
            elif target_type == 'fixed':
                size = int(max(UI_RADIUS_MIN, (target.get('radius') or 10)) * self.transform.map_scale)
                rect = pygame.Rect(screen_x - size // 2 - 5, screen_y - size // 2 - 5, size + 10, size + 10)
                pygame.draw.rect(self.screen, SELECT_BORDER, rect, 3)
            elif target_type in ['waypoint', 'moving']:
                size = int(max(UI_RADIUS_MIN, (target.get('radius') or 10)) * self.transform.map_scale)
                pygame.draw.circle(self.screen, SELECT_BORDER, (screen_x, screen_y), size + 5, 3)
            else:
                size = int(max(UI_RADIUS_MIN, (target.get('radius') or 10)) * self.transform.map_scale)
                rect = pygame.Rect(screen_x - size // 2 - 5, screen_y - size // 2 - 5, size + 10, size + 10)
                pygame.draw.rect(self.screen, SELECT_BORDER, rect, 3)

        # Label
        label = self.canvas_label_font.render(f"{target['name']}", True, TEXT_COLOR)
        self.screen.blit(label, (screen_x + 20, screen_y - 10))

    def draw_obstacle(self, obstacle: Dict):
        """Draw obstacle on canvas"""
        x, y = obstacle['position']['x'], obstacle['position']['y']
        screen_x, screen_y = self.transform.world_to_screen(x, y)

        color = OBSTACLE_COLORS.get(obstacle.get('type', 'circle'), WHITE)

        # Draw based on type
        obstacle_type = obstacle.get('type', 'circle')
        if obstacle_type == 'point':
            radius = int(max(UI_RADIUS_MIN, (obstacle.get('radius') or 10)) * self.transform.map_scale)
            pygame.draw.circle(self.screen, color, (screen_x, screen_y), radius)
            pygame.draw.circle(self.screen, WHITE, (screen_x, screen_y), radius, 2)
        elif obstacle_type == 'circle':
            radius = int((obstacle.get('radius') or 10) * self.transform.map_scale)
            pygame.draw.circle(self.screen, color, (screen_x, screen_y), radius)
            pygame.draw.circle(self.screen, WHITE, (screen_x, screen_y), radius, 2)
        elif obstacle_type == 'ellipse':
            width = int((obstacle.get('width') or 10) * self.transform.map_scale * 2)
            height = int((obstacle.get('length') or 10) * self.transform.map_scale * 2)
            rect = pygame.Rect(screen_x - width // 2, screen_y - height // 2, width, height)
            pygame.draw.ellipse(self.screen, color, rect)
            pygame.draw.ellipse(self.screen, WHITE, rect, 2)
        elif obstacle_type == 'polygon' and obstacle.get('vertices'):
            points = [(self.transform.world_to_screen(v['x'], v['y'])) for v in obstacle['vertices']]
            if len(points) >= 3:
                pygame.draw.polygon(self.screen, color, points)
                pygame.draw.polygon(self.screen, WHITE, points, 2)
        else:
            radius = int((obstacle.get('radius') or 10) * self.transform.map_scale)
            rect = pygame.Rect(screen_x - radius // 2, screen_y - radius // 2, radius, radius)
            pygame.draw.rect(self.screen, color, rect)

        # Selection indicator
        if self.selected_item and self.selected_item['type'] == 'obstacle' and self.selected_item['data']['id'] == obstacle['id']:
            if obstacle_type == 'point':
                radius = int(max(UI_RADIUS_MIN, (obstacle.get('radius') or 10)) * self.transform.map_scale)
                pygame.draw.circle(self.screen, SELECT_BORDER, (screen_x, screen_y), radius + 5, 3)
            elif obstacle_type == 'circle':
                radius = int((obstacle.get('radius') or 10) * self.transform.map_scale)
                pygame.draw.circle(self.screen, SELECT_BORDER, (screen_x, screen_y), radius + 5, 3)
            else:
                radius = int((obstacle.get('radius') or 10) * self.transform.map_scale)
                rect = pygame.Rect(screen_x - radius // 2 - 5, screen_y - radius // 2 - 5, radius + 10, radius + 10)
                pygame.draw.rect(self.screen, SELECT_BORDER, rect, 3)

        # Label
        label = self.canvas_label_font.render(f"{obstacle['name']}", True, TEXT_COLOR)
        self.screen.blit(label, (screen_x + 20, screen_y - 10))

    def draw_toolbar(self):
        """Draw toolbar with buttons"""
        # Toolbar background
        pygame.draw.rect(self.screen, TOOLBAR_BG, pygame.Rect(0, 0, SCREEN_WIDTH, 50))
        pygame.draw.line(self.screen, PANEL_BORDER, (0, 50), (SCREEN_WIDTH, 50), 2)

        # Draw buttons
        for button in self.toolbar_buttons:
            enabled = button.get('enabled', True)
            is_toggle = button.get('toggle', False)
            is_move_toggle = button.get('text') == 'Move' and button.get('toggle_active', False)
            is_snap_toggle = button.get('text') == 'Snap to Grid' and is_toggle

            if is_snap_toggle:
                # Snap to Grid button shows active state when enabled
                bg_color = ACTIVE_BUTTON_BG if self.snap_to_grid_enabled else BUTTON_BG
                border_color = ACTIVE_BUTTON_BORDER if self.snap_to_grid_enabled else BUTTON_BORDER
            elif is_move_toggle:
                bg_color = ACTIVE_BUTTON_BG
                border_color = ACTIVE_BUTTON_BORDER
            elif not enabled:
                bg_color = DISABLED_BUTTON_BG
                border_color = DISABLED_BUTTON_BORDER
            else:
                bg_color = BUTTON_BG
                border_color = BUTTON_BORDER

            pygame.draw.rect(self.screen, bg_color, button['rect'])
            pygame.draw.rect(self.screen, border_color, button['rect'], 2)

            text_color = TEXT_COLOR if enabled else (150, 150, 150)
            text = self.font.render(button['text'], True, text_color)
            text_rect = text.get_rect(center=button['rect'].center)
            self.screen.blit(text, text_rect)

    def draw_canvas_controls(self):
        """Draw canvas control buttons and zoom slider"""
        # Canvas buttons
        for button in self.canvas_buttons:
            pygame.draw.rect(self.screen, CANVAS_BUTTON_BG, button['rect'])
            pygame.draw.rect(self.screen, CANVAS_BUTTON_BORDER, button['rect'], 2)

            text = self.font.render(button['text'], True, TEXT_COLOR)
            text_rect = text.get_rect(center=button['rect'].center)
            self.screen.blit(text, text_rect)

        # Zoom slider
        slider = self.zoom_slider
        pygame.draw.rect(self.screen, SLIDER_TRACK, slider['rect'])
        pygame.draw.rect(self.screen, SLIDER_BORDER, slider['rect'], 2)
        pygame.draw.rect(self.screen, SLIDER_HANDLE, slider['handle_rect'])
        pygame.draw.rect(self.screen, SLIDER_HANDLE_BORDER, slider['handle_rect'], 1)

        # Zoom text
        zoom_text = f"{self.transform.map_scale:.1f}x"
        zoom_surface = self.font.render(zoom_text, True, TEXT_COLOR)
        zoom_rect = zoom_surface.get_rect(center=(slider['rect'].centerx, slider['rect'].bottom + 12))
        self.screen.blit(zoom_surface, zoom_rect)

    def draw_status_bar(self):
        """Draw status bar at bottom"""
        status_height = 30
        status_rect = pygame.Rect(0, SCREEN_HEIGHT - status_height, SCREEN_WIDTH, status_height)
        pygame.draw.rect(self.screen, STATUS_BAR_BG, status_rect)
        pygame.draw.line(self.screen, PANEL_BORDER, (0, SCREEN_HEIGHT - status_height), (SCREEN_WIDTH, SCREEN_HEIGHT - status_height), 2)

        # Status text - prioritize move mode instructions
        if self.move_mode and self.move_mode_item:
            item_name = self.move_mode_item['data'].get('name', 'Unknown')
            snap_info = f" (Snap: {self.grid_size}m)" if self.snap_to_grid_enabled else ""
            status_text = f"MOVE MODE: Click to place '{item_name}' at new position{snap_info} | Press ESC or M to cancel"
            text_color = SELECT_BORDER  # Blue color to emphasize move mode
        else:
            status_text = f"Drones: {len(self.drones)} | Targets: {len(self.targets)} | Obstacles: {len(self.obstacles)}"
            if self.snap_to_grid_enabled:
                status_text += f" | SNAP TO GRID: {self.grid_size}m"
            if self.dirty:
                status_text += " | UNSAVED CHANGES"
            if self.selected_item:
                item_type = self.selected_item['type'].capitalize()
                item_name = self.selected_item['data'].get('name', 'Unknown')
                item_id = self.selected_item['data'].get('id', 'Unknown')
                pos = self.selected_item['data'].get('position', {}) if self.selected_item.get('data') else {}
                pos_x = pos.get('x')
                pos_y = pos.get('y')
                pos_z = pos.get('z')
                if (pos_x is None or pos_y is None) and self.selected_item_world_pos:
                    pos_x, pos_y = self.selected_item_world_pos
                if pos_z is None:
                    pos_z = 0.0
                if pos_x is not None and pos_y is not None:
                    status_text += (
                        f" | Selected: {item_type} - {item_name} [{item_id}]"
                        f" ({format_number(pos_x)}, {format_number(pos_y)}, {format_number(pos_z)})"
                    )
                else:
                    status_text += f" | Selected: {item_type} - {item_name} [{item_id}]"
            text_color = TEXT_COLOR

        status_surface = self.font.render(status_text, True, text_color)
        self.screen.blit(status_surface, (10, SCREEN_HEIGHT - status_height + 8))

        # Draw last click coordinates on the right side of status bar
        if self.last_click_world_pos:
            world_x, world_y = self.last_click_world_pos
            coord_text = f"Last Click: ({world_x:.2f}, {world_y:.2f})"
            coord_surface = self.font.render(coord_text, True, text_color)
            coord_x = SCREEN_WIDTH - coord_surface.get_width() - 10
            self.screen.blit(coord_surface, (coord_x, SCREEN_HEIGHT - status_height + 8))

    def compute_world_bounds(self) -> Tuple[float, float, float, float]:
        """Compute world bounds that include drones, targets, and obstacles.
        Returns (min_x, max_x, min_y, max_y). If no items, returns a default box."""
        min_x: Optional[float] = None
        max_x: Optional[float] = None
        min_y: Optional[float] = None
        max_y: Optional[float] = None

        def update_bounds(px: float, py: float):
            nonlocal min_x, max_x, min_y, max_y
            min_x = px if min_x is None else min(min_x, px)
            max_x = px if max_x is None else max(max_x, px)
            min_y = py if min_y is None else min(min_y, py)
            max_y = py if max_y is None else max(max_y, py)

        # Drones
        for d in self.drones:
            update_bounds(d["position"]["x"], d["position"]["y"])

        # Targets (include radius)
        for t in self.targets:
            cx = t["position"]["x"]
            cy = t["position"]["y"]
            r = t.get("radius", 0) or 0
            update_bounds(cx - r, cy - r)
            update_bounds(cx + r, cy + r)

        # Obstacles: circle uses radius, polygon uses vertices, ellipse uses width/length
        for o in self.obstacles:
            ox = o["position"]["x"]
            oy = o["position"]["y"]
            if o["type"] == "circle":
                r = o.get("radius", 0) or 0
                update_bounds(ox - r, oy - r)
                update_bounds(ox + r, oy + r)
            elif o["type"] == "ellipse":
                w = o.get("width", 0) or 10
                l = o.get("length", 0) or 10
                update_bounds(ox - w/2, oy - l/2)
                update_bounds(ox + w/2, oy + l/2)
            elif o["type"] == "polygon" and o.get("vertices"):
                for v in o["vertices"]:
                    update_bounds(v["x"], v["y"])
            else:
                r = o.get("radius") or 10
                update_bounds(ox - r, oy - r)
                update_bounds(ox + r, oy + r)

        # Default bounds if no items
        if min_x is None or max_x is None or min_y is None or max_y is None:
            min_x, max_x = -50.0, 50.0
            min_y, max_y = -50.0, 50.0
        else:
            # Ensure minimum bounds size (especially important for single items)
            # This prevents the minimap from having zero/tiny dimensions
            min_width = 20.0
            min_height = 20.0
            width = max_x - min_x
            height = max_y - min_y

            if width < min_width:
                center_x = (min_x + max_x) / 2
                min_x = center_x - min_width / 2
                max_x = center_x + min_width / 2

            if height < min_height:
                center_y = (min_y + max_y) / 2
                min_y = center_y - min_height / 2
                max_y = center_y + min_height / 2

        return min_x, max_x, min_y, max_y

    def draw_minimap(self):
        """Draw a bottom-left thumbnail (minimap) with a green viewport rectangle."""
        if not self.minimap_visible:
            return

        # Minimap geometry
        margin = 10
        mini_w = 200
        mini_h = 140
        mini_x = margin
        # Reserve extra space for the status bar to avoid overlap
        bottom_reserved = 50  # ~30 for status bar + extra spacing
        mini_y = SCREEN_HEIGHT - mini_h - bottom_reserved
        mini_rect = pygame.Rect(mini_x, mini_y, mini_w, mini_h)

        # Panel style background
        pygame.draw.rect(self.screen, PANEL_BG, mini_rect)
        pygame.draw.rect(self.screen, PANEL_BORDER, mini_rect, 2)

        # Inner content area to keep points and viewport away from edges
        content_pad = 8
        content_rect = pygame.Rect(
            mini_rect.x + content_pad,
            mini_rect.y + content_pad,
            mini_rect.width - 2 * content_pad,
            mini_rect.height - 2 * content_pad,
        )

        # Cache rects for event handling
        self._minimap_mini_rect = mini_rect
        self._minimap_content_rect = content_rect

        # Compute world bounds
        min_x, max_x, min_y, max_y = self.compute_world_bounds()
        world_w = max(1e-6, max_x - min_x)
        world_h = max(1e-6, max_y - min_y)

        # Add world-space padding so items have breathing room inside content
        pad_ratio = 0.05
        pad_x = world_w * pad_ratio
        pad_y = world_h * pad_ratio
        min_x -= pad_x
        max_x += pad_x
        min_y -= pad_y
        max_y += pad_y
        world_w = max_x - min_x
        world_h = max_y - min_y

        # Scale world to minimap content preserving aspect ratio and centering
        scale = min(content_rect.width / world_w, content_rect.height / world_h)
        offset_x = content_rect.x + (content_rect.width - world_w * scale) / 2.0
        offset_y = content_rect.y + (content_rect.height - world_h * scale) / 2.0

        def to_mini(wx: float, wy: float) -> Tuple[int, int]:
            mx = int(offset_x + (wx - min_x) * scale)
            # Y increases upwards in world, but downwards on screen; flip using bounds
            my = int(offset_y + (max_y - wy) * scale)
            return mx, my

        # Draw viewport rectangle (current screen area in world coords)
        visible_width = (SCREEN_WIDTH - self.transform.margin_x) / self.transform.map_scale
        visible_height = (SCREEN_HEIGHT - self.transform.margin_y) / self.transform.map_scale

        vx_min = self.transform.lower_left_corner[0]
        vx_max = self.transform.lower_left_corner[0] + visible_width
        vy_min = self.transform.lower_left_corner[1]
        vy_max = self.transform.lower_left_corner[1] + visible_height

        tl = to_mini(vx_min, vy_max)
        br = to_mini(vx_max, vy_min)
        viewport_rect = pygame.Rect(tl[0], tl[1], br[0] - tl[0], br[1] - tl[1])
        # Clip viewport to inner content bounds so it never draws outside
        clipped = viewport_rect.clip(content_rect)
        if clipped.width > 0 and clipped.height > 0:
            pygame.draw.rect(self.screen, (0, 255, 0), clipped, 2)  # Green rectangle

        # Draw points for drones, targets, and obstacles
        point_radius = 3
        # Drones
        for d in self.drones:
            mx, my = to_mini(d["position"]["x"], d["position"]["y"])
            color = DRONE_COLORS.get(d.get("status", "idle"), GRAY)
            pygame.draw.circle(self.screen, color, (mx, my), point_radius)
        # Targets
        for t in self.targets:
            mx, my = to_mini(t["position"]["x"], t["position"]["y"])
            color = TARGET_COLORS.get(t.get("type", "fixed"), WHITE)
            pygame.draw.circle(self.screen, color, (mx, my), point_radius)
        # Obstacles (draw center point)
        for o in self.obstacles:
            mx, my = to_mini(o["position"]["x"], o["position"]["y"])
            color = OBSTACLE_COLORS.get(o.get("type", "circle"), GRAY)
            pygame.draw.circle(self.screen, color, (mx, my), point_radius)

    def handle_minimap_click(self, pos: Tuple[int, int]) -> bool:
        """If click is inside the minimap content, recenter main view to that world point.
        Double-click resets view to initial state."""
        # Don't handle clicks if minimap is not visible
        if not self.minimap_visible:
            return False

        if not self._minimap_content_rect or not self._minimap_content_rect.collidepoint(pos):
            return False

        # Check for double-click to reset view
        current_time = time.time()
        time_since_last_click = current_time - self.last_minimap_click_time

        if time_since_last_click <= self.minimap_double_click_threshold:
            # Double-click detected - reset view to initial state
            self.auto_fit_view()
            self.last_minimap_click_time = 0  # Reset to prevent triple-click
            return True

        # Update last click time
        self.last_minimap_click_time = current_time

        # Single click - recenter view to clicked position
        # Recompute mapping to invert click to world (mirror draw_minimap logic)
        content_rect = self._minimap_content_rect
        min_x, max_x, min_y, max_y = self.compute_world_bounds()
        world_w = max(1e-6, max_x - min_x)
        world_h = max(1e-6, max_y - min_y)

        # Same padding used in draw_minimap
        pad_ratio = 0.05
        pad_x = world_w * pad_ratio
        pad_y = world_h * pad_ratio
        min_x -= pad_x
        max_x += pad_x
        min_y -= pad_y
        max_y += pad_y
        world_w = max_x - min_x
        world_h = max_y - min_y

        scale = min(content_rect.width / world_w, content_rect.height / world_h)
        offset_x = content_rect.x + (content_rect.width - world_w * scale) / 2.0
        offset_y = content_rect.y + (content_rect.height - world_h * scale) / 2.0

        # Invert mapping
        mx, my = pos
        wx = min_x + (mx - offset_x) / scale
        wy = max_y - (my - offset_y) / scale

        # Set main view origin and optional status click indicator
        self.transform.lower_left_corner = (wx, wy)
        self.last_click_world_pos = (wx, wy)
        return True

    def draw_move_mode_indicator(self):
        """Draw visual indicator when in move mode"""
        if not self.move_mode or not self.move_mode_item:
            return

        # Get mouse position
        mouse_pos = pygame.mouse.get_pos()
        screen_x, screen_y = mouse_pos

        # Draw crosshair at mouse position
        crosshair_size = 15
        crosshair_color = SELECT_BORDER

        # Horizontal line
        pygame.draw.line(self.screen, crosshair_color,
                        (screen_x - crosshair_size, screen_y),
                        (screen_x + crosshair_size, screen_y), 3)
        # Vertical line
        pygame.draw.line(self.screen, crosshair_color,
                        (screen_x, screen_y - crosshair_size),
                        (screen_x, screen_y + crosshair_size), 3)

        # Draw small circle at center
        pygame.draw.circle(self.screen, crosshair_color, (screen_x, screen_y), 3)
        pygame.draw.circle(self.screen, WHITE, (screen_x, screen_y), 3, 1)

        # Draw ghost preview of item at mouse position
        world_x, world_y = self.transform.screen_to_world(screen_x, screen_y)

        # Apply snap to grid if enabled (for preview)
        if self.snap_to_grid_enabled:
            preview_x = snap_to_grid(world_x, self.grid_size)
            preview_y = snap_to_grid(world_y, self.grid_size)
        else:
            preview_x = world_x
            preview_y = world_y

        preview_screen_x, preview_screen_y = self.transform.world_to_screen(preview_x, preview_y)

        # Draw semi-transparent preview based on item type
        item_type = self.move_mode_item['type']
        ghost_color = (100, 150, 255)  # Light blue

        if item_type == 'drone':
            radius = int(5 * self.transform.map_scale)
            # Draw ghost circle
            s = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
            pygame.draw.circle(s, (*ghost_color, 100), (radius * 2, radius * 2), radius)
            self.screen.blit(s, (preview_screen_x - radius * 2, preview_screen_y - radius * 2))
        elif item_type == 'target':
            target_data = self.move_mode_item['data']
            if target_data.get('type') == 'circle':
                radius = int((target_data.get('radius') or 10) * self.transform.map_scale)
                s = pygame.Surface((radius * 2 + 10, radius * 2 + 10), pygame.SRCALPHA)
                pygame.draw.circle(s, (*ghost_color, 100), (radius + 5, radius + 5), radius)
                self.screen.blit(s, (preview_screen_x - radius - 5, preview_screen_y - radius - 5))
            elif target_data.get('type') == 'polygon' and target_data.get('vertices'):
                # Draw polygon preview with translated vertices
                old_center_x, old_center_y = get_polygon_center(target_data['vertices'])
                delta_x = preview_x - old_center_x
                delta_y = preview_y - old_center_y

                # Calculate preview vertices
                preview_points = []
                for vertex in target_data['vertices']:
                    new_x = vertex['x'] + delta_x
                    new_y = vertex['y'] + delta_y
                    point = self.transform.world_to_screen(new_x, new_y)
                    preview_points.append(point)

                if len(preview_points) >= 3:
                    # Draw filled polygon with transparency
                    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                    pygame.draw.polygon(s, (*ghost_color, 80), preview_points)
                    pygame.draw.polygon(s, (*ghost_color, 150), preview_points, 2)
                    self.screen.blit(s, (0, 0))
            else:
                size = int((target_data.get('radius') or 10) * self.transform.map_scale)
                s = pygame.Surface((size + 10, size + 10), pygame.SRCALPHA)
                pygame.draw.rect(s, (*ghost_color, 100), pygame.Rect(5, 5, size, size))
                self.screen.blit(s, (preview_screen_x - size // 2 - 5, preview_screen_y - size // 2 - 5))
        elif item_type == 'obstacle':
            obstacle_data = self.move_mode_item['data']
            obstacle_type = obstacle_data.get('type', 'circle')

            if obstacle_type == 'polygon' and obstacle_data.get('vertices'):
                # Draw polygon preview with translated vertices
                old_center_x, old_center_y = get_polygon_center(obstacle_data['vertices'])
                delta_x = preview_x - old_center_x
                delta_y = preview_y - old_center_y

                # Calculate preview vertices
                preview_points = []
                for vertex in obstacle_data['vertices']:
                    new_x = vertex['x'] + delta_x
                    new_y = vertex['y'] + delta_y
                    point = self.transform.world_to_screen(new_x, new_y)
                    preview_points.append(point)

                if len(preview_points) >= 3:
                    # Draw filled polygon with transparency
                    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                    pygame.draw.polygon(s, (*ghost_color, 80), preview_points)
                    pygame.draw.polygon(s, (*ghost_color, 150), preview_points, 2)
                    self.screen.blit(s, (0, 0))
            elif obstacle_type == 'ellipse':
                # Draw ellipse preview
                width = int((obstacle_data.get('width') or 10) * self.transform.map_scale * 2)
                height = int((obstacle_data.get('length') or 10) * self.transform.map_scale * 2)
                s = pygame.Surface((width + 10, height + 10), pygame.SRCALPHA)
                rect = pygame.Rect(5, 5, width, height)
                pygame.draw.ellipse(s, (*ghost_color, 100), rect)
                pygame.draw.ellipse(s, (*ghost_color, 150), rect, 2)
                self.screen.blit(s, (preview_screen_x - width // 2 - 5, preview_screen_y - height // 2 - 5))
            else:
                # Circle or point obstacle
                radius = int((obstacle_data.get('radius') or 10) * self.transform.map_scale)
                s = pygame.Surface((radius * 2 + 10, radius * 2 + 10), pygame.SRCALPHA)
                pygame.draw.circle(s, (*ghost_color, 100), (radius + 5, radius + 5), radius)
                self.screen.blit(s, (preview_screen_x - radius - 5, preview_screen_y - radius - 5))

    def find_item_at_pos(self, world_x: float, world_y: float) -> Optional[Dict]:
        """Find item at world position, returns {'type': ..., 'data': ...} or None"""
        # Check drones (small radius)
        for drone in self.drones:
            dx = drone['position']['x']
            dy = drone['position']['y']
            if is_point_in_circle(world_x, world_y, dx, dy, UI_RADIUS_MIN / self.transform.map_scale):
                return {'type': 'drone', 'data': drone}

        # Check targets
        for target in self.targets:
            tx = target['position']['x']
            ty = target['position']['y']
            target_type = target.get('type', 'fixed')

            if target_type == 'polygon' and target.get('vertices'):
                if is_point_in_polygon(world_x, world_y, target['vertices']):
                    return {'type': 'target', 'data': target}
            elif target_type == 'circle':
                radius = (target.get('radius') or 10)
                if is_point_in_circle(world_x, world_y, tx, ty, radius):
                    return {'type': 'target', 'data': target}
            elif target_type in ['fixed', 'waypoint', 'moving']:
                radius = max(UI_RADIUS_MIN, (target.get('radius') or 10)) / self.transform.map_scale
                if is_point_in_circle(world_x, world_y, tx, ty, radius):
                    return {'type': 'target', 'data': target}
            else:
                radius = max(UI_RADIUS_MIN, (target.get('radius') or 10)) / self.transform.map_scale
                if is_point_in_circle(world_x, world_y, tx, ty, radius):
                    return {'type': 'target', 'data': target}

        # Check obstacles
        for obstacle in self.obstacles:
            ox = obstacle['position']['x']
            oy = obstacle['position']['y']
            obstacle_type = obstacle.get('type', 'circle')

            if obstacle_type == 'polygon' and obstacle.get('vertices'):
                if is_point_in_polygon(world_x, world_y, obstacle['vertices']):
                    return {'type': 'obstacle', 'data': obstacle}
            elif obstacle_type == 'point':
                radius = max(UI_RADIUS_MIN, (obstacle.get('radius') or 10)) / self.transform.map_scale
                if is_point_in_circle(world_x, world_y, ox, oy, radius):
                    return {'type': 'obstacle', 'data': obstacle}
            elif obstacle_type == 'circle':
                radius = (obstacle.get('radius') or 10)
                if is_point_in_circle(world_x, world_y, ox, oy, radius):
                    return {'type': 'obstacle', 'data': obstacle}
            elif obstacle_type == 'ellipse':
                width = (obstacle.get('width') or 10)
                height = (obstacle.get('length') or 10)
                if is_point_in_ellipse(world_x, world_y, ox, oy, width, height):
                    return {'type': 'obstacle', 'data': obstacle}

        return None

    def find_all_items_at_pos(self, world_x: float, world_y: float) -> List[Dict]:
        """Find all items at world position, returns list of {'type': ..., 'data': ...}"""
        items = []

        # Check drones (small radius)
        for drone in self.drones:
            dx = drone['position']['x']
            dy = drone['position']['y']
            if is_point_in_circle(world_x, world_y, dx, dy, UI_RADIUS_MIN / self.transform.map_scale):
                items.append({'type': 'drone', 'data': drone})

        # Check targets
        for target in self.targets:
            tx = target['position']['x']
            ty = target['position']['y']
            target_type = target.get('type', 'fixed')

            if target_type == 'polygon' and target.get('vertices'):
                if is_point_in_polygon(world_x, world_y, target['vertices']):
                    items.append({'type': 'target', 'data': target})
            elif target_type == 'circle':
                radius = (target.get('radius') or 10)
                if is_point_in_circle(world_x, world_y, tx, ty, radius):
                    items.append({'type': 'target', 'data': target})
            elif target_type in ['fixed', 'waypoint', 'moving']:
                radius = max(UI_RADIUS_MIN, (target.get('radius') or 10)) / self.transform.map_scale
                if is_point_in_circle(world_x, world_y, tx, ty, radius):
                    items.append({'type': 'target', 'data': target})
            else:
                radius = max(UI_RADIUS_MIN, (target.get('radius') or 10)) / self.transform.map_scale
                if is_point_in_circle(world_x, world_y, tx, ty, radius):
                    items.append({'type': 'target', 'data': target})

        # Check obstacles
        for obstacle in self.obstacles:
            ox = obstacle['position']['x']
            oy = obstacle['position']['y']
            obstacle_type = obstacle.get('type', 'circle')

            if obstacle_type == 'polygon' and obstacle.get('vertices'):
                if is_point_in_polygon(world_x, world_y, obstacle['vertices']):
                    items.append({'type': 'obstacle', 'data': obstacle})
            elif obstacle_type == 'point':
                radius = max(UI_RADIUS_MIN, (obstacle.get('radius') or 10)) / self.transform.map_scale
                if is_point_in_circle(world_x, world_y, ox, oy, radius):
                    items.append({'type': 'obstacle', 'data': obstacle})
            elif obstacle_type == 'circle':
                radius = (obstacle.get('radius') or 10)
                if is_point_in_circle(world_x, world_y, ox, oy, radius):
                    items.append({'type': 'obstacle', 'data': obstacle})
            elif obstacle_type == 'ellipse':
                width = (obstacle.get('width') or 10)
                height = (obstacle.get('length') or 10)
                if is_point_in_ellipse(world_x, world_y, ox, oy, width, height):
                    items.append({'type': 'obstacle', 'data': obstacle})

        return items

    def change_selected(self):
        """Change selection to next item at the same position (for overlapping items)"""
        if not self.selected_item or not self.selected_item_world_pos:
            self.logger.info("No item selected, cannot change selection")
            return

        # Use the world position where the item was clicked
        world_x, world_y = self.selected_item_world_pos

        # Find all items at this position
        items_at_pos = self.find_all_items_at_pos(world_x, world_y)

        if len(items_at_pos) <= 1:
            self.logger.info("Only one item at this position, cannot change selection")
            return

        # Find current item index
        current_index = -1
        for i, item in enumerate(items_at_pos):
            if (item['type'] == self.selected_item['type'] and
                item['data']['id'] == self.selected_item['data']['id']):
                current_index = i
                break

        if current_index == -1:
            # Current item not found, select first item
            self.selected_item = items_at_pos[0]
        else:
            # Select next item (wrap around to start)
            next_index = (current_index + 1) % len(items_at_pos)
            self.selected_item = items_at_pos[next_index]

        self.update_button_states()
        self.logger.info(f"Changed selection to {self.selected_item['type']}: {self.selected_item['data'].get('name', 'Unknown')}")

    def handle_mouse_down(self, pos: Tuple[int, int], button: int):
        """Handle mouse button down"""
        if button != 1:  # Only left click
            return

        self.mouse_down_pos = pos

        # Check toolbar buttons
        for btn in self.toolbar_buttons:
            if btn['rect'].collidepoint(pos) and btn.get('enabled', True):
                if btn['text'] == 'Edit':
                    self.logger.info("Edit toolbar button pressed at %s", pos)
                btn['action']()
                return

        # Check canvas control buttons
        for btn in self.canvas_buttons:
            if btn['rect'].collidepoint(pos):
                btn['action']()
                return

        # Check zoom slider
        if self.zoom_slider['rect'].collidepoint(pos):
            self.dragging_slider = True
            self.set_zoom_from_slider(pos[0])
            return

        # Check minimap click
        if self.handle_minimap_click(pos):
            # Minimap handled the click, don't start canvas drag
            self.mouse_down_pos = None
            return

        # Get world coordinates of click
        world_x, world_y = self.transform.screen_to_world(pos[0], pos[1])

        # Store last click position for status bar display
        self.last_click_world_pos = (world_x, world_y)

        # If in move mode, place the item at clicked position
        if self.move_mode and self.move_mode_item:
            self.move_item_to_position(world_x, world_y)
            return

        # Check if clicking on an item (for selection, NOT for dragging)
        item = self.find_item_at_pos(world_x, world_y)

        if item:
            # Select item only (no dragging)
            self.selected_item = item
            self.selected_item_world_pos = (world_x, world_y)  # Store where it was clicked
            self.update_button_states()
        else:
            # Clicked on empty space - deselect and prepare to pan
            self.selected_item = None
            self.selected_item_world_pos = None
            self.last_mouse_pos = pos
            self.update_button_states()

    def handle_mouse_up(self, pos: Tuple[int, int], button: int):
        """Handle mouse button up"""
        if button != 1:
            return

        # Reset drag states
        self.dragging_canvas = False
        self.dragging_slider = False
        self.mouse_down_pos = None

    def handle_mouse_motion(self, pos: Tuple[int, int]):
        """Handle mouse motion"""
        if self.dragging_slider:
            self.set_zoom_from_slider(pos[0])
            return

        if self.mouse_down_pos:
            # Check if we should start panning (only if not clicking on UI elements)
            dx = abs(pos[0] - self.mouse_down_pos[0])
            dy = abs(pos[1] - self.mouse_down_pos[1])
            if dx > 5 or dy > 5:
                self.dragging_canvas = True

        if self.dragging_canvas:
            # Pan canvas
            dx = pos[0] - self.last_mouse_pos[0]
            dy = pos[1] - self.last_mouse_pos[1]

            world_dx = -dx / self.transform.map_scale
            world_dy = dy / self.transform.map_scale

            self.transform.lower_left_corner = (
                self.transform.lower_left_corner[0] + world_dx,
                self.transform.lower_left_corner[1] + world_dy
            )

        self.last_mouse_pos = pos

    def handle_mouse_wheel(self, direction: int, pos: Tuple[int, int]):
        """Handle mouse wheel for zoom"""
        if direction > 0:  # Zoom in
            self.current_zoom_index = min(self.current_zoom_index + 1, len(self.zoom_levels) - 1)
        else:  # Zoom out
            self.current_zoom_index = max(self.current_zoom_index - 1, 0)

        self.transform.map_scale = self.zoom_levels[self.current_zoom_index]
        self.update_slider_position()

    def set_zoom_from_slider(self, mouse_x: int):
        """Set zoom level from slider position"""
        slider = self.zoom_slider
        t = (mouse_x - slider['rect'].x) / slider['rect'].width
        t = max(0.0, min(1.0, t))
        self.current_zoom_index = int(t * (len(self.zoom_levels) - 1))
        self.transform.map_scale = self.zoom_levels[self.current_zoom_index]
        self.update_slider_position()

    # Move mode methods
    def toggle_move_mode(self):
        """Toggle move mode for selected item"""
        if self.move_mode:
            self.exit_move_mode()
        else:
            self.enter_move_mode()

    def enter_move_mode(self):
        """Enter move mode for selected item"""
        if not self.selected_item:
            return

        self.move_mode = True
        self.move_mode_item = self.selected_item
        self.update_button_states()

    def exit_move_mode(self):
        """Exit move mode"""
        self.move_mode = False
        self.move_mode_item = None
        self.update_button_states()

    def move_item_to_position(self, world_x: float, world_y: float):
        """Move selected item to new position"""
        if not self.move_mode_item:
            return

        item_data = self.move_mode_item['data']

        # Apply snap to grid or round to nearest integer
        if self.snap_to_grid_enabled:
            # Snap to grid takes precedence - align to grid_size intervals
            world_x = snap_to_grid(world_x, self.grid_size)
            world_y = snap_to_grid(world_y, self.grid_size)
        else:
            # When snap to grid is disabled, round to nearest integer for cleaner coordinates
            world_x = round(world_x)
            world_y = round(world_y)

        # For polygon targets/obstacles, translate vertices with the new center
        item_category = self.move_mode_item['type']
        if item_category in ['target', 'obstacle']:
            shape_type = item_data.get('type')
            vertices = item_data.get('vertices')
            if shape_type == 'polygon' and vertices:
                old_center_x, old_center_y = get_polygon_center(vertices)
                delta_x = world_x - old_center_x
                delta_y = world_y - old_center_y

                for vertex in vertices:
                    vertex['x'] = round(vertex['x'] + delta_x)
                    vertex['y'] = round(vertex['y'] + delta_y)

        # Update position
        item_data['position']['x'] = world_x
        item_data['position']['y'] = world_y
        self.dirty = True

        # Exit move mode
        self.exit_move_mode()

    def update_button_states(self):
        """Update enabled state of toolbar buttons based on current state"""
        has_selection = self.selected_item is not None

        # Check if there are multiple items at the selection position for "Selection" button
        has_multiple_items = False
        if has_selection and self.selected_item_world_pos:
            world_x, world_y = self.selected_item_world_pos
            items_at_pos = self.find_all_items_at_pos(world_x, world_y)
            has_multiple_items = len(items_at_pos) > 1

        for btn in self.toolbar_buttons:
            if btn['text'] in ['Delete', 'Move', 'Edit', 'Duplicate']:
                btn['enabled'] = has_selection
            elif btn['text'] == 'Selection':
                btn['enabled'] = has_multiple_items  # Only enable if multiple items at position
            if btn['text'] == 'Move':
                btn['toggle_active'] = self.move_mode

    # Button actions
    def save_changes(self):
        """Save all changes to API and persist to storage using session POST method"""
        if not self.dirty:
            self._show_info_dialog("No Changes", "No unsaved changes to save.")
            return

        try:
            self.logger.info("Saving session %s using session POST method", self.session_id)

            # Get full session data from API
            session_data_response = self.api_server.api_get_session_data(self.session_id)
            if not session_data_response:
                raise Exception("Failed to retrieve current session data from API")

            save_payload = dict(session_data_response)
            save_payload.update({
                'drones': self.drones,
                'targets': self.targets,
                'obstacles': self.obstacles,
            })
            save_payload = normalize_session_canvas_fields(save_payload)

            self.logger.info(
                "Saving entities (drones=%d, targets=%d, obstacles=%d)",
                len(self.drones), len(self.targets), len(self.obstacles)
            )
            if self.pending_deletions:
                self.logger.info("Applying %d pending deletions on save", len(self.pending_deletions))

            # Use POST /sessions/{id} to save the entire session with all entities
            # The API now handles replacement automatically without overwrite=true
            response = self.api_server.api_new_session_with_id(self.session_id, save_payload)
            if not response:
                raise Exception("Failed to save session data")

            self.logger.info("Successfully saved session: %s", response.get('id', 'unknown'))

            self.dirty = False

            # Reload data from API to ensure we have the latest state
            self.logger.debug("Reloading data from API to verify save")
            self.load_data()

            # Fetch a fresh snapshot for storage and persist via utils helper
            storage_result = None
            storage_snapshot = self.api_server.api_get_session_data(self.session_id)
            if storage_snapshot:
                try:
                    saved_path = save_session_to_file(storage_snapshot)
                    storage_result = str(saved_path)
                    self.logger.info("Session saved to storage file: %s", saved_path)
                except Exception as exc:
                    self.logger.warning(f"Failed to save session to storage: {exc}")
            else:
                self.logger.warning("Could not fetch session snapshot for storage after saving")

            # Show success message
            self._show_info_dialog(
                "Success",
                f"Changes saved successfully!\n\n"
                f"Drones: {len(self.drones)}\n"
                f"Targets: {len(self.targets)}\n"
                f"Obstacles: {len(self.obstacles)}\n\n"
                f"Storage: {storage_result or 'Not saved to file'}"
            )

            # Notify GUI Controller that session was saved
            self._notify_session_saved()

        except Exception as e:
            self._show_error_dialog("Error", f"Failed to save changes:\n\n{str(e)}")
            self.logger.exception("Failed to save session %s: %s", self.session_id, e)

    def save_as_session(self):
        """Save current session as a new session with '_modified' postfix using session POST method"""
        try:
            # Get new session name
            original_name = self.session_data.get('name')
            if not original_name:
                try:
                    session_info = self.api_server.api_get_session_data(self.session_id, show_error=False)
                except Exception:
                    session_info = None
                if session_info:
                    normalized = extract_session_metadata(session_info) or {}
                    original_name = normalized.get('name')
                    if not original_name:
                        nested_session = normalized.get('session')
                        if isinstance(nested_session, dict):
                            original_name = nested_session.get('name')
            original_name = original_name or 'Unknown'
            new_session_name = f"{original_name}_modified"

            # Ask user to confirm or customize the name
            if getattr(self, 'logger', None):
                self.logger.info(
                    "Save As initial name: %s (session_data name=%s)",
                    new_session_name,
                    self.session_data.get('name')
                )
            result = self._prompt_text_dialog(
                "Save As New Session",
                "Enter name for the new session:",
                initialvalue=new_session_name,
                force_custom=True
            )

            if not result:
                return  # User cancelled

            new_session_name = result.strip()

            self.logger.info("Creating new session '%s' using session POST method", new_session_name)

            # Get current session data from API
            session_data_response = self.api_server.api_get_session_data(self.session_id)
            if not session_data_response:
                raise Exception("Failed to retrieve current session data from API")

            # Prepare copies of all items with session_id updated
            # We need to remove IDs so the API generates new ones
            drones_copy = []
            for drone in self.drones:
                drone_copy = deepcopy(drone)
                drone_copy.pop('id', None)  # Remove ID so API generates new one
                drone_copy['session_id'] = None  # Will be set by API
                drones_copy.append(drone_copy)

            targets_copy = []
            for target in self.targets:
                target_copy = deepcopy(target)
                target_copy.pop('id', None)
                target_copy['session_id'] = None
                targets_copy.append(target_copy)

            obstacles_copy = []
            for obstacle in self.obstacles:
                obstacle_copy = deepcopy(obstacle)
                obstacle_copy.pop('id', None)
                obstacle_copy['session_id'] = None
                obstacles_copy.append(obstacle_copy)

            # Build payload with flattened structure (session fields at top level)
            save_payload = {
                'name': new_session_name,
                'description': self.session_data.get('description', '') + ' (modified copy)',
                'status': 'active',
                'task_type': self.session_data.get('task_type', 'others'),
                'task_description': self.session_data.get('task_description', ''),
                'drones': drones_copy,
                'targets': targets_copy,
                'obstacles': obstacles_copy,
                'environment': session_data_response.get('environment'),
                'canvas_width': session_data_response.get('canvas_width'),
                'canvas_length': session_data_response.get('canvas_length'),
                'canvas_height': session_data_response.get('canvas_height'),
                'area_width': session_data_response.get('area_width'),
                'area_height': session_data_response.get('area_height'),
            }
            save_payload = normalize_session_canvas_fields(save_payload)

            self.logger.info(
                "Creating new session payload (drones=%d, targets=%d, obstacles=%d)",
                len(drones_copy), len(targets_copy), len(obstacles_copy)
            )

            # Use POST /sessions/new to create new session with all data
            response = self.api_server.api_new_session(save_payload)
            if not response:
                raise Exception("Failed to create new session")

            new_session_id = response.get('id')
            self.logger.info("Successfully created new session: %s", new_session_id)

            # Activate the new session
            self.logger.info("Activating new session %s", new_session_id)
            self.api_server.api_set_session_as_current(new_session_id)

            # Save to storage via shared helper
            self.logger.debug("Saving new session %s to storage", new_session_id)
            storage_result = None
            storage_snapshot = self.api_server.api_get_session_data(new_session_id)
            if storage_snapshot:
                try:
                    saved_path = save_session_to_file(storage_snapshot)
                    storage_result = str(saved_path)
                    self.logger.info("Session saved to storage file: %s", saved_path)
                except Exception as exc:
                    self.logger.warning(f"Failed to save new session to storage: {exc}")
            else:
                self.logger.warning("Could not fetch snapshot for new session storage")

            # Update current session reference
            self.session_id = new_session_id
            self.session_data['id'] = new_session_id
            self.session_data['name'] = new_session_name
            self.dirty = False

            # Reload data from new session to verify
            self.logger.debug("Reloading data from new session %s", new_session_id)
            self.load_data()

            self.logger.info(
                "Verification after save-as: drones=%d, targets=%d, obstacles=%d",
                len(self.drones), len(self.targets), len(self.obstacles)
            )

            # Update window title
            pygame.display.set_caption(f"Session Editor - {new_session_name}")

            # Show success message
            self._show_info_dialog(
                "Success",
                f"Session saved as '{new_session_name}'!\n\n"
                f"New Session ID: {new_session_id}\n"
                f"Drones: {len(self.drones)}\n"
                f"Targets: {len(self.targets)}\n"
                f"Obstacles: {len(self.obstacles)}\n\n"
                f"Storage: {storage_result or 'Not saved to file'}"
            )

            # Notify GUI Controller that session was saved
            self._notify_session_saved()

        except Exception as e:
            self._show_error_dialog("Error", f"Failed to save as new session: {str(e)}")
            self.logger.exception("Failed to save session as new copy: %s", e)

    def _notify_session_saved(self):
        """Notify the GUI controller or parent process that a save occurred."""
        if self.on_saved:
            try:
                self.logger.info("Calling on_saved callback to refresh GUI Controller")
                self.on_saved()
            except Exception as callback_error:
                self.logger.warning(f"on_saved callback failed: {callback_error}")
        self._write_save_signal()

    def _write_save_signal(self):
        """Write to the save signal file so GUI controller threads can refresh."""
        if not self.save_signal_file:
            return
        try:
            payload = json.dumps({
                'timestamp': time.time(),
                'session_id': self.session_id,
            })
            with open(self.save_signal_file, 'w', encoding='utf-8') as f:
                f.write(payload)
            self.logger.debug("Updated save signal file at %s", self.save_signal_file)
        except Exception as exc:
            self.logger.debug("Failed to update save signal file '%s': %s", self.save_signal_file, exc)

    def add_drone(self):
        """Add new drone"""
        self.logger.info("Opening add drone dialog")

        try:
            # Pass current drones list for name counter generation
            dialog = AddDroneDialog(session_data={'drones': self.drones})
        except Exception as e:
            self._show_error_dialog("Error", f"Failed to open add drone dialog: {str(e)}")
            self.logger.exception("Failed to open add drone dialog: %s", e)
            return

        self.active_dialog = {
            'dialog': dialog,
            'type': 'drone',
            'is_add': True
        }
        self.update_button_states()

        # Prime the dialog so it appears immediately
        self._update_active_dialog()

    def add_target(self):
        """Add new target"""
        self.logger.info("Opening add target dialog")

        try:
            # Pass current targets list for name counter generation
            dialog = AddTargetDialog(session_data={'targets': self.targets})
        except Exception as e:
            self._show_error_dialog("Error", f"Failed to open add target dialog: {str(e)}")
            self.logger.exception("Failed to open add target dialog: %s", e)
            return

        self.active_dialog = {
            'dialog': dialog,
            'type': 'target',
            'is_add': True
        }
        self.update_button_states()

        # Prime the dialog so it appears immediately
        self._update_active_dialog()

    def add_obstacle(self):
        """Add new obstacle"""
        self.logger.info("Opening add obstacle dialog")

        try:
            # Pass current obstacles list for name counter generation
            dialog = AddObstacleDialog(session_data={'obstacles': self.obstacles})
        except Exception as e:
            self._show_error_dialog("Error", f"Failed to open add obstacle dialog: {str(e)}")
            self.logger.exception("Failed to open add obstacle dialog: %s", e)
            return

        self.active_dialog = {
            'dialog': dialog,
            'type': 'obstacle',
            'is_add': True
        }
        self.update_button_states()

        # Prime the dialog so it appears immediately
        self._update_active_dialog()

    def delete_selected(self):
        """Delete selected item"""
        if not self.selected_item:
            return

        # Confirm deletion
        confirm = self._ask_yes_no_dialog(
            "Confirm Delete",
            f"Delete {self.selected_item['type']} '{self.selected_item['data']['name']}'?"
        )

        if not confirm:
            return

        item_type = self.selected_item['type']
        item_id = self.selected_item['data']['id']
        item_name = self.selected_item['data'].get('name')
        item_data_copy = deepcopy(self.selected_item['data'])

        collection_map = {
            'drone': self.drones,
            'target': self.targets,
            'obstacle': self.obstacles
        }

        collection = collection_map.get(item_type)
        if collection is None:
            self.logger.error("Unknown item type '%s' cannot be deleted", item_type)
            return

        # Remove the item locally
        original_length = len(collection)
        collection[:] = [obj for obj in collection if obj.get('id') != item_id]

        if len(collection) == original_length:
            self.logger.warning("Item %s id=%s not found in collection during deletion", item_type, item_id)
            return

        # Track pending deletion so it can be finalized on save or restored on revert
        self.pending_deletions.append({
            'type': item_type,
            'data': item_data_copy
        })

        self.selected_item = None
        self.selected_item_world_pos = None
        self.dirty = True
        self.update_button_states()

        self.logger.info(
            "Marked %s id=%s name=%s for deletion (pending save)",
            item_type,
            item_id,
            item_name
        )

    def edit_selected_item(self):
        """Launch attribute editor for the currently selected item"""
        if not self.selected_item:
            self.logger.debug("Edit requested but no item is selected")
            return
        if self.active_dialog:
            self.logger.debug("Edit requested while another dialog is active; ignoring")
            return

        # Exit move mode when opening the editor
        if self.move_mode:
            self.logger.debug("Edit requested while in move mode; exiting move mode before editing")
            self.exit_move_mode()

        item_type = self.selected_item['type']
        item_data = deepcopy(self.selected_item['data'])

        dialog_class_map = {
            'drone': DroneEditorDialog,
            'target': TargetEditorDialog,
            'obstacle': ObstacleEditorDialog
        }

        dialog_class = dialog_class_map.get(item_type)
        if not dialog_class:
            self.logger.warning("No dialog available for item type '%s'", item_type)
            return

        try:
            self.logger.info(
                "Opening edit dialog for %s id=%s name=%s",
                item_type,
                item_data.get('id'),
                item_data.get('name')
            )
            dialog = dialog_class(f"Edit {item_type.capitalize()}", item_data)
        except Exception as e:
            self._show_error_dialog("Error", f"Failed to open editor for {item_type}: {str(e)}")
            self.logger.exception("Failed to open %s editor: %s", item_type, e)
            return

        self.active_dialog = {
            'dialog': dialog,
            'type': item_type
        }
        self.update_button_states()

        # Prime the dialog so it appears immediately
        self._update_active_dialog()

    def duplicate_selected_item(self):
        """Duplicate the currently selected item"""
        if not self.selected_item:
            self.logger.debug("Duplicate requested but no item is selected")
            return
        if self.active_dialog:
            self.logger.debug("Duplicate requested while another dialog is active; ignoring")
            return

        if self.move_mode:
            self.logger.debug("Duplicate requested while in move mode; exiting move mode before duplicating")
            self.exit_move_mode()

        item_type = self.selected_item['type']
        source_data = deepcopy(self.selected_item['data'])

        collection_map = {
            'drone': self.drones,
            'target': self.targets,
            'obstacle': self.obstacles
        }
        collection = collection_map.get(item_type)
        if collection is None:
            self.logger.warning("Unknown item type '%s' cannot be duplicated", item_type)
            return

        existing_names = [item.get('name') for item in collection if item.get('name')]
        base_name = source_data.get('name') or item_type.capitalize()
        copy_base = f"{base_name} Copy"
        if copy_base in existing_names:
            new_name = create_new_name(copy_base, exist_list=existing_names)
        else:
            new_name = copy_base

        source_data['id'] = str(uuid.uuid4())[:8]
        source_data['name'] = new_name

        offset = self.grid_size or 10.0
        position = source_data.get('position')
        if isinstance(position, dict):
            position['x'] = (position.get('x') or 0.0) + offset
            position['y'] = (position.get('y') or 0.0) + offset

        vertices = source_data.get('vertices')
        if isinstance(vertices, list) and vertices:
            for vertex in vertices:
                if isinstance(vertex, dict):
                    vertex['x'] = (vertex.get('x') or 0.0) + offset
                    vertex['y'] = (vertex.get('y') or 0.0) + offset

        self.apply_item_add(item_type, source_data)

        new_pos = None
        if isinstance(position, dict):
            new_pos = (position.get('x'), position.get('y'))
        elif isinstance(vertices, list) and vertices:
            try:
                new_pos = get_polygon_centroid(vertices)
            except Exception:
                new_pos = None

        if new_pos and new_pos[0] is not None and new_pos[1] is not None:
            self.selected_item_world_pos = (float(new_pos[0]), float(new_pos[1]))
        elif self.selected_item_world_pos:
            self.selected_item_world_pos = (
                self.selected_item_world_pos[0] + offset,
                self.selected_item_world_pos[1] + offset
            )

    def _update_active_dialog(self):
        """Poll the active dialog and apply changes when closed"""
        if not self.active_dialog:
            return

        dialog_wrapper = self.active_dialog
        dialog = dialog_wrapper['dialog']
        dialog.poll_events()

        if dialog.is_closed():
            result = dialog.result
            item_type = dialog_wrapper['type']
            is_add = dialog_wrapper.get('is_add', False)
            self.active_dialog = None

            # Clear mouse state to prevent spurious drag events after dialog closes
            self.dragging_canvas = False
            self.dragging_slider = False
            self.mouse_down_pos = None

            # Clear pygame event queue to remove any stale mouse events
            pygame.event.clear()

            if result:
                if is_add:
                    self.logger.info(
                        "Add dialog confirmed for %s id=%s name=%s",
                        item_type,
                        result.get('id'),
                        result.get('name')
                    )
                    self.apply_item_add(item_type, result)
                else:
                    self.logger.info(
                        "Edit dialog confirmed for %s id=%s",
                        item_type,
                        result.get('id')
                    )
                    self.apply_item_update(item_type, result)
            else:
                action = "add" if is_add else "edit"
                self.logger.info("Dialog canceled for %s %s", action, item_type)
                self.update_button_states()

    def apply_item_update(self, item_type: str, updated_data: Dict[str, Any]):
        """Apply item updates locally (marks session as dirty, requires save)"""
        if not updated_data or 'id' not in updated_data:
            self.logger.warning("Attempted to update %s with no data or missing ID", item_type)
            return

        item_id = updated_data['id']
        new_data = deepcopy(updated_data)

        # Clean up type-specific fields
        if item_type == 'target':
            target_type = new_data.get('type')
            if target_type == 'polygon':
                new_data.pop('radius', None)
            else:
                new_data.pop('vertices', None)
        elif item_type == 'obstacle':
            obstacle_type = new_data.get('type')
            if obstacle_type == 'polygon':
                new_data.pop('radius', None)
                new_data.pop('width', None)
                new_data.pop('length', None)
            elif obstacle_type == 'ellipse':
                new_data.pop('radius', None)
                new_data.pop('vertices', None)
            else:
                new_data.pop('width', None)
                new_data.pop('length', None)
                new_data.pop('vertices', None)

        # Update local collection
        collection_map = {
            'drone': self.drones,
            'target': self.targets,
            'obstacle': self.obstacles
        }

        collection = collection_map[item_type]
        updated_item_ref = None
        for idx, item in enumerate(collection):
            if item.get('id') == item_id:
                collection[idx] = new_data
                updated_item_ref = collection[idx]
                break

        if updated_item_ref is None:
            self.logger.warning("Item %s id=%s not found in local collection", item_type, item_id)
            return

        # Update selection to point to the updated item
        self.selected_item = {
            'type': item_type,
            'data': updated_item_ref
        }

        self.logger.info(
            "Updated %s id=%s name=%s locally (pending save)",
            item_type,
            updated_item_ref.get('id'),
            updated_item_ref.get('name')
        )

        # Mark session as dirty (unsaved changes)
        self.dirty = True
        self.update_button_states()

    def apply_item_add(self, item_type: str, new_data: Dict[str, Any]):
        """Add a new item locally (marks session as dirty, requires save)"""
        if not new_data:
            self.logger.warning("Attempted to add %s with no data", item_type)
            return

        created_data = deepcopy(new_data)

        # Clean up type-specific fields
        if item_type == 'target':
            target_type = created_data.get('type')
            if target_type == 'polygon':
                created_data.pop('radius', None)
            else:
                created_data.pop('vertices', None)
        elif item_type == 'obstacle':
            obstacle_type = created_data.get('type')
            if obstacle_type == 'polygon':
                created_data.pop('radius', None)
                created_data.pop('width', None)
                created_data.pop('length', None)
            elif obstacle_type == 'ellipse':
                created_data.pop('radius', None)
                created_data.pop('vertices', None)
            else:
                created_data.pop('width', None)
                created_data.pop('length', None)
                created_data.pop('vertices', None)

        # Add to the appropriate local collection
        collection_map = {
            'drone': self.drones,
            'target': self.targets,
            'obstacle': self.obstacles
        }

        collection = collection_map[item_type]
        collection.append(created_data)
        created_item_ref = collection[-1]

        # Select the newly created item
        self.selected_item = {
            'type': item_type,
            'data': created_item_ref
        }

        self.logger.info(
            "Added new %s id=%s name=%s locally (pending save)",
            item_type,
            created_item_ref.get('id'),
            created_item_ref.get('name')
        )

        # Mark session as dirty (unsaved changes)
        self.dirty = True
        self.update_button_states()

    def toggle_snap_to_grid(self):
        """Toggle snap to grid"""
        self.snap_to_grid_enabled = not self.snap_to_grid_enabled

    def _ask_save_discard_dialog(self) -> str:
        """Show dialog for unsaved changes with Save/Save As/Discard/Cancel options."""
        root = self._prepare_tk_dialog()
        if not root:
            if getattr(self, 'logger', None):
                self.logger.warning("Cannot display unsaved changes dialog; defaulting to cancel")
            return 'cancel'

        dialog = tk.Toplevel(root)
        dialog.title("Unsaved Changes")
        set_window_geometry_and_center(
            dialog,
            500,
            150,
            None,
            make_transient=False,
            align_to_pointer=True,
            bring_to_front=True
        )
        dialog.resizable(False, False)

        result = {'action': 'cancel'}

        tk.Label(dialog, text="You have unsaved changes.\nWhat would you like to do?", pady=20).pack()

        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)

        def set_action(action):
            result['action'] = action
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            dialog.destroy()

        tk.Button(button_frame, text="Save", command=lambda: set_action('save'), width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Save As", command=lambda: set_action('save_as'), width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Discard", command=lambda: set_action('discard'), width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=lambda: set_action('cancel'), width=8).pack(side=tk.LEFT, padx=5)

        dialog.protocol("WM_DELETE_WINDOW", lambda: set_action('cancel'))
        
        dialog.attributes('-topmost', True)
        dialog.update_idletasks()
        dialog.deiconify()
        dialog.grab_set()
        dialog.lift()
        
        while True:
            try:
                if not dialog.winfo_exists():
                    break
                dialog.update()
                pygame.time.wait(10)
            except tk.TclError:
                break

        try:
            root.withdraw()
        except tk.TclError:
            pass
        self._reset_mouse_state()

        return result['action']

    def close_editor(self):
        """Close editor (with unsaved changes check)"""
        if self.dirty:
            action = self._ask_save_discard_dialog()
            
            if action == 'save':
                self.save_changes()
                # If save_changes succeeded, self.dirty will be False
                if not self.dirty:
                    self.running = False
            elif action == 'save_as':
                # save_as_session sets self.dirty = False on success
                self.save_as_session()
                if not self.dirty:
                    self.running = False
            elif action == 'discard':
                self.logger.info("Discarded unsaved changes; reverting to baseline before exit")
                self.revert_to_baseline()
                self.running = False
            # 'cancel' or None -> do nothing, stay running
        else:
            self.running = False

    # Canvas navigation
    def move_up(self):
        """Move canvas view up"""
        self.transform.lower_left_corner = (
            self.transform.lower_left_corner[0],
            self.transform.lower_left_corner[1] + 20 / self.transform.map_scale
        )

    def move_down(self):
        """Move canvas view down"""
        self.transform.lower_left_corner = (
            self.transform.lower_left_corner[0],
            self.transform.lower_left_corner[1] - 20 / self.transform.map_scale
        )

    def move_left(self):
        """Move canvas view left"""
        self.transform.lower_left_corner = (
            self.transform.lower_left_corner[0] - 20 / self.transform.map_scale,
            self.transform.lower_left_corner[1]
        )

    def move_right(self):
        """Move canvas view right"""
        self.transform.lower_left_corner = (
            self.transform.lower_left_corner[0] + 20 / self.transform.map_scale,
            self.transform.lower_left_corner[1]
        )

    def run(self):
        """Main event loop"""
        while self.running:
            self._update_active_dialog()

            # Check if shutdown was requested via signal (SIGTERM from parent process)
            if self.signal_shutdown_requested:
                self.logger.info("Processing signal shutdown request...")
                self.signal_shutdown_requested = False  # Reset flag
                self.close_editor()
                # If close_editor() didn't set running=False (user cancelled), continue
                if self.running:
                    self.logger.info("User cancelled shutdown, continuing...")
                continue

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.close_editor()
                    continue

                if self.active_dialog:
                    continue

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button in [1, 3]:  # Left or right click
                        self.handle_mouse_down(event.pos, event.button)
                    elif event.button in [4, 5]:  # Mouse wheel
                        self.handle_mouse_wheel(1 if event.button == 4 else -1, event.pos)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.handle_mouse_up(event.pos, event.button)
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_motion(event.pos)
                elif event.type == pygame.KEYDOWN:
                    mods = pygame.key.get_mods()
                    if event.key == pygame.K_w and (mods & (pygame.KMOD_CTRL | pygame.KMOD_META | pygame.KMOD_GUI)):
                        if self._has_open_tk_dialog():
                            continue
                        self.close_editor()
                        continue
                    if event.key == pygame.K_ESCAPE:
                        if self.move_mode:
                            self.exit_move_mode()
                        else:
                            self.selected_item = None
                            self.selected_item_world_pos = None
                            self.update_button_states()
                    elif event.key == pygame.K_DELETE:
                        self.delete_selected()
                    elif event.key == pygame.K_m:
                        self.toggle_move_mode()
                    elif event.key == pygame.K_e:
                        self.logger.info("Edit shortcut (E) pressed")
                        self.edit_selected_item()
                    elif event.key == pygame.K_d:
                        self.logger.info("Duplicate shortcut (D) pressed")
                        self.duplicate_selected_item()
                    elif event.key == pygame.K_g:
                        self.toggle_snap_to_grid()
                    elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                        # Zoom in with + or =
                        self.current_zoom_index = min(self.current_zoom_index + 1, len(self.zoom_levels) - 1)
                        self.transform.map_scale = self.zoom_levels[self.current_zoom_index]
                        self.update_slider_position()
                    elif event.key == pygame.K_MINUS or event.key == pygame.K_UNDERSCORE:
                        # Zoom out with - or _
                        self.current_zoom_index = max(self.current_zoom_index - 1, 0)
                        self.transform.map_scale = self.zoom_levels[self.current_zoom_index]
                        self.update_slider_position()

            self._update_active_dialog()

            # Draw
            self.screen.fill(BG_COLOR)
            self.draw_grid()

            # Draw items (obstacles -> targets -> drones)
            for obstacle in self.obstacles:
                self.draw_obstacle(obstacle)
            for target in self.targets:
                self.draw_target(target)
            for drone in self.drones:
                self.draw_drone(drone)

            # Draw UI
            self.draw_toolbar()
            self.draw_canvas_controls()
            self.draw_minimap()
            self.draw_status_bar()

            # Draw move mode indicator (on top of everything)
            if self.move_mode:
                self.draw_move_mode_indicator()

            pygame.display.flip()
            self.clock.tick(30)  # 30 FPS

        pygame.quit()

        # Ensure Tk resources are cleaned up so no phantom windows remain
        self._shutdown_tk_subsystem()


def start_session_editor(session_id: str, session_data: Dict[str, Any],
                        on_saved: Optional[callable] = None, save_signal_file: Optional[str] = None):
    """Start the session editor

    Args:
        session_id: Session ID to edit
        session_data: Session data dictionary
        on_saved: Optional callback function to call when session is saved
        save_signal_file: Optional file path to notify GUI controller about saves
    """
    editor = SessionEditor(session_id, session_data, on_saved, save_signal_file)
    editor.run()
