"""
UAV API Client
Wrapper for the UAV Control System API to simplify drone operations
"""
import json
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional

from logging_config import get_logger


logger = get_logger(__name__)
MAX_LOG_VALUE_LENGTH = 1000
PATH_RESULT_FIELDS = [
    "successful_points_count",
    "successful_points",
    "unsuccessful_points_count",
    "unsuccessful_points",
]


def _format_log_value(value: Any) -> str:
    """Serialize request details for compact operational logs."""
    try:
        text = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = str(value)
    text = " ".join(text.replace("\r", " ").replace("\n", " ").replace("\t", " ").split())
    if len(text) > MAX_LOG_VALUE_LENGTH:
        return f"{text[:MAX_LOG_VALUE_LENGTH]}...<truncated>"
    return text


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def _response_json_safe(response: Any) -> Any:
    try:
        return response.json()
    except Exception:
        return None


def _compact_command_response(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    fields = [
        "status",
        "success",
        "partial_success",
        "message",
        "drone_id",
        "command",
        "position",
        "final_position",
        "completed_waypoints",
        "waypoint_count",
        "current_waypoint_index",
    ]
    if value.get("command") == "move_along_path" or any(value.get(key) is not None for key in PATH_RESULT_FIELDS):
        fields.extend(PATH_RESULT_FIELDS)
    compact = {key: value.get(key) for key in fields if key in value and value.get(key) is not None}
    return compact or None


def _sanitize_command_response(endpoint: str, value: Any) -> Any:
    if not isinstance(value, dict) or "/command/" not in endpoint:
        return value
    if endpoint.endswith("/command/move_along_path") or value.get("command") == "move_along_path":
        return value
    return {
        key: item
        for key, item in value.items()
        if key not in PATH_RESULT_FIELDS
    }


class UAVAPIClient:
    """Client for interacting with the UAV Control System API"""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        """
        Initialize UAV API Client

        Args:
            base_url: Base URL of the UAV API server
            api_key: Optional API key for authentication (defaults to USER role if not provided)
                    - None or empty: USER role (basic access)
                    - Valid key: SYSTEM or ADMIN role (based on key)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {}
        if self.api_key:
            self.headers['X-API-Key'] = self.api_key
        self._api_call_records: Optional[List[Dict[str, Any]]] = None

    def start_api_call_recording(self) -> None:
        self._api_call_records = []

    def get_api_call_records(self) -> List[Dict[str, Any]]:
        return list(self._api_call_records or [])

    def stop_api_call_recording(self) -> List[Dict[str, Any]]:
        records = self.get_api_call_records()
        self._api_call_records = None
        return records

    def _start_api_call_record(self, method: str, endpoint: str, kwargs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if self._api_call_records is None:
            return None
        record = {
            "index": len(self._api_call_records) + 1,
            "started_at": datetime.now().isoformat(),
            "method": method,
            "endpoint": endpoint,
            "params": _json_safe(kwargs.get("params")),
            "json": _json_safe(kwargs.get("json")),
            "data": _json_safe(kwargs.get("data")),
            "success": None,
            "status_code": None,
            "response": None,
            "error": None,
        }
        self._api_call_records.append(record)
        return record

    def _finish_api_call_record(
        self,
        record: Optional[Dict[str, Any]],
        *,
        success: bool,
        status_code: Optional[int] = None,
        response: Any = None,
        error: Optional[str] = None,
    ) -> None:
        if record is None:
            return
        record["completed_at"] = datetime.now().isoformat()
        record["success"] = success
        record["status_code"] = status_code
        record["response"] = _json_safe(response)
        record["error"] = error

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make HTTP request to the API"""
        url = f"{self.base_url}{endpoint}"

        # Merge authentication headers with any provided headers
        headers = kwargs.pop('headers', {})
        headers.update(self.headers)

        logger.info(
            "MultiUAV-Plat request method=%s endpoint=%s params=%s json=%s data=%s",
            method,
            endpoint,
            _format_log_value(kwargs.get("params")),
            _format_log_value(kwargs.get("json")),
            _format_log_value(kwargs.get("data")),
        )
        api_call_record = self._start_api_call_record(method, endpoint, kwargs)

        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            if response.status_code == 204:
                self._finish_api_call_record(
                    api_call_record,
                    success=True,
                    status_code=response.status_code,
                    response=None,
                )
                return None
            result = response.json()
            result = _sanitize_command_response(endpoint, result)
            record_response = _compact_command_response(result) or result
            compact_response = _compact_command_response(result)
            if "/command/" in endpoint and compact_response is not None:
                logger.info(
                    "MultiUAV-Plat command response endpoint=%s response=%s",
                    endpoint,
                    _format_log_value(compact_response),
                )
            self._finish_api_call_record(
                api_call_record,
                success=True,
                status_code=response.status_code,
                response=record_response,
            )
            return result
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                error_message = "Authentication failed: Invalid API key"
                self._finish_api_call_record(
                    api_call_record,
                    success=False,
                    status_code=e.response.status_code,
                    response=_response_json_safe(e.response),
                    error=error_message,
                )
                raise Exception(error_message)
            elif e.response.status_code == 403:
                error_response = _response_json_safe(e.response)
                error_detail = error_response.get('detail', 'Access denied') if isinstance(error_response, dict) else 'Access denied'
                error_message = f"Permission denied: {error_detail}"
                self._finish_api_call_record(
                    api_call_record,
                    success=False,
                    status_code=e.response.status_code,
                    response=error_response,
                    error=error_message,
                )
                raise Exception(error_message)
            error_message = f"API request failed: {e}"
            self._finish_api_call_record(
                api_call_record,
                success=False,
                status_code=e.response.status_code,
                response=_response_json_safe(e.response),
                error=error_message,
            )
            raise Exception(error_message)
        except requests.exceptions.RequestException as e:
            error_message = f"API request failed: {e}"
            self._finish_api_call_record(api_call_record, success=False, error=error_message)
            raise Exception(error_message)

    # Drone Operations
    def list_drones(self) -> List[Dict[str, Any]]:
        """Get all drones in the current session"""
        return self._request('GET', '/drones')

    def get_drone_status(self, drone_id: str) -> Dict[str, Any]:
        """Get detailed status of a specific drone"""
        return self._request('GET', f'/drones/{drone_id}')

    def take_off(self, drone_id: str, altitude: float = 10.0) -> Dict[str, Any]:
        """Command drone to take off to specified altitude"""
        return self._request('POST', f'/drones/{drone_id}/command/take_off',params={'altitude': altitude})

    def land(self, drone_id: str) -> Dict[str, Any]:
        """Command drone to land at current position"""
        return self._request('POST', f'/drones/{drone_id}/command/land')

    def move_to(self, drone_id: str, x: float, y: float, z: float) -> Dict[str, Any]:
        """Move drone to specific coordinates"""
        return self._request('POST', f'/drones/{drone_id}/command/move_to',
                            params={'x': x, 'y': y, 'z': z})

    def move_along_path(
        self,
        drone_id: str,
        waypoints: List[Dict[str, float]],
        allow_partial_move: bool = True,
    ) -> Dict[str, Any]:
        """Move drone along one or more 2D/3D waypoints."""
        return self._request('POST', f'/drones/{drone_id}/command/move_along_path',
                            json={
                                'waypoints': waypoints,
                                'allow_partial_move': allow_partial_move,
                            })

    def change_altitude(self, drone_id: str, altitude: float) -> Dict[str, Any]:
        """Change drone altitude while maintaining X/Y position"""
        return self._request('POST', f'/drones/{drone_id}/command/change_altitude',
                            params={'altitude': altitude})

    def hover(self, drone_id: str, duration: Optional[float] = None) -> Dict[str, Any]:
        """
        Command drone to hover at current position.
        
        Args:
            drone_id: ID of the drone
            duration: Optional duration to hover in seconds
        """
        params = {}
        if duration is not None:
            params['duration'] = duration
        return self._request('POST', f'/drones/{drone_id}/command/hover', params=params)

    def rotate(self, drone_id: str, heading: float) -> Dict[str, Any]:
        """Rotate drone to face specific direction (0-360 degrees)"""
        return self._request('POST', f'/drones/{drone_id}/command/rotate',
                            params={'heading': heading})
    
    def move_towards(self, drone_id: str, distance: float, heading: Optional[float] = None, 
                    dz: Optional[float] = None) -> Dict[str, Any]:
        """
        Move drone a specific distance in a direction.
        
        Args:
            drone_id: ID of the drone
            distance: Distance to move in meters
            heading: Optional heading direction (0-360). If None, uses current heading.
            dz: Optional vertical component (altitude change)
        """
        params = {'distance': distance}
        if heading is not None:
            params['heading'] = heading
        if dz is not None:
            params['dz'] = dz
        return self._request('POST', f'/drones/{drone_id}/command/move_towards', params=params)

    def return_home(self, drone_id: str) -> Dict[str, Any]:
        """Command drone to return to home position"""
        return self._request('POST', f'/drones/{drone_id}/command/return_home')
        
    def set_home(self, drone_id: str) -> Dict[str, Any]:
        """Set current position as home position"""
        return self._request('POST', f'/drones/{drone_id}/command/set_home')
        
    def calibrate(self, drone_id: str) -> Dict[str, Any]:
        """Calibrate drone sensors"""
        return self._request('POST', f'/drones/{drone_id}/command/calibrate')

    def charge(self, drone_id: str, charge_amount: float) -> Dict[str, Any]:
        """Charge drone battery (when landed)"""
        return self._request('POST', f'/drones/{drone_id}/command/charge',
                            params={'charge_amount': charge_amount})

    def take_photo(self, drone_id: str) -> Dict[str, Any]:
        """Take a photo with drone camera"""
        return self._request('POST', f'/drones/{drone_id}/command/take_photo')
        
    def send_message(self, drone_id: str, target_drone_id: str, message: str) -> Dict[str, Any]:
        """
        Send a message to another drone.
        
        Args:
            drone_id: ID of the sender drone
            target_drone_id: ID of the recipient drone
            message: Content of the message
        """
        return self._request('POST', f'/drones/{drone_id}/command/send_message', 
                           params={'target_drone_id': target_drone_id, 'message': message})
                           
    def broadcast(self, drone_id: str, message: str) -> Dict[str, Any]:
        """
        Broadcast a message to all other drones.
        
        Args:
            drone_id: ID of the sender drone
            message: Content of the message
        """
        return self._request('POST', f'/drones/{drone_id}/command/broadcast', 
                           params={'message': message})

    # Session Operations
    def get_current_session(self) -> Dict[str, Any]:
        """Get information about current mission session"""
        return self._request('GET', '/sessions/current')

    def get_session_data(self, session_id: str = 'current') -> Dict[str, Any]:
        """Get all entities in a session (drones, targets, obstacles, environment)"""
        return self._request('GET', f'/sessions/{session_id}/data')

    def get_task_progress(self, session_id: str = 'current') -> Dict[str, Any]:
        """Get mission task completion progress"""
        return self._request('GET', f'/sessions/{session_id}/task-progress')

    # Environment Operations
    def get_weather(self) -> Dict[str, Any]:
        """Get current weather conditions"""
        return self._request('GET', '/environments/current')

    def get_target(self, target_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific target"""
        return self._request('GET', f'/targets/{target_id}')

    def get_waypoints(self) -> List[Dict[str, Any]]:
        """Get all charging station waypoints"""
        return self._request('GET', '/targets/waypoints')

    def get_obstacle(self, obstacle_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific obstacle"""
        return self._request('GET', f'/obstacles/{obstacle_id}')

    def get_nearby_entities(self, drone_id: str) -> Dict[str, Any]:
        """Get entities near a drone (within perceived radius)"""
        return self._request('GET', f'/drones/{drone_id}/nearby')

    # Safety Operations
    def check_point_collision(self, x: float, y: float, z: float,
                             safety_margin: float = 0.0) -> Optional[Dict[str, Any]]:
        """Check if a point collides with any obstacle"""
        result = self._request('POST', '/obstacles/collision/check',
                              json={
                                  'point': {'x': x, 'y': y, 'z': z},
                                  'safety_margin': safety_margin
                              })
        return result

    def check_path_collision(self, start_x: float, start_y: float, start_z: float,
                            end_x: float, end_y: float, end_z: float,
                            safety_margin: float = 1.0) -> Optional[Dict[str, Any]]:
        """Check if a path intersects any obstacle"""
        result = self._request('POST', '/obstacles/collision/path',
                              json={
                                  'start': {'x': start_x, 'y': start_y, 'z': start_z},
                                  'end': {'x': end_x, 'y': end_y, 'z': end_z},
                                  'safety_margin': safety_margin
                              })
        return result
