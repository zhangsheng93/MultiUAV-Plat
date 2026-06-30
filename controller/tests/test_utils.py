import unittest
import math
from unittest.mock import patch
from utils import (
    parse_vertices_from_text,
    format_vertices_to_text,
    distance_point_to_point,
    is_point_in_circle,
    is_point_in_ellipse,
    is_point_in_polygon,
    clamp,
    distance_point_to_line,
    snap_value_to_grid,
    sanitize_filename,
    create_new_names,
    set_window_geometry_and_center,
)


class FakeWindow:
    def __init__(self, *, state="normal", screenwidth=1920, screenheight=1080, pointer=(0, 0)):
        self._state = state
        self._screenwidth = screenwidth
        self._screenheight = screenheight
        self._pointer = pointer
        self.geometry_calls = []
        self.attributes_calls = []
        self.withdrawn = False
        self.deiconified = False
        self.lifted = False
        self.grabbed = False

    def state(self):
        return self._state

    def withdraw(self):
        self.withdrawn = True
        self._state = "withdrawn"

    def deiconify(self):
        self.deiconified = True
        self._state = "normal"

    def transient(self, parent):
        self.transient_parent = parent

    def geometry(self, value):
        self.geometry_calls.append(value)

    def grab_set(self):
        self.grabbed = True

    def winfo_width(self):
        return 0

    def winfo_height(self):
        return 0

    def winfo_reqwidth(self):
        return 0

    def winfo_reqheight(self):
        return 0

    def winfo_screenwidth(self):
        return self._screenwidth

    def winfo_screenheight(self):
        return self._screenheight

    def winfo_pointerx(self):
        return self._pointer[0]

    def winfo_pointery(self):
        return self._pointer[1]

    def lift(self):
        self.lifted = True

    def attributes(self, *args):
        self.attributes_calls.append(args)

    def after_idle(self, callback):
        self.after_idle_callback = callback


class FakeParent:
    def __init__(self, *, rootx, rooty, width, height, state="normal", viewable=True):
        self._rootx = rootx
        self._rooty = rooty
        self._width = width
        self._height = height
        self._state = state
        self._viewable = viewable
        self.updated = False

    def winfo_viewable(self):
        return self._viewable

    def state(self):
        return self._state

    def update_idletasks(self):
        self.updated = True

    def winfo_rootx(self):
        return self._rootx

    def winfo_rooty(self):
        return self._rooty

    def winfo_width(self):
        return self._width

    def winfo_height(self):
        return self._height

class TestUtils(unittest.TestCase):

    def test_parse_vertices_from_text_valid(self):
        text = "10, 20\n30, 40\n50, 60"
        expected = [{'x': 10.0, 'y': 20.0}, {'x': 30.0, 'y': 40.0}, {'x': 50.0, 'y': 60.0}]
        self.assertEqual(parse_vertices_from_text(text), expected)

    def test_parse_vertices_from_text_with_comments_and_whitespace(self):
        text = "10, 20 # comment\n  30, 40  \n"
        expected = [{'x': 10.0, 'y': 20.0}, {'x': 30.0, 'y': 40.0}]
        self.assertEqual(parse_vertices_from_text(text), expected)

    def test_parse_vertices_from_text_invalid_format(self):
        text = "10 20" # Missing comma
        with self.assertRaises(ValueError):
            parse_vertices_from_text(text)

    def test_parse_vertices_from_text_invalid_number(self):
        text = "10, abc"
        with self.assertRaises(ValueError):
            parse_vertices_from_text(text)

    def test_format_vertices_to_text(self):
        vertices = [{'x': 10.123, 'y': 20.456}, {'x': 30.0, 'y': 40.0}]
        expected = "10.12, 20.46\n30.00, 40.00"
        self.assertEqual(format_vertices_to_text(vertices), expected)

    def test_distance_point_to_point(self):
        self.assertAlmostEqual(distance_point_to_point(0, 0, 3, 4), 5.0)
        self.assertAlmostEqual(distance_point_to_point(1, 1, 1, 1), 0.0)

    def test_is_point_in_circle(self):
        self.assertTrue(is_point_in_circle(0, 0, 0, 0, 5))
        self.assertTrue(is_point_in_circle(3, 4, 0, 0, 5.0001))
        self.assertFalse(is_point_in_circle(6, 0, 0, 0, 5))

    def test_is_point_in_ellipse(self):
        # Ellipse centered at 0,0 with width=4, height=2 (semi-axes a=4, b=2 per implementation logic check)
        self.assertTrue(is_point_in_ellipse(0, 0, 0, 0, 4, 2))
        self.assertTrue(is_point_in_ellipse(4, 0, 0, 0, 4, 2))
        self.assertTrue(is_point_in_ellipse(0, 2, 0, 0, 4, 2))
        self.assertFalse(is_point_in_ellipse(5, 0, 0, 0, 4, 2))
        self.assertFalse(is_point_in_ellipse(0, 0, 0, 0, -1, 2)) # Invalid width

    def test_is_point_in_polygon(self):
        # Square 0,0 to 10,10
        vertices = [{'x': 0, 'y': 0}, {'x': 10, 'y': 0}, {'x': 10, 'y': 10}, {'x': 0, 'y': 10}]
        self.assertTrue(is_point_in_polygon(5, 5, vertices))
        self.assertFalse(is_point_in_polygon(15, 5, vertices))
        self.assertFalse(is_point_in_polygon(5, 5, [])) # Empty vertices

    def test_clamp(self):
        self.assertEqual(clamp(5, 0, 10), 5)
        self.assertEqual(clamp(-5, 0, 10), 0)
        self.assertEqual(clamp(15, 0, 10), 10)

    def test_distance_point_to_line(self):
        # Point on line
        self.assertAlmostEqual(distance_point_to_line(1, 1, 0, 0, 2, 2), 0.0)
        # Point off line (perpendicular distance)
        self.assertAlmostEqual(distance_point_to_line(0, 1, 0, 0, 2, 0), 1.0)
        # Point beyond segment (closest to endpoint)
        self.assertAlmostEqual(distance_point_to_line(3, 0, 0, 0, 2, 0), 1.0)
        # Zero length line
        self.assertAlmostEqual(distance_point_to_line(1, 0, 0, 0, 0, 0), 1.0)

    def test_snap_value_to_grid(self):
        self.assertEqual(snap_value_to_grid(12, 10), 10)
        self.assertEqual(snap_value_to_grid(16, 10), 20)
        self.assertEqual(snap_value_to_grid(12, 0), 12)

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("test file"), "test_file")
        self.assertEqual(sanitize_filename("test/file"), "test_file")
        self.assertEqual(sanitize_filename("test\\file"), "test_file")
        self.assertEqual(sanitize_filename("..test.."), "test")
        self.assertEqual(sanitize_filename(""), "file")

    def test_create_new_names_from_plain_prefix(self):
        self.assertEqual(
            create_new_names("New Session", n=3, exist_list=[]),
            ["New Session 1", "New Session 2", "New Session 3"]
        )

    def test_create_new_names_from_numbered_prefix(self):
        self.assertEqual(
            create_new_names("New Session 2", n=3, exist_list=["New Session 1"]),
            ["New Session 2", "New Session 3", "New Session 4"]
        )

    def test_create_new_names_from_numbered_prefix_skips_existing(self):
        self.assertEqual(
            create_new_names("New Session 2", n=2, exist_list=["New Session 1", "New Session 2", "New Session 4"]),
            ["New Session 5", "New Session 6"]
        )

    def test_windows_parent_on_left_monitor_preserves_negative_x(self):
        window = FakeWindow()
        parent = FakeParent(rootx=-1400, rooty=100, width=800, height=600)
        with patch("utils.platform.system", return_value="Windows"), \
             patch("utils._get_windows_monitor_work_area_from_rect", return_value=(-1600, 0, 0, 900)):
            set_window_geometry_and_center(window, 300, 200, parent, grab=False, withdraw_first=False)
        self.assertEqual(window.geometry_calls[-1], "300x200+-1150+300")

    def test_windows_parent_on_right_monitor_stays_on_same_monitor(self):
        window = FakeWindow()
        parent = FakeParent(rootx=2200, rooty=80, width=800, height=600)
        with patch("utils.platform.system", return_value="Windows"), \
             patch("utils._get_windows_monitor_work_area_from_rect", return_value=(1920, 0, 3840, 1040)):
            set_window_geometry_and_center(window, 500, 300, parent, grab=False, withdraw_first=False)
        self.assertEqual(window.geometry_calls[-1], "500x300+2350+230")

    def test_windows_pointer_aligned_dialog_uses_pointer_monitor_bounds(self):
        window = FakeWindow(pointer=(2500, 500))
        with patch("utils.platform.system", return_value="Windows"), \
             patch("utils._get_windows_monitor_work_area_from_point", return_value=(1920, 0, 3840, 1040)):
            set_window_geometry_and_center(window, 700, 300, None, grab=False, withdraw_first=False, align_to_pointer=True)
        self.assertEqual(window.geometry_calls[-1], "700x300+2150+350")

    def test_windows_monitor_lookup_failure_does_not_reapply_primary_screen_clamp(self):
        window = FakeWindow(pointer=(2500, 500), screenwidth=1920, screenheight=1080)
        with patch("utils.platform.system", return_value="Windows"), \
             patch("utils._get_windows_monitor_work_area_from_point", return_value=None):
            set_window_geometry_and_center(window, 700, 300, None, grab=False, withdraw_first=False, align_to_pointer=True)
        self.assertEqual(window.geometry_calls[-1], "700x300+2150+350")

    def test_darwin_parent_centering_remains_unchanged(self):
        window = FakeWindow()
        parent = FakeParent(rootx=300, rooty=120, width=800, height=600)
        with patch("utils.platform.system", return_value="Darwin"):
            set_window_geometry_and_center(window, 400, 250, parent, grab=False, withdraw_first=False)
        self.assertEqual(window.geometry_calls[-1], "400x250+500+295")

    def test_linux_screen_centering_remains_unchanged(self):
        window = FakeWindow(screenwidth=1920, screenheight=1080)
        with patch("utils.platform.system", return_value="Linux"):
            set_window_geometry_and_center(window, 400, 200, None, grab=False, withdraw_first=False)
        self.assertEqual(window.geometry_calls[-1], "400x200+760+440")

    def test_pre_withdrawn_window_is_deiconified_after_positioning(self):
        window = FakeWindow(state="withdrawn", screenwidth=1920, screenheight=1080)
        with patch("utils.platform.system", return_value="Darwin"):
            set_window_geometry_and_center(window, 400, 200, None, grab=False, withdraw_first=True)
        self.assertFalse(window.withdrawn)
        self.assertTrue(window.deiconified)
        self.assertEqual(window.geometry_calls[-1], "400x200+760+440")

if __name__ == '__main__':
    unittest.main()
