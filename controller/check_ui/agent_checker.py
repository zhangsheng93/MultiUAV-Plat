#!/usr/bin/env python3
"""
AI Agent Auto-Check UI Gadget

A standalone UI application for automatically testing tasks using the AI agent,
monitoring responses, and checking task completion results.

Features:
- Multi-select sessions and tasks
- Automatic agent command execution
- Task completion checking
- Pause/resume functionality
- Force landing option
- Force charging option
- JSON export of results

Author: UAV Control System
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import os
import json
import logging
import threading
import time
import random
import copy
import hashlib
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union

# Add parent directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app_version import VERSION as APP_VERSION
from api_server import APIServer
from check_ui.agent_client import AgentClient
from check_ui.result_compare_window import ResultCompareWindow
from utils import (
    is_export_id_valid,
    setup_shared_logger,
    sanitize_filename,
    set_window_geometry_and_center,
    load_session_from_file,
    normalize_session_canvas_fields
)
from app_settings import get_settings, DEFAULT_STORAGE_PATH


TK_SHIFT_MASK = 0x0001
TK_CONTROL_MASK = 0x0004


class AgentCheckerApp:
    """Main application for AI Agent Auto-Check."""
    
    # Configuration Constants
    AGENT_POLL_INTERVAL = 5.0      # Seconds between status checks to agent server
    AGENT_TIMEOUT = 300.0          # Seconds to wait for agent to finish a task
    LOG_THROTTLE_INTERVAL = 30.0   # Seconds between agent status logs to prevent bloat
    WORKFLOW_STEP_DELAY = 1.0      # Seconds delay between tasks in the workflow
    WINDOW_WIDTH = 1350
    WINDOW_HEIGHT = 820
    LEFT_COLUMN_WIDTH = 520
    QUEUE_DISPLAY_LIMIT = 160
    SKIP_LOG_BATCH_SIZE = 100
    SKIP_SCORE_UPDATE_INTERVAL = 100

    def __init__(self, root):
        self.root = root
        self.root.title("AI Agent Auto-Check")
        self._icon_image = None
        self._set_window_icon()

        parent_anchor = getattr(self.root, "master", None)
        if parent_anchor is self.root:
            parent_anchor = None

        # Set window size and center it
        set_window_geometry_and_center(
            self.root,
            self.WINDOW_WIDTH,
            self.WINDOW_HEIGHT,
            parent_anchor,
            make_transient=False,
            grab=False,
            withdraw_first=True,
            align_to_pointer=True,
            bring_to_front=True,
        )

        # Initialize logger
        self.logger = setup_shared_logger("AgentChecker", log_level=logging.INFO)

        # Initialize API clients
        api_base_url = get_settings().get('api_base_url', 'http://127.0.0.1:8000')
        agent_base_url = get_settings().get('agent_base_url', 'http://localhost:18000')

        self.api_server = APIServer(base_url=api_base_url, logger=self.logger)
        self.agent_client = AgentClient(base_url=agent_base_url, logger=self.logger)

        # State variables
        self.sessions_data = []
        self.filtered_session_indices = []  # Listbox index -> sessions_data index
        self.all_tasks_data = {}  # {session_id: [tasks]}
        self.selected_tasks = []  # List of (session_id, task_id, task_name) tuples
        self.task_check_results = {}  # {(session_id, task_id): {status, details, timestamp}}
        self.session_file_map = {}  # {session_id: file_path}
        self.task_log_marks = {}  # {(session_id, task_id): mark_name}
        self.filter_var = tk.StringVar()

        # Session storage - load and validate from settings
        app_settings = get_settings()
        self.session_storage_path = app_settings.get('session_storage_path')

        # Validate and create directory if needed
        if not self.session_storage_path or not os.path.isdir(self.session_storage_path):
            self.session_storage_path = DEFAULT_STORAGE_PATH
            app_settings.set('session_storage_path', self.session_storage_path)

        try:
            Path(self.session_storage_path).mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self.logger.warning(f"Failed to ensure storage directory exists: {exc}")

        self.imported_storage_files = set()  # Track imported files to avoid duplicates
        self.logger.info(f"Session storage path: {self.session_storage_path}")

        # Workflow control
        self.is_running = False
        self.is_paused = False
        self.stop_requested = False
        self.current_task_index = 0
        self.current_log_task_progress: Optional[Tuple[int, int]] = None
        self.worker_thread = None

        # UI setup
        self.create_menu_bar()
        self.setup_ui()
        self.setup_keyboard_shortcuts()

        # Load initial data
        self.root.after(100, self.load_sessions)

    def _set_window_icon(self):
        """Apply the shared controller icon when available."""
        try:
            icon_path = Path(__file__).resolve().parent.parent / "img" / "controller.png"
            if icon_path.exists():
                self._icon_image = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, self._icon_image)
                setattr(self.root, "_uav_icon_image", self._icon_image)
            else:
                self.logger.debug(f"Icon file not found at {icon_path}")
        except Exception as exc:
            if hasattr(self, "logger"):
                self.logger.debug(f"Failed to set Agent Checker icon: {exc}")

    def create_menu_bar(self):
        """Create an Auto-Check-specific menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        sessions_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Sessions", menu=sessions_menu)
        sessions_menu.add_command(label="Refresh Sessions", command=self.load_sessions, accelerator="F5")
        sessions_menu.add_command(label="Add Tasks in Selected Sessions", command=self.add_session_tasks_to_queue)
        sessions_menu.add_separator()
        sessions_menu.add_command(label="Close", command=self.root.destroy)

        queue_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Queue", menu=queue_menu)
        queue_menu.add_command(label="Add Selected Tasks", command=self.add_selected_to_queue)
        queue_menu.add_command(label="Uncheck Selected Task", command=self.uncheck_selected_task, accelerator="U")
        queue_menu.add_command(label="Clear Queue", command=self.clear_queue)

        run_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Run", menu=run_menu)
        run_menu.add_command(label="Start / Stop", command=self.toggle_start_stop)
        run_menu.add_command(label="Pause / Resume", command=self.toggle_pause_resume)

        results_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Results", menu=results_menu)
        results_menu.add_command(label="Import Results", command=self.import_results)
        results_menu.add_command(label="Export Results", command=self.export_results)

    def setup_keyboard_shortcuts(self):
        """Bind keyboard shortcuts for the Auto-Check window."""
        self.root.bind('<F5>', lambda event: self.load_sessions())
        self.root.bind('<u>', self.handle_uncheck_shortcut)
        self.root.bind('<U>', self.handle_uncheck_shortcut)

    def handle_uncheck_shortcut(self, event=None):
        """Uncheck the selected queue task unless focus is in a text input."""
        focused = self.root.focus_get()
        if isinstance(focused, (tk.Entry, ttk.Entry, tk.Text)):
            return None
        self.uncheck_selected_task()
        return "break"

    def setup_ui(self):
        """Set up the user interface."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Content area with two panels
        self.content_frame = ttk.Frame(main_frame)
        self.content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.content_frame.rowconfigure(0, weight=1)

        # Left panel: Session and Task selection
        self.left_panel = self.create_selection_panel(self.content_frame)
        self.left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        # Right panel: Control and Progress
        self.right_panel = self.create_control_panel(self.content_frame)
        self.right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))

        self.configure_stable_content_columns()

        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        status_frame.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var,
                                relief=tk.SUNKEN, anchor=tk.W)
        status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))

    def configure_stable_content_columns(self):
        """Keep the left column fixed and give extra width to the right column."""
        horizontal_padding = 40
        available_width = max(self.WINDOW_WIDTH - horizontal_padding, 1)
        left_minsize = min(self.LEFT_COLUMN_WIDTH, available_width)
        right_minsize = max(available_width - left_minsize, 1)

        self.content_frame.columnconfigure(
            0,
            weight=0,
            minsize=left_minsize,
        )
        self.content_frame.columnconfigure(
            1,
            weight=1,
            minsize=right_minsize,
        )

        self.content_frame.grid_propagate(False)

    def format_queue_display_text(
        self,
        session_name: str,
        task_name: str,
        prefix: str = "",
        index: Optional[int] = None,
    ) -> str:
        """Format queue rows without letting very long names drive layout width."""
        order_text = f"{index + 1}. " if index is not None else ""
        text = f"{prefix}{order_text}[{session_name}] {task_name}"
        if len(text) <= self.QUEUE_DISPLAY_LIMIT:
            return text
        return text[:self.QUEUE_DISPLAY_LIMIT - 3] + "..."

    def create_selection_panel(self, parent):
        """Create the session and task selection panel."""
        panel = ttk.LabelFrame(parent, text="Session & Task Selection", padding="10")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)
        panel.rowconfigure(4, weight=2)

        # Sessions section
        sessions_label = ttk.Label(panel, text="Sessions:", font=('Arial', 10, 'bold'))
        sessions_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        # Sessions listbox with scrollbar
        sessions_frame = ttk.Frame(panel)
        sessions_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        sessions_frame.columnconfigure(0, weight=1)
        sessions_frame.rowconfigure(0, weight=1)

        sessions_scrollbar = ttk.Scrollbar(sessions_frame)
        sessions_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        self.sessions_listbox = tk.Listbox(sessions_frame,
                                           selectmode=tk.EXTENDED,
                                           exportselection=False,
                                           yscrollcommand=sessions_scrollbar.set,
                                           height=12)
        self.sessions_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        sessions_scrollbar.config(command=self.sessions_listbox.yview)
        self.bind_platform_listbox_selection(self.sessions_listbox, self.on_session_select)
        self.sessions_listbox.bind('<<ListboxSelect>>', self.on_session_select)

        # Session buttons
        session_btn_frame = ttk.Frame(panel)
        session_btn_frame.grid(row=2, column=0, sticky=tk.W, pady=(0, 10))

        ttk.Button(session_btn_frame, text="Refresh Sessions",
                   command=self.load_sessions).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(session_btn_frame, text="Add Tasks in Sessions",
                   command=self.add_session_tasks_to_queue).pack(side=tk.LEFT, padx=(0, 5))

        # Tasks section
        tasks_label = ttk.Label(panel, text="Tasks:", font=('Arial', 10, 'bold'))
        tasks_label.grid(row=3, column=0, sticky=tk.W, pady=(10, 5))

        # Tasks tree with scrollbar
        tasks_frame = ttk.Frame(panel)
        tasks_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tasks_frame.columnconfigure(0, weight=1)
        tasks_frame.rowconfigure(0, weight=1)

        tasks_scrollbar = ttk.Scrollbar(tasks_frame)
        tasks_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Use Treeview for tasks with checkboxes
        self.tasks_tree = ttk.Treeview(tasks_frame,
                                       columns=('session', 'status'),
                                       yscrollcommand=tasks_scrollbar.set,
                                       height=20,
                                       selectmode='extended')
        self.tasks_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tasks_scrollbar.config(command=self.tasks_tree.yview)

        self.tasks_tree.heading('#0', text='Task Name')
        self.tasks_tree.heading('session', text='Session')
        self.tasks_tree.heading('status', text='Status')

        self.tasks_tree.column('#0', width=250)
        self.tasks_tree.column('session', width=150)
        self.tasks_tree.column('status', width=80)
        
        # Double-click to add to queue
        self.tasks_tree.bind('<Double-1>', self.on_task_double_click)

        # Task buttons
        task_btn_frame = ttk.Frame(panel)
        task_btn_frame.grid(row=5, column=0, sticky=tk.W, pady=(5, 0))

        ttk.Button(task_btn_frame, text="Select All",
                   command=self.select_all_tasks).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(task_btn_frame, text="Deselect All",
                   command=self.deselect_all_tasks).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(task_btn_frame, text="Add Selected to Queue",
                   command=self.add_selected_to_queue).pack(side=tk.LEFT)

        # Filter section
        filter_frame = ttk.Frame(panel)
        filter_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=(8, 0))
        filter_frame.columnconfigure(1, weight=1)

        ttk.Label(filter_frame, text="Filter:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var)
        self.filter_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(filter_frame, text="Clear",
                   command=self.clear_filter).grid(row=0, column=2, sticky=tk.E)
        self.filter_var.trace_add("write", self.on_filter_changed)

        return panel

    def create_control_panel(self, parent):
        """Create the control and progress panel."""
        panel = ttk.LabelFrame(parent, text="Control & Progress", padding="10")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)  # Task queue gets weight
        panel.rowconfigure(2, weight=1)  # Log gets weight

        # Compact control section - no title frames
        control_frame = ttk.Frame(panel)
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        # Checkboxes grid for alignment
        checkbox_frame = ttk.Frame(control_frame)
        checkbox_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.config_checkboxes = []
        
        # Row 0
        self.skip_checked_var = tk.BooleanVar(value=True)
        skip_checked_check = ttk.Checkbutton(checkbox_frame,
                                             text="Skip already checked tasks",
                                             variable=self.skip_checked_var)
        skip_checked_check.grid(row=0, column=0, sticky=tk.W, padx=(0, 20), pady=2)
        self.config_checkboxes.append(skip_checked_check)

        self.skip_passed_var = tk.BooleanVar(value=False)
        skip_passed_check = ttk.Checkbutton(checkbox_frame,
                                            text="Skip passed tasks",
                                            variable=self.skip_passed_var,
                                            command=self.handle_skip_passed_toggle)
        skip_passed_check.grid(row=0, column=1, sticky=tk.W, pady=2)
        self.config_checkboxes.append(skip_passed_check)

        # Row 1
        self.force_land_var = tk.BooleanVar(value=True)
        force_land_check = ttk.Checkbutton(checkbox_frame,
                                           text="Force land all drones before each task",
                                           variable=self.force_land_var)
        force_land_check.grid(row=1, column=0, sticky=tk.W, padx=(0, 20), pady=2)
        self.config_checkboxes.append(force_land_check)

        self.force_charge_var = tk.BooleanVar(value=True)
        force_charge_check = ttk.Checkbutton(checkbox_frame,
                                             text="Force charge all drones before each task",
                                             variable=self.force_charge_var)
        force_charge_check.grid(row=1, column=1, sticky=tk.W, pady=2)
        self.config_checkboxes.append(force_charge_check)

        # Row 2
        self.random_command_var = tk.BooleanVar(value=False)
        random_command_check = ttk.Checkbutton(checkbox_frame,
                                               text="Random send one of the commands",
                                               variable=self.random_command_var)
        random_command_check.grid(row=2, column=0, sticky=tk.W, padx=(0, 20), pady=2)
        self.config_checkboxes.append(random_command_check)

        self.reload_session_var = tk.BooleanVar(value=False)
        reload_session_check = ttk.Checkbutton(checkbox_frame,
                                               text="Reload session before each task",
                                               variable=self.reload_session_var)
        reload_session_check.grid(row=2, column=1, sticky=tk.W, pady=2)
        self.config_checkboxes.append(reload_session_check)

        # Timing inputs
        timeout_frame = ttk.Frame(checkbox_frame)
        timeout_frame.grid(row=3, column=0, sticky=tk.W, padx=(0, 20), pady=2)
        
        ttk.Label(timeout_frame, text="Agent Timeout (s):").pack(side=tk.LEFT, padx=(0, 5))
        self.timeout_var = tk.StringVar(value="500")
        self.timeout_entry = ttk.Entry(timeout_frame, textvariable=self.timeout_var, width=8)
        self.timeout_entry.pack(side=tk.LEFT)
        self.config_checkboxes.append(self.timeout_entry) # Reusing list for easy state control

        wait_frame = ttk.Frame(checkbox_frame)
        wait_frame.grid(row=3, column=1, sticky=tk.W, pady=2)

        ttk.Label(wait_frame, text="Wait before start (s):").pack(side=tk.LEFT, padx=(0, 5))
        self.wait_before_start_var = tk.StringVar(value="0")
        self.wait_before_start_entry = ttk.Entry(wait_frame, textvariable=self.wait_before_start_var, width=8)
        self.wait_before_start_entry.pack(side=tk.LEFT)
        self.config_checkboxes.append(self.wait_before_start_entry)

        # Buttons on second row
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X)
        button_padx = (0, 1)
        compact_button_style = "AgentChecker.Compact.TButton"
        ttk.Style().configure(compact_button_style, padding=(1, 0))

        # Combined Start/Stop button
        self.start_stop_button = ttk.Button(btn_frame, text="Start",
                                            command=self.toggle_start_stop, state=tk.NORMAL,
                                            style=compact_button_style)
        self.start_stop_button.pack(side=tk.LEFT, padx=button_padx)

        # Combined Pause/Resume button
        self.pause_resume_button = ttk.Button(btn_frame, text="Pause",
                                              command=self.toggle_pause_resume, state=tk.DISABLED,
                                              style=compact_button_style)
        self.pause_resume_button.pack(side=tk.LEFT, padx=button_padx)

        ttk.Button(btn_frame, text="Remove",
                   command=self.remove_selected_queue_tasks,
                   style=compact_button_style).pack(side=tk.LEFT, padx=button_padx)

        ttk.Button(btn_frame, text="Clear",
                   command=self.clear_queue,
                   style=compact_button_style).pack(side=tk.LEFT, padx=button_padx)

        ttk.Button(btn_frame, text="Uncheck",
                   command=self.uncheck_selected_task,
                   style=compact_button_style).pack(side=tk.LEFT, padx=button_padx)

        self.export_results_button = ttk.Button(btn_frame, text="Export",
                                                command=self.export_results,
                                                state=tk.DISABLED,
                                                style=compact_button_style)
        self.export_results_button.pack(side=tk.LEFT, padx=button_padx)

        self.import_results_button = ttk.Button(btn_frame, text="Import",
                                                command=self.import_results,
                                                state=tk.DISABLED,
                                                style=compact_button_style)
        self.import_results_button.pack(side=tk.LEFT, padx=button_padx)

        self.compare_button = ttk.Button(btn_frame, text="Compare",
                                         command=self.open_compare_window,
                                         state=tk.DISABLED,
                                         style=compact_button_style)
        self.compare_button.pack(side=tk.LEFT, padx=button_padx)

        score_frame = ttk.Frame(control_frame)
        score_frame.pack(fill=tk.X, pady=(8, 0))
        score_frame.columnconfigure(1, weight=1)

        ttk.Label(score_frame, text="Real-time Score:",
                  font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=(0, 8))
        self.score_var = tk.StringVar(value="Queue 0/0 | Tasks 0 passed / 0 failed | Checks 0/0 passed")
        self.score_label = ttk.Label(score_frame, textvariable=self.score_var,
                                     anchor=tk.W, width=60)
        self.score_label.grid(row=0, column=1, sticky=(tk.W, tk.E))

        # Task Queue section (swapped with log, comes first)
        queue_frame = ttk.LabelFrame(panel, text="Task Queue", padding="5")
        queue_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        queue_frame.columnconfigure(0, weight=1)
        queue_frame.rowconfigure(0, weight=1)

        queue_scrollbar = ttk.Scrollbar(queue_frame)
        queue_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        queue_xscrollbar = ttk.Scrollbar(queue_frame, orient=tk.HORIZONTAL)
        queue_xscrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # Use Listbox with colored items
        self.queue_listbox = tk.Listbox(queue_frame,
                                        yscrollcommand=queue_scrollbar.set,
                                        xscrollcommand=queue_xscrollbar.set,
                                        selectmode=tk.EXTENDED,
                                        exportselection=False,
                                        width=1,
                                        height=12)
        self.queue_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        queue_scrollbar.config(command=self.queue_listbox.yview)
        queue_xscrollbar.config(command=self.queue_listbox.xview)

        # Double-click to remove from queue
        self.queue_listbox.bind('<Double-1>', self.on_queue_double_click)
        # Single-click to locate log
        self.bind_platform_listbox_selection(self.queue_listbox, self.on_queue_select)
        self.queue_listbox.bind('<<ListboxSelect>>', self.on_queue_select)
        self.queue_listbox.bind('<Command-a>', self.select_all_queue_tasks)
        self.queue_listbox.bind('<Control-a>', self.select_all_queue_tasks)

        # Configure colors for task queue items
        self.queue_listbox.config(selectbackground='#0078d7', selectforeground='white')

        # Log area (swapped with queue, comes second)
        log_frame = ttk.LabelFrame(panel, text="Log", padding="5")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)

        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.grid(row=0, column=0, columnspan=2, sticky=tk.E, pady=(0, 5))

        ttk.Button(log_btn_frame, text="Clear",
                   command=self.clear_log).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(log_btn_frame, text="Export",
                   command=self.export_log).pack(side=tk.LEFT)

        log_scrollbar = ttk.Scrollbar(log_frame)
        log_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        log_xscrollbar = ttk.Scrollbar(log_frame, orient=tk.HORIZONTAL)
        log_xscrollbar.grid(row=2, column=0, sticky=(tk.W, tk.E))

        self.log_text = tk.Text(log_frame, height=12, width=1, wrap=tk.NONE,
                                yscrollcommand=log_scrollbar.set,
                                xscrollcommand=log_xscrollbar.set,
                                state=tk.DISABLED)
        self.log_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_scrollbar.config(command=self.log_text.yview)
        log_xscrollbar.config(command=self.log_text.xview)

        return panel

    def bind_platform_listbox_selection(self, listbox: tk.Listbox, selection_callback):
        """Bind listbox mouse selection with native toggle modifier behavior."""
        listbox.bind(
            '<ButtonPress-1>',
            lambda event: self.handle_platform_listbox_selection(
                event,
                listbox,
                selection_callback,
            ),
        )

        is_macos = platform.system() == 'Darwin'
        toggle_binding = '<Command-ButtonPress-1>' if is_macos else '<Control-ButtonPress-1>'
        listbox.bind(
            toggle_binding,
            lambda event: self.handle_platform_listbox_selection(
                event,
                listbox,
                selection_callback,
                force_toggle=True,
            ),
        )

        if is_macos:
            listbox.bind(
                '<Control-ButtonPress-1>',
                lambda event: self.handle_platform_listbox_selection(
                    event,
                    listbox,
                    selection_callback,
                ),
            )

    def handle_platform_listbox_selection(
        self,
        event,
        listbox: tk.Listbox,
        selection_callback,
        force_toggle: bool = False,
    ):
        """Handle listbox plain/range/toggle mouse selection consistently."""
        if event is None:
            return None

        listbox.focus_set()
        clicked_index = listbox.nearest(event.y)
        if clicked_index < 0 or clicked_index >= listbox.size():
            return "break"

        state = int(getattr(event, 'state', 0))
        is_range = self._is_listbox_range_select_modifier(state)
        is_toggle = force_toggle or self._is_listbox_toggle_select_modifier(state)

        if is_range:
            anchor_index = getattr(listbox, "_agent_checker_selection_anchor", None)
            if anchor_index is None or anchor_index < 0 or anchor_index >= listbox.size():
                anchor_index = clicked_index
            start_index, end_index = sorted((anchor_index, clicked_index))
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(start_index, end_index)
            listbox.selection_anchor(anchor_index)
        elif is_toggle:
            if listbox.selection_includes(clicked_index):
                listbox.selection_clear(clicked_index)
            else:
                listbox.selection_set(clicked_index)
            listbox.selection_anchor(clicked_index)
            setattr(listbox, "_agent_checker_selection_anchor", clicked_index)
        else:
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(clicked_index)
            listbox.selection_anchor(clicked_index)
            setattr(listbox, "_agent_checker_selection_anchor", clicked_index)

        listbox.activate(clicked_index)
        listbox.see(clicked_index)
        selection_callback(None)
        return "break"

    @staticmethod
    def _is_listbox_range_select_modifier(state: int) -> bool:
        return bool(state & TK_SHIFT_MASK)

    @staticmethod
    def _is_listbox_toggle_select_modifier(state: int) -> bool:
        if platform.system() == 'Darwin':
            return False
        return bool(state & TK_CONTROL_MASK)

    # Filtering methods

    def get_filter_text(self) -> str:
        """Return the normalized selection filter text."""
        if not hasattr(self, "filter_var"):
            return ""
        return self.filter_var.get().strip().lower()

    def clear_filter(self):
        """Clear the session/task filter."""
        self.filter_var.set("")

    def on_filter_changed(self, *_args):
        """Refresh visible tasks after the filter changes."""
        self.refresh_tasks_tree_for_current_selection()

    def get_selected_session_ids(self) -> List[str]:
        """Return selected session IDs using the filtered listbox mapping."""
        selected_ids = []
        for listbox_index in self.sessions_listbox.curselection():
            session = self.get_session_for_listbox_index(int(listbox_index))
            if session:
                selected_ids.append(session.get('id'))
        return selected_ids

    def get_session_for_listbox_index(self, listbox_index: int) -> Optional[Dict[str, Any]]:
        """Resolve a visible listbox index back to the source session object."""
        if listbox_index < 0 or listbox_index >= len(self.filtered_session_indices):
            return None
        source_index = self.filtered_session_indices[listbox_index]
        if source_index < 0 or source_index >= len(self.sessions_data):
            return None
        return self.sessions_data[source_index]

    def refresh_sessions_list(self, selected_session_ids: Optional[List[str]] = None):
        """Render all sessions while keeping listbox indexes mapped to source data."""
        if not hasattr(self, "sessions_listbox"):
            return

        selected_ids = set(selected_session_ids or [])
        self.filtered_session_indices = []
        self.sessions_listbox.delete(0, tk.END)

        for source_index, session in enumerate(self.sessions_data):
            session_id = session.get('id', 'unknown')
            session_name = session.get('name', session_id)
            display_text = f"{session_name} ({session_id})"
            self.filtered_session_indices.append(source_index)
            self.sessions_listbox.insert(tk.END, display_text)

            if session_id in selected_ids:
                self.sessions_listbox.selection_set(tk.END)

    def refresh_tasks_tree_for_current_selection(self):
        """Refresh the task tree for currently selected visible sessions."""
        self.on_session_select()

    def task_visible_for_filter(
        self,
        task: Dict[str, Any],
        session: Dict[str, Any],
        filter_text: str,
    ) -> bool:
        """Return True when a task row should be shown for the current filter."""
        if not filter_text:
            return True
        return (
            self.session_fields_match_filter(session, filter_text)
            or self.task_matches_filter(task, filter_text)
        )

    def session_fields_match_filter(self, session: Dict[str, Any], filter_text: str) -> bool:
        """Return True when session-level searchable fields match."""
        fields = [
            session.get('id'),
            session.get('name'),
            session.get('task_type'),
            session.get('category'),
        ]
        return self.fields_match_filter(fields, filter_text)

    def task_matches_filter(self, task: Dict[str, Any], filter_text: str) -> bool:
        """Return True when task searchable fields match the filter."""
        if not filter_text:
            return True

        fields = [
            task.get('id'),
            task.get('name'),
            task.get('category'),
            task.get('task_type'),
        ]
        fields.extend(self.collect_category_metadata(task))
        return self.fields_match_filter(fields, filter_text)

    @staticmethod
    def fields_match_filter(fields: List[Any], filter_text: str) -> bool:
        """Case-insensitive substring match against normalized field values."""
        normalized_filter = str(filter_text).strip().lower()
        if not normalized_filter:
            return True
        for field in fields:
            if field is None:
                continue
            if normalized_filter in str(field).lower():
                return True
        return False

    @classmethod
    def collect_category_metadata(cls, value: Any) -> List[str]:
        """Collect category-like metadata from nested task/check structures."""
        matches = []
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {'category', 'task_type'} and child is not None:
                    matches.append(str(child))
                elif isinstance(child, (dict, list)):
                    matches.extend(cls.collect_category_metadata(child))
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, (dict, list)):
                    matches.extend(cls.collect_category_metadata(child))
        return matches

    # Data loading methods

    def load_sessions(self):
        """Load all sessions from the API, auto-importing from storage folder first."""
        self.update_status("Loading sessions...")
        self.log("Loading sessions from API...")

        try:
            # First, auto-import sessions from storage folder. Reuse the
            # sessions fetched for duplicate checks unless imports changed it.
            sessions = self.auto_import_sessions_from_storage()
            if sessions is None:
                sessions = self.api_server.api_get_sessions()
            if sessions:
                # Custom sort function
                def session_sort_key(s):
                    # 1. Check if 'example' is in name/id (case-insensitive) - prioritize these (0 for true, 1 for false)
                    s_id = str(s.get('id', '')).lower()
                    s_name = str(s.get('name', '')).lower()
                    is_example = 'example' in s_id or 'example' in s_name
                    priority_rank = 0 if is_example else 1
                    
                    # 2. Created time (increasing / oldest first)
                    # Fallback to ID if created_at missing, but ensure it's comparable
                    created_at = s.get('created_at') or s.get('id') or ''
                    
                    return (priority_rank, created_at)

                sessions.sort(key=session_sort_key)
                
                self.sessions_data = sessions
                self.refresh_sessions_list()
                self.tasks_tree.delete(*self.tasks_tree.get_children())

                self.log(f"Loaded {len(sessions)} sessions")
                self.update_status(f"Loaded {len(sessions)} sessions")
            else:
                self.sessions_data = []
                self.filtered_session_indices = []
                self.sessions_listbox.delete(0, tk.END)
                self.tasks_tree.delete(*self.tasks_tree.get_children())
                self.log("No sessions found or failed to load sessions")
                self.update_status("Failed to load sessions")
                messagebox.showwarning("No Sessions", "No sessions found or failed to load sessions")
        except Exception as e:
            self.logger.error(f"Error loading sessions: {e}", exc_info=True)
            self.log(f"ERROR: {e}")
            self.update_status("Error loading sessions")
            messagebox.showerror("Error", f"Failed to load sessions: {str(e)}")

    def auto_import_sessions_from_storage(self):
        """Import all session files from the configured storage directory.

        Only imports sessions that don't already exist on the server to avoid duplicates.
        Similar to session_manager.py implementation.
        """
        if not self.session_storage_path:
            return None

        storage_dir = Path(self.session_storage_path)
        try:
            storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self.logger.error(f"Failed to prepare session storage directory: {exc}")
            return None

        # Get list of existing sessions to avoid re-importing
        existing_sessions = self.api_server.api_get_sessions()
        existing_session_ids = set()
        if existing_sessions:
            existing_session_ids = {s.get('id') for s in existing_sessions if s.get('id')}
            self.logger.debug(f"Found {len(existing_session_ids)} existing sessions on server")

        imported_count = 0
        skipped_count = 0

        # Import all JSON files from storage directory
        for json_file in sorted(storage_dir.glob('*.json')):
            resolved = str(json_file.resolve())

            # Skip if already imported
            if resolved in self.imported_storage_files:
                continue

            try:
                payload, _ = load_session_from_file(json_file)

                if not isinstance(payload, dict):
                    self.logger.warning(f"Skipping file without valid session payload: {json_file.name}")
                    self.imported_storage_files.add(resolved)
                    continue

                session_id = payload.get('id')
                if not session_id:
                    self.logger.warning(f"Skipping file without session ID: {json_file.name}")
                    self.imported_storage_files.add(resolved)
                    continue

                # Map session ID to file path
                self.session_file_map[session_id] = resolved

                # Skip if session already exists on server
                if session_id in existing_session_ids:
                    self.logger.debug(f"Session {session_id} already exists, skipping")
                    self.imported_storage_files.add(resolved)
                    skipped_count += 1
                    continue

                # Import the session
                request_data = dict(payload)
                request_data['status'] = 'inactive'
                request_data = normalize_session_canvas_fields(request_data)

                result = self.api_server.api_new_session_with_id(session_id, request_data, show_error=False)
                if result is not None:
                    imported_count += 1
                    self.imported_storage_files.add(resolved)
                    self.logger.info(f"Imported session from {json_file.name}")

            except Exception as exc:
                self.logger.error(f"Failed to import session file {json_file.name}: {exc}")

        # Log summary
        if imported_count > 0:
            self.log(f"Auto-imported {imported_count} new session(s) from storage folder")
            return None
        if skipped_count > 0:
            self.logger.debug(f"Skipped {skipped_count} existing session(s)")

        return existing_sessions

    def on_session_select(self, event=None):
        """Handle session selection - load tasks for selected sessions."""
        selection = self.sessions_listbox.curselection()

        # Clear existing tasks in tree
        self.tasks_tree.delete(*self.tasks_tree.get_children())
        if not selection:
            self.update_status("No sessions selected")
            return
        
        total_tasks = 0
        loaded_sessions = 0
        filter_text = self.get_filter_text()
        
        for idx in selection:
            session = self.get_session_for_listbox_index(int(idx))
            if not session:
                continue
            session_id = session.get('id')
            session_name = session.get('name', session_id)

            # Use cached tasks if available, otherwise load
            tasks = []
            if session_id in self.all_tasks_data:
                tasks = self.all_tasks_data[session_id]
            else:
                try:
                    self.update_status(f"Loading tasks for {session_name}...")
                    self.root.update_idletasks()  # Force UI update
                    tasks = self.api_server.api_get_session_tasks(session_id)
                    if tasks:
                        self.all_tasks_data[session_id] = tasks
                except Exception as e:
                    self.logger.error(f"Error loading tasks for {session_name}: {e}")
                    continue
            
            if tasks:
                loaded_sessions += 1
                for task in tasks:
                    if not self.task_visible_for_filter(task, session, filter_text):
                        continue
                    task_id = task.get('id')
                    task_name = task.get('name', 'Unnamed Task')
                    is_done = task.get('is_done', False)
                    status = 'Done' if is_done else 'Pending'

                    self.tasks_tree.insert('', tk.END,
                                          text=task_name,
                                          values=(session_name, status),
                                          tags=(session_id, task_id))
                    total_tasks += 1

        self.update_status(f"Loaded {total_tasks} tasks from {loaded_sessions} sessions")

    def add_session_tasks_to_queue(self):
        """Add all tasks from selected sessions to the queue."""
        selection = self.sessions_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select sessions to add their tasks")
            return

        added_count = 0
        filter_text = self.get_filter_text()
        
        for idx in selection:
            session = self.get_session_for_listbox_index(int(idx))
            if not session:
                continue
            session_id = session.get('id')
            session_name = session.get('name', session_id)
            
            # Ensure tasks are loaded
            tasks = []
            if session_id in self.all_tasks_data:
                tasks = self.all_tasks_data[session_id]
            else:
                try:
                    tasks = self.api_server.api_get_session_tasks(session_id)
                    if tasks:
                        self.all_tasks_data[session_id] = tasks
                except Exception:
                    continue
            
            if tasks:
                for task in tasks:
                    if not self.task_visible_for_filter(task, session, filter_text):
                        continue
                    task_id = task.get('id')
                    task_name = task.get('name', 'Unnamed Task')
                    
                    task_tuple = (session_id, task_id, task_name, session_name)
                    
                    if task_tuple not in self.selected_tasks:
                        self.selected_tasks.append(task_tuple)
                        queue_index = len(self.selected_tasks) - 1
                        display = self.format_queue_display_text(session_name, task_name, "⏳ ", queue_index)
                        self.queue_listbox.insert(tk.END, display)
                        added_count += 1
                        
        self.log(f"Added {added_count} tasks from {len(selection)} sessions to queue")
        self.update_status(f"Added {added_count} tasks to queue")
        self.update_queue_dependent_buttons()
        self.update_realtime_score()

    def add_selected_to_queue(self):
        """Add selected tasks to the checking queue."""
        selected_items = self.tasks_tree.selection()

        if not selected_items:
            messagebox.showwarning("No Selection", "Please select tasks to add to queue")
            return

        added_count = 0
        for item in selected_items:
            tags = self.tasks_tree.item(item, 'tags')
            if len(tags) >= 2:
                session_id = tags[0]
                task_id = tags[1]
                task_name = self.tasks_tree.item(item, 'text')
                session_name = self.tasks_tree.item(item, 'values')[0]

                task_tuple = (session_id, task_id, task_name, session_name)

                # Avoid duplicates
                if task_tuple not in self.selected_tasks:
                    self.selected_tasks.append(task_tuple)
                    queue_index = len(self.selected_tasks) - 1
                    display = self.format_queue_display_text(session_name, task_name, "⏳ ", queue_index)
                    self.queue_listbox.insert(tk.END, display)
                    added_count += 1

        self.log(f"Added {added_count} tasks to queue (Total: {len(self.selected_tasks)})")
        self.update_status(f"Added {added_count} tasks to queue")
        self.update_queue_dependent_buttons()
        self.update_realtime_score()

    def on_task_double_click(self, event):
        """Handle double-click on task in tree."""
        item = self.tasks_tree.identify_row(event.y)
        if item:
            # If not already selected, select it first
            if item not in self.tasks_tree.selection():
                self.tasks_tree.selection_set(item)
            self.add_selected_to_queue()

    def on_queue_double_click(self, event):
        """Handle double-click on task in queue (remove it)."""
        index = self.queue_listbox.nearest(event.y)
        if index >= 0:
            self.queue_listbox.selection_clear(0, tk.END)
            self.queue_listbox.selection_set(index)
        self.remove_selected_queue_tasks()

    def remove_selected_queue_tasks(self):
        """Remove selected tasks from the queue and their recorded results."""
        if self.is_running and not self.is_paused:
            messagebox.showwarning("Running", "Cannot modify queue while checking is running. Please pause or stop first.")
            return

        selection = list(self.queue_listbox.curselection())
        if not selection:
            return

        removed_names = []
        first_index = min(selection)

        for index in sorted(selection, reverse=True):
            if index >= len(self.selected_tasks):
                continue

            session_id, task_id, task_name, _ = self.selected_tasks.pop(index)
            self.task_check_results.pop((session_id, task_id), None)
            self.task_log_marks.pop((session_id, task_id), None)
            self.queue_listbox.delete(index)
            removed_names.append(task_name)

        if not removed_names:
            return

        self.refresh_queue_order_numbers(first_index)
        if first_index < self.queue_listbox.size():
            self.queue_listbox.selection_set(first_index)
        elif self.queue_listbox.size() > 0:
            self.queue_listbox.selection_set(tk.END)

        if len(removed_names) == 1:
            self.log(f"Removed from queue and results: {removed_names[0]}")
            self.update_status("Removed task and results")
        else:
            self.log(f"Removed {len(removed_names)} tasks from queue and results")
            self.update_status(f"Removed {len(removed_names)} tasks and results")

        self.update_queue_dependent_buttons()
        self.update_realtime_score()

    def select_all_tasks(self):
        """Select all tasks in the tree."""
        for item in self.tasks_tree.get_children():
            self.tasks_tree.selection_add(item)

    def deselect_all_tasks(self):
        """Deselect all tasks in the tree."""
        self.tasks_tree.selection_remove(*self.tasks_tree.get_children())

    def clear_queue(self):
        """Clear the task queue."""
        if self.is_running and not self.is_paused:
            messagebox.showwarning("Running", "Cannot clear queue while checking is running. Please pause or stop first.")
            return

        if not messagebox.askyesno(
            "Clear Queue",
            "Clear the queue, results, and log? This action cannot be undone.",
            parent=self.root,
        ):
            return

        self.selected_tasks.clear()
        self.queue_listbox.delete(0, tk.END)
        
        # Clear results and log mapping
        self.task_check_results.clear()
        self.task_log_marks.clear()
        # Clear log text
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        self.log("Queue cleared")
        self.update_status("Queue cleared")
        self.update_queue_dependent_buttons()
        self.update_realtime_score()

    # Control methods

    def handle_skip_passed_toggle(self):
        """Keep skip-passed mode mutually clear from skip-already-checked mode."""
        if not self.skip_passed_var.get() or not self.skip_checked_var.get():
            return

        confirmed = messagebox.askyesno(
            "Skip Already Checked Tasks Enabled",
            "Skip already checked tasks is also enabled. That option skips every checked task, including non-passed tasks.\n\n"
            "To skip only passed tasks, Skip already checked tasks must be unchecked. Continue?",
            parent=self.root,
        )

        if confirmed:
            self.skip_checked_var.set(False)
        else:
            self.skip_passed_var.set(False)

    def set_config_state(self, state: str):
        """Enable or disable configuration checkboxes."""
        for cb in self.config_checkboxes:
            cb.config(state=state)

    def toggle_start_stop(self):
        """Toggle between Start and Stop states."""
        if not self.is_running:
            # Start checking
            if not self.selected_tasks:
                messagebox.showwarning("No Tasks", "Please add tasks to the queue first")
                return

            # Check agent server health
            self.update_status("Checking agent server...")
            if not self.agent_client.check_health():
                messagebox.showerror("Agent Server Unavailable",
                                   "Cannot connect to agent server. Please ensure it's running on port 18000.")
                self.update_status("Agent server unavailable")
                return

            self.is_running = True
            self.is_paused = False
            self.stop_requested = False
            self.current_task_index = 0
            self.current_log_task_progress = None

            # Update UI
            self.start_stop_button.config(text="Stop")
            self.pause_resume_button.config(text="Pause", state=tk.NORMAL)
            self.set_config_state(tk.DISABLED)
            
            # Reset icons for tasks that will be checked
            for idx, (s_id, t_id, _, _) in enumerate(self.selected_tasks):
                # Only reset if NOT skipping
                should_skip = False
                if self.skip_checked_var.get() and (s_id, t_id) in self.task_check_results:
                    should_skip = True
                elif self.skip_passed_var.get():
                    res = self.task_check_results.get((s_id, t_id))
                    if res and res.get('status') == 'passed':
                        should_skip = True
                
                if not should_skip:
                    self.task_check_results.pop((s_id, t_id), None)
                    self.update_queue_item_status(idx, 'pending')

            self.update_realtime_score(current_index=0)

            self.log("Started automated checking")

            # Start worker thread
            self.worker_thread = threading.Thread(target=self.run_checking_workflow, daemon=True)
            self.worker_thread.start()

            self.update_status("Running...")
        else:
            # Stop checking
            self.stop_requested = True
            self.is_running = False
            self.is_paused = False
            self.current_log_task_progress = None

            self.start_stop_button.config(text="Start", state=tk.NORMAL)
            self.pause_resume_button.config(text="Pause", state=tk.DISABLED)
            self.set_config_state(tk.NORMAL)

            self.log("Stopped by user")
            self.update_status("Stopped")
            self.update_realtime_score()

    def toggle_pause_resume(self):
        """Toggle between Pause and Resume states."""
        if not self.is_paused:
            # Pause
            self.is_paused = True
            self.pause_resume_button.config(text="Resume")
            self.set_config_state(tk.NORMAL)
            self.log("Paused")
            self.update_status("Paused")
        else:
            # Resume
            self.is_paused = False
            self.pause_resume_button.config(text="Pause")
            self.set_config_state(tk.DISABLED)
            self.log("Resumed")
            self.update_status("Resumed")
            
    def mark_task_log_start(self, session_id, task_id):
        """Mark the current end of log as the start for this task."""
        mark_name = f"task_{session_id}_{task_id}"
        # Set mark at current end
        self.log_text.mark_set(mark_name, "end-1c") 
        self.log_text.mark_gravity(mark_name, tk.LEFT)
        self.task_log_marks[(session_id, task_id)] = mark_name
        
    def on_queue_select(self, event):
        """Handle selection in queue to scroll to log."""
        selection = self.queue_listbox.curselection()
        if not selection:
            return

        active = self.queue_listbox.index(tk.ACTIVE)
        index = active if active in selection else selection[-1]
        if index < len(self.selected_tasks):
            session_id, task_id, _, _ = self.selected_tasks[index]
            
            mark_name = self.task_log_marks.get((session_id, task_id))
            if mark_name:
                try:
                    self.log_text.see(mark_name)
                    
                    # Optional: Highlight the line temporarily?
                    # For now just scrolling is good.
                    
                    # self.log_text.tag_remove('highlight', '1.0', tk.END)
                    # self.log_text.tag_add('highlight', mark_name, f"{mark_name} lineend")
                    # self.log_text.tag_config('highlight', background='yellow')
                except Exception:
                    pass

    def select_all_queue_tasks(self, event=None):
        """Select all queued tasks."""
        if self.queue_listbox.size() == 0:
            return "break"
        self.queue_listbox.selection_set(0, tk.END)
        return "break"

    def update_queue_dependent_buttons(self):
        """Enable controls that require at least one queued task."""
        if not hasattr(self, "compare_button"):
            return
        state = tk.NORMAL if self.selected_tasks else tk.DISABLED
        self.compare_button.config(state=state)
        self.export_results_button.config(state=state)
        self.import_results_button.config(state=state)

    def open_compare_window(self):
        """Open the queue-scoped result comparison window."""
        if not self.selected_tasks:
            messagebox.showinfo("No Tasks", "Please add tasks to the queue first.", parent=self.root)
            self.update_queue_dependent_buttons()
            return
        ResultCompareWindow(self.root, list(self.selected_tasks), set_icon=self._apply_icon_to_window)

    def _apply_icon_to_window(self, window):
        """Apply the already-loaded app icon to a child window."""
        if self._icon_image is not None:
            window.iconphoto(True, self._icon_image)
            setattr(window, "_uav_icon_image", self._icon_image)

    def refresh_queue_item_display(self, index: int, status: str = 'pending'):
        """Refresh one queue row while preserving its queue order number."""
        if index >= self.queue_listbox.size() or index >= len(self.selected_tasks):
            return

        session_id, task_id, task_name, session_name = self.selected_tasks[index]
        status_icons = {
            'pending': '⏳ ',
            'running': '▶️ ',
            'passed': '✅ ',
            'failed': '❌ '
        }

        prefix = status_icons.get(status, '')
        display_task_name = task_name
        if (session_id, task_id) in self.task_check_results:
            result_data = self.task_check_results[(session_id, task_id)]
            details = result_data.get('details', [])
            leaf_details = [d for d in details if d.get('type') == 'leaf']
            total_checks = len(leaf_details)
            passed_checks = sum(1 for d in leaf_details if d.get('result', False))
            if total_checks > 0:
                rate = (passed_checks / total_checks) * 100
                display_task_name = f"{task_name} (Checked:{total_checks} Passed:{passed_checks} Rate:{rate:.0f}%)"

        text = self.format_queue_display_text(session_name, display_task_name, prefix, index)
        self.queue_listbox.delete(index)
        self.queue_listbox.insert(index, text)

        if status == 'passed':
            self.queue_listbox.itemconfig(index, {'bg': '#e6fffa'})
        elif status == 'failed':
            self.queue_listbox.itemconfig(index, {'bg': '#fff5f5'})

    def refresh_queue_order_numbers(self, start_index: int = 0):
        """Refresh queue rows whose displayed order number may have changed."""
        for index in range(start_index, self.queue_listbox.size()):
            session_id, task_id, _, _ = self.selected_tasks[index]
            result = self.task_check_results.get((session_id, task_id))
            status = result.get('status', 'pending') if result else 'pending'
            self.refresh_queue_item_display(index, status)

    # Checking workflow

    def run_checking_workflow(self):
        """Main workflow for checking tasks (runs in background thread)."""
        total_tasks = len(self.selected_tasks)
        skip_log_buffer = []

        def flush_skip_logs():
            if not skip_log_buffer:
                return
            messages = list(skip_log_buffer)
            skip_log_buffer.clear()
            self.root.after(0, lambda msgs=messages: self.log_many(msgs))

        for idx, (session_id, task_id, task_name, session_name) in enumerate(self.selected_tasks):
            self.root.after(0, lambda: self.set_current_log_task_progress(None))
            # Check for stop request
            if self.stop_requested:
                flush_skip_logs()
                self.root.after(0, lambda: self.log("Workflow stopped"))
                break

            # Wait while paused
            while self.is_paused and not self.stop_requested:
                time.sleep(0.5)

            if self.stop_requested:
                flush_skip_logs()
                break

            self.current_task_index = idx
            
            # Check skip already checked logic
            if self.skip_checked_var.get() and (session_id, task_id) in self.task_check_results:
                skip_log_buffer.append((f"Skipping checked: {task_name}", (idx + 1, total_tasks)))
                if len(skip_log_buffer) >= self.SKIP_LOG_BATCH_SIZE:
                    flush_skip_logs()
                if (idx + 1) % self.SKIP_SCORE_UPDATE_INTERVAL == 0:
                    self.root.after(0, lambda i=idx: self.update_realtime_score(current_index=i))
                continue

            # Check skip passed tasks logic (only from current results)
            if self.skip_passed_var.get():
                res = self.task_check_results.get((session_id, task_id))
                if res and res.get('status') == 'passed':
                    skip_log_buffer.append((f"Skipping passed: {task_name}", (idx + 1, total_tasks)))
                    if len(skip_log_buffer) >= self.SKIP_LOG_BATCH_SIZE:
                        flush_skip_logs()
                    if (idx + 1) % self.SKIP_SCORE_UPDATE_INTERVAL == 0:
                        self.root.after(0, lambda i=idx: self.update_realtime_score(current_index=i))
                    continue

            flush_skip_logs()
            self.root.after(
                0,
                lambda p=(idx + 1, total_tasks): self.set_current_log_task_progress(p),
            )
            self.root.after(0, lambda i=idx: self.update_realtime_score(current_index=i))

            # Update status bar with current task
            self.root.after(0, lambda i=idx, t=total_tasks, n=task_name, s=session_name:
                          self.update_status(f"[{i+1}/{t}] {s} - {n}"))

            # Update task queue item to show "running" status
            self.root.after(0, lambda i=idx: self.update_queue_item_status(i, 'running'))

            # Record log start position for this task
            self.root.after(0, lambda s=session_id, t=task_id: self.mark_task_log_start(s, t))

            # Log current task
            self.root.after(0, lambda n=task_name:
                          self.log(f"Processing: {n}"))

            # Execute the check workflow for this task
            try:
                self.check_single_task(session_id, task_id, task_name, session_name)
            except Exception as e:
                self.logger.error(f"Error checking task {task_name}: {e}", exc_info=True)
                self.root.after(0, lambda e=e: self.log(f"ERROR: {str(e)}"))

            # Small delay between tasks
            time.sleep(self.WORKFLOW_STEP_DELAY)

        # Complete
        flush_skip_logs()
        self.root.after(0, lambda: self.set_current_log_task_progress(None))
        self.root.after(0, self.on_workflow_complete)

    def check_single_task(self, session_id: str, task_id: str, task_name: str, session_name: str):
        """Check a single task using the agent."""

        # Step 1: Reload session if requested
        if self.reload_session_var.get():
            self.root.after(0, lambda: self.log(f"  Reloading session {session_id} from file..."))
            
            file_path = self.session_file_map.get(session_id)
            if file_path and os.path.exists(file_path):
                try:
                    payload, error = load_session_from_file(file_path)
                    if payload:
                         # Ensure ID matches
                        if payload.get('id') == session_id:
                            request_data = dict(payload)
                            request_data['status'] = 'inactive'
                            request_data = normalize_session_canvas_fields(request_data)
                            
                            self.api_server.api_new_session_with_id(session_id, request_data, show_error=False)
                            self.root.after(0, lambda: self.log("  Session reloaded successfully"))
                        else:
                             self.root.after(0, lambda: self.log(f"  WARNING: ID mismatch in file {Path(file_path).name}"))
                    else:
                        self.root.after(0, lambda: self.log(f"  WARNING: Failed to load file: {error}"))
                except Exception as e:
                    self.root.after(0, lambda e=e: self.log(f"  ERROR reloading session: {e}"))
            else:
                 self.root.after(0, lambda: self.log(f"  WARNING: Session file not found for {session_id}"))

        # Step 2: Set session as current
        self.api_server.api_set_session_as_current(session_id, show_error=False)

        # Step 3: Force land if requested
        if self.force_land_var.get():
            self.root.after(0, lambda: self.log("  Landing all drones..."))
            result = self.api_server.api_land_all_drones(show_error=False)
            if result:
                self.root.after(0, lambda: self.log("  Drones landed"))
            else:
                self.root.after(0, lambda: self.log("  WARNING: Failed to land drones"))
            time.sleep(2)

        # Step 4: Force charge if requested
        if self.force_charge_var.get():
            self.root.after(0, lambda: self.log("  Charging all drones..."))
            result = self.api_server.api_charge_all_drones(show_error=False)
            if result:
                self.root.after(0, lambda: self.log("  Drones charged"))
            else:
                self.root.after(0, lambda: self.log("  WARNING: Failed to charge drones"))
            time.sleep(2)

        try:
            wait_before_start = max(0.0, float(self.wait_before_start_var.get()))
        except ValueError:
            wait_before_start = 0.0

        if wait_before_start > 0 and not self.stop_requested:
            self.root.after(0, lambda w=wait_before_start: self.log(f"  Waiting {w:g}s before starting agent..."))
            end_time = time.time() + wait_before_start
            while time.time() < end_time and not self.stop_requested:
                time.sleep(min(0.5, end_time - time.time()))

        # Step 5: Get task command
        task_data = self.api_server.api_get_session_task(session_id, task_id)
        if not task_data:
            self.root.after(0, lambda: self.log("  ERROR: Failed to fetch task data"))
            self.record_task_result(session_id, task_id, 'failed', [], 'Failed to fetch task data')
            return

        # Get command (original or random alias)
        command = task_data.get('content', '')
        content_aliases = task_data.get('content_aliases', [])

        # Determine which command(s) to use
        if self.random_command_var.get():
            # Random mode: choose from content + aliases
            all_commands = [command] if command else []
            if content_aliases and isinstance(content_aliases, list):
                all_commands.extend(content_aliases)
                
            if not all_commands:
                self.root.after(0, lambda: self.log("  ERROR: No command content found"))
                self.record_task_result(session_id, task_id, 'failed', [], 'No command content')
                return

            selected_command = random.choice(all_commands)
        else:
            # Default mode: use only main content
            if not command:
                self.root.after(0, lambda: self.log("  ERROR: No command content found"))
                self.record_task_result(session_id, task_id, 'failed', [], 'No command content')
                return
            selected_command = command

        self.root.after(0, lambda c=selected_command: self.log(f"  Command: {c[:80]}..."))

        # Step 6: Submit to agent
        self.root.after(0, lambda: self.log("  Submitting to agent..."))

        last_log_time = -self.LOG_THROTTLE_INTERVAL  # Initialize to force first log

        def status_callback(status, elapsed):
            """Callback for agent status updates."""
            nonlocal last_log_time
            # Only log every X seconds to prevent log bloat
            if elapsed - last_log_time >= self.LOG_THROTTLE_INTERVAL:
                self.root.after(0, lambda s=status, e=elapsed:
                              self.log(f"  Agent status: {s} ({e:.1f}s)"))
                last_log_time = elapsed
            return not self.stop_requested  # Return False to cancel if stop requested

        # Get dynamic timeout from UI
        try:
            current_timeout = float(self.timeout_var.get())
        except ValueError:
            current_timeout = self.AGENT_TIMEOUT

        success, result = self.agent_client.submit_and_wait(
            selected_command,
            poll_interval=self.AGENT_POLL_INTERVAL,
            timeout=current_timeout,
            status_callback=status_callback
        )

        # Always check task completion, even if agent failed/timeout/stopped
        # This tells us if the agent did part of the work correctly

        agent_error = None
        if self.stop_requested:
            self.root.after(0, lambda: self.log("  Stopped by user - still checking task completion..."))
            agent_error = "Stopped by user"
        elif not success or not result:
            self.root.after(0, lambda: self.log("  Agent execution failed/timeout - still checking task completion..."))
            agent_error = "Agent execution failed or timeout"
        else:
            agent_result = result.get('result', {})
            agent_output = agent_result.get('output', 'No output')
            self.root.after(0, lambda o=agent_output: self.log(f"  Agent output: {o[:100]}..."))

        # Step 7: Check task completion (ALWAYS, regardless of agent success)
        self.root.after(0, lambda: self.log("  Checking task completion..."))

        execution_check_apis = task_data.get('execution_check_apis')
        if not execution_check_apis or not isinstance(execution_check_apis, dict):
            self.root.after(0, lambda: self.log("  WARNING: No execution checks defined"))
            error_msg = 'No execution checks defined'
            if agent_error:
                error_msg = f"{agent_error}; {error_msg}"
            self.record_task_result(session_id, task_id, 'failed', [], error_msg)
            return

        # Evaluate check tree
        check_passed, check_details = self.evaluate_execution_check_node(execution_check_apis, session_id)

        # Count checks
        leaf_details = [d for d in check_details if d.get('type') == 'leaf']
        passed_checks = sum(1 for d in leaf_details if d.get('result', False))
        total_checks = len(leaf_details)

        status = 'passed' if check_passed else 'failed'
        self.root.after(0, lambda s=status, p=passed_checks, t=total_checks:
                      self.log(f"  Check result: {s.upper()} ({p}/{t} checks passed)"))

        # Add agent error to result if any
        error_msg = agent_error if agent_error else None

        # Record result
        self.record_task_result(session_id, task_id, status, check_details, error_msg)

        # Mark as done if passed (only if agent succeeded AND checks passed)
        if check_passed and not agent_error:
            self.api_server.api_mark_task_done(session_id, task_id)

    def evaluate_execution_check_node(self, node, session_id, depth=0):
        """
        Recursively evaluate an execution check node (group or leaf).
        Reuses logic from gui_controller.py

        Returns:
            tuple: (result: bool, details: list of dict)
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
                child_result, child_details = self.evaluate_execution_check_node(check, session_id, depth + 1)
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
        expect = node.get('expect', True)

        # Ensure expect is boolean
        if isinstance(expect, dict) and 'result' in expect:
            expect = bool(expect.get('result'))
        elif not isinstance(expect, bool):
            expect = True

        # Make the check API call
        try:
            params_with_session = dict(parameters)
            if 'session_id' not in params_with_session and session_id:
                params_with_session['session_id'] = session_id

            response = self.api_server.api_check_execution(endpoint, params_with_session, show_error=False)

            if response is None:
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

            actual_result = response.get('result', False) if isinstance(response, dict) else False
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

    def record_task_result(self, session_id: str, task_id: str, status: str,
                          details: List[Dict], error_msg: str = None):
        """Record the result of a task check and update queue item status."""
        result_record = {
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'error': error_msg
        }

        self.task_check_results[(session_id, task_id)] = result_record

        # Update queue item visual status
        for idx, (s_id, t_id, _, _) in enumerate(self.selected_tasks):
            if s_id == session_id and t_id == task_id:
                self.root.after(0, lambda i=idx, st=status: self.update_queue_item_status(i, st))
                break

        self.root.after(0, self.update_realtime_score)

    def on_workflow_complete(self):
        """Called when the checking workflow completes."""
        self.is_running = False
        self.is_paused = False

        self.start_stop_button.config(text="Start", state=tk.NORMAL)
        self.pause_resume_button.config(text="Pause", state=tk.DISABLED)
        self.set_config_state(tk.NORMAL)

        # Calculate statistics
        total = len(self.selected_tasks)
        passed = sum(1 for r in self.task_check_results.values() if r['status'] == 'passed')
        failed = sum(1 for r in self.task_check_results.values() if r['status'] != 'passed')

        self.log(f"Workflow complete: {passed} passed, {failed} failed out of {total} tasks")
        self.update_status(f"Complete: {passed} passed, {failed} failed out of {total} tasks")
        self.update_realtime_score()

        messagebox.showinfo("Complete",
                           f"Checking complete!\n\n"
                           f"Passed: {passed}\n"
                           f"Failed: {failed}\n"
                           f"Total: {total}")
                           
    def uncheck_selected_task(self):
        """Reset the selected task status to unchecked/pending."""
        if self.is_running and not self.is_paused:
            messagebox.showwarning("Running", "Cannot modify tasks while running")
            return
            
        selection = self.queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a task to uncheck")
            return
            
        unchecked_names = []

        for index in selection:
            if index >= len(self.selected_tasks):
                continue

            session_id, task_id, task_name, session_name = self.selected_tasks[index]
            
            # Remove from results
            if (session_id, task_id) in self.task_check_results:
                del self.task_check_results[(session_id, task_id)]
                unchecked_names.append(task_name)
                
                # Reset visual status
                self.refresh_queue_item_display(index, 'pending')

        self.queue_listbox.selection_clear(0, tk.END)
        for index in selection:
            if index < self.queue_listbox.size():
                self.queue_listbox.selection_set(index)

        if unchecked_names:
            if len(unchecked_names) == 1:
                self.log(f"Unchecked task: {unchecked_names[0]}")
                self.update_status("Task unchecked")
            else:
                self.log(f"Unchecked {len(unchecked_names)} tasks")
                self.update_status(f"Unchecked {len(unchecked_names)} tasks")
            self.update_realtime_score()

    def import_results(self):
        """Import checking results from a JSON file."""
        filename = filedialog.askopenfilename(
            title="Import Check Results",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filename:
            return
            
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not is_export_id_valid(data):
                self.log(f"Rejected unacceptable import file: {Path(filename).name}")
                self.update_status("Import refused")
                messagebox.showwarning(
                    "Import Refused",
                    "This file is not acceptable. Results were not imported."
                )
                return
                
            results = data.get('results', [])
            if not results:
                messagebox.showwarning("Invalid File", "No results found in file")
                return
                
            imported_count = 0
            
            for res in results:
                session_id = res.get('session_id')
                task_id = res.get('task_id')
                status = res.get('status')
                details = res.get('details', [])
                timestamp = res.get('timestamp')
                error = res.get('error')
                task_name = res.get('task_name', 'Unknown Task')
                session_name = res.get('session_name', 'Unknown Session')
                
                if session_id and task_id:
                    # Update results map with all metadata
                    self.task_check_results[(session_id, task_id)] = {
                        'status': status,
                        'details': details,
                        'timestamp': timestamp,
                        'error': error,
                        'task_name': task_name,
                        'session_name': session_name
                    }
                    imported_count += 1
                    
                    # Update queue visualization if task is in queue
                    for idx, (s_id, t_id, _, _) in enumerate(self.selected_tasks):
                        if s_id == session_id and t_id == task_id:
                            self.update_queue_item_status(idx, status)
                            
            self.log(f"Imported {imported_count} results from {Path(filename).name}")
            self.update_status(f"Imported {imported_count} results")
            self.update_realtime_score()
            messagebox.showinfo("Import Success", f"Successfully imported {imported_count} task results.")
            
        except Exception as e:
            self.logger.error(f"Failed to import results: {e}")
            self.log(f"ERROR importing {Path(filename).name}: {e}")
            messagebox.showerror("Import Error", f"Failed to import results: {str(e)}")

    # Export functionality

    def get_queue_scoped_result_rows(self):
        """Return result rows only for tasks currently present in the queue."""
        rows = []
        for session_id, task_id, task_name, session_name in self.selected_tasks:
            result_data = self.task_check_results.get((session_id, task_id))
            if result_data is None:
                continue
            rows.append((session_id, task_id, task_name, session_name, result_data))
        return rows

    def export_results(self):
        """Export checking results to JSON file."""
        queue_result_rows = self.get_queue_scoped_result_rows()
        if not queue_result_rows:
            messagebox.showinfo("No Results", "No queued task results to export")
            return

        self.update_status("Preparing export...")

        # Build export data
        task_results = []
        passed_count = 0
        failed_count = 0
        total_failed_tasks_count = 0
        total_checks = 0
        passed_checks = 0
        sum_of_task_pass_rates = 0.0  # For calculating average

        for session_id, task_id, task_name, session_name, result_data in queue_result_rows:
            task_name = task_name or result_data.get('task_name') or "Unknown Task"
            session_name = session_name or result_data.get('session_name') or "Unknown Session"

            status = result_data.get('status')
            details = result_data.get('details', [])
            timestamp = result_data.get('timestamp')
            error = result_data.get('error')

            # Count checks
            leaf_details = [d for d in details if d.get('type') == 'leaf']
            task_total_checks = len(leaf_details)
            task_passed_checks = sum(1 for d in leaf_details if d.get('result', False))

            total_checks += task_total_checks
            passed_checks += task_passed_checks

            # Calculate this task's pass rate
            task_check_pass_rate = task_passed_checks / task_total_checks if task_total_checks > 0 else 0
            sum_of_task_pass_rates += task_check_pass_rate
            
            # Count tasks with 0 passed checks
            if task_passed_checks == 0:
                total_failed_tasks_count += 1

            if status == 'passed':
                passed_count += 1
            else:
                failed_count += 1

            task_record = {
                "session_id": session_id,
                "session_name": session_name,
                "task_id": task_id,
                "task_name": task_name,
                "status": status,
                "timestamp": timestamp,
                "error": error,
                "statistics": {
                    "total_checks_apis": task_total_checks,
                    "passed_checks_apis": task_passed_checks,
                    "failed_checks_apis": task_total_checks - task_passed_checks,
                    "pass_rate": round(task_check_pass_rate, 4)
                },
                "details": details
            }
            task_results.append(task_record)

        # Calculate statistics
        total_tasks = len(task_results)
        task_pass_rate = passed_count / total_tasks if total_tasks > 0 else 0
        total_failed_task_rate = total_failed_tasks_count / total_tasks if total_tasks > 0 else 0
        check_pass_rate = passed_checks / total_checks if total_checks > 0 else 0
        average_check_pass_rate = sum_of_task_pass_rates / total_tasks if total_tasks > 0 else 0

        server_version = None
        try:
            server_version = self.api_server.api_get_server_version(show_error=False)
        except Exception as e:
            self.logger.debug(f"Failed to fetch server version for export: {e}")

        export_data = {
            "id": "calculating...",
            "export_timestamp": datetime.now().isoformat(),
            "tool": "AI Agent Auto-Check",
            "version": APP_VERSION,
            "server_version": server_version,
            "statistics": {
                "total_tasks": total_tasks,
                "passed_tasks_count": passed_count,
                "failed_tasks_count": failed_count,
                "total_failed_task_count": total_failed_tasks_count,
                "task_pass_rate": round(task_pass_rate, 4),
                "total_failed_task_rate": round(total_failed_task_rate, 4),
                "average_check_pass_rate": round(average_check_pass_rate, 4),
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "failed_checks": total_checks - passed_checks,
                "check_pass_rate": round(check_pass_rate, 4)
            },
            "results": task_results
        }

        # Calculate MD5 hash
        try:
            data_to_hash = copy.deepcopy(export_data)
            data_to_hash.pop("id", None)
            results_json = json.dumps(data_to_hash, sort_keys=True)
            md5_hash = hashlib.md5(results_json.encode('utf-8')).hexdigest()
            export_data["id"] = md5_hash
        except Exception as e:
            self.logger.error(f"Failed to calculate MD5: {e}")
            export_data["id"] = "error_calculating_hash"

        # Save to file
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested_filename = f"agent_check_results_{timestamp_str}.json"

        filename = filedialog.asksaveasfilename(
            title="Export Check Results",
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

            self.log(f"Results exported to {filename}")
            self.update_status("Results exported")
            messagebox.showinfo("Export Success",
                              f"Results exported to:\n{filename}\n\n"
                              f"Tasks: {passed_count} passed / {failed_count} failed\n"
                              f"Checks: {passed_checks} passed / {total_checks - passed_checks} failed")
        except Exception as e:
            self.logger.error(f"Failed to export: {e}")
            messagebox.showerror("Export Error", f"Failed to export results: {str(e)}")
            self.update_status("Export failed")

    # UI helper methods

    def update_status(self, message: str):
        """Update the status bar."""
        self.status_var.set(message)

    def set_current_log_task_progress(self, progress: Optional[Tuple[int, int]]):
        """Set the task progress prefix used by task-scoped log lines."""
        self.current_log_task_progress = progress

    def get_log_content(self) -> str:
        """Return the visible log contents without Tk's trailing newline."""
        return self.log_text.get("1.0", "end-1c")

    def clear_log(self):
        """Clear the visible log after confirmation."""
        if not self.get_log_content().strip():
            messagebox.showinfo("Log Empty", "There is no log content to clear.", parent=self.root)
            return

        if not messagebox.askyesno(
            "Clear Log",
            "Clear the log? This action cannot be undone.",
            parent=self.root,
        ):
            return

        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.update_status("Log cleared")
        self.logger.info("Log cleared")

    def export_log(self):
        """Export the visible log contents to a text file."""
        log_content = self.get_log_content()
        if not log_content.strip():
            messagebox.showinfo("No Log", "No log content to export.", parent=self.root)
            return

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested_filename = f"agent_check_log_{timestamp_str}.txt"
        filename = filedialog.asksaveasfilename(
            title="Export Log",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Log files", "*.log"), ("All files", "*.*")],
            initialfile=suggested_filename,
            parent=self.root,
        )

        if not filename:
            self.update_status("Log export cancelled")
            return

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(log_content)
                if not log_content.endswith("\n"):
                    f.write("\n")

            self.log(f"Log exported to {filename}")
            self.update_status("Log exported")
            messagebox.showinfo("Export Success", f"Log exported to:\n{filename}", parent=self.root)
        except Exception as e:
            self.logger.error(f"Failed to export log: {e}")
            messagebox.showerror("Export Error", f"Failed to export log: {str(e)}", parent=self.root)
            self.update_status("Log export failed")

    def update_realtime_score(self, current_index: Optional[int] = None):
        """Refresh the live score summary shown above the queue."""
        total_tasks = len(self.selected_tasks)
        completed_tasks = 0
        passed_tasks = 0
        failed_tasks = 0
        total_checks = 0
        passed_checks = 0

        for session_id, task_id, _, _ in self.selected_tasks:
            task_key = (session_id, task_id)
            result_data = self.task_check_results.get(task_key)
            if not result_data:
                continue

            completed_tasks += 1
            if result_data.get('status') == 'passed':
                passed_tasks += 1
            else:
                failed_tasks += 1

            details = result_data.get('details', [])
            leaf_details = [d for d in details if d.get('type') == 'leaf']
            total_checks += len(leaf_details)
            passed_checks += sum(1 for d in leaf_details if d.get('result', False))

        parts = [
            f"Queue {completed_tasks}/{total_tasks}",
            f"Tasks {passed_tasks} passed / {failed_tasks} failed",
            f"Checks {passed_checks}/{total_checks} passed"
        ]

        if total_checks > 0:
            parts[-1] += f" ({(passed_checks / total_checks) * 100:.0f}%)"

        if self.is_running and total_tasks > 0:
            running_index = self.current_task_index if current_index is None else current_index
            running_index = min(running_index + 1, total_tasks)
            parts.append(f"Running {running_index}/{total_tasks}")

        self.score_var.set(" | ".join(parts))

    def update_queue_item_status(self, index: int, status: str):
        """Update the visual status of a task queue item with color coding and stats.

        Args:
            index: Index of the item in the queue
            status: 'pending', 'running', 'passed', 'failed'
        """
        if index >= self.queue_listbox.size() or index >= len(self.selected_tasks):
            return
        self.refresh_queue_item_display(index, status)

        # Scroll to show current item
        if status == 'running':
            self.queue_listbox.see(index)

    def format_log_line(
        self,
        message: str,
        timestamp: str,
        task_progress: Optional[Tuple[int, int]] = None,
    ) -> Tuple[str, str]:
        """Format one visible log line and return it with the cleaned message."""
        cleaned_message = str(message).replace('\n', ' ')
        progress = task_progress if task_progress is not None else self.current_log_task_progress
        prefix = f"[{timestamp}]"
        if progress is not None:
            task_number, total_tasks = progress
            prefix = f"{prefix} [{task_number}/{total_tasks}]"
        return f"{prefix} {cleaned_message}\n", cleaned_message

    def log(self, message: str, task_progress: Optional[Tuple[int, int]] = None):
        """Add a message to the log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message, cleaned_message = self.format_log_line(message, timestamp, task_progress)

        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

        self.logger.info(cleaned_message)

    def log_many(self, messages: List[Union[str, Tuple[str, Optional[Tuple[int, int]]]]]):
        """Add multiple messages to the log with one Tk update."""
        if not messages:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cleaned_messages = []
        log_lines = []
        for entry in messages:
            task_progress = None
            message = entry
            if isinstance(entry, tuple):
                message, task_progress = entry
            log_line, cleaned_message = self.format_log_line(message, timestamp, task_progress)
            log_lines.append(log_line)
            cleaned_messages.append(cleaned_message)
        log_text = "".join(log_lines)

        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_text)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

        for message in cleaned_messages:
            self.logger.info(message)


def main():
    """Main entry point."""
    root = tk.Tk()
    app = AgentCheckerApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
