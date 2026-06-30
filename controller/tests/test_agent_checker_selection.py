import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    from check_ui.agent_checker import AgentCheckerApp, TK_CONTROL_MASK
except ModuleNotFoundError as exc:
    if exc.name not in {"_tkinter", "requests"}:
        raise
    AgentCheckerApp = None
    IMPORT_SKIP_REASON = f"{exc.name} is not available in this Python environment"
    TK_CONTROL_MASK = 0x0004
else:
    IMPORT_SKIP_REASON = None


class TestAgentCheckerSelection(unittest.TestCase):
    def setUp(self):
        if AgentCheckerApp is None:
            self.skipTest(IMPORT_SKIP_REASON)

    def test_toggle_modifier_ignores_control_on_macos(self):
        with patch("check_ui.agent_checker.platform.system", return_value="Darwin"):
            self.assertFalse(AgentCheckerApp._is_listbox_toggle_select_modifier(TK_CONTROL_MASK))

    def test_control_click_is_plain_selection_on_macos(self):
        app = object.__new__(AgentCheckerApp)
        listbox = _FakeListbox(size=3, selected={0})
        callback = _SelectionCallback()

        with patch("check_ui.agent_checker.platform.system", return_value="Darwin"):
            result = app.handle_platform_listbox_selection(
                SimpleNamespace(y=2, state=TK_CONTROL_MASK),
                listbox,
                callback,
            )

        self.assertEqual(result, "break")
        self.assertEqual(listbox.selected, {2})
        self.assertEqual(listbox._agent_checker_selection_anchor, 2)
        self.assertTrue(callback.called)

    def test_forced_command_binding_toggles_on_macos(self):
        app = object.__new__(AgentCheckerApp)
        listbox = _FakeListbox(size=3, selected={0})
        callback = _SelectionCallback()

        with patch("check_ui.agent_checker.platform.system", return_value="Darwin"):
            result = app.handle_platform_listbox_selection(
                SimpleNamespace(y=2, state=0),
                listbox,
                callback,
                force_toggle=True,
            )

        self.assertEqual(result, "break")
        self.assertEqual(listbox.selected, {0, 2})
        self.assertEqual(listbox._agent_checker_selection_anchor, 2)
        self.assertTrue(callback.called)

    def test_control_click_toggles_off_macos(self):
        app = object.__new__(AgentCheckerApp)
        listbox = _FakeListbox(size=3, selected={0})
        callback = _SelectionCallback()

        with patch("check_ui.agent_checker.platform.system", return_value="Linux"):
            result = app.handle_platform_listbox_selection(
                SimpleNamespace(y=1, state=TK_CONTROL_MASK),
                listbox,
                callback,
            )

        self.assertEqual(result, "break")
        self.assertEqual(listbox.selected, {0, 1})
        self.assertEqual(listbox._agent_checker_selection_anchor, 1)
        self.assertTrue(callback.called)

    def test_session_and_queue_listboxes_keep_independent_selection(self):
        selection_panel_source = inspect.getsource(AgentCheckerApp.create_selection_panel)
        control_panel_source = inspect.getsource(AgentCheckerApp.create_control_panel)

        self.assertIn("exportselection=False", selection_panel_source)
        self.assertIn("exportselection=False", control_panel_source)

    def test_queue_scoped_result_rows_exclude_results_not_in_queue(self):
        app = object.__new__(AgentCheckerApp)
        app.selected_tasks = [
            ("s2", "t2", "Queued Task 2", "Session 2"),
            ("s1", "t1", "Queued Task 1", "Session 1"),
            ("s3", "t3", "Queued Task 3", "Session 3"),
        ]
        app.task_check_results = {
            ("s1", "t1"): {"status": "passed"},
            ("s2", "t2"): {"status": "failed"},
            ("stale", "task"): {"status": "passed"},
        }

        rows = app.get_queue_scoped_result_rows()

        self.assertEqual(
            [(session_id, task_id) for session_id, task_id, *_ in rows],
            [("s2", "t2"), ("s1", "t1")],
        )
        self.assertEqual([row[4]["status"] for row in rows], ["failed", "passed"])

    def test_queue_dependent_buttons_disable_when_queue_is_empty(self):
        app = object.__new__(AgentCheckerApp)
        app.selected_tasks = []
        app.compare_button = _FakeButton()
        app.export_results_button = _FakeButton()
        app.import_results_button = _FakeButton()

        app.update_queue_dependent_buttons()

        self.assertEqual(app.compare_button.state, "disabled")
        self.assertEqual(app.export_results_button.state, "disabled")
        self.assertEqual(app.import_results_button.state, "disabled")

    def test_queue_dependent_buttons_enable_when_queue_has_tasks(self):
        app = object.__new__(AgentCheckerApp)
        app.selected_tasks = [("s1", "t1", "Task", "Session")]
        app.compare_button = _FakeButton()
        app.export_results_button = _FakeButton()
        app.import_results_button = _FakeButton()

        app.update_queue_dependent_buttons()

        self.assertEqual(app.compare_button.state, "normal")
        self.assertEqual(app.export_results_button.state, "normal")
        self.assertEqual(app.import_results_button.state, "normal")

    def test_empty_filter_matches_sessions_and_tasks(self):
        app = object.__new__(AgentCheckerApp)

        self.assertTrue(app.task_matches_filter({"id": "t1", "name": "Task"}, ""))

    def test_task_name_and_id_filter_is_case_insensitive(self):
        app = object.__new__(AgentCheckerApp)
        task = {"id": "Task-42", "name": "Inspect Bridge"}

        self.assertTrue(app.task_matches_filter(task, "task-42"))
        self.assertTrue(app.task_matches_filter(task, "BRIDGE"))
        self.assertFalse(app.task_matches_filter(task, "survey"))

    def test_task_category_fields_match_filter(self):
        app = object.__new__(AgentCheckerApp)
        task = {
            "id": "t1",
            "name": "Task",
            "category": "Navigation",
            "execution_check_apis": {
                "checks": [
                    {"category": "Task Progress", "endpoint": "/check/progress"},
                    {"task_type": "Delivery", "endpoint": "/check/delivery"},
                ]
            },
        }

        self.assertTrue(app.task_matches_filter(task, "navigation"))
        self.assertTrue(app.task_matches_filter(task, "task progress"))
        self.assertTrue(app.task_matches_filter(task, "delivery"))

    def test_task_visibility_filter_matches_session_name(self):
        app = object.__new__(AgentCheckerApp)
        session = {"id": "s1", "name": "Thermal Session"}
        task = {"id": "t1", "name": "Unrelated Task"}

        self.assertTrue(app.task_visible_for_filter(task, session, "thermal"))
        self.assertTrue(app.task_visible_for_filter(task, session, "SESSION"))
        self.assertFalse(app.task_visible_for_filter(task, session, "delivery"))

    def test_refresh_sessions_list_ignores_filter_text(self):
        app = object.__new__(AgentCheckerApp)
        app.sessions_data = [
            {"id": "source-0", "name": "Hidden"},
            {"id": "source-1", "name": "Visible"},
        ]
        app.sessions_listbox = _FakeSessionListbox()
        app.filter_var = _FakeVar("visible")

        app.refresh_sessions_list()

        self.assertEqual(
            app.sessions_listbox.items,
            ["Hidden (source-0)", "Visible (source-1)"],
        )
        self.assertEqual(app.filtered_session_indices, [0, 1])

    def test_filtered_listbox_index_resolves_to_source_session(self):
        app = object.__new__(AgentCheckerApp)
        app.sessions_data = [
            {"id": "source-0", "name": "Hidden"},
            {"id": "source-1", "name": "Visible"},
        ]
        app.filtered_session_indices = [1]

        self.assertEqual(app.get_session_for_listbox_index(0)["id"], "source-1")
        self.assertIsNone(app.get_session_for_listbox_index(1))

    def test_skip_passed_confirmation_yes_unchecks_skip_already_checked(self):
        app = object.__new__(AgentCheckerApp)
        app.root = object()
        app.skip_passed_var = _FakeVar(True)
        app.skip_checked_var = _FakeVar(True)

        with patch("check_ui.agent_checker.messagebox.askyesno", return_value=True) as askyesno:
            app.handle_skip_passed_toggle()

        askyesno.assert_called_once()
        self.assertTrue(app.skip_passed_var.get())
        self.assertFalse(app.skip_checked_var.get())

    def test_skip_passed_confirmation_no_restores_skip_passed_unchecked(self):
        app = object.__new__(AgentCheckerApp)
        app.root = object()
        app.skip_passed_var = _FakeVar(True)
        app.skip_checked_var = _FakeVar(True)

        with patch("check_ui.agent_checker.messagebox.askyesno", return_value=False) as askyesno:
            app.handle_skip_passed_toggle()

        askyesno.assert_called_once()
        self.assertFalse(app.skip_passed_var.get())
        self.assertTrue(app.skip_checked_var.get())

    def test_skip_passed_without_skip_already_checked_does_not_prompt(self):
        app = object.__new__(AgentCheckerApp)
        app.skip_passed_var = _FakeVar(True)
        app.skip_checked_var = _FakeVar(False)

        with patch("check_ui.agent_checker.messagebox.askyesno") as askyesno:
            app.handle_skip_passed_toggle()

        askyesno.assert_not_called()
        self.assertTrue(app.skip_passed_var.get())
        self.assertFalse(app.skip_checked_var.get())


class _SelectionCallback:
    def __init__(self):
        self.called = False

    def __call__(self, event):
        self.called = True


class _FakeButton:
    def __init__(self):
        self.state = None

    def config(self, **kwargs):
        self.state = kwargs.get("state", self.state)


class _FakeVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _FakeSessionListbox:
    def __init__(self):
        self.items = []
        self.selected = set()

    def delete(self, first, last=None):
        self.items.clear()
        self.selected.clear()

    def insert(self, index, value):
        self.items.append(value)

    def selection_set(self, index):
        if index == "end":
            index = len(self.items) - 1
        self.selected.add(index)

    def curselection(self):
        return tuple(sorted(self.selected))


class _FakeListbox:
    def __init__(self, *, size, selected):
        self._size = size
        self.selected = set(selected)
        self.activated = None
        self.seen = None
        self.anchor = None
        self.focused = False

    def focus_set(self):
        self.focused = True

    def nearest(self, y):
        return y

    def size(self):
        return self._size

    def selection_includes(self, index):
        return index in self.selected

    def selection_clear(self, first, last=None):
        if last is None:
            self.selected.discard(first)
            return
        self.selected.clear()

    def selection_set(self, first, last=None):
        if last is None:
            self.selected.add(first)
            return
        self.selected.update(range(first, last + 1))

    def selection_anchor(self, index):
        self.anchor = index

    def activate(self, index):
        self.activated = index

    def see(self, index):
        self.seen = index


if __name__ == "__main__":
    unittest.main()
