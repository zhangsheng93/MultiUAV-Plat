#!/usr/bin/env python3
"""
MultiUAV-Plat Control System - API Definitions

Defines available APIs and commands for task creation interface.

Author: MultiUAV-Plat Control System
Version: Provided by application entrypoint
"""

from typing import Dict, List, Any


# Drone Commands - Available commands for drone control
DRONE_COMMANDS = [
    "take_off",
    "land",
    "move_to",
    "move_towards",
    "move_along_path",
    "change_altitude",
    "hover",
    "rotate",
    "return_home",
    "set_home",
    "calibrate",
    "take_photo",
    "send_message",
    "broadcast",
    "charge"
]


# API Endpoints organized by category
API_CATEGORIES = {
    "Health": [
        {
            "endpoint": "/",
            "method": "GET",
            "description": "API server health check",
            "parameters": []
        },
        {
            "endpoint": "/version",
            "method": "GET",
            "description": "API server version",
            "parameters": []
        }
    ],

    "Command Management": [
        {
            "endpoint": "/drones/{id}/command",
            "method": "POST",
            "description": "Send any drone command",
            "parameters": ["id", "command", "parameters"]
        },
        {
            "endpoint": "/drones/{id}/commands",
            "method": "GET",
            "description": "Get drone command history",
            "parameters": ["id"]
        },
        {
            "endpoint": "/commands/{command_id}",
            "method": "GET",
            "description": "Get command status",
            "parameters": ["command_id"]
        }
    ],

    "Drone Commands": [
        {
            "endpoint": "/drones/{id}/command/take_off",
            "method": "POST",
            "description": "Takeoff to altitude",
            "parameters": ["id", "altitude"]
        },
        {
            "endpoint": "/drones/{id}/command/land",
            "method": "POST",
            "description": "Land at position",
            "parameters": ["id"]
        },
        {
            "endpoint": "/drones/{id}/command/move_to",
            "method": "POST",
            "description": "Move to coordinates",
            "parameters": ["id", "x", "y", "z"]
        },
        {
            "endpoint": "/drones/{id}/command/move_towards",
            "method": "POST",
            "description": "Move distance in direction",
            "parameters": ["id", "distance", "heading", "dx", "dy", "dz", "azimuth", "elevation"]
        },
        {
            "endpoint": "/drones/{id}/command/move_along_path",
            "method": "POST",
            "description": "Follow waypoints",
            "parameters": ["id", "waypoints", "allow_partial_move"]
        },
        {
            "endpoint": "/drones/{id}/command/change_altitude",
            "method": "POST",
            "description": "Change altitude only",
            "parameters": ["id", "altitude"]
        },
        {
            "endpoint": "/drones/{id}/command/hover",
            "method": "POST",
            "description": "Hold position",
            "parameters": ["id", "duration"]
        },
        {
            "endpoint": "/drones/{id}/command/rotate",
            "method": "POST",
            "description": "Change heading/orientation",
            "parameters": ["id", "heading"]
        },
        {
            "endpoint": "/drones/{id}/command/return_home",
            "method": "POST",
            "description": "Return to launch",
            "parameters": ["id"]
        },
        {
            "endpoint": "/drones/{id}/command/set_home",
            "method": "POST",
            "description": "Set home position",
            "parameters": ["id"]
        },
        {
            "endpoint": "/drones/{id}/command/calibrate",
            "method": "POST",
            "description": "Calibrate sensors",
            "parameters": ["id"]
        },
        {
            "endpoint": "/drones/{id}/command/take_photo",
            "method": "POST",
            "description": "Capture image",
            "parameters": ["id"]
        },
        {
            "endpoint": "/drones/{id}/command/send_message",
            "method": "POST",
            "description": "Send to drone",
            "parameters": ["id", "target_drone_id", "message"]
        },
        {
            "endpoint": "/drones/{id}/command/broadcast",
            "method": "POST",
            "description": "Send to all",
            "parameters": ["id", "message"]
        },
        {
            "endpoint": "/drones/{id}/command/charge",
            "method": "POST",
            "description": "Charge battery",
            "parameters": ["id", "charge_amount"]
        }
    ],
    
    
    "Drone Management": [
        {
            "endpoint": "/drones",
            "method": "GET",
            "description": "List all drones",
            "parameters": []
        },
        {
            "endpoint": "/drones",
            "method": "POST",
            "description": "Register new drone",
            "parameters": ["name", "model", "max_speed", "max_altitude", "battery_capacity", "position"]
        },
        {
            "endpoint": "/drones/{id}",
            "method": "GET",
            "description": "Get drone details",
            "parameters": ["id"]
        },
        {
            "endpoint": "/drones/{id}",
            "method": "PUT",
            "description": "Update drone properties",
            "parameters": ["id", "name", "model", "status", "position", "battery_level", "home_position"]
        },
        {
            "endpoint": "/drones/{id}/position",
            "method": "PUT",
            "description": "Update drone position",
            "parameters": ["id", "x", "y", "z"]
        },
        {
            "endpoint": "/drones/{id}",
            "method": "DELETE",
            "description": "Delete drone",
            "parameters": ["id"]
        },
        {
            "endpoint": "/drones/{id}/battery",
            "method": "POST",
            "description": "Update battery level",
            "parameters": ["id", "battery_level"]
        },
        {
            "endpoint": "/drones/land_all",
            "method": "POST",
            "description": "Land all drones",
            "parameters": []
        },
        {
            "endpoint": "/drones/charge_all",
            "method": "POST",
            "description": "Fully charge all drones",
            "parameters": []
        }
    ],
    "Target Management": [
        {
            "endpoint": "/targets",
            "method": "GET",
            "description": "List all targets",
            "parameters": []
        },
        {
            "endpoint": "/targets",
            "method": "POST",
            "description": "Create target",
            "parameters": ["name", "type", "position", "radius"]
        },
        {
            "endpoint": "/targets/{id}",
            "method": "GET",
            "description": "Get target details",
            "parameters": ["id"]
        },
        {
            "endpoint": "/targets/{id}",
            "method": "PUT",
            "description": "Update target",
            "parameters": ["id"]
        },
        {
            "endpoint": "/targets/{id}",
            "method": "DELETE",
            "description": "Delete target",
            "parameters": ["id"]
        },
        {
            "endpoint": "/targets/type/{type}",
            "method": "GET",
            "description": "List targets by type",
            "parameters": ["type"]
        },
        {
            "endpoint": "/targets/waypoints/{id}/check-drone",
            "method": "POST",
            "description": "Check if drone is in waypoint range",
            "parameters": ["id", "drone_position"]
        }
    ],

    "Obstacle Management": [
        {
            "endpoint": "/obstacles",
            "method": "GET",
            "description": "List all obstacles",
            "parameters": []
        },
        {
            "endpoint": "/obstacles",
            "method": "POST",
            "description": "Create obstacle",
            "parameters": ["name", "type", "position"]
        },
        {
            "endpoint": "/obstacles/{id}",
            "method": "GET",
            "description": "Get obstacle",
            "parameters": ["id"]
        },
        {
            "endpoint": "/obstacles/{id}",
            "method": "PUT",
            "description": "Update obstacle",
            "parameters": ["id"]
        },
        {
            "endpoint": "/obstacles/{id}",
            "method": "DELETE",
            "description": "Delete obstacle",
            "parameters": ["id"]
        },
        {
            "endpoint": "/obstacles/type/{type}",
            "method": "GET",
            "description": "List obstacles by type",
            "parameters": ["type"]
        },
        {
            "endpoint": "/obstacles/path_collision",
            "method": "POST",
            "description": "Check path collision",
            "parameters": ["start", "end", "safety_margin"]
        },
        {
            "endpoint": "/obstacles/point_collision",
            "method": "POST",
            "description": "Check point collision",
            "parameters": ["x", "y", "z", "margin"]
        }
    ],

    "Environment Management": [
        {
            "endpoint": "/environments",
            "method": "GET",
            "description": "List all environments",
            "parameters": []
        },
        {
            "endpoint": "/environments",
            "method": "POST",
            "description": "Create environment",
            "parameters": ["name", "weather", "temperature", "humidity"]
        },
        {
            "endpoint": "/environments/current",
            "method": "GET",
            "description": "Get active environment",
            "parameters": []
        },
        {
            "endpoint": "/environments/{id}",
            "method": "GET",
            "description": "Get environment",
            "parameters": ["id"]
        },
        {
            "endpoint": "/environments/{id}",
            "method": "PUT",
            "description": "Update environment",
            "parameters": ["id"]
        },
        {
            "endpoint": "/environments/{id}",
            "method": "DELETE",
            "description": "Delete environment",
            "parameters": ["id"]
        },
        {
            "endpoint": "/environments/{id}/set-current",
            "method": "POST",
            "description": "Set environment as active",
            "parameters": ["id"]
        }
    ],

    "Session Management": [
        {
            "endpoint": "/sessions",
            "method": "GET",
            "description": "List all sessions",
            "parameters": []
        },
        {
            "endpoint": "/sessions",
            "method": "POST",
            "description": "Create session with auto-generated ID",
            "parameters": [
                "name", "description", "with_examples", "task_type",
                "task_description", "is_distance_3d", "canvas_width",
                "canvas_height", "creator", "drones", "targets",
                "obstacles", "environment", "data"
            ]
        },
        {
            "endpoint": "/sessions/current",
            "method": "GET",
            "description": "Get active session",
            "parameters": ["data"]
        },
        {
            "endpoint": "/sessions/current/data",
            "method": "GET",
            "description": "Get active session with complete data",
            "parameters": []
        },
        {
            "endpoint": "/sessions/current/screenshot",
            "method": "GET",
            "description": "Export active session screenshot",
            "parameters": ["format", "width", "height", "center_x", "center_y", "scale_px_per_meter", "show_status", "show_label"]
        },
        {
            "endpoint": "/sessions/current/reset",
            "method": "POST",
            "description": "Reset current session history and statistics",
            "parameters": []
        },
        {
            "endpoint": "/sessions/{id}",
            "method": "POST",
            "description": "Create/restore session with specific ID",
            "parameters": [
                "id", "name", "description", "with_examples", "task_type",
                "task_description", "is_distance_3d", "canvas_width",
                "canvas_height", "creator", "drones", "targets",
                "obstacles", "environment", "data"
            ]
        },
        {
            "endpoint": "/sessions/{id}",
            "method": "GET",
            "description": "Get session",
            "parameters": ["id", "data"]
        },
        {
            "endpoint": "/sessions/{id}/data",
            "method": "GET",
            "description": "Export complete session data",
            "parameters": ["id"]
        },
        {
            "endpoint": "/sessions/{session_id}/screenshot",
            "method": "GET",
            "description": "Export session screenshot",
            "parameters": ["session_id", "format", "width", "height", "center_x", "center_y", "scale_px_per_meter", "show_status", "show_label"]
        },
        {
            "endpoint": "/sessions/{id}/set-current",
            "method": "POST",
            "description": "Set session as active",
            "parameters": ["id"]
        },
        {
            "endpoint": "/sessions/{id}",
            "method": "PUT",
            "description": "Update session metadata and settings",
            "parameters": [
                "id", "name", "description", "status", "task_type",
                "task_description", "is_distance_3d", "canvas_width",
                "canvas_height", "creator", "data"
            ]
        },
        {
            "endpoint": "/sessions/{id}",
            "method": "DELETE",
            "description": "Delete session",
            "parameters": ["id"]
        },
        {
            "endpoint": "/sessions/{id}/reset",
            "method": "POST",
            "description": "Reset to initial state",
            "parameters": ["id"]
        },
        {
            "endpoint": "/sessions/{id}/command-history",
            "method": "GET",
            "description": "Get recent command history",
            "parameters": ["id", "limit"]
        },
        {
            "endpoint": "/sessions/{id}/status-history",
            "method": "GET",
            "description": "Get drone status history",
            "parameters": ["id", "drone_id"]
        },
        {
            "endpoint": "/sessions/{id}/target-reaches",
            "method": "GET",
            "description": "Get target reach summaries",
            "parameters": ["id"]
        },
        {
            "endpoint": "/sessions/{id}/moving-target-tracking",
            "method": "GET",
            "description": "Get moving-target tracking summaries",
            "parameters": ["id"]
        },
        {
            "endpoint": "/sessions/{id}/area-coverage",
            "method": "GET",
            "description": "Get area coverage summary",
            "parameters": ["id"]
        },
        {
            "endpoint": "/sessions/{id}/task-progress",
            "method": "GET",
            "description": "Get task progress summary",
            "parameters": ["id"]
        }
    ],

    "Task Management": [
        {
            "endpoint": "/sessions/current/tasks",
            "method": "GET",
            "description": "Get all tasks in current session",
            "parameters": []
        },
        {
            "endpoint": "/sessions/current/tasks/next",
            "method": "GET",
            "description": "Get next pending task in current session",
            "parameters": []
        },
        {
            "endpoint": "/sessions/current/tasks/{task_id}",
            "method": "GET",
            "description": "Get specific task from current session",
            "parameters": ["task_id"]
        },
        {
            "endpoint": "/sessions/current/tasks/{task_id}/check",
            "method": "GET",
            "description": "Evaluate task execution checks in current session",
            "parameters": ["task_id", "since_timestamp"]
        },
        {
            "endpoint": "/sessions/current/tasks/{task_id}/mark-done",
            "method": "POST",
            "description": "Mark current-session task as completed",
            "parameters": ["task_id"]
        },
        {
            "endpoint": "/sessions/current/tasks/{task_id}/mark-pending",
            "method": "POST",
            "description": "Mark current-session task as pending",
            "parameters": ["task_id"]
        },
        {
            "endpoint": "/sessions/{session_id}/tasks",
            "method": "GET",
            "description": "Get all tasks in a session",
            "parameters": ["session_id"]
        },
        {
            "endpoint": "/sessions/{session_id}/tasks",
            "method": "POST",
            "description": "Create a new task",
            "parameters": [
                "session_id", "name", "content", "content_aliases",
                "description", "creator", "originated_from", "difficulty",
                "related_apis", "execution_check_apis", "commands"
            ]
        },
        {
            "endpoint": "/sessions/{session_id}/tasks/{task_id}",
            "method": "GET",
            "description": "Get specific task",
            "parameters": ["session_id", "task_id"]
        },
        {
            "endpoint": "/sessions/{session_id}/tasks/{task_id}",
            "method": "PUT",
            "description": "Update task",
            "parameters": [
                "session_id", "task_id", "name", "content",
                "content_aliases", "description", "creator",
                "originated_from", "difficulty", "related_apis",
                "execution_check_apis", "commands"
            ]
        },
        {
            "endpoint": "/sessions/{session_id}/tasks/{task_id}",
            "method": "DELETE",
            "description": "Delete task",
            "parameters": ["session_id", "task_id"]
        },
        {
            "endpoint": "/sessions/{session_id}/tasks/{task_id}/mark-done",
            "method": "POST",
            "description": "Mark task as completed",
            "parameters": ["session_id", "task_id"]
        },
        {
            "endpoint": "/sessions/{session_id}/tasks/{task_id}/mark-pending",
            "method": "POST",
            "description": "Mark task as pending",
            "parameters": ["session_id", "task_id"]
        },
        {
            "endpoint": "/sessions/{session_id}/tasks/swap",
            "method": "POST",
            "description": "Swap the order of two tasks in a session",
            "parameters": ["session_id", "task_id_1", "task_id_2"]
        }
    ],

    "Proximity": [
        {
            "endpoint": "/drones/{id}/nearby",
            "method": "GET",
            "description": "Get nearby drones, targets, obstacles",
            "parameters": ["id"]
        },
        {
            "endpoint": "/drones/{id}/nearby/drones",
            "method": "GET",
            "description": "Get nearby drones",
            "parameters": ["id"]
        },
        {
            "endpoint": "/drones/{id}/nearby/targets",
            "method": "GET",
            "description": "Get nearby targets",
            "parameters": ["id"]
        },
        {
            "endpoint": "/drones/{id}/nearby/obstacles",
            "method": "GET",
            "description": "Get nearby obstacles",
            "parameters": ["id"]
        }
    ]
}

CHECK_API_CATEGORIES = {
    "Drone State": [
        {
            "endpoint": "/check/drone_position",
            "method": "GET",
            "description": "Distance to expected position; result true if within tolerance",
            "parameters": ["drone_id", "x", "y", "z", "tolerance"]
        },
        {
            "endpoint": "/check/drone_altitude",
            "method": "GET",
            "description": "Altitude proximity to expected value",
            "parameters": ["drone_id", "expected_altitude", "tolerance"]
        },
        {
            "endpoint": "/check/drone_status",
            "method": "GET",
            "description": "Drone status equals expected",
            "parameters": ["drone_id", "expected_status"]
        },
        {
            "endpoint": "/check/drone_on_ground",
            "method": "GET",
            "description": "Drone near ground with ground-like status",
            "parameters": ["drone_id", "tolerance"]
        },
        {
            "endpoint": "/check/all_drones_on_ground",
            "method": "GET",
            "description": "Fleet ground-state count within altitude tolerance",
            "parameters": ["tolerance"]
        },
        {
            "endpoint": "/check/drone_hovering",
            "method": "GET",
            "description": "Drone hovering above ground",
            "parameters": ["drone_id", "tolerance"]
        },
        {
            "endpoint": "/check/all_drones_hovering",
            "method": "GET",
            "description": "Fleet hovering count within tolerance",
            "parameters": ["tolerance"]
        },
        {
            "endpoint": "/check/drone_over_height",
            "method": "GET",
            "description": "Altitude above minimum height",
            "parameters": ["drone_id", "min_height", "tolerance"]
        },
        {
            "endpoint": "/check/drone_battery_level",
            "method": "GET",
            "description": "Battery level above minimum",
            "parameters": ["drone_id", "min_level"]
        },
        {
            "endpoint": "/check/drone_heading",
            "method": "GET",
            "description": "Heading within tolerance",
            "parameters": ["drone_id", "expected_heading", "tolerance"]
        },
        {
            "endpoint": "/check/drone_at_home",
            "method": "GET",
            "description": "Drone within tolerance of home position",
            "parameters": ["drone_id", "tolerance"]
        },
        {
            "endpoint": "/check/drone_has_taken_off",
            "method": "GET",
            "description": "Drone has matching takeoff history for a minimum, range, or exact altitude",
            "parameters": ["drone_id", "min_altitude", "max_altitude", "tolerance", "since_timestamp"]
        },
        {
            "endpoint": "/check/drone_has_landed",
            "method": "GET",
            "description": "Drone has landed in history",
            "parameters": ["drone_id", "min_count", "since_timestamp"]
        },
        {
            "endpoint": "/check/drone_has_visited_position",
            "method": "GET",
            "description": "Drone has visited position in history",
            "parameters": ["drone_id", "x", "y", "z", "tolerance", "since_timestamp"]
        },
        {
            "endpoint": "/check/drone_has_moved_distance",
            "method": "GET",
            "description": "Drone moved minimum distance",
            "parameters": ["drone_id", "min_distance", "since_timestamp"]
        },
        {
            "endpoint": "/check/drone_has_moved_directed_distance",
            "method": "GET",
            "description": "Drone moved minimum distance in a direction",
            "parameters": ["drone_id", "min_distance", "heading", "tolerance", "since_timestamp"]
        },
        {
            "endpoint": "/check/drone_has_hovered",
            "method": "GET",
            "description": "Drone has hovered in history",
            "parameters": ["drone_id", "min_duration", "since_timestamp"]
        },
        {
            "endpoint": "/check/drone_has_taken_photo",
            "method": "GET",
            "description": "Drone has taken photos",
            "parameters": ["drone_id", "min_count", "since_timestamp"]
        },
        {
            "endpoint": "/check/drone_has_charged",
            "method": "GET",
            "description": "Drone has charged in history",
            "parameters": ["drone_id", "min_charge_amount", "since_timestamp"]
        },
        {
            "endpoint": "/check/drone_has_sent_message",
            "method": "GET",
            "description": "Drone has sent messages",
            "parameters": ["drone_id", "to_drone_id", "min_count", "since_timestamp"]
        },
        {
            "endpoint": "/check/drone_has_sent_message_content",
            "method": "GET",
            "description": "Drone has sent message containing text",
            "parameters": ["drone_id", "content", "to_drone_id", "min_count", "since_timestamp"]
        },
        {
            "endpoint": "/check/all_drones_have_taken_off",
            "method": "GET",
            "description": "All drones have taken off",
            "parameters": ["min_altitude", "since_timestamp", "check_history"]
        },
        {
            "endpoint": "/check/all_drones_have_landed",
            "method": "GET",
            "description": "All drones have landed",
            "parameters": ["min_count", "since_timestamp", "check_history"]
        }
    ],
    "Distance & Proximity": [
        {
            "endpoint": "/check/target_within_drone_distance",
            "method": "GET",
            "description": "Target within max distance of drone",
            "parameters": ["drone_id", "target_id", "max_distance"]
        },
        {
            "endpoint": "/check/obstacle_within_drone_distance",
            "method": "GET",
            "description": "Obstacle within max distance of drone",
            "parameters": ["drone_id", "obstacle_id", "max_distance"]
        },
        {
            "endpoint": "/check/two_drones_distance",
            "method": "GET",
            "description": "Two drones within max distance",
            "parameters": ["drone_1_id", "drone_2_id", "max_distance", "min_distance"]
        },
        {
            "endpoint": "/check/drone_group_distance",
            "method": "GET",
            "description": "Drone group pairwise distance check",
            "parameters": ["drone_ids", "max_distance", "min_distance", "mode"]
        },
        {
            "endpoint": "/check/drone_in_target",
            "method": "GET",
            "description": "Drone inside target radius",
            "parameters": ["drone_id", "target_id"]
        },
        {
            "endpoint": "/check/target_within_drone_task_radius",
            "method": "GET",
            "description": "Target within drone task radius",
            "parameters": ["drone_id", "target_id"]
        },
        {
            "endpoint": "/check/target_within_drone_perceived_radius",
            "method": "GET",
            "description": "Target within drone perceived radius",
            "parameters": ["drone_id", "target_id"]
        },
        {
            "endpoint": "/check/obstacle_within_drone_perceived_radius",
            "method": "GET",
            "description": "Obstacle within drone perceived radius",
            "parameters": ["drone_id", "obstacle_id"]
        }
    ],
    "Target Reachability": [
        {
            "endpoint": "/check/target_is_reached",
            "method": "GET",
            "description": "Any drone reached target",
            "parameters": ["target_id", "since_timestamp"]
        },
        {
            "endpoint": "/check/target_in_photo_taken_by_drone",
            "method": "GET",
            "description": "Target detected in drone photo",
            "parameters": ["drone_id", "target_id"]
        },
        {
            "endpoint": "/check/target_is_reached_by_drone",
            "method": "GET",
            "description": "Specific drone reached target",
            "parameters": ["target_id", "drone_id", "since_timestamp"]
        },
        {
            "endpoint": "/check/target_reached_drone_number",
            "method": "GET",
            "description": "Number of drones reached target vs expected",
            "parameters": ["target_id", "expected_count", "since_timestamp"]
        },
        {
            "endpoint": "/check/moving_target_tracked",
            "method": "GET",
            "description": "Moving target tracked for minimum duration",
            "parameters": ["target_id", "drone_id", "min_duration", "since_timestamp"]
        },
        {
            "endpoint": "/check/target_is_fully_searched",
            "method": "GET",
            "description": "Target search coverage above threshold",
            "parameters": ["target_id", "coverage_threshold"]
        },
        {
            "endpoint": "/check/target_searched_area_percentage",
            "method": "GET",
            "description": "Target coverage meets expected percentage",
            "parameters": ["target_id", "expected_percentage"]
        }
    ],
    "Task Progress": [
        {
            "endpoint": "/check/task_progress",
            "method": "GET",
            "description": "Task progress meets expected ratio",
            "parameters": ["expected_progress"]
        },
        {
            "endpoint": "/check/task_done",
            "method": "GET",
            "description": "Task completion flag using session progress",
            "parameters": []
        }
    ]
}


def get_all_api_endpoints() -> List[str]:
    """Get a flat list of all API endpoints."""
    endpoints = []
    for category, apis in API_CATEGORIES.items():
        for api in apis:
            endpoint_display = f"{api['method']} {api['endpoint']}"
            endpoints.append(endpoint_display)
    return sorted(endpoints)


def get_api_by_category() -> Dict[str, List[Dict[str, Any]]]:
    """Get APIs organized by category."""
    return API_CATEGORIES


def get_commands() -> List[str]:
    """Get list of available drone commands."""
    return DRONE_COMMANDS


def get_check_api_by_category() -> Dict[str, List[Dict[str, Any]]]:
    """Get execution check APIs organized by category."""
    return CHECK_API_CATEGORIES


def format_api_display(api: Dict[str, Any]) -> str:
    """Format an API for display in the UI."""
    params = ", ".join(api.get("parameters", []))
    params_display = f" ({params})" if params else ""
    return f"{api['method']} {api['endpoint']}{params_display} - {api['description']}"
