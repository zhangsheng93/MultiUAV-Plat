"""
MultiUAV-Plat Server System - Pygame UI Interface

Copyright (C) 2026 MultiUAV-Plat Server System Project

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import pygame
import pygame.gfxdraw as gfxdraw
import sys
import os
import math
import re
import threading
import time
import webbrowser
from typing import Dict, List, Tuple, Optional

# --- macOS App Reopen Fix ---
# This addresses a crash on macOS when the dock icon is clicked.
# It works by using ctypes to register a no-op handler for the
# 'reopen' Apple event, preventing the Tcl/Tk backend (which may
# be initialized by other libraries) from crashing.
if sys.platform == 'darwin':
    try:
        import ctypes
        from ctypes.util import find_library

        # Define a C callback function signature for the event handler
        # The actual signature is OSErr(const AppleEvent *ev, AppleEvent *reply, long ref)
        EventHandlerProcPtr = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long)

        def _handle_reopen_app_event(event, reply, ref_con):
            """A no-op handler for the reopen event."""
            # Returning noErr is enough to prevent the crash.
            return 0  # noErr

        # Convert the Python function to a C function pointer
        _reopen_handler_c = EventHandlerProcPtr(_handle_reopen_app_event)

        def install_reopen_handler():
            """Installs the event handler for the 'reopen' application event."""
            app_services = ctypes.cdll.LoadLibrary(find_library('ApplicationServices'))
            
            # Event class and ID for 'reopen' ('aevt'/'rapp') and 'open' ('aevt'/'oapp')
            kCoreEventClass = int.from_bytes(b'aevt', 'big')
            kAEReopenApplication = int.from_bytes(b'rapp', 'big')
            kAEGotRequiredParams = int.from_bytes(b'oapp', 'big')

            # Install the handler for both reopen and open events.
            app_services.AEInstallEventHandler(kCoreEventClass, kAEReopenApplication, _reopen_handler_c, 0, False)
            app_services.AEInstallEventHandler(kCoreEventClass, kAEGotRequiredParams, _reopen_handler_c, 0, False)

    except (ImportError, OSError, AttributeError) as e:
        print(f"macOS reopen fix: Could not install event handler: {e}", file=sys.stderr)
        install_reopen_handler = lambda: None
else:
    # On other platforms, create a dummy function.
    install_reopen_handler = lambda: None
# --- End macOS App Reopen Fix ---

from config.util import distance as euclidean_distance

# Import controllers and models
from controllers.drone_controller import DroneController
from controllers.target_controller import TargetController
from controllers.obstacle_controller import ObstacleController
from controllers.environment_controller import EnvironmentController
from controllers.session_controller import SessionController
from models.session import DEFAULT_REQUEST_HISTORY_LIMIT
from models.drone import DroneCommand

from ui.font_utils import safe_sys_font

DEFAULT_UI_FONT = "alibabapuhuiti"

# Constants
BASE_SCREEN_WIDTH = 1024
BASE_SCREEN_HEIGHT = 768
BASE_UI_RADIUS_MIN = 5
SCREEN_WIDTH = BASE_SCREEN_WIDTH
SCREEN_HEIGHT = BASE_SCREEN_HEIGHT
UI_RADIUS_MIN = BASE_UI_RADIUS_MIN
# --- UI Theme Palette (centralized) ---
BG_COLOR = (245, 245, 250)           # Light background
GRID_COLOR = (220, 225, 230)         # Soft grid
TEXT_COLOR = (30, 30, 30)            # Dark readable text
WHITE = (255, 255, 255)
TEXT_DISABLED = (120, 120, 120)
AXIS_COLOR = (100, 100, 110)
TICK_COLOR = (120, 120, 130)

# Status colors
STATUS_OK = (0, 255, 0)
STATUS_WARN = (255, 165, 0)
STATUS_ERROR = (255, 0, 0)
CYAN = (0, 255, 255)
GRAY = (128, 128, 128)
LINK_COLOR = (0, 90, 180)
LINK_HOVER_COLOR = (0, 120, 255)

# Controls
BUTTON_BG = (235, 235, 240)
BUTTON_BORDER = (200, 200, 210)
ACTIVE_BUTTON_BG = (220, 245, 220)
ACTIVE_BUTTON_BORDER = (190, 220, 190)
DISABLED_BUTTON_BG = (230, 230, 230)
DISABLED_BUTTON_BORDER = (200, 200, 200)

# Canvas controls and slider
CANVAS_BUTTON_BG = (235, 235, 240)
CANVAS_BUTTON_BORDER = (200, 200, 210)
SLIDER_TRACK = (230, 230, 230)
SLIDER_BORDER = (200, 200, 210)
SLIDER_HANDLE = (180, 180, 180)
SLIDER_HANDLE_BORDER = (120, 120, 120)

# Panels and bars
PANEL_BG = (235, 235, 240)
PANEL_BORDER = (200, 200, 210)
STATUS_BAR_BG = (235, 235, 240)

# Selection highlight
SELECT_BORDER = (160, 160, 160)
MINIMAP_SELECTION_HIGHLIGHT = (255, 255, 0)

# Drone path trail color (very light blue)
DRONE_PATH_TRAIL_COLOR = (173, 216, 230)  # Light blue
DEFAULT_PATH_STEPS = 10

DRONE_COLORS = {
    "idle": (100, 100, 100),      # Gray
    "ready": (0, 255, 0),        # Green
    "taking_off": (0, 255, 255),  # Cyan
    "flying": (0, 0, 255),       # Blue
    "moving": (255, 165, 0),     # Orange
    "hovering": (0, 255, 255),   # Cyan
    "landing": (255, 255, 0),    # Yellow
    "emergency": (255, 0, 0),    # Red
    "offline": (50, 50, 50)      # Dark gray
}

TARGET_COLORS = {
    "fixed": (255, 200, 0),      # Gold (includes points of interest)
    "moving": (255, 100, 100),   # Light red
    "waypoint": (0, 255, 100),   # Light green
    "circle": (0, 100, 255),    # deep sky blue
    "polygon": (0, 200, 255)      #  sky blue
}

OBSTACLE_COLORS = {
    "point": (21, 21, 30),      # Black
    "circle": (139, 69, 19),     # Brown
    "ellipse": (82, 82, 122),    # Dark slate blue
    "polygon": (105, 105, 105),  # Dim gray
}


def get_app_version() -> str:
    """Read the application version from main.py without importing main."""
    for module_name in ("__main__", "main"):
        module = sys.modules.get(module_name)
        version = getattr(module, "VERSION", None) if module else None
        if isinstance(version, str) and version:
            return version

    candidate_paths = []
    if getattr(sys, "frozen", False):
        candidate_paths.append(os.path.join(getattr(sys, "_MEIPASS", ""), "main.py"))
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate_paths.append(os.path.join(project_root, "main.py"))

    for main_path in candidate_paths:
        if not main_path:
            continue
        try:
            with open(main_path, "r", encoding="utf-8") as main_file:
                match = re.search(r'^VERSION\s*=\s*"([^"]+)"', main_file.read(), re.MULTILINE)
            if match:
                return match.group(1)
        except OSError:
            continue

    return "unknown"


def format_enum_value(value: str) -> str:
    """Format enum values to be more human-readable.

    Converts:
    - snake_case to Title Case
    - underscores to spaces

    Examples:
        'take_off' -> 'Take Off'
        'moving' -> 'Moving'
        'area_search' -> 'Area Search'
    """
    if not value:
        return value
    # Replace underscores with spaces and title case each word
    return value.replace('_', ' ').title()


class DroneUI:
    def __init__(self, drone_controller=None, target_controller=None, obstacle_controller=None,
                 environment_controller=None, session_controller=None, confirm_on_close=False,
                 ui_drone_control=False,
                 request_history_limit=DEFAULT_REQUEST_HISTORY_LIMIT):
        if "SDL_VIDEO_HIGHDPI_DISABLED" not in os.environ:
            # Allow SDL to request high-DPI framebuffers when the platform supports them.
            os.environ["SDL_VIDEO_HIGHDPI_DISABLED"] = "0"

        # On macOS, install a handler to prevent crashes when the dock icon is clicked.
        # This must be done before pygame.init().
        if sys.platform == 'darwin':
            install_reopen_handler()

        pygame.init()
        self.ui_scale = self._detect_ui_scale()

        global SCREEN_WIDTH, SCREEN_HEIGHT, UI_RADIUS_MIN
        SCREEN_WIDTH = max(BASE_SCREEN_WIDTH, int(round(BASE_SCREEN_WIDTH * self.ui_scale)))
        SCREEN_HEIGHT = max(BASE_SCREEN_HEIGHT, int(round(BASE_SCREEN_HEIGHT * self.ui_scale)))
        UI_RADIUS_MIN = max(BASE_UI_RADIUS_MIN, int(round(BASE_UI_RADIUS_MIN * self.ui_scale)))

        # Initialize controllers (use provided or create new ones)
        self.obstacle_controller = obstacle_controller or ObstacleController()
        self.environment_controller = environment_controller or EnvironmentController()
        self.target_controller = target_controller or TargetController(obstacle_controller=self.obstacle_controller)
        self.drone_controller = drone_controller or DroneController(
            obstacle_controller=self.obstacle_controller,
            environment_controller=self.environment_controller,
            target_controller=self.target_controller
        )
        self.session_controller = session_controller or SessionController(
            drone_controller=self.drone_controller,
            target_controller=self.target_controller,
            obstacle_controller=self.obstacle_controller,
            environment_controller=self.environment_controller,
            request_history_limit=request_history_limit,
        )
        if session_controller is not None:
            self.session_controller.set_request_history_limit(request_history_limit)
        # Set session controller reference in drone controller for command tracking
        self.drone_controller.set_session_controller(self.session_controller)

        # Set window icon
        try:
            # Get the correct path for the icon (works in both dev and PyInstaller)
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                base_path = sys._MEIPASS
            else:
                # Running in development
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            icon_path = os.path.join(base_path, 'ui', 'img', 'drone.png')
            if os.path.exists(icon_path):
                icon = pygame.image.load(icon_path)
                pygame.display.set_icon(icon)
        except Exception as e:
            print(f"Warning: Could not load window icon: {e}")

        pygame.display.set_caption("MultiUAV-Plat Server System")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = safe_sys_font(DEFAULT_UI_FONT, self._scale_px(15))
        # Unified canvas label font for drones, targets, and obstacles
        self.canvas_label_font = safe_sys_font(DEFAULT_UI_FONT, self._scale_px(10))
        self.large_font = safe_sys_font(DEFAULT_UI_FONT, self._scale_px(22))
        # Smaller fonts for details panel
        self.details_font = safe_sys_font(DEFAULT_UI_FONT, self._scale_px(14))
        self.details_title_font = safe_sys_font(DEFAULT_UI_FONT, self._scale_px(18))
        
        # UI state
        self.drones = []
        self.targets = []
        self.obstacles = []
        self.session = None  # Current session data
        self.task_progress = None  # Task progress data
        self.selected_drone = None
        self.selected_target = None
        self.selected_obstacle = None
        self.lower_left_corner = (0, 0)  # World coordinates of the canvas lower-left corner
        self.pending_title_update = None  # Store pending window title update (must happen on main thread)
        self._deferred_canvas_labels = []

        # Path visualization settings per drone (UI layer, not stored in drone model)
        # Format: {drone_id: keep_path_steps}
        # Special values: 0=hide, 1=one segment, -1=all, N>1=last N positions
        self.default_path_steps = DEFAULT_PATH_STEPS
        self.drone_path_settings = {}  # Falls back to default_path_steps for each drone
        self.show_object_labels = True

        # Canvas margins for coordinate system (origin near bottom-left corner)
        self.margin_x = self._scale_px(80)  # pixels from left edge
        self.margin_y = self._scale_px(60)  # pixels from bottom edge

        # Area coverage tracking: {target_id: set of (x, y) grid points covered}
        self.area_coverage = {}

        # Coverage rendering cache: {target_id: (surface, last_point_count, last_scale, last_offset)}
        self.coverage_cache = {}

        # Discrete zoom levels
        self.zoom_levels = [0.1, 0.3, 0.5, 0.7, 0.8, 1, 1.2, 1.5, 2, 3, 5, 10, 20, 50, 100]
        self.current_zoom_index = 5  # Start at zoom level 1 (index 5)
        self.map_scale = self.zoom_levels[self.current_zoom_index]  # Pixels per meter
        self.running = True
        self.confirm_on_close = confirm_on_close
        self.close_action = "close_server"
        self.ui_drone_control = ui_drone_control

        # Store initial view state for reset functionality
        self.initial_lower_left_corner = (0, 0)
        self.initial_zoom_index = 3  # Default zoom level index
        
        # Mouse interaction state
        self.dragging = False
        self.last_mouse_pos = (0, 0)
        self.mouse_down_pos = None  # Track where mouse was pressed down

        # Double-click detection for minimap
        self.last_minimap_click_time = 0
        self.minimap_double_click_threshold = 0.3  # seconds
        self.minimap_visible = True  # Toggle minimap visibility with 'M' key
        
        # UI components
        self.buttons = []
        if self.ui_drone_control:
            self.buttons.append({
                "role": "take_off_land",
                "text": "Take Off",
                "action": self.send_take_off_land_command,
                "rect": pygame.Rect(self._scale_px(20), self._scale_px(20), self._scale_px(100), self._scale_px(30))
            })
        self.buttons.extend([
            {
                "role": "change_selected",
                "text": "Change Selected",
                "action": self.change_selected_object,
                "rect": pygame.Rect(self._scale_px(130), self._scale_px(20), self._scale_px(200), self._scale_px(30))
            },
            {
                "role": "path_display",
                "text": "Path: 10",
                "action": self.cycle_path_display,
                "rect": pygame.Rect(self._scale_px(340), self._scale_px(20), self._scale_px(100), self._scale_px(30))
            },
            {
                "role": "labels",
                "text": "Hide Labels",
                "action": self.toggle_object_labels,
                "rect": pygame.Rect(self._scale_px(450), self._scale_px(20), self._scale_px(130), self._scale_px(30))
            },
            {
                "role": "about",
                "text": "About",
                "action": self._show_about_dialog,
                "rect": pygame.Rect(self._scale_px(590), self._scale_px(20), self._scale_px(90), self._scale_px(30))
            }
        ])
        
        # Track overlapping objects at last click position
        self.overlapping_objects = []
        self.current_selection_index = 0
        self.last_click_pos = None
        
        # Track mouse clicking position for status bar
        self.mouse_click_world_pos = None
        
        # Canvas control buttons (bottom-right corner with proper margins)
        button_size = self._scale_px(35)
        margin = self._scale_px(5)
        edge_margin = self._scale_px(30)  # Extra margin from screen edges
        
        # Calculate positions ensuring everything fits within screen boundaries
        buttons_width = button_size * 3 + margin * 2  # 3 buttons wide
        buttons_height = button_size * 2 + margin * 2 # 2 buttons tall
        
        start_x = SCREEN_WIDTH - buttons_width - edge_margin
        start_y = SCREEN_HEIGHT - buttons_height - edge_margin * 3
        
        self.canvas_buttons = [
            {"text": "↑", "action": self.move_up, "rect": pygame.Rect(start_x + button_size + margin, start_y, button_size, button_size)},
            {"text": "←", "action": self.move_left, "rect": pygame.Rect(start_x, start_y + button_size + margin, button_size, button_size)},
            {"text": "↓", "action": self.move_down, "rect": pygame.Rect(start_x + button_size + margin, start_y + button_size + margin, button_size, button_size)},
            {"text": "→", "action": self.move_right, "rect": pygame.Rect(start_x + (button_size + margin) * 2, start_y + button_size + margin, button_size, button_size)},
        ]
        
        # Zoom slider (horizontal, positioned below the control buttons)
        slider_width = buttons_width  # Match the width of button area
        slider_height = self._scale_px(18)
        slider_x = start_x
        slider_y = start_y + buttons_height + margin * 2  # Position below the buttons
        
        self.zoom_slider = {
            "rect": pygame.Rect(slider_x, slider_y, slider_width, slider_height),
            "min_zoom": self.zoom_levels[0],
            "max_zoom": self.zoom_levels[-1],
            "dragging": False
        }
        
        # Calculate initial slider position based on current zoom
        self.update_slider_position()

        # Auto-fit flag to ensure we only auto-fit once after initial data load
        # IMPORTANT: Initialize BEFORE starting refresh thread to avoid race condition
        self.autofit_done = False

        # Minimap runtime geometry cache (set during draw)
        self._minimap_mini_rect: Optional[pygame.Rect] = None
        self._minimap_content_rect: Optional[pygame.Rect] = None

        # Start data refresh thread (start AFTER all attributes are initialized)
        self.refresh_thread = threading.Thread(target=self.periodic_refresh, daemon=True)
        self.refresh_thread.start()

    def _scale_px(self, value: float, minimum: int = 1) -> int:
        """Scale a base pixel value for high-DPI displays."""
        return max(minimum, int(round(value * self.ui_scale)))

    def _gfx_value_fits(self, *values: int) -> bool:
        """pygame.gfxdraw uses signed 16-bit coordinates/radii internally."""
        limit = 32767
        return all(-limit <= int(value) <= limit for value in values)

    def _detect_ui_scale(self) -> float:
        """Pick a larger render size for dense displays to avoid blurry OS upscaling."""
        env_value = os.environ.get("DRONE_UI_SCALE")
        if env_value:
            try:
                return max(1.0, min(3.0, float(env_value)))
            except ValueError:
                pass

        try:
            display_info = pygame.display.Info()
            desktop_w = max(BASE_SCREEN_WIDTH, int(display_info.current_w))
            desktop_h = max(BASE_SCREEN_HEIGHT, int(display_info.current_h))
        except pygame.error:
            return 1.0

        # Use desktop-size thresholds instead of pure ratios so Retina laptop
        # panels do not get the same scale as large external 4K displays.
        if desktop_w >= 3600 or desktop_h >= 2100:
            return 2.0
        if desktop_w >= 3000 or desktop_h >= 1900:
            return 1.5
        if desktop_w >= 2200 or desktop_h >= 1400:
            return 1.25
        return 1.0

    def _aa_circle(self, color: Tuple[int, int, int], center: Tuple[int, int], radius: int,
                   outline_color: Optional[Tuple[int, int, int]] = None, outline_width: int = 0):
        """Draw a solid circle with a crisp outline."""
        x, y = int(center[0]), int(center[1])
        radius = max(1, int(radius))
        if self._gfx_value_fits(x, y, radius):
            gfxdraw.filled_circle(self.screen, x, y, radius, color)
        else:
            pygame.draw.circle(self.screen, color, (x, y), radius)
        if outline_color and outline_width > 0:
            pygame.draw.circle(self.screen, outline_color, (x, y), radius, max(1, int(outline_width)))

    def _aa_circle_outline(self, color: Tuple[int, int, int], center: Tuple[int, int], radius: int, width: int = 1):
        """Draw a stable circle outline.

        Plain pygame strokes avoid the multi-ring artifacts that appear with
        repeated gfxdraw antialias passes at very large radii.
        """
        x, y = int(center[0]), int(center[1])
        radius = max(1, int(radius))
        pygame.draw.circle(self.screen, color, (x, y), radius, max(1, int(width)))

    def _aa_ellipse(self, color: Tuple[int, int, int], rect: pygame.Rect,
                    outline_color: Optional[Tuple[int, int, int]] = None, outline_width: int = 0):
        """Draw a solid ellipse with a crisp outline."""
        cx, cy = rect.center
        rx = max(1, rect.width // 2)
        ry = max(1, rect.height // 2)
        if self._gfx_value_fits(cx, cy, rx, ry):
            gfxdraw.filled_ellipse(self.screen, cx, cy, rx, ry, color)
        else:
            pygame.draw.ellipse(self.screen, color, rect)
        if outline_color and outline_width > 0:
            pygame.draw.ellipse(self.screen, outline_color, rect, max(1, int(outline_width)))

    def _aa_polygon(self, color: Tuple[int, int, int], points: List[Tuple[int, int]],
                    outline_color: Optional[Tuple[int, int, int]] = None, outline_width: int = 0):
        """Draw a solid polygon with a crisp outline."""
        int_points = [(int(px), int(py)) for px, py in points]
        if len(int_points) < 3:
            return
        if all(self._gfx_value_fits(px, py) for px, py in int_points):
            gfxdraw.filled_polygon(self.screen, int_points, color)
        else:
            pygame.draw.polygon(self.screen, color, int_points)
        if outline_color and outline_width > 0:
            pygame.draw.polygon(self.screen, outline_color, int_points, max(1, int(outline_width)))

    def _aa_line(self, color: Tuple[int, int, int], start: Tuple[int, int], end: Tuple[int, int], width: int = 1):
        """Draw an antialiased line, falling back to a normal line for thicker strokes."""
        start_i = (int(start[0]), int(start[1]))
        end_i = (int(end[0]), int(end[1]))
        if width <= 1 and self._gfx_value_fits(start_i[0], start_i[1], end_i[0], end_i[1]):
            gfxdraw.line(self.screen, start_i[0], start_i[1], end_i[0], end_i[1], color)
        else:
            pygame.draw.line(self.screen, color, start_i, end_i, int(width))

    def _show_close_confirmation_dialog(self) -> str:
        """Show a close confirmation dialog and return selected action.

        Returns:
            "close_server": Close UI and server
            "close_ui_only": Close UI only and keep server running
            "cancel": Keep UI open
        """
        dialog_w, dialog_h = self._scale_px(620), self._scale_px(240)
        dialog_rect = pygame.Rect(
            (SCREEN_WIDTH - dialog_w) // 2,
            (SCREEN_HEIGHT - dialog_h) // 2,
            dialog_w,
            dialog_h
        )
        button_y = dialog_rect.y + dialog_h - self._scale_px(70)
        btn_close_server = pygame.Rect(dialog_rect.x + self._scale_px(25), button_y, self._scale_px(180), self._scale_px(40))
        btn_close_ui = pygame.Rect(dialog_rect.x + self._scale_px(220), button_y, self._scale_px(180), self._scale_px(40))
        btn_cancel = pygame.Rect(dialog_rect.x + self._scale_px(415), button_y, self._scale_px(180), self._scale_px(40))

        while True:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "cancel"
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "cancel"
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        return "cancel"
                    if event.key == pygame.K_1:
                        return "close_server"
                    if event.key == pygame.K_2:
                        return "close_ui_only"
                    if event.key == pygame.K_3:
                        return "cancel"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_close_server.collidepoint(event.pos):
                        return "close_server"
                    if btn_close_ui.collidepoint(event.pos):
                        return "close_ui_only"
                    if btn_cancel.collidepoint(event.pos):
                        return "cancel"

            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 130))
            self.screen.blit(overlay, (0, 0))

            pygame.draw.rect(self.screen, WHITE, dialog_rect, border_radius=self._scale_px(10))
            pygame.draw.rect(self.screen, PANEL_BORDER, dialog_rect, self._scale_px(2), border_radius=self._scale_px(10))

            title = self.large_font.render("Close Application", True, TEXT_COLOR)
            msg1 = self.font.render("Choose what to do before closing this window:", True, TEXT_COLOR)
            msg2 = self.font.render("Do you want to close this interface now?", True, TICK_COLOR)
            self.screen.blit(title, (dialog_rect.x + self._scale_px(20), dialog_rect.y + self._scale_px(22)))
            self.screen.blit(msg1, (dialog_rect.x + self._scale_px(20), dialog_rect.y + self._scale_px(72)))
            self.screen.blit(msg2, (dialog_rect.x + self._scale_px(20), dialog_rect.y + self._scale_px(98)))

            for rect, label in (
                (btn_close_server, "Close Server"),
                (btn_close_ui, "Close UI Only"),
                (btn_cancel, "Cancel"),
            ):
                hovered = rect.collidepoint(mouse_pos)
                is_default = rect == btn_cancel and not (
                    btn_close_server.collidepoint(mouse_pos)
                    or btn_close_ui.collidepoint(mouse_pos)
                    or btn_cancel.collidepoint(mouse_pos)
                )
                pygame.draw.rect(
                    self.screen,
                    ACTIVE_BUTTON_BG if (hovered or is_default) else BUTTON_BG,
                    rect,
                    border_radius=8
                )
                pygame.draw.rect(
                    self.screen,
                    ACTIVE_BUTTON_BORDER if (hovered or is_default) else BUTTON_BORDER,
                    rect,
                    2,
                    border_radius=8
                )
                label_surf = self.font.render(label, True, TEXT_COLOR)
                self.screen.blit(
                    label_surf,
                    (rect.centerx - label_surf.get_width() // 2, rect.centery - label_surf.get_height() // 2)
                )

            pygame.display.flip()
            self.clock.tick(30)

    def _show_about_dialog(self):
        """Show application metadata, copyright, and project links."""
        dialog_w, dialog_h = self._scale_px(760), self._scale_px(430)
        dialog_rect = pygame.Rect(
            (SCREEN_WIDTH - dialog_w) // 2,
            (SCREEN_HEIGHT - dialog_h) // 2,
            dialog_w,
            dialog_h
        )
        content_x = dialog_rect.x + self._scale_px(28)
        content_y = dialog_rect.y + self._scale_px(78)
        row_gap = self._scale_px(27)
        label_w = self._scale_px(92)
        ok_button = pygame.Rect(
            dialog_rect.centerx - self._scale_px(55),
            dialog_rect.bottom - self._scale_px(62),
            self._scale_px(110),
            self._scale_px(38),
        )
        background = self.screen.copy()
        version = get_app_version()
        info_rows = [
            ("App", "MultiUAV-Plat Server System"),
            ("Version", version),
            ("Description", "Multi-Drone Coordinative Planning Platform"),
            ("Copyright", "Copyright (C) 2026 MultiUAV-Plat Server System Project"),
            ("License", "Licensed under GNU GPL v3"),
            ("Paper", "https://arxiv.org/abs/2606.31073"),
            ("Project", "https://github.com/zhangsheng93/MultiUAV-Plat"),
            ("Website", "https://zhangsheng93.github.io/multiuavweb/"),
        ]
        link_rects = []

        while True:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                        return
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if ok_button.collidepoint(event.pos):
                        return
                    link_clicked = False
                    for rect, url in link_rects:
                        if rect.collidepoint(event.pos):
                            try:
                                webbrowser.open(url)
                            except Exception as e:
                                print(f"Warning: Could not open URL {url}: {e}", file=sys.stderr)
                            link_clicked = True
                            break
                    if not link_clicked and not dialog_rect.collidepoint(event.pos):
                        return

            self.screen.blit(background, (0, 0))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 130))
            self.screen.blit(overlay, (0, 0))

            pygame.draw.rect(self.screen, WHITE, dialog_rect, border_radius=self._scale_px(10))
            pygame.draw.rect(self.screen, PANEL_BORDER, dialog_rect, self._scale_px(2), border_radius=self._scale_px(10))

            title = self.large_font.render("About MultiUAV-Plat", True, TEXT_COLOR)
            self.screen.blit(title, (content_x, dialog_rect.y + self._scale_px(26)))

            current_link_rects = []
            for index, (label, value) in enumerate(info_rows):
                row_y = content_y + index * row_gap
                label_surf = self.details_font.render(f"{label}:", True, TICK_COLOR)
                value_pos = (content_x + label_w, row_y)
                value_rect = None
                is_link = value.startswith("https://")
                if is_link:
                    value_rect = self.details_font.render(value, True, LINK_COLOR).get_rect(topleft=value_pos)
                    current_link_rects.append((value_rect, value))
                is_hovered_link = bool(value_rect and value_rect.collidepoint(mouse_pos))
                value_color = LINK_HOVER_COLOR if is_hovered_link else (LINK_COLOR if is_link else TEXT_COLOR)
                value_surf = self.details_font.render(value, True, value_color)
                self.screen.blit(label_surf, (content_x, row_y))
                self.screen.blit(value_surf, value_pos)
                if is_hovered_link:
                    underline_y = value_rect.bottom + self._scale_px(1)
                    pygame.draw.line(
                        self.screen,
                        LINK_HOVER_COLOR,
                        (value_rect.left, underline_y),
                        (value_rect.right, underline_y),
                        self._scale_px(1),
                    )
            link_rects = current_link_rects

            hovered = ok_button.collidepoint(mouse_pos)
            pygame.draw.rect(
                self.screen,
                ACTIVE_BUTTON_BG if hovered else BUTTON_BG,
                ok_button,
                border_radius=self._scale_px(8)
            )
            pygame.draw.rect(
                self.screen,
                ACTIVE_BUTTON_BORDER if hovered else BUTTON_BORDER,
                ok_button,
                self._scale_px(2),
                border_radius=self._scale_px(8)
            )
            ok_surf = self.font.render("OK", True, TEXT_COLOR)
            self.screen.blit(
                ok_surf,
                (ok_button.centerx - ok_surf.get_width() // 2, ok_button.centery - ok_surf.get_height() // 2)
            )

            pygame.display.flip()
            self.clock.tick(30)
    
    def world_to_screen(self, x: float, y: float) -> Tuple[int, int]:
        """Convert world coordinates to screen coordinates

        Origin (0,0) is positioned near the bottom-left corner of the canvas.
        X increases to the right, Y increases upward (standard mathematical coordinates).
        """
        screen_x = int(self.margin_x + (x - self.lower_left_corner[0]) * self.map_scale)
        screen_y = int(SCREEN_HEIGHT - self.margin_y - (y - self.lower_left_corner[1]) * self.map_scale)
        return screen_x, screen_y

    def screen_to_world(self, screen_x: int, screen_y: int) -> Tuple[float, float]:
        """Convert screen coordinates to world coordinates

        Origin (0,0) is positioned near the bottom-left corner of the canvas.
        X increases to the right, Y increases upward (standard mathematical coordinates).
        """
        world_x = self.lower_left_corner[0] + (screen_x - self.margin_x) / self.map_scale
        world_y = self.lower_left_corner[1] + (SCREEN_HEIGHT - self.margin_y - screen_y) / self.map_scale
        return world_x, world_y
    
    def draw_grid(self):
        """Draw a grid on the map for reference"""
        # Calculate grid spacing in pixels
        grid_spacing = self._scale_px(20)  # pixels

        # Calculate world coordinates for grid lines based on bottom-left origin
        visible_width = (SCREEN_WIDTH - self.margin_x) / self.map_scale
        visible_height = (SCREEN_HEIGHT - self.margin_y) / self.map_scale

        # Extend grid coverage into the screen margins so axes feel continuous
        start_x = int(self.lower_left_corner[0] - self.margin_x / self.map_scale)
        end_x = int(self.lower_left_corner[0] + visible_width)
        start_y = int(self.lower_left_corner[1] - self.margin_y / self.map_scale)
        end_y = int(self.lower_left_corner[1] + visible_height)
        
        # Round to nearest grid_spacing/map_scale
        grid_world_spacing = grid_spacing / self.map_scale
        start_x = math.floor(start_x / grid_world_spacing) * grid_world_spacing
        start_y = math.floor(start_y / grid_world_spacing) * grid_world_spacing
        
        # Draw vertical grid lines
        x = start_x
        while x <= end_x:
            start_point = self.world_to_screen(x, start_y)
            end_point = self.world_to_screen(x, end_y)
            self._aa_line(GRID_COLOR, start_point, end_point, 1)
            x += grid_world_spacing
        
        # Draw horizontal grid lines
        y = start_y
        while y <= end_y:
            start_point = self.world_to_screen(start_x, y)
            end_point = self.world_to_screen(end_x, y)
            self._aa_line(GRID_COLOR, start_point, end_point, 1)
            y += grid_world_spacing

    def _nice_tick_step(self, raw_step: float) -> float:
        """Return a 'nice' step size (1, 2, 5 * 10^n) for axis ticks."""
        if raw_step <= 0:
            return 1.0
        exponent = math.floor(math.log10(raw_step))
        fraction = raw_step / (10 ** exponent)
        if fraction <= 1:
            nice = 1
        elif fraction <= 2:
            nice = 2
        elif fraction <= 5:
            nice = 5
        else:
            nice = 10
        return nice * (10 ** exponent)

    def _format_axis_value(self, value: float, step: float) -> str:
        """Format axis labels based on step size to avoid clutter."""
        step = abs(step)
        if step >= 1:
            if abs(value - round(value)) < 1e-6:
                return f"{int(round(value))}"
            return f"{value:.1f}"
        if step >= 0.1:
            return f"{value:.1f}"
        if step >= 0.01:
            return f"{value:.2f}"
        return f"{value:.3f}"

    def draw_axes(self):
        """Draw X/Y axes with scaled tick marks and labels."""
        if self.map_scale <= 0:
            return

        axis_x = max(self._scale_px(10), self.margin_x - self._scale_px(40))
        axis_y = min(SCREEN_HEIGHT - self._scale_px(5), SCREEN_HEIGHT - self.margin_y + self._scale_px(5))

        # Avoid drawing through the top button row.
        buttons_bottom = max((btn["rect"].bottom for btn in self.buttons), default=0)
        axis_top = min(max(buttons_bottom + self._scale_px(10), 0), axis_y - self._scale_px(20))

        # Axis lines
        self._aa_line(AXIS_COLOR, (axis_x, axis_y), (SCREEN_WIDTH - self._scale_px(10), axis_y), self._scale_px(2))
        self._aa_line(AXIS_COLOR, (axis_x, axis_y), (axis_x, axis_top), self._scale_px(2))

        # Determine visible world bounds along axes
        world_x_min = self.lower_left_corner[0]
        world_x_max = self.lower_left_corner[0] + (SCREEN_WIDTH - axis_x) / self.map_scale
        world_y_min = self.lower_left_corner[1]
        world_y_max = self.lower_left_corner[1] + (SCREEN_HEIGHT - axis_top) / self.map_scale

        # Target ~80px between ticks
        target_px = float(self._scale_px(80))
        step = self._nice_tick_step(target_px / self.map_scale)
        if step <= 0:
            return

        tick_len = self._scale_px(6)
        label_offset = self._scale_px(4)
        max_ticks = 500

        # X-axis ticks and labels
        start_x = math.floor(world_x_min / step) * step
        tick_count = 0
        x = start_x
        while x <= world_x_max and tick_count < max_ticks:
            sx, sy = self.world_to_screen(x, world_y_min)
            if axis_x <= sx <= SCREEN_WIDTH - self._scale_px(10):
                self._aa_line(TICK_COLOR, (sx, axis_y), (sx, axis_y + tick_len), 1)
                label = self._format_axis_value(x, step)
                text = self.canvas_label_font.render(label, True, TEXT_COLOR)
                self.screen.blit(text, (sx - text.get_width() // 2, axis_y + tick_len + label_offset))
            x += step
            tick_count += 1

        # Y-axis ticks and labels
        start_y = math.floor(world_y_min / step) * step
        tick_count = 0
        y = start_y
        while y <= world_y_max and tick_count < max_ticks:
            sx, sy = self.world_to_screen(world_x_min, y)
            if axis_top <= sy <= axis_y:
                self._aa_line(TICK_COLOR, (axis_x, sy), (axis_x - tick_len, sy), 1)
                label = self._format_axis_value(y, step)
                text = self.canvas_label_font.render(label, True, TEXT_COLOR)
                self.screen.blit(text, (axis_x - tick_len - label_offset - text.get_width(), sy - text.get_height() // 2))
            y += step
            tick_count += 1

        # Axis labels
        x_label = self.canvas_label_font.render("X (m)", True, TEXT_COLOR)
        y_label = self.canvas_label_font.render("Y (m)", True, TEXT_COLOR)
        self.screen.blit(x_label, (SCREEN_WIDTH - x_label.get_width() - self._scale_px(12), axis_y + tick_len + label_offset + self._scale_px(12)))
        self.screen.blit(y_label, (axis_x - y_label.get_width() - self._scale_px(10), axis_top - y_label.get_height() - self._scale_px(4)))

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
            # Add a default padding around drones to ensure they create a non-zero area
            padding = 10.0  # meters
            px, py = d["position"]["x"], d["position"]["y"]
            update_bounds(px - padding, py - padding)
            update_bounds(px + padding, py + padding)

        # Targets (include radius)
        for t in self.targets:
            cx = t["position"]["x"]
            cy = t["position"]["y"]
            r = t.get("radius", 0) or 0
            update_bounds(cx - r, cy - r)
            update_bounds(cx + r, cy + r)

        # Obstacles: circle uses radius, polygon uses vertices, others use radius/size
        for o in self.obstacles:
            ox = o["position"]["x"]
            oy = o["position"]["y"]
            if o["type"] == "circle":
                r = o.get("radius", 0) or 0
                update_bounds(ox - r, oy - r)
                update_bounds(ox + r, oy + r)
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

        return min_x, max_x, min_y, max_y

    def fit_view_to_items(self, padding_ratio: float = 0.1):
        """Fit the view to show all items with appropriate zoom and centering."""
        min_x, max_x, min_y, max_y = self.compute_world_bounds()
        width_span = max(1.0, max_x - min_x)  # Ensure non-zero span
        height_span = max(1.0, max_y - min_y) # Ensure non-zero span

        viewable_width_px = SCREEN_WIDTH - self.margin_x * 2 # Usable area between margins
        viewable_height_px = SCREEN_HEIGHT - self.margin_y * 2 # Usable area between margins

        # Calculate the ideal scale to fit the content
        scale_x = viewable_width_px / width_span
        scale_y = viewable_height_px / height_span
        
        # Use the smaller scale to ensure everything fits, and apply padding
        ideal_scale = min(scale_x, scale_y) * (1 - padding_ratio)
        
        # Cap the maximum initial zoom to prevent excessive zoom-in on small scenes
        ideal_scale = min(ideal_scale, 5.0)

        # Find the closest zoom level in our discrete list that is <= the ideal scale
        chosen_index = 0
        for i, level in enumerate(self.zoom_levels):
            if level <= ideal_scale:
                chosen_index = i
            else:
                # We've gone past the ideal scale, so the previous one was the best fit
                break
        
        self.current_zoom_index = chosen_index
        self.map_scale = self.zoom_levels[self.current_zoom_index]
        self.update_slider_position()

        # Center the view on the content
        center_x = min_x + width_span / 2
        center_y = min_y + height_span / 2
        
        # Calculate the new lower-left corner to center the content
        center_screen_x = self.margin_x + viewable_width_px / 2
        center_screen_y = SCREEN_HEIGHT - self.margin_y - viewable_height_px / 2
        
        # Back-calculate the required lower_left_corner
        # From world_to_screen: screen_x = margin_x + (world_x - ll_x) * scale
        # (screen_x - margin_x) / scale = world_x - ll_x
        # ll_x = world_x - (screen_x - margin_x) / scale
        ll_x = center_x - (center_screen_x - self.margin_x) / self.map_scale
        ll_y = center_y - (SCREEN_HEIGHT - self.margin_y - center_screen_y) / self.map_scale
        
        self.lower_left_corner = (ll_x, ll_y)

        return self.lower_left_corner, chosen_index

    def auto_fit_view(self, padding_ratio: float = 0.05):
        """Auto-fit the initial view to include most items with padding.
        Called once during initial data load."""
        corner, zoom_index = self.fit_view_to_items(padding_ratio)

        # Store this fitted view as the initial state for reset functionality
        self.initial_lower_left_corner = corner
        self.initial_zoom_index = zoom_index
    
    def get_battery_color(self, battery_level: float) -> tuple:
        """Get color based on battery level"""
        if battery_level > 40:
            return STATUS_OK  # Green
        elif battery_level > 10:
            return STATUS_WARN  # Orange
        else:
            return STATUS_ERROR  # Red

    def draw_minimap(self):
        """Draw a bottom-left thumbnail (minimap) with a green viewport rectangle."""
        # Minimap geometry
        margin = self._scale_px(10)
        mini_w = self._scale_px(200)
        mini_h = self._scale_px(140)
        mini_x = margin
        # Reserve extra space for the status bar to avoid overlap
        bottom_reserved = self._scale_px(50)  # ~30 for status bar + extra spacing
        mini_y = SCREEN_HEIGHT - mini_h - bottom_reserved
        mini_rect = pygame.Rect(mini_x, mini_y, mini_w, mini_h)

        # Panel style background
        pygame.draw.rect(self.screen, PANEL_BG, mini_rect)
        pygame.draw.rect(self.screen, PANEL_BORDER, mini_rect, self._scale_px(2))

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
        # Account for bottom-left origin with margins
        # Guard against division by zero or invalid map_scale
        if self.map_scale <= 0 or not isinstance(self.map_scale, (int, float)):
            return  # Skip minimap viewport drawing if map_scale is invalid
        visible_width = (SCREEN_WIDTH - self.margin_x) / self.map_scale
        visible_height = (SCREEN_HEIGHT - self.margin_y) / self.map_scale

        vx_min = self.lower_left_corner[0]
        vx_max = self.lower_left_corner[0] + visible_width
        vy_min = self.lower_left_corner[1]
        vy_max = self.lower_left_corner[1] + visible_height

        try:
            tl = to_mini(vx_min, vy_max)
            br = to_mini(vx_max, vy_min)
            # Ensure width and height are positive for pygame.Rect and explicitly cast to int
            rect_x = int(min(tl[0], br[0]))
            rect_y = int(min(tl[1], br[1]))
            rect_w = max(0, int(abs(br[0] - tl[0])))
            rect_h = max(0, int(abs(br[1] - tl[1])))
            viewport_rect = pygame.Rect(rect_x, rect_y, rect_w, rect_h)
        except (TypeError, ValueError, OverflowError) as e:
            # Skip drawing viewport if coordinates are invalid
            viewport_rect = None
        # Clip viewport to inner content bounds so it never draws outside
        if viewport_rect is not None:
            clipped = viewport_rect.clip(content_rect)
            if clipped.width > 0 and clipped.height > 0:
                pygame.draw.rect(self.screen, STATUS_OK, clipped, 2)  # Green rectangle

        def is_selected(obj_type: str, obj: Dict) -> bool:
            obj_id = obj.get("id")
            if obj_type == "drone":
                return bool(self.selected_drone and obj_id == self.selected_drone.get("id"))
            if obj_type == "target":
                return bool(self.selected_target and obj_id == self.selected_target.get("id"))
            if obj_type == "obstacle":
                return bool(self.selected_obstacle and obj_id == self.selected_obstacle.get("id"))
            return False

        def draw_mini_point(obj_type: str, obj: Dict, color: Tuple[int, int, int]):
            mx, my = to_mini(obj["position"]["x"], obj["position"]["y"])
            pygame.draw.circle(self.screen, color, (mx, my), point_radius)
            if is_selected(obj_type, obj):
                pygame.draw.circle(self.screen, MINIMAP_SELECTION_HIGHLIGHT, (mx, my), point_radius + 4, 2)

        # Draw points for drones, targets, and obstacles
        point_radius = 3
        # Drones
        for d in self.drones:
            color = DRONE_COLORS.get(d.get("status", "idle"), GRAY)
            draw_mini_point("drone", d, color)
        # Targets
        for t in self.targets:
            color = TARGET_COLORS.get(t.get("type", "fixed"), WHITE)
            draw_mini_point("target", t, color)
        # Obstacles (draw center point)
        for o in self.obstacles:
            color = OBSTACLE_COLORS.get(o.get("type", "building"), GRAY)
            draw_mini_point("obstacle", o, color)

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
            self.reset_view()
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

        # Set main view lower-left corner and optional status click indicator
        self.lower_left_corner = (wx, wy)
        self.mouse_click_world_pos = (wx, wy)
        return True
    
    def draw_drone(self, drone: Dict):
        """Draw a drone on the map"""
        # Get UI path display setting for this drone
        drone_id = drone["id"]
        keep_path_steps = self.drone_path_settings.get(drone_id, self.default_path_steps)

        # Draw path trail if enabled and available
        if keep_path_steps != 0:  # 0 means hide path
            path_history = []
            if self.session and "history" in self.session and "path_history" in self.session["history"]:
                path_history = self.session["history"]["path_history"].get(drone_id, [])

            # Determine which positions to display based on keep_path_steps
            if keep_path_steps == -1:
                # Show all positions
                positions_to_draw = path_history
            elif keep_path_steps == 1:
                # Show only last segment (last 2 positions)
                positions_to_draw = path_history[-2:] if len(path_history) >= 2 else path_history
            else:
                # Show last N positions
                positions_to_draw = path_history[-keep_path_steps:] if len(path_history) > keep_path_steps else path_history

            # Draw lines connecting the positions
            if len(positions_to_draw) >= 2:
                for i in range(len(positions_to_draw) - 1):
                    pos1 = positions_to_draw[i]
                    pos2 = positions_to_draw[i + 1]
                    screen_x1, screen_y1 = self.world_to_screen(pos1["x"], pos1["y"])
                    screen_x2, screen_y2 = self.world_to_screen(pos2["x"], pos2["y"])
                    self._aa_line(
                        DRONE_PATH_TRAIL_COLOR,
                        (screen_x1, screen_y1),
                        (screen_x2, screen_y2),
                        self._scale_px(2)
                    )

        # Get drone position and convert to screen coordinates
        x = drone["position"]["x"]
        y = drone["position"]["y"]
        z = drone["position"]["z"]
        screen_x, screen_y = self.world_to_screen(x, y)

        # Get color based on status
        color = DRONE_COLORS.get(drone["status"], WHITE)

        # Draw drone body (icon size halved from previous)
        radius = max(UI_RADIUS_MIN, int(5 * self.map_scale))
        self._aa_circle(color, (screen_x, screen_y), radius)
        
        # Draw battery indicator ring around drone
        battery_level = drone["battery_level"]
        battery_color = self.get_battery_color(battery_level)
        self._aa_circle_outline(battery_color, (screen_x, screen_y), radius + self._scale_px(3), self._scale_px(3))
        
        # Draw drone direction indicator
        heading_rad = math.radians(drone.get("heading", 0))
        indicator_x = screen_x + int(radius * 1.5 * math.sin(heading_rad))
        indicator_y = screen_y - int(radius * 1.5 * math.cos(heading_rad))
        self._aa_line(WHITE, (screen_x, screen_y), (indicator_x, indicator_y), self._scale_px(2))
        
        # Draw selection indicator if this drone is selected
        is_selected = self.selected_drone and drone["id"] == self.selected_drone["id"]
        if is_selected:
            self._aa_circle_outline(SELECT_BORDER, (screen_x, screen_y), radius + self._scale_px(8), self._scale_px(2))
        
        if not self.show_object_labels:
            return

        # Draw drone ID and altitude (use unified canvas label font)
        id_text = self.canvas_label_font.render(f"{drone['name']} (ID: {drone['id']})", True, TEXT_COLOR)
        alt_text = self.canvas_label_font.render(f"Alt: {z:.1f}m", True, TEXT_COLOR)
        status_text = self.canvas_label_font.render(f"Status: {format_enum_value(drone['status'])}", True, TEXT_COLOR)
        
        # Draw battery text with color coding
        battery_text = self.canvas_label_font.render(f"Battery: {battery_level:.1f}%", True, battery_color)
        
        # Tighter vertical spacing for labels using font line height
        line_step = max(self._scale_px(8), int(self.canvas_label_font.get_linesize() * 0.75))
        start_y = screen_y - 3 * line_step
        label_x = screen_x + radius + self._scale_px(5)
        self._queue_canvas_label(
            [
                (id_text, (label_x, start_y)),
                (alt_text, (label_x, start_y + line_step)),
                (status_text, (label_x, start_y + 2 * line_step)),
                (battery_text, (label_x, start_y + 3 * line_step)),
            ],
            selected=bool(is_selected),
        )
    
    def draw_buttons(self):
        """Draw UI buttons"""
        # Draw main control buttons
        for button in self.buttons:
            # Determine if button should be enabled
            button_enabled = True
            button_color = BUTTON_BG
            border_color = BUTTON_BORDER
            
            # Determine button text (dynamic for some buttons)
            button_text = button["text"]
            button_role = button.get("role")
            if button_role == "take_off_land":
                if self.selected_drone:
                    if self.selected_drone["status"] == "idle":
                        button_text = "Take Off"
                    else:
                        button_text = "Land"
                else:
                    button_text = "Take Off"  # Default when no drone selected
            elif button_role == "change_selected":
                if len(self.overlapping_objects) > 1:
                    # Multiple overlapping objects - show change option with counter
                    current_obj = self.overlapping_objects[self.current_selection_index]
                    obj_type = current_obj["type"].capitalize()
                    button_text = f"Change ({self.current_selection_index + 1}/{len(self.overlapping_objects)}) {obj_type}"
                    button_color = ACTIVE_BUTTON_BG  # Light green when active
                    border_color = ACTIVE_BUTTON_BORDER
                elif len(self.overlapping_objects) == 1 or self.selected_drone or self.selected_target or self.selected_obstacle:
                    # Single object selected or any selection exists - show cancel option
                    button_text = "Cancel Selection"
                    button_color = BUTTON_BG  # Normal button color
                    border_color = BUTTON_BORDER
                    button_enabled = True
                else:
                    # No selection - disable button
                    button_text = "Change Selected"
                    button_enabled = False
                    button_color = DISABLED_BUTTON_BG  # Lighter when disabled
                    border_color = DISABLED_BUTTON_BORDER
            elif button_role == "path_display":
                if self.selected_drone:
                    # Show path setting for selected drone
                    drone_id = self.selected_drone["id"]
                    path_setting = self.drone_path_settings.get(drone_id, self.default_path_steps)
                    if path_setting == 0:
                        button_text = "Path: Hide"
                    elif path_setting == 1:
                        button_text = "Path: 1"
                    elif path_setting == -1:
                        button_text = "Path: All"
                    else:
                        button_text = f"Path: {path_setting}"
                else:
                    # Show setting for all drones (use first drone as reference)
                    if self.drones:
                        first_drone_id = self.drones[0]["id"]
                        path_setting = self.drone_path_settings.get(first_drone_id, self.default_path_steps)
                        if path_setting == 0:
                            button_text = "Path: Hide"
                        elif path_setting == 1:
                            button_text = "Path: 1"
                        elif path_setting == -1:
                            button_text = "Path: All"
                        else:
                            button_text = f"Path: {path_setting}"
                    else:
                        path_setting = self.default_path_steps
                        if path_setting == 0:
                            button_text = "Path: Hide"
                        elif path_setting == 1:
                            button_text = "Path: 1"
                        elif path_setting == -1:
                            button_text = "Path: All"
                        else:
                            button_text = f"Path: {path_setting}"
            elif button_role == "labels":
                button_text = "Hide Labels" if self.show_object_labels else "Show Labels"
            
            # Draw button background
            pygame.draw.rect(self.screen, button_color, button["rect"])
            pygame.draw.rect(self.screen, border_color, button["rect"], self._scale_px(2))
            
            # Draw button text
            text_color = TEXT_COLOR if button_enabled else TEXT_DISABLED
            text = self.font.render(button_text, True, text_color)
            text_rect = text.get_rect(center=button["rect"].center)
            self.screen.blit(text, text_rect)
        
        # Draw canvas control buttons
        for button in self.canvas_buttons:
            # Draw button background
            pygame.draw.rect(self.screen, CANVAS_BUTTON_BG, button["rect"])
            pygame.draw.rect(self.screen, CANVAS_BUTTON_BORDER, button["rect"], self._scale_px(2))
            
            # Draw button text
            text = self.font.render(button["text"], True, TEXT_COLOR)
            text_rect = text.get_rect(center=button["rect"].center)
            self.screen.blit(text, text_rect)
        
        # Draw zoom slider
        slider = self.zoom_slider
        # Draw slider track
        pygame.draw.rect(self.screen, SLIDER_TRACK, slider["rect"])
        pygame.draw.rect(self.screen, SLIDER_BORDER, slider["rect"], self._scale_px(2))
        
        # Draw slider handle
        if "handle_rect" in slider:
            pygame.draw.rect(self.screen, SLIDER_HANDLE, slider["handle_rect"])
            pygame.draw.rect(self.screen, SLIDER_HANDLE_BORDER, slider["handle_rect"], 1)
        
        # Draw zoom level text
        zoom_text = f"{self.map_scale:.1f}x"
        zoom_surface = self.font.render(zoom_text, True, TEXT_COLOR)
        zoom_rect = zoom_surface.get_rect(center=(slider["rect"].centerx, slider["rect"].bottom + self._scale_px(12)))
        self.screen.blit(zoom_surface, zoom_rect)
    
    def draw_coverage_optimized(self, target_id: str):
        """Draw area coverage using optimized rendering with viewport culling and batching

        Args:
            target_id: ID of the target whose coverage to draw
        """
        if target_id not in self.area_coverage or not self.area_coverage[target_id]:
            return

        grid_resolution = 2.0
        grid_size_pixels = max(2, int(grid_resolution * self.map_scale))

        # Viewport culling: Calculate world bounds of visible area
        canvas_width = SCREEN_WIDTH - self.margin_x
        canvas_height = SCREEN_HEIGHT - self.margin_y

        # Define a generous buffer (e.g., 25% of the viewport size) to prevent pop-in.
        # This ensures that coverage for large targets near the edge is still rendered.
        buffer_x = (canvas_width / self.map_scale) * 0.25
        buffer_y = (canvas_height / self.map_scale) * 0.25

        view_min_x = self.lower_left_corner[0] - buffer_x
        view_max_x = self.lower_left_corner[0] + (canvas_width / self.map_scale) + buffer_x
        view_min_y = self.lower_left_corner[1] - buffer_y
        view_max_y = self.lower_left_corner[1] + (canvas_height / self.map_scale) + buffer_y

        # Filter points to only those visible in the buffered viewport
        visible_points = []
        for grid_x, grid_y in self.area_coverage[target_id]:
            if view_min_x <= grid_x <= view_max_x and view_min_y <= grid_y <= view_max_y:
                screen_x, screen_y = self.world_to_screen(grid_x, grid_y)
                visible_points.append((screen_x, screen_y))

        # Draw using rectangles (faster than circles) in batches
        if visible_points:
            for sx, sy in visible_points:
                # Draw filled rectangle (faster than circle)
                rect = pygame.Rect(sx - grid_size_pixels//2, sy - grid_size_pixels//2,
                                  grid_size_pixels, grid_size_pixels)
                pygame.draw.rect(self.screen, (0, 255, 0), rect)

    def draw_target(self, target: Dict):
        """Draw a target on the map"""
        # Get target position and convert to screen coordinates
        x = target["position"]["x"]
        y = target["position"]["y"]
        z = target["position"]["z"]
        screen_x, screen_y = self.world_to_screen(x, y)

        # Check if this target has been reached based on session data
        target_reached = False
        target_id = target.get("id")
        target_type = target.get("type", "fixed")

        tracking_status = target.get("tracking_status")
        if target_type == "moving":
            target_reached = tracking_status == "tracked"
        elif self.session and target_id:
            target_reached = bool(target.get("is_reached"))

        # Get color based on target type and reach status
        if target_reached:
            # Only fixed and moving targets change color when reached
            # Circle and polygon targets show progress via coverage tracks instead
            if target_type in ["fixed", "moving"]:
                color = (0, 255, 0)  # Bright green for reached fixed/moving targets
            else:
                color = TARGET_COLORS.get(target_type, WHITE)  # Keep original color for circle/polygon
        else:
            color = TARGET_COLORS.get(target_type, WHITE)
        
        # Draw target based on its type
        if target["type"] == "fixed":
            # Draw a square
            size = max(UI_RADIUS_MIN, int(target["radius"] * self.map_scale))
            rect = pygame.Rect(screen_x - size//2, screen_y - size//2, size, size)
            pygame.draw.rect(self.screen, color, rect)
        elif target["type"] == "moving":
            # Draw a diamond
            size = max(UI_RADIUS_MIN, int(target["radius"] * self.map_scale))
            points = [
                (screen_x, screen_y - size),
                (screen_x + size, screen_y),
                (screen_x, screen_y + size),
                (screen_x - size, screen_y)
            ]
            self._aa_polygon(color, points)
        elif target["type"] == "waypoint":
            # Draw a triangle
            size = max(UI_RADIUS_MIN, int(3 * self.map_scale))
            points = [
                (screen_x, screen_y - size),
                (screen_x + size, screen_y + size),
                (screen_x - size, screen_y + size)
            ]
            self._aa_polygon(color, points)
        elif target["type"] == "circle":
            # Draw a filled circle target
            radius = max(UI_RADIUS_MIN, int((target.get("radius") or 0) * self.map_scale))
            if radius > 0:
                self._aa_circle(color, (screen_x, screen_y), radius)

                # Draw covered area using optimized method
                self.draw_coverage_optimized(target["id"])
        elif target["type"] == "polygon":
            # Draw a polygon target using absolute vertices
            if target.get("vertices"):
                points = []
                for vertex in target["vertices"]:
                    vx = vertex["x"]
                    vy = vertex["y"]
                    screen_vx, screen_vy = self.world_to_screen(vx, vy)
                    points.append((screen_vx, screen_vy))
                if len(points) >= 3:
                    self._aa_polygon(color, points)

                    # Draw covered area using optimized method
                    self.draw_coverage_optimized(target["id"])
        else:  # fixed, moving, waypoint, or unknown type
            # Draw a circle
            size = max(UI_RADIUS_MIN, int(target["radius"] * self.map_scale))
            self._aa_circle(color, (screen_x, screen_y), size)
        
        # Draw selection indicator if this target is selected
        is_selected = self.selected_target and target["id"] == self.selected_target["id"]
        if is_selected:
            if target["type"] == "circle":
                size = int((target.get("radius") or 0) * self.map_scale)
                if size > 0:
                    self._aa_circle_outline(SELECT_BORDER, (screen_x, screen_y), size + self._scale_px(5), self._scale_px(3))
            elif target["type"] == "polygon" and target.get("vertices"):
                sel_points = []
                for vertex in target["vertices"]:
                    vx = vertex["x"]
                    vy = vertex["y"]
                    screen_vx, screen_vy = self.world_to_screen(vx, vy)
                    sel_points.append((screen_vx, screen_vy))
                if len(sel_points) >= 3:
                    # Expand selection outline outward by a margin from centroid
                    cx = sum(p[0] for p in sel_points) / len(sel_points)
                    cy = sum(p[1] for p in sel_points) / len(sel_points)
                    margin_px = self._scale_px(8)
                    expanded = []
                    for (px, py) in sel_points:
                        dx = px - cx
                        dy = py - cy
                        length = math.hypot(dx, dy)
                        if length > 0:
                            ex = int(px + margin_px * dx / length)
                            ey = int(py + margin_px * dy / length)
                        else:
                            ex, ey = px, py
                        expanded.append((ex, ey))
                    pygame.draw.polygon(self.screen, SELECT_BORDER, expanded, self._scale_px(3))
            else:
                # Default selection indicator: small rectangle around position
                size = int((target.get("radius") or 10) * self.map_scale)
                pad = self._scale_px(5)
                rect = pygame.Rect(screen_x - size//2 - pad, screen_y - size//2 - pad, size + pad * 2, size + pad * 2)
                pygame.draw.rect(self.screen, SELECT_BORDER, rect, self._scale_px(2))
        
        if not self.show_object_labels:
            return

        # Draw target name, type, and ID
        name_text = self.canvas_label_font.render(f"{target['name']}", True, TEXT_COLOR)
        type_text = self.canvas_label_font.render(f"Type: {format_enum_value(target['type'])}", True, TEXT_COLOR)
        id_text = self.canvas_label_font.render(f"ID: {target['id']}", True, TEXT_COLOR)
        
        # For polygon targets, move labels outside near the boundary (top-right)
        if target["type"] == "polygon" and target.get("vertices"):
            label_points = []
            for vertex in target["vertices"]:
                screen_vx, screen_vy = self.world_to_screen(vertex["x"], vertex["y"])
                label_points.append((screen_vx, screen_vy))
            if label_points:
                max_x = max(p[0] for p in label_points)
                min_y = min(p[1] for p in label_points)
                label_x = max_x + self._scale_px(10)
                line_step = max(self._scale_px(8), int(self.canvas_label_font.get_linesize() * 0.75))
                label_y = min_y - line_step
                self._queue_canvas_label(
                    [
                        (name_text, (label_x, label_y)),
                        (type_text, (label_x, label_y + line_step)),
                        (id_text, (label_x, label_y + line_step * 2)),
                    ],
                    selected=bool(is_selected),
                )
            else:
                line_step = max(self._scale_px(8), int(self.canvas_label_font.get_linesize() * 0.75))
                label_x = screen_x + self._scale_px(20)
                self._queue_canvas_label(
                    [
                        (name_text, (label_x, screen_y - line_step)),
                        (type_text, (label_x, screen_y)),
                        (id_text, (label_x, screen_y + line_step)),
                    ],
                    selected=bool(is_selected),
                )
        elif target["type"] == "circle":
            line_step = max(self._scale_px(8), int(self.canvas_label_font.get_linesize() * 0.75))
            radius_px = max(UI_RADIUS_MIN, int((target.get("radius") or 0) * self.map_scale))
            label_x = screen_x + radius_px + self._scale_px(10)
            self._queue_canvas_label(
                [
                    (name_text, (label_x, screen_y - line_step)),
                    (type_text, (label_x, screen_y)),
                    (id_text, (label_x, screen_y + line_step)),
                ],
                selected=bool(is_selected),
            )
        else:
            line_step = max(self._scale_px(8), int(self.canvas_label_font.get_linesize() * 0.75))
            label_x = screen_x + self._scale_px(20)
            self._queue_canvas_label(
                [
                    (name_text, (label_x, screen_y - line_step)),
                    (type_text, (label_x, screen_y)),
                    (id_text, (label_x, screen_y + line_step)),
                ],
                selected=bool(is_selected),
            )
    
    def draw_obstacle(self, obstacle: Dict):
        """Draw an obstacle on the map"""
        # Get obstacle position and convert to screen coordinates
        x = obstacle["position"]["x"]
        y = obstacle["position"]["y"]
        screen_x, screen_y = self.world_to_screen(x, y)
        
        # Get color based on obstacle type
        color = OBSTACLE_COLORS.get(obstacle["type"], GRAY)

        # Draw obstacle based on its type
        if obstacle["type"] in ["point", "circle"]:
            # Draw a filled circle
            radius = max(UI_RADIUS_MIN, int(obstacle["radius"] * self.map_scale))
            self._aa_circle(color, (screen_x, screen_y), radius)
        elif obstacle["type"] == "ellipse":
            # Draw an ellipse
            width = max(UI_RADIUS_MIN, int(obstacle["width"] * self.map_scale * 2))
            height = max(UI_RADIUS_MIN, int(obstacle["length"] * self.map_scale * 2))
            rect = pygame.Rect(screen_x - width//2, screen_y - height//2, width, height)
            self._aa_ellipse(color, rect)
        elif obstacle["type"] == "polygon":
            # Draw a filled polygon
            if obstacle.get("vertices"):
                points = []
                for vertex in obstacle["vertices"]:
                    # Vertices are absolute coordinates, not relative to obstacle position
                    vx = vertex["x"]
                    vy = vertex["y"]
                    screen_vx, screen_vy = self.world_to_screen(vx, vy)
                    points.append((screen_vx, screen_vy))

                if len(points) >= 3:
                    self._aa_polygon(color, points)
        else:
            # Default fallback: draw as a rectangle
            radius = obstacle.get("radius") or 10
            size = max(UI_RADIUS_MIN, int(radius * self.map_scale))
            rect = pygame.Rect(screen_x - size//2, screen_y - size//2, size, size)
            pygame.draw.rect(self.screen, color, rect)
        
        # Draw selection indicator if this obstacle is selected
        is_selected = self.selected_obstacle and obstacle["id"] == self.selected_obstacle["id"]
        if is_selected:
            if obstacle["type"] in ["point", "circle"]:
                radius = int(obstacle["radius"] * self.map_scale)
                self._aa_circle_outline(SELECT_BORDER, (screen_x, screen_y), radius + self._scale_px(5), self._scale_px(3))
            elif obstacle["type"] == "ellipse":
                width = int(obstacle["width"] * self.map_scale * 2)
                height = int(obstacle["length"] * self.map_scale * 2)
                pad = self._scale_px(5)
                rect = pygame.Rect(screen_x - width//2 - pad, screen_y - height//2 - pad, width + pad * 2, height + pad * 2)
                pygame.draw.ellipse(self.screen, SELECT_BORDER, rect, self._scale_px(3))
            elif obstacle["type"] == "polygon" and obstacle.get("vertices"):
                # Draw selection outline around polygon boundary
                sel_points = []
                for vertex in obstacle["vertices"]:
                    vx = vertex["x"]
                    vy = vertex["y"]
                    screen_vx, screen_vy = self.world_to_screen(vx, vy)
                    sel_points.append((screen_vx, screen_vy))

                if len(sel_points) >= 3:
                    # Expand selection outline outward by a margin from centroid
                    cx = sum(p[0] for p in sel_points) / len(sel_points)
                    cy = sum(p[1] for p in sel_points) / len(sel_points)
                    margin_px = self._scale_px(8)
                    expanded = []
                    for (px, py) in sel_points:
                        dx = px - cx
                        dy = py - cy
                        length = math.hypot(dx, dy)
                        if length > 0:
                            ex = int(px + margin_px * dx / length)
                            ey = int(py + margin_px * dy / length)
                        else:
                            ex, ey = px, py
                        expanded.append((ex, ey))
                    pygame.draw.polygon(self.screen, SELECT_BORDER, expanded, self._scale_px(3))
            else:
                # Fallback rectangular selection
                radius = obstacle.get("radius") or 10
                size = int(radius * self.map_scale)
                pad = self._scale_px(5)
                rect = pygame.Rect(screen_x - size//2 - pad, screen_y - size//2 - pad, size + pad * 2, size + pad * 2)
                pygame.draw.rect(self.screen, SELECT_BORDER, rect, self._scale_px(3))
        
        if not self.show_object_labels:
            return

        # Draw obstacle name, type, and ID - position based on obstacle size to avoid overlap
        name_text = self.canvas_label_font.render(f"{obstacle['name']}", True, TEXT_COLOR)
        type_text = self.canvas_label_font.render(f"Type: {format_enum_value(obstacle['type'])}", True, TEXT_COLOR)
        id_text = self.canvas_label_font.render(f"ID: {obstacle['id']}", True, TEXT_COLOR)

        line_step = max(self._scale_px(8), int(self.canvas_label_font.get_linesize() * 0.75))

        # Calculate label position based on obstacle type and size
        label_x_offset = self._scale_px(5)  # Small margin from obstacle edge
        if obstacle["type"] in ["point", "circle"]:
            radius = int(obstacle["radius"] * self.map_scale)
            label_x = screen_x + radius + label_x_offset
            label_y = screen_y - line_step
        elif obstacle["type"] == "ellipse":
            width = int(obstacle["width"] * self.map_scale * 2)
            label_x = screen_x + width//2 + label_x_offset
            label_y = screen_y - line_step
        elif obstacle["type"] == "polygon":
            # For polygon, place label at the rightmost point
            if obstacle.get("vertices"):
                max_x = max(vertex["x"] for vertex in obstacle["vertices"])
                screen_max_x, _ = self.world_to_screen(max_x, obstacle["position"]["y"])
                label_x = screen_max_x + label_x_offset
                label_y = screen_y - line_step
            else:
                label_x = screen_x + self._scale_px(25)
                label_y = screen_y - line_step
        else:
            # Default fallback
            radius = obstacle.get("radius") or 10
            size = int(radius * self.map_scale)
            label_x = screen_x + size//2 + label_x_offset
            label_y = screen_y - line_step

        self._queue_canvas_label(
            [
                (name_text, (label_x, label_y)),
                (type_text, (label_x, label_y + line_step)),
                (id_text, (label_x, label_y + line_step * 2)),
            ],
            selected=bool(is_selected),
        )

    def _queue_canvas_label(self, label_items: List[Tuple[pygame.Surface, Tuple[int, int]]], selected: bool = False):
        """Queue canvas labels so they render after all objects; selected labels render last."""
        self._deferred_canvas_labels.append((1 if selected else 0, label_items))

    def draw_deferred_canvas_labels(self):
        """Draw queued canvas labels after objects so labels stay in front."""
        for priority in (0, 1):
            for item_priority, label_items in self._deferred_canvas_labels:
                if item_priority != priority:
                    continue
                for surface, position in label_items:
                    self.screen.blit(surface, position)

    def _draw_wrapped_text(self, text: str, rect: pygame.Rect, font: Optional[pygame.font.Font] = None,
                           color: tuple = TEXT_COLOR, line_spacing: int = 4, max_lines: Optional[int] = None) -> int:
        """Draw word-wrapped text inside the given rect. Returns total vertical pixels used.

        - Wraps on whitespace; if a single token exceeds width, it breaks within the word.
        - Respects rect width and height; stops drawing when vertical space is exhausted.
        - If max_lines is provided, caps the number of lines and adds an ellipsis.
        """
        if font is None:
            font = self.font
        x, y, w, h = rect.x, rect.y, rect.width, rect.height

        if not text:
            return 0

        words = text.split()
        lines: List[str] = []
        current = ""

        for word in words:
            # Handle extremely long tokens by breaking within the word when starting a new line
            if not current and font.size(word)[0] > w:
                chunk = ""
                for ch in word:
                    if font.size(chunk + ch)[0] <= w:
                        chunk += ch
                    else:
                        if chunk:
                            lines.append(chunk)
                        chunk = ch
                current = chunk
                continue

            test = word if not current else current + " " + word
            if font.size(test)[0] <= w:
                current = test
            else:
                lines.append(current)
                current = word

        if current:
            lines.append(current)

        # Apply max_lines cap with ellipsis if requested
        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines]
            last = lines[-1]
            # Ensure last line fits with ellipsis
            ellipsis = "…"
            while font.size(last + ellipsis)[0] > w and last:
                last = last[:-1]
            lines[-1] = (last + ellipsis) if last else ellipsis

        used = 0
        line_height = font.get_linesize()
        for line in lines:
            if y + line_height > rect.y + h:
                break
            surf = font.render(line, True, color)
            self.screen.blit(surf, (x, y))
            y += line_height + line_spacing
            used += line_height + line_spacing

        return used

    def _format_polygon_vertex_details(self, vertices: List[Dict], fallback_z: float) -> List[str]:
        """Format polygon vertex coordinates for the details panel."""
        details = []
        fallback_z = 0.0 if fallback_z is None else fallback_z
        for index, vertex in enumerate(vertices, start=1):
            x = vertex.get("x", 0.0)
            y = vertex.get("y", 0.0)
            z = vertex.get("z", fallback_z)
            x = 0.0 if x is None else x
            y = 0.0 if y is None else y
            z = fallback_z if z is None else z
            details.append(f"{index}. ({float(x):.1f}, {float(y):.1f}, {float(z):.1f})")
        return details

    def draw_details_panel(self):
        """Draw details panel for selected drone, target, or obstacle"""
        if not self.selected_drone and not self.selected_target and not self.selected_obstacle:
            return

        # Determine panel position based on selected item's screen position
        # This ensures panel doesn't cover the selected item, especially important for moving drones
        item_screen_x = None

        if self.selected_drone:
            item_screen_x, _ = self.world_to_screen(
                self.selected_drone['position']['x'],
                self.selected_drone['position']['y']
            )
        elif self.selected_target:
            item_screen_x, _ = self.world_to_screen(
                self.selected_target['position']['x'],
                self.selected_target['position']['y']
            )
        elif self.selected_obstacle:
            item_screen_x, _ = self.world_to_screen(
                self.selected_obstacle['position']['x'],
                self.selected_obstacle['position']['y']
            )

        # Position panel on opposite side of screen from selected item
        # If item is on left half, show panel on right; if on right half, show on left
        if item_screen_x is not None and item_screen_x < SCREEN_WIDTH / 2:
            panel_rect = pygame.Rect(SCREEN_WIDTH - 300, 60, 280, 350)
        else:
            panel_rect = pygame.Rect(20, 60, 280, 350)
        pygame.draw.rect(self.screen, PANEL_BG, panel_rect)
        pygame.draw.rect(self.screen, PANEL_BORDER, panel_rect, 2)
        
        if self.selected_drone:
            # Draw drone details
            title = self.details_title_font.render("Drone Details", True, TEXT_COLOR)
            self.screen.blit(title, (panel_rect.x + 10, panel_rect.y + 10))

            details = [
                f"Name: {self.selected_drone['name']}",
                f"Model: {self.selected_drone['model']}",
                f"ID: {self.selected_drone['id']}",
                f"Status: {format_enum_value(self.selected_drone['status'])}",
                f"Position: ({self.selected_drone['position']['x']:.1f}, "
                f"{self.selected_drone['position']['y']:.1f}, "
                f"{self.selected_drone['position']['z']:.1f})",
                f"Battery: {self.selected_drone['battery_level']:.1f}%",
                f"Max Speed: {self.selected_drone['max_speed']} m/s",
                f"Max Altitude: {self.selected_drone['max_altitude']} m",
                f"Task Radius: {self.selected_drone.get('task_radius', 20.0):.1f} m",
                f"Perceived Radius: {self.selected_drone.get('perceived_radius', 100.0):.1f} m"
            ]
        elif self.selected_target:
            # Draw target details
            title = self.details_title_font.render("Target Details", True, TEXT_COLOR)
            self.screen.blit(title, (panel_rect.x + 10, panel_rect.y + 10))
            
            details = [
                f"Name: {self.selected_target['name']}",
                f"Type: {format_enum_value(self.selected_target['type'])}",
                f"ID: {self.selected_target['id']}",
                f"Position: ({self.selected_target['position']['x']:.1f}, "
                f"{self.selected_target['position']['y']:.1f}, "
                f"{self.selected_target['position']['z']:.1f})",
                f"Description: {self.selected_target.get('description', 'N/A')}"
            ]
            if self.selected_target['type'] != 'polygon':
                details.insert(-1, f"Radius: {self.selected_target['radius']:.1f} m")
            
            # Add specific info for moving targets
            if self.selected_target['type'] == 'moving':
                moving_duration = self.selected_target.get('moving_duration')
                if moving_duration is not None:
                    details.insert(-1, f"Duration: {moving_duration:.1f} s")

                movement_mode = self.selected_target.get('movement_mode')
                if movement_mode:
                    details.insert(-1, f"Movement Mode: {format_enum_value(movement_mode)}")

                tracking_status = self.selected_target.get('tracking_status')
                if tracking_status:
                    details.insert(-1, f"Tracking Status: {format_enum_value(tracking_status)}")

                velocity = self.selected_target.get('velocity')
                moving_path = self.selected_target.get('moving_path')

                if movement_mode == "velocity" and velocity:
                    details.insert(-1, f"Velocity: ({velocity['x']:.1f}, {velocity['y']:.1f}, {velocity['z']:.1f})")
                elif movement_mode == "path" and moving_path:
                    details.insert(-1, f"Path Waypoints: {len(moving_path)}")
                    current_path_index = self.selected_target.get('current_path_index')
                    if current_path_index is not None:
                        details.insert(-1, f"Current Waypoint: {current_path_index}")
                    path_direction = self.selected_target.get('path_direction')
                    if path_direction is not None:
                        details.insert(-1, f"Path Direction: {path_direction}")
            
            # Add charge amount info for waypoint targets
            if self.selected_target['type'] == 'waypoint':
                charge_amount = self.selected_target.get('charge_amount')
                if charge_amount is not None:
                    details.insert(-1, f"Charge Amount: {charge_amount:.1f}%")

            # Add polygon vertices info for polygon targets
            if self.selected_target['type'] == 'polygon':
                vertices = self.selected_target.get('vertices')
                if vertices and isinstance(vertices, list):
                    fallback_z = self.selected_target.get("position", {}).get("z", 0.0)
                    vertex_details = [
                        f"Vertices: {self.selected_target.get('name', 'N/A')}",
                        *self._format_polygon_vertex_details(vertices, fallback_z),
                    ]
                    details[-1:-1] = vertex_details
        else:
            # Draw obstacle details
            title = self.details_title_font.render("Obstacle Details", True, TEXT_COLOR)
            self.screen.blit(title, (panel_rect.x + 10, panel_rect.y + 10))
            
            details = [
                f"Name: {self.selected_obstacle['name']}",
                f"Type: {format_enum_value(self.selected_obstacle['type'])}",
                f"ID: {self.selected_obstacle['id']}",
                f"Position: ({self.selected_obstacle['position']['x']:.1f}, "
                f"{self.selected_obstacle['position']['y']:.1f}, "
                f"{self.selected_obstacle['position'].get('z', 0.0):.1f})",
                f"Height: {self.selected_obstacle['height']:.1f} m",
                f"Description: {self.selected_obstacle.get('description', 'N/A')}"
            ]
            
            if self.selected_obstacle['type'] == 'circle':
                details.append(f"Radius: {self.selected_obstacle.get('radius', 0):.1f} m")
            elif self.selected_obstacle.get('vertices'):
                fallback_z = self.selected_obstacle.get("position", {}).get("z", 0.0)
                vertex_details = self._format_polygon_vertex_details(self.selected_obstacle['vertices'], fallback_z)
                details[-1:-1] = vertex_details
        
        y_offset = 50
        line_gap = 4
        left_x = panel_rect.x + 10
        right_limit = panel_rect.right - 10
        bottom_limit = panel_rect.bottom - 10
        available_width = right_limit - left_x

        for detail in details:
            # Respect vertical bounds of the panel
            if panel_rect.y + y_offset >= bottom_limit:
                break

            if detail.startswith("Description: "):
                # Draw description content on the same line after the label, with wrapping
                desc = detail[len("Description: "):] or "N/A"
                combined = f"Description: {desc}"
                content_rect = pygame.Rect(
                    left_x,
                    panel_rect.y + y_offset,
                    available_width,
                    max(0, bottom_limit - (panel_rect.y + y_offset))
                )
                used = self._draw_wrapped_text(combined, content_rect, font=self.details_font, color=TEXT_COLOR, line_spacing=line_gap)
                y_offset += used if used > 0 else (self.details_font.get_linesize() + line_gap)
            else:
                # Regular single-line fields
                text = self.details_font.render(detail, True, TEXT_COLOR)
                self.screen.blit(text, (left_x, panel_rect.y + y_offset))
                y_offset += self.details_font.get_linesize() + line_gap

    def draw_drone_details(self):
        """Legacy method for drawing drone details"""
        self.draw_details_panel()
    
    def draw_status_bar(self):
        """Draw status bar at the bottom of the screen"""
        status_rect = pygame.Rect(0, SCREEN_HEIGHT - 30, SCREEN_WIDTH, 30)
        pygame.draw.rect(self.screen, STATUS_BAR_BG, status_rect)
        
        # Dynamic layout to avoid overlapping: render left group left-to-right,
        # and right group right-to-left with measured widths.
        margin = 10
        gap = 15
        base_y = SCREEN_HEIGHT - 25

        # Left group: API status, session timer, counts (combined)
        left_x = margin

        # Connection status (check if controllers are available)
        try:
            # Simple check: try to get current session
            if self.session_controller and self.drone_controller:
                status_text = "System: Ready"
                status_color = STATUS_OK  # Green
            else:
                status_text = "System: Error"
                status_color = STATUS_WARN  # Orange
        except Exception:
            status_text = "System: Error"
            status_color = STATUS_ERROR  # Red

        status_surf = self.font.render(status_text, True, status_color)
        self.screen.blit(status_surf, (left_x, base_y))
        left_x += status_surf.get_width() + gap

        # Session timer (if available)
        if self.session and 'statistics' in self.session and 'session_time' in self.session['statistics']:
            session_time = self.session['statistics']['session_time']
            if session_time >= 3600:
                hours = int(session_time // 3600)
                minutes = int((session_time % 3600) // 60)
                seconds = int(session_time % 60)
                time_text = f"Time: {hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                minutes = int(session_time // 60)
                seconds = int(session_time % 60)
                time_text = f"Time: {minutes:02d}:{seconds:02d}"

            time_surf = self.font.render(time_text, True, CYAN)
            self.screen.blit(time_surf, (left_x, base_y))
            left_x += time_surf.get_width() + gap

        # Task progress (if available and not 'others' task type)
        if self.task_progress and self.task_progress.get("task_type") != "others":
            progress_percentage = self.task_progress.get("progress_percentage", 0)
            is_completed = self.task_progress.get("is_completed", False)

            # Determine color based on completion status
            if is_completed:
                progress_color = STATUS_OK  # Green for completed
                progress_text = f"Task Finished"
            else:
                progress_color = STATUS_ERROR  # Red for in progress
                progress_text = f"Task: {progress_percentage}%"

            progress_surf = self.font.render(progress_text, True, progress_color)
            self.screen.blit(progress_surf, (left_x, base_y))
            left_x += progress_surf.get_width() + gap

        # Counts combined to reduce width
        counts_text = f"Dro/Tar/Obs: {len(self.drones)}/{len(self.targets)}/{len(self.obstacles)}"
        counts_surf = self.font.render(counts_text, True, TEXT_COLOR)
        self.screen.blit(counts_surf, (left_x, base_y))
        left_x += counts_surf.get_width() + gap

        # Right group: center, click, scale rendered from right edge
        right_x = SCREEN_WIDTH - margin

        # Map scale
        scale_text = f"Scale: {round(self.map_scale, 1)} px/m"
        scale_surf = self.font.render(scale_text, True, TEXT_COLOR)
        right_x -= scale_surf.get_width()
        self.screen.blit(scale_surf, (right_x, base_y))
        right_x -= gap

        # Mouse click position
        if self.mouse_click_world_pos:
            click_text = f"Click: ({self.mouse_click_world_pos[0]:.1f}, {self.mouse_click_world_pos[1]:.1f})"
        else:
            click_text = "Click: (-, -)"
        click_surf = self.font.render(click_text, True, TEXT_COLOR)
        right_x -= click_surf.get_width()
        self.screen.blit(click_surf, (right_x, base_y))
        right_x -= gap

        # Lower-left reference point position
        view_text = f"LowerLeft: ({self.lower_left_corner[0]:.1f}, {self.lower_left_corner[1]:.1f})"
        view_surf = self.font.render(view_text, True, TEXT_COLOR)
        right_x -= view_surf.get_width()
        self.screen.blit(view_surf, (right_x, base_y))
        # No need to subtract gap afterwards; last item on right
    
    def handle_mouse_click(self, pos: Tuple[int, int]):
        """Handle mouse click events"""
        # Store the world coordinates of the click for status bar display
        self.mouse_click_world_pos = self.screen_to_world(pos[0], pos[1])
        
        # Check if a main control button was clicked
        for button in self.buttons:
            if button["rect"].collidepoint(pos):
                button["action"]()  # Call the button's action function
                return
        
        # Check if a canvas control button was clicked
        for button in self.canvas_buttons:
            if button["rect"].collidepoint(pos):
                button["action"]()  # Call the button's action function
                return
        
        # Priority: If a drone is selected and in flying/hovering/moving state,
        # prioritize sending move command over changing selection
        if (self.ui_drone_control and self.selected_drone
                and self.selected_drone["status"] in ["flying", "hovering", "moving"]):
            world_x, world_y = self.screen_to_world(pos[0], pos[1])
            self.send_move_command(world_x, world_y)
            return

        # Find all overlapping objects at this position
        overlapping_objects = self.find_overlapping_objects(pos)

        # If we have overlapping objects, handle selection
        if overlapping_objects:
            # Check if this is the same position as last click
            if (self.last_click_pos and
                abs(pos[0] - self.last_click_pos[0]) < 10 and
                abs(pos[1] - self.last_click_pos[1]) < 10 and
                len(overlapping_objects) > 1):
                # Same position with multiple objects - cycle through them
                self.current_selection_index = (self.current_selection_index + 1) % len(overlapping_objects)
            else:
                # New position or single object - start fresh
                self.overlapping_objects = overlapping_objects
                self.current_selection_index = 0
                self.last_click_pos = pos

            # Select the current object
            current_obj = overlapping_objects[self.current_selection_index]
            obj_type = current_obj["type"]
            obj_data = current_obj["object"]

            # Clear all selections first
            self.selected_drone = None
            self.selected_target = None
            self.selected_obstacle = None

            # Set the appropriate selection
            if obj_type == "drone":
                self.selected_drone = obj_data
            elif obj_type == "target":
                self.selected_target = obj_data
            elif obj_type == "obstacle":
                self.selected_obstacle = obj_data

            # Update overlapping objects list for the Change Selected button
            self.overlapping_objects = overlapping_objects

        else:
            # No objects clicked - handle deselection for idle drones or clear selections
            if self.selected_drone and self.selected_drone["status"] == "idle":
                # Hide details panel for idle drones when clicking elsewhere
                self.selected_drone = None
                self.selected_target = None
                self.selected_obstacle = None
                self.overlapping_objects = []
                self.current_selection_index = 0
                self.last_click_pos = None
                return

            # Clear selections when clicking on empty space (if no active flying drone)
            self.selected_drone = None
            self.selected_target = None
            self.selected_obstacle = None
            self.overlapping_objects = []
            self.current_selection_index = 0
            self.last_click_pos = None
    
    def handle_mouse_wheel(self, y: int, mouse_pos: Tuple[int, int] = None):
        """Handle mouse wheel events for zooming"""
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()
        
        # Get world coordinates of mouse position before zoom
        world_x, world_y = self.screen_to_world(mouse_pos[0], mouse_pos[1])
        
        # Apply discrete zoom
        old_scale = self.map_scale
        if y > 0:  # Zoom in
            if self.current_zoom_index < len(self.zoom_levels) - 1:
                self.current_zoom_index += 1
                self.map_scale = self.zoom_levels[self.current_zoom_index]
        else:  # Zoom out
            if self.current_zoom_index > 0:
                self.current_zoom_index -= 1
                self.map_scale = self.zoom_levels[self.current_zoom_index]
        
        # Adjust lower-left corner to keep mouse position at the same world coordinates
        if old_scale != self.map_scale:
            new_world_x, new_world_y = self.screen_to_world(mouse_pos[0], mouse_pos[1])
            dx = world_x - new_world_x
            dy = world_y - new_world_y
            self.lower_left_corner = (
                self.lower_left_corner[0] + dx,
                self.lower_left_corner[1] + dy,
            )
            
            # Update slider position to reflect new zoom level
            self.update_slider_position()
    
    def _is_point_in_polygon(self, x: float, y: float, vertices: List[Dict[str, float]]) -> bool:
        """Check if a point is inside a polygon using ray casting algorithm"""
        n = len(vertices)
        inside = False
        
        p1x, p1y = vertices[0]["x"], vertices[0]["y"]
        for i in range(1, n + 1):
            p2x, p2y = vertices[i % n]["x"], vertices[i % n]["y"]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside

    def deselect_all(self):
        """Deselect all selected elements"""
        self.selected_drone = None
        self.selected_target = None
        self.selected_obstacle = None
        self.overlapping_objects = []
        self.current_selection_index = 0
        self.last_click_pos = None
        self.mouse_click_world_pos = None
    
    def find_overlapping_objects(self, pos: Tuple[int, int]) -> List[Dict]:
        """Find all objects (drones, targets, obstacles) at the given position"""
        overlapping = []
        
        # Check obstacles
        for obstacle in self.obstacles:
            screen_x, screen_y = self.world_to_screen(obstacle["position"]["x"], obstacle["position"]["y"])

            if obstacle["type"] in ["point", "circle"]:
                distance = euclidean_distance(pos, (screen_x, screen_y))
                if distance <= obstacle["radius"] * self.map_scale:
                    overlapping.append({"type": "obstacle", "object": obstacle})
            elif obstacle["type"] == "ellipse":
                # Check if point is inside ellipse
                width = obstacle["width"] * self.map_scale
                height = obstacle["length"] * self.map_scale
                dx = (pos[0] - screen_x) / width
                dy = (pos[1] - screen_y) / height
                if dx * dx + dy * dy <= 1.0:
                    overlapping.append({"type": "obstacle", "object": obstacle})
            elif obstacle["type"] == "polygon" and obstacle.get("vertices"):
                world_click_x, world_click_y = self.screen_to_world(pos[0], pos[1])
                if self._is_point_in_polygon(world_click_x, world_click_y, obstacle["vertices"]):
                    overlapping.append({"type": "obstacle", "object": obstacle})
            else:
                # Fallback for unknown types
                radius = obstacle.get("radius") or 10
                size = radius * self.map_scale
                distance = euclidean_distance(pos, (screen_x, screen_y))
                if distance <= size:
                    overlapping.append({"type": "obstacle", "object": obstacle})
        
        # Check targets
        for target in self.targets:
            screen_x, screen_y = self.world_to_screen(target["position"]["x"], target["position"]["y"])
            if target.get("type") == "polygon" and target.get("vertices"):
                world_click_x, world_click_y = self.screen_to_world(pos[0], pos[1])
                if self._is_point_in_polygon(world_click_x, world_click_y, target["vertices"]):
                    overlapping.append({"type": "target", "object": target})
            else:
                distance = euclidean_distance(pos, (screen_x, screen_y))
                if distance <= (target.get("radius") or 0) * self.map_scale:
                    overlapping.append({"type": "target", "object": target})
        
        # Check drones
        for drone in self.drones:
            screen_x, screen_y = self.world_to_screen(drone["position"]["x"], drone["position"]["y"])
            distance = euclidean_distance(pos, (screen_x, screen_y))
            if distance <= 15:  # Drone selection radius
                overlapping.append({"type": "drone", "object": drone})
        
        return overlapping
    
    def change_selected_object(self):
        """Cycle through overlapping objects at the last click position, or cancel selection if only one item"""
        # If there's only one object or any selection exists, cancel/clear the selection
        if len(self.overlapping_objects) <= 1:
            self.deselect_all()
            return

        # Multiple overlapping objects - cycle to next one
        # Move to next object in the list
        self.current_selection_index = (self.current_selection_index + 1) % len(self.overlapping_objects)

        # Select the current object
        current_obj = self.overlapping_objects[self.current_selection_index]
        obj_type = current_obj["type"]
        obj_data = current_obj["object"]

        # Clear all selections first
        self.selected_drone = None
        self.selected_target = None
        self.selected_obstacle = None

        # Set the appropriate selection
        if obj_type == "drone":
            self.selected_drone = obj_data
        elif obj_type == "target":
            self.selected_target = obj_data
        elif obj_type == "obstacle":
            self.selected_obstacle = obj_data

    def cycle_path_display(self):
        """Cycle through path display settings for selected drone or all drones"""
        # Path display cycle: 10 -> 20 -> 1 -> 0 (hide) -> -1 (all) -> 10
        path_values = [10, 20, 1, 0, -1]

        if self.selected_drone:
            # Cycle path display for selected drone only
            drone_id = self.selected_drone["id"]
            current = self.drone_path_settings.get(drone_id, self.default_path_steps)

            # Find current value in cycle and move to next
            try:
                current_index = path_values.index(current)
                next_index = (current_index + 1) % len(path_values)
            except ValueError:
                # Current value not in list, start at beginning
                next_index = 0

            self.default_path_steps = path_values[next_index]
            self.drone_path_settings[drone_id] = self.default_path_steps
        else:
            # No drone selected - cycle all drones
            # Determine the most common current setting
            common_value = self.default_path_steps
            if self.drones and self.drone_path_settings:
                # Use the first drone's setting as reference
                first_drone_id = self.drones[0]["id"]
                common_value = self.drone_path_settings.get(first_drone_id, self.default_path_steps)

            # Find next value
            try:
                current_index = path_values.index(common_value)
                next_index = (current_index + 1) % len(path_values)
            except ValueError:
                next_index = 0

            # Apply to all current and future drones
            self.default_path_steps = path_values[next_index]
            for drone in self.drones:
                self.drone_path_settings[drone["id"]] = self.default_path_steps

    def toggle_object_labels(self):
        """Show or hide object labels on the canvas."""
        self.show_object_labels = not self.show_object_labels

    def reset_session_action(self):
        """Action to reset the current session."""
        if self.session and self.session.get("id"):
            session_id = self.session["id"]
            
            # Call the controller to reset the session on the backend
            self.session_controller.reset_session(session_id)
            
            # Immediately clear the UI's local data to prevent stale draws
            self.drones.clear()
            self.targets.clear()
            self.obstacles.clear()
            self.area_coverage.clear()
            self.drone_path_settings.clear()
            self.deselect_all()
            self.session = None
            
            # Force an immediate redraw of the cleared canvas
            self.screen.fill(BG_COLOR)
            self.draw_grid()
            self.draw_buttons()
            self.draw_details_panel()
            if self.minimap_visible:
                self.draw_minimap()
            self.draw_status_bar()
            pygame.display.flip()
            
            # The background periodic_refresh will eventually pick up the cleared state.

    def cycle_path_display(self):
        """Cycle through path display settings for selected drone or all drones"""
        # Path display cycle: 10 -> 20 -> 1 -> 0 (hide) -> -1 (all) -> 10
        path_values = [10, 20, 1, 0, -1]

        if self.selected_drone:
            # Cycle path display for selected drone only
            drone_id = self.selected_drone["id"]
            current = self.drone_path_settings.get(drone_id, self.default_path_steps)

            # Find current value in cycle and move to next
            try:
                current_index = path_values.index(current)
                next_index = (current_index + 1) % len(path_values)
            except ValueError:
                # Current value not in list, start at beginning
                next_index = 0

            self.default_path_steps = path_values[next_index]
            self.drone_path_settings[drone_id] = self.default_path_steps
        else:
            # No drone selected - cycle all drones
            # Determine the most common current setting
            common_value = self.default_path_steps
            if self.drones and self.drone_path_settings:
                # Use the first drone's setting as reference
                first_drone_id = self.drones[0]["id"]
                common_value = self.drone_path_settings.get(first_drone_id, self.default_path_steps)

            # Find next value
            try:
                current_index = path_values.index(common_value)
                next_index = (current_index + 1) % len(path_values)
            except ValueError:
                next_index = 0

            # Apply to all current and future drones
            self.default_path_steps = path_values[next_index]
            for drone in self.drones:
                self.drone_path_settings[drone["id"]] = self.default_path_steps

    def reset_session_action(self):
        """Action to reset the current session."""
        if self.session and self.session.get("id"):
            session_id = self.session["id"]
            
            # Call the controller to reset the session on the backend
            self.session_controller.reset_session(session_id)
            
            # Immediately clear the UI's local data to prevent stale draws
            self.drones.clear()
            self.targets.clear()
            self.obstacles.clear()
            self.area_coverage.clear()
            self.drone_path_settings.clear()
            self.deselect_all()
            
            # Force a refresh to get the (now empty) state from the backend
            # and reset the session object in the UI
            self.refresh_data()

    def handle_key_press(self, key: int):
        """Handle key press events"""
        if key == pygame.K_UP:
            self.lower_left_corner = (
                self.lower_left_corner[0],
                self.lower_left_corner[1] + 20 / self.map_scale,
            )
        elif key == pygame.K_DOWN:
            self.lower_left_corner = (
                self.lower_left_corner[0],
                self.lower_left_corner[1] - 20 / self.map_scale,
            )
        elif key == pygame.K_LEFT:
            self.lower_left_corner = (
                self.lower_left_corner[0] - 20 / self.map_scale,
                self.lower_left_corner[1],
            )
        elif key == pygame.K_RIGHT:
            self.lower_left_corner = (
                self.lower_left_corner[0] + 20 / self.map_scale,
                self.lower_left_corner[1],
            )
        elif key == pygame.K_PLUS or key == pygame.K_EQUALS:  # + key (with or without shift)
            if self.current_zoom_index < len(self.zoom_levels) - 1:
                self.current_zoom_index += 1
                self.map_scale = self.zoom_levels[self.current_zoom_index]
                self.update_slider_position()
        elif key == pygame.K_MINUS:
            if self.current_zoom_index > 0:
                self.current_zoom_index -= 1
                self.map_scale = self.zoom_levels[self.current_zoom_index]
                self.update_slider_position()
        elif key == pygame.K_r:
            self.refresh_drones()
        elif key == pygame.K_m:
            # Toggle minimap visibility
            self.minimap_visible = not self.minimap_visible
        elif key == pygame.K_ESCAPE:
            self.deselect_all()  # Deselect all elements on ESC key
    
    def refresh_data(self):
        """Refresh drone, target, obstacle, and session data from the controllers"""
        try:
            # Preserve previous session id to detect session switch
            prev_session_id = self.session.get("id") if isinstance(self.session, dict) and self.session.get("id") else None

            # Refresh session data
            # Fetch full session data including history for UI visualization
            self.session = self.session_controller.get_current_session(data=True)
            
            current_session_id = self.session.get("id") if self.session else None

            # If the session has changed, reset relevant UI state
            if prev_session_id and prev_session_id != current_session_id:
                self.deselect_all()
                self.area_coverage = {}
                self.autofit_done = False  # Re-trigger auto-fit for the new session

            if self.session:
                # Prepare window title update (must happen on main thread)
                if self.session.get("name") and self.session.get("id"):
                    session_name = self.session.get("name")
                    session_id = self.session.get("id")
                    self.pending_title_update = f"MultiUAV-Plat Server System - {session_name} ({session_id})"
                else:
                    self.pending_title_update = "MultiUAV-Plat Server System"

            # Refresh drones
            self.drones = self.drone_controller.get_all_drones()

            # Update selected drone if it exists
            if self.selected_drone:
                drone_found = False
                for drone in self.drones:
                    if drone["id"] == self.selected_drone["id"]:
                        self.selected_drone = drone
                        drone_found = True
                        break
                if not drone_found:
                    self.selected_drone = None

            # Refresh targets from session snapshot when available so tracking state stays canonical
            if self.session and isinstance(self.session.get("targets"), list):
                self.targets = self.session.get("targets", [])
            else:
                self.targets = self.target_controller.get_all_targets()

            # Update selected target if it exists
            if self.selected_target:
                target_found = False
                for target in self.targets:
                    if target["id"] == self.selected_target["id"]:
                        self.selected_target = target
                        target_found = True
                        break
                if not target_found:
                    self.selected_target = None

            # Refresh obstacles
            self.obstacles = self.obstacle_controller.get_all_obstacles()

            # Update selected obstacle if it exists
            if self.selected_obstacle:
                obstacle_found = False
                for obstacle in self.obstacles:
                    if obstacle["id"] == self.selected_obstacle["id"]:
                        self.selected_obstacle = obstacle
                        obstacle_found = True
                        break
                if not obstacle_found:
                    self.selected_obstacle = None

            # Extract area coverage and task progress from session data
            if self.session and self.session.get("id"):
                # Get area coverage directly from session response (nested in history)
                history = self.session.get("history", {})
                area_coverage_data = history.get("area_coverage", {})
                
                # Fallback for flat structure (if any)
                if not area_coverage_data:
                    area_coverage_data = self.session.get("area_coverage", {})

                if isinstance(area_coverage_data, dict):
                    new_coverage = {}

                    for target_id, coverage_info in area_coverage_data.items():
                        covered_points = coverage_info.get("covered_points", [])
                        if covered_points:
                            new_coverage[target_id] = set(tuple(p) if isinstance(p, list) else p for p in covered_points)

                    # Always update coverage to ensure UI reflects current session state
                    # This prevents stale coverage from previous sessions from being displayed
                    self.area_coverage = new_coverage

                # Get task progress from session response
                statistics = self.session.get("statistics", {})
                self.task_progress = statistics.get("task_progress")

            # Perform initial auto-fit once when data is first available
            if not self.autofit_done:
                if self.drones or self.targets or self.obstacles:
                    self.auto_fit_view()
                    self.autofit_done = True
        except Exception as e:
            # Controllers might not be available or have errors
            import traceback
            print(f"Warning: Error refreshing UI data: {e}")
            traceback.print_exc()

    def refresh_drones(self):
        """Refresh drone data from the API (legacy method)"""
        self.refresh_data()
    
    def periodic_refresh(self):
        """Periodically refresh drone and target data in a separate thread"""
        while self.running:
            self.refresh_data()
            time.sleep(1)  # Refresh every second
    
    # Canvas control methods
    def move_up(self):
        """Move map view up"""
        self.lower_left_corner = (self.lower_left_corner[0], self.lower_left_corner[1] + 10)
    
    def move_down(self):
        """Move map view down"""
        self.lower_left_corner = (self.lower_left_corner[0], self.lower_left_corner[1] - 10)
    
    def move_left(self):
        """Move map view left"""
        self.lower_left_corner = (self.lower_left_corner[0] - 10, self.lower_left_corner[1])
    
    def move_right(self):
        """Move map view right"""
        self.lower_left_corner = (self.lower_left_corner[0] + 10, self.lower_left_corner[1])
    
    def zoom_in(self):
        """Zoom in on the map"""
        if self.current_zoom_index < len(self.zoom_levels) - 1:
            self.current_zoom_index += 1
            self.map_scale = self.zoom_levels[self.current_zoom_index]
            self.update_slider_position()
    
    def zoom_out(self):
        """Zoom out on the map"""
        if self.current_zoom_index > 0:
            self.current_zoom_index -= 1
            self.map_scale = self.zoom_levels[self.current_zoom_index]
            self.update_slider_position()

    def reset_view(self):
        """Reset view to fit all items within canvas.
        This re-computes the optimal view to show almost all items."""
        # Use the same logic as auto_fit_view to re-fit view to current items
        corner, zoom_index = self.fit_view_to_items(padding_ratio=0.05)

        # Update the initial state as well, so subsequent resets use this view
        self.initial_lower_left_corner = corner
        self.initial_zoom_index = zoom_index

        # Clear any selections
        self.mouse_click_world_pos = None

    def update_slider_position(self):
        """Update slider handle position based on current zoom level"""
        # Calculate normalized zoom position based on discrete index (0.0 to 1.0)
        normalized_zoom = self.current_zoom_index / (len(self.zoom_levels) - 1)
        
        # Calculate handle position (horizontal slider: left = min zoom, right = max zoom)
        handle_width = 12
        usable_width = self.zoom_slider["rect"].width - handle_width
        handle_x = self.zoom_slider["rect"].x + usable_width * normalized_zoom
        
        self.zoom_slider["handle_rect"] = pygame.Rect(
            int(handle_x),
            self.zoom_slider["rect"].y,
            handle_width,
            self.zoom_slider["rect"].height
        )
    
    def set_zoom_from_slider(self, mouse_x: int):
        """Set zoom level based on slider position"""
        handle_width = 12
        usable_width = self.zoom_slider["rect"].width - handle_width
        
        # Calculate relative position (0.0 to 1.0)
        relative_x = (mouse_x - self.zoom_slider["rect"].x) / usable_width
        relative_x = max(0.0, min(1.0, relative_x))
        
        # Convert to discrete zoom level index
        zoom_index = int(relative_x * (len(self.zoom_levels) - 1) + 0.5)  # Round to nearest
        zoom_index = max(0, min(len(self.zoom_levels) - 1, zoom_index))
        
        # Update zoom if changed
        if zoom_index != self.current_zoom_index:
            self.current_zoom_index = zoom_index
            self.map_scale = self.zoom_levels[self.current_zoom_index]
            self.update_slider_position()
    
    def send_take_off_land_command(self):
        """Send take off or land command based on the selected drone's status"""
        if not self.selected_drone:
            return
        
        # Check drone status to determine which command to send
        if self.selected_drone["status"] == "idle":
            self.send_take_off_command()
        else:
            self.send_land_command()
    
    def send_take_off_command(self):
        """Send take off command to the selected drone"""
        if not self.selected_drone:
            return

        try:
            self.drone_controller.send_command(
                drone_id=self.selected_drone['id'],
                command=DroneCommand.TAKE_OFF,
                parameters={"altitude": 5.0}
            )
            self.refresh_drones()
        except Exception:
            pass
    
    def send_land_command(self):
        """Send land command to the selected drone"""
        if not self.selected_drone:
            return

        try:
            self.drone_controller.send_command(
                drone_id=self.selected_drone['id'],
                command=DroneCommand.LAND,
                parameters={}
            )
            self.refresh_drones()
        except Exception:
            pass
    
    def send_move_command(self, x: float, y: float):
        """Send move command to the selected drone"""
        if not self.selected_drone:
            return

        try:
            self.drone_controller.send_command(
                drone_id=self.selected_drone['id'],
                command=DroneCommand.MOVE_TO,
                parameters={
                    "x": x,
                    "y": y,
                    "z": self.selected_drone["position"]["z"]  # Maintain current altitude
                }
            )
            self.refresh_drones()
        except Exception:
            pass
    
    def send_return_home_command(self):
        """Send return home command to the selected drone or reset view origin to (0, 0)"""
        if not self.selected_drone:
            # If no drone is selected, align the view so the lower-left corner is at the origin
            self.lower_left_corner = (0, 0)
            return

        try:
            self.drone_controller.send_command(
                drone_id=self.selected_drone['id'],
                command=DroneCommand.RETURN_HOME,
                parameters={}
            )
            self.refresh_drones()
        except Exception:
            pass
    
    def send_emergency_command(self):
        """Send emergency command to the selected drone"""
        if not self.selected_drone:
            return

        try:
            self.drone_controller.send_command(
                drone_id=self.selected_drone['id'],
                command=DroneCommand.EMERGENCY,
                parameters={}
            )
            self.refresh_drones()
        except Exception:
            pass
    
    def handle_mouse_drag_start(self, pos: Tuple[int, int]):
        """Start mouse drag operation"""
        # Check if clicking on zoom slider
        if self.zoom_slider["rect"].collidepoint(pos):
            self.zoom_slider["dragging"] = True
            self.set_zoom_from_slider(pos[0])
            return
        
        # For all other areas (including game objects and empty canvas),
        # prepare for potential drag operation
        self.last_mouse_pos = pos
    
    def handle_mouse_drag(self, pos: Tuple[int, int]):
        """Handle mouse drag operation"""
        # Handle zoom slider dragging
        if self.zoom_slider["dragging"]:
            self.set_zoom_from_slider(pos[0])
            return
        
        # Check if we should start dragging (mouse moved significantly)
        if not self.dragging and self.mouse_down_pos:
            dx = abs(pos[0] - self.mouse_down_pos[0])
            dy = abs(pos[1] - self.mouse_down_pos[1])
            # Start dragging if mouse moved more than 5 pixels
            if dx > 5 or dy > 5:
                # Check if we can drag from this position (not on game objects)
                can_drag = True
                
                # Check if starting position was on a game object
                for drone in self.drones:
                    screen_x, screen_y = self.world_to_screen(drone["position"]["x"], drone["position"]["y"])
                    distance = euclidean_distance(self.mouse_down_pos, (screen_x, screen_y))
                    if distance <= 15:
                        can_drag = False
                        break
                
                if can_drag:
                    for target in self.targets:
                        screen_x, screen_y = self.world_to_screen(target["position"]["x"], target["position"]["y"])
                        distance = euclidean_distance(self.mouse_down_pos, (screen_x, screen_y))
                        if distance <= target["radius"] * self.map_scale:
                            can_drag = False
                            break
                
                if can_drag:
                    for obstacle in self.obstacles:
                        screen_x, screen_y = self.world_to_screen(obstacle["position"]["x"], obstacle["position"]["y"])
                        if obstacle["type"] in ["point", "circle"]:
                            distance = euclidean_distance(self.mouse_down_pos, (screen_x, screen_y))
                            if distance <= obstacle["radius"] * self.map_scale:
                                can_drag = False
                                break
                        elif obstacle["type"] == "ellipse":
                            width = obstacle["width"] * self.map_scale
                            height = obstacle["length"] * self.map_scale
                            dx = (self.mouse_down_pos[0] - screen_x) / width
                            dy = (self.mouse_down_pos[1] - screen_y) / height
                            if dx * dx + dy * dy <= 1.0:
                                can_drag = False
                                break
                        elif obstacle["type"] == "polygon" and obstacle.get("vertices"):
                            world_x, world_y = self.screen_to_world(self.mouse_down_pos[0], self.mouse_down_pos[1])
                            if self._is_point_in_polygon(world_x, world_y, obstacle["vertices"]):
                                can_drag = False
                                break
                        else:
                            radius = obstacle.get("radius") or 10
                            size = radius * self.map_scale
                            distance = euclidean_distance(self.mouse_down_pos, (screen_x, screen_y))
                            if distance <= size:
                                can_drag = False
                                break
                
                if can_drag:
                    self.dragging = True
        
        if self.dragging:
            dx = pos[0] - self.last_mouse_pos[0]
            dy = pos[1] - self.last_mouse_pos[1]
            
            # Convert screen movement to world movement
            world_dx = -dx / self.map_scale
            world_dy = dy / self.map_scale  # Y is inverted
            
            self.lower_left_corner = (
                self.lower_left_corner[0] + world_dx,
                self.lower_left_corner[1] + world_dy,
            )
            self.last_mouse_pos = pos
    
    def run(self):
        """Main UI loop"""
        self.refresh_drones()  # Initial data load
        
        while self.running:
            # Apply pending window title update (must happen on main thread)
            if self.pending_title_update is not None:
                pygame.display.set_caption(self.pending_title_update)
                self.pending_title_update = None

            # Handle events
            should_break_event_loop = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.confirm_on_close:
                        action = self._show_close_confirmation_dialog()
                        if action == "cancel":
                            continue
                        self.close_action = action
                    self.running = False
                    should_break_event_loop = True
                    break
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        # Minimap click to recenter view
                        if self.handle_minimap_click(event.pos):
                            # Do not start canvas drag when minimap handled the click
                            self.mouse_down_pos = None
                        else:
                            self.mouse_down_pos = event.pos
                            # Try to start drag operation
                            self.handle_mouse_drag_start(event.pos)
                    elif event.button == 3:  # Right click - deselect all elements
                        self.deselect_all()
                    elif event.button in [4, 5]:  # Mouse wheel
                        self.handle_mouse_wheel(1 if event.button == 4 else -1, event.pos)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:  # Left click release
                        # Check if this was a click (no significant movement) or a drag
                        was_dragging = self.dragging or self.zoom_slider["dragging"]
                        
                        if self.dragging:
                            self.dragging = False
                        if self.zoom_slider["dragging"]:
                            self.zoom_slider["dragging"] = False
                        
                        # If we weren't dragging and mouse didn't move much, treat as click
                        if not was_dragging and self.mouse_down_pos:
                            dx = abs(event.pos[0] - self.mouse_down_pos[0])
                            dy = abs(event.pos[1] - self.mouse_down_pos[1])
                            # Only treat as click if mouse moved less than 5 pixels
                            if dx < 5 and dy < 5:
                                self.handle_mouse_click(event.pos)
                        
                        self.mouse_down_pos = None
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_drag(event.pos)

                elif event.type == pygame.KEYDOWN:
                    self.handle_key_press(event.key)

            # Exit immediately without rendering another frame after close is confirmed.
            if should_break_event_loop or not self.running:
                break
            
            # Draw UI
            self.screen.fill(BG_COLOR)
            self.draw_grid()
            self.draw_axes()
            self._deferred_canvas_labels = []
            
            # Draw obstacles first (bottom layer)
            for obstacle in self.obstacles:
                self.draw_obstacle(obstacle)
            
            # Draw targets next (middle layer)
            for target in self.targets:
                self.draw_target(target)
            
            # Draw drones last (top layer)
            for drone in self.drones:
                self.draw_drone(drone)

            self.draw_deferred_canvas_labels()
            
            # Draw UI elements
            self.draw_buttons()
            self.draw_details_panel()
            if self.minimap_visible:
                self.draw_minimap()
            self.draw_status_bar()
            
            # Update display
            pygame.display.flip()
            self.clock.tick(30)  # 30 FPS
        
        self.running = False
        if hasattr(self, "refresh_thread") and self.refresh_thread.is_alive():
            self.refresh_thread.join(timeout=1.2)

        # Clear queued events to avoid stale window events during teardown.
        try:
            pygame.event.clear()
        except Exception:
            pass

        # Explicit display teardown improves reliability on macOS.
        try:
            if sys.platform == "darwin":
                try:
                    pygame.display.iconify()
                except Exception:
                    pass
                try:
                    self.screen = pygame.display.set_mode((1, 1), pygame.HIDDEN)
                except Exception:
                    pass
            pygame.display.quit()
        finally:
            pygame.quit()
        return self.close_action


def start_ui(
    ui_drone_control=False,
    request_history_limit=DEFAULT_REQUEST_HISTORY_LIMIT,
):
    """Start the UI"""
    ui = DroneUI(
        ui_drone_control=ui_drone_control,
        request_history_limit=request_history_limit,
    )
    ui.run()


if __name__ == "__main__":
    start_ui()
