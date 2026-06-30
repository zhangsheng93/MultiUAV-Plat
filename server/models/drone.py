from enum import Enum
from typing import Any, Dict, List, Mapping, Optional
import time
import math

from config.util import generate_random_id


class DroneStatus(str, Enum):
    """Enum representing the possible statuses of a drone"""
    IDLE = "idle"              # Drone is on the ground and not active
    READY = "ready"            # Drone is on the ground but ready for takeoff
    TAKING_OFF = "taking_off"  # Drone is in the process of taking off
    FLYING = "flying"          # Drone is in the air and stable
    MOVING = "moving"          # Drone is in the air and moving to a destination
    HOVERING = "hovering"      # Drone is in the air but stationary
    LANDING = "landing"        # Drone is in the process of landing
    EMERGENCY = "emergency"    # Drone is in emergency state due to low battery
    OFFLINE = "offline"        # Drone is not connected or responding


class DroneCommand(str, Enum):
    """Enum representing the possible commands that can be sent to a drone"""
    CONNECT = "connect"            # Connect to the drone
    DISCONNECT = "disconnect"      # Disconnect from the drone
    TAKE_OFF = "take_off"          # Take off from the ground
    LAND = "land"                  # Land on the ground
    MOVE_TO = "move_to"            # Move to a specific position (x, y, z)
    MOVE_TOWARDS = "move_towards"  # Move a certain distance in a specific direction
    MOVE_ALONG_PATH = "move_along_path"  # Move along a path defined by multiple waypoints
    CHANGE_ALTITUDE = "change_altitude"  # Change only the altitude (z position)
    HOVER = "hover"                # Hover in place
    ROTATE = "rotate"              # Rotate to a specific heading
    RETURN_HOME = "return_home"    # Return to home position
    SET_HOME = "set_home"          # Set the home position
    CALIBRATE = "calibrate"        # Calibrate sensors
    TAKE_PHOTO = "take_photo"      # Take a photo with the drone's camera
    SEND_MESSAGE = "send_message"  # Send a message to another drone
    BROADCAST = "broadcast"        # Broadcast a message to all nearby drones
    CHARGE = "charge"              # Charge the drone's battery
    EMERGENCY_STOP = "emergency"   # Emergency stop command


class Drone:
    """Class representing a drone in the system"""
    
    def __init__(
        self,
        name: str,
        model: str,
        max_speed: float,
        max_altitude: float,
        battery_capacity: float,
        perceived_radius: float = 100.0,
        task_radius: float = 20.0,
        drone_id: Optional[str] = None,
        status: Optional[DroneStatus] = None,
        position: Optional[Mapping[str, Any]] = None,
        heading: float = 0.0,
        speed: float = 0.0,
        battery_level: Optional[float] = None,
        battery_volume: Optional[float] = None,
        home_position: Optional[Mapping[str, Any]] = None,
        created_at: Optional[float] = None,
        last_updated: Optional[float] = None,
    ):
        self.id = drone_id or generate_random_id()
        self.name = name
        self.model = model

        self.max_speed = self._positive_float(max_speed, "max_speed")
        self.max_altitude = self._positive_float(max_altitude, "max_altitude")
        self.perceived_radius = self._positive_float(perceived_radius, "perceived_radius")
        self.task_radius = self._positive_float(task_radius, "task_radius")

        self.status = self._coerce_status(status or DroneStatus.IDLE)
        self.position = self._normalize_position(position)
        if self.position["z"] > self.max_altitude:
            raise ValueError(f"Initial altitude exceeds maximum ({self.max_altitude}m)")
        self.heading = float(heading) % 360.0
        self.speed = max(0.0, float(speed))

        self.battery_capacity = self._positive_float(battery_capacity, "battery_capacity")
        self.battery_level = 100.0
        self.battery_volume = self.battery_capacity
        if battery_volume is not None:
            self.battery_volume = self._clamp(battery_volume, 0.0, self.battery_capacity)
            self.battery_level = (self.battery_volume / self.battery_capacity) * 100.0
        elif battery_level is not None:
            self.battery_level = self._clamp(battery_level, 0.0, 100.0)
            self.battery_volume = (self.battery_level / 100.0) * self.battery_capacity

        self.home_position = self._normalize_position(home_position, default=self.position)
        if self.home_position["z"] > self.max_altitude:
            raise ValueError(f"Home altitude exceeds maximum ({self.max_altitude}m)")
        self.created_at = created_at or time.time()
        self.last_updated = last_updated or self.created_at

        # History status tracking - internal session-scoped tracking (not persisted)
        # Records waypoints reached and status events during the drone's lifecycle
        self.history_status: List[Dict[str, Any]] = []
        self.max_history_records = 500  # Limit to prevent memory issues

        self._apply_battery_safety()
    
    @staticmethod
    def _positive_float(value: float, field_name: str) -> float:
        value = float(value)
        if value <= 0:
            raise ValueError(f"{field_name} must be positive")
        return value

    @staticmethod
    def _clamp(value: float, lower: float, upper: float) -> float:
        value = float(value)
        return max(lower, min(upper, value))

    @staticmethod
    def _coerce_status(status: Any) -> DroneStatus:
        if isinstance(status, DroneStatus):
            return status
        try:
            return DroneStatus(status)
        except ValueError as exc:
            raise ValueError(f"Unsupported drone status: {status}") from exc

    @staticmethod
    def _normalize_position(
        position: Optional[Mapping[str, Any]],
        default: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, float]:
        source = position or default or {"x": 0.0, "y": 0.0, "z": 0.0}
        if "x" not in source or "y" not in source:
            raise ValueError("Position must include 'x' and 'y' coordinates")
        z_value = float(source.get("z", 0.0))
        if z_value < 0:
            raise ValueError("Altitude cannot be negative")
        normalized = {
            "x": float(source["x"]),
            "y": float(source["y"]),
            "z": z_value,
        }
        return normalized

    def _apply_battery_safety(self) -> None:
        """Ensure battery-related safety rules are enforced."""
        if self.battery_level < 0.5 and self.status != DroneStatus.EMERGENCY and self.position["z"] > 0:
            self.status = DroneStatus.EMERGENCY
            self.position["z"] = 0.0
        elif self.battery_level >= 5.0 and self.status == DroneStatus.EMERGENCY:
            self.status = DroneStatus.IDLE

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Drone":
        required = ["name", "model", "max_speed", "max_altitude", "battery_capacity"]
        for field in required:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        position = data.get("position")
        status = data.get("status")
        if status is None and position:
            status = DroneStatus.HOVERING if float(position.get("z", 0.0)) > 0 else DroneStatus.IDLE

        return cls(
            name=data["name"],
            model=data["model"],
            max_speed=data["max_speed"],
            max_altitude=data["max_altitude"],
            battery_capacity=data["battery_capacity"],
            perceived_radius=data.get("perceived_radius", 50.0),
            task_radius=data.get("task_radius", 20.0),
            drone_id=data.get("id"),
            status=status,
            position=position,
            heading=data.get("heading", 0.0),
            speed=data.get("speed", 0.0),
            battery_level=data.get("battery_level"),
            battery_volume=data.get("battery_volume"),
            home_position=data.get("home_position"),
            created_at=data.get("created_at"),
            last_updated=data.get("last_updated"),
        )

    def apply_update(self, updates: Mapping[str, Any]) -> None:
        """Apply a partial update to this drone."""
        changed = False

        if "name" in updates:
            self.name = updates["name"]
            changed = True

        if "model" in updates:
            self.model = updates["model"]
            changed = True

        if "max_speed" in updates:
            self.max_speed = self._positive_float(updates["max_speed"], "max_speed")
            changed = True

        if "max_altitude" in updates:
            new_max_altitude = self._positive_float(updates["max_altitude"], "max_altitude")
            if self.position["z"] > new_max_altitude or self.home_position["z"] > new_max_altitude:
                raise ValueError("Existing altitude exceeds the new maximum altitude")
            self.max_altitude = new_max_altitude
            changed = True

        if "battery_capacity" in updates:
            new_capacity = self._positive_float(updates["battery_capacity"], "battery_capacity")
            self.battery_capacity = new_capacity
            self.battery_volume = (self.battery_level / 100.0) * new_capacity
            changed = True

        if "perceived_radius" in updates:
            self.perceived_radius = self._positive_float(updates["perceived_radius"], "perceived_radius")
            changed = True

        if "task_radius" in updates:
            self.task_radius = self._positive_float(updates["task_radius"], "task_radius")
            changed = True

        if "status" in updates:
            self.update_status(updates["status"])

        if "heading" in updates:
            self.update_heading(float(updates["heading"]))

        if "speed" in updates:
            self.speed = max(0.0, float(updates["speed"]))
            changed = True

        if "position" in updates:
            pos = updates["position"] or {}
            self.update_position(
                float(pos.get("x", self.position["x"])),
                float(pos.get("y", self.position["y"])),
                float(pos.get("z", self.position["z"])),
            )

        if "home_position" in updates:
            self.home_position = self._normalize_position(updates["home_position"])
            if self.home_position["z"] > self.max_altitude:
                raise ValueError("Home altitude exceeds maximum altitude")
            changed = True

        if "battery_level" in updates:
            self.update_battery(float(updates["battery_level"]))

        if "battery_volume" in updates:
            self.update_battery_volume(float(updates["battery_volume"]))

        if changed:
            self.last_updated = time.time()

    def to_dict(self) -> Dict:
        """Convert drone object to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "model": self.model,
            "status": self.status.value,
            "position": self.position.copy(),
            "heading": self.heading,
            "speed": self.speed,
            "perceived_radius": self.perceived_radius,
            "task_radius": self.task_radius,
            "battery_level": self.battery_level,      # Percentage (0-100%)
            "battery_volume": self.battery_volume,    # Current volume in mAh
            "battery_capacity": self.battery_capacity, # Maximum capacity in mAh
            "max_speed": self.max_speed,
            "max_altitude": self.max_altitude,
            "home_position": self.home_position.copy(),
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }
    
    def update_status(self, status: DroneStatus) -> None:
        """Update the status of the drone"""
        self.status = self._coerce_status(status)
        self.last_updated = time.time()
    
    def update_position(self, x: float, y: float, z: float) -> None:
        """Update the position of the drone"""
        z = float(z)
        if z < 0:
            raise ValueError("Altitude cannot be negative")
        if z > self.max_altitude:
            raise ValueError(f"Altitude exceeds maximum ({self.max_altitude}m)")
        self.position = {"x": float(x), "y": float(y), "z": z}
        self.last_updated = time.time()

    def update_heading(self, heading: float) -> None:
        """Update the heading of the drone (0-359 degrees)"""
        # Normalize heading to 0-359 range
        self.heading = heading % 360.0
        self.last_updated = time.time()

    def calculate_heading_to(self, target_x: float, target_y: float) -> float:
        """Calculate the heading from current position to a target position"""
        dx = target_x - self.position["x"]
        dy = target_y - self.position["y"]

        # Calculate angle in radians (atan2 returns -pi to pi)
        angle_rad = math.atan2(dx, dy)

        # Convert to degrees (0-360, where 0 is North)
        heading = math.degrees(angle_rad)
        if heading < 0:
            heading += 360.0

        return heading

    def update_battery(self, level: float) -> None:
        """Update the battery level and volume of the drone

        Args:
            level: Battery level in percentage (0-100%)
        """
        # Clamp percentage to 0-100%
        self.battery_level = max(0.0, min(100.0, level))

        # Calculate corresponding mAh volume
        self.battery_volume = (self.battery_level / 100.0) * self.battery_capacity

        self.last_updated = time.time()

        self._apply_battery_safety()

    def update_battery_volume(self, volume: float) -> None:
        """Update the battery by volume directly

        Args:
            volume: Battery volume in mAh
        """
        # Clamp volume to 0-capacity
        self.battery_volume = max(0.0, min(self.battery_capacity, volume))

        # Calculate corresponding percentage
        self.battery_level = (self.battery_volume / self.battery_capacity) * 100.0

        self.last_updated = time.time()

        self._apply_battery_safety()

    def consume_battery_mah(self, mah: float) -> float:
        """Consume a specific amount of battery in mAh

        Args:
            mah: Amount of battery to consume in mAh

        Returns:
            Actual mAh consumed (may be less if battery is low)
        """
        original_volume = self.battery_volume
        new_volume = max(0.0, self.battery_volume - mah)
        actual_consumed = original_volume - new_volume

        self.update_battery_volume(new_volume)

        return actual_consumed
    
    def is_emergency_battery(self) -> bool:
        """Check if drone is in emergency battery state"""
        return self.battery_level < 0.5
    
    def can_operate(self) -> bool:
        """Check if drone can perform operations (not in emergency state)"""
        return self.battery_level >= 5.0 or self.status != DroneStatus.EMERGENCY
    
    def set_home_position(self) -> None:
        """Set the current position as home position"""
        self.home_position = self.position.copy()

    def record_history_waypoint(
        self,
        event: str,
        start_position: Optional[Dict[str, float]] = None,
        position: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a waypoint reached event in history

        Args:
            event: Event name (e.g., "move_to", "take_off", "land")
            start_position: Starting position of the movement (defaults to current position)
            position: Ending position where event occurred (defaults to current position)
            metadata: Additional event-specific data
        """
        self.record_history_event(
            event_type="waypoint",
            event=event,
            start_position=start_position,
            position=position,
            duration=0,
            metadata=metadata
        )

    def record_history_status(
        self,
        event: str,
        start_position: Optional[Dict[str, float]] = None,
        position: Optional[Dict[str, float]] = None,
        duration: float = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a status event in history

        Args:
            event: Event name (e.g., "hovering", "take_photo", "charging")
            start_position: Starting position when event began (defaults to current position)
            position: Ending position where event occurred (defaults to current position)
            duration: Duration of the event in seconds (default: 0)
            metadata: Additional event-specific data
        """
        self.record_history_event(
            event_type="status_event",
            event=event,
            start_position=start_position,
            position=position,
            duration=duration,
            metadata=metadata
        )

    def record_history_event(
        self,
        event_type: str,
        event: str,
        start_position: Optional[Dict[str, float]] = None,
        position: Optional[Dict[str, float]] = None,
        duration: float = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """General method to record any history event

        Args:
            event_type: Type of event ("waypoint", "status_event", "other")
            event: Event name
            start_position: Starting position when event began (defaults to current position)
            position: Ending position where event occurred (defaults to current position)
            duration: Duration of the event in seconds (default: 0)
            metadata: Additional event-specific data
        """
        # Use current position if not provided
        start_pos = start_position if start_position is not None else self.position.copy()
        end_pos = position if position is not None else self.position.copy()

        # Create history record
        record = {
            "type": event_type,
            "event": event,
            "start_position": start_pos,
            "position": end_pos,
            "timestamp": time.time(),
            "duration": float(duration),
            "metadata": metadata.copy() if metadata else {}
        }

        # Add to history
        self.history_status.append(record)

        # Limit history size to prevent memory issues
        if len(self.history_status) > self.max_history_records:
            self.history_status = self.history_status[-self.max_history_records:]

    def get_history_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get all history events of a specific type

        Args:
            event_type: Type to filter by ("waypoint", "status_event", "other")

        Returns:
            List of history records matching the type
        """
        return [record.copy() for record in self.history_status if record["type"] == event_type]

    def get_history_by_event(self, event: str) -> List[Dict[str, Any]]:
        """Get all history events with a specific event name

        Args:
            event: Event name to filter by

        Returns:
            List of history records matching the event name
        """
        return [record.copy() for record in self.history_status if record["event"] == event]

    def get_all_history(self) -> List[Dict[str, Any]]:
        """Get all history events

        Returns:
            List of all history records
        """
        return [record.copy() for record in self.history_status]

    def clear_history(self) -> None:
        """Clear all history records"""
        self.history_status = []
