import time
import unittest

from fastapi.testclient import TestClient

from api.server import (
    app,
    ROLE_SECRETS,
    UserRole,
    session_controller,
)
from models.target import Target, TargetType


class MovingTargetRefactorTests(unittest.TestCase):
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
            "name": f"moving-target-session-{task_type}-{suffix}",
            "description": "Moving target refactor test session",
            "with_examples": False,
            "task_type": task_type,
            "task_description": "Moving target tests",
            "creator": "test",
        }
        resp = self.client.post("/sessions", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        session_id = resp.json()["id"]

        set_resp = self.client.post(f"/sessions/{session_id}/set-current", headers=self.admin_headers)
        self.assertEqual(set_resp.status_code, 200, set_resp.text)
        return session_id

    def _create_drone(self, position=None, task_radius: float = 20.0):
        payload = {
            "name": "Moving Target Drone",
            "model": "TestModel",
            "max_speed": 10.0,
            "max_altitude": 50.0,
            "battery_capacity": 100.0,
            "task_radius": task_radius,
        }
        if position is not None:
            payload["position"] = position
        resp = self.client.post("/drones", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return resp.json()

    def _create_obstacle(self, position, radius: float = 1.0):
        payload = {
            "name": "Blocking Obstacle",
            "type": "circle",
            "position": position,
            "radius": radius,
            "height": 0,
        }
        resp = self.client.post("/obstacles", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return resp.json()

    def _create_moving_target(self, position=None, velocity=None, moving_path=None, moving_duration=10.0):
        payload = {
            "name": "Moving Target",
            "type": "moving",
            "position": position or {"x": 0.0, "y": 0.0, "z": 0.0},
            "radius": 2.0,
            "moving_duration": moving_duration,
        }
        if velocity is not None:
            payload["velocity"] = velocity
        if moving_path is not None:
            payload["moving_path"] = moving_path
        resp = self.client.post("/targets", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return resp.json()

    def test_velocity_mode_response_includes_canonical_fields(self):
        self._create_session(task_type="target_tracking")
        target = self._create_moving_target(
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            velocity={"x": 1.0, "y": 0.0, "z": 0.0},
            moving_duration=8.0,
        )

        resp = self.client.get("/targets", headers=self.admin_headers)
        self.assertEqual(resp.status_code, 200, resp.text)
        targets = resp.json()
        current = next(item for item in targets if item["id"] == target["id"])
        self.assertEqual(current["movement_mode"], "velocity")
        self.assertEqual(current["tracking_status"], "never_tracked")
        self.assertIsNone(current["last_tracked_at"])

    def test_rejects_moving_path_that_crosses_obstacle(self):
        self._create_session()
        self._create_obstacle(position={"x": 5.0, "y": 0.0, "z": 0.0}, radius=1.5)

        payload = {
            "name": "Blocked Moving Target",
            "type": "moving",
            "position": {"x": 0.0, "y": 0.0, "z": 0.0},
            "radius": 2.0,
            "moving_duration": 10.0,
            "moving_path": [
                {"x": 0.0, "y": 0.0, "z": 0.0},
                {"x": 10.0, "y": 0.0, "z": 0.0},
            ],
        }
        resp = self.client.post("/targets", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 400, resp.text)
        self.assertIn("moving_path segment intersects obstacle", resp.text)

    def test_path_mode_handles_large_delta_without_invalid_state(self):
        target = Target(
            name="Path Target",
            target_type=TargetType.MOVING,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            velocity={"x": 0.0, "y": 0.0, "z": 0.0},
            moving_path=[
                {"x": 0.0, "y": 0.0, "z": 0.0},
                {"x": 10.0, "y": 0.0, "z": 0.0},
                {"x": 20.0, "y": 0.0, "z": 0.0},
            ],
            moving_duration=10.0,
        )

        target.update_moving_target(15.0)

        self.assertAlmostEqual(target.position["x"], 10.0, places=3)
        self.assertAlmostEqual(target.position["y"], 0.0, places=3)
        self.assertEqual(target.movement_mode.value, "path")

    def test_tracking_status_can_become_stale_while_reach_stays_true(self):
        session_id = self._create_session(task_type="target_tracking")
        drone = self._create_drone(position={"x": 0.0, "y": 0.0, "z": 0.0}, task_radius=15.0)
        target = self._create_moving_target(
            position={"x": 0.0, "y": 10.0, "z": 0.0},
            velocity={"x": 1.0, "y": 0.0, "z": 0.0},
            moving_duration=10.0,
        )

        takeoff_resp = self.client.post(
            f"/drones/{drone['id']}/command/take_off",
            headers=self.admin_headers,
            params={"altitude": 1.0},
        )
        self.assertEqual(takeoff_resp.status_code, 200, takeoff_resp.text)

        move_resp = self.client.post(
            f"/drones/{drone['id']}/command/move_to",
            headers=self.admin_headers,
            params={"x": 0.0, "y": 10.0, "z": 1.0},
        )
        self.assertEqual(move_resp.status_code, 200, move_resp.text)

        target_resp = self.client.get(f"/targets/{target['id']}", headers=self.admin_headers)
        self.assertEqual(target_resp.status_code, 200, target_resp.text)
        self.assertEqual(target_resp.json()["tracking_status"], "tracked")
        self.assertIsNotNone(target_resp.json()["last_tracked_at"])

        progress_resp = self.client.get("/sessions/current/task-progress", headers=self.admin_headers)
        self.assertEqual(progress_resp.status_code, 200, progress_resp.text)
        self.assertEqual(progress_resp.json()["details"]["currently_tracked"], 1)
        self.assertEqual(progress_resp.json()["details"]["ever_tracked"], 1)

        session_obj = session_controller.sessions[session_id]
        session_obj.moving_target_tracking[target["id"]]["last_tracked_at"] -= 11.0

        stale_target_resp = self.client.get(f"/targets/{target['id']}", headers=self.admin_headers)
        self.assertEqual(stale_target_resp.status_code, 200, stale_target_resp.text)
        self.assertEqual(stale_target_resp.json()["tracking_status"], "stale")
        self.assertTrue(stale_target_resp.json()["is_reached"])

        reached_resp = self.client.get(
            "/check/target_is_reached",
            params={"target_id": target["id"]},
            headers=self.admin_headers,
        )
        self.assertEqual(reached_resp.status_code, 200, reached_resp.text)
        self.assertTrue(reached_resp.json()["result"])

    def test_tracking_and_reach_history_are_compact_but_informative(self):
        session_id = self._create_session(task_type="target_tracking")
        drone = self._create_drone(position={"x": 0.0, "y": 0.0, "z": 0.0}, task_radius=15.0)
        target = self._create_moving_target(
            position={"x": 0.0, "y": 10.0, "z": 0.0},
            velocity={"x": 1.0, "y": 0.0, "z": 0.0},
            moving_duration=10.0,
        )

        takeoff_resp = self.client.post(
            f"/drones/{drone['id']}/command/take_off",
            headers=self.admin_headers,
            params={"altitude": 1.0},
        )
        self.assertEqual(takeoff_resp.status_code, 200, takeoff_resp.text)

        move_resp = self.client.post(
            f"/drones/{drone['id']}/command/move_to",
            headers=self.admin_headers,
            params={"x": 0.0, "y": 10.0, "z": 1.0},
        )
        self.assertEqual(move_resp.status_code, 200, move_resp.text)

        reaches_resp = self.client.get(
            f"/sessions/{session_id}/target-reaches",
            headers=self.admin_headers,
        )
        self.assertEqual(reaches_resp.status_code, 200, reaches_resp.text)
        reach_data = reaches_resp.json()["target_reaches"]
        self.assertIn("by_drone", reach_data)
        self.assertIn("by_target", reach_data)
        self.assertGreaterEqual(reach_data["by_drone"][drone["id"]][target["id"]]["count"], 1)
        self.assertEqual(reach_data["by_target"][target["id"]]["unique_drones"], 1)
        self.assertTrue(reach_data["by_target"][target["id"]]["recent_reached_at"])

        tracking_resp = self.client.get(
            f"/sessions/{session_id}/moving-target-tracking",
            headers=self.admin_headers,
        )
        self.assertEqual(tracking_resp.status_code, 200, tracking_resp.text)
        tracking_data = tracking_resp.json()["moving_target_tracking"][target["id"]]
        self.assertEqual(tracking_data["tracking_status"], "tracked")
        self.assertGreaterEqual(tracking_data["total_track_events"], 1)
        self.assertEqual(len(tracking_data["recent_periods"]), 1)
        self.assertGreaterEqual(tracking_data["recent_periods"][0]["event_count"], 1)
        self.assertIn("by_drone", tracking_data)
        self.assertIn(drone["id"], tracking_data["by_drone"])
        self.assertGreaterEqual(tracking_data["by_drone"][drone["id"]]["total_track_events"], 1)
        self.assertEqual(len(tracking_data["by_drone"][drone["id"]]["recent_periods"]), 1)

    def test_check_moving_target_tracked_for_any_or_specific_drone(self):
        session_id = self._create_session(task_type="target_tracking")
        drone = self._create_drone(position={"x": 0.0, "y": 0.0, "z": 0.0}, task_radius=15.0)
        target = self._create_moving_target(
            position={"x": 0.0, "y": 10.0, "z": 0.0},
            velocity={"x": 1.0, "y": 0.0, "z": 0.0},
            moving_duration=10.0,
        )

        takeoff_resp = self.client.post(
            f"/drones/{drone['id']}/command/take_off",
            headers=self.admin_headers,
            params={"altitude": 1.0},
        )
        self.assertEqual(takeoff_resp.status_code, 200, takeoff_resp.text)

        move_resp = self.client.post(
            f"/drones/{drone['id']}/command/move_to",
            headers=self.admin_headers,
            params={"x": 0.0, "y": 10.0, "z": 1.0},
        )
        self.assertEqual(move_resp.status_code, 200, move_resp.text)

        session_obj = session_controller.sessions[session_id]
        target_tracking = session_obj.moving_target_tracking[target["id"]]
        target_tracking["track_periods"] = [{
            "start_at": 100.0,
            "end_at": 112.5,
            "last_update_at": 102.0,
            "event_count": 2,
            "last_tracked_by": drone["id"],
            "tracked_by": [drone["id"]],
        }]
        target_tracking["by_drone"][drone["id"]]["track_periods"] = [{
            "start_at": 100.0,
            "end_at": 112.5,
            "last_update_at": 102.0,
            "event_count": 2,
        }]

        any_resp = self.client.get(
            "/check/moving_target_tracked",
            params={"target_id": target["id"], "min_duration": 10.0},
            headers=self.admin_headers,
        )
        self.assertEqual(any_resp.status_code, 200, any_resp.text)
        self.assertTrue(any_resp.json()["result"])
        self.assertAlmostEqual(any_resp.json()["max_tracked_duration"], 12.5, places=2)

        drone_resp = self.client.get(
            "/check/moving_target_tracked",
            params={"target_id": target["id"], "drone_id": drone["id"], "min_duration": 10.0},
            headers=self.admin_headers,
        )
        self.assertEqual(drone_resp.status_code, 200, drone_resp.text)
        self.assertTrue(drone_resp.json()["result"])
        self.assertEqual(drone_resp.json()["drone_id"], drone["id"])

        too_long_resp = self.client.get(
            "/check/moving_target_tracked",
            params={"target_id": target["id"], "drone_id": drone["id"], "min_duration": 20.0},
            headers=self.admin_headers,
        )
        self.assertEqual(too_long_resp.status_code, 200, too_long_resp.text)
        self.assertFalse(too_long_resp.json()["result"])

    def test_check_moving_target_tracked_respects_since_timestamp(self):
        session_id = self._create_session(task_type="target_tracking")
        drone = self._create_drone(position={"x": 0.0, "y": 0.0, "z": 0.0}, task_radius=15.0)
        target = self._create_moving_target(
            position={"x": 0.0, "y": 10.0, "z": 0.0},
            velocity={"x": 1.0, "y": 0.0, "z": 0.0},
            moving_duration=10.0,
        )

        session_obj = session_controller.sessions[session_id]
        session_obj.moving_target_tracking[target["id"]] = {
            "first_tracked_at": 80.0,
            "last_tracked_at": 125.0,
            "last_tracked_by": drone["id"],
            "tracked_by": [drone["id"]],
            "total_track_events": 3,
            "track_periods": [
                {
                    "start_at": 80.0,
                    "end_at": 90.0,
                    "last_update_at": 80.0,
                    "event_count": 1,
                    "last_tracked_by": drone["id"],
                    "tracked_by": [drone["id"]],
                },
                {
                    "start_at": 95.0,
                    "end_at": 105.0,
                    "last_update_at": 95.0,
                    "event_count": 1,
                    "last_tracked_by": drone["id"],
                    "tracked_by": [drone["id"]],
                },
                {
                    "start_at": 110.0,
                    "end_at": 125.0,
                    "last_update_at": 110.0,
                    "event_count": 1,
                    "last_tracked_by": drone["id"],
                    "tracked_by": [drone["id"]],
                },
            ],
            "by_drone": {
                drone["id"]: {
                    "first_tracked_at": 80.0,
                    "last_tracked_at": 125.0,
                    "total_track_events": 3,
                    "track_periods": [
                        {"start_at": 80.0, "end_at": 90.0, "last_update_at": 80.0, "event_count": 1},
                        {"start_at": 95.0, "end_at": 105.0, "last_update_at": 95.0, "event_count": 1},
                        {"start_at": 110.0, "end_at": 125.0, "last_update_at": 110.0, "event_count": 1},
                    ],
                }
            },
        }

        scoped_resp = self.client.get(
            "/check/moving_target_tracked",
            params={
                "target_id": target["id"],
                "drone_id": drone["id"],
                "min_duration": 12.0,
                "since_timestamp": 100.0,
            },
            headers=self.admin_headers,
        )
        self.assertEqual(scoped_resp.status_code, 200, scoped_resp.text)
        scoped_data = scoped_resp.json()
        self.assertTrue(scoped_data["result"])
        self.assertAlmostEqual(scoped_data["max_tracked_duration"], 15.0, places=2)
        self.assertEqual(scoped_data["matching_periods"], 1)

        too_long_resp = self.client.get(
            "/check/moving_target_tracked",
            params={
                "target_id": target["id"],
                "drone_id": drone["id"],
                "min_duration": 18.0,
                "since_timestamp": 100.0,
            },
            headers=self.admin_headers,
        )
        self.assertEqual(too_long_resp.status_code, 200, too_long_resp.text)
        self.assertFalse(too_long_resp.json()["result"])

    def test_check_moving_target_tracked_validation(self):
        self._create_session()
        drone = self._create_drone(position={"x": 0.0, "y": 0.0, "z": 0.0})
        fixed_target_payload = {
            "name": "Fixed Target",
            "type": "fixed",
            "position": {"x": 0.0, "y": 0.0, "z": 0.0},
            "radius": 2.0,
        }
        fixed_resp = self.client.post("/targets", headers=self.admin_headers, json=fixed_target_payload)
        self.assertEqual(fixed_resp.status_code, 201, fixed_resp.text)
        fixed_target = fixed_resp.json()

        wrong_type_resp = self.client.get(
            "/check/moving_target_tracked",
            params={"target_id": fixed_target["id"]},
            headers=self.admin_headers,
        )
        self.assertEqual(wrong_type_resp.status_code, 400, wrong_type_resp.text)

        missing_drone_resp = self.client.get(
            "/check/moving_target_tracked",
            params={"target_id": fixed_target["id"], "drone_id": "missing"},
            headers=self.admin_headers,
        )
        self.assertIn(missing_drone_resp.status_code, (400, 404))

        negative_duration_resp = self.client.get(
            "/check/moving_target_tracked",
            params={"target_id": fixed_target["id"], "min_duration": -1.0},
            headers=self.admin_headers,
        )
        self.assertEqual(negative_duration_resp.status_code, 400, negative_duration_resp.text)
