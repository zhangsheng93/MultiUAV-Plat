"""
Battery Configuration for MultiUAV-Plat Server System

This module defines battery consumption rates for different drone operations.
All values are in percentage points (0-100).
"""

from config.util import distance as euclidean_distance


class BatteryConfig:
    """Battery consumption configuration for drone operations"""

    # Emergency thresholds
    CRITICAL_BATTERY_LEVEL = 5.0  # Below this, drone cannot take off
    EMERGENCY_BATTERY_LEVEL = 0.5  # Below this, emergency landing triggered

    # Base command costs (fixed percentage costs)
    COMMAND_COSTS = {
        # Connection commands (no cost)
        "connect": 0.0,
        "disconnect": 0.0,

        # Takeoff and landing
        "take_off": 0.5,  # Taking off uses significant power
        "land": 0,       # Landing uses minimal power

        # Movement commands (base cost, additional cost per meter)
        "move_to": {
            "base": 0.0,           # Direct movement charges distance only
            "per_meter": 0.005,     # Cost per meter traveled
            "per_meter_vertical": 0.02  # Vertical movement costs more
        },

        "move_towards": {
            "base": 0.0,
            "per_meter": 0.005, 
            "per_meter_vertical": 0.02
        },

        "move_along_path": {
            "base": 0.0,           # Path following charges distance only; no per-waypoint initiation cost
            "per_meter": 0.005, 
            "per_meter_vertical": 0.02
        },

        # Altitude and orientation
        "change_altitude": {
            "base": 0.1,
            "per_meter": 0.02  # Vertical movement is energy intensive
        },

        "rotate": 0.2,  # Rotating uses motors but no movement

        # Status commands
        "hover": 0.1,      # Hovering uses power to stay stable (per command call)
        "set_home": 0.0,   # Just updating a variable
        "calibrate": 0.5,  # Sensor calibration uses some power

        # Navigation
        "return_home": {
            "base": 0.5,
            "per_meter": 0.04,
            "per_meter_vertical": 0.06
        },

        # Camera and communication
        "take_photo": 0.3,     # Camera activation
        "send_message": 0.1,   # Radio transmission
        "broadcast": 0.2,      # Broadcasting to multiple drones

        # Emergency
        "emergency": 0.0,  # Emergency stop doesn't consume battery (cuts power)

        # Charging (negative = adds battery)
        "charge": -1.0,  # This is handled specially, negative value ignored
    }

    # Maximum battery consumption per command (safety cap)
    MAX_BATTERY_PER_COMMAND = 100.0  # No single command should drain more than 15%

    # Idle power consumption (per minute when hovering/idle)
    IDLE_CONSUMPTION_PER_MINUTE = 0  # Realistic idle drain

    # Speed-based multipliers (faster = more power)
    SPEED_MULTIPLIER = {
        "slow": 0.8,      # 0-30% of max speed
        "normal": 1.0,    # 30-70% of max speed
        "fast": 1.3,      # 70-100% of max speed
    }

    # Environmental multipliers
    ENVIRONMENTAL_MULTIPLIERS = {
        "clear": 1.0,
        "partly_cloudy": 1.05,
        "cloudy": 1.1,
        "rain": 1.3,      # Rain increases resistance
        "heavy_rain": 1.5,
        "snow": 1.4,
        "fog": 1.1,
        "windy": 1.2,
        "storm": 1.6,     # Storms require much more power
    }

    # Temperature ranges and multipliers (in Celsius)
    TEMPERATURE_MULTIPLIERS = {
        "extreme_cold": (-30, -10, 1.35),  # (min, max, multiplier)
        "cold": (-10, 10, 1.20),
        "cool": (10, 15, 1.05),
        "optimal": (15, 25, 1.0),          # Optimal operating range
        "warm": (25, 30, 1.03),
        "hot": (30, 40, 1.10),
        "extreme_hot": (40, 50, 1.25),     # Battery protection kicks in
    }

    # Wind speed thresholds and multipliers (in m/s)
    WIND_SPEED_MULTIPLIERS = {
        "calm": (0, 2, 1.0),               # (min, max, multiplier)
        "light_breeze": (2, 5, 1.05),
        "moderate": (5, 10, 1.15),
        "strong": (10, 15, 1.25),
        "very_strong": (15, 20, 1.40),
        "storm_winds": (20, 100, 1.60),    # Dangerous conditions
    }

    # Wind direction impact factors
    WIND_DIRECTION_FACTORS = {
        "headwind": 1.0,      # Full penalty for flying into wind
        "crosswind": 0.7,     # 70% of full penalty for perpendicular wind
        "tailwind": -0.1,     # 10% bonus for wind assistance
    }

    # Humidity thresholds and multipliers (in percentage)
    HUMIDITY_MULTIPLIERS = {
        "very_low": (0, 20, 1.03),         # (min, max, multiplier)
        "low": (20, 30, 1.02),
        "optimal": (30, 70, 1.0),          # Comfortable range
        "high": (70, 80, 1.02),
        "very_high": (80, 100, 1.05),      # Moisture affects electronics
    }

    # Payload multiplier (if carrying extra weight)
    PAYLOAD_MULTIPLIER = 1.0  # Can be adjusted per drone

    @staticmethod
    def get_temperature_multiplier(temperature: float) -> float:
        """Calculate battery multiplier based on temperature

        Args:
            temperature: Temperature in Celsius

        Returns:
            Multiplier for battery consumption (1.0 = normal)
        """
        for _, (min_temp, max_temp, multiplier) in BatteryConfig.TEMPERATURE_MULTIPLIERS.items():
            if min_temp <= temperature < max_temp:
                return multiplier

        # Default fallback for extreme temperatures outside defined ranges
        if temperature < -30:
            return 1.5  # Extremely dangerous cold
        elif temperature >= 50:
            return 1.4  # Extremely dangerous heat
        return 1.0

    @staticmethod
    def get_wind_speed_multiplier(wind_speed: float) -> float:
        """Calculate battery multiplier based on wind speed

        Args:
            wind_speed: Wind speed in m/s

        Returns:
            Base multiplier for wind speed (direction not considered)
        """
        for _, (min_speed, max_speed, multiplier) in BatteryConfig.WIND_SPEED_MULTIPLIERS.items():
            if min_speed <= wind_speed < max_speed:
                return multiplier

        # Extreme wind speeds
        if wind_speed >= 100:
            return 2.0  # Nearly impossible to fly
        return 1.0

    @staticmethod
    def get_wind_direction_factor(drone_heading: float, wind_direction_str: str, wind_speed: float) -> float:
        """Calculate wind direction impact factor based on drone heading vs wind direction

        Args:
            drone_heading: Drone's heading in degrees (0=North, 90=East, 180=South, 270=West)
            wind_direction_str: Wind direction as string (e.g., "north", "northeast")
            wind_speed: Wind speed in m/s (used to determine if wind is significant)

        Returns:
            Factor to multiply with wind speed multiplier (1.0=headwind, 0.7=crosswind, -0.1=tailwind)
        """
        # If wind is calm, direction doesn't matter
        if wind_speed < 1.0:
            return 0.0  # No wind impact

        # Convert wind direction string to degrees
        wind_direction_map = {
            "north": 0.0,
            "northeast": 45.0,
            "east": 90.0,
            "southeast": 135.0,
            "south": 180.0,
            "southwest": 225.0,
            "west": 270.0,
            "northwest": 315.0,
        }

        wind_direction_degrees = wind_direction_map.get(wind_direction_str.lower(), 0.0)

        # Calculate relative angle (drone heading relative to wind direction)
        # Wind blows FROM the direction, so we need to consider opposite direction
        wind_from_degrees = (wind_direction_degrees + 180.0) % 360.0

        # Calculate angle difference between drone heading and wind source
        angle_diff = abs(drone_heading - wind_from_degrees)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff

        # Determine wind type based on angle
        if angle_diff <= 45:
            # Headwind (flying into wind)
            return BatteryConfig.WIND_DIRECTION_FACTORS["headwind"]
        elif angle_diff >= 135:
            # Tailwind (wind pushing from behind)
            return BatteryConfig.WIND_DIRECTION_FACTORS["tailwind"]
        else:
            # Crosswind (perpendicular)
            return BatteryConfig.WIND_DIRECTION_FACTORS["crosswind"]

    @staticmethod
    def get_humidity_multiplier(humidity: float) -> float:
        """Calculate battery multiplier based on humidity

        Args:
            humidity: Humidity percentage (0-100)

        Returns:
            Multiplier for battery consumption
        """
        for _, (min_hum, max_hum, multiplier) in BatteryConfig.HUMIDITY_MULTIPLIERS.items():
            if min_hum <= humidity <= max_hum:
                return multiplier

        return 1.0

    @staticmethod
    def get_pressure_altitude_multiplier(pressure: float, altitude: float) -> float:
        """Calculate battery multiplier based on atmospheric pressure and altitude

        Lower pressure at higher altitudes means thinner air, which affects:
        - Less air resistance (good for horizontal flight)
        - Motors work harder for lift (bad for vertical stability)

        Args:
            pressure: Atmospheric pressure in hPa (hectopascals)
            altitude: Current altitude in meters

        Returns:
            Multiplier for battery consumption
        """
        # Standard pressure at sea level is 1013.25 hPa
        standard_pressure = 1013.25

        # Calculate pressure ratio
        pressure_ratio = pressure / standard_pressure

        # Altitude effect (approximation)
        # Every 1000m of altitude increases energy consumption by ~5%
        altitude_factor = 1.0 + (altitude / 1000.0) * 0.05

        # Pressure effect
        # Lower pressure (higher altitude) = slightly more work for motors
        # This is a simplified model
        if pressure_ratio < 0.85:  # Very low pressure (high altitude)
            pressure_factor = 1.15
        elif pressure_ratio < 0.95:  # Low pressure
            pressure_factor = 1.08
        else:  # Normal to high pressure
            pressure_factor = 1.0

        # Combine factors (but cap the total multiplier)
        combined = min(altitude_factor * pressure_factor, 1.5)
        return combined

    @staticmethod
    def calculate_distance_3d(start_pos: dict, end_pos: dict) -> tuple:
        """Calculate horizontal and vertical distance between two positions

        Returns:
            tuple: (horizontal_distance, vertical_distance)
        """
        

        dx = end_pos["x"] - start_pos["x"]
        dy = end_pos["y"] - start_pos["y"]
        dz = end_pos["z"] - start_pos["z"]

        horizontal_distance = euclidean_distance(
            (start_pos["x"], start_pos["y"]),
            (end_pos["x"], end_pos["y"]),
        )
        vertical_distance = abs(dz)

        return horizontal_distance, vertical_distance

    @staticmethod
    def calculate_total_distance(start_pos: dict, end_pos: dict) -> float:
        """Calculate total 3D distance between two positions"""
        return euclidean_distance(start_pos, end_pos)

    @classmethod
    def calculate_environmental_multiplier(cls, environment: dict, drone_heading: float = 0.0,
                                          drone_altitude: float = 0.0) -> tuple:
        """Calculate comprehensive environmental multiplier for battery consumption

        Args:
            environment: Dictionary with environmental data:
                - weather: Weather condition string
                - temperature: Temperature in Celsius
                - humidity: Humidity percentage
                - pressure: Atmospheric pressure in hPa
                - wind_speed: Wind speed in m/s
                - wind_direction: Wind direction string
            drone_heading: Drone's current heading in degrees (for wind direction calculation)
            drone_altitude: Drone's current altitude in meters (for pressure calculation)

        Returns:
            Tuple of (total_multiplier, breakdown_dict) where breakdown_dict contains individual factors
        """
        # Start with base multiplier
        multipliers = {}

        # Weather multiplier (existing system)
        weather = environment.get("weather", "clear")
        weather_mult = cls.ENVIRONMENTAL_MULTIPLIERS.get(weather, 1.0)
        multipliers["weather"] = weather_mult

        # Temperature multiplier
        temperature = environment.get("temperature", 22.0)
        temp_mult = cls.get_temperature_multiplier(temperature)
        multipliers["temperature"] = temp_mult

        # Wind speed multiplier
        wind_speed = environment.get("wind_speed", 0.0)
        wind_speed_mult = cls.get_wind_speed_multiplier(wind_speed)

        # Wind direction factor (modifies wind speed impact)
        wind_direction = environment.get("wind_direction", "north")
        wind_dir_factor = cls.get_wind_direction_factor(drone_heading, wind_direction, wind_speed)

        # Combined wind impact: base multiplier adjusted by direction
        # If tailwind (negative factor), it reduces consumption
        # If headwind (positive factor), it increases consumption
        if wind_dir_factor < 0:
            # Tailwind bonus (reduces consumption)
            wind_combined = 1.0 + (wind_speed_mult - 1.0) * abs(wind_dir_factor)
            wind_combined = max(0.9, wind_combined)  # At least 10% reduction possible
        else:
            # Headwind/crosswind penalty
            wind_combined = 1.0 + (wind_speed_mult - 1.0) * wind_dir_factor

        multipliers["wind"] = wind_combined

        # Humidity multiplier
        humidity = environment.get("humidity", 50.0)
        humidity_mult = cls.get_humidity_multiplier(humidity)
        multipliers["humidity"] = humidity_mult

        # Pressure/altitude multiplier
        pressure = environment.get("pressure", 1013.25)
        pressure_alt_mult = cls.get_pressure_altitude_multiplier(pressure, drone_altitude)
        multipliers["pressure_altitude"] = pressure_alt_mult

        # Calculate total multiplier (multiplicative combination)
        total_multiplier = (
            weather_mult *
            temp_mult *
            wind_combined *
            humidity_mult *
            pressure_alt_mult
        )

        # Apply reasonable cap (max 3x drain in extreme conditions)
        total_multiplier = min(total_multiplier, 3.0)

        return total_multiplier, multipliers

    @classmethod
    def calculate_movement_cost(cls, command: str, start_pos: dict, end_pos: dict,
                                weather: str = "clear", environment: dict = None,
                                drone_heading: float = 0.0) -> float:
        """Calculate battery cost for movement commands

        Args:
            command: Command name (move_to, move_towards, etc.)
            start_pos: Starting position dict with x, y, z
            end_pos: Ending position dict with x, y, z
            weather: Current weather condition (legacy, used if environment not provided)
            environment: Full environment dictionary with all conditions (preferred)
            drone_heading: Drone's heading in degrees (for wind direction calculations)

        Returns:
            Battery cost in percentage points
        """
        if command not in cls.COMMAND_COSTS:
            return 0.0

        cost_config = cls.COMMAND_COSTS[command]

        if isinstance(cost_config, dict):
            # Calculate distances
            h_distance, v_distance = cls.calculate_distance_3d(start_pos, end_pos)

            # Calculate base cost
            base_cost = cost_config.get("base", 0.0)

            # Calculate distance costs
            h_cost = h_distance * cost_config.get("per_meter", 0.0)
            v_cost = v_distance * cost_config.get("per_meter_vertical", 0.0)

            total_cost = base_cost + h_cost + v_cost

            # Apply environmental multiplier
            if environment:
                # Use comprehensive environmental calculation
                drone_altitude = (start_pos.get("z", 0.0) + end_pos.get("z", 0.0)) / 2.0
                env_multiplier, _ = cls.calculate_environmental_multiplier(
                    environment, drone_heading, drone_altitude
                )
            else:
                # Legacy: use weather-only multiplier
                env_multiplier = cls.ENVIRONMENTAL_MULTIPLIERS.get(weather, 1.0)

            total_cost *= env_multiplier

            # Apply safety cap
            return min(total_cost, cls.MAX_BATTERY_PER_COMMAND)
        else:
            # Fixed cost command
            return cost_config

    @classmethod
    def get_command_cost(cls, command: str) -> float:
        """Get fixed cost for a command (non-movement commands)"""
        cost = cls.COMMAND_COSTS.get(command, 0.0)

        if isinstance(cost, dict):
            return cost.get("base", 0.0)
        return cost

    @classmethod
    def check_battery_sufficient(cls, command: str, current_battery_level: float,
                                 start_pos: dict, end_pos: dict,
                                 environment: dict = None, drone_heading: float = 0.0) -> dict:
        """Check if drone has sufficient battery to complete a movement command

        Args:
            command: Command name (move_to, move_towards, move_along_path)
            current_battery_level: Current battery level in percentage
            start_pos: Starting position dict with x, y, z
            end_pos: Ending position dict with x, y, z
            environment: Environment dictionary (optional)
            drone_heading: Drone's heading in degrees (for wind calculations)

        Returns:
            Dictionary with:
                - sufficient (bool): True if battery is sufficient
                - required_battery (float): Battery percentage required for movement
                - available_battery (float): Usable battery (excluding safety margin)
                - shortage (float): Battery shortage if insufficient (negative if sufficient)
                - message (str): Human-readable message
        """
        # Calculate required battery for this movement
        required_battery = cls.calculate_movement_cost(
            command=command,
            start_pos=start_pos,
            end_pos=end_pos,
            weather="clear",  # Fallback
            environment=environment,
            drone_heading=drone_heading
        )

        # Available battery (current level minus critical safety margin)
        available_battery = current_battery_level - cls.CRITICAL_BATTERY_LEVEL

        # Check if sufficient
        shortage = required_battery - available_battery
        sufficient = shortage <= 0

        if sufficient:
            remaining_after = current_battery_level - required_battery
            message = (f"Battery sufficient: requires {required_battery:.2f}%, "
                      f"have {available_battery:.2f}% available "
                      f"(will have {remaining_after:.2f}% after movement)")
        else:
            message = (f"Insufficient battery: requires {required_battery:.2f}%, "
                      f"but only {available_battery:.2f}% available "
                      f"(shortage: {shortage:.2f}%). "
                      f"Current level: {current_battery_level:.1f}%, "
                      f"critical reserve: {cls.CRITICAL_BATTERY_LEVEL}%")

        return {
            "sufficient": sufficient,
            "required_battery": required_battery,
            "available_battery": available_battery,
            "current_battery": current_battery_level,
            "shortage": shortage,
            "critical_reserve": cls.CRITICAL_BATTERY_LEVEL,
            "message": message
        }

    @classmethod
    def predict_flight_range(cls, battery_level: float, battery_capacity: float,
                            environment: dict, drone_altitude: float = 10.0) -> dict:
        """Predict how far a drone can fly given current battery and environment

        Args:
            battery_level: Current battery level in percentage
            battery_capacity: Battery capacity in mAh (for future use)
            environment: Environment dictionary
            drone_altitude: Flying altitude in meters

        Returns:
            Dictionary with predictions for different flight patterns
        """
        _ = battery_capacity  # Reserved for future energy-based calculations
        # Calculate environmental multiplier
        env_multiplier, breakdown = cls.calculate_environmental_multiplier(
            environment, drone_heading=0.0, drone_altitude=drone_altitude
        )

        # Get base movement costs
        per_meter_horizontal = cls.COMMAND_COSTS["move_to"]["per_meter"]
        per_meter_vertical = cls.COMMAND_COSTS["move_to"]["per_meter_vertical"]

        # Apply environmental multiplier
        effective_h_cost = per_meter_horizontal * env_multiplier
        effective_v_cost = per_meter_vertical * env_multiplier

        # Calculate maximum distances (leaving 5% safety margin)
        usable_battery = max(0.0, battery_level - cls.CRITICAL_BATTERY_LEVEL)

        max_horizontal_distance = usable_battery / effective_h_cost if effective_h_cost > 0 else 0
        max_vertical_distance = usable_battery / effective_v_cost if effective_v_cost > 0 else 0

        return {
            "battery_level": battery_level,
            "usable_battery": usable_battery,
            "environmental_multiplier": env_multiplier,
            "multiplier_breakdown": breakdown,
            "max_horizontal_range_m": max_horizontal_distance,
            "max_vertical_range_m": max_vertical_distance,
            "estimated_flight_time_min": (usable_battery / (cls.IDLE_CONSUMPTION_PER_MINUTE or 0.5)) if cls.IDLE_CONSUMPTION_PER_MINUTE > 0 else 0,
            "safety_margin_percent": cls.CRITICAL_BATTERY_LEVEL,
        }

    @classmethod
    def get_optimal_conditions(cls) -> dict:
        """Get optimal environmental conditions for battery efficiency

        Returns:
            Dictionary describing ideal conditions
        """
        return {
            "weather": "clear",
            "temperature_range": (15, 25),
            "temperature_optimal": 20,
            "wind_speed_max": 2.0,
            "humidity_range": (30, 70),
            "humidity_optimal": 50,
            "pressure_optimal": 1013.25,
            "description": "Clear weather, 20°C, calm wind (<2 m/s), 50% humidity, sea-level pressure"
        }

    @classmethod
    def evaluate_flight_conditions(cls, environment: dict, drone_altitude: float = 10.0) -> dict:
        """Evaluate current environmental conditions and provide recommendations

        Args:
            environment: Environment dictionary
            drone_altitude: Planned flying altitude in meters

        Returns:
            Dictionary with condition evaluation and recommendations
        """
        # Calculate multiplier and breakdown
        total_mult, breakdown = cls.calculate_environmental_multiplier(
            environment, drone_heading=0.0, drone_altitude=drone_altitude
        )

        # Determine condition severity
        if total_mult <= 1.1:
            severity = "excellent"
            recommendation = "Optimal conditions for flight operations"
        elif total_mult <= 1.3:
            severity = "good"
            recommendation = "Good conditions, minor impact on battery life"
        elif total_mult <= 1.6:
            severity = "moderate"
            recommendation = "Moderate conditions, expect reduced flight time (up to 60%)"
        elif total_mult <= 2.0:
            severity = "poor"
            recommendation = "Poor conditions, flight time significantly reduced. Consider delaying mission."
        else:
            severity = "dangerous"
            recommendation = "Dangerous conditions! Flight not recommended unless critical."

        # Identify problem factors
        problem_factors = []
        for factor, value in breakdown.items():
            if value > 1.15:
                problem_factors.append({
                    "factor": factor,
                    "multiplier": value,
                    "impact": "high" if value > 1.3 else "moderate"
                })

        # Get environment details
        weather = environment.get("weather", "clear")
        temperature = environment.get("temperature", 22.0)
        wind_speed = environment.get("wind_speed", 0.0)
        humidity = environment.get("humidity", 50.0)

        return {
            "severity": severity,
            "total_multiplier": total_mult,
            "battery_impact_percent": (total_mult - 1.0) * 100,
            "recommendation": recommendation,
            "problem_factors": problem_factors,
            "current_conditions": {
                "weather": weather,
                "temperature_c": temperature,
                "wind_speed_ms": wind_speed,
                "humidity_percent": humidity,
                "altitude_m": drone_altitude
            },
            "multiplier_breakdown": breakdown
        }

    @classmethod
    def should_delay_mission(cls, environment: dict, required_range: float,
                            battery_level: float, drone_altitude: float = 10.0) -> dict:
        """Determine if a mission should be delayed due to environmental conditions

        Args:
            environment: Environment dictionary
            required_range: Required flight distance in meters
            battery_level: Current battery level in percentage
            drone_altitude: Planned flying altitude

        Returns:
            Dictionary with decision and reasoning
        """
        # Get flight range prediction
        range_prediction = cls.predict_flight_range(
            battery_level, 5000, environment, drone_altitude  # Using typical 5000mAh
        )

        max_range = range_prediction["max_horizontal_range_m"]
        env_multiplier = range_prediction["environmental_multiplier"]

        # Check if mission is possible
        # Add 20% safety margin for return trip
        safe_range = max_range * 0.4  # 40% of max range (allows for return trip with margin)

        if required_range > safe_range:
            should_delay = True
            reason = f"Insufficient range: Mission requires {required_range:.0f}m, but safe range is only {safe_range:.0f}m"
        elif env_multiplier > 1.8:
            should_delay = True
            reason = f"Extreme conditions: Environmental multiplier is {env_multiplier:.2f}x (dangerous)"
        elif battery_level < 50.0:
            should_delay = True
            reason = f"Low battery: Current level is {battery_level:.1f}%, recommend charging above 50%"
        else:
            should_delay = False
            reason = "Conditions acceptable for mission"

        return {
            "should_delay": should_delay,
            "reason": reason,
            "required_range_m": required_range,
            "available_safe_range_m": safe_range,
            "max_range_m": max_range,
            "environmental_multiplier": env_multiplier,
            "battery_level": battery_level,
            "recommendation": "Wait for better conditions" if should_delay else "Proceed with mission"
        }
