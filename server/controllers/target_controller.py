from typing import Dict, List, Any, Optional
import time

from models.target import Target, TargetType, MovementMode
from config.util import distance as euclidean_distance


class TargetController:
    """Controller class for managing targets"""
    
    def __init__(self, obstacle_controller=None):
        self.targets: Dict[str, Target] = {}
        self.obstacle_controller = obstacle_controller
        self.last_update_time = time.time()
    

    
    def add_target(self, target_data: Dict[str, Any]) -> Dict:
        """Add a new target to the system

        Args:
            target_data: Dictionary containing target data with keys:
                - name: Target name (required)
                - type: Target type (required)
                - position: Position dict with x, y, z (required)
                - description: Description string (optional)
                - radius: Radius for circle/waypoint targets (optional, default: 1.0)
                - vertices: List of vertices for polygon targets (optional)
                - velocity: Velocity dict for moving targets (optional)
                - moving_path: Path for moving targets (optional)
                - moving_duration: Duration for movement (optional)
                - charge_amount: Charge amount for waypoint targets (optional)
                - id: Optional ID to preserve when restoring from sessions

        Returns:
            Dict representation of the created target
        """
        # Check for obstacle collision at target position
        position = target_data.get("position")
        if not position:
            raise ValueError("Target position is required")

        collision_result = self._check_position_collision(position)
        if collision_result:
            raise ValueError(f"Cannot place target: {collision_result}")

        self._validate_motion_config(target_data, current_target=None)

        # Create target from dict (preserves ID if provided)
        target = Target.from_dict(target_data)

        self.targets[target.id] = target
        return target.to_dict()
    
    def get_all_targets(self) -> List[Dict]:
        """Get all targets"""
        return [target.to_dict() for target in self.targets.values()]
    
    def get_target(self, target_id: str) -> Optional[Dict]:
        """Get a specific target by ID"""
        if target_id in self.targets:
            return self.targets[target_id].to_dict()
        return None
    
    def get_targets_by_type(self, target_type: TargetType) -> List[Dict]:
        """Get all targets of a specific type"""
        return [target.to_dict() for target in self.targets.values() 
                if target.type == target_type]
    
    def get_waypoints(self) -> List[Dict]:
        """Get all waypoint targets (charging stations)"""
        return self.get_targets_by_type(TargetType.WAYPOINT)
    
    def update_target(self, target_id: str, updates: Dict[str, Any]) -> Optional[Dict]:
        """Update a target's properties"""
        if target_id not in self.targets:
            return None
        
        target = self.targets[target_id]
        payload: Dict[str, Any] = {}
        
        # Update position if provided
        if "position" in updates:
            pos = updates["position"]
            new_position = {
                "x": pos.get("x", target.position["x"]),
                "y": pos.get("y", target.position["y"]),
                "z": pos.get("z", target.position["z"])
            }
            
            # Check for obstacle collision at new position
            collision_result = self._check_position_collision(new_position)
            if collision_result:
                raise ValueError(f"Cannot update target position: {collision_result}")
            
            payload["position"] = new_position
        
        # Update velocity if provided (only for moving targets)
        if "velocity" in updates and target.type == TargetType.MOVING:
            vel = updates["velocity"]
            payload["velocity"] = {
                "x": vel.get("x", target.velocity["x"] if target.velocity else 0.0),
                "y": vel.get("y", target.velocity["y"] if target.velocity else 0.0),
                "z": vel.get("z", target.velocity["z"] if target.velocity else 0.0),
            }
        
        # Update moving path if provided (only for moving targets)
        if "moving_path" in updates and target.type == TargetType.MOVING:
            payload["moving_path"] = updates["moving_path"]

        # Update moving duration if provided (only for moving targets)
        if "moving_duration" in updates and target.type == TargetType.MOVING:
            payload["moving_duration"] = updates["moving_duration"]
        
        # Update charge amount if provided (only for waypoints)
        if "charge_amount" in updates and target.type == TargetType.WAYPOINT:
            payload["charge_amount"] = updates["charge_amount"]
        
        # Update other properties
        if "name" in updates:
            payload["name"] = updates["name"]
        
        if "description" in updates:
            payload["description"] = updates["description"]
        
        if "radius" in updates:
            payload["radius"] = updates["radius"]

        # Update vertices if provided (only meaningful for polygon targets)
        if "vertices" in updates:
            payload["vertices"] = updates["vertices"]

        if payload:
            merged_target_data = target.to_dict()
            merged_target_data.update(payload)
            self._validate_motion_config(merged_target_data, current_target=target)
            target.apply_update(payload)

        return target.to_dict()
    
    def delete_target(self, target_id: str) -> bool:
        """Delete a target"""
        if target_id in self.targets:
            del self.targets[target_id]
            return True
        return False
    
    def update_moving_targets(self) -> None:
        """Update positions of moving targets based on their velocities and paths"""
        current_time = time.time()
        delta_time = current_time - self.last_update_time
        self.last_update_time = current_time
        
        for target in self.targets.values():
            if target.type == TargetType.MOVING:
                # Store old position for collision checking
                old_position = target.position.copy()
                
                # Update target position
                target.update_moving_target(delta_time)
                
                # Check for obstacle collision at new position
                collision_result = self._check_position_collision(target.position)
                if collision_result:
                    # Revert to old position if collision detected
                    target.position = old_position
                    target.reverse_motion_direction()
                    target.last_updated = time.time()
    
    def check_drone_at_waypoint(self, waypoint_id: str, drone_position: Dict[str, float]) -> bool:
        """Check if a drone is within range of a specific waypoint"""
        if waypoint_id in self.targets:
            target = self.targets[waypoint_id]
            if target.type == TargetType.WAYPOINT:
                return target.can_charge_drone(drone_position)
        return False
    
    def get_charge_amount_at_waypoint(self, waypoint_id: str) -> float:
        """Get the instant charge amount of a waypoint"""
        if waypoint_id in self.targets:
            target = self.targets[waypoint_id]
            if target.type == TargetType.WAYPOINT:
                return target.charge_amount or 0.0
        return 0.0
    
    def find_nearest_waypoint(self, position: Dict[str, float]) -> Optional[Dict]:
        """Find the nearest waypoint to a given position"""
        nearest_waypoint = None
        min_distance = float('inf')
        
        for target in self.targets.values():
            if target.type == TargetType.WAYPOINT:
                distance = euclidean_distance(target.position, position)
                
                if distance < min_distance:
                    min_distance = distance
                    nearest_waypoint = target.to_dict()
        
        return nearest_waypoint
    
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

    def _validate_motion_config(self, target_data: Dict[str, Any], current_target: Optional[Target]) -> None:
        target_type = target_data.get("type")
        if isinstance(target_type, str):
            try:
                target_type = TargetType(target_type)
            except ValueError:
                return

        if target_type != TargetType.MOVING:
            return

        velocity = target_data.get("velocity")
        moving_path = target_data.get("moving_path")
        moving_duration = target_data.get("moving_duration")

        if moving_duration is not None and float(moving_duration) < 0:
            raise ValueError("moving_duration must be non-negative")

        probe = Target.from_dict({
            "id": current_target.id if current_target else target_data.get("id"),
            "name": target_data.get("name", current_target.name if current_target else "moving-target"),
            "type": TargetType.MOVING,
            "position": target_data.get("position", current_target.position if current_target else {"x": 0.0, "y": 0.0, "z": 0.0}),
            "description": target_data.get("description", current_target.description if current_target else ""),
            "radius": target_data.get("radius", current_target.radius if current_target else 1.0),
            "velocity": velocity if velocity is not None else (current_target.velocity if current_target else None),
            "moving_path": moving_path if moving_path is not None else (current_target.moving_path if current_target else None),
            "moving_duration": moving_duration if moving_duration is not None else (current_target.moving_duration if current_target else None),
            "current_path_index": target_data.get("current_path_index", current_target.current_path_index if current_target else None),
            "path_direction": target_data.get("path_direction", current_target.path_direction if current_target else None),
            "time_in_direction": target_data.get("time_in_direction", current_target.time_in_direction if current_target else None),
        })

        if probe.movement_mode != MovementMode.PATH:
            return

        for waypoint in probe.moving_path:
            collision_result = self._check_position_collision(waypoint)
            if collision_result:
                raise ValueError(f"moving_path waypoint conflicts with obstacle: {collision_result}")

        if not self.obstacle_controller:
            return

        for start, end in zip(probe.moving_path, probe.moving_path[1:]):
            collision_result = self.obstacle_controller.check_path_collision(
                start["x"],
                start["y"],
                end["x"],
                end["y"],
                start.get("z", 0.0),
                end.get("z", 0.0),
                safety_margin=0.0,
            )
            if collision_result.get("collision"):
                obstacle = collision_result.get("obstacle") or {}
                obstacle_name = obstacle.get("name", "unknown")
                raise ValueError(f"moving_path segment intersects obstacle '{obstacle_name}'")
