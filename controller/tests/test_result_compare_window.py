import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from check_ui.result_compare_window import (
    ComparisonMethod,
    build_comparison_rows,
    build_sheet_table,
    load_comparison_method,
    render_result_cell,
)
from utils import calculate_export_id


def make_result(session_id, task_id, total, passed, status="failed"):
    return {
        "session_id": session_id,
        "task_id": task_id,
        "task_name": task_id,
        "status": status,
        "statistics": {
            "total_checks_apis": total,
            "passed_checks_apis": passed,
            "failed_checks_apis": total - passed,
            "pass_rate": passed / total if total else 0,
        },
        "details": [],
    }


def make_statistics(total_tasks, passed_tasks, total_checks, passed_checks, average_check_pass_rate=None):
    task_pass_rate = passed_tasks / total_tasks if total_tasks else 0
    if average_check_pass_rate is None:
        average_check_pass_rate = task_pass_rate
    return {
        "total_tasks": total_tasks,
        "passed_tasks_count": passed_tasks,
        "failed_tasks_count": total_tasks - passed_tasks,
        "total_failed_task_count": 0,
        "task_pass_rate": task_pass_rate,
        "total_failed_task_rate": 0,
        "average_check_pass_rate": average_check_pass_rate,
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "failed_checks": total_checks - passed_checks,
        "check_pass_rate": passed_checks / total_checks if total_checks else 0,
    }


class TestResultCompareWindowLogic(unittest.TestCase):
    def test_all_passed_renders_checkmark(self):
        result = make_result("s1", "t1", 5, 5, status="passed")

        self.assertEqual(render_result_cell(result), "✅")

    def test_zero_passed_renders_cross(self):
        result = make_result("s1", "t1", 5, 0, status="failed")

        self.assertEqual(render_result_cell(result), "❌")

    def test_partial_passed_renders_passed_count_emoji(self):
        result = make_result("s1", "t1", 5, 3, status="failed")

        with patch("check_ui.result_compare_window.platform.system", return_value="Darwin"):
            self.assertEqual(render_result_cell(result), "3️⃣")

    def test_partial_passed_renders_plain_digits_on_windows(self):
        result = make_result("s1", "t1", 5, 3, status="failed")

        with patch("check_ui.result_compare_window.platform.system", return_value="Windows"):
            self.assertEqual(render_result_cell(result), "3")

    def test_windows_still_renders_pass_and_fail_emoji(self):
        passed_result = make_result("s1", "t1", 5, 5, status="passed")
        failed_result = make_result("s1", "t2", 5, 0, status="failed")

        with patch("check_ui.result_compare_window.platform.system", return_value="Windows"):
            self.assertEqual(render_result_cell(passed_result), "✅")
            self.assertEqual(render_result_cell(failed_result), "❌")

    def test_missing_result_renders_placeholder(self):
        self.assertEqual(render_result_cell(None), "-")

    def test_queue_ordering_is_preserved(self):
        queue_tasks = [
            ("s1", "t2", "Second Task", "Session"),
            ("s1", "t1", "First Task", "Session"),
        ]
        method = ComparisonMethod(
            name="Method",
            path=Path("method.json"),
            results={
                ("s1", "t1"): make_result("s1", "t1", 2, 2, status="passed"),
                ("s1", "t2"): make_result("s1", "t2", 4, 1, status="failed"),
            },
        )

        rows = build_comparison_rows(queue_tasks, [method])

        task_rows = rows[7:]
        self.assertEqual([row["id"] for row in task_rows], ["t2", "t1"])
        self.assertEqual([row["name"] for row in task_rows], ["Second Task", "First Task"])
        self.assertEqual([row["checks"] for row in task_rows], [4, 2])
        self.assertEqual([row["cells"][0] for row in task_rows], ["1️⃣", "✅"])

    def test_method_order_controls_cell_order(self):
        queue_tasks = [("s1", "t1", "Task", "Session")]
        method_one = ComparisonMethod(
            name="Method 1",
            path=Path("method1.json"),
            results={("s1", "t1"): make_result("s1", "t1", 4, 4, status="passed")},
        )
        method_two = ComparisonMethod(
            name="Method 2",
            path=Path("method2.json"),
            results={("s1", "t1"): make_result("s1", "t1", 4, 2, status="failed")},
        )

        rows = build_comparison_rows(queue_tasks, [method_two, method_one])

        self.assertEqual(rows[7]["cells"], ["2️⃣", "✅"])

    def test_summary_rows_show_totals_passed_counts_and_rates(self):
        queue_tasks = [
            ("s1", "t1", "Task 1", "Session"),
            ("s1", "t2", "Task 2", "Session"),
        ]
        method_one = ComparisonMethod(
            name="Method 1",
            path=Path("method1.json"),
            results={
                ("s1", "t1"): make_result("s1", "t1", 4, 4, status="passed"),
                ("s1", "t2"): make_result("s1", "t2", 3, 1, status="failed"),
            },
        )
        method_two = ComparisonMethod(
            name="Method 2",
            path=Path("method2.json"),
            results={
                ("s1", "t1"): make_result("s1", "t1", 4, 2, status="failed"),
                ("s1", "t2"): make_result("s1", "t2", 3, 3, status="passed"),
            },
        )

        rows = build_comparison_rows(queue_tasks, [method_one, method_two])

        self.assertEqual(rows[0]["name"], "Total Tasks")
        self.assertEqual(rows[0]["id"], "-")
        self.assertEqual(rows[0]["checks"], 2)
        self.assertEqual(rows[0]["cells"], ["2", "2"])
        self.assertEqual(rows[1]["name"], "Total Checks")
        self.assertEqual(rows[1]["id"], "-")
        self.assertEqual(rows[1]["checks"], 7)
        self.assertEqual(rows[1]["cells"], ["7", "7"])
        self.assertEqual(rows[2]["name"], "Passed Tasks")
        self.assertEqual(rows[2]["checks"], 2)
        self.assertEqual(rows[2]["cells"], ["1", "1"])
        self.assertEqual(rows[3]["name"], "Passed Task Rate")
        self.assertEqual(rows[3]["checks"], 2)
        self.assertEqual(rows[3]["cells"], ["50%", "50%"])
        self.assertEqual(rows[4]["name"], "Average Check Pass Rate")
        self.assertEqual(rows[4]["checks"], 2)
        self.assertEqual(rows[4]["cells"], ["66.7%", "75%"])
        self.assertEqual(rows[5]["name"], "Passed Checks")
        self.assertEqual(rows[5]["checks"], 7)
        self.assertEqual(rows[5]["cells"], ["5", "5"])
        self.assertEqual(rows[6]["name"], "Passed Check Rate")
        self.assertEqual(rows[6]["checks"], 7)
        self.assertEqual(rows[6]["cells"], ["71.4%", "71.4%"])

    def test_summary_method_cells_ignore_export_statistics(self):
        queue_tasks = [("s1", "t1", "Task 1", "Session")]
        method = ComparisonMethod(
            name="Method",
            path=Path("method.json"),
            results={("s1", "t1"): make_result("s1", "t1", 4, 2, status="failed")},
            statistics=make_statistics(
                total_tasks=1500,
                passed_tasks=976,
                total_checks=8006,
                passed_checks=6544,
                average_check_pass_rate=0.805,
            ),
        )

        rows = build_comparison_rows(queue_tasks, [method])

        self.assertEqual(rows[0]["cells"], ["1"])
        self.assertEqual(rows[1]["cells"], ["4"])
        self.assertEqual(rows[2]["cells"], ["0"])
        self.assertEqual(rows[3]["cells"], ["0%"])
        self.assertEqual(rows[4]["cells"], ["50%"])
        self.assertEqual(rows[5]["cells"], ["2"])
        self.assertEqual(rows[6]["cells"], ["50%"])

    def test_sheet_table_includes_headers_data_and_best_positions(self):
        queue_tasks = [("s1", "t1", "Task 1", "Session")]
        method_one = ComparisonMethod(
            name="Method 1",
            path=Path("method1.json"),
            results={("s1", "t1"): make_result("s1", "t1", 4, 4, status="passed")},
        )
        method_two = ComparisonMethod(
            name="Method 2",
            path=Path("method2.json"),
            results={("s1", "t1"): make_result("s1", "t1", 4, 2, status="failed")},
        )

        headers, data, best_cells, summary_rows, row_index_labels = build_sheet_table(queue_tasks, [method_one, method_two])

        self.assertEqual(headers, ["Name", "ID", "Checks", "Method 1", "Method 2"])
        self.assertEqual(data[0], ["Total Tasks", "-", 1, "1", "1"])
        self.assertEqual(data[1], ["Total Checks", "-", 4, "4", "4"])
        self.assertEqual(data[2], ["Passed Tasks", "-", 1, "1", "0"])
        self.assertEqual(data[3], ["Passed Task Rate", "-", 1, "100%", "0%"])
        self.assertEqual(data[4], ["Average Check Pass Rate", "-", 1, "100%", "50%"])
        self.assertEqual(data[5], ["Passed Checks", "-", 4, "4", "2"])
        self.assertEqual(data[6], ["Passed Check Rate", "-", 4, "100%", "50%"])
        self.assertEqual(data[7], ["Task 1", "t1", 4, "✅", "2️⃣"])
        self.assertEqual(best_cells, [(2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3)])
        self.assertEqual(summary_rows, [0, 1, 2, 3, 4, 5, 6])
        self.assertEqual(row_index_labels, ["-", "-", "-", "-", "-", "-", "-", "1"])

    def test_sheet_table_keeps_long_name_and_id_separate(self):
        long_name = "Target Area Complete Coverage and Verification Long Task Name"
        queue_tasks = [("s1", "abc12345", long_name, "Session")]

        headers, data, _best_cells, _summary_rows, row_index_labels = build_sheet_table(queue_tasks, [])

        self.assertEqual(headers[:3], ["Name", "ID", "Checks"])
        self.assertEqual(data[7][0], long_name)
        self.assertEqual(data[7][1], "abc12345")
        self.assertEqual(row_index_labels, ["-", "-", "-", "-", "-", "-", "-", "1"])

    def test_best_values_are_identified_for_ties(self):
        queue_tasks = [("s1", "t1", "Task", "Session")]
        method_one = ComparisonMethod(
            name="Method 1",
            path=Path("method1.json"),
            results={("s1", "t1"): make_result("s1", "t1", 4, 2, status="failed")},
        )
        method_two = ComparisonMethod(
            name="Method 2",
            path=Path("method2.json"),
            results={("s1", "t1"): make_result("s1", "t1", 4, 2, status="failed")},
        )
        method_three = ComparisonMethod(
            name="Method 3",
            path=Path("method3.json"),
            results={("s1", "t1"): make_result("s1", "t1", 4, 1, status="failed")},
        )

        rows = build_comparison_rows(queue_tasks, [method_one, method_two, method_three])

        self.assertEqual(rows[7]["cells"], ["2️⃣", "2️⃣", "1️⃣"])
        self.assertEqual(rows[7]["best_indexes"], [0, 1])

    def test_all_failed_row_has_no_best_highlight(self):
        queue_tasks = [("s1", "t1", "Task", "Session")]
        method_one = ComparisonMethod(
            name="Method 1",
            path=Path("method1.json"),
            results={("s1", "t1"): make_result("s1", "t1", 4, 0, status="failed")},
        )
        method_two = ComparisonMethod(
            name="Method 2",
            path=Path("method2.json"),
            results={("s1", "t1"): make_result("s1", "t1", 4, 0, status="failed")},
        )

        rows = build_comparison_rows(queue_tasks, [method_one, method_two])

        self.assertEqual(rows[7]["cells"], ["❌", "❌"])
        self.assertEqual(rows[7]["best_indexes"], [])

    def test_invalid_export_id_is_rejected(self):
        payload = {
            "id": "not-a-valid-id",
            "results": [make_result("s1", "t1", 1, 1, status="passed")],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as fh:
            json.dump(payload, fh)
            path = Path(fh.name)

        try:
            with self.assertRaises(ValueError):
                load_comparison_method(path)
        finally:
            path.unlink(missing_ok=True)

    def test_valid_export_loads_lookup(self):
        payload = {
            "statistics": make_statistics(total_tasks=1, passed_tasks=1, total_checks=1, passed_checks=1),
            "results": [make_result("s1", "t1", 1, 1, status="passed")],
        }
        payload["id"] = calculate_export_id(payload)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as fh:
            json.dump(payload, fh)
            path = Path(fh.name)

        try:
            method = load_comparison_method(path)
            self.assertIn(("s1", "t1"), method.results)
            self.assertEqual(method.statistics["total_tasks"], 1)
            self.assertEqual(method.name, path.stem)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
