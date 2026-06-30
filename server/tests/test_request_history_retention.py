import unittest

from controllers.session_controller import SessionController
from main import create_argument_parser
from models.session import DEFAULT_REQUEST_HISTORY_LIMIT, Session


class RequestHistoryRetentionTests(unittest.TestCase):
    @staticmethod
    def _record(index):
        return {
            "request_id": f"request-{index}",
            "timestamp": "2026-06-25T00:00:00Z",
            "method": "GET",
            "path": f"/requests/{index}",
            "request_body": None,
            "status_code": 200,
            "success": True,
            "duration_sec": 0.001,
            "response_body": {},
            "error": None,
        }

    def test_default_session_retains_latest_5000_records(self):
        session = Session(name="Default retention")

        for index in range(DEFAULT_REQUEST_HISTORY_LIMIT + 1):
            session.add_request_to_history(self._record(index))

        self.assertEqual(DEFAULT_REQUEST_HISTORY_LIMIT, 5000)
        self.assertEqual(session.max_request_history, 5000)
        self.assertEqual(len(session.request_history), 5000)
        self.assertEqual(session.request_history[0]["request_id"], "request-1")
        self.assertEqual(
            session.request_history[-1]["request_id"],
            "request-5000",
        )

    def test_controller_custom_limit_applies_to_new_sessions(self):
        controller = SessionController(request_history_limit=3)

        session_data = controller.add_session(
            {
                "id": "custom-limit",
                "name": "Custom limit",
                "with_examples": False,
            }
        )
        session = controller.sessions[session_data["id"]]
        for index in range(5):
            session.add_request_to_history(self._record(index))

        self.assertEqual(session.max_request_history, 3)
        self.assertEqual(
            [record["request_id"] for record in session.request_history],
            ["request-2", "request-3", "request-4"],
        )

    def test_lowering_controller_limit_trims_existing_sessions(self):
        controller = SessionController(request_history_limit=5)
        session = controller.create_session_from_dict(
            {
                "id": "existing",
                "name": "Existing",
            }
        )
        for index in range(5):
            session.add_request_to_history(self._record(index))
        controller.sessions[session.id] = session

        controller.set_request_history_limit(2)

        self.assertEqual(controller.request_history_limit, 2)
        self.assertEqual(session.max_request_history, 2)
        self.assertEqual(
            [record["request_id"] for record in session.request_history],
            ["request-3", "request-4"],
        )

    def test_restored_history_is_discarded_but_uses_controller_limit(self):
        controller = SessionController(request_history_limit=2)

        restored = controller.create_session_from_dict(
            {
                "id": "restored",
                "name": "Restored",
                "history": {
                    "request_history": [
                        self._record(index) for index in range(5)
                    ]
                },
            }
        )

        self.assertEqual(restored.max_request_history, 2)
        self.assertEqual(restored.request_history, [])
        self.assertNotIn(
            "max_request_history",
            restored.to_dict(data=True),
        )
        self.assertNotIn(
            "request_history",
            restored.to_dict(data=True)["history"],
        )

    def test_controller_rejects_non_positive_limits(self):
        with self.assertRaises(ValueError):
            SessionController(request_history_limit=0)

        controller = SessionController()
        with self.assertRaises(ValueError):
            controller.set_request_history_limit(-1)

    def test_cli_default_and_custom_limit(self):
        parser = create_argument_parser()

        self.assertEqual(
            parser.parse_args([]).request_history_limit,
            DEFAULT_REQUEST_HISTORY_LIMIT,
        )
        self.assertEqual(
            parser.parse_args(
                ["--request-history-limit", "2500"]
            ).request_history_limit,
            2500,
        )

    def test_cli_rejects_non_positive_limit(self):
        parser = create_argument_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(["--request-history-limit", "0"])
        with self.assertRaises(SystemExit):
            parser.parse_args(["--request-history-limit", "-1"])


if __name__ == "__main__":
    unittest.main()
