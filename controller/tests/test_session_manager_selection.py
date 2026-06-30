import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    from session_manager import SessionManager, TK_CONTROL_MASK
except ModuleNotFoundError as exc:
    if exc.name not in {"_tkinter", "requests"}:
        raise
    SessionManager = None
    IMPORT_SKIP_REASON = f"{exc.name} is not available in this Python environment"
    TK_CONTROL_MASK = 0x0004
else:
    IMPORT_SKIP_REASON = None

TK_OPTION_MASK = 0x0010


class TestSessionManagerSelection(unittest.TestCase):
    def setUp(self):
        if SessionManager is None:
            self.skipTest(IMPORT_SKIP_REASON)

    def test_toggle_modifier_ignores_state_mask_on_macos(self):
        with patch("session_manager.platform.system", return_value="Darwin"):
            self.assertFalse(SessionManager._is_session_toggle_select_modifier(TK_OPTION_MASK))
            self.assertFalse(SessionManager._is_session_toggle_select_modifier(TK_CONTROL_MASK))

    def test_toggle_modifier_uses_control_off_macos(self):
        with patch("session_manager.platform.system", return_value="Linux"):
            self.assertTrue(SessionManager._is_session_toggle_select_modifier(TK_CONTROL_MASK))
            self.assertFalse(SessionManager._is_session_toggle_select_modifier(TK_OPTION_MASK))

    def test_option_click_does_not_toggle_session_selection_on_macos(self):
        manager = object.__new__(SessionManager)
        manager.sessions = [{}, {}, {}]
        manager.sessions_listbox = _FakeListbox(size=3, selected={0})
        manager._selection_anchor_index = 0
        manager.selection_changed = False
        manager.on_session_select = lambda event: setattr(manager, "selection_changed", True)

        with patch("session_manager.platform.system", return_value="Darwin"):
            result = manager.handle_session_mouse_selection(SimpleNamespace(y=2, state=TK_OPTION_MASK))

        self.assertEqual(result, "break")
        self.assertEqual(manager.sessions_listbox.selected, {2})
        self.assertEqual(manager._selection_anchor_index, 2)
        self.assertTrue(manager.selection_changed)

    def test_control_click_toggles_session_selection_off_macos(self):
        manager = object.__new__(SessionManager)
        manager.sessions = [{}, {}, {}]
        manager.sessions_listbox = _FakeListbox(size=3, selected={0})
        manager._selection_anchor_index = 0
        manager.on_session_select = lambda event: None

        with patch("session_manager.platform.system", return_value="Windows"):
            result = manager.handle_session_mouse_selection(SimpleNamespace(y=1, state=TK_CONTROL_MASK))

        self.assertEqual(result, "break")
        self.assertEqual(manager.sessions_listbox.selected, {0, 1})
        self.assertEqual(manager._selection_anchor_index, 1)

    def test_forced_toggle_does_not_depend_on_event_state_mask(self):
        manager = object.__new__(SessionManager)
        manager.sessions = [{}, {}, {}]
        manager.sessions_listbox = _FakeListbox(size=3, selected={0})
        manager._selection_anchor_index = 0
        manager.on_session_select = lambda event: None

        result = manager.handle_session_mouse_selection(
            SimpleNamespace(y=2, state=0),
            force_toggle=True,
        )

        self.assertEqual(result, "break")
        self.assertEqual(manager.sessions_listbox.selected, {0, 2})
        self.assertEqual(manager._selection_anchor_index, 2)


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
