#!/usr/bin/env python3
"""
Standalone GUI tool for creating tasks from templates across multiple sessions.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Dict, Any, List, Optional, Tuple
import sys
import random
from datetime import datetime

from api_server import APIServer
from app_settings import get_settings
from task_template_manager import TaskTemplateManager
from task_template_dialog import TemplateBrowserDialog, TemplateParameterDialog
from template_placeholders import get_placeholder_info, generate_random_value, parse_dynamic_random
from utils import set_window_geometry_and_center, create_new_names, save_session_to_file


def _order_sessions(sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Match the session manager ordering: examples first, then creation time."""
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


def _format_session_label(session: Dict[str, Any]) -> str:
    session_id = session.get('id', 'Unknown')
    name = session.get('name', 'Unknown')
    status = session.get('status', 'unknown')
    created = session.get('created_at', 0)
    created_str = datetime.fromtimestamp(created).strftime('%Y-%m-%d %H:%M') if created else 'n/a'
    active_prefix = "【ACTIVE】 " if status == 'active' else ""
    return f"{active_prefix}[{session_id}] {name} - {created_str}"


class SessionSelectionDialog:
    """Dialog for selecting multiple sessions."""

    def __init__(self, parent, api_server: APIServer):
        self.result: Optional[List[Dict[str, Any]]] = None
        self.api_server = api_server
        self.sessions: List[Dict[str, Any]] = []
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Select Sessions")
        set_window_geometry_and_center(self.dialog, 700, 500, parent)

        self.create_widgets()
        self.refresh_sessions()
        self.dialog.wait_window()

    def create_widgets(self):
        frame = ttk.Frame(self.dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Choose Sessions to Create Tasks For",
                  font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(0, 8))

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, exportselection=False)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.bind("<Button-1>", self._handle_click)
        self._anchor_index = None

        button_row = ttk.Frame(frame)
        button_row.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(button_row, text="Select All", command=self.select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_row, text="Select Active", command=self.select_active).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_row, text="Random Select", command=self.random_select).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_row, text="Clear", command=self.clear_selection).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_row, text="Refresh", command=self.refresh_sessions).pack(side=tk.RIGHT, padx=2)

        action_row = ttk.Frame(frame)
        action_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(action_row, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=4)
        ttk.Button(action_row, text="Use Selected", command=self.confirm).pack(side=tk.RIGHT, padx=4)

        self.dialog.bind('<Escape>', lambda e: self.cancel())

    def refresh_sessions(self):
        sessions = self.api_server.api_get_sessions() or []
        ordered_sessions = _order_sessions(sessions)

        current_session_id = None
        try:
            current_session = self.api_server.api_get_current_session(show_error=False)
            current_session_id = current_session.get('id') if current_session else None
        except Exception:
            current_session_id = None

        for session in ordered_sessions:
            session['status'] = 'active' if current_session_id and session.get('id') == current_session_id else 'inactive'

        self.sessions = ordered_sessions
        self.listbox.delete(0, tk.END)
        for session in self.sessions:
            self.listbox.insert(tk.END, _format_session_label(session))

    def select_all(self):
        self.listbox.selection_set(0, tk.END)

    def select_active(self):
        self.listbox.selection_clear(0, tk.END)
        for idx, session in enumerate(self.sessions):
            if session.get('status') == 'active':
                self.listbox.selection_set(idx)

    def clear_selection(self):
        self.listbox.selection_clear(0, tk.END)

    def random_select(self):
        if not self.sessions:
            messagebox.showwarning("No Sessions", "No sessions available to select.")
            return
        default_count = min(5, len(self.sessions))
        count = self._ask_random_count(default_count, len(self.sessions))
        if count is None:
            return
        self.listbox.selection_clear(0, tk.END)
        indices = random.sample(range(len(self.sessions)), k=count)
        for idx in indices:
            self.listbox.selection_set(idx)

    def _ask_random_count(self, default_count: int, max_count: int) -> Optional[int]:
        dialog = tk.Toplevel(self.dialog)
        dialog.title("Random Select")
        set_window_geometry_and_center(dialog, 200, 100, self.dialog)
        dialog.transient(self.dialog)
        dialog.grab_set()

        value = tk.IntVar(value=default_count)

        frame = ttk.Frame(dialog, padding="12")
        frame.pack(fill=tk.BOTH, expand=True)

        input_row = ttk.Frame(frame)
        input_row.pack(anchor=tk.W, pady=(0, 8))
        ttk.Label(input_row, text="Select count:").pack(side=tk.LEFT, padx=(0, 8))
        spin = ttk.Spinbox(input_row, from_=1, to=max_count, textvariable=value, width=8)
        spin.pack(side=tk.LEFT)
        spin.focus_set()
        spin.selection_range(0, tk.END)

        result = {'value': None}

        def _submit():
            try:
                selected = int(value.get())
            except (TypeError, ValueError):
                messagebox.showerror("Invalid Value", "Please enter a valid number.")
                return
            if selected < 1 or selected > max_count:
                messagebox.showerror("Invalid Value", f"Enter a value between 1 and {max_count}.")
                return
            result['value'] = selected
            dialog.destroy()

        def _cancel():
            dialog.destroy()

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=_cancel).pack(side=tk.RIGHT, padx=4)
        ttk.Button(buttons, text="OK", command=_submit).pack(side=tk.RIGHT, padx=4)

        dialog.bind('<Return>', lambda e: _submit())
        dialog.bind('<Escape>', lambda e: _cancel())
        dialog.wait_window()

        return result['value']

    def _handle_click(self, event):
        index = self.listbox.nearest(event.y)
        if index < 0 or index >= len(self.sessions):
            return "break"

        shift = bool(event.state & 0x0001)
        ctrl = bool(event.state & 0x0004)
        cmd_mask = 0x0008 if sys.platform == 'darwin' else 0x0010
        cmd = bool(event.state & cmd_mask)
        toggle = ctrl or cmd

        if shift and self._anchor_index is not None:
            start = min(self._anchor_index, index)
            end = max(self._anchor_index, index)
            if self.listbox.selection_includes(index):
                for i in range(start, end + 1):
                    self.listbox.selection_clear(i)
            else:
                for i in range(start, end + 1):
                    self.listbox.selection_set(i)
            return "break"

        if toggle:
            if self.listbox.selection_includes(index):
                self.listbox.selection_clear(index)
            else:
                self.listbox.selection_set(index)
            self._anchor_index = index
            return "break"

        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(index)
        self._anchor_index = index
        return "break"

    def confirm(self):
        indices = self.listbox.curselection()
        if not indices:
            messagebox.showwarning("No Selection", "Please select at least one session.")
            return
        self.result = [self.sessions[i] for i in indices]
        self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()


class MultiSessionTemplateTool:
    """Standalone tool for multi-session task creation from templates."""

    def __init__(self, root: Optional[tk.Misc] = None, show_window: bool = True):
        self.root = root or tk.Tk()
        self._owns_root = root is None

        self.app_settings = get_settings()
        self.username = self.app_settings.get('username', 'SYSTEM')

        self.api_server = APIServer()
        self.template_manager = TaskTemplateManager()

        self.status_var = tk.StringVar(master=self.root, value="Ready.")

        if show_window:
            self.root.title("Multi-Session Template Task Creator")
            set_window_geometry_and_center(self.root, 700, 420, None)
            self.create_widgets()

    def create_widgets(self):
        main = ttk.Frame(self.root, padding="16")
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="Standalone Multi-Session Task Creator",
                  font=('Arial', 14, 'bold')).pack(anchor=tk.W, pady=(0, 8))
        ttk.Label(main, text="Create tasks from templates across multiple sessions.",
                  foreground='gray').pack(anchor=tk.W, pady=(0, 16))

        ttk.Button(main, text="Use Template", style='Accent.TButton',
                   command=self.handle_use_template).pack(anchor=tk.W)

        status_frame = ttk.Frame(main)
        status_frame.pack(fill=tk.X, pady=(20, 0))
        ttk.Label(status_frame, text="Status:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=(6, 0))

    def handle_use_template(self):
        session_dialog = SessionSelectionDialog(self.root, self.api_server)
        if not session_dialog.result:
            return

        session_payloads = self._load_session_payloads(session_dialog.result)
        if not session_payloads:
            messagebox.showerror("Error", "No sessions available for task creation.")
            return

        current_task_type = self._resolve_common_task_type(session_payloads)
        template_dialog = TemplateBrowserDialog(
            self.root,
            self.template_manager,
            available_drones=[],
            available_targets=[],
            available_obstacles=[],
            username=self.username,
            existing_task_names=[],
            select_only=True,
            current_task_type=current_task_type
        )
        template_id = template_dialog.result
        if not template_id:
            return

        template_data = self.template_manager.get_template(template_id)
        if not template_data:
            messagebox.showerror("Error", "Template not found.")
            return

        union_drones, union_targets, union_obstacles = self._build_union_entities(session_payloads)
        existing_task_names = self._build_union_task_names(session_payloads)

        param_dialog = TemplateParameterDialog(
            self.root,
            template_data,
            union_drones,
            template_manager=self.template_manager,
            template_id=template_id,
            available_targets=union_targets,
            available_obstacles=union_obstacles,
            username=self.username,
            existing_task_names=existing_task_names,
            return_spec=True,
            allow_specific_entities=False
        )

        if not param_dialog.result:
            return

        self._create_tasks_for_sessions(
            template_id,
            template_data,
            session_payloads,
            param_dialog.result
        )

    def _resolve_common_task_type(self, session_payloads: List[Dict[str, Any]]) -> Optional[str]:
        task_types = {
            (payload.get('session') or {}).get('task_type')
            for payload in session_payloads
            if (payload.get('session') or {}).get('task_type')
        }
        if len(task_types) == 1:
            return next(iter(task_types))
        return None

    def _load_session_payloads(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        payloads = []
        for session in sessions:
            session_id = session.get('id')
            if not session_id:
                continue
            data = self.api_server.api_get_session_data(session_id)
            if not data:
                messagebox.showwarning("Session Error", f"Failed to load data for session {session_id}.")
                continue
            payloads.append({
                'session': session,
                'data': data
            })
        return payloads

    def _build_union_entities(self, session_payloads: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]],
                                                                                    List[Dict[str, Any]],
                                                                                    List[Dict[str, Any]]]:
        def _merge_entities(key: str) -> List[Dict[str, Any]]:
            seen = {}
            for payload in session_payloads:
                for entity in payload['data'].get(key, []) or []:
                    entity_id = entity.get('id') or entity.get('name')
                    if entity_id and entity_id not in seen:
                        seen[entity_id] = entity
            return list(seen.values())

        return _merge_entities('drones'), _merge_entities('targets'), _merge_entities('obstacles')

    def _build_union_task_names(self, session_payloads: List[Dict[str, Any]]) -> List[str]:
        names = []
        for payload in session_payloads:
            tasks = payload['data'].get('tasks', []) or []
            names.extend([t.get('name', '') for t in tasks if t.get('name')])
        return names

    def _create_tasks_for_sessions(self, template_id: str, template_data: Dict[str, Any],
                                   session_payloads: List[Dict[str, Any]], result_payload: Dict[str, Any]):
        if result_payload.get('type') != 'spec':
            messagebox.showerror("Error", "Unexpected parameter payload.")
            return

        spec = result_payload.get('spec', {})
        mode = result_payload.get('mode', 'single')
        count = result_payload.get('count', 1) if mode == 'batch' else 1

        summary = []
        total_success = 0
        total_failed = 0
        ordered_indices: Dict[str, Dict[str, int]] = {}

        for payload in session_payloads:
            session = payload['session']
            session_id = session.get('id')
            session_name = session.get('name', session_id)
            data = payload['data']
            if not session_id:
                continue

            ordered_indices.setdefault(session_id, {'drone': 0, 'target': 0, 'obstacle': 0})
            existing_names = [t.get('name', '') for t in data.get('tasks', []) or []]

            base_name = spec.get('name_base', template_data.get('name', 'Task'))
            new_names = create_new_names(base_name, count, existing_names) if count > 1 else [base_name]

            success = 0
            failed = 0
            for idx in range(count):
                params, error = self._resolve_spec_for_task(
                    spec,
                    data,
                    ordered_indices[session_id]
                )
                if error:
                    failed += 1
                    continue
                params['name'] = new_names[idx]
                params['creator'] = self.username

                task_data = self.template_manager.instantiate_template(template_id, params)
                if not task_data:
                    failed += 1
                    continue
                result = self.api_server.api_create_task(session_id, task_data)
                if result:
                    success += 1
                else:
                    failed += 1

            total_success += success
            total_failed += failed
            saved_path = None
            save_error = None
            if success > 0:
                try:
                    latest_data = self.api_server.api_get_session_data(session_id)
                    if latest_data:
                        saved_path = save_session_to_file(latest_data)
                    else:
                        save_error = "Failed to fetch session data for save"
                except Exception as exc:
                    save_error = str(exc)

            if saved_path:
                summary.append(f"{session_name} ({session_id}): {success} created, {failed} failed, saved to {saved_path}")
            elif save_error and success > 0:
                summary.append(f"{session_name} ({session_id}): {success} created, {failed} failed, save error: {save_error}")
            else:
                summary.append(f"{session_name} ({session_id}): {success} created, {failed} failed")

        self.status_var.set(f"Done. {total_success} created, {total_failed} failed.")
        if total_failed == 0:
            messagebox.showinfo("Success", "All tasks created successfully.\n\n" + "\n".join(summary))
        else:
            messagebox.showwarning("Completed with Errors", "\n".join(summary))

    def _resolve_spec_for_task(self, spec: Dict[str, Any], session_data: Dict[str, Any],
                               ordered_index: Dict[str, int]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        params: Dict[str, Any] = {}
        random_cache: Dict[str, Any] = {}

        drones = session_data.get('drones', []) or []
        targets = session_data.get('targets', []) or []
        obstacles = session_data.get('obstacles', []) or []

        def _build_random_pool(available: List[Dict[str, Any]], requested: int) -> List[Dict[str, Any]]:
            if requested <= 0 or not available:
                return []
            if len(available) >= requested:
                return random.sample(available, requested)
            return [random.choice(available) for _ in range(requested)]

        random_counts = {'drone': 0, 'target': 0, 'obstacle': 0}
        for entity in spec.get('entities', []):
            if entity.get('selection') == '[RANDOM]' and entity.get('entity_type') in random_counts:
                random_counts[entity['entity_type']] += 1

        random_pools = {
            'drone': _build_random_pool(drones, random_counts['drone']),
            'target': _build_random_pool(targets, random_counts['target']),
            'obstacle': _build_random_pool(obstacles, random_counts['obstacle'])
        }

        def _select_ordered(entity_type: str, available: List[Dict[str, Any]]):
            if not available:
                return None
            index = ordered_index.get(entity_type, 0) % len(available)
            ordered_index[entity_type] = (index + 1) % len(available)
            return available[index]

        def _find_entity(available: List[Dict[str, Any]], value: str) -> Optional[Dict[str, Any]]:
            value = value.strip()
            if ' - ' in value:
                value = value.split(' - ', 1)[0].strip()
            return next((e for e in available if e.get('id') == value or e.get('name') == value), None)

        def _resolve_random_value(raw_value: Any) -> Optional[Any]:
            if not isinstance(raw_value, str):
                return None
            value_str = raw_value.strip()
            if not value_str:
                return None
            placeholder = value_str[1:-1] if value_str.startswith('{') and value_str.endswith('}') else value_str

            var_name, dynamic_value, is_anonymous = parse_dynamic_random(placeholder)
            if dynamic_value is not None:
                if is_anonymous:
                    return dynamic_value
                if var_name in random_cache:
                    return random_cache[var_name]
                random_cache[var_name] = dynamic_value
                return dynamic_value

            info = get_placeholder_info(placeholder)
            if info and info.get('type') == 'random_float':
                if placeholder not in random_cache:
                    random_cache[placeholder] = generate_random_value(info)
                return random_cache[placeholder]
            return None

        for entity in spec.get('entities', []):
            selection = entity.get('selection')
            entity_type = entity.get('entity_type')
            id_param = entity.get('id_param')
            name_param = entity.get('name_param')

            available = drones if entity_type == 'drone' else targets if entity_type == 'target' else obstacles

            if selection == '[RANDOM]':
                if not available:
                    return None, f"No {entity_type}s available for random selection"
                selected = random_pools[entity_type].pop() if random_pools[entity_type] else random.choice(available)
            elif selection == '[ORDERED]':
                selected = _select_ordered(entity_type, available)
                if not selected:
                    return None, f"No {entity_type}s available for ordered selection"
            else:
                selected = _find_entity(available, selection)
                if not selected and entity_type == 'drone':
                    return None, f"Drone not found for selection '{selection}'"
                if not selected:
                    selected = {'id': selection, 'name': selection}

            if id_param:
                params[id_param] = selected.get('id') or selected.get('name')
            if name_param:
                params[name_param] = selected.get('name') or selected.get('id')

        for field_name, field in spec.get('fields', {}).items():
            if field.get('kind') == 'numeric':
                if field.get('range'):
                    min_val = float(field.get('min', 0))
                    max_val = float(field.get('max', 0))
                    params[field_name] = round(random.uniform(min_val, max_val), 1)
                else:
                    value = field.get('value', '')
                    resolved = _resolve_random_value(value)
                    if resolved is not None:
                        params[field_name] = resolved
                    else:
                        try:
                            params[field_name] = float(value) if '.' in value else int(value)
                        except ValueError:
                            params[field_name] = value
            else:
                value = field.get('value', '')
                resolved = _resolve_random_value(value)
                if resolved is not None:
                    params[field_name] = resolved
                else:
                    try:
                        params[field_name] = float(value) if '.' in value else int(value)
                    except ValueError:
                        params[field_name] = value

        if obstacles:
            params['_context_obstacles'] = obstacles

        return params, None

    def run(self):
        self.root.mainloop()


def launch_task_ui_flow(parent, set_icon=None):
    """Open the task template flow directly at session selection."""
    host = tk.Toplevel(parent)
    host.withdraw()

    if set_icon is not None:
        try:
            set_icon(host)
        except Exception:
            pass

    try:
        tool = MultiSessionTemplateTool(root=host, show_window=False)
        tool.handle_use_template()
    finally:
        try:
            if host.winfo_exists():
                host.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    try:
        tool = MultiSessionTemplateTool(root=root, show_window=False)
        tool.handle_use_template()
    finally:
        try:
            if root.winfo_exists():
                root.destroy()
        except Exception:
            pass
