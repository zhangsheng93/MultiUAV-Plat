#!/usr/bin/env python3
"""
MultiUAV-Plat Control System - Task Dialog

Enhanced task creation dialog with:
- One-by-one API addition with parameter inputs
- Automatic command extraction from APIs
- Better parameter management

Author: MultiUAV-Plat Control System
Version: Provided by application entrypoint
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from typing import Dict, List, Any, Optional
import json
import math
from api_server import APIServer
import os
import copy
from api_definitions import get_api_by_category, get_check_api_by_category
from utils import set_window_geometry_and_center, create_new_name


PARAMETER_HELP_TEXTS = {
    'position': '(dict: {"x": 0, "y": 0, "z": 0})',
    'waypoints': '(list: [{"x": 0, "y": 0, "z": 0}, ...])',
    'point': '(dict: {"x": 0, "y": 0, "z": 0})',
    'start': '(dict: {"x": 0, "y": 0, "z": 0})',
    'end': '(dict: {"x": 0, "y": 0, "z": 0})',
    'x': '(float)',
    'y': '(float)',
    'z': '(float)',
    'altitude': '(float, meters)',
    'expected_altitude': '(float, meters)',
    'distance': '(float, meters)',
    'heading': '(float, degrees 0-360)',
    'expected_heading': '(float, degrees 0-360)',
    'battery_level': '(float, 0-100)',
    'min_level': '(float, 0-100)',
    'min_height': '(float, meters)',
    'radius': '(float, meters)',
    'tolerance': '(float, tolerance/threshold)',
    'max_distance': '(float, meters)',
    'expected_progress': '(float, 0-1)',
    'expected_percentage': '(float, 0-1)',
    'coverage_threshold': '(float, 0-1)',
    'expected_count': '(int)'
}


def get_parameter_help_text(param: str) -> str:
    """Get help text for specific parameters."""
    return PARAMETER_HELP_TEXTS.get(param, '')


def normalize_expect_value(expect_val: Any) -> Optional[bool]:
    """
    Convert an expect value into a boolean if possible.
    - Booleans pass through.
    - Legacy dicts like {"result": true} collapse to that boolean.
    - Strings "true"/"false" (case-insensitive) are converted.
    Returns None when the value cannot be interpreted.
    """
    if isinstance(expect_val, bool):
        return expect_val
    if isinstance(expect_val, dict) and 'result' in expect_val:
        return bool(expect_val.get('result'))
    if isinstance(expect_val, str):
        lowered = expect_val.strip().lower()
        if lowered in ('true', 'false'):
            return lowered == 'true'
    return None


def is_id_like_param(param_name: str) -> bool:
    """Return True when a parameter name represents an ID field."""
    return param_name == 'id' or param_name.endswith('_id') or '_id_' in param_name


def format_param_value(param_name: str, value: Any) -> str:
    """Format parameter values for display, keeping IDs as stable strings."""
    if value is None:
        return ''
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    if is_id_like_param(param_name) and isinstance(value, (int, float)):
        if isinstance(value, float):
            if not math.isfinite(value):
                return str(value)
            if value.is_integer():
                return str(int(value))
            return format(value, 'f').rstrip('0').rstrip('.')
        return str(value)
    return str(value)


def normalize_id_param_value(param_name: str, value: Any) -> Any:
    """Normalize ID-like params to strings while preserving None."""
    if value is None:
        return None
    if is_id_like_param(param_name):
        return format_param_value(param_name, value)
    return value


def normalize_id_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure ID-like params are stored as strings."""
    return {key: normalize_id_param_value(key, value) for key, value in (params or {}).items()}


def fetch_dropdown_values_for_param(param: str, api_endpoint: str, template_mode: bool = False) -> Optional[List[str]]:
    """Get dropdown values for ID parameters by fetching from API."""
    if template_mode:
        return None

    param_to_endpoint = {
        'id': None,  # Determined by context
        'drone_id': '/drones',
        'drone_1_id': '/drones',
        'drone_2_id': '/drones',
        'target_drone_id': '/drones',
        'target_id': '/targets',
        'obstacle_id': '/obstacles',
        'session_id': '/sessions',
        'task_id': None  # Context-dependent
    }

    relative_endpoint = param_to_endpoint.get(param)

    if param == 'id':
        if '/drones/' in api_endpoint:
            relative_endpoint = '/drones'
        elif '/targets/' in api_endpoint:
            relative_endpoint = '/targets'
        elif '/obstacles/' in api_endpoint:
            relative_endpoint = '/obstacles'
        elif '/sessions/' in api_endpoint:
            relative_endpoint = '/sessions'
        else:
            relative_endpoint = None

    if not relative_endpoint:
        return None

    try:
        server = APIServer()
        items = server.api_get_list(relative_endpoint, show_error=False)
        
        if items is not None:
            dropdown_values = []
            for item in items:
                item_id = item.get('id', '')
                item_name = item.get('name', '')
                if item_id:
                    dropdown_values.append(f"{item_id} - {item_name}" if item_name else str(item_id))
            return dropdown_values if dropdown_values else None
    except Exception:
        return None

    return None


class AddAPIDialog:
    """Dialog for adding or editing a single API with its parameters"""

    def __init__(self, parent, api_categories: Dict[str, List[Dict[str, Any]]],
                 edit_data: Optional[Dict[str, Any]] = None, template_mode: bool = False):
        self.result = None
        self.api_categories = api_categories
        self.edit_data = edit_data  # Existing API data for edit mode
        self.edit_mode = edit_data is not None
        self.template_mode = template_mode  # Template editor uses placeholders, not live selections

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Edit API with Parameters" if self.edit_mode else "Add API with Parameters")
        set_window_geometry_and_center(self.dialog, 500, 600, parent)

        self.create_widgets()
        self.dialog.wait_window()

    def create_widgets(self):
        """Create dialog widgets"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Info (removed title label as requested)
        info_text = "Modify the API parameters" if self.edit_mode else "Select an API endpoint and provide parameter values"
        info_label = ttk.Label(main_frame,
                              text=info_text,
                              font=('Arial', 9), foreground='gray')
        info_label.pack(pady=(0, 10))

        # Scrollable frame
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        row = 0
        scrollable_frame.columnconfigure(1, weight=1)
        scrollable_frame.columnconfigure(2, weight=1)
        scrollable_frame.columnconfigure(3, weight=1)

        # Category selection
        ttk.Label(scrollable_frame, text="Category:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(scrollable_frame, textvariable=self.category_var,
                                           values=list(self.api_categories.keys()),
                                           state="readonly", width=35)
        self.category_combo.bind('<<ComboboxSelected>>', self.on_category_changed)
        self.category_combo.grid(row=row, column=1, pady=5, sticky=tk.W)
        row += 1

        # API selection
        ttk.Label(scrollable_frame, text="API Endpoint:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        self.api_var = tk.StringVar()
        self.api_combo = ttk.Combobox(scrollable_frame, textvariable=self.api_var,
                                      state="readonly", width=35)
        self.api_combo.bind('<<ComboboxSelected>>', self.on_api_changed)
        self.api_combo.grid(row=row, column=1, pady=5, sticky=tk.W)
        row += 1

        # API Description
        ttk.Label(scrollable_frame, text="Description:").grid(
            row=row, column=0, sticky=tk.NW, pady=5)
        self.description_label = ttk.Label(scrollable_frame, text="",
                                          foreground='gray', wraplength=280)
        self.description_label.grid(row=row, column=1, pady=5, sticky=tk.W)
        row += 1

        # Separator
        ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky=tk.EW, pady=10)
        row += 1

        # Parameters section
        self.params_label = ttk.Label(scrollable_frame, text="Parameters:",
                                     font=('Arial', 10, 'bold'))
        self.params_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1

        # Parameters frame (dynamic)
        self.params_frame = ttk.Frame(scrollable_frame)
        self.params_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        self.param_entries = {}  # Will store parameter entry widgets
        self.param_dropdown_values = {}
        row += 1

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        button_text = "Save" if self.edit_mode else "Add"
        ttk.Button(button_frame, text=button_text, command=self.ok_clicked).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.RIGHT)

        # If in edit mode, pre-populate fields
        if self.edit_mode and self.edit_data:
            self._populate_edit_data()

    def on_category_changed(self, event=None):
        """Handle category selection change"""
        category = self.category_var.get()
        if category and category in self.api_categories:
            apis = self.api_categories[category]
            # Format API list for display
            api_displays = []
            self.api_map = {}  # Map display string to API dict
            for api in apis:
                display = f"{api['method']} {api['endpoint']}"
                api_displays.append(display)
                self.api_map[display] = api

            self.api_combo['values'] = api_displays
            self.api_combo.set('')
            self.description_label.config(text='')
            self._clear_parameters()

    def on_api_changed(self, event=None):
        """Handle API selection change"""
        api_display = self.api_var.get()
        if api_display and api_display in self.api_map:
            api = self.api_map[api_display]
            self.selected_api = api

            # Update description
            self.description_label.config(text=api.get('description', ''))

            # Create parameter input fields
            self._create_parameter_fields(api.get('parameters', []))

    def _create_parameter_fields(self, parameters: List[str]):
        """Create input fields for API parameters"""
        # Clear existing parameters
        self._clear_parameters()

        if not parameters:
            no_params_label = ttk.Label(self.params_frame, text="No parameters required",
                                       foreground='gray', font=('Arial', 9, 'italic'))
            no_params_label.pack(pady=5)
            return

        # Create input field for each parameter
        for param in parameters:
            param_row_frame = ttk.Frame(self.params_frame)
            param_row_frame.pack(fill=tk.X, pady=3)

            # Parameter name label
            param_label = ttk.Label(param_row_frame, text=f"{param}:", width=15)
            param_label.pack(side=tk.LEFT, padx=5)

            # Check if this parameter should use a dropdown (for existing items)
            dropdown_values = None if self.template_mode else self._get_dropdown_values_for_param(param)

            if dropdown_values:
                # Use dropdown for ID parameters
                self.param_dropdown_values[param] = dropdown_values
                param_var = tk.StringVar()
                param_combo = ttk.Combobox(param_row_frame, textvariable=param_var,
                                          values=dropdown_values, width=23)
                param_combo.pack(side=tk.LEFT, padx=5)
                # Store the variable, not the widget
                self.param_entries[param] = param_var
            else:
                # Use regular text entry
                self.param_dropdown_values.pop(param, None)
                param_entry = ttk.Entry(param_row_frame, width=25)
                param_entry.pack(side=tk.LEFT, padx=5)
                # Store entry widget
                self.param_entries[param] = param_entry

            # Add help text for special parameters
            help_text = self._get_parameter_help(param)
            if help_text:
                help_label = ttk.Label(param_row_frame, text=help_text,
                                      foreground='gray', font=('Arial', 8))
                help_label.pack(side=tk.LEFT, padx=5)

    def _get_dropdown_values_for_param(self, param: str) -> Optional[List[str]]:
        """Delegate to shared dropdown helper using current API endpoint."""
        api_endpoint = self.selected_api.get('endpoint', '')
        return fetch_dropdown_values_for_param(param, api_endpoint, self.template_mode)

    def _get_parameter_help(self, param: str) -> str:
        return get_parameter_help_text(param)

    def _clear_parameters(self):
        """Clear all parameter input fields"""
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        self.param_entries = {}
        self.param_dropdown_values = {}

    def _populate_edit_data(self):
        """Populate fields with existing API data in edit mode"""
        if not self.edit_data:
            return

        # Explicit category hint if stored
        explicit_category = self.edit_data.get('category')

        # Find and set the category based on the API endpoint
        api_path = self.edit_data.get('path', '') or self.edit_data.get('endpoint', '')
        api_method = self.edit_data.get('method', '')
        api_endpoint = f"{api_method} {api_path}"

        # Find the category that contains this API
        found_category = None
        found_api = None

        for category, apis in self.api_categories.items():
            for api in apis:
                if f"{api['method']} {api['endpoint']}" == api_endpoint:
                    found_category = category
                    found_api = api
                    break
            if found_category:
                break

        if not found_category and explicit_category and explicit_category in self.api_categories:
            found_category = explicit_category

        if found_category and found_api:
            # Set category
            self.category_var.set(found_category)
            self.on_category_changed()  # Populate API list

            # Set API
            self.api_var.set(api_endpoint)
            self.selected_api = found_api
            self.on_api_changed()  # Create parameter fields

            # Disable category and API selection in edit mode
            self.category_combo.config(state='disabled')
            self.api_combo.config(state='disabled')

            # Populate parameter values
            existing_params = self.edit_data.get('parameters', {})
            for param_name, entry_or_var in self.param_entries.items():
                if param_name in existing_params:
                    value = existing_params[param_name]

                    # Convert value to string for display
                    value_str = format_param_value(param_name, value)

                    # Set the value
                    if isinstance(entry_or_var, tk.StringVar):
                        # For dropdown, try to match the value
                        # If it's just an ID, try to find matching "ID - Name" format
                        dropdown_values = self.param_dropdown_values.get(param_name, [])
                        for dropdown_val in dropdown_values:
                            if dropdown_val.startswith(value_str + ' - ') or dropdown_val == value_str:
                                value_str = dropdown_val
                                break
                        entry_or_var.set(value_str)
                    else:
                        # For text entry
                        entry_or_var.delete(0, tk.END)
                        entry_or_var.insert(0, value_str)
        else:
            # Fallback: build a minimal selection so existing data shows up
            if explicit_category and explicit_category in self.api_categories:
                self.category_var.set(explicit_category)
            else:
                self.category_var.set('')
            self.api_var.set(api_endpoint)
            self.selected_api = {
                'endpoint': api_path,
                'method': api_method,
                'parameters': list(self.edit_data.get('parameters', {}).keys()),
                'description': self.edit_data.get('description', '')
            }
            self._create_parameter_fields(self.selected_api.get('parameters', []))
            existing_params = self.edit_data.get('parameters', {})
            for param_name, entry_or_var in self.param_entries.items():
                if param_name in existing_params:
                    value = existing_params[param_name]
                    value_str = format_param_value(param_name, value)
                    if isinstance(entry_or_var, tk.StringVar):
                        entry_or_var.set(value_str)
                    else:
                        entry_or_var.delete(0, tk.END)
                        entry_or_var.insert(0, value_str)

    def ok_clicked(self):
        """Handle OK button click"""
        if not hasattr(self, 'selected_api'):
            messagebox.showerror("Error", "Please select an API endpoint")
            return

        # Collect parameter values
        param_values = {}
        for param_name, entry_or_var in self.param_entries.items():
            # Handle both Entry widgets and StringVar (from Combobox)
            if isinstance(entry_or_var, tk.StringVar):
                value = entry_or_var.get().strip()
            else:
                value = entry_or_var.get().strip()

            if value:
                # Extract ID from "id - name" format (from dropdown) only in runtime mode
                if not self.template_mode and ' - ' in value and is_id_like_param(param_name):
                    value = value.split(' - ')[0].strip()

                if self.template_mode:
                    # Keep raw text/placeholders
                    param_values[param_name] = value
                elif is_id_like_param(param_name):
                    # Preserve IDs as strings to avoid scientific notation
                    param_values[param_name] = value
                else:
                    # Try to parse as JSON for complex types
                    if value.startswith('{') or value.startswith('['):
                        try:
                            param_values[param_name] = json.loads(value)
                        except json.JSONDecodeError:
                            param_values[param_name] = value
                    else:
                        # Try to convert to appropriate type
                        try:
                            # Try float first
                            param_values[param_name] = float(value)
                        except ValueError:
                            # Keep as string
                            param_values[param_name] = value
            else:
                # Empty value - could be optional
                param_values[param_name] = None

        # Build result
        api_endpoint = f"{self.selected_api['method']} {self.selected_api['endpoint']}"
        self.result = {
            'endpoint': api_endpoint,
            'method': self.selected_api['method'],
            'path': self.selected_api['endpoint'],
            'description': self.selected_api.get('description', ''),
            'parameters': param_values
        }

        self.dialog.destroy()

    def cancel_clicked(self):
        """Handle Cancel button click"""
        self.dialog.destroy()


class ExecutionCheckAPIDialog:
    """Dialog for adding or editing a single execution check API (logical leaf)."""

    def __init__(self, parent, api_categories: Dict[str, List[Dict[str, Any]]],
                 edit_data: Optional[Dict[str, Any]] = None, template_mode: bool = False):
        self.result = None
        self.api_categories = api_categories
        self.edit_data = edit_data
        self.edit_mode = edit_data is not None
        self.param_dropdown_values = {}
        self.template_mode = template_mode

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Edit Execution Check" if self.edit_mode else "Add Execution Check")
        set_window_geometry_and_center(self.dialog, 580, 640, parent)

        self.create_widgets()
        self.dialog.wait_window()

    def create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        info_label = ttk.Label(
            main_frame,
            text="Select a /check endpoint, set parameters, and optional expected result (true/false).",
            font=('Arial', 9),
            foreground='gray',
            wraplength=460
        )
        info_label.pack(pady=(0, 10))

        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        row = 0
        scrollable_frame.columnconfigure(1, weight=1)

        ttk.Label(scrollable_frame, text="Category:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(
            scrollable_frame,
            textvariable=self.category_var,
            values=list(self.api_categories.keys()),
            state="readonly",
            width=35
        )
        self.category_combo.bind('<<ComboboxSelected>>', self.on_category_changed)
        self.category_combo.grid(row=row, column=1, pady=5, sticky=tk.W)
        row += 1

        ttk.Label(scrollable_frame, text="Check Endpoint:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        self.api_var = tk.StringVar()
        self.api_combo = ttk.Combobox(scrollable_frame, textvariable=self.api_var, state="readonly", width=35)
        self.api_combo.bind('<<ComboboxSelected>>', self.on_api_changed)
        self.api_combo.grid(row=row, column=1, pady=5, sticky=tk.W)
        row += 1

        ttk.Label(scrollable_frame, text="Description:").grid(row=row, column=0, sticky=tk.NW, pady=5)
        self.description_label = ttk.Label(scrollable_frame, text="", foreground='gray', wraplength=320)
        self.description_label.grid(row=row, column=1, pady=5, sticky=tk.W)
        row += 1

        ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=10)
        row += 1

        self.params_label = ttk.Label(scrollable_frame, text="Parameters:", font=('Arial', 10, 'bold'))
        self.params_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1

        self.params_frame = ttk.Frame(scrollable_frame)
        self.params_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        self.param_entries = {}
        row += 1

        ttk.Label(scrollable_frame, text="Expected result (optional)").grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5))
        self.expect_var = tk.StringVar()
        self.expect_combo = ttk.Combobox(
            scrollable_frame,
            textvariable=self.expect_var,
            values=["", "True", "False"],
            state="readonly",
            width=10
        )
        self.expect_combo.grid(row=row, column=1, pady=(10, 5), sticky=tk.W)
        row += 1

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        ttk.Button(button_frame, text="Save" if self.edit_mode else "Add", command=self.ok_clicked).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.RIGHT)

        if self.edit_mode and self.edit_data:
            self._populate_edit_data()

    def on_category_changed(self, event=None):
        category = self.category_var.get()
        if category and category in self.api_categories:
            apis = self.api_categories[category]
            api_displays = []
            self.api_map = {}
            for api in apis:
                display = f"{api['method']} {api['endpoint']}"
                api_displays.append(display)
                self.api_map[display] = api

            self.api_combo['values'] = api_displays
            self.api_combo.set('')
            self.description_label.config(text='')
            self._clear_parameters()

    def on_api_changed(self, event=None):
        api_display = self.api_var.get()
        if api_display and api_display in getattr(self, 'api_map', {}):
            api = self.api_map[api_display]
            self.selected_api = api
            self.description_label.config(text=api.get('description', ''))
            self._create_parameter_fields(api.get('parameters', []))

    def _create_parameter_fields(self, parameters: List[str]):
        self._clear_parameters()
        if not parameters:
            no_params_label = ttk.Label(self.params_frame, text="No parameters required", foreground='gray', font=('Arial', 9, 'italic'))
            no_params_label.pack(pady=5)
            return

        for param in parameters:
            param_row_frame = ttk.Frame(self.params_frame)
            param_row_frame.pack(fill=tk.X, pady=3)

            ttk.Label(param_row_frame, text=f"{param}:", width=18).pack(side=tk.LEFT, padx=5)

            dropdown_values = fetch_dropdown_values_for_param(param, self.selected_api.get('endpoint', ''), self.template_mode)
            if dropdown_values:
                self.param_dropdown_values[param] = dropdown_values
                param_var = tk.StringVar()
                param_combo = ttk.Combobox(param_row_frame, textvariable=param_var, values=dropdown_values, width=26)
                param_combo.pack(side=tk.LEFT, padx=5)
                self.param_entries[param] = param_var
            else:
                self.param_dropdown_values.pop(param, None)
                param_entry = ttk.Entry(param_row_frame, width=28)
                param_entry.pack(side=tk.LEFT, padx=5)
                self.param_entries[param] = param_entry

            help_text = get_parameter_help_text(param)
            if help_text:
                ttk.Label(param_row_frame, text=help_text, foreground='gray', font=('Arial', 8)).pack(side=tk.LEFT, padx=5)

    def _clear_parameters(self):
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        self.param_entries = {}
        self.param_dropdown_values = {}

    def _populate_edit_data(self):
        api_path = self.edit_data.get('path') or self.edit_data.get('endpoint', '')
        api_method = self.edit_data.get('method', 'GET')
        api_endpoint = f"{api_method} {api_path}" if ' ' not in api_path else api_path

        found_category = None
        found_api = None
        for category, apis in self.api_categories.items():
            for api in apis:
                if f"{api['method']} {api['endpoint']}" == api_endpoint:
                    found_category = category
                    found_api = api
                    break
            if found_category:
                break

        if found_category and found_api:
            self.category_var.set(found_category)
            self.on_category_changed()
            self.api_var.set(api_endpoint)
            self.selected_api = found_api
            self.on_api_changed()
            self.category_combo.config(state='disabled')
            self.api_combo.config(state='disabled')

            existing_params = self.edit_data.get('parameters', {})
            for param_name, entry_or_var in self.param_entries.items():
                if param_name in existing_params:
                    value = existing_params[param_name]
                    value_str = format_param_value(param_name, value)
                    if isinstance(entry_or_var, tk.StringVar):
                        dropdown_values = self.param_dropdown_values.get(param_name, [])
                        for dropdown_val in dropdown_values:
                            if dropdown_val.startswith(value_str + ' - ') or dropdown_val == value_str:
                                value_str = dropdown_val
                                break
                        entry_or_var.set(value_str)
                    else:
                        entry_or_var.delete(0, tk.END)
                        entry_or_var.insert(0, value_str)

            expect_val = normalize_expect_value(self.edit_data.get('expect'))
            if expect_val is not None:
                self.expect_var.set("True" if expect_val else "False")

    def ok_clicked(self):
        if not hasattr(self, 'selected_api'):
            messagebox.showerror("Error", "Please select a /check endpoint")
            return

        param_values = {}
        for param_name, entry_or_var in self.param_entries.items():
            value = entry_or_var.get().strip() if isinstance(entry_or_var, tk.StringVar) else entry_or_var.get().strip()
            if value:
                if ' - ' in value and is_id_like_param(param_name) and not self.template_mode:
                    value = value.split(' - ')[0].strip()
                if self.template_mode:
                    param_values[param_name] = value
                elif is_id_like_param(param_name):
                    param_values[param_name] = value
                else:
                    if value.startswith('{') or value.startswith('['):
                        try:
                            param_values[param_name] = json.loads(value)
                        except json.JSONDecodeError:
                            param_values[param_name] = value
                    else:
                        try:
                            param_values[param_name] = float(value)
                        except ValueError:
                            param_values[param_name] = value
            else:
                param_values[param_name] = None

        expect_raw = (self.expect_var.get() or "").strip()
        expect_value = None
        if expect_raw:
            lowered = expect_raw.lower()
            if lowered in ('true', 'false'):
                expect_value = lowered == 'true'
            else:
                messagebox.showerror("Error", "Expectation must be 'True' or 'False'")
                return

        api_endpoint = f"{self.selected_api['method']} {self.selected_api['endpoint']}"
        self.result = {
            'endpoint': api_endpoint,
            'method': self.selected_api['method'],
            'path': self.selected_api['endpoint'],
            'description': self.selected_api.get('description', ''),
            'parameters': param_values,
            'expect': expect_value
        }
        self.dialog.destroy()

    def cancel_clicked(self):
        self.dialog.destroy()


class TaskDialog:
    """Dialog for creating or editing tasks with API/parameter management"""

    def __init__(self, parent, edit_mode=False, initial_data=None, username='SYSTEM', task_count=0):
        self.result = None
        self.edit_mode = edit_mode
        self.initial_data = initial_data or {}
        self.username = username
        self.task_count = task_count

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Edit Task" if edit_mode else "Create Task")
        set_window_geometry_and_center(self.dialog, 718, 840, parent)

        # Initialize API data storage
        self.api_entries = []  # List of API dictionaries with parameters
        self.execution_check_data = self._initialize_execution_check_data(self.initial_data.get('execution_check_apis'))
        self.execution_check_node_map = {}

        self.create_widgets()
        self.dialog.wait_window()

    def create_widgets(self):
        """Create dialog widgets"""
        # Main content frame (scrollable area)
        content_frame = ttk.Frame(self.dialog)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        # Create scrollable canvas for all fields
        canvas = tk.Canvas(content_frame, highlightthickness=0, bg='SystemButtonFace')
        scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollable_frame.columnconfigure(0, weight=1)
        scrollable_frame.columnconfigure(1, weight=1)
        scrollable_frame.columnconfigure(2, weight=1)
        scrollable_frame.columnconfigure(3, weight=1)

        row = 0

        # Basics frame
        section_width = 660

        details_frame = ttk.LabelFrame(scrollable_frame, text="Task Details", width=section_width)
        details_frame.grid(row=row, column=0, columnspan=4, sticky=tk.W, pady=(0, 10))
        details_frame.grid_propagate(True)
        details_frame.columnconfigure(1, weight=1)
        details_frame.columnconfigure(3, weight=0)

        ttk.Label(details_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=4)
        
        default_name = self.initial_data.get('name')
        if not default_name:
            try:
                server = APIServer()
                existing_tasks = server.api_get_current_session_tasks()
                
                existing_names = [t.get('name', '') for t in existing_tasks] if existing_tasks else []
                default_name = create_new_name("New Task", exist_list=existing_names)
            except Exception:
                default_name = f"New Task {self.task_count + 1}"

        self.name_var = tk.StringVar(value=default_name)
        ttk.Entry(details_frame, textvariable=self.name_var, width=60).grid(
            row=0, column=1, pady=4, sticky=tk.EW, columnspan=3)

        meta_row = ttk.Frame(details_frame)
        meta_row.grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=4)
        ttk.Label(meta_row, text="Difficulty:").pack(side=tk.LEFT, padx=(0, 40))
        self.difficulty_var = tk.StringVar(value=self.initial_data.get('difficulty', "easy"))
        difficulty_combo = ttk.Combobox(
            meta_row,
            textvariable=self.difficulty_var,
            values=["easy", "medium", "hard"],
            state="readonly",
            width=10
        )
        difficulty_combo.pack(side=tk.LEFT, padx=(0, 40))

        ttk.Label(meta_row, text="Creator:").pack(side=tk.LEFT, padx=(40, 4))
        self.creator_var = tk.StringVar(value=self.initial_data.get('creator', self.username))
        ttk.Entry(meta_row, textvariable=self.creator_var, width=22).pack(side=tk.LEFT)

        ttk.Label(details_frame, text="Content:").grid(row=2, column=0, sticky=tk.NW, pady=4)
        self.content_text = tk.Text(details_frame, width=70, height=5)
        self.content_text.insert("1.0", self.initial_data.get('content', ""))
        self.content_text.grid(row=2, column=1, pady=4, sticky=tk.EW)

        ttk.Label(details_frame, text="Content Aliases:").grid(row=3, column=0, sticky=tk.NW, pady=4)
        self.content_aliases_text = tk.Text(details_frame, width=70, height=4)
        initial_aliases = self.initial_data.get('content_aliases', [])
        alias_text = ""
        if isinstance(initial_aliases, list):
            alias_text = "\n".join(str(alias) for alias in initial_aliases if alias is not None)
        elif isinstance(initial_aliases, str):
            alias_text = initial_aliases
        self.content_aliases_text.insert("1.0", alias_text)
        self.content_aliases_text.grid(row=3, column=1, pady=4, sticky=tk.EW)

        ttk.Label(
            details_frame,
            text="Enter one alias per line or separate with commas.",
            foreground='gray',
            font=('Arial', 9, 'italic')
        ).grid(row=4, column=1, sticky=tk.W, pady=(0, 4))

        ttk.Label(details_frame, text="Description:").grid(row=5, column=0, sticky=tk.NW, pady=4)
        self.description_text = tk.Text(details_frame, width=70, height=3)
        self.description_text.insert("1.0", self.initial_data.get('description', ""))
        self.description_text.grid(row=5, column=1, pady=4, sticky=tk.EW)

        row += 1

        # Related APIs section - NEW APPROACH: One by one with parameters
        api_container = ttk.LabelFrame(scrollable_frame, text="Related APIs", padding="8", width=section_width)
        api_container.grid(row=row, column=0, columnspan=4, sticky=tk.W, pady=(0, 10))
        api_container.grid_propagate(False)

        api_display_frame = ttk.Frame(api_container)
        api_display_frame.pack(fill=tk.BOTH, expand=True)
        api_display_frame.grid_propagate(False)  # Prevent frame from shrinking

        api_list_frame = ttk.Frame(api_display_frame, padding="5")
        api_list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('endpoint', 'parameters')
        self.api_tree = ttk.Treeview(api_list_frame, columns=columns, show='tree headings', height=6)
        self.api_tree.heading('endpoint', text='API Endpoint')
        self.api_tree.heading('parameters', text='Parameters')
        self.api_tree.column('#0', width=35, stretch=False)
        self.api_tree.column('endpoint', width=320, stretch=False)
        self.api_tree.column('parameters', width=290, stretch=False)

        api_tree_scrollbar = ttk.Scrollbar(api_list_frame, orient=tk.VERTICAL,
                                          command=self.api_tree.yview)
        self.api_tree.configure(yscrollcommand=api_tree_scrollbar.set)

        self.api_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        api_tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        api_controls_frame = ttk.Frame(api_container)
        api_controls_frame.pack(fill=tk.X, pady=6)

        ttk.Button(api_controls_frame, text="Add", command=self.add_api_with_params,
                  width=5).pack(side=tk.LEFT, padx=2)
        ttk.Button(api_controls_frame, text="Edit", command=self.edit_selected_api,
                  width=5).pack(side=tk.LEFT, padx=2)
        ttk.Button(api_controls_frame, text="Duplicate", command=self.duplicate_selected_api,
                  width=9).pack(side=tk.LEFT, padx=2)
        ttk.Button(api_controls_frame, text="Remove", command=self.remove_selected_api,
                  width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(api_controls_frame, text="↑", command=self.move_api_up,
                  width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(api_controls_frame, text="↓", command=self.move_api_down,
                  width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(api_controls_frame, text="Import", command=self.import_apis_from_jsonl,
                  width=7).pack(side=tk.LEFT, padx=2)

        row += 1

        # Execution Check APIs section
        check_container = ttk.LabelFrame(scrollable_frame, text="Execution Check APIs", padding="8", width=section_width)
        check_container.grid(row=row, column=0, columnspan=4, sticky=tk.W, pady=(0, 10))
        check_container.grid_propagate(False)

        check_list_frame = ttk.Frame(check_container, padding="5")
        check_list_frame.pack(fill=tk.BOTH, expand=True)

        check_columns = ('logic', 'endpoint', 'parameters', 'expect')
        self.execution_check_tree = ttk.Treeview(
            check_list_frame,
            columns=check_columns,
            show='tree headings',
            height=6
        )
        self.execution_check_tree.heading('logic', text='Logic')
        self.execution_check_tree.heading('endpoint', text='Endpoint')
        self.execution_check_tree.heading('parameters', text='Parameters')
        self.execution_check_tree.heading('expect', text='Expect')
        self.execution_check_tree.column('#0', width=50, stretch=False)
        self.execution_check_tree.column('logic', width=60, stretch=False)
        self.execution_check_tree.column('endpoint', width=220, stretch=False)
        self.execution_check_tree.column('parameters', width=250, stretch=False)
        self.execution_check_tree.column('expect', width=60, stretch=False)

        check_tree_scrollbar = ttk.Scrollbar(check_list_frame, orient=tk.VERTICAL, command=self.execution_check_tree.yview)
        self.execution_check_tree.configure(yscrollcommand=check_tree_scrollbar.set)
        self.execution_check_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        check_tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        check_controls_frame = ttk.Frame(check_container)
        check_controls_frame.pack(fill=tk.X, pady=6)
        ttk.Button(check_controls_frame, text="Add Check", command=self.add_execution_check, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(check_controls_frame, text="Add Group", command=self.add_execution_group, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(check_controls_frame, text="Edit", command=self.edit_execution_node, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(check_controls_frame, text="Remove", command=self.remove_execution_node, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(check_controls_frame, text="↑", command=lambda: self.move_execution_node(-1), width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(check_controls_frame, text="↓", command=lambda: self.move_execution_node(1), width=3).pack(side=tk.LEFT, padx=2)

        self._refresh_execution_check_tree()

        row += 1

        # Commands section - AUTO-GENERATED (read-only display)
        commands_container = ttk.LabelFrame(scrollable_frame, text="Commands (auto-generated from APIs)", padding="8", width=section_width)
        commands_container.grid(row=row, column=0, columnspan=4, sticky=tk.W, pady=(0, 10))

        self.commands_text = tk.Text(commands_container, width=70, height=4,
                                     state='disabled', bg='#f0f0f0')
        self.commands_text.pack(fill=tk.BOTH, expand=True)

        row += 1

        # Pack canvas and scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons at the bottom
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        button_text = "Save Changes" if self.edit_mode else "Create"
        ok_button = ttk.Button(button_frame, text=button_text, command=self.ok_clicked)
        ok_button.pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.RIGHT, padx=5)

        # Load initial data if editing
        if self.edit_mode:
            # Handle new API format (related_apis with endpoint and parameters)
            if 'related_apis' in self.initial_data:
                related_apis = self.initial_data['related_apis']
                # Convert new format to internal api_entries format
                for api in related_apis:
                    if isinstance(api, dict) and 'endpoint' in api:
                        # New format: {"endpoint": "...", "parameters": {...}}
                        self.api_entries.append({
                            'endpoint': f"POST {api['endpoint']}",  # Add method
                            'method': 'POST',
                            'path': api['endpoint'],
                            'description': '',
                            'parameters': api.get('parameters', {})
                        })
                    elif isinstance(api, str):
                        # Old format: just endpoint string
                        self.api_entries.append({
                            'endpoint': api,
                            'method': 'POST',
                            'path': api.split(' ')[1] if ' ' in api else api,
                            'description': '',
                            'parameters': {}
                        })
                self._refresh_api_tree()
                self._update_commands_display()
            # Fallback to old api_entries format if exists
            elif 'api_entries' in self.initial_data:
                self.api_entries = self.initial_data['api_entries']
                self._refresh_api_tree()
                self._update_commands_display()

    def add_api_with_params(self):
        """Open dialog to add an API with parameters"""
        api_categories = get_api_by_category()
        dialog = AddAPIDialog(self.dialog, api_categories)

        if dialog.result:
            # Add to our API entries list
            self.api_entries.append(dialog.result)
            self._refresh_api_tree()
            self._update_commands_display()

    def edit_selected_api(self):
        """Edit the selected API entry"""
        selection = self.api_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an API to edit")
            return

        # Get the index from the selection
        item = selection[0]
        index = int(self.api_tree.item(item, 'text')) - 1

        if 0 <= index < len(self.api_entries):
            # Get the existing API data
            api_categories = get_api_by_category()
            existing_api_data = self.api_entries[index]

            # Open edit dialog with existing data
            dialog = AddAPIDialog(self.dialog, api_categories, edit_data=existing_api_data)

            if dialog.result:
                # Update the API entry
                self.api_entries[index] = dialog.result
                self._refresh_api_tree()
                self._update_commands_display()

                # Re-select the edited item
                new_item = self.api_tree.get_children()[index]
                self.api_tree.selection_set(new_item)

    def remove_selected_api(self):
        """Remove selected API from the list"""
        selection = self.api_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an API to remove")
            return

        # Get the index from the selection
        item = selection[0]
        index = int(self.api_tree.item(item, 'text')) - 1

        if 0 <= index < len(self.api_entries):
            del self.api_entries[index]
            self._refresh_api_tree()
            self._update_commands_display()

    def duplicate_selected_api(self):
        """Duplicate the selected API and add it to the end of the list"""
        selection = self.api_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an API to duplicate")
            return

        # Get the index from the selection
        item = selection[0]
        index = int(self.api_tree.item(item, 'text')) - 1

        if 0 <= index < len(self.api_entries):
            # Create a deep copy of the API entry
            duplicated_api = copy.deepcopy(self.api_entries[index])

            # Append to the end of the list
            self.api_entries.append(duplicated_api)
            self._refresh_api_tree()
            self._update_commands_display()

            # Select the newly duplicated item (last item in the tree)
            children = self.api_tree.get_children()
            if children:
                last_item = children[-1]
                self.api_tree.selection_set(last_item)
                self.api_tree.see(last_item)  # Scroll to show the duplicated item

    def import_apis_from_jsonl(self):
        """Import APIs from a JSONL file and add them to related_apis"""
        # Open file dialog to select JSONL file
        file_path = filedialog.askopenfilename(
            parent=self.dialog,
            title="Select JSONL file to import",
            filetypes=[("JSONL files", "*.jsonl"), ("All files", "*.*")]
        )

        if not file_path:
            return  # User cancelled

        try:
            imported_count = 0
            errors = []

            # Read and parse JSONL file
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue  # Skip empty lines

                    try:
                        # Parse JSON line
                        api_data = json.loads(line)

                        # Expected format: {"endpoint": "...", "parameters": {...}}
                        # or {"endpoint": "...", "method": "...", "parameters": {...}}
                        if not isinstance(api_data, dict):
                            errors.append(f"Line {line_num}: Not a JSON object")
                            continue

                        endpoint = api_data.get('endpoint', '')
                        if not endpoint:
                            errors.append(f"Line {line_num}: Missing 'endpoint' field")
                            continue

                        # Extract method if provided, otherwise default to POST
                        method = api_data.get('method', 'POST').upper()

                        # Build the API entry in the internal format
                        api_entry = {
                            'endpoint': f"{method} {endpoint}",
                            'method': method,
                            'path': endpoint,
                            'description': api_data.get('description', ''),
                            'parameters': api_data.get('parameters', {})
                        }

                        # Add to the end of the API entries list
                        self.api_entries.append(api_entry)
                        imported_count += 1

                    except json.JSONDecodeError as e:
                        errors.append(f"Line {line_num}: Invalid JSON - {str(e)}")
                    except Exception as e:
                        errors.append(f"Line {line_num}: {str(e)}")

            # Refresh the display
            if imported_count > 0:
                self._refresh_api_tree()
                self._update_commands_display()

                # Scroll to the first imported item
                children = self.api_tree.get_children()
                if children and len(children) >= imported_count:
                    first_imported = children[-imported_count]
                    self.api_tree.see(first_imported)
                    self.api_tree.selection_set(first_imported)

            # Show results
            if errors:
                error_msg = f"Imported {imported_count} API(s).\n\nErrors encountered:\n"
                error_msg += "\n".join(errors[:10])  # Show first 10 errors
                if len(errors) > 10:
                    error_msg += f"\n... and {len(errors) - 10} more errors"
                messagebox.showwarning("Import Completed with Errors", error_msg)
            else:
                messagebox.showinfo("Import Successful",
                                   f"Successfully imported {imported_count} API(s) from JSONL file.")

        except Exception as e:
            messagebox.showerror("Import Failed", f"Failed to import JSONL file:\n{str(e)}")

    def move_api_up(self):
        """Move selected API up in the list"""
        selection = self.api_tree.selection()
        if not selection:
            return

        item = selection[0]
        index = int(self.api_tree.item(item, 'text')) - 1

        if 0 < index < len(self.api_entries):
            # Swap
            self.api_entries[index], self.api_entries[index - 1] = \
                self.api_entries[index - 1], self.api_entries[index]
            self._refresh_api_tree()
            # Re-select
            new_item = self.api_tree.get_children()[index - 1]
            self.api_tree.selection_set(new_item)

    def move_api_down(self):
        """Move selected API down in the list"""
        selection = self.api_tree.selection()
        if not selection:
            return

        item = selection[0]
        index = int(self.api_tree.item(item, 'text')) - 1

        if 0 <= index < len(self.api_entries) - 1:
            # Swap
            self.api_entries[index], self.api_entries[index + 1] = \
                self.api_entries[index + 1], self.api_entries[index]
            self._refresh_api_tree()
            # Re-select
            new_item = self.api_tree.get_children()[index + 1]
            self.api_tree.selection_set(new_item)

    def _refresh_api_tree(self):
        """Refresh the API treeview display"""
        # Clear existing items
        for item in self.api_tree.get_children():
            self.api_tree.delete(item)

        # Add API entries
        for idx, api_entry in enumerate(self.api_entries):
            endpoint = api_entry.get('endpoint', '')
            params = api_entry.get('parameters', {})

            # Format parameters for display
            param_str = ', '.join([f"{k}={format_param_value(k, v)}" for k, v in params.items() if v is not None])
            if not param_str:
                param_str = "(no parameters)"

            # Add to tree
            self.api_tree.insert('', tk.END, text=str(idx + 1),
                                values=(endpoint, param_str))

    def _update_commands_display(self):
        """Update the commands display based on selected APIs"""
        commands = self._extract_commands_from_apis()

        # Update text widget
        self.commands_text.config(state='normal')
        self.commands_text.delete('1.0', tk.END)
        if commands:
            self.commands_text.insert('1.0', ', '.join(commands))
        else:
            self.commands_text.insert('1.0', '(No commands - add APIs to auto-generate)')
        self.commands_text.config(state='disabled')

    def _extract_commands_from_apis(self) -> List[str]:
        """Extract command names from API endpoints in the same order as APIs"""
        commands = []
        seen = set()  # Track duplicates

        for api_entry in self.api_entries:
            endpoint = api_entry.get('path', '')

            # Extract command from endpoint like "/drones/{id}/command/take_off"
            if '/command/' in endpoint:
                parts = endpoint.split('/command/')
                if len(parts) > 1:
                    command = parts[1].strip('/')
                    # Only add if not already seen (preserve first occurrence order)
                    if command not in seen:
                        commands.append(command)
                        seen.add(command)

        return commands

    def _initialize_execution_check_data(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Normalize execution_check_apis data into internal structure."""
        if not data or not isinstance(data, dict):
            return {"logic": "and", "checks": []}

        logic = data.get('logic', 'and')
        checks = data.get('checks', [])
        normalized_checks = []
        for child in checks or []:
            normalized = self._normalize_execution_check_node(child)
            if normalized:
                normalized_checks.append(normalized)

        return {"logic": str(logic).lower(), "checks": normalized_checks}

    def _normalize_execution_check_node(self, node: Any) -> Optional[Dict[str, Any]]:
        """Normalize a single execution check node (group or leaf)."""
        if not isinstance(node, dict):
            return None

        if 'checks' in node:
            checks_list = node.get('checks') or []
            return {
                "logic": str(node.get('logic', 'and')).lower(),
                "checks": [normalized for normalized in (self._normalize_execution_check_node(child) for child in checks_list) if normalized]
            }

        endpoint_field = node.get('endpoint', '') or node.get('path', '')
        method = node.get('method', 'GET')
        if endpoint_field.startswith(('GET ', 'POST ', 'PUT ', 'DELETE ', 'PATCH ')):
            endpoint_display = endpoint_field
            endpoint_path = endpoint_field.split(' ', 1)[1] if ' ' in endpoint_field else endpoint_field
        else:
            endpoint_display = f"{method} {endpoint_field}".strip()
            endpoint_path = endpoint_field

        expect_bool = normalize_expect_value(node.get('expect'))

        return {
            "endpoint": endpoint_display,
            "method": method,
            "path": endpoint_path,
            "description": node.get('description', ''),
            "parameters": node.get('parameters', {}) or {},
            "expect": expect_bool
        }

    def _refresh_execution_check_tree(self):
        """Refresh tree view for execution_check_apis."""
        if not hasattr(self, 'execution_check_tree'):
            return

        for item in self.execution_check_tree.get_children():
            self.execution_check_tree.delete(item)

        self.execution_check_node_map = {}
        root_logic = self.execution_check_data.get('logic', 'and')

        root_item = self.execution_check_tree.insert(
            '',
            tk.END,
            text='Root',
            values=(root_logic.upper(), '', '', ''),
            open=True
        )
        self.execution_check_node_map[root_item] = {'node': self.execution_check_data, 'parent_checks': None}

        for child in self.execution_check_data.get('checks', []):
            self._insert_execution_check_node(root_item, child, self.execution_check_data['checks'])

    def _insert_execution_check_node(self, parent_item: str, node: Dict[str, Any], parent_checks: List[Dict[str, Any]]):
        """Insert a node into the tree view and map it back to the data list."""
        is_group = 'checks' in node
        logic = node.get('logic', '').upper() if is_group else ''
        endpoint = node.get('endpoint', '') if not is_group else f"{len(node.get('checks', []))} checks"

        params = node.get('parameters', {}) if not is_group else {}
        param_str = ', '.join([f"{k}={format_param_value(k, v)}" for k, v in params.items() if v is not None])
        if not param_str and not is_group:
            param_str = "(no parameters)"

        expect_val = node.get('expect')
        expect_str = ''
        if isinstance(expect_val, bool):
            expect_str = json.dumps(expect_val)

        item_id = self.execution_check_tree.insert(
            parent_item,
            tk.END,
            text="Group" if is_group else "Check",
            values=(logic, endpoint, param_str, expect_str),
            open=True if is_group else False
        )

        self.execution_check_node_map[item_id] = {'node': node, 'parent_checks': parent_checks}

        if is_group:
            for child in node.get('checks', []):
                self._insert_execution_check_node(item_id, child, node['checks'])

    def _get_selected_execution_node(self):
        selection = self.execution_check_tree.selection()
        if not selection:
            return None
        return self.execution_check_node_map.get(selection[0])

    def _get_target_check_list(self) -> List[Dict[str, Any]]:
        """Return the list to which new nodes should be added."""
        context = self._get_selected_execution_node()
        if not context:
            return self.execution_check_data['checks']
        node = context['node']
        if node and 'checks' in node:
            return node['checks']
        return context.get('parent_checks') or self.execution_check_data['checks']

    def add_execution_group(self):
        target_checks = self._get_target_check_list()
        target_checks.append({"logic": "and", "checks": []})
        self._refresh_execution_check_tree()

    def add_execution_check(self):
        api_categories = get_check_api_by_category()
        dialog = ExecutionCheckAPIDialog(self.dialog, api_categories)
        if dialog.result:
            target_checks = self._get_target_check_list()
            target_checks.append(dialog.result)
            self._refresh_execution_check_tree()

    def edit_execution_node(self):
        context = self._get_selected_execution_node()
        if not context:
            messagebox.showwarning("No Selection", "Please select a group or check to edit")
            return

        node = context['node']
        if node is self.execution_check_data:
            # Editing root -> change logic only
            self._prompt_logic_change(node)
            return

        if 'checks' in node:
            self._prompt_logic_change(node)
        else:
            parent_checks = context.get('parent_checks')
            if parent_checks is None:
                parent_checks = self.execution_check_data['checks']
            try:
                index = parent_checks.index(node)
            except ValueError:
                index = None

            api_categories = get_check_api_by_category()
            dialog = ExecutionCheckAPIDialog(self.dialog, api_categories, edit_data=node)
            if dialog.result and index is not None:
                parent_checks[index] = dialog.result
                self._refresh_execution_check_tree()

    def _prompt_logic_change(self, node: Dict[str, Any]):
        logic_dialog = tk.Toplevel(self.dialog)
        logic_dialog.title("Set Logic")
        logic_dialog.transient(self.dialog)
        logic_dialog.grab_set()
        ttk.Label(logic_dialog, text="Choose logic for this group:").pack(padx=10, pady=(10, 5))
        logic_var = tk.StringVar(value=node.get('logic', 'and').upper())
        logic_combo = ttk.Combobox(logic_dialog, textvariable=logic_var, values=["AND", "OR", "NOT"], state="readonly", width=8)
        logic_combo.pack(padx=10, pady=5)

        def save_logic():
            node['logic'] = logic_var.get().lower()
            logic_dialog.destroy()
            self._refresh_execution_check_tree()

        btn_frame = ttk.Frame(logic_dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Save", command=save_logic).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=logic_dialog.destroy).pack(side=tk.LEFT, padx=5)
        logic_dialog.wait_window()

    def remove_execution_node(self):
        context = self._get_selected_execution_node()
        if not context:
            messagebox.showwarning("No Selection", "Please select a group or check to remove")
            return

        node = context['node']
        if node is self.execution_check_data:
            messagebox.showwarning("Invalid Action", "Root group cannot be removed")
            return

        parent_checks = context.get('parent_checks')
        if not parent_checks:
            return

        try:
            parent_checks.remove(node)
            self._refresh_execution_check_tree()
        except ValueError:
            pass

    def move_execution_node(self, direction: int):
        """Move selected execution node up (-1) or down (+1) within its parent list."""
        context = self._get_selected_execution_node()
        if not context:
            return
        node = context['node']
        parent_checks = context.get('parent_checks')
        if not parent_checks:
            return
        try:
            index = parent_checks.index(node)
        except ValueError:
            return

        new_index = index + direction
        if 0 <= new_index < len(parent_checks):
            parent_checks[index], parent_checks[new_index] = parent_checks[new_index], parent_checks[index]
            self._refresh_execution_check_tree()
            # Reselect moved node
            for item_id, mapping in self.execution_check_node_map.items():
                if mapping['node'] is node:
                    self.execution_check_tree.selection_set(item_id)
                    self.execution_check_tree.see(item_id)
                    break

    def _build_execution_check_result(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Convert internal execution check structure into payload format."""
        if 'checks' in node:
            return {
                "logic": node.get('logic', 'and'),
                "checks": [self._build_execution_check_result(child) for child in node.get('checks', [])]
            }

        endpoint_str = node.get('path') or node.get('endpoint', '')
        if ' ' in endpoint_str:
            endpoint_str = endpoint_str.split(' ', 1)[1]

        cleaned = {
            "endpoint": endpoint_str,
            "parameters": normalize_id_params(node.get('parameters', {}) or {})
        }
        expect_val = normalize_expect_value(node.get('expect'))
        if expect_val is not None:
            cleaned['expect'] = expect_val
        return cleaned

    def ok_clicked(self):
        """Handle OK button click"""
        try:
            # Extract commands from APIs
            commands = self._extract_commands_from_apis()

            # Build result - use new API format with endpoint and parameters
            related_apis_new_format = []
            for api in self.api_entries:
                related_apis_new_format.append({
                    "endpoint": api.get('path', api.get('endpoint', '')),
                    "parameters": normalize_id_params(api.get('parameters', {}))
                })

            # Parse aliases from the text box (one per line or comma separated)
            aliases_raw = self.content_aliases_text.get("1.0", tk.END)
            content_aliases = []
            if aliases_raw:
                # Replace newlines with commas so users can mix delimiters
                raw_parts = aliases_raw.replace('\n', ',').split(',')
                for part in raw_parts:
                    alias = part.strip()
                    if alias:
                        content_aliases.append(alias)

            originated_from = self.initial_data.get('originated_from') or self.creator_var.get()

            self.result = {
                "name": self.name_var.get(),
                "creator": self.creator_var.get(),
                "originated_from": originated_from,
                "difficulty": self.difficulty_var.get(),
                "description": self.description_text.get("1.0", tk.END).strip(),
                "content": self.content_text.get("1.0", tk.END).strip(),
                "content_aliases": content_aliases,
                "related_apis": related_apis_new_format,  # New format with parameters
                "execution_check_apis": self._build_execution_check_result(self.execution_check_data),
                "commands": commands  # Auto-generated commands
            }

            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Invalid Input", f"Error: {str(e)}")

    def cancel_clicked(self):
        """Handle Cancel button click"""
        self.dialog.destroy()


# For backward compatibility, keep old name available
ImprovedTaskDialog = TaskDialog
