import logging
import time
import unittest
import uuid
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.server import (
    ROLE_SECRETS,
    RequestLoggingMiddleware,
    UserRole,
    _get_recent_request_history,
    app,
    drone_controller,
    session_controller,
)
from config.logging_config import log_api_request
from models.drone import DroneCommand
from models.session import Session


class SessionRequestHistoryTests(unittest.TestCase):
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
        self.created_session_ids = []
        self.session_id = self._create_session("current")
        session_controller.set_current_session(self.session_id)
        self.session = session_controller.sessions[self.session_id]
        session_controller.clear_request_history(self.session_id)

    def tearDown(self):
        for session_id in self.created_session_ids:
            session_controller.delete_session(session_id)
        if (
            self.previous_current_session_id
            and self.previous_current_session_id in session_controller.sessions
        ):
            session_controller.set_current_session(self.previous_current_session_id)

    def _create_session(self, suffix):
        session_id = f"test-request-history-{suffix}-{time.time_ns()}"
        session_controller.add_session(
            {
                "id": session_id,
                "name": session_id,
                "description": "Request history endpoint test",
                "with_examples": False,
                "task_type": "others",
                "task_description": "Test request history",
                "creator": "test",
            }
        )
        self.created_session_ids.append(session_id)
        return session_id

    @staticmethod
    def _request_record(index):
        return {
            "request_id": str(uuid.uuid4()),
            "timestamp": f"2026-06-23T10:30:{index:02d}Z",
            "method": "GET",
            "path": f"/test/{index}",
            "client_ip": "127.0.0.1",
            "client_port": 50000,
            "client_privilege": "ADMIN",
            "authentication_status": "api_key",
            "session_id": "fixture-session",
            "query_params": {},
            "user_agent": "test-client",
            "agent_id": None,
            "request_body": None,
            "status_code": 200,
            "success": True,
            "duration_sec": 0.001,
            "response_body": {"index": index},
            "error": None,
        }

    def test_middleware_records_normalized_request_schema(self):
        response = self.client.get("/version", headers=self.admin_headers)
        self.assertEqual(response.status_code, 200, response.text)

        self.assertEqual(len(self.session.request_history), 1)
        record = self.session.request_history[0]
        self.assertEqual(
            set(record),
            {
                "request_id",
                "timestamp",
                "method",
                "path",
                "client_ip",
                "client_port",
                "client_privilege",
                "authentication_status",
                "session_id",
                "query_params",
                "user_agent",
                "agent_id",
                "request_body",
                "status_code",
                "success",
                "duration_sec",
                "response_body",
                "error",
            },
        )
        uuid.UUID(record["request_id"])
        datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
        self.assertEqual(record["method"], "GET")
        self.assertEqual(record["path"], "/version")
        self.assertEqual(record["client_ip"], "testclient")
        self.assertIsInstance(record["client_port"], int)
        self.assertEqual(record["client_privilege"], "ADMIN")
        self.assertEqual(record["authentication_status"], "api_key")
        self.assertEqual(record["session_id"], self.session_id)
        self.assertEqual(record["query_params"], {})
        self.assertTrue(record["user_agent"])
        self.assertIsNone(record["agent_id"])
        self.assertIsNone(record["request_body"])
        self.assertEqual(record["status_code"], 200)
        self.assertTrue(record["success"])
        self.assertGreaterEqual(record["duration_sec"], 0)
        self.assertIsInstance(record["response_body"], dict)
        self.assertIsNone(record["error"])

    def test_authentication_context_for_all_roles_and_default_agent(self):
        cases = [
            (self.admin_headers, "ADMIN", "api_key"),
            (self.system_headers, "SYSTEM", "api_key"),
            (self.user_headers, "USER", "api_key"),
            (self.agent_headers, "AGENT", "api_key"),
            (None, "AGENT", "default_agent"),
        ]

        for headers, expected_role, expected_status in cases:
            with self.subTest(expected_role=expected_role, expected_status=expected_status):
                response = self.client.get("/version", headers=headers)
                self.assertEqual(response.status_code, 200, response.text)
                record = self.session.request_history[-1]
                self.assertEqual(record["client_privilege"], expected_role)
                self.assertEqual(record["authentication_status"], expected_status)
                if expected_role == "AGENT":
                    self.assertEqual(record["agent_id"], "default_agent")
                else:
                    self.assertIsNone(record["agent_id"])

    def test_agent_id_header_is_recorded_only_for_agent_requests(self):
        response = self.client.get(
            "/version",
            headers={**self.agent_headers, "X-Agent-ID": "  agent-alpha  "},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.session.request_history[-1]["agent_id"], "agent-alpha")

        response = self.client.get(
            "/version",
            headers={**self.agent_headers, "X-Agent-ID": "a" * 140},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.session.request_history[-1]["agent_id"], "a" * 128)

        response = self.client.get(
            "/version",
            headers={**self.system_headers, "X-Agent-ID": "system-label"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(self.session.request_history[-1]["agent_id"])

    def test_invalid_api_key_records_invalid_authentication_without_key(self):
        response = self.client.get(
            "/version",
            headers={"X-API-Key": "invalid-secret-value"},
        )

        self.assertEqual(response.status_code, 401, response.text)
        record = self.session.request_history[-1]
        self.assertIsNone(record["client_privilege"])
        self.assertEqual(record["authentication_status"], "invalid")
        self.assertNotIn("X-API-Key", record)
        self.assertNotIn("api_key", record)
        self.assertNotIn("invalid-secret-value", str(record))

    def test_denied_request_retains_actual_client_privilege(self):
        response = self.client.get(
            "/sessions/current/request-history",
            headers=self.user_headers,
        )

        self.assertEqual(response.status_code, 403, response.text)
        record = self.session.request_history[-1]
        self.assertEqual(record["client_privilege"], "USER")
        self.assertEqual(record["authentication_status"], "api_key")

    def test_network_query_and_user_agent_metadata(self):
        long_user_agent = "a" * 600
        response = self.client.get(
            "/version",
            params={"filter": "active", "limit": "25"},
            headers={
                **self.admin_headers,
                "User-Agent": long_user_agent,
                "X-Forwarded-For": "203.0.113.10",
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        record = self.session.request_history[-1]
        self.assertEqual(record["client_ip"], "testclient")
        self.assertNotEqual(record["client_ip"], "203.0.113.10")
        self.assertIsInstance(record["client_port"], int)
        self.assertEqual(
            record["query_params"],
            {"filter": "active", "limit": "25"},
        )
        self.assertEqual(record["user_agent"], "a" * 512)
        self.assertNotIn("X-Forwarded-For", record)

    def test_successful_direct_move_to_preserves_replayable_query_params(self):
        drone = drone_controller.add_drone(
            {
                "name": "Request History Drone",
                "model": "TestModel",
                "max_speed": 10.0,
                "max_altitude": 100.0,
                "battery_capacity": 100.0,
                "position": {"x": 450.0, "y": 599.0, "z": 0.0},
            }
        )
        drone_controller.send_command(
            drone["id"],
            DroneCommand.TAKE_OFF,
            {"altitude": 10.0},
        )
        session_controller.clear_request_history(self.session_id)

        response = self.client.post(
            f"/drones/{drone['id']}/command/move_to",
            params={"x": "451", "y": "600", "z": "21"},
            headers=self.admin_headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        record = self.session.request_history[-1]
        self.assertEqual(
            record["path"],
            f"/drones/{drone['id']}/command/move_to",
        )
        self.assertEqual(
            record["query_params"],
            {"x": "451", "y": "600", "z": "21"},
        )
        self.assertIsNone(record["request_body"])

    def test_json_body_and_query_params_are_preserved_independently(self):
        response = self.client.post(
            "/unknown-request-history-test",
            params={"mode": "safe"},
            headers=self.admin_headers,
            json={"action": "inspect"},
        )

        self.assertEqual(response.status_code, 404)
        record = self.session.request_history[-1]
        self.assertEqual(record["query_params"], {"mode": "safe"})
        self.assertEqual(record["request_body"], {"action": "inspect"})

    def test_repeated_query_keys_preserve_order_as_arrays(self):
        response = self.client.get(
            "/version?tag=alpha&tag=beta&limit=10",
            headers=self.admin_headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            self.session.request_history[-1]["query_params"],
            {"tag": ["alpha", "beta"], "limit": "10"},
        )

    def test_sensitive_query_values_are_redacted_with_repeated_shape(self):
        response = self.client.get(
            "/version?api_key=one&api_key=two&Authorization=bearer"
            "&refresh_token=refresh&session_token=session&target_id=target-1",
            headers=self.admin_headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        query_params = self.session.request_history[-1]["query_params"]
        self.assertEqual(
            query_params["api_key"],
            ["***REDACTED***", "***REDACTED***"],
        )
        self.assertEqual(query_params["Authorization"], "***REDACTED***")
        self.assertEqual(query_params["refresh_token"], "***REDACTED***")
        self.assertEqual(query_params["session_token"], "***REDACTED***")
        self.assertEqual(query_params["target_id"], "target-1")
        self.assertNotIn("one", str(query_params))
        self.assertNotIn("bearer", str(query_params))

    def test_failed_validation_preserves_attempted_query_params(self):
        response = self.client.post(
            "/drones/missing/command/move_to",
            params={"x": "invalid", "y": "600"},
            headers=self.admin_headers,
        )

        self.assertEqual(response.status_code, 422, response.text)
        record = self.session.request_history[-1]
        self.assertEqual(
            record["query_params"],
            {"x": "invalid", "y": "600"},
        )
        self.assertFalse(record["success"])

    def test_query_params_are_captured_for_all_supported_http_methods(self):
        for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                response = self.client.request(
                    method,
                    "/unknown-query-method-test",
                    params=[("tag", "alpha"), ("tag", "beta")],
                    headers=self.admin_headers,
                )
                self.assertEqual(response.status_code, 404)
                record = self.session.request_history[-1]
                self.assertEqual(record["method"], method)
                self.assertEqual(
                    record["query_params"],
                    {"tag": ["alpha", "beta"]},
                )

    def test_current_endpoint_returns_latest_history_in_chronological_order(self):
        records = [self._request_record(index) for index in range(5)]
        self.session.request_history = records
        expected_records = list(records[-2:])

        response = self.client.get(
            "/sessions/current/request-history",
            params={"limit": 2},
            headers=self.system_headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"request_history": expected_records})
        self.assertEqual(len(self.session.request_history), 6)
        self.assertEqual(
            self.session.request_history[-1]["path"],
            "/sessions/current/request-history",
        )
        self.assertIsNone(self.session.request_history[-1]["response_body"])

    def test_request_history_body_capture_is_skipped(self):
        self.assertTrue(
            RequestLoggingMiddleware.should_skip_body_logging(
                "/sessions/current/request-history"
            )
        )
        self.assertTrue(
            RequestLoggingMiddleware.should_skip_body_logging(
                f"/sessions/{self.session_id}/request-history"
            )
        )
        self.assertTrue(
            RequestLoggingMiddleware.should_skip_body_logging(
                "/sessions/current/data",
                method="GET",
            )
        )
        self.assertTrue(
            RequestLoggingMiddleware.should_skip_body_logging(
                f"/sessions/{self.session_id}/data",
                method="GET",
            )
        )
        self.assertTrue(
            RequestLoggingMiddleware.should_skip_body_logging(
                "/sessions/current",
                method="GET",
                query_params={"data": "true"},
            )
        )
        self.assertTrue(
            RequestLoggingMiddleware.should_skip_body_logging(
                f"/sessions/{self.session_id}",
                method="GET",
                query_params={"data": "true"},
            )
        )
        self.assertFalse(
            RequestLoggingMiddleware.should_skip_body_logging(
                "/sessions/current"
            )
        )

    def test_response_body_summary_classifies_omitted_large_bodies(self):
        self.assertEqual(
            RequestLoggingMiddleware.response_body_summary(
                "/sessions/current/data",
                method="GET",
            ),
            "session_data_omitted",
        )
        self.assertEqual(
            RequestLoggingMiddleware.response_body_summary(
                "/sessions/current/request-history",
            ),
            "request_history_omitted",
        )
        self.assertEqual(
            RequestLoggingMiddleware.response_body_summary(
                "/sessions/current/screenshot",
                content_type="image/png",
            ),
            "binary_omitted",
        )

    def test_structured_api_log_omits_full_response_body(self):
        records = []

        class CapturingLogger:
            name = "uav_system.api"

            def makeRecord(self, *args, **kwargs):
                return logging.getLogger(self.name).makeRecord(*args, **kwargs)

            def handle(self, record):
                records.append(record)

        with patch("config.logging_config.get_logger", return_value=CapturingLogger()):
            log_api_request(
                method="GET",
                path="/version",
                status_code=200,
                duration_ms=1.2,
                client_ip="127.0.0.1",
                response_size_bytes=123,
                response_body_type="application/json",
                response_body_summary="omitted",
            )

        self.assertEqual(len(records), 1)
        extra_data = records[0].extra_data
        self.assertNotIn("response_body", extra_data)
        self.assertEqual(extra_data["response_size_bytes"], 123)
        self.assertEqual(extra_data["response_body_type"], "application/json")
        self.assertEqual(extra_data["response_body_summary"], "omitted")

    def test_current_session_data_request_is_not_recorded_in_request_history(self):
        self.session.request_history = [self._request_record(1)]

        response = self.client.get(
            "/sessions/current/data",
            headers=self.system_headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("request_history", response.json()["history"])
        self.assertEqual(len(self.session.request_history), 1)
        self.assertEqual(self.session.request_history[0]["path"], "/test/1")

    def test_recent_request_history_helper_slices_before_normalizing(self):
        records = [self._request_record(index) for index in range(10)]
        legacy_record = self._request_record(99)
        legacy_record.pop("query_params")
        legacy_record.pop("agent_id")
        self.session.request_history = records + [legacy_record]

        returned = _get_recent_request_history(self.session, 3)

        self.assertEqual(
            [record["path"] for record in returned],
            ["/test/8", "/test/9", "/test/99"],
        )
        self.assertEqual(returned[-1]["query_params"], {})
        self.assertIsNone(returned[-1]["agent_id"])
        self.assertEqual(_get_recent_request_history(self.session, 0), [])

    def test_explicit_endpoint_reads_requested_session(self):
        other_session_id = self._create_session("other")
        other_session = session_controller.sessions[other_session_id]
        other_record = self._request_record(1)
        other_session.request_history = [other_record]

        response = self.client.get(
            f"/sessions/{other_session_id}/request-history",
            headers=self.admin_headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"request_history": [other_record]})
        self.assertEqual(len(other_session.request_history), 1)
        self.assertEqual(
            self.session.request_history[-1]["path"],
            f"/sessions/{other_session_id}/request-history",
        )

    def test_limit_defaults_to_all_and_explicit_limit_slices(self):
        self.session.request_history = [
            self._request_record(index % 60) for index in range(1005)
        ]

        default_response = self.client.get(
            "/sessions/current/request-history",
            headers=self.system_headers,
        )
        response = self.client.get(
            "/sessions/current/request-history",
            params={"limit": 1002},
            headers=self.system_headers,
        )

        self.assertEqual(default_response.status_code, 200, default_response.text)
        self.assertEqual(len(default_response.json()["request_history"]), 1005)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()["request_history"]), 1002)
        self.assertEqual(len(self.session.request_history), 1007)

    def test_legacy_request_history_records_default_agent_id_to_none(self):
        legacy_record = self._request_record(1)
        legacy_record.pop("agent_id")
        self.session.request_history = [legacy_record]

        response = self.client.get(
            "/sessions/current/request-history",
            headers=self.system_headers,
        )

        expected_record = dict(legacy_record)
        expected_record["agent_id"] = None
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["request_history"], [expected_record])

    def test_missing_sessions_return_expected_404_responses(self):
        session_controller.current_session_id = None
        current_response = self.client.get(
            "/sessions/current/request-history",
            headers=self.system_headers,
        )
        explicit_response = self.client.get(
            "/sessions/missing-session/request-history",
            headers=self.system_headers,
        )

        self.assertEqual(current_response.status_code, 404, current_response.text)
        self.assertEqual(
            current_response.json(),
            {"detail": "No current session found"},
        )
        self.assertEqual(explicit_response.status_code, 404, explicit_response.text)
        self.assertEqual(explicit_response.json(), {"detail": "Session not found"})

    def test_request_history_role_access(self):
        for headers in (self.user_headers,):
            with self.subTest(headers=headers):
                response = self.client.get(
                    "/sessions/current/request-history",
                    headers=headers,
                )
                self.assertEqual(response.status_code, 403, response.text)

        agent_response = self.client.get(
            "/sessions/current/request-history",
            headers=self.agent_headers,
        )
        self.assertEqual(agent_response.status_code, 200, agent_response.text)

        default_agent_response = self.client.get("/sessions/current/request-history")
        self.assertEqual(default_agent_response.status_code, 200, default_agent_response.text)

        system_response = self.client.get(
            "/sessions/current/request-history",
            headers=self.system_headers,
        )
        self.assertEqual(system_response.status_code, 200, system_response.text)

        admin_response = self.client.get(
            "/sessions/current/request-history",
            headers=self.admin_headers,
        )
        self.assertEqual(admin_response.status_code, 200, admin_response.text)

        explicit_agent_response = self.client.get(
            f"/sessions/{self.session_id}/request-history",
            headers=self.agent_headers,
        )
        self.assertEqual(explicit_agent_response.status_code, 403, explicit_agent_response.text)

    def test_agent_current_request_history_is_filtered_by_agent_id(self):
        records = []
        for index, (role, agent_id) in enumerate(
            [
                ("AGENT", "agent-alpha"),
                ("ADMIN", None),
                ("AGENT", "agent-beta"),
                ("USER", None),
                ("AGENT", None),
                ("SYSTEM", None),
                ("AGENT", "agent-alpha"),
                ("AGENT", "agent-alpha"),
            ]
        ):
            record = self._request_record(index)
            record["client_privilege"] = role
            record["agent_id"] = agent_id
            records.append(record)

        legacy_record = self._request_record(50)
        legacy_record["client_privilege"] = "AGENT"
        legacy_record.pop("agent_id")
        self.session.request_history = [legacy_record] + records

        response = self.client.get(
            "/sessions/current/request-history",
            params={"limit": 2},
            headers={**self.agent_headers, "X-Agent-ID": "agent-alpha"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        returned = response.json()["request_history"]
        self.assertEqual(
            [record["path"] for record in returned],
            ["/test/6", "/test/7"],
        )
        self.assertTrue(all(record["agent_id"] == "agent-alpha" for record in returned))
        self.assertTrue(all(record["client_privilege"] == "AGENT" for record in returned))

    def test_recent_request_history_helper_filters_agent_before_limit(self):
        records = []
        for index in range(12):
            record = self._request_record(index)
            record["client_privilege"] = "AGENT"
            record["agent_id"] = "agent-alpha" if index in (1, 5, 9, 11) else "agent-beta"
            records.append(record)
        self.session.request_history = records

        returned = _get_recent_request_history(
            self.session,
            2,
            agent_id="agent-alpha",
        )

        self.assertEqual(
            [record["path"] for record in returned],
            ["/test/9", "/test/11"],
        )
        self.assertTrue(all(record["agent_id"] == "agent-alpha" for record in returned))

    def test_default_agent_current_request_history_is_filtered_to_default_agent(self):
        matching_record = self._request_record(1)
        matching_record["client_privilege"] = "AGENT"
        matching_record["agent_id"] = "default_agent"

        other_record = self._request_record(2)
        other_record["client_privilege"] = "AGENT"
        other_record["agent_id"] = "agent-alpha"

        legacy_record = self._request_record(3)
        legacy_record["client_privilege"] = "AGENT"
        legacy_record.pop("agent_id")

        self.session.request_history = [other_record, legacy_record, matching_record]

        response = self.client.get(
            "/sessions/current/request-history",
            headers=self.agent_headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["request_history"], [matching_record])

    def test_system_can_clear_current_request_history_without_recording_clear(self):
        records = [self._request_record(index) for index in range(3)]
        command_record = {"command": "take_off", "timestamp": time.time()}
        status_record = {"status": "flying", "timestamp": time.time()}
        self.session.request_history = records
        self.session.command_history = [command_record]
        self.session.status_history = {"drone-1": [status_record]}
        self.session.path_history = {"drone-1": [{"x": 1.0, "y": 2.0, "z": 3.0}]}
        retention_limit = self.session.max_request_history

        response = self.client.delete(
            "/sessions/current/request-history",
            headers=self.system_headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {
                "cleared": True,
                "session_id": self.session_id,
                "cleared_count": 3,
            },
        )
        self.assertEqual(self.session.request_history, [])
        self.assertEqual(self.session.command_history, [command_record])
        self.assertEqual(self.session.status_history, {"drone-1": [status_record]})
        self.assertEqual(
            self.session.path_history,
            {"drone-1": [{"x": 1.0, "y": 2.0, "z": 3.0}]},
        )
        self.assertEqual(self.session.max_request_history, retention_limit)

        get_response = self.client.get(
            "/sessions/current/request-history",
            headers=self.system_headers,
        )
        self.assertEqual(get_response.status_code, 200, get_response.text)
        self.assertEqual(get_response.json(), {"request_history": []})

    def test_admin_can_clear_explicit_request_history(self):
        other_session_id = self._create_session("clear-other")
        other_session = session_controller.sessions[other_session_id]
        other_session.request_history = [
            self._request_record(1),
            self._request_record(2),
        ]
        self.session.request_history = [self._request_record(3)]

        response = self.client.delete(
            f"/sessions/{other_session_id}/request-history",
            headers=self.admin_headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {
                "cleared": True,
                "session_id": other_session_id,
                "cleared_count": 2,
            },
        )
        self.assertEqual(other_session.request_history, [])
        self.assertEqual(len(self.session.request_history), 1)

    def test_clear_request_history_rejects_non_system_roles(self):
        for headers in (self.user_headers, self.agent_headers, None):
            with self.subTest(headers=headers):
                response = self.client.delete(
                    "/sessions/current/request-history",
                    headers=headers,
                )
                self.assertEqual(response.status_code, 403, response.text)

        explicit_agent_response = self.client.delete(
            f"/sessions/{self.session_id}/request-history",
            headers=self.agent_headers,
        )
        self.assertEqual(
            explicit_agent_response.status_code,
            403,
            explicit_agent_response.text,
        )

    def test_clear_request_history_missing_sessions_return_404(self):
        session_controller.current_session_id = None

        current_response = self.client.delete(
            "/sessions/current/request-history",
            headers=self.system_headers,
        )
        explicit_response = self.client.delete(
            "/sessions/missing-session/request-history",
            headers=self.system_headers,
        )

        self.assertEqual(current_response.status_code, 404, current_response.text)
        self.assertEqual(
            current_response.json(),
            {"detail": "No current session found"},
        )
        self.assertEqual(explicit_response.status_code, 404, explicit_response.text)
        self.assertEqual(explicit_response.json(), {"detail": "Session not found"})

    def test_agent_filtered_request_history_is_empty_after_privileged_clear(self):
        agent_record = self._request_record(1)
        agent_record["client_privilege"] = "AGENT"
        agent_record["agent_id"] = "agent-alpha"
        self.session.request_history = [agent_record]

        clear_response = self.client.delete(
            "/sessions/current/request-history",
            headers=self.system_headers,
        )
        self.assertEqual(clear_response.status_code, 200, clear_response.text)

        agent_response = self.client.get(
            "/sessions/current/request-history",
            headers={**self.agent_headers, "X-Agent-ID": "agent-alpha"},
        )
        self.assertEqual(agent_response.status_code, 200, agent_response.text)
        self.assertEqual(agent_response.json(), {"request_history": []})

    def test_sensitive_values_are_redacted_and_binary_bodies_are_omitted(self):
        secret_response = self.client.post(
            "/unknown-request-history-test",
            headers=self.admin_headers,
            json={
                "api_key": "secret-key",
                "nested": {"password": "secret-password"},
                "items": [{"access_token": "secret-token"}],
            },
        )
        screenshot_response = self.client.get(
            "/unknown/screenshot",
            headers=self.admin_headers,
        )

        self.assertEqual(secret_response.status_code, 404)
        self.assertEqual(screenshot_response.status_code, 404)
        secret_record, screenshot_record = self.session.request_history[-2:]
        self.assertEqual(secret_record["request_body"]["api_key"], "***REDACTED***")
        self.assertEqual(
            secret_record["request_body"]["nested"]["password"],
            "***REDACTED***",
        )
        self.assertEqual(
            secret_record["request_body"]["items"][0]["access_token"],
            "***REDACTED***",
        )
        self.assertFalse(secret_record["success"])
        self.assertIsNone(screenshot_record["response_body"])

    def test_request_history_is_omitted_from_export_and_restore(self):
        record = self._request_record(1)
        record["query_params"] = {
            "tag": ["alpha", "beta"],
            "limit": "10",
        }
        self.session.request_history = [record]
        exported = self.session.to_dict(data=True)

        self.assertNotIn("request_history", exported["history"])

        restored = Session.from_dict(exported)
        self.assertEqual(restored.request_history, [])

    def test_imported_request_history_is_silently_discarded(self):
        legacy_record = {
            "request_id": str(uuid.uuid4()),
            "timestamp": "2026-06-23T10:30:00Z",
            "method": "GET",
            "path": "/legacy",
            "request_body": None,
            "status_code": 200,
            "success": True,
            "duration_sec": 0.01,
            "response_body": {},
            "error": None,
        }
        session_data = self.session.to_dict(data=True)
        session_data["history"]["request_history"] = [legacy_record]

        restored = Session.from_dict(session_data)
        self.assertEqual(restored.request_history, [])
        self.assertNotIn(
            "request_history",
            restored.to_dict(data=True)["history"],
        )

    def test_full_session_response_omits_request_history(self):
        self.session.request_history = [self._request_record(1)]

        requests = [
            ("/sessions/current", {"data": "true"}),
            (f"/sessions/{self.session_id}", {"data": "true"}),
            (f"/sessions/{self.session_id}/data", None),
        ]

        for path, params in requests:
            with self.subTest(path=path):
                response = self.client.get(
                    path,
                    params=params,
                    headers=self.system_headers,
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertNotIn("request_history", response.json()["history"])
                recorded_response = self.session.request_history[-1]["response_body"]
                self.assertIsNone(recorded_response)

    def test_session_history_response_schema_omits_request_history(self):
        schema = app.openapi()["components"]["schemas"]["SessionHistory"]
        self.assertNotIn("request_history", schema["properties"])

    def test_import_api_discards_request_history_and_omits_it_from_response(self):
        imported_session_id = f"import-runtime-only-{time.time_ns()}"
        self.created_session_ids.append(imported_session_id)

        response = self.client.post(
            f"/sessions/{imported_session_id}",
            params={"data": "true"},
            headers=self.system_headers,
            json={
                "name": "Imported runtime-only history",
                "with_examples": False,
                "history": {
                    "request_history": [self._request_record(1)],
                },
            },
        )

        self.assertEqual(response.status_code, 201, response.text)
        self.assertNotIn("request_history", response.json()["history"])
        self.assertEqual(
            session_controller.sessions[imported_session_id].request_history,
            [],
        )

    def test_reset_clears_history_without_recording_reset_request(self):
        self.session.request_history = [self._request_record(1)]

        response = self.client.post(
            "/sessions/current/reset",
            headers=self.system_headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.session.request_history, [])

    def test_switch_request_is_attributed_to_session_active_after_response(self):
        other_session_id = self._create_session("switch-target")
        old_session = self.session
        other_session = session_controller.sessions[other_session_id]
        session_controller.clear_request_history(old_session.id)
        session_controller.clear_request_history(other_session.id)

        response = self.client.post(
            f"/sessions/{other_session_id}/set-current",
            headers=self.agent_headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(old_session.request_history, [])
        self.assertEqual(len(other_session.request_history), 1)
        self.assertEqual(
            other_session.request_history[0]["path"],
            f"/sessions/{other_session_id}/set-current",
        )

    def test_creation_request_is_attributed_to_session_active_after_response(self):
        response = self.client.post(
            "/sessions",
            headers=self.system_headers,
            json={
                "name": "Inactive created session",
                "description": "Created while another session is active",
                "with_examples": False,
            },
        )

        self.assertEqual(response.status_code, 201, response.text)
        created_session_id = response.json()["id"]
        self.created_session_ids.append(created_session_id)
        self.assertEqual(session_controller.current_session_id, self.session_id)
        self.assertEqual(self.session.request_history[-1]["path"], "/sessions")
        self.assertEqual(
            session_controller.sessions[created_session_id].request_history,
            [],
        )


if __name__ == "__main__":
    unittest.main()
