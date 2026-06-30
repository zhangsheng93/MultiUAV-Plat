import time
import unittest
from fastapi.testclient import TestClient
from api.server import app, ROLE_SECRETS, UserRole

class CheckMovedDirectedDistanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()
        cls.admin_headers = {"X-API-Key": ROLE_SECRETS[UserRole.ADMIN]}
        cls.agent_headers = {"X-API-Key": ROLE_SECRETS[UserRole.AGENT]}

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)

    def _create_session(self):
        suffix = int(time.time() * 1_000_000)
        payload = {
            "name": f"test-directed-dist-{suffix}",
            "description": "Test session",
            "with_examples": False,
        }
        resp = self.client.post("/sessions", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201)
        session_id = resp.json()["id"]
        self.client.post(f"/sessions/{session_id}/set-current", headers=self.admin_headers)
        return session_id

    def _create_drone(self):
        payload = {
            "name": "Test Drone",
            "model": "TestModel",
            "max_speed": 10.0,
            "max_altitude": 50.0,
            "battery_capacity": 100.0,
            "position": {"x": 0.0, "y": 0.0, "z": 0.0}
        }
        resp = self.client.post("/drones", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201)
        return resp.json()

    def test_drone_has_moved_directed_distance(self):
        self._create_session()
        drone = self._create_drone()
        drone_id = drone["id"]

        # Take off first
        self.client.post(
            f"/drones/{drone_id}/command/take_off",
            params={"altitude": 5.0},
            headers=self.agent_headers
        )

        # Move North (Heading 0) 10m
        self.client.post(
            f"/drones/{drone_id}/command/move_towards",
            params={"distance": 10.0, "heading": 0.0},
            headers=self.agent_headers
        )

        # Move East (Heading 90) 10m
        self.client.post(
            f"/drones/{drone_id}/command/move_towards",
            params={"distance": 10.0, "heading": 90.0},
            headers=self.agent_headers
        )

        # Move South (Heading 180) 5m
        self.client.post(
            f"/drones/{drone_id}/command/move_towards",
            params={"distance": 5.0, "heading": 180.0},
            headers=self.agent_headers
        )

        # Check North (0 deg) - Expected 10m
        resp = self.client.get(
            "/check/drone_has_moved_directed_distance",
            params={"drone_id": drone_id, "min_distance": 9.9, "heading": 0.0, "tolerance": 5.0},
            headers=self.admin_headers
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertTrue(data["result"], f"Should have moved ~10m North. Value: {data.get('value')}")
        self.assertAlmostEqual(data["value"], 10.0, delta=0.5)

        # Check East (90 deg) - Expected 10m
        resp = self.client.get(
            "/check/drone_has_moved_directed_distance",
            params={"drone_id": drone_id, "min_distance": 9.9, "heading": 90.0, "tolerance": 5.0},
            headers=self.admin_headers
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["result"], f"Should have moved ~10m East. Value: {data.get('value')}")
        self.assertAlmostEqual(data["value"], 10.0, delta=0.5)

        # Check South (180 deg) - Expected 5m
        resp = self.client.get(
            "/check/drone_has_moved_directed_distance",
            params={"drone_id": drone_id, "min_distance": 4.9, "heading": 180.0, "tolerance": 5.0},
            headers=self.admin_headers
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["result"], f"Should have moved ~5m South. Value: {data.get('value')}")
        self.assertAlmostEqual(data["value"], 5.0, delta=0.5)

        # Check West (270 deg) - Expected 0m
        resp = self.client.get(
            "/check/drone_has_moved_directed_distance",
            params={"drone_id": drone_id, "min_distance": 0.1, "heading": 270.0, "tolerance": 5.0},
            headers=self.admin_headers
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["result"], f"Should NOT have moved West. Value: {data.get('value')}")
        self.assertAlmostEqual(data["value"], 0.0, delta=0.5)
        
        # Check tolerance
        # Move at 45 deg.
        self.client.post(
            f"/drones/{drone_id}/command/move_towards",
            params={"distance": 10.0, "heading": 45.0},
            headers=self.agent_headers
        )
        
        # Check 40 deg with 10 deg tolerance -> Should include the 45 deg move
        resp = self.client.get(
            "/check/drone_has_moved_directed_distance",
            params={"drone_id": drone_id, "min_distance": 9.9, "heading": 40.0, "tolerance": 10.0},
            headers=self.admin_headers
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["result"], "Should match 45deg move within 10deg tolerance of 40deg")
        self.assertAlmostEqual(data["value"], 10.0, delta=0.5)
        
        # Check 40 deg with 2 deg tolerance -> Should NOT include the 45 deg move
        resp = self.client.get(
            "/check/drone_has_moved_directed_distance",
            params={"drone_id": drone_id, "min_distance": 0.1, "heading": 40.0, "tolerance": 2.0},
            headers=self.admin_headers
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["result"], "Should NOT match 45deg move within 2deg tolerance of 40deg")
        self.assertAlmostEqual(data["value"], 0.0, delta=0.5)
