import asyncio
import time
import unittest

from fastapi.testclient import TestClient

from api.server import (
    CommandRequest,
    MoveAlongPathRequest,
    ROLE_SECRETS,
    UserRole,
    app,
    direct_move_along_path,
    drone_controller,
    obstacle_controller,
    send_command as api_send_command,
    session_controller,
    target_controller,
)
from config.battery_config import BatteryConfig
from models.drone import DroneCommand


class MoveAlongPathPartialTests(unittest.TestCase):
    def _create_session(self) -> str:
        session_id = f"test-path-partial-{int(time.time() * 1_000_000)}"
        session_controller.add_session(
            {
                "id": session_id,
                "name": session_id,
                "description": "Session created by automated tests",
                "with_examples": False,
                "task_type": "others",
                "task_description": "Test task",
                "creator": "test",
            }
        )
        session_controller.set_current_session(session_id)
        return session_id

    def _create_drone(self, position=None, **overrides) -> dict:
        drone_data = {
            "name": "Path Test Drone",
            "model": "TestModel",
            "max_speed": 10.0,
            "max_altitude": 50.0,
            "battery_capacity": 100.0,
            "position": position or {"x": 0.0, "y": 0.0, "z": 0.0},
        }
        drone_data.update(overrides)
        return drone_controller.add_drone(drone_data)

    def _create_obstacle(self, name: str, position: dict, radius: float = 1.0, height: float = 5.0) -> dict:
        return obstacle_controller.add_obstacle(
            {
                "name": name,
                "type": "circle",
                "position": position,
                "radius": radius,
                "height": height,
            }
        )

    def _create_circle_target(self, name: str, position: dict, radius: float = 5.0) -> dict:
        return target_controller.add_target(
            {
                "name": name,
                "type": "circle",
                "position": position,
                "radius": radius,
            }
        )

    def _take_off(self, drone_id: str, altitude: float = 1.0) -> dict:
        return drone_controller.send_command(drone_id, command=DroneCommand.TAKE_OFF, parameters={"altitude": altitude})

    def _assert_no_point_feedback_fields(self, body: dict) -> None:
        self.assertNotIn("successful_points_count", body)
        self.assertNotIn("successful_points", body)
        self.assertNotIn("unsuccessful_points_count", body)
        self.assertNotIn("unsuccessful_points", body)

    def test_only_move_along_path_advertises_point_feedback_schema(self):
        openapi = app.openapi()
        schemas = openapi["components"]["schemas"]
        command_props = schemas["CommandResponse"]["properties"]
        path_props = schemas["MoveAlongPathCommandResponse"]["properties"]

        self.assertNotIn("successful_points_count", command_props)
        self.assertNotIn("successful_points", command_props)
        self.assertNotIn("unsuccessful_points_count", command_props)
        self.assertNotIn("unsuccessful_points", command_props)
        self.assertIn("successful_points_count", path_props)
        self.assertIn("successful_points", path_props)
        self.assertIn("unsuccessful_points_count", path_props)
        self.assertIn("unsuccessful_points", path_props)

        move_to_schema = openapi["paths"]["/drones/{drone_id}/command/move_to"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
        move_towards_schema = openapi["paths"]["/drones/{drone_id}/command/move_towards"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
        move_along_path_schema = openapi["paths"]["/drones/{drone_id}/command/move_along_path"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
        self.assertEqual(move_to_schema["$ref"], "#/components/schemas/CommandResponse")
        self.assertEqual(move_towards_schema["$ref"], "#/components/schemas/CommandResponse")
        self.assertEqual(move_along_path_schema["$ref"], "#/components/schemas/MoveAlongPathCommandResponse")

    def test_non_path_command_http_responses_omit_point_feedback_fields(self):
        self._create_session()
        drone = self._create_drone()
        takeoff = self._take_off(drone["id"])
        self.assertEqual(takeoff["status"], "success")
        headers = {"X-API-Key": ROLE_SECRETS[UserRole.ADMIN]}

        with TestClient(app) as client:
            direct_move_to = client.post(
                f"/drones/{drone['id']}/command/move_to",
                params={"x": 1.0, "y": 1.0, "z": 1.0},
                headers=headers,
            )
            self.assertEqual(direct_move_to.status_code, 200, direct_move_to.text)
            self.assertEqual(direct_move_to.json()["status"], "success")
            self._assert_no_point_feedback_fields(direct_move_to.json())

            direct_move_towards = client.post(
                f"/drones/{drone['id']}/command/move_towards",
                params={"distance": 1.0, "heading": 90.0},
                headers=headers,
            )
            self.assertEqual(direct_move_towards.status_code, 200, direct_move_towards.text)
            self.assertEqual(direct_move_towards.json()["status"], "success")
            self._assert_no_point_feedback_fields(direct_move_towards.json())

            generic_move_to = client.post(
                f"/drones/{drone['id']}/command",
                json={"command": "move_to", "parameters": {"x": 3.0, "y": 1.0, "z": 1.0}},
                headers=headers,
            )
            self.assertEqual(generic_move_to.status_code, 200, generic_move_to.text)
            self.assertEqual(generic_move_to.json()["status"], "success")
            self._assert_no_point_feedback_fields(generic_move_to.json())

    def test_move_along_path_http_responses_include_point_feedback_fields(self):
        self._create_session()
        drone = self._create_drone()
        takeoff = self._take_off(drone["id"])
        self.assertEqual(takeoff["status"], "success")
        headers = {"X-API-Key": ROLE_SECRETS[UserRole.ADMIN]}

        with TestClient(app) as client:
            direct_path = client.post(
                f"/drones/{drone['id']}/command/move_along_path",
                json={"waypoints": [{"x": 1.0, "y": 1.0, "z": 1.0}]},
                headers=headers,
            )
            self.assertEqual(direct_path.status_code, 200, direct_path.text)
            direct_body = direct_path.json()
            self.assertEqual(direct_body["status"], "success")
            self.assertEqual(direct_body["successful_points_count"], 1)
            self.assertEqual(direct_body["successful_points"], [[1.0, 1.0, 1.0]])
            self.assertEqual(direct_body["unsuccessful_points_count"], 0)
            self.assertEqual(direct_body["unsuccessful_points"], [])

            generic_path = client.post(
                f"/drones/{drone['id']}/command",
                json={"command": "move_along_path", "parameters": {"waypoints": [{"x": 2.0, "y": 1.0, "z": 1.0}]}},
                headers=headers,
            )
            self.assertEqual(generic_path.status_code, 200, generic_path.text)
            generic_body = generic_path.json()
            self.assertEqual(generic_body["status"], "success")
            self.assertEqual(generic_body["successful_points_count"], 1)
            self.assertEqual(generic_body["successful_points"], [[2.0, 1.0, 1.0]])
            self.assertEqual(generic_body["unsuccessful_points_count"], 0)
            self.assertEqual(generic_body["unsuccessful_points"], [])

    def test_move_along_path_request_defaults_partial_move_to_false(self):
        request = MoveAlongPathRequest(waypoints=[{"x": 1.0, "y": 2.0, "z": 3.0}, {"x": 4.0, "y": 5.0, "z": 6.0}])
        self.assertFalse(request.allow_partial_move)

    def test_move_to_and_move_along_path_battery_costs_have_no_base_cost(self):
        cost = BatteryConfig.calculate_movement_cost(
            command="move_along_path",
            start_pos={"x": 0.0, "y": 0.0, "z": 1.0},
            end_pos={"x": 10.0, "y": 0.0, "z": 1.0},
            weather="clear",
            environment=None,
        )
        self.assertAlmostEqual(cost, 0.05, places=4)

        move_to_cost = BatteryConfig.calculate_movement_cost(
            command="move_to",
            start_pos={"x": 0.0, "y": 0.0, "z": 1.0},
            end_pos={"x": 10.0, "y": 0.0, "z": 1.0},
            weather="clear",
            environment=None,
        )
        self.assertAlmostEqual(move_to_cost, 0.05, places=4)

    def test_move_along_path_accepts_single_waypoint(self):
        self._create_session()
        drone = self._create_drone()
        takeoff = self._take_off(drone["id"])
        self.assertEqual(takeoff["status"], "success")

        resp = asyncio.run(
            direct_move_along_path(
                drone["id"],
                MoveAlongPathRequest(
                    waypoints=[{"x": 12.0, "y": 5.0, "z": 1.0}],
                ),
                _role=UserRole.ADMIN,
            )
        )
        self.assertEqual(resp["status"], "success")
        self.assertIn("completed path with 1 waypoints", resp["message"])
        self.assertEqual(resp["successful_points_count"], 1)
        self.assertEqual(resp["successful_points"], [(12.0, 5.0, 1.0)])
        self.assertEqual(resp["unsuccessful_points_count"], 0)
        self.assertEqual(resp["unsuccessful_points"], [])

        drone_state = drone_controller.get_drone(drone["id"])
        self.assertEqual(drone_state["position"], {"x": 12.0, "y": 5.0, "z": 1.0})
        self.assertEqual(drone_state["status"], "hovering")

    def test_move_along_path_accepts_2d_waypoints_at_current_altitude(self):
        self._create_session()
        drone = self._create_drone()
        takeoff = self._take_off(drone["id"], altitude=7.0)
        self.assertEqual(takeoff["status"], "success")

        resp = asyncio.run(
            direct_move_along_path(
                drone["id"],
                MoveAlongPathRequest(
                    waypoints=[
                        {"x": 12.0, "y": 5.0},
                        {"x": 14.0, "y": 8.0},
                    ],
                ),
                _role=UserRole.ADMIN,
            )
        )
        self.assertEqual(resp["status"], "success")
        self.assertIn("completed path with 2 waypoints", resp["message"])
        self.assertEqual(resp["successful_points_count"], 2)
        self.assertEqual(resp["successful_points"], [(12.0, 5.0, 7.0), (14.0, 8.0, 7.0)])
        self.assertEqual(resp["unsuccessful_points_count"], 0)
        self.assertEqual(resp["unsuccessful_points"], [])

        drone_state = drone_controller.get_drone(drone["id"])
        self.assertEqual(drone_state["position"], {"x": 14.0, "y": 8.0, "z": 7.0})
        self.assertEqual(drone_state["status"], "hovering")

        drone_events = drone_controller.drones[drone["id"]].get_history_by_event("move_along_path")
        self.assertEqual(drone_events[-2]["position"], {"x": 12.0, "y": 5.0, "z": 7.0})
        self.assertEqual(drone_events[-1]["position"], {"x": 14.0, "y": 8.0, "z": 7.0})

    def test_move_along_path_stays_strict_by_default(self):
        self._create_session()
        drone = self._create_drone()
        takeoff = self._take_off(drone["id"])
        self.assertEqual(takeoff["status"], "success")
        self._create_obstacle(
            name="Segment Blocker",
            position={"x": 15.0, "y": 0.0, "z": 0.0},
            radius=2.0,
        )

        resp = asyncio.run(
            direct_move_along_path(
                drone["id"],
                MoveAlongPathRequest(
                    waypoints=[
                        {"x": 10.0, "y": 0.0, "z": 1.0},
                        {"x": 20.0, "y": 0.0, "z": 1.0},
                    ]
                ),
                _role=UserRole.ADMIN,
            )
        )
        self.assertEqual(resp["status"], "error")
        self.assertIn("Path to waypoint 2 blocked", resp["message"])
        self._assert_no_point_feedback_fields(resp)

        drone_state = drone_controller.get_drone(drone["id"])
        self.assertEqual(drone_state["position"], {"x": 0.0, "y": 0.0, "z": 1.0})
        self.assertEqual(drone_state["status"], "hovering")

    def test_allow_partial_move_stops_at_last_safe_waypoint_and_limits_side_effects(self):
        session_id = self._create_session()
        drone = self._create_drone()
        takeoff = self._take_off(drone["id"])
        self.assertEqual(takeoff["status"], "success")
        self._create_obstacle(
            name="Segment Blocker",
            position={"x": 15.0, "y": 0.0, "z": 0.0},
            radius=2.0,
        )

        battery_before = drone_controller.get_drone(drone["id"])["battery_level"]
        resp = asyncio.run(
            direct_move_along_path(
                drone["id"],
                MoveAlongPathRequest(
                    waypoints=[
                        {"x": 10.0, "y": 0.0, "z": 1.0},
                        {"x": 20.0, "y": 0.0, "z": 1.0},
                    ],
                    allow_partial_move=True,
                ),
                _role=UserRole.ADMIN,
            )
        )
        self.assertEqual(resp["status"], "partial_success")
        self.assertIn("partially completed path", resp["message"])
        self.assertIn("waypoint 2", resp["message"])
        self.assertEqual(resp["successful_points_count"], 1)
        self.assertEqual(resp["successful_points"], [(10.0, 0.0, 1.0)])
        self.assertEqual(resp["unsuccessful_points_count"], 1)
        self.assertEqual(resp["unsuccessful_points"], [(20.0, 0.0, 1.0)])

        drone_state = drone_controller.get_drone(drone["id"])
        self.assertEqual(drone_state["position"], {"x": 10.0, "y": 0.0, "z": 1.0})
        self.assertEqual(drone_state["status"], "hovering")

        expected_segment_cost = BatteryConfig.calculate_movement_cost(
            command="move_along_path",
            start_pos={"x": 0.0, "y": 0.0, "z": 1.0},
            end_pos={"x": 10.0, "y": 0.0, "z": 1.0},
            weather="clear",
            environment=None,
            drone_heading=90.0,
        )
        self.assertAlmostEqual(
            drone_state["battery_level"],
            battery_before - expected_segment_cost,
            places=4,
        )

        session_obj = session_controller.sessions[session_id]
        self.assertEqual(session_obj.total_commands_executed, 1)
        self.assertAlmostEqual(session_obj.total_distance_traveled, 10.0, places=4)
        self.assertGreater(session_obj.total_flight_time, 0.0)
        self.assertEqual(
            session_obj.path_history[drone["id"]],
            [
                {"x": 0.0, "y": 0.0, "z": 1.0},
                {"x": 10.0, "y": 0.0, "z": 1.0},
            ],
        )

        drone_events = drone_controller.drones[drone["id"]].get_history_by_event("move_along_path")
        self.assertEqual(len(drone_events), 1)
        self.assertEqual(drone_events[0]["position"], {"x": 10.0, "y": 0.0, "z": 1.0})

    def test_allow_partial_move_stops_at_last_waypoint_with_sufficient_battery(self):
        self._create_session()
        drone = self._create_drone(
            position={"x": 0.0, "y": 0.0, "z": 1.0},
            status="hovering",
            battery_level=5.07,
        )

        resp = asyncio.run(
            direct_move_along_path(
                drone["id"],
                MoveAlongPathRequest(
                    waypoints=[
                        {"x": 10.0, "y": 0.0, "z": 1.0},
                        {"x": 20.0, "y": 0.0, "z": 1.0},
                    ],
                    allow_partial_move=True,
                ),
                _role=UserRole.ADMIN,
            )
        )
        self.assertEqual(resp["status"], "partial_success")
        self.assertIn("partially completed path with 1 of 2 waypoints", resp["message"])
        self.assertIn("Insufficient battery for waypoint 2", resp["message"])
        self.assertEqual(resp["successful_points_count"], 1)
        self.assertEqual(resp["successful_points"], [(10.0, 0.0, 1.0)])
        self.assertEqual(resp["unsuccessful_points_count"], 1)
        self.assertEqual(resp["unsuccessful_points"], [(20.0, 0.0, 1.0)])

        drone_state = drone_controller.get_drone(drone["id"])
        self.assertEqual(drone_state["position"], {"x": 10.0, "y": 0.0, "z": 1.0})
        self.assertAlmostEqual(drone_state["battery_level"], 5.02, places=4)

    def test_allow_partial_move_returns_error_when_first_waypoint_lacks_battery(self):
        self._create_session()
        drone = self._create_drone(
            position={"x": 0.0, "y": 0.0, "z": 1.0},
            status="hovering",
            battery_level=5.04,
        )

        resp = asyncio.run(
            direct_move_along_path(
                drone["id"],
                MoveAlongPathRequest(
                    waypoints=[
                        {"x": 10.0, "y": 0.0, "z": 1.0},
                    ],
                    allow_partial_move=True,
                ),
                _role=UserRole.ADMIN,
            )
        )
        self.assertEqual(resp["status"], "error")
        self.assertIn("Insufficient battery for waypoint 1", resp["message"])
        self._assert_no_point_feedback_fields(resp)

        drone_state = drone_controller.get_drone(drone["id"])
        self.assertEqual(drone_state["position"], {"x": 0.0, "y": 0.0, "z": 1.0})
        self.assertAlmostEqual(drone_state["battery_level"], 5.04, places=4)

    def test_allow_partial_move_returns_error_when_first_waypoint_is_blocked(self):
        self._create_session()
        drone = self._create_drone()
        takeoff = self._take_off(drone["id"])
        self.assertEqual(takeoff["status"], "success")
        self._create_obstacle(
            name="First Waypoint Blocker",
            position={"x": 10.0, "y": 0.0, "z": 0.0},
            radius=1.5,
        )

        resp = asyncio.run(
            direct_move_along_path(
                drone["id"],
                MoveAlongPathRequest(
                    waypoints=[
                        {"x": 10.0, "y": 0.0, "z": 1.0},
                        {"x": 20.0, "y": 0.0, "z": 1.0},
                    ],
                    allow_partial_move=True,
                ),
                _role=UserRole.ADMIN,
            )
        )
        self.assertEqual(resp["status"], "error")
        self.assertIn("Waypoint 1 conflicts with obstacle", resp["message"])
        self._assert_no_point_feedback_fields(resp)

        drone_state = drone_controller.get_drone(drone["id"])
        self.assertEqual(drone_state["position"], {"x": 0.0, "y": 0.0, "z": 1.0})
        self.assertEqual(drone_state["status"], "hovering")

    def test_generic_command_supports_partial_move_for_waypoint_collision(self):
        self._create_session()
        drone = self._create_drone()
        takeoff = self._take_off(drone["id"])
        self.assertEqual(takeoff["status"], "success")
        self._create_obstacle(
            name="Waypoint Blocker",
            position={"x": 20.0, "y": 0.0, "z": 0.0},
            radius=1.0,
        )

        resp = asyncio.run(
            api_send_command(
                drone["id"],
                CommandRequest(
                    command="move_along_path",
                    parameters={
                        "waypoints": [
                            {"x": 10.0, "y": 0.0, "z": 1.0},
                            {"x": 20.0, "y": 0.0, "z": 1.0},
                        ],
                        "allow_partial_move": True,
                    },
                ),
                _role=UserRole.ADMIN,
            )
        )
        self.assertEqual(resp["status"], "partial_success")
        self.assertIn("partially completed path", resp["message"])
        self.assertIn("Waypoint 2 conflicts with obstacle", resp["message"])
        self.assertEqual(resp["successful_points_count"], 1)
        self.assertEqual(resp["successful_points"], [(10.0, 0.0, 1.0)])
        self.assertEqual(resp["unsuccessful_points_count"], 1)
        self.assertEqual(resp["unsuccessful_points"], [(20.0, 0.0, 1.0)])

        drone_state = drone_controller.get_drone(drone["id"])
        self.assertEqual(drone_state["position"], {"x": 10.0, "y": 0.0, "z": 1.0})

    def test_generic_command_accepts_2d_waypoints_at_current_altitude(self):
        self._create_session()
        drone = self._create_drone()
        takeoff = self._take_off(drone["id"], altitude=4.0)
        self.assertEqual(takeoff["status"], "success")

        resp = asyncio.run(
            api_send_command(
                drone["id"],
                CommandRequest(
                    command="move_along_path",
                    parameters={
                        "waypoints": [
                            {"x": 3.0, "y": 4.0},
                        ],
                    },
                ),
                _role=UserRole.ADMIN,
            )
        )
        self.assertEqual(resp["status"], "success")
        self.assertEqual(resp["successful_points_count"], 1)
        self.assertEqual(resp["successful_points"], [(3.0, 4.0, 4.0)])
        self.assertEqual(resp["unsuccessful_points_count"], 0)
        self.assertEqual(resp["unsuccessful_points"], [])

        drone_state = drone_controller.get_drone(drone["id"])
        self.assertEqual(drone_state["position"], {"x": 3.0, "y": 4.0, "z": 4.0})

    def test_large_multi_waypoint_path_preserves_final_state_and_history(self):
        session_id = self._create_session()
        drone = self._create_drone()
        takeoff = self._take_off(drone["id"])
        self.assertEqual(takeoff["status"], "success")

        waypoints = [{"x": float(i * 2), "y": float((i % 3) * 2), "z": 1.0} for i in range(1, 41)]
        resp = asyncio.run(
            direct_move_along_path(
                drone["id"],
                MoveAlongPathRequest(waypoints=waypoints),
                _role=UserRole.ADMIN,
            )
        )
        self.assertEqual(resp["status"], "success")
        self.assertIn("completed path with 40 waypoints", resp["message"])

        drone_state = drone_controller.get_drone(drone["id"])
        self.assertEqual(drone_state["position"], waypoints[-1])
        self.assertEqual(drone_state["status"], "hovering")

        session_obj = session_controller.sessions[session_id]
        self.assertEqual(session_obj.path_history[drone["id"]][0], {"x": 0.0, "y": 0.0, "z": 1.0})
        self.assertEqual(session_obj.path_history[drone["id"]][-1], waypoints[-1])
        self.assertEqual(len(session_obj.path_history[drone["id"]]), len(waypoints) + 1)

        drone_events = drone_controller.drones[drone["id"]].get_history_by_event("move_along_path")
        self.assertEqual(len(drone_events), len(waypoints))
        self.assertEqual(drone_events[-1]["position"], waypoints[-1])

    def test_path_battery_uses_precomputed_total_without_per_segment_consume(self):
        self._create_session()
        drone = self._create_drone()
        takeoff = self._take_off(drone["id"])
        self.assertEqual(takeoff["status"], "success")

        battery_before = drone_controller.get_drone(drone["id"])["battery_level"]
        waypoints = [
            {"x": 10.0, "y": 0.0, "z": 1.0},
            {"x": 10.0, "y": 10.0, "z": 1.0},
            {"x": 20.0, "y": 10.0, "z": 1.0},
        ]
        expected_cost = sum(
            BatteryConfig.calculate_movement_cost(
                command="move_along_path",
                start_pos=start,
                end_pos=end,
                weather="clear",
                environment=None,
            )
            for start, end in zip([{"x": 0.0, "y": 0.0, "z": 1.0}] + waypoints[:-1], waypoints)
        )

        original_consume_battery = drone_controller._consume_battery
        drone_controller._consume_battery = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("_consume_battery should not be called during optimized path execution")
        )
        try:
            resp = asyncio.run(
                direct_move_along_path(
                    drone["id"],
                    MoveAlongPathRequest(waypoints=waypoints),
                    _role=UserRole.ADMIN,
                )
            )
        finally:
            drone_controller._consume_battery = original_consume_battery

        self.assertEqual(resp["status"], "success")
        drone_state = drone_controller.get_drone(drone["id"])
        self.assertAlmostEqual(drone_state["battery_level"], battery_before - expected_cost, places=4)

    def test_command_recording_uses_lightweight_session_sync(self):
        session_id = self._create_session()
        drone = self._create_drone()
        takeoff = self._take_off(drone["id"])
        self.assertEqual(takeoff["status"], "success")

        session_obj = session_controller.sessions[session_id]
        original_to_dict = session_obj.to_dict
        session_obj.to_dict = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("command recording should not serialize full session data")
        )
        try:
            resp = asyncio.run(
                direct_move_along_path(
                    drone["id"],
                    MoveAlongPathRequest(waypoints=[{"x": 5.0, "y": 0.0, "z": 1.0}]),
                    _role=UserRole.ADMIN,
                )
            )
        finally:
            session_obj.to_dict = original_to_dict

        self.assertEqual(resp["status"], "success")

    def test_batched_path_coverage_increases_for_area_target(self):
        session_id = self._create_session()
        drone = self._create_drone(task_radius=4.0)
        target = self._create_circle_target(
            name="Coverage Circle",
            position={"x": 12.0, "y": 0.0, "z": 0.0},
            radius=6.0,
        )
        takeoff = self._take_off(drone["id"])
        self.assertEqual(takeoff["status"], "success")

        resp = asyncio.run(
            direct_move_along_path(
                drone["id"],
                MoveAlongPathRequest(
                    waypoints=[
                        {"x": 8.0, "y": 0.0, "z": 1.0},
                        {"x": 16.0, "y": 0.0, "z": 1.0},
                        {"x": 24.0, "y": 0.0, "z": 1.0},
                    ]
                ),
                _role=UserRole.ADMIN,
            )
        )
        self.assertEqual(resp["status"], "success")

        coverage = session_controller.sessions[session_id].area_coverage[target["id"]]
        self.assertGreater(coverage["covered_area"], 0.0)
        self.assertGreater(coverage["coverage_percentage"], 0.0)


if __name__ == "__main__":
    unittest.main()
