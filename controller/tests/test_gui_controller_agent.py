import unittest
from unittest.mock import Mock, mock_open, patch

from task_agent_utils import extract_original_task_command


class TestGuiControllerAgentHelpers(unittest.TestCase):
    def test_extract_original_task_command_returns_stripped_content(self):
        task = {"content": "  inspect the target area  "}

        self.assertEqual(extract_original_task_command(task), "inspect the target area")

    def test_extract_original_task_command_ignores_aliases(self):
        task = {
            "content": "original command",
            "content_aliases": ["alias command"],
        }

        self.assertEqual(extract_original_task_command(task), "original command")

    def test_extract_original_task_command_returns_empty_for_blank_content(self):
        self.assertEqual(extract_original_task_command({"content": "   \n"}), "")

    def test_extract_original_task_command_returns_empty_for_missing_or_invalid_task(self):
        self.assertEqual(extract_original_task_command({}), "")
        self.assertEqual(extract_original_task_command(None), "")

    def test_shortcut_modifier_uses_command_on_macos(self):
        UAVControllerGUI = self._import_gui_controller()
        with patch("gui_controller.platform.system", return_value="Darwin"):
            self.assertEqual(UAVControllerGUI._shortcut_modifier(), "Command")

    def test_shortcut_modifier_uses_control_off_macos(self):
        UAVControllerGUI = self._import_gui_controller()
        with patch("gui_controller.platform.system", return_value="Windows"):
            self.assertEqual(UAVControllerGUI._shortcut_modifier(), "Control")

    def test_tasks_copy_shortcut_copies_original_command_on_tasks_tab(self):
        UAVControllerGUI = self._import_gui_controller()
        controller = object.__new__(UAVControllerGUI)
        controller.notebook = _FakeNotebook("Tasks")
        controller.task_listbox = _FakeListbox(has_selection=True)
        controller.copy_original_called = False

        def copy_original_command():
            controller.copy_original_called = True

        controller.copy_original_command = copy_original_command

        result = controller.handle_tasks_copy_shortcut(None)

        self.assertEqual(result, "break")
        self.assertTrue(controller.copy_original_called)

    def test_tasks_copy_shortcut_ignores_other_tabs(self):
        UAVControllerGUI = self._import_gui_controller()
        controller = object.__new__(UAVControllerGUI)
        controller.notebook = _FakeNotebook("History")
        controller.task_listbox = _FakeListbox(has_selection=True)
        controller.copy_original_called = False

        def copy_original_command():
            controller.copy_original_called = True

        controller.copy_original_command = copy_original_command

        result = controller.handle_tasks_copy_shortcut(None)

        self.assertIsNone(result)
        self.assertFalse(controller.copy_original_called)

    def test_copy_original_command_status_includes_task_title(self):
        UAVControllerGUI = self._import_gui_controller()
        controller = object.__new__(UAVControllerGUI)
        controller.root = _FakeRoot()
        controller.task_data = [
            {"id": "task-1", "name": "Survey Alpha", "content": "scan alpha"}
        ]
        controller.status_text = None

        controller.get_selected_task_id = lambda: "task-1"
        controller.update_status = lambda message: setattr(controller, "status_text", message)

        controller.copy_original_command()

        self.assertEqual(controller.root.clipboard, "scan alpha")
        self.assertEqual(
            controller.status_text,
            "Original command copied to clipboard: Survey Alpha",
        )

    def test_fetch_session_screenshot_forwards_show_label_option(self):
        UAVControllerGUI = self._import_gui_controller()
        controller = object.__new__(UAVControllerGUI)
        controller.api_server = Mock()
        controller.api_server.api_get_session_screenshot.return_value = b"image"

        response = controller.fetch_session_screenshot(
            fmt="svg",
            width=640,
            height=480,
            show_status=True,
            show_label=False,
        )

        self.assertEqual(response, b"image")
        controller.api_server.api_get_session_screenshot.assert_called_once_with(
            fmt="svg",
            width=640,
            height=480,
            show_status=True,
            show_label=False,
            show_error=True,
        )

    def test_refresh_request_history_replaces_entries(self):
        UAVControllerGUI = self._import_gui_controller()
        controller = object.__new__(UAVControllerGUI)
        entries = [
            {
                "request_id": "request-1",
                "method": "POST",
                "path": "/drones/drone-1/command",
                "request_body": {"command": "take_off", "parameters": {"altitude": 10}},
                "status_code": 200,
                "success": True,
            }
        ]
        controller.command_history = [{"path": "/stale"}]
        controller.api_server = Mock()
        controller.api_server.api_get_current_session_request_history.return_value = {
            "request_history": entries
        }
        controller.logger = Mock()
        controller._is_gui_available = lambda: True
        controller._clear_history_selection_and_details = Mock()
        controller.refresh_history_tree = Mock()
        controller.update_status = Mock()

        controller.refresh_request_history()

        self.assertEqual(controller.command_history, entries)
        controller.api_server.api_get_current_session_request_history.assert_called_once_with(
            limit=1000,
            show_error=False,
        )
        controller._clear_history_selection_and_details.assert_called_once_with()
        controller.refresh_history_tree.assert_called_once_with()
        controller.update_status.assert_called_once_with("Loaded 1 request history entry")

    def test_refresh_request_history_clears_invalid_response(self):
        UAVControllerGUI = self._import_gui_controller()
        controller = object.__new__(UAVControllerGUI)
        controller.command_history = [{"command": "stale"}]
        controller.api_server = Mock()
        controller.api_server.api_get_current_session_request_history.return_value = None
        controller.logger = Mock()
        controller._is_gui_available = lambda: True
        controller._clear_history_selection_and_details = Mock()
        controller.refresh_history_tree = Mock()
        controller.update_status = Mock()

        controller.refresh_request_history()

        self.assertEqual(controller.command_history, [])
        controller.refresh_history_tree.assert_called_once_with()
        controller.update_status.assert_called_once_with(
            "No current session or request history is unavailable"
        )

    def test_clear_request_history_deletes_remote_history_and_clears_loaded_entries(self):
        UAVControllerGUI = self._import_gui_controller()
        controller = object.__new__(UAVControllerGUI)
        controller.command_history = [{"path": "/stale"}]
        controller.api_server = Mock()
        controller.api_server.api_clear_current_session_request_history.return_value = {
            "cleared": True,
            "session_id": "session-1",
            "cleared_count": 2,
        }
        controller.logger = Mock()
        controller._is_gui_available = lambda: True
        controller._clear_history_selection_and_details = Mock()
        controller.refresh_history_tree = Mock()
        controller.update_status = Mock()

        with patch("gui_controller.messagebox.askyesno", return_value=True):
            controller.clear_request_history()

        controller.api_server.api_clear_current_session_request_history.assert_called_once_with(
            show_error=False
        )
        self.assertEqual(controller.command_history, [])
        controller._clear_history_selection_and_details.assert_called_once_with()
        controller.refresh_history_tree.assert_called_once_with()
        controller.update_status.assert_called_once_with("Cleared 2 request history entries")

    def test_clear_request_history_cancel_does_not_call_api(self):
        UAVControllerGUI = self._import_gui_controller()
        controller = object.__new__(UAVControllerGUI)
        controller.api_server = Mock()
        controller._is_gui_available = lambda: True

        with patch("gui_controller.messagebox.askyesno", return_value=False):
            controller.clear_request_history()

        controller.api_server.api_clear_current_session_request_history.assert_not_called()

    def test_history_tab_selection_refreshes_request_history(self):
        UAVControllerGUI = self._import_gui_controller()
        controller = object.__new__(UAVControllerGUI)
        controller.refresh_request_history = Mock()
        controller.refresh_statistics = Mock()

        controller.on_tab_changed(_FakeTabEvent("History"))

        controller.refresh_request_history.assert_called_once_with()
        controller.refresh_statistics.assert_not_called()

    def test_request_history_filters_match_method_privilege_endpoint_and_success(self):
        UAVControllerGUI = self._import_gui_controller()
        entry = {
            "method": "POST",
            "client_privilege": "agent",
            "path": "/drones/drone-1/command",
            "success": True,
        }

        self.assertTrue(
            UAVControllerGUI._history_entry_matches_filters(
                entry, "POST", "AGENT", "drone-1", "Success"
            )
        )
        self.assertFalse(
            UAVControllerGUI._history_entry_matches_filters(
                entry, "GET", "AGENT", "drone-1", "Success"
            )
        )
        self.assertFalse(
            UAVControllerGUI._history_entry_matches_filters(
                entry, "POST", "ADMIN", "drone-1", "Success"
            )
        )
        self.assertFalse(
            UAVControllerGUI._history_entry_matches_filters(
                entry, "POST", "AGENT", "target", "Success"
            )
        )
        self.assertFalse(
            UAVControllerGUI._history_entry_matches_filters(
                entry, "POST", "AGENT", "drone-1", "Failure"
            )
        )

    def test_request_history_details_preserve_additional_fields(self):
        UAVControllerGUI = self._import_gui_controller()

        details = UAVControllerGUI._format_request_history_details({
            "request_id": "request-1",
            "method": "GET",
            "path": "/health",
            "success": True,
            "server_node": "node-a",
        })

        self.assertEqual(details["Request ID"], "request-1")
        self.assertEqual(details["Path"], "/health")
        self.assertEqual(details["server_node"], "node-a")

    def test_history_timestamp_uses_millisecond_display_format(self):
        UAVControllerGUI = self._import_gui_controller()

        self.assertEqual(
            UAVControllerGUI._format_history_timestamp("2026-01-01T15:00:00.123456"),
            "2026-01-01 15:00:00.123",
        )
        self.assertEqual(
            UAVControllerGUI._format_history_timestamp("2026-01-01T15:00:00Z"),
            "2026-01-01 15:00:00.000",
        )

    def test_request_history_replay_uses_method_path_body_and_query_params(self):
        UAVControllerGUI = self._import_gui_controller()

        normalized = UAVControllerGUI._normalize_request_history_entry_for_replay({
            "method": "POST",
            "path": "/drones/drone-1/command",
            "request_body": {"command": "land", "parameters": {}},
            "query_params": {"wait": "true"},
        })

        self.assertEqual(normalized, {
            "method": "POST",
            "endpoint": "/drones/drone-1/command",
            "payload": {"command": "land", "parameters": {}},
            "params": {"wait": "true"},
        })

    def test_request_history_replay_preserves_move_towards_query_params(self):
        UAVControllerGUI = self._import_gui_controller()

        normalized = UAVControllerGUI._normalize_request_history_entry_for_replay({
            "method": "POST",
            "path": "/drones/f446e041/command/move_towards",
            "request_body": None,
            "query_params": {
                "distance": "50.0",
                "heading": "280.0",
                "dz": "0.0",
            },
        })

        self.assertEqual(normalized["payload"], None)
        self.assertEqual(normalized["params"], {
            "distance": "50.0",
            "heading": "280.0",
            "dz": "0.0",
        })

    def test_request_history_replay_defaults_missing_query_params_for_legacy_entries(self):
        UAVControllerGUI = self._import_gui_controller()

        normalized = UAVControllerGUI._normalize_request_history_entry_for_replay({
            "method": "GET",
            "path": "/health",
        })

        self.assertEqual(normalized["params"], {})

    def test_request_history_replay_preserves_repeated_query_values(self):
        UAVControllerGUI = self._import_gui_controller()

        normalized = UAVControllerGUI._normalize_request_history_entry_for_replay({
            "method": "GET",
            "path": "/example",
            "query_params": {"tag": ["alpha", "beta"]},
        })

        self.assertEqual(normalized["params"], {"tag": ["alpha", "beta"]})

    def test_load_history_and_run_sends_query_params_to_api_client(self):
        UAVControllerGUI = self._import_gui_controller()
        controller = object.__new__(UAVControllerGUI)
        controller.api_server = Mock()
        controller.logger = Mock()
        controller.update_status = Mock()
        controller.root = Mock()
        controller.root.after.side_effect = lambda delay, callback: callback()
        history_line = (
            '{"method":"POST",'
            '"path":"/drones/f446e041/command/move_towards",'
            '"request_body":null,'
            '"query_params":{"distance":"50.0","heading":"280.0","dz":"0.0"}}\n'
        )

        with (
            patch(
                "gui_controller.filedialog.askopenfilename",
                return_value="/tmp/history.jsonl",
            ),
            patch("builtins.open", mock_open(read_data=history_line)),
            patch("gui_controller.threading.Thread", _ImmediateThread),
            patch("gui_controller.messagebox.showinfo"),
        ):
            controller.load_history_and_run()

        controller.api_server.api_generic_request.assert_called_once_with(
            "POST",
            "/drones/f446e041/command/move_towards",
            None,
            params={
                "distance": "50.0",
                "heading": "280.0",
                "dz": "0.0",
            },
        )

    def test_refresh_all_data_does_not_refresh_request_history(self):
        UAVControllerGUI = self._import_gui_controller()
        controller = object.__new__(UAVControllerGUI)
        controller._is_gui_available = lambda: True
        controller._cached_current_session_payload = None
        controller.refresh_statistics = Mock()
        controller.refresh_drones = Mock()
        controller.refresh_targets = Mock()
        controller.refresh_obstacles = Mock()
        controller.refresh_environments = Mock()
        controller.refresh_tasks = Mock()
        controller.refresh_request_history = Mock()

        controller.refresh_all_data(prefetched_data={"session": {"tasks": []}})

        controller.refresh_request_history.assert_not_called()

    def test_request_history_tree_handles_duplicate_and_missing_request_ids(self):
        UAVControllerGUI = self._import_gui_controller()
        controller = object.__new__(UAVControllerGUI)
        controller.command_history = [
            {
                "request_id": "duplicate",
                "method": "GET",
                "client_privilege": "admin",
                "path": "/first",
                "status_code": 200,
                "success": True,
            },
            {
                "request_id": "duplicate",
                "method": "POST",
                "path": "/second",
                "status_code": 201,
                "success": True,
            },
            {
                "method": "DELETE",
                "path": "/third",
                "status_code": 204,
                "success": True,
            },
        ]
        controller.history_tree = _FakeHistoryTree()

        controller.refresh_history_tree()

        self.assertEqual(len(controller.history_tree.items), 3)
        self.assertEqual(len(controller.history_index_by_iid), 3)
        self.assertEqual(
            [entry["path"] for entry in controller.history_index_by_iid.values()],
            ["/first", "/second", "/third"],
        )
        self.assertEqual(
            controller.history_tree.items["duplicate"],
            ("-", "GET", "admin", "/first", "200", "🟢 Yes"),
        )
        self.assertEqual(
            next(
                values
                for values in controller.history_tree.items.values()
                if values[3] == "/second"
            ),
            ("-", "POST", "-", "/second", "201", "🟢 Yes"),
        )

    def test_save_filtered_history_exports_only_matching_raw_entries(self):
        UAVControllerGUI = self._import_gui_controller()
        controller = object.__new__(UAVControllerGUI)
        matching_entry = {
            "request_id": "request-1",
            "method": "POST",
            "client_privilege": "agent",
            "path": "/drones/drone-1/command/move_towards",
            "status_code": 200,
            "success": True,
            "request_body": {"command": "move_towards"},
            "query_params": {"distance": "50", "heading": "90", "tag": ["a", "b"]},
            "extra_server_field": {"preserved": True},
        }
        controller.command_history = [
            matching_entry,
            {
                "request_id": "request-2",
                "method": "GET",
                "client_privilege": "agent",
                "path": "/drones",
                "status_code": 200,
                "success": True,
                "query_params": {},
            },
            {
                "request_id": "request-3",
                "method": "POST",
                "client_privilege": "system",
                "path": "/drones/drone-1/command/move_towards",
                "status_code": 422,
                "success": False,
                "query_params": {"distance": "50"},
            },
        ]
        controller.history_method_filter_var = _FakeStringVar("POST")
        controller.history_privilege_filter_var = _FakeStringVar("AGENT")
        controller.history_endpoint_filter_var = _FakeStringVar("move_towards")
        controller.history_success_filter_var = _FakeStringVar("Success")
        controller.current_session_name = "Path Planning Hard 4"
        controller.logger = Mock()
        controller._save_history_entries = Mock(return_value="/tmp/filtered.jsonl")

        with patch("gui_controller.messagebox.showinfo") as showinfo:
            controller.save_filtered_history_to_json()

        controller._save_history_entries.assert_called_once_with(
            [matching_entry],
            "Path_Planning_Hard_4-filtered_entries",
        )
        showinfo.assert_called_once_with("Saved", "Filtered history saved to /tmp/filtered.jsonl")

    def test_save_filtered_history_warns_when_no_entries_match(self):
        UAVControllerGUI = self._import_gui_controller()
        controller = object.__new__(UAVControllerGUI)
        controller.command_history = [
            {
                "request_id": "request-1",
                "method": "GET",
                "client_privilege": "agent",
                "path": "/drones",
                "success": True,
            }
        ]
        controller.history_method_filter_var = _FakeStringVar("POST")
        controller.history_privilege_filter_var = _FakeStringVar("AGENT")
        controller.history_endpoint_filter_var = _FakeStringVar("move_towards")
        controller.history_success_filter_var = _FakeStringVar("Success")
        controller.current_session_name = "Path Planning Hard 4"
        controller.logger = Mock()
        controller._save_history_entries = Mock()

        with patch("gui_controller.messagebox.showwarning") as showwarning:
            controller.save_filtered_history_to_json()

        controller._save_history_entries.assert_not_called()
        showwarning.assert_called_once_with(
            "No Matching Entries",
            "No history entries match the current filters.",
        )

    def test_history_select_all_selects_every_visible_row(self):
        UAVControllerGUI = self._import_gui_controller()
        controller = object.__new__(UAVControllerGUI)
        controller.history_tree = _FakeHistoryTree()
        controller.history_tree.items = {
            "request-1": (),
            "request-2": (),
            "request-3": (),
        }

        result = controller.handle_history_select_all()

        self.assertEqual(result, "break")
        self.assertEqual(
            controller.history_tree.selected,
            ("request-1", "request-2", "request-3"),
        )

    def _import_gui_controller(self):
        try:
            from gui_controller import UAVControllerGUI
        except ModuleNotFoundError as exc:
            if exc.name == "_tkinter":
                self.skipTest("tkinter is not available in this Python environment")
            raise
        return UAVControllerGUI


class _FakeNotebook:
    def __init__(self, current_tab):
        self.current_tab = current_tab

    def select(self):
        return "selected-tab"

    def tab(self, selected, option):
        return self.current_tab


class _FakeListbox:
    def __init__(self, has_selection):
        self.has_selection = has_selection

    def curselection(self):
        return (0,) if self.has_selection else ()


class _FakeRoot:
    def __init__(self):
        self.clipboard = None

    def clipboard_clear(self):
        self.clipboard = ""

    def clipboard_append(self, content):
        self.clipboard = content


class _FakeStringVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class _FakeHistoryTree:
    def __init__(self):
        self.items = {}
        self.selected = ()

    def get_children(self):
        return tuple(self.items)

    def delete(self, iid):
        self.items.pop(iid, None)

    def insert(self, parent, position, iid, values):
        if iid in self.items:
            raise ValueError(f"Duplicate iid: {iid}")
        self.items[iid] = values

    def selection_set(self, items):
        self.selected = tuple(items)


class _FakeTabEvent:
    def __init__(self, tab_name):
        self.widget = _FakeNotebook(tab_name)


class _ImmediateThread:
    def __init__(self, target, daemon):
        self.target = target
        self.daemon = daemon

    def start(self):
        self.target()


if __name__ == "__main__":
    unittest.main()
