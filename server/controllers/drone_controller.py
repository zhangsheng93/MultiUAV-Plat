import time
import math
from typing import Dict, List, Any, Optional, Tuple
from models.drone import Drone, DroneStatus, DroneCommand
from models.target import TargetType
from config.battery_config import BatteryConfig
from config.util import (
    distance as euclidean_distance,
    distance_2d,
    generate_random_id,
    polygon_area,
)
from shapely.geometry import Point, Polygon as ShapelyPolygon, LineString
from shapely import prepared


class DroneController:
    """Controller class for managing drones and executing commands"""

    def __init__(self, obstacle_controller=None, environment_controller=None, target_controller=None, session_controller=None):
        self.drones: Dict[str, Drone] = {}
        self.commands: Dict[str, Dict] = {}
        self.obstacle_controller = obstacle_controller
        self.environment_controller = environment_controller
        self.target_controller = target_controller
        self.session_controller = session_controller  # Reference to session controller for tracking
        self.is_3d = False

    def set_is_3d(self, is_3d: bool):
        """Set whether distance calculations should be 3D or 2D"""
        self.is_3d = bool(is_3d)

    def set_session_controller(self, session_controller):
        """Set the session controller reference (called after initialization)"""
        self.session_controller = session_controller

    def _get_current_session_ref(self):
        if not self.session_controller or not hasattr(self.session_controller, "get_current_session_ref"):
            return None
        return self.session_controller.get_current_session_ref()

    def _add_to_path_history(self, drone_id: str, position: Dict[str, float]) -> None:
        """Add position to path history via session controller"""
        session = self._get_current_session_ref()
        if session is not None:
            session.add_position_to_path_history(drone_id, position)

    def _get_last_path_position(self, drone_id: str) -> Optional[Dict[str, float]]:
        """Get the last position from path history via session controller"""
        session = self._get_current_session_ref()
        if session is not None and drone_id in session.path_history and session.path_history[drone_id]:
            return session.path_history[drone_id][-1]
        return None

    def _record_drone_status_to_session(self, drone: Drone) -> None:
        """Record a drone's status to the current session (if available)"""
        session = self._get_current_session_ref()
        if session is not None:
            session.record_drone_status(
                drone_id=drone.id,
                status=drone.status.value if hasattr(drone.status, 'value') else str(drone.status),
                position=drone.position.copy(),
                battery_level=drone.battery_level,
                battery_volume=drone.battery_volume
            )

    def _grid_points_for_geometry(self, geometry, grid_resolution: float) -> set:
        """Return coverage grid center points inside a Shapely geometry."""
        if geometry.is_empty:
            return set()

        minx, miny, maxx, maxy = geometry.bounds
        points = set()
        prep_geometry = prepared.prep(geometry)
        half_grid = grid_resolution / 2.0

        x = math.floor(minx / grid_resolution) * grid_resolution + half_grid
        while x <= maxx:
            y = math.floor(miny / grid_resolution) * grid_resolution + half_grid
            while y <= maxy:
                if prep_geometry.covers(Point(x, y)):
                    points.add((x, y))
                y += grid_resolution
            x += grid_resolution

        return points

    def _record_movement_polyline(self, drone: Drone, positions: List[Dict[str, float]]) -> None:
        """Record cumulative area coverage for a movement path."""
        if not self.session_controller or not self.target_controller or len(positions) < 2:
            return

        try:
            session = self._get_current_session_ref()
            if session is None:
                return

            coordinates = [(pos["x"], pos["y"]) for pos in positions]
            path_line = LineString(coordinates)
            if path_line.length < 0.5:
                return

            all_targets = self.target_controller.get_all_targets()
            area_targets = [t for t in all_targets if t.get("type") in ["circle", "polygon"]]
            if not area_targets:
                return

            grid_resolution = 2.0
            grid_cell_area = grid_resolution * grid_resolution
            coverage_corridor = path_line.buffer(drone.task_radius)

            for target in area_targets:
                target_id = target["id"]
                target_type = target.get("type")

                if target_type == "circle":
                    tx, ty = target["position"]["x"], target["position"]["y"]
                    radius = target.get("radius", 0)
                    if radius <= 0:
                        continue

                    target_geometry = Point(tx, ty).buffer(radius)
                    if target_id not in session.area_coverage:
                        total_points = self._grid_points_for_geometry(target_geometry, grid_resolution)
                        total_area = len(total_points) * grid_cell_area
                        if total_area <= 0:
                            total_area = math.pi * radius * radius
                        session.initialize_area_coverage(target_id, "circle", total_area)

                elif target_type == "polygon":
                    verts = target.get("vertices", [])
                    if len(verts) < 3:
                        continue

                    target_geometry = ShapelyPolygon([(v["x"], v["y"]) for v in verts])
                    if target_id not in session.area_coverage:
                        total_points = self._grid_points_for_geometry(target_geometry, grid_resolution)
                        total_area = len(total_points) * grid_cell_area
                        if total_area <= 0:
                            total_area = polygon_area(verts)
                        session.initialize_area_coverage(target_id, "polygon", total_area)

                else:
                    continue

                if not coverage_corridor.intersects(target_geometry):
                    continue

                covered_area = coverage_corridor.intersection(target_geometry)
                if covered_area.is_empty:
                    continue

                covered = self._grid_points_for_geometry(covered_area, grid_resolution)
                if covered:
                    session.update_area_coverage(target_id, covered, grid_cell_area)

        except Exception:
            # Don't fail the movement command if coverage tracking has issues.
            pass

    def _record_movement_path(self, drone: Drone, start_pos: Dict[str, float], end_pos: Dict[str, float]) -> None:
        """Record movement path for area coverage - OPTIMIZED

        Args:
            drone: The drone that moved
            start_pos: Starting position
            end_pos: Ending position
        """
        self._record_movement_polyline(drone, [start_pos, end_pos])

    def _consume_battery(self, drone: Drone, command: str,
                        start_pos: Optional[Dict] = None,
                        end_pos: Optional[Dict] = None) -> tuple:
        """Calculate and consume battery for a command

        Args:
            drone: The drone executing the command
            command: Command name
            start_pos: Starting position (for movement commands)
            end_pos: Ending position (for movement commands)

        Returns:
            Tuple of (percentage_consumed, mah_consumed)
        """
        # Get current environment if environment controller is available
        environment = None
        weather = "clear"  # Fallback for legacy support

        if self.environment_controller:
            try:
                current_env = self.environment_controller.get_current_environment()
                if current_env:
                    environment = current_env
                    weather = current_env.get("weather", "clear")
            except:
                pass  # Default to clear weather if we can't get environment

        # Calculate battery cost in percentage
        if start_pos and end_pos:
            # Movement command with distance calculation
            # Pass full environment data and drone heading for comprehensive calculation
            battery_cost_percent = BatteryConfig.calculate_movement_cost(
                command=command,
                start_pos=start_pos,
                end_pos=end_pos,
                weather=weather,
                environment=environment,
                drone_heading=drone.heading
            )
        else:
            # Fixed cost command
            battery_cost_percent = BatteryConfig.get_command_cost(command)

        # Convert percentage to mAh
        battery_cost_mah = (battery_cost_percent / 100.0) * drone.battery_capacity

        # Apply battery consumption
        new_battery_level = max(0.0, drone.battery_level - battery_cost_percent)
        drone.update_battery(new_battery_level)

        return battery_cost_percent, battery_cost_mah

    def _check_and_record_target_reaches(self, drone: Drone) -> List[Dict]:
        """Check if drone has reached any targets and record them

        Args:
            drone: The drone to check

        Returns:
            List of targets that were reached
        """
        if not self.target_controller:
            return []

        targets_reached = []
        
        # Iterate over target objects directly to use their check method
        for target in self.target_controller.targets.values():
            if target.check_drone_reached(drone.id, drone.position, drone.task_radius, is_distance_3d=self.is_3d):
                # Record the visit on the drone (supports multiple visits to same target)
                targets_reached.append(target.to_dict())

                # Also record in session's tracking system (supports multiple visits)
                if self.session_controller:
                    try:
                        session = self._get_current_session_ref()
                        if session is not None:
                            session.record_target_reach(
                                drone_id=drone.id,
                                target_id=target.id
                            )
                            if target.type == TargetType.MOVING:
                                session.record_target_tracking(target.id, drone.id)
                                target.mark_tracked()

                            # For point-type targets (fixed, waypoint, moving), reaching means 100% searched
                            if target.type not in [TargetType.CIRCLE, TargetType.POLYGON]:
                                session.mark_target_fully_covered(target.id)
                    except Exception:
                        pass  # Don't fail if session tracking has issues

        return targets_reached

    def _get_target_geometry_cache(self) -> List[Dict[str, Any]]:
        """Build target geometry objects once for a command."""
        if not self.target_controller:
            return []

        cache = []
        for target in self.target_controller.targets.values():
            cache.append({
                "target": target,
                "geometry": target.to_geometry(),
            })
        return cache

    def _check_and_record_target_reaches_along_path(
        self,
        drone: Drone,
        start_pos: Dict[str, float],
        end_pos: Dict[str, float],
        target_geometry_cache: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict]:
        """Check if drone has reached any targets along a movement path and record them

        This method checks if any point along the straight-line path from start_pos to end_pos
        comes within the drone's task_radius of any target.

        Args:
            drone: The drone that is moving
            start_pos: Starting position of the movement
            end_pos: Ending position of the movement

        Returns:
            List of targets that were reached along the path
        """
        if not self.target_controller:
            return []

        targets_reached = []
        
        # Calculate path length
        # Use 3D distance for path length calculation if is_3d, else 2D
        if self.is_3d:
            path_length = euclidean_distance(start_pos, end_pos)
        else:
            path_length = distance_2d(start_pos, end_pos)

        if path_length == 0:
            # If no movement, just check current position
            return self._check_and_record_target_reaches(drone)
            
        # Create path line (2D) for geometry checks
        path_line = LineString([(start_pos["x"], start_pos["y"]), (end_pos["x"], end_pos["y"])])
        
        # Z-range for path
        min_z = min(start_pos.get("z", 0), end_pos.get("z", 0))
        max_z = max(start_pos.get("z", 0), end_pos.get("z", 0))

        target_entries = target_geometry_cache
        if target_entries is None:
            target_entries = self._get_target_geometry_cache()

        # Iterate over target objects
        for entry in target_entries:
            target = entry["target"]
            geometry = entry["geometry"]
            
            in_range = False
            
            if geometry is not None:
                # 2D distance from path to target geometry
                dist_2d = path_line.distance(geometry)
                
                # Z distance
                if not self.is_3d or target.type in [TargetType.CIRCLE, TargetType.POLYGON]:
                    # Ignore Z if 2D mode or for area targets (infinite height cylinder)
                    dist_z = 0.0
                else:
                    target_z = target.position.get("z", 0)
                    # If target Z is within path Z range, Z-distance is 0. Else, dist to range.
                    if min_z <= target_z <= max_z:
                        dist_z = 0
                    else:
                        dist_z = min(abs(target_z - min_z), abs(target_z - max_z))
                
                # Combined distance
                distance = (dist_2d**2 + dist_z**2)**0.5
                
                if distance <= drone.task_radius:
                    in_range = True
            else:
                # Fallback logic for targets without geometry (e.g. invalid polygon or points)
                target_position = target.position
                
                # Calculate the closest point on the line segment to the target
                dx = end_pos["x"] - start_pos["x"]
                dy = end_pos["y"] - start_pos["y"]
                dz = end_pos["z"] - start_pos["z"]
                
                # Vector from start to target
                to_target_x = target_position["x"] - start_pos["x"]
                to_target_y = target_position["y"] - start_pos["y"]
                to_target_z = target_position["z"] - start_pos["z"]

                # Project target onto path line (normalized parameter t)
                # Note: This projection is 3D. In 2D mode, we should ideally use 2D projection.
                # However, if start_pos and end_pos have same Z (or we ignore Z), 
                # then dz=0 and to_target_z is ignored if we zero it out.
                
                if not self.is_3d:
                    dz = 0.0
                    to_target_z = 0.0
                    # Recalculate 2D path length squared
                    p_len_sq = dx*dx + dy*dy
                else:
                    p_len_sq = path_length * path_length

                if p_len_sq > 0:
                    t = (to_target_x * dx + to_target_y * dy + to_target_z * dz) / p_len_sq
                    t = max(0.0, min(1.0, t))
                else:
                    t = 0.0

                # Calculate closest point on the path
                closest_x = start_pos["x"] + t * dx
                closest_y = start_pos["y"] + t * dy
                closest_z = start_pos["z"] + t * dz
                closest_point = {"x": closest_x, "y": closest_y, "z": closest_z}

                # Calculate distance from target to closest point on path
                if self.is_3d:
                    distance_to_path = euclidean_distance(target_position, closest_point)
                else:
                    distance_to_path = distance_2d(target_position, closest_point)
                
                if distance_to_path <= drone.task_radius:
                    in_range = True

            if in_range:
                # Record the visit on the drone
                targets_reached.append(target.to_dict())

                # Also record in session's tracking system (supports multiple visits)
                if self.session_controller:
                    try:
                        session = self._get_current_session_ref()
                        if session is not None:
                            session.record_target_reach(
                                drone_id=drone.id,
                                target_id=target.id
                            )
                            if target.type == TargetType.MOVING:
                                session.record_target_tracking(target.id, drone.id)
                                target.mark_tracked()

                            # For point-type targets (fixed, waypoint, moving), reaching means 100% searched
                            if target.type not in [TargetType.CIRCLE, TargetType.POLYGON]:
                                session.mark_target_fully_covered(target.id)
                    except Exception:
                        pass  # Don't fail if session tracking has issues

        return targets_reached

    def add_drone(self, drone_data: Dict[str, Any]) -> Dict:
        """Add a new drone to the system

        Args:
            drone_data: Dictionary containing drone data with keys:
                - name: Drone name (required)
                - model: Drone model (required)
                - max_speed: Maximum speed in m/s (required)
                - max_altitude: Maximum altitude in meters (required)
                - battery_capacity: Battery capacity in mAh (required)
                - position: Initial position dict with x, y, z (optional, default: {x: 0, y: 0, z: 0})
                - perceived_radius: Perception radius in meters (optional, default: 50.0)
                - task_radius: Task radius in meters (optional, default: 10.0)
                - heading: Initial heading in degrees (optional, default: 0.0)
                - speed: Initial speed in m/s (optional, default: 0.0)
                - battery_level: Initial battery level percentage (optional)
                - battery_volume: Initial battery volume in mAh (optional, overrides battery_level)
                - status: Initial status (optional)
                - home_position: Home position dict with x, y, z (optional, defaults to position)
                - id: Optional ID to preserve when restoring from sessions

        Returns:
            Dict representation of the created drone
        """
        # Ensure position has a default if not provided
        if "position" not in drone_data:
            drone_data["position"] = {"x": 0.0, "y": 0.0, "z": 0.0}

        # Create drone from dict (preserves ID if provided)
        drone = Drone.from_dict(drone_data)

        # Only set home position automatically if not provided in data
        if "home_position" not in drone_data:
            drone.set_home_position()

        self.drones[drone.id] = drone
        return drone.to_dict()
    
    def get_all_drones(self) -> List[Dict]:
        """Get all registered drones"""
        return [drone.to_dict() for drone in self.drones.values()]
    
    def get_drone(self, drone_id: str) -> Optional[Dict]:
        """Get a specific drone by ID"""
        if drone_id in self.drones:
            return self.drones[drone_id].to_dict()
        return None

    def update_drone(self, drone_id: str, updates: Dict[str, Any]) -> Optional[Dict]:
        """Update a drone's properties

        Args:
            drone_id: The ID of the drone to update
            updates: Dictionary of properties to update

        Returns:
            Updated drone dictionary, or None if drone not found
        """
        if drone_id not in self.drones:
            return None

        drone = self.drones[drone_id]
        drone.apply_update(updates)
        return drone.to_dict()

    def update_drone_position(self, drone_id: str, x: float, y: float, z: float) -> Optional[Dict]:
        """Update a drone's position directly (administrative function)

        Args:
            drone_id: The ID of the drone to update
            x: New X coordinate
            y: New Y coordinate
            z: New Z coordinate (altitude)

        Returns:
            Updated drone dictionary, or None if drone not found
        """
        if drone_id not in self.drones:
            return None

        drone = self.drones[drone_id]

        # Validate altitude
        if z < 0:
            raise ValueError("Altitude cannot be negative")
        if z > drone.max_altitude:
            raise ValueError(f"Altitude exceeds maximum ({drone.max_altitude}m)")

        # Check for obstacle collision at new position
        if self.obstacle_controller:
            new_position = {"x": x, "y": y, "z": z}
            collision_result = self.obstacle_controller.check_point_collision(x, y, z, margin=0.0)
            if collision_result["result"]:
                # Get the first obstacle from the list
                first_obstacle = collision_result["inside_obstacles"][0]
                raise ValueError(f"Position conflicts with {first_obstacle['type']} obstacle '{first_obstacle['name']}'")

        # Update position
        drone.update_position(x, y, z)

        # Update status based on altitude
        if z > 0 and drone.status in [DroneStatus.IDLE, DroneStatus.READY]:
            drone.update_status(DroneStatus.HOVERING)
        elif z == 0 and drone.status in [DroneStatus.HOVERING, DroneStatus.FLYING, DroneStatus.MOVING]:
            drone.update_status(DroneStatus.IDLE)

        return drone.to_dict()

    def get_other_drones(self, drone_id: str) -> List[Dict]:
        """Get other drones within the calling drone's perceived radius"""
        if drone_id not in self.drones:
            raise KeyError(f"Drone with ID {drone_id} not found")

        origin = self.drones[drone_id]
        r = origin.perceived_radius

        nearby = []
        for d in self.drones.values():
            if d.id == origin.id:
                continue
            
            if self.is_3d:
                dist = euclidean_distance(d.position, origin.position)
            else:
                dist = distance_2d(d.position, origin.position)
                
            if dist <= r:
                nearby.append(d.to_dict())
        return nearby

    def get_other_targets(self, drone_id: str) -> List[Dict]:
        """Get targets within the calling drone's perceived radius

        For shaped targets (circles, polygons), calculates distance to the boundary/edge.
        For point targets, calculates distance to center.
        """
        if drone_id not in self.drones:
            raise KeyError(f"Drone with ID {drone_id} not found")
        if not self.target_controller:
            return []

        origin = self.drones[drone_id]
        r = origin.perceived_radius

        # Create drone point for geometry calculations
        drone_point = Point(origin.position["x"], origin.position["y"])

        nearby = []
        # Iterate over target instances (not dicts) to access to_geometry() method
        for target in self.target_controller.targets.values():
            try:
                # Try to get geometry for shaped targets
                geometry = target.to_geometry()
                
                if geometry is not None:
                    # Calculate 2D distance to geometry boundary (Shapely handles edge distance)
                    dist_2d = geometry.distance(drone_point)
                    
                    if not self.is_3d or target.type in [TargetType.CIRCLE, TargetType.POLYGON]:
                        dist = dist_2d
                    else:
                        dist_z = abs(origin.position.get("z", 0.0) - target.position.get("z", 0.0))
                        dist = (dist_2d**2 + dist_z**2)**0.5
                else:
                    if self.is_3d:
                        dist = euclidean_distance(target.position, origin.position)
                    else:
                        dist = distance_2d(target.position, origin.position)
            except Exception:
                if self.is_3d:
                    dist = euclidean_distance(target.position, origin.position)
                else:
                    dist = distance_2d(target.position, origin.position)

            if dist <= r:
                nearby.append(target.to_dict())
        return nearby

    def get_other_obstacles(self, drone_id: str) -> List[Dict]:
        """Get obstacles within the calling drone's perceived radius

        Uses distance to boundary/edge for all obstacle types.
        """
        if drone_id not in self.drones:
            raise KeyError(f"Drone with ID {drone_id} not found")
        if not self.obstacle_controller:
            return []

        origin = self.drones[drone_id]
        r = origin.perceived_radius
        ox, oy, oz = origin.position["x"], origin.position["y"], origin.position["z"]

        # Create drone point for geometry calculations
        drone_point = Point(ox, oy)

        nearby = []
        # Use obstacle instances for precise geometry checks
        for obstacle in self.obstacle_controller.obstacles.values():
            try:
                geometry = obstacle.to_geometry()
                if geometry is not None:
                    # Calculate 2D distance to geometry boundary
                    dist_2d = geometry.distance(drone_point)
                    
                    if not self.is_3d:
                        dist = dist_2d
                    else:
                        # For obstacles, they have a height or are infinite
                        # Most obstacles in this system seem to have a height or are infinite
                        # Let's check if obstacle has height
                        obs_z = obstacle.position.get("z", 0.0)
                        obs_height = getattr(obstacle, 'height', None)
                        
                        if obs_height is None: # Infinite height
                            dist = dist_2d
                        else:
                            # Distance to vertical segment [obs_z, obs_z + obs_height]
                            if obs_z <= oz <= obs_z + obs_height:
                                dist_z = 0.0
                            else:
                                dist_z = min(abs(oz - obs_z), abs(oz - (obs_z + obs_height)))
                            dist = (dist_2d**2 + dist_z**2)**0.5
                else:
                    if self.is_3d:
                        dist = euclidean_distance(obstacle.position, origin.position)
                    else:
                        dist = distance_2d(obstacle.position, origin.position)
            except Exception:
                if self.is_3d:
                    dist = euclidean_distance(obstacle.position, origin.position)
                else:
                    dist = distance_2d(obstacle.position, origin.position)

            if dist <= r:
                nearby.append(obstacle.to_dict())
        return nearby

    def get_others(self, drone_id: str) -> Dict[str, List[Dict]]:
        """Get all nearby entities (drones, targets, obstacles) for a drone"""
        return {
            "drones": self.get_other_drones(drone_id),
            "targets": self.get_other_targets(drone_id),
            "obstacles": self.get_other_obstacles(drone_id),
        }
    
    def send_command(self, drone_id: str, command: DroneCommand, parameters: Dict[str, Any]) -> Dict:
        """Send a command to a specific drone"""
        if drone_id not in self.drones:
            raise KeyError(f"Drone with ID {drone_id} not found")
        
        drone = self.drones[drone_id]
        command_id = generate_random_id()
        
        # Process the command based on its type
        command_result = self._process_command(drone, command, parameters)
        if len(command_result) == 3:
            status, message, response_metadata = command_result
        else:
            status, message = command_result
            response_metadata = {}
        
        # Create command response
        command_response = {
            "command_id": command_id,
            "drone_id": drone_id,
            "command": command,
            "status": status,
            "message": message,
            "timestamp": time.time()
        }
        command_response.update(response_metadata)
        
        # Store command in history
        self.commands[command_id] = command_response

        # Record command in session history if session controller is available
        session = self._get_current_session_ref()
        if session is not None:
            session.add_command_to_history(
                command_id=command_id,
                drone_id=drone_id,
                command=command.value if hasattr(command, 'value') else str(command),
                parameters=parameters,
                status=status,
                message=message
            )
            # Record drone status after command execution
            self._record_drone_status_to_session(drone)

        if self.session_controller and hasattr(self.session_controller, "sync_current_session_state"):
            self.session_controller.sync_current_session_state()
        elif self.session_controller and hasattr(self.session_controller, "sync_current_session_snapshot"):
            self.session_controller.sync_current_session_snapshot()

        return command_response
    
    def _validate_and_execute_path(
        self,
        drone: Drone,
        waypoints: List[Dict[str, Any]],
        command_name: str,
        allow_partial_move: bool = False,
    ) -> tuple[str, Any]:
        """
        Common logic for moving a drone along a path (single or multiple waypoints).
        Handles validation, collision checks, battery checks, and execution.
        """
        if not waypoints:
            return "error", "No waypoints provided"

        def waypoint_triple(waypoint: Dict[str, Any]) -> Tuple[float, float, float]:
            return (float(waypoint["x"]), float(waypoint["y"]), float(waypoint["z"]))

        def point_progress(completed_count: int) -> Dict[str, Any]:
            successful_points = [waypoint_triple(waypoint) for waypoint in waypoints[:completed_count]]
            unsuccessful_points = [waypoint_triple(waypoint) for waypoint in waypoints[completed_count:]]
            return {
                "successful_points_count": len(successful_points),
                "successful_points": successful_points,
                "unsuccessful_points_count": len(unsuccessful_points),
                "unsuccessful_points": unsuccessful_points,
            }

        # 1. Validate payload and calculate per-segment battery before any movement.
        current_pos = drone.position
        prev_pos = current_pos
        total_battery_required = 0.0
        segments = []

        # Environment for battery check
        environment = None
        if self.environment_controller:
            try:
                environment = self.environment_controller.get_current_environment()
            except:
                pass

        normalized_waypoints = []
        default_z = current_pos.get("z", 0.0)

        for i, waypoint in enumerate(waypoints):
            # Validate coordinates
            if "x" not in waypoint or "y" not in waypoint:
                return "error", f"Waypoint {i+1} missing coordinates"
            waypoint = dict(waypoint)
            waypoint.setdefault("z", default_z)
            # Validate altitude
            z = waypoint["z"]
            if z > drone.max_altitude:
                return "error", f"Waypoint {i+1} altitude exceeds maximum ({drone.max_altitude}m)"
            if z < 0:
                return "error", f"Waypoint {i+1} altitude cannot be negative"

            heading = drone.calculate_heading_to(waypoint["x"], waypoint["y"])
            if self.is_3d:
                dist = euclidean_distance(prev_pos, waypoint)
            else:
                dist = distance_2d(prev_pos, waypoint)

            # Calculate battery cost for this segment
            segment_battery = BatteryConfig.calculate_movement_cost(
                command=command_name,
                start_pos=prev_pos,
                end_pos=waypoint,
                weather="clear", 
                environment=environment,
                drone_heading=drone.heading
            )
            normalized_waypoints.append(waypoint)
            segments.append({
                "index": i,
                "start": prev_pos,
                "end": waypoint,
                "heading": heading,
                "distance": dist,
                "battery_percent": segment_battery,
            })
            total_battery_required += segment_battery
            
            prev_pos = waypoint

        waypoints = normalized_waypoints

        # 2. Battery Sufficiency Check
        available_battery = drone.battery_level - BatteryConfig.CRITICAL_BATTERY_LEVEL
        if not allow_partial_move and total_battery_required > available_battery:
            shortage = total_battery_required - available_battery
            return "error", (f"Insufficient battery to complete path: "
                             f"requires {total_battery_required:.2f}%, "
                             f"available {available_battery:.2f}% "
                             f"(shortage: {shortage:.2f}%)")

        executable_segments = segments
        blocked_reason = None
        blocked_waypoint_index = None

        if allow_partial_move:
            executable_segments = []
            selected_battery_required = 0.0
            for segment in segments:
                i = segment["index"]
                waypoint = segment["end"]
                segment_battery = segment["battery_percent"]
                if selected_battery_required + segment_battery > available_battery:
                    required = selected_battery_required + segment_battery
                    shortage = required - available_battery
                    blocked_reason = (
                        f"Insufficient battery for waypoint {i+1}: "
                        f"requires {required:.2f}%, available {available_battery:.2f}% "
                        f"(shortage: {shortage:.2f}%)"
                    )
                    blocked_waypoint_index = i + 1
                    break

                collision_result = self._check_position_collision(waypoint)
                if collision_result:
                    blocked_reason = f"Waypoint {i+1} conflicts with obstacle: {collision_result}"
                    blocked_waypoint_index = i + 1
                    break

                path_collision_result = self._check_path_collision(segment["start"], waypoint)
                if path_collision_result:
                    blocked_reason = f"Path to waypoint {i+1} blocked: {path_collision_result}"
                    blocked_waypoint_index = i + 1
                    break

                executable_segments.append(segment)
                selected_battery_required += segment_battery

            if not executable_segments:
                return "error", blocked_reason or "Path is blocked before reaching the first waypoint"
        else:
            for segment in segments:
                i = segment["index"]
                waypoint = segment["end"]
                collision_result = self._check_position_collision(waypoint)
                if collision_result:
                    return "error", f"Waypoint {i+1} conflicts with obstacle: {collision_result}"

                path_collision_result = self._check_path_collision(segment["start"], waypoint)
                if path_collision_result:
                    return "error", f"Path to waypoint {i+1} blocked: {path_collision_result}"

        # 3. Execution
        drone.update_status(DroneStatus.MOVING)

        start_position = drone.position.copy()
        current_pos = start_position
        total_distance = 0.0
        all_targets_reached = []
        total_battery_percent = sum(segment["battery_percent"] for segment in executable_segments)
        total_battery_mah = (total_battery_percent / 100.0) * drone.battery_capacity
        
        # Add start position to path history if needed
        last_pos = self._get_last_path_position(drone.id)
        if not last_pos or last_pos != start_position:
            self._add_to_path_history(drone.id, start_position)

        executed_positions = [start_position] + [segment["end"] for segment in executable_segments]
        self._record_movement_polyline(drone, executed_positions)
        target_geometry_cache = self._get_target_geometry_cache()

        for i, segment in enumerate(executable_segments):
            waypoint = segment["end"]
            new_heading = segment["heading"]
            dist = segment["distance"]
            seg_cost_p = segment["battery_percent"]
            drone.update_heading(new_heading)
            total_distance += dist
            # Add to path history
            self._add_to_path_history(drone.id, waypoint)

            # Check targets
            segment_targets = self._check_and_record_target_reaches_along_path(
                drone,
                current_pos,
                waypoint,
                target_geometry_cache=target_geometry_cache,
            )
            all_targets_reached.extend(segment_targets)

            # Record history waypoint
            drone.record_history_waypoint(
                event=command_name,
                start_position=current_pos,
                position=waypoint,
                metadata={
                    "waypoint_index": i,
                    "total_waypoints": len(waypoints),
                    "distance_segment": dist,
                    "heading": new_heading,
                    "battery_consumed": seg_cost_p
                }
            )

            current_pos = waypoint

        drone.update_battery(drone.battery_level - total_battery_percent)

        # Finalize
        final_waypoint = executable_segments[-1]["end"]
        drone.update_position(final_waypoint["x"], final_waypoint["y"], final_waypoint["z"])
        drone.update_status(DroneStatus.HOVERING)

        return "success", {
            "battery_consumed": total_battery_percent,
            "battery_consumed_mah": total_battery_mah,
            "distance": total_distance,
            "targets_reached": all_targets_reached,
            "final_position": final_waypoint,
            "final_heading": drone.heading,
            "requested_waypoints": len(waypoints),
            "completed_waypoints": len(executable_segments),
            "partial_move": len(executable_segments) < len(waypoints),
            "blocked_waypoint_index": blocked_waypoint_index,
            "blocked_reason": blocked_reason,
            **point_progress(len(executable_segments)),
        }

    def _process_command(self, drone: Drone, command: DroneCommand, 
                        parameters: Dict[str, Any]) -> tuple:
        """Process a command for a drone and return status and message"""
        
        # Check for emergency battery status before processing most commands
        if command not in [DroneCommand.CONNECT, DroneCommand.DISCONNECT, DroneCommand.EMERGENCY_STOP]:
            if drone.is_emergency_battery() and drone.status != DroneStatus.EMERGENCY:
                # Force emergency landing
                drone.update_status(DroneStatus.EMERGENCY)
                drone.update_position(drone.position["x"], drone.position["y"], 0.0)
                return "error", "Emergency landing executed due to critical battery level (<0.5%)"
            
            if drone.status == DroneStatus.EMERGENCY and not drone.can_operate():
                return "error", "Drone is in emergency state. Battery must be above 5% to resume operations."
        
        # Simulate command processing
        if command == DroneCommand.CONNECT:
            if drone.status == DroneStatus.OFFLINE:
                drone.update_status(DroneStatus.IDLE)
                return "success", "Drone connected successfully"
            return "error", "Drone is already connected"
        
        elif command == DroneCommand.DISCONNECT:
            drone.update_status(DroneStatus.OFFLINE)
            return "success", "Drone disconnected successfully"
        
        elif command == DroneCommand.TAKE_OFF:
            if drone.status in [DroneStatus.IDLE, DroneStatus.READY]:
                # Check battery level
                if drone.battery_level < BatteryConfig.CRITICAL_BATTERY_LEVEL:
                    return "error", f"Battery level too low for takeoff (need {BatteryConfig.CRITICAL_BATTERY_LEVEL}%, have {drone.battery_level:.1f}%)"

                # Get altitude from parameters or use default
                target_altitude = parameters.get("altitude", 5.0)
                if target_altitude > drone.max_altitude:
                    return "error", f"Requested altitude exceeds maximum ({drone.max_altitude}m)"

                # Check for obstacle collision at takeoff position
                start_position = drone.position.copy()
                target_position = {
                    "x": drone.position["x"],
                    "y": drone.position["y"],
                    "z": target_altitude
                }

                collision_result = self._check_position_collision(target_position)
                if collision_result:
                    return "error", f"Cannot take off: {collision_result}"

                # Update drone status and position
                drone.update_status(DroneStatus.TAKING_OFF)
                drone.update_position(drone.position["x"], drone.position["y"], target_altitude)
                drone.update_status(DroneStatus.HOVERING)

                # Check target reaches along path
                self._check_and_record_target_reaches_along_path(drone, start_position, target_position)

                # Consume battery (takeoff cost + vertical movement)
                battery_cost_percent, battery_cost_mah = self._consume_battery(drone, "take_off", start_position, target_position)

                # Record waypoint reached
                drone.record_history_waypoint(
                    event="take_off",
                    start_position=start_position,
                    position=target_position,
                    metadata={
                        "altitude": target_altitude,
                        "distance_traveled": abs(target_altitude - start_position["z"]) if self.is_3d else 0.0,
                    }
                )

                return "success", f"Drone taking off to altitude {target_altitude}m (battery: -{battery_cost_percent:.1f}%/-{battery_cost_mah:.0f}mAh, remaining: {drone.battery_level:.1f}%/{drone.battery_volume:.0f}mAh)"
            return "error", f"Cannot take off from current status: {drone.status}"
        
        elif command == DroneCommand.LAND:
            if drone.status in [DroneStatus.HOVERING, DroneStatus.FLYING, DroneStatus.MOVING]:
                start_position = drone.position.copy()
                end_position = {"x": drone.position["x"], "y": drone.position["y"], "z": 0.0}

                collision_result = self._check_position_collision(end_position)
                if collision_result:
                    return "error", f"Cannot land: {collision_result}"

                drone.update_status(DroneStatus.LANDING)
                drone.update_position(drone.position["x"], drone.position["y"], 0.0)
                drone.update_status(DroneStatus.IDLE)

                # Check target reaches along path
                self._check_and_record_target_reaches_along_path(drone, start_position, end_position)

                # Consume battery for landing
                battery_cost_percent, battery_cost_mah = self._consume_battery(drone, "land", start_position, end_position)

                # Record waypoint reached
                drone.record_history_waypoint(
                    event="land",
                    start_position=start_position,
                    position=end_position,
                    metadata={
                        "altitude_descended": start_position["z"],
                        "battery_consumed": battery_cost_percent
                    }
                )

                return "success", f"Drone landed successfully (battery: -{battery_cost_percent:.1f}%/-{battery_cost_mah:.0f}mAh, remaining: {drone.battery_level:.1f}%/{drone.battery_volume:.0f}mAh)"
            return "error", f"Cannot land from current status: {drone.status}"
        
        elif command == DroneCommand.MOVE_TO:
            if drone.status in [DroneStatus.HOVERING, DroneStatus.FLYING, DroneStatus.MOVING]:
                # Get position parameters
                x = parameters.get("x", drone.position["x"])
                y = parameters.get("y", drone.position["y"])
                z = parameters.get("z", drone.position["z"])

                target_position = {"x": x, "y": y, "z": z}
                
                # Execute movement using shared logic
                status, result = self._validate_and_execute_path(drone, [target_position], "move_to")
                
                if status == "error":
                    # Adapt error message for single target context
                    if "Waypoint 1" in str(result):
                        result = str(result).replace("Waypoint 1", "Target position")
                    return status, result

                # Build response message
                message = f"Drone moved to position ({x}, {y}, {z}), heading: {result['final_heading']:.1f}° (battery: -{result['battery_consumed']:.1f}%/-{result['battery_consumed_mah']:.0f}mAh, remaining: {drone.battery_level:.1f}%/{drone.battery_volume:.0f}mAh)"
                
                targets_reached = result["targets_reached"]
                if targets_reached:
                    # Deduplicate targets by ID for display
                    seen_ids = set()
                    unique_targets = []
                    for t in targets_reached:
                        if t["id"] not in seen_ids:
                            unique_targets.append(t)
                            seen_ids.add(t["id"])
                    
                    target_names = ", ".join([t["name"] for t in unique_targets])
                    message += f" - Reached target(s): {target_names}"

                return "success", message
            return "error", f"Cannot move from current status: {drone.status}"

        elif command == DroneCommand.MOVE_TOWARDS:
            if drone.status in [DroneStatus.HOVERING, DroneStatus.FLYING, DroneStatus.MOVING]:
                # Get distance parameter
                distance = parameters.get("distance")
                if distance is None:
                    return "error", "Distance parameter is required"

                try:
                    distance = float(distance)
                except (ValueError, TypeError):
                    return "error", "Distance must be a valid number"

                if distance <= 0:
                    return "error", "Distance must be positive"

                # Get direction parameters
                heading = parameters.get("heading")
                dx = parameters.get("dx")
                dy = parameters.get("dy")
                dz = parameters.get("dz", 0.0)
                azimuth = parameters.get("azimuth")
                elevation = parameters.get("elevation", 0.0)

                current_x = drone.position["x"]
                current_y = drone.position["y"]
                current_z = drone.position["z"]

                # Calculate target position
                # If no direction is specified, use current drone heading
                if heading is None and dx is None and dy is None and azimuth is None:
                    heading = drone.heading

                if heading is not None:
                    try:
                        heading = float(heading)
                    except (ValueError, TypeError):
                        return "error", "Heading must be a valid number"
                    
                    # Convert heading to radians
                    heading_rad = math.radians(heading)
                    
                    target_x = current_x + distance * math.sin(heading_rad)
                    target_y = current_y + distance * math.cos(heading_rad)
                    target_z = current_z + float(dz)
                    

                elif dx is not None and dy is not None:
                    try:
                        dx = float(dx)
                        dy = float(dy)
                        dz = float(dz)
                    except (ValueError, TypeError):
                        return "error", "Direction vector components (dx, dy, dz) must be valid numbers"

                    vector_length = euclidean_distance((dx, dy, dz), (0.0, 0.0, 0.0))
                    if vector_length == 0:
                        return "error", "Direction vector cannot be zero"

                    target_x = current_x + distance * (dx / vector_length)
                    target_y = current_y + distance * (dy / vector_length)
                    target_z = current_z + distance * (dz / vector_length)

                elif azimuth is not None:
                    try:
                        azimuth = float(azimuth)
                        elevation = float(elevation)
                    except (ValueError, TypeError):
                        return "error", "Azimuth and elevation must be valid numbers"

                    azimuth_rad = math.radians(azimuth)
                    elevation_rad = math.radians(elevation)

                    horizontal_distance = distance * math.cos(elevation_rad)
                    target_x = current_x + horizontal_distance * math.sin(azimuth_rad)
                    target_y = current_y + horizontal_distance * math.cos(azimuth_rad)
                    target_z = current_z + distance * math.sin(elevation_rad)

                else:
                    return "error", "Direction must be specified using 'heading', 'dx/dy/dz', or 'azimuth/elevation'"

                # Create waypoint
                target_position = {"x": target_x, "y": target_y, "z": target_z}
                
                # Execute movement
                status, result = self._validate_and_execute_path(drone, [target_position], "move_towards")
                
                if status == "error":
                    if "Waypoint 1" in str(result):
                        result = str(result).replace("Waypoint 1", "Target position")
                    return status, result

                # Build response message
                message = f"Drone moved {distance:.2f}m to position ({target_x:.2f}, {target_y:.2f}, {target_z:.2f}), heading: {result['final_heading']:.1f}° (battery: -{result['battery_consumed']:.1f}%/-{result['battery_consumed_mah']:.0f}mAh, remaining: {drone.battery_level:.1f}%/{drone.battery_volume:.0f}mAh)"
                
                targets_reached = result["targets_reached"]
                if targets_reached:
                    # Deduplicate targets
                    seen_ids = set()
                    unique_targets = []
                    for t in targets_reached:
                        if t["id"] not in seen_ids:
                            unique_targets.append(t)
                            seen_ids.add(t["id"])
                    
                    target_names = ", ".join([t["name"] for t in unique_targets])
                    message += f" - Reached target(s): {target_names}"

                return "success", message
            return "error", f"Cannot move from current status: {drone.status}"

        elif command == DroneCommand.MOVE_ALONG_PATH:
            if drone.status in [DroneStatus.HOVERING, DroneStatus.FLYING, DroneStatus.MOVING]:
                # Get waypoints from parameters
                waypoints = parameters.get("waypoints")
                allow_partial_move = parameters.get("allow_partial_move", False)
                if not waypoints:
                    return "error", "Missing waypoints parameter"

                if not isinstance(waypoints, list) or len(waypoints) < 1:
                    return "error", "Waypoints must be a list with at least 1 point"

                if isinstance(allow_partial_move, str):
                    allow_partial_move = allow_partial_move.strip().lower() in ("1", "true", "yes", "on")
                else:
                    allow_partial_move = bool(allow_partial_move)

                # Execute movement
                status, result = self._validate_and_execute_path(
                    drone,
                    waypoints,
                    "move_along_path",
                    allow_partial_move=allow_partial_move,
                )

                if status == "error":
                    return status, result

                # Build response message
                if result.get("partial_move"):
                    message = (
                        f"Drone partially completed path with {result['completed_waypoints']} of "
                        f"{result['requested_waypoints']} waypoints before stopping"
                    )
                    if result.get("blocked_waypoint_index") is not None:
                        message += f" at waypoint {result['blocked_waypoint_index']}"
                    if result.get("blocked_reason"):
                        message += f" ({result['blocked_reason']})"
                else:
                    message = f"Drone completed path with {len(waypoints)} waypoints"

                message += (
                    f" (total distance: {result['distance']:.2f}m, battery: "
                    f"-{result['battery_consumed']:.1f}%/-{result['battery_consumed_mah']:.0f}mAh, "
                    f"remaining: {drone.battery_level:.1f}%/{drone.battery_volume:.0f}mAh)"
                )

                targets_reached = result["targets_reached"]
                if targets_reached:
                    # Deduplicate targets
                    seen_ids = set()
                    unique_targets = []
                    for t in targets_reached:
                        if t["id"] not in seen_ids:
                            unique_targets.append(t)
                            seen_ids.add(t["id"])
                    
                    target_names = ", ".join([t["name"] for t in unique_targets])
                    message += f" - Reached target(s): {target_names}"

                metadata = {
                    "successful_points_count": result["successful_points_count"],
                    "successful_points": result["successful_points"],
                    "unsuccessful_points_count": result["unsuccessful_points_count"],
                    "unsuccessful_points": result["unsuccessful_points"],
                }
                return ("partial_success" if result.get("partial_move") else "success"), message, metadata
            return "error", f"Cannot move along path from current status: {drone.status}"
            
        elif command == DroneCommand.CHANGE_ALTITUDE:
            if drone.status in [DroneStatus.HOVERING, DroneStatus.FLYING, DroneStatus.MOVING]:
                # Get altitude parameter
                altitude = parameters.get("altitude")
                
                # Validate altitude parameter
                if altitude is None:
                    return "error", "Altitude parameter is required"
                
                # Convert to float if needed
                try:
                    altitude = float(altitude)
                except (ValueError, TypeError):
                    return "error", "Altitude must be a valid number"
                
                # Validate altitude range
                if altitude > drone.max_altitude:
                    return "error", f"Requested altitude exceeds maximum ({drone.max_altitude}m)"
                if altitude < 0:
                    return "error", "Altitude cannot be negative"
                
                # Check for obstacle collision at new altitude
                current_x = drone.position["x"]
                current_y = drone.position["y"]
                target_position = {"x": current_x, "y": current_y, "z": altitude}
                
                collision_result = self._check_position_collision(target_position)
                if collision_result:
                    return "error", f"Cannot change altitude: {collision_result}"
                
                # Check for obstacle collision along the vertical path
                current_position = drone.position
                path_collision_result = self._check_path_collision(current_position, target_position)
                if path_collision_result:
                    return "error", f"Cannot change altitude along path: {path_collision_result}"
                
                # Save start position for battery calculation
                start_position = current_position
                end_position = target_position

                # Update drone status and position
                drone.update_status(DroneStatus.MOVING)
                drone.update_position(current_x, current_y, altitude)
                drone.update_status(DroneStatus.HOVERING)

                # Check target reaches along path
                self._check_and_record_target_reaches_along_path(drone, start_position, end_position)

                # Consume battery (vertical movement is expensive)
                battery_cost_percent, battery_cost_mah = self._consume_battery(drone, "change_altitude", start_position, end_position)

                # Record waypoint reached
                drone.record_history_waypoint(
                    event="change_altitude",
                    start_position=start_position,
                    position=end_position,
                    metadata={
                        "altitude_change": altitude - start_position["z"],
                        "battery_consumed": battery_cost_percent
                    }
                )

                return "success", f"Drone altitude changed to {altitude}m (battery: -{battery_cost_percent:.1f}%/-{battery_cost_mah:.0f}mAh, remaining: {drone.battery_level:.1f}%/{drone.battery_volume:.0f}mAh)"
            return "error", f"Cannot change altitude from current status: {drone.status}"
        
        elif command == DroneCommand.HOVER:
            if drone.status in [DroneStatus.FLYING, DroneStatus.MOVING, DroneStatus.HOVERING]:
                drone.update_status(DroneStatus.HOVERING)
                # Consume minimal battery for hover command
                battery_cost_percent, battery_cost_mah = self._consume_battery(drone, "hover")

                # Get duration from parameters if specified
                duration = parameters.get("duration", 0)

                # Record status event (start and end position are the same for hovering)
                current_pos = drone.position.copy()
                drone.record_history_status(
                    event="hovering",
                    start_position=current_pos,
                    position=current_pos,
                    duration=duration,
                    metadata={
                        "battery_consumed": battery_cost_percent
                    }
                )

                return "success", f"Drone now hovering (battery: -{battery_cost_percent:.1f}%/-{battery_cost_mah:.0f}mAh, remaining: {drone.battery_level:.1f}%/{drone.battery_volume:.0f}mAh)"
            return "error", f"Cannot hover from current status: {drone.status}"

        elif command == DroneCommand.ROTATE:
            if drone.status in [DroneStatus.HOVERING, DroneStatus.FLYING, DroneStatus.MOVING, DroneStatus.IDLE, DroneStatus.READY]:
                # Get heading parameter
                heading = parameters.get("heading")

                if heading is None:
                    return "error", "Heading parameter is required"

                try:
                    heading = float(heading)
                except (ValueError, TypeError):
                    return "error", "Heading must be a valid number"

                # Normalize heading to 0-359 range
                heading = heading % 360.0

                # Update drone heading
                old_heading = drone.heading
                drone.update_heading(heading)

                # Consume battery for rotation
                battery_cost_percent, battery_cost_mah = self._consume_battery(drone, "rotate")

                # Record status event (start and end position are the same for rotation)
                current_pos = drone.position.copy()
                drone.record_history_status(
                    event="rotate",
                    start_position=current_pos,
                    position=current_pos,
                    metadata={
                        "old_heading": old_heading,
                        "new_heading": heading,
                        "battery_consumed": battery_cost_percent
                    }
                )

                return "success", f"Drone heading set to {heading:.1f}° (battery: -{battery_cost_percent:.1f}%/-{battery_cost_mah:.0f}mAh, remaining: {drone.battery_level:.1f}%/{drone.battery_volume:.0f}mAh)"
            return "error", f"Cannot rotate from current status: {drone.status}"

        elif command == DroneCommand.EMERGENCY_STOP:
            # Emergency stop - immediately land the drone
            start_altitude = drone.position["z"]
            drone.update_status(DroneStatus.LANDING)
            drone.update_position(drone.position["x"], drone.position["y"], 0.0)

            # Record emergency stop event
            start_pos = {"x": drone.position["x"], "y": drone.position["y"], "z": start_altitude}
            end_pos = drone.position.copy()
            drone.record_history_status(
                event="emergency_stop",
                start_position=start_pos,
                position=end_pos,
                metadata={
                    "altitude_descended": start_altitude,
                    "battery_level": drone.battery_level,
                    "is_emergency_battery": drone.is_emergency_battery()
                }
            )

            if drone.is_emergency_battery():
                drone.update_status(DroneStatus.EMERGENCY)
                return "success", "Emergency landing executed - drone in emergency state due to low battery"
            else:
                drone.update_status(DroneStatus.IDLE)
                return "success", "Emergency landing executed"
        
        elif command == DroneCommand.RETURN_HOME:
            if drone.status in [DroneStatus.HOVERING, DroneStatus.FLYING, DroneStatus.MOVING]:
                start_position = drone.position.copy()
                end_position = drone.home_position.copy()

                drone.update_status(DroneStatus.MOVING)
                drone.update_position(
                    drone.home_position["x"],
                    drone.home_position["y"],
                    drone.home_position["z"]
                )
                drone.update_status(DroneStatus.HOVERING)

                # Check target reaches along path
                self._check_and_record_target_reaches_along_path(drone, start_position, end_position)

                # Consume battery for return trip
                battery_cost_percent, battery_cost_mah = self._consume_battery(drone, "return_home", start_position, end_position)

                # Record waypoint reached
                drone.record_history_waypoint(
                    event="return_home",
                    start_position=start_position,
                    position=end_position,
                    metadata={
                        "distance_traveled": euclidean_distance(start_position, end_position),
                        "battery_consumed": battery_cost_percent
                    }
                )

                return "success", f"Drone returned to home position (battery: -{battery_cost_percent:.1f}%/-{battery_cost_mah:.0f}mAh, remaining: {drone.battery_level:.1f}%/{drone.battery_volume:.0f}mAh)"
            return "error", f"Cannot return home from current status: {drone.status}"

        elif command == DroneCommand.SET_HOME:
            drone.set_home_position()
            # Set home doesn't consume battery (just updating memory)
            battery_cost_percent, battery_cost_mah = self._consume_battery(drone, "set_home")
            return "success", f"Home position set to current position ({drone.position['x']:.1f}, {drone.position['y']:.1f}, {drone.position['z']:.1f})"

        elif command == DroneCommand.CALIBRATE:
            if drone.status in [DroneStatus.IDLE, DroneStatus.READY]:
                drone.update_status(DroneStatus.READY)
                # Consume battery for calibration
                battery_cost_percent, battery_cost_mah = self._consume_battery(drone, "calibrate")

                # Record status event (start and end position are the same for calibration)
                current_pos = drone.position.copy()
                drone.record_history_status(
                    event="calibrate",
                    start_position=current_pos,
                    position=current_pos,
                    metadata={
                        "battery_consumed": battery_cost_percent
                    }
                )

                return "success", f"Drone calibrated successfully (battery: -{battery_cost_percent:.1f}%/-{battery_cost_mah:.0f}mAh, remaining: {drone.battery_level:.1f}%/{drone.battery_volume:.0f}mAh)"
            return "error", f"Cannot calibrate from current status: {drone.status}"

        elif command == DroneCommand.TAKE_PHOTO:
            # Check if drone is in a valid state for taking photos
            if drone.status in [DroneStatus.HOVERING, DroneStatus.FLYING]:
                # Simulate taking a photo - in a real system, this would trigger camera hardware
                photo_id = generate_random_id()  # Generate a short ID for the photo
                # Consume battery for taking photo
                battery_cost_percent, battery_cost_mah = self._consume_battery(drone, "take_photo")

                # Record status event (start and end position are the same for taking photo)
                current_pos = drone.position.copy()
                drone.record_history_status(
                    event="take_photo",
                    start_position=current_pos,
                    position=current_pos,
                    metadata={
                        "photo_id": photo_id,
                        "battery_consumed": battery_cost_percent
                    }
                )

                return "success", f"Photo taken successfully. Photo ID: {photo_id} (battery: -{battery_cost_percent:.1f}%/-{battery_cost_mah:.0f}mAh, remaining: {drone.battery_level:.1f}%/{drone.battery_volume:.0f}mAh)"
            return "error", f"Cannot take photo from current status: {drone.status}. Drone must be hovering or flying."

        elif command == DroneCommand.SEND_MESSAGE:
            # Check if target drone ID is provided
            if "target_drone_id" not in parameters:
                return "error", "Missing target_drone_id parameter"
            if "message" not in parameters:
                return "error", "Missing message parameter"

            target_drone_id = parameters["target_drone_id"]
            message_content = parameters["message"]

            # Check if target drone exists
            if target_drone_id not in self.drones:
                return "error", f"Target drone with ID {target_drone_id} not found"

            # Check if drone is in a valid state for sending messages
            if drone.status != DroneStatus.OFFLINE:
                # In a real system, this would use communication hardware
                # Consume battery for sending message
                battery_cost_percent, battery_cost_mah = self._consume_battery(drone, "send_message")

                # Record status event (start and end position are the same for sending message)
                current_pos = drone.position.copy()
                drone.record_history_status(
                    event="send_message",
                    start_position=current_pos,
                    position=current_pos,
                    metadata={
                        "target_drone_id": target_drone_id,
                        "message": message_content,
                        "battery_consumed": battery_cost_percent
                    }
                )

                return "success", f"Message sent to drone {target_drone_id}: '{message_content}' (battery: -{battery_cost_percent:.1f}%/-{battery_cost_mah:.0f}mAh, remaining: {drone.battery_level:.1f}%/{drone.battery_volume:.0f}mAh)"
            return "error", f"Cannot send message from current status: {drone.status}"
        
        elif command == DroneCommand.BROADCAST:
            # Check if message is provided
            if "message" not in parameters:
                return "error", "Missing message parameter"

            message_content = parameters["message"]

            # Check if drone is in a valid state for broadcasting
            if drone.status != DroneStatus.OFFLINE:
                # Count how many drones would receive the message (excluding self)
                recipient_count = len(self.drones) - 1

                if recipient_count <= 0:
                    return "success", "Broadcast sent, but no other drones are available to receive it"

                # Consume battery for broadcasting
                battery_cost_percent, battery_cost_mah = self._consume_battery(drone, "broadcast")

                # Record status event (start and end position are the same for broadcast)
                current_pos = drone.position.copy()
                drone.record_history_status(
                    event="broadcast",
                    start_position=current_pos,
                    position=current_pos,
                    metadata={
                        "message": message_content,
                        "recipient_count": recipient_count,
                        "battery_consumed": battery_cost_percent
                    }
                )

                return "success", f"Broadcast message sent to {recipient_count} drones: '{message_content}' (battery: -{battery_cost_percent:.1f}%/-{battery_cost_mah:.0f}mAh, remaining: {drone.battery_level:.1f}%/{drone.battery_volume:.0f}mAh)"
            return "error", f"Cannot broadcast from current status: {drone.status}"
        
        elif command == DroneCommand.CHARGE:
            # Check if drone is in IDLE state (landed) for charging
            if drone.status != DroneStatus.IDLE:
                return "error", "Drone must be in idle state (landed) to charge battery"
            
            # Check if drone is at a valid charging station
            is_at_charging_station = False
            if self.target_controller:
                for target in self.target_controller.targets.values():
                    if target.can_charge_drone(drone.position):
                        is_at_charging_station = True
                        break
            
            if not is_at_charging_station:
                return "error", "Drone is not at a valid charging station"
            
            # Get charge amount from parameters
            charge_amount = parameters.get("charge_amount")
            if charge_amount is None:
                return "error", "Missing charge_amount parameter"
            
            # Validate charge amount
            try:
                charge_amount = float(charge_amount)
            except (ValueError, TypeError):
                return "error", "Charge amount must be a valid number"
            
            if charge_amount < 0.1 or charge_amount > 100.0:
                return "error", "Charge amount must be between 0.1 and 100.0"
            
            # Calculate new battery level (instant charging)
            current_battery_percent = drone.battery_level
            current_battery_mah = drone.battery_volume
            new_battery_level = min(100.0, current_battery_percent + charge_amount)

            # Update battery level instantly
            drone.update_battery(new_battery_level)

            # Calculate actual charge added
            actual_charge_percent = new_battery_level - current_battery_percent
            actual_charge_mah = drone.battery_volume - current_battery_mah

            # Record status event (start and end position are the same for charging)
            current_pos = drone.position.copy()
            drone.record_history_status(
                event="charging",
                start_position=current_pos,
                position=current_pos,
                metadata={
                    "charge_amount": actual_charge_percent,
                    "battery_before": current_battery_percent,
                    "battery_after": drone.battery_level
                }
            )

            return "success", f"Battery instantly charged by +{actual_charge_percent:.1f}%/+{actual_charge_mah:.0f}mAh (from {current_battery_percent:.1f}%/{current_battery_mah:.0f}mAh to {drone.battery_level:.1f}%/{drone.battery_volume:.0f}mAh)"
        
        else:
            return "error", f"Unknown command: {command}"
    
    def get_drone_commands(self, drone_id: str) -> List[Dict]:
        """Get command history for a specific drone"""
        if drone_id not in self.drones:
            raise KeyError(f"Drone with ID {drone_id} not found")
        
        # Retrieve from session command history
        session = self._get_current_session_ref()
        if session is not None:
            return [cmd for cmd in session.command_history if cmd.get("drone_id") == drone_id]
        
        return []
    
    def get_command(self, command_id: str) -> Optional[Dict]:
        """Get a specific command by ID"""
        return self.commands.get(command_id)
    
    def delete_drone(self, drone_id: str) -> bool:
        """Delete a drone from the system"""
        if drone_id in self.drones:
            del self.drones[drone_id]
            return True
        return False
    
    def update_drone_simulation(self) -> None:
        """Update the simulated drones (called periodically)"""
        for drone in self.drones.values():
            if drone.status != DroneStatus.OFFLINE:
                # Track if drone is charging this update cycle
                is_charging = False

                # Check for automatic charging at waypoint targets
                # Only charge when drone is landed or idle (not hovering in air)
                if drone.status in [DroneStatus.IDLE, DroneStatus.READY] and self.target_controller:
                    # Check if drone is within any waypoint target's radius
                    for target in self.target_controller.targets.values():
                        if target.can_charge_drone(drone.position):
                            # Automatically charge battery to 100% instantly
                            if drone.battery_level < 100.0:
                                charge_amount = target.get_charge_amount()
                                old_battery = drone.battery_level
                                old_volume = drone.battery_volume
                                new_battery_level = min(100.0, drone.battery_level + charge_amount)
                                drone.update_battery(new_battery_level)

                                # Log the automatic charging event
                                charge_added_percent = drone.battery_level - old_battery
                                charge_added_mah = drone.battery_volume - old_volume
                                print(f"[AUTO-CHARGE] Drone {drone.name} ({drone.id}) automatically charged at waypoint '{target.name}': +{charge_added_percent:.1f}%/+{charge_added_mah:.0f}mAh (from {old_battery:.1f}% to {drone.battery_level:.1f}%)")

                                # Record auto-charging event in history (start and end position are the same)
                                current_pos = drone.position.copy()
                                drone.record_history_status(
                                    event="auto_charging",
                                    start_position=current_pos,
                                    position=current_pos,
                                    metadata={
                                        "waypoint_id": target.id,
                                        "waypoint_name": target.name,
                                        "charge_amount": charge_added_percent,
                                        "battery_before": old_battery,
                                        "battery_after": drone.battery_level
                                    }
                                )

                                is_charging = True
                            break  # Only charge from one waypoint at a time

                # Simulate battery drain (skip if currently charging)
                if not is_charging:
                    if drone.status in [DroneStatus.FLYING, DroneStatus.MOVING, DroneStatus.HOVERING]:
                        battery_drain = 0.05  # Higher drain when flying
                    else:
                        battery_drain = 0.01  # Lower drain when on ground

                    drone.update_battery(drone.battery_level - battery_drain)

                # Emergency landing if battery too low
                if drone.battery_level < 5.0 and drone.status in [
                    DroneStatus.FLYING, DroneStatus.MOVING, DroneStatus.HOVERING
                ]:
                    self.send_command(
                        drone_id=drone.id,
                        command=DroneCommand.EMERGENCY_STOP,
                        parameters={}
                    )
    
    def _check_position_collision(self, position: Dict[str, float]) -> Optional[str]:
        """Check if a position collides with any obstacle"""
        if not self.obstacle_controller:
            return None

        # Check collision with all obstacles
        collision_result = self.obstacle_controller.check_point_collision(
            position["x"], position["y"], position.get("z", 0.0), margin=0.0
        )

        if collision_result["result"]:
            # Get the first obstacle from the list
            first_obstacle = collision_result["inside_obstacles"][0]
            return f"Position conflicts with {first_obstacle['type']} obstacle '{first_obstacle['name']}'"

        return None
    
    def _check_path_collision(self, start_pos: Dict[str, float], end_pos: Dict[str, float]) -> Optional[str]:
        """Check if a path between two positions collides with any obstacle"""
        if not self.obstacle_controller:
            return None
        
        # Check path collision with all obstacles (no safety margin)
        collision_result = self.obstacle_controller.check_path_collision(
            start_pos["x"], start_pos["y"], end_pos["x"], end_pos["y"],
            start_pos["z"], end_pos["z"],
            safety_margin=0.0
        )
        
        if collision_result["collision"]:
            obstacle_info = collision_result["obstacle"]
            return f"Flight path intersects with {obstacle_info['type']} obstacle '{obstacle_info['name']}'"
        
        return None
