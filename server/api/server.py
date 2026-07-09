"""
MultiUAV-Plat Server System - FastAPI Server

Copyright (C) 2026 MultiUAV-Plat Server System Project

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from fastapi import FastAPI, HTTPException, Depends, status, Response, Header, Security, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from contextlib import asynccontextmanager
import time
import os
import json
import math
import inspect
import sys
import uuid
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware


from config.util import distance as euclidean_distance, distance_2d
from config.logging_config import (
    log_api_request,
    log_command_execution,
    get_logger,
    sanitize_sensitive_data,
)
from config.privilege_keys import (
    ADMIN_PRIVILEGE_KEYS,
    SYSTEM_PRIVILEGE_KEYS,
    USER_PRIVILEGE_KEYS,
)

# Import models and controllers
from models.drone import DroneStatus, DroneCommand
from controllers.drone_controller import DroneController
from models.target import TargetType
from controllers.target_controller import TargetController
from models.environment import WeatherCondition, WindDirection
from controllers.environment_controller import EnvironmentController
from models.obstacle import ObstacleType
from controllers.obstacle_controller import ObstacleController
from models.session import Session, SessionStatus
from controllers.session_controller import SessionController
from models.task import TaskDifficulty

# ==================== Authentication System ====================

class UserRole(str, Enum):
    """User roles for access control"""
    ADMIN = "admin"      # Full access to all endpoints
    SYSTEM = "system"    # Can manage drones, targets, obstacles, sessions (add, delete, change)
    AGENT = "agent"      # Same privileges as USER - can control drones (but cannot register new drones)
    USER = "user"        # Can control drones (but cannot register new drones)


# Secret keys for each role.
ROLE_SECRETS = {
    UserRole.USER: USER_PRIVILEGE_KEYS[0],
    UserRole.AGENT: os.getenv("AGENT_SECRET_KEY", "agent_secret_key_change_in_production"),
    UserRole.SYSTEM: SYSTEM_PRIVILEGE_KEYS[0],
    UserRole.ADMIN: ADMIN_PRIVILEGE_KEYS[0]
}

ROLE_SECRET_KEYS = {
    UserRole.USER: USER_PRIVILEGE_KEYS,
    UserRole.AGENT: (ROLE_SECRETS[UserRole.AGENT],),
    UserRole.SYSTEM: SYSTEM_PRIVILEGE_KEYS,
    UserRole.ADMIN: ADMIN_PRIVILEGE_KEYS,
}

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def resolve_api_key(api_key: Optional[str]) -> Tuple[Optional[UserRole], str]:
    """Resolve an API key without raising or exposing the credential."""
    if not api_key:
        return UserRole.AGENT, "default_agent"

    for role, secrets in ROLE_SECRET_KEYS.items():
        if api_key in secrets:
            return role, "api_key"

    return None, "invalid"


def get_current_user_role(api_key: str = Security(api_key_header)) -> UserRole:
    """Validate API key and return user role

    If no API key is provided, defaults to AGENT role with basic permissions.
    If an API key is provided but invalid, raises 401 Unauthorized.

    Args:
        api_key: The API key from the X-API-Key header (optional)

    Returns:
        UserRole: The validated user role (defaults to AGENT if no key provided)

    Raises:
        HTTPException: If API key is provided but invalid
    """
    role, _authentication_status = resolve_api_key(api_key)
    if role is not None:
        return role

    # API key provided but invalid
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key. Use USER role by omitting the key, or provide a valid key for AGENT, SYSTEM or ADMIN roles."
    )


def require_role(*allowed_roles: UserRole):
    """Dependency factory to require specific roles with hierarchy support

    Role Hierarchy:
    - ADMIN: Full access to all endpoints
    - SYSTEM: Can access SYSTEM, USER and AGENT endpoints
    - USER: Can access USER and AGENT endpoints
    - AGENT: Can only access AGENT endpoints

    Args:
        *allowed_roles: Roles that are allowed to access the endpoint

    Returns:
        A dependency function that checks if the user has one of the allowed roles
    """
    def role_checker(request: Request, current_role: UserRole = Depends(get_current_user_role)) -> UserRole:
        # Store role in request state for logging middleware
        request.state.user_role = current_role.value

        # ADMIN has access to everything
        if current_role == UserRole.ADMIN:
            return current_role

        # SYSTEM has access to SYSTEM, USER and AGENT endpoints
        if current_role == UserRole.SYSTEM:
             if UserRole.SYSTEM in allowed_roles: return current_role
             if UserRole.USER in allowed_roles: return current_role
             if UserRole.AGENT in allowed_roles: return current_role

        # USER has access to USER and AGENT endpoints
        if current_role == UserRole.USER:
             if UserRole.USER in allowed_roles: return current_role
             if UserRole.AGENT in allowed_roles: return current_role

        # AGENT has access to AGENT endpoints only
        if current_role == UserRole.AGENT:
             if UserRole.AGENT in allowed_roles: return current_role

        # Check if current role is exactly in allowed roles (fallback)
        if current_role in allowed_roles:
            return current_role

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required role: {', '.join([r.value for r in allowed_roles])}. Your role: {current_role.value}"
        )
        return current_role

    return role_checker


# Convenience role dependencies
require_admin = require_role(UserRole.ADMIN)
require_system = require_role(UserRole.SYSTEM)
require_agent = require_role(UserRole.AGENT)
require_user = require_role(UserRole.USER)


def require_current_request_history_role(
    request: Request,
    current_role: UserRole = Depends(get_current_user_role),
) -> UserRole:
    """Allow current-session request history for AGENT/SYSTEM/ADMIN only."""
    request.state.user_role = current_role.value
    if current_role in (UserRole.AGENT, UserRole.SYSTEM, UserRole.ADMIN):
        return current_role
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Access denied. Required role: agent, system, admin. Your role: {current_role.value}"
    )

# ==================== End Authentication System ====================

# ==================== Logging Middleware ====================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests and responses"""

    # Methods that typically include request bodies
    BODY_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    # Paths to exclude from detailed logging (health checks, etc.)
    EXCLUDE_PATHS = {"/"}

    AGENT_ID_HEADER = "X-Agent-ID"
    DEFAULT_AGENT_ID = "default_agent"
    MAX_AGENT_ID_LENGTH = 128

    @staticmethod
    def _query_value_is_true(value: Any) -> bool:
        """Return True when a query value represents an enabled flag."""
        if isinstance(value, list):
            return any(RequestLoggingMiddleware._query_value_is_true(item) for item in value)
        return str(value).lower() in {"1", "true", "yes"}

    @staticmethod
    def is_session_data_path(path: str, query_params: Optional[Dict[str, Any]] = None) -> bool:
        """Return True for session-data endpoints that can produce large payloads."""
        if path == "/sessions/current/data":
            return True
        if path.startswith("/sessions/") and path.endswith("/data"):
            return True

        parts = path.strip("/").split("/")
        if len(parts) == 2 and parts[0] == "sessions":
            return RequestLoggingMiddleware._query_value_is_true(
                (query_params or {}).get("data")
            )
        return False

    @staticmethod
    def should_skip_body_logging(
        path: str,
        method: str = "",
        query_params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if we should skip response body capture for this path."""
        if "/screenshot" in path or path.endswith("/request-history"):
            return True
        return (
            method.upper() == "GET"
            and RequestLoggingMiddleware.is_session_data_path(path, query_params)
        )

    @staticmethod
    def response_body_type(content_type: Optional[str]) -> str:
        """Normalize a response Content-Type header for structured logs."""
        if not content_type:
            return "unknown"
        return content_type.split(";", 1)[0].strip().lower() or "unknown"

    @staticmethod
    def response_body_summary(
        path: str,
        method: str = "",
        query_params: Optional[Dict[str, Any]] = None,
        content_type: Optional[str] = None,
    ) -> str:
        """Return a short reason instead of logging full response bodies."""
        if path.endswith("/request-history"):
            return "request_history_omitted"
        if "/screenshot" in path:
            return "binary_omitted"
        if (
            method.upper() == "GET"
            and RequestLoggingMiddleware.is_session_data_path(path, query_params)
        ):
            return "session_data_omitted"
        if RequestLoggingMiddleware.response_body_type(content_type).startswith("image/"):
            return "binary_omitted"
        return "omitted"

    @staticmethod
    def parse_content_length(value: Optional[str]) -> Optional[int]:
        """Parse Content-Length for structured logs without forcing body capture."""
        if value is None:
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None

    @staticmethod
    def should_omit_history_response_body(path: str) -> bool:
        """Prevent request-history responses from recursively embedding history."""
        return path.endswith("/request-history")

    @staticmethod
    def should_skip_session_history(path: str, method: str = "") -> bool:
        """Keep session request history empty after reset or explicit clear."""
        if method.upper() == "GET" and path == "/sessions/current/data":
            return True
        if path.endswith("/reset") and path.startswith("/sessions/"):
            return True
        return method.upper() == "DELETE" and path.endswith("/request-history")

    @staticmethod
    def sanitize_session_history_body(value: Any) -> Any:
        """Redact sensitive values stored in runtime request history."""
        return sanitize_sensitive_data(value)

    @classmethod
    def normalize_agent_id(cls, value: Optional[str]) -> str:
        """Normalize the non-secret agent history attribution label."""
        if value is None:
            return cls.DEFAULT_AGENT_ID
        normalized = str(value).strip()[:cls.MAX_AGENT_ID_LENGTH]
        return normalized or cls.DEFAULT_AGENT_ID

    @staticmethod
    def normalize_query_params(request: Request) -> Dict[str, Any]:
        """Preserve query values and repeated keys in replayable form."""
        normalized: Dict[str, Any] = {}
        for key, value in request.query_params.multi_items():
            if key not in normalized:
                normalized[key] = value
            elif isinstance(normalized[key], list):
                normalized[key].append(value)
            else:
                normalized[key] = [normalized[key], value]
        return sanitize_sensitive_data(normalized)

    async def dispatch(self, request: Request, call_next):
        """Process request and log details"""
        # Record start time
        start_time = time.time()
        request_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        request_id = str(uuid.uuid4())

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        client_port = request.client.port if request.client else None

        # Resolve authentication context independently so rejected requests are
        # still attributable without storing or exposing the API key.
        resolved_role, authentication_status = resolve_api_key(
            request.headers.get("X-API-Key")
        )
        client_privilege = resolved_role.name if resolved_role else None
        agent_id = (
            self.normalize_agent_id(request.headers.get(self.AGENT_ID_HEADER))
            if resolved_role == UserRole.AGENT
            else None
        )
        user_agent_header = request.headers.get("User-Agent")
        user_agent = user_agent_header[:512] if user_agent_header else None

        # Get request path and method
        path = request.url.path
        method = request.method

        # Get full URL including query parameters
        full_url = str(request.url.path)
        query_params = self.normalize_query_params(request)
        if request.url.query:
            full_url = f"{full_url}?{request.url.query}"

        # Initialize variables
        request_body = None
        response_body = None
        response_size_bytes = None
        response_body_type = "unknown"
        response_body_summary = "omitted"
        status_code = 500
        user_role = None
        session_id = None
        error_message = None

        try:
            # Read request body for POST/PUT/DELETE requests
            if method in self.BODY_METHODS and path not in self.EXCLUDE_PATHS:
                try:
                    body_bytes = await request.body()
                    if body_bytes:
                        request_body = json.loads(body_bytes)
                except Exception as e:
                    # If body is not JSON or cannot be read, log the error
                    request_body = {"error": f"Could not parse request body: {str(e)}"}

            # Process request
            response = await call_next(request)
            status_code = response.status_code
            response_size_bytes = self.parse_content_length(
                response.headers.get("content-length")
            )
            response_body_type = self.response_body_type(
                response.headers.get("content-type")
            )
            response_body_summary = self.response_body_summary(
                path,
                method=method,
                query_params=query_params,
                content_type=response.headers.get("content-type"),
            )

            # Try to capture response body for non-streaming responses
            # Skip binary responses (images, PDFs, etc.) to avoid Content-Length issues
            skip_body = self.should_skip_body_logging(
                path,
                method=method,
                query_params=query_params,
            )

            if path not in self.EXCLUDE_PATHS and not skip_body:
                try:
                    # Read response body
                    response_body_bytes = b""
                    async for chunk in response.body_iterator:
                        response_body_bytes += chunk
                    if response_size_bytes is None:
                        response_size_bytes = len(response_body_bytes)

                    # Parse response body if it's JSON
                    if response_body_bytes:
                        try:
                            response_body = json.loads(response_body_bytes)
                        except json.JSONDecodeError:
                            # Not JSON, store as full string (NO TRUNCATION)
                            response_body = response_body_bytes.decode('utf-8', errors='ignore')

                    # Recreate response with the body we just read. Remove any existing
                    # Content-Length header so Starlette recalculates it for the new body.
                    response_headers = dict(response.headers)
                    headers_to_remove = [
                        key for key in response_headers.keys()
                        if key.lower() == "content-length"
                    ]
                    for key in headers_to_remove:
                        response_headers.pop(key, None)
                    response = Response(
                        content=response_body_bytes,
                        status_code=status_code,
                        headers=response_headers,
                        media_type=response.media_type,
                        background=getattr(response, "background", None)
                    )
                except Exception as e:
                    # If we can't read the body, just pass through the response
                    error_message = f"Could not capture response body: {str(e)}"

        except Exception as e:
            # Log the error
            error_message = str(e)
            status_code = 500
            # Re-raise to let FastAPI handle it
            raise

        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Try to extract user role from request state (set by authentication)
            if hasattr(request.state, "user_role"):
                user_role = request.state.user_role

            # Attribute the request to the session active after the response.
            session_controller_ref = globals().get("session_controller")
            if (
                session_controller_ref
                and session_controller_ref.current_session_id
            ):
                session_id = session_controller_ref.current_session_id

            if (
                session_id
                and not self.should_skip_session_history(path, method)
                and session_controller_ref
            ):
                if session_controller_ref.get_session_ref(session_id) is not None:
                    history_response_body = (
                        None
                        if self.should_omit_history_response_body(path)
                        else response_body
                    )
                    session_controller_ref.add_request_to_history(
                        session_id,
                        {
                            "request_id": request_id,
                            "timestamp": request_timestamp,
                            "method": method,
                            "path": path,
                            "client_ip": client_ip,
                            "client_port": client_port,
                            "client_privilege": client_privilege,
                            "authentication_status": authentication_status,
                            "session_id": session_id,
                            "query_params": query_params,
                            "user_agent": user_agent,
                            "agent_id": agent_id,
                            "request_body": self.sanitize_session_history_body(request_body),
                            "status_code": status_code,
                            "success": status_code < 400,
                            "duration_sec": round(duration_ms / 1000, 6),
                            "response_body": self.sanitize_session_history_body(history_response_body),
                            "error": error_message,
                        },
                    )

            # Log the request (skip health check endpoint for cleaner logs)
            if path not in self.EXCLUDE_PATHS:
                log_api_request(
                    method=method,
                    path=path,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    client_ip=client_ip,
                    user_role=user_role,
                    request_body=request_body,
                    session_id=session_id,
                    error=error_message,
                    query_params=query_params or None,
                    response_size_bytes=response_size_bytes,
                    response_body_type=response_body_type,
                    response_body_summary=response_body_summary,
                )

                # Also log to access logger for human-readable format
                logger = get_logger("uav_system")
                role_str = f" - Role: {user_role}" if user_role else ""
                logger.info(
                    f"{client_ip} {method} {full_url} {status_code} - {duration_ms:.0f}ms{role_str}"
                )

        return response


# ==================== End Logging Middleware ====================

# Create FastAPI app
app = FastAPI(
    title="MultiUAV-Plat Server System API",
    description="RESTful API for controlling UAVs/drones",
    version="1.0.0"
)

# Add middlewares
# Note: Middlewares are executed in reverse order of addition
# So we add RequestLoggingMiddleware first to ensure it wraps everything

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize controllers
obstacle_controller = ObstacleController()
environment_controller = EnvironmentController()
target_controller = TargetController(obstacle_controller=obstacle_controller)
drone_controller = DroneController(
    obstacle_controller=obstacle_controller,
    environment_controller=environment_controller,
    target_controller=target_controller
)
session_controller = SessionController(
    drone_controller=drone_controller,
    target_controller=target_controller,
    obstacle_controller=obstacle_controller,
    environment_controller=environment_controller
)
# Set session controller reference in drone controller for command tracking
drone_controller.set_session_controller(session_controller)

# Helper to execute a command and record session statistics for state-changing outcomes
STATE_CHANGING_COMMAND_STATUSES = {"success", "partial_success"}

def _execute_command_and_record(drone_id: str, command: DroneCommand, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a drone command and update session statistics when it changes state.

    Records:
    - total_commands_executed
    - total_distance_traveled (based on position delta)
    - total_flight_time (distance divided by speed/max_speed)
    - target reach statistics (syncs new target visits from the drone)
    """
    # Snapshot pre-command state
    pre_drone = drone_controller.get_drone(drone_id)
    pre_position = pre_drone.get("position") if pre_drone else None

    # Execute command
    result = drone_controller.send_command(
        drone_id=drone_id,
        command=command,
        parameters=parameters
    )

    # Log command execution
    current_session_id = session_controller.current_session_id if session_controller else None
    log_command_execution(
        drone_id=drone_id,
        command=command.value if hasattr(command, 'value') else str(command),
        parameters=parameters,
        result=result.get("status", "unknown").upper(),
        session_id=current_session_id,
        error=result.get("message") if result.get("status") not in STATE_CHANGING_COMMAND_STATUSES else None
    )

    # Record command and movement metrics for full or partial state-changing outcomes.
    if result.get("status") in STATE_CHANGING_COMMAND_STATUSES:
        session_controller.record_command_execution()

        # Fetch post-command drone state
        post_drone = drone_controller.get_drone(drone_id)
        post_position = post_drone.get("position") if post_drone else None

        # Compute distance traveled from position delta
        distance = 0.0
        if pre_position and post_position:
            distance = _get_session_distance(post_position, pre_position)

        if distance > 0.0:
            session_controller.record_distance_traveled(distance)

            # Estimate flight time using speed or max_speed
            speed_candidates = [
                post_drone.get("speed") if post_drone else None,
                pre_drone.get("speed") if pre_drone else None,
                post_drone.get("max_speed") if post_drone else None,
                pre_drone.get("max_speed") if pre_drone else None
            ]
            # Choose first positive speed candidate; default to max_speed or 1.0
            speed = next((s for s in speed_candidates if isinstance(s, (int, float)) and s and s > 0), 0.0)
            if not speed:
                speed = (post_drone.get("max_speed") if post_drone else None) or (pre_drone.get("max_speed") if pre_drone else None) or 1.0
            flight_time = distance / float(speed) if speed > 0 else 0.0
            if flight_time > 0.0:
                session_controller.record_flight_time(flight_time)

    return result


def _get_task_progress_response(session_id: str) -> Dict[str, Any]:
    """Return task progress information for a session id."""
    if session_id in session_controller.sessions:
        session_obj = session_controller.sessions[session_id]
        return session_obj.get_task_progress()

    return {
        "task_type": "unknown",
        "progress_percentage": 0,
        "is_completed": False,
        "status_message": "Session not found",
        "details": {}
    }


def _mask_task_for_role(task: Dict[str, Any], role: UserRole) -> Dict[str, Any]:
    """Hide sensitive task fields for USER and AGENT roles."""
    if role in (UserRole.USER, UserRole.AGENT):
        masked = task.copy()
        masked["related_apis"] = []
        masked["commands"] = []
        masked["execution_check_apis"] = None
        return masked
    return task


def _mask_session_for_role(session_data: Dict[str, Any], role: UserRole, data: bool = True) -> Dict[str, Any]:
    """Hide sensitive session fields for USER and AGENT roles.

    For USER/AGENT roles:
    - Always removes history field
    - Masks tasks if present in the data (clears related_apis, commands, execution_check_apis)

    For SYSTEM/ADMIN roles:
    - No masking applied, returns data as-is

    Args:
        session_data: Session dictionary to mask
        role: User role making the request
        data: Whether this is full data (True) or metadata only (False)
    """
    if role in (UserRole.USER, UserRole.AGENT):
        # Always remove history for USER/AGENT roles
        session_data.pop("history", None)

        # Mask tasks if present in the session data
        if "tasks" in session_data and isinstance(session_data["tasks"], list):
            session_data["tasks"] = [_mask_task_for_role(task, role) for task in session_data["tasks"]]

    return session_data

# Startup sequence to create an initial session with examples
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create an initial session with examples when the server starts"""
    session_controller.add_session({
        "name": "Example Session",
        "description": "A comprehensive example session with drones, targets, obstacles, and environment setup for testing and demonstration purposes.",
        "with_examples": True,
        "task_type": "others",
        "task_description": "General purpose example session for testing and demonstration",
        "creator": "system"
    })
    yield


app.router.lifespan_context = lifespan

# API Models
# Drone Models
class DroneRegistrationRequest(BaseModel):
    name: str = Field(..., description="Name of the drone")
    model: str = Field(..., description="Model of the drone")
    max_speed: float = Field(..., description="Maximum speed in m/s")
    max_altitude: float = Field(..., description="Maximum altitude in meters")
    battery_capacity: float = Field(..., description="Battery capacity in mAh")
    position: Optional[Dict[str, float]] = Field(None, description="Initial position with x, y, z coordinates")
    heading: float = Field(0.0, description="Initial heading in degrees")
    speed: float = Field(0.0, description="Initial speed in m/s")
    battery_level: float = Field(100.0, description="Initial battery level percentage")
    battery_volume: Optional[float] = Field(None, description="Initial battery volume in mAh (if provided, takes precedence over battery_level)")
    status: Optional[str] = Field(None, description="Initial status")
    home_position: Optional[Dict[str, float]] = Field(None, description="Home position with x, y, z coordinates (defaults to initial position if not specified)")
    perceived_radius: float = Field(100.0, description="Perception radius in meters (how far the drone can perceive objects)")
    task_radius: float = Field(10.0, description="Task radius in meters (how close the drone needs to be to accomplish tasks)")

class PositionData(BaseModel):
    """Position data for partial updates"""
    x: Optional[float] = Field(None, description="X coordinate in meters")
    y: Optional[float] = Field(None, description="Y coordinate in meters")
    z: Optional[float] = Field(None, description="Z coordinate (altitude) in meters")

class DroneUpdateRequest(BaseModel):
    """Request model for updating drone properties

    All fields are optional - only provided fields will be updated.
    Validates constraints like positive values and altitude limits.
    """
    # Basic metadata
    name: Optional[str] = Field(None, description="Name of the drone")
    model: Optional[str] = Field(None, description="Model of the drone")

    # Performance specifications
    max_speed: Optional[float] = Field(None, gt=0, description="Maximum speed in m/s (must be positive)")
    max_altitude: Optional[float] = Field(None, gt=0, description="Maximum altitude in meters (must be positive)")
    battery_capacity: Optional[float] = Field(None, gt=0, description="Battery capacity in mAh (must be positive)")
    perceived_radius: Optional[float] = Field(None, gt=0, description="Perception radius in meters (must be positive)")
    task_radius: Optional[float] = Field(None, gt=0, description="Task radius in meters (must be positive)")

    # State attributes
    status: Optional[DroneStatus] = Field(None, description="Current status of the drone")
    position: Optional[PositionData] = Field(None, description="Current position (x, y, z) - partial coordinates supported")
    heading: Optional[float] = Field(None, ge=0, lt=360, description="Heading in degrees (0-359)")
    speed: Optional[float] = Field(None, ge=0, description="Current speed in m/s (must be non-negative)")

    # Battery state
    battery_level: Optional[float] = Field(None, ge=0, le=100, description="Battery level percentage (0-100)")
    battery_volume: Optional[float] = Field(None, ge=0, description="Battery volume in mAh (must be non-negative)")

    # Home position
    home_position: Optional[PositionData] = Field(None, description="Home position (x, y, z) - partial coordinates supported")

class PositionUpdateRequest(BaseModel):
    x: float = Field(..., description="X coordinate in meters")
    y: float = Field(..., description="Y coordinate in meters")
    z: float = Field(..., description="Z coordinate (altitude) in meters")

class DroneResponse(BaseModel):
    id: str
    name: str
    model: str
    status: DroneStatus
    position: Dict[str, float]
    heading: float
    speed: float
    battery_level: float
    max_speed: float
    max_altitude: float
    battery_capacity: float
    perceived_radius: float
    task_radius: float
    home_position: Dict[str, float]
    created_at: float
    last_updated: float

class CommandRequest(BaseModel):
    command: DroneCommand
    parameters: Dict[str, Any] = Field(default_factory=dict)

class MoveAlongPathRequest(BaseModel):
    waypoints: List[Dict[str, float]] = Field(
        ...,
        description="Ordered list of one or more waypoint coordinates with x, y, and optional z values. If z is omitted, the drone's current altitude is used.",
    )
    allow_partial_move: bool = Field(
        False,
        description="When true, move through consecutive safe waypoints and stop at the last reachable waypoint before an obstacle or insufficient battery blocks the remaining path",
    )

class CommandResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    command_id: str
    drone_id: str
    command: DroneCommand
    status: str
    message: str


class MoveAlongPathCommandResponse(CommandResponse):
    successful_points_count: Optional[int] = None
    successful_points: Optional[List[Tuple[float, float, float]]] = None
    unsuccessful_points_count: Optional[int] = None
    unsuccessful_points: Optional[List[Tuple[float, float, float]]] = None

# Target Models
class TargetRequest(BaseModel):
    name: str = Field(..., description="Name of the target")
    type: TargetType = Field(..., description="Type of target (fixed, moving, waypoint, circle, polygon) - fixed can represent points of interest")
    position: Dict[str, float] = Field(..., description="Position coordinates {x, y, z}")
    description: str = Field("", description="Description of the target")
    velocity: Optional[Dict[str, float]] = Field(None, description="Velocity for moving targets {x, y, z}. PRIORITY 1: If non-zero, uses velocity-based movement (ignores moving_path)")
    radius: float = Field(1.0, description="Target radius/size in meters")
    moving_path: Optional[List[Dict[str, float]]] = Field(None, description="Path waypoints for moving targets. PRIORITY 2: Used only if velocity is zero/null")
    moving_duration: Optional[float] = Field(10.0, description="Time in seconds: For velocity mode, time before reversing direction. For path mode, time to complete one-way traverse (speed auto-calculated). If 0, target is stationary")
    charge_amount: Optional[float] = Field(None, description="Instant charge amount for waypoint targets (battery percentage)")
    vertices: Optional[List[Dict[str, float]]] = Field(None, description="Polygon vertices (for polygon targets), absolute world coordinates")

class TargetResponse(BaseModel):
    id: str
    name: str
    type: TargetType
    position: Dict[str, float]
    description: str
    velocity: Optional[Dict[str, float]] = None
    radius: float
    created_at: float
    last_updated: float
    moving_path: Optional[List[Dict[str, float]]] = None
    moving_duration: Optional[float] = None
    current_path_index: Optional[int] = None
    path_direction: Optional[int] = None
    time_in_direction: Optional[float] = None
    calculated_speed: Optional[float] = None
    movement_mode: Optional[str] = None
    last_motion_update: Optional[float] = None
    charge_amount: Optional[float] = None
    vertices: Optional[List[Dict[str, float]]] = None
    tracking_status: Optional[str] = None
    last_tracked_at: Optional[float] = None
    is_reached: Optional[bool] = None
    reached_by: Optional[List[str]] = None

    class Config:
        # Include None values in the response
        exclude_none = False
        # Allow arbitrary types
        arbitrary_types_allowed = True

class TargetUpdateRequest(BaseModel):
    name: Optional[str] = None
    position: Optional[Dict[str, float]] = None
    description: Optional[str] = None
    velocity: Optional[Dict[str, float]] = None
    radius: Optional[float] = None
    moving_path: Optional[List[Dict[str, float]]] = None
    moving_duration: Optional[float] = None
    charge_amount: Optional[float] = None
    vertices: Optional[List[Dict[str, float]]] = None

# Environment Models
class EnvironmentRequest(BaseModel):
    name: str = Field(..., description="Name of the environment")
    weather: WeatherCondition = Field(..., description="Weather condition")
    temperature: float = Field(..., description="Temperature in Celsius")
    humidity: float = Field(..., description="Humidity percentage")
    pressure: float = Field(1013.25, description="Atmospheric pressure in hPa")
    wind_speed: float = Field(0.0, description="Wind speed in m/s")
    wind_direction: WindDirection = Field(WindDirection.NORTH, description="Wind direction")
    visibility: float = Field(10000.0, description="Visibility in meters")

class EnvironmentResponse(BaseModel):
    id: str
    name: str
    weather: WeatherCondition
    temperature: float
    humidity: float
    pressure: float
    wind_speed: float
    wind_direction: WindDirection
    visibility: float
    created_at: float
    last_updated: float

class EnvironmentUpdateRequest(BaseModel):
    name: Optional[str] = None
    weather: Optional[WeatherCondition] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[WindDirection] = None
    visibility: Optional[float] = None

# Obstacle Models
class ObstacleRequest(BaseModel):
    name: str = Field(..., description="Name of the obstacle")
    type: ObstacleType = Field(..., description="Type of obstacle (point, circle, ellipse, polygon)")
    position: Optional[Dict[str, float]] = Field(None, description="Position coordinates {x, y, z}")
    description: str = Field("", description="Description of the obstacle")
    radius: Optional[float] = Field(None, description="Radius for point/circle obstacles (defaults to 1.0 for point)")
    vertices: Optional[List[Dict[str, float]]] = Field(None, description="Vertices for polygon obstacles (3+ vertices)")
    width: Optional[float] = Field(None, description="Semi-major axis for ellipse obstacles")
    length: Optional[float] = Field(None, description="Semi-minor axis for ellipse obstacles")
    height: float = Field(0, description="Height in meters; 0 = impassable at any altitude")

class ObstacleResponse(BaseModel):
    id: str
    name: str
    type: ObstacleType
    position: Dict[str, float]
    description: str
    radius: Optional[float]
    vertices: Optional[List[Dict[str, float]]]
    width: Optional[float]
    length: Optional[float]
    height: float
    area: float
    created_at: float
    last_updated: float

class ObstacleUpdateRequest(BaseModel):
    name: Optional[str] = None
    position: Optional[Dict[str, float]] = None
    description: Optional[str] = None
    radius: Optional[float] = None
    vertices: Optional[List[Dict[str, float]]] = None
    width: Optional[float] = None
    length: Optional[float] = None
    height: Optional[float] = None

class CollisionCheckRequest(BaseModel):
    point: Dict[str, float] = Field(..., description="Point to check {x, y, z}")
    safety_margin: float = Field(0.0, description="Safety margin in meters")

class PathCollisionCheckRequest(BaseModel):
    start: Dict[str, float] = Field(..., description="Start point {x, y, z}")
    end: Dict[str, float] = Field(..., description="End point {x, y, z}")
    safety_margin: float = Field(1.0, description="Safety margin in meters")

class CollisionResponse(BaseModel):
    obstacle_id: str
    obstacle_name: str
    type: ObstacleType
    collision_type: str
    distance: Optional[float] = None

class PointInObstaclesRequest(BaseModel):
    x: float = Field(..., description="X coordinate of the point")
    y: float = Field(..., description="Y coordinate of the point")
    z: Optional[float] = Field(None, description="Z coordinate (altitude) of the point")
    margin: float = Field(0.0, description="Margin in meters around obstacles")

class ObstacleInfo(BaseModel):
    id: str
    name: str
    type: ObstacleType
    height: float
    distance_to_boundary: float = Field(..., description="Distance from point to obstacle boundary (negative if inside)")

class PointInObstaclesResponse(BaseModel):
    result: bool = Field(..., description="True if point is inside or on boundary of any obstacle")
    inside_obstacle_ids: List[str] = Field(..., description="List of obstacle IDs containing the point")
    inside_obstacles: List[ObstacleInfo] = Field(..., description="Detailed info about obstacles containing the point")
    point: Dict[str, float] = Field(..., description="The point that was checked")
    margin: float = Field(..., description="Margin used for the check")
    message: str = Field(..., description="Human-readable message about the result")

class NearbyEntitiesResponse(BaseModel):
    drones: List[DroneResponse]
    targets: List[TargetResponse]
    obstacles: List[ObstacleResponse]

# Session Models
class SessionRequest(BaseModel):
    name: str = Field(..., description="Name of the session")
    description: str = Field("", description="Description of the session")
    status: Optional[str] = Field(None, description="Session status")
    with_examples: bool = Field(True, description="Whether to create example data")
    task_type: str = Field("others", description="Task type: 'area_search', 'area_assignment_and_patrol', 'target_assignment', 'target_tracking', or 'others'")
    task_description: str = Field("", description="Detailed description of the task/mission")
    creator: Optional[str] = Field(None, description="Name of the user creating the session")
    canvas_width: float = Field(1024.0, description="Width of the simulation canvas in meters")
    canvas_height: float = Field(768.0, description="Height of the simulation canvas in meters")

class SessionResponse(BaseModel):
    id: str
    name: str
    description: str
    status: SessionStatus
    creator: str
    task_type: str
    task_description: str
    is_distance_3d: bool = False
    canvas_width: float = 1024.0
    canvas_height: float = 768.0
    created_at: float
    last_updated: float
    statistics: Dict[str, Any]  # Now includes task_progress nested within

class SessionUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[SessionStatus] = None
    canvas_width: Optional[float] = None
    canvas_height: Optional[float] = None
    is_distance_3d: Optional[bool] = None

class SessionHistory(BaseModel):
    command_history: List[Dict[str, Any]] = Field(default_factory=list)
    status_history: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    path_history: Dict[str, List[Dict[str, float]]] = Field(default_factory=dict)
    area_coverage: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    target_reaches: Dict[str, Any] = Field(default_factory=dict)
    moving_target_tracking: Dict[str, Any] = Field(default_factory=dict)

class SessionDataResponse(SessionResponse):
    """Complete session data including all entities (nested history)"""
    drones: List[Dict[str, Any]] = Field(default_factory=list)
    targets: List[Dict[str, Any]] = Field(default_factory=list)
    obstacles: List[Dict[str, Any]] = Field(default_factory=list)
    environment: Optional[Dict[str, Any]] = None
    tasks: List[Dict[str, Any]] = Field(default_factory=list)
    history: SessionHistory = Field(default_factory=SessionHistory)

class SessionCreateRequest(BaseModel):
    """Flexible session creation/restoration request"""
    # Session metadata (required)
    name: str = Field(..., description="Name of the session")
    description: str = Field("", description="Description of the session")
    creator: Optional[str] = Field(None, description="Name of the user creating the session")

    # Session configuration (optional)
    status: Optional[str] = Field(None, description="Session status")
    with_examples: bool = Field(False, description="Whether to create example data")
    task_type: str = Field("others", description="Task type: 'area_search', 'area_assignment_and_patrol', 'target_assignment', 'target_tracking', or 'others'")
    task_description: str = Field("", description="Detailed description of the task/mission")
    is_distance_3d: bool = Field(False, description="Whether to use 3D distance for calculations")
    canvas_width: float = Field(1024.0, description="Width of the simulation canvas in meters")
    canvas_height: float = Field(768.0, description="Height of the simulation canvas in meters")
    created_at: Optional[float] = Field(None, description="Original creation timestamp (preserved when restoring from file)")
    last_updated: Optional[float] = Field(None, description="Last update timestamp (preserved when restoring from file)")

    # Entities to restore/create (optional)
    drones: List[Dict[str, Any]] = Field(default_factory=list, description="Drones to create")
    targets: List[Dict[str, Any]] = Field(default_factory=list, description="Targets to create")
    obstacles: List[Dict[str, Any]] = Field(default_factory=list, description="Obstacles to create")
    environment: Optional[Dict[str, Any]] = Field(None, description="Environment to create")
    tasks: List[Dict[str, Any]] = Field(default_factory=list, description="Tasks to create")
    
    # History data (optional)
    history: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session history data including command_history, status_history, etc.")

# Task Models
class RelatedAPIModel(BaseModel):
    """Model for a related API endpoint with parameters"""
    endpoint: str = Field(..., description="API endpoint path (e.g., '/drones/{id}/command/move_to')")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Dictionary of parameter names to their descriptions or example values")

class ExecutionCheckNode(BaseModel):
    """Logical check node describing /check endpoint validation."""
    model_config = ConfigDict(ser_json_exclude_none=True)

    endpoint: Optional[str] = Field(None, description="Check endpoint path (e.g., /check/drone_position). Omit for pure logical grouping.")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters to pass to the endpoint")
    expect: Optional[bool] = Field(default=None, description="Expected boolean result from the check endpoint (defaults to true if not specified)")
    logic: Optional[str] = Field(default=None, description="Logical operator for nested checks: and, or, not (defaults to 'and' if not specified)")
    checks: Optional[List["ExecutionCheckNode"]] = Field(default=None, description="Nested check nodes for logical composition")


ExecutionCheckNode.model_rebuild()


class TaskRequest(BaseModel):
    name: str = Field(..., description="Short name for the task")
    content: str = Field("", description="Detailed content/instructions for the task")
    content_aliases: List[str] = Field(default_factory=list, description="List of alternative names or aliases for the content")
    description: str = Field("", description="Brief description of what the task entails")
    creator: Optional[str] = Field(None, description="Name of the user creating the task")
    originated_from: Optional[str] = Field(None, description="Principal that originated the task (defaults to creator)")
    difficulty: TaskDifficulty = Field(TaskDifficulty.MEDIUM, description="Difficulty level: easy, medium, or hard")
    related_apis: List[RelatedAPIModel] = Field(default_factory=list, description="List of API endpoint objects with endpoint and parameters")
    execution_check_apis: Optional[ExecutionCheckNode] = Field(default=None, description="Structured /check validation tree (logic + checks)")
    commands: List[str] = Field(default_factory=list, description="List of drone commands needed to complete this task")

class TaskResponse(BaseModel):
    id: str
    name: str
    content: str
    content_aliases: List[str]
    description: str
    creator: str
    originated_from: str
    difficulty: TaskDifficulty
    related_apis: List[RelatedAPIModel]
    execution_check_apis: Optional[Dict[str, Any]] = None  # Keep as dict to preserve original structure
    commands: List[str]
    is_done: bool
    is_passed: bool
    created_at: float
    last_updated: float

class TaskUpdateRequest(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    content_aliases: Optional[List[str]] = None
    description: Optional[str] = None
    difficulty: Optional[TaskDifficulty] = None
    originated_from: Optional[str] = None
    related_apis: Optional[List[RelatedAPIModel]] = None
    execution_check_apis: Optional[ExecutionCheckNode] = None
    commands: Optional[List[str]] = None
    is_done: Optional[bool] = None

class TaskSwapRequest(BaseModel):
    task_id_1: str = Field(..., description="ID of the first task to swap")
    task_id_2: str = Field(..., description="ID of the second task to swap")

# API Routes
@app.get("/", tags=["Health"])
async def root():
    """
    Health check endpoint to verify the API server is running.

    **Required Privileges:**
    - None: No authentication required

    **Response Format:**
    - status: Always "online" when server is running
    - message: Descriptive message about the API

    **Examples:**
    - Use this for load balancer health checks or simple connectivity verification
    """
    return {"status": "online", "message": "MultiUAV-Plat Server System API is running"}

@app.get("/version", tags=["Health"])
async def get_version(_role: UserRole = Depends(require_agent)):
    """
    Get server version information.

    **Required Privileges:**
    - AGENT: Basic access
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Response Format:**
    - name: API server name
    - version: Version string (typically retrieved from main module's VERSION attribute)
    """
    version = app.version
    for module_name in ("__main__", "main"):
        module = sys.modules.get(module_name)
        if module and hasattr(module, "VERSION"):
            version = getattr(module, "VERSION")
            break
    return {
        "name": app.title,
        "version": version
    }

@app.get("/drones", response_model=List[DroneResponse], tags=["Drones"])
async def get_all_drones(current_role: UserRole = Depends(require_agent)):
    """
    Get a list of all registered drones.

    **Required Privileges:**
    - AGENT: Basic access
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Response Format:**
    - Array of DroneResponse objects containing drone details including ID, name, position, status, battery, etc.
    """
    return drone_controller.get_all_drones()

@app.post("/drones", response_model=DroneResponse, status_code=status.HTTP_201_CREATED, tags=["Drones"])
async def register_drone(drone: DroneRegistrationRequest, current_role: UserRole = Depends(require_system)):
    """
    Register a new drone in the system.

    **Required Privileges:**
    - SYSTEM: Can register new drones
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - name: Drone name (required)
    - model: Drone model (required)
    - max_speed: Maximum speed in m/s (required)
    - max_altitude: Maximum altitude in meters (required)
    - battery_capacity: Battery capacity in mAh (required)
    - position: Initial position {x, y, z} (optional)
    - heading: Initial heading in degrees (optional, default: 0.0)
    - speed: Initial speed in m/s (optional, default: 0.0)
    - battery_level: Initial battery level percentage (optional, default: 100.0)
    - battery_volume: Initial battery volume in mAh (optional)
    - status: Initial status (optional)
    - home_position: Home position {x, y, z} (optional, defaults to initial position)
    - perceived_radius: Perception radius in meters (optional, default: 100.0)
    - task_radius: Task radius in meters (optional, default: 10.0)

    **Response Format:**
    - DroneResponse object with the registered drone including its generated ID
    """
    # Convert Pydantic model to dict for controller
    drone_data = {
        "name": drone.name,
        "model": drone.model,
        "max_speed": drone.max_speed,
        "max_altitude": drone.max_altitude,
        "battery_capacity": drone.battery_capacity,
    }

    # Add optional fields only if provided
    if drone.position is not None:
        drone_data["position"] = drone.position
    if drone.perceived_radius is not None:
        drone_data["perceived_radius"] = drone.perceived_radius
    if drone.task_radius is not None:
        drone_data["task_radius"] = drone.task_radius
    if drone.heading is not None:
        drone_data["heading"] = drone.heading
    if drone.speed is not None:
        drone_data["speed"] = drone.speed
    if drone.battery_level is not None:
        drone_data["battery_level"] = drone.battery_level
    if drone.battery_volume is not None:
        drone_data["battery_volume"] = drone.battery_volume
    if drone.status is not None:
        drone_data["status"] = drone.status
    if drone.home_position is not None:
        drone_data["home_position"] = drone.home_position

    result = drone_controller.add_drone(drone_data)
    return result

@app.get("/drones/{drone_id}", response_model=DroneResponse, tags=["Drones"])
async def get_drone(drone_id: str, current_role: UserRole = Depends(require_agent)):
    """
    Get a specific drone by its ID.

    **Required Privileges:**
    - AGENT: Basic access
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: ID of the drone to retrieve (path parameter)

    **Response Format:**
    - DroneResponse object with complete drone details
    - 404 Not Found if drone doesn't exist
    """
    drone = drone_controller.get_drone(drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")
    return drone

@app.get("/drones/{drone_id}/nearby", response_model=NearbyEntitiesResponse, tags=["Drones"])
async def get_nearby_entities(drone_id: str, current_role: UserRole = Depends(require_agent)):
    """
    Get all nearby drones, targets, and obstacles around a specific drone.

    **Required Privileges:**
    - AGENT: Basic access
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: ID of the drone to search around (path parameter)

    **Response Format:**
    - drones: Array of nearby DroneResponse objects
    - targets: Array of nearby TargetResponse objects
    - obstacles: Array of nearby ObstacleResponse objects
    - 404 Not Found if drone doesn't exist

    **Notes:**
    - The search area is determined by the drone's `perceived_radius` property
    - The requesting drone itself is not included in the results
    """
    try:
        # Use controller methods which automatically use the drone's perceived_radius
        drones = drone_controller.get_other_drones(drone_id)
        targets = drone_controller.get_other_targets(drone_id)
        obstacles = drone_controller.get_other_obstacles(drone_id)

        return {"drones": drones, "targets": targets, "obstacles": obstacles}
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.get("/drones/{drone_id}/nearby/drones", response_model=List[DroneResponse], tags=["Drones"])
async def get_nearby_drones(drone_id: str, _role: UserRole = Depends(require_agent)):
    """
    Get only nearby drones around a specific drone.

    **Required Privileges:**
    - AGENT: Basic access
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: ID of the drone to search around (path parameter)

    **Response Format:**
    - Array of nearby DroneResponse objects
    - 404 Not Found if drone doesn't exist

    **Notes:**
    - The search area is determined by the drone's `perceived_radius` property
    - The requesting drone itself is not included in the results
    """
    try:
        drones = drone_controller.get_other_drones(drone_id)
        return drones
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.get("/drones/{drone_id}/nearby/targets", response_model=List[TargetResponse], tags=["Drones"])
async def get_nearby_targets(drone_id: str, _role: UserRole = Depends(require_agent)):
    """
    Get only nearby targets around a specific drone.

    **Required Privileges:**
    - AGENT: Basic access
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: ID of the drone to search around (path parameter)

    **Response Format:**
    - Array of nearby TargetResponse objects
    - 404 Not Found if drone doesn't exist

    **Notes:**
    - The search area is determined by the drone's `perceived_radius` property
    """
    try:
        targets = drone_controller.get_other_targets(drone_id)
        return targets
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.get("/drones/{drone_id}/nearby/obstacles", response_model=List[ObstacleResponse], tags=["Drones"])
async def get_nearby_obstacles(drone_id: str, _role: UserRole = Depends(require_agent)):
    """
    Get only nearby obstacles around a specific drone.

    **Required Privileges:**
    - AGENT: Basic access
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: ID of the drone to search around (path parameter)

    **Response Format:**
    - Array of nearby ObstacleResponse objects
    - 404 Not Found if drone doesn't exist

    **Notes:**
    - The search area is determined by the drone's `perceived_radius` property
    """
    try:
        obstacles = drone_controller.get_other_obstacles(drone_id)
        return obstacles
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.put("/drones/{drone_id}", response_model=DroneResponse, tags=["Drones"])
async def update_drone(drone_id: str, drone_update: DroneUpdateRequest, _role: UserRole = Depends(require_system)):
    """
    Update a drone's properties.

    **Required Privileges:**
    - SYSTEM: Can modify drone properties
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - drone_id: ID of the drone to update (path parameter)
    - name: Drone name (optional)
    - model: Drone model (optional)
    - max_speed: Maximum speed in m/s (optional, must be > 0)
    - max_altitude: Maximum altitude in meters (optional, must be > 0)
    - battery_capacity: Battery capacity in mAh (optional, must be > 0)
    - perceived_radius: Perception radius in meters (optional, must be > 0)
    - task_radius: Task radius in meters (optional, must be > 0)
    - status: Drone status (optional)
    - position: Position {x, y, z} (optional, supports partial updates)
    - heading: Heading in degrees (optional, 0-359)
    - speed: Speed in m/s (optional, >= 0)
    - battery_level: Battery level percentage (optional, 0-100)
    - battery_volume: Battery volume in mAh (optional, >= 0)
    - home_position: Home position {x, y, z} (optional, supports partial updates)

    **Response Format:**
    - Updated DroneResponse object
    - 400 Bad Request if validation fails
    - 404 Not Found if drone doesn't exist

    **Notes:**
    - All fields are optional - only provided fields will be updated
    - Position and home_position support partial updates (e.g., only updating z coordinate)
    - You can also use PUT /drones/{drone_id}/position for position-only updates
    """
    # Convert Pydantic model to dict, excluding None values
    updates = drone_update.model_dump(exclude_none=True)

    # Convert nested PositionData models to dicts if present
    if "position" in updates and updates["position"] is not None:
        updates["position"] = updates["position"]  # Already converted by model_dump
    if "home_position" in updates and updates["home_position"] is not None:
        updates["home_position"] = updates["home_position"]  # Already converted by model_dump

    if not updates:
        raise HTTPException(status_code=400, detail="No valid updates provided")

    try:
        updated_drone = drone_controller.update_drone(drone_id, updates)
        if not updated_drone:
            raise HTTPException(status_code=404, detail="Drone not found")
        return updated_drone
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/drones/{drone_id}/position", response_model=DroneResponse, tags=["Drones"])
async def update_drone_position(drone_id: str, position_update: PositionUpdateRequest, _role: UserRole = Depends(require_system)):
    """
    Directly set a drone's position (administrative function).

    **Required Privileges:**
    - SYSTEM: Can directly modify drone positions
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - drone_id: ID of the drone to update (path parameter)
    - x: Target X coordinate in meters
    - y: Target Y coordinate in meters
    - z: Target Z coordinate (altitude) in meters

    **Response Format:**
    - Updated DroneResponse object with new position
    - 400 Bad Request if new position has obstacle collision or validation fails
    - 404 Not Found if drone doesn't exist

    **Behavior:**
    - This bypasses normal movement logic and teleports the drone
    - Drone status automatically updates based on altitude:
      * If z > 0 and drone is IDLE/READY: status changes to HOVERING
      * If z == 0 and drone is HOVERING/FLYING/MOVING: status changes to IDLE
    - Performs obstacle collision checks at the new position before updating
    """
    try:
        updated_drone = drone_controller.update_drone_position(
            drone_id,
            position_update.x,
            position_update.y,
            position_update.z
        )
        if not updated_drone:
            raise HTTPException(status_code=404, detail="Drone not found")
        return updated_drone
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/drones/{drone_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Drones"])
async def delete_drone(drone_id: str, _role: UserRole = Depends(require_system)):
    """
    Remove a drone from the system.

    **Required Privileges:**
    - SYSTEM: Can delete drones
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - drone_id: ID of the drone to delete (path parameter)

    **Response Format:**
    - 204 No Content on successful deletion
    - 404 Not Found if drone doesn't exist

    **Notes:**
    - This action cannot be undone
    - Session history for this drone remains in session records
    """
    success = drone_controller.delete_drone(drone_id)
    if not success:
        raise HTTPException(status_code=404, detail="Drone not found")
    return None

@app.post("/drones/{drone_id}/command", response_model=CommandResponse, tags=["Drone Commands"])
async def send_command(drone_id: str, command_request: CommandRequest, _role: UserRole = Depends(require_agent)):
    """
    Send a generic command to a drone using the command enum.

    **Required Privileges:**
    - AGENT: Can send basic commands
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: Target drone ID (path parameter)
    - command: Command from DroneCommand enum (body parameter)
    - parameters: Dictionary of command-specific parameters (body parameter)

    **Response Format:**
    - CommandResponse with command_id, status, and execution details
    - 400 Bad Request if command or parameters are invalid
    - 404 Not Found if drone doesn't exist

    **Notes:**
    - Session statistics are automatically updated for full or partial state-changing execution
    - Consider using the direct command endpoints (like /take_off, /move_to) for easier API usage
    """
    try:
        return _execute_command_and_record(
            drone_id=drone_id,
            command=command_request.command,
            parameters=command_request.parameters
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.get("/drones/{drone_id}/commands", response_model=List[CommandResponse], tags=["Drone Commands"])
async def get_drone_commands(drone_id: str, _role: UserRole = Depends(require_agent)):
    """
    Retrieve the command execution history for a specific drone.

    **Required Privileges:**
    - AGENT: Can view command history
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: Target drone ID (path parameter)

    **Response Format:**
    - Array of CommandResponse objects sorted by most recent first
    - 404 Not Found if drone doesn't exist
    """
    try:
        return drone_controller.get_drone_commands(drone_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.get("/commands/{command_id}", response_model=CommandResponse, tags=["Drone Commands"])
async def get_command_status(command_id: str, _role: UserRole = Depends(require_agent)):
    """
    Get the status and details of a specific command execution.

    **Required Privileges:**
    - AGENT: Can view command status
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - command_id: Command execution ID (path parameter)

    **Response Format:**
    - CommandResponse with complete execution details
    - 404 Not Found if command doesn't exist
    """
    command = drone_controller.get_command(command_id)
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    return command

# Alternative RESTful API endpoints for direct command execution
@app.post("/drones/{drone_id}/command/take_off", response_model=CommandResponse, tags=["Drone Commands"])
async def direct_take_off(drone_id: str, altitude: float = 10.0, _role: UserRole = Depends(require_agent)):
    """
    Command a drone to take off and hover at a specified altitude.

    **Required Privileges:**
    - AGENT: Can send takeoff commands
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: Target drone ID (path parameter)
    - altitude: Target hover altitude in meters (query parameter, default: 10.0)

    **Response Format:**
    - CommandResponse with execution status
    - 400 Bad Request if obstacles are in the way or altitude invalid
    - 404 Not Found if drone doesn't exist

    **Behavior:**
    - Drone status changes from IDLE/READY to TAKING_OFF then HOVERING
    - Performs obstacle checks before and during ascent
    """
    try:
        return _execute_command_and_record(
            drone_id=drone_id,
            command=DroneCommand.TAKE_OFF,
            parameters={"altitude": altitude}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.post("/drones/{drone_id}/command/land", response_model=CommandResponse, tags=["Drone Commands"])
async def direct_land(drone_id: str, _role: UserRole = Depends(require_agent)):
    """
    Command a drone to land at its current XY position.

    **Required Privileges:**
    - AGENT: Can send landing commands
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: Target drone ID (path parameter)

    **Response Format:**
    - CommandResponse with execution status
    - 400 Bad Request if landing position is blocked
    - 404 Not Found if drone doesn't exist

    **Behavior:**
    - Descends straight down (Z to 0) maintaining XY position
    - Status changes to LANDING then IDLE when on ground
    - Performs obstacle check at landing position first
    """
    try:
        return _execute_command_and_record(
            drone_id=drone_id,
            command=DroneCommand.LAND,
            parameters={}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.post("/drones/{drone_id}/command/move_to", response_model=CommandResponse, tags=["Drone Commands"])
async def direct_move_to(drone_id: str, x: float, y: float, z: Optional[float] = None, _role: UserRole = Depends(require_agent)):
    """
    Command a drone to move to an exact coordinate position.

    **Required Privileges:**
    - AGENT: Can send movement commands
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: Target drone ID (path parameter)
    - x: Target X coordinate in meters (query parameter)
    - y: Target Y coordinate in meters (query parameter)
    - z: Target Z coordinate (altitude) in meters (query parameter, optional)
      * If not provided, maintains current altitude

    **Response Format:**
    - CommandResponse with execution status
    - 400 Bad Request if path is blocked by obstacles
    - 404 Not Found if drone doesn't exist

    **Behavior:**
    - Calculates direct linear path to target
    - Performs obstacle collision checks along the path
    - Updates drone status to MOVING during transit
    """
    try:
        # Get current drone position if z is not provided
        if z is None:
            drone = drone_controller.get_drone(drone_id)
            if not drone:
                raise HTTPException(status_code=404, detail="Drone not found")
            z = drone["position"]["z"]

        return _execute_command_and_record(
            drone_id=drone_id,
            command=DroneCommand.MOVE_TO,
            parameters={"x": x, "y": y, "z": z}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.post("/drones/{drone_id}/command/move_towards", response_model=CommandResponse, tags=["Drone Commands"])
async def direct_move_towards(
    drone_id: str,
    distance: float,
    heading: Optional[float] = None,
    dx: Optional[float] = None,
    dy: Optional[float] = None,
    dz: Optional[float] = 0.0,
    azimuth: Optional[float] = None,
    elevation: Optional[float] = 0.0
, _role: UserRole = Depends(require_agent)):
    """
    Command a drone to move a specific distance in a given direction.

    **Required Privileges:**
    - AGENT: Can send movement commands
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: Target drone ID (path parameter)
    - distance: Distance to move in meters (required)

    **Direction Specification (ONE method required):**
    1. **Heading Method:**
       - heading: Compass bearing (0=North, 90=East, 180=South, 270=West)
       - dz: Optional altitude change in meters (default: 0.0)

    2. **Vector Method:**
       - dx, dy, dz: Direction vector components (meters)

    3. **Spherical Method:**
       - azimuth: Horizontal angle (0=North, clockwise)
       - elevation: Vertical angle (0=horizontal, positive=up)

    **Response Format:**
    - CommandResponse with execution status
    - 400 Bad Request if direction not specified or path blocked
    - 404 Not Found if drone doesn't exist
    """
    try:
        parameters = {"distance": distance}

        if heading is not None:
            parameters["heading"] = heading
            if dz != 0.0:
                parameters["dz"] = dz
        elif dx is not None and dy is not None:
            parameters["dx"] = dx
            parameters["dy"] = dy
            parameters["dz"] = dz
        elif azimuth is not None:
            parameters["azimuth"] = azimuth
            parameters["elevation"] = elevation
        else:
            raise ValueError("Direction must be specified using 'heading', 'dx/dy', or 'azimuth'")

        return _execute_command_and_record(
            drone_id=drone_id,
            command=DroneCommand.MOVE_TOWARDS,
            parameters=parameters
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.post("/drones/{drone_id}/command/move_along_path", response_model=MoveAlongPathCommandResponse, tags=["Drone Commands"])
async def direct_move_along_path(drone_id: str, path_request: MoveAlongPathRequest, _role: UserRole = Depends(require_agent)):
    """
    Move a drone along a multi-segment path defined by waypoints.

    **Required Privileges:**
    - AGENT: Can send movement commands
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: ID of the drone to command (path parameter)
    - waypoints: Array of {x, y, z} coordinates defining the path. z is optional and defaults to current altitude
    - allow_partial_move: Boolean flag enabling partial path execution if blocked

    **Response Format:**
    - CommandResponse object with command_id, drone_id, status, and message
    - status `success` means all requested waypoints were reached
    - status `partial_success` means at least one waypoint was reached but the final requested waypoint was not reached
    - move_along_path responses include successful_points_count, successful_points, unsuccessful_points_count, and unsuccessful_points
    - successful_points and unsuccessful_points are lists of normalized (x, y, z) coordinate triples
    - 400 Bad Request if path is invalid or movement blocked
    - 404 Not Found if drone doesn't exist

    **Partial Movement Behavior:**
    - When allow_partial_move = false (default):
      * If any segment is blocked by obstacles, entire command fails
      * Drone remains at starting position
    - When allow_partial_move = true:
      * Drone moves along consecutive safe waypoints until blocked
      * Stops at the last reachable waypoint before an obstacle or insufficient battery
      * Returns status `partial_success` with a partial completion message
      * Session history records the actual path traveled

    **Notes:**
    - Waypoints are visited in the exact order provided
    - Each segment is checked for obstacle collisions before moving
    - Movement consumes battery based on distance traveled
    - Session statistics are updated automatically for distance and flight time
    """
    try:
        return _execute_command_and_record(
            drone_id=drone_id,
            command=DroneCommand.MOVE_ALONG_PATH,
            parameters={
                "waypoints": path_request.waypoints,
                "allow_partial_move": path_request.allow_partial_move,
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.post("/drones/{drone_id}/command/change_altitude", response_model=CommandResponse, tags=["Drone Commands"])
async def direct_change_altitude(drone_id: str, altitude: float, _role: UserRole = Depends(require_agent)):
    """
    Command a drone to change its altitude while maintaining XY position.

    **Required Privileges:**
    - AGENT: Can send altitude change commands
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: Target drone ID (path parameter)
    - altitude: New target altitude in meters (query parameter)

    **Response Format:**
    - CommandResponse with execution status
    - 400 Bad Request if altitude out of bounds or obstacles in way
    - 404 Not Found if drone doesn't exist

    **Behavior:**
    - Moves only vertically (Z axis)
    - Drone must already be airborne (hovering/flying)
    - Maintains current position (X and Y unchanged)
    """
    try:
        return _execute_command_and_record(
            drone_id=drone_id,
            command=DroneCommand.CHANGE_ALTITUDE,
            parameters={"altitude": altitude}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.post("/drones/{drone_id}/command/hover", response_model=CommandResponse, tags=["Drone Commands"])
async def direct_hover(drone_id: str, duration: Optional[float] = None, _role: UserRole = Depends(require_agent)):
    """
    Command a drone to hover in place at its current position.

    **Required Privileges:**
    - AGENT: Can send hover commands
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: Target drone ID (path parameter)
    - duration: Optional hover duration in seconds (query parameter)

    **Response Format:**
    - CommandResponse with execution status
    - 400 Bad Request if drone is not airborne
    - 404 Not Found if drone doesn't exist

    **Behavior:**
    - Maintains current position and altitude
    - Changes status to HOVERING
    - If duration provided, will hover for specified time then continue
    """
    try:
        parameters = {}
        if duration is not None:
            parameters["duration"] = duration

        return _execute_command_and_record(
            drone_id=drone_id,
            command=DroneCommand.HOVER,
            parameters=parameters
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.post("/drones/{drone_id}/command/rotate", response_model=CommandResponse, tags=["Drone Commands"])
async def direct_rotate(drone_id: str, heading: float, _role: UserRole = Depends(require_agent)):
    """
    Command a drone to rotate to a specific heading without moving position.

    **Required Privileges:**
    - AGENT: Can send rotation commands
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: Target drone ID (path parameter)
    - heading: Target heading in degrees (query parameter)
      * 0 = North, 90 = East, 180 = South, 270 = West

    **Response Format:**
    - CommandResponse with execution status
    - 400 Bad Request if heading out of bounds (0-359)
    - 404 Not Found if drone doesn't exist
    """
    try:
        return _execute_command_and_record(
            drone_id=drone_id,
            command=DroneCommand.ROTATE,
            parameters={"heading": heading}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.post("/drones/{drone_id}/command/return_home", response_model=CommandResponse, tags=["Drone Commands"])
async def direct_return_home(drone_id: str, _role: UserRole = Depends(require_agent)):
    """
    Command a drone to return to its home position.

    **Required Privileges:**
    - AGENT: Can send return-to-home commands
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: Target drone ID (path parameter)

    **Response Format:**
    - CommandResponse with execution status
    - 400 Bad Request if path home is blocked
    - 404 Not Found if drone doesn't exist

    **Behavior:**
    - Returns to the home position (set via set_home command)
    - Maintains current altitude during transit
    - Can land after arrival (call land command separately if needed)
    """
    try:
        return _execute_command_and_record(
            drone_id=drone_id,
            command=DroneCommand.RETURN_HOME,
            parameters={}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.post("/drones/{drone_id}/command/set_home", response_model=CommandResponse, tags=["Drone Commands"])
async def direct_set_home(drone_id: str, _role: UserRole = Depends(require_agent)):
    """
    Set drone's current position as its new home position.

    **Required Privileges:**
    - AGENT: Can set home position
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: Target drone ID (path parameter)

    **Response Format:**
    - CommandResponse with execution status
    - 404 Not Found if drone doesn't exist

    **Notes:**
    - Home position is used by return_home command
    - Current position (X, Y, Z) is stored as the new home
    """
    try:
        return _execute_command_and_record(
            drone_id=drone_id,
            command=DroneCommand.SET_HOME,
            parameters={}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.post("/drones/{drone_id}/command/calibrate", response_model=CommandResponse, tags=["Drone Commands"])
async def direct_calibrate(drone_id: str, _role: UserRole = Depends(require_agent)):
    """
    Command a drone to calibrate its onboard sensors.

    **Required Privileges:**
    - AGENT: Can send calibration commands
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: Target drone ID (path parameter)

    **Response Format:**
    - CommandResponse with execution status
    - 404 Not Found if drone doesn't exist

    **Notes:**
    - Drone should be on the ground and stationary during calibration
    - Calibrates IMU, compass, and other onboard sensors
    """
    try:
        return _execute_command_and_record(
            drone_id=drone_id,
            command=DroneCommand.CALIBRATE,
            parameters={}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.post("/drones/{drone_id}/command/take_photo", response_model=CommandResponse, tags=["Drone Commands"])
async def direct_take_photo(drone_id: str, _role: UserRole = Depends(require_agent)):
    """
    Command a drone to take a photo with its camera.

    **Required Privileges:**
    - AGENT: Can trigger photo capture
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: Target drone ID (path parameter)

    **Response Format:**
    - CommandResponse with execution status and photo_id metadata
    - 404 Not Found if drone doesn't exist

    **Notes:**
    - Photo event is stored in drone's status history
    - Position and timestamp are recorded with the photo
    - Can be used with check_target_in_photo_taken_by_drone endpoint
    """
    try:
        return _execute_command_and_record(
            drone_id=drone_id,
            command=DroneCommand.TAKE_PHOTO,
            parameters={}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.post("/drones/{drone_id}/command/send_message", response_model=CommandResponse, tags=["Drone Commands"])
async def direct_send_message(drone_id: str, target_drone_id: str, message: str, _role: UserRole = Depends(require_agent)):
    """
    Send a direct message from one drone to another.

    **Required Privileges:**
    - AGENT: Can send inter-drone messages
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: Sender drone ID (path parameter)
    - target_drone_id: Recipient drone ID (query parameter)
    - message: Message content (query parameter)

    **Response Format:**
    - CommandResponse with execution status
    - 404 Not Found if sender or target drone doesn't exist
    """
    try:
        return _execute_command_and_record(
            drone_id=drone_id,
            command=DroneCommand.SEND_MESSAGE,
            parameters={"target_drone_id": target_drone_id, "message": message}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.post("/drones/{drone_id}/command/broadcast", response_model=CommandResponse, tags=["Drone Commands"])
async def direct_broadcast(drone_id: str, message: str, _role: UserRole = Depends(require_agent)):
    """
    Broadcast a message from one drone to all other drones.

    **Required Privileges:**
    - AGENT: Can send broadcast messages
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: Sender drone ID (path parameter)
    - message: Broadcast message content (query parameter)

    **Response Format:**
    - CommandResponse with execution status
    - 404 Not Found if sender drone doesn't exist
    """
    try:
        return _execute_command_and_record(
            drone_id=drone_id,
            command=DroneCommand.BROADCAST,
            parameters={"message": message}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")

@app.post("/drones/{drone_id}/command/charge", response_model=CommandResponse, tags=["Drone Commands"])
async def direct_charge(drone_id: str, charge_amount: float, _role: UserRole = Depends(require_agent)):
    """
    Command a drone to charge its battery (typically at a charging station).

    **Required Privileges:**
    - AGENT: Can send charge commands
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: Target drone ID (path parameter)
    - charge_amount: Percentage to charge (1.0 = 100%, 0.5 = 50%) (query parameter)

    **Response Format:**
    - CommandResponse with execution status
    - 400 Bad Request if charge_amount invalid (0-1)
    - 404 Not Found if drone doesn't exist

    **Notes:**
    - Drone should be positioned near a charging target/waypoint
    - Charging adds battery without changing position
    """
    try:
        return _execute_command_and_record(
            drone_id=drone_id,
            command=DroneCommand.CHARGE,
            parameters={"charge_amount": charge_amount}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")


class BatteryUpdateRequest(BaseModel):
    """Request model for updating drone battery level (testing purposes)"""
    battery_level: float = Field(..., ge=0.0, le=100.0, description="Battery level percentage (0-100)")


@app.post("/drones/{drone_id}/battery", tags=["Drones"])
async def update_battery_level(drone_id: str, request: BatteryUpdateRequest, _role: UserRole = Depends(require_agent)):
    """
    Directly set a drone's battery level (primarily for testing/debugging).

    **Required Privileges:**
    - AGENT: Can modify battery levels
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - drone_id: Target drone ID (path parameter)
    - battery_level: New battery level percentage (0-100) (body parameter)

    **Response Format:**
    - message: Confirmation message
    - drone_id: Updated drone ID
    - battery_level: New battery level
    - status: Current drone status
    - 404 Not Found if drone doesn't exist

    **Notes:**
    - This is an administrative override, not normal charging
    - No physical charging station required
    - Drone position and status remain unchanged
    - Session history records the battery change
    """
    try:
        drone = drone_controller.get_drone(drone_id)
        if not drone:
            raise HTTPException(status_code=404, detail="Drone not found")

        # Update battery level directly
        drone_obj = drone_controller.drones[drone_id]
        drone_obj.update_battery(request.battery_level)

        return {
            "message": f"Battery level updated to {request.battery_level}%",
            "drone_id": drone_id,
            "battery_level": drone_obj.battery_level,
            "status": drone_obj.status
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="Drone not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/drones/land_all", tags=["Drones"])
async def land_all_drones(_role: UserRole = Depends(require_system)):
    """
    Administrative command to immediately land all drones.

    **Required Privileges:**
    - SYSTEM: Can perform bulk administrative actions
    - ADMIN: Inherits access from role hierarchy

    **Response Format:**
    - message: Summary message
    - total_drones: Total number of drones processed
    - drones_landed: Count of drones successfully landed
    - drones_blocked: Count of drones that couldn't land due to obstacles
    - drones_already_grounded: Count of drones already on the ground
    - details: Array with individual drone results including:
      * drone_id, drone_name
      * previous_status, previous_altitude
      * new_status, new_altitude
      * action: "landed", "blocked", or "already_on_ground"
      * reason: Only present if action was blocked

    **Behavior:**
    - This is a management command that bypasses normal command queue
    - Teleports drones directly to ground altitude (z = 0)
    - No battery consumption occurs
    - Status changes to IDLE unless already in EMERGENCY status
    - Drones in EMERGENCY stay in EMERGENCY but still get altitude reset
    - Per-obstacle collision checks performed at landing position
    - Blocked drones remain at their current altitude
    - Session history records status changes for affected drones
    """
    results = []
    all_drones = drone_controller.get_all_drones()

    for drone_dict in all_drones:
        drone_id = drone_dict['id']
        drone = drone_controller.drones[drone_id]

        # Record previous state
        previous_status = drone.status.value if hasattr(drone.status, 'value') else str(drone.status)
        previous_altitude = drone.position.get('z', 0.0)

        blocked_reason = None
        if previous_altitude > 0:
            landing_position = {"x": drone.position["x"], "y": drone.position["y"], "z": 0.0}
            blocked_reason = drone_controller._check_position_collision(landing_position)

        if blocked_reason:
            results.append({
                "drone_id": drone_id,
                "drone_name": drone.name,
                "previous_status": previous_status,
                "previous_altitude": previous_altitude,
                "new_status": previous_status,
                "new_altitude": previous_altitude,
                "action": "blocked",
                "reason": f"Cannot land: {blocked_reason}"
            })
            continue

        # Land the drone: set altitude to 0
        drone.position['z'] = 0.0

        # Update status to IDLE if not in EMERGENCY
        if drone.status != DroneStatus.EMERGENCY:
            drone.status = DroneStatus.IDLE

        # Record the status change in session history
        current_session = session_controller.get_current_session()
        if current_session:
            session_id = current_session.get('id')
            if session_id and session_id in session_controller.sessions:
                session = session_controller.sessions[session_id]
                session.record_drone_status(
                    drone_id=drone.id,
                    status=drone.status.value if hasattr(drone.status, 'value') else str(drone.status),
                    position=drone.position.copy(),
                    battery_level=drone.battery_level,
                    battery_volume=drone.battery_volume
                )

        results.append({
            "drone_id": drone_id,
            "drone_name": drone.name,
            "previous_status": previous_status,
            "previous_altitude": previous_altitude,
            "new_status": drone.status.value if hasattr(drone.status, 'value') else str(drone.status),
            "new_altitude": 0.0,
            "action": "landed" if previous_altitude > 0 else "already_on_ground"
        })

    return {
        "message": f"Successfully landed {len(results)} drone(s)",
        "total_drones": len(results),
        "drones_landed": len([r for r in results if r["action"] == "landed"]),
        "drones_blocked": len([r for r in results if r["action"] == "blocked"]),
        "drones_already_grounded": len([r for r in results if r["action"] == "already_on_ground"]),
        "details": results
    }


@app.post("/drones/charge_all", tags=["Drones"])
async def charge_all_drones(_role: UserRole = Depends(require_system)):
    """
    Administrative command to fully charge all drone batteries.

    **Required Privileges:**
    - SYSTEM: Can perform bulk administrative actions
    - ADMIN: Inherits access from role hierarchy

    **Response Format:**
    - message: Summary message
    - total_drones: Total number of drones processed
    - drones_charged: Count of drones charged (from <100% to 100%)
    - drones_already_full: Count of drones already at 100% battery
    - details: Array with individual drone results including:
      * drone_id, drone_name
      * previous_battery_level, previous_battery_volume
      * new_battery_level, new_battery_volume
      * action: "charged" or "already_full"

    **Behavior:**
    - This is a management command that bypasses normal command queue
    - Sets battery_level to 100.0% for all drones
    - Updates battery_volume to maximum capacity if applicable
    - Does not change drone position or status
    - Session history records battery changes for all drones
    - Safe to call repeatedly - drones already at 100% are ignored gracefully
    """
    results = []
    all_drones = drone_controller.get_all_drones()

    for drone_dict in all_drones:
        drone_id = drone_dict["id"]
        drone = drone_controller.drones[drone_id]

        previous_level = drone.battery_level
        previous_volume = drone.battery_volume

        drone.update_battery(100.0)

        # Record the status change in session history with updated battery
        current_session = session_controller.get_current_session()
        if current_session:
            session_id = current_session.get("id")
            if session_id and session_id in session_controller.sessions:
                session = session_controller.sessions[session_id]
                session.record_drone_status(
                    drone_id=drone.id,
                    status=drone.status.value if hasattr(drone.status, "value") else str(drone.status),
                    position=drone.position.copy(),
                    battery_level=drone.battery_level,
                    battery_volume=drone.battery_volume
                )

        results.append({
            "drone_id": drone_id,
            "drone_name": drone.name,
            "previous_battery_level": previous_level,
            "previous_battery_volume": previous_volume,
            "new_battery_level": drone.battery_level,
            "new_battery_volume": drone.battery_volume,
            "action": "charged" if previous_level < 100.0 else "already_full"
        })

    return {
        "message": f"Successfully charged {len(results)} drone(s)",
        "total_drones": len(results),
        "drones_charged": len([r for r in results if r["action"] == "charged"]),
        "drones_already_full": len([r for r in results if r["action"] == "already_full"]),
        "details": results
    }


# Target API Routes
@app.get("/targets", tags=["Targets"])
async def get_all_targets(current_role: UserRole = Depends(require_user)):
    """
    Get a list of all registered targets.

    **Required Privileges:**
    - USER: Can view targets
    - SYSTEM, ADMIN: Inherit access from role hierarchy

    **Response Format:**
    - Array of TargetResponse objects with full target details
    """
    session_controller.sync_current_session_snapshot()
    session = session_controller.get_current_session_ref()
    if session is not None:
        return session.to_dict(data=True).get("targets", [])
    return target_controller.get_all_targets()

@app.post("/targets", status_code=status.HTTP_201_CREATED, tags=["Targets"])
async def add_target(target: TargetRequest, _role: UserRole = Depends(require_system)):
    """
    Create a new target in the system.

    **Required Privileges:**
    - SYSTEM: Can create and modify targets
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - name: Target name (required)
    - type: Target type (required):
      * 'fixed' - Static point of interest
      * 'moving' - Mobile target
      * 'waypoint' - Charge/refuel station
      * 'circle' - Circular area target
      * 'polygon' - Custom polygon area
    - position: Initial {x, y, z} coordinates (required)
    - description: Human-readable description (optional, default: "")
    - velocity: Movement vector {x, y, z} for moving targets (optional)
    - radius: Target size in meters (optional, default: 1.0)
    - moving_path: Array of waypoint coordinates for path-following targets (optional)
    - moving_duration: Seconds for ping-pong or path traversal (optional, default: 10.0)
    - charge_amount: Instant charge percent for waypoint type (optional)
    - vertices: Array of coordinates for polygon targets (optional)

    **Response Format:**
    - Complete TargetResponse object with generated ID
    - 400 Bad Request if validation fails or conflicts with obstacles

    **Movement Priority for Moving Targets:**
    (Evaluated in this order - only one mode active)
    1. VELOCITY MODE (highest priority):
       * Trigger: velocity is non-zero AND moving_duration > 0
       * Behavior: Ping-pong movement - moves continuously with velocity vector, reverses direction after moving_duration
    2. PATH MODE (middle priority):
       * Trigger: velocity is null/zero AND moving_path exists AND moving_duration > 0
       * Behavior: Follows waypoint path sequentially - speed automatically calculated to complete one-way trip in moving_duration
    3. STATIONARY (fallback):
       * Trigger: moving_duration == 0 OR neither velocity nor path provided
       * Behavior: Target stays fixed at position

    **Target Type Notes:**
    - 'waypoint' targets can recharge drones automatically when task_radius is entered
    - 'circle' and 'polygon' targets are area targets for area search/coverage tasks
    - 'moving' targets track drone visits and update statistics when reached
    """
    try:
        # Convert Pydantic model to dict for controller
        target_data = {
            "name": target.name,
            "type": target.type,
            "position": target.position,
            "description": target.description,
            "radius": target.radius,
        }

        # Add optional fields only if provided
        if target.velocity is not None:
            target_data["velocity"] = target.velocity
        if target.moving_path is not None:
            target_data["moving_path"] = target.moving_path
        if target.moving_duration is not None:
            target_data["moving_duration"] = target.moving_duration
        if target.charge_amount is not None:
            target_data["charge_amount"] = target.charge_amount
        if target.vertices is not None:
            target_data["vertices"] = target.vertices

        result = target_controller.add_target(target_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/targets/waypoints/{waypoint_id}/check-drone", tags=["Targets"])
async def check_drone_at_waypoint(waypoint_id: str, drone_position: Dict[str, float], _role: UserRole = Depends(require_user)):
    """
    Verify if a drone is within range of a charging waypoint.

    **Required Privileges:**
    - USER: Can check waypoint proximity
    - SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - waypoint_id: Target waypoint ID (path parameter)
    - drone_position: Drone's {x, y, z} coordinates (body parameter)

    **Response Format:**
    - waypoint_id: Verified waypoint ID
    - drone_in_range: Boolean indicating if drone is within task_radius
    - charge_amount: Percentage charge available at this waypoint
    - drone_position: Echoed drone position
    - 404 Not Found if waypoint doesn't exist
    """
    is_at_waypoint = target_controller.check_drone_at_waypoint(waypoint_id, drone_position)
    charge_amount = 0.0
    if is_at_waypoint:
        charge_amount = target_controller.get_charge_amount_at_waypoint(waypoint_id)

    return {
        "waypoint_id": waypoint_id,
        "drone_in_range": is_at_waypoint,
        "charge_amount": charge_amount,
        "drone_position": drone_position
    }

@app.get("/targets/{target_id}", tags=["Targets"])
async def get_target(target_id: str, _role: UserRole = Depends(require_agent)):
    """
    Get a specific target by its ID.

    **Required Privileges:**
    - AGENT: Can view target details
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - target_id: Target ID to retrieve (path parameter)

    **Response Format:**
    - TargetResponse object with full target details
    - 404 Not Found if target doesn't exist
    """
    session_controller.sync_current_session_snapshot()
    session = session_controller.get_current_session_ref()
    target = None
    if session is not None:
        for target_data in session.to_dict(data=True).get("targets", []):
            if target_data.get("id") == target_id:
                target = target_data
                break
    if target is None:
        target = target_controller.get_target(target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return target

@app.put("/targets/{target_id}", tags=["Targets"])
async def update_target(target_id: str, target_update: TargetUpdateRequest, _role: UserRole = Depends(require_system)):
    """
    Update a target's properties.

    **Required Privileges:**
    - SYSTEM: Can modify target properties
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - target_id: Target ID to update (path parameter)
    - name: Updated name (optional)
    - position: Updated coordinates (optional)
    - description: Updated description (optional)
    - velocity: Updated movement vector (optional)
    - radius: Updated radius (optional)
    - moving_path: Updated path waypoints (optional)
    - moving_duration: Updated duration (optional)
    - charge_amount: Updated charge amount (optional)
    - vertices: Updated polygon vertices (optional)

    **Response Format:**
    - Updated TargetResponse object
    - 400 Bad Request if validation fails or position conflicts with obstacles
    - 404 Not Found if target doesn't exist
    """
    updates = {k: v for k, v in target_update.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(status_code=400, detail="No valid updates provided")

    try:
        updated_target = target_controller.update_target(target_id, updates)
        if not updated_target:
            raise HTTPException(status_code=404, detail="Target not found")
        session_controller.sync_current_session_snapshot()
        session = session_controller.get_current_session_ref()
        if session is not None:
            for target_data in session.to_dict(data=True).get("targets", []):
                if target_data.get("id") == target_id:
                    return target_data
        return updated_target
    except ValueError as e:
        # Handle validation errors and collision conflicts
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(status_code=500, detail=f"Failed to update target: {str(e)}")

@app.delete("/targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Targets"])
async def delete_target(target_id: str, _role: UserRole = Depends(require_system)):
    """
    Remove a target from the system.

    **Required Privileges:**
    - SYSTEM: Can delete targets
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - target_id: Target ID to delete (path parameter)

    **Response Format:**
    - 204 No Content on success
    - 404 Not Found if target doesn't exist

    **Notes:**
    - This action cannot be undone
    - Target reach history remains in session statistics
    """
    success = target_controller.delete_target(target_id)
    if not success:
        raise HTTPException(status_code=404, detail="Target not found")
    return None

@app.get("/targets/type/{type}", tags=["Targets"])
async def get_targets_by_type(type: TargetType, _role: UserRole = Depends(require_user)):
    """
    Get all targets of a specific type.

    **Required Privileges:**
    - USER: Can view targets by type
    - SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - type: Target type (path parameter):
      * 'fixed' - Static points of interest
      * 'moving' - Mobile targets
      * 'waypoint' - Charge/refuel stations
      * 'circle' - Circular area targets
      * 'polygon' - Custom polygon areas

    **Response Format:**
    - Array of TargetResponse objects matching the specified type
    """
    session_controller.sync_current_session_snapshot()
    session = session_controller.get_current_session_ref()
    if session is not None:
        return [
            target for target in session.to_dict(data=True).get("targets", [])
            if target.get("type") == type.value
        ]
    return target_controller.get_targets_by_type(type)


# Environment API Routes
@app.get("/environments", response_model=List[EnvironmentResponse], tags=["Environment"])
async def get_all_environments(_role: UserRole = Depends(require_system)):
    """
    Get a list of all available environment configurations.

    **Required Privileges:**
    - SYSTEM: Can view all environments
    - ADMIN: Inherits access from role hierarchy

    **Response Format:**
    - Array of EnvironmentResponse objects with full environment details
    """
    return environment_controller.get_all_environments()

@app.post("/environments", response_model=EnvironmentResponse, status_code=status.HTTP_201_CREATED, tags=["Environment"])
async def create_environment(environment: EnvironmentRequest, _role: UserRole = Depends(require_system)):
    """
    Create a new environment configuration.

    **Required Privileges:**
    - SYSTEM: Can create environments
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - name: Environment name (required)
    - weather: Weather condition (required):
      * 'clear' - Clear skies
      * 'cloudy' - Cloudy weather
      * 'rain' - Rainy conditions
      * 'fog' - Low visibility fog
      * 'storm' - Storm conditions
    - temperature: Temperature in Celsius (required)
    - humidity: Humidity percentage 0-100 (required)
    - pressure: Atmospheric pressure in hPa (optional, default: 1013.25)
    - wind_speed: Wind speed in m/s (optional, default: 0.0)
    - wind_direction: Wind direction (optional, default: 'north')
    - visibility: Visibility in meters (optional, default: 10000.0)

    **Response Format:**
    - Created EnvironmentResponse object with ID
    - 400 Bad Request if validation fails
    """
    # Convert Pydantic model to dict for controller
    environment_data = {
        "name": environment.name,
        "weather": environment.weather,
        "temperature": environment.temperature,
        "humidity": environment.humidity,
        "pressure": environment.pressure,
        "wind_speed": environment.wind_speed,
        "wind_direction": environment.wind_direction,
        "visibility": environment.visibility,
    }

    return environment_controller.add_environment(environment_data)

@app.get("/environments/current", response_model=EnvironmentResponse, tags=["Environment"])
async def get_current_environment(_role: UserRole = Depends(require_agent)):
    """
    Get the currently active environment configuration.

    **Required Privileges:**
    - AGENT: Can view current environment
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Response Format:**
    - EnvironmentResponse object with active environment details
    - 404 Not Found if no environment is active
    """
    return environment_controller.get_current_environment()

@app.post("/environments/{environment_id}/set-current", response_model=EnvironmentResponse, tags=["Environment"])
async def set_current_environment(environment_id: str, _role: UserRole = Depends(require_system)):
    """
    Set an environment as the active configuration.

    **Required Privileges:**
    - SYSTEM: Can change active environment
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - environment_id: Environment ID to activate (path parameter)

    **Response Format:**
    - EnvironmentResponse object of the now-active environment
    - 404 Not Found if environment doesn't exist
    """
    environment = environment_controller.set_current_environment(environment_id)
    if not environment:
        raise HTTPException(status_code=404, detail="Environment not found")
    return environment

@app.get("/environments/{environment_id}", response_model=EnvironmentResponse, tags=["Environment"])
async def get_environment(environment_id: str, _role: UserRole = Depends(require_agent)):
    """
    Get a specific environment configuration by ID.

    **Required Privileges:**
    - AGENT: Can view environment details
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - environment_id: Environment ID to retrieve (path parameter)

    **Response Format:**
    - EnvironmentResponse object with full details
    - 404 Not Found if environment doesn't exist
    """
    environment = environment_controller.get_environment(environment_id)
    if not environment:
        raise HTTPException(status_code=404, detail="Environment not found")
    return environment

@app.put("/environments/{environment_id}", response_model=EnvironmentResponse, tags=["Environment"])
async def update_environment(environment_id: str, environment_update: EnvironmentUpdateRequest, _role: UserRole = Depends(require_system)):
    """
    Update an environment's properties.

    **Required Privileges:**
    - SYSTEM: Can modify environments
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - environment_id: Environment ID to update (path parameter)
    - name: Updated name (optional)
    - weather: Updated weather condition (optional)
    - temperature: Updated temperature (optional)
    - humidity: Updated humidity (optional)
    - pressure: Updated pressure (optional)
    - wind_speed: Updated wind speed (optional)
    - wind_direction: Updated wind direction (optional)
    - visibility: Updated visibility (optional)

    **Response Format:**
    - Updated EnvironmentResponse object
    - 400 Bad Request if validation fails
    - 404 Not Found if environment doesn't exist
    """
    updates = {k: v for k, v in environment_update.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(status_code=400, detail="No valid updates provided")

    try:
        updated_environment = environment_controller.update_environment(environment_id, updates)
        if not updated_environment:
            raise HTTPException(status_code=404, detail="Environment not found")
        return updated_environment
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(status_code=500, detail=f"Failed to update environment: {str(e)}")

@app.delete("/environments/{environment_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Environment"])
async def delete_environment(environment_id: str, _role: UserRole = Depends(require_system)):
    """
    Remove an environment configuration from the system.

    **Required Privileges:**
    - SYSTEM: Can delete environments
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - environment_id: Environment ID to delete (path parameter)

    **Response Format:**
    - 204 No Content on success
    - 400 Bad Request if trying to delete the currently active environment or the last environment
    - 404 Not Found if environment doesn't exist

    **Notes:**
    - You cannot delete the currently active environment - switch to another first
    - You cannot delete the last remaining environment - create another first
    """
    environment = environment_controller.get_environment(environment_id)
    if not environment:
        raise HTTPException(status_code=404, detail="Environment not found")

    if environment_controller.is_environment_current(environment_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the current environment. Set another environment as current before deleting this one."
        )

    success = environment_controller.delete_environment(environment_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the only environment. Create another environment before deleting this one."
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Obstacle API Routes
@app.get("/obstacles", response_model=List[ObstacleResponse], tags=["Obstacles"])
async def get_all_obstacles(_role: UserRole = Depends(require_user)):
    """
    Get a list of all registered obstacles.

    **Required Privileges:**
    - USER: Can view obstacles
    - SYSTEM, ADMIN: Inherit access from role hierarchy

    **Response Format:**
    - Array of ObstacleResponse objects with full obstacle details
    """
    return obstacle_controller.get_all_obstacles()

@app.post("/obstacles", response_model=ObstacleResponse, status_code=status.HTTP_201_CREATED, tags=["Obstacles"])
async def create_obstacle(obstacle: ObstacleRequest, _role: UserRole = Depends(require_system)):
    """
    Create a new obstacle in the environment.

    **Required Privileges:**
    - SYSTEM: Can create obstacles
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - name: Obstacle name (required)
    - type: Obstacle type (required):
      * 'point' - Single point obstacle
      * 'circle' - Circular obstacle (needs radius)
      * 'ellipse' - Elliptical obstacle (needs width/length)
      * 'polygon' - Custom polygon (needs vertices array)
    - position: Center coordinates {x, y, z} (optional for polygons, depending on type)
    - description: Human-readable description (optional, default: "")
    - radius: Radius in meters (required for point/circle)
    - vertices: Array of coordinates (required for polygon)
    - width: Semi-major axis in meters (required for ellipse)
    - length: Semi-minor axis in meters (required for ellipse)
    - height: Height in meters (optional, default: 0):
      * 0 = Impassable at any altitude
      * >0 = Collision only if drone altitude <= height

    **Response Format:**
    - Created ObstacleResponse object with ID and calculated area
    - 400 Bad Request if validation fails or type-specific params are missing
    """
    try:
        # Convert Pydantic model to dict for controller
        obstacle_data = {
            "name": obstacle.name,
            "type": obstacle.type,
            "position": obstacle.position,
            "description": obstacle.description,
        }

        # Add optional fields only if provided
        if obstacle.radius is not None:
            obstacle_data["radius"] = obstacle.radius
        if obstacle.vertices is not None:
            obstacle_data["vertices"] = obstacle.vertices
        if obstacle.width is not None:
            obstacle_data["width"] = obstacle.width
        if obstacle.length is not None:
            obstacle_data["length"] = obstacle.length
        if obstacle.height is not None:
            obstacle_data["height"] = obstacle.height

        result = obstacle_controller.add_obstacle(obstacle_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/obstacles/{obstacle_id}", response_model=ObstacleResponse, tags=["Obstacles"])
async def get_obstacle(obstacle_id: str, _role: UserRole = Depends(require_agent)):
    """
    Retrieve a specific obstacle by its unique identifier.

    **Required Privileges:**
    - AGENT: Basic access to retrieve obstacle details
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - obstacle_id: Unique identifier of the obstacle to retrieve

    **Response Format:**
    - ObstacleResponse object with complete obstacle details
    - 404 Not Found if obstacle with given ID does not exist
    """
    obstacle = obstacle_controller.get_obstacle(obstacle_id)
    if not obstacle:
        raise HTTPException(status_code=404, detail="Obstacle not found")
    return obstacle

@app.put("/obstacles/{obstacle_id}", response_model=ObstacleResponse, tags=["Obstacles"])
async def update_obstacle(obstacle_id: str, obstacle_update: ObstacleUpdateRequest, _role: UserRole = Depends(require_system)):
    """
    Update an existing obstacle's properties.

    **Required Privileges:**
    - SYSTEM: Can modify obstacle properties
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - obstacle_id: Unique identifier of the obstacle to update
    - obstacle_update: Request body containing fields to update:
      - name: New name for the obstacle
      - description: New description
      - position: New position coordinates (x, y, optional z)
      - radius: New radius for point/circle obstacles
      - vertices: New vertices for polygon obstacles
      - width: New semi-major axis for ellipse obstacles
      - length: New semi-minor axis for ellipse obstacles
      - height: New height value (0 = always blocked, >0 = altitude-limited)

    **Response Format:**
    - Updated ObstacleResponse object
    - 400 Bad Request if no valid fields provided or validation fails
    - 404 Not Found if obstacle with given ID does not exist

    **Notes:**
    - Only provided fields are updated; omitted fields remain unchanged
    - Type-specific validation applies (e.g., radius required for circle obstacles)
    """
    updates = {k: v for k, v in obstacle_update.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(status_code=400, detail="No valid updates provided")

    try:
        updated_obstacle = obstacle_controller.update_obstacle(obstacle_id, updates)
        if not updated_obstacle:
            raise HTTPException(status_code=404, detail="Obstacle not found")
        return updated_obstacle
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(status_code=500, detail=f"Failed to update obstacle: {str(e)}")

@app.delete("/obstacles/{obstacle_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Obstacles"])
async def delete_obstacle(obstacle_id: str, _role: UserRole = Depends(require_system)):
    """
    Delete an obstacle from the environment.

    **Required Privileges:**
    - SYSTEM: Can delete obstacles
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - obstacle_id: Unique identifier of the obstacle to delete

    **Response Format:**
    - 204 No Content on successful deletion
    - 404 Not Found if obstacle with given ID does not exist

    **Notes:**
    - Deletion is permanent and cannot be undone
    - Removes the obstacle from all collision detection calculations
    """
    success = obstacle_controller.delete_obstacle(obstacle_id)
    if not success:
        raise HTTPException(status_code=404, detail="Obstacle not found")
    return None

@app.get("/obstacles/type/{type}", response_model=List[ObstacleResponse], tags=["Obstacles"])
async def get_obstacles_by_type(type: ObstacleType, _role: UserRole = Depends(require_user)):
    """
    Retrieve all obstacles of a specific geometric type.

    **Required Privileges:**
    - USER: Can access filtered obstacle lists
    - SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - type: Obstacle type enum (point, circle, ellipse, polygon)

    **Response Format:**
    - Array of ObstacleResponse objects matching the requested type
    - Empty array if no obstacles of that type exist
    """
    return obstacle_controller.get_obstacles_by_type(type)

@app.post("/obstacles/path_collision", response_model=CollisionResponse, tags=["Obstacles"])
async def check_path_collision(path_check: PathCollisionCheckRequest, _role: UserRole = Depends(require_system)):
    """
    Check if a flight path between two points collides with any obstacles.

    **Required Privileges:**
    - SYSTEM: Can perform collision detection checks
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - path_check: Request body containing:
      - start: Starting coordinate with x, y (required) and z (optional, default: 0.0)
      - end: Ending coordinate with x, y (required) and z (optional, default: 0.0)
      - safety_margin: Additional buffer distance in meters (optional, default: 0.0)

    **Response Format:**
    - CollisionResponse object with:
      - collision: Boolean indicating if collision detected
      - obstacle: ObstacleResponse of first colliding obstacle (only if collision = true)
      - collision_point: Coordinates where collision occurs (only if collision = true)

    **Height Logic:**
    - Obstacle height = 0: Impassable at any altitude (always collides in 2D)
    - Obstacle height > 0: Collision only if max flight altitude <= obstacle.height

    **Notes:**
    - Returns the FIRST obstacle that collides with the path
    - Safety margin adds extra distance around obstacles for collision detection
    """
    start = path_check.start
    end = path_check.end
    return obstacle_controller.check_path_collision(
        start["x"], start["y"], end["x"], end["y"],
        start.get("z", 0.0), end.get("z", 0.0),
        path_check.safety_margin
    )

@app.post("/obstacles/point_collision", response_model=PointInObstaclesResponse, tags=["Obstacles"])
async def check_point_collision(request: PointInObstaclesRequest, _role: UserRole = Depends(require_system)):
    """
    Check if a point is inside or on the boundary of any obstacles, considering a safety margin.

    **Required Privileges:**
    - SYSTEM: Can perform point collision detection checks
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - request: Request body containing:
      - x, y: Coordinates of point to check (required)
      - z: Altitude in meters (optional)
      - margin: Safety buffer distance in meters (optional, default: 0.0)

    **Response Format:**
    - PointInObstaclesResponse object with:
      - inside_any: Boolean indicating if point is inside any obstacle
      - obstacles: Array of ObstacleResponse objects containing the point

    **Height Logic:**
    - If z NOT provided: Checks 2D area only (all obstacles considered non-flyable)
    - If z provided and obstacle height = 0: Area is non-flyable at any altitude
    - If z provided and obstacle height > 0:
      - Point is inside if z <= obstacle.height + margin
      - Point is outside if z > obstacle.height + margin

    **Notes:**
    - Returns ALL obstacles that contain the point (not just the first one)
    - Margin expands obstacle boundaries for more conservative collision detection
    """
    return obstacle_controller.check_point_collision(
        request.x, request.y, request.z, request.margin
    )

# Session API Routes
@app.get("/sessions", response_model=List[SessionResponse], tags=["Sessions"])
async def get_all_sessions(_role: UserRole = Depends(require_agent)):
    """
    Retrieve a list of all available sessions.

    **Required Privileges:**
    - AGENT: Basic access to session metadata
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Response Format:**
    - Array of SessionResponse objects, each containing:
      - id, name, description, status, creator, statistics
      - timestamps: created_at, last_updated
    - No history or entity data included (metadata only for all roles)

    **Data Masking:**
    - All roles receive metadata-only responses (no drones, targets, obstacles, or history)
    - To retrieve complete session data, use GET /sessions/{session_id} with data=true
    """
    sessions = session_controller.get_all_sessions()
    # Mask sessions for AGENT/USER roles (metadata only, no history)
    return [_mask_session_for_role(session, _role, data=False) for session in sessions]

@app.post("/sessions", status_code=status.HTTP_201_CREATED, tags=["Sessions"])
async def create_session(
    session_data: SessionCreateRequest,
    data: bool = True,
    current_role: UserRole = Depends(require_system)
):
    """
    Create a new session with an auto-generated unique identifier.

    **Required Privileges:**
    - SYSTEM: Can create new sessions
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_data: Request body containing session configuration:
      - name: Session name (required)
      - description: Session description (optional)
      - creator: Creator name (optional, defaults to role name)
      - with_examples: Boolean to create example data (optional, default: false)
      - task_type: Type of task (optional, default: 'others')
      - task_description: Detailed task description (optional)
      - drones: Array of drone objects to initialize (optional)
      - targets: Array of target objects to initialize (optional)
      - obstacles: Array of obstacle objects to initialize (optional)
      - tasks: Array of task objects to initialize (optional)
      - environment: Environment configuration object (optional)
      - history: Command history records to restore (optional)
      - status_history: Drone status history to restore (optional)
      - area_coverage: Area coverage tracking data (optional)
      - target_reaches: Target reach tracking data (optional)
    - data: Query parameter - return full session data in response (optional, default: true)

    **Response Format:**
    - 201 Created with SessionResponse object
    - Session metadata (ID, name, status, timestamps, etc.)
    - If data=true, includes complete session state with all entities
    - 400 Bad Request if initialization fails

    **Behavior:**
    - Creates a new session with auto-generated UUID
    - If entity data provided (drones, targets, etc.), initializes them in the session
    - Can restore complete session state from backup data
    - Automatically sets creator from current role if not specified
    - Does NOT automatically set as current session (use POST /sessions/{id}/set-current)
    """
    creator_name = session_data.creator or current_role.value

    # Create session with metadata
    new_session = session_controller.add_session({
        "name": session_data.name,
        "description": session_data.description,
        "with_examples": session_data.with_examples,
        "task_type": session_data.task_type,
        "task_description": session_data.task_description,
        "creator": creator_name
    })
    session_id = new_session["id"]

    # If entities provided, restore them using flat format
    if (
        session_data.drones
        or session_data.targets
        or session_data.obstacles
        or session_data.environment
        or session_data.tasks
        or session_data.history
    ):
        try:
            payload = session_data.model_dump()
            payload["id"] = session_id
            payload.setdefault("creator", creator_name)
            payload.setdefault("status", session_data.status or new_session.get("status", SessionStatus.ACTIVE.value))
            payload.setdefault("created_at", new_session.get("created_at"))
            payload.setdefault("last_updated", new_session.get("last_updated"))
            payload.setdefault("statistics", new_session.get("statistics", {}))

            # Ensure history is properly set in payload
            if session_data.history:
                payload["history"] = session_data.history

            # Re-create session from provided data (with generated id metadata)
            session = session_controller.create_session_from_dict(payload)

            # Replace the session in the controller
            session_controller.sessions[session_id] = session

            # Load data to controllers if this is the current session
            if session_id == session_controller.current_session_id:
                session_controller._load_session_data_to_controllers(session)
        except Exception as e:
            # If restoration fails, delete the session and raise error
            session_controller.delete_session(session_id)
            raise HTTPException(status_code=400, detail=f"Failed to create entities: {str(e)}")

    # Return session metadata (or full data if requested)
    return session_controller.get_session(session_id, data=data)

@app.get("/sessions/current", tags=["Sessions"])
async def get_current_session(data: bool = False, _role: UserRole = Depends(require_agent)):
    """
    Get the current active session.

    **Required Privileges:**
    - AGENT: Can access session metadata
    - USER: Can access metadata and entity data (no history)
    - SYSTEM, ADMIN: Full access to everything including session history

    **Request Parameters:**
    - data: Boolean query parameter (default: false)
      * false: Returns only session metadata and statistics
      * true: Returns complete session data including all drones, targets, obstacles, tasks, and environment

    **Response Format:**
    - Session metadata: id, name, description, status, creator, task_type, statistics, etc.
    - (When data=true and role permits): Nested drones, targets, obstacles, environment, tasks, and history
    - 404 Not Found if no current session is active

    **Role-Based Data Masking:**
    - AGENT: Always gets metadata-only response regardless of data parameter
    - USER: Can request data=true but sensitive fields/tasks are masked and history is removed
    - SYSTEM/ADMIN: Get complete unfiltered data including full history when data=true

    **Examples:**
    - GET /sessions/current - Returns session metadata only
    - GET /sessions/current?data=true - Returns complete session data (USER/SYSTEM/ADMIN only)
    """
    if not session_controller.current_session_id:
        raise HTTPException(status_code=404, detail="No current session found")

    # AGENT role always gets metadata only (data=False)
    # USER role can request data=True (but history is masked by _mask_session_for_role)
    if _role == UserRole.AGENT:
        use_data = False
    else:
        # USER, SYSTEM, ADMIN respect the data parameter
        use_data = data

    session_controller.sync_current_session_snapshot()

    if use_data:
        # Return complete session data
        session_data = session_controller.get_session(session_controller.current_session_id, data=True)
        if not session_data:
            raise HTTPException(status_code=404, detail="No current session found")
        return _mask_session_for_role(session_data, _role, data=True)
    else:
        # Return metadata only
        current_session = session_controller.get_current_session()
        if not current_session:
            raise HTTPException(status_code=404, detail="No current session found")
        return _mask_session_for_role(current_session, _role, data=False)

@app.get("/sessions/current/data", tags=["Sessions"])
async def get_current_session_data(_role: UserRole = Depends(require_system)):
    """
    Get complete data for the current active session.

    **Required Privileges:**
    - SYSTEM: Full access to complete session data
    - ADMIN: Inherits access from role hierarchy
    - USER/AGENT: Only receive metadata (no entity data or history)

    **Response Format:**
    - Complete session data including:
      - Session metadata and statistics
      - All drones with current state
      - All targets (fixed, moving, waypoint, circle, polygon)
      - All obstacles
      - Current environment settings
      - All tasks
    - 404 Not Found if no current session is active

    **Notes:**
    - Convenience endpoint equivalent to GET /sessions/current?data=true
    - For USER/AGENT roles, sensitive fields are masked and history is removed
    """
    if not session_controller.current_session_id:
        raise HTTPException(status_code=404, detail="No current session found")

    # USER/AGENT roles always get metadata only (data=False), regardless of endpoint
    use_data = _role not in (UserRole.USER, UserRole.AGENT)

    session_controller.sync_current_session_snapshot()

    if use_data:
        session_data = session_controller.get_session(session_controller.current_session_id, data=True)
        if not session_data:
            raise HTTPException(status_code=404, detail="No current session found")
        return _mask_session_for_role(session_data, _role, data=True)
    else:
        # Return metadata only for USER role
        current_session = session_controller.get_current_session()
        if not current_session:
            raise HTTPException(status_code=404, detail="No current session found")
        return _mask_session_for_role(current_session, _role, data=False)

@app.get("/sessions/{session_id}", tags=["Sessions"])
async def get_session(session_id: str, data: bool = False, _role: UserRole = Depends(require_system)):
    """
    Retrieve a specific session by its unique identifier.

    **Required Privileges:**
    - SYSTEM: Full access to session data
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session to retrieve
    - data: Query parameter (default: false)
      * false: Returns only session metadata and statistics
      * true: Returns complete session data including all entities

    **Response Format:**
    - Session metadata: id, name, description, status, creator, task_type, statistics, timestamps
    - (When data=true): Complete session data with drones, targets, obstacles, environment, tasks, history
    - 404 Not Found if session with given ID does not exist

    **Examples:**
    - GET /sessions/abc123 - Returns session metadata only
    - GET /sessions/abc123?data=true - Returns complete session data
    """
    session_controller.sync_session_snapshot(session_id)
    if data:
        # Return complete session data
        session_data = session_controller.get_session(session_id, data=True)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        return session_data
    else:
        # Return metadata only
        session = session_controller.get_session(session_id, data=False)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

@app.put("/sessions/{session_id}", tags=["Sessions"])
async def update_session(
    session_id: str,
    session_update: SessionUpdateRequest,
    data: bool = False,
    _role: UserRole = Depends(require_system)
):
    """
    Update a session's metadata properties.

    **Required Privileges:**
    - SYSTEM: Can modify session metadata
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session to update
    - session_update: Request body containing fields to update:
      - name: New session name
      - description: New session description
      - status: New session status (active, paused, completed, archived)
      - task_type: New task type
      - task_description: New task description
    - data: Query parameter (default: false) - return complete session data in response

    **Response Format:**
    - Updated SessionResponse object
    - 404 Not Found if session with given ID does not exist

    **Notes:**
    - Only updates metadata; does NOT modify drones, targets, obstacles, or tasks
    - Use entity-specific endpoints to modify those resources
    - Omitted fields remain unchanged
    """
    updates = {k: v for k, v in session_update.model_dump().items() if v is not None}
    updated_session = session_controller.update_session(session_id, updates)
    if not updated_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Return based on data parameter
    if data:
        session_data_response = session_controller.get_session(session_id, data=True)
        if not session_data_response:
            raise HTTPException(status_code=404, detail="Session not found")
        return session_data_response
    else:
        return updated_session

@app.post("/sessions/{session_id}", status_code=status.HTTP_201_CREATED, tags=["Sessions"])
async def create_session_with_id(
    session_id: str,
    session_data: SessionCreateRequest,
    data: bool = True,
    current_role: UserRole = Depends(require_system)
):
    """
    Create or restore a session with a specific custom identifier.

    **Required Privileges:**
    - SYSTEM: Can create/restore sessions with custom IDs
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Custom unique identifier for the session
    - session_data: Request body with session configuration (see POST /sessions for details)
    - data: Query parameter (default: true) - return complete session data in response

    **Response Format:**
    - 201 Created with SessionResponse object
    - 400 Bad Request if creation/restore fails

    **Behavior:**
    - If session with same ID already exists, it will be completely overwritten
    - Can restore complete session state from backup data including all entities and history
    - Preserves created_at timestamp if restoring and not provided
    - If restoring the current active session, maintains its active status
    - Does NOT automatically set as current session (use POST /sessions/{id}/set-current)
    """
    creator_name = session_data.creator or current_role.value

    # Check if session already exists
    existing_session = session_controller.get_session(session_id)
    preserved_created_at = None

    if existing_session:
        # If session exists, we always overwrite it
        preserved_created_at = existing_session.get("created_at")
        # Remember if we're overwriting the current session
        was_current_session = (session_id == session_controller.current_session_id)

        # Delete existing session
        success = session_controller.delete_session(session_id)
        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete existing session {session_id}"
            )

        # Restore current_session_id reference if we deleted the current session
        if was_current_session:
            session_controller.current_session_id = session_id

    # Prepare full restoration data in flat format
    restore_data = {
        "id": session_id,
        "name": session_data.name,
        "description": session_data.description,
        "status": session_data.status or "active",
        "task_type": session_data.task_type,
        "task_description": session_data.task_description,
        "creator": creator_name,
        "created_at": session_data.created_at or preserved_created_at or time.time(),
        "last_updated": session_data.last_updated or time.time(),
        "drones": session_data.drones,
        "targets": session_data.targets,
        "obstacles": session_data.obstacles,
        "environment": session_data.environment,
        "tasks": session_data.tasks,
        "history": session_data.history
    }

    # Create session from flat data
    try:
        session = session_controller.create_session_from_dict(restore_data)

        # Check if we're restoring the current active session
        is_current_session = (session.id == session_controller.current_session_id)

        if is_current_session:
            # Preserve the active status when restoring current session
            session.update_status(SessionStatus.ACTIVE)

        # Store the session (this may overwrite existing session with same ID)
        session_controller.sessions[session.id] = session

        if is_current_session:
            # Load the restored data into controllers since this is the active session
            session_controller._load_session_data_to_controllers(session)

        restored_session = session.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create/restore session: {str(e)}")

    # Return based on data parameter
    if data:
        session_data_response = session_controller.get_session(session_id, data=True)
        if not session_data_response:
            raise HTTPException(status_code=404, detail="Created session not found")
        return session_data_response
    else:
        return restored_session

@app.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Sessions"])
async def delete_session(session_id: str, _role: UserRole = Depends(require_system)):
    """
    Delete a session permanently.

    **Required Privileges:**
    - SYSTEM: Can delete sessions
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session to delete

    **Response Format:**
    - 204 No Content on successful deletion
    - 404 Not Found if session with given ID does not exist

    **Notes:**
    - Deletion is permanent and cannot be undone
    - If deleting the current active session, will need to set a new current session
    - All session data including entities and history are removed
    """
    success = session_controller.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return None

@app.post("/sessions/{session_id}/set-current", response_model=SessionResponse, tags=["Sessions"])
async def set_current_session(session_id: str, _role: UserRole = Depends(require_agent)):
    """
    Set a session as the current active session.

    **Required Privileges:**
    - AGENT: Can switch between sessions
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session to activate

    **Response Format:**
    - SessionResponse with metadata of the newly activated session
    - 404 Not Found if session with given ID does not exist

    **Behavior:**
    - Loads the session's entities (drones, targets, obstacles, environment) into active controllers
    - Deactivates the previous current session if one existed
    - Session status is automatically set to ACTIVE
    - Returns metadata-only response for all roles
    """
    session = session_controller.set_current_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # Mask session for AGENT/USER roles (metadata only, no history)
    return _mask_session_for_role(session, _role, data=False)

@app.post("/sessions/current/reset", response_model=SessionResponse, tags=["Sessions"])
async def reset_current_session(_role: UserRole = Depends(require_system)):
    """
    Reset the current session to its initial state.

    **Required Privileges:**
    - SYSTEM: Can reset sessions
    - ADMIN: Inherits access from role hierarchy

    **Response Format:**
    - SessionResponse of the reset session
    - 404 Not Found if no current session is active

    **Behavior:**
    - Clears all history tracking data:
      * Command history
      * Status history (drone status changes)
      * Path history (drone movement traces)
      * Target reach logs
      * Area coverage data
      * Statistics (total commands, flight time, distance)
      * Session timer
    - Preserves: session ID, name, description, all entities (drones, targets, obstacles, environment)
    - Resets drones to their initial positions and states
    """
    if not session_controller.current_session_id:
        raise HTTPException(status_code=404, detail="No current session")

    session = session_controller.reset_session(session_controller.current_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Current session not found")
    return session

@app.post("/sessions/{session_id}/reset", response_model=SessionResponse, tags=["Sessions"])
async def reset_session(session_id: str, _role: UserRole = Depends(require_system)):
    """
    Reset a specific session to its initial state.

    **Required Privileges:**
    - SYSTEM: Can reset sessions
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session to reset

    **Response Format:**
    - SessionResponse of the reset session
    - 404 Not Found if session with given ID does not exist

    **Behavior:**
    - Clears all history tracking data (see POST /sessions/current/reset for details)
    - Preserves session ID, name, description, and all entities
    - Can reset any session, not just the current active one
    """
    session = session_controller.reset_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.get("/sessions/{session_id}/data", response_model=SessionDataResponse, tags=["Sessions"])
async def get_session_data(session_id: str, _role: UserRole = Depends(require_system)):
    """
    Get complete session data for a specific session.

    **Required Privileges:**
    - SYSTEM: Full access to complete session data
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session

    **Response Format:**
    - Complete session data including all entities (drones, targets, obstacles, environment, tasks)
    - 404 Not Found if session with given ID does not exist

    **Notes:**
    - Convenience endpoint equivalent to GET /sessions/{session_id}?data=true
    """
    session_data = session_controller.get_session(session_id, data=True)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    return session_data

@app.get("/sessions/current/screenshot", tags=["Sessions"])
async def get_current_session_screenshot(
    format: str = "png",
    width: int = 1024,
    height: int = 768,
    center_x: Optional[float] = None,
    center_y: Optional[float] = None,
    scale_px_per_meter: Optional[float] = None,
    show_status: bool = False,
    show_label: bool = True,
    _role: UserRole = Depends(require_agent)
):
    """
    Generate a visual screenshot of the current active session.

    **Required Privileges:**
    - AGENT: Can generate screenshots of current session
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - format: Output format (default: 'png'). Valid options:
      * 'png' - Portable Network Graphics (image/png)
      * 'jpg' or 'jpeg' - JPEG Image (image/jpeg)
      * 'pdf' - Portable Document Format (application/pdf)
      * 'svg' - Scalable Vector Graphics (image/svg+xml)
      * 'eps' - Encapsulated PostScript (application/postscript)
    - width: Image width in pixels (default: 1024)
    - height: Image height in pixels (default: 768)
    - center_x: Optional canvas center X coordinate in meters (auto-centered if not specified)
    - center_y: Optional canvas center Y coordinate in meters (auto-centered if not specified)
    - scale_px_per_meter: Optional zoom level - pixels per meter (auto-scale if not specified)
    - show_status: Boolean flag to include additional overlay information (default: false):
      * Drone path traces
      * Area coverage heatmaps
      * Reached target markers
      * Status bar with session statistics
    - show_label: Boolean flag to include object labels for drones, targets, and obstacles (default: true)

    **Response Format:**
    - Binary image/file data with appropriate Content-Type header
    - 400 Bad Request if invalid format specified
    - 404 Not Found if no current session or generation fails

    **Examples:**
    - GET /sessions/current/screenshot - Default PNG at 1024x768
    - GET /sessions/current/screenshot?format=svg&show_status=true - Vector with status overlays
    - GET /sessions/current/screenshot?width=1920&height=1080&format=jpg - HD JPEG
    """
    fmt = format.lower()
    if fmt not in ("png", "jpg", "jpeg", "pdf", "svg", "eps"):
        raise HTTPException(status_code=400, detail="Invalid format. Use png, jpg, jpeg, pdf, svg, or eps.")

    img_bytes = session_controller.generate_session_screenshot(
        session_id=None,
        fmt=fmt,
        width=width,
        height=height,
        center_x=center_x,
        center_y=center_y,
        scale_px_per_meter=scale_px_per_meter,
        show_status=show_status,
        show_label=show_label,
    )
    if img_bytes is None or len(img_bytes) == 0:
        raise HTTPException(status_code=404, detail="No current session found or screenshot generation failed")

    media_type = (
        "image/png" if fmt == "png" else
        "image/jpeg" if fmt in ("jpg", "jpeg") else
        "application/pdf" if fmt == "pdf" else
        "image/svg+xml" if fmt == "svg" else
        "application/postscript"
    )
    return Response(content=img_bytes, media_type=media_type)

@app.get("/sessions/{session_id}/screenshot", tags=["Sessions"])
async def get_session_screenshot(
    session_id: str,
    format: str = "png",
    width: int = 1024,
    height: int = 768,
    center_x: Optional[float] = None,
    center_y: Optional[float] = None,
    scale_px_per_meter: Optional[float] = None,
    show_status: bool = False,
    show_label: bool = True,
    _role: UserRole = Depends(require_system)
):
    """
    Generate a visual screenshot of a specific saved session.

    **Required Privileges:**
    - SYSTEM: Can generate screenshots of historical sessions
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Target session ID (path parameter, required)
    - format: Output format (default: 'png'). Valid options:
      * 'png' - Portable Network Graphics (image/png)
      * 'jpg' or 'jpeg' - JPEG Image (image/jpeg)
      * 'pdf' - Portable Document Format (application/pdf)
      * 'svg' - Scalable Vector Graphics (image/svg+xml)
      * 'eps' - Encapsulated PostScript (application/postscript)
    - width: Image width in pixels (default: 1024)
    - height: Image height in pixels (default: 768)
    - center_x: Optional canvas center X coordinate in meters (auto-centered if not specified)
    - center_y: Optional canvas center Y coordinate in meters (auto-centered if not specified)
    - scale_px_per_meter: Optional zoom level - pixels per meter (auto-scale if not specified)
    - show_status: Boolean flag to include additional overlay information (default: false):
      * Drone path traces from the session
      * Area coverage heatmaps
      * Reached target markers
      * Status bar with session statistics
    - show_label: Boolean flag to include object labels for drones, targets, and obstacles (default: true)

    **Response Format:**
    - Binary image/file data with appropriate Content-Type header
    - 400 Bad Request if invalid format specified
    - 404 Not Found if session doesn't exist or generation fails

    **Examples:**
    - GET /sessions/{session_id}/screenshot - Default PNG at 1024x768
    - GET /sessions/{session_id}/screenshot?format=pdf&show_status=true - PDF report with status
    """
    fmt = format.lower()
    if fmt not in ("png", "jpg", "jpeg", "pdf", "svg", "eps"):
        raise HTTPException(status_code=400, detail="Invalid format. Use png, jpg, jpeg, pdf, svg, or eps.")

    # Verify session exists
    session = session_controller.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    img_bytes = session_controller.generate_session_screenshot(
        session_id=session_id,
        fmt=fmt,
        width=width,
        height=height,
        center_x=center_x,
        center_y=center_y,
        scale_px_per_meter=scale_px_per_meter,
        show_status=show_status,
        show_label=show_label,
    )
    if img_bytes is None or len(img_bytes) == 0:
        raise HTTPException(status_code=404, detail="Screenshot generation failed")

    media_type = (
        "image/png" if fmt == "png" else
        "image/jpeg" if fmt in ("jpg", "jpeg") else
        "application/pdf" if fmt == "pdf" else
        "image/svg+xml" if fmt == "svg" else
        "application/postscript"
    )
    return Response(content=img_bytes, media_type=media_type)


# Session Tracking API Routes
def _get_recent_command_history(session_obj: Session, limit: int) -> List[Dict[str, Any]]:
    """Return the most recent command history entries, capped at 1000."""
    command_history = session_obj.command_history
    capped_limit = min(limit, 1000)
    return command_history[-capped_limit:] if len(command_history) > capped_limit else command_history


def _get_recent_request_history(
    session_obj: Session,
    limit: Optional[int],
    agent_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return recent request history entries, or all entries when limit is None."""
    if limit is not None and limit <= 0:
        return []

    request_history = session_obj.request_history
    if agent_id is None:
        selected = request_history if limit is None else request_history[-limit:]
        return [
            session_obj.normalize_request_history_record(record)
            for record in selected
        ]

    selected = []
    for record in reversed(request_history):
        normalized = session_obj.normalize_request_history_record(record)
        if (
            normalized.get("client_privilege") == UserRole.AGENT.name
            and normalized.get("agent_id") == agent_id
        ):
            selected.append(normalized)
            if limit is not None and len(selected) >= limit:
                break

    selected.reverse()
    return selected


def _clear_request_history_response(session_obj: Session) -> Dict[str, Any]:
    """Clear runtime request history and return a compact summary."""
    cleared_count = session_controller.clear_request_history(session_obj.id)
    if cleared_count is None:
        cleared_count = 0
    return {
        "cleared": True,
        "session_id": session_obj.id,
        "cleared_count": cleared_count,
    }


@app.get("/sessions/current/request-history", tags=["Session Tracking"])
async def get_current_session_request_history(
    request: Request,
    limit: Optional[int] = None,
    _role: UserRole = Depends(require_current_request_history_role),
):
    """
    Get HTTP request history for the current active session.

    The history contains all retained session-associated requests by default.
    The request that retrieves history is recorded after its response is
    produced and therefore appears only in subsequent history queries.
    """
    session_obj = session_controller.get_current_session_ref()
    if session_obj is None:
        raise HTTPException(status_code=404, detail="No current session found")

    agent_id = None
    if _role == UserRole.AGENT:
        agent_id = RequestLoggingMiddleware.normalize_agent_id(
            request.headers.get(RequestLoggingMiddleware.AGENT_ID_HEADER)
        )

    return {
        "request_history": _get_recent_request_history(
            session_obj,
            limit,
            agent_id=agent_id,
        )
    }


@app.get("/sessions/{session_id}/request-history", tags=["Session Tracking"])
async def get_session_request_history(session_id: str, limit: Optional[int] = None, _role: UserRole = Depends(require_system)):
    """Get HTTP request history for a specific session."""
    session_obj = session_controller.get_session_ref(session_id)
    if session_obj is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"request_history": _get_recent_request_history(session_obj, limit)}


@app.delete("/sessions/current/request-history", tags=["Session Tracking"])
async def clear_current_session_request_history(_role: UserRole = Depends(require_system)):
    """Clear HTTP request history for the current active session."""
    session_obj = session_controller.get_current_session_ref()
    if session_obj is None:
        raise HTTPException(status_code=404, detail="No current session found")

    return _clear_request_history_response(session_obj)


@app.delete("/sessions/{session_id}/request-history", tags=["Session Tracking"])
async def clear_session_request_history(session_id: str, _role: UserRole = Depends(require_system)):
    """Clear HTTP request history for a specific session."""
    session_obj = session_controller.get_session_ref(session_id)
    if session_obj is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return _clear_request_history_response(session_obj)


@app.get("/sessions/current/command-history", tags=["Session Tracking"])
async def get_current_session_command_history(limit: int = 100, _role: UserRole = Depends(require_system)):
    """
    Get the command execution history for the current active session.

    **Required Privileges:**
    - SYSTEM: Full access to command history
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - limit: Query parameter - maximum number of recent commands to return (default: 100, max: 1000)

    **Response Format:**
    - Object with "command_history" array containing timestamped command records
    - Each record includes: command name, parameters, timestamp, drone ID, success status
    - 404 Not Found if no current session is active
    """
    session_obj = session_controller.get_current_session_ref()
    if session_obj is None:
        raise HTTPException(status_code=404, detail="No current session found")

    return {"command_history": _get_recent_command_history(session_obj, limit)}


@app.get("/sessions/{session_id}/command-history", tags=["Session Tracking"])
async def get_session_command_history(session_id: str, limit: int = 100, _role: UserRole = Depends(require_system)):
    """
    Get the command execution history for a session.

    **Required Privileges:**
    - SYSTEM: Full access to command history
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session
    - limit: Query parameter - maximum number of recent commands to return (default: 100, max: 1000)

    **Response Format:**
    - Object with "command_history" array containing timestamped command records
    - Each record includes: command name, parameters, timestamp, drone ID, success status
    - 404 Not Found if session with given ID does not exist
    """
    session_obj = session_controller.get_session_ref(session_id)
    if session_obj is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"command_history": _get_recent_command_history(session_obj, limit)}


@app.get("/sessions/{session_id}/status-history", tags=["Session Tracking"])
async def get_session_status_history(session_id: str, drone_id: Optional[str] = None, _role: UserRole = Depends(require_system)):
    """
    Get drone status change history for a session.

    **Required Privileges:**
    - SYSTEM: Full access to status history
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session
    - drone_id: Query parameter - optional filter to get history for specific drone only

    **Response Format:**
    - Object with "status_history" key:
      * If drone_id provided: {drone_id: [status_change_records]}
      * If no drone_id: {drone_id_1: [...], drone_id_2: [...], ...}
    - Each status change includes: previous status, new status, timestamp, position
    - 404 Not Found if session with given ID does not exist
    """
    session = session_controller.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session_id in session_controller.sessions:
        session_obj = session_controller.sessions[session_id]
        if drone_id:
            # Return history for specific drone
            return {"status_history": {drone_id: session_obj.status_history.get(drone_id, [])}}
        else:
            # Return all status history
            return {"status_history": session_obj.status_history}

    return {"status_history": {}}


@app.get("/sessions/{session_id}/target-reaches", tags=["Session Tracking"])
async def get_session_target_reaches(session_id: str, _role: UserRole = Depends(require_system)):
    """
    Get target reach tracking data for a session.

    **Required Privileges:**
    - SYSTEM: Full access to tracking data
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session

    **Response Format:**
    - Object with:
      * target_reaches: Detailed records of each target reach event
      * summary: Summary statistics including total reached, not reached, first/last reach times
    - 404 Not Found if session with given ID does not exist

    **Notes:**
    - Records include: target ID, drone ID, timestamp, position at reach time
    """
    session_controller.sync_session_snapshot(session_id)
    session = session_controller.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session_id in session_controller.sessions:
        session_obj = session_controller.sessions[session_id]
        summary = session_obj.get_target_reach_summary()
        return {
            "target_reaches": session_obj.get_target_reach_details(),
            "summary": summary
        }

    return {"target_reaches": {}, "summary": {}}


@app.get("/sessions/{session_id}/moving-target-tracking", tags=["Session Tracking"])
async def get_session_moving_target_tracking(session_id: str, _role: UserRole = Depends(require_system)):
    """
    Get moving target tracking data for a session.

    **Required Privileges:**
    - SYSTEM: Full access to tracking data
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session

    **Response Format:**
    - Object with "moving_target_tracking" key containing:
      * For each moving target: position history, tracking drones, tracking success metrics
    - 404 Not Found if session with given ID does not exist

    **Notes:**
    - Useful for analyzing how well drones track moving targets over time
    """
    session_controller.sync_session_snapshot(session_id)
    session = session_controller.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session_id in session_controller.sessions:
        session_obj = session_controller.sessions[session_id]
        return {
            "moving_target_tracking": session_obj.get_moving_target_tracking_details(),
        }

    return {"moving_target_tracking": {}}


@app.get("/sessions/{session_id}/area-coverage", tags=["Session Tracking"])
async def get_session_area_coverage(session_id: str, _role: UserRole = Depends(require_system)):
    """
    Get area coverage tracking data for a session.

    **Required Privileges:**
    - SYSTEM: Full access to tracking data
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session

    **Response Format:**
    - Object with:
      * area_coverage: Grid-based coverage data with visit counts per cell
      * summary: Statistics including total area, covered area, coverage percentage
    - 404 Not Found if session with given ID does not exist

    **Notes:**
    - Used for search and surveillance mission analysis
    - Coverage is tracked in a grid cell system
    """
    session_controller.sync_session_snapshot(session_id)
    session = session_controller.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session_id in session_controller.sessions:
        session_obj = session_controller.sessions[session_id]
        summary = session_obj.get_area_coverage_summary()
        return {
            "area_coverage": session_obj.area_coverage,
            "summary": summary
        }

    return {"area_coverage": {}, "summary": {}}


@app.get("/sessions/current/task-progress", tags=["Session Tracking"])
async def get_current_session_task_progress(_role: UserRole = Depends(require_agent)):
    """
    Get task progress metrics for the current active session.

    **Required Privileges:**
    - AGENT: Can access task progress
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Response Format:**
    - Progress metrics based on session task_type:
      * area_search/area_assignment_and_patrol: percentage of area explored (90% = complete)
      * target_assignment: percentage of targets visited at least once (100% = complete)
      * target_tracking: percentage of targets currently tracked + visit completion
      * others: no specific progress tracking
    - 404 Not Found if no current session is active
    """
    session_controller.sync_current_session_snapshot()
    current_session = session_controller.get_current_session()
    if not current_session:
        raise HTTPException(status_code=404, detail="No current session found")

    return _get_task_progress_response(current_session["id"])


@app.get("/sessions/{session_id}/task-progress", tags=["Session Tracking"])
async def get_session_task_progress(session_id: str, _role: UserRole = Depends(require_system)):
    """
    Get task progress metrics for a specific session.

    **Required Privileges:**
    - SYSTEM: Full access to progress metrics
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session

    **Response Format:**
    - Progress metrics based on session task_type:
      * area_search/area_assignment_and_patrol: percentage of area explored (90% = complete)
      * target_assignment: percentage of targets visited at least once (100% = complete)
      * target_tracking: percentage of targets currently tracked + visit completion
      * others: no specific progress tracking
    - 404 Not Found if session with given ID does not exist
    """
    session_controller.sync_session_snapshot(session_id)
    session = session_controller.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return _get_task_progress_response(session_id)


@app.get("/sessions/current/tasks", response_model=List[TaskResponse], tags=["Tasks"])
async def get_current_session_tasks(_role: UserRole = Depends(require_agent)):
    """
    Get all tasks in the current active session.

    **Required Privileges:**
    - AGENT: Can access task list (sensitive fields masked)
    - USER, SYSTEM, ADMIN: Inherit access with appropriate masking

    **Response Format:**
    - Array of TaskResponse objects in order
    - Tasks include: id, name, description, status (is_passed), difficulty
    - For AGENT/USER: sensitive fields (related_apis, commands, execution_check_apis) are masked
    - 404 Not Found if no current session is active
    """
    session_controller.sync_current_session_snapshot()
    current_session = session_controller.get_current_session()
    if not current_session:
        raise HTTPException(status_code=404, detail="No current session found")

    tasks = session_controller.get_all_tasks(current_session["id"])
    # tasks should never be None if current_session exists, but return empty list if it happens
    if tasks is None:
        return []
    return [_mask_task_for_role(task, _role) for task in tasks]


@app.get("/sessions/current/tasks/next", response_model=TaskResponse, tags=["Tasks"])
async def get_current_session_next_task(_role: UserRole = Depends(require_agent)):
    """
    Get the next pending (not completed) task in the current active session.

    **Required Privileges:**
    - AGENT: Can access next task (sensitive fields masked)
    - USER, SYSTEM, ADMIN: Inherit access with appropriate masking

    **Response Format:**
    - Single TaskResponse object (first pending task in order)
    - 404 Not Found if no current session or no pending tasks
    """
    session_controller.sync_current_session_snapshot()
    current_session = session_controller.get_current_session()
    if not current_session:
        raise HTTPException(status_code=404, detail="No current session found")

    task = session_controller.get_next_pending_task(current_session["id"])
    if not task:
        raise HTTPException(status_code=404, detail="No pending task found")
    return _mask_task_for_role(task, _role)


@app.get("/sessions/current/tasks/{task_id}/check", tags=["Tasks"])
async def check_current_session_task(
    task_id: str,
    since_timestamp: Optional[float] = None,
    _role: UserRole = Depends(require_agent)
):
    """
    Evaluate a task's completion criteria and mark it as passed if successful.

    **Required Privileges:**
    - AGENT: Can check task completion (sensitive details masked)
    - USER, SYSTEM, ADMIN: Inherit access (SYSTEM/ADMIN see full evaluation details)

    **Request Parameters:**
    - task_id: Unique identifier of the task to check
    - since_timestamp: Optional timestamp to limit evaluation to events after this time

    **Response Format:**
    - Object with:
      * result: Boolean indicating if task passed
      * task: Updated TaskResponse with is_passed status
      * details: Full evaluation details (SYSTEM/ADMIN only)
    - 404 Not Found if no current session or task not found

    **Notes:**
    - Evaluates the task's execution_check_apis logical tree
    - If no checks defined, automatically marks as passed
    - If check passes, automatically sets is_passed = True on the task
    """
    session_controller.sync_current_session_snapshot()
    current_session = session_controller.get_current_session()
    if not current_session:
        raise HTTPException(status_code=404, detail="No current session found")

    task = session_controller.get_task(current_session["id"], task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_node = task.get("execution_check_apis")
    if not check_node:
        task = session_controller.update_task(current_session["id"], task_id, {"is_passed": True}) or task
        return {"result": True, "task": _mask_task_for_role(task, _role)}

    evaluation = await _evaluate_check_node(check_node, since_timestamp=since_timestamp)
    result = bool(evaluation.get("result"))

    if result:
        task = session_controller.update_task(current_session["id"], task_id, {"is_passed": True}) or task

    response: Dict[str, Any] = {"result": result, "task": _mask_task_for_role(task, _role)}
    if _role in (UserRole.SYSTEM, UserRole.ADMIN):
        response["details"] = evaluation
    return response


@app.get("/sessions/current/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def get_current_session_task(task_id: str, _role: UserRole = Depends(require_agent)):
    """
    Get a specific task from the current active session.

    **Required Privileges:**
    - AGENT: Can access task (sensitive fields masked)
    - USER, SYSTEM, ADMIN: Inherit access with appropriate masking

    **Request Parameters:**
    - task_id: Unique identifier of the task

    **Response Format:**
    - TaskResponse object
    - 404 Not Found if no current session or task not found
    """
    current_session = session_controller.get_current_session()
    if not current_session:
        raise HTTPException(status_code=404, detail="No current session found")

    task = session_controller.get_task(current_session["id"], task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _mask_task_for_role(task, _role)


@app.get("/sessions/{session_id}/tasks", response_model=List[TaskResponse], tags=["Tasks"])
async def get_session_tasks(session_id: str, _role: UserRole = Depends(require_user)):
    """
    Get all tasks in a specific session.

    **Required Privileges:**
    - USER: Can access task list (sensitive fields masked)
    - SYSTEM, ADMIN: Inherit access with appropriate masking

    **Request Parameters:**
    - session_id: Unique identifier of the session

    **Response Format:**
    - Array of TaskResponse objects in order
    - 404 Not Found if session with given ID does not exist
    """
    tasks = session_controller.get_all_tasks(session_id)
    if tasks is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return [_mask_task_for_role(task, _role) for task in tasks]


@app.post("/sessions/{session_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, tags=["Tasks"])
async def create_task(session_id: str, task: TaskRequest, _role: UserRole = Depends(require_system)):
    """
    Create a new task in a session.

    **Required Privileges:**
    - SYSTEM: Can create tasks
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session
    - task: Request body with task details:
      * name: Task name (required)
      * content: Main task content
      * content_aliases: Alternative content variations
      * description: Detailed description
      * creator: Creator name (defaults to role name)
      * originated_from: Origin source
      * difficulty: Task difficulty rating
      * related_apis: List of related API endpoints
      * execution_check_apis: Logical check tree for automatic completion
      * commands: List of commands associated with the task

    **Response Format:**
    - Created TaskResponse object with generated ID
    - 404 Not Found if session with given ID does not exist
    """
    creator_name = task.creator or _role.value
    origin = task.originated_from or creator_name
    created_task = session_controller.create_task(
        session_id=session_id,
        name=task.name,
        content=task.content,
        content_aliases=task.content_aliases,
        description=task.description,
        creator=creator_name,
        originated_from=origin,
        difficulty=task.difficulty,
        related_apis=[api.model_dump() for api in task.related_apis],
        execution_check_apis=task.execution_check_apis.model_dump(exclude_unset=True) if task.execution_check_apis else None,
        commands=task.commands
    )
    if not created_task:
        raise HTTPException(status_code=404, detail="Session not found")
    return created_task


@app.get("/sessions/{session_id}/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def get_task(session_id: str, task_id: str, _role: UserRole = Depends(require_user)):
    """
    Get a specific task from a session.

    **Required Privileges:**
    - USER: Can access task (sensitive fields masked)
    - SYSTEM, ADMIN: Inherit access with appropriate masking

    **Request Parameters:**
    - session_id: Unique identifier of the session
    - task_id: Unique identifier of the task

    **Response Format:**
    - TaskResponse object
    - 404 Not Found if session or task not found
    """
    task = session_controller.get_task(session_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or session not found")
    return _mask_task_for_role(task, _role)


@app.put("/sessions/{session_id}/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def update_task(session_id: str, task_id: str, task_update: TaskUpdateRequest, _role: UserRole = Depends(require_system)):
    """
    Update a task's properties.

    **Required Privileges:**
    - SYSTEM: Can modify tasks
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session
    - task_id: Unique identifier of the task
    - task_update: Request body with fields to update (all optional)

    **Response Format:**
    - Updated TaskResponse object
    - 400 Bad Request if no valid fields provided
    - 404 Not Found if session or task not found
    """
    updates = {k: v for k, v in task_update.model_dump().items() if v is not None}

    if "related_apis" in updates and updates["related_apis"] is not None:
        updates["related_apis"] = [api for api in updates["related_apis"]]
    if "execution_check_apis" in updates and updates["execution_check_apis"] is not None:
        updates["execution_check_apis"] = task_update.execution_check_apis.model_dump(exclude_defaults=True)

    if not updates:
        raise HTTPException(status_code=400, detail="No valid updates provided")

    updated_task = session_controller.update_task(session_id, task_id, updates)
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found or session not found")
    return updated_task


@app.delete("/sessions/{session_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tasks"])
async def delete_task(session_id: str, task_id: str, _role: UserRole = Depends(require_system)):
    """
    Delete a task from a session.

    **Required Privileges:**
    - SYSTEM: Can delete tasks
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session
    - task_id: Unique identifier of the task

    **Response Format:**
    - 204 No Content on successful deletion
    - 404 Not Found if session or task not found
    """
    success = session_controller.delete_task(session_id, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or session not found")
    return None


@app.post("/sessions/{session_id}/tasks/{task_id}/mark-done", response_model=TaskResponse, tags=["Tasks"])
async def mark_task_done(session_id: str, task_id: str, _role: UserRole = Depends(require_system)):
    """
    Manually mark a task as completed.

    **Required Privileges:**
    - SYSTEM: Can mark task status
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session
    - task_id: Unique identifier of the task

    **Response Format:**
    - Updated TaskResponse with is_passed = True
    - 404 Not Found if session or task not found
    """
    updated_task = session_controller.mark_task_done(session_id, task_id)
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found or session not found")
    return updated_task


@app.post("/sessions/{session_id}/tasks/{task_id}/mark-pending", response_model=TaskResponse, tags=["Tasks"])
async def mark_task_pending(session_id: str, task_id: str, _role: UserRole = Depends(require_system)):
    """
    Manually mark a task as pending (not completed).

    **Required Privileges:**
    - SYSTEM: Can mark task status
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session
    - task_id: Unique identifier of the task

    **Response Format:**
    - Updated TaskResponse with is_passed = False
    - 404 Not Found if session or task not found
    """
    updated_task = session_controller.mark_task_pending(session_id, task_id)
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found or session not found")
    return updated_task


@app.post("/sessions/current/tasks/{task_id}/mark-done", response_model=TaskResponse, tags=["Tasks"])
async def mark_current_session_task_done(task_id: str, _role: UserRole = Depends(require_agent)):
    """
    Manually mark a task as completed in the current session.

    **Required Privileges:**
    - AGENT: Can mark task status in current session
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - task_id: Unique identifier of the task

    **Response Format:**
    - Updated TaskResponse with is_passed = True
    - 404 Not Found if no current session or task not found
    """
    current_session = session_controller.get_current_session()
    if not current_session:
        raise HTTPException(status_code=404, detail="No current session found")

    updated_task = session_controller.mark_task_done(current_session["id"], task_id)
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated_task


@app.post("/sessions/current/tasks/{task_id}/mark-pending", response_model=TaskResponse, tags=["Tasks"])
async def mark_current_session_task_pending(task_id: str, _role: UserRole = Depends(require_agent)):
    """
    Manually mark a task as pending (not completed) in the current session.

    **Required Privileges:**
    - AGENT: Can mark task status in current session
    - USER, SYSTEM, ADMIN: Inherit access from role hierarchy

    **Request Parameters:**
    - task_id: Unique identifier of the task

    **Response Format:**
    - Updated TaskResponse with is_passed = False
    - 404 Not Found if no current session or task not found
    """
    current_session = session_controller.get_current_session()
    if not current_session:
        raise HTTPException(status_code=404, detail="No current session found")

    updated_task = session_controller.mark_task_pending(current_session["id"], task_id)
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated_task


@app.post("/sessions/{session_id}/tasks/swap", response_model=List[TaskResponse], tags=["Tasks"])
async def swap_tasks(session_id: str, swap_request: TaskSwapRequest, _role: UserRole = Depends(require_system)):
    """
    Swap the order of two tasks in a session.

    **Required Privileges:**
    - SYSTEM: Can reorder tasks
    - ADMIN: Inherits access from role hierarchy

    **Request Parameters:**
    - session_id: Unique identifier of the session
    - swap_request: Request body with:
      * task_id_1: First task to swap
      * task_id_2: Second task to swap

    **Response Format:**
    - List of all tasks in the new order
    - 404 Not Found if session or one/both tasks not found
    """
    swapped_tasks = session_controller.swap_tasks(
        session_id=session_id,
        task_id_1=swap_request.task_id_1,
        task_id_2=swap_request.task_id_2
    )
    if not swapped_tasks:
        raise HTTPException(
            status_code=404,
            detail="Session not found or one or both tasks not found"
        )
    return swapped_tasks


# ==================== Check Endpoints (ADMIN only) ====================

# Helper for executing check nodes
async def _evaluate_check_node(
    node: Dict[str, Any] | ExecutionCheckNode,
    since_timestamp: Optional[float] = None
) -> Dict[str, Any]:
    """Recursively evaluate an execution check node and return detailed results."""
    if hasattr(node, "model_dump"):
        data = node.model_dump()
    else:
        data = node
    
    # Branch node logic
    checks = data.get("checks")
    if checks:
        results_details = [await _evaluate_check_node(c, since_timestamp=since_timestamp) for c in checks]
        results_bools = [r["result"] for r in results_details]
        
        logic = str(data.get("logic", "and")).lower()
        
        if logic == "or":
            outcome = any(results_bools)
        elif logic == "not":
            outcome = not all(results_bools)
        else: # "and"
            outcome = all(results_bools)
            
        return {
            "result": outcome,
            "type": "logic",
            "logic": logic,
            "checks": results_details
        }
            
    # Leaf node logic
    endpoint = data.get("endpoint")
    if endpoint:
        # Find the endpoint function
        func = None
        for route in app.routes:
            if getattr(route, "path", "") == endpoint:
                func = route.endpoint
                break
        
        if not func:
            return {
                "result": False,
                "type": "error",
                "endpoint": endpoint,
                "error": "Endpoint not found"
            }
            
        params = data.get("parameters", {}).copy()
        
        try:
            # Bind parameters
            sig = inspect.signature(func)
            if (
                since_timestamp is not None
                and "since_timestamp" in sig.parameters
                and "since_timestamp" not in params
            ):
                params["since_timestamp"] = since_timestamp
            call_args = {}
            for name, param in sig.parameters.items():
                if name == "_role":
                    call_args[name] = UserRole.ADMIN # System performs check
                elif name in params:
                    call_args[name] = params[name]
                elif param.default != inspect.Parameter.empty:
                    pass # Use default
                elif name == "session_id":
                    call_args[name] = session_controller.current_session_id
            
            # Call the check function
            if inspect.iscoroutinefunction(func):
                response = await func(**call_args)
            else:
                response = func(**call_args)
                
            # Response is a dict with "result" boolean
            check_result = response.get("result", False)
            
            expected = data.get("expect")
            if expected is not None:
                final_result = (check_result == expected)
            else:
                final_result = check_result
            
            return {
                "result": final_result,
                "type": "check",
                "endpoint": endpoint,
                "parameters": params,
                "expected": expected,
                "check_response": response
            }
            
        except Exception as e:
            return {
                "result": False,
                "type": "error",
                "endpoint": endpoint,
                "error": str(e)
            }

    return {"result": True, "type": "empty"} # Default for empty node


GROUND_STATUSES = {
    DroneStatus.IDLE.value,
    DroneStatus.READY.value,
    DroneStatus.LANDING.value
}
HOVER_STATUSES = {DroneStatus.HOVERING.value}


def _build_check_response(result: bool, value: Any, **extra_fields: Any) -> Dict[str, Any]:
    """Standardize check responses with required keys."""
    payload = {"result": bool(result), "value": value}
    payload.update(extra_fields)
    return payload


def _get_session_or_404(session_id: Optional[str] = None) -> Tuple[str, Session]:
    """Resolve a session ID to a Session object or raise 404."""
    target_session_id = session_id or session_controller.current_session_id
    if not target_session_id:
        raise HTTPException(status_code=404, detail="No current session found")

    session_obj = session_controller.sessions.get(target_session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail=f"Session {target_session_id} not found")

    return target_session_id, session_obj


def _get_session_distance(pos1: Any, pos2: Any) -> float:
    """Calculate distance between two points, respecting session's is_distance_3d flag."""
    is_3d = False
    if session_controller and session_controller.current_session_id:
        curr_session = session_controller.sessions.get(session_controller.current_session_id)
        if curr_session:
            is_3d = getattr(curr_session, "is_distance_3d", False)
    
    if is_3d:
        return euclidean_distance(pos1, pos2)
    else:
        return distance_2d(pos1, pos2)


def _get_drone_or_404(drone_id: str) -> Dict[str, Any]:
    """Fetch a drone or raise 404."""
    drone = drone_controller.get_drone(drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail=f"Drone {drone_id} not found")
    return drone


def _get_target_or_404(target_id: str) -> Dict[str, Any]:
    """Fetch a target or raise 404."""
    target = target_controller.get_target(target_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Target {target_id} not found")
    return target


def _get_obstacle_or_404(obstacle_id: str) -> Dict[str, Any]:
    """Fetch an obstacle or raise 404."""
    obstacle = obstacle_controller.get_obstacle(obstacle_id)
    if not obstacle:
        raise HTTPException(status_code=404, detail=f"Obstacle {obstacle_id} not found")
    return obstacle


def _is_drone_on_ground(drone: Dict[str, Any], tolerance: float) -> bool:
    """Check if a drone is effectively on the ground."""
    altitude = drone.get("position", {}).get("z", 0.0)
    status = drone.get("status")
    return altitude <= tolerance and status in GROUND_STATUSES


def _is_drone_hovering(drone: Dict[str, Any], tolerance: float) -> bool:
    """Check if a drone is hovering above ground."""
    altitude = drone.get("position", {}).get("z", 0.0)
    status = drone.get("status")
    return altitude > tolerance and status in HOVER_STATUSES


def _heading_delta(current: float, expected: float) -> float:
    """Smallest absolute delta between two headings."""
    diff = (current - expected + 180) % 360 - 180
    return abs(diff)


# Helper functions for history status checking
def _get_drone_history(drone_id: str) -> List[Dict[str, Any]]:
    """Get history_status from drone object

    Args:
        drone_id: ID of the drone

    Returns:
        List of history records

    Raises:
        HTTPException: If drone not found
    """
    drone_obj = drone_controller.drones.get(drone_id)
    if not drone_obj:
        raise HTTPException(status_code=404, detail=f"Drone {drone_id} not found")
    return drone_obj.get_all_history()


def _filter_history_by_timestamp(history: List[Dict[str, Any]], since_timestamp: Optional[float]) -> List[Dict[str, Any]]:
    """Filter history events after a certain timestamp

    Args:
        history: List of history records
        since_timestamp: Timestamp to filter from (None = no filter)

    Returns:
        Filtered list of history records
    """
    if since_timestamp is None:
        return history
    return [h for h in history if h.get("timestamp", 0) >= since_timestamp]


def _filter_history_by_type(history: List[Dict[str, Any]], event_type: str) -> List[Dict[str, Any]]:
    """Filter history by event type

    Args:
        history: List of history records
        event_type: Type to filter by ("waypoint", "status_event", "other")

    Returns:
        Filtered list of history records
    """
    return [h for h in history if h.get("type") == event_type]


def _filter_history_by_event(history: List[Dict[str, Any]], event_name: str) -> List[Dict[str, Any]]:
    """Filter history by event name

    Args:
        history: List of history records
        event_name: Event name to filter by (e.g., "move_to", "take_photo")

    Returns:
        Filtered list of history records
    """
    return [h for h in history if h.get("event") == event_name]


def _calculate_distance_from_history(history: List[Dict[str, Any]]) -> float:
    """Calculate total distance traveled from waypoint history

    Args:
        history: List of history records (should be waypoint types)

    Returns:
        Total distance in meters
    """
    total = 0.0
    for h in history:
        if h.get("type") == "waypoint":
            start = h.get("start_position", {})
            end = h.get("position", {})
            if start and end:
                total += _get_session_distance(start, end)
    return total


def _calculate_directed_distance_from_history(history: List[Dict[str, Any]], heading: float, tolerance: float) -> float:
    """Calculate total distance traveled in a specific heading direction from waypoint history

    Args:
        history: List of history records (should be waypoint types)
        heading: Target heading in degrees
        tolerance: Tolerance in degrees

    Returns:
        Total distance in meters
    """
    total = 0.0
    for h in history:
        if h.get("type") == "waypoint":
            start = h.get("start_position", {})
            end = h.get("position", {})
            if start and end:
                dx = end.get("x", 0.0) - start.get("x", 0.0)
                dy = end.get("y", 0.0) - start.get("y", 0.0)

                # Skip if no movement (or very small to avoid noise)
                if abs(dx) < 0.001 and abs(dy) < 0.001:
                    continue

                # Calculate heading of movement
                angle_rad = math.atan2(dx, dy)
                move_heading = math.degrees(angle_rad)
                if move_heading < 0:
                    move_heading += 360.0

                if _heading_delta(move_heading, heading) <= tolerance:
                    total += _get_session_distance(start, end)
    return total


def _position_within_tolerance(pos1: Dict[str, float], pos2: Dict[str, float],
                               tolerance: float, check_z: bool = True) -> bool:
    """Check if two positions are within tolerance

    Args:
        pos1: First position {x, y, z}
        pos2: Second position {x, y, z}
        tolerance: Maximum distance in meters
        check_z: Whether to include Z coordinate in distance calculation

    Returns:
        True if within tolerance, False otherwise
    """
    if check_z:
        return _get_session_distance(pos1, pos2) <= tolerance
    else:
        return distance_2d(pos1, pos2) <= tolerance


def _filter_timestamps_since(timestamps: List[float], since_timestamp: Optional[float]) -> List[float]:
    """Filter timestamp values with the same inclusive semantics as history events."""
    if since_timestamp is None:
        return [float(ts) for ts in timestamps]
    return [float(ts) for ts in timestamps if float(ts) >= since_timestamp]


def _collect_target_reach_drone_ids(
    session_obj: Session,
    target_id: str,
    since_timestamp: Optional[float] = None
) -> set[str]:
    """Gather all drones that have reached a target."""
    reached_by = set()

    for drone_id, targets in session_obj.target_reaches.items():
        if target_id in targets and _filter_timestamps_since(targets[target_id], since_timestamp):
            reached_by.add(drone_id)

    return reached_by


def _filter_tracking_periods_since(
    periods: List[Dict[str, Any]],
    since_timestamp: Optional[float]
) -> List[Dict[str, Any]]:
    """Return tracking periods clipped to the requested timestamp boundary."""
    if since_timestamp is None:
        return periods

    filtered_periods = []
    for period in periods:
        start_at = float(period.get("start_at", 0.0))
        end_at = float(period.get("end_at", 0.0))
        if end_at < since_timestamp:
            continue
        clipped_period = period.copy()
        clipped_period["start_at"] = max(start_at, since_timestamp)
        filtered_periods.append(clipped_period)
    return filtered_periods


@app.get("/check/drone_position", tags=["Checks"])
async def check_drone_position(
    drone_id: str,
    x: float,
    y: float,
    z: Optional[float] = None,
    tolerance: float = 1.0,
    _role: UserRole = Depends(require_admin)
):
    """Check if a drone is at a given position.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - x: Expected X coordinate
    - y: Expected Y coordinate
    - z: Expected Z coordinate (altitude). If not provided, only checks X and Y
    - tolerance: Acceptable distance tolerance in meters (default: 1.0)

    **Response Format:**
    - Object with result boolean, distance value, drone_id, current_position, expected_position, and tolerance

    **Notes:**
    - If z is provided, uses session's distance_3d flag to determine whether to calculate 2D or 3D distance
    - If z is not provided, always uses 2D horizontal distance only
    """
    drone = _get_drone_or_404(drone_id)

    current_pos = drone["position"]

    # Calculate distance based on whether Z coordinate is provided
    if z is not None:
        # 3D distance (respecting session flag)
        expected_pos = {"x": x, "y": y, "z": z}
        distance = _get_session_distance(current_pos, expected_pos)
    else:
        # Explicit 2D distance (horizontal only)
        distance = distance_2d(current_pos, {"x": x, "y": y})
        expected_pos = {"x": x, "y": y, "z": None}

    is_at_position = distance <= tolerance

    return _build_check_response(
        is_at_position,
        round(distance, 3),
        drone_id=drone_id,
        current_position=current_pos,
        expected_position=expected_pos,
        tolerance=tolerance
    )


@app.get("/check/drone_status", tags=["Checks"])
async def check_drone_status(
    drone_id: str,
    expected_status: DroneStatus,
    _role: UserRole = Depends(require_admin)
):
    """Check if a drone has a specific status.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - expected_status: Expected drone status (idle, ready, taking_off, flying, moving, hovering, landing, emergency, offline)

    **Response Format:**
    - Object with result boolean, current_status value, drone_id, and expected_status
    """
    drone = _get_drone_or_404(drone_id)

    current_status = drone["status"]
    is_at_status = current_status == expected_status.value

    return _build_check_response(
        is_at_status,
        current_status,
        drone_id=drone_id,
        expected_status=expected_status.value
    )


@app.get("/check/drone_battery_level", tags=["Checks"])
async def check_drone_battery_level(
    drone_id: str,
    min_level: float = 0.0,
    _role: UserRole = Depends(require_admin)
):
    """Check if a drone's battery level meets a minimum threshold.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - min_level: Minimum required battery level (default: 0.0)

    **Response Format:**
    - Object with result boolean, current battery level value, drone_id, and min_level
    """
    drone = _get_drone_or_404(drone_id)
    level = float(drone.get("battery_level", 0.0))
    meets = level >= min_level

    return _build_check_response(
        meets,
        level,
        drone_id=drone_id,
        min_level=min_level
    )


@app.get("/check/drone_heading", tags=["Checks"])
async def check_drone_heading(
    drone_id: str,
    expected_heading: float,
    tolerance: float = 5.0,
    _role: UserRole = Depends(require_admin)
):
    """Check if a drone's heading is within tolerance of expected.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - expected_heading: Expected heading in degrees (0-360)
    - tolerance: Acceptable difference in degrees (default: 5.0)

    **Response Format:**
    - Object with result boolean, current heading value, drone_id, expected_heading, heading_delta, and tolerance

    **Notes:**
    - Both current and expected headings are normalized to 0-360 degrees
    - Calculates the smallest angular difference (handles wrap-around at 0/360)
    """
    drone = _get_drone_or_404(drone_id)
    current_heading = float(drone.get("heading", 0.0)) % 360.0
    delta = _heading_delta(current_heading, expected_heading)
    within = delta <= tolerance

    return _build_check_response(
        within,
        current_heading,
        drone_id=drone_id,
        expected_heading=expected_heading % 360.0,
        heading_delta=round(delta, 3),
        tolerance=tolerance
    )


@app.get("/check/drone_over_height", tags=["Checks"])
async def check_drone_over_height(
    drone_id: str,
    min_height: float,
    tolerance: float = 0.1,
    _role: UserRole = Depends(require_admin)
):
    """Check if a drone's altitude is above (or near) a minimum height.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - min_height: Minimum required altitude in meters
    - tolerance: Acceptable tolerance (default: 0.1 meters)

    **Response Format:**
    - Object with result boolean, current altitude value, drone_id, min_height, and tolerance

    **Notes:**
    - Tolerance allows for slight under-height to still pass (altitude + tolerance >= min_height)
    """
    drone = _get_drone_or_404(drone_id)
    altitude = drone["position"]["z"]
    meets = altitude + tolerance >= min_height

    return _build_check_response(
        meets,
        altitude,
        drone_id=drone_id,
        min_height=min_height,
        tolerance=tolerance
    )


@app.get("/check/drone_in_target", tags=["Checks"])
async def check_drone_in_target(
    drone_id: str,
    target_id: str,
    _role: UserRole = Depends(require_admin)
):
    """Check if a drone is inside a target's radius (center-based).

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - target_id: ID of the target to check against

    **Response Format:**
    - Object with result boolean, distance value, drone_id, target_id, and target_radius

    **Notes:**
    - Only works with circular/radial target types
    - Calculates distance from drone to target center, compares to target radius
    """
    drone = _get_drone_or_404(drone_id)
    target = _get_target_or_404(target_id)

    target_pos = target.get("position") or {"x": 0.0, "y": 0.0, "z": 0.0}
    radius = float(target.get("radius") or 0.0)
    distance = _get_session_distance(drone["position"], target_pos)
    inside = distance <= radius

    return _build_check_response(
        inside,
        round(distance, 3),
        drone_id=drone_id,
        target_id=target_id,
        target_radius=radius
    )


@app.get("/check/drone_at_home", tags=["Checks"])
async def check_drone_at_home(
    drone_id: str,
    tolerance: float = 1.0,
    _role: UserRole = Depends(require_admin)
):
    """Check if a drone is at (or near) its home position.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - tolerance: Acceptable distance in meters (default: 1.0)

    **Response Format:**
    - Object with result boolean, distance value, drone_id, home_position, and tolerance
    """
    drone = _get_drone_or_404(drone_id)
    home_pos = drone.get("home_position") or {"x": 0.0, "y": 0.0, "z": 0.0}
    distance = _get_session_distance(drone["position"], home_pos)
    at_home = distance <= tolerance

    return _build_check_response(
        at_home,
        round(distance, 3),
        drone_id=drone_id,
        home_position=home_pos,
        tolerance=tolerance
    )


@app.get("/check/target_within_drone_distance", tags=["Checks"])
async def check_target_within_drone_distance(
    drone_id: str,
    target_id: str,
    max_distance: float,
    _role: UserRole = Depends(require_admin)
):
    """Check if a target is within a specified distance from a drone.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone
    - target_id: ID of the target
    - max_distance: Maximum allowed distance in meters

    **Response Format:**
    - Object with result boolean, distance value, drone_id, target_id, and max_distance
    """
    drone = _get_drone_or_404(drone_id)
    target = _get_target_or_404(target_id)

    distance = _get_session_distance(drone["position"], target["position"])
    within = distance <= max_distance

    return _build_check_response(
        within,
        round(distance, 3),
        drone_id=drone_id,
        target_id=target_id,
        max_distance=max_distance
    )


@app.get("/check/target_within_drone_task_radius", tags=["Checks"])
async def check_target_within_drone_task_radius(
    drone_id: str,
    target_id: str,
    _role: UserRole = Depends(require_admin)
):
    """Check if a target is within a drone's task radius.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone
    - target_id: ID of the target

    **Response Format:**
    - Object with result boolean, distance value, drone_id, target_id, and task_radius
    """
    drone = _get_drone_or_404(drone_id)
    target = _get_target_or_404(target_id)

    task_radius = float(drone.get("task_radius", 0.0))
    distance = _get_session_distance(drone["position"], target["position"])
    within = distance <= task_radius

    return _build_check_response(
        within,
        round(distance, 3),
        drone_id=drone_id,
        target_id=target_id,
        task_radius=task_radius
    )


@app.get("/check/target_within_drone_perceived_radius", tags=["Checks"])
async def check_target_within_drone_perceived_radius(
    drone_id: str,
    target_id: str,
    _role: UserRole = Depends(require_admin)
):
    """Check if a target is within a drone's perceived radius.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone
    - target_id: ID of the target

    **Response Format:**
    - Object with result boolean, distance value, drone_id, target_id, and perceived_radius
    """
    drone = _get_drone_or_404(drone_id)
    target = _get_target_or_404(target_id)

    perceived_radius = float(drone.get("perceived_radius", 0.0))
    distance = _get_session_distance(drone["position"], target["position"])
    within = distance <= perceived_radius

    return _build_check_response(
        within,
        round(distance, 3),
        drone_id=drone_id,
        target_id=target_id,
        perceived_radius=perceived_radius
    )


@app.get("/check/target_in_photo_taken_by_drone", tags=["Checks"])
async def check_target_in_photo(drone_id: str, target_id: str, _role: UserRole = Depends(require_admin)):
    """
    Verify if a target was visible to a drone when photos were taken.

    **Required Privileges:**
    - ADMIN: Full access to check endpoints

    **Request Parameters:**
    - drone_id: Drone that took photos (path parameter)
    - target_id: Target to check visibility for (path parameter)

    **Response Format:**
    - result: Boolean indicating if target was visible in any photo
    - drone_id: Verified drone ID
    - target_id: Verified target ID
    - perceived_radius: Drone's visibility radius used for check
    - matching_photos: Array of photo events with timestamp, position, distance
    - 404 Not Found if drone or target doesn't exist

    **Behavior:**
    - Searches drone's status history for TAKE_PHOTO events
    - For each photo, checks if target was within drone's perceived_radius
    - Returns all matching photo events with details
    """
    try:
        drone = drone_controller.get_drone(drone_id)
        if not drone:
            raise HTTPException(status_code=404, detail="Drone not found")

        target = target_controller.get_target(target_id)
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")

        # Get the drone object (not just the dict) to access history
        drone_obj = drone_controller.drones[drone_id]
        history = drone_obj.get_history_by_event("take_photo")

        perceived_radius = drone["perceived_radius"]
        target_pos = target["position"]

        found = False
        matching_photos = []

        for event in history:
            drone_pos_at_photo = event["position"]

            # Calculate distance from drone to target
            dist = _get_session_distance(drone_pos_at_photo, target_pos)
            if dist <= perceived_radius:
                found = True
                matching_photos.append({
                    "photo_id": event.get("metadata", {}).get("photo_id"),
                    "timestamp": event["timestamp"],
                    "drone_position": drone_pos_at_photo,
                    "distance": dist
                })

        return {
            "result": found,
            "drone_id": drone_id,
            "target_id": target_id,
            "perceived_radius": perceived_radius,
            "matching_photos": matching_photos
        }

    except KeyError:
        raise HTTPException(status_code=404, detail="Drone or Target not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/check/obstacle_within_drone_distance", tags=["Checks"])
async def check_obstacle_within_drone_distance(
    drone_id: str,
    obstacle_id: str,
    max_distance: float,
    _role: UserRole = Depends(require_admin)
):
    """Check if an obstacle is within a specified distance from a drone.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone
    - obstacle_id: ID of the obstacle
    - max_distance: Maximum allowed distance in meters

    **Response Format:**
    - Object with result boolean, distance value, drone_id, obstacle_id, and max_distance
    """
    drone = _get_drone_or_404(drone_id)
    obstacle = _get_obstacle_or_404(obstacle_id)

    obstacle_pos = obstacle.get("position") or {"x": 0.0, "y": 0.0, "z": 0.0}
    distance = _get_session_distance(drone["position"], obstacle_pos)
    within = distance <= max_distance

    return _build_check_response(
        within,
        round(distance, 3),
        drone_id=drone_id,
        obstacle_id=obstacle_id,
        max_distance=max_distance
    )


@app.get("/check/obstacle_within_drone_perceived_radius", tags=["Checks"])
async def check_obstacle_within_drone_perceived_radius(
    drone_id: str,
    obstacle_id: str,
    _role: UserRole = Depends(require_admin)
):
    """Check if an obstacle is within a drone's perceived radius.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone
    - obstacle_id: ID of the obstacle

    **Response Format:**
    - Object with result boolean, distance value, drone_id, obstacle_id, and perceived_radius
    """
    drone = _get_drone_or_404(drone_id)
    obstacle = _get_obstacle_or_404(obstacle_id)

    obstacle_pos = obstacle.get("position") or {"x": 0.0, "y": 0.0, "z": 0.0}
    perceived_radius = float(drone.get("perceived_radius", 0.0))
    distance = _get_session_distance(drone["position"], obstacle_pos)
    within = distance <= perceived_radius

    return _build_check_response(
        within,
        round(distance, 3),
        drone_id=drone_id,
        obstacle_id=obstacle_id,
        perceived_radius=perceived_radius
    )


@app.get("/check/two_drones_distance", tags=["Checks"])
async def check_two_drones_distance(
    drone_1_id: Optional[str] = None,
    drone_2_id: Optional[str] = None,
    max_distance: Optional[float] = None,
    min_distance: float = 0.0,
    _role: UserRole = Depends(require_admin)
):
    """Check if two drones are within a specified distance range.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_1_id: ID of the first drone
    - drone_2_id: ID of the second drone
    - max_distance: Maximum allowed distance (optional, None means no upper limit)
    - min_distance: Minimum allowed distance (default: 0.0)

    **Response Format:**
    - Object with result boolean, distance value, drone_1_id, drone_2_id, max_distance, and min_distance
    - Result is true when min_distance <= distance <= max_distance (with max_distance optional)
    """
    if not drone_1_id or not drone_2_id:
        raise HTTPException(status_code=400, detail="Missing required drone IDs (drone_1_id, drone_2_id).")

    drone1 = _get_drone_or_404(drone_1_id)
    drone2 = _get_drone_or_404(drone_2_id)

    distance = _get_session_distance(drone1["position"], drone2["position"])

    # Check bounds
    lower_bound_ok = distance >= min_distance
    upper_bound_ok = True
    if max_distance is not None:
        upper_bound_ok = distance <= max_distance

    within = lower_bound_ok and upper_bound_ok

    response = _build_check_response(
        within,
        round(distance, 3),
        drone_1_id=drone_1_id,
        drone_2_id=drone_2_id,
        max_distance=max_distance,
        min_distance=min_distance
    )

    return response


@app.get("/check/drone_group_distance", tags=["Checks"])
async def check_drone_group_distance(
    drone_ids: List[str] = Query(..., description="Drone IDs to check, provided as repeated query parameters"),
    max_distance: Optional[float] = None,
    min_distance: float = 0.0,
    mode: str = Query("all_pairs", description="Group evaluation mode: all_pairs or any_pair"),
    _role: UserRole = Depends(require_admin)
):
    """Check whether a group of drones satisfies pairwise distance constraints.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_ids: List of drone IDs to check (at least 2 required, no duplicates)
    - max_distance: Maximum allowed distance (optional, None means no upper limit)
    - min_distance: Minimum allowed distance (default: 0.0)
    - mode: Evaluation mode: "all_pairs" (all must satisfy) or "any_pair" (at least one must satisfy)

    **Response Format:**
    - Object with result boolean, count of passing pairs, and detailed pair_distances array
    - Also includes drone_ids, min_distance, max_distance, mode, total_pairs, passing_pairs, failing_pairs
    """
    if len(drone_ids) < 2:
        raise HTTPException(status_code=400, detail="At least two drone_ids are required.")

    if len(set(drone_ids)) != len(drone_ids):
        raise HTTPException(status_code=400, detail="Duplicate drone_ids are not allowed.")

    if mode not in {"all_pairs", "any_pair"}:
        raise HTTPException(status_code=400, detail="Invalid mode. Supported values: all_pairs, any_pair.")

    drones = {drone_id: _get_drone_or_404(drone_id) for drone_id in drone_ids}

    pair_distances = []
    passing_pairs = []
    failing_pairs = []

    for index, drone_1_id in enumerate(drone_ids):
        for drone_2_id in drone_ids[index + 1:]:
            distance = _get_session_distance(
                drones[drone_1_id]["position"],
                drones[drone_2_id]["position"]
            )
            pair_result = distance >= min_distance
            if max_distance is not None:
                pair_result = pair_result and distance <= max_distance

            pair_record = {
                "drone_1_id": drone_1_id,
                "drone_2_id": drone_2_id,
                "distance": round(distance, 3),
                "result": pair_result
            }
            pair_distances.append(pair_record)
            if pair_result:
                passing_pairs.append(pair_record)
            else:
                failing_pairs.append(pair_record)

    total_pairs = len(pair_distances)
    if mode == "all_pairs":
        result = len(passing_pairs) == total_pairs
    else:
        result = len(passing_pairs) >= 1

    return _build_check_response(
        result,
        len(passing_pairs),
        drone_ids=drone_ids,
        min_distance=min_distance,
        max_distance=max_distance,
        mode=mode,
        total_pairs=total_pairs,
        passing_pairs=len(passing_pairs),
        failing_pairs=len(failing_pairs),
        pair_distances=pair_distances
    )


@app.get("/check/drone_altitude", tags=["Checks"])
async def check_drone_altitude(
    drone_id: str,
    expected_altitude: float,
    tolerance: float = 0.5,
    _role: UserRole = Depends(require_admin)
):
    """Check if a drone is at the expected altitude.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - expected_altitude: Target altitude in meters
    - tolerance: Acceptable difference (default: 0.5 meters)

    **Response Format:**
    - Object with result boolean, current altitude value, drone_id, expected_altitude, difference, and tolerance
    """
    drone = _get_drone_or_404(drone_id)
    current_altitude = drone["position"]["z"]
    difference = current_altitude - expected_altitude
    within_tolerance = abs(difference) <= tolerance

    return _build_check_response(
        within_tolerance,
        current_altitude,
        drone_id=drone_id,
        expected_altitude=expected_altitude,
        difference=round(difference, 3),
        tolerance=tolerance
    )


@app.get("/check/drone_on_ground", tags=["Checks"])
async def check_drone_on_ground(
    drone_id: str,
    tolerance: float = 0.1,
    _role: UserRole = Depends(require_admin)
):
    """Check if a drone is on the ground (altitude within tolerance AND status is grounded).

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - tolerance: Acceptable altitude (default: 0.1 meters)

    **Response Format:**
    - Object with result boolean, current altitude value, drone_id, status, and tolerance

    **Notes:**
    - Requires both altitude <= tolerance AND status in {idle, ready, landing}
    """
    drone = _get_drone_or_404(drone_id)
    altitude = drone["position"]["z"]
    on_ground = _is_drone_on_ground(drone, tolerance)

    return _build_check_response(
        on_ground,
        altitude,
        drone_id=drone_id,
        status=drone["status"],
        tolerance=tolerance
    )


@app.get("/check/all_drones_on_ground", tags=["Checks"])
async def check_all_drones_on_ground(
    tolerance: float = 0.1,
    _role: UserRole = Depends(require_admin)
):
    """Check if all drones are on the ground.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - tolerance: Acceptable altitude (default: 0.1 meters)

    **Response Format:**
    - Object with result boolean, count of on-ground drones, and lists of on_ground_drones and not_on_ground_drones
    """
    drones = drone_controller.get_all_drones()
    if not drones:
        return _build_check_response(
            False,
            0,
            total_drones=0,
            on_ground_drones=[],
            not_on_ground_drones=[]
        )

    on_ground_drones = [d["id"] for d in drones if _is_drone_on_ground(d, tolerance)]
    not_on_ground = [d["id"] for d in drones if d["id"] not in on_ground_drones]
    all_on_ground = len(on_ground_drones) == len(drones)

    return _build_check_response(
        all_on_ground,
        len(on_ground_drones),
        total_drones=len(drones),
        on_ground_drones=on_ground_drones,
        not_on_ground_drones=not_on_ground,
        tolerance=tolerance
    )


@app.get("/check/drone_hovering", tags=["Checks"])
async def check_drone_hovering(
    drone_id: str,
    tolerance: float = 0.1,
    _role: UserRole = Depends(require_admin)
):
    """Check if a drone is hovering above ground.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - tolerance: Minimum altitude to consider "above ground" (default: 0.1 meters)

    **Response Format:**
    - Object with result boolean, status value, drone_id, altitude, and tolerance

    **Notes:**
    - Requires both altitude > tolerance AND status is hovering
    """
    drone = _get_drone_or_404(drone_id)
    altitude = drone["position"]["z"]
    hovering = _is_drone_hovering(drone, tolerance)

    return _build_check_response(
        hovering,
        drone["status"],
        drone_id=drone_id,
        altitude=altitude,
        tolerance=tolerance
    )


@app.get("/check/all_drones_hovering", tags=["Checks"])
async def check_all_drones_hovering(
    tolerance: float = 0.1,
    _role: UserRole = Depends(require_admin)
):
    """Check if all drones are hovering.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - tolerance: Minimum altitude to consider "above ground" (default: 0.1 meters)

    **Response Format:**
    - Object with result boolean, count of hovering drones, and lists of hovering_drones and not_hovering_drones
    """
    drones = drone_controller.get_all_drones()
    if not drones:
        return _build_check_response(
            False,
            0,
            total_drones=0,
            hovering_drones=[],
            not_hovering_drones=[]
        )

    hovering_drones = [d["id"] for d in drones if _is_drone_hovering(d, tolerance)]
    not_hovering = [d["id"] for d in drones if d["id"] not in hovering_drones]
    all_hovering = len(hovering_drones) == len(drones)

    return _build_check_response(
        all_hovering,
        len(hovering_drones),
        total_drones=len(drones),
        hovering_drones=hovering_drones,
        not_hovering_drones=not_hovering,
        tolerance=tolerance
    )


@app.get("/check/target_is_reached", tags=["Checks"])
async def check_target_is_reached(
    target_id: str,
    since_timestamp: Optional[float] = None,
    _role: UserRole = Depends(require_admin)
):
    """Check if any drone has reached a target.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - target_id: ID of the target to check
    - since_timestamp: Only consider reaches after this timestamp (optional)

    **Response Format:**
    - Object with result boolean, count of drones that reached it, target_id, reached_by list, and session_id
    """
    _get_target_or_404(target_id)
    resolved_session_id, session_obj = _get_session_or_404()
    reached_by = _collect_target_reach_drone_ids(session_obj, target_id, since_timestamp=since_timestamp)

    return _build_check_response(
        bool(reached_by),
        len(reached_by),
        session_id=resolved_session_id,
        target_id=target_id,
        reached_by=list(reached_by),
        since_timestamp=since_timestamp
    )


@app.get("/check/target_is_reached_by_drone", tags=["Checks"])
async def check_target_is_reached_by_drone(
    target_id: str,
    drone_id: str,
    since_timestamp: Optional[float] = None,
    _role: UserRole = Depends(require_admin)
):
    """Check if a specific drone has reached a target.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - target_id: ID of the target to check
    - drone_id: ID of the drone to check
    - since_timestamp: Only consider reaches after this timestamp (optional)

    **Response Format:**
    - Object with result boolean, count of visits, target_id, drone_id, session_id, and since_timestamp
    """
    _get_target_or_404(target_id)
    _get_drone_or_404(drone_id)
    resolved_session_id, session_obj = _get_session_or_404()

    visit_entries = _filter_timestamps_since(
        session_obj.target_reaches.get(drone_id, {}).get(target_id, []),
        since_timestamp
    )
    visit_count = len(visit_entries)
    reached = visit_count > 0

    return _build_check_response(
        reached,
        visit_count,
        session_id=resolved_session_id,
        target_id=target_id,
        drone_id=drone_id,
        since_timestamp=since_timestamp
    )


@app.get("/check/target_reached_drone_number", tags=["Checks"])
async def check_target_reached_drone_number(
    target_id: str,
    expected_count: Optional[int] = None,
    since_timestamp: Optional[float] = None,
    _role: UserRole = Depends(require_admin)
):
    """Check how many drones reached a target and validate against expectation.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - target_id: ID of the target to check
    - expected_count: Minimum number of drones that need to reach (optional, defaults to >0)
    - since_timestamp: Only consider reaches after this timestamp (optional)

    **Response Format:**
    - Object with result boolean, count of drones that reached, target_id, expected_count, reached_by list, and session_id

    **Notes:**
    - If expected_count is provided, checks if count >= expected_count
    - If expected_count is not provided, checks if count > 0
    """
    _get_target_or_404(target_id)
    resolved_session_id, session_obj = _get_session_or_404()
    reached_by = _collect_target_reach_drone_ids(session_obj, target_id, since_timestamp=since_timestamp)
    count = len(reached_by)

    meets_expectation = False
    if expected_count is not None:
        meets_expectation = count >= expected_count
    else:
        meets_expectation = count > 0

    return _build_check_response(
        meets_expectation,
        count,
        session_id=resolved_session_id,
        target_id=target_id,
        expected_count=expected_count,
        reached_by=list(reached_by),
        since_timestamp=since_timestamp
    )


@app.get("/check/moving_target_tracked", tags=["Checks"])
async def check_moving_target_tracked(
    target_id: str,
    drone_id: Optional[str] = None,
    min_duration: float = 0.0,
    since_timestamp: Optional[float] = None,
    _role: UserRole = Depends(require_admin)
):
    """Check whether a moving target has a retained tracking period meeting a minimum duration.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - target_id: ID of the moving target to check (must be type "moving")
    - drone_id: Optional specific drone to check tracking for (checks all drones if not provided)
    - min_duration: Minimum required tracking duration in seconds (default: 0.0)
    - since_timestamp: Only consider periods after this timestamp (optional)

    **Response Format:**
    - Object with result boolean, max_tracked_duration value, and details about matching_periods and tracking_status

    **Notes:**
    - tracking_status can be "never_tracked", "tracked", or "stale" (if tracked >10 seconds ago)
    """
    if min_duration < 0:
        raise HTTPException(status_code=400, detail="min_duration must be non-negative")

    target = _get_target_or_404(target_id)
    if target.get("type") != "moving":
        raise HTTPException(status_code=400, detail="target_id must refer to a moving target")

    if drone_id is not None:
        _get_drone_or_404(drone_id)

    resolved_session_id, session_obj = _get_session_or_404()
    tracking_periods = session_obj.get_target_tracking_periods(target_id, drone_id=drone_id)
    tracking_periods = _filter_tracking_periods_since(tracking_periods, since_timestamp)

    durations = [max(0.0, float(period.get("end_at", 0.0)) - float(period.get("start_at", 0.0))) for period in tracking_periods]
    matching_durations = [duration for duration in durations if duration >= min_duration]
    max_tracked_duration = max(durations) if durations else 0.0

    tracking_details = session_obj.get_moving_target_tracking_details().get(target_id, {})
    if drone_id is None:
        tracking_status = tracking_details.get("tracking_status", "never_tracked")
    else:
        drone_details = tracking_details.get("by_drone", {}).get(drone_id, {})
        last_tracked_at = drone_details.get("last_tracked_at")
        if last_tracked_at is None:
            tracking_status = "never_tracked"
        elif (time.time() - float(last_tracked_at)) <= 10.0:
            tracking_status = "tracked"
        else:
            tracking_status = "stale"

    return _build_check_response(
        bool(matching_durations),
        round(max_tracked_duration, 3),
        session_id=resolved_session_id,
        target_id=target_id,
        drone_id=drone_id,
        min_duration=min_duration,
        max_tracked_duration=round(max_tracked_duration, 3),
        matching_periods=len(matching_durations),
        tracking_status=tracking_status,
        since_timestamp=since_timestamp,
    )


@app.get("/check/target_is_fully_searched", tags=["Checks"])
async def check_target_is_fully_searched(
    target_id: str,
    coverage_threshold: float = 0.99,
    _role: UserRole = Depends(require_admin)
):
    """Check if a target's area coverage meets the full threshold.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - target_id: ID of the target to check
    - coverage_threshold: Minimum coverage ratio (0-1) to consider "fully searched" (default: 0.99 = 99%)

    **Response Format:**
    - Object with result boolean, coverage_ratio value, target_id, coverage_percentage, and coverage_threshold
    """
    _get_target_or_404(target_id)
    resolved_session_id, session_obj = _get_session_or_404()

    coverage_data = session_obj.area_coverage.get(target_id) if session_obj else None
    coverage_pct = coverage_data.get("coverage_percentage", 0.0) if coverage_data else 0.0
    coverage_ratio = coverage_pct / 100.0
    fully_searched = coverage_ratio >= coverage_threshold

    return _build_check_response(
        fully_searched,
        coverage_ratio,
        session_id=resolved_session_id,
        target_id=target_id,
        coverage_percentage=coverage_pct,
        coverage_threshold=coverage_threshold
    )


@app.get("/check/target_searched_area_percentage", tags=["Checks"])
async def check_target_searched_area_percentage(
    target_id: str,
    expected_percentage: float,
    _role: UserRole = Depends(require_admin)
):
    """Check if a target's searched area meets an expected percentage (0-1).

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - target_id: ID of the target to check
    - expected_percentage: Minimum required coverage ratio (0-1, e.g. 0.5 = 50%)

    **Response Format:**
    - Object with result boolean, coverage_ratio value, target_id, expected_percentage, and coverage_percentage
    """
    if expected_percentage < 0 or expected_percentage > 1:
        raise HTTPException(status_code=400, detail="expected_percentage must be between 0 and 1")

    _get_target_or_404(target_id)
    resolved_session_id, session_obj = _get_session_or_404()

    coverage_data = session_obj.area_coverage.get(target_id) if session_obj else None
    coverage_pct = coverage_data.get("coverage_percentage", 0.0) if coverage_data else 0.0
    coverage_ratio = coverage_pct / 100.0
    meets_expectation = coverage_ratio >= expected_percentage if coverage_data else False

    return _build_check_response(
        meets_expectation,
        coverage_ratio,
        session_id=resolved_session_id,
        target_id=target_id,
        expected_percentage=expected_percentage,
        coverage_percentage=coverage_pct
    )

@app.get("/check/task/{task_id}", tags=["Checks"])
async def check_task_execution(
    task_id: str,
    since_timestamp: Optional[float] = None,
    _role: UserRole = Depends(require_agent)
):
    """Check if the execution conditions for a task are met.

    **Required Privileges:**
    - AGENT: Can check task execution (only boolean result returned)
    - SYSTEM/ADMIN: Full access to detailed check results

    **Request Parameters:**
    - task_id: ID of the task to check
    - since_timestamp: Only consider events after this timestamp (optional)

    **Response Format:**
    - AGENT: `{"result": bool}`
    - SYSTEM/ADMIN: Full evaluation tree with detailed results for each check

    **Notes:**
    - Evaluates the 'execution_check_apis' logical tree defined in the task
    """
    current_session = session_controller.get_current_session()
    if not current_session:
        raise HTTPException(status_code=404, detail="No current session found")
        
    task = session_controller.get_task(current_session["id"], task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    check_node = task.get("execution_check_apis")
    if not check_node:
        return {"result": True}
        
    evaluation = await _evaluate_check_node(check_node, since_timestamp=since_timestamp)
    
    if _role in (UserRole.SYSTEM, UserRole.ADMIN):
        return evaluation
    else:
        return {"result": evaluation["result"]}



@app.get("/check/task_progress", tags=["Checks"])
async def check_task_progress(
    expected_progress: Optional[float] = None,
    _role: UserRole = Depends(require_admin)
):
    """Check task progress against an expected value (0-1).

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - expected_progress: Minimum progress ratio (0-1) required (optional)

    **Response Format:**
    - Object with result boolean, progress_ratio value, session_id, expected_progress, task_type, progress_percentage, and is_completed
    """
    if expected_progress is not None and (expected_progress < 0 or expected_progress > 1):
        raise HTTPException(status_code=400, detail="expected_progress must be between 0 and 1")

    resolved_session_id, session_obj = _get_session_or_404()
    task_progress = session_obj.get_task_progress()
    progress_percentage = task_progress.get("progress_percentage", 0)
    progress_ratio = progress_percentage / 100.0
    meets_expectation = progress_ratio >= expected_progress if expected_progress is not None else False

    return _build_check_response(
        meets_expectation,
        progress_ratio,
        session_id=resolved_session_id,
        expected_progress=expected_progress,
        task_type=task_progress.get("task_type", "unknown"),
        progress_percentage=progress_percentage,
        is_completed=bool(task_progress.get("is_completed"))
    )


@app.get("/check/task_done", tags=["Checks"])
async def check_task_done(
    _role: UserRole = Depends(require_admin)
):
    """Check if a task is completed in a session.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Response Format:**
    - Object with result boolean (is_completed), progress_ratio value, session_id, session_name, task_type, progress_percentage, status_message, and details

    **Notes:**
    - Checks the current active session (no session_id parameter needed)
    """
    resolved_session_id, session_obj = _get_session_or_404()
    task_progress = session_obj.get_task_progress()
    progress_percentage = task_progress.get("progress_percentage", 0)
    progress_ratio = progress_percentage / 100.0
    is_completed = bool(task_progress.get("is_completed", False))

    return _build_check_response(
        is_completed,
        progress_ratio,
        session_id=resolved_session_id,
        session_name=getattr(session_obj, "name", "Unknown"),
        task_type=task_progress.get("task_type", "unknown"),
        progress_percentage=progress_percentage,
        status_message=task_progress.get("status_message", ""),
        details=task_progress.get("details", {})
    )


# ==================== History Status Check Endpoints (ADMIN only) ====================

@app.get("/check/drone_has_taken_off", tags=["Checks"])
async def check_drone_has_taken_off(
    drone_id: str,
    min_altitude: float = 5.0,
    max_altitude: Optional[float] = None,
    tolerance: float = 0.0,
    since_timestamp: Optional[float] = None,
    _role: UserRole = Depends(require_admin)
):
    """Check if drone has taken off (from history).

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - min_altitude: Minimum altitude to count as takeoff (default: 5.0 meters)
    - max_altitude: Optional maximum altitude to bound takeoff matches
    - tolerance: Inclusive altitude tolerance applied to the match bounds
    - since_timestamp: Only check events after this timestamp (optional)

    **Response Format:**
    - Object with result boolean, count of matching takeoffs, drone_id, takeoff_count, last_takeoff_time, max_altitude_reached, min_altitude_threshold, max_altitude_threshold, tolerance, matched_altitude_min, matched_altitude_max
    """
    if tolerance < 0:
        raise HTTPException(status_code=400, detail="Tolerance cannot be negative")
    if max_altitude is not None and max_altitude < min_altitude:
        raise HTTPException(status_code=400, detail="max_altitude cannot be less than min_altitude")

    history = _get_drone_history(drone_id)
    history = _filter_history_by_timestamp(history, since_timestamp)

    takeoffs = _filter_history_by_event(history, "take_off")
    lower_bound = min_altitude - tolerance
    upper_bound = max_altitude + tolerance if max_altitude is not None else None
    matching_takeoffs = []
    for takeoff in takeoffs:
        altitude = takeoff.get("position", {}).get("z", 0)
        if upper_bound is None:
            if altitude >= lower_bound:
                matching_takeoffs.append(takeoff)
        elif lower_bound <= altitude <= upper_bound:
            matching_takeoffs.append(takeoff)

    has_taken_off = len(matching_takeoffs) > 0
    max_altitude_reached = max([t["position"]["z"] for t in takeoffs], default=0.0) if takeoffs else 0.0
    last_takeoff = max(takeoffs, key=lambda x: x["timestamp"])["timestamp"] if takeoffs else None

    return _build_check_response(
        has_taken_off,
        len(matching_takeoffs),
        drone_id=drone_id,
        takeoff_count=len(takeoffs),
        last_takeoff_time=last_takeoff,
        max_altitude_reached=round(max_altitude_reached, 2),
        min_altitude_threshold=min_altitude,
        max_altitude_threshold=max_altitude,
        tolerance=tolerance,
        matched_altitude_min=round(lower_bound, 3),
        matched_altitude_max=round(upper_bound, 3) if upper_bound is not None else None
    )


@app.get("/check/drone_has_landed", tags=["Checks"])
async def check_drone_has_landed(
    drone_id: str,
    min_count: int = 1,
    since_timestamp: Optional[float] = None,
    _role: UserRole = Depends(require_admin)
):
    """Check if drone has landed (from history).

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - min_count: Minimum number of landings required (default: 1)
    - since_timestamp: Only check events after this timestamp (optional)

    **Response Format:**
    - Object with result boolean, count of landings, drone_id, min_count, last_landing_time, last_landing_position
    """
    history = _get_drone_history(drone_id)
    history = _filter_history_by_timestamp(history, since_timestamp)

    landings = _filter_history_by_event(history, "land")

    has_landed = len(landings) >= min_count
    last_landing = max(landings, key=lambda x: x["timestamp"]) if landings else None
    last_landing_time = last_landing["timestamp"] if last_landing else None
    last_landing_pos = last_landing["position"] if last_landing else None

    return _build_check_response(
        has_landed,
        len(landings),
        drone_id=drone_id,
        min_count=min_count,
        last_landing_time=last_landing_time,
        last_landing_position=last_landing_pos
    )


@app.get("/check/drone_has_visited_position", tags=["Checks"])
async def check_drone_has_visited_position(
    drone_id: str,
    x: float,
    y: float,
    z: Optional[float] = None,
    tolerance: float = 5.0,
    since_timestamp: Optional[float] = None,
    _role: UserRole = Depends(require_admin)
):
    """Check if drone has visited a specific position (from history).

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - x: Target X coordinate
    - y: Target Y coordinate
    - z: Target Z coordinate (optional - if None, only checks X and Y)
    - tolerance: Acceptable distance tolerance in meters (default: 5.0)
    - since_timestamp: Only check events after this timestamp (optional)

    **Response Format:**
    - Object with result boolean, count of visits, drone_id, target_position, tolerance, closest_distance, first_visit_time, last_visit_time
    """
    history = _get_drone_history(drone_id)
    history = _filter_history_by_timestamp(history, since_timestamp)

    # Get all waypoint events
    waypoints = _filter_history_by_type(history, "waypoint")

    target_pos = {"x": x, "y": y, "z": z if z is not None else 0}
    check_z = z is not None

    # Find visits within tolerance
    visits = []
    distances = []

    for wp in waypoints:
        end_pos = wp.get("position", {})
        if _position_within_tolerance(end_pos, target_pos, tolerance, check_z):
            visits.append(wp)
            distances.append(_get_session_distance(end_pos, target_pos) if check_z else
                           distance_2d(end_pos, target_pos))

    has_visited = len(visits) > 0
    closest_distance = min(distances) if distances else float('inf')
    first_visit = min(visits, key=lambda x: x["timestamp"]) if visits else None
    last_visit = max(visits, key=lambda x: x["timestamp"]) if visits else None

    return _build_check_response(
        has_visited,
        len(visits),
        drone_id=drone_id,
        target_position=target_pos,
        tolerance=tolerance,
        closest_distance=round(closest_distance, 2) if closest_distance != float('inf') else None,
        first_visit_time=first_visit["timestamp"] if first_visit else None,
        last_visit_time=last_visit["timestamp"] if last_visit else None
    )


@app.get("/check/drone_has_moved_distance", tags=["Checks"])
async def check_drone_has_moved_distance(
    drone_id: str,
    min_distance: float,
    since_timestamp: Optional[float] = None,
    _role: UserRole = Depends(require_admin)
):
    """Check if drone has moved at least a minimum distance (from history).

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - min_distance: Minimum total distance in meters
    - since_timestamp: Only check events after this timestamp (optional)

    **Response Format:**
    - Object with result boolean, total_distance value, drone_id, min_distance, movement_count, average_distance_per_move
    """
    history = _get_drone_history(drone_id)
    history = _filter_history_by_timestamp(history, since_timestamp)

    # Get all waypoint events
    waypoints = _filter_history_by_type(history, "waypoint")

    total_distance = _calculate_distance_from_history(waypoints)
    movement_count = len(waypoints)
    average_distance = total_distance / movement_count if movement_count > 0 else 0.0

    has_moved = total_distance >= min_distance

    return _build_check_response(
        has_moved,
        round(total_distance, 2),
        drone_id=drone_id,
        min_distance=min_distance,
        movement_count=movement_count,
        average_distance_per_move=round(average_distance, 2)
    )


@app.get("/check/drone_has_moved_directed_distance", tags=["Checks"])
async def check_drone_has_moved_directed_distance(
    drone_id: str,
    min_distance: float,
    heading: float = Query(..., description="Target heading in degrees"),
    tolerance: float = Query(5.0, description="Tolerance in degrees"),
    since_timestamp: Optional[float] = None,
    _role: UserRole = Depends(require_admin)
):
    """Check if drone has moved at least a minimum distance in a specific direction (from history).

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - min_distance: Minimum total distance in meters
    - heading: Target heading in degrees
    - tolerance: Tolerance in degrees (default 5)
    - since_timestamp: Only check events after this timestamp (optional)

    **Response Format:**
    - Object with result boolean, total_directed_distance value, drone_id, min_distance, heading, tolerance, movement_count, average_distance_per_move
    """
    history = _get_drone_history(drone_id)
    history = _filter_history_by_timestamp(history, since_timestamp)

    # Get all waypoint events
    waypoints = _filter_history_by_type(history, "waypoint")

    total_distance = _calculate_directed_distance_from_history(waypoints, heading, tolerance)
    movement_count = len(waypoints)
    average_distance = total_distance / movement_count if movement_count > 0 else 0.0

    has_moved = total_distance >= min_distance

    return _build_check_response(
        has_moved,
        round(total_distance, 2),
        drone_id=drone_id,
        min_distance=min_distance,
        heading=heading,
        tolerance=tolerance,
        movement_count=movement_count,
        average_distance_per_move=round(average_distance, 2)
    )


@app.get("/check/drone_has_hovered", tags=["Checks"])
async def check_drone_has_hovered(
    drone_id: str,
    min_duration: Optional[float] = None,
    min_count: int = 1,
    since_timestamp: Optional[float] = None,
    _role: UserRole = Depends(require_admin)
):
    """Check if drone has hovered (from history).

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - min_duration: Minimum hover duration in seconds (optional - if None, any hover counts)
    - min_count: Minimum number of hover events (default: 1)
    - since_timestamp: Only check events after this timestamp (optional)

    **Response Format:**
    - Object with result boolean, count of hover events, drone_id, min_duration, min_count, total_hover_duration, average_duration, last_hover_time
    """
    history = _get_drone_history(drone_id)
    history = _filter_history_by_timestamp(history, since_timestamp)

    hovers = _filter_history_by_event(history, "hovering")

    # Filter by duration if specified
    if min_duration is not None:
        hovers = [h for h in hovers if h.get("duration", 0) >= min_duration]

    total_duration = sum(h.get("duration", 0) for h in hovers)
    average_duration = total_duration / len(hovers) if hovers else 0.0
    last_hover = max(hovers, key=lambda x: x["timestamp"]) if hovers else None

    has_hovered = len(hovers) >= min_count

    return _build_check_response(
        has_hovered,
        len(hovers),
        drone_id=drone_id,
        min_duration=min_duration,
        min_count=min_count,
        total_hover_duration=round(total_duration, 2),
        average_duration=round(average_duration, 2),
        last_hover_time=last_hover["timestamp"] if last_hover else None
    )


@app.get("/check/drone_has_taken_photo", tags=["Checks"])
async def check_drone_has_taken_photo(
    drone_id: str,
    min_count: int = 1,
    at_position: Optional[str] = None,
    tolerance: float = 5.0,
    since_timestamp: Optional[float] = None,
    _role: UserRole = Depends(require_admin)
):
    """Check if drone has taken photos (from history).

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - min_count: Minimum number of photos required (default: 1)
    - at_position: Optional JSON string of position {"x": 100, "y": 200, "z": 50} to filter photos by location
    - tolerance: Position tolerance in meters (default: 5.0)
    - since_timestamp: Only check events after this timestamp (optional)

    **Response Format:**
    - Object with result boolean, photo_count value, drone_id, min_count, photo_ids, first_photo_time, last_photo_time, positions (up to 10)
    """
    history = _get_drone_history(drone_id)
    history = _filter_history_by_timestamp(history, since_timestamp)

    photos = _filter_history_by_event(history, "take_photo")

    # Filter by position if specified
    if at_position:
        import json
        target_pos = json.loads(at_position)
        photos = [
            p for p in photos
            if _position_within_tolerance(p["position"], target_pos, tolerance)
        ]

    photo_ids = [p.get("metadata", {}).get("photo_id") for p in photos if p.get("metadata")]
    positions = [p["position"] for p in photos]

    has_photos = len(photos) >= min_count
    first_photo = min(photos, key=lambda x: x["timestamp"]) if photos else None
    last_photo = max(photos, key=lambda x: x["timestamp"]) if photos else None

    return _build_check_response(
        has_photos,
        len(photos),
        drone_id=drone_id,
        min_count=min_count,
        photo_ids=photo_ids,
        first_photo_time=first_photo["timestamp"] if first_photo else None,
        last_photo_time=last_photo["timestamp"] if last_photo else None,
        positions=positions[:10]  # Limit to first 10 positions
    )


@app.get("/check/drone_has_charged", tags=["Checks"])
async def check_drone_has_charged(
    drone_id: str,
    min_charge_amount: Optional[float] = None,
    include_auto: bool = True,
    since_timestamp: Optional[float] = None,
    _role: UserRole = Depends(require_admin)
):
    """Check if drone has charged battery (from history).

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - min_charge_amount: Minimum charge amount in percentage (optional)
    - include_auto: Include auto-charging events (default: True)
    - since_timestamp: Only check events after this timestamp (optional)

    **Response Format:**
    - Object with result boolean, count of charge events, drone_id, total_charge_received, manual_charge_count, auto_charge_count, last_charge_time

    **Notes:**
    - If min_charge_amount is specified, charges that top off to full also count even if below the minimum amount
    """
    history = _get_drone_history(drone_id)
    history = _filter_history_by_timestamp(history, since_timestamp)

    manual_charges = _filter_history_by_event(history, "charging")
    auto_charges = _filter_history_by_event(history, "auto_charging") if include_auto else []

    all_charges = manual_charges + auto_charges

    # Filter by charge amount if specified; allow top-off to full even if below minimum.
    if min_charge_amount is not None:
        filtered_charges = []
        for charge in all_charges:
            metadata = charge.get("metadata", {})
            charge_amount = metadata.get("charge_amount", 0)
            battery_after = metadata.get("battery_after")
            reached_full = battery_after is not None and float(battery_after) >= 100.0

            if charge_amount >= min_charge_amount or reached_full:
                filtered_charges.append(charge)
        all_charges = filtered_charges

    total_charge = sum(c.get("metadata", {}).get("charge_amount", 0) for c in all_charges)
    last_charge = max(all_charges, key=lambda x: x["timestamp"]) if all_charges else None

    has_charged = len(all_charges) > 0

    return _build_check_response(
        has_charged,
        len(all_charges),
        drone_id=drone_id,
        total_charge_received=round(total_charge, 2),
        manual_charge_count=len(manual_charges),
        auto_charge_count=len(auto_charges),
        last_charge_time=last_charge["timestamp"] if last_charge else None
    )


@app.get("/check/drone_has_sent_message", tags=["Checks"])
async def check_drone_has_sent_message(
    drone_id: str,
    to_drone_id: Optional[str] = None,
    min_count: int = 1,
    since_timestamp: Optional[float] = None,
    _role: UserRole = Depends(require_admin)
):
    """Check if drone has sent messages (from history).

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - to_drone_id: Filter by recipient drone ID (optional, includes broadcasts)
    - min_count: Minimum number of messages (default: 1)
    - since_timestamp: Only check events after this timestamp (optional)

    **Response Format:**
    - Object with result boolean, message_count value, drone_id, to_drone_id, min_count, recipient_drones, last_message_time
    """
    history = _get_drone_history(drone_id)
    history = _filter_history_by_timestamp(history, since_timestamp)

    messages = [e for e in history if e.get("event") in ["send_message", "broadcast"]]

    # Filter by recipient if specified
    if to_drone_id:
        messages = [
            m for m in messages
            if m.get("metadata", {}).get("target_drone_id") == to_drone_id or m.get("event") == "broadcast"
        ]

    recipient_drones = []
    for m in messages:
        target_id = m.get("metadata", {}).get("target_drone_id")
        if target_id:
            recipient_drones.append(target_id)
        elif m.get("event") == "broadcast":
            recipient_drones.append("all")
    recipient_drones = list(set(recipient_drones))

    has_sent = len(messages) >= min_count
    last_message = max(messages, key=lambda x: x["timestamp"]) if messages else None

    return _build_check_response(
        has_sent,
        len(messages),
        drone_id=drone_id,
        to_drone_id=to_drone_id,
        min_count=min_count,
        recipient_drones=recipient_drones,
        last_message_time=last_message["timestamp"] if last_message else None
    )


@app.get("/check/drone_has_sent_message_content", tags=["Checks"])
async def check_drone_has_sent_message_content(
    drone_id: str,
    content: str,
    to_drone_id: Optional[str] = None,
    min_count: int = 1,
    since_timestamp: Optional[float] = None,
    _role: UserRole = Depends(require_admin)
):
    """Check if drone has sent messages containing the requested content (from history).

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - drone_id: ID of the drone to check
    - content: Substring to search for in messages
    - to_drone_id: Filter by recipient drone ID (optional, includes broadcasts)
    - min_count: Minimum number of matching messages (default: 1)
    - since_timestamp: Only check events after this timestamp (optional)

    **Response Format:**
    - Object with result boolean, match_count value, drone_id, content, to_drone_id, min_count, recipient_drones, last_message_time, matched_messages (up to 10), match_mode="contains"
    """
    normalized_content = content.strip()
    if not normalized_content:
        raise HTTPException(status_code=400, detail="Content must be a non-empty string.")

    history = _get_drone_history(drone_id)
    history = _filter_history_by_timestamp(history, since_timestamp)

    messages = [e for e in history if e.get("event") in ["send_message", "broadcast"]]

    if to_drone_id:
        messages = [
            m for m in messages
            if m.get("metadata", {}).get("target_drone_id") == to_drone_id or m.get("event") == "broadcast"
        ]

    matched_events = []
    recipient_drones = []
    for message_event in messages:
        metadata = message_event.get("metadata", {})
        message_text = metadata.get("message")
        if not isinstance(message_text, str) or normalized_content not in message_text:
            continue

        matched_events.append(message_event)
        target_id = metadata.get("target_drone_id")
        if target_id:
            recipient_drones.append(target_id)
        elif message_event.get("event") == "broadcast":
            recipient_drones.append("all")

    recipient_drones = list(set(recipient_drones))
    has_sent = len(matched_events) >= min_count
    last_message = max(matched_events, key=lambda x: x["timestamp"]) if matched_events else None
    matched_messages = [
        event.get("metadata", {}).get("message")
        for event in matched_events[:10]
        if isinstance(event.get("metadata", {}).get("message"), str)
    ]

    return _build_check_response(
        has_sent,
        len(matched_events),
        drone_id=drone_id,
        content=normalized_content,
        to_drone_id=to_drone_id,
        min_count=min_count,
        recipient_drones=recipient_drones,
        last_message_time=last_message["timestamp"] if last_message else None,
        matched_messages=matched_messages,
        match_mode="contains"
    )


# ==================== Aggregate History/Status Check Endpoints (ADMIN only) ====================

@app.get("/check/all_drones_have_taken_off", tags=["Checks"])
async def check_all_drones_have_taken_off(
    min_altitude: float = 5.0,
    since_timestamp: Optional[float] = None,
    check_history: bool = True,
    _role: UserRole = Depends(require_admin)
):
    """Check if all drones have taken off (from history or current status).

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - min_altitude: Minimum altitude to count as takeoff (default: 5.0 meters)
    - since_timestamp: Only check events after this timestamp (optional, history mode only)
    - check_history: If True, check history; if False, check current altitude only (default: True)

    **Response Format:**
    - Object with result boolean, count of drones that have taken off, total_drones, drones_taken_off, drones_not_taken_off, percentage, check_mode, min_altitude_threshold
    """
    drones = drone_controller.get_all_drones()
    if not drones:
        return _build_check_response(
            False,
            0,
            total_drones=0,
            drones_taken_off=[],
            drones_not_taken_off=[],
            percentage=0.0,
            check_mode="history" if check_history else "current"
        )

    taken_off_drones = []
    not_taken_off_drones = []

    if check_history:
        # Check history for takeoff events
        for drone_dict in drones:
            drone_id = drone_dict["id"]
            history = _get_drone_history(drone_id)
            history = _filter_history_by_timestamp(history, since_timestamp)

            takeoffs = _filter_history_by_event(history, "take_off")
            takeoffs_above_min = [
                t for t in takeoffs
                if t.get("position", {}).get("z", 0) >= min_altitude
            ]

            if takeoffs_above_min:
                taken_off_drones.append(drone_id)
            else:
                not_taken_off_drones.append(drone_id)
    else:
        # Check current altitude
        for drone_dict in drones:
            current_altitude = drone_dict.get("position", {}).get("z", 0)
            if current_altitude >= min_altitude:
                taken_off_drones.append(drone_dict["id"])
            else:
                not_taken_off_drones.append(drone_dict["id"])

    total_drones = len(drones)
    all_taken_off = len(not_taken_off_drones) == 0
    percentage = (len(taken_off_drones) / total_drones * 100) if total_drones > 0 else 0.0

    return _build_check_response(
        all_taken_off,
        len(taken_off_drones),
        total_drones=total_drones,
        drones_taken_off=taken_off_drones,
        drones_not_taken_off=not_taken_off_drones,
        percentage=round(percentage, 2),
        check_mode="history" if check_history else "current",
        min_altitude_threshold=min_altitude
    )


@app.get("/check/all_drones_hovering", tags=["Checks"])
async def check_all_drones_hovering_aggregate(
    tolerance: float = 0.1,
    _role: UserRole = Depends(require_admin)
):
    """Check if all drones are currently hovering.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - tolerance: Altitude tolerance in meters (default: 0.1)

    **Response Format:**
    - Object with result boolean, count of hovering drones, total_drones, hovering_drones, not_hovering_drones, percentage, tolerance

    **Notes:**
    - This checks current status only (not history)
    - Alias for consistency with other aggregate endpoints
    """
    drones = drone_controller.get_all_drones()
    if not drones:
        return _build_check_response(
            False,
            0,
            total_drones=0,
            hovering_drones=[],
            not_hovering_drones=[],
            percentage=0.0,
            tolerance=tolerance
        )

    hovering_drones = [d["id"] for d in drones if _is_drone_hovering(d, tolerance)]
    not_hovering = [d["id"] for d in drones if d["id"] not in hovering_drones]
    all_hovering = len(hovering_drones) == len(drones)
    percentage = (len(hovering_drones) / len(drones) * 100) if drones else 0.0

    return _build_check_response(
        all_hovering,
        len(hovering_drones),
        total_drones=len(drones),
        hovering_drones=hovering_drones,
        not_hovering_drones=not_hovering,
        percentage=round(percentage, 2),
        tolerance=tolerance
    )


@app.get("/check/all_drones_have_landed", tags=["Checks"])
async def check_all_drones_have_landed(
    min_count: int = 1,
    since_timestamp: Optional[float] = None,
    check_history: bool = True,
    _role: UserRole = Depends(require_admin)
):
    """Check if all drones have landed (from history or current status).

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - min_count: Minimum number of landings required per drone (default: 1, history mode only)
    - since_timestamp: Only check events after this timestamp (optional, history mode only)
    - check_history: If True, check history; if False, check current status only (default: True)

    **Response Format:**
    - Object with result boolean, count of drones that have landed, total_drones, drones_landed, drones_not_landed, percentage, check_mode
    """
    drones = drone_controller.get_all_drones()
    if not drones:
        return _build_check_response(
            False,
            0,
            total_drones=0,
            drones_landed=[],
            drones_not_landed=[],
            percentage=0.0,
            check_mode="history" if check_history else "current"
        )

    landed_drones = []
    not_landed_drones = []

    if check_history:
        # Check history for landing events
        for drone_dict in drones:
            drone_id = drone_dict["id"]
            history = _get_drone_history(drone_id)
            history = _filter_history_by_timestamp(history, since_timestamp)

            landings = _filter_history_by_event(history, "land")

            if len(landings) >= min_count:
                landed_drones.append(drone_id)
            else:
                not_landed_drones.append(drone_id)
    else:
        # Check current status (on ground)
        tolerance = 0.1
        for drone_dict in drones:
            if _is_drone_on_ground(drone_dict, tolerance):
                landed_drones.append(drone_dict["id"])
            else:
                not_landed_drones.append(drone_dict["id"])

    total_drones = len(drones)
    all_landed = len(not_landed_drones) == 0
    percentage = (len(landed_drones) / total_drones * 100) if total_drones > 0 else 0.0

    return _build_check_response(
        all_landed,
        len(landed_drones),
        total_drones=total_drones,
        drones_landed=landed_drones,
        drones_not_landed=not_landed_drones,
        percentage=round(percentage, 2),
        check_mode="history" if check_history else "current",
        min_count=min_count
    )


@app.get("/check/all_drones_on_ground", tags=["Checks"])
async def check_all_drones_on_ground_aggregate(
    tolerance: float = 0.1,
    _role: UserRole = Depends(require_admin)
):
    """Check if all drones are currently on the ground.

    **Required Privileges:**
    - ADMIN: Can access this endpoint

    **Request Parameters:**
    - tolerance: Altitude tolerance in meters (default: 0.1)

    **Response Format:**
    - Object with result boolean, count of drones on ground, total_drones, drones_on_ground, drones_not_on_ground, percentage, tolerance

    **Notes:**
    - This checks current status only (not history)
    - Alias for consistency with other aggregate endpoints
    """
    drones = drone_controller.get_all_drones()
    if not drones:
        return _build_check_response(
            False,
            0,
            total_drones=0,
            drones_on_ground=[],
            drones_not_on_ground=[],
            percentage=0.0,
            tolerance=tolerance
        )

    on_ground_drones = [d["id"] for d in drones if _is_drone_on_ground(d, tolerance)]
    not_on_ground = [d["id"] for d in drones if d["id"] not in on_ground_drones]
    all_on_ground = len(on_ground_drones) == len(drones)
    percentage = (len(on_ground_drones) / len(drones) * 100) if drones else 0.0

    return _build_check_response(
        all_on_ground,
        len(on_ground_drones),
        total_drones=len(drones),
        drones_on_ground=on_ground_drones,
        drones_not_on_ground=not_on_ground,
        percentage=round(percentage, 2),
        tolerance=tolerance
    )
