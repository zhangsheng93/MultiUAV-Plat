import unittest
from unittest.mock import Mock

from check_ui.agent_client import AgentClient


class TestAgentClientLogging(unittest.TestCase):

    def test_preview_compacts_whitespace_and_truncates(self):
        preview = AgentClient._preview("line one\nline two\tline three", limit=18)

        self.assertEqual(preview, "line one line two...")

    def test_log_job_status_uses_single_line_truncated_output(self):
        logger = Mock()
        client = AgentClient(logger=logger)
        output = "[TASK DONE]\n" + ("Communication relay mission completed successfully. " * 10)

        client._log_job_status(
            "7a237dda-b808-4e8a-8dbd-e3acc3179bd8",
            {
                "status": "completed",
                "result": {
                    "success": True,
                    "output": output,
                },
            },
            55.1,
        )

        message = logger.info.call_args.args[0]
        self.assertNotIn("\n", message)
        self.assertIn("result_success=True", message)
        self.assertIn("output=[TASK DONE] Communication relay mission", message)
        self.assertLessEqual(len(message), 620)


if __name__ == "__main__":
    unittest.main()
