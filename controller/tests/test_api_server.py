import unittest
from unittest.mock import patch

from api_server import APIServer


class TestAPIServerSuccessInference(unittest.TestCase):
    def setUp(self):
        self.api_server = APIServer()

    def test_partial_success_command_response_counts_as_success(self):
        response_data = {
            "command_id": "cmd-1",
            "drone_id": "drone-1",
            "command": "move_along_path",
            "status": "partial_success",
            "message": "Path partially completed",
            "successful_points_count": 1,
            "successful_points": [[10.0, 20.0, 15.0]],
            "unsuccessful_points_count": 1,
            "unsuccessful_points": [[30.0, 40.0, 15.0]],
        }

        self.assertTrue(
            self.api_server.infer_api_success(
                "POST",
                "/drones/drone-1/command/move_along_path",
                response_data,
                200,
            )
        )

    def test_error_command_response_counts_as_failure(self):
        response_data = {
            "command_id": "cmd-1",
            "drone_id": "drone-1",
            "command": "move_along_path",
            "status": "error",
            "message": "First waypoint cannot be reached",
            "successful_points_count": 0,
            "successful_points": [],
            "unsuccessful_points_count": 1,
            "unsuccessful_points": [[30.0, 40.0, 15.0]],
        }

        self.assertFalse(
            self.api_server.infer_api_success(
                "POST",
                "/drones/drone-1/command/move_along_path",
                response_data,
                200,
            )
        )

    def test_current_session_request_history_uses_limit_query_parameter(self):
        with patch.object(
            self.api_server,
            "make_request",
            return_value={"request_history": []},
        ) as make_request:
            response = self.api_server.api_get_current_session_request_history()

        self.assertEqual(response, {"request_history": []})
        make_request.assert_called_once_with(
            "GET",
            "/sessions/current/request-history",
            params={"limit": 1000},
            show_error=False,
        )

    def test_session_screenshot_includes_show_label_query_parameter(self):
        with patch.object(
            self.api_server,
            "make_request",
            return_value=b"image",
        ) as make_request:
            response = self.api_server.api_get_session_screenshot(
                fmt="svg",
                width=640,
                height=480,
                show_status=True,
                show_label=False,
                show_error=False,
            )

        self.assertEqual(response, b"image")
        make_request.assert_called_once_with(
            "GET",
            "/sessions/current/screenshot",
            params={
                "format": "svg",
                "width": 640,
                "height": 480,
                "show_status": "true",
                "show_label": "false",
            },
            expect_json=False,
            show_error=False,
        )

    def test_clear_current_session_request_history_uses_delete_endpoint(self):
        with patch.object(
            self.api_server,
            "make_request",
            return_value={"cleared": True, "session_id": "session-1", "cleared_count": 3},
        ) as make_request:
            response = self.api_server.api_clear_current_session_request_history()

        self.assertEqual(response["cleared_count"], 3)
        make_request.assert_called_once_with(
            "DELETE",
            "/sessions/current/request-history",
            show_error=False,
        )


if __name__ == "__main__":
    unittest.main()
