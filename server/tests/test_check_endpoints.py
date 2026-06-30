import time
import unittest

from fastapi.testclient import TestClient

from api.server import app, ROLE_SECRETS, UserRole, session_controller


class CheckEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()
        cls.admin_headers = {"X-API-Key": ROLE_SECRETS[UserRole.ADMIN]}

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)

    def _create_session(self, task_type: str = "others") -> str:
        """Create and activate a fresh session for testing."""
        suffix = int(time.time() * 1_000_000)
        payload = {
            "name": f"test-session-{task_type}-{suffix}",
            "description": "Session created by automated tests",
            "with_examples": False,
            "task_type": task_type,
            "task_description": "Test task",
            "creator": "test",
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
        }
        if position is not None:
            payload["position"] = position
        resp = self.client.post("/drones", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return resp.json()

    def _create_target(self, type: str = "circle", position=None, radius: float = 5.0):
        payload = {
            "name": "Test Target",
            "type": type,
            "position": position or {"x": 0.0, "y": 0.0, "z": 0.0},
            "radius": radius,
        }
        resp = self.client.post("/targets", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return resp.json()

    def _create_obstacle(self, type: str = "point", position=None, radius: float = 1.0):
        payload = {
            "name": "Test Obstacle",
            "type": type,
            "position": position or {"x": 0.0, "y": 0.0, "z": 0.0},
            "radius": radius,
            "height": 0,
        }
        resp = self.client.post("/obstacles", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return resp.json()

    def _sync_session(self, session_id: str) -> None:
        """Persist current controller state into the session model."""
        session_controller._save_current_data_to_session(session_id)  # type: ignore[attr-defined]

    def _take_off(self, drone_id: str, altitude: float) -> dict:
        resp = self.client.post(
            f"/drones/{drone_id}/command/take_off",
            headers=self.admin_headers,
            params={"altitude": altitude},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json()

    def _create_task(self, session_id: str, execution_check_apis: dict) -> dict:
        payload = {
            "name": f"check-task-{int(time.time() * 1_000_000)}",
            "content": "Timestamp scoped check task",
            "description": "Task used by timestamp-scoped check tests",
            "creator": "test",
            "execution_check_apis": execution_check_apis,
        }
        resp = self.client.post(f"/sessions/{session_id}/tasks", headers=self.admin_headers, json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return resp.json()

    def test_drone_position_altitude_status_checks(self):
        session_id = self._create_session()
        drone = self._create_drone(position={"x": 1.0, "y": 2.0, "z": 0.0})

        pos_resp = self.client.get(
            "/check/drone_position",
            params={"drone_id": drone["id"], "x": 1.0, "y": 2.0, "tolerance": 0.2},
            headers=self.admin_headers,
        )
        self.assertEqual(pos_resp.status_code, 200, pos_resp.text)
        self.assertTrue(pos_resp.json()["result"])
        self.assertAlmostEqual(pos_resp.json()["value"], 0.0, places=3)

        alt_resp = self.client.get(
            "/check/drone_altitude",
            params={"drone_id": drone["id"], "expected_altitude": 0.0, "tolerance": 0.1},
            headers=self.admin_headers,
        )
        self.assertEqual(alt_resp.status_code, 200, alt_resp.text)
        self.assertTrue(alt_resp.json()["result"])
        self.assertEqual(alt_resp.json()["value"], 0.0)

        status_resp = self.client.get(
            "/check/drone_status",
            params={"drone_id": drone["id"], "expected_status": "idle"},
            headers=self.admin_headers,
        )
        self.assertEqual(status_resp.status_code, 200, status_resp.text)
        self.assertTrue(status_resp.json()["result"])
        self.assertEqual(status_resp.json()["value"], "idle")

        # keep lint happy about unused variable
        self.assertIsNotNone(session_id)

    def test_ground_and_hover_checks(self):
        self._create_session()
        drone_ground = self._create_drone(position={"x": 0.0, "y": 0.0, "z": 0.0})
        drone_hover = self._create_drone(position={"x": 5.0, "y": 0.0, "z": 0.0})

        ground_resp = self.client.get(
            "/check/drone_on_ground",
            params={"drone_id": drone_ground["id"]},
            headers=self.admin_headers,
        )
        self.assertEqual(ground_resp.status_code, 200, ground_resp.text)
        self.assertTrue(ground_resp.json()["result"])

        update_hover = self.client.put(
            f"/drones/{drone_hover['id']}/position",
            headers=self.admin_headers,
            json={"x": 5.0, "y": 0.0, "z": 2.0},
        )
        self.assertEqual(update_hover.status_code, 200, update_hover.text)

        hovering_resp = self.client.get(
            "/check/drone_hovering",
            params={"drone_id": drone_hover["id"]},
            headers=self.admin_headers,
        )
        self.assertEqual(hovering_resp.status_code, 200, hovering_resp.text)
        self.assertTrue(hovering_resp.json()["result"])

        all_ground_resp = self.client.get("/check/all_drones_on_ground", headers=self.admin_headers)
        self.assertEqual(all_ground_resp.status_code, 200, all_ground_resp.text)
        self.assertFalse(all_ground_resp.json()["result"])

        lift_ground = self.client.put(
            f"/drones/{drone_ground['id']}/position",
            headers=self.admin_headers,
            json={"x": 0.0, "y": 0.0, "z": 1.5},
        )
        self.assertEqual(lift_ground.status_code, 200, lift_ground.text)

        all_hover_resp = self.client.get("/check/all_drones_hovering", headers=self.admin_headers)
        self.assertEqual(all_hover_resp.status_code, 200, all_hover_resp.text)
        self.assertTrue(all_hover_resp.json()["result"])

    def test_target_reach_checks(self):
        session_id = self._create_session(task_type="target_assignment")
        drone = self._create_drone(position={"x": 0.0, "y": 0.0, "z": 0.0})
        target = self._create_target(position={"x": 0.0, "y": 10.0, "z": 0.0}, radius=3.0)

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

        self._sync_session(session_id)

        reached_resp = self.client.get(
            "/check/target_is_reached",
            params={"target_id": target["id"]},
            headers=self.admin_headers,
        )
        self.assertEqual(reached_resp.status_code, 200, reached_resp.text)
        self.assertTrue(reached_resp.json()["result"])

        by_drone_resp = self.client.get(
            "/check/target_is_reached_by_drone",
            params={"target_id": target["id"], "drone_id": drone["id"]},
            headers=self.admin_headers,
        )
        self.assertEqual(by_drone_resp.status_code, 200, by_drone_resp.text)
        self.assertTrue(by_drone_resp.json()["result"])

        count_resp = self.client.get(
            "/check/target_reached_drone_number",
            params={"target_id": target["id"], "expected_count": 1},
            headers=self.admin_headers,
        )
        self.assertEqual(count_resp.status_code, 200, count_resp.text)
        self.assertTrue(count_resp.json()["result"])

    def test_target_reach_checks_respect_since_timestamp(self):
        session_id = self._create_session(task_type="target_assignment")
        drone_old = self._create_drone()
        drone_new = self._create_drone()
        target = self._create_target(position={"x": 0.0, "y": 10.0, "z": 0.0}, radius=3.0)
        self._sync_session(session_id)

        session_obj = session_controller.sessions[session_id]
        session_obj.target_reaches = {
            drone_old["id"]: {target["id"]: [100.0]},
            drone_new["id"]: {target["id"]: [200.0]},
        }

        reached_resp = self.client.get(
            "/check/target_is_reached",
            params={"target_id": target["id"], "since_timestamp": 150.0},
            headers=self.admin_headers,
        )
        self.assertEqual(reached_resp.status_code, 200, reached_resp.text)
        self.assertTrue(reached_resp.json()["result"])
        self.assertEqual(reached_resp.json()["value"], 1)
        self.assertEqual(reached_resp.json()["reached_by"], [drone_new["id"]])

        old_drone_resp = self.client.get(
            "/check/target_is_reached_by_drone",
            params={"target_id": target["id"], "drone_id": drone_old["id"], "since_timestamp": 150.0},
            headers=self.admin_headers,
        )
        self.assertEqual(old_drone_resp.status_code, 200, old_drone_resp.text)
        self.assertFalse(old_drone_resp.json()["result"])
        self.assertEqual(old_drone_resp.json()["value"], 0)

        count_resp = self.client.get(
            "/check/target_reached_drone_number",
            params={"target_id": target["id"], "expected_count": 2, "since_timestamp": 150.0},
            headers=self.admin_headers,
        )
        self.assertEqual(count_resp.status_code, 200, count_resp.text)
        self.assertFalse(count_resp.json()["result"])
        self.assertEqual(count_resp.json()["value"], 1)

        inclusive_resp = self.client.get(
            "/check/target_reached_drone_number",
            params={"target_id": target["id"], "expected_count": 2, "since_timestamp": 100.0},
            headers=self.admin_headers,
        )
        self.assertEqual(inclusive_resp.status_code, 200, inclusive_resp.text)
        self.assertTrue(inclusive_resp.json()["result"])
        self.assertEqual(inclusive_resp.json()["value"], 2)

    def test_area_search_and_task_progress_checks(self):
        session_id = self._create_session(task_type="area_search")
        target = self._create_target(type="circle", position={"x": 5.0, "y": 5.0, "z": 0.0}, radius=4.0)
        self._sync_session(session_id)

        session_obj = session_controller.sessions[session_id]
        session_obj.initialize_area_coverage(target["id"], "circle", total_area=100.0)
        session_obj.update_area_coverage(target["id"], [(0.0, 0.0)], 100.0)

        full_search_resp = self.client.get(
            "/check/target_is_fully_searched",
            params={"target_id": target["id"]},
            headers=self.admin_headers,
        )
        self.assertEqual(full_search_resp.status_code, 200, full_search_resp.text)
        self.assertTrue(full_search_resp.json()["result"])
        self.assertAlmostEqual(full_search_resp.json()["value"], 1.0)

        area_resp = self.client.get(
            "/check/target_searched_area_percentage",
            params={"target_id": target["id"], "expected_percentage": 0.5},
            headers=self.admin_headers,
        )
        self.assertEqual(area_resp.status_code, 200, area_resp.text)
        self.assertTrue(area_resp.json()["result"])

        progress_resp = self.client.get(
            "/check/task_progress",
            params={"expected_progress": 0.8},
            headers=self.admin_headers,
        )
        self.assertEqual(progress_resp.status_code, 200, progress_resp.text)
        self.assertTrue(progress_resp.json()["result"])
        self.assertAlmostEqual(progress_resp.json()["value"], 1.0)

        done_resp = self.client.get(
            "/check/task_done",
            params={},
            headers=self.admin_headers,
        )
        self.assertEqual(done_resp.status_code, 200, done_resp.text)
        self.assertTrue(done_resp.json()["result"])

    def test_drone_has_taken_off_altitude_matching(self):
        self._create_session()
        drone_high = self._create_drone()
        drone_low = self._create_drone()
        drone_range = self._create_drone()
        drone_near_exact = self._create_drone()
        drone_outside_exact = self._create_drone()

        self._take_off(drone_high["id"], 10.0)
        self._take_off(drone_low["id"], 9.4)
        self._take_off(drone_range["id"], 12.3)
        self._take_off(drone_near_exact["id"], 10.3)
        self._take_off(drone_outside_exact["id"], 10.6)

        threshold_resp = self.client.get(
            "/check/drone_has_taken_off",
            params={"drone_id": drone_high["id"], "min_altitude": 9.9},
            headers=self.admin_headers,
        )
        self.assertEqual(threshold_resp.status_code, 200, threshold_resp.text)
        threshold_data = threshold_resp.json()
        self.assertTrue(threshold_data["result"])
        self.assertEqual(threshold_data["value"], 1)
        self.assertEqual(threshold_data["min_altitude_threshold"], 9.9)
        self.assertIsNone(threshold_data["max_altitude_threshold"])
        self.assertEqual(threshold_data["tolerance"], 0.0)
        self.assertAlmostEqual(threshold_data["matched_altitude_min"], 9.9, places=3)
        self.assertIsNone(threshold_data["matched_altitude_max"])

        threshold_fail_resp = self.client.get(
            "/check/drone_has_taken_off",
            params={"drone_id": drone_low["id"], "min_altitude": 9.5},
            headers=self.admin_headers,
        )
        self.assertEqual(threshold_fail_resp.status_code, 200, threshold_fail_resp.text)
        self.assertFalse(threshold_fail_resp.json()["result"])
        self.assertEqual(threshold_fail_resp.json()["value"], 0)

        threshold_tolerance_resp = self.client.get(
            "/check/drone_has_taken_off",
            params={"drone_id": drone_high["id"], "min_altitude": 10.2, "tolerance": 0.3},
            headers=self.admin_headers,
        )
        self.assertEqual(threshold_tolerance_resp.status_code, 200, threshold_tolerance_resp.text)
        self.assertTrue(threshold_tolerance_resp.json()["result"])
        self.assertEqual(threshold_tolerance_resp.json()["value"], 1)

        threshold_tolerance_fail_resp = self.client.get(
            "/check/drone_has_taken_off",
            params={"drone_id": drone_low["id"], "min_altitude": 10.0, "tolerance": 0.5},
            headers=self.admin_headers,
        )
        self.assertEqual(threshold_tolerance_fail_resp.status_code, 200, threshold_tolerance_fail_resp.text)
        self.assertFalse(threshold_tolerance_fail_resp.json()["result"])
        self.assertEqual(threshold_tolerance_fail_resp.json()["value"], 0)

        range_resp = self.client.get(
            "/check/drone_has_taken_off",
            params={"drone_id": drone_range["id"], "min_altitude": 12.0, "max_altitude": 12.5},
            headers=self.admin_headers,
        )
        self.assertEqual(range_resp.status_code, 200, range_resp.text)
        range_data = range_resp.json()
        self.assertTrue(range_data["result"])
        self.assertEqual(range_data["value"], 1)
        self.assertEqual(range_data["max_altitude_threshold"], 12.5)
        self.assertAlmostEqual(range_data["matched_altitude_min"], 12.0, places=3)
        self.assertAlmostEqual(range_data["matched_altitude_max"], 12.5, places=3)

        range_tolerance_resp = self.client.get(
            "/check/drone_has_taken_off",
            params={"drone_id": drone_range["id"], "min_altitude": 12.4, "max_altitude": 12.4, "tolerance": 0.1},
            headers=self.admin_headers,
        )
        self.assertEqual(range_tolerance_resp.status_code, 200, range_tolerance_resp.text)
        self.assertTrue(range_tolerance_resp.json()["result"])
        self.assertEqual(range_tolerance_resp.json()["value"], 1)

        range_tolerance_fail_resp = self.client.get(
            "/check/drone_has_taken_off",
            params={"drone_id": drone_range["id"], "min_altitude": 12.5, "max_altitude": 12.5, "tolerance": 0.1},
            headers=self.admin_headers,
        )
        self.assertEqual(range_tolerance_fail_resp.status_code, 200, range_tolerance_fail_resp.text)
        self.assertFalse(range_tolerance_fail_resp.json()["result"])
        self.assertEqual(range_tolerance_fail_resp.json()["value"], 0)

        exact_resp = self.client.get(
            "/check/drone_has_taken_off",
            params={"drone_id": drone_near_exact["id"], "min_altitude": 10.0, "max_altitude": 10.0, "tolerance": 0.5},
            headers=self.admin_headers,
        )
        self.assertEqual(exact_resp.status_code, 200, exact_resp.text)
        self.assertTrue(exact_resp.json()["result"])
        self.assertEqual(exact_resp.json()["value"], 1)

        exact_fail_resp = self.client.get(
            "/check/drone_has_taken_off",
            params={"drone_id": drone_outside_exact["id"], "min_altitude": 10.0, "max_altitude": 10.0, "tolerance": 0.5},
            headers=self.admin_headers,
        )
        self.assertEqual(exact_fail_resp.status_code, 200, exact_fail_resp.text)
        self.assertFalse(exact_fail_resp.json()["result"])
        self.assertEqual(exact_fail_resp.json()["value"], 0)

    def test_drone_has_taken_off_validation(self):
        self._create_session()
        drone = self._create_drone()
        self._take_off(drone["id"], 10.0)

        negative_tolerance_resp = self.client.get(
            "/check/drone_has_taken_off",
            params={"drone_id": drone["id"], "min_altitude": 10.0, "tolerance": -0.1},
            headers=self.admin_headers,
        )
        self.assertEqual(negative_tolerance_resp.status_code, 400, negative_tolerance_resp.text)
        self.assertIn("Tolerance cannot be negative", negative_tolerance_resp.text)

        invalid_range_resp = self.client.get(
            "/check/drone_has_taken_off",
            params={"drone_id": drone["id"], "min_altitude": 12.0, "max_altitude": 10.0},
            headers=self.admin_headers,
        )
        self.assertEqual(invalid_range_resp.status_code, 400, invalid_range_resp.text)
        self.assertIn("max_altitude cannot be less than min_altitude", invalid_range_resp.text)

    def test_task_check_since_timestamp_scopes_history_leaf_checks(self):
        session_id = self._create_session()
        drone = self._create_drone()

        before_takeoff = time.time()
        time.sleep(0.01)
        self._take_off(drone["id"], 10.0)
        time.sleep(0.01)
        after_takeoff = time.time()

        task = self._create_task(session_id, {
            "endpoint": "/check/drone_has_taken_off",
            "parameters": {"drone_id": drone["id"], "min_altitude": 5.0},
            "expect": True,
        })

        unscoped_resp = self.client.get(
            f"/sessions/current/tasks/{task['id']}/check",
            headers=self.admin_headers,
        )
        self.assertEqual(unscoped_resp.status_code, 200, unscoped_resp.text)
        self.assertTrue(unscoped_resp.json()["result"])

        scoped_fail_resp = self.client.get(
            f"/sessions/current/tasks/{task['id']}/check",
            params={"since_timestamp": after_takeoff},
            headers=self.admin_headers,
        )
        self.assertEqual(scoped_fail_resp.status_code, 200, scoped_fail_resp.text)
        scoped_fail_data = scoped_fail_resp.json()
        self.assertFalse(scoped_fail_data["result"])
        self.assertEqual(
            scoped_fail_data["details"]["parameters"]["since_timestamp"],
            after_takeoff,
        )

        scoped_pass_resp = self.client.get(
            f"/check/task/{task['id']}",
            params={"since_timestamp": before_takeoff},
            headers=self.admin_headers,
        )
        self.assertEqual(scoped_pass_resp.status_code, 200, scoped_pass_resp.text)
        self.assertTrue(scoped_pass_resp.json()["result"])

    def test_task_check_since_timestamp_does_not_override_explicit_leaf_timestamp(self):
        session_id = self._create_session()
        drone = self._create_drone()

        before_takeoff = time.time()
        time.sleep(0.01)
        self._take_off(drone["id"], 10.0)
        time.sleep(0.01)
        after_takeoff = time.time()

        task = self._create_task(session_id, {
            "endpoint": "/check/drone_has_taken_off",
            "parameters": {
                "drone_id": drone["id"],
                "min_altitude": 5.0,
                "since_timestamp": before_takeoff,
            },
            "expect": True,
        })

        resp = self.client.get(
            f"/sessions/current/tasks/{task['id']}/check",
            params={"since_timestamp": after_takeoff},
            headers=self.admin_headers,
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertTrue(data["result"])
        self.assertEqual(data["details"]["parameters"]["since_timestamp"], before_takeoff)

    def test_distance_checks(self):
        self._create_session()
        drone1 = self._create_drone(position={"x": 0.0, "y": 0.0, "z": 0.0})
        drone2 = self._create_drone(position={"x": 3.0, "y": 4.0, "z": 0.0})  # distance 5.0
        target = self._create_target(position={"x": 0.0, "y": 0.0, "z": 0.0}, radius=3.5)
        obstacle = self._create_obstacle(position={"x": 0.0, "y": 4.0, "z": 0.0}, radius=1.0)

        at_home_resp = self.client.get(
            "/check/drone_at_home",
            params={"drone_id": drone1["id"], "tolerance": 0.5},
            headers=self.admin_headers,
        )
        self.assertEqual(at_home_resp.status_code, 200, at_home_resp.text)
        self.assertTrue(at_home_resp.json()["result"])

        battery_resp = self.client.get(
            "/check/drone_battery_level",
            params={"drone_id": drone1["id"], "min_level": 10.0},
            headers=self.admin_headers,
        )
        self.assertEqual(battery_resp.status_code, 200, battery_resp.text)
        self.assertTrue(battery_resp.json()["result"])

        heading_resp = self.client.get(
            "/check/drone_heading",
            params={"drone_id": drone1["id"], "expected_heading": 0.0, "tolerance": 10.0},
            headers=self.admin_headers,
        )
        self.assertEqual(heading_resp.status_code, 200, heading_resp.text)
        self.assertTrue(heading_resp.json()["result"])

        drone_target_resp = self.client.get(
            "/check/target_within_drone_distance",
            params={"drone_id": drone1["id"], "target_id": target["id"], "max_distance": 4.0},
            headers=self.admin_headers,
        )
        self.assertEqual(drone_target_resp.status_code, 200, drone_target_resp.text)
        self.assertTrue(drone_target_resp.json()["result"])
        self.assertAlmostEqual(drone_target_resp.json()["value"], 0.0, places=3)

        in_target_resp = self.client.get(
            "/check/drone_in_target",
            params={"drone_id": drone1["id"], "target_id": target["id"]},
            headers=self.admin_headers,
        )
        self.assertEqual(in_target_resp.status_code, 200, in_target_resp.text)
        self.assertTrue(in_target_resp.json()["result"])

        task_radius_resp = self.client.get(
            "/check/target_within_drone_task_radius",
            params={"drone_id": drone1["id"], "target_id": target["id"]},
            headers=self.admin_headers,
        )
        self.assertEqual(task_radius_resp.status_code, 200, task_radius_resp.text)
        self.assertTrue(task_radius_resp.json()["result"])

        perceived_target_resp = self.client.get(
            "/check/target_within_drone_perceived_radius",
            params={"drone_id": drone1["id"], "target_id": target["id"]},
            headers=self.admin_headers,
        )
        self.assertEqual(perceived_target_resp.status_code, 200, perceived_target_resp.text)
        self.assertTrue(perceived_target_resp.json()["result"])

        drone_obstacle_resp = self.client.get(
            "/check/obstacle_within_drone_distance",
            params={"drone_id": drone1["id"], "obstacle_id": obstacle["id"], "max_distance": 4.1},
            headers=self.admin_headers,
        )
        self.assertEqual(drone_obstacle_resp.status_code, 200, drone_obstacle_resp.text)
        self.assertTrue(drone_obstacle_resp.json()["result"])
        self.assertAlmostEqual(drone_obstacle_resp.json()["value"], 4.0, places=3)

        perceived_obstacle_resp = self.client.get(
            "/check/obstacle_within_drone_perceived_radius",
            params={"drone_id": drone1["id"], "obstacle_id": obstacle["id"]},
            headers=self.admin_headers,
        )
        self.assertEqual(perceived_obstacle_resp.status_code, 200, perceived_obstacle_resp.text)
        self.assertTrue(perceived_obstacle_resp.json()["result"])

        two_drone_resp = self.client.get(
            "/check/two_drones_distance",
            params={"drone_1_id": drone1["id"], "drone_2_id": drone2["id"], "max_distance": 5.0},
            headers=self.admin_headers,
        )
        self.assertEqual(two_drone_resp.status_code, 200, two_drone_resp.text)
        self.assertTrue(two_drone_resp.json()["result"])
        self.assertAlmostEqual(two_drone_resp.json()["value"], 5.0, places=3)

        # Test with min_distance
        # Distance is 5.0. If min_distance is 6.0, result should be False.
        min_dist_fail_resp = self.client.get(
            "/check/two_drones_distance",
            params={"drone_1_id": drone1["id"], "drone_2_id": drone2["id"], "min_distance": 6.0},
            headers=self.admin_headers,
        )
        self.assertEqual(min_dist_fail_resp.status_code, 200, min_dist_fail_resp.text)
        self.assertFalse(min_dist_fail_resp.json()["result"])

        # Test with min_distance success
        # Distance is 5.0. If min_distance is 4.0, result should be True.
        min_dist_success_resp = self.client.get(
            "/check/two_drones_distance",
            params={"drone_1_id": drone1["id"], "drone_2_id": drone2["id"], "min_distance": 4.0},
            headers=self.admin_headers,
        )
        self.assertEqual(min_dist_success_resp.status_code, 200, min_dist_success_resp.text)
        self.assertTrue(min_dist_success_resp.json()["result"])

        # Test range
        # Distance is 5.0. Range 4.0-6.0 should be True.
        range_resp = self.client.get(
            "/check/two_drones_distance",
            params={
                "drone_1_id": drone1["id"], 
                "drone_2_id": drone2["id"], 
                "min_distance": 4.0,
                "max_distance": 6.0
            },
            headers=self.admin_headers,
        )
        self.assertEqual(range_resp.status_code, 200, range_resp.text)
        self.assertTrue(range_resp.json()["result"])

    def test_drone_group_distance_check(self):
        self._create_session()
        drone1 = self._create_drone(position={"x": 0.0, "y": 0.0, "z": 0.0})
        drone2 = self._create_drone(position={"x": 3.0, "y": 4.0, "z": 0.0})  # 5 from drone1
        drone3 = self._create_drone(position={"x": 6.0, "y": 8.0, "z": 0.0})  # 10 from drone1, 5 from drone2
        drone4 = self._create_drone(position={"x": 100.0, "y": 100.0, "z": 0.0})

        all_pairs_resp = self.client.get(
            "/check/drone_group_distance",
            params=[
                ("drone_ids", drone1["id"]),
                ("drone_ids", drone2["id"]),
                ("drone_ids", drone3["id"]),
                ("min_distance", 4.0),
                ("max_distance", 10.0),
            ],
            headers=self.admin_headers,
        )
        self.assertEqual(all_pairs_resp.status_code, 200, all_pairs_resp.text)
        all_pairs_data = all_pairs_resp.json()
        self.assertTrue(all_pairs_data["result"])
        self.assertEqual(all_pairs_data["mode"], "all_pairs")
        self.assertEqual(all_pairs_data["value"], 3)
        self.assertEqual(all_pairs_data["total_pairs"], 3)
        self.assertEqual(all_pairs_data["passing_pairs"], 3)
        self.assertEqual(all_pairs_data["failing_pairs"], 0)
        self.assertEqual(len(all_pairs_data["pair_distances"]), 3)

        all_pairs_fail_resp = self.client.get(
            "/check/drone_group_distance",
            params=[
                ("drone_ids", drone1["id"]),
                ("drone_ids", drone2["id"]),
                ("drone_ids", drone3["id"]),
                ("min_distance", 6.0),
            ],
            headers=self.admin_headers,
        )
        self.assertEqual(all_pairs_fail_resp.status_code, 200, all_pairs_fail_resp.text)
        all_pairs_fail_data = all_pairs_fail_resp.json()
        self.assertFalse(all_pairs_fail_data["result"])
        self.assertEqual(all_pairs_fail_data["value"], 1)
        self.assertEqual(all_pairs_fail_data["passing_pairs"], 1)
        self.assertEqual(all_pairs_fail_data["failing_pairs"], 2)

        any_pair_resp = self.client.get(
            "/check/drone_group_distance",
            params=[
                ("drone_ids", drone1["id"]),
                ("drone_ids", drone2["id"]),
                ("drone_ids", drone4["id"]),
                ("min_distance", 4.0),
                ("max_distance", 10.0),
                ("mode", "any_pair"),
            ],
            headers=self.admin_headers,
        )
        self.assertEqual(any_pair_resp.status_code, 200, any_pair_resp.text)
        any_pair_data = any_pair_resp.json()
        self.assertTrue(any_pair_data["result"])
        self.assertEqual(any_pair_data["mode"], "any_pair")
        self.assertEqual(any_pair_data["value"], 1)
        self.assertEqual(any_pair_data["passing_pairs"], 1)
        self.assertEqual(any_pair_data["failing_pairs"], 2)

        any_pair_fail_resp = self.client.get(
            "/check/drone_group_distance",
            params=[
                ("drone_ids", drone1["id"]),
                ("drone_ids", drone2["id"]),
                ("drone_ids", drone3["id"]),
                ("min_distance", 11.0),
                ("mode", "any_pair"),
            ],
            headers=self.admin_headers,
        )
        self.assertEqual(any_pair_fail_resp.status_code, 200, any_pair_fail_resp.text)
        any_pair_fail_data = any_pair_fail_resp.json()
        self.assertFalse(any_pair_fail_data["result"])
        self.assertEqual(any_pair_fail_data["value"], 0)
        self.assertEqual(any_pair_fail_data["passing_pairs"], 0)
        self.assertEqual(any_pair_fail_data["failing_pairs"], 3)

        max_only_resp = self.client.get(
            "/check/drone_group_distance",
            params=[
                ("drone_ids", drone1["id"]),
                ("drone_ids", drone2["id"]),
                ("drone_ids", drone3["id"]),
                ("max_distance", 10.0),
            ],
            headers=self.admin_headers,
        )
        self.assertEqual(max_only_resp.status_code, 200, max_only_resp.text)
        self.assertTrue(max_only_resp.json()["result"])

        min_only_any_pair_resp = self.client.get(
            "/check/drone_group_distance",
            params=[
                ("drone_ids", drone1["id"]),
                ("drone_ids", drone2["id"]),
                ("drone_ids", drone3["id"]),
                ("min_distance", 9.0),
                ("mode", "any_pair"),
            ],
            headers=self.admin_headers,
        )
        self.assertEqual(min_only_any_pair_resp.status_code, 200, min_only_any_pair_resp.text)
        self.assertTrue(min_only_any_pair_resp.json()["result"])

        invalid_mode_resp = self.client.get(
            "/check/drone_group_distance",
            params=[
                ("drone_ids", drone1["id"]),
                ("drone_ids", drone2["id"]),
                ("mode", "bad_mode"),
            ],
            headers=self.admin_headers,
        )
        self.assertEqual(invalid_mode_resp.status_code, 400, invalid_mode_resp.text)

        too_few_resp = self.client.get(
            "/check/drone_group_distance",
            params=[("drone_ids", drone1["id"])],
            headers=self.admin_headers,
        )
        self.assertEqual(too_few_resp.status_code, 400, too_few_resp.text)

        duplicate_resp = self.client.get(
            "/check/drone_group_distance",
            params=[
                ("drone_ids", drone1["id"]),
                ("drone_ids", drone1["id"]),
            ],
            headers=self.admin_headers,
        )
        self.assertEqual(duplicate_resp.status_code, 400, duplicate_resp.text)

        missing_drone_resp = self.client.get(
            "/check/drone_group_distance",
            params=[
                ("drone_ids", drone1["id"]),
                ("drone_ids", "missing-drone"),
            ],
            headers=self.admin_headers,
        )
        self.assertEqual(missing_drone_resp.status_code, 404, missing_drone_resp.text)


if __name__ == "__main__":
    unittest.main()
