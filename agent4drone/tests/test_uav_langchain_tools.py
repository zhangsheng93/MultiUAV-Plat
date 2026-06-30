import json
import sys
from pathlib import Path
from types import SimpleNamespace

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from blackboard import PerceptionBlackboard
from uav_agent import UAVControlAgent
from uav_langchain_tools import _COVERAGE_PLAN_CACHE, create_uav_tools


class FakeUAVClient:
    def __init__(self):
        self.targets = [
            {
                "id": "circle-area",
                "name": "Circle Area",
                "type": "circle",
                "position": {"x": 10.0, "y": 10.0, "z": 0.0},
                "radius": 3.0,
            },
            {
                "id": "polygon-area",
                "name": "Polygon Area",
                "type": "polygon",
                "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                "vertices": [
                    {"x": 0.0, "y": 0.0},
                    {"x": 6.0, "y": 0.0},
                    {"x": 6.0, "y": 5.0},
                    {"x": 0.0, "y": 5.0},
                ],
            },
            {
                "id": "fixed-target",
                "name": "Fixed Target",
                "type": "fixed",
                "position": {"x": 30.0, "y": 30.0, "z": 0.0},
                "radius": 1.0,
            },
        ]
        self.drones = [
            {
                "id": "drone-1",
                "name": "Drone 1",
                "status": "idle",
                "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                "battery_level": 90.0,
                "perceived_radius": 100.0,
                "task_radius": 0.8,
            },
            {
                "id": "drone-2",
                "name": "Drone 2",
                "status": "hovering",
                "position": {"x": 20.0, "y": 0.0, "z": 10.0},
                "battery_level": 95.0,
                "perceived_radius": 100.0,
                "task_radius": 1.0,
            },
        ]
        self.move_to_calls = []
        self.move_towards_calls = []
        self.move_calls = []
        self.nearby_calls = []
        self.takeoff_calls = []
        self.land_calls = []

    def get_target(self, target_id):
        for target in self.targets:
            if target["id"] == target_id:
                return target
        raise KeyError(target_id)

    def get_obstacle(self, obstacle_id):
        return {
            "id": obstacle_id,
            "name": "Obstacle",
            "type": "circle",
            "position": {"x": 4.0, "y": 4.0, "z": 0.0},
            "radius": 1.0,
        }

    def get_nearby_entities(self, drone_id):
        self.nearby_calls.append(drone_id)
        return {
            "drone_id": drone_id,
            "targets": self.targets[:2],
            "obstacles": [
                {
                    "id": "obstacle-1",
                    "type": "circle",
                    "position": {"x": 40.0, "y": 40.0, "z": 0.0},
                    "radius": 1.0,
                }
            ],
            "drones": [],
        }

    def list_drones(self):
        return self.drones

    def get_drone_status(self, drone_id):
        for drone in self.drones:
            if drone["id"] == drone_id:
                return drone
        raise KeyError(drone_id)

    def move_along_path(self, drone_id, waypoints, allow_partial_move=True):
        drone = self.get_drone_status(drone_id)
        if waypoints:
            drone["position"] = {
                "x": waypoints[-1]["x"],
                "y": waypoints[-1]["y"],
                "z": waypoints[-1].get("z", drone["position"].get("z", 0.0)),
            }
        self.move_calls.append(
            {
                "drone_id": drone_id,
                "waypoints": waypoints,
                "allow_partial_move": allow_partial_move,
            }
        )
        return {
            "success": True,
            "drone_id": drone_id,
            "waypoint_count": len(waypoints),
            "allow_partial_move": allow_partial_move,
        }

    def move_to(self, drone_id, x, y, z):
        drone = self.get_drone_status(drone_id)
        drone["position"] = {"x": float(x), "y": float(y), "z": float(z)}
        self.move_to_calls.append({"drone_id": drone_id, "x": x, "y": y, "z": z})
        return {"success": True, "drone_id": drone_id, "position": drone["position"]}

    def move_towards(self, drone_id, distance, heading=None, dz=None):
        drone = self.get_drone_status(drone_id)
        self.move_towards_calls.append(
            {"drone_id": drone_id, "distance": distance, "heading": heading, "dz": dz}
        )
        z = drone["position"].get("z", 0.0)
        if dz is not None:
            z += float(dz)
        drone["position"] = {
            "x": drone["position"].get("x", 0.0) + float(distance),
            "y": drone["position"].get("y", 0.0),
            "z": z,
        }
        return {"success": True, "drone_id": drone_id, "position": drone["position"]}

    def take_off(self, drone_id, altitude=10.0):
        drone = self.get_drone_status(drone_id)
        drone["status"] = "hovering"
        drone["position"]["z"] = altitude
        self.takeoff_calls.append({"drone_id": drone_id, "altitude": altitude})
        return {"success": True, "drone_id": drone_id, "altitude": altitude}

    def land(self, drone_id):
        drone = self.get_drone_status(drone_id)
        drone["status"] = "landed"
        drone["position"]["z"] = 0.0
        self.land_calls.append({"drone_id": drone_id})
        return {"success": True, "drone_id": drone_id, "status": "landed"}


def _tools_by_name(client, blackboard=None):
    return {tool.name: tool for tool in create_uav_tools(client, blackboard=blackboard)}


def _call_tool(tool, payload=None):
    if payload is None:
        return tool.invoke({})
    return tool.invoke({"input_json": json.dumps(payload)})


def test_area_coverage_tools_are_available():
    tools = _tools_by_name(FakeUAVClient())

    assert "get_targets" not in tools
    assert "get_task_progress" not in tools
    assert "get_target_info" in tools
    assert "get_obstacle_info" in tools
    assert "sense_nearby_entities" in tools
    assert "update_blackboard_notes" in tools
    assert "generate_coverage_path" in tools
    assert "move_along_path" in tools
    assert "move_along_path_and_sense" in tools
    assert "navigate_to" in tools
    assert "navigate_to_and_sense" in tools
    assert "move_to" in tools
    assert "move_to_and_sense" in tools
    assert "move_towards_and_sense" in tools
    assert "navigate_waypoint_route" not in tools


def test_specific_target_and_obstacle_tools_return_details():
    tools = _tools_by_name(FakeUAVClient())

    target = json.loads(_call_tool(tools["get_target_info"], {"target_id": "circle-area"}))
    obstacle = json.loads(_call_tool(tools["get_obstacle_info"], {"obstacle_id": "obstacle-1"}))

    assert target["id"] == "circle-area"
    assert obstacle["id"] == "obstacle-1"


def test_sense_nearby_entities_queries_all_drones_and_updates_blackboard():
    client = FakeUAVClient()
    blackboard = PerceptionBlackboard()
    tools = _tools_by_name(client, blackboard=blackboard)

    result = json.loads(_call_tool(tools["sense_nearby_entities"], {}))

    assert client.nearby_calls == ["drone-1", "drone-2"]
    assert result["sensed_drone_ids"] == ["drone-1", "drone-2"]
    assert set(result["changes"]["new_targets"]) == {"circle-area", "polygon-area"}
    assert "obstacle-1" in result["changes"]["new_obstacles"]
    assert set(blackboard.targets) == {"circle-area", "polygon-area"}
    assert set(blackboard.obstacles) == {"obstacle-1"}
    assert "status" not in result["blackboard"]["targets"][0]


def test_sense_nearby_entities_accepts_explicit_drones_and_omits_seen_metadata():
    client = FakeUAVClient()
    blackboard = PerceptionBlackboard()
    tools = _tools_by_name(client, blackboard=blackboard)

    first = json.loads(_call_tool(tools["sense_nearby_entities"], {"drone_ids": ["drone-1"]}))
    second = json.loads(_call_tool(tools["sense_nearby_entities"], {"drone_ids": ["drone-1"]}))

    assert client.nearby_calls == ["drone-1", "drone-1"]
    assert set(first["changes"]["new_targets"]) == {"circle-area", "polygon-area"}
    assert set(second["changes"]["updated_targets"]) == {"circle-area", "polygon-area"}
    target_entry = blackboard.targets["circle-area"]
    assert "first_seen_by" not in target_entry
    assert "last_seen_by" not in target_entry
    assert "first_seen_step" not in target_entry
    assert "last_seen_step" not in target_entry
    assert "status" not in target_entry


def test_blackboard_compacts_geometry_fields_to_tuples():
    blackboard = PerceptionBlackboard()
    changes = blackboard.ingest_nearby(
        "drone-1",
        {
            "targets": [
                {
                    "id": "target-poly",
                    "name": "Target Poly",
                    "type": "polygon",
                    "position": {"x": 1.0, "y": 2.0, "z": 3.0},
                    "coordinates": {"x": 4.0, "y": 5.0},
                    "vertices": [
                        {"x": 0.0, "y": 0.0},
                        {"x": 1.0, "y": 0.0},
                        {"x": 1.0, "y": 1.0},
                    ],
                }
            ],
            "obstacles": [],
            "drones": [],
        },
    )

    assert changes["new_targets"] == ["target-poly"]
    facts = blackboard.targets["target-poly"]["facts"]
    assert facts["position"] == (1.0, 2.0, 3.0)
    assert facts["coordinates"] == (4.0, 5.0)
    assert facts["vertices"] == [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]
    summary_target = blackboard.summary()["targets"][0]
    assert summary_target["position"] == (1.0, 2.0, 3.0)
    assert summary_target["vertices"] == [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]


def test_blackboard_stores_session_id_and_clear_preserves_it():
    blackboard = PerceptionBlackboard(session_id="session-abc")
    blackboard.ingest_nearby(
        "drone-1",
        {
            "targets": [{"id": "target-1", "type": "fixed", "position": {"x": 1.0, "y": 2.0}}],
            "obstacles": [{"id": "obstacle-1", "type": "circle", "position": {"x": 3.0, "y": 4.0}}],
            "drones": [{"id": "drone-2", "position": {"x": 5.0, "y": 6.0}}],
        },
    )

    assert blackboard.session_id == "session-abc"
    assert blackboard._step == 1
    assert blackboard.targets
    assert blackboard.obstacles
    assert blackboard.drones

    blackboard.clear()

    assert blackboard.session_id == "session-abc"
    assert blackboard._step == 0
    assert blackboard.targets == {}
    assert blackboard.obstacles == {}
    assert blackboard.drones == {}


def test_move_to_and_sense_moves_then_updates_blackboard():
    client = FakeUAVClient()
    blackboard = PerceptionBlackboard()
    tools = _tools_by_name(client, blackboard=blackboard)

    result = json.loads(
        _call_tool(
            tools["move_to_and_sense"],
            {"drone_id": "drone-1", "x": 5.0, "y": 6.0, "z": 7.0},
        )
    )

    assert client.move_to_calls == [{"drone_id": "drone-1", "x": 5.0, "y": 6.0, "z": 7.0}]
    assert client.nearby_calls == ["drone-1"]
    assert result["move_result"]["success"] is True
    assert result["nearby"]["counts"]["targets"] == 2
    assert set(result["changes"]["new_targets"]) == {"circle-area", "polygon-area"}
    assert "obstacle-1" in result["changes"]["new_obstacles"]
    assert set(blackboard.targets) == {"circle-area", "polygon-area"}
    assert set(blackboard.obstacles) == {"obstacle-1"}


def test_move_towards_and_sense_moves_then_updates_blackboard():
    client = FakeUAVClient()
    blackboard = PerceptionBlackboard()
    tools = _tools_by_name(client, blackboard=blackboard)

    result = json.loads(
        _call_tool(
            tools["move_towards_and_sense"],
            {"drone_id": "drone-1", "distance": 12.0, "heading": 90.0, "dz": 2.0},
        )
    )

    assert client.move_towards_calls == [
        {"drone_id": "drone-1", "distance": 12.0, "heading": 90.0, "dz": 2.0}
    ]
    assert client.nearby_calls == ["drone-1"]
    assert result["move_result"]["success"] is True
    assert result["nearby"]["drone_id"] == "drone-1"
    assert set(result["changes"]["new_targets"]) == {"circle-area", "polygon-area"}
    assert set(blackboard.targets) == {"circle-area", "polygon-area"}


def test_navigate_to_and_sense_navigates_then_updates_blackboard():
    client = FakeUAVClient()
    client.drones[0]["task_radius"] = 20.0
    client.drones[0]["position"] = {"x": 82.0, "y": 0.0, "z": 10.0}
    blackboard = PerceptionBlackboard()
    tools = _tools_by_name(client, blackboard=blackboard)

    result = json.loads(
        _call_tool(
            tools["navigate_to_and_sense"],
            {
                "drone_id": "drone-1",
                "x": 100.0,
                "y": 0.0,
            },
        )
    )

    assert client.move_to_calls == [{"drone_id": "drone-1", "x": 100.0, "y": 0.0, "z": 10.0}]
    assert client.nearby_calls == ["drone-1"]
    assert result["navigation_result"]["success"] is True
    assert result["navigation_result"]["movement_strategy"] == "move_to"
    assert result["nearby"]["counts"]["targets"] == 2
    assert set(result["changes"]["new_targets"]) == {"circle-area", "polygon-area"}
    assert set(blackboard.targets) == {"circle-area", "polygon-area"}


def test_update_blackboard_notes_rejects_unknown_entities():
    tools = _tools_by_name(FakeUAVClient(), blackboard=PerceptionBlackboard())

    result = _call_tool(
        tools["update_blackboard_notes"],
        {
            "entity_id": "missing-target",
            "entity_kind": "target",
            "note": "Search later",
        },
    )

    assert "not in the perception blackboard" in result


def test_update_blackboard_notes_updates_note_without_overwriting_facts():
    client = FakeUAVClient()
    blackboard = PerceptionBlackboard()
    tools = _tools_by_name(client, blackboard=blackboard)
    _call_tool(tools["sense_nearby_entities"], {"drone_ids": ["drone-1"]})
    original_facts = dict(blackboard.obstacles["obstacle-1"]["facts"])

    result = json.loads(
        _call_tool(
            tools["update_blackboard_notes"],
            {
                "entity_id": "obstacle-1",
                "entity_kind": "obstacle",
                "note": "Avoid during eastbound route planning",
                "priority": "high",
            },
        )
    )

    assert result["updated"] is True
    assert result["entity"]["note"] == "Avoid during eastbound route planning"
    assert result["entity"]["priority"] == "high"
    assert blackboard.obstacles["obstacle-1"]["facts"] == original_facts


def test_generate_coverage_path_creates_cached_2d_circle_paths():
    _COVERAGE_PLAN_CACHE.clear()
    tools = _tools_by_name(FakeUAVClient())

    result = json.loads(
        _call_tool(
            tools["generate_coverage_path"],
            {
                "target_id": "circle-area",
                "drone_ids": ["drone-1", "drone-2"],
            },
        )
    )

    plan = _COVERAGE_PLAN_CACHE[result["coverage_plan_id"]]

    assert result["target"]["type"] == "circle"
    assert result["task_radius"] == 0.8
    assert result["point_spacing"] == 0.8
    assert [item["drone_id"] for item in result["drone_assignments"]] == ["drone-1", "drone-2"]
    assert set(plan["paths"]) == {"drone-1", "drone-2"}
    assert all("z" not in waypoint for path in plan["paths"].values() for waypoint in path)


def test_generate_coverage_path_handles_polygon_targets():
    _COVERAGE_PLAN_CACHE.clear()
    tools = _tools_by_name(FakeUAVClient())

    result = json.loads(
        _call_tool(
            tools["generate_coverage_path"],
            {
                "target_id": "polygon-area",
                "drone_ids": ["drone-1"],
            },
        )
    )

    assert result["target"]["type"] == "polygon"
    assert result["drone_assignments"][0]["drone_id"] == "drone-1"
    assert result["drone_assignments"][0]["waypoint_count"] > 1


def test_generate_coverage_path_ignores_legacy_point_spacing_input():
    _COVERAGE_PLAN_CACHE.clear()
    tools = _tools_by_name(FakeUAVClient())

    result = json.loads(
        _call_tool(
            tools["generate_coverage_path"],
            {
                "target_id": "circle-area",
                "drone_ids": ["drone-1"],
                "point_spacing": 0.5,
            },
        )
    )
    plan = _COVERAGE_PLAN_CACHE[result["coverage_plan_id"]]
    path = plan["paths"]["drone-1"]

    assert result["task_radius"] == 0.8
    assert result["point_spacing"] == 0.8
    assert result["drone_assignments"][0]["waypoint_count"] == len(path)
    assert len(path) < 30


def test_generate_coverage_path_rejects_non_area_targets():
    tools = _tools_by_name(FakeUAVClient())

    result = _call_tool(
        tools["generate_coverage_path"],
        {
            "target_id": "fixed-target",
            "drone_ids": ["drone-1"],
        },
    )

    assert "unsupported type" in result
    assert "circle" in result
    assert "polygon" in result


def test_move_along_path_dispatches_explicit_waypoints():
    client = FakeUAVClient()
    tools = _tools_by_name(client)

    result = json.loads(
        _call_tool(
            tools["move_along_path"],
            {
                "drone_id": "drone-1",
                "waypoints": [{"x": 1.0, "y": 2.0}, {"x": 3.0, "y": 4.0}],
                "allow_partial_move": True,
            },
        )
    )

    assert result["success"] is True
    assert client.move_calls == [
        {
            "drone_id": "drone-1",
            "waypoints": [{"x": 1.0, "y": 2.0}, {"x": 3.0, "y": 4.0}],
            "allow_partial_move": True,
        }
    ]


def test_move_along_path_and_sense_dispatches_explicit_waypoints_and_updates_blackboard():
    client = FakeUAVClient()
    blackboard = PerceptionBlackboard()
    tools = _tools_by_name(client, blackboard=blackboard)

    result = json.loads(
        _call_tool(
            tools["move_along_path_and_sense"],
            {
                "drone_id": "drone-1",
                "waypoints": [{"x": 1.0, "y": 2.0}, {"x": 3.0, "y": 4.0}],
                "allow_partial_move": "false",
            },
        )
    )

    assert client.move_calls == [
        {
            "drone_id": "drone-1",
            "waypoints": [{"x": 1.0, "y": 2.0}, {"x": 3.0, "y": 4.0}],
            "allow_partial_move": False,
        }
    ]
    assert client.nearby_calls == ["drone-1"]
    assert result["move_result"]["success"] is True
    assert result["move_result"]["allow_partial_move"] is False
    assert result["nearby"]["counts"]["obstacles"] == 1
    assert "obstacle-1" in blackboard.obstacles


class PartialSuccessMoveClient(FakeUAVClient):
    def move_along_path(self, drone_id, waypoints, allow_partial_move=True):
        self.move_calls.append(
            {
                "drone_id": drone_id,
                "waypoints": waypoints,
                "allow_partial_move": allow_partial_move,
            }
        )
        drone = self.get_drone_status(drone_id)
        drone["position"] = {
            "x": waypoints[0]["x"],
            "y": waypoints[0]["y"],
            "z": waypoints[0].get("z", drone["position"].get("z", 0.0)),
        }
        return {
            "success": False,
            "partial_success": True,
            "drone_id": drone_id,
            "completed_waypoints": 1,
        }


def test_move_along_path_preserves_partial_success_response():
    client = PartialSuccessMoveClient()
    tools = _tools_by_name(client)

    result = json.loads(
        _call_tool(
            tools["move_along_path"],
            {
                "drone_id": "drone-1",
                "waypoints": [{"x": 1.0, "y": 2.0}, {"x": 3.0, "y": 4.0}],
            },
        )
    )

    assert result["success"] is False
    assert result["partial_success"] is True


def test_move_along_path_and_sense_senses_after_partial_success():
    client = PartialSuccessMoveClient()
    blackboard = PerceptionBlackboard()
    tools = _tools_by_name(client, blackboard=blackboard)

    result = json.loads(
        _call_tool(
            tools["move_along_path_and_sense"],
            {
                "drone_id": "drone-1",
                "waypoints": [{"x": 1.0, "y": 2.0}, {"x": 3.0, "y": 4.0}],
            },
        )
    )

    assert result["move_result"]["success"] is False
    assert result["move_result"]["partial_success"] is True
    assert client.nearby_calls == ["drone-1"]
    assert set(blackboard.targets) == {"circle-area", "polygon-area"}


def test_move_along_path_defaults_to_partial_move():
    client = FakeUAVClient()
    tools = _tools_by_name(client)

    result = json.loads(
        _call_tool(
            tools["move_along_path"],
            {
                "drone_id": "drone-1",
                "waypoints": [{"x": 1.0, "y": 2.0}],
            },
        )
    )

    assert result["success"] is True
    assert client.move_calls[-1]["allow_partial_move"] is True


def test_move_along_path_parses_string_false_for_partial_move():
    client = FakeUAVClient()
    tools = _tools_by_name(client)

    _call_tool(
        tools["move_along_path"],
        {
            "drone_id": "drone-1",
            "waypoints": [{"x": 1.0, "y": 2.0}],
            "allow_partial_move": "false",
        },
    )

    assert client.move_calls[-1]["allow_partial_move"] is False


def test_move_along_path_dispatches_cached_coverage_plan():
    _COVERAGE_PLAN_CACHE.clear()
    client = FakeUAVClient()
    tools = _tools_by_name(client)
    plan_result = json.loads(
        _call_tool(
            tools["generate_coverage_path"],
            {
                "target_id": "circle-area",
                "drone_ids": ["drone-1", "drone-2"],
            },
        )
    )

    move_result = json.loads(
        _call_tool(
            tools["move_along_path"],
            {
                "drone_id": "drone-2",
                "coverage_plan_id": plan_result["coverage_plan_id"],
            },
        )
    )

    assert move_result["success"] is True
    move_call = client.move_calls[-1]
    assert move_call["drone_id"] == "drone-2"
    assert move_call["allow_partial_move"] is True
    assert move_call["waypoints"]
    assert all("coordinates" not in waypoint for waypoint in move_call["waypoints"])
    assert all("x" in waypoint and "y" in waypoint for waypoint in move_call["waypoints"])


def test_move_along_path_and_sense_dispatches_cached_coverage_plan():
    _COVERAGE_PLAN_CACHE.clear()
    client = FakeUAVClient()
    blackboard = PerceptionBlackboard()
    tools = _tools_by_name(client, blackboard=blackboard)
    plan_result = json.loads(
        _call_tool(
            tools["generate_coverage_path"],
            {
                "target_id": "circle-area",
                "drone_ids": ["drone-1", "drone-2"],
            },
        )
    )

    result = json.loads(
        _call_tool(
            tools["move_along_path_and_sense"],
            {
                "drone_id": "drone-2",
                "coverage_plan_id": plan_result["coverage_plan_id"],
            },
        )
    )

    assert result["move_result"]["success"] is True
    assert client.nearby_calls == ["drone-2"]
    move_call = client.move_calls[-1]
    assert move_call["drone_id"] == "drone-2"
    assert move_call["allow_partial_move"] is True
    assert move_call["waypoints"]
    assert set(blackboard.targets) == {"circle-area", "polygon-area"}


def test_navigate_to_uses_one_meter_arrival_tolerance_by_default():
    client = FakeUAVClient()
    client.drones[0]["task_radius"] = 20.0
    client.drones[0]["position"] = {"x": 82.0, "y": 0.0, "z": 10.0}
    tools = _tools_by_name(client)

    result = json.loads(
        _call_tool(
            tools["navigate_to"],
            {
                "drone_id": "drone-1",
                "x": 100.0,
                "y": 0.0,
            },
        )
    )

    assert result["success"] is True
    assert client.move_to_calls == [{"drone_id": "drone-1", "x": 100.0, "y": 0.0, "z": 10.0}]
    assert client.move_calls == []
    assert result["distance_remaining"] <= 1.0


def test_navigate_to_returns_success_when_already_within_arrival_tolerance():
    client = FakeUAVClient()
    client.drones[0]["task_radius"] = 20.0
    client.drones[0]["position"] = {"x": 99.5, "y": 0.0, "z": 10.0}
    tools = _tools_by_name(client)

    result = json.loads(
        _call_tool(
            tools["navigate_to"],
            {
                "drone_id": "drone-1",
                "x": 100.0,
                "y": 0.0,
            },
        )
    )

    assert result["success"] is True
    assert client.move_to_calls == []
    assert client.move_calls == []


class DirectMoveMissClient(FakeUAVClient):
    def move_to(self, drone_id, x, y, z):
        drone = self.get_drone_status(drone_id)
        drone["position"] = {"x": float(x) - 5.0, "y": float(y), "z": float(z)}
        self.move_to_calls.append({"drone_id": drone_id, "x": x, "y": y, "z": z})
        return {"success": True, "drone_id": drone_id, "position": drone["position"]}


def test_navigate_to_fails_if_direct_move_succeeds_but_misses_coordinate():
    client = DirectMoveMissClient()
    tools = _tools_by_name(client)

    result = json.loads(
        _call_tool(
            tools["navigate_to"],
            {
                "drone_id": "drone-1",
                "x": 100.0,
                "y": 0.0,
            },
        )
    )

    assert result["success"] is False
    assert result["distance_remaining"] == 5.0
    assert client.move_to_calls
    assert client.move_calls == []


class DirectMoveFailsClient(FakeUAVClient):
    def move_to(self, drone_id, x, y, z):
        self.move_to_calls.append({"drone_id": drone_id, "x": x, "y": y, "z": z})
        return {"success": False, "message": "Direct movement blocked"}

    def get_nearby_entities(self, drone_id):
        self.nearby_calls.append(drone_id)
        return {
            "drone_id": drone_id,
            "targets": [],
            "obstacles": [],
            "drones": [],
        }


class DirectMoveFailsWithNearbyClient(DirectMoveFailsClient):
    def get_nearby_entities(self, drone_id):
        return FakeUAVClient.get_nearby_entities(self, drone_id)


def test_navigate_to_falls_back_to_full_path_when_direct_move_fails():
    client = DirectMoveFailsClient()
    tools = _tools_by_name(client)

    result = json.loads(
        _call_tool(
            tools["navigate_to"],
            {
                "drone_id": "drone-1",
                "x": 100.0,
                "y": 0.0,
                "z": 10.0,
            },
        )
    )

    assert result["success"] is True
    assert client.move_to_calls
    assert client.nearby_calls == ["drone-1"]
    assert len(client.move_calls) == 1
    assert client.move_calls[0]["allow_partial_move"] is False
    assert client.move_calls[0]["waypoints"][-1] == {"x": 100.0, "y": 0.0, "z": 10.0}


def test_navigate_to_and_sense_senses_after_fallback_navigation():
    client = DirectMoveFailsWithNearbyClient()
    blackboard = PerceptionBlackboard()
    tools = _tools_by_name(client, blackboard=blackboard)

    result = json.loads(
        _call_tool(
            tools["navigate_to_and_sense"],
            {
                "drone_id": "drone-1",
                "x": 100.0,
                "y": 0.0,
                "z": 10.0,
            },
        )
    )

    assert result["navigation_result"]["success"] is True
    assert result["navigation_result"]["movement_strategy"] == "planned_fallback"
    assert client.nearby_calls == ["drone-1", "drone-1"]
    assert len(client.move_calls) == 1
    assert set(result["changes"]["updated_targets"]) == {"circle-area", "polygon-area"}
    assert set(blackboard.targets) == {"circle-area", "polygon-area"}


class PartialFallbackClient(DirectMoveFailsClient):
    def move_along_path(self, drone_id, waypoints, allow_partial_move=True):
        self.move_calls.append(
            {
                "drone_id": drone_id,
                "waypoints": waypoints,
                "allow_partial_move": allow_partial_move,
            }
        )
        drone = self.get_drone_status(drone_id)
        drone["position"] = {"x": 40.0, "y": 0.0, "z": waypoints[-1].get("z", 0.0)}
        return {"success": False, "partial_success": True, "completed_waypoints": 1}


def test_navigate_to_fails_if_fallback_is_partial():
    client = PartialFallbackClient()
    tools = _tools_by_name(client)

    result = json.loads(
        _call_tool(
            tools["navigate_to"],
            {
                "drone_id": "drone-1",
                "x": 100.0,
                "y": 0.0,
            },
        )
    )

    assert result["success"] is False
    assert result["last_move_result"]["partial_success"] is True
    assert len(client.move_calls) == 1


def test_agent_prompt_describes_area_coverage_workflow():
    agent = UAVControlAgent.__new__(UAVControlAgent)
    agent.tools = [
        SimpleNamespace(name="get_nearby_entities", description="Get nearby entities"),
        SimpleNamespace(name="sense_nearby_entities", description="Sense nearby entities"),
        SimpleNamespace(name="update_blackboard_notes", description="Update blackboard notes"),
        SimpleNamespace(name="get_target_info", description="Get target details"),
        SimpleNamespace(name="get_obstacle_info", description="Get obstacle details"),
        SimpleNamespace(name="generate_coverage_path", description="Generate coverage"),
        SimpleNamespace(name="navigate_to", description="Navigate to point"),
        SimpleNamespace(name="move_along_path", description="Move along path"),
    ]

    prompt = agent._build_system_prompt()

    assert "AREA COVERAGE WORKFLOW" in prompt
    assert "area_search" in prompt
    assert "ID AND NAME RESOLUTION" in prompt
    assert "8-character `id`" in prompt
    assert "Polygon Target 1" in prompt
    assert "Circle Target 1" in prompt
    assert "resolve their names to ids" in prompt
    assert "generate_coverage_path once per area target" in prompt
    assert "move_along_path with its drone_id and the returned coverage_plan_id" in prompt
    assert "POINT-TO-POINT NAVIGATION WORKFLOW" in prompt
    assert "For a single coordinate destination, use navigate_to" in prompt
    assert "move_along_path once with all waypoints in order and allow_partial_move=false" in prompt
    assert "Treat partial_success as incomplete" in prompt
    assert "navigate_waypoint_route" not in prompt
    assert "LOCAL PERCEPTION BLACKBOARD" in prompt
    assert "sense_nearby_entities" in prompt
    assert "last-known observations" in prompt
