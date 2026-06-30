import time
import unittest

from fastapi.testclient import TestClient

from api.server import app, ROLE_SECRETS, UserRole


class LandAllObstacleBlockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()
        cls.admin_headers = {"X-API-Key": ROLE_SECRETS[UserRole.ADMIN]}

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)

    def _create_session(self):
        suffix = int(time.time() * 1_000_000)
        payload = {
            "name": f"test-land-all-obstacle-{suffix}",
            "description": "Land all blocked over obstacle",
            "with_examples": False,
        }
        resp = self.client.post("/sessions", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        session_id = resp.json()["id"]
        set_resp = self.client.post(f"/sessions/{session_id}/set-current", headers=self.admin_headers)
        self.assertEqual(set_resp.status_code, 200, set_resp.text)
        return session_id

    def _create_drone(self, position=None):
        payload = {
            "name": "Test Drone",
            "model": "TestModel",
            "max_speed": 10.0,
            "max_altitude": 50.0,
            "battery_capacity": 100.0,
            "position": position or {"x": 0.0, "y": 0.0, "z": 0.0},
        }
        resp = self.client.post("/drones", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return resp.json()

    def _create_obstacle(self):
        payload = {
            "name": "Landing Blocker",
            "type": "circle",
            "position": {"x": 0.0, "y": 0.0, "z": 0.0},
            "radius": 2.0,
            "height": 5.0,
        }
        resp = self.client.post("/obstacles", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return resp.json()

    def test_land_all_blocked_over_obstacle(self):
        self._create_session()
        self._create_obstacle()
        drone = self._create_drone()

        takeoff_resp = self.client.post(
            f"/drones/{drone['id']}/command/take_off",
            params={"altitude": 10.0},
            headers=self.admin_headers,
        )
        self.assertEqual(takeoff_resp.status_code, 200, takeoff_resp.text)
        self.assertEqual(takeoff_resp.json()["status"], "success")

        land_all_resp = self.client.post("/drones/land_all", headers=self.admin_headers)
        self.assertEqual(land_all_resp.status_code, 200, land_all_resp.text)
        details = land_all_resp.json().get("details", [])
        matched = next((d for d in details if d.get("drone_id") == drone["id"]), None)
        self.assertIsNotNone(matched, "Drone missing from land_all response")
        self.assertEqual(matched["action"], "blocked")
        self.assertIn("Cannot land", matched.get("reason", ""))

        drone_resp = self.client.get(f"/drones/{drone['id']}", headers=self.admin_headers)
        self.assertEqual(drone_resp.status_code, 200, drone_resp.text)
        self.assertGreater(drone_resp.json()["position"]["z"], 0.0)
        self.assertEqual(drone_resp.json()["status"], "hovering")
