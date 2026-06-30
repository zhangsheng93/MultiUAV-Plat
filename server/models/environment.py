from enum import Enum
from typing import Dict, List, Optional, Union
import time

from config.util import generate_random_id


class WeatherCondition(str, Enum):
    """Enum representing possible weather conditions"""
    CLEAR = "clear"              # Clear skies
    PARTLY_CLOUDY = "partly_cloudy"  # Partly cloudy
    CLOUDY = "cloudy"            # Cloudy
    RAIN = "rain"                # Rain
    HEAVY_RAIN = "heavy_rain"    # Heavy rain
    SNOW = "snow"                # Snow
    FOG = "fog"                  # Fog
    WINDY = "windy"              # Windy
    STORM = "storm"              # Storm


class WindDirection(str, Enum):
    """Enum representing wind directions"""
    NORTH = "north"
    NORTHEAST = "northeast"
    EAST = "east"
    SOUTHEAST = "southeast"
    SOUTH = "south"
    SOUTHWEST = "southwest"
    WEST = "west"
    NORTHWEST = "northwest"


class Environment:
    """Class representing environmental conditions"""
    
    def __init__(
        self,
        name: str = "Default Environment",
        weather: Union[WeatherCondition, str] = WeatherCondition.CLEAR,
        temperature: float = 22.0,  # in Celsius
        humidity: float = 50.0,     # percentage
        pressure: float = 1013.25,  # hPa (hectopascals)
        wind_speed: float = 0.0,    # in m/s
        wind_direction: Union[WindDirection, str] = WindDirection.NORTH,
        visibility: float = 10000.0,  # in meters
        environment_id: Optional[str] = None,
        created_at: Optional[float] = None,
        last_updated: Optional[float] = None
    ):
        if isinstance(weather, str):
            weather = WeatherCondition(weather)
        if isinstance(wind_direction, str):
            wind_direction = WindDirection(wind_direction)

        current_time = time.time()

        self.id = environment_id or generate_random_id()
        self.name = name
        self.weather = weather
        self.temperature = temperature
        self.humidity = humidity
        self.pressure = pressure
        self.wind_speed = wind_speed
        self.wind_direction = wind_direction
        self.visibility = visibility
        self.created_at = created_at if created_at is not None else current_time
        self.last_updated = last_updated if last_updated is not None else self.created_at
    
    def to_dict(self) -> Dict:
        """Convert environment object to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "weather": self.weather,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "pressure": self.pressure,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "visibility": self.visibility,
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }
    
    def update_weather(self, weather: WeatherCondition) -> None:
        """Update the weather condition"""
        self.weather = weather
        self.last_updated = time.time()
    
    def update_temperature(self, temperature: float) -> None:
        """Update the temperature"""
        self.temperature = temperature
        self.last_updated = time.time()
    
    def update_wind(self, speed: float, direction: WindDirection) -> None:
        """Update wind conditions"""
        self.wind_speed = speed
        self.wind_direction = direction
        self.last_updated = time.time()
