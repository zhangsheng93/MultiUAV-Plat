#!/usr/bin/env python3
"""
Template Editor with Placeholder Support

Features:
- Easy placeholder insertion via buttons
- Placeholder browser/selector
- Real-time placeholder validation
- Preview with sample values
- Comprehensive placeholder documentation
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, Any, Optional, List
import json
import copy
from app_settings import get_settings
from task_template_manager import TEMPLATE_SUITABLE_TASK_TYPES
from utils import set_window_geometry_and_center, create_new_name
from template_placeholders import (
    PLACEHOLDER_DEFINITIONS,
    get_placeholder_categories,
    get_placeholder_info,
    find_placeholders_in_text,
    substitute_placeholders,
    get_missing_placeholders,
    generate_example_content,
    generate_example_alias,
    create_placeholder_help_text,
    parse_dynamic_random
)


def normalize_expect_value(expect_val: Any) -> Optional[bool]:
    """
    Convert expect values to booleans when possible.
    - Booleans pass through.
    - Legacy dicts with a 'result' key collapse to that value.
    - Strings 'true'/'false' (case-insensitive) convert accordingly.
    Returns None if the value cannot be interpreted as a boolean.
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


class PlaceholderSelectorDialog:
    """Dialog for selecting and inserting placeholders"""

    def __init__(self, parent):
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Insert Placeholder")
        set_window_geometry_and_center(self.dialog, 900, 600, parent)

        self.create_widgets()
        self.dialog.wait_window()

    def create_widgets(self):
        """Create dialog widgets"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(main_frame, text="Select Placeholder to Insert",
                 font=('Arial', 12, 'bold')).pack(pady=(0, 5))

        # Categories
        categories = get_placeholder_categories()

        # Notebook for categories
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        for category, placeholders in sorted(categories.items()):
            # Create tab for each category
            tab = ttk.Frame(notebook)
            notebook.add(tab, text=category)

            # Scrollable frame for placeholders
            canvas = tk.Canvas(tab, highlightthickness=0)
            scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
            canvas.configure(yscrollcommand=scrollbar.set)

            # Add placeholder buttons in a grid (3 per row)
            cols = 3
            for idx, placeholder in enumerate(sorted(placeholders)):
                info = PLACEHOLDER_DEFINITIONS[placeholder]
                row = idx // cols
                col = idx % cols
                self.create_placeholder_button(scrollable_frame, placeholder, info, row, col)

            for col in range(cols):
                scrollable_frame.columnconfigure(col, weight=1, uniform="placeholder_cols")

            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=5)

    def create_placeholder_button(self, parent, placeholder: str, info: Dict[str, Any], row: int, col: int):
        """Create a button for a placeholder"""
        frame = ttk.Frame(parent, padding=6)
        frame.grid(row=row, column=col, sticky="nwe")

        # Button to insert placeholder
        button = ttk.Button(frame, text=f"{{{placeholder}}}",
                           command=lambda: self.select_placeholder(placeholder),
                           width=24)
        button.pack(fill=tk.X, padx=2, pady=(0, 4))

        # Description and example
        ttk.Label(
            frame,
            text=info['description'],
            font=('Arial', 12),
            wraplength=360,
            justify=tk.LEFT
        ).pack(fill=tk.X, anchor=tk.W)
        ttk.Label(
            frame,
            text=f"Example: {info['example']}",
            font=('Arial', 11),
            foreground='gray',
            wraplength=360,
            justify=tk.LEFT
        ).pack(fill=tk.X, anchor=tk.W)

    def select_placeholder(self, placeholder: str):
        """Select a placeholder"""
        self.result = placeholder
        self.dialog.destroy()

    def cancel(self):
        """Cancel selection"""
        self.dialog.destroy()


class TemplateEditor:
    """Template editor with placeholder support"""

    def __init__(self, parent, template_manager, initial_data: Optional[Dict[str, Any]] = None):
        self.result = None
        self.template_manager = template_manager
        self.initial_data = initial_data or {}
        self.edit_mode = bool(initial_data and initial_data.get('id'))
        self.app_settings = get_settings()
        self.username = self.app_settings.get('username', 'SYSTEM')
        self.execution_check_data = None
        self.execution_check_node_map = {}

        self.dialog = tk.Toplevel(parent)
        dialog_title = "Task Template Editor - Edit Template" if self.edit_mode else "Task Template Editor - Create New Template"
        self.dialog.title(dialog_title)
        set_window_geometry_and_center(self.dialog, 1120, 900, parent)

        self.create_widgets()
        self.dialog.wait_window()

    def create_widgets(self):
        """Create dialog widgets"""
        text_font = ('Courier New', 13)
        # Main container with two columns
        main_container = ttk.Frame(self.dialog)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel - Editor
        left_panel = ttk.Frame(main_container)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Right panel - Helpers
        right_panel = ttk.Frame(main_container, width=240)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        right_panel.pack_propagate(False)

        # === LEFT PANEL: Editor ===
        self.create_editor_panel(left_panel, text_font)

        # === RIGHT PANEL: Helpers ===
        self.create_helper_panel(right_panel)

        # === BOTTOM: Buttons ===
        self.create_button_panel()

    def create_editor_panel(self, parent, text_font):
        """Create the main editor panel"""

        # Scrollable content
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        row = 0

        # Template Name
        ttk.Label(scrollable_frame, text="Template Name:*", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(scrollable_frame, width=55)
        initial_name = self.initial_data.get('name') if self.edit_mode else (self.initial_data.get('name') or self._generate_default_name())
        self.name_entry.insert(0, initial_name or '')
        self.name_entry.grid(row=row, column=1, pady=5, sticky=tk.W)
        row += 1

        # Category and Difficulty
        ttk.Label(scrollable_frame, text="Category:").grid(row=row, column=0, sticky=tk.W, pady=5)
        inline_frame = ttk.Frame(scrollable_frame)
        inline_frame.grid(row=row, column=1, pady=5, sticky=tk.W, columnspan=3)

        self.category_var = tk.StringVar(value=self.initial_data.get('category', 'Custom'))
        ttk.Combobox(
            inline_frame,
            textvariable=self.category_var,
            values=['Basic Operations', 'Patrol', 'Search', 'Delivery', 'Search', 'Emergency', 'Custom'],
            width=30
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(inline_frame, text="Difficulty:").pack(side=tk.LEFT, padx=(20, 4))
        self.difficulty_var = tk.StringVar(value=self.initial_data.get('difficulty', 'easy'))
        ttk.Combobox(
            inline_frame,
            textvariable=self.difficulty_var,
            values=['easy', 'medium', 'hard'],
            state='readonly',
            width=14
        ).pack(side=tk.LEFT)
        row += 1

        ttk.Label(scrollable_frame, text="Suitable Tasks:").grid(
            row=row, column=0, sticky=tk.NW, pady=5
        )
        suitable_frame = ttk.Frame(scrollable_frame)
        suitable_frame.grid(row=row, column=1, pady=5, sticky=tk.W)

        initial_suitable = set(self.initial_data.get('suitable_task', []) or [])
        self.suitable_task_vars: Dict[str, tk.BooleanVar] = {}
        suitable_cols = 3
        for idx, task_type in enumerate(TEMPLATE_SUITABLE_TASK_TYPES):
            row_idx = idx // suitable_cols
            col_idx = idx % suitable_cols
            label = "All" if task_type == 'all' else task_type.replace('_', ' ').title()
            var = tk.BooleanVar(value=task_type in initial_suitable)
            ttk.Checkbutton(
                suitable_frame,
                text=label,
                variable=var
            ).grid(row=row_idx, column=col_idx, sticky=tk.W, padx=(0, 12), pady=2)
            self.suitable_task_vars[task_type] = var
        ttk.Label(
            suitable_frame,
            text="Select All for every session task type, or leave all unchecked for backward-compatible all-task behavior.",
            foreground='gray'
        ).grid(
            row=(len(TEMPLATE_SUITABLE_TASK_TYPES) + suitable_cols - 1) // suitable_cols,
            column=0,
            columnspan=suitable_cols,
            sticky=tk.W,
            pady=(4, 0)
        )
        row += 1

        self.exclude_in_random_generation_var = tk.BooleanVar(
            value=bool(self.initial_data.get('exclude_in_random_generation', False))
        )
        ttk.Checkbutton(
            scrollable_frame,
            text="Exclude from random generation",
            variable=self.exclude_in_random_generation_var
        ).grid(row=row, column=1, sticky=tk.W, pady=(0, 5))
        row += 1

        text_input_width = 80
        

        # Content with placeholder insertion
        content_label_frame = ttk.Frame(scrollable_frame)
        content_label_frame.grid(row=row, column=0, sticky=tk.NW, pady=5)
        ttk.Label(content_label_frame, text="Content:*", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        placeholder_btn_width = 9
        placeholder_btn_padding = -8
        ttk.Button(content_label_frame, text="+Placeholder",
                  command=lambda: self.insert_placeholder(self.content_text),
                  width=placeholder_btn_width, padding=placeholder_btn_padding).pack(anchor=tk.W, pady=1)

        self.content_text = tk.Text(scrollable_frame, width=text_input_width, height=8, font=text_font, wrap="word")
        self.content_text.insert('1.0', self.initial_data.get('content', ''))
        self.content_text.grid(row=row, column=1, pady=5, sticky=tk.W)
        row += 1

        # Content Aliases with placeholder insertion
        aliases_label_frame = ttk.Frame(scrollable_frame)
        aliases_label_frame.grid(row=row, column=0, sticky=tk.NW, pady=5)
        ttk.Label(aliases_label_frame, text="Aliases:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        ttk.Button(aliases_label_frame, text="+Placeholder",
                  command=lambda: self.insert_placeholder(self.aliases_text),
                  width=placeholder_btn_width, padding=placeholder_btn_padding).pack(anchor=tk.W, pady=1)
        ttk.Button(aliases_label_frame, text="Example",
                  command=self.insert_example_aliases,
                  width=placeholder_btn_width, padding=placeholder_btn_padding).pack(anchor=tk.W, pady=1)

        self.aliases_text = tk.Text(scrollable_frame, width=text_input_width, height=8, wrap="word", font=text_font)
        aliases = self.initial_data.get('content_aliases', [])
        if aliases:
            self.aliases_text.insert('1.0', '\n'.join(aliases))
        self.aliases_text.grid(row=row, column=1, pady=5, sticky=tk.W)
        row += 1

        # Description
        ttk.Label(scrollable_frame, text="Description:").grid(row=row, column=0, sticky=tk.NW, pady=5)
        self.description_text = tk.Text(scrollable_frame, width=text_input_width, height=2, font=text_font, wrap="word")
        self.description_text.insert('1.0', self.initial_data.get('description', ''))
        self.description_text.grid(row=row, column=1, pady=5, sticky=tk.W)
        row += 1

        # Related APIs section
        apis_label_frame = ttk.Frame(scrollable_frame)
        apis_label_frame.grid(row=row, column=0, sticky=tk.NW, pady=5)
        ttk.Label(apis_label_frame, text="Related APIs:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        api_actions = ttk.Frame(apis_label_frame)
        api_actions.pack(anchor=tk.W)
        ttk.Button(api_actions, text="Add", width=placeholder_btn_width, padding=placeholder_btn_padding, command=self.add_api).pack(fill=tk.X, pady=1)
        ttk.Button(api_actions, text="Edit", width=placeholder_btn_width, padding=placeholder_btn_padding, command=self.edit_api).pack(fill=tk.X, pady=1)
        ttk.Button(api_actions, text="Duplicate", width=placeholder_btn_width, padding=placeholder_btn_padding, command=self.duplicate_api).pack(fill=tk.X, pady=1)
        ttk.Button(api_actions, text="Remove", width=placeholder_btn_width, padding=placeholder_btn_padding, command=self.delete_api).pack(fill=tk.X, pady=1)
        ttk.Button(api_actions, text="↑", width=placeholder_btn_width, padding=placeholder_btn_padding, command=lambda: self.move_api(-1)).pack(fill=tk.X, pady=1)
        ttk.Button(api_actions, text="↓", width=placeholder_btn_width, padding=placeholder_btn_padding, command=lambda: self.move_api(1)).pack(fill=tk.X, pady=1)

        api_tree_frame = ttk.Frame(scrollable_frame)
        api_tree_frame.grid(row=row, column=1, pady=5, sticky=tk.W)

        api_columns = ('endpoint', 'parameters')
        self.api_tree = ttk.Treeview(api_tree_frame, columns=api_columns, show='tree headings', height=8)
        self.api_tree.heading('endpoint', text='API Endpoint')
        self.api_tree.heading('parameters', text='Parameters')
        self.api_tree.column('#0', width=30, stretch=False)
        self.api_tree.column('endpoint', width=300, stretch=False)
        self.api_tree.column('parameters', width=320, stretch=False)

        api_tree_scroll = ttk.Scrollbar(api_tree_frame, orient=tk.VERTICAL, command=self.api_tree.yview)
        self.api_tree.configure(yscrollcommand=api_tree_scroll.set)
        self.api_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        api_tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.related_apis = list(self.initial_data.get('related_apis', []))
        self._refresh_api_tree()
        row += 1

        # Execution Check APIs section
        checks_label_frame = ttk.Frame(scrollable_frame)
        checks_label_frame.grid(row=row, column=0, sticky=tk.NW, pady=5)
        ttk.Label(checks_label_frame, text="Execution Check APIs:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        controls = ttk.Frame(checks_label_frame)
        controls.pack(anchor=tk.W, pady=(2, 0))
        for text, cmd in [
            ("+Check", self.add_execution_check),
            ("+Group", self.add_execution_group),
            ("Edit", self.edit_execution_node),
            ("Remove", self.remove_execution_node),
            ("↑", lambda: self.move_execution_node(-1)),
            ("↓", lambda: self.move_execution_node(1)),
        ]:
            ttk.Button(controls, text=text, command=cmd, width=placeholder_btn_width, padding=placeholder_btn_padding).pack(fill=tk.X, pady=1)

        self.execution_check_data = self._initialize_execution_check_data(self.initial_data.get('execution_check_apis'))

        self.execution_checks_frame = ttk.Frame(scrollable_frame)
        self.execution_checks_frame.grid(row=row, column=1, pady=5, sticky=tk.W)

        # Inline execution check tree creation (previously _build_execution_checks_view)
        for widget in self.execution_checks_frame.winfo_children():
            widget.destroy()

        tree_frame = ttk.Frame(self.execution_checks_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('logic', 'endpoint', 'parameters')
        tree_holder = ttk.Frame(tree_frame)
        tree_holder.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.execution_check_tree = ttk.Treeview(
            tree_holder,
            columns=columns,
            show='tree headings',
            height=10
        )
        self.execution_check_tree.heading('logic', text='Logic')
        self.execution_check_tree.heading('endpoint', text='Endpoint')
        self.execution_check_tree.heading('parameters', text='Parameters')
        self.execution_check_tree.column('#0', width=60, stretch=False)
        self.execution_check_tree.column('logic', width=70, stretch=False)
        self.execution_check_tree.column('endpoint', width=260, stretch=False)
        self.execution_check_tree.column('parameters', width=260, stretch=False)

        scrollbar = ttk.Scrollbar(tree_holder, orient=tk.VERTICAL, command=self.execution_check_tree.yview)
        self.execution_check_tree.configure(yscrollcommand=scrollbar.set)
        self.execution_check_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._refresh_execution_check_tree()
        row += 1

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def create_helper_panel(self, parent):
        """Create the helper panel with placeholder info and preview"""
        # Placeholders detected
        detect_frame = ttk.LabelFrame(parent, text="Detected Placeholders", padding="5")
        detect_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(detect_frame, text="🔍 Detect & Validate",
                  command=self.detect_placeholders).pack(fill=tk.X)

        self.detected_text = scrolledtext.ScrolledText(detect_frame, width=25, height=20,
                                                       font=('Courier', 9))
        self.detected_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # Quick insert buttons
        quick_frame = ttk.LabelFrame(parent, text="Quick Insert", padding="5")
        quick_frame.pack(fill=tk.X, pady=(0, 10))

        common_placeholders = [
            ('drone_id', 'Drone ID'),
            ('altitude', 'Altitude'),
            ('position_x', 'X'),
            ('position_y', 'Y'),
            ('position_z', 'Z'),
        ]

        for placeholder, label in common_placeholders:
            ttk.Button(quick_frame, text=label,
                      command=lambda p=placeholder: self.quick_insert_placeholder(p)).pack(fill=tk.X, pady=1)

        ttk.Button(quick_frame, text="📋 Browse All...",
                  command=self.browse_placeholders).pack(fill=tk.X, pady=(5, 0))

        # Help
        help_frame = ttk.LabelFrame(parent, text="Help", padding="5")
        help_frame.pack(fill=tk.BOTH, expand=True)

        help_text = (
            "Tips:\n"
            "- Use {_id}/{_name} pairs for entities (drone/target/obstacle, indexed works too).\n"
            "- Randoms: predefined (e.g., {random_altitude}) are sticky; "
            "dynamic {random:min:max} / {randint:min:max} re-roll each occurrence; "
            "named {random_var:min:max} sticks per task.\n"
            "- Reuse the same placeholder everywhere you need the same value."
        )
        ttk.Label(help_frame, text=help_text, wraplength=230,
                 font=('Arial', 12), foreground='gray', justify=tk.LEFT).pack()

    def create_button_panel(self):
        """Create bottom button panel"""
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        save_text = "Update Template" if self.edit_mode else "Create Template"
        ttk.Button(button_frame, text=save_text, command=self.save_template).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Preview", command=self.preview_template).pack(side=tk.RIGHT, padx=5)

    def insert_placeholder(self, text_widget: tk.Text):
        """Insert placeholder at cursor position in text widget"""
        dialog = PlaceholderSelectorDialog(self.dialog)
        if dialog.result:
            placeholder = f"{{{dialog.result}}}"
            try:
                text_widget.insert(tk.INSERT, placeholder)
            except:
                text_widget.insert(tk.END, placeholder)

    def quick_insert_placeholder(self, placeholder: str):
        """Quick insert placeholder into content"""
        placeholder_str = f"{{{placeholder}}}"
        try:
            self.content_text.insert(tk.INSERT, placeholder_str)
        except:
            self.content_text.insert(tk.END, placeholder_str)

    def browse_placeholders(self):
        """Show placeholder browser"""
        help_dialog = tk.Toplevel(self.dialog)
        help_dialog.title("Placeholder Reference")
        set_window_geometry_and_center(help_dialog, 700, 600, self.dialog)

        frame = ttk.Frame(help_dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        text_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=('Courier', 9))
        text_widget.pack(fill=tk.BOTH, expand=True)

        text_widget.insert('1.0', create_placeholder_help_text())
        text_widget.config(state='disabled')

        ttk.Button(frame, text="Close", command=help_dialog.destroy).pack(pady=5)

    def insert_example_aliases(self):
        """Insert example aliases"""
        examples = generate_example_alias()
        current = self.aliases_text.get('1.0', tk.END).strip()
        if current:
            self.aliases_text.insert(tk.END, '\n' + '\n'.join(examples))
        else:
            self.aliases_text.insert('1.0', '\n'.join(examples))

    def detect_placeholders(self):
        """Detect and validate placeholders in content and aliases"""
        self.detected_text.delete('1.0', tk.END)

        # Get content
        content = self.content_text.get('1.0', tk.END).strip()
        aliases_text = self.aliases_text.get('1.0', tk.END).strip()

        # Find placeholders
        content_placeholders = find_placeholders_in_text(content)
        alias_placeholders = find_placeholders_in_text(aliases_text)

        all_placeholders = list(set(content_placeholders + alias_placeholders))

        if not all_placeholders:
            self.detected_text.insert('1.0', "No placeholders detected.\n\nClick '+ Placeholder' to add some!")
            return

        self.detected_text.insert('1.0', f"Found {len(all_placeholders)} placeholder(s):\n\n")

        for placeholder in sorted(all_placeholders):
            info = get_placeholder_info(placeholder)
            if info:
                self.detected_text.insert(tk.END, f"✓ {{{placeholder}}}\n", 'valid')
                self.detected_text.insert(tk.END, f"  {info['description']}\n\n", 'info')
            else:
                var_name, dynamic_value, is_anonymous = parse_dynamic_random(placeholder)
                if dynamic_value is not None:
                    # Valid dynamic random placeholder
                    if is_anonymous:
                        desc = "Dynamic random number (anonymous) - each occurrence gets a fresh value."
                    else:
                        desc = f"Dynamic random number (named '{var_name}') - first occurrence is reused everywhere."
                    self.detected_text.insert(tk.END, f"✓ {{{placeholder}}}\n", 'valid')
                    self.detected_text.insert(tk.END, f"  {desc}\n\n", 'info')
                else:
                    self.detected_text.insert(tk.END, f"✗ {{{placeholder}}}\n", 'invalid')
                    self.detected_text.insert(tk.END, f"  Unknown placeholder!\n\n", 'error')

        # Configure tags
        self.detected_text.tag_config('valid', foreground='green')
        self.detected_text.tag_config('invalid', foreground='red')
        self.detected_text.tag_config('info', foreground='gray')
        self.detected_text.tag_config('error', foreground='red')

    def _refresh_api_tree(self):
        """Refresh the Treeview for related APIs."""
        if not hasattr(self, 'api_tree'):
            return

        for item in self.api_tree.get_children():
            self.api_tree.delete(item)

        for idx, api in enumerate(self.related_apis):
            endpoint = api.get('endpoint', '')
            params = api.get('parameters', {})
            param_str = ', '.join([f"{k}={v}" for k, v in params.items() if v is not None])
            if not param_str:
                param_str = "(no parameters)"
            self.api_tree.insert('', tk.END, text=str(idx + 1), values=(endpoint, param_str))

    def _get_selected_api_index(self) -> Optional[int]:
        if not hasattr(self, 'api_tree'):
            return None
        selection = self.api_tree.selection()
        if not selection:
            return None
        item = selection[0]
        try:
            return int(self.api_tree.item(item, 'text')) - 1
        except (ValueError, TypeError):
            return None

    def add_api(self):
        """Add a new API to related_apis"""
        from api_definitions import get_api_by_category
        from task_dialog import AddAPIDialog

        api_categories = get_api_by_category()
        dialog = AddAPIDialog(self.dialog, api_categories, template_mode=True)
        if dialog.result:
            self.related_apis.append(dialog.result)
            self._refresh_api_tree()

    def edit_api(self):
        """Edit selected API"""
        from api_definitions import get_api_by_category
        from task_dialog import AddAPIDialog

        index = self._get_selected_api_index()
        if index is None or not (0 <= index < len(self.related_apis)):
            messagebox.showwarning("No Selection", "Please select an API to edit")
            return

        api_categories = get_api_by_category()
        dialog = AddAPIDialog(self.dialog, api_categories, edit_data=self.related_apis[index], template_mode=True)
        if dialog.result:
            self.related_apis[index] = dialog.result
            self._refresh_api_tree()

    def duplicate_api(self):
        """Duplicate selected API"""
        index = self._get_selected_api_index()
        if index is None or not (0 <= index < len(self.related_apis)):
            messagebox.showwarning("No Selection", "Please select an API to duplicate")
            return

        self.related_apis.append(copy.deepcopy(self.related_apis[index]))
        self._refresh_api_tree()
        children = self.api_tree.get_children()
        if children:
            self.api_tree.selection_set(children[-1])
            self.api_tree.see(children[-1])

    def delete_api(self):
        """Delete selected API from related_apis"""
        index = self._get_selected_api_index()
        if index is None or not (0 <= index < len(self.related_apis)):
            messagebox.showwarning("No Selection", "Please select an API to delete")
            return

        api = self.related_apis[index]
        api_display = f"{api.get('method', 'GET')} {api.get('path', '')}"

        if messagebox.askyesno("Confirm Delete", f"Delete this API?\n\n{api_display}"):
            self.related_apis.pop(index)
            self._refresh_api_tree()

    def move_api(self, direction: int):
        """Move selected API up (-1) or down (+1)."""
        index = self._get_selected_api_index()
        if index is None:
            return
        new_index = index + direction
        if 0 <= new_index < len(self.related_apis):
            self.related_apis[index], self.related_apis[new_index] = self.related_apis[new_index], self.related_apis[index]
            self._refresh_api_tree()
            children = self.api_tree.get_children()
            if 0 <= new_index < len(children):
                self.api_tree.selection_set(children[new_index])
                self.api_tree.see(children[new_index])

    def _initialize_execution_check_data(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Normalize execution_check_apis data for the editor."""
        if not data or not isinstance(data, dict):
            return {"logic": "and", "checks": []}

        logic = str(data.get('logic', 'and')).lower()
        normalized_checks = []
        for child in data.get('checks', []) or []:
            normalized = self._normalize_execution_check_node(child)
            if normalized:
                normalized_checks.append(normalized)

        return {"logic": logic, "checks": normalized_checks}

    def _normalize_execution_check_node(self, node: Any) -> Optional[Dict[str, Any]]:
        """Normalize a single execution check node (group or leaf)."""
        if not isinstance(node, dict):
            return None

        if 'checks' in node:
            return {
                "logic": str(node.get('logic', 'and')).lower(),
                "checks": [normalized for normalized in (self._normalize_execution_check_node(child) for child in node.get('checks', [])) if normalized]
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
            values=(root_logic.upper(), '', ''),
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
        param_str = ', '.join([f"{k}={v}" for k, v in params.items() if v is not None])
        if not param_str and not is_group:
            param_str = "(no parameters)"

        item_id = self.execution_check_tree.insert(
            parent_item,
            tk.END,
            text="Group" if is_group else "Check",
            values=(logic, endpoint, param_str),
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

    def _generate_default_name(self) -> str:
        """Generate an auto-incrementing default template name."""
        base = "New Task Template"
        try:
            existing = [t.get('name', '') for t in self.template_manager.get_template_list()]
        except Exception:
            existing = []

        return create_new_name(base, exist_list=existing)

    def add_execution_group(self):
        target_checks = self._get_target_check_list()
        target_checks.append({"logic": "and", "checks": []})
        self._refresh_execution_check_tree()

    def _get_target_check_list(self) -> List[Dict[str, Any]]:
        context = self._get_selected_execution_node()
        if not context:
            return self.execution_check_data['checks']
        node = context['node']
        if node and 'checks' in node:
            return node['checks']
        return context.get('parent_checks') or self.execution_check_data['checks']

    def add_execution_check(self):
        from api_definitions import get_check_api_by_category
        from task_dialog import ExecutionCheckAPIDialog

        api_categories = get_check_api_by_category()
        dialog = ExecutionCheckAPIDialog(self.dialog, api_categories, template_mode=True)
        if dialog.result:
            target_checks = self._get_target_check_list()
            target_checks.append(dialog.result)
            self._refresh_execution_check_tree()

    def edit_execution_node(self):
        from api_definitions import get_check_api_by_category
        from task_dialog import ExecutionCheckAPIDialog

        context = self._get_selected_execution_node()
        if not context:
            messagebox.showwarning("No Selection", "Please select a group or check to edit")
            return

        node = context['node']
        if node is self.execution_check_data:
            self._prompt_logic_change(node)
            return

        if 'checks' in node:
            self._prompt_logic_change(node)
        else:
            parent_checks = context.get('parent_checks') or self.execution_check_data['checks']
            try:
                index = parent_checks.index(node)
            except ValueError:
                index = None

            api_categories = get_check_api_by_category()
            dialog = ExecutionCheckAPIDialog(self.dialog, api_categories, edit_data=node, template_mode=True)
            if dialog.result and index is not None:
                parent_checks[index] = dialog.result
                self._refresh_execution_check_tree()

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
            "parameters": node.get('parameters', {}) or {}
        }
        expect_val = normalize_expect_value(node.get('expect'))
        if expect_val is not None:
            cleaned['expect'] = expect_val
        return cleaned

    def preview_template(self):
        """Preview template with sample values"""
        # Sample values
        sample_values = {
            'drone_id': 'drone-001',
            'altitude': '15.0',
            'position_x': '100.0',
            'position_y': '150.0',
            'position_z': '20.0',
            'distance': '50.0',
            'heading': '90.0',
            'hover_time': '5.0',
        }

        content = self.content_text.get('1.0', tk.END).strip()
        aliases_text = self.aliases_text.get('1.0', tk.END).strip()

        # Substitute with sticky random values
        random_cache = {}
        preview_content, random_cache = substitute_placeholders(content, sample_values, random_cache)
        preview_aliases = []
        for line in aliases_text.split('\n'):
            if line.strip():
                substituted, random_cache = substitute_placeholders(line, sample_values, random_cache)
                preview_aliases.append(substituted)

        # Show preview
        preview_dialog = tk.Toplevel(self.dialog)
        preview_dialog.title("Template Preview")
        set_window_geometry_and_center(preview_dialog, 600, 400, self.dialog)

        frame = ttk.Frame(preview_dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Preview with Sample Values", font=('Arial', 12, 'bold')).pack(pady=(0, 10))

        text_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True)

        text_widget.insert('1.0', "CONTENT:\n")
        text_widget.insert(tk.END, preview_content + "\n\n")
        text_widget.insert(tk.END, "ALIASES:\n")
        for i, alias in enumerate(preview_aliases, 1):
            text_widget.insert(tk.END, f"{i}. {alias}\n")

        text_widget.config(state='disabled')

        close_button = ttk.Button(frame, text="Close", command=lambda d=preview_dialog: d.destroy())
        close_button.pack(pady=5)
        preview_dialog.protocol("WM_DELETE_WINDOW", close_button.invoke)

    def save_template(self):
        """Save the template"""
        try:
            # Validate
            name = self.name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Template name is required")
                return

            content = self.content_text.get('1.0', tk.END).strip()
            if not content:
                messagebox.showerror("Error", "Content is required")
                return

            # Parse aliases
            aliases_text = self.aliases_text.get('1.0', tk.END).strip()
            aliases = [line.strip() for line in aliases_text.split('\n') if line.strip()]

            # Generate template ID
            if self.edit_mode:
                template_id = self.initial_data.get('id', '')
            else:
                template_id = name.lower().replace(' ', '_').replace('-', '_')
                counter = 1
                base_id = template_id
                while self.template_manager.get_template(template_id):
                    template_id = f"{base_id}_{counter}"
                    counter += 1

            # Build template
            template_data = {
                'name': name,
                'description': self.description_text.get('1.0', tk.END).strip(),
                'content': content,
                'content_aliases': aliases,
                'suitable_task': [
                    task_type for task_type, var in self.suitable_task_vars.items()
                    if var.get()
                ],
                'difficulty': self.difficulty_var.get(),
                'creator': self.username,
                'category': self.category_var.get(),
                'is_builtin': False,
                'exclude_in_random_generation': bool(self.exclude_in_random_generation_var.get()),
                'related_apis': self.related_apis,  # Use the managed list
                'execution_check_apis': self._build_execution_check_result(self.execution_check_data),
                'commands': self.initial_data.get('commands', [])
            }

            # Save
            success = self.template_manager.add_template(template_id, template_data)

            if success:
                self.result = {'id': template_id, 'data': template_data}
                messagebox.showinfo("Success", f"Template '{name}' saved successfully!")
                self.dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to save template")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save template: {str(e)}")

    def cancel(self):
        """Cancel and close"""
        self.dialog.destroy()
