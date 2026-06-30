#!/usr/bin/env python3
"""
MultiUAV-Plat Control System - Task Template Dialogs

Provides UI for managing task templates:
- Template browser dialog
- Template editor dialog
- Template instantiation dialog with parameter customization

Author: MultiUAV-Plat Control System
Version: Provided by application entrypoint
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from typing import Dict, List, Any, Optional
import json
import random
import re
import platform
from detail_panel import DetailPanel
from template_editor import TemplateEditor
from task_template_manager import (
    TaskTemplateManager,
    SUPPORTED_SESSION_TASK_TYPES,
    TEMPLATE_SUITABLE_TASK_TYPES,
)
from utils import set_window_geometry_and_center, create_new_names
from template_placeholders import (
    get_placeholder_info,
    generate_random_value,
    parse_dynamic_random,
    find_placeholders_in_text
)


def format_task_type_label(task_type: str) -> str:
    """Format a task type key for UI display."""
    return str(task_type).replace('_', ' ').title()


def format_suitable_task_label(suitable_task: List[str]) -> str:
    """Format suitability metadata for compact display."""
    normalized = TaskTemplateManager.normalize_suitable_task(suitable_task)
    if not normalized or 'all' in normalized:
        return "All"
    return ", ".join(format_task_type_label(task_type) for task_type in normalized)


def template_matches_task_type(template: Dict[str, Any], current_task_type: Optional[str]) -> bool:
    """Return whether the template is suitable for the given session task type."""
    normalized = TaskTemplateManager.normalize_suitable_task(template.get('suitable_task'))
    if not current_task_type or not normalized or 'all' in normalized:
        return True
    return current_task_type in normalized


class TemplateParameterDialog:
    """Dialog for customizing template parameters before instantiation"""

    def __init__(self, parent, template_data: Dict[str, Any], available_drones: List[Dict[str, Any]],
                 template_manager=None, template_id=None, available_targets: List[Dict[str, Any]] = None,
                 available_obstacles: List[Dict[str, Any]] = None, username: str = "SYSTEM",
                 existing_task_names: List[str] = None, return_spec: bool = False,
                 allow_specific_entities: bool = True):
        self.result = None
        self.template_data = template_data
        self.available_drones = available_drones
        self.available_targets  = available_targets
        self.available_obstacles = available_obstacles
        self.username = username
        self.existing_task_names = existing_task_names or []
        self.return_spec = return_spec
        self.allow_specific_entities = allow_specific_entities

        self.template_manager = template_manager
        self.template_id = template_id
        self._ordered_index = {'drone': 0, 'target': 0, 'obstacle': 0}

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Customize Template: {template_data.get('name', 'Template')}")
        set_window_geometry_and_center(self.dialog, 600, 500, parent)

        self.create_widgets()
        self.dialog.wait_window()

    def create_widgets(self):
        """Create dialog widgets"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame,
                               text=f"Template: {self.template_data.get('name', 'Unknown')}",
                               font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 5))

        # Description
        desc_label = ttk.Label(main_frame,
                              text=self.template_data.get('description', ''),
                              foreground='gray',
                              wraplength=550)
        desc_label.pack(pady=(0, 10))

        # Scrollable frame for parameters
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Parameters section
        self.param_widgets = {}
        row = 0

        # Task name
        ttk.Label(scrollable_frame, text="Task Name:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        self.param_widgets['name'] = ttk.Entry(scrollable_frame, width=50)
        self.param_widgets['name'].insert(0, self.template_data.get('name', ''))
        self.param_widgets['name'].grid(row=row, column=1, pady=5, sticky=tk.W, padx=5)
        row += 1

        # Detect parameters from template
        parameters = self._detect_template_parameters()

        if parameters:
            ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL).grid(
                row=row, column=0, columnspan=2, sticky=tk.EW, pady=10)
            row += 1

            ttk.Label(scrollable_frame, text="Template Parameters:",
                     font=('Arial', 10, 'bold')).grid(
                row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
            row += 1

            # Create input fields for each detected parameter
            for param_name, param_info in sorted(parameters.items()):
                # Parameter label with description
                label_text = f"{param_name}:"
                ttk.Label(scrollable_frame, text=label_text, font=('Arial', 9, 'bold')).grid(
                    row=row, column=0, sticky=tk.W, pady=5, padx=(10, 5))

                # Parameter input widget
                # Check for grouped entity parameters (drone, drone_1, target, target_2, obstacle, obstacle_3, etc.)
                if param_info.get('type') == 'entity':
                    entity_type = param_info.get('entity_type')

                    # Handle drone entities
                    if entity_type == 'drone' and self.available_drones:
                        # Drone selection with multiple modes
                        drone_frame = ttk.Frame(scrollable_frame)
                        drone_frame.grid(row=row, column=1, pady=5, sticky=tk.W, padx=5)

                        # Dropdown for single mode / specific drone in batch
                        drone_options = ['[RANDOM]', '[ORDERED]']
                        if self.allow_specific_entities:
                            drone_options += [f"{d['id']} - {d['name']}" for d in self.available_drones]
                        param_var = tk.StringVar()
                        param_combo = ttk.Combobox(drone_frame, textvariable=param_var,
                                                  values=drone_options, width=40, state='readonly')
                        if drone_options:
                            param_combo.set(drone_options[0])  # Default to [RANDOM]
                        param_combo.pack(side=tk.LEFT)

                        self.param_widgets[param_name] = {
                            'type': 'entity',
                            'entity_type': 'drone',
                            'id_param': param_info['id_param'],
                            'name_param': param_info['name_param'],
                            'single_var': param_var,
                            'single_combo': param_combo
                        }

                        row += 1  # Extra row previously used by batch options

                    # Handle target entities
                    elif entity_type == 'target':
                        # Target selection with dropdown (always shown; if no data, allow typing)
                        target_frame = ttk.Frame(scrollable_frame)
                        target_frame.grid(row=row, column=1, pady=5, sticky=tk.W, padx=5)

                        def _format_target(t):
                            tid = t.get('id', '')
                            tname = t.get('name', '') or tid
                            return f"{tid} - {tname}" if tid and tname else (tid or tname)

                        target_options = ['[RANDOM]', '[ORDERED]']
                        if self.allow_specific_entities:
                            target_options += [_format_target(t) for t in self.available_targets]
                        target_map = {'[RANDOM]': None}
                        if self.allow_specific_entities:
                            for t in self.available_targets:
                                label = _format_target(t)
                                target_map[label] = t

                        param_var = tk.StringVar()
                        combo_state = 'readonly'
                        param_combo = ttk.Combobox(target_frame, textvariable=param_var,
                                                  values=target_options, width=40, state=combo_state)
                        if target_options:
                            param_combo.set(target_options[0])
                        param_combo.pack(side=tk.LEFT)

                        self.param_widgets[param_name] = {
                            'type': 'entity',
                            'entity_type': 'target',
                            'id_param': param_info.get('id_param'),
                            'name_param': param_info.get('name_param'),
                            'single_var': param_var,
                            'single_combo': param_combo,
                            'options_map': target_map
                        }

                        row += 1

                    # Handle obstacle entities
                    elif entity_type == 'obstacle':
                        # Obstacle selection with dropdown (always shown; if no data, allow typing)
                        obstacle_frame = ttk.Frame(scrollable_frame)
                        obstacle_frame.grid(row=row, column=1, pady=5, sticky=tk.W, padx=5)

                        def _format_obstacle(o):
                            oid = o.get('id', '')
                            oname = o.get('name', '') or oid
                            return f"{oid} - {oname}" if oid and oname else (oid or oname)

                        obstacle_options = ['[RANDOM]', '[ORDERED]']
                        if self.allow_specific_entities:
                            obstacle_options += [_format_obstacle(o) for o in self.available_obstacles]
                        obstacle_map = {'[RANDOM]': None}
                        if self.allow_specific_entities:
                            for o in self.available_obstacles:
                                label = _format_obstacle(o)
                                obstacle_map[label] = o

                        param_var = tk.StringVar()
                        combo_state = 'readonly'
                        param_combo = ttk.Combobox(obstacle_frame, textvariable=param_var,
                                                  values=obstacle_options, width=40, state=combo_state)
                        if obstacle_options:
                            param_combo.set(obstacle_options[0])
                        param_combo.pack(side=tk.LEFT)

                        self.param_widgets[param_name] = {
                            'type': 'entity',
                            'entity_type': 'obstacle',
                            'id_param': param_info.get('id_param'),
                            'name_param': param_info.get('name_param'),
                            'single_var': param_var,
                            'single_combo': param_combo,
                            'options_map': obstacle_map
                        }

                        row += 1
                elif param_info.get('type') in ['float', 'int']:
                    # Numeric parameter - support both single value and range
                    param_frame = ttk.Frame(scrollable_frame)
                    param_frame.grid(row=row, column=1, pady=5, sticky=tk.W, padx=5)

                    # Checkbox for range mode
                    range_var = tk.BooleanVar(value=False)
                    range_check = ttk.Checkbutton(param_frame, text="Range", variable=range_var,
                                                  command=lambda pf=param_frame, rv=range_var, pn=param_name: self._toggle_range_mode(pf, rv, pn))
                    range_check.pack(side=tk.LEFT, padx=(0, 5))

                    # Single value entry (default)
                    value_entry = ttk.Entry(param_frame, width=20)
                    if param_info.get('default'):
                        value_entry.insert(0, str(param_info['default']))
                    value_entry.pack(side=tk.LEFT, padx=2)

                    # Range entries (initially hidden)
                    min_label = ttk.Label(param_frame, text="Min:")
                    min_entry = ttk.Entry(param_frame, width=15)
                    max_label = ttk.Label(param_frame, text="Max:")
                    max_entry = ttk.Entry(param_frame, width=15)

                    # Store widgets for toggling
                    self.param_widgets[param_name] = {
                        'type': 'numeric',
                        'range_var': range_var,
                        'value_entry': value_entry,
                        'min_label': min_label,
                        'min_entry': min_entry,
                        'max_label': max_label,
                        'max_entry': max_entry
                    }
                else:
                    # Text entry for other parameters
                    param_entry = ttk.Entry(scrollable_frame, width=50)
                    if param_info.get('default'):
                        param_entry.insert(0, str(param_info['default']))
                    param_entry.grid(row=row, column=1, pady=5, sticky=tk.W, padx=5)
                    self.param_widgets[param_name] = param_entry

                row += 1

                # Help text showing description and type
                desc = param_info.get('description', '')
                param_type = param_info.get('type', 'string')
                if desc:
                    help_text = f"{desc} (type: {param_type})"
                else:
                    help_text = f"(type: {param_type})"

                help_label = ttk.Label(scrollable_frame,
                                     text=help_text,
                                     foreground='gray',
                                     font=('Arial', 8),
                                     wraplength=400)
                help_label.grid(row=row, column=1, sticky=tk.W, padx=5, pady=(0, 5))

                row += 1

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        self.create_button = ttk.Button(button_frame, text="Create Task", command=self.ok_clicked)
        self.create_button.pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Batch Create", command=self.batch_create_clicked).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.RIGHT)

    def _toggle_range_mode(self, param_frame, range_var, param_name):
        """Toggle between single value and range mode for numeric parameters"""
        widgets = self.param_widgets[param_name]

        if range_var.get():
            # Switch to range mode
            widgets['value_entry'].pack_forget()
            widgets['min_label'].pack(side=tk.LEFT, padx=2)
            widgets['min_entry'].pack(side=tk.LEFT, padx=2)
            widgets['max_label'].pack(side=tk.LEFT, padx=2)
            widgets['max_entry'].pack(side=tk.LEFT, padx=2)
        else:
            # Switch to single value mode
            widgets['min_label'].pack_forget()
            widgets['min_entry'].pack_forget()
            widgets['max_label'].pack_forget()
            widgets['max_entry'].pack_forget()
            widgets['value_entry'].pack(side=tk.LEFT, padx=2)

    def _detect_template_parameters(self) -> Dict[str, Dict[str, Any]]:
        """Detect parameters used in template

        Groups related _id and _name placeholders into single entities:
        - drone_id + drone_name -> drone
        - drone_1_id + drone_1_name -> drone_1
        - target_id + target_name -> target
        - obstacle_2_id + obstacle_2_name -> obstacle_2

        Returns:
            Dictionary of parameter names to parameter info
        """
        # Import here to avoid circular dependency
        
        def _is_random_placeholder(name: str) -> bool:
            """Return True if placeholder is a random placeholder (predefined or dynamic)."""
            name = name.strip() # Ensure no leading/trailing whitespace
            info = get_placeholder_info(name)
            if info and info.get('type') == 'random_float':
                return True

            # Check for named variable references without range (e.g., {randint_var} or {random_var})
            # These are references to sticky random variables defined elsewhere
            if re.match(r'^randint_([a-zA-Z_][a-zA-Z0-9_]*)$', name):
                return True
            if re.match(r'^random_([a-zA-Z_][a-zA-Z0-9_]*)$', name):
                return True

            # Check for coordinate variable references without range (e.g., {randx_var}, {randy_var}, {randz_var})
            # Also composite types without range (e.g., {randxy_var}, {randxyz_var}, {randpos_var}, {randxyc_var})
            if re.match(r'^(randx|randy|randz|randxy|randxyz|randpos|randxyc)_([a-zA-Z_][a-zA-Z0-9_]*)$', name):
                return True

            # For dynamic randoms (new and legacy syntax), parse_dynamic_random will return a value if it matches
            _, dynamic_value, _ = parse_dynamic_random(name)
            return dynamic_value is not None

        raw_parameters = {}
        def _maybe_add_placeholder(placeholder: str):
            if placeholder in raw_parameters or _is_random_placeholder(placeholder):
                return
            info = get_placeholder_info(placeholder)
            if info:
                raw_parameters[placeholder] = {
                    'type': info.get('type', 'string'),
                    'default': info.get('example', None),
                    'description': info.get('description', '')
                }
            else:
                raw_parameters[placeholder] = {
                    'type': 'string',
                    'default': None,
                    'description': ''
                }

        # Check content field for placeholders
        if 'content' in self.template_data:
            content = self.template_data['content']
            if isinstance(content, str):
                placeholders = find_placeholders_in_text(content)
                for placeholder in placeholders:
                    if placeholder not in raw_parameters and not _is_random_placeholder(placeholder):
                        _maybe_add_placeholder(placeholder)

        # Check content_aliases for placeholders
        if 'content_aliases' in self.template_data:
            for alias in self.template_data.get('content_aliases', []):
                if isinstance(alias, str):
                    placeholders = find_placeholders_in_text(alias)
                    for placeholder in placeholders:
                        if placeholder not in raw_parameters and not _is_random_placeholder(placeholder):
                            _maybe_add_placeholder(placeholder)

        # Check related_apis for placeholder parameters
        if 'related_apis' in self.template_data:
            for api in self.template_data['related_apis']:
                if 'parameters' in api:
                    for param_key, param_value in api['parameters'].items():
                        # Detect placeholder format: {param_name}
                        if isinstance(param_value, str) and param_value.startswith('{') and param_value.endswith('}'):
                            placeholder = param_value[1:-1]
                            if placeholder not in raw_parameters and not _is_random_placeholder(placeholder):
                                _maybe_add_placeholder(placeholder)

        def _collect_from_value(value: Any):
            if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
                placeholder = value[1:-1]
                if placeholder not in raw_parameters and not _is_random_placeholder(placeholder):
                    _maybe_add_placeholder(placeholder)
            elif isinstance(value, dict):
                for v in value.values():
                    _collect_from_value(v)
            elif isinstance(value, list):
                for v in value:
                    _collect_from_value(v)

        def _traverse_checks(node: Dict[str, Any]):
            if not isinstance(node, dict):
                return
            if 'checks' in node:
                for child in node.get('checks', []):
                    _traverse_checks(child)
            else:
                params = node.get('parameters', {})
                for param_val in params.values():
                    _collect_from_value(param_val)
                expect_val = node.get('expect')
                if expect_val is not None:
                    _collect_from_value(expect_val)

        if 'execution_check_apis' in self.template_data:
            _traverse_checks(self.template_data.get('execution_check_apis'))

        # Group related _id and _name parameters into single entities
        parameters = {}
        grouped = set()  # Track which parameters have been grouped

        for param_name in raw_parameters.keys():
            if param_name in grouped:
                continue

            # Check if this is an _id or _name parameter
            if param_name.endswith('_id'):
                base_name = param_name[:-3]  # Remove '_id'
                name_param = base_name + '_name'

                # Check if corresponding _name exists
                if name_param in raw_parameters:
                    # Group them under base name (e.g., 'drone', 'drone_1', 'target_2')
                    parameters[base_name] = {
                        'type': 'entity',  # Special type to indicate grouped entity
                        'entity_type': base_name.split('_')[0] if '_' in base_name else base_name,  # 'drone', 'target', 'obstacle'
                        'has_id': True,
                        'has_name': True,
                        'id_param': param_name,
                        'name_param': name_param,
                        'description': raw_parameters[param_name].get('description', ''),
                        'default': raw_parameters[param_name].get('default', None)
                    }
                    grouped.add(param_name)
                    grouped.add(name_param)
                else:
                    # Only _id exists, still treat as entity with id only
                    parameters[base_name] = {
                        'type': 'entity',
                        'entity_type': base_name.split('_')[0] if '_' in base_name else base_name,
                        'has_id': True,
                        'has_name': False,
                        'id_param': param_name,
                        'name_param': None,
                        'description': raw_parameters[param_name].get('description', ''),
                        'default': raw_parameters[param_name].get('default', None)
                    }
                    grouped.add(param_name)

            elif param_name.endswith('_name'):
                base_name = param_name[:-5]  # Remove '_name'
                id_param = base_name + '_id'

                # Check if this _name wasn't already grouped with an _id
                if id_param not in raw_parameters:
                    # Only _name exists, treat as entity with name only
                    parameters[base_name] = {
                        'type': 'entity',
                        'entity_type': base_name.split('_')[0] if '_' in base_name else base_name,
                        'has_id': False,
                        'has_name': True,
                        'id_param': None,
                        'name_param': param_name,
                        'description': raw_parameters[param_name].get('description', ''),
                        'default': raw_parameters[param_name].get('default', None)
                    }
                    grouped.add(param_name)
                # else: already handled in the _id case above

            else:
                # Not an _id or _name parameter, keep as is
                parameters[param_name] = raw_parameters[param_name]

        return parameters

    def ok_clicked(self):
        """Handle OK button click - single task creation"""
        try:
            if self.return_spec:
                self._create_single_task_spec()
            else:
                self._create_single_task()
        except Exception as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")

    def batch_create_clicked(self):
        """Prompt for count and generate multiple tasks"""
        try:
            count = simpledialog.askinteger("Batch Create", "How many tasks to generate?", parent=self.dialog,
                                            minvalue=1, maxvalue=200, initialvalue=3)
            if count is None:
                return
            if self.return_spec:
                self._generate_batch_tasks_spec(count)
            else:
                self._generate_batch_tasks(count)
        except Exception as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")

    def _collect_parameters(self, include_name: bool = True) -> Optional[Dict[str, Any]]:
        """Collect parameter values from UI. Returns dict or None on error."""
        params = {}
        random_cache: Dict[str, Any] = {}

        # Get task name
        task_name = self.param_widgets['name'].get().strip()
        if include_name:
            if not task_name:
                messagebox.showerror("Error", "Task name cannot be empty")
                return None
            params['name'] = task_name

        # Precompute unique random selections when requested
        def _build_random_pool(entity_type: str, available_list: List[Dict[str, Any]], requested: int):
            if requested <= 0 or not available_list:
                return []
            if len(available_list) >= requested:
                return random.sample(available_list, requested)
            # Not enough unique items; allow repeats but keep size
            return [random.choice(available_list) for _ in range(requested)]

        # Count random requests per entity type to enforce uniqueness when possible
        random_counts = {'drone': 0, 'target': 0, 'obstacle': 0}
        for widget in self.param_widgets.values():
            if isinstance(widget, dict) and widget.get('type') == 'entity':
                entity_type = widget.get('entity_type')
                if 'single_var' in widget and widget['single_var'].get().strip() == '[RANDOM]':
                    if entity_type in random_counts:
                        random_counts[entity_type] += 1

        random_pools = {
            'drone': _build_random_pool('drone', self.available_drones, random_counts['drone']),
            'target': _build_random_pool('target', self.available_targets, random_counts['target']),
            'obstacle': _build_random_pool('obstacle', self.available_obstacles, random_counts['obstacle'])
        }

        def _select_ordered(entity_type: str, available_list: List[Dict[str, Any]]):
            if not available_list:
                messagebox.showerror("Error", f"No {entity_type}s available for ordered selection")
                return None
            index = self._ordered_index.get(entity_type, 0) % len(available_list)
            self._ordered_index[entity_type] = (index + 1) % len(available_list)
            return available_list[index]

        def _resolve_random_value(raw_value: Any) -> Optional[Any]:
            """Resolve dynamic random placeholders for template parameters."""
            if not isinstance(raw_value, str):
                return None

            value_str = raw_value.strip()
            if not value_str:
                return None

            # Allow placeholders with or without braces
            placeholder = value_str[1:-1] if value_str.startswith('{') and value_str.endswith('}') else value_str

            # Dynamic random / randint placeholders
            var_name, dynamic_value, is_anonymous = parse_dynamic_random(placeholder)
            if dynamic_value is not None:
                if is_anonymous:
                    return dynamic_value
                if var_name in random_cache:
                    return random_cache[var_name]
                random_cache[var_name] = dynamic_value
                return dynamic_value

            # Predefined random placeholders
            info = get_placeholder_info(placeholder)
            if info and info.get('type') == 'random_float':
                if placeholder not in random_cache:
                    random_cache[placeholder] = generate_random_value(info)
                return random_cache[placeholder]

            return None

        # Get other parameters
        for param_name, widget in self.param_widgets.items():
            if param_name == 'name':
                continue

            if isinstance(widget, dict) and widget.get('type') == 'entity':
                # Handle entity parameter (drone, drone_1, target, target_2, etc.)
                entity_type = widget.get('entity_type')

                if entity_type == 'drone':
                    value = widget['single_var'].get().strip()
                    if value == '[RANDOM]':
                        if self.available_drones:
                            selected_drone = random_pools['drone'].pop() if random_pools['drone'] else random.choice(self.available_drones)
                        else:
                            messagebox.showerror("Error", "No drones available for random selection")
                            return None
                    elif value == '[ORDERED]':
                        selected_drone = _select_ordered('drone', self.available_drones)
                        if selected_drone is None:
                            return None
                    elif ' - ' in value:
                        drone_id = value.split(' - ')[0].strip()
                        selected_drone = next((d for d in self.available_drones if d['id'] == drone_id), None)
                        if not selected_drone:
                            messagebox.showerror("Error", f"Drone {drone_id} not found")
                            return None
                    else:
                        messagebox.showerror("Error", "Invalid drone selection")
                        return None

                    if widget.get('id_param'):
                        params[widget['id_param']] = selected_drone['id']
                    if widget.get('name_param'):
                        params[widget['name_param']] = selected_drone['name']

                elif entity_type == 'target':
                    if 'single_var' in widget:
                        value = widget['single_var'].get().strip()
                        if value == '[RANDOM]':
                            if self.available_targets:
                                selected_target = random_pools['target'].pop() if random_pools['target'] else random.choice(self.available_targets)
                            else:
                                messagebox.showerror("Error", "No targets available for random selection")
                                return None
                        elif value == '[ORDERED]':
                            selected_target = _select_ordered('target', self.available_targets)
                            if selected_target is None:
                                return None
                        elif value in widget.get('options_map', {}):
                            selected_target = widget['options_map'][value]
                        else:
                            target_id = None
                            target_name = None
                            if ' - ' in value:
                                parts = value.split(' - ', 1)
                                target_id = parts[0].strip()
                                target_name = parts[1].strip() if len(parts) > 1 else parts[0].strip()
                            else:
                                target_id = value.strip()
                                target_name = value.strip()

                            selected_target = next((t for t in self.available_targets
                                                    if t.get('id') == target_id or t.get('name') == target_name), None)
                            if not selected_target:
                                selected_target = {'id': target_id, 'name': target_name}

                        if widget.get('id_param'):
                            params[widget['id_param']] = selected_target.get('id') or selected_target.get('name')
                        if widget.get('name_param'):
                            params[widget['name_param']] = selected_target.get('name') or selected_target.get('id')
                    else:
                        value = widget['entry'].get().strip()
                        if value:
                            params[widget['id_param']] = value
                            params[widget['name_param']] = value

                elif entity_type == 'obstacle':
                    if 'single_var' in widget:
                        value = widget['single_var'].get().strip()
                        if value == '[RANDOM]':
                            if self.available_obstacles:
                                selected_obstacle = random_pools['obstacle'].pop() if random_pools['obstacle'] else random.choice(self.available_obstacles)
                            else:
                                messagebox.showerror("Error", "No obstacles available for random selection")
                                return None
                        elif value == '[ORDERED]':
                            selected_obstacle = _select_ordered('obstacle', self.available_obstacles)
                            if selected_obstacle is None:
                                return None
                        elif value in widget.get('options_map', {}):
                            selected_obstacle = widget['options_map'][value]
                        elif ' - ' in value:
                            obstacle_id = value.split(' - ')[0].strip()
                            selected_obstacle = next((o for o in self.available_obstacles if o.get('id') == obstacle_id), None)
                            if not selected_obstacle:
                                selected_obstacle = next((o for o in self.available_obstacles if o.get('name') == obstacle_id), None)
                            if not selected_obstacle:
                                messagebox.showerror("Error", f"Obstacle {obstacle_id} not found")
                                return None
                        else:
                            entered_id = value.strip()
                            selected_obstacle = next((o for o in self.available_obstacles if o.get('id') == entered_id or o.get('name') == entered_id), None)
                            if not selected_obstacle:
                                selected_obstacle = {'id': entered_id, 'name': entered_id}

                        if widget.get('id_param'):
                            params[widget['id_param']] = selected_obstacle.get('id') or selected_obstacle.get('name')
                        if widget.get('name_param'):
                            params[widget['name_param']] = selected_obstacle.get('name') or selected_obstacle.get('id')
                    else:
                        value = widget['entry'].get().strip()
                        if value:
                            if widget.get('id_param'):
                                params[widget['id_param']] = value
                            if widget.get('name_param'):
                                params[widget['name_param']] = value

            elif isinstance(widget, dict) and widget.get('type') == 'numeric':
                if widget['range_var'].get():
                    min_val = float(widget['min_entry'].get().strip())
                    max_val = float(widget['max_entry'].get().strip())
                    if widget.get('param_type') == 'int':
                        value = random.randint(int(min_val), int(max_val))
                    else:
                        value = round(random.uniform(min_val, max_val), 1)
                    params[param_name] = value
                else:
                    value = widget['value_entry'].get().strip()
                    if value:
                        resolved = _resolve_random_value(value)
                        if resolved is not None:
                            params[param_name] = resolved
                        else:
                            try:
                                if '.' in value:
                                    params[param_name] = float(value)
                                else:
                                    params[param_name] = int(value)
                            except ValueError:
                                params[param_name] = value

            elif isinstance(widget, tk.StringVar):
                value = widget.get().strip()
                if value:
                    resolved = _resolve_random_value(value)
                    params[param_name] = resolved if resolved is not None else value

            else:
                value = widget.get().strip()
                if value:
                    resolved = _resolve_random_value(value)
                    if resolved is not None:
                        params[param_name] = resolved
                    else:
                        try:
                            if '.' in value:
                                params[param_name] = float(value)
                            else:
                                params[param_name] = int(value)
                        except ValueError:
                            params[param_name] = value
        
        # Inject available obstacles for collision avoidance in random generation
        if self.available_obstacles:
            params['_context_obstacles'] = self.available_obstacles

        return params

    def _collect_parameter_spec(self, include_name: bool = True) -> Optional[Dict[str, Any]]:
        """Collect raw parameter inputs without resolving entity selections."""
        spec: Dict[str, Any] = {
            'fields': {},
            'entities': []
        }

        task_name = self.param_widgets['name'].get().strip()
        if include_name:
            if not task_name:
                messagebox.showerror("Error", "Task name cannot be empty")
                return None
            spec['name_base'] = task_name

        for param_name, widget in self.param_widgets.items():
            if param_name == 'name':
                continue

            if isinstance(widget, dict) and widget.get('type') == 'entity':
                selection = widget.get('single_var').get().strip() if widget.get('single_var') else ''
                if selection:
                    spec['entities'].append({
                        'param_name': param_name,
                        'entity_type': widget.get('entity_type'),
                        'id_param': widget.get('id_param'),
                        'name_param': widget.get('name_param'),
                        'selection': selection
                    })
                continue

            if isinstance(widget, dict) and widget.get('type') == 'numeric':
                range_on = bool(widget['range_var'].get())
                value = widget['value_entry'].get().strip() if widget.get('value_entry') else ''
                min_val = widget['min_entry'].get().strip() if widget.get('min_entry') else ''
                max_val = widget['max_entry'].get().strip() if widget.get('max_entry') else ''
                if range_on and (not min_val or not max_val):
                    messagebox.showerror("Error", f"Range values required for {param_name}")
                    return None
                if range_on or value:
                    spec['fields'][param_name] = {
                        'kind': 'numeric',
                        'range': range_on,
                        'value': value,
                        'min': min_val,
                        'max': max_val
                    }
                continue

            if isinstance(widget, tk.StringVar):
                value = widget.get().strip()
                if value:
                    spec['fields'][param_name] = {'kind': 'text', 'value': value}
                continue

            value = widget.get().strip()
            if value:
                spec['fields'][param_name] = {'kind': 'text', 'value': value}

        return spec

    def _create_single_task(self):
        """Create a single task (original behavior)"""
        params = self._collect_parameters(include_name=True)
        if params is None:
            return

        # Always use the configured username as the creator for tasks generated from templates
        params['creator'] = self.username
        self.result = params
        self.dialog.destroy()

    def _create_single_task_spec(self):
        """Create a single task spec (raw selection inputs)."""
        spec = self._collect_parameter_spec(include_name=True)
        if spec is None:
            return
        self.result = {'type': 'spec', 'mode': 'single', 'spec': spec}
        self.dialog.destroy()

    def _generate_batch_tasks(self, count: int):
        """Generate multiple tasks with numbered names."""
        if count > 1000:
            if not messagebox.askyesno("Warning", f"You are about to generate {count} tasks. Continue?"):
                return

        base_name = self.param_widgets['name'].get().strip() or self.template_data.get('name', 'Task')
        
        # Generate new names respecting existing tasks
        new_names = create_new_names(base_name, count, self.existing_task_names)
        
        tasks = []

        for i in range(count):
            params = self._collect_parameters(include_name=False)
            if params is None:
                return
            params['name'] = new_names[i]
            params['creator'] = self.username

            if self.template_manager and self.template_id:
                task_data = self.template_manager.instantiate_template(self.template_id, params)
                if task_data:
                    tasks.append(task_data)
            else:
                tasks.append(params)

        self.result = {
            'type': 'batch',
            'tasks': tasks
        }
        self.dialog.destroy()

    def _generate_batch_tasks_spec(self, count: int):
        """Generate a batch spec with numbered names."""
        if count > 100:
            if not messagebox.askyesno("Warning", f"You are about to generate {count} tasks. Continue?"):
                return

        spec = self._collect_parameter_spec(include_name=True)
        if spec is None:
            return

        self.result = {
            'type': 'spec',
            'mode': 'batch',
            'count': count,
            'spec': spec
        }
        self.dialog.destroy()

    def cancel_clicked(self):
        """Handle Cancel button click"""
        self.dialog.destroy()


class TemplateBrowserDialog:
    """Dialog for browsing and selecting task templates"""

    def __init__(self, parent, template_manager: TaskTemplateManager, available_drones: List[Dict[str, Any]] = None,
                 available_targets: List[Dict[str, Any]] = None, available_obstacles: List[Dict[str, Any]] = None,
                 username: str = "SYSTEM", existing_task_names: List[str] = None,
                 select_only: bool = False, current_task_type: Optional[str] = None):
        self.result = None
        self.template_manager = template_manager
        self.available_drones = available_drones or []
        self.available_targets = available_targets or []
        self.available_obstacles = available_obstacles or []
        self.existing_task_names = existing_task_names or []
        self.parent = parent
        self.username = username
        self.select_only = select_only
        self.current_task_type = current_task_type if current_task_type in SUPPORTED_SESSION_TASK_TYPES else None
        self.show_all_templates = tk.BooleanVar(value=True)

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Task Template Browser")
        set_window_geometry_and_center(self.dialog, 980, 680, parent)

        self.create_widgets()
        self.refresh_template_list()
        self.dialog.wait_window()

    def create_widgets(self):
        """Create dialog widgets"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        if self.current_task_type:
            filter_frame = ttk.Frame(main_frame)
            filter_frame.pack(fill=tk.X, pady=(0, 8))
            ttk.Label(
                filter_frame,
                text=f"Session Task Type: {format_task_type_label(self.current_task_type)}",
                foreground='gray'
            ).pack(side=tk.LEFT)
            ttk.Checkbutton(
                filter_frame,
                text="Show all templates",
                variable=self.show_all_templates,
                command=self.refresh_template_list
            ).pack(side=tk.RIGHT)

        # Template list frame
        list_frame = ttk.LabelFrame(main_frame, text="Available Templates", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Treeview for templates
        columns = ('index', 'name', 'category', 'difficulty', 'suitable', 'checks')
        self.template_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        self.template_tree.heading('index', text='#')
        self.template_tree.heading('name', text='Template Name')
        self.template_tree.heading('category', text='Category')
        self.template_tree.heading('difficulty', text='Difficulty')
        self.template_tree.heading('suitable', text='Suitable For')
        self.template_tree.heading('checks', text='Check Count')

        self.template_tree.column('index', width=20, anchor=tk.CENTER)
        self.template_tree.column('name', width=270)
        self.template_tree.column('category', width=150)
        self.template_tree.column('difficulty', width=50)
        self.template_tree.column('suitable', width=190)
        self.template_tree.column('checks', width=50, anchor=tk.CENTER)

        # Scrollbar
        tree_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                       command=self.template_tree.yview)
        self.template_tree.configure(yscrollcommand=tree_scrollbar.set)

        self.template_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind double-click to use template
        self.template_tree.bind('<Double-Button-1>', lambda e: self.use_template())

        # Bind keyboard shortcuts
        self.template_tree.bind('<space>', self._handle_space_key)
        self.template_tree.bind('<Up>', self._navigate_up)
        self.template_tree.bind('<Down>', self._navigate_down)

        # Bind Escape to close dialog
        self.dialog.bind('<Escape>', lambda e: self.close_dialog())
        if platform.system() == 'Darwin':
            self.dialog.bind('<Command-w>', self._handle_close_shortcut)
        else:
            self.dialog.bind('<Control-w>', self._handle_close_shortcut)

        # Description frame (enlarged)
        desc_frame = ttk.LabelFrame(main_frame, text="Template Description & Content", padding="5")
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Scrolled text for description
        desc_scrollbar = ttk.Scrollbar(desc_frame, orient=tk.VERTICAL)
        self.description_text = tk.Text(desc_frame, height=8, wrap=tk.WORD,
                                       yscrollcommand=desc_scrollbar.set)
        desc_scrollbar.config(command=self.description_text.yview)

        self.description_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        desc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind selection change to update description
        self.template_tree.bind('<<TreeviewSelect>>', self.on_template_selected)

        # Buttons - Row 1: Template Management
        mgmt_button_frame = ttk.Frame(main_frame)
        mgmt_button_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(mgmt_button_frame, text="Use Template",
                  command=self.use_template, style='Accent.TButton').pack(side=tk.LEFT, padx=1)
        ttk.Button(mgmt_button_frame, text="New", width=5,
                  command=self.create_new_template).pack(side=tk.LEFT,padx=1)
        ttk.Button(mgmt_button_frame, text="Preview",
                  command=self.view_template_details).pack(side=tk.LEFT, padx=1)
        ttk.Button(mgmt_button_frame, text="Edit", width=5,
                  command=self.edit_template).pack(side=tk.LEFT, padx=1)
        ttk.Button(mgmt_button_frame, text="Duplicate",
                  command=self.duplicate_template).pack(side=tk.LEFT, padx=1)
        ttk.Button(mgmt_button_frame, text="Import",
                  command=self.import_template).pack(side=tk.LEFT, padx=1)
        ttk.Button(mgmt_button_frame, text="Export",
                  command=self.export_template).pack(side=tk.LEFT, padx=1)
        ttk.Button(mgmt_button_frame, text="Delete",
                  command=self.delete_template).pack(side=tk.LEFT, padx=1)
        ttk.Button(mgmt_button_frame, text="Close",
                  command=self.close_dialog).pack(side=tk.RIGHT, padx=1)        

    def _handle_close_shortcut(self, event=None):
        self.close_dialog()
        return "break"

    def refresh_template_list(self):
        """Refresh the template list"""
        previous_selection = self.template_tree.selection()

        # Clear existing items
        for item in self.template_tree.get_children():
            self.template_tree.delete(item)

        # Get all templates
        templates = self.template_manager.get_template_list()

        # Sort by created_at ascending (oldest first)
        templates.sort(key=lambda t: t.get('created_at', 0))

        # Add templates to tree
        row_num = 0
        for template in templates:
            if self.current_task_type and not self.show_all_templates.get():
                if not template_matches_task_type(template, self.current_task_type):
                    continue
            row_num += 1
            self.template_tree.insert('', tk.END,
                                     iid=template['id'],
                                     values=(
                                         row_num,
                                         template['name'],
                                         template.get('category', 'Custom'),
                                         template.get('difficulty', 'medium'),
                                         format_suitable_task_label(template.get('suitable_task', [])),
                                         template.get('check_count', 0)
                                     ))

        if previous_selection:
            template_id = previous_selection[0]
            if self.template_tree.exists(template_id):
                self.template_tree.selection_set(template_id)
                self.template_tree.see(template_id)
                self.on_template_selected()
                return

        self.on_template_selected()

    def on_template_selected(self, event=None):
        """Handle template selection change"""
        selection = self.template_tree.selection()
        if not selection:
            self.description_text.config(state='normal')
            self.description_text.delete('1.0', tk.END)
            self.description_text.config(state='disabled')
            return

        template_id = selection[0]
        template = self.template_manager.get_template(template_id)

        if template:
            # Build comprehensive description
            lines = []

            # Description
            desc = template.get('description', 'No description available')
            lines.append(f"Description: {desc}")
            lines.append("")

            # Task Content
            content = template.get('content', '')
            if content:
                lines.append("Task Content:")
                lines.append(content)
                lines.append("")

            # Content Aliases
            aliases = template.get('content_aliases', [])
            if aliases:
                lines.append(f"Content Aliases ({len(aliases)}):")
                for i, alias in enumerate(aliases[:5], 1):  # Show first 5
                    lines.append(f"  {i}. {alias}")
                if len(aliases) > 5:
                    lines.append(f"  ... and {len(aliases) - 5} more")
                lines.append("")

            # Category and Difficulty
            category = template.get('category', 'N/A')
            difficulty = template.get('difficulty', 'N/A')
            lines.append(f"Category: {category} | Difficulty: {difficulty}")
            lines.append(f"Suitable For: {format_suitable_task_label(template.get('suitable_task', []))}")

            # Creator
            creator = template.get('creator', 'Unknown')
            is_builtin = template.get('is_builtin', False)
            type_str = "Built-in" if is_builtin else "Custom"
            lines.append(f"Type: {type_str} | Creator: {creator}")

            if self.current_task_type and self.show_all_templates.get():
                if not template_matches_task_type(template, self.current_task_type):
                    lines.append("")
                    lines.append(
                        f"Warning: this template is not marked suitable for "
                        f"{format_task_type_label(self.current_task_type)}."
                    )

            # Update text widget
            self.description_text.config(state='normal')
            self.description_text.delete('1.0', tk.END)
            self.description_text.insert('1.0', '\n'.join(lines))
            self.description_text.config(state='disabled')

    def use_template(self):
        """Use selected template to create a task"""
        selection = self.template_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a template")
            return

        template_id = selection[0]
        template = self.template_manager.get_template(template_id)

        if not template:
            messagebox.showerror("Error", "Template not found")
            return

        if self.current_task_type and self.show_all_templates.get():
            if not template_matches_task_type(template, self.current_task_type):
                self.description_text.config(state='normal')
                self.description_text.insert(
                    tk.END,
                    f"\n\nWarning: this template is not marked suitable for "
                    f"{format_task_type_label(self.current_task_type)}."
                )
                self.description_text.config(state='disabled')

        if self.select_only:
            self.result = template_id
            self.dialog.destroy()
            return

        # Open parameter customization dialog
        param_dialog = TemplateParameterDialog(self.dialog, template, self.available_drones,
                                               self.template_manager, template_id,
                                               self.available_targets, self.available_obstacles,
                                               username=self.username,
                                               existing_task_names=self.existing_task_names)

        if param_dialog.result:
            # Check if batch mode
            if isinstance(param_dialog.result, dict) and param_dialog.result.get('type') == 'batch':
                # Batch mode - tasks already instantiated
                self.result = param_dialog.result
                self.dialog.destroy()
            else:
                # Single mode - instantiate template with parameters
                task_data = self.template_manager.instantiate_template(template_id, param_dialog.result)

                if task_data:
                    self.result = task_data
                    self.dialog.destroy()

    def view_template_details(self):
        """View detailed template information"""
        selection = self.template_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a template")
            return

        template_id = selection[0]
        template = self.template_manager.get_template(template_id)

        if not template:
            messagebox.showerror("Error", "Template not found")
            return

        # Create detail dialog
        detail_dialog = tk.Toplevel(self.dialog)
        detail_dialog.title(f"Template Details: {template.get('name', 'Unknown')}")
        set_window_geometry_and_center(detail_dialog, 600, 500, self.dialog)

        # Function to update detail view
        # Defined before detail_panel so we can use it in navigation callbacks
        def update_detail_view():
            current_selection = self.template_tree.selection()
            if current_selection:
                current_template = self.template_manager.get_template(current_selection[0])
                if current_template:
                    detail_dialog.title(f"Template Details: {current_template.get('name', 'Unknown')}")
                    # detail_panel will be available in closure scope when this is called
                    detail_panel.load_data(current_template)

        # Function to navigate and update
        def navigate_prev(event=None):
            self._navigate_up()
            update_detail_view()
            return 'break'

        def navigate_next(event=None):
            self._navigate_down()
            update_detail_view()
            return 'break'

        # Use DetailPanel
        detail_panel = DetailPanel(
            detail_dialog, 
            data=template, 
            view_raw_data_title="Template Raw Data",
            on_close=detail_dialog.destroy,
            on_prev_item=lambda: navigate_prev(),
            on_next_item=lambda: navigate_next()
        )
        detail_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Bind keyboard shortcuts
        detail_dialog.bind('<Escape>', lambda e: detail_dialog.destroy())
        detail_dialog.bind('<space>', lambda e: detail_dialog.destroy())

    def create_new_template(self):
        """Create a new template"""
        # Import here to avoid circular imports
        

        # Open template editor
        editor = TemplateEditor(self.dialog, self.template_manager)

        if editor.result:
            # Refresh template list
            self.refresh_template_list()
            messagebox.showinfo("Success",
                              f"Template '{editor.result['data']['name']}' created successfully!")

    def edit_template(self):
        """Edit selected template"""
        selection = self.template_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a template to edit")
            return

        template_id = selection[0]
        template = self.template_manager.get_template(template_id)

        if not template:
            messagebox.showerror("Error", "Template not found")
            return

        # Check if it's a built-in template
        if template.get('is_builtin', False):
            response = messagebox.askyesno("Built-in Template",
                                          "This is a built-in template. Do you want to create an editable copy instead?")
            if not response:
                return
            # Create a copy for editing
            template = dict(template)
            template['is_builtin'] = False
            template['name'] = template['name'] + ' (Copy)'
            template_id = None  # Force new template

        # Prepare initial data
        initial_data = dict(template)
        if template_id and not template.get('is_builtin', False):
            initial_data['id'] = template_id

        # Open template editor
        editor = TemplateEditor(self.dialog, self.template_manager, initial_data)

        if editor.result:
            self.refresh_template_list()
            messagebox.showinfo("Success",
                              f"Template '{editor.result['data']['name']}' updated successfully!")

    def duplicate_template(self):
        """Duplicate selected template"""
        selection = self.template_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a template to duplicate")
            return

        template_id = selection[0]
        template = self.template_manager.get_template(template_id)

        if not template:
            messagebox.showerror("Error", "Template not found")
            return

        # Create a copy
        import copy
        duplicate_data = copy.deepcopy(template)

        # Ask user for new template name
        default_name = f"{duplicate_data.get('name', 'Template')} (Copy)"
        new_name = simpledialog.askstring(
            "Duplicate Template",
            "Enter a name for the duplicated template:",
            initialvalue=default_name,
            parent=self.dialog
        )
        if not new_name:
            return

        new_name = new_name.strip()
        if not new_name:
            messagebox.showerror("Error", "Template name cannot be empty")
            return

        # Modify for duplication
        duplicate_data['name'] = new_name
        duplicate_data['creator'] = self.username
        duplicate_data['is_builtin'] = False

        # Generate new ID based on name (fallback to original id copy)
        base_id = re.sub(r'[^a-zA-Z0-9_-]+', '_', new_name.strip().lower()).strip('_') or f"{template_id}_copy"
        new_id = base_id
        counter = 1
        while self.template_manager.get_template(new_id):
            new_id = f"{base_id}_{counter}"
            counter += 1

        # Save duplicate
        try:
            success = self.template_manager.add_template(new_id, duplicate_data)
            if success:
                self.refresh_template_list()
                messagebox.showinfo("Success",
                                  f"Template duplicated as '{duplicate_data['name']}'")
                # Select the new template
                self.template_tree.selection_set(new_id)
                self.template_tree.see(new_id)
            else:
                messagebox.showerror("Error", "Failed to duplicate template")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to duplicate template: {str(e)}")

    def export_template(self):
        """Export the selected template to a JSON file."""
        selection = self.template_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a template to export")
            return

        template_id = selection[0]
        template = self.template_manager.get_template(template_id)
        if not template:
            messagebox.showerror("Error", "Template not found")
            return

        default_filename = re.sub(r'[^a-zA-Z0-9_-]+', '_', template.get('name', template_id)).strip('_') or template_id
        filepath = filedialog.asksaveasfilename(
            parent=self.dialog,
            title="Export Template",
            defaultextension=".json",
            initialfile=f"[task template] {default_filename}.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filepath:
            return

        export_payload = {
            'id': template_id,
            'template': template,
        }
        try:
            with open(filepath, 'w', encoding='utf-8') as fh:
                json.dump(export_payload, fh, indent=2, ensure_ascii=False)
            messagebox.showinfo("Success", f"Template exported to:\n{filepath}")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to export template: {exc}")

    def import_template(self):
        """Import a template from a JSON file."""
        filepath = filedialog.askopenfilename(
            parent=self.dialog,
            title="Import Template",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filepath:
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as fh:
                payload = json.load(fh)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to read template file: {exc}")
            return

        if isinstance(payload, dict) and isinstance(payload.get('template'), dict):
            template_data = dict(payload['template'])
            base_id = str(payload.get('id') or '').strip()
        elif isinstance(payload, dict):
            template_data = dict(payload)
            base_id = ''
        else:
            messagebox.showerror("Error", "Invalid template file format.")
            return

        name = str(template_data.get('name') or '').strip()
        if not name:
            messagebox.showerror("Error", "Imported template is missing a name.")
            return

        template_data.pop('created_at', None)
        template_data.pop('last_modified', None)
        template_data['is_builtin'] = False
        template_data['creator'] = self.username

        if not base_id:
            base_id = re.sub(r'[^a-zA-Z0-9_-]+', '_', name.lower()).strip('_') or "imported_template"
        template_id = base_id
        counter = 1
        while self.template_manager.get_template(template_id):
            template_id = f"{base_id}_{counter}"
            counter += 1

        try:
            success = self.template_manager.add_template(template_id, template_data)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to import template: {exc}")
            return

        if not success:
            messagebox.showerror("Error", "Failed to import template.")
            return

        self.refresh_template_list()
        if self.template_tree.exists(template_id):
            self.template_tree.selection_set(template_id)
            self.template_tree.see(template_id)
            self.on_template_selected()
        messagebox.showinfo("Success", f"Template '{name}' imported successfully.")

    def delete_template(self):
        """Delete selected template"""
        selection = self.template_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a template to delete")
            return

        template_id = selection[0]
        template = self.template_manager.get_template(template_id)

        if not template:
            messagebox.showerror("Error", "Template not found")
            return

        # Check if it's a built-in template
        if template.get('is_builtin', False):
            messagebox.showerror("Cannot Delete",
                               "Built-in templates cannot be deleted.\n\n"
                               "You can duplicate it and modify the copy instead.")
            return

        # Confirm deletion
        response = messagebox.askyesno("Confirm Delete",
                                      f"Are you sure you want to delete the template:\n\n"
                                      f"'{template['name']}'?\n\n"
                                      f"This action cannot be undone.")

        if not response:
            return

        # Delete template
        try:
            success = self.template_manager.delete_template(template_id)
            if success:
                self.refresh_template_list()
                messagebox.showinfo("Success",
                                  f"Template '{template['name']}' deleted successfully")
            else:
                messagebox.showerror("Error", "Failed to delete template")
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete template: {str(e)}")

    def close_dialog(self):
        """Close dialog without selection"""
        self.dialog.destroy()

    def _handle_space_key(self, event=None):
        """Handle space key press to view template details"""
        self.view_template_details()
        return 'break'  # Prevent event propagation

    def _navigate_up(self, event=None):
        """Navigate to previous template"""
        current_selection = self.template_tree.selection()
        if not current_selection:
            # Select first item if nothing selected
            items = self.template_tree.get_children()
            if items:
                self.template_tree.selection_set(items[0])
                self.template_tree.focus(items[0])
                self.template_tree.see(items[0])
                self.on_template_selected()
            return 'break'

        current_item = current_selection[0]
        prev_item = self.template_tree.prev(current_item)

        if prev_item:
            self.template_tree.selection_set(prev_item)
            self.template_tree.focus(prev_item)
            self.template_tree.see(prev_item)
            self.on_template_selected()

        return 'break'

    def _navigate_down(self, event=None):
        """Navigate to next template"""
        current_selection = self.template_tree.selection()
        if not current_selection:
            # Select first item if nothing selected
            items = self.template_tree.get_children()
            if items:
                self.template_tree.selection_set(items[0])
                self.template_tree.focus(items[0])
                self.template_tree.see(items[0])
                self.on_template_selected()
            return 'break'

        current_item = current_selection[0]
        next_item = self.template_tree.next(current_item)

        if next_item:
            self.template_tree.selection_set(next_item)
            self.template_tree.focus(next_item)
            self.template_tree.see(next_item)
            self.on_template_selected()

        return 'break'
