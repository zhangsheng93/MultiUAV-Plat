from typing import Dict, List, Any, Optional
import time
import random

from models.environment import Environment, WeatherCondition, WindDirection


class EnvironmentController:
    """Controller class for managing environmental conditions"""
    
    def __init__(self):
        self.environments: Dict[str, Environment] = {}
        self.current_environment_id: Optional[str] = None
    
    def _ensure_current_environment_id(self) -> Optional[str]:
        """Ensure current_environment_id references an existing environment."""
        if not self.environments:
            return None

        if self.current_environment_id in self.environments:
            return self.current_environment_id

        # Fall back to the first available environment when unset/invalid
        self.current_environment_id = next(iter(self.environments.keys()))
        return self.current_environment_id
    
    
    def add_environment(self, environment_data: Dict[str, Any]) -> Dict:
        """Add a new environment to the system

        Args:
            environment_data: Dictionary containing environment data with keys:
                - name: Environment name (required)
                - weather: Weather condition (required)
                - temperature: Temperature in Celsius (required)
                - humidity: Humidity percentage (required)
                - pressure: Atmospheric pressure in hPa (required)
                - wind_speed: Wind speed in m/s (required)
                - wind_direction: Wind direction (required)
                - visibility: Visibility in meters (required)
                - id: Optional ID to preserve when restoring from sessions
                - created_at: Optional creation timestamp
                - last_updated: Optional last update timestamp

        Returns:
            Dict representation of the created environment
        """
        # Extract optional ID and timestamps
        environment_id = environment_data.get("id")
        created_at = environment_data.get("created_at")
        last_updated = environment_data.get("last_updated")

        # Create environment instance
        env = Environment(
            name=environment_data["name"],
            weather=environment_data["weather"],
            temperature=environment_data["temperature"],
            humidity=environment_data["humidity"],
            pressure=environment_data["pressure"],
            wind_speed=environment_data["wind_speed"],
            wind_direction=environment_data["wind_direction"],
            visibility=environment_data["visibility"],
            environment_id=environment_id,
            created_at=created_at,
            last_updated=last_updated
        )

        self.environments[env.id] = env
        return env.to_dict()
    
    def get_all_environments(self) -> List[Dict]:
        """Get all environments"""
        return [env.to_dict() for env in self.environments.values()]
    
    def get_environment(self, environment_id: str) -> Optional[Dict]:
        """Get a specific environment by ID"""
        if environment_id in self.environments:
            return self.environments[environment_id].to_dict()
        return None
    
    def _add_default_environment(self) -> None:
        """Add a default environment to the system"""
        default_env = Environment(
            name="Default Environment",
            weather=WeatherCondition.CLEAR,
            temperature=22.0,
            humidity=50.0,
            pressure=1013.25,
            wind_speed=0.0,
            wind_direction=WindDirection.NORTH,
            visibility=10000.0
        )
        self.environments[default_env.id] = default_env
        self.current_environment_id = default_env.id
    
    def get_current_environment(self) -> Dict:
        """Get the current active environment"""
        if not self.environments:
            self._add_default_environment()

        current_id = self._ensure_current_environment_id()
        if current_id:
            return self.environments[current_id].to_dict()

        # If no current environment is set, return the first one or create a default
        if not self.environments:
            self._add_default_environment()
        return next(iter(self.environments.values())).to_dict()
    
    def set_current_environment(self, environment_id: str) -> Optional[Dict]:
        """Set the current active environment"""
        if environment_id in self.environments:
            self.current_environment_id = environment_id
            return self.environments[environment_id].to_dict()
        return None
    
    def update_environment(self, environment_id: str, updates: Dict[str, Any]) -> Optional[Dict]:
        """Update an environment's properties"""
        if environment_id not in self.environments:
            return None
        
        env = self.environments[environment_id]
        
        # Update properties if provided
        if "name" in updates:
            env.name = updates["name"]
        
        if "weather" in updates:
            env.update_weather(updates["weather"])
        
        if "temperature" in updates:
            env.update_temperature(updates["temperature"])
        
        if "humidity" in updates:
            env.humidity = updates["humidity"]
            env.last_updated = time.time()
        
        if "pressure" in updates:
            env.pressure = updates["pressure"]
            env.last_updated = time.time()
        
        if "wind_speed" in updates and "wind_direction" in updates:
            env.update_wind(updates["wind_speed"], updates["wind_direction"])
        elif "wind_speed" in updates:
            env.update_wind(updates["wind_speed"], env.wind_direction)
        elif "wind_direction" in updates:
            env.update_wind(env.wind_speed, updates["wind_direction"])
        
        if "visibility" in updates:
            env.visibility = updates["visibility"]
            env.last_updated = time.time()
        
        return env.to_dict()

    def is_environment_current(self, environment_id: str) -> bool:
        """Return True when the provided environment is the active one."""
        current_id = self._ensure_current_environment_id()
        return current_id == environment_id
    
    def delete_environment(self, environment_id: str) -> bool:
        """Delete an environment"""
        if environment_id not in self.environments:
            return False

        # Prevent deleting the current environment
        if self.is_environment_current(environment_id):
            return False

        # Don't delete if it's the only environment in the system
        if len(self.environments) <= 1:
            return False
        
        del self.environments[environment_id]
        return True
    
    def simulate_weather_changes(self) -> None:
        """Simulate gradual weather changes over time"""
        if not self.current_environment_id:
            return
        
        env = self.environments[self.current_environment_id]
        
        # Small random changes to temperature (±0.5°C)
        temp_change = random.uniform(-0.5, 0.5)
        env.update_temperature(env.temperature + temp_change)
        
        # Small random changes to wind
        wind_change = random.uniform(-0.2, 0.2)
        new_wind = max(0, env.wind_speed + wind_change)  # Wind speed can't be negative
        
        # Occasionally change wind direction
        if random.random() < 0.05:  # 5% chance to change direction
            directions = list(WindDirection)
            new_direction = random.choice(directions)
            env.update_wind(new_wind, new_direction)
        else:
            env.update_wind(new_wind, env.wind_direction)
        
        # Occasionally change weather condition (very rare)
        if random.random() < 0.001:  # 1% chance to change weather
            weather_conditions = list(WeatherCondition)
            new_weather = random.choice(weather_conditions)
            env.update_weather(new_weather)
