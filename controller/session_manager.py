#!/usr/bin/env python3
"""
MultiUAV-Plat Control System - Session Manager

This module provides a session management interface that allows users to:
- Create new sessions
- Load existing sessions
- Export sessions to JSON files
- Import sessions from JSON files
- Launch the main GUI controller for a selected session

Author: MultiUAV-Plat Control System
Version: Provided by main entrypoint
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from api_server import APIServer
import json
import logging
import os
import re
import platform
import importlib
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from app_settings import get_settings, DEFAULT_STORAGE_PATH, DEFAULT_TEMPLATE_PATH, resolve_api_key, show_settings_dialog
from gui_controller import UAVControllerGUI
from detail_panel import DetailPanel
from utils import (
    setup_shared_logger,
    extract_session_collections,
    extract_session_metadata,
    load_session_from_file,
    normalize_session_canvas_fields,
    save_session_to_file,
    sanitize_filename,
    _clean_session_data_for_export,
    set_window_geometry_and_center,
    create_new_name,
    create_new_names
)
from random_session_generator import RandomSessionGenerator
from task_template_manager import TaskTemplateManager
from multi_session_template_tool import launch_task_ui_flow
from task_auto_generator import (
    auto_create_tasks_for_session,
    build_auto_template_params,
    detect_template_entity_groups,
    template_matches_task_type,
)
from shared_dialogs import show_about_dialog
from check_ui.agent_checker import AgentCheckerApp
SESSION_EDITOR_IMPORT_ERROR = None
start_session_editor = None
try:
    start_session_editor = importlib.import_module("session_editor").start_session_editor
except ImportError as exc:
    SESSION_EDITOR_IMPORT_ERROR = exc


# ============================================================================
# Configuration Constants for Session Creation
# ============================================================================

# Base area size (standard default)
BASE_AREA_WIDTH = 1024.0
BASE_AREA_HEIGHT = 768.0

# Predefined area size multipliers
AREA_SIZE_MULTIPLIERS = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0]

# Generate predefined area size options
PREDEFINED_AREA_SIZES = [
    (int(BASE_AREA_WIDTH * m), int(BASE_AREA_HEIGHT * m))
    for m in AREA_SIZE_MULTIPLIERS
]

TK_SHIFT_MASK = 0x0001
TK_CONTROL_MASK = 0x0004

class SessionManager:
    """Session management interface for MultiUAV-Plat Control System"""

    def __init__(self, version: str, build: str):
        self.version = version
        self.build = build
        self.current_session = None
        self.sessions = []
        self.launching_session = False  # Flag to prevent multiple launches
        self.imported_storage_files = set()  # type: set[str]
        self.session_filepath_map = {}  # Track session_id -> filepath mapping
        self._icon_image = None
        self._cached_current_session_id: Optional[str] = None  # Cache to avoid redundant API calls
        self._server_unavailable = False  # Track if server is unavailable
        self._connection_error_shown = False  # Track if we've already shown connection error
        self._selection_anchor_index: Optional[int] = None

        # Load shared settings
        self.app_settings = get_settings()
        self.session_storage_path: Optional[str] = self.app_settings.get('session_storage_path')
        self.template_storage_path: Optional[str] = self.app_settings.get('template_storage_path')
        self.username: str = self.app_settings.get('username', 'SYSTEM')

        # API Authentication - ADMIN role required for controller operations.
        
        # Setup logging
        self.setup_logging()
        
        self.api_server = APIServer(logger=self.logger, error_handler=lambda title, msg: messagebox.showerror(title, msg))

        # Initialize random session generator
        self.random_generator = RandomSessionGenerator(logger=self.logger)
        self.template_manager = TaskTemplateManager(template_dir=self.template_storage_path)

        # Create main window
        self.root = tk.Tk()
        self.root.title("MultiUAV-Plat Control System - Session Manager")
        self.root.resizable(True, True)
        self._set_window_icon(self.root)
        
        # Center the window
        set_window_geometry_and_center(
            self.root,
            800,
            600,
            None,
            make_transient=False,
            grab=False,
            withdraw_first=True,
            align_to_pointer=True,
            bring_to_front=True
        )

        # Create UI
        self.create_widgets()

        # Create menu bar
        self.create_menu_bar()

        # Load storage configuration (if any)
        self.load_storage_config()

        # Load sessions on startup - force fetch on initial load
        self.refresh_sessions(force_fetch_current=True)
        
    def setup_logging(self):
        """Setup logging configuration using shared logger"""
        self.logger = setup_shared_logger('SessionManager', logging.INFO)

        # self.logger.info("============================================================")
        self.logger.info("MultiUAV-Plat Control System - Session Manager started")
        self.logger.info("API Base URL: http://127.0.0.1:8000")
        self.logger.info("Authentication: ADMIN role (API key configured)")
        # self.logger.info("============================================================")

    def _set_window_icon(self, window, set_default: bool = True):
        """Set the application icon for the provided window if the asset exists."""
        if window is None:
            return
        try:
            icon_path = Path(__file__).resolve().parent / "img" / "controller.png"
            if not icon_path.exists():
                self.logger.debug(f"Icon file not found at {icon_path}")
                return
            if self._icon_image is None:
                self._icon_image = tk.PhotoImage(file=str(icon_path))
            window.iconphoto(bool(set_default), self._icon_image)
            setattr(window, "_uav_icon_image", self._icon_image)
        except Exception as exc:
            self.logger.debug(f"Failed to set window icon: {exc}")
        
    def create_widgets(self):
        """Create the main UI widgets"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Session Overview", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Sessions list frame
        sessions_frame = ttk.LabelFrame(main_frame, text="Available Sessions", padding="10")
        sessions_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        sessions_frame.columnconfigure(0, weight=100)  # Listbox gets more space
        sessions_frame.columnconfigure(1, weight=2)  # Details panel gets less space but is fixed
        sessions_frame.rowconfigure(0, weight=1)
        
        # Sessions listbox with scrollbar
        listbox_frame = ttk.Frame(sessions_frame)
        listbox_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        listbox_frame.columnconfigure(0, weight=1)
        listbox_frame.rowconfigure(0, weight=1)
        
        self.sessions_listbox = tk.Listbox(listbox_frame, selectmode=tk.EXTENDED, exportselection=False)
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.sessions_listbox.yview)
        self.sessions_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.sessions_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.sessions_listbox.focus_set()

        # Bind actions to session list
        self.sessions_listbox.bind('<ButtonPress-1>', self.handle_session_mouse_selection)
        toggle_click_binding = '<Command-ButtonPress-1>' if platform.system() == 'Darwin' else '<Control-ButtonPress-1>'
        self.sessions_listbox.bind(
            toggle_click_binding,
            lambda event: self.handle_session_mouse_selection(event, force_toggle=True)
        )
        self.sessions_listbox.bind('<Double-Button-1>', self.launch_selected_session)
        self.sessions_listbox.bind('<space>', self.preview_selected_session)
        self.sessions_listbox.bind('<BackSpace>', self.delete_selected_session_shortcut)
        self.sessions_listbox.bind('<Delete>', self.delete_selected_session_shortcut)
        for key in ('<Up>', '<Down>', '<Prior>', '<Next>', '<Home>', '<End>'):
            self.sessions_listbox.bind(key, self.handle_session_navigation_key)
        self.sessions_listbox.bind('<B1-Motion>', lambda event: "break")
        self.sessions_listbox.bind('<Shift-B1-Motion>', lambda event: "break")
        self.sessions_listbox.bind('<Control-B1-Motion>', lambda event: "break")
        self.sessions_listbox.bind('<Command-B1-Motion>', lambda event: "break")
        self.sessions_listbox.bind('<ButtonRelease-1>', lambda event: "break")
        self.sessions_listbox.bind('<Shift-ButtonRelease-1>', lambda event: "break")
        self.sessions_listbox.bind('<Control-ButtonRelease-1>', lambda event: "break")
        self.sessions_listbox.bind('<Command-ButtonRelease-1>', lambda event: "break")
        
        # Session details frame
        details_frame = ttk.LabelFrame(sessions_frame, text="Session Details", padding="10", width=300)
        details_frame.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.E), padx=(10, 0))
        details_frame.grid_propagate(False)  # Prevent frame from shrinking to fit contents
        details_frame.columnconfigure(0, weight=0)  # Label column - don't expand
        details_frame.columnconfigure(1, weight=1)  # Value column - expand to fill
        
        # Session details labels
        ttk.Label(details_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.name_label = ttk.Label(details_frame, text="-", foreground="blue")
        self.name_label.grid(row=0, column=1, sticky=tk.W, pady=2)

        ttk.Label(details_frame, text="ID:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.id_label = ttk.Label(details_frame, text="-", foreground="gray")
        self.id_label.grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(details_frame, text="Status:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.status_label = ttk.Label(details_frame, text="-")
        self.status_label.grid(row=2, column=1, sticky=tk.W, pady=2)

        ttk.Label(details_frame, text="Description:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.description_label = ttk.Label(details_frame, text="-", wraplength=250)
        self.description_label.grid(row=3, column=1, sticky=tk.W, pady=2)

        ttk.Label(details_frame, text="Task Type:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.task_label = ttk.Label(details_frame, text="-")
        self.task_label.grid(row=4, column=1, sticky=tk.W, pady=2)

        ttk.Label(details_frame, text="Task Des.:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.task_description_label = ttk.Label(details_frame, text="-", wraplength=250)
        self.task_description_label.grid(row=5, column=1, sticky=tk.W, pady=2)

        ttk.Label(details_frame, text="Drones:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.drones_label = ttk.Label(details_frame, text="-")
        self.drones_label.grid(row=6, column=1, sticky=tk.W, pady=2)

        ttk.Label(details_frame, text="Targets:").grid(row=7, column=0, sticky=tk.W, pady=2)
        self.targets_label = ttk.Label(details_frame, text="-")
        self.targets_label.grid(row=7, column=1, sticky=tk.W, pady=2)

        ttk.Label(details_frame, text="Obstacles:").grid(row=8, column=0, sticky=tk.W, pady=2)
        self.obstacles_label = ttk.Label(details_frame, text="-")
        self.obstacles_label.grid(row=8, column=1, sticky=tk.W, pady=2)

        ttk.Label(details_frame, text="Tasks:").grid(row=9, column=0, sticky=tk.W, pady=2)
        self.tasks_label = ttk.Label(details_frame, text="-")
        self.tasks_label.grid(row=9, column=1, sticky=tk.W, pady=2)

        ttk.Label(details_frame, text="Created:").grid(row=10, column=0, sticky=tk.W, pady=2)
        self.created_label = ttk.Label(details_frame, text="-")
        self.created_label.grid(row=10, column=1, sticky=tk.W, pady=2)
        
        # Bind selection event
        self.sessions_listbox.bind('<<ListboxSelect>>', self.on_session_select)
        
        # Buttons frame (two rows)
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=2, column=0, columnspan=3, pady=10)

        # Row 1: Launch, Preview, Rename, Edit, Export, Delete, CheckUI
        row1_frame = ttk.Frame(buttons_frame)
        row1_frame.pack(pady=2)
        ttk.Button(row1_frame, text="Launch", command=self.launch_selected_session).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1_frame, text="Preview", command=self.load_session).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1_frame, text="Rename", command=self.rename_session).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1_frame, text="Edit", command=self.edit_session).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1_frame, text="Export", command=self.export_session).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1_frame, text="Delete", command=self.delete_session).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1_frame, text="CheckUI", command=self.launch_batch_check).pack(side=tk.LEFT, padx=5)

        # Row 2: New, Duplicate, Import, About, Settings, Refresh, TaskUI
        row2_frame = ttk.Frame(buttons_frame)
        row2_frame.pack(pady=2)
        ttk.Button(row2_frame, text="New", command=self.create_session).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2_frame, text="Clone", command=self.duplicate_session).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2_frame, text="Import", command=self.import_session).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2_frame, text="About", command=self.show_about).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2_frame, text="Settings", command=self.show_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2_frame, text="Refresh", command=self.user_refresh_sessions).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2_frame, text="TaskUI", command=self.launch_task_ui).pack(side=tk.LEFT, padx=5)


        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

    def create_menu_bar(self):
        """Create the menu bar with all menus"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Session Menu
        session_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Session", menu=session_menu)
        session_menu.add_command(label="New Session", command=self.create_session, accelerator="Ctrl+N")
        session_menu.add_command(label="Duplicate Session", command=self.duplicate_session, accelerator="Ctrl+D")
        session_menu.add_separator()
        session_menu.add_command(label="Import Session", command=self.import_session, accelerator="Ctrl+I")
        session_menu.add_command(label="Export Session", command=self.export_session, accelerator="Ctrl+E")
        session_menu.add_separator()
        session_menu.add_command(label="Refresh Sessions", command=self.user_refresh_sessions, accelerator="F5")
        session_menu.add_separator()
        session_menu.add_command(label="Settings", command=self.show_settings)
        session_menu.add_separator()
        close_accelerator = "Cmd+W" if platform.system() == 'Darwin' else "Ctrl+W"
        session_menu.add_command(label="Exit", command=self.root.quit, accelerator=close_accelerator)

        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Launch Session", command=self.launch_selected_session, accelerator="Enter")
        edit_menu.add_command(label="Preview Session", command=self.load_session, accelerator="Space")
        edit_menu.add_separator()
        edit_menu.add_command(label="Rename Session", command=self.rename_session, accelerator="F2")
        edit_menu.add_command(label="Edit Session", command=self.edit_session)
        edit_menu.add_separator()
        edit_menu.add_command(label="Delete Session", command=self.delete_session, accelerator="Delete")

        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh", command=self.user_refresh_sessions, accelerator="F5")

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

        # Bind keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self.create_session())
        self.root.bind('<Control-d>', lambda e: self.duplicate_session())
        self.root.bind('<Control-i>', lambda e: self.import_session())
        self.root.bind('<Control-e>', lambda e: self.export_session())
        self.root.bind('<F5>', lambda e: self.user_refresh_sessions())
        self.root.bind('<F2>', lambda e: self.rename_session())
        self.root.bind('<Delete>', lambda e: self.delete_session())
        self.root.bind('<Return>', lambda e: self.launch_selected_session())
        if platform.system() == 'Darwin':
            self.root.bind('<Command-w>', self.handle_close_shortcut)
        else:
            self.root.bind('<Control-w>', self.handle_close_shortcut)

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

    def handle_close_shortcut(self, event=None):
        """Close the session manager window with Ctrl/Cmd+W."""
        if self._has_open_popout():
            self.update_status("Close shortcut disabled while a dialog is open")
            return "break"
        self.root.quit()
        return "break"

    def update_status(self, message: str):
        """Update status bar message"""
        self.status_var.set(message)
        self.root.update_idletasks()
        
    def _order_sessions(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return sessions ordered with examples first, then by creation time."""
        example_sessions = []
        normal_sessions = []
        for session in sessions:
            name = (session.get('name') or '').strip().lower()
            if name.startswith('example'):
                example_sessions.append(session)
            else:
                normal_sessions.append(session)

        example_sessions.sort(key=lambda s: s.get('created_at') or 0)
        normal_sessions.sort(key=lambda s: s.get('created_at') or 0)
        return example_sessions + normal_sessions

    def refresh_sessions(self, force_fetch_current: bool = False, user_initiated: bool = False):
        """Refresh the sessions list

        Args:
            force_fetch_current: If True, always fetch current session from server.
                               If False, use cached value when available.
            user_initiated: If True, this refresh was manually triggered by the user.
                          In this case, reset connection error flag to show new errors.
        """
        self.update_status("Refreshing sessions...")
        self.logger.info("Refreshing sessions list")

        # If user manually clicked refresh, reset the connection error flag
        # so they can see if the server is still unavailable
        if user_initiated:
            self._connection_error_shown = False
            self.logger.info("User-initiated refresh: resetting connection error flag")

        sessions = self.api_server.api_get_sessions()
        if sessions is not None:
            ordered_sessions = self._order_sessions(sessions)
            # Get the current session from cache or server
            current_session_id = None
            if not force_fetch_current and self._cached_current_session_id is not None:
                # Use cached value to avoid redundant API call
                current_session_id = self._cached_current_session_id
                self.logger.debug(f"Using cached current session: {current_session_id}")
            else:
                # Fetch from server and update cache
                try:
                    current_session = self.api_server.api_get_current_session(show_error=False)
                    current_session_id = current_session.get('id') if current_session else None
                    self._cached_current_session_id = current_session_id
                    self.logger.info(f"Current session from server: {current_session_id}")
                except Exception as exc:
                    self.logger.warning(f"Failed to get current session from server: {exc}")
                    current_session_id = None

            if not current_session_id and ordered_sessions:
                fallback_session_id = ordered_sessions[0].get('id')
                if fallback_session_id:
                    response = self.api_server.api_set_session_as_current(
                        fallback_session_id,
                        show_error=False
                    )
                    if response is not None:
                        current_session_id = fallback_session_id
                        self._cached_current_session_id = fallback_session_id
                        self.logger.info(
                            f"No current session found. Set fallback session: {fallback_session_id}")
                    else:
                        self.logger.warning(
                            "No current session found and failed to set fallback session")

            for session in ordered_sessions:
                session_id = session.get('id')

                # Update session status based on current session from server
                if current_session_id and session_id == current_session_id:
                    # Mark the current session as active
                    if session.get('status') != 'active':
                        self.logger.info(f"Setting session {session_id} status to active")
                        self.api_server.api_update_session_status(session_id, 'active')
                        session['status'] = 'active'
                else:
                    # Force all other sessions to inactive
                    if session.get('status') != 'inactive':
                        self.logger.info(f"Setting session {session_id} status to inactive")
                        self.api_server.api_update_session_status(session_id, 'inactive')
                        session['status'] = 'inactive'

            self.sessions = ordered_sessions
            self.sessions_listbox.delete(0, tk.END)

            for session in ordered_sessions:
                name = session.get('name', 'Unknown')
                session_id = session.get('id', 'Unknown')
                status = session.get('status', 'unknown')
                created = datetime.fromtimestamp(session.get('created_at', 0)).strftime('%Y-%m-%d %H:%M')
                active_prefix = "【ACTIVE】 " if status == 'active' else ""
                display_text = f"{active_prefix}[{session_id}] {name} - {created}"
                self.sessions_listbox.insert(tk.END, display_text)

            self.update_status(f"Found {len(sessions)} sessions")
            self.logger.info(f"Successfully loaded {len(sessions)} sessions")
        else:
            if self._server_unavailable:
                self.update_status("Server unavailable - Click 'Refresh' to retry")
            else:
                self.update_status("Failed to refresh sessions")

    def user_refresh_sessions(self):
        """Handle user-initiated refresh from the Refresh button"""
        self.refresh_sessions(force_fetch_current=True, user_initiated=True)

    def _get_session_task_count(self, session: Dict[str, Any]) -> int:
        """Return the best available task count from a session payload."""
        stats = session.get('statistics') or {}
        stats_task_count = stats.get('task_count')
        if isinstance(stats_task_count, (int, float)):
            return int(stats_task_count)

        tasks = session.get('tasks')
        if isinstance(tasks, list):
            return len(tasks)
        return 0

    def on_session_select(self, event):
        """Handle session selection"""
        selection = self.sessions_listbox.curselection()
        if not selection:
            return

        if len(selection) > 1:
            selected_sessions = [self.sessions[index] for index in selection if index < len(self.sessions)]
            self.name_label.config(text=f"{len(selected_sessions)} sessions selected")
            self.id_label.config(text="-")
            self.status_label.config(text="mixed")
            self.description_label.config(text="Multiple sessions selected for batch export or delete.")
            self.task_label.config(text="-")
            self.task_description_label.config(text="-")
            self.drones_label.config(
                text=str(sum((session.get('statistics', {}) or {}).get('drone_count', 0) for session in selected_sessions))
            )
            self.targets_label.config(
                text=str(sum((session.get('statistics', {}) or {}).get('target_count', 0) for session in selected_sessions))
            )
            self.obstacles_label.config(
                text=str(sum((session.get('statistics', {}) or {}).get('obstacle_count', 0) for session in selected_sessions))
            )
            self.tasks_label.config(
                text=str(sum(self._get_session_task_count(session) for session in selected_sessions))
            )
            self.created_label.config(text="-")
            return

        session_index = selection[0]
        if session_index < len(self.sessions):
            session = self.sessions[session_index]

            # Update details
            self.name_label.config(text=session.get('name', 'Unknown'))
            self.id_label.config(text=session.get('id', 'Unknown'))
            self.status_label.config(text=session.get('status', 'unknown'))
            self.description_label.config(text=session.get('description', 'No description'))
            self.task_label.config(text=session.get('task_type', 'others'))
            self.task_description_label.config(text=session.get('task_description') or '-')

            stats = session.get('statistics', {})
            self.drones_label.config(text=str(stats.get('drone_count', 0)))
            self.targets_label.config(text=str(stats.get('target_count', 0)))
            self.obstacles_label.config(text=str(stats.get('obstacle_count', 0)))
            self.tasks_label.config(text=str(self._get_session_task_count(session)))

            created = datetime.fromtimestamp(session.get('created_at', 0)).strftime('%Y-%m-%d %H:%M:%S')
            self.created_label.config(text=created)
    
    def sync_selection_with_keyboard(self, event=None):
        """Ensure keyboard navigation updates the actual selection."""
        try:
            active_index = self.sessions_listbox.index(tk.ACTIVE)
        except tk.TclError:
            return
        if active_index < 0 or active_index >= self.sessions_listbox.size():
            return
        current = self.sessions_listbox.curselection()
        if current and current[0] == active_index:
            return
        self.sessions_listbox.selection_clear(0, tk.END)
        self.sessions_listbox.selection_set(active_index)
        self.sessions_listbox.selection_anchor(active_index)
        self.sessions_listbox.see(active_index)
        self._selection_anchor_index = active_index
        self.on_session_select(None)
        return None

    def handle_session_navigation_key(self, event=None):
        """Move the list selection with plain navigation keys."""
        if event is None or self.sessions_listbox.size() == 0:
            return "break"

        # Leave modified selection behavior to Tk's default bindings.
        state = int(getattr(event, 'state', 0))
        if self._is_session_range_select_modifier(state) or self._is_session_toggle_select_modifier(state):
            return None

        selected = self._get_selected_session_indices()
        try:
            current_index = self.sessions_listbox.index(tk.ACTIVE)
        except tk.TclError:
            current_index = selected[0] if selected else 0

        current_index = max(0, min(current_index, self.sessions_listbox.size() - 1))
        keysym = getattr(event, 'keysym', '')
        if keysym == 'Up':
            new_index = current_index - 1
        elif keysym == 'Down':
            new_index = current_index + 1
        elif keysym == 'Prior':
            new_index = current_index - 10
        elif keysym == 'Next':
            new_index = current_index + 10
        elif keysym == 'Home':
            new_index = 0
        elif keysym == 'End':
            new_index = self.sessions_listbox.size() - 1
        else:
            return None

        new_index = max(0, min(new_index, self.sessions_listbox.size() - 1))
        self.sessions_listbox.selection_clear(0, tk.END)
        self.sessions_listbox.selection_set(new_index)
        self.sessions_listbox.selection_anchor(new_index)
        self.sessions_listbox.activate(new_index)
        self.sessions_listbox.see(new_index)
        self._selection_anchor_index = new_index
        self.on_session_select(None)
        return "break"

    def delete_selected_session_shortcut(self, event=None):
        """Delete the current session selection from the list keyboard focus."""
        self.delete_session()
        return "break"

    def handle_session_mouse_selection(self, event=None, force_toggle: bool = False):
        """Handle mouse selection with explicit plain/range/toggle behavior."""
        if event is None:
            return None
        self.sessions_listbox.focus_set()
        clicked_index = self.sessions_listbox.nearest(event.y)
        if clicked_index < 0 or clicked_index >= self.sessions_listbox.size():
            return "break"

        state = int(getattr(event, 'state', 0))
        is_shift = self._is_session_range_select_modifier(state)
        is_toggle = force_toggle or self._is_session_toggle_select_modifier(state)

        if is_shift:
            anchor_index = self._selection_anchor_index
            if anchor_index is None or anchor_index < 0 or anchor_index >= self.sessions_listbox.size():
                anchor_index = clicked_index
            start_index, end_index = sorted((anchor_index, clicked_index))
            self.sessions_listbox.selection_clear(0, tk.END)
            self.sessions_listbox.selection_set(start_index, end_index)
            self.sessions_listbox.selection_anchor(anchor_index)
        elif is_toggle:
            if self.sessions_listbox.selection_includes(clicked_index):
                self.sessions_listbox.selection_clear(clicked_index)
            else:
                self.sessions_listbox.selection_set(clicked_index)
            self.sessions_listbox.selection_anchor(clicked_index)
            self._selection_anchor_index = clicked_index
        else:
            self.sessions_listbox.selection_clear(0, tk.END)
            self.sessions_listbox.selection_set(clicked_index)
            self.sessions_listbox.selection_anchor(clicked_index)
            self._selection_anchor_index = clicked_index

        self.sessions_listbox.activate(clicked_index)
        self.sessions_listbox.see(clicked_index)
        self.on_session_select(None)
        return "break"

    @staticmethod
    def _is_session_range_select_modifier(state: int) -> bool:
        return bool(state & TK_SHIFT_MASK)

    @staticmethod
    def _is_session_toggle_select_modifier(state: int) -> bool:
        if platform.system() == 'Darwin':
            # Command-click is handled by an explicit <Command-ButtonPress-1>
            # binding. Do not infer it from event.state on macOS because Tk
            # builds can report Option with the same bit this code previously
            # treated as Command.
            return False
        return bool(state & TK_CONTROL_MASK)

    def _get_selected_session_indices(self) -> List[int]:
        return [index for index in self.sessions_listbox.curselection() if 0 <= index < len(self.sessions)]

    def _get_selected_sessions(self) -> List[Dict[str, Any]]:
        return [self.sessions[index] for index in self._get_selected_session_indices()]

    def _require_single_selected_session(self, action_label: str) -> Optional[Tuple[int, Dict[str, Any]]]:
        selected_indices = self._get_selected_session_indices()
        if not selected_indices:
            messagebox.showwarning("No Selection", f"Please select a session to {action_label}")
            return None
        if len(selected_indices) > 1:
            messagebox.showwarning("Multiple Selection", f"Please select exactly one session to {action_label}")
            return None
        session_index = selected_indices[0]
        return session_index, self.sessions[session_index]
            
    def create_session(self):
        """Create a new session"""
        default_name = self._generate_default_session_name()
        dialog = SessionDialog(self.root, "Create New Session", {
            'name': default_name,
            'with_examples': True,
            'populate_random': False,
            'task_type': 'others',
            'task_description': '',
            'area_width': 1024.0,
            'area_height': 768.0,
            'generate_screenshot': False,
            'do_not_scatter_drones': False,
            'auto_generate_tasks': False,
            'generated_task_count': 3,
            'auto_load_created_session': False
        })
        if dialog.result:
            self.update_status("Creating session...")
            self.logger.info(f"Creating new session: {dialog.result}")

            base_result = dict(dialog.result)
            batch_count = max(1, int(base_result.pop('batch_count', 1) or 1))
            auto_description = base_result.pop('_auto_description', False)

            try:
                area_width = float(base_result.get('area_width', 1024.0) or 1024.0)
                area_height = float(base_result.get('area_height', 768.0) or 768.0)
            except (TypeError, ValueError):
                area_width, area_height = 1024.0, 768.0

            base_name = base_result.get('name') or self._generate_default_session_name()
            base_description = base_result.pop('description', '')
            base_task = base_result.get('task_type', 'others')
            populate_random = base_result.get('populate_random', False)
            with_examples = base_result.get('with_examples', True)
            generate_screenshot = bool(base_result.get('generate_screenshot', False))
            base_result['generate_screenshot'] = generate_screenshot
            do_not_scatter_drones = bool(base_result.get('do_not_scatter_drones', False))
            base_result['do_not_scatter_drones'] = do_not_scatter_drones
            auto_generate_tasks = bool(base_result.get('auto_generate_tasks', False))
            generated_task_count = max(0, int(base_result.get('generated_task_count', 0) or 0))
            auto_load_created_session = bool(base_result.get('auto_load_created_session', False))
            base_drone_count = int(base_result.get('drone_count', 0) or 0)
            base_target_count = int(base_result.get('target_count', 0) or 0)
            base_obstacle_count = int(base_result.get('obstacle_count', 0) or 0)

            created_sessions: List[Tuple[str, str]] = []
            existing_names = [
                (session.get('name') or "").strip()
                for session in getattr(self, 'sessions', [])
            ]
            batch_names = (
                create_new_names(base_name, n=batch_count, exist_list=existing_names)
                if batch_count > 1
                else [base_name]
            )
            progress_dialog = self._show_batch_progress_dialog(batch_count)

            try:
                for idx, session_name in enumerate(batch_names):
                    # Add small delay between batch creations to ensure unique timestamps
                    if idx > 0:
                        time.sleep(0.1)  # 100ms delay between sessions
                    self._update_batch_progress(progress_dialog, idx, batch_count, f"Creating session {idx + 1}/{batch_count}: {session_name}")

                    result_config = dict(base_result)
                    result_config['name'] = session_name
                    result_config['with_examples'] = with_examples
                    result_config['populate_random'] = populate_random
                    result_config['generate_screenshot'] = bool(generate_screenshot)
                    result_config['do_not_scatter_drones'] = bool(do_not_scatter_drones and populate_random)

                    result_config['drone_count'] = base_drone_count if populate_random else 0
                    result_config['target_count'] = base_target_count if populate_random else 0
                    result_config['obstacle_count'] = base_obstacle_count if populate_random else 0

                    if auto_description:
                        result_config['description'] = self._auto_session_description(
                            session_name,
                            area_width,
                            area_height,
                            result_config.get('task_type', 'others'),
                            populate_random,
                            result_config['drone_count'],
                            result_config['target_count'],
                            result_config['obstacle_count'],
                            result_config.get('with_examples', True)
                        )
                    else:
                        result_config['description'] = base_description

                    session_request = {
                        'name': session_name,
                        'description': result_config.get('description', ''),
                        'with_examples': result_config.get('with_examples', True),
                        'creator': self.username,
                        'canvas_width': area_width,
                        'canvas_height': area_height,
                    }
                    if result_config.get('task_type'):
                        session_request['task_type'] = result_config['task_type']
                    if result_config.get('task_description'):
                        session_request['task_description'] = result_config['task_description']

                    if populate_random:
                        generated_session_data = self.random_generator.generate_session_data(
                            drone_count=result_config['drone_count'],
                            target_count=result_config['target_count'],
                            obstacle_count=result_config['obstacle_count'],
                            area_width=area_width,
                            area_height=area_height,
                            task_type=result_config.get('task_type', 'others'),
                            do_not_scatter_drones=result_config.get('do_not_scatter_drones', False)
                        )
                        session_request['with_examples'] = False
                        session_request['drones'] = generated_session_data.get('drones', [])
                        session_request['targets'] = generated_session_data.get('targets', [])
                        session_request['obstacles'] = generated_session_data.get('obstacles', [])
                        session_request['environment'] = self._default_environment_payload(session_name)
                        actual_counts = {
                            'drones': len(session_request['drones']),
                            'targets': len(session_request['targets']),
                            'obstacles': len(session_request['obstacles']),
                        }
                        expected_counts = {
                            'drones': result_config['drone_count'],
                            'targets': result_config['target_count'],
                            'obstacles': result_config['obstacle_count'],
                        }
                        if actual_counts != expected_counts:
                            self.logger.warning(
                                "Random generator produced fewer entities than requested for %s. expected=%s actual=%s",
                                session_name,
                                expected_counts,
                                actual_counts
                            )

                    result = self.api_server.api_new_session(session_request)
                    if not result:
                        self.logger.error(f"Failed to create session '{session_name}'")
                        continue

                    session_id = result.get('id', 'Unknown')
                    created_sessions.append((session_id, session_name))
                    self.logger.info(f"Session created successfully: {session_id}")

                    response = self.api_server.api_set_session_as_current(session_id)
                    if response is not None:
                        # Update cache after setting current session
                        self._cached_current_session_id = session_id

                    if populate_random:
                        expected_counts = {
                            'drones': result_config['drone_count'],
                            'targets': result_config['target_count'],
                            'obstacles': result_config['obstacle_count'],
                        }
                        self._wait_for_session_entities(session_id, expected_counts)
                    else:
                        if self._ensure_environment_for_session(session_id, session_name):
                            self.logger.info("Default environment provisioned for the new session.")
                        else:
                            self.logger.warning("Default environment could not be provisioned for the new session.")

                    if auto_generate_tasks and generated_task_count > 0:
                        self._update_batch_progress(
                            progress_dialog,
                            idx,
                            batch_count,
                            f"Generating tasks for session {idx + 1}/{batch_count}: {session_name}"
                        )
                        self._auto_create_tasks_for_session(
                            session_id=session_id,
                            session_name=session_name,
                            session_task_type=result_config.get('task_type', 'others'),
                            task_count=generated_task_count
                        )

                    json_path = self.save_session_to_storage(session_id, session_name)
                    if result_config.get('generate_screenshot'):
                        self.save_session_screenshot(session_id, session_name, json_path)

                    self._update_batch_progress(progress_dialog, idx + 1, batch_count, f"Completed session {idx + 1}/{batch_count}: {session_name}")
            finally:
                self._close_batch_progress_dialog(progress_dialog)

            if created_sessions:
                if len(created_sessions) == 1:
                    session_name = created_sessions[0][1]
                    messagebox.showinfo("Success", f"Session '{session_name}' created successfully!")
                else:
                    names = ", ".join(name for _, name in created_sessions)
                    messagebox.showinfo("Success", f"Sessions created successfully:\n{names}")
                # Force fetch current session after creating new sessions
                self.refresh_sessions(force_fetch_current=True)
                if auto_load_created_session:
                    last_session_id = created_sessions[-1][0]
                    self._select_session_in_list(last_session_id)
                    self.launch_selected_session()
                self.update_status("Ready")
            else:
                self.update_status("Failed to create session")
                messagebox.showerror("Error", "Failed to create session(s).")
                
    def _generate_default_session_name(self) -> str:
        """Generate a unique default session name of the form 'New Session #'"""
        base_name = "New Session"
        existing_names = [
            (session.get('name') or "").strip()
            for session in getattr(self, 'sessions', [])
        ]
        return create_new_name(base_name, exist_list=existing_names)

    def _show_batch_progress_dialog(self, total: int):
        dialog = tk.Toplevel(self.root)
        self._set_window_icon(dialog, set_default=False)
        dialog.title("Creating Sessions")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", lambda: None)
        set_window_geometry_and_center(dialog, 420, 120, self.root)

        frame = ttk.Frame(dialog, padding="12")
        frame.pack(fill=tk.BOTH, expand=True)
        label_var = tk.StringVar(value="Preparing batch creation...")
        ttk.Label(frame, textvariable=label_var, wraplength=380).pack(anchor=tk.W, pady=(0, 8))
        progress = ttk.Progressbar(frame, orient=tk.HORIZONTAL, mode='determinate', maximum=max(1, total))
        progress.pack(fill=tk.X)
        dialog.update_idletasks()
        return {'dialog': dialog, 'label_var': label_var, 'progress': progress}

    def _update_batch_progress(self, progress_dialog, value: int, total: int, message: str):
        if not progress_dialog:
            return
        try:
            progress_dialog['label_var'].set(message)
            progress_dialog['progress'].configure(maximum=max(1, total), value=max(0, min(value, total)))
            progress_dialog['dialog'].update_idletasks()
            progress_dialog['dialog'].update()
        except tk.TclError:
            pass

    def _close_batch_progress_dialog(self, progress_dialog):
        if not progress_dialog:
            return
        try:
            progress_dialog['dialog'].grab_release()
        except Exception:
            pass
        try:
            progress_dialog['dialog'].destroy()
        except Exception:
            pass

    def _wait_for_session_entities(
        self,
        session_id: str,
        expected_counts: Dict[str, int],
        timeout_sec: float = 1.5,
        poll_interval_sec: float = 0.1
    ) -> Dict[str, Any]:
        """Poll until a session exposes at least the expected entity counts."""
        deadline = time.time() + max(0.1, timeout_sec)
        last_data: Dict[str, Any] = {}
        while time.time() < deadline:
            data = self.api_server.api_get_session_data(session_id, show_error=False) or {}
            last_data = data
            if (
                len(data.get('drones', []) or []) >= expected_counts.get('drones', 0) and
                len(data.get('targets', []) or []) >= expected_counts.get('targets', 0) and
                len(data.get('obstacles', []) or []) >= expected_counts.get('obstacles', 0)
            ):
                return data
            time.sleep(poll_interval_sec)

        actual_counts = {
            'drones': len(last_data.get('drones', []) or []),
            'targets': len(last_data.get('targets', []) or []),
            'obstacles': len(last_data.get('obstacles', []) or []),
        }
        self.logger.warning(
            "Session %s did not reach expected entity counts within %.1fs. expected=%s actual=%s",
            session_id,
            timeout_sec,
            expected_counts,
            actual_counts
        )
        return last_data

    def _select_session_in_list(self, session_id: str):
        for index, session in enumerate(self.sessions):
            if session.get('id') == session_id:
                self.sessions_listbox.selection_clear(0, tk.END)
                self.sessions_listbox.selection_set(index)
                self.sessions_listbox.activate(index)
                self.sessions_listbox.see(index)
                self.on_session_select(None)
                break

    def _template_matches_task_type(self, template_data: Dict[str, Any], session_task_type: str) -> bool:
        return template_matches_task_type(self.template_manager, template_data, session_task_type)

    def _detect_template_entity_groups(self, template_data: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
        return detect_template_entity_groups(template_data)

    def _build_auto_template_params(
        self,
        template_data: Dict[str, Any],
        session_data: Dict[str, Any],
        task_name: str
    ) -> Optional[Dict[str, Any]]:
        return build_auto_template_params(template_data, session_data, task_name, self.username)

    def _auto_create_tasks_for_session(
        self,
        session_id: str,
        session_name: str,
        session_task_type: str,
        task_count: int
    ) -> int:
        session_data = self.api_server.api_get_session_data(session_id, show_error=False) or {}
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
        return result.created_count
                
    def launch_selected_session(self, event=None):
        """Launch the GUI controller for the selected session"""
        # Prevent multiple simultaneous launches
        if self.launching_session:
            self.logger.warning("Session launch already in progress, ignoring request")
            return

        selected = self._require_single_selected_session("launch")
        if not selected:
            return

        _, session = selected
        session_id = session.get('id')
        session_name = session.get('name', 'Unknown')
        
        # Set launching flag
        self.launching_session = True
        
        self.logger.info(f"Launching session: {session_name} ({session_id})")
        
        try:
            # Set this session as current (if not already)
            # Use cached value if available to avoid redundant API call
            is_already_current = (self._cached_current_session_id == session_id)

            set_current_success = False
            if is_already_current:
                self.logger.debug(f"Session {session_id} is already current, skipping set-current call")
                set_current_success = True
            else:
                set_current_response = self.api_server.api_set_session_as_current(session_id)
                set_current_success = set_current_response is not None
                if set_current_success:
                    # Update cache after successfully setting current session
                    self._cached_current_session_id = session_id
                    self.logger.info(f"Set session {session_id} as current")

            if set_current_success:
                self.update_status("Preparing controller data...")
                prefetched_data = {}
                try:
                    # Pass session_id to avoid redundant /sessions/current call
                    prefetched_data = self._prefetch_controller_data(session_id=session_id)
                    # self.logger.info(f"Prefetched {len(prefetched_data)} datasets for GUI controller: {list(prefetched_data.keys())}")
                except Exception as exc:
                    prefetched_data = {}
                    self.logger.warning(f"Prefetch for controller failed: {exc}")

                self.update_status(f"Launching session: {session_name}")

                self.root.withdraw()

                try:
                    # Create a new Tkinter root window for the GUI controller
                    gui_root = tk.Toplevel(self.root)
                    self._set_window_icon(gui_root, set_default=False)
                    gui_root.withdraw()  # Hide initially

                    # Launch GUI controller with prefetched data
                    # Pass the dict as-is (even if empty) - GUI handles it correctly
                    gui = UAVControllerGUI(
                        gui_root,
                        initial_data=prefetched_data,
                        version=self.version,
                        build=self.build,
                    )
                    
                    # Show the GUI window and block until closed
                    gui_root.deiconify()
                    gui_root.wait_window()
                    
                    # When GUI closes, show session manager again
                    self._safe_show_root()
                    # Force fetch after GUI closes as current session may have changed
                    if self._root_alive():
                        try:
                            self.refresh_sessions(force_fetch_current=True)
                            self.update_status("Session closed, back to session manager")
                        except Exception as refresh_exc:
                            self.logger.warning(f"Refresh after GUI close skipped: {refresh_exc}")
                    
                except Exception as e:
                    self.logger.error(f"Error launching GUI: {str(e)}")
                    messagebox.showerror("Launch Error", f"Failed to launch session GUI: {str(e)}")
                    self._safe_show_root()
            else:
                self.update_status("Failed to set current session")
        finally:
            # Always reset the launching flag
            self.launching_session = False

    def _safe_show_root(self):
        """Safely deiconify/lift the session manager window if it still exists."""
        try:
            if self._root_alive():
                self.root.deiconify()
                try:
                    self.root.lift()
                except Exception:
                    pass
        except Exception:
            pass

    def launch_batch_check(self):
        """Open the AI Agent Auto-Check interface."""
        self.logger.info("Launching batch check interface")

        try:
            checker_root = tk.Toplevel(self.root)
            self._set_window_icon(checker_root, set_default=False)
            checker_root.withdraw()

            AgentCheckerApp(checker_root)

            self.root.withdraw()
            checker_root.deiconify()
            checker_root.lift()
            checker_root.focus_force()
            self.update_status("Batch Check interface opened")
            checker_root.wait_window()
            self._safe_show_root()
            self.update_status("Batch Check closed, back to session manager")
        except Exception as exc:
            self.logger.error(f"Error launching batch check interface: {exc}")
            self._safe_show_root()
            messagebox.showerror(
                "Batch Check Error",
                f"Failed to launch batch check interface: {exc}"
            )

    def launch_task_ui(self):
        """Open the multi-session task template flow."""
        self.logger.info("Launching task UI flow")

        try:
            self.root.withdraw()
            launch_task_ui_flow(
                self.root,
                set_icon=lambda window: self._set_window_icon(window, set_default=False),
            )
            self._safe_show_root()
            self.update_status("TaskUI closed, back to session manager")
        except Exception as exc:
            self.logger.error(f"Error launching TaskUI: {exc}")
            self._safe_show_root()
            messagebox.showerror(
                "TaskUI Error",
                f"Failed to launch TaskUI: {exc}"
            )

    def _root_alive(self) -> bool:
        """Check if the Tk root is still alive."""
        try:
            return bool(self.root and self.root.winfo_exists())
        except Exception:
            return False
            
    def _prefetch_controller_data(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetch datasets the GUI controller expects so it can skip redundant API calls.

        Args:
            session_id: If provided, only used for filepath mapping; the API fetches the
                        current session after setting it active.
        """
        datasets: Dict[str, Any] = {}

        try:
            # Fetch the active session with ?data=true so we can reuse the response
            response = self.api_server.api_get_current_session(include_data=True, show_error=False)

            if response is not None and isinstance(response, dict):
                self.logger.debug(f"Prefetch response keys: {list(response.keys())}")

                # Keep full session payload so GUI doesn't need to re-fetch it
                datasets['session'] = response

                # Split collections for GUI convenience (drones/targets/obstacles, etc.)
                collections = extract_session_collections(response)
                for key, value in collections.items():
                    target_key = key
                    datasets[target_key] = value
                    if isinstance(value, list):
                        self.logger.debug(f"Extracted {len(value)} {target_key}")
                    else:
                        self.logger.debug(f"Extracted {target_key}: {type(value)}")

                # Fetch environments list so GUI can skip an extra call
                env_list = self.api_server.api_get_environments(show_error=False)
                if env_list is not None:
                    datasets['environments'] = env_list
                    self.logger.debug(f"Extracted {len(env_list)} environments from prefetch")

                self.logger.info(f"Successfully prefetched {len(datasets)} datasets for GUI controller")

                # Add filepath mapping if available
                if session_id and session_id in self.session_filepath_map:
                    datasets['_imported_filepath'] = self.session_filepath_map[session_id]
                    self.logger.debug(f"Added filepath to prefetch data: {datasets['_imported_filepath']}")

        except Exception as e:
            self.logger.error(f"Error in prefetch with ?data=true: {e}, falling back to individual API calls")

        return datasets

    
            
    def delete_session(self):
        """Delete the selected session"""
        selected_sessions = self._get_selected_sessions()
        if not selected_sessions:
            messagebox.showwarning("No Selection", "Please select a session to delete")
            return

        if len(selected_sessions) == 1:
            confirm_message = (
                f"Are you sure you want to delete session '{selected_sessions[0].get('name', 'Unknown')}'?\n\n"
                "This action cannot be undone."
            )
        else:
            confirm_message = (
                f"Are you sure you want to delete {len(selected_sessions)} selected sessions?\n\n"
                "This action cannot be undone."
            )

        if not messagebox.askyesno("Delete Session", confirm_message):
            return

        deleted_names: List[str] = []
        failed_names: List[str] = []
        for session in selected_sessions:
            session_id = session.get('id')
            session_name = session.get('name', 'Unknown')
            self.update_status(f"Deleting session: {session_name}")
            self.logger.info(f"Deleting session: {session_name} ({session_id})")
            result = self.api_server.api_delete_session(session_id)
            if result is not None:
                self.logger.info(f"Session deleted successfully: {session_id}")
                self._delete_session_storage_files(session_id, session_name)
                deleted_names.append(session_name)
                if self._cached_current_session_id == session_id:
                    self._cached_current_session_id = None
            else:
                failed_names.append(session_name)

        if deleted_names:
            self.refresh_sessions(force_fetch_current=True)
            if failed_names:
                messagebox.showwarning(
                    "Partial Delete",
                    f"Deleted {len(deleted_names)} session(s):\n" + "\n".join(deleted_names) +
                    f"\n\nFailed to delete {len(failed_names)} session(s):\n" + "\n".join(failed_names)
                )
            else:
                if len(deleted_names) == 1:
                    messagebox.showinfo("Success", f"Session '{deleted_names[0]}' deleted successfully!")
                else:
                    messagebox.showinfo("Success", f"Deleted {len(deleted_names)} sessions successfully.")
            self.update_status("Delete completed")
        else:
            self.update_status("Failed to delete session")

    def rename_session(self):
        """Rename the selected session"""
        selected = self._require_single_selected_session("rename")
        if not selected:
            return

        session_index, session = selected
        session_id = session.get('id')
        current_name = session.get('name', 'Unknown')

        # Ask user for new name
        new_name = simpledialog.askstring(
            "Rename Session",
            f"Enter new name for session '{current_name}':",
            initialvalue=current_name,
            parent=self.root
        )

        if not new_name:
            return  # User cancelled

        new_name = new_name.strip()
        if not new_name:
            messagebox.showwarning("Invalid Name", "Session name cannot be empty")
            return

        if new_name == current_name:
            return  # No change

        self.update_status(f"Renaming session: {current_name} -> {new_name}")
        self.logger.info(f"Renaming session: {current_name} ({session_id}) to {new_name}")

        # Update session via API
        update_data = {
            'name': new_name,
            'description': session.get('description', ''),
            'task_type': session.get('task_type', 'others'),
            'task_description': session.get('task_description', '')
        }

        result = self.api_server.api_update_session(session_id, update_data)
        if result:
            self.logger.info(f"Session renamed successfully: {session_id}")

            # Update storage file with new session data
            try:
                settings = get_settings()
                storage_path = Path(settings.get('storage_path', DEFAULT_STORAGE_PATH))

                # Look for existing storage files with old name
                old_safe_name = sanitize_filename(current_name)
                old_safe_id = sanitize_filename(session_id)

                old_file = None
                # Try to find the old storage file
                for old_pattern in [f"{old_safe_name}-{old_safe_id}.json", f"{old_safe_id}.json"]:
                    potential_file = storage_path / old_pattern
                    if potential_file.exists():
                        old_file = potential_file
                        break

                # Fetch the updated session data from API
                updated_session_data = self.api_server.api_get_session_data(session_id)
                if updated_session_data:
                    # Save with the new name
                    saved_path = save_session_to_file(updated_session_data)
                    self.logger.info(f"Saved updated session data to: {saved_path}")

                    # Delete the old file if it exists and is different from the new one
                    if old_file and old_file.exists():
                        new_safe_name = sanitize_filename(new_name)
                        new_file = storage_path / f"{new_safe_name}-{old_safe_id}.json"
                        # Only delete old file if it's different from the new file
                        if old_file.resolve() != new_file.resolve():
                            old_file.unlink()
                            self.logger.info(f"Deleted old storage file: {old_file.name}")
                else:
                    self.logger.warning("Failed to fetch updated session data for storage")

            except Exception as e:
                self.logger.warning(f"Failed to update storage file: {e}")

            messagebox.showinfo("Success", f"Session renamed to '{new_name}' successfully!")
            self.refresh_sessions()
        else:
            self.update_status("Failed to rename session")

    def duplicate_session(self):
        """Duplicate the selected session (similar to Save As in session_editor)"""
        selected = self._require_single_selected_session("duplicate")
        if not selected:
            return

        session_index, session = selected
        session_id = session.get('id')
        original_name = session.get('name', 'Unknown')

        # Suggest a new name
        suggested_name = f"{original_name} (Copy)"

        # Ask user for new session name
        new_name = simpledialog.askstring(
            "Duplicate Session",
            f"Enter name for the duplicated session:",
            initialvalue=suggested_name,
            parent=self.root
        )

        if not new_name:
            return  # User cancelled

        new_name = new_name.strip()
        if not new_name:
            messagebox.showwarning("Invalid Name", "Session name cannot be empty")
            return

        self.update_status(f"Duplicating session: {original_name}")
        self.logger.info(f"Duplicating session: {original_name} ({session_id}) to {new_name}")

        try:
            # Get complete session data using the /data endpoint
            session_data_response = self.api_server.api_get_session_data(session_id)
            if not session_data_response:
                raise Exception("Failed to retrieve session data from API")

            # Prepare copies of all items
            # Remove IDs so the API generates new ones
            drones_copy = []
            for drone in session_data_response.get('drones', []):
                drone_copy = deepcopy(drone)
                drone_copy.pop('id', None)  # Remove ID so API generates new one
                drone_copy['session_id'] = None  # Will be set by API
                drones_copy.append(drone_copy)

            targets_copy = []
            for target in session_data_response.get('targets', []):
                target_copy = deepcopy(target)
                target_copy.pop('id', None)
                target_copy['session_id'] = None
                targets_copy.append(target_copy)

            obstacles_copy = []
            for obstacle in session_data_response.get('obstacles', []):
                obstacle_copy = deepcopy(obstacle)
                obstacle_copy.pop('id', None)
                obstacle_copy['session_id'] = None
                obstacles_copy.append(obstacle_copy)

            tasks_copy = []
            for task in session_data_response.get('tasks', []):
                task_copy = deepcopy(task)
                task_copy.pop('id', None)
                task_copy['session_id'] = None
                tasks_copy.append(task_copy)

            # Build payload with flattened structure (session fields at top level)
            save_payload = {
                'name': new_name,
                'description': session.get('description', '') + ' (duplicated copy)',
                'status': 'active',
                'task_type': session.get('task_type', 'others'),
                'task_description': session.get('task_description', ''),
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

            # Use POST /sessions/new to create new session with all data
            response = self.api_server.api_new_session(save_payload)
            if not response:
                raise Exception("Failed to create duplicated session")

            new_session_id = response.get('id')
            self.logger.info(f"Successfully created duplicated session: {new_session_id}")

            # Save to storage
            self.logger.debug(f"Saving duplicated session {new_session_id} to storage")
            storage_snapshot = self.api_server.api_get_session_data(new_session_id)
            if storage_snapshot:
                try:
                    saved_path = save_session_to_file(storage_snapshot)
                    self.logger.info(f"Duplicated session saved to storage file: {saved_path}")
                except Exception as exc:
                    self.logger.warning(f"Failed to save duplicated session to storage: {exc}")
            else:
                self.logger.warning("Could not fetch snapshot for duplicated session storage")

            messagebox.showinfo(
                "Success",
                f"Session duplicated successfully as '{new_name}'!\n\n"
                f"New Session ID: {new_session_id}\n"
                f"Drones: {len(drones_copy)}\n"
                f"Targets: {len(targets_copy)}\n"
                f"Obstacles: {len(obstacles_copy)}\n"
                f"Tasks: {len(tasks_copy)}"
            )

            self.refresh_sessions()
            self.update_status(f"Session duplicated successfully: {new_name}")

        except Exception as e:
            self.logger.exception(f"Failed to duplicate session: {e}")
            messagebox.showerror("Error", f"Failed to duplicate session: {str(e)}")
            self.update_status("Failed to duplicate session")

    def export_session(self):
        """Export session data to JSON file using the new /data endpoint"""
        selected_sessions = self._get_selected_sessions()
        if not selected_sessions:
            messagebox.showwarning("No Selection", "Please select a session to export")
            return
        if len(selected_sessions) == 1:
            self._export_single_session(selected_sessions[0])
            return

        export_dir = filedialog.askdirectory(title="Select Export Folder")
        if not export_dir:
            return

        exported_files: List[str] = []
        failed_names: List[str] = []
        for session in selected_sessions:
            session_id = session.get('id')
            session_name = session.get('name', 'Unknown')
            safe_name = sanitize_filename(session_name)
            safe_id = sanitize_filename(session_id)
            target_path = Path(export_dir) / f"{safe_name}-{safe_id}-export.json"
            if self._export_session_to_path(session, str(target_path)):
                exported_files.append(target_path.name)
            else:
                failed_names.append(session_name)

        if exported_files:
            self.refresh_sessions()
            if failed_names:
                messagebox.showwarning(
                    "Partial Export",
                    f"Exported {len(exported_files)} session(s) to:\n{export_dir}\n\n"
                    f"Failed to export {len(failed_names)} session(s):\n" + "\n".join(failed_names)
                )
            else:
                messagebox.showinfo("Success", f"Exported {len(exported_files)} sessions to:\n{export_dir}")
            self.update_status("Session export completed")
        else:
            self.update_status("Failed to export sessions")

    def _export_single_session(self, session: Dict[str, Any]):
        session_id = session.get('id')
        session_name = session.get('name', 'Unknown')
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
            return

        if self._export_session_to_path(session, filename):
            messagebox.showinfo("Success", f"Session exported successfully to:\n{filename}")
            self.refresh_sessions()
            self.update_status("Session exported successfully")
        else:
            self.update_status("Failed to export session")

    def _export_session_to_path(self, session: Dict[str, Any], filename: str) -> bool:
        session_id = session.get('id')
        session_name = session.get('name', 'Unknown')
        self.update_status(f"Exporting session: {session_name}")
        self.logger.info(f"Exporting session data for: {session_name} (ID: {session_id})")

        session_data = self.api_server.api_get_session_data(session_id)
        if not session_data:
            self.logger.error(f"Failed to get session data for export: {session_id}")
            return False

        try:
            cleaned_session_data = _clean_session_data_for_export(session_data)
            server_version = None
            try:
                server_version = self.api_server.api_get_server_version(show_error=False)
            except Exception as exc:
                self.logger.debug(f"Failed to fetch server version for export: {exc}")

            export_data = {
                "export_info": {
                    "exported_at": datetime.now().isoformat(),
                    "exported_by": "MultiUAV-Plat Control System Session Manager",
                    "version": self.version,
                    "server_version": server_version
                },
                **cleaned_session_data
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            stats = session_data.get('statistics', {}) or {}
            self.logger.info(f"Session exported successfully to: {filename}")
            self.logger.info(
                "Export contains: %s drones, %s targets, %s obstacles",
                stats.get('drone_count', 0),
                stats.get('target_count', 0),
                stats.get('obstacle_count', 0)
            )

            if session_id:
                self.api_server.api_update_session_status(session_id, 'inactive')
            return True
        except Exception as e:
            self.logger.error(f"Error exporting session {session_id}: {str(e)}")
            messagebox.showerror("Export Error", f"Failed to export session '{session_name}': {str(e)}")
            return False
            
    def preview_selected_session(self, event=None):
        """Handle spacebar shortcut to preview the selected session."""
        self.load_session()
        return "break" if event else None

    def load_session(self):
        """Load selected session data using the enhanced /data endpoint"""
        selected = self._require_single_selected_session("load")
        if not selected:
            return

        selection_index, _ = selected
        session_id = self.sessions[selection_index]['id']
        session_name = self.sessions[selection_index]['name']
        
        try:
            self.update_status("Loading session data...")
            self.logger.info(f"Loading session data: {session_id}")
            
            # Get complete session data using the enhanced /data endpoint
            session_data = self.api_server.api_get_session_data(session_id)
            
            if session_data:
                session_info = extract_session_metadata(session_data) or {}
                drones = session_data.get('drones', []) or []
                targets = session_data.get('targets', []) or []
                obstacles = session_data.get('obstacles', []) or []
                environment = session_data.get('environment')

                # Log detailed information about loaded data
                self.logger.info(f"Loaded session '{session_name}' with:")
                self.logger.info(f"  - {len(drones)} drones")
                self.logger.info(f"  - {len(targets)} targets")
                self.logger.info(f"  - {len(obstacles)} obstacles")
                self.logger.info(f"  - Environment: {'Yes' if environment else 'No'}")

                # Display session data in a new window with enhanced information
                self.show_session_data(session_name, session_data, selection_index)
                self.update_status(f"Session data loaded: {len(drones)} drones, {len(targets)} targets, {len(obstacles)} obstacles")
                self.api_server.api_update_session_status(session_id, 'inactive')
                self.refresh_sessions()
            else:
                self.update_status("Failed to load session data")
                
        except Exception as e:
            self.logger.error(f"Error loading session: {str(e)}")
            messagebox.showerror("Load Error", f"Failed to load session: {str(e)}")
            self.update_status("Failed to load session data")
            self.api_server.api_update_session_status(session_id, 'inactive')
            self.refresh_sessions()

    def edit_session(self):
        """Launch visual session editor for selected session"""
        selected = self._require_single_selected_session("edit")
        if not selected:
            return

        session_index, session = selected
        session_id = session['id']
        session_name = session['name']

        try:
            self.update_status("Loading session for editing...")
            self.logger.info(f"Opening session editor for: {session_id}")

            # Activate the selected session before editing (if not already current)
            is_already_current = (self._cached_current_session_id == session_id)
            if is_already_current:
                self.logger.debug(f"Session {session_id} is already current, skipping set-current call")
            else:
                self.logger.info(f"Activating session {session_id} for editing...")
                activate_response = self.api_server.api_set_session_as_current(session_id)
                if not activate_response:
                    self.logger.warning(f"Failed to activate session {session_id}, continuing anyway...")
                else:
                    # Update cache after setting current session
                    self._cached_current_session_id = session_id

            # Get complete session data
            session_data = self.api_server.api_get_session_data(session_id)

            if session_data:
                session_metadata = extract_session_metadata(session_data) or {}
                try:
                    if start_session_editor is None:
                        raise ImportError(SESSION_EDITOR_IMPORT_ERROR or "Session editor unavailable")
                    # Hide the session manager window
                    self.logger.info("Hiding session manager window")
                    self.root.withdraw()

                    # Launch the session editor (this blocks until editor closes)
                    self.logger.info(f"Launching session editor for '{session_name}'")
                    try:
                        start_session_editor(
                            session_id=session_id,
                            session_data=session_metadata
                        )
                        self.logger.info("Session editor returned normally")
                    except Exception as editor_error:
                        self.logger.error(f"Session editor raised exception: {editor_error}")
                        raise

                    # Show the session manager window again
                    self.logger.info("Showing session manager window again")
                    self.root.deiconify()
                    self.root.update()  # Force window update
                    self.root.lift()
                    self.root.focus_force()
                    self.root.attributes('-topmost', True)  # Bring to front
                    self.root.after(100, lambda: self.root.attributes('-topmost', False))  # Remove topmost after brief delay

                    # Refresh after editor closes - force fetch as editor may have changed session
                    self.refresh_sessions(force_fetch_current=True)
                    self.update_status(f"Session editor closed")

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
                    try:
                        self.logger.info("Attempting to restore session manager window after error")
                        self.root.deiconify()
                        self.root.update()
                        self.root.lift()
                        self.root.focus_force()
                    except Exception as restore_error:
                        self.logger.error(f"Failed to restore session manager window: {restore_error}")
                    messagebox.showerror("Editor Error", f"Error in session editor: {str(e)}")
                    self.update_status("Session editor error")
            else:
                self.update_status("Failed to load session data for editing")

        except Exception as e:
            self.logger.error(f"Error opening session editor: {str(e)}")
            # Show window again on error
            try:
                self.root.deiconify()
            except:
                pass
            messagebox.showerror("Editor Error", f"Failed to open session editor: {str(e)}")
            self.update_status("Failed to open session editor")

    def load_storage_config(self):
        """Load storage folder configuration from shared settings."""
        try:
            self.imported_storage_files.clear()
            # Get from shared settings
            self.session_storage_path = self.app_settings.get('session_storage_path')
            self.template_storage_path = self.app_settings.get('template_storage_path')

            if not self.session_storage_path or not os.path.isdir(self.session_storage_path):
                self.session_storage_path = DEFAULT_STORAGE_PATH
                # Update in settings
                self.app_settings.set('session_storage_path', self.session_storage_path)

            if not self.template_storage_path or not os.path.isdir(self.template_storage_path):
                self.template_storage_path = DEFAULT_TEMPLATE_PATH
                self.app_settings.set('template_storage_path', self.template_storage_path)

            try:
                Path(self.session_storage_path).mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                self.logger.warning(f"Failed to ensure storage directory exists: {exc}")

            try:
                Path(self.template_storage_path).mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                self.logger.warning(f"Failed to ensure template directory exists: {exc}")

            self.template_manager = TaskTemplateManager(template_dir=self.template_storage_path)
            self.auto_import_sessions_from_storage()
        except Exception as exc:
            self.logger.warning(f"Failed to load session storage configuration: {exc}")
            self.session_storage_path = DEFAULT_STORAGE_PATH
            self.template_storage_path = DEFAULT_TEMPLATE_PATH
            try:
                Path(self.session_storage_path).mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            try:
                Path(self.template_storage_path).mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            self.template_manager = TaskTemplateManager(template_dir=self.template_storage_path)
            self.auto_import_sessions_from_storage()

    def save_storage_config(self):
        """Persist storage folder configuration to shared settings."""
        try:
            self.app_settings.set('session_storage_path', self.session_storage_path)
        except Exception as exc:
            self.logger.warning(f"Failed to save session storage configuration: {exc}")

    def auto_import_sessions_from_storage(self):
        """Import all session files located in the configured storage directory.

        Only imports sessions that don't already exist on the server to avoid redundant API calls.
        """
        if not self.session_storage_path:
            return
        storage_dir = Path(self.session_storage_path)
        try:
            storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self.logger.error(f"Failed to prepare session storage directory: {exc}")
            return

        # Get list of existing sessions from server to avoid re-importing
        existing_sessions = self.api_server.api_get_sessions()
        existing_session_ids = set()
        if existing_sessions:
            existing_session_ids = {s.get('id') for s in existing_sessions if s.get('id')}
            self.logger.info(f"Found {len(existing_session_ids)} existing sessions on server")

        imported_any = False
        skipped_existing = 0
        for json_file in sorted(storage_dir.glob('*.json')):
            resolved = str(json_file.resolve())
            if resolved in self.imported_storage_files:
                continue
            try:
                payload, _ = load_session_from_file(json_file)

                if not isinstance(payload, dict):
                    self.logger.warning(f"Skipping storage file without valid session payload: {json_file}")
                    self.imported_storage_files.add(resolved)
                    continue

                session_id = payload.get('id')
                if not session_id:
                    self.logger.warning(f"Skipping storage file without session ID: {json_file}")
                    self.imported_storage_files.add(resolved)
                    continue

                # Skip if session already exists on server
                if session_id in existing_session_ids:
                    self.logger.debug(f"Session {session_id} already exists on server, skipping import")
                    self.imported_storage_files.add(resolved)
                    skipped_existing += 1
                    continue

                request_data = dict(payload)
                request_data['status'] = 'inactive'
                request_data = normalize_session_canvas_fields(request_data)

                result = self.api_server.api_new_session_with_id(session_id, request_data)
                if result is not None:
                    imported_any = True
                    self.imported_storage_files.add(resolved)
                    # Store the filepath mapping
                    self.session_filepath_map[session_id] = resolved
            except Exception as exc:
                self.logger.error(f"Failed to import session file {json_file}: {exc}")

        # Log summary
        if skipped_existing > 0:
            self.logger.info(f"Skipped {skipped_existing} existing session(s) already on server")
        if imported_any:
            self.logger.info(f"Imported new session(s) from storage")


    def save_session_to_storage(self, session_id: str, session_name: str):
        """Export specified session data to the configured storage folder."""
        data = self.api_server.api_get_session_data(session_id)
        if not data:
            return None

        try:
            target_path = save_session_to_file(data, storage_dir=self.session_storage_path)
            self.imported_storage_files.add(str(target_path.resolve()))
            self.api_server.api_update_session_status(session_id, 'inactive')
            return target_path
        except Exception as exc:
            self.logger.error(f"Failed to save session to storage: {exc}")
            return None

    def save_session_screenshot(self, session_id: str, session_name: str, json_path: Optional[Path] = None):
        if not self.session_storage_path:
            return
        storage_dir = Path(self.session_storage_path)
        try:
            storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self.logger.error(f"Failed to prepare storage directory for screenshot: {exc}")
            return

        safe_name = sanitize_filename(session_name)
        if json_path and json_path.parent == storage_dir:
            target_path = json_path.with_suffix('.jpg')
        else:
            target_path = storage_dir / f"{safe_name}_{session_id}_init.jpg"

        try:
            screenshot_width, screenshot_height = self._resolve_session_screenshot_size(
                session_id=session_id,
                json_path=json_path
            )
            self.api_server.api_set_session_as_current(session_id, show_error=False)
            content = self.api_server.api_get_session_screenshot(
                fmt='jpg',
                width=screenshot_width,
                height=screenshot_height,
                show_error=False
            )
            
            if content:
                with target_path.open('wb') as fh:
                    fh.write(content)
                self.logger.info(
                    "Saved session screenshot to %s at %sx%s",
                    target_path,
                    screenshot_width,
                    screenshot_height
                )
            else:
                self.logger.warning(f"Failed to capture screenshot for session {session_id}")
        except Exception as exc:
            self.logger.error(f"Failed to save screenshot: {exc}")

    def _resolve_session_screenshot_size(self, session_id: str, json_path: Optional[Path] = None) -> Tuple[int, int]:
        """Size generated screenshots at 2x for small maps and 1x for larger maps."""
        session_data: Dict[str, Any] = {}

        if json_path and json_path.exists():
            try:
                with json_path.open('r', encoding='utf-8') as fh:
                    session_data = json.load(fh)
            except Exception as exc:
                self.logger.warning("Failed to read session file for screenshot sizing: %s", exc)

        if not session_data:
            session_data = self.api_server.api_get_session_data(session_id, show_error=False) or {}

        canvas_width = session_data.get('canvas_width')
        canvas_height = (
            session_data.get('canvas_length')
            if session_data.get('canvas_length') is not None
            else session_data.get('canvas_height')
        )
        scale_factor = self._get_default_session_screenshot_scale_factor(canvas_width, canvas_height)

        try:
            width = max(1, int(round(float(canvas_width) * scale_factor)))
        except (TypeError, ValueError):
            width = int(BASE_AREA_WIDTH * 2)

        try:
            height = max(1, int(round(float(canvas_height) * scale_factor)))
        except (TypeError, ValueError):
            height = int(BASE_AREA_HEIGHT * 2)

        return width, height

    def _get_default_session_screenshot_scale_factor(self, canvas_width: Any, canvas_height: Any) -> int:
        """Use 2x for maps up to the base area, otherwise 1x."""
        try:
            width = float(canvas_width)
        except (TypeError, ValueError):
            width = BASE_AREA_WIDTH

        try:
            height = float(canvas_height)
        except (TypeError, ValueError):
            height = BASE_AREA_HEIGHT

        if width <= BASE_AREA_WIDTH and height <= BASE_AREA_HEIGHT:
            return 2
        return 1

    def _delete_session_storage_files(self, session_id: str, session_name: str):
        if not self.session_storage_path:
            return
        storage_dir = Path(self.session_storage_path)
        safe_name = sanitize_filename(session_name)
        patterns = [
            storage_dir / f"{safe_name}_{session_id}.json",
            storage_dir / f"{safe_name}_{session_id}_init.jpg"
        ]
        for path in patterns:
            try:
                if path.exists():
                    path.unlink()
                    self.logger.info(f"Removed session file {path}")
            except Exception as exc:
                self.logger.warning(f"Failed to remove session file {path}: {exc}")
            
    def show_session_data(self, session_name, session_data, selection_index=None):
        """Display session data in a new window using DetailPanel"""
        data_window = tk.Toplevel(self.root)
        self._set_window_icon(data_window, set_default=False)
        data_window.title(f"Session Data: {session_name}")
        set_window_geometry_and_center(data_window, 600, 500, self.root)

        # Store navigation context as window attributes
        data_window._current_index = selection_index
        data_window._detail_panel = None  # Will be set after creating the widget

        def close_preview(event=None):
            if selection_index is not None:
                try:
                    self.sessions_listbox.selection_clear(0, tk.END)
                    self.sessions_listbox.selection_set(selection_index)
                    self.sessions_listbox.see(selection_index)
                    self.sessions_listbox.activate(selection_index)
                    self.sessions_listbox.selection_anchor(selection_index)
                    self.sessions_listbox.focus_set()
                    self.on_session_select(None)
                except Exception:
                    pass
            data_window.destroy()
            return "break" if event else None

        def navigate_previous(event=None):
            """Navigate to the previous session"""
            current_idx = data_window._current_index
            if current_idx is not None and current_idx > 0:
                new_index = current_idx - 1
                self._update_session_preview(data_window, new_index)
            return "break"

        def navigate_next(event=None):
            """Navigate to the next session"""
            current_idx = data_window._current_index
            if current_idx is not None and current_idx < len(self.sessions) - 1:
                new_index = current_idx + 1
                self._update_session_preview(data_window, new_index)
            return "break"

        def handle_space_close(event=None):
            focus_widget = data_window.focus_get()
            if focus_widget is not None:
                widget_class = focus_widget.winfo_class()
                if widget_class in ("Entry", "TEntry", "Text", "TCombobox"):
                    return
            return close_preview(event)

        data_window.bind("<space>", handle_space_close)
        data_window.bind("<Escape>", close_preview)
        data_window.protocol("WM_DELETE_WINDOW", close_preview)
        
        # Create DetailPanel
        detail_panel = DetailPanel(
            data_window, 
            data=session_data, 
            view_raw_data_title=f"Session Data: {session_name}",
            on_close=close_preview,
            on_prev_item=lambda: navigate_previous(),
            on_next_item=lambda: navigate_next()
        )
        detail_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Store detail panel reference for updates
        data_window._detail_panel = detail_panel

    def _update_session_preview(self, data_window, new_index):
        """Update the session preview window with new session data"""
        if new_index < 0 or new_index >= len(self.sessions):
            return

        # Update listbox selection
        self.sessions_listbox.selection_clear(0, tk.END)
        self.sessions_listbox.selection_set(new_index)
        self.sessions_listbox.see(new_index)
        self.sessions_listbox.activate(new_index)

        # Get new session data
        session = self.sessions[new_index]
        session_id = session['id']
        session_name = session['name']

        try:
            # Fetch session data
            session_data = self.api_server.api_get_session_data(session_id)

            if session_data:
                # Update window title
                data_window.title(f"Session Data: {session_name}")

                # Update current index
                data_window._current_index = new_index

                # Update detail panel content
                detail_panel = data_window._detail_panel
                if detail_panel:
                    detail_panel.load_data(session_data)
                    # Update raw view title
                    detail_panel.view_raw_data_title = f"Session Data: {session_name}"

                # Update the session details panel
                self.on_session_select(None)

        except Exception as e:
            self.logger.error(f"Error updating session preview: {str(e)}")

    def import_session(self):
        """Import session data from JSON file using the new /restore endpoint"""
        filename = filedialog.askopenfilename(
            title="Import Session",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                import_data, resolved_path = load_session_from_file(filename)
                
                export_info = import_data.get('export_info', {})
                if export_info:
                    self.logger.info(f"Importing session exported at: {export_info.get('exported_at', 'Unknown')}")

                if not isinstance(import_data, dict):
                    messagebox.showerror("Import Error", "Invalid session file format. No session data found.")
                    return

                self.update_status("Importing session...")
                self.logger.info(f"Importing session from: {filename}")

                request_data = normalize_session_canvas_fields(import_data)
                restored_session = self.api_server.api_new_session(request_data)

                if restored_session:
                    session_id = restored_session.get('id')
                    restored_stats = restored_session.get('statistics', {})

                    # Store the filepath mapping
                    self.session_filepath_map[session_id] = str(resolved_path)

                    self.logger.info(f"Session restored successfully: {session_id}")
                    self.logger.info(f"Restored: {restored_stats.get('drone_count', 0)} drones, {restored_stats.get('target_count', 0)} targets, {restored_stats.get('obstacle_count', 0)} obstacles")
                    self.logger.info(f"Stored filepath mapping: {session_id} -> {resolved_path}")

                    messagebox.showinfo("Success",
                        f"Session imported successfully!\n\n"
                        f"Restored:\n"
                        f"• {restored_stats.get('drone_count', 0)} drones\n"
                        f"• {restored_stats.get('target_count', 0)} targets\n"
                        f"• {restored_stats.get('obstacle_count', 0)} obstacles\n"
                        f"• Environment: {'Yes' if restored_stats.get('environment_id') else 'No'}\n\n"
                        f"Session ID: {session_id}")

                        # Force fetch current session after import
                    self.refresh_sessions(force_fetch_current=True)
                    self.update_status("Session imported successfully")
                else:
                    self.update_status("Failed to import session")
                        
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error: {str(e)}")
                messagebox.showerror("Import Error", f"Invalid JSON file: {str(e)}")
            except Exception as e:
                self.logger.error(f"Error importing session: {str(e)}")
                messagebox.showerror("Import Error", f"Failed to import session: {str(e)}")
                
    def on_settings_saved(self, updated_settings: Dict[str, Any]):
        """Callback when settings are saved from the dialog."""
        self.username = updated_settings.get('username', 'SYSTEM')
        
        # Check if storage path changed
        old_path = self.session_storage_path
        new_path = updated_settings.get('session_storage_path')
        
        if new_path != old_path:
            self.session_storage_path = new_path
            # Reload imports if path changed
            self.imported_storage_files.clear()
            self.auto_import_sessions_from_storage()
        
        self.template_storage_path = updated_settings.get('template_storage_path')
        self.template_manager = TaskTemplateManager(template_dir=self.template_storage_path)
        
        # Update API key
        new_key = updated_settings.get('api_key')
        self.api_server.api_key = resolve_api_key(new_key)
        
        self.logger.info("Session Manager settings refreshed from dialog.")

    def show_settings(self):
        """Show settings dialog for user profile, storage, and API configuration"""
        show_settings_dialog(self.root, self.on_settings_saved)

    def show_about(self):
        """Show About dialog with system information"""
        show_about_dialog(
            self.root,
            version=self.version,
            build=self.build,
            api_base_url=self.api_server.api_base_url,
            api_connected=not self._server_unavailable,
            set_icon=lambda dialog: self._set_window_icon(dialog, set_default=False),
        )

    def run(self):
        """Run the session manager"""
        self.root.mainloop()

    # --- Random population helpers ---
    def populate_session_random(
        self,
        session_id: str,
        drone_count: int,
        target_count: int,
        obstacle_count: int,
        area_width: float = 1024.0,
        area_height: float = 768.0,
        task_type: str = 'others',
        do_not_scatter_drones: bool = False
    ):
        """Populate the given session with random drones, targets, and obstacles"""
        # Ensure session is current so created resources attach correctly
        response = self.api_server.api_set_session_as_current(session_id)
        if response is not None:
            # Update cache after setting current session
            self._cached_current_session_id = session_id

        # Generate all session data using the random generator
        session_data = self.random_generator.generate_session_data(
            drone_count=drone_count,
            target_count=target_count,
            obstacle_count=obstacle_count,
            area_width=area_width,
            area_height=area_height,
            task_type=task_type,
            do_not_scatter_drones=do_not_scatter_drones
        )

        # Create targets
        for payload in session_data['targets']:
            self.api_server.api_create_target(payload)

        # Create obstacles
        for payload in session_data['obstacles']:
            self.api_server.api_create_obstacle(payload)

        # Create drones
        for payload in session_data['drones']:
            self.api_server.api_create_drone(payload)


    def _ensure_environment_for_session(self, session_id: str, session_name: str) -> bool:
        """Ensure there is at least one environment for the newly created session."""
        try:
            environments = self.api_server.api_get_environments() or []
            if environments:
                env_id = environments[0].get('id')
                if env_id:
                    try:
                        self.api_server.api_set_environment_as_current(env_id)
                    except Exception:
                        pass
                return True

            env_payload = self._default_environment_payload(session_name)
            created_env = self.api_server.api_create_environment(env_payload)
            if created_env and created_env.get('id'):
                env_id = created_env['id']
                self.api_server.api_set_environment_as_current(env_id)
                return True
        except Exception as exc:
            self.logger.error(f"Failed to provision default environment for session {session_id}: {exc}")
        return False

    def _default_environment_payload(self, session_name: str) -> Dict[str, Any]:
        """Generate a default environment payload for new sessions."""
        return self.random_generator.generate_environment_payload(session_name)

    def _auto_session_description(
        self,
        name: str,
        area_width: float,
        area_height: float,
        task_type: Optional[str],
        populate_random: bool,
        drone_count: int,
        target_count: int,
        obstacle_count: int,
        with_examples: bool
    ) -> str:
        return self.random_generator.generate_session_description(
            name=name,
            area_width=area_width,
            area_height=area_height,
            task_type=task_type,
            populate_random=populate_random,
            drone_count=drone_count,
            target_count=target_count,
            obstacle_count=obstacle_count,
            with_examples=with_examples
        )


class SessionDialog:
    """Dialog for creating/editing sessions"""
    
    def __init__(self, parent, title, initial_data=None):
        self.result = None
        self.parent = parent
        
        self.dialog = tk.Toplevel(parent)
        icon_image = getattr(parent, "_uav_icon_image", None)
        if icon_image is None:
            icon_path = Path(__file__).resolve().parent / "img" / "controller.png"
            if icon_path.exists():
                try:
                    icon_image = tk.PhotoImage(file=str(icon_path))
                except Exception:
                    icon_image = None
        if icon_image is not None:
            self.dialog.iconphoto(False, icon_image)
            setattr(self.dialog, "_uav_icon_image", icon_image)
        self._icon_image = icon_image
        self.dialog.title(title)
        set_window_geometry_and_center(self.dialog, 520, 660, parent)
        
        self.create_widgets(initial_data or {})
        self.dialog.wait_window()
        
    def create_widgets(self, initial_data):
        """Create dialog widgets"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        self.batch_count = 1
        
        # Session name
        ttk.Label(main_frame, text="Session Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(main_frame, width=40)
        self.name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        self.name_entry.insert(0, initial_data.get('name', ''))
        
        # Description
        ttk.Label(main_frame, text="Description:").grid(row=1, column=0, sticky=(tk.W, tk.N), pady=5)
        self.description_text = tk.Text(main_frame, width=40, height=6)
        self.description_text.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        self.description_text.insert('1.0', initial_data.get('description', ''))

        # Task selection
        ttk.Label(main_frame, text="Task Type:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.task_var = tk.StringVar(value=initial_data.get('task_type', 'others'))
        ttk.Combobox(
            main_frame,
            textvariable=self.task_var,
            values=[
                "area_search",
                "area_assignment_and_patrol",
                "target_assignment",
                "target_tracking",
                "others"
            ],
            state="readonly",
            width=38
        ).grid(row=2, column=1, sticky=tk.W, pady=5)

        # Task description
        ttk.Label(main_frame, text="Task Des.:").grid(row=3, column=0, sticky=(tk.W, tk.N), pady=5)
        self.task_description_text = tk.Text(main_frame, width=40, height=4)
        self.task_description_text.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        self.task_description_text.insert('1.0', initial_data.get('task_description', ''))

        # Area dimensions - Use predefined sizes
        ttk.Label(main_frame, text="Area Size (m):").grid(row=4, column=0, sticky=tk.W, pady=5)
        area_frame = ttk.Frame(main_frame)
        area_frame.grid(row=4, column=1, sticky=tk.W, pady=5)

        # Build area size options with scale factors
        area_size_options = []
        for i, (w, h) in enumerate(PREDEFINED_AREA_SIZES):
            scale = AREA_SIZE_MULTIPLIERS[i]
            if scale == 1.0:
                area_size_options.append(f"{w} × {h} (Standard, 1.0×)")
            else:
                area_size_options.append(f"{w} × {h} ({scale}×)")

        # Find initial selection based on current values
        initial_width = float(initial_data.get('area_width', BASE_AREA_WIDTH) or BASE_AREA_WIDTH)
        initial_height = float(initial_data.get('area_height', BASE_AREA_HEIGHT) or BASE_AREA_HEIGHT)
        initial_selection = 1  # Default to standard size (1.0×)
        for i, (w, h) in enumerate(PREDEFINED_AREA_SIZES):
            if abs(w - initial_width) < 1 and abs(h - initial_height) < 1:
                initial_selection = i
                break

        self.area_size_var = tk.StringVar(value=area_size_options[initial_selection])
        area_combo = ttk.Combobox(
            area_frame,
            textvariable=self.area_size_var,
            values=area_size_options,
            state="readonly",
            width=30
        )
        area_combo.pack(side=tk.LEFT)
        area_combo.current(initial_selection)

        # Session initialization options aligned with POST /sessions
        ttk.Label(main_frame, text="Initialization:").grid(row=5, column=0, sticky=tk.W, pady=(12, 4))
        default_mode = 'examples'
        if initial_data.get('populate_random'):
            default_mode = 'random'
        elif initial_data.get('with_examples') is False:
            default_mode = 'empty'
        self.init_mode = tk.StringVar(value=default_mode)
        
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=5, column=1, sticky=tk.W, pady=(12, 4))
        ttk.Radiobutton(
            options_frame,  
            text="Seed with API example data",
            value='examples',
            variable=self.init_mode,
            command=self.update_init_mode_state
        ).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(
            options_frame,
            text="Start empty session",
            value='empty',
            variable=self.init_mode,
            command=self.update_init_mode_state
        ).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(
            options_frame,
            text="Start auto-generate random entities",
            value='random',
            variable=self.init_mode,
            command=self.update_init_mode_state
        ).pack(anchor=tk.W, pady=2)
        
        
        
        # Counts for entities when random data is requested
        counts_frame = ttk.LabelFrame(main_frame, text="Random entity counts")
        counts_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8)

        self.random_counts_label = ttk.Label(counts_frame, text="Drones:")
        self.random_counts_label.grid(row=0, column=0, sticky=tk.W, padx=(0,6), pady=4)
        self.drone_count_var = tk.IntVar(value=int(initial_data.get('drone_count', 3) or 0))
        self.drone_count_spin = ttk.Spinbox(counts_frame, from_=0, to=50, textvariable=self.drone_count_var, width=4)
        self.drone_count_spin.grid(row=0, column=1, sticky=tk.W, pady=4)

        ttk.Label(counts_frame, text="Targets:").grid(row=0, column=2, sticky=tk.W, padx=(12,6), pady=4)
        self.target_count_var = tk.IntVar(value=int(initial_data.get('target_count', 6) or 0))
        self.target_count_spin = ttk.Spinbox(counts_frame, from_=0, to=100, textvariable=self.target_count_var, width=4)
        self.target_count_spin.grid(row=0, column=3, sticky=tk.W, pady=4)

        ttk.Label(counts_frame, text="Obstacles:").grid(row=0, column=4, sticky=tk.W, padx=(12,6), pady=4)
        self.obstacle_count_var = tk.IntVar(value=int(initial_data.get('obstacle_count', 6) or 0))
        self.obstacle_count_spin = ttk.Spinbox(counts_frame, from_=0, to=100, textvariable=self.obstacle_count_var, width=4)
        self.obstacle_count_spin.grid(row=0, column=5, sticky=tk.W, pady=4)
        self.random_count_controls = [
            self.drone_count_spin,
            self.target_count_spin,
            self.obstacle_count_spin
        ]

        task_options_frame = ttk.Frame(main_frame)
        task_options_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(4, 8))
        self.auto_generate_tasks_var = tk.BooleanVar(value=bool(initial_data.get('auto_generate_tasks', False)))
        ttk.Checkbutton(
            task_options_frame,
            text="Create tasks from templates",
            variable=self.auto_generate_tasks_var,
            command=self.update_auto_task_state
        ).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(task_options_frame, text="Task Num:").grid(row=0, column=1, sticky=tk.W, pady=2, padx=(16, 6))
        self.generated_task_count_var = tk.IntVar(value=int(initial_data.get('generated_task_count', 3) or 0))
        self.generated_task_count_spin = ttk.Spinbox(
            task_options_frame,
            from_=0,
            to=100,
            textvariable=self.generated_task_count_var,
            width=6
        )
        self.generated_task_count_spin.grid(row=0, column=2, sticky=tk.W, pady=2)

        self.generate_screenshot_var = tk.BooleanVar(value=bool(initial_data.get('generate_screenshot', False)))
        ttk.Checkbutton(
            main_frame,
            text="Generate session init screenshot",
            variable=self.generate_screenshot_var
        ).grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=(0, 3))

        self.do_not_scatter_drones_var = tk.BooleanVar(value=bool(initial_data.get('do_not_scatter_drones', False)))
        self.do_not_scatter_drones_check = ttk.Checkbutton(
            main_frame,
            text="Do NOT scatter the drones",
            variable=self.do_not_scatter_drones_var
        )
        self.do_not_scatter_drones_check.grid(row=9, column=0, columnspan=2, sticky=tk.W, pady=(0, 3))

        self.auto_load_created_session_var = tk.BooleanVar(value=bool(initial_data.get('auto_load_created_session', False)))
        ttk.Checkbutton(
            main_frame,
            text="Auto load created session",
            variable=self.auto_load_created_session_var
        ).grid(row=10, column=0, columnspan=2, sticky=tk.W, pady=(0, 6))

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=11, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Create", command=self.ok_clicked).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Create Batch", command=self.ok_clicked_batch).pack(side=tk.LEFT, padx=5)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        
        # Apply initial mode state
        self.update_init_mode_state()
        self.update_auto_task_state()
        
        # Focus on name entry
        self.name_entry.focus()
        self.name_entry.select_range(0, tk.END)
        self.name_entry.icursor(tk.END)
        
    def ok_clicked(self):
        """Handle OK button click"""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Session name is required")
            return
            
        description = self.description_text.get('1.0', tk.END).strip()
        mode = self.init_mode.get()
        populate_random = (mode == 'random')
        with_examples = (mode == 'examples')
        if populate_random:
            with_examples = False
        task = self.task_var.get() or 'others'
        task_description = self.task_description_text.get('1.0', tk.END).strip()
        drone_count = int(self.drone_count_var.get())
        target_count = int(self.target_count_var.get())
        obstacle_count = int(self.obstacle_count_var.get())
        auto_generated = False

        # Parse selected area size from combobox
        try:
            area_size_str = self.area_size_var.get()
            # Extract width and height from format "width × height (...)"
            match = re.match(r'(\d+)\s*×\s*(\d+)', area_size_str)
            if match:
                area_width = float(match.group(1))
                area_height = float(match.group(2))
            else:
                # Fallback to default
                area_width = BASE_AREA_WIDTH
                area_height = BASE_AREA_HEIGHT
        except Exception:
            messagebox.showerror("Error", "Failed to parse area size")
            return

        if area_width <= 0 or area_height <= 0:
            messagebox.showerror("Error", "Area width and height must be positive")
            return

        if not description:
            area_str = f"{area_width:.0f}×{area_height:.0f} m"
            task_label = (task or '').replace('_', ' ').strip() or 'general operations'

            desc_parts = [
                f"{name} covers a {area_str} mission zone.",
                f"It is configured for {task_label}."
            ]

            if populate_random:
                count_bits = []
                if drone_count > 0:
                    count_bits.append(f"{drone_count} drones")
                if target_count > 0:
                    count_bits.append(f"{target_count} targets")
                if obstacle_count > 0:
                    count_bits.append(f"{obstacle_count} obstacles")
                if count_bits:
                    desc_parts.append("Random seeding will create " + ", ".join(count_bits) + ".")
            else:
                if with_examples:
                    desc_parts.append("It will load with the API example data.")
                else:
                    desc_parts.append("It starts empty and ready for manual population.")

            description = " ".join(desc_parts)
            auto_generated = True
        
        current_batch = getattr(self, 'batch_count', 1)
        self.result = {
            'name': name,
            'description': description,
            'with_examples': with_examples,
            'task_type': task,
            'task_description': task_description,
            'populate_random': populate_random,
            'area_width': area_width,
            'area_height': area_height,
            'drone_count': drone_count if populate_random else 0,
            'target_count': target_count if populate_random else 0,
            'obstacle_count': obstacle_count if populate_random else 0,
            'batch_count': max(1, int(current_batch)),
            '_auto_description': auto_generated,
            'generate_screenshot': bool(self.generate_screenshot_var.get()),
            'do_not_scatter_drones': bool(self.do_not_scatter_drones_var.get()) if populate_random else False,
            'auto_generate_tasks': bool(self.auto_generate_tasks_var.get()),
            'generated_task_count': int(self.generated_task_count_var.get()) if self.auto_generate_tasks_var.get() else 0,
            'auto_load_created_session': bool(self.auto_load_created_session_var.get())
        }
        self.batch_count = 1

        self.dialog.destroy()

    def ok_clicked_batch(self):
        try:
            count = self._prompt_batch_count()
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to read batch count: {exc}")
            return
        if not count:
            return
        self.batch_count = count
        self.ok_clicked()

    def _prompt_batch_count(self) -> Optional[int]:
        result = {'value': None}
        dialog = tk.Toplevel(self.dialog)
        if self._icon_image is not None:
            dialog.iconphoto(False, self._icon_image)
            setattr(dialog, "_uav_icon_image", self._icon_image)
        dialog.title("Create Batch")
        dialog.transient(self.dialog)
        dialog.grab_set()
        dialog.resizable(False, False)
        set_window_geometry_and_center(dialog, 320, 130, self.dialog)

        frame = ttk.Frame(dialog, padding="16")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Number of sessions to create:").grid(row=0, column=0, columnspan=2, pady=(0, 2))

        count_var = tk.IntVar(value=max(2, getattr(self, 'batch_count', 2)))
        spinbox = ttk.Spinbox(frame, from_=2, to=999, textvariable=count_var, width=8, justify='center')
        spinbox.grid(row=1, column=0, columnspan=2, pady=(10, 0))

        def submit():
            try:
                value = int(count_var.get())
            except (TypeError, ValueError):
                messagebox.showerror("Error", "Please enter a valid batch count.", parent=dialog)
                return
            if value < 2:
                messagebox.showerror("Error", "Batch count must be at least 2.", parent=dialog)
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
        self.dialog.wait_window(dialog)
        return result['value']
        
    def cancel_clicked(self):
        """Handle Cancel button click"""
        self.dialog.destroy()

    def update_init_mode_state(self):
        """Enable or disable random count inputs based on initialization mode"""
        enable_random = self.init_mode.get() == 'random'
        state = 'normal' if enable_random else 'disabled'
        for control in getattr(self, 'random_count_controls', []):
            control.configure(state=state)
        if hasattr(self, 'do_not_scatter_drones_check'):
            self.do_not_scatter_drones_check.configure(state=state)

    def update_auto_task_state(self):
        state = 'normal' if self.auto_generate_tasks_var.get() else 'disabled'
        self.generated_task_count_spin.configure(state=state)


if __name__ == "__main__":
    # Create and run session manager
    session_manager = SessionManager(version="unknown", build="dev")
    session_manager.run()
