from enum import Enum
from typing import Any, Dict, List, Mapping, Optional
import time

from config.util import (
    distance as euclidean_distance,
    generate_random_id,
    is_point_in_polygon,
    validate_polygon_vertices,
    normalize_polygon_vertices,
)


class TargetType(str, Enum):
    """Enum representing the possible types of targets"""
    FIXED = "fixed"              # Fixed point with radius (can also be points of interest)
    MOVING = "moving"            # Moving target with velocity and optional path
    WAYPOINT = "waypoint"        # Charging station with radius
    CIRCLE = "circle"            # Geometric circle target with radius
    POLYGON = "polygon"          # Geometric polygon target with vertices


class MovementMode(str, Enum):
    """Enum representing moving-target runtime movement modes."""
    VELOCITY = "velocity"
    PATH = "path"
    STATIONARY = "stationary"


class Target:
    """Class representing a target in the system"""
    
    def __init__(
        self,
        name: str,
        target_type: TargetType,
        position: Dict[str, float],
        description: str = "",
        radius: Optional[float] = None,
        vertices: Optional[List[Dict[str, float]]] = None,
        velocity: Optional[Dict[str, float]] = None,
        moving_path: Optional[List[Dict[str, float]]] = None,
        moving_duration: Optional[float] = None,
        charge_amount: Optional[float] = None,
        target_id: Optional[str] = None,
        created_at: Optional[float] = None,
        last_updated: Optional[float] = None,
        current_path_index: Optional[int] = None,
        path_direction: Optional[int] = None,
        time_in_direction: Optional[float] = None,
        movement_mode: Optional[MovementMode | str] = None,
        last_motion_update: Optional[float] = None,
        last_tracked_at: Optional[float] = None,
        is_reached: bool = False,
        reached_by: Optional[List[str]] = None,
    ):
        self.id = target_id or generate_random_id()
        self.name = name
        self.type = target_type
        self.description = description

        self.vertices = self._copy_vertices(vertices)

        # For polygon targets, calculate centroid from vertices if vertices are provided
        if target_type == TargetType.POLYGON and self.vertices and len(self.vertices) >= 3:
            self.position = self._calculate_polygon_centroid(self.vertices)
        else:
            self.position = self._normalize_position(position)

        self.radius = radius if radius is not None else 1.0

        if target_type == TargetType.MOVING:
            self.velocity = self._copy_vector(velocity) or {"x": 0.0, "y": 0.0, "z": 0.0}
            self.moving_path = self._copy_path(moving_path) or []
            self.moving_duration = moving_duration if moving_duration is not None else 10.0  # Default 10 seconds
            if current_path_index is None:
                self.current_path_index = 0
            else:
                max_index = max(0, len(self.moving_path) - 1)
                self.current_path_index = max(0, min(current_path_index, max_index)) if self.moving_path else 0
            # Track direction for path-based movement: 1 = forward, -1 = backward
            self.path_direction = path_direction if path_direction is not None else 1
            # Track elapsed time in current direction for velocity-based movement
            self.time_in_direction = time_in_direction if time_in_direction is not None else 0.0
            # Calculate speed for path-based movement (auto-calculated from path length and duration)
            resolved_mode = self._determine_movement_mode()
            self.movement_mode = self._coerce_movement_mode(movement_mode) or resolved_mode
            self.calculated_speed = self._calculate_speed_for_path(self.movement_mode)
            self.last_motion_update = last_motion_update
            self.last_tracked_at = float(last_tracked_at) if last_tracked_at is not None else None
        else:
            self.velocity = self._copy_vector(velocity)
            self.moving_path = self._copy_path(moving_path)
            self.moving_duration = None
            self.current_path_index = None
            self.path_direction = None
            self.time_in_direction = None
            self.movement_mode = None
            self.calculated_speed = None
            self.last_motion_update = None
            self.last_tracked_at = None
        
        if target_type == TargetType.WAYPOINT:
            self.charge_amount = charge_amount if charge_amount is not None else 25.0
        else:
            self.charge_amount = charge_amount

        now = time.time()
        self.created_at = created_at or now
        self.last_updated = last_updated or now

        # Tracking whether target has been reached
        self.is_reached = is_reached
        self.reached_by: List[str] = reached_by if reached_by is not None else []

        self._validate_target()

    @classmethod
    def _copy_vertices(cls, vertices: Optional[List[Mapping[str, Any]]]) -> Optional[List[Dict[str, float]]]:
        if vertices is None:
            return None
        normalized = [cls._normalize_position(vertex) for vertex in vertices]
        return normalize_polygon_vertices(normalized)

    @staticmethod
    def _copy_vector(vector: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        if vector is None:
            return None
        return {axis: float(value) for axis, value in vector.items()}

    @classmethod
    def _copy_path(cls, points: Optional[List[Mapping[str, Any]]]) -> Optional[List[Dict[str, float]]]:
        if points is None:
            return None
        return [cls._normalize_position(point) for point in points]

    @staticmethod
    def _coerce_movement_mode(value: Optional["MovementMode | str"]) -> Optional["MovementMode"]:
        if value is None:
            return None
        if isinstance(value, MovementMode):
            return value
        try:
            return MovementMode(str(value))
        except ValueError:
            return None

    def _has_velocity(self) -> bool:
        """Check if velocity is non-zero (at least one component is non-zero)"""
        if not self.velocity:
            return False
        return (abs(self.velocity.get("x", 0.0)) > 1e-9 or
                abs(self.velocity.get("y", 0.0)) > 1e-9 or
                abs(self.velocity.get("z", 0.0)) > 1e-9)

    def _calculate_path_length(self) -> float:
        """Calculate the total length of the moving_path"""
        if not self.moving_path or len(self.moving_path) < 2:
            return 0.0

        total_length = 0.0
        for i in range(len(self.moving_path) - 1):
            segment_length = euclidean_distance(self.moving_path[i], self.moving_path[i + 1])
            total_length += segment_length

        return total_length

    def _determine_movement_mode(self) -> MovementMode:
        """Determine which movement mode to use based on priority

        Returns:
            "velocity" - Use velocity-based movement
            "path" - Use path-based movement with auto-calculated speed
            "stationary" - No movement
        """
        # Priority 1: Velocity-based movement
        if self._has_velocity() and self.moving_duration > 0:
            return MovementMode.VELOCITY

        # Priority 2: Path-based movement
        if self.moving_path and len(self.moving_path) >= 2 and self.moving_duration > 0:
            return MovementMode.PATH

        # Priority 3: Stationary
        return MovementMode.STATIONARY

    def _calculate_speed_for_path(self, movement_mode: Optional[MovementMode] = None) -> Optional[float]:
        """Calculate speed for path-based movement

        Returns:
            Speed in m/s required to complete the path in moving_duration seconds,
            or None if not in path-based mode
        """
        # Only calculate for path-based mode
        resolved_mode = movement_mode or self._determine_movement_mode()
        if resolved_mode != MovementMode.PATH:
            return None

        path_length = self._calculate_path_length()
        if path_length > 0 and self.moving_duration > 0:
            return path_length / self.moving_duration

        return None

    @staticmethod
    def _normalize_position(position: Mapping[str, Any]) -> Dict[str, float]:
        if "x" not in position or "y" not in position:
            raise ValueError("Position must include 'x' and 'y' coordinates")
        return {
            "x": float(position["x"]),
            "y": float(position["y"]),
            "z": float(position.get("z", 0.0)),
        }

    @staticmethod
    def _calculate_polygon_centroid(vertices: List[Dict[str, float]]) -> Dict[str, float]:
        """Calculate the centroid (center) of a polygon from its vertices"""
        if not vertices or len(vertices) < 3:
            raise ValueError("Need at least 3 vertices to calculate polygon centroid")

        # Calculate centroid as average of all vertices
        x_sum = sum(v["x"] for v in vertices)
        y_sum = sum(v["y"] for v in vertices)
        n = len(vertices)

        # Round to integers
        center_x = round(x_sum / n)
        center_y = round(y_sum / n)

        # Z coordinate: use the first vertex's z if available, otherwise 0
        center_z = vertices[0].get("z", 0.0) if vertices else 0.0

        return {"x": float(center_x), "y": float(center_y), "z": float(center_z)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Target":
        if "name" not in data:
            raise ValueError("Missing required field: name")
        if "type" not in data:
            raise ValueError("Missing required field: type")
        if "position" not in data:
            raise ValueError("Missing required field: position")

        target_type = data["type"]
        if not isinstance(target_type, TargetType):
            try:
                target_type = TargetType(target_type)
            except ValueError as exc:
                raise ValueError(f"Unsupported target type: {data['type']}") from exc

        return cls(
            name=data["name"],
            target_type=target_type,
            position=data["position"],
            description=data.get("description", ""),
            radius=data.get("radius"),
            vertices=data.get("vertices"),
            velocity=data.get("velocity"),
            moving_path=data.get("moving_path"),
            moving_duration=data.get("moving_duration"),
            charge_amount=data.get("charge_amount"),
            target_id=data.get("id"),
            created_at=data.get("created_at"),
            last_updated=data.get("last_updated"),
            current_path_index=data.get("current_path_index"),
            path_direction=data.get("path_direction"),
            time_in_direction=data.get("time_in_direction"),
            movement_mode=data.get("movement_mode"),
            last_motion_update=data.get("last_motion_update"),
            last_tracked_at=data.get("last_tracked_at"),
            is_reached=data.get("is_reached", False),
            reached_by=data.get("reached_by"),
        )

    def apply_update(self, updates: Mapping[str, Any]) -> None:
        if "type" in updates:
            new_type = updates["type"]
            if not isinstance(new_type, TargetType):
                try:
                    new_type = TargetType(new_type)
                except ValueError as exc:
                    raise ValueError(f"Unsupported target type: {updates['type']}") from exc
            if new_type != self.type:
                raise ValueError("Changing target type is not supported")

        if "name" in updates:
            self.name = updates["name"]

        if "description" in updates:
            self.description = updates["description"]

        if "radius" in updates:
            self.radius = float(updates["radius"])

        if "charge_amount" in updates:
            if self.type != TargetType.WAYPOINT:
                raise ValueError("charge_amount is only valid for waypoint targets")
            self.charge_amount = float(updates["charge_amount"])

        if "position" in updates:
            pos = updates["position"] or {}
            x = float(pos.get("x", self.position.get("x", 0.0)))
            y = float(pos.get("y", self.position.get("y", 0.0)))
            z = float(pos.get("z", self.position.get("z", 0.0)))
            self.update_position(x, y, z)

        if "velocity" in updates:
            if self.type != TargetType.MOVING:
                raise ValueError("velocity can only be updated for moving targets")
            vel = updates["velocity"] or {}
            vx = float(vel.get("x", self.velocity.get("x", 0.0) if self.velocity else 0.0))
            vy = float(vel.get("y", self.velocity.get("y", 0.0) if self.velocity else 0.0))
            vz = float(vel.get("z", self.velocity.get("z", 0.0) if self.velocity else 0.0))
            self.update_velocity(vx, vy, vz)

        if "moving_path" in updates:
            if self.type != TargetType.MOVING:
                raise ValueError("moving_path can only be set for moving targets")
            path = updates["moving_path"] or []
            self.set_moving_path(path)

        if "moving_duration" in updates:
            if self.type != TargetType.MOVING:
                raise ValueError("moving_duration can only be set for moving targets")
            self.moving_duration = float(updates["moving_duration"])
            self._refresh_motion_state()

        if "vertices" in updates:
            self.vertices = self._copy_vertices(updates["vertices"])
            self._validate_polygon_vertices()
            # Recalculate centroid for polygon targets
            if self.type == TargetType.POLYGON and self.vertices and len(self.vertices) >= 3:
                self.position = self._calculate_polygon_centroid(self.vertices)

        self._validate_target()
        self.last_updated = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert target object to dictionary for API responses"""
        result = {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "position": self.position,
            "description": self.description,
            "radius": self.radius,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "velocity": self.velocity,
            "moving_path": self.moving_path,
            "moving_duration": self.moving_duration,
            "current_path_index": self.current_path_index,
            "path_direction": self.path_direction,
            "time_in_direction": self.time_in_direction,
            "movement_mode": self.movement_mode.value if isinstance(self.movement_mode, MovementMode) else self.movement_mode,
            "calculated_speed": self.calculated_speed,
            "last_motion_update": self.last_motion_update,
            "last_tracked_at": self.last_tracked_at,
            "charge_amount": self.charge_amount,
            "is_reached": self.is_reached,
            "reached_by": self.reached_by
        }
        if self.vertices is not None:
            result["vertices"] = self.vertices

        return result

    def to_geometry(self):
        try:
            from shapely.geometry import Point, Polygon

            # For point-like targets with radius, create a circle
            if self.type in [TargetType.FIXED, TargetType.WAYPOINT,
                           TargetType.MOVING, TargetType.CIRCLE]:
                center = Point(float(self.position["x"]),
                             float(self.position["y"]))
                return center.buffer(float(self.radius))

            # For polygon targets, create polygon from vertices
            if self.type == TargetType.POLYGON:
                if not self.vertices or len(self.vertices) < 3:
                    return None
                coords = [(float(v["x"]), float(v["y"]))
                         for v in self.vertices]
                # Close the polygon if not already closed
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                return Polygon(coords)
        except Exception:
            return None

        return None

    def update_position(self, x: float, y: float, z: float) -> None:
        """Update the position of the target

        For polygon targets, this moves all vertices so that the centroid
        is at the new position (x, y, z).
        """
        if self.type == TargetType.POLYGON and self.vertices:
            # Calculate offset from current centroid to new position
            dx = x - self.position["x"]
            dy = y - self.position["y"]
            dz = z - self.position.get("z", 0.0)

            # Update all vertices by the same offset
            for vertex in self.vertices:
                vertex["x"] += dx
                vertex["y"] += dy
                if "z" in vertex:
                    vertex["z"] += dz

            # Update position to new centroid (rounded to integers)
            self.position = {"x": round(x), "y": round(y), "z": z}
        else:
            self.position = {
                "x": float(x),
                "y": float(y),
                "z": float(z),
            }
        self.last_updated = time.time()
    
    def update_velocity(self, vx: float, vy: float, vz: float) -> None:
        """Update the velocity of a moving target"""
        if self.type == TargetType.MOVING:
            self.velocity = {
                "x": float(vx),
                "y": float(vy),
                "z": float(vz),
            }
            self._refresh_motion_state()
            self.last_updated = time.time()
    
    def set_moving_path(self, path: List[Dict[str, float]]) -> None:
        """Set the moving path for a moving target"""
        if self.type == TargetType.MOVING:
            self.moving_path = self._copy_path(path) or []
            self.current_path_index = 0
            self.path_direction = 1  # Reset to forward direction
            self.time_in_direction = 0.0  # Reset time counter
            self._refresh_motion_state()
            self.last_updated = time.time()

    def _refresh_motion_state(self) -> None:
        if self.type != TargetType.MOVING:
            return
        self.movement_mode = self._determine_movement_mode()
        self.calculated_speed = self._calculate_speed_for_path(self.movement_mode)
        if self.movement_mode != MovementMode.PATH:
            self.current_path_index = 0
            self.path_direction = 1 if self.path_direction is None else self.path_direction
        if self.movement_mode != MovementMode.VELOCITY:
            self.time_in_direction = 0.0

    def _advance_path_index(self) -> None:
        if not self.moving_path:
            self.current_path_index = 0
            self.path_direction = 1
            return
        self.current_path_index += self.path_direction
        if self.current_path_index >= len(self.moving_path):
            self.current_path_index = len(self.moving_path) - 2
            self.path_direction = -1
        elif self.current_path_index < 0:
            self.current_path_index = 1
            self.path_direction = 1
        self.current_path_index = max(0, min(self.current_path_index, len(self.moving_path) - 1))

    def _move_along_path(self, delta_time: float) -> None:
        if not self.moving_path or len(self.moving_path) < 2:
            return

        remaining_time = max(0.0, float(delta_time))
        speed = self.calculated_speed or 0.0
        if speed <= 0.0:
            return

        max_iterations = max(1, len(self.moving_path) * 4)
        iterations = 0
        epsilon = 1e-9

        while remaining_time > epsilon and iterations < max_iterations:
            target_waypoint = self.moving_path[self.current_path_index]
            distance_to_waypoint = euclidean_distance(target_waypoint, self.position)

            if distance_to_waypoint <= 0.5:
                self.position = target_waypoint.copy()
                self._advance_path_index()
                iterations += 1
                continue

            max_distance = speed * remaining_time
            travel_distance = min(distance_to_waypoint, max_distance)
            if travel_distance <= epsilon:
                break

            dx = target_waypoint["x"] - self.position["x"]
            dy = target_waypoint["y"] - self.position["y"]
            dz = target_waypoint["z"] - self.position["z"]
            dx_norm = dx / distance_to_waypoint
            dy_norm = dy / distance_to_waypoint
            dz_norm = dz / distance_to_waypoint

            self.position["x"] += dx_norm * travel_distance
            self.position["y"] += dy_norm * travel_distance
            self.position["z"] += dz_norm * travel_distance
            remaining_time -= travel_distance / speed

            if abs(travel_distance - distance_to_waypoint) <= 0.5:
                self.position = target_waypoint.copy()
                self._advance_path_index()

            iterations += 1

    def reverse_motion_direction(self) -> None:
        if self.type != TargetType.MOVING:
            return
        if self.movement_mode == MovementMode.VELOCITY and self.velocity:
            self.velocity["x"] *= -1
            self.velocity["y"] *= -1
            self.velocity["z"] *= -1
            self.time_in_direction = 0.0
        elif self.movement_mode == MovementMode.PATH:
            self.path_direction *= -1
            if self.moving_path:
                self.current_path_index = max(0, min(self.current_path_index, len(self.moving_path) - 1))
    
    def update_moving_target(self, delta_time: float) -> None:
        """Update position of moving target based on priority-based movement mode

        Priority-based movement modes:
        1. Velocity-based: If velocity is non-zero and moving_duration > 0
        2. Path-based: If no velocity (or zero) and has path and moving_duration > 0
        3. Stationary: If moving_duration == 0 or neither condition met
        """
        if self.type != TargetType.MOVING:
            return

        # Determine movement mode based on priority
        movement_mode = self._determine_movement_mode()
        self.movement_mode = movement_mode

        if movement_mode == MovementMode.STATIONARY:
            # Target does not move
            return

        elif movement_mode == MovementMode.VELOCITY:
            # PRIORITY 1: Velocity-based movement with time-based ping-pong
            remaining_time = max(0.0, float(delta_time))
            max_iterations = 8
            iterations = 0
            epsilon = 1e-9
            while remaining_time > epsilon and iterations < max_iterations:
                time_until_reverse = max(0.0, self.moving_duration - self.time_in_direction)
                step_time = remaining_time if time_until_reverse <= epsilon else min(remaining_time, time_until_reverse)
                self.position["x"] += self.velocity["x"] * step_time
                self.position["y"] += self.velocity["y"] * step_time
                self.position["z"] += self.velocity["z"] * step_time
                self.time_in_direction += step_time
                remaining_time -= step_time
                if self.time_in_direction + epsilon >= self.moving_duration:
                    self.reverse_motion_direction()
                iterations += 1

        elif movement_mode == MovementMode.PATH:
            self._move_along_path(delta_time)

        self.last_updated = time.time()
        self.last_motion_update = self.last_updated

    def distance_to_position(self, position: Dict[str, float], is_distance_3d: bool = True) -> float:
        geometry = self.to_geometry()

        if geometry is not None:
            from shapely.geometry import Point
            drone_point = Point(position["x"], position["y"])
            dist_2d = geometry.distance(drone_point)

            if not is_distance_3d or self.type in [TargetType.CIRCLE, TargetType.POLYGON]:
                dist_z = 0.0
            else:
                dist_z = abs(position.get("z", 0.0) - self.position.get("z", 0.0))

            return (dist_2d ** 2 + dist_z ** 2) ** 0.5

        if is_distance_3d:
            return euclidean_distance(position, self.position)

        from config.util import distance_2d
        return distance_2d(position, self.position)

    def is_position_within_radius(self, position: Dict[str, float], radius: float, is_distance_3d: bool = True) -> bool:
        return self.distance_to_position(position, is_distance_3d=is_distance_3d) <= float(radius)
    
    def is_drone_in_range(self, drone_position: Dict[str, float], is_distance_3d: bool = True) -> bool:
        """Check if a drone is within the target area.
        - For circle/fixed/waypoint/moving: use spherical radius (3D) or horizontal (2D).
        - For polygon: use 2D point-in-polygon on x,y ignoring z.
        """
        if self.type == TargetType.POLYGON and self.vertices:
            return is_point_in_polygon(drone_position["x"], drone_position["y"], self.vertices)

        if is_distance_3d:
            return euclidean_distance(drone_position, self.position) <= (self.radius or 0.0)
        else:
            from config.util import distance_2d
            return distance_2d(drone_position, self.position) <= (self.radius or 0.0)

    def check_drone_reached(self, drone_id: str, drone_position: Dict[str, float], task_radius: float, is_distance_3d: bool = True) -> bool:
        """Check if a drone has reached the target within its task_radius.
        Updates is_reached and reached_by tracking.

        Args:
            drone_id: The ID of the drone to check
            drone_position: The current position of the drone
            task_radius: The task radius of the drone
            is_distance_3d: Whether to use 3D distance (default: True)

        Returns:
            True if the drone is within task_radius of the target
        """
        # Calculate distance based on target type
        in_range = self.is_position_within_radius(drone_position, task_radius, is_distance_3d=is_distance_3d)

        # Update tracking if drone is in range
        if in_range:
            if drone_id not in self.reached_by:
                self.reached_by.append(drone_id)
                self.is_reached = True
                self.last_updated = time.time()

        return in_range

    def reset_reached_status(self) -> None:
        """Reset the reached status and clear the list of drones that reached this target."""
        self.is_reached = False
        self.reached_by = []
        self.last_updated = time.time()

    def mark_tracked(self, timestamp: Optional[float] = None) -> None:
        if self.type == TargetType.MOVING:
            self.last_tracked_at = float(timestamp) if timestamp is not None else time.time()
            self.last_updated = time.time()
    
    def can_charge_drone(self, drone_position: Dict[str, float]) -> bool:
        """Check if this waypoint can charge a drone at the given position"""
        return (self.type == TargetType.WAYPOINT and 
                self.is_drone_in_range(drone_position))
    
    def get_charge_amount(self) -> float:
        """Get the instant charge amount at this waypoint"""
        if self.type == TargetType.WAYPOINT and self.charge_amount:
            return self.charge_amount
        return 0.0

    def _validate_target(self) -> None:
        if self.radius is None or self.radius < 0:
            raise ValueError("Targets must have a non-negative radius")
        if self.type == TargetType.POLYGON:
            self._validate_polygon_vertices()
        if self.type == TargetType.MOVING:
            if self.velocity is None:
                raise ValueError("Moving targets require a velocity vector")
            if self.moving_duration is not None and self.moving_duration < 0:
                raise ValueError("moving_duration must be non-negative")

            # Validate movement modes
            movement_mode = self._determine_movement_mode()
            if movement_mode == MovementMode.PATH:
                # Path-based mode requires valid path
                if not self.moving_path or len(self.moving_path) < 2:
                    raise ValueError("Path-based movement requires at least 2 waypoints in moving_path")
                if self.moving_duration <= 0:
                    raise ValueError("Path-based movement requires moving_duration > 0")
                self._validate_moving_path()

    def _validate_moving_path(self) -> None:
        if self.type != TargetType.MOVING or not self.moving_path:
            return
        if len(self.moving_path) < 2:
            raise ValueError("moving_path must contain at least 2 waypoints")
        for index in range(len(self.moving_path) - 1):
            if euclidean_distance(self.moving_path[index], self.moving_path[index + 1]) <= 1e-9:
                raise ValueError("moving_path contains degenerate consecutive waypoints")

    def _validate_polygon_vertices(self) -> None:
        if self.type == TargetType.POLYGON:
            is_valid, reason = validate_polygon_vertices(self.vertices)
            if not is_valid:
                raise ValueError(f"Invalid polygon vertices: {reason}")
