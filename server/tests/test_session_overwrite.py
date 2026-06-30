import unittest
from fastapi.testclient import TestClient
from api.server import app, ROLE_SECRETS, UserRole

class SessionOverwriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.system_headers = {"X-API-Key": ROLE_SECRETS[UserRole.SYSTEM]}

    def test_session_automatic_overwrite(self):
        session_id = "test-overwrite-session"
        
        # 1. Create initial session
        payload1 = {
            "name": "Initial Session",
            "description": "First version",
            "creator": "test"
        }
        resp1 = self.client.post(f"/sessions/{session_id}", headers=self.system_headers, json=payload1)
        self.assertEqual(resp1.status_code, 201, f"Failed to create initial session: {resp1.text}")
        data1 = resp1.json()
        self.assertEqual(data1["name"], "Initial Session")
        
        # 2. Create session with same ID but different data (should overwrite)
        payload2 = {
            "name": "Overwritten Session",
            "description": "Second version",
            "creator": "test",
            "drones": [{"name": "Test Drone", "model": "Test", "max_speed": 10, "max_altitude": 100, "battery_capacity": 100}]
        }
        # Note: No 'overwrite' param needed anymore
        # Also verifying data=True default: response should contain 'drones' list
        resp2 = self.client.post(f"/sessions/{session_id}", headers=self.system_headers, json=payload2)
        self.assertEqual(resp2.status_code, 201, f"Failed to overwrite session: {resp2.text}")
        data2 = resp2.json()
        self.assertIn("drones", data2, "Response should contain full data (drones list) by default")
        self.assertEqual(len(data2["drones"]), 1)
        
        # 3. Verify the session has updated data
        resp_get = self.client.get(f"/sessions/{session_id}", headers=self.system_headers)
        self.assertEqual(resp_get.status_code, 200)
        data_get = resp_get.json()
        
        self.assertEqual(data_get["name"], "Overwritten Session")
        self.assertEqual(data_get["description"], "Second version")
        
        # Cleanup
        self.client.delete(f"/sessions/{session_id}", headers=self.system_headers)

if __name__ == "__main__":
    unittest.main()
