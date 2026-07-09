from typing import Dict, List, Any, Optional
import time
import json
import os
from pathlib import Path

from ui.screenshot import generate_session_screenshot as _render_session_screenshot

from models.session import (
    DEFAULT_REQUEST_HISTORY_LIMIT,
    Session,
    SessionStatus,
)
from models.target import TargetType
from models.obstacle import ObstacleType
from models.environment import WeatherCondition, WindDirection
from models.task import Task

class SessionController:
    """Controller class for managing simulation sessions"""
    
    def __init__(
        self,
        drone_controller=None,
        target_controller=None,
        obstacle_controller=None,
        environment_controller=None,
        request_history_limit: int = DEFAULT_REQUEST_HISTORY_LIMIT,
    ):
        self.sessions: Dict[str, Session] = {}
        self.current_session_id: Optional[str] = None
        self.request_history_limit = Session._validate_request_history_limit(
            request_history_limit
        )
        
        # References to other controllers
        self.drone_controller = drone_controller
        self.target_controller = target_controller
        self.obstacle_controller = obstacle_controller
        self.environment_controller = environment_controller
    
    def add_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new session to the system

        Args:
            session_data: Dictionary containing session data with keys:
                - name: Session name (required)
                - description: Session description (optional, default: "")
                - with_examples: Whether to create example data (optional, default: True)
                - task_type: Task type for the session (optional, default: "others")
                - task_description: Detailed task description (optional, default: "")
                - creator: User role who created the session (optional, default: "unknown")
                - id: Optional ID to preserve when restoring from backup

        Returns:
            Dict representation of the created session
        """
        # Extract with_examples flag (not part of Session model)
        with_examples = session_data.get("with_examples", False)

        # Create session data dict for Session.from_dict (exclude with_examples)
        session_model_data = {
            "name": session_data["name"],
            "description": session_data.get("description", ""),
            "task_type": session_data.get("task_type", "others"),
            "task_description": session_data.get("task_description", ""),
            "creator": session_data.get("creator", "unknown"),
        }
        
        # Add optional canvas dimensions
        if "canvas_width" in session_data:
            session_model_data["canvas_width"] = session_data["canvas_width"]
        if "canvas_height" in session_data:
            session_model_data["canvas_height"] = session_data["canvas_height"]

        # Include optional ID if provided
        if "id" in session_data:
            session_model_data["id"] = session_data["id"]

        session = self.create_session_from_dict(session_model_data)
        
        # Store the session
        self.sessions[session.id] = session

        # Check if there's already an active session
        has_active_session = any(sess.status == SessionStatus.ACTIVE for sess in self.sessions.values() if sess.id != session.id)

        if has_active_session:
            # Keep new session inactive if there's already an active session
            session.update_status(SessionStatus.INACTIVE)

            # Create example data for the session even if it's not active
            # The data will be stored in the session object and loaded when it becomes active
            if with_examples:
                # Temporarily store controller states
                old_drones = dict(self.drone_controller.drones) if self.drone_controller else {}
                old_targets = dict(self.target_controller.targets) if self.target_controller else {}
                old_obstacles = dict(self.obstacle_controller.obstacles) if self.obstacle_controller else {}
                old_envs = dict(self.environment_controller.environments) if self.environment_controller else {}
                old_current_env = self.environment_controller.current_environment_id if self.environment_controller else None

                # Clear controllers temporarily
                self._clear_all_data()

                # Create example data
                self._create_example_data_for_session(session)

                # Save the created data to the session
                self._save_current_data_to_session(session.id)

                # Restore original controller states
                if self.drone_controller:
                    self.drone_controller.drones = old_drones
                if self.target_controller:
                    self.target_controller.targets = old_targets
                if self.obstacle_controller:
                    self.obstacle_controller.obstacles = old_obstacles
                if self.environment_controller:
                    self.environment_controller.environments = old_envs
                    self.environment_controller.current_environment_id = old_current_env
        else:
            # Set as current session and activate it only if no other session is active
            self.current_session_id = session.id
            session.update_status(SessionStatus.ACTIVE)
            self._discard_non_current_request_history()

            # Clear existing data from controllers and load session data
            self._clear_all_data()

            # Add example data if requested
            if with_examples:
                self._create_example_data_for_session(session)

            # Load session data into controllers
            self._load_session_data_to_controllers(session)

        return session.to_dict()

    def create_session_from_dict(self, session_data: Dict[str, Any]) -> Session:
        """Create a session using this controller's request-history retention."""
        return Session.from_dict(
            session_data,
            max_request_history=self.request_history_limit,
        )

    def set_request_history_limit(self, limit: int) -> None:
        """Apply request-history retention to current and future sessions."""
        normalized_limit = Session._validate_request_history_limit(limit)
        self.request_history_limit = normalized_limit
        for session in self.sessions.values():
            session.set_request_history_limit(normalized_limit)

    def add_request_to_history(
        self,
        session_id: str,
        request_record: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Add a request record only for the current active session."""
        if session_id != self.current_session_id:
            return None

        session = self.sessions.get(session_id)
        if session is None:
            return None

        return session.add_request_to_history(request_record)

    def clear_request_history(self, session_id: str) -> Optional[int]:
        """Clear runtime request history for one session."""
        session = self.sessions.get(session_id)
        if session is None:
            return None

        cleared_count = len(session.request_history)
        session.request_history = []
        session.last_updated = time.time()
        return cleared_count

    def _discard_non_current_request_history(self) -> None:
        """Discard request history for every non-current session."""
        for session_id, session in self.sessions.items():
            if session_id != self.current_session_id and session.request_history:
                session.request_history = []
                session.last_updated = time.time()
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all sessions"""
        return [session.to_dict() for session in self.sessions.values()]
    
    def get_session(self, session_id: str, data: bool = True) -> Optional[Dict[str, Any]]:
        """Get a specific session by ID

        Args:
            session_id: The ID of the session to retrieve
            data: If True, returns complete session data including all entities.
                  If False, returns session metadata only. Default is True.

        Returns:
            Session dict with complete data or metadata only, or None if not found
        """
        if session_id in self.sessions:
            return self.sessions[session_id].to_dict(data=data)
        return None
    
    def get_current_session(self, data: bool = False) -> Optional[Dict[str, Any]]:
        """Get the current active session
        
        Args:
            data: If True, returns complete session data including all entities.
                  If False, returns session metadata only. Default is False.
        """
        if self.current_session_id:
            session = self.sessions.get(self.current_session_id)
            if session:
                return session.to_dict(data=data)
        return None

    def get_session_ref(self, session_id: str) -> Optional[Session]:
        """Get a direct session object reference without syncing or serialization."""
        return self.sessions.get(session_id)

    def get_current_session_ref(self) -> Optional[Session]:
        """Get the current session object reference without syncing or serialization."""
        if not self.current_session_id:
            return None
        return self.sessions.get(self.current_session_id)

    def sync_session_snapshot(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Sync controller state into a session snapshot and return the serialized session."""
        target_session_id = session_id or self.current_session_id
        if not target_session_id or target_session_id not in self.sessions:
            return None

        session = self.sessions[target_session_id]
        if target_session_id == self.current_session_id:
            session.update_session_time()
        self._save_current_data_to_session(target_session_id)
        return session.to_dict(data=True)

    def sync_session_state(self, session_id: Optional[str] = None) -> Optional[Session]:
        """Sync controller state into a session without serializing full history data."""
        target_session_id = session_id or self.current_session_id
        if not target_session_id or target_session_id not in self.sessions:
            return None

        session = self.sessions[target_session_id]
        if target_session_id == self.current_session_id:
            session.update_session_time()
        self._save_current_data_to_session(target_session_id)
        return session

    def sync_current_session_snapshot(self) -> Optional[Dict[str, Any]]:
        """Sync and return the current active session snapshot."""
        return self.sync_session_snapshot(self.current_session_id)

    def sync_current_session_state(self) -> Optional[Session]:
        """Sync and return the current active session object without serialization."""
        return self.sync_session_state(self.current_session_id)
    
    def set_current_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Set the current active session and load its data into controllers"""
        if session_id not in self.sessions:
            return None
        
        # Save current data to the previously active session
        if self.current_session_id and self.current_session_id in self.sessions:
            self._save_current_data_to_session(self.current_session_id)

        # Deactivate all other sessions to ensure only one is active
        for sid, sess in self.sessions.items():
            if sid != session_id:
                sess.update_status(SessionStatus.INACTIVE, update_timestamp=False)
        
        # Set new current session and activate it
        self.current_session_id = session_id
        session = self.sessions[session_id]
        session.update_status(SessionStatus.ACTIVE, update_timestamp=False)
        self._discard_non_current_request_history()

        # Load session data into global controllers
        self._load_session_data_to_controllers(session)

        # Return full session data including area_coverage for UI restoration
        return self.sync_current_session_snapshot()
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a session's properties

        Note: If updating the status of the current session to INACTIVE,
        the current_session_id reference will NOT be cleared.
        Use set_current_session() or delete_session() to properly change sessions.
        """
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]

        # Apply updates to the session
        session.apply_update(updates)

        # Sync 3D distance setting to drone controller if this is the active session
        if session_id == self.current_session_id and "is_distance_3d" in updates:
            if self.drone_controller and hasattr(self.drone_controller, "set_is_3d"):
                self.drone_controller.set_is_3d(getattr(session, "is_distance_3d", False))

        # If this is the current session and status changed to INACTIVE, warn
        if session_id == self.current_session_id:
            if "status" in updates and updates["status"] == SessionStatus.INACTIVE:
                # Current session was set to inactive via update
                # Note: We keep current_session_id pointing to it for now
                # User should call set_current_session() to switch to another session
                pass

        return session.to_dict()
    
    def reset_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Reset a session to its initial state

        Clears all drones, targets, obstacles, environment, and statistics.
        If the session is the current active session, also clears all controllers.

        Args:
            session_id: The ID of the session to reset

        Returns:
            The reset session dict, or None if session not found
        """
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]

        # Reset the session model
        session.reset()

        return session.to_dict()

    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            # If deleting the current session, clear current session
            if session_id == self.current_session_id:
                self.current_session_id = None
                self._clear_all_data()
            
            del self.sessions[session_id]
            return True
        return False
    
    
    def create_example_session(self) -> Dict[str, Any]:
        """Create a session with example data from JSON files

        This creates a session with task type 'others' which loads from Example_Session.json.
        The example data includes drones, targets, obstacles, and environment configuration.
        """
        return self.add_session({
            "name": "Example Session",
            "description": "A comprehensive example session with drones, targets, obstacles, and environment setup for testing and demonstration purposes.",
            "with_examples": True,
            "task_type": "others",
            "task_description": "General purpose example session for testing and demonstration"
        })
    
    def _clear_all_data(self) -> None:
        """Clear all data from controllers"""
        if self.drone_controller:
            self.drone_controller.drones.clear()

        if self.target_controller:
            self.target_controller.targets.clear()

        if self.obstacle_controller:
            self.obstacle_controller.obstacles.clear()

        if self.environment_controller:
            self.environment_controller.environments.clear()
            self.environment_controller.current_environment_id = None

    def _load_example_json_for_task(self, task_type: str) -> Optional[Dict[str, Any]]:
        """Load example JSON file based on task type

        Args:
            task_type: The task type (area_search, target_tracking, etc.)

        Returns:
            Dictionary with session data from JSON file, or None if file not found
        """
        # Map task types to JSON filenames
        task_to_file = {
            "area_search": "Example_Session_Area_Search.json",
            "area_assignment_and_patrol": "Example_Session_Area_Assignment_and_Patrol.json",
            "target_assignment": "Example_Session_Target_Assignment.json",
            "target_tracking": "Example_Session_Target_Tracking.json",
            "others": "Example_Session.json"
        }

        filename = task_to_file.get(task_type, "Example_Session.json")

        # Construct path to config/example/ directory
        # Assuming the script is running from project root
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "example")
        file_path = os.path.join(config_dir, filename)

        # Try to load the JSON file
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return data
        except FileNotFoundError:
            print(f"Warning: Example JSON file not found: {file_path}")
            return None
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse JSON file {file_path}: {e}")
            return None

    def _create_example_data_from_json(self, session: Session, json_data: Dict[str, Any]) -> None:
        """Create example data for session from loaded JSON

        Args:
            session: The session object to populate
            json_data: The loaded JSON data containing drones, targets, obstacles, environment
        """
        # Generate new IDs and timestamps for the session
        current_time = time.time()

        # Load environment
        if "environment" in json_data and self.environment_controller:
            env_data = json_data["environment"].copy()
            # Ensure weather and wind_direction are enum instances
            if "weather" in env_data and not isinstance(env_data["weather"], WeatherCondition):
                env_data["weather"] = WeatherCondition(env_data.get("weather", "clear"))
            if "wind_direction" in env_data and not isinstance(env_data["wind_direction"], WindDirection):
                env_data["wind_direction"] = WindDirection(env_data.get("wind_direction", "north"))

            # Set defaults for missing fields
            env_data.setdefault("name", "Example Environment")
            env_data.setdefault("temperature", 20.0)
            env_data.setdefault("humidity", 50.0)
            env_data.setdefault("pressure", 1013.25)
            env_data.setdefault("wind_speed", 0.0)
            env_data.setdefault("visibility", 10000.0)

            env = self.environment_controller.add_environment(env_data)
            self.environment_controller.set_current_environment(env["id"])
            session.environment = env

        # Load drones
        if "drones" in json_data and self.drone_controller:
            for drone_data_src in json_data["drones"]:
                drone_data = drone_data_src.copy()
                # Set defaults for missing fields
                drone_data.setdefault("name", "Drone")
                drone_data.setdefault("model", "Generic")
                drone_data.setdefault("max_speed", 15.0)
                drone_data.setdefault("max_altitude", 100.0)
                drone_data.setdefault("battery_capacity", 100.0)
                drone_data.setdefault("position", {"x": 0.0, "y": 0.0, "z": 0.0})
                drone_data.setdefault("heading", 0.0)
                drone_data.setdefault("speed", 0.0)
                drone_data.setdefault("perceived_radius", 50.0)
                drone_data.setdefault("task_radius", 10.0)

                drone = self.drone_controller.add_drone(drone_data)
                session.drones[drone["id"]] = drone

        # Load targets
        if "targets" in json_data and self.target_controller:
            for target_data_src in json_data["targets"]:
                target_data = target_data_src.copy()
                # Ensure type is converted to enum if string
                if "type" in target_data and not isinstance(target_data["type"], TargetType):
                    target_data["type"] = TargetType(target_data.get("type", "fixed"))

                # Set defaults for missing fields
                target_data.setdefault("name", "Target")
                target_data.setdefault("position", {"x": 0.0, "y": 0.0, "z": 0.0})
                target_data.setdefault("description", "")
                target_data.setdefault("radius", 5.0)

                target = self.target_controller.add_target(target_data)
                session.targets[target["id"]] = target

        # Load obstacles
        if "obstacles" in json_data and self.obstacle_controller:
            for obstacle_data_src in json_data["obstacles"]:
                obstacle_data = obstacle_data_src.copy()
                # Ensure type is converted to enum if string
                if "type" in obstacle_data and not isinstance(obstacle_data["type"], ObstacleType):
                    obstacle_data["type"] = ObstacleType(obstacle_data.get("type", "circle"))

                # Set defaults for missing fields
                obstacle_data.setdefault("name", "Obstacle")
                obstacle_data.setdefault("position", {"x": 0.0, "y": 0.0, "z": 0.0})
                obstacle_data.setdefault("description", "")
                obstacle_data.setdefault("height", 10.0)

                obstacle = self.obstacle_controller.add_obstacle(obstacle_data)
                session.obstacles[obstacle["id"]] = obstacle
    
    def _create_example_data_for_session(self, session: Session) -> None:
        """Create example data for the session from JSON files

        Loads example data from JSON files in config/example/ directory based on task type.
        If the JSON file is not found, a warning is printed and no example data is created.
        """
        # Load from JSON file based on task type
        task_type = session.task_type.value if hasattr(session.task_type, 'value') else str(session.task_type)
        json_data = self._load_example_json_for_task(task_type)

        if json_data:
            # Use JSON data to populate the session
            self._create_example_data_from_json(session, json_data)
        else:
            # No example data available
            print(f"Warning: No example JSON file found for task type '{task_type}'. Session created without example data.")
    
    def _save_current_data_to_session(self, session_id: str) -> None:
        """Save current controller data to the specified session

        This method preserves all session-level history data that has already been
        accumulated (command_history, request_history, status_history, target_reaches, area_coverage, path_history)
        while updating the entity snapshots (drones, targets, obstacles, environment).
        """
        if session_id not in self.sessions:
            return

        session = self.sessions[session_id]

        # Save drones
        if self.drone_controller:
            session.drones = {drone_id: drone.to_dict() for drone_id, drone in self.drone_controller.drones.items()}

        # Save targets
        if self.target_controller:
            session.targets = {target_id: target.to_dict() for target_id, target in self.target_controller.targets.items()}

        # Save obstacles
        if self.obstacle_controller:
            session.obstacles = {obstacle_id: obstacle.to_dict() for obstacle_id, obstacle in self.obstacle_controller.obstacles.items()}

        # Save environment
        if self.environment_controller and self.environment_controller.current_environment_id:
            current_env = self.environment_controller.get_current_environment()
            session.environment = current_env

        # NOTE: We do NOT overwrite session-level history data here:
        # - session.command_history (tracked by session.add_command_to_history)
        # - session.request_history (tracked by request logging middleware)
        # - session.status_history (tracked by session.record_drone_status)
        # - session.target_reaches (tracked by session.record_target_reach)
        # - session.area_coverage (tracked by session.update_area_coverage)
        # These are already being maintained at the session level and should persist

        session.update_statistics()
    
    def _load_session_data_to_controllers(self, session: Session) -> None:
        """Load session data into global controllers"""
        # Clear existing data
        self._clear_all_data()

        # Update 3D distance setting in drone controller
        if self.drone_controller and hasattr(self.drone_controller, "set_is_3d"):
            self.drone_controller.set_is_3d(getattr(session, "is_distance_3d", False))
        
        # Load environment first
        if session.environment and self.environment_controller:
            env_data = session.environment.copy()
            # Ensure weather and wind_direction are enum instances
            weather_value = env_data.get("weather", WeatherCondition.CLEAR)
            if not isinstance(weather_value, WeatherCondition):
                weather_value = WeatherCondition(weather_value)
            env_data["weather"] = weather_value

            wind_value = env_data.get("wind_direction", WindDirection.NORTH)
            if not isinstance(wind_value, WindDirection):
                wind_value = WindDirection(wind_value)
            env_data["wind_direction"] = wind_value

            # Set defaults for missing fields
            env_data.setdefault("name", "Example Environment")
            env_data.setdefault("temperature", 20.0)
            env_data.setdefault("humidity", 50.0)
            env_data.setdefault("pressure", 1013.25)
            env_data.setdefault("wind_speed", 0.0)
            env_data.setdefault("visibility", 10000.0)

            env = self.environment_controller.add_environment(env_data)
            self.environment_controller.set_current_environment(env["id"])
        
        # Load drones
        if self.drone_controller:
            for drone_data in session.drones.values():
                # Use controller method to add drone (preserves ID since it's in the data)
                # The add_drone method now supports ID preservation when included in the dict
                self.drone_controller.add_drone(drone_data.copy())
        
        # Load targets
        if self.target_controller:
            for target_data in session.targets.values():
                # Use controller method to add target (preserves ID since it's in the data)
                # The add_target method now supports ID preservation when included in the dict
                self.target_controller.add_target(target_data.copy())
        
        # Load obstacles
        if self.obstacle_controller:
            for obstacle_data in session.obstacles.values():
                # Use controller method to add obstacle (preserves ID since it's in the data)
                # The add_obstacle method now supports ID preservation when included in the dict
                self.obstacle_controller.add_obstacle(obstacle_data.copy())
    
    def record_command_execution(self, session_id: Optional[str] = None) -> None:
        """Record that a command was executed in the session"""
        target_session_id = session_id or self.current_session_id
        if target_session_id and target_session_id in self.sessions:
            self.sessions[target_session_id].add_command_executed()
    
    def record_flight_time(self, flight_time: float, session_id: Optional[str] = None) -> None:
        """Record flight time in the session"""
        target_session_id = session_id or self.current_session_id
        if target_session_id and target_session_id in self.sessions:
            self.sessions[target_session_id].add_flight_time(flight_time)
    
    def record_distance_traveled(self, distance: float, session_id: Optional[str] = None) -> None:
        """Record distance traveled in the session"""
        target_session_id = session_id or self.current_session_id
        if target_session_id and target_session_id in self.sessions:
            self.sessions[target_session_id].add_distance_traveled(distance)
    


    def generate_session_screenshot(self, session_id: Optional[str] = None, fmt: str = "png", width: int = 1024, height: int = 768, center_x: Optional[float] = None, center_y: Optional[float] = None, scale_px_per_meter: Optional[float] = None, show_status: bool = False, show_label: bool = True) -> Optional[bytes]:
        """Render a static image of the current session UI to PNG/JPG/PDF/SVG/EPS bytes,
        updated to mirror ui/interface.py visuals (colors, shapes, outlines, labels).

        Args:
            session_id: Optional session id; defaults to current session
            fmt: One of 'png', 'jpg', 'jpeg', 'pdf', 'svg', 'eps'
            width: Image width in pixels
            height: Image height in pixels
            center_x: Optional override for canvas center X (meters)
            center_y: Optional override for canvas center Y (meters)
            scale_px_per_meter: Optional override for canvas scale (pixels per meter)
            show_status: Whether to include UI-equivalent path/coverage/status overlays
            show_label: Whether to include object labels for drones, targets, and obstacles

        Returns:
            Bytes of the encoded image or None if no session
        """
        target_session_id = session_id or self.current_session_id
        if not target_session_id or target_session_id not in self.sessions:
            return None

        session = self.sessions.get(target_session_id)

        drones = list(self.drone_controller.drones.values()) if self.drone_controller else []
        targets = list(self.target_controller.targets.values()) if self.target_controller else []
        obstacles = list(self.obstacle_controller.obstacles.values()) if self.obstacle_controller else []

        return _render_session_screenshot(
            session=session,
            drones=drones,
            targets=targets,
            obstacles=obstacles,
            fmt=fmt,
            width=width,
            height=height,
            center_x=center_x,
            center_y=center_y,
            scale_px_per_meter=scale_px_per_meter,
            show_status=show_status,
            show_label=show_label,
        )

    # ==================== Task Management Methods ====================

    @staticmethod
    def _normalize_task_compat(task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Backfill defaults for legacy task dictionaries."""
        normalized = task_data.copy()
        if "is_done" not in normalized:
            normalized["is_done"] = False
        if "is_passed" not in normalized:
            normalized["is_passed"] = False
        return normalized

    def create_task(
        self,
        session_id: str,
        name: str,
        content: str = "",
        content_aliases: Optional[List[str]] = None,
        description: str = "",
        creator: str = "unknown",
        difficulty: str = "medium",
        related_apis: Optional[List[Dict[str, Any]]] = None,
        execution_check_apis: Optional[Dict[str, Any]] = None,
        commands: Optional[List[str]] = None,
        originated_from: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new task in a session

        Args:
            session_id: ID of the session to add the task to
            name: Short name for the task
            content: Detailed content/instructions
            content_aliases: List of alternative names or aliases for the content
            description: Brief description
            creator: Who created the task
            difficulty: Difficulty level (easy, medium, or hard)
            related_apis: List of API endpoint objects with endpoint and parameters
            execution_check_apis: List of /check endpoints to validate execution
            commands: List of drone commands for the task
            originated_from: Principal that originated the task (defaults to creator)

        Returns:
            Task dictionary if successful, None if session not found
        """
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]

        # Compatibility: ensure tasks attribute exists for old sessions
        if not hasattr(session, 'tasks'):
            session.tasks = {}

        task = Task(
            task_id=None,
            name=name,
            content=content,
            content_aliases=content_aliases,
            description=description,
            creator=creator,
            originated_from=originated_from or creator,
            difficulty=difficulty,
            related_apis=related_apis,
            execution_check_apis=execution_check_apis,
            commands=commands
        )

        # Add task to session
        session.tasks[task.id] = task.to_dict()
        session.last_updated = time.time()

        return task.to_dict()

    def get_task(self, session_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific task from a session

        Args:
            session_id: ID of the session
            task_id: ID of the task

        Returns:
            Task dictionary if found, None otherwise
        """
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]

        # Compatibility: ensure tasks attribute exists for old sessions
        if not hasattr(session, 'tasks'):
            session.tasks = {}

        task_data = session.tasks.get(task_id)
        if task_data is None:
            return None

        normalized = self._normalize_task_compat(task_data)
        if normalized != task_data:
            session.tasks[task_id] = normalized
        return normalized

    def get_all_tasks(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get all tasks in a session

        Args:
            session_id: ID of the session

        Returns:
            List of task dictionaries, None if session not found
        """
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]

        # Compatibility: ensure tasks attribute exists for old sessions
        if not hasattr(session, 'tasks'):
            session.tasks = {}

        normalized_tasks: List[Dict[str, Any]] = []
        for task_id, task_data in session.tasks.items():
            normalized = self._normalize_task_compat(task_data)
            if normalized != task_data:
                session.tasks[task_id] = normalized
            normalized_tasks.append(normalized)

        return normalized_tasks

    def get_next_pending_task(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the next pending (not completed) task in a session

        Args:
            session_id: ID of the session

        Returns:
            Task dictionary if a pending task exists, None otherwise
        """
        tasks = self.get_all_tasks(session_id)
        if tasks is None:
            return None

        for task in tasks:
            if not task.get("is_done", False):
                return task

        return None

    def update_task(
        self,
        session_id: str,
        task_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a task's properties

        Args:
            session_id: ID of the session
            task_id: ID of the task to update
            updates: Dictionary of fields to update

        Returns:
            Updated task dictionary if successful, None if not found
        """
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]

        # Compatibility: ensure tasks attribute exists for old sessions
        if not hasattr(session, 'tasks'):
            session.tasks = {}

        task_data = session.tasks.get(task_id)

        if not task_data:
            return None

        from models.task import Task

        # Recreate task from dict, apply updates, and save
        task = Task.from_dict(task_data)
        task.update(updates)

        session.tasks[task_id] = task.to_dict()
        session.last_updated = time.time()

        return task.to_dict()

    def delete_task(self, session_id: str, task_id: str) -> bool:
        """Delete a task from a session

        Args:
            session_id: ID of the session
            task_id: ID of the task to delete

        Returns:
            True if deleted successfully, False if not found
        """
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        # Compatibility: ensure tasks attribute exists for old sessions
        if not hasattr(session, 'tasks'):
            session.tasks = {}

        if task_id in session.tasks:
            del session.tasks[task_id]
            session.last_updated = time.time()
            return True

        return False

    def mark_task_done(self, session_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """Mark a task as completed

        Args:
            session_id: ID of the session
            task_id: ID of the task

        Returns:
            Updated task dictionary if successful, None if not found
        """
        return self.update_task(session_id, task_id, {"is_done": True})

    def mark_task_pending(self, session_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """Mark a task as pending (not completed)

        Args:
            session_id: ID of the session
            task_id: ID of the task

        Returns:
            Updated task dictionary if successful, None if not found
        """
        return self.update_task(session_id, task_id, {"is_done": False})

    def swap_tasks(self, session_id: str, task_id_1: str, task_id_2: str) -> Optional[List[Dict[str, Any]]]:
        """Swap the order of two tasks in a session

        This method swaps the dictionary keys order by recreating the tasks dict
        with the two specified tasks in swapped positions.

        Args:
            session_id: ID of the session
            task_id_1: ID of the first task to swap
            task_id_2: ID of the second task to swap

        Returns:
            List of all tasks in new order if successful, None if session or tasks not found
        """
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]

        # Compatibility: ensure tasks attribute exists for old sessions
        if not hasattr(session, 'tasks'):
            session.tasks = {}

        # Check if both tasks exist
        if task_id_1 not in session.tasks or task_id_2 not in session.tasks:
            return None

        # If both IDs are the same, no swap needed
        if task_id_1 == task_id_2:
            return list(session.tasks.values())

        # Create new ordered dict with swapped tasks
        task_keys = list(session.tasks.keys())
        idx1 = task_keys.index(task_id_1)
        idx2 = task_keys.index(task_id_2)

        # Swap the keys
        task_keys[idx1], task_keys[idx2] = task_keys[idx2], task_keys[idx1]

        # Rebuild the tasks dict in new order
        new_tasks = {}
        for key in task_keys:
            new_tasks[key] = session.tasks[key]

        session.tasks = new_tasks
        session.last_updated = time.time()

        return list(session.tasks.values())
