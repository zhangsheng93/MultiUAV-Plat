#!/usr/bin/env python3
"""Comparison window for AI Agent Auto-Check result exports."""

import json
import platform
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from tksheet import Sheet
from utils import is_export_id_valid, set_window_geometry_and_center


TaskKey = Tuple[str, str]
QueueTask = Tuple[str, str, str, str]
Score = Union[int, float]


@dataclass
class ComparisonMethod:
    """One imported method/result file shown as a dynamic comparison column."""

    name: str
    path: Path
    results: Dict[TaskKey, Dict[str, Any]]
    statistics: Dict[str, Any] = field(default_factory=dict)


def count_result_checks(result: Optional[Dict[str, Any]]) -> Tuple[int, int]:
    """Return (total checks, passed checks) for an exported task result."""
    if not isinstance(result, dict):
        return 0, 0

    statistics = result.get("statistics")
    if isinstance(statistics, dict):
        total = statistics.get("total_checks_apis")
        passed = statistics.get("passed_checks_apis")
        if isinstance(total, int) and isinstance(passed, int):
            return max(total, 0), max(passed, 0)

    details = result.get("details", [])
    if isinstance(details, list):
        leaf_details = [d for d in details if isinstance(d, dict) and d.get("type") == "leaf"]
        total = len(leaf_details)
        passed = sum(1 for d in leaf_details if d.get("result", False))
        return total, passed

    return 0, 0


def keycap_number(number: int) -> str:
    """Render a non-negative integer as keycap emoji digits where practical."""
    digits = {
        "0": "0️⃣",
        "1": "1️⃣",
        "2": "2️⃣",
        "3": "3️⃣",
        "4": "4️⃣",
        "5": "5️⃣",
        "6": "6️⃣",
        "7": "7️⃣",
        "8": "8️⃣",
        "9": "9️⃣",
    }
    return "".join(digits.get(ch, ch) for ch in str(max(number, 0)))


def passed_count_label(number: int) -> str:
    """Render partial passed-check counts for the current platform."""
    if platform.system() == "Windows":
        return str(max(number, 0))
    return keycap_number(number)


def render_result_cell(result: Optional[Dict[str, Any]], missing: str = "-") -> str:
    """Render one method/task comparison cell."""
    if not isinstance(result, dict):
        return missing

    total, passed = count_result_checks(result)
    if result.get("status") == "passed" or (total > 0 and passed >= total):
        return "✅"
    if passed == 0:
        return "❌"
    return passed_count_label(passed)


def is_result_passed(result: Optional[Dict[str, Any]]) -> bool:
    """Return True when a task result should count as a passed task."""
    if not isinstance(result, dict):
        return False
    total, passed = count_result_checks(result)
    return result.get("status") == "passed" or (total > 0 and passed >= total)


def best_value_indexes(scores: Iterable[Optional[Score]]) -> List[int]:
    """Return all indexes sharing the best numeric score."""
    score_list = list(scores)
    numeric_scores = [score for score in score_list if score is not None]
    if not numeric_scores:
        return []

    best = max(numeric_scores)
    if best <= 0:
        return []
    return [index for index, score in enumerate(score_list) if score == best]


def format_rate(rate: Optional[float], missing: str = "-") -> str:
    """Format a 0..1 rate for summary rows."""
    if isinstance(rate, (int, float)) and not isinstance(rate, bool):
        percent = max(float(rate), 0.0) * 100
        return f"{percent:.1f}".rstrip("0").rstrip(".") + "%"
    return missing


def result_lookup_from_payload(payload: Dict[str, Any]) -> Dict[TaskKey, Dict[str, Any]]:
    """Build a result lookup keyed by (session_id, task_id)."""
    lookup: Dict[TaskKey, Dict[str, Any]] = {}
    results = payload.get("results", [])
    if not isinstance(results, list):
        return lookup

    for result in results:
        if not isinstance(result, dict):
            continue
        session_id = result.get("session_id")
        task_id = result.get("task_id")
        if session_id and task_id:
            lookup[(str(session_id), str(task_id))] = result
    return lookup


def load_comparison_method(path: Path) -> ComparisonMethod:
    """Load and validate an exported result file as a comparison method."""
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    if not is_export_id_valid(payload):
        raise ValueError("invalid export id")

    return ComparisonMethod(
        name=path.stem,
        path=path,
        results=result_lookup_from_payload(payload),
        statistics=payload.get("statistics") if isinstance(payload.get("statistics"), dict) else {},
    )


def build_comparison_rows(
    queue_tasks: Iterable[QueueTask],
    methods: Iterable[ComparisonMethod],
    missing: str = "-",
) -> List[Dict[str, Any]]:
    """Build queue-ordered comparison rows for display and tests."""
    method_list = list(methods)
    queue_task_list = list(queue_tasks)
    rows: List[Dict[str, Any]] = []

    expected_total_checks = 0
    method_passed_tasks: List[int] = []
    method_passed_checks: List[int] = []
    method_total_tasks: List[int] = []
    method_total_checks: List[int] = []
    method_task_rates: List[float] = []
    method_average_check_rates: List[float] = []
    method_check_rates: List[float] = []
    total_tasks = len(queue_task_list)

    for method in method_list:
        passed_tasks = 0
        total_checks = 0
        passed_checks = 0
        task_check_rate_sum = 0.0

        for session_id, task_id, _task_name, _session_name in queue_task_list:
            result = method.results.get((session_id, task_id))
            result_total_checks, result_passed_checks = count_result_checks(result)
            total_checks += result_total_checks
            passed_checks += result_passed_checks

            if is_result_passed(result):
                passed_tasks += 1
            if result_total_checks > 0:
                task_check_rate_sum += result_passed_checks / result_total_checks

        method_total_tasks.append(total_tasks)
        method_total_checks.append(total_checks)
        method_passed_tasks.append(passed_tasks)
        method_passed_checks.append(passed_checks)
        method_task_rates.append(passed_tasks / total_tasks if total_tasks > 0 else 0.0)
        method_average_check_rates.append(task_check_rate_sum / total_tasks if total_tasks > 0 else 0.0)
        method_check_rates.append(passed_checks / total_checks if total_checks > 0 else 0.0)

    for session_id, task_id, _task_name, _session_name in queue_task_list:
        key = (session_id, task_id)
        totals = [
            count_result_checks(method.results.get(key))[0]
            for method in method_list
            if key in method.results
        ]
        expected_total_checks += max(totals) if totals else 0

    summary_rows = [
        {
            "key": ("__summary__", "total_tasks"),
            "id": "-",
            "name": "Total Tasks",
            "checks": total_tasks,
            "cells": [str(value) for value in method_total_tasks],
            "scores": [],
        },
        {
            "key": ("__summary__", "total_checks"),
            "id": "-",
            "name": "Total Checks",
            "checks": expected_total_checks,
            "cells": [str(value) for value in method_total_checks],
            "scores": [],
        },
        {
            "key": ("__summary__", "passed_tasks"),
            "id": "-",
            "name": "Passed Tasks",
            "checks": total_tasks,
            "cells": [str(value) for value in method_passed_tasks],
            "scores": method_passed_tasks,
        },
        {
            "key": ("__summary__", "passed_task_rate"),
            "id": "-",
            "name": "Passed Task Rate",
            "checks": total_tasks,
            "cells": [format_rate(rate, missing) for rate in method_task_rates],
            "scores": method_task_rates,
        },
        {
            "key": ("__summary__", "average_check_pass_rate"),
            "id": "-",
            "name": "Average Check Pass Rate",
            "checks": total_tasks,
            "cells": [format_rate(rate, missing) for rate in method_average_check_rates],
            "scores": method_average_check_rates,
        },
        {
            "key": ("__summary__", "passed_checks"),
            "id": "-",
            "name": "Passed Checks",
            "checks": expected_total_checks,
            "cells": [str(value) for value in method_passed_checks],
            "scores": method_passed_checks,
        },
        {
            "key": ("__summary__", "passed_check_rate"),
            "id": "-",
            "name": "Passed Check Rate",
            "checks": expected_total_checks,
            "cells": [format_rate(rate, missing) for rate in method_check_rates],
            "scores": method_check_rates,
        },
    ]
    for row in summary_rows:
        row["best_indexes"] = best_value_indexes(row["scores"])
        rows.append(row)

    for session_id, task_id, task_name, _session_name in queue_task_list:
        key = (session_id, task_id)
        totals = [
            count_result_checks(method.results.get(key))[0]
            for method in method_list
            if key in method.results
        ]
        checks = max(totals) if totals else 0
        cells = [render_result_cell(method.results.get(key), missing=missing) for method in method_list]
        scores = [
            count_result_checks(method.results.get(key))[1] if key in method.results else None
            for method in method_list
        ]
        rows.append({
            "key": key,
            "id": task_id,
            "name": task_name,
            "checks": checks,
            "cells": cells,
            "scores": scores,
            "best_indexes": best_value_indexes(scores),
        })

    return rows


def build_sheet_table(
    queue_tasks: Iterable[QueueTask],
    methods: Iterable[ComparisonMethod],
) -> Tuple[List[str], List[List[Any]], List[Tuple[int, int]], List[int], List[str]]:
    """Return tksheet headers, rows, best-cell positions, summary row indexes, and row labels."""
    method_list = list(methods)
    headers = ["Name", "ID", "Checks"] + [method.name for method in method_list]
    rows = build_comparison_rows(queue_tasks, method_list)
    data = [
        [row["name"], row["id"], row["checks"]] + row["cells"]
        for row in rows
    ]
    best_cells = [
        (row_index, 3 + method_index)
        for row_index, row in enumerate(rows)
        for method_index in row.get("best_indexes", [])
    ]
    summary_rows = [
        row_index
        for row_index, row in enumerate(rows)
        if row.get("key", ("", ""))[0] == "__summary__"
    ]
    row_index_labels: List[str] = []
    task_index = 1
    for row in rows:
        if row.get("key", ("", ""))[0] == "__summary__":
            row_index_labels.append("-")
        else:
            row_index_labels.append(str(task_index))
            task_index += 1
    return headers, data, best_cells, summary_rows, row_index_labels


class ResultCompareWindow:
    """Tk window for comparing multiple exported AI Agent Auto-Check result files."""

    WINDOW_WIDTH = 980
    WINDOW_HEIGHT = 620

    def __init__(self, parent: tk.Misc, queue_tasks: Iterable[QueueTask], set_icon=None):
        self.parent = parent
        self.queue_tasks = list(queue_tasks)
        self.methods: List[ComparisonMethod] = []
        self.set_icon = set_icon

        self.window = tk.Toplevel(parent)
        self.window.withdraw()
        self.window.title("Compare Results")
        if self.set_icon:
            self.set_icon(self.window)

        self.method_name_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Import result JSON files to compare methods.")
        self.sheet = None
        self._setup_ui()
        self.refresh_table()
        set_window_geometry_and_center(
            self.window,
            self.WINDOW_WIDTH,
            self.WINDOW_HEIGHT,
            parent,
            make_transient=True,
            grab=False,
            withdraw_first=True,
            align_to_pointer=False,
            bring_to_front=True,
        )

    def _setup_ui(self):
        container = ttk.Frame(self.window, padding="10")
        container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        toolbar = ttk.Frame(container)
        toolbar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 8))
        ttk.Button(toolbar, text="Import JSON", command=self.import_json_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Clear", command=self.clear_methods).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(toolbar, textvariable=self.status_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        method_frame = ttk.LabelFrame(container, text="Methods", padding="5")
        method_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 8))
        method_frame.columnconfigure(0, weight=1)

        self.method_tree = ttk.Treeview(
            method_frame,
            columns=("name", "file"),
            show="headings",
            height=4,
            selectmode="browse",
        )
        self.method_tree.heading("name", text="Method Name")
        self.method_tree.heading("file", text="File")
        self.method_tree.column("name", width=180, stretch=False)
        self.method_tree.column("file", width=620, stretch=True)
        self.method_tree.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.method_tree.bind("<<TreeviewSelect>>", self.on_method_select)

        rename_frame = ttk.Frame(method_frame)
        rename_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(6, 0))
        rename_frame.columnconfigure(1, weight=1)
        ttk.Label(rename_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.method_name_entry = ttk.Entry(rename_frame, textvariable=self.method_name_var)
        self.method_name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.method_name_entry.bind("<Return>", lambda _event: self.rename_selected_method())
        ttk.Button(rename_frame, text="Rename", command=self.rename_selected_method).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(rename_frame, text="Remove", command=self.remove_selected_method).grid(row=0, column=3, padx=(0, 5))
        ttk.Button(rename_frame, text="Up", command=self.move_selected_method_up).grid(row=0, column=4, padx=(0, 5))
        ttk.Button(rename_frame, text="Down", command=self.move_selected_method_down).grid(row=0, column=5)

        table_frame = ttk.Frame(container)
        table_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        if Sheet is None:
            ttk.Label(
                table_frame,
                text="Install tksheet to show the interactive comparison table.",
                anchor=tk.CENTER,
            ).grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            return

        self.sheet = Sheet(
            table_frame,
            data=[],
            headers=[],
            allow_cell_overflow=False,
        )
        self.sheet.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.configure_sheet_bindings()

    def configure_sheet_bindings(self):
        """Enable table interactions without allowing result edits."""
        if self.sheet is None:
            return

        bindings = (
            "single_select",
            "drag_select",
            "select_all",
            "column_select",
            "row_select",
            "arrowkeys",
            "right_click_popup_menu",
            "rc_select",
            "copy",
            "column_width_resize",
            "double_click_column_resize",
            "row_height_resize",
            "row_width_resize",
            "column_height_resize",
        )
        try:
            self.sheet.enable_bindings(*bindings)
        except Exception:
            self.sheet.enable_bindings(
                "single_select",
                "drag_select",
                "select_all",
                "column_select",
                "row_select",
                "arrowkeys",
                "copy",
                "column_width_resize",
                "double_click_column_resize",
                "row_height_resize",
            )

    def import_json_files(self):
        filenames = filedialog.askopenfilenames(
            title="Import Result JSON Files",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=self.window,
        )
        if not filenames:
            return

        imported = 0
        invalid_files: List[str] = []
        for filename in filenames:
            path = Path(filename)
            try:
                self.methods.append(load_comparison_method(path))
                imported += 1
            except Exception:
                invalid_files.append(path.name)

        self.refresh_methods()
        self.refresh_table()

        if invalid_files:
            messagebox.showwarning(
                "Import Warning",
                "Skipped invalid result file(s):\n" + "\n".join(invalid_files),
                parent=self.window,
            )
        self.status_var.set(f"Imported {imported} file(s). {len(self.queue_tasks)} queued task(s).")

    def clear_methods(self):
        self.methods.clear()
        self.method_name_var.set("")
        self.refresh_methods()
        self.refresh_table()
        self.status_var.set("Cleared imported methods.")

    def refresh_methods(self):
        self.method_tree.delete(*self.method_tree.get_children())
        for index, method in enumerate(self.methods):
            self.method_tree.insert("", tk.END, iid=str(index), values=(method.name, str(method.path)))

    def on_method_select(self, _event=None):
        selection = self.method_tree.selection()
        if not selection:
            return
        index = int(selection[0])
        if 0 <= index < len(self.methods):
            self.method_name_var.set(self.methods[index].name)

    def rename_selected_method(self):
        selection = self.method_tree.selection()
        if not selection:
            return
        index = int(selection[0])
        new_name = self.method_name_var.get().strip()
        if not new_name or not (0 <= index < len(self.methods)):
            return

        self.methods[index].name = new_name
        self.refresh_methods()
        self.method_tree.selection_set(str(index))
        self.refresh_table(reset_widths=False)
        self.status_var.set(f"Renamed method to {new_name}.")

    def remove_selected_method(self):
        selection = self.method_tree.selection()
        if not selection:
            return

        index = int(selection[0])
        if not (0 <= index < len(self.methods)):
            return

        removed_name = self.methods[index].name
        self.methods.pop(index)
        self.refresh_methods()

        if self.methods:
            next_index = min(index, len(self.methods) - 1)
            self.method_tree.selection_set(str(next_index))
            self.method_tree.focus(str(next_index))
            self.method_tree.see(str(next_index))
            self.method_name_var.set(self.methods[next_index].name)
        else:
            self.method_name_var.set("")

        self.refresh_table()
        self.status_var.set(f"Removed method {removed_name}.")

    def move_selected_method_up(self):
        self.move_selected_method(-1)

    def move_selected_method_down(self):
        self.move_selected_method(1)

    def move_selected_method(self, offset: int):
        selection = self.method_tree.selection()
        if not selection:
            return

        index = int(selection[0])
        new_index = index + offset
        if not (0 <= index < len(self.methods)) or not (0 <= new_index < len(self.methods)):
            return

        self.methods[index], self.methods[new_index] = self.methods[new_index], self.methods[index]
        self.refresh_methods()
        self.method_tree.selection_set(str(new_index))
        self.method_tree.focus(str(new_index))
        self.method_tree.see(str(new_index))
        self.method_name_var.set(self.methods[new_index].name)
        self.refresh_table()
        self.status_var.set("Reordered methods.")

    def refresh_table(self, reset_widths: bool = True):
        if self.sheet is None:
            return

        headers, data, best_cells, summary_rows, row_index_labels = build_sheet_table(self.queue_tasks, self.methods)
        widths = [220, 110, 70] + [120 for _method in self.methods]

        try:
            self.sheet.set_sheet_data(
                data,
                reset_col_positions=True,
                reset_row_positions=True,
                reset_highlights=True,
                redraw=False,
            )
        except TypeError:
            self.sheet.set_sheet_data(data, redraw=False)

        self.sheet.headers(headers, reset_col_positions=True, redraw=False)
        self.apply_sheet_row_index(row_index_labels)
        if reset_widths:
            self.apply_sheet_column_widths(widths)
        self.apply_sheet_alignment(len(headers))
        self.apply_sheet_highlights(best_cells, summary_rows)
        self.sheet.redraw()

    def apply_sheet_column_widths(self, widths: List[int]):
        for column_index, width in enumerate(widths):
            try:
                self.sheet.column_width(column=column_index, width=width, redraw=False)
            except Exception:
                pass

    def apply_sheet_row_index(self, row_index_labels: List[str]):
        try:
            self.sheet.row_index(row_index_labels, reset_row_positions=True, redraw=False)
        except Exception:
            try:
                self.sheet.set_index_data(row_index_labels, redraw=False)
            except Exception:
                pass

    def apply_sheet_alignment(self, column_count: int):
        try:
            self.sheet.align_columns(columns=0, align="w", align_header=False, redraw=False)
            self.sheet.align_header(columns=0, align="center", redraw=False)
        except Exception:
            pass

        if column_count <= 1:
            return

        centered_columns = list(range(1, column_count))
        try:
            self.sheet.align_columns(columns=centered_columns, align="center", align_header=False, redraw=False)
            self.sheet.align_header(columns=centered_columns, align="center", redraw=False)
        except Exception:
            pass

    def apply_sheet_highlights(self, best_cells: List[Tuple[int, int]], summary_rows: List[int]):
        try:
            self.sheet.dehighlight_cells(all_=True, redraw=False)
        except Exception:
            pass

        for row_index in summary_rows:
            try:
                self.sheet.highlight_rows(rows=[row_index], bg="#f4f4f4", fg="black", redraw=False)
            except Exception:
                pass

        for row_index, column_index in best_cells:
            try:
                self.sheet.highlight_cells(row=row_index, column=column_index, bg="#fff2a8", fg="black", redraw=False)
            except Exception:
                try:
                    self.sheet.highlight_cells(cells=[(row_index, column_index)], bg="#fff2a8", fg="black", redraw=False)
                except Exception:
                    pass
