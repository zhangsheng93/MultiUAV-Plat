import time
import unittest
from fastapi.testclient import TestClient
from api.server import app, ROLE_SECRETS, UserRole

class MessageCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()
        cls.admin_headers = {"X-API-Key": ROLE_SECRETS[UserRole.ADMIN]}

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)

    def _create_drone(self, name="Test Drone"):
        payload = {
            "name": name,
            "model": "TestModel",
            "max_speed": 10.0,
            "max_altitude": 50.0,
            "battery_capacity": 100.0,
        }
        resp = self.client.post("/drones", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201)
        return resp.json()

    def _send_direct_message(self, source_id: str, target_id: str, message: str):
        resp = self.client.post(
            f"/drones/{source_id}/command/send_message",
            params={"target_drone_id": target_id, "message": message},
            headers=self.admin_headers
        )
        self.assertEqual(resp.status_code, 200)
        return resp

    def _broadcast_message(self, source_id: str, message: str):
        resp = self.client.post(
            f"/drones/{source_id}/command/broadcast",
            params={"message": message},
            headers=self.admin_headers
        )
        self.assertEqual(resp.status_code, 200)
        return resp

    def test_drone_has_sent_message_with_broadcast(self):
        # Create two drones
        drone1 = self._create_drone("Drone 1")
        drone2 = self._create_drone("Drone 2")
        
        # Initially no messages sent
        resp = self.client.get(
            "/check/drone_has_sent_message",
            params={"drone_id": drone1["id"]},
            headers=self.admin_headers
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["result"])
        self.assertEqual(resp.json()["value"], 0)

        # Send a direct message
        self._send_direct_message(drone1["id"], drone2["id"], "Hello")

        # Check if message is recorded
        resp = self.client.get(
            "/check/drone_has_sent_message",
            params={"drone_id": drone1["id"]},
            headers=self.admin_headers
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["result"])
        self.assertEqual(resp.json()["value"], 1)

        # Broadcast a message
        self._broadcast_message(drone1["id"], "Broadcast message")

        # Check if broadcast is recorded
        resp = self.client.get(
            "/check/drone_has_sent_message",
            params={"drone_id": drone1["id"]},
            headers=self.admin_headers
        )
        self.assertEqual(resp.status_code, 200)
        # Now broadcast SHOULD be counted
        self.assertEqual(resp.json()["value"], 2)
        self.assertIn("all", resp.json()["recipient_drones"])

        # Check if it works with to_drone_id filter
        resp = self.client.get(
            "/check/drone_has_sent_message",
            params={"drone_id": drone1["id"], "to_drone_id": drone2["id"]},
            headers=self.admin_headers
        )
        self.assertEqual(resp.status_code, 200)
        # Should be 2 because the broadcast also counts for drone2
        self.assertEqual(resp.json()["value"], 2)
        self.assertIn(drone2["id"], resp.json()["recipient_drones"])
        self.assertIn("all", resp.json()["recipient_drones"])

    def test_drone_has_sent_message_content(self):
        drone1 = self._create_drone("Drone 1 content")
        drone2 = self._create_drone("Drone 2 content")

        no_match_resp = self.client.get(
            "/check/drone_has_sent_message_content",
            params={"drone_id": drone1["id"], "content": "alert"},
            headers=self.admin_headers
        )
        self.assertEqual(no_match_resp.status_code, 200)
        self.assertFalse(no_match_resp.json()["result"])
        self.assertEqual(no_match_resp.json()["value"], 0)

        self._send_direct_message(drone1["id"], drone2["id"], "alert: hold position")

        direct_match_resp = self.client.get(
            "/check/drone_has_sent_message_content",
            params={"drone_id": drone1["id"], "content": "alert"},
            headers=self.admin_headers
        )
        self.assertEqual(direct_match_resp.status_code, 200)
        direct_match_data = direct_match_resp.json()
        self.assertTrue(direct_match_data["result"])
        self.assertEqual(direct_match_data["value"], 1)
        self.assertEqual(direct_match_data["match_mode"], "contains")
        self.assertIn("alert: hold position", direct_match_data["matched_messages"])

        non_match_resp = self.client.get(
            "/check/drone_has_sent_message_content",
            params={"drone_id": drone1["id"], "content": "resume"},
            headers=self.admin_headers
        )
        self.assertEqual(non_match_resp.status_code, 200)
        self.assertFalse(non_match_resp.json()["result"])

        before_broadcast = time.time()
        time.sleep(0.01)
        self._broadcast_message(drone1["id"], "mission alert for all drones")

        broadcast_match_resp = self.client.get(
            "/check/drone_has_sent_message_content",
            params={"drone_id": drone1["id"], "content": "mission alert"},
            headers=self.admin_headers
        )
        self.assertEqual(broadcast_match_resp.status_code, 200)
        broadcast_match_data = broadcast_match_resp.json()
        self.assertTrue(broadcast_match_data["result"])
        self.assertEqual(broadcast_match_data["value"], 1)
        self.assertIn("all", broadcast_match_data["recipient_drones"])

        filtered_resp = self.client.get(
            "/check/drone_has_sent_message_content",
            params={
                "drone_id": drone1["id"],
                "to_drone_id": drone2["id"],
                "content": "mission alert"
            },
            headers=self.admin_headers
        )
        self.assertEqual(filtered_resp.status_code, 200)
        filtered_data = filtered_resp.json()
        self.assertTrue(filtered_data["result"])
        self.assertIn("all", filtered_data["recipient_drones"])

        self._send_direct_message(drone1["id"], drone2["id"], "alert: fallback")

        min_count_resp = self.client.get(
            "/check/drone_has_sent_message_content",
            params={
                "drone_id": drone1["id"],
                "content": "alert",
                "min_count": 2
            },
            headers=self.admin_headers
        )
        self.assertEqual(min_count_resp.status_code, 200)
        self.assertTrue(min_count_resp.json()["result"])
        self.assertEqual(min_count_resp.json()["value"], 3)

        since_resp = self.client.get(
            "/check/drone_has_sent_message_content",
            params={
                "drone_id": drone1["id"],
                "content": "alert",
                "since_timestamp": before_broadcast
            },
            headers=self.admin_headers
        )
        self.assertEqual(since_resp.status_code, 200)
        since_data = since_resp.json()
        self.assertTrue(since_data["result"])
        self.assertEqual(since_data["value"], 2)

        empty_content_resp = self.client.get(
            "/check/drone_has_sent_message_content",
            params={"drone_id": drone1["id"], "content": "   "},
            headers=self.admin_headers
        )
        self.assertEqual(empty_content_resp.status_code, 400)

if __name__ == "__main__":
    unittest.main()
