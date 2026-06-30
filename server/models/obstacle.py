from enum import Enum
from typing import Any, Dict, List, Mapping, Optional
import time
import math
from shapely.affinity import scale
from shapely.geometry import Point, Polygon

from config.util import (
    distance as euclidean_distance,
    generate_random_id,
    point_to_line_distance,
    validate_polygon_vertices,
    normalize_polygon_vertices,
)


class ObstacleType(str, Enum):
    """Enum representing the possible types of obstacles

    - POINT: Single point obstacle (circular with small radius)
    - CIRCLE: Circular obstacle
    - POLYGON: Polygonal obstacle (3+ vertices)
    - ELLIPSE: Ellipse obstacle (width and height axes)

    Height interpretation:
    - height = 0: Impassable area, drones cannot pass through at any altitude
    - height > 0: Drones can fly over if their altitude > obstacle height
    """
    POINT = "point"      # Point obstacle (small circular)
    CIRCLE = "circle"    # Circular obstacle
    POLYGON = "polygon"  # Polygonal obstacle
    ELLIPSE = "ellipse"  # Ellipse obstacle


class Obstacle:
    """Class representing an obstacle in the system"""
    
    def __init__(
        self,
        name: str,
        obstacle_type: ObstacleType,
        position: Optional[Dict[str, float]] = None,
        description: str = "",
        radius: Optional[float] = None,
        vertices: Optional[List[Dict[str, float]]] = None,
        height: float = 10.0,
        width: Optional[float] = None,  # For ellipse obstacles (x-axis)
        length: Optional[float] = None,  # For ellipse obstacles (y-axis)
        obstacle_id: Optional[str] = None,
        created_at: Optional[float] = None,
        last_updated: Optional[float] = None,
    ):
        self.id = obstacle_id or generate_random_id()
        self.name = name
        self.type = obstacle_type
        self.description = description
        self.height = height  # Height in meters: 0 = impassable, >0 = can fly over

        # For circular and point obstacles
        self.radius = radius

        # For ellipse obstacles
        self.width = width    # Semi-major axis (x-direction)
        self.length = length  # Semi-minor axis (y-direction)

        # For polygonal obstacles (list of vertices)
        self.vertices = self._copy_vertices(vertices)

        # Set position based on obstacle type
        self.position = self._resolve_position(position)
        
        # Calculate area and validate before exposing the instance
        self.area = self._calculate_area()
        self._validate_obstacle()

        now = time.time()
        self.created_at = created_at or now
        self.last_updated = last_updated or now

    @staticmethod
    def _copy_vertices(vertices: Optional[List[Dict[str, float]]]) -> List[Dict[str, float]]:
        if not vertices:
            return []
        # Create a clean copy first
        v_copy = [vertex.copy() for vertex in vertices]
        return normalize_polygon_vertices(v_copy)

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
        center_z = vertices[0].get("z", 0) if vertices else 0

        return {"x": center_x, "y": center_y, "z": center_z}

    def _resolve_position(self, position: Optional[Dict[str, float]]) -> Dict[str, float]:
        if self.type in [ObstacleType.POINT, ObstacleType.CIRCLE, ObstacleType.ELLIPSE]:
            if position is None:
                raise ValueError(f"{self.type} obstacles must have a position")
            return position.copy()

        # Polygon obstacle - calculate centroid from vertices
        if self.vertices:
            return self._calculate_polygon_centroid(self.vertices)
        if position is not None:
            return position.copy()
        raise ValueError("Polygon obstacles must have vertices or position")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Obstacle":
        """Build an obstacle from a raw dictionary payload."""
        if "name" not in data:
            raise ValueError("Missing required field: name")
        if "type" not in data:
            raise ValueError("Missing required field: type")

        obstacle_type = data["type"]
        if not isinstance(obstacle_type, ObstacleType):
            try:
                obstacle_type = ObstacleType(obstacle_type)
            except ValueError as exc:
                raise ValueError(f"Unsupported obstacle type: {data['type']}") from exc

        return cls(
            name=data["name"],
            obstacle_type=obstacle_type,
            position=data.get("position"),
            description=data.get("description", ""),
            radius=data.get("radius"),
            vertices=data.get("vertices"),
            height=data.get("height", 10.0),
            width=data.get("width"),
            length=data.get("length"),
            obstacle_id=data.get("id"),
            created_at=data.get("created_at"),
            last_updated=data.get("last_updated"),
        )

    def apply_update(self, update_data: Mapping[str, Any]) -> None:
        """Apply updates from a payload and keep validation centralized."""
        if "type" in update_data:
            new_type = update_data["type"]
            if not isinstance(new_type, ObstacleType):
                try:
                    new_type = ObstacleType(new_type)
                except ValueError as exc:
                    raise ValueError(f"Unsupported obstacle type: {update_data['type']}") from exc
            if new_type != self.type:
                raise ValueError("Changing obstacle type is not supported")

        requires_area_recalc = False
        requires_validation = False

        if "name" in update_data:
            self.name = update_data["name"]
        if "description" in update_data:
            self.description = update_data["description"]
        if "height" in update_data:
            self.height = float(update_data["height"])

        if "position" in update_data:
            position = update_data["position"] or {}
            x = position.get("x", self.position.get("x", 0.0))
            y = position.get("y", self.position.get("y", 0.0))
            z = position.get("z", self.position.get("z", 0.0))
            self.update_position(x, y, z)

        if "radius" in update_data and self.type in [ObstacleType.POINT, ObstacleType.CIRCLE]:
            self.radius = float(update_data["radius"])
            requires_area_recalc = True
            requires_validation = True

        if "width" in update_data and self.type == ObstacleType.ELLIPSE:
            self.width = float(update_data["width"])
            requires_area_recalc = True
            requires_validation = True

        if "length" in update_data and self.type == ObstacleType.ELLIPSE:
            self.length = float(update_data["length"])
            requires_area_recalc = True
            requires_validation = True

        if "vertices" in update_data and self.type == ObstacleType.POLYGON:
            new_vertices = update_data["vertices"] or []
            self.vertices = self._copy_vertices(new_vertices)
            if self.vertices:
                # Recalculate centroid as the position
                self.position = self._calculate_polygon_centroid(self.vertices)
            requires_area_recalc = True
            requires_validation = True

        if requires_area_recalc:
            self.area = self._calculate_area()

        if requires_validation:
            self._validate_obstacle()

        self.last_updated = time.time()
    
    def _calculate_area(self) -> float:
        """Calculate the area of the obstacle"""
        if self.type == ObstacleType.POINT:
            # Point obstacles have minimal area (1 meter radius default)
            r = self.radius if self.radius else 1.0
            return math.pi * r ** 2
        elif self.type == ObstacleType.CIRCLE:
            if self.radius is None:
                return 0.0
            return math.pi * self.radius ** 2
        elif self.type == ObstacleType.ELLIPSE:
            if self.width is None or self.length is None:
                return 0.0
            return math.pi * self.width * self.length
        else:  # POLYGON
            # For polygon obstacles, use shapely to calculate area
            if not self.vertices or len(self.vertices) < 3:
                return 0.0

            # Convert vertices to shapely polygon format
            coords = [(vertex["x"], vertex["y"]) for vertex in self.vertices]
            polygon = Polygon(coords)
            return polygon.area

    def _validate_obstacle(self) -> None:
        """Validate obstacle data based on type"""
        if self.type == ObstacleType.POINT:
            # Point obstacles use a small default radius if not specified
            if self.radius is None:
                self.radius = 1.0  # Default 1 meter radius
        elif self.type == ObstacleType.CIRCLE:
            if self.radius is None or self.radius <= 0:
                raise ValueError("Circle obstacles must have a positive radius")
        elif self.type == ObstacleType.ELLIPSE:
            if self.width is None or self.width <= 0:
                raise ValueError("Elliptical obstacles must have a positive width")
            if self.length is None or self.length <= 0:
                raise ValueError("Elliptical obstacles must have a positive length")
        elif self.type == ObstacleType.POLYGON:
            is_valid, reason = validate_polygon_vertices(self.vertices)
            if not is_valid:
                raise ValueError(f"Invalid polygon vertices: {reason}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert obstacle object to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "position": self.position,
            "description": self.description,
            "radius": self.radius,
            "width": self.width,
            "length": self.length,
            "vertices": self.vertices,
            "height": self.height,
            "area": self.area,
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }
    
    def update_position(self, x: float, y: float, z: float) -> None:
        """Update the position of the obstacle

        For polygon obstacles, this moves all vertices so that the centroid
        is at the new position (x, y, z).
        """
        if self.type in [ObstacleType.POINT, ObstacleType.CIRCLE, ObstacleType.ELLIPSE]:
            self.position = {"x": x, "y": y, "z": z}
        else:
            # For polygon obstacles, move all vertices to maintain the centroid at (x, y, z)
            if self.vertices:
                # Calculate offset from current centroid to new position
                dx = x - self.position["x"]
                dy = y - self.position["y"]
                dz = z - self.position.get("z", 0)

                # Update all vertices by the same offset
                for vertex in self.vertices:
                    vertex["x"] += dx
                    vertex["y"] += dy
                    if "z" in vertex:
                        vertex["z"] += dz

                # Update position to new centroid (rounded to integers)
                self.position = {"x": round(x), "y": round(y), "z": z}
                self.area = self._calculate_area()
            else:
                self.position = {"x": round(x), "y": round(y), "z": z}

        self.last_updated = time.time()
    
    def is_point_inside(self, point: Dict[str, float]) -> bool:
        """Check if a point is inside the obstacle

        Height logic:
        - height = 0: Impassable, collision at any altitude
        - height > 0: Collision only if point altitude <= obstacle height
        """
        # Check height: if height is 0, it's impassable at any altitude
        if self.height > 0 and point["z"] > self.height:
            # Drone is above the obstacle, no collision
            return False

        # Check 2D collision based on type
        if self.type in [ObstacleType.POINT, ObstacleType.CIRCLE]:
            return self._is_point_in_circle(point)
        elif self.type == ObstacleType.ELLIPSE:
            return self._is_point_in_ellipse(point)
        else:  # POLYGON
            return self._is_point_in_polygon(point)
    
    def _is_point_in_circle(self, point: Dict[str, float]) -> bool:
        """Check if a point is inside a circular obstacle"""
        return euclidean_distance(
            (point["x"], point["y"]),
            (self.position["x"], self.position["y"]),
        ) <= self.radius
    
    def _is_point_in_ellipse(self, point: Dict[str, float]) -> bool:
        """Check if a point is inside an elliptical obstacle"""
        dx = point["x"] - self.position["x"]
        dy = point["y"] - self.position["y"]
        # Ellipse equation: (dx/width)² + (dy/length)² <= 1
        return (dx / self.width) ** 2 + (dy / self.length) ** 2 <= 1.0

    def _is_point_in_polygon(self, point: Dict[str, float]) -> bool:
        """Check if a point is inside a polygonal obstacle using ray casting algorithm"""
        x, y = point["x"], point["y"]
        n = len(self.vertices)
        inside = False

        p1x, p1y = self.vertices[0]["x"], self.vertices[0]["y"]
        for i in range(1, n + 1):
            p2x, p2y = self.vertices[i % n]["x"], self.vertices[i % n]["y"]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside
    
    def get_collision_distance(self, point: Dict[str, float]) -> float:
        """Get the minimum distance from a point to the obstacle boundary"""
        if self.type in [ObstacleType.POINT, ObstacleType.CIRCLE]:
            dx = point["x"] - self.position["x"]
            dy = point["y"] - self.position["y"]
            distance_to_center = euclidean_distance(
                (point["x"], point["y"]),
                (self.position["x"], self.position["y"]),
            )
            return max(0, self.radius - distance_to_center)
        elif self.type == ObstacleType.ELLIPSE:
            # For ellipse, approximate distance using parametric form
            dx = point["x"] - self.position["x"]
            dy = point["y"] - self.position["y"]
            distance_to_center = euclidean_distance(
                (point["x"], point["y"]),
                (self.position["x"], self.position["y"]),
            )
            # Approximate radius in the direction of the point
            if distance_to_center > 0:
                angle = math.atan2(dy, dx)
                # Radius at this angle for ellipse
                r = (self.width * self.length) / euclidean_distance(
                    (self.length * math.cos(angle), self.width * math.sin(angle)),
                    (0.0, 0.0),
                )
                return max(0, r - distance_to_center)
            return 0
        else:
            # For polygons, calculate distance to nearest edge
            min_distance = float('inf')
            for i in range(len(self.vertices)):
                v1 = self.vertices[i]
                v2 = self.vertices[(i + 1) % len(self.vertices)]
                distance = point_to_line_distance(point, v1, v2)
                min_distance = min(min_distance, distance)
            return min_distance
    
    def to_geometry(self):
        """Return a Shapely geometry representing this obstacle."""
        try:
            if self.type in [ObstacleType.POINT, ObstacleType.CIRCLE]:
                if self.radius is None:
                    return None
                center = Point(float(self.position["x"]), float(self.position["y"]))
                return center.buffer(float(self.radius))

            if self.type == ObstacleType.ELLIPSE:
                if self.width is None or self.length is None:
                    return None
                center = Point(float(self.position["x"]), float(self.position["y"]))
                unit_circle = center.buffer(1.0)
                return scale(unit_circle, xfact=float(self.width), yfact=float(self.length))

            if self.type == ObstacleType.POLYGON:
                if not self.vertices or len(self.vertices) < 3:
                    return None
                coords = [(float(vertex["x"]), float(vertex["y"])) for vertex in self.vertices]
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                return Polygon(coords)
        except Exception:
            return None

        return None
    
    def check_path_collision(self, start: Dict[str, float], 
                           end: Dict[str, float], 
                           safety_margin: float = 1.0) -> bool:
        """Check if a path from start to end collides with the obstacle"""
        # Simple implementation: check multiple points along the path
        steps = 20
        for i in range(steps + 1):
            t = i / steps
            point = {
                "x": start["x"] + t * (end["x"] - start["x"]),
                "y": start["y"] + t * (end["y"] - start["y"]),
                "z": start["z"] + t * (end["z"] - start["z"])
            }
            
            if self.is_point_inside(point):
                return True
            
            # Check safety margin
            if self.get_collision_distance(point) < safety_margin:
                return True
        
        return False
