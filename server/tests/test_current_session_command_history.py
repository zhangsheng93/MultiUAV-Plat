import time
import unittest

from fastapi.testclient import TestClient

from api.server import ROLE_SECRETS, UserRole, app, session_controller


class CurrentSessionCommandHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()
        cls.system_headers = {"X-API-Key": ROLE_SECRETS[UserRole.SYSTEM]}
        cls.admin_headers = {"X-API-Key": ROLE_SECRETS[UserRole.ADMIN]}
        cls.user_headers = {"X-API-Key": ROLE_SECRETS[UserRole.USER]}
        cls.agent_headers = {"X-API-Key": ROLE_SECRETS[UserRole.AGENT]}

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)

    def setUp(self):
        self.previous_current_session_id = session_controller.current_session_id
        self.session_id = f"test-current-command-history-{time.time_ns()}"
        session_controller.add_session(
            {
                "id": self.session_id,
                "name": self.session_id,
                "description": "Current command history endpoint test",
                "with_examples": False,
                "task_type": "others",
                "task_description": "Test current command history",
                "creator": "test",
            }
        )
        session_controller.set_current_session(self.session_id)
        self.session = session_controller.sessions[self.session_id]

    def tearDown(self):
        session_controller.delete_session(self.session_id)
        if (
            self.previous_current_session_id
            and self.previous_current_session_id in session_controller.sessions
        ):
            session_controller.set_current_session(self.previous_current_session_id)

    @staticmethod
    def _command_record(index):
        return {
            "command_id": f"command-{index}",
            "drone_id": "drone-1",
            "command": "move_to",
            "parameters": {"x": index, "y": 0, "z": 1},
            "status": "success",
            "message": f"Moved to {index}",
            "timestamp": float(index),
        }

    def test_current_endpoint_returns_active_session_history(self):
        self.session.command_history = [self._command_record(1), self._command_record(2)]

        response = self.client.get(
            "/sessions/current/command-history",
            headers=self.system_headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"command_history": self.session.command_history})

    def test_current_endpoint_limit_matches_session_id_endpoint(self):
        self.session.command_history = [self._command_record(index) for index in range(5)]

        current_response = self.client.get(
            "/sessions/current/command-history",
            params={"limit": 2},
            headers=self.system_headers,
        )
        session_response = self.client.get(
            f"/sessions/{self.session_id}/command-history",
            params={"limit": 2},
            headers=self.system_headers,
        )

        expected = {"command_history": self.session.command_history[-2:]}
        self.assertEqual(current_response.status_code, 200, current_response.text)
        self.assertEqual(session_response.status_code, 200, session_response.text)
        self.assertEqual(current_response.json(), expected)
        self.assertEqual(session_response.json(), expected)

    def test_current_endpoint_caps_limit_at_1000(self):
        self.session.command_history = [self._command_record(index) for index in range(1001)]

        response = self.client.get(
            "/sessions/current/command-history",
            params={"limit": 5000},
            headers=self.system_headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()["command_history"]), 1000)
        self.assertEqual(response.json()["command_history"][0]["command_id"], "command-1")

    def test_current_endpoint_returns_empty_history(self):
        response = self.client.get(
            "/sessions/current/command-history",
            headers=self.system_headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"command_history": []})

    def test_current_endpoint_returns_404_without_current_session(self):
        session_controller.current_session_id = None

        response = self.client.get(
            "/sessions/current/command-history",
            headers=self.system_headers,
        )

        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(response.json(), {"detail": "No current session found"})

    def test_current_endpoint_requires_system_role(self):
        for headers in (self.user_headers, self.agent_headers, None):
            with self.subTest(headers=headers):
                response = self.client.get(
                    "/sessions/current/command-history",
                    headers=headers,
                )
                self.assertEqual(response.status_code, 403, response.text)

    def test_current_endpoint_allows_admin_role(self):
        response = self.client.get(
            "/sessions/current/command-history",
            headers=self.admin_headers,
        )

        self.assertEqual(response.status_code, 200, response.text)


if __name__ == "__main__":
    unittest.main()
