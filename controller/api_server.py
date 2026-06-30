import requests
import json
import time
from datetime import datetime
import logging
from typing import Optional, Dict, Any, Callable, Union
from app_settings import get_settings, resolve_api_key

class APIServer:
    """
    Unified API Server wrapper for handling all backend communication.
    Centralizes authentication, error handling, logging, and history recording.
    """

    def __init__(
        self, 
        base_url: str = "http://127.0.0.1:8000", 
        logger: Optional[logging.Logger] = None, 
        history_recorder: Optional[Callable[[Dict[str, Any]], None]] = None,
        error_handler: Optional[Callable[[str, str], None]] = None
    ):
        """
        Initialize the API Server wrapper.

        Args:
            base_url: The base URL of the API (e.g., "http://127.0.0.1:8000")
            logger: Optional logger instance
            history_recorder: Optional callback to record request history (receives a dict)
            error_handler: Optional callback to handle errors (receives title, message)
        """
        self.api_base_url = get_settings().get('api_base_url', base_url) or base_url
        # Load API key from settings, falling back to the built-in ADMIN controller key.
        self.api_key = resolve_api_key(get_settings().get('api_key'))
        self.logger = logger or logging.getLogger("APIServer")
        self.history_recorder = history_recorder
        self.error_handler = error_handler
        self._server_unavailable = False
        self._connection_error_shown = False

    def infer_api_success(self, method: str, endpoint: str, response_data: Any, status_code: Optional[int]) -> bool:
        """Infer business-level API success from response content and status code."""
        try:
            if status_code is None or status_code < 200 or status_code >= 300:
                return False
            # 2xx
            if isinstance(response_data, dict):
                if 'success' in response_data:
                    return bool(response_data.get('success'))
                if 'status' in response_data:
                    status_val = str(response_data.get('status')).lower()
                    if status_val in {'success', 'partial_success', 'ok', 'completed'}:
                        return True
                    if status_val in {'error', 'failed', 'failure'}:
                        return False
                if 'error' in response_data:
                    return False
                if 'id' in response_data:
                    return True
                # Default for dict in 2xx
                return True
            # Lists and others considered successful in 2xx
            return True
        except Exception as exc:
            try:
                self.logger.debug(f"infer_api_success fallback for {method} {endpoint}: {exc}")
            except Exception:
                pass
            return False

    def make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        *,
        params: Optional[Dict[str, Any]] = None,
        expect_json: bool = True,
        show_error: bool = True
    ) -> Optional[Any]:
        """
        Make HTTP request to the API with comprehensive logging and error handling.
        """
        url = f"{self.api_base_url}{endpoint}"
        request_id = f"{method.upper()}_{endpoint.replace('/', '_')}_{int(time.time() * 1000)}"
        
        self.logger.info(f"[{request_id}] Starting API request, Method: {method.upper()}, Endpoint: {endpoint}, URL: {url}")
        
        if data:
            self.logger.info(f"[{request_id}] Request payload size: {len(json.dumps(data))}")
            self.logger.debug(f"[{request_id}] Request payload: {json.dumps(data, indent=2)}")
        if params:
            self.logger.debug(f"[{request_id}] Request params: {params}")
        
        start_time = time.time()
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'UAV-Controller-Unified/1.0',
                'X-API-Key': self.api_key
            }

            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, params=params, timeout=30)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, headers=headers, params=params, timeout=30)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, params=params, timeout=30)
            elif method.upper() == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, params=params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # If we get here, server is available
            if self._server_unavailable:
                self._server_unavailable = False
                self.logger.info("Server connection restored")

            duration = time.time() - start_time
            self.logger.info(f"[{request_id}] Response received in {duration:.3f}s, Status code: {response.status_code}")
            
            # Handle successful responses
            if response.status_code in [200, 201, 204]:
                if not expect_json:
                    content = response.content or b""
                    api_success = True
                    if self.history_recorder:
                        self.history_recorder({
                            'request_id': request_id,
                            'timestamp': datetime.now().isoformat(),
                            'method': method.upper(),
                            'path': endpoint,
                            'url': url,
                            'request_body': data or params,
                            'duration_sec': round(duration, 3),
                            'status_code': response.status_code,
                            'success': api_success,
                            'response_body': {'bytes': len(content)},
                        })
                    return content
                
                if response.content:
                    try:
                        response_data = response.json()
                        self.logger.debug(f"[{request_id}] Request completed successfully, Response payload: {json.dumps(response_data, indent=2)}")
                        api_success = self.infer_api_success(method.upper(), endpoint, response_data, response.status_code)
                        
                        if self.history_recorder:
                            self.history_recorder({
                                'request_id': request_id,
                                'timestamp': datetime.now().isoformat(),
                                'method': method.upper(),
                                'path': endpoint,
                                'url': url,
                                'request_body': data or params,
                                'duration_sec': round(duration, 3),
                                'status_code': response.status_code,
                                'success': api_success,
                                'response_body': response_data,
                            })
                        return response_data
                    except json.JSONDecodeError as e:
                        # Fallback for non-JSON content if it was expected but failed
                        self.logger.error(f"[{request_id}] JSON decode error: {e}")
                        if self.history_recorder:
                             self.history_recorder({
                                'request_id': request_id,
                                'timestamp': datetime.now().isoformat(),
                                'method': method.upper(),
                                'path': endpoint,
                                'url': url,
                                'request_body': data or params,
                                'duration_sec': round(duration, 3),
                                'status_code': response.status_code,
                                'success': False,
                                'response_body': response.text,
                                'error': f"Invalid JSON response: {str(e)}"
                            })
                        if show_error and self.error_handler:
                            self.error_handler("Response Error", "Invalid JSON response from server")
                        return None
                else:
                    # Empty response (common for 204)
                    self.logger.info(f"[{request_id}] Request completed successfully (empty response)")
                    api_success = True
                    if self.history_recorder:
                        self.history_recorder({
                            'request_id': request_id,
                            'method': method.upper(),
                            'path': endpoint,
                            'url': url,
                            'request_body': data or params,
                            'timestamp': datetime.now().isoformat(),
                            'duration_sec': round(duration, 3),
                            'status_code': response.status_code,
                            'success': api_success,
                            'response_body': {},
                        })
                    return {}
            else:
                # Handle error responses
                error_msg = ""
                error_title = "API Error"
                
                if response.status_code == 401:
                    error_title = "Authentication Error"
                    error_msg = "Invalid API key. Check the key configured in Settings.\nThis application requires ADMIN role permissions."
                    self.logger.error(f"[{request_id}] Authentication failed: {error_msg}")
                elif response.status_code == 403:
                    error_title = "Authorization Error"
                    error_msg = f"Insufficient permissions: {response.text}\nThis application requires ADMIN role permissions."
                    self.logger.error(f"[{request_id}] Authorization failed: {error_msg}")
                else:
                    error_msg = f"Request failed: {response.status_code}\n{response.text}"
                    self.logger.error(f"[{request_id}] Request failed with status {response.status_code}: {response.text}")

                # Try to parse error body
                try:
                    error_body = response.json()
                except Exception:
                    error_body = response.text

                if self.history_recorder:
                    self.history_recorder({
                        'request_id': request_id,
                        'method': method.upper(),
                        'path': endpoint,
                        'url': url,
                        'request_body': data,
                        'timestamp': datetime.now().isoformat(),
                        'duration_sec': round(duration, 3),
                        'status_code': response.status_code,
                        'success': False,
                        'response_body': error_body,
                        'error': error_msg,
                    })
                
                if show_error and self.error_handler:
                    self.error_handler(error_title, error_msg)
                
                return None

        except requests.exceptions.Timeout as e:
            duration = time.time() - start_time
            error_msg = f"Request timeout after {duration:.3f}s: {str(e)}"
            self.logger.error(f"[{request_id}] {error_msg}")
            
            if self.history_recorder:
                self.history_recorder({
                    'request_id': request_id,
                    'method': method.upper(),
                    'path': endpoint,
                    'url': url,
                    'request_body': data,
                    'timestamp': datetime.now().isoformat(),
                    'duration_sec': round(duration, 3),
                    'status_code': None,
                    'success': False,
                    'response_body': None,
                    'error': error_msg,
                })
            
            if show_error and self.error_handler:
                self.error_handler("Timeout Error", "Request timed out. Please check your connection and try again.")
            return None
            
        except requests.exceptions.ConnectionError as e:
            duration = time.time() - start_time
            error_msg = f"Could not connect to the API server: {str(e)}"
            self._server_unavailable = True
            self.logger.error(f"[{request_id}] Connection error after {duration:.3f}s: {str(e)}")
            
            if self.history_recorder:
                self.history_recorder({
                    'request_id': request_id,
                    'method': method.upper(),
                    'path': endpoint,
                    'url': url,
                    'request_body': data,
                    'timestamp': datetime.now().isoformat(),
                    'duration_sec': round(duration, 3),
                    'status_code': None,
                    'success': False,
                    'response_body': None,
                    'error': error_msg,
                })
            
            if show_error and self.error_handler and not self._connection_error_shown:
                self._connection_error_shown = True # Only show once per session/reset
                self.error_handler("Connection Error", f"Could not connect to the API server at {self.api_base_url}.\nPlease ensure it's running.")
            return None
            
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            error_msg = f"Request failed: {str(e)}"
            self.logger.error(f"[{request_id}] Request exception after {duration:.3f}s: {str(e)}")
            
            if self.history_recorder:
                self.history_recorder({
                    'request_id': request_id,
                    'method': method.upper(),
                    'path': endpoint,
                    'url': url,
                    'request_body': data,
                    'timestamp': datetime.now().isoformat(),
                    'duration_sec': round(duration, 3),
                    'status_code': None,
                    'success': False,
                    'response_body': None,
                    'error': error_msg,
                })
            
            if show_error and self.error_handler:
                self.error_handler("Request Error", error_msg)
            return None
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(f"[{request_id}] Unexpected error after {duration:.3f}s: {str(e)}")
            self.logger.exception(f"[{request_id}] Full exception details:")
            
            if self.history_recorder:
                self.history_recorder({
                    'request_id': request_id,
                    'method': method.upper(),
                    'path': endpoint,
                    'url': url,
                    'request_body': data,
                    'timestamp': datetime.now().isoformat(),
                    'duration_sec': round(duration, 3),
                    'status_code': None,
                    'success': False,
                    'response_body': None,
                    'error': error_msg,
                })
            
            if show_error and self.error_handler:
                self.error_handler("Error", error_msg)
            return None

    def reset_connection_error_flag(self):
        """Reset the connection error flag to allow showing the error dialog again."""
        self._connection_error_shown = False

    # ------------------------------------------------------------------
    # API wrapper methods
    # ------------------------------------------------------------------
    
    def api_get_sessions(self, show_error: bool = True):
        return self.make_request('GET', '/sessions', show_error=show_error)

    def api_get_current_session(self, include_data: bool = False, show_error: bool = True):
        endpoint = '/sessions/current?data=true' if include_data else '/sessions/current'
        return self.make_request('GET', endpoint, show_error=show_error)

    def api_get_current_session_with_data(self):
        return self.make_request('GET', '/sessions/current?data=true')

    def api_get_session_data(self, session_id: str, show_error: bool = True):
        return self.make_request('GET', f'/sessions/{session_id}/data', show_error=show_error)
    
    def api_get_session_info(self):
        """Get current session basic info."""
        return self.make_request('GET', '/sessions/current')

    def api_get_session_with_data(self):
        """Get current session with full data."""
        return self.make_request('GET', '/sessions/current?data=true')

    def api_get_session_screenshot(
        self,
        fmt: str = "png",
        width: int = 1024,
        height: int = 768,
        show_status: bool = False,
        show_error: bool = True
    ):
        endpoint = "/sessions/current/screenshot"
        params = {"format": fmt, "width": width, "height": height, "show_status": str(bool(show_status)).lower()}
        return self.make_request('GET', endpoint, params=params, expect_json=False, show_error=show_error)

    def api_get_session_task(self, session_id: str, task_id: str):
        return self.make_request('GET', f'/sessions/{session_id}/tasks/{task_id}')

    def api_get_session_tasks(self, session_id: str):
        return self.make_request('GET', f'/sessions/{session_id}/tasks')

    def api_get_current_session_tasks(self):
        return self.make_request('GET', '/sessions/current/tasks')

    def api_get_current_session_request_history(self, limit: int = 1000, show_error: bool = False):
        """Get recent HTTP request history for the current session."""
        return self.make_request(
            'GET',
            '/sessions/current/request-history',
            params={'limit': limit},
            show_error=show_error,
        )

    def api_clear_current_session_request_history(self, show_error: bool = False):
        """Clear runtime HTTP request history for the current session."""
        return self.make_request(
            'DELETE',
            '/sessions/current/request-history',
            show_error=show_error,
        )


    def api_get_drones(self, session_id: Optional[str] = None, show_error: bool = True):
        params = {'session_id': session_id} if session_id else None
        return self.make_request('GET', '/drones', params=params, show_error=show_error)

    def api_get_drone(self, drone_id: str):
        return self.make_request('GET', f'/drones/{drone_id}')

    def api_get_nearby_drones(self, drone_id: str):
        return self.make_request('GET', f'/drones/{drone_id}/nearby')

    def api_get_targets(self, session_id: Optional[str] = None, show_error: bool = True):
        params = {'session_id': session_id} if session_id else None
        return self.make_request('GET', '/targets', params=params, show_error=show_error)

    def api_get_target(self, target_id: str):
        return self.make_request('GET', f'/targets/{target_id}')

    def api_get_obstacles(self, session_id: Optional[str] = None, show_error: bool = True):
        params = {'session_id': session_id} if session_id else None
        return self.make_request('GET', '/obstacles', params=params, show_error=show_error)

    def api_get_obstacle(self, obstacle_id: str):
        return self.make_request('GET', f'/obstacles/{obstacle_id}')

    def api_get_environments(self, show_error: bool = True):
        return self.make_request('GET', '/environments', show_error=show_error)

    def api_get_environment(self, env_id: str):
        return self.make_request('GET', f'/environments/{env_id}')
        
    def api_create_session(self, session_request: Dict[str, Any], show_error: bool = True):
        return self.make_request('POST', '/sessions', session_request, show_error=show_error)
        
    def api_new_session(self, save_payload: Dict[str, Any], show_error: bool = True):
        return self.make_request('POST', '/sessions', save_payload, show_error=show_error)

    def api_set_session_as_current(self, session_id: str, show_error: bool = True):
        return self.make_request('POST', f'/sessions/{session_id}/set-current', show_error=show_error)

    def api_new_session_with_id(self, session_id: str, payload: Dict[str, Any], show_error: bool = True):
        """Create or replace a session with a specific ID."""
        return self.make_request('POST', f'/sessions/{session_id}', payload, show_error=show_error)

    def api_create_drone(self, payload: Dict[str, Any], show_error: bool = True):
        return self.make_request('POST', '/drones', payload, show_error=show_error)

    def api_send_drone_command(self, drone_id: str, command_data: Dict[str, Any]):
        return self.make_request('POST', f'/drones/{drone_id}/command', command_data)

    def api_create_target(self, payload: Dict[str, Any], show_error: bool = True):
        return self.make_request('POST', '/targets', payload, show_error=show_error)

    def api_create_environment(self, payload: Dict[str, Any], show_error: bool = True):
        return self.make_request('POST', '/environments', payload, show_error=show_error)

    def api_set_environment_current(self, env_id: str, show_error: bool = True):
        return self.make_request('POST', f'/environments/{env_id}/set-current', show_error=show_error)
    
    # Alias for api_set_environment_current
    def api_set_environment_as_current(self, env_id: str, show_error: bool = True):
        return self.api_set_environment_current(env_id, show_error=show_error)

    def api_create_task(self, session_id: str, payload: Dict[str, Any]):
        return self.make_request('POST', f'/sessions/{session_id}/tasks', payload)

    def api_mark_task_pending(self, session_id: str, task_id: str):
        return self.make_request('POST', f'/sessions/{session_id}/tasks/{task_id}/mark-pending')

    def api_mark_task_done(self, session_id: str, task_id: str):
        return self.make_request('POST', f'/sessions/{session_id}/tasks/{task_id}/mark-done')

    def api_swap_tasks(self, session_id: str, swap_data: Dict[str, Any]):
        return self.make_request('POST', f'/sessions/{session_id}/tasks/swap', swap_data)

    def api_check_execution(self, endpoint: str, parameters: Dict[str, Any], show_error: bool = False):
        """
        Call a /check/* endpoint to validate execution status.

        Args:
            endpoint: The check endpoint path (e.g., '/check/drone_position')
            parameters: Query parameters for the check (e.g., {'drone_id': 'drone-1', 'x': 10, 'y': 20})
            show_error: Whether to show error dialogs on failure (default: False for silent checks)

        Returns:
            Response dict with 'result' field (boolean) and other check-specific data, or None on failure
        """
        return self.make_request('GET', endpoint, params=parameters, show_error=show_error)

    def api_create_obstacle(self, payload: Dict[str, Any], show_error: bool = True):
        return self.make_request('POST', '/obstacles', payload, show_error=show_error)

    def api_check_path_collision(self, start: Dict[str, float], end: Dict[str, float], safety_margin: float = 0.0, show_error: bool = True):
        """
        Check if a flight path collides with any obstacles.
        """
        payload = {
            "start": start,
            "end": end,
            "safety_margin": safety_margin
        }
        return self.make_request('POST', '/obstacles/path_collision', payload, show_error=show_error)

    def api_check_point_collision(self, x: float, y: float, z: Optional[float] = None, margin: float = 0.0, show_error: bool = True):
        """
        Check if a point collides with any obstacles.
        """
        payload = {
            "x": x,
            "y": y,
            "margin": margin
        }
        if z is not None:
            payload["z"] = z
            
        return self.make_request('POST', '/obstacles/point_collision', payload, show_error=show_error)

    def api_charge_drone(self, drone_id: str):
        return self.make_request('POST', f'/drones/{drone_id}/command/charge?charge_amount=100.0')

    def api_return_drone_home(self, drone_id: str):
        return self.make_request('POST', f'/drones/{drone_id}/command/return_home')
        
    def api_update_session(self, session_id: str, update_data: Dict[str, Any], show_error: bool = True):
        return self.make_request('PUT', f'/sessions/{session_id}', update_data, show_error=show_error)
        
    def api_update_session_status(self, session_id: str, status: str, show_error: bool = True):
        return self.make_request('PUT', f'/sessions/{session_id}', {'status': status}, show_error=show_error)

    def api_update_drone(self, drone_id: str, payload: Dict[str, Any]):
        return self.make_request('PUT', f'/drones/{drone_id}', payload)

    def api_update_target(self, target_id: str, payload: Dict[str, Any]):
        return self.make_request('PUT', f'/targets/{target_id}', payload)

    def api_update_environment(self, env_id: str, payload: Dict[str, Any]):
        return self.make_request('PUT', f'/environments/{env_id}', payload)

    def api_update_task(self, session_id: str, task_id: str, payload: Dict[str, Any]):
        return self.make_request('PUT', f'/sessions/{session_id}/tasks/{task_id}', payload)

    def api_update_obstacle(self, obstacle_id: str, payload: Dict[str, Any]):
        return self.make_request('PUT', f'/obstacles/{obstacle_id}', payload)

    def api_reset_session(self):
        """Reset the current session to a clean state."""
        return self.make_request('POST', '/sessions/current/reset')

    def api_health_check(self):
        """Check API server health."""
        return self.make_request('GET', '/health')

    def _extract_server_version(self, response: Any) -> Optional[str]:
        """Extract a version string from a server response if present."""
        if not isinstance(response, dict):
            return None
        for key in ("version", "api_version", "server_version"):
            if response.get(key):
                return str(response.get(key))
        info = response.get("info")
        if isinstance(info, dict):
            for key in ("version", "api_version", "server_version"):
                if info.get(key):
                    return str(info.get(key))
        return None

    def api_get_server_version(self, show_error: bool = False) -> Optional[str]:
        """Get the server version string if the server reports one."""
        for endpoint in ("/version", "/"):
            response = self.make_request('GET', endpoint, show_error=show_error)
            version = self._extract_server_version(response)
            if version:
                return version
        return None

    def api_add_task_current(self, payload: Dict[str, Any]):
        """Create a task in the current session."""
        # This requires the caller to know the current session ID, or we fetch it.
        # But fetching it here creates a dependency on knowing which one is current.
        # Best to rely on the caller or fetch it if needed.
        # Since this is a convenience method, let's fetch it if possible.
        current_session = self.api_get_current_session(show_error=False)
        if current_session and 'id' in current_session:
            return self.api_create_task(current_session['id'], payload)
        return None

    def api_delete_session(self, session_id: str, show_error: bool = True):
        return self.make_request('DELETE', f'/sessions/{session_id}', show_error=show_error)

    def api_delete_drone(self, drone_id: str):
        return self.make_request('DELETE', f'/drones/{drone_id}')

    def api_land_all_drones(self, show_error: bool = True):
        """Land all drones immediately (SYSTEM+ permission required)"""
        return self.make_request('POST', '/drones/land_all', show_error=show_error)

    def api_charge_all_drones(self, show_error: bool = True):
        """Fully charge all drones immediately (SYSTEM+ permission required)"""
        return self.make_request('POST', '/drones/charge_all', show_error=show_error)

    def api_delete_target(self, target_id: str):
        return self.make_request('DELETE', f'/targets/{target_id}')

    def api_delete_environment(self, env_id: str):
        return self.make_request('DELETE', f'/environments/{env_id}')

    def api_delete_task(self, session_id: str, task_id: str):
        return self.make_request('DELETE', f'/sessions/{session_id}/tasks/{task_id}')

    def api_delete_obstacle(self, obstacle_id: str):
        return self.make_request('DELETE', f'/obstacles/{obstacle_id}')

    def api_get_list(self, endpoint: str, show_error: bool = False):
        """Generic wrapper for getting a list of items from an endpoint."""
        return self.make_request('GET', endpoint, show_error=show_error)

    def api_generic_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None, *, params: Optional[Dict[str, Any]] = None, expect_json: bool = True, show_error: bool = True):
        """Generic wrapper for making any request."""
        return self.make_request(method, endpoint, data, params=params, expect_json=expect_json, show_error=show_error)
