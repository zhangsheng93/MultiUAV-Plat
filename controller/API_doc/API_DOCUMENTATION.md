# MultiUAV-Plat Server System API Documentation

> Comprehensive API reference for the MultiUAV-Plat Server System - A complete guide to controlling drones, managing environments, and simulating flight scenarios.

**Version:** 1.0.0
**Base URL:** `http://localhost:8000`
**Interactive Docs:** http://localhost:8000/docs

---

## Table of Contents

### Getting Started
1. [Base URL](#base-url)
2. [Authentication](#authentication)
3. [Response Format](#response-format)
4. [Quick Start Guide](#quick-start-guide)

### Core Features
5. [Automatic Charging System](#automatic-charging-system)
6. [Session Management](#session-api)
7. [Drone Control](#drone-api)
8. [Command Execution](#command-api)

### API Endpoints
9. [Session API](#session-api)
10. [Task Management API](#task-management-api)
11. [Drone API](#drone-api)
12. [Command API](#command-api)
13. [Direct Command API](#direct-command-api)
14. [Battery Management API](#battery-management-api)
15. [Target API](#target-api)
16. [Waypoint API](#waypoint-api)
17. [Environment API](#environment-api)
18. [Obstacle API](#obstacle-api)
19. [Collision Detection API](#collision-detection-api)

---

## Base URL

All API endpoints are relative to the base URL of your server deployment.

**Default:** `http://localhost:8000`

You can customize the host and port using command-line arguments:
```bash
python main.py --host 0.0.0.0 --port 8080

# Override the current-session stored request-history retention
python main.py --api-only --request-history-limit 10000
```

## Authentication

The API uses **API Key-based authentication** with role-based access control (RBAC).

### Roles

There are **four user roles**:

| Role | Access Level | Authentication Required | Permissions |
|------|-------------|------------------------|-------------|
| **AGENT** | Basic Access | No - default when `X-API-Key` is omitted or blank; optional AGENT key accepted | Can control drones and view resources with AGENT visibility limits |
| **USER** | Basic Access | Yes - provide USER API key | Inherits AGENT and can view additional scenario resources |
| **SYSTEM** | Management | Yes - provide SYSTEM API key | Can manage all resources (inherits USER/AGENT permissions) |
| **ADMIN** | Full Access | Yes - provide ADMIN API key | Full access to all endpoints |

### Authentication Header

When `X-API-Key` is omitted or left blank, requests default to the AGENT role. To use another role, include one of that role's valid keys in the `X-API-Key` header:

```bash
# Example with AGENT key
curl -H "X-API-Key: <AGENT_API_KEY>" http://localhost:8000/drones

# Example with SYSTEM key
curl -H "X-API-Key: <SYSTEM_API_KEY>" http://localhost:8000/sessions
```

**API Keys:**
- AGENT: `<AGENT_API_KEY>`
- USER: one of the hard-coded USER privilege keys
- SYSTEM: one of the hard-coded SYSTEM privilege keys
- ADMIN: one of the hard-coded ADMIN privilege keys

The actual key values are stored in the software and are intentionally omitted from the documentation.

For complete authentication details, see [AUTHENTICATION.md](AUTHENTICATION.md).

## Response Format

All API responses use JSON format with consistent structure.

### Success Response
```json
{
  "id": "drone-123",
  "name": "Scout Alpha",
  "status": "flying",
  ...
}
```

### Error Response
```json
{
  "detail": "Drone not found"
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET, PUT requests |
| 201 | Created | Successful POST requests |
| 204 | No Content | Successful DELETE requests |
| 400 | Bad Request | Invalid request parameters |
| 404 | Not Found | Resource doesn't exist |
| 500 | Internal Server Error | Server error |

## Quick Start Guide

### 1. Start the Server
```bash
python main.py --api-only
```

### 2. Verify Server is Running
```bash
curl http://localhost:8000/
# Response: {"status":"online","message":"MultiUAV-Plat Server System API is running"}
```

### 3. Check Server Version
```bash
curl http://localhost:8000/version
# Response: {"name":"MultiUAV-Plat Server System API","version":"1.0.0"}
```

### 4. Create Your First Drone
```bash
curl -X POST "http://localhost:8000/drones" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Drone",
    "model": "Quadcopter X1",
    "max_speed": 15.0,
    "max_altitude": 100.0,
    "battery_capacity": 100.0
  }'
```

### 5. Control the Drone
```bash
# Take off
curl -X POST "http://localhost:8000/drones/{drone_id}/command/take_off?altitude=10.0"

# Move to location
curl -X POST "http://localhost:8000/drones/{drone_id}/command/move_to?x=50&y=50&z=15"

# Land
curl -X POST "http://localhost:8000/drones/{drone_id}/command/land"
```

---

## Automatic Charging System

The MultiUAV-Plat Server System includes an automatic charging feature that helps maintain drone battery levels during operations without requiring manual charge commands.

### How It Works

1. **Waypoint Targets**: Create waypoint targets with `charge_amount` property to serve as charging stations
2. **Automatic Detection**: The system continuously monitors drone positions relative to waypoint targets
3. **Automatic Charging**: When a drone is **landed or idle** (not hovering) within a waypoint's radius, the system automatically charges its battery
4. **Instant Charging**: The `charge_amount` is applied instantly per update cycle (default: 25% per cycle)
5. **No Manual Command Required**: Unlike the manual `CHARGE` command, this happens automatically without user intervention
6. **Battery Management**: Charging stops when battery reaches 100% or drone leaves the waypoint radius

### Charging Requirements

For automatic charging to occur, the following conditions must be met:
- Drone must be in **IDLE** or **READY** status (landed on ground, not hovering)
- Drone must be within the waypoint target's **radius** (spherical distance check)
- Target must be of type **waypoint** with a valid `charge_amount`
- Drone battery must be below 100%

**Important:** Drones that are hovering in air will NOT charge automatically, even if within the waypoint radius. The drone must be landed.

### Waypoint Properties for Charging

Waypoint targets that serve as charging stations have these properties:
- `type`: Must be set to `waypoint`
- `radius`: Defines the charging area radius in meters (typically 5-10 meters)
- `charge_amount`: Battery percentage added per update cycle (default: 25%, range: 0.1-100%)
- `position`: Location of the charging station {x, y, z}

### Usage Example

1. Create a waypoint target with charging capability:
```bash
curl -X POST http://localhost:8000/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Charging Station Alpha",
    "type": "waypoint",
    "position": {"x": 0.0, "y": 0.0, "z": 0.0},
    "radius": 10.0,
    "charge_amount": 25.0
  }'
```

2. Land your drone within the waypoint radius (the drone will automatically charge)
3. Monitor battery levels through the Drone API - you'll see automatic increases
4. System logs will show `[AUTO-CHARGE]` messages when charging occurs

### Manual vs Automatic Charging

- **Manual Charging**: Use the `CHARGE` command with explicit `charge_amount` parameter
- **Automatic Charging**: Happens automatically when drone is landed within waypoint radius
- Both methods are instant and can charge to 100%
- Automatic charging does not prevent battery drain when active

### API Integration

The automatic charging system works with these endpoints:
- **Target API**: Create and manage waypoint charging stations
- **Drone API**: View real-time battery status and automatic charging effects
- **Command API**: Manual charging still available via `CHARGE` command if needed

## Session API

The Session API allows you to manage simulation sessions that contain all the drones, targets, obstacles, and environment data. Sessions provide a way to organize and isolate different scenarios or missions.

**Note:** When the server starts up, it automatically creates an "Example Session" with sample data including drones, targets, obstacles, and environment settings. This ensures that the system is ready to use immediately without requiring manual session creation.

### Get All Sessions

**Endpoint:** `GET /sessions`

**Authentication:** Requires USER role (SYSTEM and ADMIN inherit)

**Description:** Retrieves a list of all sessions in the system. For AGENT/USER roles, returns metadata only (no history, no entity data). For SYSTEM/ADMIN roles, returns full session metadata.

**Parameters:** None

**Response:** Array of session objects

**Example Request:**
```bash
curl -X GET http://localhost:8000/sessions
```

**Example Response:**
```json
[
  {
    "id": "session-123e4567-e89b-12d3-a456-426614174000",
    "name": "Example Session",
    "description": "A comprehensive example session with drones, targets, obstacles, and environment setup",
    "status": "active",
    "task_type": "area_search",
    "task_description": "Search designated areas for targets of interest",
    "created_at": 1620000000.0,
    "last_updated": 1620000100.0,
    "statistics": {
      "drone_count": 3,
      "target_count": 6,
      "obstacle_count": 6,
      "environment_id": "env-456",
      "commands_executed": 15,
      "total_flight_time": 120.5,
      "total_distance_traveled": 450.2
    }
  }
]
```

### Create a New Session

**Endpoint:** `POST /sessions`

**Description:** Creates a new session with auto-generated ID. Can optionally include drones, targets, obstacles, and environment data to be created along with the session.

**Request Body Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | Yes | Name of the session |
| description | string | No | Description of the session |
| with_examples | boolean | No | Whether to create example data (default: false) |
| task_type | string | No | Task type: 'area_search', 'area_assignment_and_patrol', 'target_assignment', 'target_tracking', or 'others' (default: 'others') |
| task_description | string | No | Detailed description of the task/mission |
| is_distance_3d | boolean | No | Whether to use 3D distance for calculations (default: false) |
| canvas_width | number | No | Width of the simulation canvas in meters (default: 1024.0) |
| canvas_height | number | No | Height of the simulation canvas in meters (default: 768.0) |
| creator | string | No | Name of the user creating the session; defaults to the caller's role if omitted |
| drones | array | No | Array of drone objects to create (default: []) |
| targets | array | No | Array of target objects to create (default: []) |
| obstacles | array | No | Array of obstacle objects to create (default: []) |
| environment | object | No | Environment object to create (default: null) |

If `creator` is not provided, the server records the caller's role as the creator.

**Query Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| data | boolean | No | true | If true, returns complete session data including all created entities. If false, returns session metadata only. |

**Response:** Session object

**Example Request (Simple Session):**
```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "name": "My Custom Session",
    "description": "A custom session for testing",
    "creator": "planner-ops",
    "with_examples": false,
    "task_type": "target_tracking",
    "task_description": "Track and monitor moving targets"
  }'
```

**Example Response:**
```json
{
  "id": "session-789a0123-b456-78c9-d012-345678901234",
  "name": "My Custom Session",
  "description": "A custom session for testing",
  "status": "active",
  "creator": "planner-ops",
  "task_type": "target_tracking",
  "task_description": "Track and monitor moving targets",
  "created_at": 1620000200.0,
  "last_updated": 1620000200.0,
  "statistics": {
    "drone_count": 0,
    "target_count": 0,
    "obstacle_count": 0,
    "environment_id": null
  }
}
```

**Example Request (With Entities):**
```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "name": "Mission with Fleet",
    "description": "Pre-configured mission",
    "drones": [
      {
        "name": "Scout-1",
        "model": "Model-D4",
        "max_speed": 20.0,
        "max_altitude": 120.0,
        "battery_capacity": 4000.0,
        "position": {"x": 0, "y": 0, "z": 0}
      }
    ],
    "targets": [
      {
        "name": "Waypoint Alpha",
        "type": "fixed",
        "position": {"x": 100, "y": 100, "z": 0},
        "radius": 5.0
      }
    ]
  }'
```

**Example Response:**
```json
{
  "id": "session-abc456",
  "name": "Mission with Fleet",
  "description": "Pre-configured mission",
  "status": "active",
  "creator": "system",
  "task_type": "others",
  "task_description": "",
  "created_at": 1620000200.0,
  "last_updated": 1620000200.0,
  "statistics": {
    "drone_count": 1,
    "target_count": 1,
    "obstacle_count": 0,
    "environment_id": null,
    "total_commands_executed": 0,
    "total_flight_time": 0.0,
    "total_distance_traveled": 0.0,
    "session_time": 0.0
  }
}
```

---

### Create/Restore Session with Specific ID

**Endpoint:** `POST /sessions/{session_id}`

**Description:** Creates or restores a session with a specific ID. Perfect for restoring sessions from backups. If the request body includes drones, targets, obstacles, or environment data, they will be automatically created/restored.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | The specific ID to use for the session |

**Request Body Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | Yes | Name of the session |
| description | string | No | Description of the session |
| status | string | No | Session status (default: 'active') |
| task_type | string | No | Task type (default: 'others') |
| task_description | string | No | Detailed task description |
| is_distance_3d | boolean | No | Use 3D distance for calculations (default: false) |
| canvas_width | number | No | Simulation canvas width in meters (default: 1024.0) |
| canvas_height | number | No | Simulation canvas height in meters (default: 768.0) |
| creator | string | No | Name of the user creating/restoring the session; defaults to the caller's role if omitted |
| drones | array | No | Array of drone objects to restore (default: []) |
| targets | array | No | Array of target objects to restore (default: []) |
| obstacles | array | No | Array of obstacle objects to restore (default: []) |
| environment | object | No | Environment object to restore (default: null) |

If `creator` is not provided, the server records the caller's role as the creator.

**Query Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| data | boolean | No | true | If true, returns complete session data. If false, returns metadata only. |

**Response:** Session object (metadata only by default, or complete data if `data=true`)

**Errors:**
- **500 Internal Server Error:** If deletion of existing session fails

**Example Request (Restore from Backup):**
```bash
curl -X POST "http://localhost:8000/sessions/mission-backup-2024?data=true" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "name": "Restored Mission",
    "description": "Restored from backup",
    "creator": "planner-ops",
    "drones": [
      {
        "id": "drone-original-001",
        "name": "Scout Alpha",
        "model": "Model-D4",
        "position": {"x": 50, "y": 30, "z": 15},
        "battery_level": 85.5
      }
    ],
    "targets": [
      {
        "id": "target-original-001",
        "name": "Search Zone",
        "type": "circle",
        "position": {"x": 100, "y": 100, "z": 0},
        "radius": 25.0
      }
    ],
    "obstacles": [],
    "environment": {
      "name": "Clear Weather",
      "weather": "clear",
      "temperature": 22.0,
      "humidity": 45.0
    }
  }'
```

**Example Response (Complete Data - Flat Format):**
```json
{
  "id": "mission-backup-2024",
  "name": "Restored Mission",
  "description": "Restored from backup",
  "status": "active",
  "creator": "planner-ops",
  "task_type": "others",
  "task_description": "",
  "created_at": 1620000300.0,
  "last_updated": 1620000300.0,
  "statistics": {
    "drone_count": 1,
    "target_count": 1,
    "obstacle_count": 0,
    "environment_id": "env-restored-001",
    "total_commands_executed": 0,
    "total_flight_time": 0.0,
    "total_distance_traveled": 0.0,
    "session_time": 0.0,
    "task_progress": {...}
  },
  "drones": [
    {
      "id": "drone-original-001",
      "name": "Scout Alpha",
      "model": "Model-D4",
      "status": "hovering",
      "position": {"x": 50, "y": 30, "z": 15},
      "battery_level": 85.5
    }
  ],
  "targets": [
    {
      "id": "target-original-001",
      "name": "Search Zone",
      "type": "circle",
      "position": {"x": 100, "y": 100, "z": 0},
      "radius": 25.0
    }
  ],
  "obstacles": [],
  "environment": {
    "id": "env-restored-001",
    "name": "Clear Weather",
    "weather": "clear",
    "temperature": 22.0,
    "humidity": 45.0
  },
  "history": {
    "command_history": [],
    "status_history": {},
    "target_reaches": {},
    "area_coverage": {},
    "path_history": {}
  }
}
```



**Behavior:**
- If session exists: Deletes existing session, then creates new one with same ID (automatic overwrite)
- If session does not exist: Creates new session with the specified ID
- Use this endpoint when restoring from backups to replace existing sessions

---

### Get Current Session

**Endpoint:** `GET /sessions/current`

**Description:** Retrieves the current active session. By default returns metadata and statistics only. Use the `data` parameter to get complete session data including all drones, targets, obstacles, and environment.

**Query Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| data | boolean | No | false | If true, returns complete session data including all entities. If false, returns metadata and statistics only. |

**Response:** Current session object (metadata only by default, or complete data if `data=true`)

**Response Fields (when data=false, default):**
- All standard session fields (id, name, description, status, etc.)
- `statistics`: Session statistics including drone count, flight time, etc.
- `task_progress`: Real-time task completion progress (task_type, progress_percentage, is_completed, status_message, details)

**Response Fields (when data=true):**
- `session`: Session metadata and statistics
- `drones`: Array of all drones with current state
- `targets`: Array of all targets (fixed, moving, waypoint, circle, polygon)
- `obstacles`: Array of all obstacles
- `environment`: Current environment settings

**Example Request (Metadata Only):**
```bash
curl -X GET http://localhost:8000/sessions/current
# or explicitly
curl -X GET "http://localhost:8000/sessions/current?data=false"
```

**Example Response:**
```json
{
  "id": "session-abc123",
  "name": "Area Search Mission",
  "description": "Urban search and rescue operation",
  "is_distance_3d": false,
  "canvas_width": 1024.0,
  "canvas_height": 768.0,
  "created_at": 1705449600.0,
  "last_updated": 1705449700.0,
  "statistics": {
    "drone_count": 3,
    "target_count": 5,
    "obstacle_count": 8,
    "environment_id": "env-456",
    "total_commands_executed": 127,
    "total_flight_time": 450.5,
    "total_distance_traveled": 2340.8,
    "total_target_reaches": 15,
    "drones_with_target_reaches": 3,
    "unique_targets_reached": 5,
    "session_time": 3600.0,
    "command_history_size": 127,
    "target_reach_log_size": 15,
    "task_progress": {
      "task_type": "area_search",
      "progress_percentage": 45,
      "is_completed": false,
      "status_message": "Task to be Done",
      "details": {
        "total_targets": 2,
        "average_coverage": 45.5,
        "coverage_by_target": {
          "target-abc": 50.0,
          "target-def": 41.0
        }
      },
      "target_reach_summary": {
        "total_reaches": 15,
        "drones_with_reaches": 3,
        "unique_targets_reached": 5
      },
      "area_coverage_summary": {
        "total_targets_tracked": 2,
        "average_coverage": 45.5,
        "fully_covered_targets": 0
      }
    }
  },
  "history": {
    "target_reaches": {
      "drone-001": {
        "target-abc": [1705449650.0, 1705449750.0],
        "target-def": [1705449800.0]
      }
    },
    "area_coverage": {
      "target-abc": {
        "area_type": "circle",
        "total_area": 1000.0,
        "covered_area": 500.0,
        "coverage_percentage": 50.0,
        "covered_points": [[10,10], [11,10]]
      }
    },
    "command_history": [
      {
        "drone_id": "drone-001",
        "command": "move_to",
        "parameters": {"x": 50.0, "y": 50.0, "z": 15.0},
        "timestamp": 1705449750.0
      }
    ],
    "status_history": {},
    "path_history": {}
  }
}
```

**Example Request (Complete Data):**
```bash
curl -X GET "http://localhost:8000/sessions/current?data=true"
```

**Example Response (Complete Data - Flat Format):**
```json
{
  "id": "session-abc123",
  "name": "Area Search Mission",
  "description": "Urban search and rescue operation",
  "status": "active",
  "creator": "system",
  "task_type": "area_search",
  "task_description": "Search grid zones for targets",
  "is_distance_3d": false,
  "canvas_width": 1024.0,
  "canvas_height": 768.0,
  "created_at": 1705449600.0,
  "last_updated": 1705449700.0,
  "statistics": {
    "drone_count": 3,
    "target_count": 5,
    "obstacle_count": 8,
    "environment_id": "env-456",
    "total_commands_executed": 25,
    "total_flight_time": 450.5,
    "total_distance_traveled": 1250.75,
    "session_time": 600.0,
    "task_progress": {
      "task_type": "area_search",
      "progress_percentage": 45,
      "is_completed": false,
      "status_message": "Task to be Done",
      "details": {
        "total_targets": 5,
        "average_coverage": 45.2
      },
      "target_reach_summary": {
        "total_reaches": 0,
        "drones_with_reaches": 0,
        "unique_targets_reached": 0
      },
      "area_coverage_summary": {
        "total_targets_tracked": 5,
        "average_coverage": 45.2,
        "fully_covered_targets": 0
      }
    }
  },
  "history": {
    "target_reaches": {},
    "area_coverage": {},
    "command_history": [],
    "status_history": {},
    "path_history": {}
  },
  "drones": [
    {
      "id": "drone-001",
      "name": "Scout Alpha",
      "model": "QuadX-450 Pro",
      "status": "hovering",
      "position": {"x": 50.0, "y": 30.0, "z": 15.0},
      "battery_level": 85.5
    }
  ],
  "targets": [
    {
      "id": "target-001",
      "name": "Search Zone Alpha",
      "type": "circle",
      "position": {"x": 100.0, "y": 100.0, "z": 0.0},
      "radius": 25.0
    }
  ],
  "obstacles": [
    {
      "id": "obstacle-001",
      "name": "Building A",
      "type": "circle",
      "position": {"x": 150.0, "y": 150.0, "z": 0.0},
      "radius": 15.0,
      "height": 30.0
    }
  ],
  "environment": {
    "id": "env-456",
    "name": "Clear Weather",
    "weather": "clear",
    "temperature": 22.0,
    "humidity": 45.0
  }
}
```

### Get Current Session Data (Convenience Endpoint)

**Endpoint:** `GET /sessions/current/data`

**Description:** Convenience endpoint that returns complete session data for the current active session. This is equivalent to `GET /sessions/current?data=true`.

**Authentication:** Requires SYSTEM role or higher

**Query Parameters:** None

**Response:** Complete session data object including all drones, targets, obstacles, and environment.

**Example Request:**
```bash
curl -X GET http://localhost:8000/sessions/current/data
```

**Example Response:**
Same structure as `GET /sessions/current?data=true` response above.

### Get a Specific Session

**Endpoint:** `GET /sessions/{session_id}`

**Description:** Retrieves information about a specific session. By default returns metadata and statistics only. Use the `data` parameter to get complete session data including all drones, targets, obstacles, and environment.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | ID of the session (in URL path) |

**Query Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| data | boolean | No | false | If true, returns complete session data including all entities. If false, returns metadata and statistics only. |

**Response:** Session object (metadata only by default, or complete data if `data=true`)

**Response Fields (when data=false, default):**
- All standard session fields (id, name, description, status, task, etc.)
- `statistics`: Comprehensive session statistics
- `task_progress`: Real-time task completion progress

**Response Fields (when data=true):**
- `session`: Session metadata and statistics
- `drones`: Array of all drones with current state
- `targets`: Array of all targets (fixed, moving, waypoint, circle, polygon)
- `obstacles`: Array of all obstacles
- `environment`: Current environment settings
- `history`: Object containing:
  - `command_history`: Array of executed commands
  - `status_history`: Drone status logs
  - `target_reaches`: Compact reach history grouped by drone and by target, including counts and recent timestamps
  - `moving_target_tracking`: Compact moving-target tracking history including status, total tracking events, and recent tracking periods
  - `area_coverage`: Area coverage tracking data
  - `path_history`: Drone movement traces/trajectories

**Example Request (Metadata Only):**
```bash
curl -X GET http://localhost:8000/sessions/session-abc123
# or explicitly
curl -X GET "http://localhost:8000/sessions/session-abc123?data=false"
```

**Example Response (Metadata Only):**
Same structure as "Get Current Session" metadata response above.

**Example Request (Complete Data):**
```bash
curl -X GET "http://localhost:8000/sessions/session-abc123?data=true"
```

**Example Response (Complete Data):**
Same structure as "Get Current Session" complete data response above.

### Update a Session

**Endpoint:** `PUT /sessions/{session_id}`

**Description:** Updates a session's metadata (name, description, status). This endpoint only updates session metadata - to update drones, targets, or obstacles, use their respective endpoints.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | ID of the session (in URL path) |

**Request Body Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | No | New name for the session |
| description | string | No | New description for the session |
| status | string | No | New status (active, paused, completed, archived) |
| is_distance_3d | boolean | No | Whether to use 3D distance for calculations |
| canvas_width | number | No | New width for the simulation canvas |
| canvas_height | number | No | New height for the simulation canvas |

**Query Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| data | boolean | No | false | If true, returns complete session data. If false, returns metadata only. |

**Response:** Updated session object (metadata only by default, or complete data if `data=true`)

**Example Request (Metadata Only):**
```bash
curl -X PUT http://localhost:8000/sessions/session-abc123 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "name": "Updated Mission Session",
    "status": "completed",
    "is_distance_3d": true
  }'
```

**Example Response (Metadata Only):**
```json
{
  "id": "session-abc123",
  "name": "Updated Mission Session",
  "description": "Original description",
  "status": "completed",
  "is_distance_3d": true,
  "canvas_width": 1024.0,
  "canvas_height": 768.0,
  "created_at": 1620000200.0,
  "last_updated": 1620000500.0,
  "statistics": {
    "drone_count": 3,
    "target_count": 5
  }
}
```

**Example Request (With Complete Data):**
```bash
curl -X PUT "http://localhost:8000/sessions/session-abc123?data=true" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "name": "Mission Complete",
    "status": "completed"
  }'
```

**Example Response (Complete Data - Flat Format):**
```json
{
  "id": "session-abc123",
  "name": "Mission Complete",
  "description": "Original description",
  "status": "completed",
  "creator": "system",
  "task_type": "area_search",
  "task_description": "Search grid zones for targets",
  "created_at": 1620000200.0,
  "last_updated": 1620000600.0,
  "statistics": {
    "drone_count": 3,
    "target_count": 5,
    "obstacle_count": 2,
    "environment_id": "env-456",
    "task_progress": {...}
  },
  "target_reaches": {},
  "drones": [...],
  "targets": [...],
  "obstacles": [...],
  "environment": {...},
  "history": {
    "command_history": [...],
    "status_history": {...},
    "target_reaches": {},
    "area_coverage": {...}
  }
}
```

### Delete a Session

**Endpoint:** `DELETE /sessions/{session_id}`

**Description:** Deletes a session from the system.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | ID of the session (in URL path) |

**Response:** No content (204)

**Example Request:**
```bash
curl -X DELETE http://localhost:8000/sessions/session-123e4567-e89b-12d3-a456-426614174000
```

### Set Current Session

**Endpoint:** `POST /sessions/{session_id}/set-current`

**Authentication:** Requires USER role (SYSTEM and ADMIN inherit)

**Description:** Sets a session as the current active session. For AGENT/USER roles, returns metadata only (no history, no entity data). For SYSTEM/ADMIN roles, returns full session metadata.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | ID of the session (in URL path) |

**Response:** Session object (metadata only for AGENT/USER roles)

**Example Request:**
```bash
curl -X POST http://localhost:8000/sessions/session-123e4567-e89b-12d3-a456-426614174000/set-current
```

### Reset a Session

**Endpoint:** `POST /sessions/{session_id}/reset`

**Description:** Resets the session to its initial state. Clears drones, targets, obstacles, environment, statistics, command/status histories, and timer while preserving the session ID, name, and description. If the session is active, also clears all controllers.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | ID of the session (in URL path) |

**Response:** Reset session object

**Example Request:**
```bash
curl -X POST http://localhost:8000/sessions/session-123e4567-e89b-12d3-a456-426614174000/reset
```

### Reset Current Session

**Endpoint:** `POST /sessions/current/reset`

**Description:** Resets the current active session to its initial state. This endpoint clears all history tracking data while preserving the session entities and configuration.

**What Gets Cleared:**
- Command history (all commands sent to drones)
- Status history (drone status change records)
- Path history (drone movement traces/trajectories)
- Target reach logs (records of when drones reached targets)
- Area coverage data (coverage tracking for area search tasks)
- Statistics (total commands executed, flight time, distance traveled)
- Session timer (resets to 0)

**What Gets Preserved:**
- Session ID, name, and description
- All drones with their current positions and states
- All targets
- All obstacles
- Environment configuration
- Task definitions

**Authentication:** Requires SYSTEM role or higher

**Response:** Reset session object

**Example Request:**
```bash
curl -X POST http://localhost:8000/sessions/current/reset
```

**Example Response:**
```json
{
  "id": "session-123e4567-e89b-12d3-a456-426614174000",
  "name": "Current Session",
  "description": "Active session for testing",
  "status": "active",
  "task_type": "area_search",
  "task_description": "Search designated areas",
  "creator": "system",
  "created_at": 1734000000.0,
  "last_updated": 1734001234.5,
  "total_commands_executed": 0,
  "total_flight_time": 0.0,
  "total_distance_traveled": 0.0,
  "session_time": 0.0,
  "num_drones": 3,
  "num_targets": 5,
  "num_obstacles": 2,
  "has_environment": true
}
```

### Get Session Data

**Endpoint:** `GET /sessions/{session_id}/data`

**Description:** Convenience endpoint that retrieves complete session data including all drones, targets, obstacles, and environment. This is equivalent to `GET /sessions/{session_id}?data=true`.

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | ID of the session (in URL path) |

**Query Parameters:** None

**Response:** Complete session data object

**Example Request:**
```bash
curl -X GET http://localhost:8000/sessions/session-123e4567-e89b-12d3-a456-426614174000/data
```

**Example Response (Flat Format):**
```json
{
  "id": "session-123e4567-e89b-12d3-a456-426614174000",
  "name": "Example Session",
  "description": "A comprehensive example session",
  "status": "active",
  "creator": "system",
      "task_type": "area_search",
      "task_description": "Search designated areas for targets",
          "is_distance_3d": false,
          "canvas_width": 1024.0,
          "canvas_height": 768.0,
          "created_at": 1620000000.0,  "last_updated": 1620000100.0,
  "statistics": {
    "drone_count": 3,
    "target_count": 6,
    "obstacle_count": 6,
    "environment_id": "env-456",
    "total_commands_executed": 15,
    "total_flight_time": 120.5,
    "total_distance_traveled": 450.2,
    "session_time": 300.0,
    "task_progress": {...}
  },
  "target_reaches": {},
  "target_reach_statistics": {...},
  "area_coverage_summary": {...},
  "recent_commands": [...],
  "drones": [
    {
      "id": "drone-001",
      "name": "Scout Alpha",
      "model": "QuadX-450 Pro",
      "status": "idle",
      "position": {"x": 10.0, "y": 10.0, "z": 0.0},
      "battery_level": 100.0
    }
  ],
  "targets": [
    {
      "id": "target-001",
      "name": "Primary Landing Zone",
      "type": "fixed",
      "position": {"x": 100.0, "y": 100.0, "z": 0.0}
    }
  ],
  "obstacles": [
    {
      "id": "obstacle-001",
      "name": "Corporate Headquarters",
      "type": "building",
      "position": {"x": 120.0, "y": 180.0, "z": 0.0}
    }
  ],
  "environment": {
    "id": "env-456",
    "name": "Clear Weather Environment",
    "weather": "clear",
    "temperature": 22.0,
    "humidity": 45.0
  },
  "history": {
    "target_reaches": {},
    "area_coverage": {},
    "command_history": [...],
    "status_history": {}
  }
}
```

### Session Screenshots

Provides rendered screenshots of the current session UI in PNG, JPG, PDF, SVG, or EPS formats. Useful for reporting, quick previews, and exporting visual state.

#### Get Current Session Screenshot

- Endpoint: `GET /sessions/current/screenshot`
- Description: Returns a screenshot of the current active session UI.
- Query Parameters:
  - `format` (string, optional): One of `png`, `jpg`, `jpeg`, `pdf`, `svg`, `eps` (default: `png`).
  - `width` (integer, optional): Image width in pixels (default: `1024`).
  - `height` (integer, optional): Image height in pixels (default: `768`).
  - `center_x` (float, optional): Canvas center X coordinate in meters.
  - `center_y` (float, optional): Canvas center Y coordinate in meters.
  - `scale_px_per_meter` (float, optional): Canvas scale in pixels per meter.
  - `show_status` (boolean, optional): When `true`, includes drone path traces, area-search coverage overlays, reached/tracked target state, and the status bar metadata shown by the UI. Defaults to `false`.
  - `show_label` (boolean, optional): When `false`, hides object labels for drones, targets, and obstacles. Defaults to `true`.
- Response: Binary image/vector content. Media type is `image/png`, `image/jpeg`, `application/pdf`, `image/svg+xml`, or `application/postscript` depending on `format`.

Example requests:

```bash
# PNG
curl -X GET "http://localhost:8000/sessions/current/screenshot?format=png&width=1024&height=768" \
  --output current_session.png

# JPG
curl -X GET "http://localhost:8000/sessions/current/screenshot?format=jpg" \
  --output current_session.jpg

# PDF
curl -X GET "http://localhost:8000/sessions/current/screenshot?format=pdf" \
  --output current_session.pdf

# SVG with status overlays
curl -X GET "http://localhost:8000/sessions/current/screenshot?format=svg&show_status=true" \
  --output current_session.svg

# SVG without object labels
curl -X GET "http://localhost:8000/sessions/current/screenshot?format=svg&show_label=false" \
  --output current_session_no_labels.svg

# EPS with status overlays
curl -X GET "http://localhost:8000/sessions/current/screenshot?format=eps&show_status=true" \
  --output current_session.eps
```

#### Get Screenshot for Specific Session

- Endpoint: `GET /sessions/{session_id}/screenshot`
- Description: Returns a screenshot for the specified session.
- Path Parameters:
  - `session_id` (string, required): Session ID to render.
- Query Parameters:
  - `format` (string, optional): One of `png`, `jpg`, `jpeg`, `pdf`, `svg`, `eps` (default: `png`).
  - `width` (integer, optional): Image width in pixels (default: `1024`).
  - `height` (integer, optional): Image height in pixels (default: `768`).
  - `center_x` (float, optional): Canvas center X coordinate in meters.
  - `center_y` (float, optional): Canvas center Y coordinate in meters.
  - `scale_px_per_meter` (float, optional): Canvas scale in pixels per meter.
  - `show_status` (boolean, optional): When `true`, includes drone path traces, area-search coverage overlays, reached/tracked target state, and the status bar metadata shown by the UI. Defaults to `false`.
  - `show_label` (boolean, optional): When `false`, hides object labels for drones, targets, and obstacles. Defaults to `true`.
- Response: Binary image/vector content. Media type is `image/png`, `image/jpeg`, `application/pdf`, `image/svg+xml`, or `application/postscript` depending on `format`.

Example request:

```bash
curl -X GET "http://localhost:8000/sessions/session-123e4567-e89b-12d3-a456-426614174000/screenshot?format=png&width=1280&height=720" \
  --output session_123e4567.png

curl -X GET "http://localhost:8000/sessions/session-123e4567-e89b-12d3-a456-426614174000/screenshot?format=svg&show_status=true" \
  --output session_123e4567.svg

curl -X GET "http://localhost:8000/sessions/session-123e4567-e89b-12d3-a456-426614174000/screenshot?format=svg&show_label=false" \
  --output session_123e4567_no_labels.svg
```

### Session Tracking

Additional endpoints provide rich tracking data for each session, including command history, status changes, target reaches, and area coverage.

#### Get Command History

- Endpoint: `GET /sessions/{session_id}/command-history`
- Current-session endpoint: `GET /sessions/current/command-history`
- Query Parameters:
  - `limit` (integer, optional): Maximum number of recent commands to return (default: `100`, max: `1000`).
- Response: `{ "command_history": [ ... ] }` containing the most recent commands for the session.
- The current-session endpoint returns `404` with `"No current session found"` when no session is active.

Examples:
```bash
curl -X GET "http://localhost:8000/sessions/session-123e4567/command-history?limit=50"

curl -X GET "http://localhost:8000/sessions/current/command-history?limit=50"
```

#### Get Request History

- Endpoints:
  - `GET /sessions/current/request-history`
  - `GET /sessions/{session_id}/request-history`
- Required privilege:
  - `GET /sessions/current/request-history`: AGENT, SYSTEM, or ADMIN.
  - `GET /sessions/{session_id}/request-history`: SYSTEM or ADMIN.
- Query Parameters:
  - `limit` (integer, optional): Maximum number of recent requests to return. If omitted, all retained request-history records are returned.
- AGENT callers should send a stable non-secret `X-Agent-ID` header. If omitted, AGENT requests are attributed to `default_agent`.
- AGENT callers can retrieve only current-session request history records from AGENT-authenticated requests with the same `agent_id`. SYSTEM and ADMIN callers receive unfiltered request history for sessions that still have runtime history.
- The server stores request history only for the current session. Non-current sessions discard request history by default, and switching the current session clears request history from all sessions except the newly current one.
- The server stores up to `5000` current-session records by default. This retention is configurable at startup with `--request-history-limit`; it bounds how many records can be returned when `limit` is omitted.
- Response: `{ "request_history": [ ... ] }` in chronological order.
- Records are associated with the session active after each response completes. Requests made without an active session are not added to session history.
- Request history is runtime-only. It is not included in session objects, JSON exports, imports, or restores, and is lost when the process restarts.
- Session reset clears the runtime request history.
- `GET /sessions/current/data` is not recorded in request history.
- Calls to these endpoints are recorded after their responses are produced, with `response_body: null`, so they appear in the next query without recursively embedding prior history.
- Structured API logs do not store full response bodies. They record `response_size_bytes`, `response_body_type`, and `response_body_summary` instead. Large response paths such as session-data endpoints, screenshot endpoints, and request-history endpoints omit response body capture.
- Request-history endpoint response bodies are intentionally omitted from session request-history records for performance and recursion safety.

Each record has this shape:

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-06-23T10:30:00Z",
  "method": "POST",
  "path": "/drones/drone-1/command",
  "client_ip": "127.0.0.1",
  "client_port": 54321,
  "client_privilege": "ADMIN",
  "authentication_status": "api_key",
  "session_id": "session-123e4567",
  "query_params": {
    "tag": ["alpha", "beta"],
    "limit": "10"
  },
  "user_agent": "client-name/1.0",
  "agent_id": "agent-alpha",
  "request_body": {
    "command": "take_off",
    "parameters": {"altitude": 10}
  },
  "status_code": 200,
  "success": true,
  "duration_sec": 0.123,
  "response_body": {},
  "error": null
}
```

- `client_ip` and `client_port` identify the direct socket peer. Forwarded IP headers are not trusted.
- `client_privilege` is `AGENT`, `USER`, `SYSTEM`, `ADMIN`, or `null`.
- `authentication_status` is `api_key`, `default_agent`, or `invalid`.
- `agent_id` is the normalized `X-Agent-ID` value for AGENT requests, `default_agent` for AGENT requests without that header, and `null` for non-AGENT or legacy records.
- `query_params` preserves raw query-string values for replay. Keys supplied once use string values; repeated keys use ordered arrays; requests without a query string use `{}`.
- Sensitive query keys are redacted case-insensitively using the same policy as request and response bodies.
- Runtime records missing `query_params` are exposed as `{}`.
- `user_agent` is capped at 512 characters.
- API keys and unrestricted request headers are never included.
- Sensitive keys, secrets, passwords, and tokens in request or response bodies are redacted. Binary screenshot bodies are not stored.

Examples:

```bash
curl -X GET "http://localhost:8000/sessions/current/request-history?limit=1000" \
  -H "X-API-Key: <AGENT_API_KEY>" \
  -H "X-Agent-ID: agent-alpha"

curl -X GET "http://localhost:8000/sessions/session-123e4567/request-history?limit=100" \
  -H "X-API-Key: <SYSTEM_API_KEY>"
```

#### Clear Request History

- Endpoints:
  - `DELETE /sessions/current/request-history`
  - `DELETE /sessions/{session_id}/request-history`
- Required privilege: SYSTEM or ADMIN.
- Description: Clears only runtime request history for the selected session. It does not reset the session, clear command history, status history, path history, task progress, entities, statistics, or the configured request-history retention limit.
- The clear request itself is not recorded back into request history.
- Response:

```json
{
  "cleared": true,
  "session_id": "session-123e4567",
  "cleared_count": 42
}
```

Examples:

```bash
curl -X DELETE "http://localhost:8000/sessions/current/request-history" \
  -H "X-API-Key: <SYSTEM_API_KEY>"

curl -X DELETE "http://localhost:8000/sessions/session-123e4567/request-history" \
  -H "X-API-Key: <SYSTEM_API_KEY>"
```

#### Get Status History

- Endpoint: `GET /sessions/{session_id}/status-history`
- Query Parameters:
  - `drone_id` (string, optional): If provided, filters status history to a specific drone.
- Response: `{ "status_history": { "drone_id": [ ... ] } }` or all drones if `drone_id` is not provided.

Example:
```bash
curl -X GET "http://localhost:8000/sessions/session-123e4567/status-history?drone_id=drone-001"
```

#### Get Target Reaches

- Endpoint: `GET /sessions/{session_id}/target-reaches`
- Description: Returns compact target reach history and aggregated statistics. **Multiple visits** to the same target are still recorded, but they are grouped into summaries instead of returned as a raw event log.
- Response:
  - `target_reaches.by_drone`: Per-drone map of reached targets with `count`, `first_reached_at`, `last_reached_at`, and `recent_reached_at`
  - `target_reaches.by_target`: Per-target map with `total_reaches`, `unique_drones`, `reached_by`, `first_reached_at`, `last_reached_at`, and `recent_reached_at`
  - `summary`: Aggregates including `total_reaches`, `drones_with_reaches`, and `unique_targets_reached`
- **Note**: This endpoint is intentionally compact. It does not return every historical event as a standalone record.

Example:
```bash
curl -X GET "http://localhost:8000/sessions/session-123e4567/target-reaches"
```

Example Response:
```json
{
  "target_reaches": {
    "by_drone": {
      "drone-001": {
        "target-abc": {
          "count": 3,
          "first_reached_at": 1705449650.0,
          "last_reached_at": 1705449850.0,
          "recent_reached_at": [1705449650.0, 1705449750.0, 1705449850.0]
        }
      }
    },
    "by_target": {
      "target-abc": {
        "total_reaches": 4,
        "unique_drones": 2,
        "reached_by": ["drone-001", "drone-002"],
        "first_reached_at": 1705449650.0,
        "last_reached_at": 1705449850.0,
        "recent_reached_at": [1705449700.0, 1705449750.0, 1705449850.0]
      }
    }
  },
  "summary": {
    "total_reaches": 4,
    "drones_with_reaches": 2,
    "unique_targets_reached": 1
  }
}
```

#### Get Moving Target Tracking

- Endpoint: `GET /sessions/{session_id}/moving-target-tracking`
- Description: Returns compact moving-target tracking history for the specified session.
- Response:
  - `moving_target_tracking.{target_id}.tracking_status`: `tracked`, `stale`, or `never_tracked`
  - `moving_target_tracking.{target_id}.first_tracked_at` / `last_tracked_at`
  - `moving_target_tracking.{target_id}.total_track_events`
  - `moving_target_tracking.{target_id}.tracked_by`
  - `moving_target_tracking.{target_id}.recent_periods`: Recent tracking periods with `start_at`, `end_at`, `last_update_at`, `event_count`, `last_tracked_by`, and `tracked_by`
  - `moving_target_tracking.{target_id}.by_drone.{drone_id}`: Compact per-drone tracking summary with `first_tracked_at`, `last_tracked_at`, `total_track_events`, and `recent_periods`
- **Note**: Tracking data is period-based and recent-history oriented. It is not an unbounded raw event stream.

#### Get Area Coverage

- Endpoint: `GET /sessions/{session_id}/area-coverage`
- Description: Returns area coverage tracking and a summarized view per target.
- Response:
  - `area_coverage`: Map of `target_id` to coverage data `{area_type, total_area, covered_area, coverage_percentage, covered_points}`.
  - `summary`: Aggregates including `total_targets_tracked`, `average_coverage`, `fully_covered_targets`, `coverage_by_target` (with `num_covered_points`).

Example:
```bash
curl -X GET "http://localhost:8000/sessions/session-123e4567/area-coverage"
```

#### Get Task Progress

- Endpoint: `GET /sessions/{session_id}/task-progress`
- Description: Returns task completion progress based on the session's task type. Progress calculation varies by task type:
  - **area_search** / **area_assignment_and_patrol**: Percentage of area explored by drones (completed at ≥90%)
  - **target_assignment**: Percentage of targets visited at least once within task_radius (completed at 100%)
  - **target_tracking**: Percentage of targets currently tracked. For moving targets, "currently tracked" is backend-derived from a freshness window on tracked events (completed when all targets have been tracked at least once)
  - **others**: No progress tracking
- Response:
  - `task_type`: The type of task (e.g., "area_search", "target_assignment", "target_tracking", "others")
  - `progress_percentage`: Integer percentage of task completion (0-100)
  - `is_completed`: Boolean indicating whether the task is completed
  - `status_message`: Human-readable status ("Task to be Done" or "Task Finished")
  - `details`: Task-specific details about progress

Example:
```bash
curl -X GET "http://localhost:8000/sessions/session-123e4567/task-progress"
```

Response example for area_search task:
```json
{
  "task_type": "area_search",
  "progress_percentage": 45,
  "is_completed": false,
  "status_message": "Task to be Done",
  "details": {
    "total_targets": 2,
    "average_coverage": 45.5,
    "coverage_by_target": {
      "target-abc": 50.0,
      "target-def": 41.0
    }
  }
}
```

Response example for target_assignment task:
```json
{
  "task_type": "target_assignment",
  "progress_percentage": 75,
  "is_completed": false,
  "status_message": "Task to be Done",
  "details": {
    "total_targets": 4,
    "visited_targets": 3,
    "unvisited_targets": 1
  }
}
```

Response example for target_tracking task:
```json
{
  "task_type": "target_tracking",
  "progress_percentage": 50,
  "is_completed": true,
  "status_message": "Task Finished",
  "details": {
    "total_targets": 4,
    "currently_tracked": 2,
    "ever_tracked": 4,
    "currently_tracked_ids": ["target-abc", "target-def"],
    "ever_tracked_ids": ["target-abc", "target-def", "target-ghi", "target-jkl"]
  }
}
```

Moving target tracking semantics:
- `reach`: Historical event recorded when a drone reaches a target within task radius
- `tracking`: Freshness-based state for moving targets
- Default moving-target tracking freshness window: `10.0` seconds
- UI and API consumers should use `tracking_status` from target responses instead of inferring moving-target freshness from raw `target_reaches`

## Task Management API

The Task Management API allows you to create, manage, and track tasks within sessions. Tasks represent specific objectives or activities that drones/clients should accomplish during a session, such as reconnaissance missions, area searches, target tracking, or any other mission objective.

### Overview

Tasks are associated with specific sessions and contain:
- **Identification**: Unique ID, name
- **Details**: Content/instructions, description
- **Metadata**: Creator, timestamps, completion status
- **Integration**: Related API endpoints, execution check endpoints, and required drone commands

Tasks can be marked as done or pending, allowing clients to track mission progress and completion status.

#### Related APIs Structure

The `related_apis` field contains an array of API endpoint objects that are relevant to completing the task. Each object has:

- **endpoint**: The API endpoint path (e.g., `/drones/{id}/command/move_to`)
- **parameters**: A dictionary describing the parameters needed for this endpoint
  - Key: Parameter name
  - Value: Description or example value for the parameter

**Example:**
```json
{
  "endpoint": "/drones/{id}/command/move_to",
  "parameters": {
    "x": "X coordinate in meters",
    "y": "Y coordinate in meters",
    "z": "Z coordinate (altitude) in meters"
  }
}
```

This structure provides clients with clear guidance on which APIs to use and what parameters are required to complete each task.

#### Execution Check APIs Structure

The `execution_check_apis` field is a **logical tree** describing how to validate execution with `/check` endpoints.

- **logic**: Logical operator (`and` default, `or`, `not`)
- **checks**: Array of child nodes
- **Leaf nodes** include:
  - **endpoint**: `/check/...` endpoint path
  - **parameters**: Dictionary of parameters to call the endpoint
  - **expect** (optional, default: true): Expected boolean `result` from the check endpoint
- Task check requests may include `since_timestamp`; the server forwards it to compatible leaf `/check` endpoints that accept `since_timestamp` unless the leaf already sets `parameters.since_timestamp`.

### Get All Tasks in a Session

**Endpoint:** `GET /sessions/{session_id}/tasks`

**Description:** Retrieves all tasks for a specific session.

**Authentication:** Requires USER role (SYSTEM and ADMIN inherit)

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | ID of the session |

**Response:** Array of task objects

**Example Request:**
```bash
curl -X GET http://localhost:8000/sessions/session-123/tasks
```

**Example Response:**
```json
[
  {
    "id": "task-abc123",
    "name": "area-search-alpha",
    "content": "Conduct a systematic search of Area Alpha (100x100m grid starting at coordinates 0,0) to identify and catalog all targets within the designated zone.",
    "content_aliases": ["search alpha", "scan zone 1"],
    "description": "Systematic area search mission",
    "creator": "system",
    "difficulty": "medium",
    "related_apis": [
      {
        "endpoint": "/drones/{id}/command/move_to",
        "parameters": {
          "x": "X coordinate in meters",
          "y": "Y coordinate in meters",
          "z": "Z coordinate (altitude) in meters"
        }
      },
      {
        "endpoint": "/drones/{id}/command/take_photo",
        "parameters": {}
      }
    ],
    "commands": ["take_off", "move_to", "take_photo", "land"],
    "is_done": false,
    "is_passed": false,
    "created_at": 1620000000.0,
    "last_updated": 1620000000.0
  },
  {
    "id": "task-def456",
    "name": "battery-check",
    "content": "Continuously monitor all drone battery levels and ensure they return to charging stations before reaching 20% battery.",
    "content_aliases": [],
    "description": "Battery management task",
    "creator": "admin",
    "difficulty": "easy",
    "related_apis": [
      {
        "endpoint": "/drones",
        "parameters": {}
      },
      {
        "endpoint": "/targets/type/waypoint",
        "parameters": {}
      }
    ],
    "commands": ["return_home", "charge"],
    "is_done": true,
    "is_passed": true,
    "created_at": 1620000100.0,
    "last_updated": 1620000500.0
  }
]
```

### Create a New Task

**Endpoint:** `POST /sessions/{session_id}/tasks`

**Description:** Creates a new task in a session.

**Authentication:** Requires SYSTEM or ADMIN role

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | ID of the session |

**Request Body Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | Yes | Short name/identifier for the task |
| content | string | No | Detailed content/instructions (default: "") |
| content_aliases | array of strings | No | List of alternative names or aliases for the content (default: []) |
| description | string | No | Brief description (default: "") |
| creator | string | No | Name of the user creating the task; defaults to the caller's role if omitted |
| originated_from | string | No | Principal that originated the task (defaults to `creator`) |
| difficulty | string | No | Difficulty level: "easy", "medium", or "hard" (default: "medium") |
| related_apis | array of objects | No | List of API endpoint objects with "endpoint" and "parameters" fields (default: []) |
| execution_check_apis | object | No | Logical tree describing `/check` validations: `logic` (`and`/`or`/`not`) and `checks` array; leaf nodes include `endpoint`, `parameters`, optional `expect` boolean (default: `true`) |
| commands | array | No | List of drone commands for the task (default: []) |

If `creator` is not provided, the server records the caller's role as the creator.

**Response:** Created task object

**Example Request:**
```bash
curl -X POST http://localhost:8000/sessions/session-123/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "name": "target-tracking-mission",
    "content": "Maintain visual contact with Target Bravo as it moves through the patrol zone. Document position every 30 seconds.",
    "content_aliases": ["track bravo", "follow bravo"],
    "description": "Track and document Target Bravo movement",
    "creator": "mission-lead",
    "difficulty": "hard",
    "related_apis": [
      {
        "endpoint": "/drones/{id}/command/move_to",
        "parameters": {
          "x": "X coordinate in meters",
          "y": "Y coordinate in meters",
          "z": "Z coordinate (altitude) in meters"
        }
      },
      {
        "endpoint": "/drones/{id}/command/take_photo",
        "parameters": {}
      }
    ],
    "execution_check_apis": {
      "logic": "and",
      "checks": [
        {
          "endpoint": "/check/drone_position",
          "parameters": {
            "drone_id": "drone-1",
            "x": "Expected X",
            "y": "Expected Y",
            "tolerance": "Distance tolerance"
          },
          "expect": true
        },
        {
          "logic": "or",
          "checks": [
                      {
                        "endpoint": "/check/task_done",
                        "parameters": {},
                        "expect": true
                      },
                      {
                        "endpoint": "/check/task_progress",
                        "parameters": { "expected_progress": 0.9 },
                        "expect": true
                      }          ]
        }
      ]
    },
    "commands": ["take_off", "move_to", "hover", "take_photo"]
  }'
```

**Example Response:**
```json
{
  "id": "task-ghi789",
  "name": "target-tracking-mission",
  "content": "Maintain visual contact with Target Bravo as it moves through the patrol zone. Document position every 30 seconds.",
  "content_aliases": ["track bravo", "follow bravo"],
  "description": "Track and document Target Bravo movement",
  "creator": "mission-lead",
  "originated_from": "mission-lead",
  "difficulty": "hard",
  "related_apis": [
    {
      "endpoint": "/drones/{id}/command/move_to",
      "parameters": {
        "x": "X coordinate in meters",
        "y": "Y coordinate in meters",
        "z": "Z coordinate (altitude) in meters"
      }
    },
    {
      "endpoint": "/drones/{id}/command/take_photo",
      "parameters": {}
    }
  ],
  "execution_check_apis": {
    "logic": "and",
    "checks": []
  },
  "commands": ["take_off", "move_to", "hover", "take_photo"],
  "is_done": false,
  "is_passed": false,
  "created_at": 1620001000.0,
  "last_updated": 1620001000.0
}
```

### Get a Specific Task

**Endpoint:** `GET /sessions/{session_id}/tasks/{task_id}`

**Description:** Retrieves details of a specific task.

**Authentication:** Requires SYSTEM role (ADMIN inherits)

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | ID of the session |
| task_id | string | Yes | ID of the task |

**Response:** Task object

**Example Request:**
```bash
curl -X GET http://localhost:8000/sessions/session-123/tasks/task-abc123
```

**Example Response:**
```json
{
  "id": "task-abc123",
  "name": "area-search-alpha",
  "content": "Conduct a systematic search of Area Alpha...",
  "content_aliases": ["search alpha", "scan zone 1"],
  "description": "Systematic area search mission",
  "creator": "system",
  "originated_from": "system",
  "difficulty": "medium",
  "related_apis": [
    {
      "endpoint": "/drones/{id}/command/move_to",
      "parameters": {
        "x": "X coordinate in meters",
        "y": "Y coordinate in meters",
        "z": "Z coordinate (altitude) in meters"
      }
    },
    {
      "endpoint": "/drones/{id}/command/take_photo",
      "parameters": {}
    }
  ],
  "commands": ["take_off", "move_to", "take_photo", "land"],
  "is_done": false,
  "is_passed": false,
  "created_at": 1620000000.0,
  "last_updated": 1620000000.0
}
```

### Update a Task

**Endpoint:** `PUT /sessions/{session_id}/tasks/{task_id}`

**Description:** Updates a task's properties. All fields are optional.

**Authentication:** Requires SYSTEM or ADMIN role

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | ID of the session |
| task_id | string | Yes | ID of the task |

**Request Body Parameters (all optional):**

| Name | Type | Description |
|------|------|-------------|
| name | string | Short name for the task |
| content | string | Detailed content/instructions |
| content_aliases | array of strings | List of alternative names or aliases for the content |
| description | string | Brief description |
| related_apis | array of objects | List of API endpoint objects with "endpoint" and "parameters" fields |
| commands | array | List of drone commands |
| is_done | boolean | Task completion status |

**Note:** `is_passed` is server-managed and cannot be set via this endpoint.

**Response:** Updated task object

**Example Request:**
```bash
curl -X PUT http://localhost:8000/sessions/session-123/tasks/task-abc123 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "description": "Updated: Systematic area search with photo documentation",
    "difficulty": "hard",
    "is_done": true
  }'
```

**Example Response:**
```json
{
  "id": "task-abc123",
  "name": "area-search-alpha",
  "content": "Conduct a systematic search of Area Alpha...",
  "content_aliases": [],
  "description": "Updated: Systematic area search with photo documentation",
  "creator": "system",
  "difficulty": "hard",
  "related_apis": [
    {
      "endpoint": "/drones/{id}/command/move_to",
      "parameters": {
        "x": "X coordinate in meters",
        "y": "Y coordinate in meters",
        "z": "Z coordinate (altitude) in meters"
      }
    },
    {
      "endpoint": "/drones/{id}/command/take_photo",
      "parameters": {}
    }
  ],
  "commands": ["take_off", "move_to", "take_photo", "land"],
  "is_done": true,
  "is_passed": true,
  "created_at": 1620000000.0,
  "last_updated": 1620002000.0
}
```

### Delete a Task

**Endpoint:** `DELETE /sessions/{session_id}/tasks/{task_id}`

**Description:** Deletes a task from a session.

**Authentication:** Requires SYSTEM or ADMIN role

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | ID of the session |
| task_id | string | Yes | ID of the task |

**Response:** 204 No Content on success

**Example Request:**
```bash
curl -X DELETE http://localhost:8000/sessions/session-123/tasks/task-abc123 \
  -H "X-API-Key: <SYSTEM_API_KEY>"
```

### Mark Task as Done (Specific Session)

**Endpoint:** `POST /sessions/{session_id}/tasks/{task_id}/mark-done`

**Description:** Marks a task as completed.

**Authentication:** Requires SYSTEM role (ADMIN inherits)

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | ID of the session |
| task_id | string | Yes | ID of the task |

**Response:** Updated task object with `is_done: true`

**Example Request:**
```bash
curl -X POST http://localhost:8000/sessions/session-123/tasks/task-abc123/mark-done
```

**Example Response:**
```json
{
  "id": "task-abc123",
  "name": "area-search-alpha",
  "difficulty": "medium",
  "is_done": true,
  "last_updated": 1620003000.0,
  ...
}
```

### Mark Task as Pending (Specific Session)

**Endpoint:** `POST /sessions/{session_id}/tasks/{task_id}/mark-pending`

**Description:** Marks a task as pending (not completed).

**Authentication:** Requires SYSTEM role (ADMIN inherits)

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | ID of the session |
| task_id | string | Yes | ID of the task |

**Response:** Updated task object with `is_done: false`

**Example Request:**
```bash
curl -X POST http://localhost:8000/sessions/session-123/tasks/task-abc123/mark-pending
```

### Mark Task as Done (Current Session)

**Endpoint:** `POST /sessions/current/tasks/{task_id}/mark-done`

**Description:** Marks a task as completed in the current session.

**Authentication:** Requires AGENT role (USER, SYSTEM and ADMIN inherit)

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| task_id | string | Yes | ID of the task |

**Response:** Updated task object with `is_done: true`

**Example Request:**
```bash
curl -X POST http://localhost:8000/sessions/current/tasks/task-abc123/mark-done
```

### Mark Task as Pending (Current Session)

**Endpoint:** `POST /sessions/current/tasks/{task_id}/mark-pending`

**Description:** Marks a task as pending (not completed) in the current session.

**Authentication:** Requires AGENT role (USER, SYSTEM and ADMIN inherit)

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| task_id | string | Yes | ID of the task |

**Response:** Updated task object with `is_done: false`

**Example Request:**
```bash
curl -X POST http://localhost:8000/sessions/current/tasks/task-abc123/mark-pending
```

### Swap Tasks

**Endpoint:** `POST /sessions/{session_id}/tasks/swap`

**Description:** Swaps the order of two tasks in a session. This reorders the tasks by swapping their positions.

**Authentication:** Requires SYSTEM or ADMIN role

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | ID of the session containing the tasks |

**Request Body:**
```json
{
  "task_id_1": "task-abc123",
  "task_id_2": "task-def456"
}
```

**Response:** Array of all tasks in the session in their new order

**Example Request:**
```bash
curl -X POST http://localhost:8000/sessions/session-123/tasks/swap \
  -H "Content-Type: application/json" \
  -d '{
    "task_id_1": "task-abc123",
    "task_id_2": "task-def456"
  }'
```

**Example Response (200 OK):**
```json
[
  {
    "id": "task-def456",
    "name": "area-patrol-bravo",
    "content": "Patrol area bravo and monitor for activity",
    "description": "Brief description",
    "creator": "system",
    "difficulty": "medium",
    "related_apis": [],
    "commands": [],
    "is_done": false,
    "is_passed": false,
    "created_at": 1620000000.0,
    "last_updated": 1620000000.0
  },
  {
    "id": "task-abc123",
    "name": "area-search-alpha",
    "content": "Search area alpha for targets",
    "description": "Brief description",
    "creator": "system",
    "difficulty": "easy",
    "related_apis": [],
    "commands": [],
    "is_done": false,
    "is_passed": false,
    "created_at": 1620000000.0,
    "last_updated": 1620000000.0
  }
]
```

**Error Responses:**
- `404 Not Found`: Session not found or one or both tasks not found

### Get Current Session Tasks

**Endpoint:** `GET /sessions/current/tasks`

**Description:** Retrieves all tasks from the current active session.

**Authentication:** Requires AGENT role (USER, SYSTEM and ADMIN inherit)

**Response:** Array of task objects

**Example Request:**
```bash
curl -X GET http://localhost:8000/sessions/current/tasks
```

### Get Next Pending Task from Current Session

**Endpoint:** `GET /sessions/current/tasks/next`

**Description:** Retrieves the next pending (not completed) task from the current active session.

**Authentication:** Requires AGENT role (USER, SYSTEM and ADMIN inherit)

**Response:** Task object

**Example Request:**
```bash
curl -X GET http://localhost:8000/sessions/current/tasks/next
```

**Error Responses:**
- `404 Not Found`: No current session found
- `404 Not Found`: No pending task found

### Get Specific Task from Current Session

**Endpoint:** `GET /sessions/current/tasks/{task_id}`

**Description:** Retrieves a specific task from the current active session.

**Authentication:** Requires AGENT role (USER, SYSTEM and ADMIN inherit)

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| task_id | string | Yes | ID of the task |

**Response:** Task object

**Example Request:**
```bash
curl -X GET http://localhost:8000/sessions/current/tasks/task-abc123
```

### Check Task in Current Session

**Endpoint:** `GET /sessions/current/tasks/{task_id}/check`

**Description:** Evaluates the task's `execution_check_apis` and sets `is_passed: true` when the check passes. Optional `since_timestamp` scopes compatible history checks to events at or after that timestamp.

**Authentication:** Requires AGENT role (USER, SYSTEM and ADMIN inherit)

**Path Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| task_id | string | Yes | ID of the task |

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| since_timestamp | float | No | Default timestamp filter passed to compatible `/check` leaf endpoints. Leaf-level `parameters.since_timestamp` takes precedence. |

**Response:** Object with `result` and `task`. For SYSTEM/ADMIN, includes `details` with full evaluation output.

**Example Request:**
```bash
curl -X GET http://localhost:8000/sessions/current/tasks/task-abc123/check
```

**Example Response:**
```json
{
  "result": true,
  "task": {
    "id": "task-abc123",
    "name": "area-search-alpha",
    "is_done": false,
    "is_passed": true
  }
}
```

### Task Management Workflow Example

Here's a complete workflow demonstrating task creation, assignment, and completion:

```python
import requests

API_BASE = "http://localhost:8000"
SYSTEM_KEY = "<SYSTEM_API_KEY>"
HEADERS = {"X-API-Key": SYSTEM_KEY, "Content-Type": "application/json"}

# 1. Get current session ID
response = requests.get(f"{API_BASE}/sessions/current")
session_id = response.json()["id"]
print(f"Current session: {session_id}")

# 2. Create a task for area search
task_data = {
    "name": "zone-1-search-rescue",
    "content": "Systematically search Zone 1 (coordinates 0,0 to 100,100) for survivors. Take photos of any findings.",
    "description": "Search and rescue operation - Zone 1",
    "related_apis": [
        {
            "endpoint": "/drones/{id}/command/move_to",
            "parameters": {
                "x": "X coordinate in meters",
                "y": "Y coordinate in meters",
                "z": "Z coordinate (altitude) in meters"
            }
        },
        {
            "endpoint": "/drones/{id}/command/take_photo",
            "parameters": {}
        }
    ],
    "commands": ["take_off", "move_to", "hover", "take_photo", "land"]
}

response = requests.post(
    f"{API_BASE}/sessions/{session_id}/tasks",
    headers=HEADERS,
    json=task_data
)
task = response.json()
task_id = task["id"]
print(f"Created task: {task_id}")

# 3. Client executes the mission commands
drone_id = "drone-001"

# Take off
requests.post(f"{API_BASE}/drones/{drone_id}/command/take_off?altitude=15")

# Move to search area and take photos
search_points = [
    {"x": 25, "y": 25, "z": 15},
    {"x": 75, "y": 25, "z": 15},
    {"x": 75, "y": 75, "z": 15},
    {"x": 25, "y": 75, "z": 15}
]

for point in search_points:
    requests.post(
        f"{API_BASE}/drones/{drone_id}/command/move_to",
        json={"command": "move_to", "parameters": point}
    )
    requests.post(f"{API_BASE}/drones/{drone_id}/command/take_photo")

# Land
requests.post(f"{API_BASE}/drones/{drone_id}/command/land")

# 4. Mark task as completed
response = requests.post(
    f"{API_BASE}/sessions/{session_id}/tasks/{task_id}/mark-done"
)
print(f"Task completed: {response.json()['is_done']}")
print(f"Task passed: {response.json().get('is_passed')}")

# 5. Get all tasks to see completion status
response = requests.get(f"{API_BASE}/sessions/{session_id}/tasks", headers=HEADERS)
tasks = response.json()
print(f"Total tasks: {len(tasks)}")
print(f"Completed tasks: {sum(1 for t in tasks if t['is_done'])}")
print(f"Passed tasks: {sum(1 for t in tasks if t.get('is_passed'))}")
```

## Drone API

### Get All Drones

**Endpoint:** `GET /drones`

**Description:** Retrieves a list of all registered drones in the system.

**Parameters:** None

**Response:** Array of drone objects

**Example Request:**
```bash
curl -X GET http://localhost:8000/drones
```

**Example Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Scout-1",
    "model": "Model-D4",
    "status": "idle",
    "position": {"x": 0.0, "y": 0.0, "z": 0.0},
    "heading": 0.0,
    "speed": 0.0,
    "perceived_radius": 100.0,
    "task_radius": 10.0,
    "home_position": {"x": 0.0, "y": 0.0, "z": 0.0},
    "created_at": 1704067200.0,
    "last_updated": 1704067350.5
  }
]
```

### Register a New Drone

**Endpoint:** `POST /drones`

**Description:** Registers a new drone in the system.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | Yes | Name of the drone |
| model | string | Yes | Model of the drone |
| max_speed | float | Yes | Maximum speed in m/s |
| max_altitude | float | Yes | Maximum altitude in meters |
| battery_capacity | float | Yes | Battery capacity in mAh |
| position | object | No | Initial position with x, y, z coordinates (default: {x: 0, y: 0, z: 0}) |
| heading | float | No | Initial heading in degrees (default: 0.0) |
| speed | float | No | Initial speed in m/s (default: 0.0) |
| battery_level | float | No | Initial battery level percentage (default: 100.0) |
| battery_volume | float | No | Initial battery volume in mAh (if provided, takes precedence over battery_level) |
| status | string | No | Initial status (default: auto-determined based on altitude) |
| home_position | object | No | Home position with x, y, z coordinates (defaults to initial position if not specified) |
| perceived_radius | float | No | Perception radius in meters (default: 100.0) |
| task_radius | float | No | Task radius in meters (default: 10.0) |

**Response:** Newly created drone object

**Example Request:**
```bash
curl -X POST http://localhost:8000/drones \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Scout-1",
    "model": "Model-D4",
    "max_speed": 20.0,
    "max_altitude": 120.0,
    "battery_capacity": 5000.0,
    "position": {"x": 100.0, "y": 100.0, "z": 0.0},
    "heading": 45.0,
    "speed": 0.0,
    "battery_volume": 4000.0,
    "status": "idle",
    "home_position": {"x": 0.0, "y": 0.0, "z": 0.0},
    "perceived_radius": 100.0,
    "task_radius": 10.0
  }'
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Scout-1",
  "model": "Model-D4",
  "status": "idle",
  "position": {"x": 100.0, "y": 100.0, "z": 0.0},
  "heading": 45.0,
  "speed": 0.0,
  "perceived_radius": 100.0,
  "task_radius": 10.0,
  "battery_level": 100.0,
  "battery_volume": 5000.0,
  "battery_capacity": 5000.0,
  "max_speed": 20.0,
  "max_altitude": 120.0,
  "home_position": {"x": 100.0, "y": 100.0, "z": 0.0},
  "created_at": 1620000000.0,
  "last_updated": 1620000000.0
}
```

### Get a Specific Drone

**Endpoint:** `GET /drones/{drone_id}`

**Description:** Retrieves information about a specific drone.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |

**Response:** Drone object

**Example Request:**
```bash
curl -X GET http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Scout-1",
  "model": "Model-D4",
  "status": "idle",
  "position": {"x": 0.0, "y": 0.0, "z": 0.0},
  "heading": 0.0,
  "speed": 0.0,
  "perceived_radius": 100.0,
  "task_radius": 10.0,
  "home_position": {"x": 0.0, "y": 0.0, "z": 0.0},
  "created_at": 1704067200.0,
  "last_updated": 1704067350.5
}
```

### Update Drone Properties

**Endpoint:** `PUT /drones/{drone_id}`

**Description:** Updates a drone's properties including metadata, performance specifications, state attributes, battery levels, position, and home position. All fields are optional - only provided fields will be updated.

**Authentication Required:** SYSTEM role

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |

**Request Body Fields (all optional):**

| Field | Type | Description |
|-------|------|-------------|
| name | string | Name of the drone |
| model | string | Model of the drone |
| max_speed | float | Maximum speed in m/s (must be > 0) |
| max_altitude | float | Maximum altitude in meters (must be > 0) |
| battery_capacity | float | Battery capacity in mAh (must be > 0) |
| perceived_radius | float | Perception radius in meters (must be > 0) |
| task_radius | float | Task radius in meters (must be > 0) |
| status | string | Current status (idle, ready, flying, hovering, etc.) |
| position | object | Current position {x, y, z} - supports partial updates |
| heading | float | Heading in degrees (0-359) |
| speed | float | Current speed in m/s (must be ≥ 0) |
| battery_level | float | Battery percentage (0-100) |
| battery_volume | float | Battery volume in mAh (must be ≥ 0) |
| home_position | object | Home position {x, y, z} - supports partial updates |

**Response:** Updated drone object

**Example Request - Update Metadata:**
```bash
curl -X PUT http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "name": "Scout-1 Enhanced",
    "model": "Model-D5",
    "max_speed": 25.0,
    "perceived_radius": 125.0
  }'
```

**Example Request - Update State:**
```bash
curl -X PUT http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "status": "hovering",
    "heading": 90.0,
    "speed": 5.0,
    "battery_level": 85.5
  }'
```

**Example Request - Partial Position Update (altitude only):**
```bash
curl -X PUT http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "position": {"z": 50.0}
  }'
```

**Example Request - Comprehensive Update:**
```bash
curl -X PUT http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "name": "Advanced Scout Alpha",
    "status": "flying",
    "position": {"x": 100.0, "y": 200.0, "z": 50.0},
    "heading": 45.0,
    "speed": 15.0,
    "battery_level": 90.0
  }'
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Advanced Scout Alpha",
  "model": "Model-D5",
  "status": "flying",
  "position": {"x": 100.0, "y": 200.0, "z": 50.0},
  "heading": 45.0,
  "speed": 15.0,
    "perceived_radius": 120.0,
    "task_radius": 15.0,
    "home_position": {"x": 0.0, "y": 0.0, "z": 0.0},
    "created_at": 1704067200.0,
    "last_updated": 1704067500.0
  }
```

**Notes:**
- All fields are optional - only send the fields you want to update
- Position and home_position support partial updates (e.g., only updating z coordinate)
- When updating battery_level, battery_volume is recalculated automatically
- When updating battery_capacity, battery_volume is recalculated based on current battery_level
- Requires SYSTEM role authentication

### Update Drone Position

**Endpoint:** `PUT /drones/{drone_id}/position`

**Description:** Directly updates a drone's position. This is an administrative function that sets the position without simulating movement. The drone's status will be automatically updated based on altitude.

**Authentication Required:** SYSTEM role

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |
| x | float | Yes | X coordinate in meters |
| y | float | Yes | Y coordinate in meters |
| z | float | Yes | Z coordinate (altitude) in meters |

**Request Body:**
```json
{
  "x": 100.0,
  "y": 200.0,
  "z": 50.0
}
```

**Response:** Updated drone object

**Example Request:**
```bash
curl -X PUT http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/position \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "x": 100.0,
    "y": 200.0,
    "z": 50.0
  }'
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Scout-1",
  "model": "Model-D4",
  "status": "hovering",
  "position": {"x": 100.0, "y": 200.0, "z": 50.0},
  "heading": 0.0,
  "speed": 0.0,
  "perceived_radius": 100.0,
  "task_radius": 10.0,
  "battery_level": 100.0,
  "battery_volume": 5000.0,
  "battery_capacity": 5000.0,
  "max_speed": 20.0,
  "max_altitude": 120.0,
  "home_position": {"x": 0.0, "y": 0.0, "z": 0.0},
  "created_at": 1620000000.0,
  "last_updated": 1620000100.0
}
```

**Automatic Status Updates:**
- If z > 0 and drone is IDLE/READY → status changes to HOVERING
- If z == 0 and drone is HOVERING/FLYING/MOVING → status changes to IDLE

**Notes:**
- All three coordinates (x, y, z) are required for this endpoint
- For partial position updates (e.g., only altitude), use `PUT /drones/{drone_id}` instead
- Checks for obstacle collisions at the target position
- Does not consume battery (administrative function)
- Does not simulate movement or check path collisions

### Delete a Drone

**Endpoint:** `DELETE /drones/{drone_id}`

**Description:** Deletes a drone from the system.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |

**Response:** No content (204)

**Example Request:**
```bash
curl -X DELETE http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000
```

### Nearby Entities

Provides proximity queries to find entities near a drone. Uses the drone's `perceived_radius` to determine the search area.

#### Get Aggregated Nearby Entities

**Endpoint:** `GET /drones/{drone_id}/nearby`

**Description:** Get nearby drones, targets, and obstacles around a drone using its perceived radius.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the reference drone (path) |

**Response:**

```json
{
  "drones": [
    {
      "id": "drone-2",
      "name": "Scout-2",
      "position": {"x": 12.5, "y": -3.2, "z": 5.0},
      "distance": 14.3
    }
  ],
  "targets": [
    {
      "id": "target-1",
      "name": "Waypoint A",
      "position": {"x": 20.0, "y": 10.0, "z": 0.0},
      "distance": 22.4
    }
  ],
  "obstacles": [
    {
      "id": "obstacle-3",
      "name": "Building B",
      "position": {"x": 30.0, "y": 5.0, "z": 0.0},
      "distance": 28.7
    }
  ]
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/drones/{drone_id}/nearby"
```

#### Get Nearby Drones

**Endpoint:** `GET /drones/{drone_id}/nearby/drones`

**Description:** Get nearby drones around a drone using its perceived radius.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the reference drone (path) |

**Response:** Array of nearby drone objects

**Example Request:**
```bash
curl -X GET "http://localhost:8000/drones/{drone_id}/nearby/drones"
```

#### Get Nearby Targets

**Endpoint:** `GET /drones/{drone_id}/nearby/targets`

**Description:** Get nearby targets around a drone using its perceived radius.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the reference drone (path) |

**Response:** Array of nearby target objects

**Example Request:**
```bash
curl -X GET "http://localhost:8000/drones/{drone_id}/nearby/targets"
```

#### Get Nearby Obstacles

**Endpoint:** `GET /drones/{drone_id}/nearby/obstacles`

**Description:** Get nearby obstacles around a drone using its perceived radius.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the reference drone (path) |

**Response:** Array of nearby obstacle objects

**Example Request:**
```bash
curl -X GET "http://localhost:8000/drones/{drone_id}/nearby/obstacles"
```

## Command API

### Send Command to Drone

**Endpoint:** `POST /drones/{drone_id}/command`

**Description:** Sends a command to a specific drone.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |
| command | string | Yes | Command to send (see DroneCommand enum) |
| parameters | object | No | Command-specific parameters |

**Available Commands:**
- `connect` - Connect to the drone
- `disconnect` - Disconnect from the drone
- `take_off` - Take off from the ground
- `land` - Land on the ground
- `move_to` - Move to a specific position (x, y, z)
- `change_altitude` - Change only the altitude (z position)
- `hover` - Hover in place
- `rotate` - Rotate to a specific heading
- `return_home` - Return to home position
- `set_home` - Set the home position
- `calibrate` - Calibrate sensors
- `take_photo` - Take a photo with the drone's camera
- `send_message` - Send a message to another drone
- `broadcast` - Broadcast a message to all nearby drones

**Response:** Command response object. Command `status` values include `success` for full completion, `partial_success` for state-changing partial completion, and `error` for commands that did not execute successfully. Only `move_along_path` advertises the extra point feedback fields: `successful_points_count`, `successful_points`, `unsuccessful_points_count`, and `unsuccessful_points`.

**Example Request:**
```bash
curl -X POST http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/command \
  -H "Content-Type: application/json" \
  -d '{
    "command": "take_off",
    "parameters": {"altitude": 10.0}
  }'
```

**Example Response:**
```json
{
  "command_id": "a1b2c3d4-e5f6-4a5b-8c7d-9e0f1a2b3c4d",
  "drone_id": "550e8400-e29b-41d4-a716-446655440000",
  "command": "take_off",
  "status": "executing",
  "message": "Taking off to altitude 10.0m"
}
```

### Get Drone Command History

**Endpoint:** `GET /drones/{drone_id}/commands`

**Description:** Retrieves the command history for a specific drone.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |

**Response:** Array of command response objects

**Example Request:**
```bash
curl -X GET http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/commands
```

**Example Response:**
```json
[
  {
    "command_id": "a1b2c3d4-e5f6-4a5b-8c7d-9e0f1a2b3c4d",
    "drone_id": "550e8400-e29b-41d4-a716-446655440000",
    "command": "take_off",
    "status": "completed",
    "message": "Took off to altitude 10.0m"
  }
]
```

### Get Command Status

**Endpoint:** `GET /commands/{command_id}`

**Description:** Retrieves the status of a specific command.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| command_id | string | Yes | ID of the command (in URL path) |

**Response:** Command response object

**Example Request:**
```bash
curl -X GET http://localhost:8000/commands/a1b2c3d4-e5f6-4a5b-8c7d-9e0f1a2b3c4d
```

**Example Response:**
```json
{
  "command_id": "a1b2c3d4-e5f6-4a5b-8c7d-9e0f1a2b3c4d",
  "drone_id": "550e8400-e29b-41d4-a716-446655440000",
  "command": "take_off",
  "status": "completed",
  "message": "Took off to altitude 10.0m"
}
```

## Direct Command API

These endpoints provide a more direct way to send specific commands to drones without having to construct a command object.

### Take Off

**Endpoint:** `POST /drones/{drone_id}/command/take_off`

**Description:** Commands a drone to take off.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |
| altitude | float | No | Target altitude in meters (default: 10.0) |

**Response:** Command response object

**Example Request:**
```bash
curl -X POST "http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/command/take_off?altitude=15.0"
```

### Land

**Endpoint:** `POST /drones/{drone_id}/command/land`

**Description:** Commands a drone to land.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |

**Response:** Command response object

**Example Request:**
```bash
curl -X POST http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/command/land
```

### Move To

**Endpoint:** `POST /drones/{drone_id}/command/move_to`

**Description:** Commands a drone to move to specific coordinates.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |
| x | float | Yes | X coordinate in meters |
| y | float | Yes | Y coordinate in meters |
| z | float | Yes | Z coordinate (altitude) in meters |

**Response:** Command response object

**Example Request:**
```bash
curl -X POST "http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/command/move_to?x=10.0&y=20.0&z=15.0"
```

### Move Towards

**Endpoint:** `POST /drones/{drone_id}/command/move_towards`

**Description:** Commands a drone to move a certain distance in a specific direction. The direction can be specified using three different methods: compass heading, direction vector, or spherical coordinates (azimuth/elevation). If no direction is specified, the drone will move in its current heading direction.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |
| distance | float | Yes | Distance to move in meters |
| **Direction Method 1: Compass Heading** | | | |
| heading | float | Conditional | Compass bearing in degrees (0=North, 90=East, 180=South, 270=West) |
| dz | float | No | Optional vertical component (altitude change) |
| **Direction Method 2: Direction Vector** | | | |
| dx | float | Conditional | X component of direction vector |
| dy | float | Conditional | Y component of direction vector |
| dz | float | No | Z component of direction vector (default: 0.0) |
| **Direction Method 3: Spherical Coordinates** | | | |
| azimuth | float | Conditional | Horizontal angle in degrees (0=North, clockwise) |
| elevation | float | No | Vertical angle in degrees (default: 0.0) |

**Note:**
- If no direction parameters are provided (heading, dx/dy, or azimuth are all None), the drone will move in its current heading direction
- Otherwise, you must specify direction using exactly ONE of the three methods above
- The drone's heading is automatically updated based on the movement direction

**Response:** Command response object

**Example Requests:**

```bash
# No direction specified: Move 50m in current heading direction
curl -X POST "http://localhost:8000/drones/drone-123/command/move_towards?distance=50.0"

# Method 1: Move 50 meters towards East (90°)
curl -X POST "http://localhost:8000/drones/drone-123/command/move_towards?distance=50.0&heading=90.0"

# Method 1: Move 30 meters Northeast with 5m altitude gain
curl -X POST "http://localhost:8000/drones/drone-123/command/move_towards?distance=30.0&heading=45.0&dz=5.0"

# Method 2: Move 25 meters using normalized direction vector
curl -X POST "http://localhost:8000/drones/drone-123/command/move_towards?distance=25.0&dx=1.0&dy=1.0&dz=0.5"

# Method 3: Move 40 meters with azimuth 135° and elevation 15°
curl -X POST "http://localhost:8000/drones/drone-123/command/move_towards?distance=40.0&azimuth=135.0&elevation=15.0"

# Using generic command endpoint
curl -X POST http://localhost:8000/drones/drone-123/command \
  -H "Content-Type: application/json" \
  -d '{
    "command": "move_towards",
    "parameters": {
      "distance": 50.0,
      "heading": 90.0
    }
  }'
```

**Example Response:**
```json
{
  "command_id": "cmd-123",
  "drone_id": "drone-123",
  "command": "move_towards",
  "status": "success",
  "message": "Drone moved 50.00m to position (150.00, 100.00, 15.00)"
}
```

**Direction Methods Explained:**

1. **Compass Heading**: Use when you want to move in a specific compass direction
   - `heading=0`: North (+Y direction)
   - `heading=90`: East (+X direction)
   - `heading=180`: South (-Y direction)
   - `heading=270`: West (-X direction)
   - Optional `dz` for altitude change

2. **Direction Vector**: Use when you have a specific direction vector
   - Specify `dx`, `dy`, `dz` components
   - Vector will be automatically normalized
   - Good for relative movements

3. **Spherical Coordinates**: Use for 3D directional control
   - `azimuth`: Horizontal angle (0-360°)
   - `elevation`: Vertical angle (-90° to +90°)
   - Good for complex 3D maneuvers

### Change Altitude

**Endpoint:** `POST /drones/{drone_id}/command/change_altitude`

**Description:** Commands a drone to change its altitude.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |
| altitude | float | Yes | Target altitude in meters |

**Response:** Command response object

**Example Request:**
```bash
curl -X POST "http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/command/change_altitude?altitude=25.0"
```

### Hover

**Endpoint:** `POST /drones/{drone_id}/command/hover`

**Description:** Commands a drone to hover in place.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |
| duration | float | No | Duration to hover in seconds (default: infinite/until next command) |

**Response:** Command response object

**Example Request:**
```bash
# Hover indefinitely
curl -X POST http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/command/hover

# Hover for 5 seconds
curl -X POST "http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/command/hover?duration=5.0"
```

### Rotate (Change Heading)

**Endpoint:** `POST /drones/{drone_id}/command/rotate`

**Description:** Commands a drone to rotate/change its heading (orientation) without changing position. The drone's heading determines the direction it will move when using `move_towards` without specifying a direction.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |
| heading | float | Yes | Target heading in degrees (0=North, 90=East, 180=South, 270=West) |

**Response:** Command response object

**Example Requests:**
```bash
# Rotate to face North
curl -X POST "http://localhost:8000/drones/drone-123/command/rotate?heading=0.0"

# Rotate to face East
curl -X POST "http://localhost:8000/drones/drone-123/command/rotate?heading=90.0"

# Rotate to face Southwest
curl -X POST "http://localhost:8000/drones/drone-123/command/rotate?heading=225.0"

# Using generic command endpoint
curl -X POST http://localhost:8000/drones/drone-123/command \
  -H "Content-Type: application/json" \
  -d '{
    "command": "rotate",
    "parameters": {
      "heading": 180.0
    }
  }'
```

**Example Response:**
```json
{
  "command_id": "cmd-456",
  "drone_id": "drone-123",
  "command": "rotate",
  "status": "success",
  "message": "Drone heading set to 180.0°"
}
```

**Use Cases:**
- Orient drone before taking photos or videos
- Prepare for `move_towards` command in a specific direction
- Point sensors or cameras in a specific direction
- Align with waypoint or target before approaching

### Return Home

**Endpoint:** `POST /drones/{drone_id}/command/return_home`

**Description:** Commands a drone to return to its home position.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |

**Response:** Command response object

**Example Request:**
```bash
curl -X POST http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/command/return_home
```

### Set Home

**Endpoint:** `POST /drones/{drone_id}/command/set_home`

**Description:** Sets the current position as the drone's home position.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |

**Response:** Command response object

**Example Request:**
```bash
curl -X POST http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/command/set_home
```

### Calibrate

**Endpoint:** `POST /drones/{drone_id}/command/calibrate`

**Description:** Calibrates the drone's sensors.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |

**Response:** Command response object

**Example Request:**
```bash
curl -X POST http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/command/calibrate
```

### Take Photo

**Endpoint:** `POST /drones/{drone_id}/command/take_photo`

**Description:** Commands a drone to take a photo with its camera.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |

**Response:** Command response object

**Example Request:**
```bash
curl -X POST http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/command/take_photo
```

### Send Message

**Endpoint:** `POST /drones/{drone_id}/command/send_message`

**Description:** Commands a drone to send a message to another drone.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the sender drone (in URL path) |
| target_drone_id | string | Yes | ID of the target drone |
| message | string | Yes | Message content |

**Response:** Command response object

**Example Request:**
```bash
curl -X POST "http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/command/send_message?target_drone_id=550e8400-e29b-41d4-a716-446655440001&message=Hello%20from%20Scout-1"
```

### Broadcast Message

**Endpoint:** `POST /drones/{drone_id}/command/broadcast`

**Description:** Commands a drone to broadcast a message to all nearby drones.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the sender drone (in URL path) |
| message | string | Yes | Message content |

**Response:** Command response object

**Example Request:**
```bash
curl -X POST "http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/command/broadcast?message=Emergency%20landing%20required"
```

### Move Along Path

**Endpoint:** `POST /drones/{drone_id}/command/move_along_path`

**Description:** Commands a drone to move along a specified path of one or more waypoints. A single waypoint is accepted and behaves like a one-step move. Waypoints may omit `z`; omitted altitude defaults to the drone's current altitude.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |
| waypoints | array | Yes | Ordered waypoint coordinates `[{x, y, z}, ...]` or 2D coordinates `[{x, y}, ...]` with at least one waypoint. Missing `z` uses the drone's current altitude. |
| allow_partial_move | boolean | No | Default `false`. When `true`, the drone stops at the last reachable waypoint before an obstacle blocks the next waypoint/segment or before battery is insufficient for the next waypoint. |

**Request Body:**
```json
{
  "waypoints": [
    {"x": 10.0, "y": 20.0, "z": 15.0},
    {"x": 30.0, "y": 40.0},
    {"x": 50.0, "y": 60.0, "z": 15.0}
  ],
  "allow_partial_move": false
}
```

**Response:** MoveAlongPathCommandResponse object. Battery usage for `move_to` and `move_along_path` is distance-based with no base movement cost. With `allow_partial_move=true`, the command returns `partial_success` if at least one waypoint is completed before an obstacle or insufficient battery blocks the remaining path; the response message states that the path was only partially completed. `success` means all requested waypoints were reached. If the first waypoint cannot be reached safely or with sufficient battery, the command returns `error` and the drone does not move. Successful and partially successful path responses include `successful_points_count`, `successful_points`, `unsuccessful_points_count`, and `unsuccessful_points`, where point lists contain normalized `(x, y, z)` triples; error responses do not populate point feedback values.

Large waypoint lists are processed with batched internal coverage tracking, reused path calculations, and lightweight session state synchronization. This improves command response time while preserving the same request and response schema, waypoint history, target reach tracking, battery semantics, and synchronous completion behavior.

**Example Request:**
```bash
curl -X POST http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/command/move_along_path \
  -H "Content-Type: application/json" \
  -d '{
    "waypoints": [
      {"x": 10.0, "y": 20.0, "z": 15.0},
      {"x": 30.0, "y": 40.0},
      {"x": 50.0, "y": 60.0, "z": 15.0}
    ],
    "allow_partial_move": true
  }'
```

### Charge Battery

**Endpoint:** `POST /drones/{drone_id}/command/charge`

**Description:** Commands a drone to charge its battery.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |
| charge_amount | float | Yes | Amount to charge in percentage (0-100) |

**Response:** Command response object

**Example Request:**
```bash
curl -X POST "http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/command/charge?charge_amount=25.0"
```

## Battery Management API

### Update Battery Level

**Endpoint:** `POST /drones/{drone_id}/battery`

**Description:** Updates a drone's battery level directly (for testing purposes).

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| drone_id | string | Yes | ID of the drone (in URL path) |
| battery_level | float | Yes | Battery level percentage (0-100) |

**Request Body:**
```json
{
  "battery_level": 75.0
}
```

**Response:** Updated drone object

**Example Request:**
```bash
curl -X POST http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/battery \
  -H "Content-Type: application/json" \
  -d '{"battery_level": 75.0}'
```

**Example Response:**
```json
{
  "message": "Battery level updated to 75.0%",
  "drone_id": "550e8400-e29b-41d4-a716-446655440000",
  "battery_level": 75.0,
  "status": "idle"
}
```

### Land All Drones

**Endpoint:** `POST /drones/land_all`

**Authentication:** Requires SYSTEM role (ADMIN inherits)

**Description:** Administrative command to immediately land all drones in the system. This is a management command that bypasses the normal command queue and directly sets all drones to ground level.

**Behavior:**
- Lands all drones to the ground (altitude = 0)
- Changes status to IDLE for all drones (except those in EMERGENCY status)
- No battery consumption occurs
- Not a user command - this is an administrative/management function
- Records status changes in session history

**Parameters:** None

**Response:** Summary object with details about each drone

**Example Request:**
```bash
curl -X POST http://localhost:8000/drones/land_all \
  -H "X-API-Key: <SYSTEM_API_KEY>"
```

**Example Response:**
```json
{
  "message": "Successfully landed 3 drone(s)",
  "total_drones": 3,
  "drones_landed": 2,
  "drones_already_grounded": 1,
  "details": [
    {
      "drone_id": "drone-001",
      "drone_name": "Alpha",
      "previous_status": "hovering",
      "previous_altitude": 15.0,
      "new_status": "idle",
      "new_altitude": 0.0,
      "action": "landed"
    },
    {
      "drone_id": "drone-002",
      "drone_name": "Beta",
      "previous_status": "flying",
      "previous_altitude": 20.0,
      "new_status": "idle",
      "new_altitude": 0.0,
      "action": "landed"
    },
    {
      "drone_id": "drone-003",
      "drone_name": "Gamma",
      "previous_status": "idle",
      "previous_altitude": 0.0,
      "new_status": "idle",
      "new_altitude": 0.0,
      "action": "already_on_ground"
    }
  ]
}
```

**Use Cases:**
- Emergency shutdown of all flight operations
- Reset simulation to ground state
- End of mission procedures
- Testing and development scenarios

**Note:** Drones in EMERGENCY status will be landed but will retain their EMERGENCY status.


### Charge All Drones

**Endpoint:** `POST /drones/charge_all`

**Authentication:** Requires SYSTEM role (ADMIN inherits)

**Description:** Administrative command to instantly set all drone batteries to full. This is a management command that bypasses the normal command queue and directly updates battery levels for every drone, regardless of location or status.

**Behavior:**
- Sets battery level to 100% for all drones
- Updates battery volume accordingly
- Does not change position or status
- Not a user command - this is an administrative/management function
- Records status updates in session history

**Parameters:** None

**Response:** Summary object with details about each drone

**Example Request:**
```bash
curl -X POST http://localhost:8000/drones/charge_all \
  -H "X-API-Key: <SYSTEM_API_KEY>"
```

**Example Response:**
```json
{
  "message": "Successfully charged 3 drone(s)",
  "total_drones": 3,
  "drones_charged": 2,
  "drones_already_full": 1,
  "details": [
    {
      "drone_id": "drone-001",
      "drone_name": "Alpha",
      "previous_battery_level": 45.0,
      "previous_battery_volume": 450.0,
      "new_battery_level": 100.0,
      "new_battery_volume": 1000.0,
      "action": "charged"
    },
    {
      "drone_id": "drone-002",
      "drone_name": "Beta",
      "previous_battery_level": 100.0,
      "previous_battery_volume": 1000.0,
      "new_battery_level": 100.0,
      "new_battery_volume": 1000.0,
      "action": "already_full"
    }
  ]
}
```

**Use Cases:**
- Reset simulation energy state across the fleet
- Testing with fully charged batteries
- Rapidly recover from low-battery scenarios in development



## Target API
### Get All Targets

**Endpoint:** `GET /targets`

**Description:** Retrieves a list of all targets in the system.

**Parameters:** None

**Response:** Array of target objects

**Example Request:**
```bash
curl -X GET http://localhost:8000/targets
```

**Example Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Landing Zone Alpha",
    "type": "fixed",
    "position": {"x": 100.0, "y": 200.0, "z": 0.0},
    "description": "Primary landing zone",
    "velocity": {"x": 0.0, "y": 0.0, "z": 0.0},
    "radius": 5.0,
    "created_at": 1620000000.0,
    "last_updated": 1620000000.0,
    "moving_path": null,
    "current_path_index": null,
    "charge_amount": null
  }
]
```

### Add a New Target

**Endpoint:** `POST /targets`

**Description:** Adds a new target to the system.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | Yes | Name of the target |
| type | string | Yes | Type of target (fixed, moving, waypoint, circle, polygon) - Note: fixed type can also represent points of interest |
| position | object | Yes | Position coordinates {x, y, z} |
| description | string | No | Description of the target (default: "") |
| velocity | object | No | Velocity for moving targets {x, y, z}. **PRIORITY 1**: If non-zero, uses velocity-based movement (ignores moving_path). Can be 1D, 2D, or 3D (default: {x: 0, y: 0, z: 0}) |
| radius | float | No | Target radius/size in meters (default: 1.0) |
| moving_path | array | No | Array of waypoint coordinates for moving targets [{x, y, z}, ...]. **PRIORITY 2**: Used only when velocity is zero/null. Target ping-pongs along path. Consecutive duplicate waypoints are rejected, and path waypoints/segments are validated against obstacles. |
| moving_duration | float | No | Time in seconds. **Velocity mode**: Time before reversing direction. **Path mode**: Time to complete one-way traverse (speed auto-calculated as path_length/duration). **If 0**: Target is stationary (default: 10.0) |
| charge_amount | float | No | Instant charge amount for waypoint targets (battery percentage) |
| vertices | array | No (Required for polygon) | Polygon vertices [{x, y}, ...], absolute world coordinates |

**Movement Priority System for Moving Targets:**
1. **VELOCITY (Priority 1)**: If `velocity` has non-zero components AND `moving_duration > 0` → Velocity-based ping-pong movement (ignores `moving_path`)
2. **PATH (Priority 2)**: If `velocity` is zero/null AND `moving_path` exists AND `moving_duration > 0` → Path-based movement with auto-calculated speed
3. **STATIONARY**: If `moving_duration == 0` → Target does not move

**Canonical runtime fields returned for moving targets:**
- `movement_mode`: One of `velocity`, `path`, or `stationary`
- `last_motion_update`: Timestamp of the most recent motion update
- `tracking_status`: One of `tracked`, `stale`, or `never_tracked`
- `last_tracked_at`: Most recent backend tracking timestamp

**Compatibility note:** Existing request fields remain unchanged. Legacy response fields such as `is_reached` and `reached_by` are still returned for compatibility, but moving-target freshness is backend-derived from tracking state instead of a UI-only timeout.

**Response:** Newly created target object

**Example Request (Fixed Target):**
```bash
curl -X POST http://localhost:8000/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Landing Zone Alpha",
    "type": "fixed",
    "position": {"x": 100.0, "y": 200.0, "z": 0.0},
    "description": "Primary landing zone",
    "radius": 5.0
  }'
```

**Example Request (Moving Target - Path-based):**
```bash
curl -X POST http://localhost:8000/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Patrol Target",
    "type": "moving",
    "position": {"x": 200.0, "y": 200.0, "z": 10.0},
    "description": "Moving patrol target",
    "velocity": {"x": 2.0, "y": 2.0, "z": 0.0},
    "radius": 3.0,
    "moving_path": [
      {"x": 250.0, "y": 200.0, "z": 10.0},
      {"x": 250.0, "y": 250.0, "z": 10.0},
      {"x": 200.0, "y": 250.0, "z": 10.0},
      {"x": 200.0, "y": 200.0, "z": 10.0}
    ]
  }'
```

**Example Request (Moving Target - Velocity-based ping-pong):**
```bash
# PRIORITY 1: Velocity-based movement (ignores moving_path even if present)
curl -X POST http://localhost:8000/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Oscillating Target",
    "type": "moving",
    "position": {"x": 300.0, "y": 300.0, "z": 5.0},
    "description": "Target moving back and forth every 10 seconds",
    "velocity": {"x": 3.0, "y": 0.0, "z": 0.0},
    "radius": 2.0,
    "moving_duration": 10.0
  }'
# Result: Moves in X direction at 3 m/s, reverses every 10 seconds
```

**Example Request (Moving Target - Path-based with auto speed):**
```bash
# PRIORITY 2: Path-based movement (only when velocity is zero/null)
curl -X POST http://localhost:8000/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Patrol Target",
    "type": "moving",
    "position": {"x": 0.0, "y": 0.0, "z": 0.0},
    "description": "Target patrolling a square path",
    "velocity": null,
    "radius": 2.0,
    "moving_path": [
      {"x": 0, "y": 0, "z": 0},
      {"x": 100, "y": 0, "z": 0},
      {"x": 100, "y": 100, "z": 0},
      {"x": 0, "y": 100, "z": 0}
    ],
    "moving_duration": 30.0
  }'
# Result: Path length = 300m. Speed = 300/30 = 10 m/s.
# Completes one-way traverse in 30 seconds, then reverses
```

**Example Request (Moving Target - Stationary):**
```bash
# STATIONARY: moving_duration = 0
curl -X POST http://localhost:8000/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Static Target",
    "type": "moving",
    "position": {"x": 200.0, "y": 200.0, "z": 5.0},
    "description": "Target that does not move",
    "velocity": {"x": 3.0, "y": 0.0, "z": 0.0},
    "radius": 2.0,
    "moving_duration": 0.0
  }'
# Result: Target remains stationary at position
```

**Example Request (Waypoint/Charging Station):**
```bash
curl -X POST http://localhost:8000/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Charging Station 1",
    "type": "waypoint",
    "position": {"x": 50.0, "y": 50.0, "z": 0.0},
    "description": "Charging station for drones",
    "radius": 10.0,
    "charge_amount": 30.0
  }'
```

**Example Request (Circle Target):**
```bash
curl -X POST http://localhost:8000/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Circular Survey Area",
    "type": "circle",
    "position": {"x": 260.0, "y": 40.0, "z": 0.0},
    "description": "Geometric circle target",
    "radius": 12.0
  }'
```

**Example Request (Polygon Target):**
```bash
curl -X POST http://localhost:8000/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Polygon Inspection Zone",
    "type": "polygon",
    "position": {"x": 520.0, "y": 220.0, "z": 0.0},
    "description": "Geometric polygon target",
    "vertices": [
      {"x": 500.0, "y": 200.0},
      {"x": 540.0, "y": 200.0},
      {"x": 560.0, "y": 240.0},
      {"x": 520.0, "y": 260.0},
      {"x": 480.0, "y": 240.0}
    ]
  }'
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Landing Zone Alpha",
  "type": "fixed",
  "position": {"x": 100.0, "y": 200.0, "z": 0.0},
  "description": "Primary landing zone",
  "velocity": null,
  "radius": 5.0,
  "created_at": 1620000000.0,
  "last_updated": 1620000000.0,
  "moving_path": null,
  "current_path_index": null,
  "charge_amount": null
}
```

### Get a Specific Target

**Endpoint:** `GET /targets/{target_id}`

**Description:** Retrieves information about a specific target.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| target_id | string | Yes | ID of the target (in URL path) |

**Response:** Target object

**Example Request:**
```bash
curl -X GET http://localhost:8000/targets/550e8400-e29b-41d4-a716-446655440000
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Landing Zone Alpha",
  "type": "fixed",
  "position": {"x": 100.0, "y": 200.0, "z": 0.0},
  "description": "Primary landing zone",
  "velocity": null,
  "radius": 5.0,
  "created_at": 1620000000.0,
  "last_updated": 1620000000.0,
  "moving_path": null,
  "current_path_index": null,
  "charge_amount": null
}
```

### Get Targets by Type

**Endpoint:** `GET /targets/type/{type}`

**Description:** Retrieves all targets of a specific type.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| type | string | Yes | Type of targets to retrieve (in URL path) |

**Response:** Array of target objects

**Example Request:**
```bash
curl -X GET "http://localhost:8000/targets/type/waypoint"
```

**Available Target Types:**
- `fixed` - Fixed targets with a specific position and radius (can also be used for points of interest)
- `moving` - Moving targets with velocity and optional path waypoints
- `waypoint` - Charging stations or waypoints for drone navigation
- `circle` - Geometric circle target defined by `radius` at `position`
- `polygon` - Geometric polygon target defined by `vertices` (absolute coordinates)

#### UI Rendering Notes (Targets)
- `circle`: Rendered filled with a thin white outline; selection uses a small rectangular indicator centered on the target.
- `polygon`: Rendered filled with a white outline; selection highlights the polygon boundary with an expanded margin around the shape for clarity. Labels render outside the top-right boundary, and the details panel omits radius while listing numbered vertex coordinates under `Vertices: <target name>`.
- Selected polygon obstacles also list numbered vertex coordinates in the details panel.
- Selected drones, targets, and obstacles are highlighted with a yellow ring in the mini-map.

## Waypoint API

### Check Drone at Waypoint

**Endpoint:** `POST /targets/waypoints/{waypoint_id}/check-drone`

**Description:** Checks if a drone is within a waypoint's radius and returns charging information if applicable.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| waypoint_id | string | Yes | ID of the waypoint (in URL path) |
| drone_position | object | Yes | Drone position coordinates {x, y, z} (in request body) |

**Request Body:**
```json
{
  "x": 52.0,
  "y": 48.0,
  "z": 0.0
}
```

**Response:**
```json
{
  "waypoint_id": "sim-waypoint-001",
  "drone_in_range": true,
  "charge_amount": 30.0,
  "drone_position": {"x": 52.0, "y": 48.0, "z": 0.0}
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/targets/waypoints/sim-waypoint-001/check-drone" \
  -H "Content-Type: application/json" \
  -d '{"x": 52.0, "y": 48.0, "z": 0.0}'
```

### Update a Target

**Endpoint:** `PUT /targets/{target_id}`

**Description:** Updates a target's properties.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| target_id | string | Yes | ID of the target (in URL path) |
| name | string | No | New name of the target |
| position | object | No | New position coordinates {x, y, z} |
| description | string | No | New description of the target |
| velocity | object | No | New velocity for moving targets {x, y, z}. Setting to zero/null switches to path-based mode |
| radius | float | No | New target radius/size in meters |
| moving_path | array | No | New path waypoints for moving targets [{x, y, z}, ...]. Speed recalculated if in path mode. Consecutive duplicate waypoints are rejected, and path waypoints/segments are validated against obstacles. |
| moving_duration | float | No | New time duration (seconds). Updates affect speed calculation for path mode |
| charge_amount | float | No | New instant charge amount for waypoint targets |

**Note:** Changing `velocity`, `moving_path`, or `moving_duration` may switch between movement modes based on priority rules. Updated target responses include `movement_mode`, and moving targets also include `tracking_status` and `last_tracked_at`.

**Response:** Updated target object

**Example Request:**
```bash
curl -X PUT http://localhost:8000/targets/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Landing Zone Bravo",
    "description": "Secondary landing zone"
  }'
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Landing Zone Bravo",
  "type": "fixed",
  "position": {"x": 100.0, "y": 200.0, "z": 0.0},
  "description": "Secondary landing zone",
  "velocity": null,
  "radius": 5.0,
  "created_at": 1620000000.0,
  "last_updated": 1620000100.0,
  "moving_path": null,
  "current_path_index": null,
  "charge_amount": null
}
```

### Delete a Target

**Endpoint:** `DELETE /targets/{target_id}`

**Description:** Deletes a target from the system.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| target_id | string | Yes | ID of the target (in URL path) |

**Response:** No content (204)

**Example Request:**
```bash
curl -X DELETE http://localhost:8000/targets/550e8400-e29b-41d4-a716-446655440000
```

## Environment API

### Get All Environments

**Endpoint:** `GET /environments`

**Description:** Retrieves a list of all environments in the system.

**Parameters:** None

**Response:** Array of environment objects

**Example Request:**
```bash
curl -X GET http://localhost:8000/environments
```

**Example Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Sunny Day",
    "weather": "clear",
    "temperature": 25.0,
    "humidity": 40.0,
    "pressure": 1013.25,
    "wind_speed": 5.0,
    "wind_direction": "north",
    "visibility": 10000.0,
    "created_at": 1620000000.0,
    "last_updated": 1620000000.0
  }
]
```

### Create a New Environment

**Endpoint:** `POST /environments`

**Description:** Creates a new environment in the system.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | Yes | Name of the environment |
| weather | string | Yes | Weather condition (clear, partly_cloudy, cloudy, rain, heavy_rain, snow, fog, windy, storm) |
| temperature | float | Yes | Temperature in Celsius |
| humidity | float | Yes | Humidity percentage |
| pressure | float | No | Atmospheric pressure in hPa (default: 1013.25) |
| wind_speed | float | No | Wind speed in m/s (default: 0.0) |
| wind_direction | string | No | Wind direction (north, northeast, east, southeast, south, southwest, west, northwest) (default: north) |
| visibility | float | No | Visibility in meters (default: 10000.0) |

**Response:** Newly created environment object

**Example Request:**
```bash
curl -X POST http://localhost:8000/environments \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Stormy Weather",
    "weather": "storm",
    "temperature": 15.0,
    "humidity": 80.0,
    "wind_speed": 20.0,
    "wind_direction": "west",
    "visibility": 2000.0
  }'
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "Stormy Weather",
  "weather": "storm",
  "temperature": 15.0,
  "humidity": 80.0,
  "pressure": 1013.25,
  "wind_speed": 20.0,
  "wind_direction": "west",
  "visibility": 2000.0,
  "created_at": 1620000100.0,
  "last_updated": 1620000100.0
}
```

### Get Current Environment

**Endpoint:** `GET /environments/current`

**Description:** Retrieves the current active environment.

**Parameters:** None

**Response:** Environment object

**Example Request:**
```bash
curl -X GET http://localhost:8000/environments/current
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Sunny Day",
  "weather": "clear",
  "temperature": 25.0,
  "humidity": 40.0,
  "pressure": 1013.25,
  "wind_speed": 5.0,
  "wind_direction": "north",
  "visibility": 10000.0,
  "created_at": 1620000000.0,
  "last_updated": 1620000000.0
}
```

### Set Current Environment

**Endpoint:** `POST /environments/{environment_id}/set-current`

**Description:** Sets an environment as the current active one.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| environment_id | string | Yes | ID of the environment (in URL path) |

**Response:** The environment object that was set as current

**Example Request:**
```bash
curl -X POST http://localhost:8000/environments/550e8400-e29b-41d4-a716-446655440001/set-current
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "Stormy Weather",
  "weather": "storm",
  "temperature": 15.0,
  "humidity": 80.0,
  "pressure": 1013.25,
  "wind_speed": 20.0,
  "wind_direction": "west",
  "visibility": 2000.0,
  "created_at": 1620000100.0,
  "last_updated": 1620000100.0
}
```

### Get a Specific Environment

**Endpoint:** `GET /environments/{environment_id}`

**Description:** Retrieves information about a specific environment.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| environment_id | string | Yes | ID of the environment (in URL path) |

**Response:** Environment object

**Example Request:**
```bash
curl -X GET http://localhost:8000/environments/550e8400-e29b-41d4-a716-446655440001
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "Stormy Weather",
  "weather": "storm",
  "temperature": 15.0,
  "humidity": 80.0,
  "pressure": 1013.25,
  "wind_speed": 20.0,
  "wind_direction": "west",
  "visibility": 2000.0,
  "created_at": 1620000100.0,
  "last_updated": 1620000100.0
}
```

### Update an Environment

**Endpoint:** `PUT /environments/{environment_id}`

**Description:** Updates an environment's properties.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| environment_id | string | Yes | ID of the environment (in URL path) |
| name | string | No | New name of the environment |
| weather | string | No | New weather condition |
| temperature | float | No | New temperature in Celsius |
| humidity | float | No | New humidity percentage |
| pressure | float | No | New atmospheric pressure in hPa |
| wind_speed | float | No | New wind speed in m/s |
| wind_direction | string | No | New wind direction |
| visibility | float | No | New visibility in meters |

**Response:** Updated environment object

**Example Request:**
```bash
curl -X PUT http://localhost:8000/environments/550e8400-e29b-41d4-a716-446655440001 \
  -H "Content-Type: application/json" \
  -d '{
    "weather": "heavy_rain",
    "wind_speed": 25.0
  }'
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "Stormy Weather",
  "weather": "heavy_rain",
  "temperature": 15.0,
  "humidity": 80.0,
  "pressure": 1013.25,
  "wind_speed": 25.0,
  "wind_direction": "west",
  "visibility": 2000.0,
  "created_at": 1620000100.0,
  "last_updated": 1620000200.0
}
```

### Delete an Environment

**Endpoint:** `DELETE /environments/{environment_id}`

**Description:** Deletes an environment from the system. Cannot delete the only environment.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| environment_id | string | Yes | ID of the environment (in URL path) |

**Response:** No content (204)

**Example Request:**
```bash
curl -X DELETE http://localhost:8000/environments/550e8400-e29b-41d4-a716-446655440001
```

## Obstacle API

### Get All Obstacles

**Endpoint:** `GET /obstacles`

**Description:** Retrieves a list of all obstacles in the system.

**Parameters:** None

**Response:** Array of obstacle objects

**Example Request:**
```bash
curl -X GET http://localhost:8000/obstacles
```

**Example Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Tall Building",
    "type": "polygon",
    "position": {"x": 100.0, "y": 200.0, "z": 0.0},
    "description": "Office building",
    "radius": null,
    "width": null,
    "length": null,
    "vertices": [
      {"x": 90.0, "y": 190.0, "z": 0.0},
      {"x": 110.0, "y": 190.0, "z": 0.0},
      {"x": 110.0, "y": 210.0, "z": 0.0},
      {"x": 90.0, "y": 210.0, "z": 0.0}
    ],
    "height": 50.0,
    "area": 400.0,
    "created_at": 1620000000.0,
    "last_updated": 1620000000.0
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "Water Tower",
    "type": "circle",
    "position": {"x": 300.0, "y": 400.0, "z": 0.0},
    "description": "Water tower",
    "radius": 15.0,
    "width": null,
    "length": null,
    "vertices": [],
    "height": 30.0,
    "area": 706.86,
    "created_at": 1620000100.0,
    "last_updated": 1620000100.0
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "name": "Garden Pond",
    "type": "ellipse",
    "position": {"x": 180.0, "y": 120.0, "z": 0.0},
    "description": "Elliptical pond area",
    "radius": null,
    "width": 20.0,
    "length": 15.0,
    "vertices": [],
    "height": 0.0,
    "area": 942.48,
    "created_at": 1620000200.0,
    "last_updated": 1620000200.0
  }
]
```

### Create a New Obstacle

**Endpoint:** `POST /obstacles`

**Description:** Creates a new obstacle in the system.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | Yes | Name of the obstacle |
| type | string | Yes | Type of obstacle (point, circle, ellipse, polygon) |
| position | object | Yes | Position coordinates {x, y, z} |
| description | string | No | Description of the obstacle (default: "") |
| radius | float | Conditional | Radius for point/circle obstacles (required for circle; defaults to 1.0 for point) |
| width | float | Conditional | Semi-major axis for elliptical obstacles (required for elliptical type) |
| length | float | Conditional | Semi-minor axis for elliptical obstacles (required for elliptical type) |
| vertices | array | Conditional | Vertices for polygon obstacles (required for polygon type, 3+ vertices) |
| height | float | No | Height in meters (default: 10.0); 0 = impassable at any altitude |

**Response:** Newly created obstacle object

**Example Request (Circle):**
```bash
curl -X POST http://localhost:8000/obstacles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Water Tower",
    "type": "circle",
    "position": {"x": 300.0, "y": 400.0, "z": 0.0},
    "description": "Water tower",
    "radius": 15.0,
    "height": 30.0
  }'
```

**Example Request (Polygon):**
```bash
curl -X POST http://localhost:8000/obstacles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tall Building",
    "type": "polygon",
    "position": {"x": 100.0, "y": 200.0, "z": 0.0},
    "description": "Office building",
    "vertices": [
      {"x": 90.0, "y": 190.0, "z": 0.0},
      {"x": 110.0, "y": 190.0, "z": 0.0},
      {"x": 110.0, "y": 210.0, "z": 0.0},
      {"x": 90.0, "y": 210.0, "z": 0.0}
    ],
    "height": 50.0
  }'
```

**Example Request (Elliptical):**
```bash
curl -X POST http://localhost:8000/obstacles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Garden Pond",
    "type": "ellipse",
    "position": {"x": 180.0, "y": 120.0, "z": 0.0},
    "description": "Elliptical pond - no fly zone",
    "width": 20.0,
    "length": 15.0,
    "height": 0.0
  }'
```

**Example Request (Point):**
```bash
curl -X POST http://localhost:8000/obstacles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Landing Marker",
    "type": "point",
    "position": {"x": 220.0, "y": 160.0, "z": 0.0},
    "description": "Landing zone marker",
    "radius": 2.0,
    "height": 0.5
  }'
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "Water Tower",
  "type": "circle",
  "position": {"x": 300.0, "y": 400.0, "z": 0.0},
  "description": "Water tower",
  "radius": 15.0,
  "vertices": null,
  "height": 30.0,
  "created_at": 1620000100.0,
  "last_updated": 1620000100.0
}
```

### Get a Specific Obstacle

**Endpoint:** `GET /obstacles/{obstacle_id}`

**Description:** Retrieves information about a specific obstacle.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| obstacle_id | string | Yes | ID of the obstacle (in URL path) |

**Response:** Obstacle object

**Example Request:**
```bash
curl -X GET http://localhost:8000/obstacles/550e8400-e29b-41d4-a716-446655440001
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "Water Tower",
  "type": "circle",
  "position": {"x": 300.0, "y": 400.0, "z": 0.0},
  "description": "Water tower",
  "radius": 15.0,
  "vertices": null,
  "height": 30.0,
  "created_at": 1620000100.0,
  "last_updated": 1620000100.0
}
```

### Update an Obstacle

**Endpoint:** `PUT /obstacles/{obstacle_id}`

**Description:** Updates an obstacle's properties.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| obstacle_id | string | Yes | ID of the obstacle (in URL path) |
| name | string | No | New name of the obstacle |
| position | object | No | New position coordinates {x, y, z} |
| description | string | No | New description of the obstacle |
| radius | float | No | New radius for circular obstacles |
| vertices | array | No | New vertices for polygonal obstacles |
| height | float | No | New height of the obstacle in meters |

**Response:** Updated obstacle object

**Example Request:**
```bash
curl -X PUT http://localhost:8000/obstacles/550e8400-e29b-41d4-a716-446655440001 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Large Water Tower",
    "radius": 20.0
  }'
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "Large Water Tower",
  "type": "circle",
  "position": {"x": 300.0, "y": 400.0, "z": 0.0},
  "description": "Water tower",
  "radius": 20.0,
  "vertices": null,
  "height": 30.0,
  "created_at": 1620000100.0,
  "last_updated": 1620000200.0
}
```

### Delete an Obstacle

**Endpoint:** `DELETE /obstacles/{obstacle_id}`

**Description:** Deletes an obstacle from the system.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| obstacle_id | string | Yes | ID of the obstacle (in URL path) |

**Response:** No content (204)

**Example Request:**
```bash
curl -X DELETE http://localhost:8000/obstacles/550e8400-e29b-41d4-a716-446655440001
```

### Get Obstacles by Type

**Endpoint:** `GET /obstacles/type/{type}`

**Description:** Retrieves all obstacles of a specific type.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| type | string | Yes | Type of obstacle (point, circle, ellipse, polygon) (in URL path) |

**Response:** Array of obstacle objects

**Example Request:**
```bash
curl -X GET http://localhost:8000/obstacles/type/polygon
```

**Example Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Tall Building",
    "type": "building",
    "position": {"x": 100.0, "y": 200.0, "z": 0.0},
    "description": "Office building",
    "radius": null,
    "vertices": [
      {"x": 90.0, "y": 190.0},
      {"x": 110.0, "y": 190.0},
      {"x": 110.0, "y": 210.0},
      {"x": 90.0, "y": 210.0}
    ],
    "height": 50.0,
    "created_at": 1620000000.0,
    "last_updated": 1620000000.0
  }
]
```

## Collision Detection API

### Check Path Collision

**Endpoint:** `POST /obstacles/path_collision`

**Authentication:** Requires SYSTEM role (ADMIN inherits)

**Description:** Checks if a flight path from start to end collides with any obstacles. Returns the **first** obstacle that collides with the path.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| start | object | Yes | Start point {x, y, z} |
| end | object | Yes | End point {x, y, z} |
| safety_margin | float | No | Additional clearance distance (in meters) around the flight path (default: 0.0). Creates a corridor with specified width on each side. Use 0.0 for direct line path, or > 0.0 for safety corridor (e.g., 5.0 creates a 10m-wide corridor). Note: Drone movement commands use 0.0 by default |

**Height Logic:**
- `height = 0`: Impassable at any altitude
- `height > 0`: Collision only if max flight altitude <= obstacle.height

**Response:** Collision response object or null if no collision

**Example Request:**
```bash
curl -X POST http://localhost:8000/obstacles/path_collision \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "start": {"x": 0.0, "y": 0.0, "z": 10.0},
    "end": {"x": 200.0, "y": 300.0, "z": 10.0},
    "safety_margin": 2.0
  }'
```

**Example Response (Collision):**
```json
{
  "obstacle_id": "550e8400-e29b-41d4-a716-446655440001",
  "obstacle_name": "Water Tower",
  "type": "circle",
  "collision_type": "path_intersection",
  "distance": 5.0
}
```

**Example Response (No Collision):**
```json
null
```

### Check Point Collision

**Endpoint:** `POST /obstacles/point_collision`

**Authentication:** Requires SYSTEM role (ADMIN inherits)

**Description:** Checks if a point is inside any obstacle or on its boundary within a margin. Returns **all** obstacles containing the point.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| x | float | Yes | X coordinate of the point |
| y | float | Yes | Y coordinate of the point |
| z | float | No | Z coordinate (altitude) of the point. If not provided, performs 2D check only |
| margin | float | No | Margin in meters around obstacles (default: 0.0). Expands obstacle geometry and height by this amount |

**Height Logic:**
- **z not provided**: Check 2D area only (all obstacles are non-flyable)
- **z provided + obstacle height = 0**: Non-flyable at any altitude
- **z provided + obstacle height > 0**:
  - Point is inside if `z <= obstacle.height + margin`
  - Point is outside if `z > obstacle.height + margin`

**Response:** Point in obstacles response object with list of all matching obstacles

**Example Request (2D Check):**
```bash
curl -X POST http://localhost:8000/obstacles/point_collision \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "x": 100.0,
    "y": 200.0,
    "margin": 0.0
  }'
```

**Example Request (3D Check with Altitude and Margin):**
```bash
curl -X POST http://localhost:8000/obstacles/point_collision \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "x": 100.0,
    "y": 200.0,
    "z": 5.0,
    "margin": 2.0
  }'
```

**Example Response (Point Inside Multiple Obstacles):**
```json
{
  "result": true,
  "inside_obstacle_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "550e8400-e29b-41d4-a716-446655440001"
  ],
  "inside_obstacles": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Building A",
      "type": "circle",
      "height": 30.0,
      "distance_to_boundary": -5.3
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "No-Fly Zone",
      "type": "polygon",
      "height": 0.0,
      "distance_to_boundary": -12.8
    }
  ],
  "point": {"x": 100.0, "y": 200.0, "z": 5.0},
  "margin": 2.0,
  "message": "Point is inside 2 obstacle(s)"
}
```

**Example Response (Point Outside All Obstacles):**
```json
{
  "result": false,
  "inside_obstacle_ids": [],
  "inside_obstacles": [],
  "point": {"x": 100.0, "y": 200.0, "z": 5.0},
  "margin": 0.0,
  "message": "Point is not inside any obstacles"
}
```
---

## Check Endpoints (ADMIN Only)

The `/check/` endpoints provide verification and validation capabilities for testing, monitoring, and automation scenarios. All endpoints in this category require ADMIN role authentication via `X-API-Key`.

### Standard Response Shape

Every check endpoint returns at least:

```json
{
  "result": true,
  "value": 0.75
}
```

- `result`: boolean outcome of the check (defaults to `false` if undecidable)
- `value`: the primary measured value (distance, altitude, progress ratio, etc.)
- Additional fields provide context (IDs, tolerances, lists, percentages, etc.)

### Endpoints (overview)

- **GET** `/check/drone_position` — distance to expected position (3D if `z` provided)
  - Params: `drone_id`, `x`, `y`, `z?`, `tolerance?`
  - `value`: distance (m); `result`: within tolerance
- **GET** `/check/drone_altitude` — altitude proximity
  - Params: `drone_id`, `expected_altitude`, `tolerance?`
  - `value`: current altitude
- **GET** `/check/drone_status` — status equality
  - Params: `drone_id`, `expected_status`
  - `value`: current status
- **GET** `/check/drone_on_ground` — altitude near ground with ground-like status
  - Params: `drone_id`, `tolerance?`
  - `value`: altitude
- **GET** `/check/all_drones_on_ground` — fleet ground-state count
  - Params: `tolerance?`
  - `value`: number of drones on ground
- **GET** `/check/drone_hovering` — hovering state above ground
  - Params: `drone_id`, `tolerance?`
  - `value`: current status
- **GET** `/check/all_drones_hovering` — fleet hovering count
  - Params: `tolerance?`
  - `value`: number of hovering drones
- **GET** `/check/drone_over_height` — altitude above minimum height
  - Params: `drone_id`, `min_height`, `tolerance?`
  - `value`: altitude (m)
- **GET** `/check/target_within_drone_distance` — is target within max distance of drone
  - Params: `drone_id`, `target_id`, `max_distance`
  - `value`: distance (m)
- **GET** `/check/obstacle_within_drone_distance` — is obstacle within max distance of drone
  - Params: `drone_id`, `obstacle_id`, `max_distance`
  - `value`: distance (m)
- **GET** `/check/two_drones_distance` — are two drones within distance range
  - Params: `drone_1_id`, `drone_2_id`, `max_distance?`, `min_distance?`
  - `value`: actual distance
- **GET** `/check/drone_group_distance` — do drone-group pairs satisfy distance range rules
  - Params: repeated `drone_ids` (at least 2), `max_distance?`, `min_distance?`, `mode?` (`all_pairs` default, or `any_pair`)
  - `value`: number of passing pairs
- **GET** `/check/drone_battery_level` — battery level vs minimum
  - Params: `drone_id`, `min_level?`
  - `value`: battery level (%)
- **GET** `/check/drone_heading` — heading within tolerance
  - Params: `drone_id`, `expected_heading`, `tolerance?`
  - `value`: current heading (deg)
- **GET** `/check/drone_in_target` — drone inside target radius
  - Params: `drone_id`, `target_id`
  - `value`: distance to target center (m)
- **GET** `/check/drone_at_home` — drone within tolerance of its home position
  - Params: `drone_id`, `tolerance?`
  - `value`: distance to home (m)
- **GET** `/check/target_within_drone_task_radius` — target inside drone task radius
  - Params: `drone_id`, `target_id`
  - `value`: distance (m)
- **GET** `/check/target_within_drone_perceived_radius` — target inside drone perceived radius
  - Params: `drone_id`, `target_id`
  - `value`: distance (m)
- **GET** `/check/obstacle_within_drone_perceived_radius` — obstacle inside drone perceived radius
  - Params: `drone_id`, `obstacle_id`
  - `value`: distance (m)
- **GET** `/check/drone_has_taken_off` — check if drone has taken off in history
  - Params: `drone_id`, `min_altitude?`, `max_altitude?`, `tolerance?`, `since_timestamp?`
  - `value`: number of takeoff events matching the requested altitude bounds
  - Modes:
    - threshold mode: omit `max_altitude`; matches takeoffs with altitude `>= min_altitude - tolerance`
    - range mode: provide both `min_altitude` and `max_altitude`; matches takeoffs within `[min_altitude - tolerance, max_altitude + tolerance]`
    - exact-height mode: set `min_altitude == max_altitude` and use `tolerance` as the acceptable band around that altitude
  - Response extras: `takeoff_count`, `last_takeoff_time`, `max_altitude_reached`, `min_altitude_threshold`, `max_altitude_threshold`, `tolerance`
- **GET** `/check/drone_has_landed` — check if drone has landed in history
  - Params: `drone_id`, `min_count?`, `since_timestamp?`
  - `value`: number of landing events found
- **GET** `/check/drone_has_visited_position` — check if drone has visited a position
  - Params: `drone_id`, `x`, `y`, `z?`, `tolerance?`, `since_timestamp?`
  - `value`: number of visits to position
- **GET** `/check/drone_has_moved_distance` — check if drone has moved minimum distance
  - Params: `drone_id`, `min_distance`, `since_timestamp?`
  - `value`: total distance moved (m)
- **GET** `/check/drone_has_moved_directed_distance` — check if drone has moved minimum distance in a specific direction
  - Params: `drone_id`, `min_distance`, `heading`, `tolerance?`, `since_timestamp?`
  - `value`: total directed distance (m)
- **GET** `/check/drone_has_hovered` — check if drone has hovered in history
  - Params: `drone_id`, `min_duration?`, `since_timestamp?`
  - `value`: number of hover events found
- **GET** `/check/drone_has_taken_photo` — check if drone has taken photos
  - Params: `drone_id`, `min_count?`, `since_timestamp?`
  - `value`: number of photos taken
- **GET** `/check/target_in_photo_taken_by_drone` — check if target in drone's photo
  - Params: `drone_id`, `target_id`
  - `value`: boolean result
- **GET** `/check/drone_has_charged` — check if drone has charged in history
  - Params: `drone_id`, `min_charge_amount?`, `since_timestamp?`
  - `value`: number of charging events found
  - Note: A charge event that tops the battery off to 100% satisfies `min_charge_amount` even if the actual charge is smaller.
- **GET** `/check/drone_has_sent_message` — check if drone has sent messages (includes broadcasts)
  - Params: `drone_id`, `to_drone_id?`, `min_count?`, `since_timestamp?`
  - `value`: number of messages sent
- **GET** `/check/drone_has_sent_message_content` — check if drone sent message text containing content
  - Params: `drone_id`, `content`, `to_drone_id?`, `min_count?`, `since_timestamp?`
  - `value`: number of matching messages
- **GET** `/check/all_drones_have_taken_off` — check if all drones have taken off
  - Params: `min_altitude?`, `since_timestamp?`, `check_history?`
  - `value`: number of drones that have taken off; `percentage` contains the fleet percentage
- **GET** `/check/all_drones_have_landed` — check if all drones have landed
  - Params: `min_count?`, `since_timestamp?`, `check_history?`
  - `value`: number of drones that have landed; `percentage` contains the fleet percentage
- **GET** `/check/target_is_reached` — any drone reached target
  - Params: `target_id`, `since_timestamp?`
  - `value`: number of drones that reached the target
- **GET** `/check/target_is_reached_by_drone` — specific drone reached target
  - Params: `target_id`, `drone_id`, `since_timestamp?`
  - `value`: visits count by that drone
- **GET** `/check/target_reached_drone_number` — reached drone count vs expectation
  - Params: `target_id`, `expected_count?`, `since_timestamp?`
  - `value`: number of drones that reached the target
- **GET** `/check/moving_target_tracked` — moving target tracked for at least a duration
  - Params: `target_id`, `drone_id?`, `min_duration?`, `since_timestamp?`
  - `value`: maximum retained tracked duration in seconds
- **GET** `/check/target_is_fully_searched` — area coverage threshold (default 0.99)
  - Params: `target_id`, `coverage_threshold?`
  - `value`: coverage ratio (0-1)
- **GET** `/check/target_searched_area_percentage` — coverage vs expected ratio
  - Params: `target_id`, `expected_percentage` (0-1)
  - `value`: coverage ratio (0-1)
- **GET** `/check/task_progress` — progress vs expected ratio
  - Params: `expected_progress?` (0-1)
  - `value`: progress ratio (0-1)
- **GET** `/check/task_done` — completion flag using session progress
  - Params: *(None)*
  - `value`: progress ratio (0-1)

### Examples

```bash
# Position within tolerance
curl -X GET "http://localhost:8000/check/drone_position?drone_id=drone-1&x=50.0&y=30.0&z=5.0&tolerance=2.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Target reach by specific drone
curl -X GET "http://localhost:8000/check/target_is_reached_by_drone?target_id=target-1&drone_id=drone-1" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Moving target tracked by any drone for at least 10 seconds
curl -X GET "http://localhost:8000/check/moving_target_tracked?target_id=target-1&min_duration=10.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Moving target tracked by a specific drone for at least 10 seconds
curl -X GET "http://localhost:8000/check/moving_target_tracked?target_id=target-1&drone_id=drone-1&min_duration=10.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check whether all pairwise distances in a drone group stay within bounds
curl -X GET "http://localhost:8000/check/drone_group_distance?drone_ids=drone-1&drone_ids=drone-2&drone_ids=drone-3&min_distance=10.0&max_distance=100.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check whether any pair in a drone group satisfies the distance bounds
curl -X GET "http://localhost:8000/check/drone_group_distance?drone_ids=drone-1&drone_ids=drone-2&drone_ids=drone-3&min_distance=10.0&max_distance=100.0&mode=any_pair" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check whether a drone sent message text containing a substring
curl -X GET "http://localhost:8000/check/drone_has_sent_message_content?drone_id=drone-1&content=alert" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check whether a drone sent matching content to a specific recipient
curl -X GET "http://localhost:8000/check/drone_has_sent_message_content?drone_id=drone-1&to_drone_id=drone-2&content=hold%20position" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Task progress meets expectation
curl -X GET "http://localhost:8000/check/task_progress?expected_progress=0.8" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if drone has taken off (history)
curl -X GET "http://localhost:8000/check/drone_has_taken_off?drone_id=drone-1&min_altitude=5.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if drone has taken off within an altitude range
curl -X GET "http://localhost:8000/check/drone_has_taken_off?drone_id=drone-1&min_altitude=9.0&max_altitude=11.0&tolerance=0.2" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if drone has taken off to about 10m (10.0 +/- 0.5)
curl -X GET "http://localhost:8000/check/drone_has_taken_off?drone_id=drone-1&min_altitude=10.0&max_altitude=10.0&tolerance=0.5" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if drone has visited a specific position
curl -X GET "http://localhost:8000/check/drone_has_visited_position?drone_id=drone-1&x=50.0&y=30.0&z=10.0&tolerance=2.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if drone has moved minimum distance
curl -X GET "http://localhost:8000/check/drone_has_moved_distance?drone_id=drone-1&min_distance=100.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if drone has moved minimum distance in a specific direction
curl -X GET "http://localhost:8000/check/drone_has_moved_directed_distance?drone_id=drone-1&min_distance=10.0&heading=90.0&tolerance=5.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if drone has taken photos
curl -X GET "http://localhost:8000/check/drone_has_taken_photo?drone_id=drone-1&min_count=3" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if all drones have taken off (check current status)
curl -X GET "http://localhost:8000/check/all_drones_have_taken_off?check_history=false&min_altitude=5.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if all drones are currently hovering
curl -X GET "http://localhost:8000/check/all_drones_hovering" \
  -H "X-API-Key: <ADMIN_API_KEY>"
```

---

  "session_name": "Area Search Mission",
  "task_type": "area_search",
  "is_completed": false,
  "progress_percentage": 75,
  "status_message": "Task to be Done",
  "details": {
    "total_targets": 2,
    "average_coverage": 75.5
  }
}
```

**Use Cases:**
- Automated testing and validation
- Mission monitoring and completion tracking
- CI/CD pipeline integration
- Performance benchmarking
