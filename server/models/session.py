import time
import copy
from typing import Dict, List, Any, Optional, Mapping
from enum import Enum
from config.util import distance_2d
from config.util import distance as euclidean_distance, generate_random_id


class SessionStatus(str, Enum):
    """Enum representing the possible states of a session"""
    ACTIVE = "active"
    INACTIVE = "inactive"


class TaskType(str, Enum):
    """Enum representing the type of task/mission for the session"""
    AREA_SEARCH = "area_search"                    # Search a defined area for objects/targets
    AREA_ASSIGNMENT_AND_PATROL = "area_assignment_and_patrol"  # Assign areas and patrol routes
    TARGET_ASSIGNMENT = "target_assignment"        # Assign specific targets to drones
    TARGET_TRACKING = "target_tracking"            # Track and follow moving targets
    OTHERS = "others"                              # Other custom mission types


MOVING_TARGET_TRACKING_WINDOW = 10.0
TARGET_REACH_RECENT_LIMIT = 5
TRACKING_PERIOD_RECENT_LIMIT = 5
DEFAULT_REQUEST_HISTORY_LIMIT = 5000


class Session:
    """Model representing a simulation session that contains drones, targets, obstacles, and environment"""

    REQUEST_HISTORY_DEFAULTS = {
        "client_ip": "unknown",
        "client_port": None,
        "client_privilege": None,
        "authentication_status": "unknown",
        "session_id": None,
        "query_params": {},
        "user_agent": None,
        "agent_id": None,
    }

    def __init__(
        self,
        name: str,
        description: str = "",
        session_id: Optional[str] = None,
        task_type: TaskType | str = TaskType.OTHERS,
        task_description: str = "",
        creator: str = "system",
        status: SessionStatus | str = SessionStatus.INACTIVE,
        is_distance_3d: bool = False,
        canvas_width: float = 1024.0,
        canvas_height: float = 768.0,
        created_at: Optional[float] = None,
        last_updated: Optional[float] = None,
        total_commands_executed: int = 0,
        total_flight_time: float = 0.0,
        total_distance_traveled: float = 0.0,
        session_time: float = 0.0,
        drones: Optional[Dict[str, Dict[str, Any]]] = None,
        targets: Optional[Dict[str, Dict[str, Any]]] = None,
        obstacles: Optional[Dict[str, Dict[str, Any]]] = None,
        environment: Optional[Dict[str, Any]] = None,
        tasks: Optional[Dict[str, Dict[str, Any]]] = None,
        command_history: Optional[List[Dict[str, Any]]] = None,
        max_request_history: int = DEFAULT_REQUEST_HISTORY_LIMIT,
        status_history: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        area_coverage: Optional[Dict[str, Dict[str, Any]]] = None,
        target_reaches: Optional[Dict[str, Dict[str, List[float]]]] = None,
        moving_target_tracking: Optional[Dict[str, Dict[str, Any]]] = None,
        path_history: Optional[Dict[str, List[Dict[str, float]]]] = None,
    ):
        self.id = session_id or generate_random_id()
        self.name = name
        self.description = description
        self.creator = creator or "system"
        self.task_type = self._coerce_task(task_type)
        self.task_description = task_description
        self.status = self._coerce_status(status)
        self.is_distance_3d = bool(is_distance_3d)
        self.canvas_width = float(canvas_width) if canvas_width is not None else 1024.0
        self.canvas_height = float(canvas_height) if canvas_height is not None else 768.0

        now = time.time()
        self.created_at = created_at or now
        self.last_updated = last_updated or now

        # Session-specific data collections
        self.drones: Dict[str, Dict[str, Any]] = copy.deepcopy(drones) if drones is not None else {}
        self.targets: Dict[str, Dict[str, Any]] = copy.deepcopy(targets) if targets is not None else {}
        self.obstacles: Dict[str, Dict[str, Any]] = copy.deepcopy(obstacles) if obstacles is not None else {}
        self.environment: Optional[Dict[str, Any]] = copy.deepcopy(environment) if environment is not None else None
        self.tasks: Dict[str, Dict[str, Any]] = copy.deepcopy(tasks) if tasks is not None else {}

        # Session metadata
        self.total_commands_executed = int(total_commands_executed)
        self.total_flight_time = float(total_flight_time)
        self.total_distance_traveled = float(total_distance_traveled)

        # Session timer (increments every second when active)
        self.session_time = float(session_time)
        self.last_timer_update = time.time()

        # Command history: record all commands sent to drones with parameters and results
        self.command_history: List[Dict[str, Any]] = copy.deepcopy(command_history) if command_history else []
        self.max_command_history = 1000  # Limit to last 1000 commands

        # Request history: record HTTP requests associated with this session
        self.max_request_history = self._validate_request_history_limit(
            max_request_history
        )
        self.request_history: List[Dict[str, Any]] = []

        # Drone status history
        self.status_history: Dict[str, List[Dict[str, Any]]] = copy.deepcopy(status_history) if status_history else {}
        self.max_status_history_per_drone = 100  # Limit to last 100 status changes per drone

        # Area coverage tracking
        self.area_coverage: Dict[str, Dict[str, Any]] = copy.deepcopy(area_coverage) if area_coverage else {}

        # Target reach tracking: {drone_id: {target_id: [timestamps]}}
        self.target_reaches: Dict[str, Dict[str, List[float]]] = copy.deepcopy(target_reaches) if target_reaches else {}

        # Moving target tracking state: {target_id: {"last_tracked_at": float, "last_tracked_by": str, "tracked_by": [drone_ids]}}
        self.moving_target_tracking: Dict[str, Dict[str, Any]] = copy.deepcopy(moving_target_tracking) if moving_target_tracking else {}

        # Path history: {drone_id: [position1, position2, ...]}
        # Stores movement history for each drone in the session
        self.path_history: Dict[str, List[Dict[str, float]]] = copy.deepcopy(path_history) if path_history else {}

        # Store initial state for reset
        self._initial_state = {
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "task_description": self.task_description,
        }

    @staticmethod
    def _coerce_status(value: SessionStatus | str) -> SessionStatus:
        if isinstance(value, SessionStatus):
            return value
        try:
            return SessionStatus(str(value))
        except ValueError:
            return SessionStatus.INACTIVE

    @staticmethod
    def _coerce_task(value: TaskType | str) -> TaskType:
        if isinstance(value, TaskType):
            return value
        try:
            return TaskType(str(value))
        except ValueError:
            return TaskType.OTHERS
    
    def update_status(self, status: SessionStatus | str, update_timestamp: bool = True) -> None:
        """Update the session status

        Note: last_updated is only modified if the status actually changes
        and update_timestamp is True. Simply switching between sessions
        (activate/deactivate) can opt out of touching last_updated by
        passing update_timestamp=False.
        """
        old_status = self.status
        new_status = self._coerce_status(status)

        # Only update last_updated if status actually changed
        if old_status != new_status:
            self.status = new_status
            now = time.time()
            if update_timestamp:
                self.last_updated = now
            # Reset timer update timestamp when transitioning to/from active
            # This prevents counting time while inactive
            self.last_timer_update = now
        else:
            # Status didn't change, don't update timestamp
            self.status = new_status

    def update_session_time(self) -> None:
        """Update the session timer based on elapsed time (only when active)"""
        if self.status == SessionStatus.ACTIVE:
            current_time = time.time()
            elapsed = current_time - self.last_timer_update
            self.session_time += elapsed
            self.last_timer_update = current_time
    
    def update_statistics(self) -> None:
        """Update session statistics based on current data

        Note: This method is called when syncing controller data back to the session.
        It does NOT update last_updated because the actual data changes have already
        been tracked and timestamped individually (commands, movements, target reaches, etc.).
        This is just a housekeeping operation.
        """
        # No timestamp update here - data changes are already timestamped when they occur
        pass

    def apply_update(self, updates: Mapping[str, Any]) -> None:
        """Apply partial updates to the session metadata."""
        changed = False

        if "name" in updates:
            self.name = updates["name"]
            changed = True

        if "description" in updates:
            self.description = updates["description"]
            changed = True

        if "creator" in updates:
            self.creator = updates["creator"]
            changed = True

        if "task_description" in updates:
            self.task_description = updates["task_description"]
            changed = True

        if "task_type" in updates:
            new_task = self._coerce_task(updates["task_type"])
            if new_task != self.task_type:
                self.task_type = new_task
                changed = True

        if "is_distance_3d" in updates:
            new_val = bool(updates["is_distance_3d"])
            if new_val != self.is_distance_3d:
                self.is_distance_3d = new_val
                changed = True

        if "canvas_width" in updates:
            val = updates["canvas_width"]
            self.canvas_width = float(val) if val is not None else None
            changed = True

        if "canvas_height" in updates:
            val = updates["canvas_height"]
            self.canvas_height = float(val) if val is not None else None
            changed = True

        if "status" in updates:
            self.update_status(updates["status"])

        if changed:
            self.last_updated = time.time()
    
    def get_drone_count(self) -> int:
        """Get the current number of drones in this session"""
        return len(self.drones)
    
    def get_target_count(self) -> int:
        """Get the current number of targets in this session"""
        return len(self.targets)
    
    def get_obstacle_count(self) -> int:
        """Get the current number of obstacles in this session"""
        return len(self.obstacles)

    def get_task_count(self) -> int:
        """Get the current number of tasks in this session"""
        return len(self.tasks)

    def get_environment_id(self) -> Optional[str]:
        """Get the current environment ID for this session"""
        return self.environment.get("id") if self.environment else None
    
    def add_command_executed(self) -> None:
        """Increment the total commands executed counter"""
        self.total_commands_executed += 1
        self.last_updated = time.time()
    
    def add_flight_time(self, flight_time: float) -> None:
        """Add flight time to the total"""
        self.total_flight_time += flight_time
        self.last_updated = time.time()
    
    def add_distance_traveled(self, distance: float) -> None:
        """Add distance to the total distance traveled"""
        self.total_distance_traveled += distance
        self.last_updated = time.time()

    def record_target_reach(self, drone_id: str, target_id: str, timestamp: Optional[float] = None) -> None:
        """Record that a drone has reached a target

        This method supports multiple visits - each time a drone enters a target's task_radius,
        a new timestamp is appended to the visit list for that drone-target pair.

        Args:
            drone_id: The ID of the drone that reached the target
            target_id: The ID of the target that was reached
            timestamp: The timestamp of when the target was reached (defaults to current time)

        Note:
            Multiple visits to the same target are recorded as separate timestamps in the list.
            Data structure: target_reaches[drone_id][target_id] = [timestamp1, timestamp2, ...]
        """
        if timestamp is None:
            timestamp = time.time()

        # Initialize drone entry if it doesn't exist
        if drone_id not in self.target_reaches:
            self.target_reaches[drone_id] = {}

        # Initialize target entry for this drone if it doesn't exist
        if target_id not in self.target_reaches[drone_id]:
            self.target_reaches[drone_id][target_id] = []

        # Record the visit timestamp
        self.target_reaches[drone_id][target_id].append(timestamp)
        self.last_updated = time.time()

    def record_target_tracking(self, target_id: str, drone_id: str, timestamp: Optional[float] = None,
                               tracking_window: float = MOVING_TARGET_TRACKING_WINDOW) -> None:
        """Record freshness-based tracking state for a moving target."""
        if timestamp is None:
            timestamp = time.time()

        tracking_entry = self.moving_target_tracking.setdefault(target_id, {
            "first_tracked_at": None,
            "last_tracked_at": None,
            "last_tracked_by": None,
            "tracked_by": [],
            "total_track_events": 0,
            "track_periods": [],
            "by_drone": {},
        })
        if tracking_entry["first_tracked_at"] is None:
            tracking_entry["first_tracked_at"] = float(timestamp)
        tracking_entry["last_tracked_at"] = float(timestamp)
        tracking_entry["last_tracked_by"] = drone_id
        tracking_entry["total_track_events"] = int(tracking_entry.get("total_track_events", 0)) + 1

        tracked_by = tracking_entry.setdefault("tracked_by", [])
        if drone_id not in tracked_by:
            tracked_by.append(drone_id)

        track_periods = tracking_entry.setdefault("track_periods", [])
        if not track_periods or float(timestamp) > float(track_periods[-1]["end_at"]):
            track_periods.append({
                "start_at": float(timestamp),
                "end_at": float(timestamp) + tracking_window,
                "last_update_at": float(timestamp),
                "event_count": 1,
                "last_tracked_by": drone_id,
                "tracked_by": [drone_id],
            })
        else:
            current_period = track_periods[-1]
            current_period["end_at"] = max(float(current_period["end_at"]), float(timestamp) + tracking_window)
            current_period["last_update_at"] = float(timestamp)
            current_period["event_count"] = int(current_period.get("event_count", 0)) + 1
            current_period["last_tracked_by"] = drone_id
            period_tracked_by = current_period.setdefault("tracked_by", [])
            if drone_id not in period_tracked_by:
                period_tracked_by.append(drone_id)

        if len(track_periods) > TRACKING_PERIOD_RECENT_LIMIT * 2:
            tracking_entry["track_periods"] = track_periods[-TRACKING_PERIOD_RECENT_LIMIT * 2:]

        by_drone = tracking_entry.setdefault("by_drone", {})
        drone_entry = by_drone.setdefault(drone_id, {
            "first_tracked_at": None,
            "last_tracked_at": None,
            "total_track_events": 0,
            "track_periods": [],
        })
        if drone_entry["first_tracked_at"] is None:
            drone_entry["first_tracked_at"] = float(timestamp)
        drone_entry["last_tracked_at"] = float(timestamp)
        drone_entry["total_track_events"] = int(drone_entry.get("total_track_events", 0)) + 1

        drone_periods = drone_entry.setdefault("track_periods", [])
        if not drone_periods or float(timestamp) > float(drone_periods[-1]["end_at"]):
            drone_periods.append({
                "start_at": float(timestamp),
                "end_at": float(timestamp) + tracking_window,
                "last_update_at": float(timestamp),
                "event_count": 1,
            })
        else:
            current_drone_period = drone_periods[-1]
            current_drone_period["end_at"] = max(float(current_drone_period["end_at"]), float(timestamp) + tracking_window)
            current_drone_period["last_update_at"] = float(timestamp)
            current_drone_period["event_count"] = int(current_drone_period.get("event_count", 0)) + 1

        if len(drone_periods) > TRACKING_PERIOD_RECENT_LIMIT * 2:
            drone_entry["track_periods"] = drone_periods[-TRACKING_PERIOD_RECENT_LIMIT * 2:]

        self.last_updated = time.time()

    def get_target_tracking_info(self, target_id: str, now: Optional[float] = None,
                                 tracking_window: float = MOVING_TARGET_TRACKING_WINDOW) -> Dict[str, Any]:
        now_ts = time.time() if now is None else float(now)
        tracking_entry = self.moving_target_tracking.get(target_id, {})
        last_tracked_at = tracking_entry.get("last_tracked_at")
        status = "never_tracked"
        if last_tracked_at is not None:
            if (now_ts - float(last_tracked_at)) <= tracking_window:
                status = "tracked"
            else:
                status = "stale"

        return {
            "tracking_status": status,
            "first_tracked_at": tracking_entry.get("first_tracked_at"),
            "last_tracked_at": last_tracked_at,
            "tracked_by": list(tracking_entry.get("tracked_by", [])),
            "last_tracked_by": tracking_entry.get("last_tracked_by"),
            "total_track_events": int(tracking_entry.get("total_track_events", 0)),
            "active_period_start": tracking_entry.get("track_periods", [])[-1]["start_at"] if status == "tracked" and tracking_entry.get("track_periods") else None,
            "recent_periods": copy.deepcopy(tracking_entry.get("track_periods", [])[-TRACKING_PERIOD_RECENT_LIMIT:]),
        }

    def get_target_reach_details(self, recent_limit: int = TARGET_REACH_RECENT_LIMIT) -> Dict[str, Any]:
        """Build compact but informative reach details grouped by drone and target."""
        by_drone: Dict[str, Dict[str, Any]] = {}
        by_target: Dict[str, Dict[str, Any]] = {}

        for drone_id, targets_dict in self.target_reaches.items():
            drone_targets: Dict[str, Any] = {}
            for target_id, timestamps in targets_dict.items():
                if not timestamps:
                    continue
                sorted_timestamps = sorted(float(ts) for ts in timestamps)
                drone_targets[target_id] = {
                    "count": len(sorted_timestamps),
                    "first_reached_at": sorted_timestamps[0],
                    "last_reached_at": sorted_timestamps[-1],
                    "recent_reached_at": sorted_timestamps[-recent_limit:],
                }

                target_entry = by_target.setdefault(target_id, {
                    "total_reaches": 0,
                    "first_reached_at": sorted_timestamps[0],
                    "last_reached_at": sorted_timestamps[-1],
                    "reached_by": [],
                    "recent_reached_at": [],
                })
                target_entry["total_reaches"] += len(sorted_timestamps)
                target_entry["first_reached_at"] = min(float(target_entry["first_reached_at"]), sorted_timestamps[0])
                target_entry["last_reached_at"] = max(float(target_entry["last_reached_at"]), sorted_timestamps[-1])
                if drone_id not in target_entry["reached_by"]:
                    target_entry["reached_by"].append(drone_id)
                target_entry["recent_reached_at"].extend(sorted_timestamps[-recent_limit:])

            if drone_targets:
                by_drone[drone_id] = drone_targets

        for target_id, target_entry in by_target.items():
            target_entry["unique_drones"] = len(target_entry["reached_by"])
            target_entry["recent_reached_at"] = sorted(target_entry["recent_reached_at"])[-recent_limit:]

        return {
            "by_drone": by_drone,
            "by_target": by_target,
        }

    def get_moving_target_tracking_details(self, now: Optional[float] = None,
                                           tracking_window: float = MOVING_TARGET_TRACKING_WINDOW,
                                           recent_period_limit: int = TRACKING_PERIOD_RECENT_LIMIT) -> Dict[str, Any]:
        """Build compact tracking details with recent tracking periods."""
        now_ts = time.time() if now is None else float(now)
        result: Dict[str, Any] = {}
        for target_id, tracking_entry in self.moving_target_tracking.items():
            tracking_info = self.get_target_tracking_info(
                target_id,
                now=now_ts,
                tracking_window=tracking_window,
            )
            result[target_id] = {
                "tracking_status": tracking_info["tracking_status"],
                "first_tracked_at": tracking_info["first_tracked_at"],
                "last_tracked_at": tracking_info["last_tracked_at"],
                "last_tracked_by": tracking_info["last_tracked_by"],
                "tracked_by": tracking_info["tracked_by"],
                "total_track_events": tracking_info["total_track_events"],
                "active_period_start": tracking_info["active_period_start"],
                "recent_periods": copy.deepcopy(tracking_entry.get("track_periods", [])[-recent_period_limit:]),
                "by_drone": {
                    drone_id: {
                        "first_tracked_at": drone_entry.get("first_tracked_at"),
                        "last_tracked_at": drone_entry.get("last_tracked_at"),
                        "total_track_events": int(drone_entry.get("total_track_events", 0)),
                        "recent_periods": copy.deepcopy(drone_entry.get("track_periods", [])[-recent_period_limit:]),
                    }
                    for drone_id, drone_entry in tracking_entry.get("by_drone", {}).items()
                },
            }
        return result

    def get_target_tracking_periods(self, target_id: str, drone_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return tracking periods for a target, optionally scoped to a specific drone."""
        tracking_entry = self.moving_target_tracking.get(target_id, {})
        if drone_id is None:
            return copy.deepcopy(tracking_entry.get("track_periods", []))
        drone_entry = tracking_entry.get("by_drone", {}).get(drone_id, {})
        return copy.deepcopy(drone_entry.get("track_periods", []))

    def has_drone_reached_target(self, drone_id: str, target_id: str) -> bool:
        """Check if a specific drone has reached a specific target

        Args:
            drone_id: The ID of the drone to check
            target_id: The ID of the target to check

        Returns:
            True if the drone has reached the target at least once, False otherwise
        """
        return (drone_id in self.target_reaches and
                target_id in self.target_reaches[drone_id] and
                len(self.target_reaches[drone_id][target_id]) > 0)

    def get_target_reach_count(self, drone_id: str, target_id: str) -> int:
        """Get the number of times a drone has reached a specific target

        Args:
            drone_id: The ID of the drone
            target_id: The ID of the target

        Returns:
            Number of times the drone has reached the target
        """
        if self.has_drone_reached_target(drone_id, target_id):
            return len(self.target_reaches[drone_id][target_id])
        return 0

    def get_drone_target_reaches(self, drone_id: str) -> Dict[str, int]:
        """Get all targets reached by a specific drone with visit counts

        Args:
            drone_id: The ID of the drone

        Returns:
            Dictionary mapping target_id to number of visits
        """
        if drone_id not in self.target_reaches:
            return {}
        return {target_id: len(visits) for target_id, visits in self.target_reaches[drone_id].items()}

    def get_target_reach_summary(self) -> Dict[str, Any]:
        """Get a summary of all target reaches in this session

        Returns:
            Dictionary with aggregate statistics about target reaches.
            Detailed per-drone, per-target reach data is available in the target_reaches attribute.
        """
        total_reaches = 0
        drones_with_reaches = 0
        targets_reached = set()

        for drone_id, targets in self.target_reaches.items():
            if targets:
                drones_with_reaches += 1
                for target_id, visits in targets.items():
                    targets_reached.add(target_id)
                    total_reaches += len(visits)

        return {
            "total_reaches": total_reaches,
            "drones_with_reaches": drones_with_reaches,
            "unique_targets_reached": len(targets_reached)
        }

    def add_command_to_history(self, command_id: str, drone_id: str, command: str,
                               parameters: Dict[str, Any], status: str, message: str) -> None:
        """Add a command to the session's command history

        Args:
            command_id: Unique identifier for the command
            drone_id: ID of the drone receiving the command
            command: The command type
            parameters: Command parameters
            status: Command execution status (e.g., "success", "failed")
            message: Result message
        """
        command_record = {
            "command_id": command_id,
            "drone_id": drone_id,
            "command": command,
            "parameters": parameters,
            "status": status,
            "message": message,
            "timestamp": time.time()
        }
        self.command_history.append(command_record)

        # Limit history size
        if len(self.command_history) > self.max_command_history:
            self.command_history = self.command_history[-self.max_command_history:]

        self.last_updated = time.time()

    def add_request_to_history(self, request_record: Dict[str, Any]) -> None:
        """Add an HTTP request record to the session's request history."""
        self.request_history.append(
            self.normalize_request_history_record(request_record)
        )

        if len(self.request_history) > self.max_request_history:
            self.request_history = self.request_history[-self.max_request_history:]

        self.last_updated = time.time()

    @staticmethod
    def _validate_request_history_limit(limit: int) -> int:
        """Validate and normalize the stored request-history retention limit."""
        normalized_limit = int(limit)
        if normalized_limit <= 0:
            raise ValueError("Request history limit must be greater than zero")
        return normalized_limit

    def set_request_history_limit(self, limit: int) -> None:
        """Apply a new retention limit and immediately trim existing history."""
        self.max_request_history = self._validate_request_history_limit(limit)
        if len(self.request_history) > self.max_request_history:
            self.request_history = self.request_history[-self.max_request_history:]

    def normalize_request_history_record(self, request_record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize current and restored request records to the public schema."""
        normalized = copy.deepcopy(request_record)
        for key, default_value in self.REQUEST_HISTORY_DEFAULTS.items():
            normalized.setdefault(key, copy.deepcopy(default_value))
        if normalized["session_id"] is None:
            normalized["session_id"] = self.id
        if not isinstance(normalized["query_params"], dict):
            normalized["query_params"] = {}
        client_privilege = normalized.get("client_privilege")
        if client_privilege is not None:
            normalized["client_privilege"] = str(client_privilege).upper()
        user_agent = normalized.get("user_agent")
        if user_agent is not None:
            normalized["user_agent"] = str(user_agent)[:512]
        return normalized

    def record_drone_status(self, drone_id: str, status: str, position: Dict[str, float],
                           battery_level: float, battery_volume: float) -> None:
        """Record a drone's status change (only when it actually changes)

        Args:
            drone_id: ID of the drone
            status: Current status
            position: Current position {x, y, z}
            battery_level: Current battery level (percentage)
            battery_volume: Current battery volume (mAh)
        """
        # Initialize history for this drone if needed
        if drone_id not in self.status_history:
            self.status_history[drone_id] = []

        # Get last recorded status for comparison
        last_record = self.status_history[drone_id][-1] if self.status_history[drone_id] else None

        # Only record if something changed
        if last_record is None or (
            last_record["status"] != status or
            last_record["position"] != position or
            abs(last_record["battery_level"] - battery_level) > 0.1  # Allow small battery fluctuations
        ):
            status_record = {
                "status": status,
                "position": position.copy(),
                "battery_level": battery_level,
                "battery_volume": battery_volume,
                "timestamp": time.time()
            }
            self.status_history[drone_id].append(status_record)

            # Limit history size per drone
            if len(self.status_history[drone_id]) > self.max_status_history_per_drone:
                self.status_history[drone_id] = self.status_history[drone_id][-self.max_status_history_per_drone:]

            self.last_updated = time.time()

    def add_position_to_path_history(self, drone_id: str, position: Dict[str, float]) -> None:
        """Add a position to a drone's path history

        Args:
            drone_id: ID of the drone
            position: Position dict {x, y, z}
        """
        if drone_id not in self.path_history:
            self.path_history[drone_id] = []
        
        self.path_history[drone_id].append(position.copy())
        self.last_updated = time.time()


    def initialize_area_coverage(self, target_id: str, area_type: str, total_area: float) -> None:
        """Initialize area coverage tracking for a target

        Args:
            target_id: ID of the target
            area_type: Type of area ('circle' or 'polygon')
            total_area: Total area of the target
        """
        self.area_coverage[target_id] = {
            "area_type": area_type,
            "total_area": total_area,
            "covered_area": 0.0,
            "coverage_percentage": 0.0,
            "covered_points": set()  # OPTIMIZED: Use set for O(1) lookup instead of list
        }
        self.last_updated = time.time()

    def update_area_coverage(self, target_id: str, covered_points: List[tuple], grid_cell_area: float) -> None:
        """Update area coverage for a target

        Args:
            target_id: ID of the target
            covered_points: List of (x, y) tuples representing covered grid points (may include duplicates)
            grid_cell_area: Area represented by each grid cell (e.g., 4.0 for 2m x 2m grid)

        Note: The covered_area is calculated as the total number of unique covered points
        multiplied by the grid cell area. This avoids double-counting overlapping coverage.
        """
        if target_id not in self.area_coverage:
            return

        # OPTIMIZED: Since covered_points is now a set, we can use set operations (much faster!)
        # This is O(n) instead of O(n*m) where n=new points, m=existing points
        points_set = self.area_coverage[target_id]["covered_points"]

        # Use set.update() which is highly optimized in Python
        # This automatically handles duplicates
        points_set.update(covered_points)

        # Calculate covered area based on TOTAL unique points (not accumulated deltas)
        # This prevents double-counting when drone flies over same area multiple times
        total_covered_points = len(points_set)
        self.area_coverage[target_id]["covered_area"] = total_covered_points * grid_cell_area

        # Calculate coverage percentage
        total_area = self.area_coverage[target_id]["total_area"]
        if total_area > 0:
            self.area_coverage[target_id]["coverage_percentage"] = min(
                100.0,
                (self.area_coverage[target_id]["covered_area"] / total_area) * 100.0
            )

        self.last_updated = time.time()

    def mark_target_fully_covered(self, target_id: str) -> None:
        """Mark a target as fully covered (100% searched).

        Useful for point-based targets where "reaching" them implies full coverage.
        """
        # Ensure entry exists
        if target_id not in self.area_coverage:
            # Create a dummy entry if it doesn't exist
            self.area_coverage[target_id] = {
                "area_type": "point",
                "total_area": 0.0,
                "covered_area": 0.0,
                "coverage_percentage": 0.0,
                "covered_points": set()
            }
        
        # Set to 100%
        self.area_coverage[target_id]["coverage_percentage"] = 100.0
        self.last_updated = time.time()

    def get_area_coverage_summary(self) -> Dict[str, Any]:
        """Get summary of area coverage for all targets in the session

        Returns:
            Dictionary with aggregate coverage statistics only

        Note: average_coverage is calculated using equal weighting for all targets,
        regardless of their actual area size. Targets not yet visited count as 0%.
        Detailed per-target coverage data is available in the area_coverage attribute.
        """
        # Calculate total number of targets in session
        total_targets = len(self.targets)

        if total_targets == 0:
            return {
                "total_targets_tracked": 0,
                "average_coverage": 0.0,
                "fully_covered_targets": 0
            }

        # Sum coverage percentages for all targets (unvisited = 0%)
        total_coverage = 0.0
        fully_covered = 0

        for target_id in self.targets:
            if target_id in self.area_coverage:
                coverage_pct = self.area_coverage[target_id]["coverage_percentage"]
                total_coverage += coverage_pct
                if coverage_pct >= 99.9:
                    fully_covered += 1

        # Equal-weighted average: sum of all coverage percentages divided by total targets
        average_coverage = total_coverage / total_targets if total_targets > 0 else 0.0

        return {
            "total_targets_tracked": len(self.area_coverage),  # Number of targets with some coverage
            "average_coverage": average_coverage,
            "fully_covered_targets": fully_covered
        }

    def get_task_progress(self) -> Dict[str, Any]:
        """Calculate task progress based on task type

        Returns:
            Dictionary with task progress information including:
            - task_type: The type of task
            - progress_percentage: Progress as a percentage (0-100)
            - is_completed: Whether the task is completed
            - status_message: Human-readable status
            - details: Task-specific details (not duplicated in summaries)

        Note: This method returns only the core progress info. The to_dict() method
        adds target_reach_summary and area_coverage_summary as nested fields.
        """

        task_type = self.task_type.value if hasattr(self.task_type, 'value') else self.task_type

        # For 'others' task type, no progress tracking
        if task_type == "others":
            return {
                "task_type": task_type,
                "progress_percentage": 0,
                "is_completed": False,
                "status_message": "No progress tracking for this task type",
                "details": {}
            }

        # For area_search and area_assignment_and_patrol tasks
        if task_type in ["area_search", "area_assignment_and_patrol"]:
            # Denominator should be the total number of targets for the task
            # Exclude waypoint targets (charging stations) from task progress calculation
            task_target_ids = [tid for tid, tdata in self.targets.items()
                             if tdata.get("type") != "waypoint"]
            total_task_targets = len(task_target_ids)

            if total_task_targets == 0:
                return {
                    "task_type": task_type,
                    "progress_percentage": 100,
                    "is_completed": True,  # No targets, so task is vacuously complete
                    "status_message": "Task Finished",
                    "details": {"total_targets": 0}
                }

            # Sum the coverage percentages of all non-waypoint targets. Unvisited targets count as 0%.
            # This uses EQUAL WEIGHTING for each target regardless of actual area size.
            # Example: 4 targets with coverage [40%, 50%, 60%, 0%] → (40+50+60+0)/4 = 37.5%
            total_percentage_sum = 0.0
            for target_id in task_target_ids:
                if target_id in self.area_coverage:
                    total_percentage_sum += self.area_coverage[target_id].get("coverage_percentage", 0.0)
                # Targets not in area_coverage contribute 0% (already handled by initialization)

            # The overall progress is the equal-weighted average of all target percentages
            average_coverage = total_percentage_sum / total_task_targets

            progress = int(average_coverage)

            # Completion requires all individual non-waypoint targets to be at least 90% covered
            all_covered = True
            # If there are targets but none have been visited yet, the task is not complete.
            if not self.area_coverage and task_target_ids:
                all_covered = False
            else:
                for target_id in task_target_ids:
                    # If a target is not in the coverage dict or its coverage is < 90%, it's not done.
                    if target_id not in self.area_coverage or self.area_coverage[target_id].get("coverage_percentage", 0) < 90.0:
                        all_covered = False
                        break
            
            is_completed = all_covered

            return {
                "task_type": task_type,
                "progress_percentage": progress,
                "is_completed": is_completed,
                "status_message": "Task Finished" if is_completed else "Task to be Done",
                "details": {
                    "total_targets": total_task_targets
                }
            }

        # For target_assignment task
        elif task_type == "target_assignment":
            # Calculate percentage of targets that have been visited at least once
            # Exclude waypoint targets (charging stations) from task progress calculation
            task_target_ids = [tid for tid, tdata in self.targets.items()
                             if tdata.get("type") != "waypoint"]
            total_targets = len(task_target_ids)

            if total_targets == 0:
                return {
                    "task_type": task_type,
                    "progress_percentage": 0,
                    "is_completed": False,
                    "status_message": "Task to be Done",
                    "details": {
                        "total_targets": 0,
                        "visited_targets": 0
                    }
                }

            # Collect all unique non-waypoint targets that have been visited
            visited_targets = set()
            for drone_id, targets_dict in self.target_reaches.items():
                for target_id in targets_dict.keys():
                    # Only count non-waypoint targets
                    if target_id in task_target_ids:
                        visited_targets.add(target_id)

            visited_count = len(visited_targets)
            progress = int((visited_count / total_targets) * 100) if total_targets > 0 else 0
            is_completed = visited_count >= total_targets

            return {
                "task_type": task_type,
                "progress_percentage": progress,
                "is_completed": is_completed,
                "status_message": "Task Finished" if is_completed else "Task to be Done",
                "details": {
                    "total_targets": total_targets,
                    "visited_targets": visited_count,
                    "unvisited_targets": total_targets - visited_count
                }
            }

        # For target_tracking task
        elif task_type == "target_tracking":
            # Calculate percentage of targets currently within task_radius of any drone
            # Exclude waypoint targets (charging stations) from task progress calculation
            task_target_ids = [tid for tid, tdata in self.targets.items()
                             if tdata.get("type") != "waypoint"]
            total_targets = len(task_target_ids)

            if total_targets == 0 or len(self.drones) == 0:
                return {
                    "task_type": task_type,
                    "progress_percentage": 0,
                    "is_completed": False,
                    "status_message": "Task to be Done",
                    "details": {
                        "total_targets": total_targets,
                        "currently_tracked": 0,
                        "ever_tracked": 0
                    }
                }

            currently_tracked = set()
            for target_id in task_target_ids:
                target_data = self.targets[target_id]
                if target_data.get("type") == "moving":
                    tracking_info = self.get_target_tracking_info(target_id)
                    if tracking_info["tracking_status"] == "tracked":
                        currently_tracked.add(target_id)
                    continue

                for drone_data in self.drones.values():
                    drone_pos = drone_data["position"]
                    task_radius = drone_data.get("task_radius", 10.0)
                    distance = self._calculate_target_distance(
                        target_data,
                        drone_pos,
                        is_distance_3d=self.is_distance_3d,
                    )
                    if distance <= task_radius:
                        currently_tracked.add(target_id)
                        break

            # Also track which non-waypoint targets have ever been tracked (from target_reaches)
            ever_tracked = set()
            for drone_id, targets_dict in self.target_reaches.items():
                for target_id in targets_dict.keys():
                    # Only count non-waypoint targets
                    if target_id in task_target_ids:
                        ever_tracked.add(target_id)

            # Progress based on currently tracked targets
            currently_tracked_count = len(currently_tracked)
            progress = int((currently_tracked_count / total_targets) * 100) if total_targets > 0 else 0

            # Task is completed if all targets have been tracked at least once
            is_completed = len(ever_tracked) >= total_targets

            return {
                "task_type": task_type,
                "progress_percentage": progress,
                "is_completed": is_completed,
                "status_message": "Task Finished" if is_completed else "Task to be Done",
                "details": {
                    "total_targets": total_targets,
                    "currently_tracked": currently_tracked_count,
                    "ever_tracked": len(ever_tracked),
                    "currently_tracked_ids": list(currently_tracked),
                    "ever_tracked_ids": list(ever_tracked)
                }
            }

        # Fallback for unknown task types
        return {
            "task_type": task_type,
            "progress_percentage": 0,
            "is_completed": False,
            "status_message": "Unknown task type",
            "details": {}
        }

    def to_dict(self, data: bool = True) -> Dict[str, Any]:
        """Convert the session to a dictionary representation.

        Args:
            data: When True, include full entity and history payloads in the result.

        Returns:
            Dictionary with session data. The statistics.task_progress field contains:
            - Core progress info (type, percentage, completion, status, details)
            - target_reach_summary: Aggregate target reach statistics
            - area_coverage_summary: Aggregate coverage statistics

            Detailed data (target_reaches, area_coverage) is at root level to avoid duplication.
        """
        target_reach_summary = self.get_target_reach_summary()
        area_coverage_summary = self.get_area_coverage_summary()
        task_progress = self.get_task_progress()

        # Nest summaries under task_progress for logical grouping
        # These provide aggregate statistics without duplicating detailed data
        task_progress["target_reach_summary"] = target_reach_summary
        task_progress["area_coverage_summary"] = area_coverage_summary

        now_ts = time.time()
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "creator": self.creator,
            "task_type": self.task_type.value,
            "task_description": self.task_description,
            "is_distance_3d": self.is_distance_3d,
            "canvas_width": self.canvas_width,
            "canvas_height": self.canvas_height,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "statistics": {
                "drone_count": self.get_drone_count(),
                "target_count": self.get_target_count(),
                "obstacle_count": self.get_obstacle_count(),
                "task_count": self.get_task_count(),
                "environment_id": self.get_environment_id(),
                "total_commands_executed": self.total_commands_executed,
                "total_flight_time": self.total_flight_time,
                "total_distance_traveled": self.total_distance_traveled,
                "total_target_reaches": target_reach_summary["total_reaches"],
                "drones_with_target_reaches": target_reach_summary["drones_with_reaches"],
                "unique_targets_reached": target_reach_summary["unique_targets_reached"],
                "session_time": self.session_time,
                "command_history_size": len(self.command_history),
                "task_progress": task_progress
            }
        }

        if not data:
            return result

        # Include complete session data when requested
        result["drones"] = list(self.drones.values())
        result["targets"] = [self._enrich_target_snapshot(target, now_ts) for target in self.targets.values()]
        result["obstacles"] = list(self.obstacles.values())
        result["environment"] = self.environment
        result["tasks"] = list(self.tasks.values())
        # Convert sets to lists for JSON serialization
        area_coverage_serializable = {}
        for target_id, coverage_data in self.area_coverage.items():
            coverage_copy = coverage_data.copy()
            coverage_copy["covered_points"] = sorted(
                coverage_data["covered_points"],
                key=lambda point: (point[0], point[1]),
            )
            area_coverage_serializable[target_id] = coverage_copy
        
        # New history object
        history = {
            "command_history": self.command_history,
            "status_history": self.status_history,
            "path_history": copy.deepcopy(self.path_history),
            "target_reaches": self.get_target_reach_details(),
            "moving_target_tracking": self.get_moving_target_tracking_details(now=now_ts),
            "area_coverage": area_coverage_serializable
        }
        result["history"] = history

        return result
    
    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
        max_request_history: int = DEFAULT_REQUEST_HISTORY_LIMIT,
    ) -> 'Session':
        """Create a Session instance from the flat dictionary payload used by the API."""
        if "name" not in data:
            raise ValueError("Missing required field: name")

        stats = data.get("statistics") or {}
        history_data = data.get("history") or {}

        task_value = data.get("task_type", TaskType.OTHERS)

        creator_value = data.get("creator") or "system"

        session = cls(
            name=data["name"],
            description=data.get("description", ""),
            session_id=data.get("id"),
            task_type=task_value,
            task_description=data.get("task_description", ""),
            creator=creator_value,
            status=data.get("status", SessionStatus.INACTIVE),
            is_distance_3d=data.get("is_distance_3d", False),
            canvas_width=data.get("canvas_width"),
            canvas_height=data.get("canvas_height"),
            created_at=data.get("created_at"),
            last_updated=data.get("last_updated"),
            total_commands_executed=stats.get("total_commands_executed", data.get("total_commands_executed", 0)),
            total_flight_time=stats.get("total_flight_time", data.get("total_flight_time", 0.0)),
            total_distance_traveled=stats.get("total_distance_traveled", data.get("total_distance_traveled", 0.0)),
            session_time=stats.get("session_time", data.get("session_time", 0.0)),
            command_history=history_data.get("command_history"),
            max_request_history=max_request_history,
            status_history=history_data.get("status_history"),
            area_coverage=history_data.get("area_coverage"),
            target_reaches=cls._deserialize_target_reaches(history_data.get("target_reaches")),
            moving_target_tracking=cls._deserialize_moving_target_tracking(history_data.get("moving_target_tracking")),
            path_history=history_data.get("path_history"),
        )

        # Populate entity collections if provided in the data
        drones_list = data.get("drones", [])
        for drone in drones_list:
            drone_copy = copy.deepcopy(drone)
            drone_id = drone_copy.get("id") or generate_random_id()
            drone_copy["id"] = drone_id
            session.drones[drone_id] = drone_copy

        targets_list = data.get("targets", [])
        for target in targets_list:
            target_copy = copy.deepcopy(target)
            target_id = target_copy.get("id") or generate_random_id()
            target_copy["id"] = target_id
            session.targets[target_id] = target_copy

        obstacles_list = data.get("obstacles", [])
        for obstacle in obstacles_list:
            obstacle_copy = copy.deepcopy(obstacle)
            obstacle_id = obstacle_copy.get("id") or generate_random_id()
            obstacle_copy["id"] = obstacle_id
            session.obstacles[obstacle_id] = obstacle_copy

        tasks_list = data.get("tasks", [])
        for task in tasks_list:
            task_copy = copy.deepcopy(task)
            task_id = task_copy.get("id") or generate_random_id()
            task_copy["id"] = task_id
            # Ensure creator is populated to satisfy response schema
            task_copy["creator"] = task_copy.get("creator") or creator_value
            session.tasks[task_id] = task_copy

        session.environment = copy.deepcopy(data.get("environment"))
        
        # Populate session history collections if provided in the history_data
        session.command_history = copy.deepcopy(history_data.get("command_history", []))
        session.status_history = copy.deepcopy(history_data.get("status_history", {}))

        # Convert covered_points from lists to sets for performance if provided in area_coverage history
        area_coverage_data = copy.deepcopy(history_data.get("area_coverage", {}))
        for target_id, coverage_data in area_coverage_data.items():
            if "covered_points" in coverage_data and isinstance(coverage_data["covered_points"], list):
                coverage_data["covered_points"] = set(tuple(p) if isinstance(p, list) else p for p in coverage_data["covered_points"])
        session.area_coverage = area_coverage_data

        session.target_reaches = cls._deserialize_target_reaches(history_data.get("target_reaches", {}))
        session.moving_target_tracking = cls._deserialize_moving_target_tracking(history_data.get("moving_target_tracking", {}))
        session.path_history = copy.deepcopy(history_data.get("path_history", {}))

        return session

    def reset(self) -> None:
        """Reset the session to its initial state

        Clears all statistics, timer, and task progress data.
        Preserves the session ID, name, description, and task type.

        Task progress data cleared:
        - area_coverage: Area coverage tracking for area search tasks
        - target_reaches: Target visit tracking for all task types
        """
        # Clear all data collections
        # self.drones = {}
        # self.targets = {}
        # self.obstacles = {}
        # self.environment = None
        # self.tasks = {}

        # Reset statistics
        self.total_commands_executed = 0
        self.total_flight_time = 0.0
        self.total_distance_traveled = 0.0

        # Reset timer
        self.session_time = 0.0
        self.last_timer_update = time.time()

        # Clear tracking data
        self.target_reaches = {}
        self.moving_target_tracking = {}
        self.command_history = []
        self.request_history = []
        self.status_history = {}
        self.area_coverage = {}
        self.path_history = {}

        # Update timestamps
        self.last_updated = time.time()

    @staticmethod
    def _calculate_target_distance(target_data: Dict[str, Any], position: Dict[str, float], is_distance_3d: bool = False) -> float:
        from models.target import Target

        return Target.from_dict(target_data).distance_to_position(
            position,
            is_distance_3d=is_distance_3d,
        )

    def _enrich_target_snapshot(self, target_data: Dict[str, Any], now_ts: Optional[float] = None) -> Dict[str, Any]:
        target_copy = copy.deepcopy(target_data)
        target_id = target_copy.get("id")
        reached_by = []
        for drone_id, targets_dict in self.target_reaches.items():
            if target_id in targets_dict and targets_dict[target_id]:
                reached_by.append(drone_id)

        target_copy["is_reached"] = bool(reached_by)
        target_copy["reached_by"] = reached_by

        if target_copy.get("type") == "moving" and target_id:
            tracking_info = self.get_target_tracking_info(target_id, now=now_ts)
            target_copy["tracking_status"] = tracking_info["tracking_status"]
            target_copy["last_tracked_at"] = tracking_info["last_tracked_at"]
        else:
            target_copy.setdefault("tracking_status", None)
            target_copy.setdefault("last_tracked_at", None)

        return target_copy

    @staticmethod
    def _deserialize_target_reaches(data: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, List[float]]]:
        if not data or not isinstance(data, dict):
            return {}

        if "by_drone" in data and isinstance(data.get("by_drone"), dict):
            restored: Dict[str, Dict[str, List[float]]] = {}
            for drone_id, targets_dict in data["by_drone"].items():
                if not isinstance(targets_dict, dict):
                    continue
                restored[drone_id] = {}
                for target_id, summary in targets_dict.items():
                    if isinstance(summary, dict):
                        recent = summary.get("recent_reached_at", [])
                        if isinstance(recent, list):
                            restored[drone_id][target_id] = [float(ts) for ts in recent]
            return restored

        restored: Dict[str, Dict[str, List[float]]] = {}
        for drone_id, targets_dict in data.items():
            if not isinstance(targets_dict, dict):
                continue
            restored[drone_id] = {}
            for target_id, timestamps in targets_dict.items():
                if isinstance(timestamps, list):
                    restored[drone_id][target_id] = [float(ts) for ts in timestamps]
        return restored

    @staticmethod
    def _deserialize_moving_target_tracking(data: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        if not data or not isinstance(data, dict):
            return {}

        restored: Dict[str, Dict[str, Any]] = {}
        for target_id, tracking_entry in data.items():
            if not isinstance(tracking_entry, dict):
                continue
            recent_periods = tracking_entry.get("recent_periods") or tracking_entry.get("track_periods") or []
            normalized_periods = []
            for period in recent_periods:
                if not isinstance(period, dict):
                    continue
                normalized_periods.append({
                    "start_at": float(period.get("start_at", 0.0)),
                    "end_at": float(period.get("end_at", 0.0)),
                    "last_update_at": float(period.get("last_update_at", period.get("end_at", 0.0))),
                    "event_count": int(period.get("event_count", 0)),
                    "last_tracked_by": period.get("last_tracked_by"),
                    "tracked_by": list(period.get("tracked_by", [])),
                })

            restored[target_id] = {
                "first_tracked_at": tracking_entry.get("first_tracked_at"),
                "last_tracked_at": tracking_entry.get("last_tracked_at"),
                "last_tracked_by": tracking_entry.get("last_tracked_by"),
                "tracked_by": list(tracking_entry.get("tracked_by", [])),
                "total_track_events": int(tracking_entry.get("total_track_events", 0)),
                "track_periods": normalized_periods,
                "by_drone": {},
            }

            by_drone_data = tracking_entry.get("by_drone", {})
            if isinstance(by_drone_data, dict):
                for drone_id, drone_entry in by_drone_data.items():
                    if not isinstance(drone_entry, dict):
                        continue
                    drone_periods = []
                    for period in drone_entry.get("recent_periods", drone_entry.get("track_periods", [])):
                        if not isinstance(period, dict):
                            continue
                        drone_periods.append({
                            "start_at": float(period.get("start_at", 0.0)),
                            "end_at": float(period.get("end_at", 0.0)),
                            "last_update_at": float(period.get("last_update_at", period.get("end_at", 0.0))),
                            "event_count": int(period.get("event_count", 0)),
                        })
                    restored[target_id]["by_drone"][drone_id] = {
                        "first_tracked_at": drone_entry.get("first_tracked_at"),
                        "last_tracked_at": drone_entry.get("last_tracked_at"),
                        "total_track_events": int(drone_entry.get("total_track_events", 0)),
                        "track_periods": drone_periods,
                    }
        return restored
