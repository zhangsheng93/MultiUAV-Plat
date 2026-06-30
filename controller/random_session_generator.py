#!/usr/bin/env python3
"""
MultiUAV-Plat Control System - Random Session Generator

This module provides functionality for generating random session data including:
- Drones with randomized positions and properties
- Targets of various types (fixed, moving, waypoint, circle, polygon)
- Obstacles with different shapes and sizes
- Environment settings

Author: MultiUAV-Plat Control System
Version: Provided by application entrypoint
"""

import random
import logging
import math
from typing import Dict, Any, List, Tuple, Optional, Callable, Union
from shapely.geometry import Point, Polygon as ShapelyPolygon
from shapely.ops import unary_union
from utils import create_new_name


# ============================================================================
# Configuration Constants - Modify these to adjust generation behavior
# ============================================================================
#
# DEVELOPER GUIDE:
# ----------------
# This section contains all configurable parameters for random session generation.
# All magic numbers have been extracted here for easy modification.
#
# Main Configuration Categories:
# 1. Area Settings - Define operational area dimensions
# 2. Item Size Ranges - Control min/max sizes for drones, targets, obstacles
# 3. Target Size Multipliers - Scale targets based on size hints
# 4. Additional Margins - Safety buffers for collision avoidance
# 5. Drone Settings - Model names, altitudes, speeds, battery levels
# 6. Target Settings - Waypoint charges, velocity ranges, tracking ratios
# 7. Obstacle Settings - Types, placement areas, margins
# 8. Position Generation - Placement algorithms and fallback behavior
# 9. Environment Settings - Weather, temperature, wind, visibility ranges
# 10. Task Configurations - Mission-specific target patterns
#
# To customize generation behavior, simply modify the values below.
# The code will automatically use your changes without any modifications needed.
#
# ============================================================================

# Base area size (standard default)
BASE_AREA_WIDTH = 1024.0
BASE_AREA_HEIGHT = 768.0

# Minimum area dimensions
MIN_AREA_WIDTH = 10.0
MIN_AREA_HEIGHT = 10.0

# ============================================================================
# Item Size Ranges - Understanding the Sizing System
# ============================================================================
#
# HOW ITEM SIZES ARE CALCULATED:
# -------------------------------
# The final size of any item is determined by THREE components:
#
# 1. BASE SIZE (defined below in ITEM_SIZE_RANGES)
#    - These are the min/max sizes when area = BASE_AREA (1024x768)
#    - Defines the fundamental size range for each item type
#
# 2. SCALE FACTOR (calculated dynamically based on area)
#    - scale_factor = sqrt(min(current_area_width / BASE_AREA_WIDTH,
#                              current_area_height / BASE_AREA_HEIGHT))
#    - Uses square-root scaling so objects grow more gently as the area increases
#    - Example: 2048x1536 area → scale_factor = sqrt(2.0) ≈ 1.41
#
# 3. SIZE MULTIPLIER (from TARGET_SIZE_MULTIPLIERS, for targets only)
#    - Applied based on size hint: 'small', 'normal', 'medium', 'large', etc.
#    - Allows fine-tuning within the scaled range
#    - Example: 'large' multiplier = (3.0, 4.0) → 3-4x the base size
#
# FINAL SIZE FORMULA:
# -------------------
# For Both Targets and Obstacles (unified sizing system):
#   final_radius = random.uniform(
#       base_min * scale_factor * multiplier_min,
#       base_max * scale_factor * multiplier_max
#   )
#
# Where:
#   - base_min/max: From ITEM_SIZE_RANGES
#   - scale_factor: sqrt(min(area_width/BASE_WIDTH, area_height/BASE_HEIGHT))
#   - multiplier_min/max: From SIZE_MULTIPLIERS
#
# EXAMPLE CALCULATION:
# --------------------
# Target Type: 'circle' with size hint 'large'
# Area: 2048x1536 (2x the base area)
#
# Step 1: Get base size from ITEM_SIZE_RANGES['target']['circle']
#         base_min = 5, base_max = 60
#
# Step 2: Calculate scale factor
#         scale_factor = sqrt(min(2048/1024, 1536/768)) = sqrt(2.0) ≈ 1.41
#
# Step 3: Get size multiplier from TARGET_SIZE_MULTIPLIERS['large']
#         mult_min = 3.0, mult_max = 4.0
#
# Step 4: Calculate final size range
#         final_min = 5 * 1.41 * 3.0 ≈ 21
#         final_max = 60 * 1.41 * 4.0 ≈ 339
#         final_radius = random.uniform(21, 339)
#
# GUIDELINES FOR CHOOSING SIZES:
# -------------------------------
# 1. Consider the PURPOSE of the item:
#    - Small fixed targets (5-15): Individual points of interest
#    - Large circles (5-60): Search areas, patrol zones
#    - Large polygons (8-70): Mission zones, restricted areas
#
# 2. Ensure VISUAL CLARITY:
#    - Items should be visible but not overlap excessively
#    - Larger areas can accommodate larger items
#    - Use scale_factor to maintain proportions
#
# 3. Allow for COLLISION AVOIDANCE:
#    - Additional margins (TARGET_ADDITIONAL_MARGINS) are added
#    - Buffer zones prevent items from overlapping
#    - Larger items need larger buffers
#
# 4. Balance QUANTITY vs SIZE:
#    - Many small items: Good for detailed missions
#    - Few large items: Good for area-based missions
#    - The generator will skip items if space runs out
#
# ============================================================================

# Item size ranges (min_radius, max_radius) for BASE_AREA (1024x768)
# These values will be scaled automatically based on actual area size
ITEM_SIZE_RANGES = {
    'drone': {
        'buffer': 5,  # Safety buffer for drone placement (radius in meters)
    },
    'target': {
        # Small point targets (individual objectives)
        'fixed': (5, 15),      # Stationary points of interest
        'moving': (5, 15),     # Mobile targets to track
        'waypoint': (5, 15),   # Charging stations, checkpoints

        # Area targets (zones to search or patrol)
        'circle': (5, 60),     # Circular search/patrol areas
        'polygon': (8, 70),    # Polygonal mission zones (largest)
    },
    'obstacle': {
        # Small obstacles (individual hazards)
        'point': (5, 15),      # Small point hazards
        'circle': (10, 40),     # Circular no-fly zones

        # Larger obstacles (area hazards)
        'ellipse': {
            'width': (10, 50),   # Ellipse width (shorter dimension)
            'length': (8, 50),   # Ellipse length (longer dimension)
        },
        'polygon': (10, 50),   # Polygonal restricted areas
    }
}
# Note: All sizes automatically scale with area size via scale_factor
# Larger operational areas will have proportionally larger items

# ============================================================================
# Target Size Multipliers - Fine-tuning Target Sizes
# ============================================================================
#
# These multipliers are applied ON TOP of the base size and scale factor.
# They allow the same target type to appear in different sizes based on mission needs.
#
# Usage: When creating a target, specify a size hint in the task configuration:
#   {'type': 'circle', 'size': 'large'}  ← 'large' is the size hint
#
# The multiplier is then applied to the scaled base size:
#   final_size = base_size * scale_factor * multiplier
#
# MULTIPLIER VALUES EXPLAINED:
# ---------------------------
# Each multiplier is a tuple: (min_multiplier, max_multiplier)
# The actual multiplier is randomly chosen between these values.
#
# Examples (assuming base size of 10 and scale factor of 1.0):
#   'small':        0.8-1.0x  → final size: 8-10   (smaller than base)
#   'normal':       1.0-1.5x  → final size: 10-15  (baseline)
#   'medium':       1.5-2.0x  → final size: 15-20  (50-100% larger)
#   'medium_large': 2.0-2.5x  → final size: 20-25  (2-2.5x larger)
#   'large':        3.0-4.0x  → final size: 30-40  (3-4x larger)
#
# WHEN TO USE EACH SIZE:
# ---------------------
# 'small':        Individual targets, precise objectives, high-detail missions
# 'normal':       Standard mission objectives, default size
# 'medium':       Important targets, medium patrol zones
# 'medium_large': Large patrol areas, significant zones of interest
# 'large':        Major search areas, primary mission zones, area coverage
#
# ============================================================================

SIZE_MULTIPLIERS = {
    'large': (3.0, 4.0),          # 3-4x: Largest targets (major search areas)
    'medium_large': (2.0, 2.5),   # 2-2.5x: Large patrol zones
    'medium': (1.5, 2.0),         # 1.5-2x: Medium-sized objectives
    'normal': (1.0, 1.5),         # 1-1.5x: Standard size (baseline)
    'small': (0.8, 1.0)           # 0.8-1x: Smallest targets (precise points)
}

# ============================================================================
# Additional Margins - Collision Avoidance and Safety Buffers
# ============================================================================
#
# WHY MARGINS ARE NEEDED:
# -----------------------
# When placing items in the operational area, we need to ensure they don't
# overlap or get too close to each other. Additional margins create "buffer zones"
# around each item for collision avoidance.
#
# HOW MARGINS WORK:
# -----------------
# The total buffer radius for placement is:
#   buffer_radius = item_radius + additional_margin
#
# This buffer is used to check if a position is clear before placing an item.
# No two items' buffers can overlap.
#
# MARGIN SIZE GUIDELINES:
# ----------------------
# - Small point targets (2.0): Minimal spacing, allows dense placement
# - Area targets (12.0-20.0): Larger spacing for visual clarity
# - Larger items need larger margins to prevent visual clutter
#
# Example:
#   Circle target with radius=50 and margin=12.0
#   → Total buffer = 50 + 12 = 62 meters
#   → Next item must be at least 62m away from this circle's center
#
# ============================================================================

# Additional margins for different target types (added to radius for spacing)
TARGET_ADDITIONAL_MARGINS = {
    'waypoint': 2.0,    # Small point targets, can be closer together
    'fixed': 2.0,       # Small point targets, can be closer together
    'moving': 2.0,      # Small point targets, can be closer together
    'circle': 5.0,     # Medium spacing for circular areas
    'polygon': 8.0,    # Large spacing for polygonal zones (largest targets)
    'fallback': 8.0    # Default margin if target type unknown
}

# Additional margins for different obstacle types (added to radius/size for spacing)
OBSTACLE_ADDITIONAL_MARGINS = {
    'point': 5.0,       # Small point hazards, moderate spacing
    'circle': 5.0,     # Circular no-fly zones, larger spacing
    'ellipse': 8.0,    # Elliptical obstacles, larger spacing
    'polygon': 8.0     # Polygonal restricted areas, maximum spacing
}
# Note: Obstacles are placed in half the area (OBSTACLE_AREA_DIVISOR = 2.0)
# to avoid cluttering the full operational zone

# Drone generation settings
DRONE_MODELS = [
    "Model-A", "Model-B", "Model-C", "Model-D", "Model-E",
    "Model-X1", "Model-X2", "Model-X3", "Model-X4", "Model-X5"
]

DRONE_GROUND_PROBABILITY = 0.95  # Probability of drone starting at z=0
DRONE_MIN_ALTITUDE = 5.0
DRONE_MAX_ALTITUDE = 100.0
DRONE_MIN_SPEED = 10.0
DRONE_MAX_SPEED = 35.0
DRONE_MIN_MAX_ALTITUDE = 200.0
DRONE_MAX_MAX_ALTITUDE = 500.0
DRONE_MIN_BATTERY = 60.0
DRONE_MAX_BATTERY = 100.0
DRONE_CLUSTER_SPACING_MULTIPLIER = 10
DRONE_CLUSTER_MIN_COLUMNS = 2
DRONE_CLUSTER_MIN_ROWS = 2


# Target generation settings
TARGET_WAYPOINT_CAPACITY_PROBABILITY = 0.3  # Probability of waypoint having capacity
TARGET_WAYPOINT_MIN_CAPACITY = 1
TARGET_WAYPOINT_MAX_CAPACITY = 5
TARGET_WAYPOINT_MIN_CHARGE = 10.0
TARGET_WAYPOINT_MAX_CHARGE = 50.0

# Target tracking task settings
TARGET_TRACKING_MOVING_RATIO = 0.7  # Ratio of moving targets in target_tracking task

# ============================================================================
# Task-Specific Target Configurations
# ============================================================================
# These configurations define how targets and obstacles are generated for different
# mission types. Use 'target_specs' and 'obstacle_specs' entries (with optional
# 'weight' keys) to bias random selection; weights are automatically normalized.
# Omit weights and entries are cycled deterministically.

# Area Search Task Configuration
# Mission: Search large areas for points of interest
AREA_SEARCH_CONFIG = {
    'target_specs': [
        {'type': 'circle', 'size': 'large', 'weight': 3},
        {'type': 'polygon', 'size': 'large', 'weight': 4},
        {'type': 'circle', 'size': 'medium_large', 'weight': 2},
        {'type': 'polygon', 'size': 'medium_large', 'weight': 3},
        {'type': 'circle', 'size': 'medium', 'weight': 1},
        {'type': 'polygon', 'size': 'medium', 'weight': 1},
        {'type': 'waypoint', 'size': 'small', 'weight': 1}
    ],
    'obstacle_specs': [
        {'type': 'circle', 'size': 'medium', 'weight': 3},
        {'type': 'polygon', 'size': 'medium', 'weight': 3},
        {'type': 'ellipse', 'size': 'medium', 'weight': 1},
        {'type': 'circle', 'size': 'normal', 'weight': 2},
        {'type': 'polygon', 'size': 'normal', 'weight': 2},
        {'type': 'ellipse', 'size': 'normal', 'weight': 1},
        {'type': 'circle', 'size': 'medium_large', 'weight': 1},
        {'type': 'polygon', 'size': 'medium_large', 'weight': 1},
        {'type': 'ellipse', 'size': 'medium_large', 'weight': 1},
        {'type': 'circle', 'size': 'small', 'weight': 1}
    ],
    'description': 'Large circular and polygonal search areas'
}

# Area Assignment and Patrol Task Configuration
# Mission: Assign specific areas to drones for patrol
AREA_ASSIGNMENT_PATROL_CONFIG = {
    'target_specs': [
        {'type': 'circle', 'size': 'medium_large', 'weight': 3},
        {'type': 'polygon', 'size': 'medium_large', 'weight': 3},
        {'type': 'circle', 'size': 'medium', 'weight': 3},
        {'type': 'polygon', 'size': 'medium', 'weight': 3},
        {'type': 'circle', 'size': 'normal', 'weight': 1},
        {'type': 'polygon', 'size': 'normal', 'weight': 1},
        {'type': 'waypoint', 'size': 'small', 'weight': 1}
    ],
    'obstacle_specs': [
        {'type': 'circle', 'size': 'normal', 'weight': 2},
        {'type': 'polygon', 'size': 'normal', 'weight': 3},
        {'type': 'point', 'size': 'small', 'weight': 1},
        {'type': 'ellipse', 'size': 'medium', 'weight': 1},
        {'type': 'circle', 'size': 'medium', 'weight': 1},
        {'type': 'polygon', 'size': 'medium', 'weight': 1},
        {'type': 'circle', 'size': 'small', 'weight': 1}
    ],
    'description': 'Medium-large patrol zones'
}

# Target Assignment Task Configuration
# Mission: Assign specific fixed targets to drones
TARGET_ASSIGNMENT_CONFIG = {
    'target_specs': [
        {'type': 'fixed', 'size': 'small', 'weight': 1}
    ],
    'obstacle_specs': [
        {'type': 'circle', 'size': 'normal', 'weight': 2},
        {'type': 'polygon', 'size': 'normal', 'weight': 3},
        {'type': 'point', 'size': 'small', 'weight': 1},
        {'type': 'ellipse', 'size': 'normal', 'weight': 1},
        {'type': 'polygon', 'size': 'medium_large', 'weight': 1},
        {'type': 'circle', 'size': 'medium_large', 'weight': 1},
        {'type': 'polygon', 'size': 'medium', 'weight': 1},
        {'type': 'circle', 'size': 'medium', 'weight': 1}
    ],
    'description': 'Small fixed-position targets'
}

# Target Tracking Task Configuration
# Mission: Track moving targets with occasional fixed reference points
TARGET_TRACKING_CONFIG = {
    'moving_ratio': 0.7,  # 70% moving, 30% fixed
    'target_specs': [
        {'type': 'moving', 'size': 'small', 'weight': 1, 'category': 'moving'},
        {'type': 'fixed', 'size': 'small', 'weight': 1, 'category': 'fixed'}
    ],
    'obstacle_specs': [
        {'type': 'circle', 'size': 'normal', 'weight': 2},
        {'type': 'polygon', 'size': 'normal', 'weight': 3},
        {'type': 'point', 'size': 'small', 'weight': 1},
        {'type': 'ellipse', 'size': 'normal', 'weight': 1}
    ],
    'shuffle': True,
    'description': 'Mix of moving and fixed targets'
}

# Default/Others Task Configuration
# Mission: General purpose with variety of target types
DEFAULT_TASK_CONFIG = {
    'target_specs': [
        {'type': 'fixed', 'size': 'small', 'weight': 4},
        {'type': 'moving', 'size': 'small', 'weight': 0},
        {'type': 'waypoint', 'size': 'small', 'weight': 2},
        {'type': 'circle', 'size': 'medium_large', 'weight': 2},
        {'type': 'polygon', 'size': 'medium_large', 'weight': 1}
    ],
    'obstacle_specs': [
        {'type': 'point', 'size': 'small', 'weight': 1},
        {'type': 'circle', 'size': 'normal', 'weight': 2},
        {'type': 'polygon', 'size': 'medium', 'weight': 2},
        {'type': 'ellipse', 'size': 'normal', 'weight': 2}
    ],
    'shuffle': True,
    'description': 'Diverse mix of all target types'
}


TASK_CONFIGS = {
    'area_search': AREA_SEARCH_CONFIG,
    'area_assignment_and_patrol': AREA_ASSIGNMENT_PATROL_CONFIG,
    'target_assignment': TARGET_ASSIGNMENT_CONFIG,
    'target_tracking': TARGET_TRACKING_CONFIG,
    'others': DEFAULT_TASK_CONFIG,
    'default': DEFAULT_TASK_CONFIG
}

# Moving target velocity ranges
MOVING_TARGET_MIN_VELOCITY_X = -5.0
MOVING_TARGET_MAX_VELOCITY_X = 5.0
MOVING_TARGET_MIN_VELOCITY_Y = -5.0
MOVING_TARGET_MAX_VELOCITY_Y = 5.0
MOVING_TARGET_MIN_VELOCITY_Z = -1.0
MOVING_TARGET_MAX_VELOCITY_Z = 1.0

# Moving target duration settings (for velocity-based ping-pong mode)
MOVING_TARGET_MIN_DURATION = 5.0   # Minimum time before reversing direction (seconds)
MOVING_TARGET_MAX_DURATION = 20.0  # Maximum time before reversing direction (seconds)

# Obstacle generation settings
OBSTACLE_TYPES = ["point", "circle", "polygon", "ellipse"]
OBSTACLE_AREA_DIVISOR = 2.0  # Obstacles are placed in half the area (half_width, half_height)

# Position generation settings
MAX_POSITION_ATTEMPTS = 200  # Maximum random attempts before grid fallback
GRID_FALLBACK_DIVISIONS = 10.0  # Number of divisions for grid fallback
MAX_ENTITY_GENERATION_ATTEMPTS = 50  # Retry count for placing drones/targets/obstacles

# Environment generation settings
WEATHER_OPTIONS = [
    'clear', 'partly_cloudy', 'cloudy', 'rain', 'heavy_rain',
    'snow', 'fog', 'windy', 'storm'
]
WIND_DIRECTIONS = [
    'north', 'northeast', 'east', 'southeast',
    'south', 'southwest', 'west', 'northwest'
]
TEMPERATURE_MIN = 12.0
TEMPERATURE_MAX = 26.0
HUMIDITY_MIN = 35.0
HUMIDITY_MAX = 65.0
PRESSURE_MIN = 990.0
PRESSURE_MAX = 1030.0
WIND_SPEED_MIN = 0.0
WIND_SPEED_MAX = 8.0
VISIBILITY_MIN = 8000.0
VISIBILITY_MAX = 15000.0


class RandomSessionGenerator:
    """
    Generator for creating random session data with drones, targets, and obstacles.

    This class handles the generation of randomized entities within a specified area,
    ensuring proper spacing between items and adherence to task-specific constraints.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the random session generator.

        Args:
            logger: Optional logger instance. If not provided, uses the root logger.
        """
        self.logger = logger or logging.getLogger(__name__)

    def generate_session_data(
        self,
        drone_count: int,
        target_count: int,
        obstacle_count: int,
        area_width: float = 1024.0,
        area_height: float = 768.0,
        task_type: str = 'others',
        do_not_scatter_drones: bool = False
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate complete session data with drones, targets, and obstacles.

        Args:
            drone_count: Number of drones to generate
            target_count: Number of targets to generate
            obstacle_count: Number of obstacles to generate
            area_width: Width of the operational area
            area_height: Height of the operational area
            task_type: Type of mission task (affects entity distribution)
            do_not_scatter_drones: Whether drones should be clustered near the
                lower-left corner instead of distributed across the full area

        Returns:
            Dictionary containing lists of drones, targets, and obstacles
        """
        try:
            area_width = max(MIN_AREA_WIDTH, float(area_width))
        except (TypeError, ValueError):
            area_width = BASE_AREA_WIDTH
        try:
            area_height = max(MIN_AREA_HEIGHT, float(area_height))
        except (TypeError, ValueError):
            area_height = BASE_AREA_HEIGHT

        used_positions: List[Tuple[float, float, float]] = []
        generated_names: List[str] = []
        task_profile = (task_type or 'others').lower()

        drones = []
        targets = []
        obstacles = []

        def generate_drones() -> None:
            for i in range(drone_count):
                payload = self._attempt_item_generation(
                    lambda idx=i: self._random_drone_payload(
                        idx,
                        used_positions,
                        area_width,
                        area_height,
                        task_profile,
                        generated_names,
                        drone_count=drone_count,
                        do_not_scatter_drones=do_not_scatter_drones
                    ),
                    f"drone {i + 1}"
                )
                if payload:
                    drones.append(payload)

        def generate_targets() -> None:
            target_specs = self._plan_target_specs(task_profile, target_count)
            for idx, spec in enumerate(target_specs):
                payload = self._attempt_item_generation(
                    lambda idx=idx, spec=spec: self._random_target_payload(
                        idx, spec, used_positions, area_width, area_height, generated_names
                    ),
                    f"target {idx + 1}"
                )
                if payload:
                    targets.append(payload)

        def generate_obstacles() -> None:
            obstacle_specs_plan = self._plan_obstacle_specs(task_profile, obstacle_count)
            for i, obstacle_spec in enumerate(obstacle_specs_plan):
                payload = self._attempt_item_generation(
                    lambda idx=i, spec=obstacle_spec: self._random_obstacle_payload(
                        idx, used_positions, area_width, area_height, generated_names, spec
                    ),
                    f"obstacle {i + 1}"
                )
                if payload:
                    obstacles.append(payload)

        if do_not_scatter_drones:
            generate_drones()
            generate_targets()
            generate_obstacles()
        else:
            generate_targets()
            generate_obstacles()
            generate_drones()

        return {
            'drones': drones,
            'targets': targets,
            'obstacles': obstacles
        }

    def generate_environment_payload(self, session_name: str) -> Dict[str, Any]:
        """
        Generate a default environment payload with random weather conditions.

        Args:
            session_name: Name of the session (used in environment name/description)

        Returns:
            Dictionary containing environment configuration
        """
        return {
            'name': f"{session_name} Environment",
            'description': f"Auto-generated environment for {session_name}",
            'weather': random.choice(WEATHER_OPTIONS),
            'temperature': round(random.uniform(TEMPERATURE_MIN, TEMPERATURE_MAX), 1),
            'humidity': round(random.uniform(HUMIDITY_MIN, HUMIDITY_MAX), 1),
            'pressure': round(random.uniform(PRESSURE_MIN, PRESSURE_MAX), 1),
            'wind_speed': round(random.uniform(WIND_SPEED_MIN, WIND_SPEED_MAX), 1),
            'wind_direction': random.choice(WIND_DIRECTIONS),
            'visibility': round(random.uniform(VISIBILITY_MIN, VISIBILITY_MAX), 1)
        }

    def generate_session_description(
        self,
        name: str,
        area_width: float,
        area_height: float,
        task_type: Optional[str],
        populate_random: bool,
        drone_count: int,
        target_count: int,
        obstacle_count: int,
        with_examples: bool
    ) -> str:
        """
        Generate an auto-description for a session based on its parameters.

        Args:
            name: Session name
            area_width: Width of operational area
            area_height: Height of operational area
            task_type: Type of mission task
            populate_random: Whether random population is enabled
            drone_count: Number of drones
            target_count: Number of targets
            obstacle_count: Number of obstacles
            with_examples: Whether example data will be loaded

        Returns:
            Generated description string
        """
        area_str = f"{area_width:.0f}×{area_height:.0f} m"
        task_label = (task_type or '').replace('_', ' ').strip() or 'general operations'

        desc_parts = [
            f"{name} covers a {area_str} mission zone.",
            f"It is configured for {task_label}."
        ]

        if populate_random:
            count_bits = []
            if drone_count:
                count_bits.append(f"{drone_count} drones")
            if target_count:
                count_bits.append(f"{target_count} targets")
            if obstacle_count:
                count_bits.append(f"{obstacle_count} obstacles")
            if count_bits:
                desc_parts.append("Random seeding will create " + ", ".join(count_bits) + ".")
        else:
            if with_examples:
                desc_parts.append("It will load with the API example data.")
            else:
                desc_parts.append("It starts empty and ready for manual population.")

        return " ".join(part for part in desc_parts if part)

    # ============================================================================
    # Private Helper Methods
    # ============================================================================

    def _clean_spec_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove metadata keys (weight/category) from a specification entry.

        Args:
            entry: Specification dictionary possibly containing metadata.

        Returns:
            Cleaned specification dictionary.
        """
        return {
            key: value
            for key, value in entry.items()
            if key not in {'weight', 'category'}
        }

    def _plan_target_specs(self, task_type: str, target_count: int) -> List[Dict[str, Any]]:
        """
        Plan target specifications based on task type using configured distributions.

        This method generates target specifications according to the task-specific
        configurations defined in TASK_CONFIGS. Different mission types require
        different target distributions and characteristics, which can now be defined
        using weighted probability scores.

        Args:
            task_type: Type of mission task (e.g., 'area_search', 'target_tracking')
            target_count: Number of targets to plan

        Returns:
            List of target specifications with type and size hints
        """
        if target_count <= 0:
            return []

        specs: List[Dict[str, Any]] = []
        task_type = (task_type or 'others').lower()

        # Get the task configuration, defaulting to 'default' if not found
        task_config = TASK_CONFIGS.get(task_type, TASK_CONFIGS['default'])

        def extend_weighted(options: List[Dict[str, Any]], count: int) -> bool:
            try:
                for _ in range(count):
                    specs.append(self._pick_spec_with_weights(options))
                return True
            except ValueError as err:
                self.logger.warning(
                    "Invalid probability configuration for task '%s': %s. Falling back to sequential selection.",
                    task_type,
                    err
                )
                return False

        def extend_sequential(sequence: List[Dict[str, Any]], count: int) -> None:
            if not sequence:
                return
            pattern_length = len(sequence)
            for i in range(count):
                specs.append(self._clean_spec_entry(sequence[i % pattern_length]))

        def extend_from_specs(
            configured_specs: Optional[List[Dict[str, Any]]],
            count: int,
            category: Optional[str] = None
        ) -> bool:
            if not configured_specs:
                return False
            specs_to_use: List[Dict[str, Any]] = [
                entry for entry in configured_specs
                if isinstance(entry, dict)
            ]
            if not specs_to_use:
                return False
            if category:
                filtered: List[Dict[str, Any]] = []
                for entry in specs_to_use:
                    entry_category = entry.get('category')
                    if entry_category in (category, 'any', None):
                        filtered.append(entry)
                specs_to_use = filtered
                if not specs_to_use:
                    return False
            has_weight = any('weight' in entry for entry in specs_to_use)
            if has_weight:
                if extend_weighted(specs_to_use, count):
                    return True
            extend_sequential(specs_to_use, count)
            return True

        # Special handling for target_tracking task (has moving/fixed split)
        if task_type == 'target_tracking':
            moving_ratio = task_config.get('moving_ratio', TARGET_TRACKING_MOVING_RATIO)
            moving_count = max(1, int(round(target_count * moving_ratio)))
            moving_count = min(moving_count, target_count)
            fixed_count = target_count - moving_count

            specs_for_tracking = task_config.get('target_specs', [])

            if not extend_from_specs(specs_for_tracking, moving_count, category='moving'):
                extend_sequential([{'type': 'moving', 'size': 'small'}], moving_count)

            if not extend_from_specs(specs_for_tracking, fixed_count, category='fixed'):
                extend_sequential([{'type': 'fixed', 'size': 'small'}], fixed_count)

            if task_config.get('shuffle', False):
                random.shuffle(specs)
        else:
            if not extend_from_specs(task_config.get('target_specs'), target_count):
                fallback_specs = DEFAULT_TASK_CONFIG.get('target_specs', [])
                if fallback_specs:
                    self.logger.warning(
                        "No target specs found for task '%s'; using default configuration.",
                        task_type
                    )
                    extend_from_specs(fallback_specs, target_count)

            if task_config.get('shuffle', False):
                random.shuffle(specs)

        return specs

    def _plan_obstacle_specs(self, task_type: str, obstacle_count: int) -> List[Dict[str, Any]]:
        """
        Create obstacle specifications using task-specific preferences.

        Args:
            task_type: Mission profile key.
            obstacle_count: Number of obstacles to create.

        Returns:
            List of obstacle specification dictionaries.
        """
        if obstacle_count <= 0:
            return []

        task_type = (task_type or 'others').lower()
        task_config = TASK_CONFIGS.get(task_type, TASK_CONFIGS['default'])

        def generate_sequence(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            usable = [entry for entry in entries if isinstance(entry, dict)]
            if not usable:
                raise ValueError("No usable obstacle specs provided.")
            has_weight = any('weight' in entry for entry in usable)
            if has_weight:
                return [self._pick_spec_with_weights(usable) for _ in range(obstacle_count)]
            pattern_length = len(usable)
            return [
                self._clean_spec_entry(usable[i % pattern_length])
                for i in range(obstacle_count)
            ]

        spec_sources = [
            task_config.get('obstacle_specs'),
            DEFAULT_TASK_CONFIG.get('obstacle_specs')
        ]

        for source in spec_sources:
            if not source:
                continue
            try:
                return generate_sequence(source)
            except ValueError as err:
                self.logger.warning(
                    "Invalid obstacle specs for task '%s': %s. Trying fallback.",
                    task_type,
                    err
                )
                continue

        return [{'size': 'normal'} for _ in range(obstacle_count)]

    def _pick_spec_with_weights(self, weighted_specs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select a specification based on configured probability weights.

        Args:
            weighted_specs: List of spec dictionaries containing an optional 'weight' key.

        Returns:
            A dictionary representing the selected specification.
        """
        valid_specs: List[Tuple[float, Dict[str, Any]]] = []
        total_weight = 0.0

        for entry in weighted_specs:
            if not isinstance(entry, dict):
                continue
            spec = self._clean_spec_entry(entry)
            if not spec:
                continue
            weight_value = entry.get('weight', 1.0)
            try:
                weight = float(weight_value)
            except (TypeError, ValueError):
                weight = 1.0
            if weight < 0:
                continue
            valid_specs.append((weight, spec))
            total_weight += weight

        if not valid_specs:
            raise ValueError("No valid specifications provided for weighted selection.")

        if total_weight <= 0:
            # If all weights were zero, treat them as equal probability
            total_weight = float(len(valid_specs))
            valid_specs = [(1.0, spec) for _, spec in valid_specs]

        pick = random.uniform(0.0, total_weight)
        cumulative = 0.0
        for weight, spec in valid_specs:
            cumulative += weight
            if pick <= cumulative:
                return dict(spec)

        return self._clean_spec_entry(valid_specs[-1][1])

    def _range_with_margin(self, total_extent: float, margin: float) -> Tuple[float, float]:
        """
        Return a safe coordinate range (positive) that keeps objects within bounds.

        Args:
            total_extent: Total size of the dimension
            margin: Margin to maintain from edges

        Returns:
            Tuple of (min_coord, max_coord)
        """
        total_extent = max(total_extent, 1.0)
        margin = max(0.0, margin)
        if margin * 2 >= total_extent:
            return 0.0, total_extent
        return margin, total_extent - margin

    def _shape_for_used_position(self, entry: Union[Tuple[float, float, float], Tuple[float, float, float, Any]]) -> Any:
        """
        Convert a stored used-position entry into a shapely geometry for overlap checks.

        Args:
            entry: Either a legacy `(x, y, buffer_radius)` tuple or an extended
                `(x, y, buffer_radius, geometry)` tuple.

        Returns:
            A shapely geometry representing the occupied area.
        """
        if len(entry) == 3:
            ux, uy, existing_buffer = entry
            return Point(ux, uy).buffer(existing_buffer)

        ux, uy, existing_buffer, existing_geometry = entry
        if existing_geometry is not None:
            return existing_geometry
        return Point(ux, uy).buffer(existing_buffer)

    def _generate_unique_xy(
        self,
        used_positions: List[Tuple[float, float, float]],
        buffer_radius: float,
        x_range: Tuple[float, float],
        y_range: Optional[Tuple[float, float]] = None,
        max_attempts: int = MAX_POSITION_ATTEMPTS,
        shape_geometry: Optional[Any] = None
    ) -> Tuple[float, float]:
        """
        Generate a unique (x, y) coordinate that avoids overlaps with existing positions.

        Args:
            used_positions: List of (x, y, buffer_radius, shape_geometry) tuples for existing entities
            buffer_radius: Required buffer radius for the new entity
            x_range: (min_x, max_x) bounds for x coordinate
            y_range: Optional (min_y, max_y) bounds for y coordinate
            max_attempts: Maximum random placement attempts before grid fallback
            shape_geometry: Optional shapely geometry object for accurate collision detection

        Returns:
            Tuple of (x, y) coordinates

        Raises:
            ValueError: If unable to find a valid position
        """
        min_x, max_x = x_range
        if y_range is None:
            min_y, max_y = min_x, max_x
        else:
            min_y, max_y = y_range

        def is_clear(x: float, y: float) -> bool:
            # Create shape for the new entity
            if shape_geometry is not None:
                # For polygons, translate the shape to the candidate position
                new_shape = shape_geometry
            else:
                # For circles and point-based entities, create a circular buffer
                new_shape = Point(x, y).buffer(buffer_radius)

            for entry in used_positions:
                existing_shape = self._shape_for_used_position(entry)

                # Check for intersection using shapely
                if new_shape.intersects(existing_shape):
                    return False
            return True

        for _ in range(max_attempts):
            x = round(random.uniform(min_x, max_x), 2)
            y = round(random.uniform(min_y, max_y), 2)
            if is_clear(x, y):
                # Store with shape geometry if provided
                if shape_geometry is not None or any(len(entry) == 4 for entry in used_positions):
                    used_positions.append((x, y, buffer_radius, shape_geometry))
                else:
                    used_positions.append((x, y, buffer_radius))
                return x, y

        # Deterministic fallback: scan a coarse grid
        span_x = max_x - min_x
        span_y = max_y - min_y
        step_x = max(buffer_radius, span_x / GRID_FALLBACK_DIVISIONS)
        step_y = max(buffer_radius, span_y / GRID_FALLBACK_DIVISIONS)

        y = min_y
        while y <= max_y:
            x = min_x
            while x <= max_x:
                candidate_x = round(x, 2)
                candidate_y = round(y, 2)
                if is_clear(candidate_x, candidate_y):
                    # Store with shape geometry if provided
                    if shape_geometry is not None or any(len(entry) == 4 for entry in used_positions):
                        used_positions.append((candidate_x, candidate_y, buffer_radius, shape_geometry))
                    else:
                        used_positions.append((candidate_x, candidate_y, buffer_radius))
                    return candidate_x, candidate_y
                x += step_x
            y += step_y

        raise ValueError("Unable to place entity without overlap; consider reducing counts or expanding area.")

    def _attempt_item_generation(
        self,
        generator_fn: Callable[[], Dict[str, Any]],
        item_label: str,
        max_attempts: int = MAX_ENTITY_GENERATION_ATTEMPTS
    ) -> Optional[Dict[str, Any]]:
        """
        Retry generation for a single entity before giving up.

        Args:
            generator_fn: Callable that creates the entity payload.
            item_label: Human-readable label for logging (e.g., 'target 1').
            max_attempts: How many attempts to perform before skipping.

        Returns:
            The generated payload, or None if all attempts fail.
        """
        last_error: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            try:
                return generator_fn()
            except ValueError as err:
                last_error = err
                if attempt < max_attempts:
                    self.logger.debug(
                        "Attempt %d/%d to place %s failed: %s",
                        attempt,
                        max_attempts,
                        item_label,
                        err
                    )

        self.logger.warning(
            "Skipping %s after %d failed attempts: %s",
            item_label,
            max_attempts,
            last_error
        )
        return None

    def _drone_placement_ranges(
        self,
        area_width: float,
        area_height: float,
        drone_count: int,
        do_not_scatter_drones: bool
    ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Build drone placement ranges for either full-map or lower-left clustering.

        Args:
            area_width: Width of the operational area
            area_height: Height of the operational area
            drone_count: Number of drones requested
            do_not_scatter_drones: Whether clustering near the origin is enabled

        Returns:
            Tuple of x-range and y-range
        """
        buffer = float(ITEM_SIZE_RANGES['drone']['buffer'])
        if not do_not_scatter_drones:
            return (
                self._range_with_margin(area_width, buffer),
                self._range_with_margin(area_height, buffer)
            )

        requested = max(1, int(drone_count))
        columns = max(DRONE_CLUSTER_MIN_COLUMNS, math.ceil(math.sqrt(requested)))
        rows = max(DRONE_CLUSTER_MIN_ROWS, math.ceil(requested / columns))
        cluster_width = min(
            area_width,
            max(buffer * 2.0, columns * buffer * DRONE_CLUSTER_SPACING_MULTIPLIER)
        )
        cluster_height = min(
            area_height,
            max(buffer * 2.0, rows * buffer * DRONE_CLUSTER_SPACING_MULTIPLIER)
        )
        return (
            self._range_with_margin(cluster_width, buffer),
            self._range_with_margin(cluster_height, buffer)
        )

    def _random_drone_payload(
        self,
        index: int,
        used_positions: List[Tuple[float, float, float]],
        area_width: float,
        area_height: float,
        task_type: str,
        exist_list: List[str],
        drone_count: int = 1,
        do_not_scatter_drones: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a random drone payload with position and properties.

        Args:
            index: Index number for drone naming
            used_positions: List of existing entity positions
            area_width: Width of operational area
            area_height: Height of operational area
            task_type: Type of mission task (affects placement)
            exist_list: List of existing names to avoid duplicates
            drone_count: Total number of drones requested for the session
            do_not_scatter_drones: Whether to cluster drones near the origin

        Returns:
            Dictionary containing drone data
        """
        buffer = float(ITEM_SIZE_RANGES['drone']['buffer'])
        x_range, y_range = self._drone_placement_ranges(
            area_width=area_width,
            area_height=area_height,
            drone_count=drone_count,
            do_not_scatter_drones=do_not_scatter_drones
        )

        x, y = self._generate_unique_xy(used_positions, buffer_radius=buffer, x_range=x_range, y_range=y_range)

        # Round positions to integers
        x, y = round(x), round(y)

        if random.random() < DRONE_GROUND_PROBABILITY:
            z = 0
        else:
            z = round(random.uniform(DRONE_MIN_ALTITUDE, DRONE_MAX_ALTITUDE))

        name = create_new_name("Drone", exist_list=exist_list)
        exist_list.append(name)

        return {
            'name': name,
            'model': random.choice(DRONE_MODELS),
            'status': 'idle',
            'max_speed': round(random.uniform(DRONE_MIN_SPEED, DRONE_MAX_SPEED), 0),
            'max_altitude': round(random.uniform(DRONE_MIN_MAX_ALTITUDE, DRONE_MAX_MAX_ALTITUDE), 0),
            'battery_capacity': round(random.uniform(DRONE_MIN_BATTERY, DRONE_MAX_BATTERY), 1),
            'position': {'x': x, 'y': y, 'z': z}
        }

    def _random_target_payload(
        self,
        index: int,
        target_spec: Dict[str, Any],
        used_positions: List[Tuple[float, float, float]],
        area_width: float,
        area_height: float,
        exist_list: List[str]
    ) -> Dict[str, Any]:
        """
        Generate a random target payload based on specification.

        Args:
            index: Index number for target naming
            target_spec: Specification dictionary with type and size hints
            used_positions: List of existing entity positions
            area_width: Width of operational area
            area_height: Height of operational area
            exist_list: List of existing names to avoid duplicates

        Returns:
            Dictionary containing target data
        """
        ttype = (target_spec or {}).get('type', 'fixed')
        size_hint = (target_spec or {}).get('size', 'normal')

        # Calculate scale factor based on the base size (1024x768) with gentler sqrt scaling
        scale_factor = math.sqrt(min(area_width / BASE_AREA_WIDTH, area_height / BASE_AREA_HEIGHT))

        # Get size range from configuration
        if ttype in ITEM_SIZE_RANGES['target']:
            base_min, base_max = ITEM_SIZE_RANGES['target'][ttype]
        else:
            base_min, base_max = ITEM_SIZE_RANGES['target']['fixed']

        # Apply size hint multipliers
        mult_min, mult_max = SIZE_MULTIPLIERS.get(size_hint, SIZE_MULTIPLIERS['normal'])

        # Calculate actual size range scaled to the area
        r_min = max(1, round(base_min * scale_factor * mult_min))
        r_max = max(r_min + 1, round(base_max * scale_factor * mult_max))

        def pick_radius(additional: float = 0.0) -> Tuple[float, float, Tuple[float, float]]:
            radius = round(random.uniform(r_min, r_max))  # Round to integer
            margin = radius + additional
            x_range = self._range_with_margin(area_width, margin)
            y_range = self._range_with_margin(area_height, margin)
            x, y = self._generate_unique_xy(used_positions, buffer_radius=margin, x_range=x_range, y_range=y_range)
            # Round positions to integers
            x, y = round(x), round(y)
            return radius, margin, (x, y)

        if ttype == 'waypoint':
            radius, margin, (x, y) = pick_radius(TARGET_ADDITIONAL_MARGINS['waypoint'])
            name = create_new_name("Waypoint", exist_list=exist_list)
            exist_list.append(name)
            payload: Dict[str, Any] = {
                'name': name,
                'type': ttype,
                'position': {'x': x, 'y': y, 'z': 0.0},
                'radius': radius,
                'charge_amount': round(random.uniform(TARGET_WAYPOINT_MIN_CHARGE, TARGET_WAYPOINT_MAX_CHARGE), 1)
            }
            if random.random() < TARGET_WAYPOINT_CAPACITY_PROBABILITY:
                payload['capacity'] = random.randint(TARGET_WAYPOINT_MIN_CAPACITY, TARGET_WAYPOINT_MAX_CAPACITY)
            return payload

        if ttype == 'fixed':
            radius, margin, (x, y) = pick_radius(TARGET_ADDITIONAL_MARGINS['fixed'])
            name = create_new_name("Fixed Target", exist_list=exist_list)
            exist_list.append(name)
            return {
                'name': name,
                'type': ttype,
                'position': {'x': x, 'y': y, 'z': 0.0},
                'radius': radius
            }

        if ttype == 'moving':
            radius, margin, (x, y) = pick_radius(TARGET_ADDITIONAL_MARGINS['moving'])
            name = create_new_name("Moving Target", exist_list=exist_list)
            exist_list.append(name)
            return {
                'name': name,
                'type': ttype,
                'position': {'x': x, 'y': y, 'z': 0.0},
                'radius': radius,
                'velocity': {
                    'x': round(random.uniform(MOVING_TARGET_MIN_VELOCITY_X, MOVING_TARGET_MAX_VELOCITY_X), 1),
                    'y': round(random.uniform(MOVING_TARGET_MIN_VELOCITY_Y, MOVING_TARGET_MAX_VELOCITY_Y), 1),
                    'z': round(random.uniform(MOVING_TARGET_MIN_VELOCITY_Z, MOVING_TARGET_MAX_VELOCITY_Z), 1)
                },
                'moving_duration': round(random.uniform(MOVING_TARGET_MIN_DURATION, MOVING_TARGET_MAX_DURATION), 1)
            }

        if ttype == 'circle':
            # For circle targets, use actual circular geometry for collision detection
            radius = round(random.uniform(r_min, r_max))
            margin = radius + TARGET_ADDITIONAL_MARGINS['circle']
            x_range = self._range_with_margin(area_width, margin)
            y_range = self._range_with_margin(area_height, margin)

            # Create shapely circle geometry for accurate collision detection
            # We'll create a placeholder at origin and check with translated versions
            circle_shape = Point(0, 0).buffer(radius)

            # Find position using shapely-based collision detection
            x, y = self._generate_unique_xy(
                used_positions,
                buffer_radius=margin,
                x_range=x_range,
                y_range=y_range,
                shape_geometry=None  # Use circular buffer for circles (simpler)
            )
            x, y = round(x), round(y)

            name = create_new_name("Circle Target", exist_list=exist_list)
            exist_list.append(name)
            return {
                'name': name,
                'type': ttype,
                'position': {'x': x, 'y': y, 'z': 0.0},
                'radius': radius
            }

        if ttype == 'polygon':
            # For polygon targets, use actual polygon geometry for collision detection
            radius = round(random.uniform(r_min, r_max))
            margin = radius + TARGET_ADDITIONAL_MARGINS['polygon']
            x_range = self._range_with_margin(area_width, margin)
            y_range = self._range_with_margin(area_height, margin)

            # First, find a candidate center position
            for attempt in range(MAX_POSITION_ATTEMPTS):
                cx = round(random.uniform(x_range[0], x_range[1]), 2)
                cy = round(random.uniform(y_range[0], y_range[1]), 2)

                # Create polygon vertices centered at (cx, cy)
                vertices = [
                    {'x': cx - radius, 'y': cy - radius},
                    {'x': cx + radius, 'y': cy - radius},
                    {'x': cx + radius, 'y': cy + radius},
                    {'x': cx - radius, 'y': cy + radius}
                ]

                # Create shapely polygon for collision detection
                polygon_coords = [(v['x'], v['y']) for v in vertices]
                polygon_shape = ShapelyPolygon(polygon_coords)

                # Check if this polygon collides with any existing shapes
                collision = False
                for entry in used_positions:
                    existing_shape = self._shape_for_used_position(entry)

                    if polygon_shape.intersects(existing_shape):
                        collision = True
                        break

                if not collision:
                    # Found a valid position - store the polygon geometry
                    used_positions.append((cx, cy, radius, polygon_shape))

                    lower_left = min(vertices, key=lambda v: (v['y'], v['x']))
                    name = create_new_name("Polygon Target", exist_list=exist_list)
                    exist_list.append(name)
                    return {
                        'name': name,
                        'type': 'polygon',
                        'position': {'x': lower_left['x'], 'y': lower_left['y'], 'z': 0.0},
                        'vertices': vertices
                    }

            # If we couldn't find a position after all attempts, raise an error
            raise ValueError(f"Unable to place polygon target {index + 1} without overlap")

        # Fallback to fixed target profile
        fallback_radius, _, (x, y) = pick_radius(TARGET_ADDITIONAL_MARGINS['fallback'])
        name = create_new_name("Fixed Target", exist_list=exist_list)
        exist_list.append(name)
        return {
            'name': name,
            'type': 'fixed',
            'position': {'x': x, 'y': y, 'z': 0.0},
            'radius': fallback_radius
        }

    def _random_obstacle_payload(
        self,
        index: int,
        used_positions: List[Tuple[float, float, float]],
        area_width: float,
        area_height: float,
        exist_list: List[str],
        obstacle_spec: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a random obstacle payload with size multipliers (same logic as targets).

        Args:
            index: Index number for obstacle naming
            used_positions: List of existing entity positions
            area_width: Width of operational area
            area_height: Height of operational area
            exist_list: List of existing names to avoid duplicates
            obstacle_spec: Optional specification with 'type' and 'size' hints

        Returns:
            Dictionary containing obstacle data
        """
        # Get obstacle type and size hint from spec (or use defaults)
        if obstacle_spec:
            otype = obstacle_spec.get('type', random.choice(OBSTACLE_TYPES))
            size_hint = obstacle_spec.get('size', 'normal')
        else:
            otype = random.choice(OBSTACLE_TYPES)
            size_hint = 'normal'

        # Use full area for obstacle placement (not half)
        # Previously used half_width/half_height which restricted obstacles to lower-left corner
        obstacle_width = area_width
        obstacle_height = area_height

        # Calculate scale factor based on the base size (1024x768) with gentler sqrt scaling
        scale_factor = math.sqrt(min(area_width / BASE_AREA_WIDTH, area_height / BASE_AREA_HEIGHT))

        # Get size multiplier (NEW: same as targets)
        mult_min, mult_max = SIZE_MULTIPLIERS.get(size_hint, SIZE_MULTIPLIERS['normal'])

        if otype == 'point':
            min_r, max_r = ITEM_SIZE_RANGES['obstacle']['point']
            # NEW: Apply multiplier like targets do
            radius = round(random.uniform(min_r * scale_factor * mult_min, max_r * scale_factor * mult_max))
            margin = radius + OBSTACLE_ADDITIONAL_MARGINS['point']
            x_range = self._range_with_margin(obstacle_width, margin)
            y_range = self._range_with_margin(obstacle_height, margin)
            x, y = self._generate_unique_xy(used_positions, buffer_radius=margin, x_range=x_range, y_range=y_range)
            # Round positions to integers
            x, y = round(x), round(y)
            name = create_new_name("Point Obstacle", exist_list=exist_list)
            exist_list.append(name)
            return {
                'name': name,
                'type': otype,
                'position': {'x': x, 'y': y, 'z': 0.0},
                'radius': radius,
                'height': 0.0
            }

        if otype == 'circle':
            min_r, max_r = ITEM_SIZE_RANGES['obstacle']['circle']
            # NEW: Apply multiplier like targets do
            radius = round(random.uniform(min_r * scale_factor * mult_min, max_r * scale_factor * mult_max))
            margin = radius + OBSTACLE_ADDITIONAL_MARGINS['circle']
            x_range = self._range_with_margin(obstacle_width, margin)
            y_range = self._range_with_margin(obstacle_height, margin)
            x, y = self._generate_unique_xy(used_positions, buffer_radius=margin, x_range=x_range, y_range=y_range)
            # Round positions to integers
            x, y = round(x), round(y)
            name = create_new_name("Circle Obstacle", exist_list=exist_list)
            exist_list.append(name)
            return {
                'name': name,
                'type': otype,
                'position': {'x': x, 'y': y, 'z': 0.0},
                'radius': radius,
                'height': 0.0
            }

        if otype == 'ellipse':
            min_w, max_w = ITEM_SIZE_RANGES['obstacle']['ellipse']['width']
            min_l, max_l = ITEM_SIZE_RANGES['obstacle']['ellipse']['length']
            # NEW: Apply multiplier like targets do
            width = round(random.uniform(min_w * scale_factor * mult_min, max_w * scale_factor * mult_max))
            length = round(random.uniform(min_l * scale_factor * mult_min, min(max_l * scale_factor * mult_max, width)))
            buffer = max(width, length) + OBSTACLE_ADDITIONAL_MARGINS['ellipse']
            x_range = self._range_with_margin(obstacle_width, buffer)
            y_range = self._range_with_margin(obstacle_height, buffer)
            x, y = self._generate_unique_xy(used_positions, buffer_radius=buffer, x_range=x_range, y_range=y_range)
            # Round positions to integers
            x, y = round(x), round(y)
            name = create_new_name("Ellipse Obstacle", exist_list=exist_list)
            exist_list.append(name)
            return {
                'name': name,
                'type': otype,
                'position': {'x': x, 'y': y, 'z': 0.0},
                'width': width,
                'length': length,
                'height': 0.0
            }

        # Polygon obstacle
        min_s, max_s = ITEM_SIZE_RANGES['obstacle']['polygon']
        # NEW: Apply multiplier like targets do
        size = round(random.uniform(min_s * scale_factor * mult_min, max_s * scale_factor * mult_max))
        margin = size + OBSTACLE_ADDITIONAL_MARGINS['polygon']
        x_range = self._range_with_margin(obstacle_width, margin)
        y_range = self._range_with_margin(obstacle_height, margin)

        for attempt in range(MAX_POSITION_ATTEMPTS):
            cx = round(random.uniform(x_range[0], x_range[1]), 2)
            cy = round(random.uniform(y_range[0], y_range[1]), 2)

            vertices = [
                {'x': cx - size, 'y': cy - size},
                {'x': cx + size, 'y': cy - size},
                {'x': cx + size, 'y': cy + size},
                {'x': cx - size, 'y': cy + size}
            ]
            polygon_shape = ShapelyPolygon([(v['x'], v['y']) for v in vertices])

            collision = False
            for entry in used_positions:
                existing_shape = self._shape_for_used_position(entry)
                if polygon_shape.intersects(existing_shape):
                    collision = True
                    break

            if collision:
                continue

            used_positions.append((cx, cy, size, polygon_shape))
            cx, cy = round(cx), round(cy)
            break
        else:
            raise ValueError(f"Unable to place polygon obstacle {index + 1} without overlap")

        # Use the center position for the obstacle (matching polygon target behavior)
        name = create_new_name("Polygon Obstacle", exist_list=exist_list)
        exist_list.append(name)
        return {
            'name': name,
            'type': otype,
            'position': {'x': cx, 'y': cy, 'z': 0.0},
            'vertices': vertices,
            'height': 0.0
        }
