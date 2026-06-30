from typing import Dict, List, Optional
from models.obstacle import Obstacle, ObstacleType

from shapely.geometry import Point, Polygon, LineString


class ObstacleController:
    """Controller for managing obstacles in the drone simulation system"""
    
    def __init__(self):
        self.obstacles: Dict[str, Obstacle] = {}
    
    def get_all_obstacles(self) -> List[Dict]:
        """Get all obstacles"""
        return [obstacle.to_dict() for obstacle in self.obstacles.values()]
    
    def get_obstacle(self, obstacle_id: str) -> Optional[Dict]:
        """Get a specific obstacle by ID"""
        obstacle = self.obstacles.get(obstacle_id)
        return obstacle.to_dict() if obstacle else None
    
    def add_obstacle(self, obstacle_data: Dict) -> Dict:
        """Add a new obstacle to the system

        Args:
            obstacle_data: Dictionary containing obstacle data with keys:
                - name: Obstacle name (required)
                - type: Obstacle type (required)
                - position: Position dict with x, y, z (required)
                - description: Description string (optional)
                - radius: Radius for circle obstacles (optional)
                - vertices: List of vertices for polygon obstacles (optional)
                - width: Width for rectangle obstacles (optional)
                - length: Length for rectangle obstacles (optional)
                - height: Height of the obstacle (optional, default: 10.0)
                - id: Optional ID to preserve when restoring from sessions

        Returns:
            Dict representation of the created obstacle
        """
        try:
            obstacle = Obstacle.from_dict(obstacle_data)
            self.obstacles[obstacle.id] = obstacle
            return obstacle.to_dict()

        except ValueError as e:
            raise ValueError(f"Invalid obstacle data: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to add obstacle: {str(e)}")
    
    def update_obstacle(self, obstacle_id: str, update_data: Dict) -> Optional[Dict]:
        """Update an existing obstacle"""
        obstacle = self.obstacles.get(obstacle_id)
        if not obstacle:
            return None
        
        try:
            obstacle.apply_update(update_data)
            return obstacle.to_dict()
            
        except Exception as e:
            raise Exception(f"Failed to update obstacle: {str(e)}")
    
    def delete_obstacle(self, obstacle_id: str) -> bool:
        """Delete an obstacle"""
        if obstacle_id in self.obstacles:
            del self.obstacles[obstacle_id]
            return True
        return False
    
    def check_path_collision(self, start_x: float, start_y: float,
                           end_x: float, end_y: float,
                           start_z: float = 0.0, end_z: float = 0.0,
                           safety_margin: float = 0.0) -> Dict:
        """Check if a flight path collides with any obstacles

        Height logic:
        - height = 0: Impassable at any altitude
        - height > 0: Collision only if max flight altitude <= obstacle.height
        """
        # Create flight path as LineString
        flight_path = LineString([(start_x, start_y), (end_x, end_y)])

        # Apply safety buffer to the path only if safety_margin > 0
        # When safety_margin=0, buffer() creates an EMPTY geometry, so use the line directly
        if safety_margin > 0:
            path_geometry = flight_path.buffer(safety_margin)
        else:
            path_geometry = flight_path

        for obstacle in self.obstacles.values():
            # Check altitude constraints: height=0 means impassable at any altitude
            max_flight_z = max(start_z, end_z)
            if obstacle.height > 0 and max_flight_z > obstacle.height:
                continue
            geometry = obstacle.to_geometry()
            if not geometry:
                continue

            # Check for intersection
            if path_geometry.intersects(geometry):
                return {
                    "collision": True,
                    "obstacle": {
                        "id": obstacle.id,
                        "name": obstacle.name,
                        "type": obstacle.type,
                        "collision_type": "path_intersection",
                        "start_point": {"x": start_x, "y": start_y, "z": start_z},
                        "end_point": {"x": end_x, "y": end_y, "z": end_z}
                    }
                }

        return {"collision": False, "obstacle": None}

    
    def get_obstacles_by_type(self, obstacle_type: ObstacleType) -> List[Dict]:
        """Get all obstacles of a specific type"""
        return [obstacle.to_dict() for obstacle in self.obstacles.values() 
                if obstacle.type == obstacle_type]

    def get_obstacle_bounds(self, obstacle_id: str) -> Optional[Dict]:
        """Get the bounding box of an obstacle using shapely"""
        obstacle = self.obstacles.get(obstacle_id)
        if not obstacle:
            return None
        
        geometry = obstacle.to_geometry()
        if geometry:
            bounds = geometry.bounds  # (minx, miny, maxx, maxy)
            return {
                "min_x": bounds[0],
                "min_y": bounds[1],
                "max_x": bounds[2],
                "max_y": bounds[3],
                "height": obstacle.height
            }
        return None
    
    def get_obstacles_in_area(self, min_x: float, min_y: float, max_x: float, max_y: float) -> List[Dict]:
        """Get all obstacles that intersect with a given rectangular area"""
        area_polygon = Polygon([
            (min_x, min_y),
            (max_x, min_y),
            (max_x, max_y),
            (min_x, max_y),
            (min_x, min_y)
        ])
        
        intersecting_obstacles = []
        for obstacle in self.obstacles.values():
            geometry = obstacle.to_geometry()
            if geometry and area_polygon.intersects(geometry):
                intersecting_obstacles.append(obstacle.to_dict())
        
        return intersecting_obstacles
    
    def find_nearest_obstacle(self, x: float, y: float, z: float = 0.0) -> Optional[Dict]:
        """Find the nearest obstacle to a given point using shapely"""
        query_point = Point(x, y)
        nearest_obstacle = None
        min_distance = float('inf')
        
        for obstacle in self.obstacles.values():
            # Skip if point is above obstacle
            if z > obstacle.height:
                continue
            
            geometry = obstacle.to_geometry()
            if geometry:
                distance = geometry.distance(query_point)
                if distance < min_distance:
                    min_distance = distance
                    nearest_obstacle = obstacle
        
        if nearest_obstacle:
            result = nearest_obstacle.to_dict()
            result['distance'] = min_distance
            return result
        
        return None
    
    def get_safe_corridor(self, start_x: float, start_y: float, end_x: float, end_y: float, 
                         corridor_width: float = 5.0, altitude: float = 10.0) -> Dict:
        """Calculate a safe corridor between two points avoiding obstacles"""
        # Create the desired path
        desired_path = LineString([(start_x, start_y), (end_x, end_y)])
        corridor = desired_path.buffer(corridor_width / 2)
        
        # Check for obstacles in the corridor
        conflicting_obstacles = []
        for obstacle in self.obstacles.values():
            # Skip if corridor is above obstacle
            if altitude > obstacle.height:
                continue
            
            geometry = obstacle.to_geometry()
            if geometry and corridor.intersects(geometry):
                conflicting_obstacles.append({
                    "id": obstacle.id,
                    "name": obstacle.name,
                    "type": obstacle.type.value
                })
        
        if conflicting_obstacles:
            return {
                "safe": False,
                "corridor": None,
                "conflicting_obstacles": conflicting_obstacles,
                "message": f"Corridor blocked by {len(conflicting_obstacles)} obstacle(s)"
            }
        
        # Convert corridor geometry to coordinates for visualization
        corridor_coords = list(corridor.exterior.coords)
        
        return {
            "safe": True,
            "corridor": {
                "width": corridor_width,
                "coordinates": corridor_coords,
                "area": corridor.area
            },
            "conflicting_obstacles": [],
            "message": "Safe corridor available"
        }
    
    def calculate_obstacle_density(self, center_x: float, center_y: float, radius: float) -> Dict:
        """Calculate obstacle density in a circular area"""
        # Create circular area
        center_point = Point(center_x, center_y)
        search_area = center_point.buffer(radius)

        obstacles_in_area = 0
        total_obstacle_area = 0.0

        for obstacle in self.obstacles.values():
            geometry = obstacle.to_geometry()
            if geometry:
                intersection = search_area.intersection(geometry)
                if not intersection.is_empty:
                    obstacles_in_area += 1
                    total_obstacle_area += intersection.area

        search_area_size = search_area.area
        density = (total_obstacle_area / search_area_size) * 100 if search_area_size > 0 else 0.0

        return {
            "density": density,  # Percentage of area covered by obstacles
            "obstacle_count": obstacles_in_area,
            "total_obstacle_area": total_obstacle_area,
            "search_area": search_area_size,
            "message": f"Found {obstacles_in_area} obstacles covering {density:.1f}% of the search area"
        }

    def check_point_collision(self, x: float, y: float, z: Optional[float] = None, margin: float = 0.0) -> Dict:
        """Check if a point is inside any obstacle or on its boundary within a margin

        Args:
            x: X coordinate of the point
            y: Y coordinate of the point
            z: Z coordinate (altitude) of the point (optional)
            margin: Margin in meters around obstacles (default: 0.0)

        Returns:
            Dictionary containing:
                - result: True if point is inside or on boundary of any obstacle
                - inside_obstacle_ids: List of obstacle IDs containing the point
                - inside_obstacles: List of detailed info about obstacles containing the point
                - point: The point that was checked
                - margin: Margin used for the check
                - message: Human-readable message about the result

        Height logic:
            - If z is not given: Check 2D area only (treats all obstacles as non-flyable)
            - If z is given and obstacle height = 0: Area is non-flyable at any altitude
            - If z is given and obstacle height > 0:
                - Point is inside if z <= obstacle.height + margin
                - Point is outside if z > obstacle.height + margin
        """
        query_point = Point(x, y)
        inside_obstacle_ids = []
        inside_obstacles = []

        for obstacle in self.obstacles.values():
            geometry = obstacle.to_geometry()
            if not geometry:
                continue

            # Apply margin to the obstacle geometry
            if margin > 0:
                geometry = geometry.buffer(margin)

            # Check if point is inside the 2D geometry (with margin)
            is_inside_2d = geometry.contains(query_point) or geometry.touches(query_point)

            if not is_inside_2d:
                continue

            # Now check altitude constraints
            # If z is not provided, treat as inside (area is non-flyable)
            if z is None:
                inside_obstacle_ids.append(obstacle.id)
                distance = -geometry.distance(query_point) if geometry.contains(query_point) else 0.0
                inside_obstacles.append({
                    "id": obstacle.id,
                    "name": obstacle.name,
                    "type": obstacle.type.value,
                    "height": obstacle.height,
                    "distance_to_boundary": distance
                })
                continue

            # If height = 0, area is non-flyable at any altitude
            if obstacle.height == 0:
                inside_obstacle_ids.append(obstacle.id)
                distance = -geometry.distance(query_point) if geometry.contains(query_point) else 0.0
                inside_obstacles.append({
                    "id": obstacle.id,
                    "name": obstacle.name,
                    "type": obstacle.type.value,
                    "height": obstacle.height,
                    "distance_to_boundary": distance
                })
                continue

            # If height > 0, check if point altitude is below obstacle height + margin
            if z <= obstacle.height + margin:
                inside_obstacle_ids.append(obstacle.id)
                distance = -geometry.distance(query_point) if geometry.contains(query_point) else 0.0
                inside_obstacles.append({
                    "id": obstacle.id,
                    "name": obstacle.name,
                    "type": obstacle.type.value,
                    "height": obstacle.height,
                    "distance_to_boundary": distance
                })

        result = len(inside_obstacle_ids) > 0

        # Build point dict
        point_dict = {"x": x, "y": y}
        if z is not None:
            point_dict["z"] = z

        # Build message
        if result:
            message = f"Point is inside {len(inside_obstacle_ids)} obstacle(s)"
        else:
            message = "Point is not inside any obstacles"

        return {
            "result": result,
            "inside_obstacle_ids": inside_obstacle_ids,
            "inside_obstacles": inside_obstacles,
            "point": point_dict,
            "margin": margin,
            "message": message
        }
