import time
import unittest

from fastapi.testclient import TestClient

from api.server import (
    ROLE_SECRETS,
    UserRole,
    app,
    drone_controller,
    obstacle_controller,
    session_controller,
    target_controller,
)
from models.drone import Drone
from models.obstacle import Obstacle, ObstacleType
from models.session import Session
from models.target import Target, TargetType


class ScreenshotEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()
        cls.admin_headers = {"X-API-Key": ROLE_SECRETS[UserRole.ADMIN]}

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)

    def _create_session(self, task_type: str = "others") -> str:
        suffix = int(time.time() * 1_000_000)
        payload = {
            "name": f"screenshot-session-{task_type}-{suffix}",
            "description": "Session created by screenshot endpoint tests",
            "with_examples": False,
            "task_type": task_type,
            "task_description": "Screenshot test task",
            "creator": "test",
        }
        resp = self.client.post("/sessions", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        session_id = resp.json()["id"]

        current_resp = self.client.post(f"/sessions/{session_id}/set-current", headers=self.admin_headers)
        self.assertEqual(current_resp.status_code, 200, current_resp.text)
        return session_id

    def _create_drone(self, name: str, position: dict[str, float]) -> dict:
        payload = {
            "name": name,
            "model": "ScreenshotTestModel",
            "max_speed": 10.0,
            "max_altitude": 50.0,
            "battery_capacity": 100.0,
            "position": position,
        }
        resp = self.client.post("/drones", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return resp.json()

    def _create_target(self, name: str, target_type: str, position: dict[str, float], radius: float) -> dict:
        payload = {
            "name": name,
            "type": target_type,
            "position": position,
            "radius": radius,
        }
        resp = self.client.post("/targets", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return resp.json()

    def _create_obstacle(self, name: str, obstacle_type: str, position: dict[str, float], radius: float) -> dict:
        payload = {
            "name": name,
            "type": obstacle_type,
            "position": position,
            "radius": radius,
            "height": 0,
        }
        resp = self.client.post("/obstacles", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return resp.json()

    def _sync_session(self, session_id: str) -> None:
        session_controller._save_current_data_to_session(session_id)  # type: ignore[attr-defined]

    def _seed_minimal_screenshot_session(self) -> str:
        suffix = int(time.time() * 1_000_000)
        session_id = f"label-session-{suffix}"
        session = Session(
            name=f"label-session-{suffix}",
            description="Minimal session for screenshot label tests",
            session_id=session_id,
            task_type="others",
            task_description="Screenshot label test task",
            creator="test",
        )
        session_controller.sessions[session_id] = session
        session_controller.current_session_id = session_id

        drone = Drone(
            name="Label Scout",
            model="ScreenshotTestModel",
            max_speed=10.0,
            max_altitude=50.0,
            battery_capacity=100.0,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            drone_id=f"drone-{suffix}",
        )
        target = Target(
            name="Label Target",
            target_type=TargetType.FIXED,
            position={"x": 0.0, "y": 8.0, "z": 0.0},
            radius=2.0,
            target_id=f"target-{suffix}",
        )
        obstacle = Obstacle(
            name="Label Rock",
            obstacle_type=ObstacleType.POINT,
            position={"x": -3.0, "y": 2.0, "z": 0.0},
            radius=1.0,
            height=0,
            obstacle_id=f"obstacle-{suffix}",
        )
        drone_controller.drones[drone.id] = drone
        target_controller.targets[target.id] = target
        obstacle_controller.obstacles[obstacle.id] = obstacle
        return session_id

    def _prepare_status_rich_session(self) -> str:
        session_id = self._create_session(task_type="area_search")
        drone = self._create_drone("Scout", {"x": 0.0, "y": 0.0, "z": 0.0})
        fixed_target = self._create_target("Fixed Alpha", "fixed", {"x": 0.0, "y": 8.0, "z": 0.0}, 2.0)
        moving_target = self._create_target("Moving Beta", "moving", {"x": 0.0, "y": 14.0, "z": 0.0}, 2.0)
        area_target = self._create_target("Search Circle", "circle", {"x": 6.0, "y": 6.0, "z": 0.0}, 4.0)
        self._create_obstacle("Rock", "point", {"x": -3.0, "y": 2.0, "z": 0.0}, 1.0)

        takeoff_resp = self.client.post(
            f"/drones/{drone['id']}/command/take_off",
            headers=self.admin_headers,
            params={"altitude": 1.0},
        )
        self.assertEqual(takeoff_resp.status_code, 200, takeoff_resp.text)

        move_fixed_resp = self.client.post(
            f"/drones/{drone['id']}/command/move_to",
            headers=self.admin_headers,
            params={"x": 0.0, "y": 8.0, "z": 1.0},
        )
        self.assertEqual(move_fixed_resp.status_code, 200, move_fixed_resp.text)

        move_moving_resp = self.client.post(
            f"/drones/{drone['id']}/command/move_to",
            headers=self.admin_headers,
            params={"x": 0.0, "y": 14.0, "z": 1.0},
        )
        self.assertEqual(move_moving_resp.status_code, 200, move_moving_resp.text)

        session_obj = session_controller.sessions[session_id]
        session_obj.initialize_area_coverage(area_target["id"], "circle", total_area=100.0)
        session_obj.update_area_coverage(area_target["id"], [(4.0, 4.0), (6.0, 6.0), (8.0, 8.0)], 16.0)
        self._sync_session(session_id)

        self.assertIn(drone["id"], session_obj.path_history)
        self.assertTrue(session_obj.has_drone_reached_target(drone["id"], fixed_target["id"]))
        self.assertTrue(session_obj.has_drone_reached_target(drone["id"], moving_target["id"]))
        return session_id

    def test_invalid_screenshot_format_rejected(self):
        self._create_session()
        resp = self.client.get(
            "/sessions/current/screenshot",
            headers=self.admin_headers,
            params={"format": "bmp"},
        )
        self.assertEqual(resp.status_code, 400, resp.text)
        self.assertIn("svg", resp.json()["detail"])
        self.assertIn("eps", resp.json()["detail"])

    def test_existing_raster_formats_still_work(self):
        self._prepare_status_rich_session()
        expected_types = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "pdf": "application/pdf",
        }
        for fmt, expected_content_type in expected_types.items():
            resp = self.client.get(
                "/sessions/current/screenshot",
                headers=self.admin_headers,
                params={"format": fmt, "width": 640, "height": 480},
            )
            self.assertEqual(resp.status_code, 200, f"{fmt}: {resp.text}")
            self.assertEqual(resp.headers["content-type"], expected_content_type)
            self.assertGreater(len(resp.content), 0)

    def test_svg_screenshot_with_status_overlays(self):
        self._prepare_status_rich_session()
        resp = self.client.get(
            "/sessions/current/screenshot",
            headers=self.admin_headers,
            params={"format": "svg", "show_status": "true", "width": 900, "height": 700},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.headers["content-type"], "image/svg+xml")
        body = resp.content.decode("utf-8")
        self.assertIn("<svg", body)
        self.assertIn("System: Ready", body)
        self.assertIn("LowerLeft:", body)
        self.assertIn("Dro/Tar/Obs:", body)
        self.assertIn("Scout", body)
        self.assertIn("Fixed Alpha", body)
        self.assertIn("Rock", body)
        self.assertIn("Type: Fixed", body)
        self.assertIn("Type: Point", body)
        self.assertIn("ID:", body)

    def test_svg_screenshot_can_hide_object_labels(self):
        session_id = self._seed_minimal_screenshot_session()
        resp = self.client.get(
            f"/sessions/{session_id}/screenshot",
            headers=self.admin_headers,
            params={"format": "svg", "show_status": "true", "show_label": "false", "width": 900, "height": 700},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.headers["content-type"], "image/svg+xml")
        body = resp.content.decode("utf-8")
        self.assertIn("<svg", body)
        self.assertIn("System: Ready", body)
        self.assertIn("LowerLeft:", body)
        self.assertIn("Dro/Tar/Obs:", body)
        self.assertNotIn("Label Scout", body)
        self.assertNotIn("Label Target", body)
        self.assertNotIn("Label Rock", body)
        self.assertNotIn("Type: Fixed", body)
        self.assertNotIn("Type: Point", body)
        self.assertNotIn("ID:", body)

    def test_eps_screenshot_for_specific_session(self):
        session_id = self._prepare_status_rich_session()
        resp = self.client.get(
            f"/sessions/{session_id}/screenshot",
            headers=self.admin_headers,
            params={"format": "eps", "show_status": "true", "width": 900, "height": 700},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.headers["content-type"], "application/postscript")
        body = resp.content.decode("utf-8")
        self.assertTrue(body.startswith("%!PS-Adobe-3.0 EPSF-3.0"))
        self.assertIn("System: Ready", body)
