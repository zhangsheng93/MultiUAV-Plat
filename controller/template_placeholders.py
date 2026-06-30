#!/usr/bin/env python3
"""
Template Placeholder System

Comprehensive placeholder system for task templates with:
- Multiple placeholder types (drone_id, positions, altitudes, etc.)
- Easy insertion UI
- Validation and substitution
- Documentation and examples
"""

from typing import Dict, Any, List, Optional
import re
import random
from api_server import APIServer

# Canvas settings for position generation
CANVAS_WIDTH = 1024
CANVAS_HEIGHT = 768
MAX_ALTITUDE = 100
CANVAS_MARGIN = 50


# Define all available placeholders
PLACEHOLDER_DEFINITIONS = {
    # Drone identifiers
    'drone_id': {
        'description': 'Drone identifier',
        'example': 'b1751588',
        'type': 'string',
        'required_in': ['API id parameter', 'content'],
        'category': 'Identifiers'
    },
    'drone_name': {
        'description': 'Drone name (human-readable)',
        'example': 'Patrol Drone Alpha',
        'type': 'string',
        'required_in': ['content'],
        'category': 'Identifiers',
        'linked_to': 'drone_id'
    },
    'target_id': {
        'description': 'Target identifier',
        'example': 'bc5429bb',
        'type': 'string',
        'required_in': ['API target_id parameter'],
        'category': 'Identifiers'
    },
    'target_name': {
        'description': 'Target name (human-readable)',
        'example': 'Building A',
        'type': 'string',
        'required_in': ['content'],
        'category': 'Identifiers',
        'linked_to': 'target_id'
    },
    'obstacle_id': {
        'description': 'Obstacle identifier',
        'example': 'b81b0447',
        'type': 'string',
        'required_in': ['API obstacle_id parameter'],
        'category': 'Identifiers'
    },
    'obstacle_name': {
        'description': 'Obstacle name (human-readable)',
        'example': 'Tower North',
        'type': 'string',
        'required_in': ['content'],
        'category': 'Identifiers',
        'linked_to': 'obstacle_id'
    },

    # Multi-entity indexed placeholders for formations and coordinated tasks
    # Drones 1-5
    'drone_1_id': {
        'description': 'First drone identifier',
        'example': 'drone-001',
        'type': 'string',
        'required_in': ['API id parameter', 'content'],
        'category': 'Multi-Entity Identifiers'
    },
    'drone_1_name': {
        'description': 'First drone name',
        'example': 'Alpha',
        'type': 'string',
        'required_in': ['content'],
        'category': 'Multi-Entity Identifiers',
        'linked_to': 'drone_1_id'
    },
    'drone_2_id': {
        'description': 'Second drone identifier',
        'example': 'drone-002',
        'type': 'string',
        'required_in': ['API id parameter', 'content'],
        'category': 'Multi-Entity Identifiers'
    },
    'drone_2_name': {
        'description': 'Second drone name',
        'example': 'Bravo',
        'type': 'string',
        'required_in': ['content'],
        'category': 'Multi-Entity Identifiers',
        'linked_to': 'drone_2_id'
    },
    'drone_3_id': {
        'description': 'Third drone identifier',
        'example': 'drone-003',
        'type': 'string',
        'required_in': ['API id parameter', 'content'],
        'category': 'Multi-Entity Identifiers'
    },
    'drone_3_name': {
        'description': 'Third drone name',
        'example': 'Charlie',
        'type': 'string',
        'required_in': ['content'],
        'category': 'Multi-Entity Identifiers',
        'linked_to': 'drone_3_id'
    },
    'drone_4_id': {
        'description': 'Fourth drone identifier',
        'example': 'drone-004',
        'type': 'string',
        'required_in': ['API id parameter', 'content'],
        'category': 'Multi-Entity Identifiers'
    },
    'drone_4_name': {
        'description': 'Fourth drone name',
        'example': 'Delta',
        'type': 'string',
        'required_in': ['content'],
        'category': 'Multi-Entity Identifiers',
        'linked_to': 'drone_4_id'
    },
    'drone_5_id': {
        'description': 'Fifth drone identifier',
        'example': 'drone-005',
        'type': 'string',
        'required_in': ['API id parameter', 'content'],
        'category': 'Multi-Entity Identifiers'
    },
    'drone_5_name': {
        'description': 'Fifth drone name',
        'example': 'Echo',
        'type': 'string',
        'required_in': ['content'],
        'category': 'Multi-Entity Identifiers',
        'linked_to': 'drone_5_id'
    },

    # Targets 1-3
    'target_1_id': {
        'description': 'First target identifier',
        'example': 'dd3d5f14',
        'type': 'string',
        'required_in': ['API target_id parameter', 'content'],
        'category': 'Multi-Entity Identifiers'
    },
    'target_1_name': {
        'description': 'First target name',
        'example': 'Building A',
        'type': 'string',
        'required_in': ['content'],
        'category': 'Multi-Entity Identifiers',
        'linked_to': 'target_1_id'
    },
    'target_2_id': {
        'description': 'Second target identifier',
        'example': '007f829c',
        'type': 'string',
        'required_in': ['API target_id parameter', 'content'],
        'category': 'Multi-Entity Identifiers'
    },
    'target_2_name': {
        'description': 'Second target name',
        'example': 'Building B',
        'type': 'string',
        'required_in': ['content'],
        'category': 'Multi-Entity Identifiers',
        'linked_to': 'target_2_id'
    },
    'target_3_id': {
        'description': 'Third target identifier',
        'example': 'b259417b',
        'type': 'string',
        'required_in': ['API target_id parameter', 'content'],
        'category': 'Multi-Entity Identifiers'
    },
    'target_3_name': {
        'description': 'Third target name',
        'example': 'Building C',
        'type': 'string',
        'required_in': ['content'],
        'category': 'Multi-Entity Identifiers',
        'linked_to': 'target_3_id'
    },

    # Obstacles 1-3
    'obstacle_1_id': {
        'description': 'First obstacle identifier',
        'example': '803ab663',
        'type': 'string',
        'required_in': ['API obstacle_id parameter', 'content'],
        'category': 'Multi-Entity Identifiers'
    },
    'obstacle_1_name': {
        'description': 'First obstacle name',
        'example': 'North Tower',
        'type': 'string',
        'required_in': ['content'],
        'category': 'Multi-Entity Identifiers',
        'linked_to': 'obstacle_1_id'
    },
    'obstacle_2_id': {
        'description': 'Second obstacle identifier',
        'example': 'obstacle-002',
        'type': 'string',
        'required_in': ['API obstacle_id parameter', 'content'],
        'category': 'Multi-Entity Identifiers'
    },
    'obstacle_2_name': {
        'description': 'Second obstacle name',
        'example': 'South Tower',
        'type': 'string',
        'required_in': ['content'],
        'category': 'Multi-Entity Identifiers',
        'linked_to': 'obstacle_2_id'
    },
    'obstacle_3_id': {
        'description': 'Third obstacle identifier',
        'example': 'obstacle-003',
        'type': 'string',
        'required_in': ['API obstacle_id parameter', 'content'],
        'category': 'Multi-Entity Identifiers'
    },
    'obstacle_3_name': {
        'description': 'Third obstacle name',
        'example': 'East Tower',
        'type': 'string',
        'required_in': ['content'],
        'category': 'Multi-Entity Identifiers',
        'linked_to': 'obstacle_3_id'
    },

    # Position coordinates
    'position_x': {
        'description': 'X coordinate position',
        'example': '100.0',
        'type': 'float',
        'required_in': ['API x parameter', 'content'],
        'category': 'Positions'
    },
    'position_y': {
        'description': 'Y coordinate position',
        'example': '150.0',
        'type': 'float',
        'required_in': ['API y parameter', 'content'],
        'category': 'Positions'
    },
    'position_z': {
        'description': 'Z coordinate position (altitude)',
        'example': '20.0',
        'type': 'float',
        'required_in': ['API z parameter', 'content'],
        'category': 'Positions'
    },

    # Altitude
    'altitude': {
        'description': 'Flight altitude in meters',
        'example': '15.0',
        'type': 'float',
        'required_in': ['API altitude parameter', 'content'],
        'category': 'Flight Parameters'
    },
    'altitude_change': {
        'description': 'Altitude change amount',
        'example': '5.0',
        'type': 'float',
        'required_in': ['API altitude parameter'],
        'category': 'Flight Parameters'
    },

    # Distance and direction
    'distance': {
        'description': 'Distance in meters',
        'example': '50.0',
        'type': 'float',
        'required_in': ['API distance parameter', 'content'],
        'category': 'Flight Parameters'
    },
    'heading': {
        'description': 'Heading angle in degrees (0-360)',
        'example': '90.0',
        'type': 'float',
        'required_in': ['API heading parameter', 'content'],
        'category': 'Flight Parameters'
    },

    # Speed
    'speed': {
        'description': 'Flight speed',
        'example': '10.0',
        'type': 'float',
        'required_in': ['API speed parameter'],
        'category': 'Flight Parameters'
    },

    # Waypoints (special handling)
    'waypoint_1_x': {
        'description': 'Waypoint 1 X coordinate',
        'example': '50.0',
        'type': 'float',
        'required_in': ['content'],
        'category': 'Waypoints'
    },
    'waypoint_1_y': {
        'description': 'Waypoint 1 Y coordinate',
        'example': '50.0',
        'type': 'float',
        'required_in': ['content'],
        'category': 'Waypoints'
    },
    'waypoint_1_z': {
        'description': 'Waypoint 1 Z coordinate',
        'example': '15.0',
        'type': 'float',
        'required_in': ['content'],
        'category': 'Waypoints'
    },
    'waypoint_2_x': {
        'description': 'Waypoint 2 X coordinate',
        'example': '100.0',
        'type': 'float',
        'required_in': ['content'],
        'category': 'Waypoints'
    },
    'waypoint_2_y': {
        'description': 'Waypoint 2 Y coordinate',
        'example': '50.0',
        'type': 'float',
        'required_in': ['content'],
        'category': 'Waypoints'
    },
    'waypoint_2_z': {
        'description': 'Waypoint 2 Z coordinate',
        'example': '15.0',
        'type': 'float',
        'required_in': ['content'],
        'category': 'Waypoints'
    },

    # Timing
    'duration': {
        'description': 'Duration in seconds',
        'example': '10.0',
        'type': 'float',
        'required_in': ['API duration parameter'],
        'category': 'Timing'
    },
    'hover_time': {
        'description': 'Hover duration in seconds',
        'example': '5.0',
        'type': 'float',
        'required_in': ['content'],
        'category': 'Timing'
    },

    # Other parameters
    'radius': {
        'description': 'Radius in meters',
        'example': '10.0',
        'type': 'float',
        'required_in': ['API radius parameter', 'content'],
        'category': 'Other'
    },
    'message': {
        'description': 'Message text',
        'example': 'Hello from drone',
        'type': 'string',
        'required_in': ['API message parameter'],
        'category': 'Other'
    },

    # Random number placeholders with predefined ranges
    'randx': {
        'description': 'Random X coordinate between 0-1024 (anonymous, new each time)',
        'example': '127',
        'type': 'dynamic_random',
        'min': 0.0,
        'max': 1024.0,
        'decimals': 0,
        'required_in': ['content', 'API x parameter'],
        'category': 'Random Numbers'
    },
    'randy': {
        'description': 'Random Y coordinate between 0-768 (anonymous, new each time)',
        'example': '89',
        'type': 'dynamic_random',
        'min': 0.0,
        'max': 768.0,
        'decimals': 0,
        'required_in': ['content', 'API y parameter'],
        'category': 'Random Numbers'
    },
    'randz': {
        'description': 'Random Z coordinate between 0-100 (anonymous, new each time)',
        'example': '18',
        'type': 'dynamic_random',
        'min': 0.0,
        'max': 100.0,
        'decimals': 0,
        'required_in': ['content', 'API z parameter'],
        'category': 'Random Numbers'
    },
    'randxy': {
        'description': 'Random X Y pair',
        'example': '127 89',
        'type': 'dynamic_random',
        'required_in': ['content'],
        'category': 'Random Numbers'
    },
    'randpos': {
        'description': 'Random position X,Y,Z',
        'example': '127,89,18',
        'type': 'dynamic_random',
        'required_in': ['content'],
        'category': 'Random Numbers'
    },
    'random_altitude': {
        'description': 'Random altitude between 5-100 meters',
        'example': '15',
        'type': 'random_float',
        'min': 5.0,
        'max': 100.0,
        'decimals': 0,
        'required_in': ['content', 'API altitude parameter'],
        'category': 'Random Numbers'
    },
    'random_x': {
        'description': 'Random X coordinate between 0-1024',
        'example': '127',
        'type': 'random_float',
        'min': 0.0,
        'max': 1024.0,
        'decimals': 0,
        'required_in': ['content', 'API x parameter'],
        'category': 'Random Numbers'
    },
    'random_y': {
        'description': 'Random Y coordinate between 0-768',
        'example': '89',
        'type': 'random_float',
        'min': 0.0,
        'max': 768.0,
        'decimals': 0,
        'required_in': ['content', 'API y parameter'],
        'category': 'Random Numbers'
    },
    'random_z': {
        'description': 'Random Z coordinate between 5-100',
        'example': '18',
        'type': 'random_float',
        'min': 5.0,
        'max': 100.0,
        'decimals': 0,
        'required_in': ['content', 'API z parameter'],
        'category': 'Random Numbers'
    },
    'random_heading': {
        'description': 'Random heading angle 0-360 degrees',
        'example': '245',
        'type': 'random_float',
        'min': 0.0,
        'max': 360.0,
        'decimals': 0,
        'required_in': ['content', 'API heading parameter'],
        'category': 'Random Numbers'
    },
    'random_distance': {
        'description': 'Random distance between 10-500 meters',
        'example': '47',
        'type': 'random_float',
        'min': 10.0,
        'max': 500.0,
        'decimals': 0,
        'required_in': ['content', 'API distance parameter'],
        'category': 'Random Numbers'
    },
    'random_speed': {
        'description': 'Random speed between 1-30 m/s',
        'example': '8',
        'type': 'random_float',
        'min': 1.0,
        'max': 30.0,
        'decimals': 0,
        'required_in': ['API speed parameter'],
        'category': 'Random Numbers'
    },
    'random_hovertime': {
        'description': 'Random hover time between 2-20 seconds',
        'example': '5',
        'type': 'random_float',
        'min': 2.0,
        'max': 20.0,
        'decimals': 0,
        'required_in': ['content'],
        'category': 'Random Numbers'
    },
    'random_duration': {
        'description': 'Random duration between 5-30 seconds',
        'example': '12',
        'type': 'random_float',
        'min': 5.0,
        'max': 30.0,
        'decimals': 0,
        'required_in': ['content'],
        'category': 'Random Numbers'
    },
}


def get_placeholder_categories() -> Dict[str, List[str]]:
    """Get placeholders organized by category

    Returns:
        Dictionary mapping category name to list of placeholder names
    """
    categories = {}
    for placeholder, info in PLACEHOLDER_DEFINITIONS.items():
        category = info.get('category', 'Other')
        if category not in categories:
            categories[category] = []
        categories[category].append(placeholder)
    return categories


def get_placeholder_info(placeholder: str) -> Optional[Dict[str, Any]]:
    """Get information about a specific placeholder

    Args:
        placeholder: Placeholder name (without braces)

    Returns:
        Placeholder information dict or None
    """
    return PLACEHOLDER_DEFINITIONS.get(placeholder)


def find_placeholders_in_text(text: str) -> List[str]:
    """Find all placeholders in text

    Args:
        text: Text to search for placeholders

    Returns:
        List of placeholder names found (without braces)
    """
    pattern = r'\{([^}]+)\}'
    matches = re.findall(pattern, text)
    return list(set(matches))


def generate_random_value(placeholder_info: Dict[str, Any]) -> float:
    """Generate a random value based on placeholder definition

    Args:
        placeholder_info: Placeholder information dictionary

    Returns:
        Random value within the defined range
    """
    min_val = placeholder_info.get('min', 0.0)
    max_val = placeholder_info.get('max', 100.0)
    # Default to 0 decimals for consistency with new standard
    decimals = placeholder_info.get('decimals', 0)

    value = random.uniform(min_val, max_val)
    return round(value, decimals) if decimals > 0 else round(value)


def check_collision(x: float, y: float, obstacles: List[Dict[str, Any]]) -> bool:
    """Check if point (x,y) collides with any obstacle using the API."""
    try:
        api = APIServer()
        SAFETY_MARGIN = 1.0
        # Call API for 2D check (z=None implies 2D footprint check)
        response = api.api_check_point_collision(x, y, z=None, margin=SAFETY_MARGIN, show_error=False)
        if response and isinstance(response, dict):
            return response.get('result', False)
    except Exception:
        pass
        
    return False

def parse_dynamic_random(placeholder: str, obstacles: Optional[List[Dict[str, Any]]] = None) -> tuple:
    """Parse and generate value for dynamic random placeholders
    
    Args:
        placeholder: Placeholder string
        obstacles: Optional list of obstacles for collision checking

    Returns:
        Tuple of (variable_name or None, random_value or None, is_anonymous)
        - variable_name: None for anonymous, or string for named variable
        - random_value: The generated random value/string or None
        - is_anonymous: True if anonymous placeholder
    """

    # --- General Dynamic Randoms (random:min:max, randint:min:max etc.) ---

    # Match randint:min:max (anonymous integer)
    match = re.match(r'^randint:(-?\d+):(-?\d+)$', placeholder)
    if match:
        min_val = int(match.group(1))
        max_val = int(match.group(2))
        value = random.randint(min_val, max_val)
        return (None, value, True)  # Anonymous, always generate new value

    # Match random:min:max or random:min:max:decimals (anonymous float)
    match = re.match(r'^random:(-?\d+\.?\d*):(-?\d+\.?\d*)(?::(\d+))?$', placeholder)
    if match:
        min_val = float(match.group(1))
        max_val = float(match.group(2))
        decimals = int(match.group(3)) if match.group(3) else 0
        value = random.uniform(min_val, max_val)
        return (None, round(value, decimals) if decimals > 0 else round(value), True)

    # Match randint_varname:min:max (named integer variable)
    match = re.match(r'^randint_([a-zA-Z_][a-zA-Z0-9_]*):(-?\d+):(-?\d+)$', placeholder)
    if match:
        var_name = match.group(1)
        min_val = int(match.group(2))
        max_val = int(match.group(3))
        value = random.randint(min_val, max_val)
        return (var_name, value, False)  # Named, should be cached

    # Match random_varname:min:max or random_varname:min:max:decimals (named variable)
    match = re.match(r'^random_([a-zA-Z_][a-zA-Z0-9_]*):(-?\d+\.?\d*):(-?\d+\.?\d*)(?::(\d+))?$', placeholder)
    if match:
        var_name = match.group(1)
        min_val = float(match.group(2))
        max_val = float(match.group(3))
        decimals = int(match.group(4)) if match.group(4) else 0
        value = random.uniform(min_val, max_val)
        return (var_name, round(value, decimals) if decimals > 0 else round(value), False)


    # --- Coordinate-Specific Randoms (randx, randy, etc.) ---
    
    types = ['randxyz', 'randxyc', 'randxy', 'randpos', 'randx', 'randy', 'randz']
    type_pattern = '|'.join(types)

    # Pattern A: Anonymous Range: randx:0:100
    pat_a = rf"^({type_pattern}):(-?\d+):(-?\d+)(?::(\d+))?$"

    # Pattern B: Variable + Optional Range: randx_var or randx_var:0:100
    pat_b = rf"^({type_pattern})(_[^_:]+)(?::(-?\d+):(-?\d+)(?::(\d+))?)?$"
    
    # Pattern C: Anonymous Default: randx
    pat_c = f"^({type_pattern})$"
    
    match_a = re.match(pat_a, placeholder)
    match_b = re.match(pat_b, placeholder)
    match_c = re.match(pat_c, placeholder)
    
    p_type = None
    var_name = None
    min_val = None
    max_val = None
    decimals = 0 # Default to 0 decimals
    is_new_syntax = False
    
    if match_a:
        is_new_syntax = True
        p_type = match_a.group(1)
        min_val = float(match_a.group(2))
        max_val = float(match_a.group(3))
        if match_a.group(4):
            decimals = int(match_a.group(4))
            
    elif match_b:
        is_new_syntax = True
        p_type = match_b.group(1)
        # Extract var name (remove leading _)
        raw_var = match_b.group(2)
        if raw_var.startswith('_'):
            raw_var = raw_var[1:]
        
        # Construct unique variable name including type to avoid collisions
        # e.g. randx_myvar
        var_name = f"{p_type}_{raw_var}"
        
        if match_b.group(3):
            min_val = float(match_b.group(3))
            max_val = float(match_b.group(4))
            if match_b.group(5):
                decimals = int(match_b.group(5))
            
    elif match_c:
        is_new_syntax = True
        p_type = match_c.group(1)

    if is_new_syntax:
        val = ""
        
        def get_range(default_max, use_margin=False, is_z=False):
            if min_val is not None and max_val is not None:
                if is_z:
                    # Clamp Z max to MAX_ALTITUDE
                    capped_max = min(max_val, MAX_ALTITUDE)
                    # If user range start is higher than allowed max, ignore user range for Z
                    if min_val > capped_max:
                        return 0.0, float(MAX_ALTITUDE)
                    return min_val, capped_max
                return min_val, max_val
            
            start = CANVAS_MARGIN if use_margin else 0
            end = default_max - CANVAS_MARGIN if use_margin else default_max
            return start, end

        # Helper to generate coordinate with optional collision check
        def generate_coord(p_type_local, max_attempts=100):
            for _ in range(max_attempts):
                # Generate candidates
                lx, ux = get_range(CANVAS_WIDTH, use_margin=(p_type_local != 'randz'))
                ly, uy = get_range(CANVAS_HEIGHT, use_margin=(p_type_local != 'randz'))
                lz, uz = get_range(MAX_ALTITUDE, use_margin=False, is_z=True)

                cx = random.uniform(lx, ux)
                cy = random.uniform(ly, uy)
                cz = random.uniform(lz, uz)
                
                # Check collision only if obstacles provided and type involves position (not just Z or scalar X/Y if we want strictness)
                # Ideally check for all positional types
                if obstacles and p_type_local in ['randxy', 'randxyc', 'randxyz', 'randpos']:
                    if check_collision(cx, cy, obstacles):
                        continue # Retry
                
                return cx, cy, cz
            return cx, cy, cz # Fallback to last generated

        # Generate based on type
        rx, ry, rz = generate_coord(p_type)

        if p_type == 'randx':
            # Scalar randx/randy usually just one dimension, but we generated all 3. 
            # We strictly only care about X here. 
            # Note: Scalar randx doesn't do 2D collision check effectively because Y is unknown.
            # So we skip collision check for scalar types in generate_coord logic above (or implicit).
            # We'll just use the generated range logic directly for scalars to match previous behavior
            lower, upper = get_range(CANVAS_WIDTH)
            num = random.uniform(lower, upper)
            val = f"{num:.{decimals}f}"
            
        elif p_type == 'randy':
            lower, upper = get_range(CANVAS_HEIGHT)
            num = random.uniform(lower, upper)
            val = f"{num:.{decimals}f}"
            
        elif p_type == 'randz':
            lower, upper = get_range(MAX_ALTITUDE, is_z=True)
            num = random.uniform(lower, upper)
            val = f"{num:.{decimals}f}"
            
        elif p_type in ['randxy', 'randxyc', 'randxyz', 'randpos']:
            fmt = f"{{:.{decimals}f}}"
            sx = fmt.format(rx)
            sy = fmt.format(ry)
            sz = fmt.format(rz)
            
            if p_type == 'randxy':
                val = f"{sx} {sy}"
            elif p_type == 'randxyc':
                val = f"{sx}, {sy}"
            elif p_type == 'randxyz':
                val = f"{sx} {sy} {sz}"
            elif p_type == 'randpos':
                val = f"{sx}, {sy}, {sz}"
        
        # Return tuple
        return (var_name, val, var_name is None)

    return (None, None, False)


def find_composite_and_scalar_vars(text: str) -> tuple:
    """Find composite position variables and scalar coordinate variables.

    Composite types (randxy_var, randxyz_var, randpos_var, randxyc_var) take
    precedence. If a composite exists, its components define the scalar values.

    Args:
        text: Template text to scan

    Returns:
        Tuple of (composite_vars, scalar_groups, composite_var_names)
        - composite_vars: Dict mapping var_name to composite placeholder info
        - scalar_groups: Dict mapping var_name to scalar coordinate placeholders
        - composite_var_names: Set of variable names that have composites
    """
    # Find composite types: randxy_var, randxyz_var, randpos_var, randxyc_var
    composite_pattern = r'\{(randxy|randxyz|randpos|randxyc)(_[^:}]+)(?::([^:}]+):([^:}]+)(?::([^}]+))?)?\}'
    composite_matches = re.findall(composite_pattern, text)

    composite_vars = {}
    composite_var_names = set()

    for match in composite_matches:
        comp_type = match[0]  # randxy, randxyz, randpos, randxyc
        var_suffix = match[1]  # _varname

        # Remove leading underscore to get clean variable name
        var_name = var_suffix[1:] if var_suffix.startswith('_') else var_suffix
        composite_var_names.add(var_name)

        # Reconstruct full placeholder
        if match[2]:  # Has range definition
            if match[4]:  # Has decimals
                full_placeholder = f"{comp_type}{var_suffix}:{match[2]}:{match[3]}:{match[4]}"
            else:
                full_placeholder = f"{comp_type}{var_suffix}:{match[2]}:{match[3]}"
        else:
            full_placeholder = f"{comp_type}{var_suffix}"

        if var_name not in composite_vars:
            composite_vars[var_name] = {
                'type': comp_type,
                'placeholder': full_placeholder
            }

    # Find scalar coordinate variables: randx_*, randy_*, randz_*
    scalar_pattern = r'\{(rand[xyz])(_[^:}]+)(?::([^:}]+):([^:}]+)(?::([^}]+))?)?\}'
    scalar_matches = re.findall(scalar_pattern, text)

    scalar_groups = {}
    for match in scalar_matches:
        coord_type = match[0]  # randx, randy, or randz
        var_suffix = match[1]  # _varname

        # Remove leading underscore to get clean variable name
        var_name = var_suffix[1:] if var_suffix.startswith('_') else var_suffix

        # Skip if this variable has a composite (composite takes precedence)
        if var_name in composite_var_names:
            continue

        if var_name not in scalar_groups:
            scalar_groups[var_name] = {}

        # Reconstruct full placeholder
        if match[2]:  # Has range definition
            if match[4]:  # Has decimals
                full_placeholder = f"{coord_type}{var_suffix}:{match[2]}:{match[3]}:{match[4]}"
            else:
                full_placeholder = f"{coord_type}{var_suffix}:{match[2]}:{match[3]}"
        else:
            full_placeholder = f"{coord_type}{var_suffix}"

        # Map coordinate type (x, y, or z)
        coord_key = coord_type[-1]  # Extract 'x', 'y', or 'z'
        scalar_groups[var_name][coord_key] = full_placeholder

    # Filter scalar groups to only include those with at least x AND y (z is optional)
    scalar_coordinated = {
        var_name: coords
        for var_name, coords in scalar_groups.items()
        if 'x' in coords and 'y' in coords
    }

    return composite_vars, scalar_coordinated, composite_var_names


def generate_coordinated_position(x_placeholder: str, y_placeholder: str, z_placeholder: Optional[str],
                                  obstacles: Optional[List[Dict[str, Any]]] = None,
                                  max_attempts: int = 100) -> tuple:
    """Generate coordinated x, y, z values with collision avoidance.

    Args:
        x_placeholder: The randx_var placeholder (e.g., 'randx_pos' or 'randx_pos:0:100')
        y_placeholder: The randy_var placeholder (e.g., 'randy_pos' or 'randy_pos:0:100')
        z_placeholder: Optional randz_var placeholder
        obstacles: List of obstacles to avoid
        max_attempts: Maximum attempts to find collision-free position

    Returns:
        Tuple of (x_value, y_value, z_value, decimals) as strings formatted appropriately
    """
    # Parse ranges and decimals from each placeholder
    def parse_range_and_decimals(placeholder: str, default_min: float, default_max: float, use_margin: bool = True):
        # Match pattern like randx_var:min:max:decimals
        match = re.match(r'^rand[xyz]_[^:]+:(-?\d+\.?\d*):(-?\d+\.?\d*)(?::(\d+))?$', placeholder)
        if match:
            min_val = float(match.group(1))
            max_val = float(match.group(2))
            decimals = int(match.group(3)) if match.group(3) else 0
        else:
            # Use defaults
            if use_margin:
                min_val = default_min + CANVAS_MARGIN
                max_val = default_max - CANVAS_MARGIN
            else:
                min_val = default_min
                max_val = default_max
            decimals = 0

        return min_val, max_val, decimals

    # Parse each coordinate
    x_min, x_max, x_decimals = parse_range_and_decimals(x_placeholder, 0.0, CANVAS_WIDTH, use_margin=True)
    y_min, y_max, y_decimals = parse_range_and_decimals(y_placeholder, 0.0, CANVAS_HEIGHT, use_margin=True)

    # Use the maximum decimals across all coordinates for consistency
    decimals = max(x_decimals, y_decimals)

    if z_placeholder:
        z_min, z_max, z_decimals = parse_range_and_decimals(z_placeholder, 0.0, MAX_ALTITUDE, use_margin=False)
        # Cap z to MAX_ALTITUDE
        z_max = min(z_max, MAX_ALTITUDE)
        decimals = max(decimals, z_decimals)
    else:
        z_min, z_max = 0.0, MAX_ALTITUDE

    # Generate position with collision avoidance
    for _ in range(max_attempts):
        x = random.uniform(x_min, x_max)
        y = random.uniform(y_min, y_max)
        z = random.uniform(z_min, z_max)

        # Check collision if obstacles provided
        if obstacles and check_collision(x, y, obstacles):
            continue  # Try again

        # Format with appropriate decimals
        if decimals > 0:
            return f"{x:.{decimals}f}", f"{y:.{decimals}f}", f"{z:.{decimals}f}"
        else:
            return f"{round(x)}", f"{round(y)}", f"{round(z)}"

    # Fallback: return last generated (couldn't find collision-free spot)
    if decimals > 0:
        return f"{x:.{decimals}f}", f"{y:.{decimals}f}", f"{z:.{decimals}f}"
    else:
        return f"{round(x)}", f"{round(y)}", f"{round(z)}"


def normalize_duplicate_drone_prefixes(text: str) -> str:
    """Collapse adjacent duplicate human-readable Drone labels."""
    return re.sub(r'\b(Drone)\s+Drone\b', r'\1', text, flags=re.IGNORECASE)


def substitute_placeholders(text: str, values: Dict[str, Any],
                          random_cache: Optional[Dict[str, Any]] = None) -> tuple:
    """Substitute all placeholders in text with values

    Handles:
    - Regular placeholders: {drone_id} -> "drone-001"
    - Random placeholders (sticky for predefined/named, per-occurrence for anonymous)
    - Composite position variables (randxy_var, randxyz_var, etc.) with collision avoidance
    - Coordinated randx_var/randy_var/randz_var with collision avoidance
    - Priority: Composite types take precedence over scalar coordinates

    Args:
        text: Text containing placeholders
        values: Dictionary mapping placeholder names to values
        random_cache: Optional dict to store/reuse random values for consistency

    Returns:
        Tuple of (substituted_text, updated_random_cache)
    """
    cache = random_cache if random_cache is not None else {}
    obstacles = values.get('_context_obstacles') # Extract obstacles if available

    # Pre-scan for composite and scalar coordinate variables
    composite_vars, scalar_groups, composite_var_names = find_composite_and_scalar_vars(text)

    # First, handle composite types and extract their components
    for var_name, comp_info in composite_vars.items():
        comp_type = comp_info['type']
        comp_placeholder = comp_info['placeholder']

        cache_key_composite = f"random_{comp_placeholder}"

        # Check if already cached
        if cache_key_composite not in cache:
            # Generate the composite value using existing logic
            _, dynamic_value, _ = parse_dynamic_random(comp_placeholder, obstacles=obstacles)

            if dynamic_value is not None:
                cache[cache_key_composite] = dynamic_value

                # Extract individual components and cache them for scalar variables
                # This ensures randx_var, randy_var, randz_var use the same values
                if comp_type == 'randxy':
                    # Format: "x y"
                    parts = str(dynamic_value).split()
                    if len(parts) >= 2:
                        cache[f"random_randx_{var_name}"] = parts[0]
                        cache[f"random_randy_{var_name}"] = parts[1]

                elif comp_type == 'randxyc':
                    # Format: "x, y" or "x,y"
                    parts = str(dynamic_value).replace(' ', '').split(',')
                    if len(parts) >= 2:
                        cache[f"random_randx_{var_name}"] = parts[0]
                        cache[f"random_randy_{var_name}"] = parts[1]

                elif comp_type == 'randxyz':
                    # Format: "x y z"
                    parts = str(dynamic_value).split()
                    if len(parts) >= 3:
                        cache[f"random_randx_{var_name}"] = parts[0]
                        cache[f"random_randy_{var_name}"] = parts[1]
                        cache[f"random_randz_{var_name}"] = parts[2]

                elif comp_type == 'randpos':
                    # Format: "x, y, z" or "x,y,z"
                    parts = str(dynamic_value).replace(' ', '').split(',')
                    if len(parts) >= 3:
                        cache[f"random_randx_{var_name}"] = parts[0]
                        cache[f"random_randy_{var_name}"] = parts[1]
                        cache[f"random_randz_{var_name}"] = parts[2]

    # Second, handle scalar coordinated groups (only if no composite exists for same var)
    for var_name, coords in scalar_groups.items():
        x_placeholder = coords.get('x')
        y_placeholder = coords.get('y')
        z_placeholder = coords.get('z')

        # Check if already cached (might be set by composite)
        cache_key_x = f"random_randx_{var_name}"
        cache_key_y = f"random_randy_{var_name}"
        cache_key_z = f"random_randz_{var_name}"

        if cache_key_x not in cache:
            # Generate coordinated position with collision avoidance
            x_val, y_val, z_val = generate_coordinated_position(
                x_placeholder, y_placeholder, z_placeholder, obstacles
            )

            # Cache the values
            cache[cache_key_x] = x_val
            cache[cache_key_y] = y_val
            if z_placeholder:
                cache[cache_key_z] = z_val

    def replace_match(match: re.Match) -> str:
        placeholder = match.group(1)

        # Direct substitution for provided scalar values
        if placeholder in values:
            return str(values[placeholder])

        # Predefined random placeholders (sticky by placeholder name)
        info = get_placeholder_info(placeholder)
        if info and info.get('type') == 'random_float':
            if placeholder not in cache:
                cache[placeholder] = generate_random_value(info)
            return str(cache[placeholder])

        # Dynamic random placeholders
        var_name, dynamic_value, is_anonymous = parse_dynamic_random(placeholder, obstacles=obstacles)
        if dynamic_value is not None:
            if is_anonymous:
                # Anonymous: new value every occurrence, never cached
                return str(dynamic_value)
            cache_key = f"random_{var_name}"
            if cache_key not in cache:
                cache[cache_key] = dynamic_value
            return str(cache[cache_key])

        # Check for references to previously defined named variables (without range)
        # e.g. {randint_name} or {random_name} referring to a cached value
        
        # Match randint_varname
        ref_match_int = re.match(r'^randint_([a-zA-Z_][a-zA-Z0-9_]*)$', placeholder)
        if ref_match_int:
            var_name = ref_match_int.group(1)
            cache_key = f"random_{var_name}"
            if cache_key in cache:
                return str(cache[cache_key])
                
        # Match random_varname
        ref_match_float = re.match(r'^random_([a-zA-Z_][a-zA-Z0-9_]*)$', placeholder)
        if ref_match_float:
            var_name = ref_match_float.group(1)
            cache_key = f"random_{var_name}"
            if cache_key in cache:
                return str(cache[cache_key])

        # Unknown placeholder, leave untouched
        return match.group(0)

    substituted_text = re.sub(r'\{([^}]+)\}', replace_match, text)
    substituted_text = normalize_duplicate_drone_prefixes(substituted_text)
    return substituted_text, cache


def get_missing_placeholders(text: str, provided_values: Dict[str, Any]) -> List[str]:
    """Find placeholders in text that don't have provided values

    Args:
        text: Text containing placeholders
        provided_values: Dictionary of provided values

    Returns:
        List of missing placeholder names
    """
    found_placeholders = find_placeholders_in_text(text)
    missing = []
    for placeholder in found_placeholders:
        if placeholder not in provided_values:
            missing.append(placeholder)
    return missing


def generate_example_content() -> str:
    """Generate example template content showing placeholder usage

    Returns:
        Example content string
    """
    return """Drone {drone_id} should take off to {altitude} meters altitude, then fly to position ({position_x}, {position_y}, {position_z}). After arriving, hover for {hover_time} seconds, then return home and land."""


def generate_example_alias() -> List[str]:
    """Generate example aliases showing placeholder usage

    Returns:
        List of example alias strings
    """
    return [
        "make {drone_name} fly to {position_x},{position_y},{position_z} at {altitude}m",
        "{drone_name} takeoff {altitude} meters, go to ({position_x}, {position_y}, {position_z})",
        "drone {drone_name}: altitude {altitude}, position {position_x} {position_y} {position_z}",
    ]


def create_placeholder_help_text() -> str:
    """Create comprehensive help text for placeholders

    Returns:
        Help text string
    """
    help_lines = [
        "AVAILABLE PLACEHOLDERS:",
        "=" * 60,
        ""
    ]

    categories = get_placeholder_categories()
    for category, placeholders in sorted(categories.items()):
        help_lines.append(f"\n{category}:")
        help_lines.append("-" * 40)
        for placeholder in sorted(placeholders):
            info = PLACEHOLDER_DEFINITIONS[placeholder]
            help_lines.append(f"  {{{placeholder}}}")
            help_lines.append(f"    → {info['description']}")
            help_lines.append(f"    Example: {info['example']}")
            help_lines.append("")

    help_lines.extend([
        "",
        "DYNAMIC RANDOM PLACEHOLDERS:",
        "-" * 40,
        "  {random:min:max}",
        "    → Random float between min and max (1 decimal)",
        "    Example: {random:10:50} → 37.4",
        "",
        "  {random:min:max:decimals}",
        "    → Random float with specified decimal places",
        "    Example: {random:0:100:2} → 42.73",
        "",
        "  {randint:min:max}",
        "    → Random integer between min and max",
        "    Example: {randint:1:10} → 7",
        "",
        "",
        "USAGE:",
        "- Use {placeholder_name} in content and aliases",
        "- Regular placeholders are replaced with user-provided values",
        "- Random placeholders generate new values each time",
        "- Indexed placeholders for multi-entity tasks:",
        "  'Drones {drone_1_name}, {drone_2_name}, and {drone_3_name} form triangle'",
        "- Example: 'Drone {drone_id} to ({random_x}, {random_y}, {random_altitude})'",
        "  becomes: 'Drone drone-001 to (127.5, 89.3, 15.0)'",
        "- Dynamic example: 'Fly to altitude {random:5:30:1} meters'",
        "  becomes: 'Fly to altitude 18.7 meters'",
    ])

    return "\n".join(help_lines)
