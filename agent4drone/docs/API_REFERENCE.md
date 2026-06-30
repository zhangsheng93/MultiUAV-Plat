# MultiUAV-Plat Server System API Reference

**Quick reference guide for developers**

> For comprehensive documentation with examples, see [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

## Base URL

```
http://localhost:8000
```

**Interactive Docs:** http://localhost:8000/docs

## Authentication

The API uses role-based access control with four roles:

| Role | Access | API Key Required |
|------|--------|-----------------|
| **USER** | Basic (control & view) | Yes |
| **AGENT** | Same as USER | Yes |
| **SYSTEM** | Management + USER/AGENT | Yes |
| **ADMIN** | Full access | Yes |

**Header:** `X-API-Key: <your-key>`

If no API key is provided, the server defaults to AGENT. USER, SYSTEM, and ADMIN each accept multiple hard-coded privilege keys; the actual values are stored in the software and omitted from documentation.

See [AUTHENTICATION.md](AUTHENTICATION.md) for details.

---

## Quick Links

| Category | Endpoints |
|----------|-----------|
| [Health](#health-check) | Server status |
| [Sessions](#session-management) | Session CRUD, reset, restore |
| [Session Tracking](#session-tracking) | Command history, status, reaches, coverage |
| [Task Management](#task-management) | Task CRUD, mark done/pending |
| [Drones](#drone-management) | Drone CRUD, battery |
| [Commands](#command-management) | Generic and direct commands |
| [Targets](#target-management) | Targets and waypoints |
| [Obstacles](#obstacle-management) | Obstacles and collisions |
| [Environment](#environment-management) | Weather conditions |
| [Proximity](#proximity) | Nearby entities around a drone |
| [Check](#check-endpoints-admin-only) | Status verification (ADMIN only) |

---

## Health Check

| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/` | `{"status":"online","message":"..."}` |
| GET | `/version` | `{"name":"...","version":"1.0.0"}` |

## Drone Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/drones` | List all drones |
| POST | `/drones` | Register new drone |
| GET | `/drones/{id}` | Get drone details |
| PUT | `/drones/{id}` | Update drone properties (metadata, state, battery, position, home) |
| PUT | `/drones/{id}/position` | Update drone position only |
| DELETE | `/drones/{id}` | Delete drone |
| POST | `/drones/{id}/battery` | Update battery level |
| POST | `/drones/land_all` | Land all drones immediately (SYSTEM+, management command) |
| POST | `/drones/charge_all` | Fully charge all drones (SYSTEM+, management command) |

## Command Management

### Generic Command Endpoint

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/drones/{id}/command` | Send any command |
| GET | `/drones/{id}/commands` | Get command history |
| GET | `/commands/{command_id}` | Get command status |

### Direct Command Endpoints

All commands use **POST** method with `/drones/{id}/command/{command_name}`

| Command | Parameters | Description |
|---------|-----------|-------------|
| `take_off` | `?altitude=10.0` | Takeoff to altitude |
| `land` | - | Land at position |
| `move_to` | `?x=50&y=50&z=15` | Move to coordinates; battery cost has no base |
| `move_towards` | `?distance=20&heading=90` | Move distance in direction (uses current heading if not specified) |
| `move_along_path` | Body: `{waypoints:[...]}` | Follow one or more waypoints; 2D waypoints use current altitude; battery cost has no per-waypoint base |
| `change_altitude` | `?altitude=20.0` | Change altitude only |
| `hover` | `duration` (optional) | Hold position |
| `rotate` | `?heading=180.0` | Change heading/orientation |
| `return_home` | - | Return to launch |
| `set_home` | - | Set home position |
| `calibrate` | - | Calibrate sensors |
| `take_photo` | - | Capture image |
| `send_message` | `?target_drone_id=X&message=Y` | Send to drone |
| `broadcast` | `?message=text` | Send to all |
| `charge` | `?charge_amount=30.0` | Charge battery |

## Target Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/targets` | List all targets |
| POST | `/targets` | Create target |
| GET | `/targets/{id}` | Get target details |
| PUT | `/targets/{id}` | Update target |
| DELETE | `/targets/{id}` | Delete target |
| GET | `/targets/type/{type}` | Get by type |
| POST | `/targets/waypoints/{id}/check-drone` | Check if drone is in range of waypoint charging |



## Environment Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/environments` | List all environments |
| POST | `/environments` | Create environment |
| GET | `/environments/current` | Get active environment |
| POST | `/environments/{id}/set-current` | Set as active |
| GET | `/environments/{id}` | Get environment |
| PUT | `/environments/{id}` | Update environment |
| DELETE | `/environments/{id}` | Delete environment |

## Obstacle Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/obstacles` | List all obstacles |
| POST | `/obstacles` | Create obstacle |
| GET | `/obstacles/{id}` | Get obstacle |
| PUT | `/obstacles/{id}` | Update obstacle |
| DELETE | `/obstacles/{id}` | Delete obstacle |
| GET | `/obstacles/type/{type}` | Get by type |

### Collision Detection

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/obstacles/path_collision` | Check if flight path collides with obstacles | SYSTEM |
| POST | `/obstacles/point_collision` | Check if point is inside any obstacles (returns all matches) | SYSTEM |

## Proximity

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/drones/{id}/nearby` | Aggregated nearby drones, targets, obstacles (uses drone's perceived_radius) |
| GET | `/drones/{id}/nearby/drones` | Nearby drones (uses drone's perceived_radius) |
| GET | `/drones/{id}/nearby/targets` | Nearby targets (uses drone's perceived_radius) |
| GET | `/drones/{id}/nearby/obstacles` | Nearby obstacles (uses drone's perceived_radius) |

All proximity endpoints use the drone's `perceived_radius` to determine the search area.

## Session Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sessions` | List all sessions (AGENT+, metadata only for AGENT/USER) |
| POST | `/sessions` | Create session with auto-generated ID (returns complete data by default) |
| POST | `/sessions/{id}` | Create/restore session with specific ID (returns complete data by default, smart entity detection) |
| GET | `/sessions/current` | Get active session (supports `?data=true` for complete data) |
| GET | `/sessions/current/data` | Get active session with complete data |
| POST | `/sessions/current/reset` | **NEW:** Reset current session history (clears stats/history, preserves entities) (SYSTEM+) |
| GET | `/sessions/{id}` | Get session (supports `?data=true` for complete data) |
| PUT | `/sessions/{id}` | Update session metadata (supports `?data=true`) |
| DELETE | `/sessions/{id}` | Delete session |
| POST | `/sessions/{id}/set-current` | Set as active (AGENT+, metadata only for AGENT/USER) |
| POST | `/sessions/{id}/reset` | Reset to initial state (SYSTEM+) |
| GET | `/sessions/{id}/data` | Export complete session data |

Session creation endpoints accept an optional `creator`; if omitted the server records the caller's role.

---

## Session Tracking

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sessions/current/request-history` | Recent HTTP requests for the current session (query `limit`) |
| GET | `/sessions/{id}/request-history` | Recent HTTP requests for a session (query `limit`) |
| DELETE | `/sessions/current/request-history` | Clear current-session runtime request history (SYSTEM+) |
| DELETE | `/sessions/{id}/request-history` | Clear runtime request history for a session (SYSTEM+) |
| GET | `/sessions/current/command-history` | Recent commands for the current session (query `limit`) |
| GET | `/sessions/{id}/command-history` | Recent commands (query `limit`) |
| GET | `/sessions/{id}/status-history` | Status changes (optional `drone_id`) |
| GET | `/sessions/{id}/target-reaches` | Compact target reach summaries and stats |
| GET | `/sessions/{id}/moving-target-tracking` | Compact moving-target tracking summaries |
| GET | `/sessions/{id}/area-coverage` | Coverage data and summary |
| GET | `/sessions/{id}/task-progress` | Task completion progress based on task type |

Request-history records include request/response details plus direct socket
`client_ip`/`client_port`, resolved `client_privilege`,
`authentication_status`, associated `session_id`, `query_params`, a
512-character-capped `user_agent`, and `agent_id`. API keys and forwarded
client-IP headers are not exposed or trusted. Query values remain raw strings
for replay, repeated keys are ordered arrays, sensitive keys are redacted, and
missing legacy `query_params` values normalize to `{}`.

Request-history storage retains 5,000 records per session by default and can be
changed with `main.py --request-history-limit N`. The endpoint `limit` query
remains capped at 1,000 records per response.

Request history is runtime-only and is returned only by the dedicated
request-history endpoints. It is excluded from session objects, exports,
imports, and restores, and is lost when the server process exits.
Request-history endpoint response bodies are intentionally omitted from
structured API logs and session request-history records for performance and
recursion safety.
`client_privilege` uses uppercase role names: `AGENT`, `USER`, `SYSTEM`, and
`ADMIN`. AGENT clients may call only `GET /sessions/current/request-history`;
they see only AGENT-authenticated records with the same normalized `X-Agent-ID`
value. AGENT requests without `X-Agent-ID` are attributed to `default_agent`.
SYSTEM and ADMIN clients see unfiltered request history, including
`GET /sessions/{id}/request-history`.

SYSTEM and ADMIN clients can clear runtime request history with
`DELETE /sessions/current/request-history` or
`DELETE /sessions/{id}/request-history`. These clear only request history,
return `{"cleared": true, "session_id": "...", "cleared_count": N}`, and are
not recorded back into the cleared request history.

**Note on Target Reaches**: Multiple visits to the same target are still recorded internally, but the API returns compact grouped summaries rather than a raw unbounded event log.



---

## Task Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sessions/current/tasks` | Get all tasks in current session (AGENT+) |
| GET | `/sessions/current/tasks/next` | Get next pending task in current session (AGENT+) |
| GET | `/sessions/current/tasks/{task_id}` | Get specific task from current session (AGENT+) |
| GET | `/sessions/current/tasks/{task_id}/check` | Check task and set is_passed when passed; optional `since_timestamp` scopes compatible history checks (AGENT+) |
| POST | `/sessions/current/tasks/{task_id}/mark-done` | Mark task as completed in current session (AGENT+) |
| POST | `/sessions/current/tasks/{task_id}/mark-pending` | Mark task as pending in current session (AGENT+) |
| GET | `/sessions/{session_id}/tasks` | Get all tasks in a session (USER+) |
| GET | `/sessions/{session_id}/tasks/{task_id}` | Get specific task (USER+) |
| POST | `/sessions/{session_id}/tasks` | Create a new task (SYSTEM+) |
| PUT | `/sessions/{session_id}/tasks/{task_id}` | Update task (SYSTEM+) |
| DELETE | `/sessions/{session_id}/tasks/{task_id}` | Delete task (SYSTEM+) |
| POST | `/sessions/{session_id}/tasks/{task_id}/mark-done` | Mark task as completed (SYSTEM+) |
| POST | `/sessions/{session_id}/tasks/{task_id}/mark-pending` | Mark task as pending (SYSTEM+) |
| POST | `/sessions/{session_id}/tasks/swap` | Swap the order of two tasks (SYSTEM+) |

**Note:**
- `related_apis` is an array of objects, where each object contains:
  - `endpoint`: API endpoint path (e.g., `/drones/{id}/command/move_to`)
  - `parameters`: Dictionary of parameter names to descriptions/example values
- `execution_check_apis` is a structured object describing logical combinations of `/check` calls:
  - `logic`: `and` (default), `or`, or `not`
  - `checks`: array of child nodes
  - Leaf nodes include `endpoint` (e.g., `/check/drone_position`), `parameters` (dict), optional `expect` (boolean, defaults to `true`) representing the expected `result`
- `GET /sessions/current/tasks/{task_id}/check?since_timestamp=...` passes the timestamp to compatible `/check` leaf endpoints that accept `since_timestamp`. A leaf-level `parameters.since_timestamp` takes precedence.

**Task Request Body (POST /sessions/{session_id}/tasks):**
```json
{
  "name": "area-search-alpha",
  "content": "Seach the area alpha",
  "content_aliases": ["search alpha", "scan zone 1"],
  "description": "Brief description",
  "creator": "mission-lead",
  "originated_from": "mission-lead",
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
          }
        ]
      }
    ]
  },
  "commands": ["take_off", "move_to", "take_photo", "land"]
}
```

If `creator` is omitted, the server records the caller's role as the creator.

**Task Response:**
```json
{
  "id": "task-abc123",
  "name": "area-search-alpha",
  "content": " Search Area Alpha for Targets",
  "content_aliases": ["search alpha", "scan zone 1"],
  "description": "Brief description",
  "creator": "system",
  "originated_from": "system",
  "related_apis": [
    {
      "endpoint": "/drones/{id}/command/move_to",
      "parameters": {
        "x": "X coordinate in meters",
        "y": "Y coordinate in meters",
        "z": "Z coordinate (altitude) in meters"
      }
    }
  ],
  "execution_check_apis": {
    "logic": "and",
    "checks": []
  },
  "commands": ["take_off", "move_to", "take_photo", "land"],
  "is_done": false,
  "is_passed": false,
  "created_at": 1620000000.0,
  "last_updated": 1620000000.0
}
```

**Swap Tasks Request Body (POST /sessions/{session_id}/tasks/swap):**
```json
{
  "task_id_1": "task-abc123",
  "task_id_2": "task-def456"
}
```

**Swap Tasks Response (200 OK):**
Returns an array of all tasks in the session in their new order:
```json
[
  {
    "id": "task-def456",
    "name": "area-patrol-bravo",
    "content": "Patrol area bravo...",
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
    "content": "Search area alpha...",
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

---

## Quick Reference - Data Models

### Key Request Bodies

#### Register Drone (POST /drones)

**Request Body:**
```json
{
  "name": "Scout Alpha",
  "model": "Model-D4",
  "max_speed": 20.0,
  "max_altitude": 120.0,
  "battery_capacity": 4000.0,
  "position": {"x": 100.0, "y": 100.0, "z": 0.0},
  "heading": 45.0,
  "speed": 0.0,
  "battery_volume": 3200.0,
  "status": "idle",
  "home_position": {"x": 0.0, "y": 0.0, "z": 0.0},
  "perceived_radius": 100.0,
  "task_radius": 10.0
}
```

**Response (201 Created):**
```json
{
  "id": "d4f3a9b2",
  "name": "Scout Alpha",
  "model": "Model-D4",
  "status": "idle",
  "position": {"x": 100.0, "y": 100.0, "z": 0.0},
  "heading": 45.0,
  "speed": 0.0,
  "battery_level": 100.0,
  "battery_volume": 4000.0,
  "battery_capacity": 4000.0,
  "max_speed": 20.0,
  "max_altitude": 120.0,
  "perceived_radius": 100.0,
  "task_radius": 10.0,
  "home_position": {"x": 100.0, "y": 100.0, "z": 0.0},
  "created_at": 1704067200.0,
  "last_updated": 1704067200.0
}
```

#### Update Drone (PUT /drones/{id})

**Request Body (all fields optional):**
```json
{
  "name": "Scout Alpha Updated",
  "model": "Model-D5",
  "max_speed": 25.0,
  "max_altitude": 150.0,
  "battery_capacity": 5000.0,
  "perceived_radius": 120.0,
  "task_radius": 15.0,
  "status": "hovering",
  "position": {"x": 100.0, "y": 50.0, "z": 20.0},
  "heading": 90.0,
  "speed": 5.0,
  "battery_level": 80.0,
  "battery_volume": 4000.0,
  "home_position": {"x": 0.0, "y": 0.0, "z": 0.0}
}
```

**Partial Position Update (only altitude):**
```json
{
  "position": {"z": 25.0}
}
```

**Response (200 OK):**
```json
{
  "id": "d4f3a9b2",
  "name": "Scout Alpha Updated",
  "model": "Model-D5",
  "status": "hovering",
  "position": {"x": 100.0, "y": 50.0, "z": 20.0},
  "heading": 90.0,
  "speed": 5.0,
  "battery_level": 80.0,
  "battery_volume": 4000.0,
  "battery_capacity": 5000.0,
  "max_speed": 25.0,
  "max_altitude": 150.0,
  "perceived_radius": 120.0,
  "task_radius": 15.0,
  "home_position": {"x": 0.0, "y": 0.0, "z": 0.0},
  "created_at": 1704067200.0,
  "last_updated": 1704067500.0
}
```

#### Send Command
```json
POST /drones/{id}/command
{
  "command": "move_to",
  "parameters": {"x": 50.0, "y": 50.0, "z": 15.0}
}
```

#### Create Target (POST /targets)

**Request Body (Fixed Target):**
```json
{
  "name": "Checkpoint Alpha",
  "type": "fixed",
  "position": {"x": 100.0, "y": 50.0, "z": 0.0},
  "radius": 5.0,
  "description": "Primary checkpoint for mission"
}
```

**Response (201 Created):**
```json
{
  "id": "t1a2b3c4",
  "name": "Checkpoint Alpha",
  "type": "fixed",
  "position": {"x": 100.0, "y": 50.0, "z": 0.0},
  "description": "Primary checkpoint for mission",
  "radius": 5.0,
  "velocity": null,
  "moving_path": null,
  "current_path_index": null,
  "charge_amount": null,
  "vertices": null,
  "created_at": 1704067200.0,
  "last_updated": 1704067200.0
}
```

**Request Body (Waypoint/Charging Station):**
```json
{
  "name": "Charging Station 1",
  "type": "waypoint",
  "position": {"x": 100.0, "y": 50.0, "z": 0.0},
  "radius": 10.0,
  "charge_amount": 30.0,
  "description": "Primary charging station"
}
```

**Response (201 Created):**
```json
{
  "id": "w5d6e7f8",
  "name": "Charging Station 1",
  "type": "waypoint",
  "position": {"x": 100.0, "y": 50.0, "z": 0.0},
  "description": "Primary charging station",
  "radius": 10.0,
  "velocity": null,
  "moving_path": null,
  "current_path_index": null,
  "charge_amount": 30.0,
  "vertices": null,
  "created_at": 1704067200.0,
  "last_updated": 1704067200.0
}
```

**Request Body (Moving Target):**
```json
{
  "name": "Moving Target 1",
  "type": "moving",
  "position": {"x": 50.0, "y": 50.0, "z": 10.0},
  "radius": 3.0,
  "velocity": {"x": 2.0, "y": 1.0, "z": 0.0},
  "moving_path": [
    {"x": 50.0, "y": 50.0, "z": 10.0},
    {"x": 100.0, "y": 80.0, "z": 10.0},
    {"x": 150.0, "y": 50.0, "z": 10.0}
  ],
  "description": "Patrol target with predefined path"
}
```

**Response (201 Created):**
```json
{
  "id": "m9g0h1i2",
  "name": "Moving Target 1",
  "type": "moving",
  "position": {"x": 50.0, "y": 50.0, "z": 10.0},
  "description": "Patrol target with predefined path",
  "radius": 3.0,
  "velocity": {"x": 2.0, "y": 1.0, "z": 0.0},
  "moving_path": [
    {"x": 50.0, "y": 50.0, "z": 10.0},
    {"x": 100.0, "y": 80.0, "z": 10.0},
    {"x": 150.0, "y": 50.0, "z": 10.0}
  ],
  "current_path_index": 0,
  "moving_duration": 10.0,
  "path_direction": 1,
  "time_in_direction": 0.0,
  "movement_mode": "velocity",
  "calculated_speed": null,
  "last_motion_update": 1704067200.0,
  "tracking_status": "never_tracked",
  "last_tracked_at": null,
  "charge_amount": null,
  "vertices": null,
  "is_reached": false,
  "reached_by": [],
  "created_at": 1704067200.0,
  "last_updated": 1704067200.0
}
```

**Request Body (Moving Target - Velocity-based Ping-Pong / PRIORITY 1):**
```json
{
  "name": "Oscillating Target",
  "type": "moving",
  "position": {"x": 100.0, "y": 100.0, "z": 5.0},
  "radius": 2.0,
  "velocity": {"x": 3.0, "y": 0.0, "z": 0.0},
  "moving_duration": 10.0,
  "description": "Target moving back and forth along X-axis every 10 seconds"
}
```

**Response (201 Created):**
```json
{
  "id": "m9g0h1i3",
  "name": "Oscillating Target",
  "type": "moving",
  "position": {"x": 100.0, "y": 100.0, "z": 5.0},
  "description": "Target moving back and forth along X-axis every 10 seconds",
  "radius": 2.0,
  "velocity": {"x": 3.0, "y": 0.0, "z": 0.0},
  "moving_path": [],
  "current_path_index": 0,
  "moving_duration": 10.0,
  "path_direction": 1,
  "time_in_direction": 0.0,
  "movement_mode": "velocity",
  "calculated_speed": null,
  "last_motion_update": 1704067200.0,
  "tracking_status": "never_tracked",
  "last_tracked_at": null,
  "charge_amount": null,
  "vertices": null,
  "is_reached": false,
  "reached_by": [],
  "created_at": 1704067200.0,
  "last_updated": 1704067200.0
}
```

**Request Body (Moving Target - Path-based with Auto Speed / PRIORITY 2):**
```json
{
  "name": "Patrol Target",
  "type": "moving",
  "position": {"x": 0.0, "y": 0.0, "z": 0.0},
  "radius": 2.0,
  "velocity": null,
  "moving_path": [
    {"x": 0, "y": 0, "z": 0},
    {"x": 100, "y": 0, "z": 0},
    {"x": 100, "y": 100, "z": 0}
  ],
  "moving_duration": 20.0,
  "description": "Target with auto-calculated speed from path and duration"
}
```

**Response (201 Created):**
```json
{
  "id": "m9g0h1i4",
  "name": "Patrol Target",
  "type": "moving",
  "position": {"x": 0.0, "y": 0.0, "z": 0.0},
  "description": "Target with auto-calculated speed from path and duration",
  "radius": 2.0,
  "velocity": null,
  "moving_path": [
    {"x": 0, "y": 0, "z": 0},
    {"x": 100, "y": 0, "z": 0},
    {"x": 100, "y": 100, "z": 0}
  ],
  "current_path_index": 0,
  "moving_duration": 20.0,
  "path_direction": 1,
  "time_in_direction": 0.0,
  "movement_mode": "path",
  "calculated_speed": 10.0,
  "last_motion_update": 1704067200.0,
  "tracking_status": "never_tracked",
  "last_tracked_at": null,
  "charge_amount": null,
  "vertices": null,
  "is_reached": false,
  "reached_by": [],
  "created_at": 1704067200.0,
  "last_updated": 1704067200.0
}
// Path length: 100 + 100 = 200m
// Speed: 200m / 20s = 10 m/s (auto-calculated)
```

**Request Body (Circle Target):**
```json
{
  "name": "Search Area Alpha",
  "type": "circle",
  "position": {"x": 200.0, "y": 150.0, "z": 0.0},
  "radius": 25.0,
  "description": "Circular search area"
}
```

**Response (201 Created):**
```json
{
  "id": "c3j4k5l6",
  "name": "Search Area Alpha",
  "type": "circle",
  "position": {"x": 200.0, "y": 150.0, "z": 0.0},
  "description": "Circular search area",
  "radius": 25.0,
  "velocity": null,
  "moving_path": null,
  "current_path_index": null,
  "charge_amount": null,
  "vertices": null,
  "created_at": 1704067200.0,
  "last_updated": 1704067200.0
}
```

**Request Body (Polygon Target):**
```json
{
  "name": "Zone Bravo",
  "type": "polygon",
  "position": {"x": 100.0, "y": 100.0, "z": 0.0},
  "radius": 1.0,
  "vertices": [
    {"x": 100.0, "y": 100.0, "z": 0.0},
    {"x": 150.0, "y": 100.0, "z": 0.0},
    {"x": 150.0, "y": 150.0, "z": 0.0},
    {"x": 100.0, "y": 150.0, "z": 0.0}
  ],
  "description": "Rectangular patrol zone"
}
```

**Response (201 Created):**
```json
{
  "id": "p7m8n9o0",
  "name": "Zone Bravo",
  "type": "polygon",
  "position": {"x": 100.0, "y": 100.0, "z": 0.0},
  "description": "Rectangular patrol zone",
  "radius": 1.0,
  "velocity": null,
  "moving_path": null,
  "current_path_index": null,
  "charge_amount": null,
  "vertices": [
    {"x": 100.0, "y": 100.0, "z": 0.0},
    {"x": 150.0, "y": 100.0, "z": 0.0},
    {"x": 150.0, "y": 150.0, "z": 0.0},
    {"x": 100.0, "y": 150.0, "z": 0.0}
  ],
  "created_at": 1704067200.0,
  "last_updated": 1704067200.0
}
```

#### Create Obstacle (POST /obstacles)

**Request Body (Circle Obstacle):**
```json
{
  "name": "Building A",
  "type": "circle",
  "position": {"x": 50.0, "y": 50.0, "z": 0.0},
  "radius": 15.0,
  "height": 30.0,
  "description": "Circular building structure"
}
```

**Response (201 Created):**
```json
{
  "id": "o1a2b3c4",
  "name": "Building A",
  "type": "circle",
  "position": {"x": 50.0, "y": 50.0, "z": 0.0},
  "description": "Circular building structure",
  "radius": 15.0,
  "width": null,
  "length": null,
  "vertices": [],
  "height": 30.0,
  "area": 706.8583470577034,
  "created_at": 1704067200.0,
  "last_updated": 1704067200.0
}
```

**Request Body (Ellipse Obstacle):**
```json
{
  "name": "Garden Pond",
  "type": "ellipse",
  "position": {"x": 100.0, "y": 80.0, "z": 0.0},
  "width": 25.0,
  "length": 18.0,
  "height": 0.0,
  "description": "Elliptical pond - no fly zone"
}
```

**Response (201 Created):**
```json
{
  "id": "o5d6e7f8",
  "name": "Garden Pond",
  "type": "ellipse",
  "position": {"x": 100.0, "y": 80.0, "z": 0.0},
  "description": "Elliptical pond - no fly zone",
  "radius": null,
  "width": 25.0,
  "length": 18.0,
  "vertices": [],
  "height": 0.0,
  "area": 1413.7166941154069,
  "created_at": 1704067200.0,
  "last_updated": 1704067200.0
}
```

**Request Body (Point Obstacle):**
```json
{
  "name": "Landing Marker",
  "type": "point",
  "position": {"x": 200.0, "y": 150.0, "z": 0.0},
  "radius": 2.0,
  "height": 0.5,
  "description": "Landing zone marker"
}
```

**Response (201 Created):**
```json
{
  "id": "o9g0h1i2",
  "name": "Landing Marker",
  "type": "point",
  "position": {"x": 200.0, "y": 150.0, "z": 0.0},
  "description": "Landing zone marker",
  "radius": 2.0,
  "width": null,
  "length": null,
  "vertices": [],
  "height": 0.5,
  "area": 12.566370614359172,
  "created_at": 1704067200.0,
  "last_updated": 1704067200.0
}
```

**Request Body (Polygon Obstacle):**
```json
{
  "name": "Office Complex",
  "type": "polygon",
  "position": {"x": 50.0, "y": 50.0, "z": 0.0},
  "vertices": [
    {"x": 40.0, "y": 40.0, "z": 0.0},
    {"x": 60.0, "y": 40.0, "z": 0.0},
    {"x": 60.0, "y": 60.0, "z": 0.0},
    {"x": 40.0, "y": 60.0, "z": 0.0}
  ],
  "height": 30.0,
  "description": "Rectangular office building"
}
```

**Response (201 Created):**
```json
{
  "id": "p3j4k5l6",
  "name": "Office Complex",
  "type": "polygon",
  "position": {"x": 40.0, "y": 40.0, "z": 0.0},
  "description": "Rectangular office building",
  "radius": null,
  "width": null,
  "length": null,
  "vertices": [
    {"x": 40.0, "y": 40.0, "z": 0.0},
    {"x": 60.0, "y": 40.0, "z": 0.0},
    {"x": 60.0, "y": 60.0, "z": 0.0},
    {"x": 40.0, "y": 60.0, "z": 0.0}
  ],
  "height": 30.0,
  "area": 400.0,
  "created_at": 1704067200.0,
  "last_updated": 1704067200.0
}
```

### Key Response Objects

#### DroneResponse (GET /drones/{id})
```json
{
  "id": "d4f3a9b2",
  "name": "Scout Alpha",
  "model": "Model-D4",
  "status": "hovering",
  "position": {"x": 50.0, "y": 30.0, "z": 15.0},
  "heading": 90.0,
  "speed": 0.0,
  "battery_level": 85.5,
  "battery_volume": 3420.0,
  "battery_capacity": 4000.0,
  "max_speed": 20.0,
  "max_altitude": 120.0,
  "perceived_radius": 100.0,
  "task_radius": 10.0,
  "home_position": {"x": 0.0, "y": 0.0, "z": 0.0},
  "created_at": 1704067200.0,
  "last_updated": 1704067350.5
}
```

#### BatteryUpdateRequest
```json
{
  "battery_level": "number (0-100)"
}
```

#### ChargeRequest
```json
{
  "charge_amount": "number (0.1-100)"
}
```

#### MoveAlongPathRequest
```json
{
  "waypoints": [
    {
      "x": "number",
      "y": "number",
      "z": "number (optional; defaults to current drone altitude)"
    }
  ],
  "allow_partial_move": "boolean (optional, default false; stop at the last reachable waypoint before an obstacle or insufficient battery)"
}
```

#### MoveTowardsRequest
```json
POST /drones/{id}/command
{
  "command": "move_towards",
  "parameters": {
    "distance": 50.0,
    // Choose ONE direction method:

    // Method 1: Compass heading (0=North, 90=East, 180=South, 270=West)
    "heading": 90.0,
    "dz": 5.0  // optional vertical component

    // Method 2: Direction vector
    // "dx": 1.0, "dy": 1.0, "dz": 0.5

    // Method 3: Spherical coordinates
    // "azimuth": 45.0, "elevation": 15.0
  }
}
```

#### CommandRequest
```json
{
  "command": "string (connect, disconnect, take_off, land, move_to, move_towards, move_along_path, change_altitude, hover, rotate, return_home, set_home, calibrate, take_photo, send_message, broadcast, charge)",
  "parameters": {}
}
```

#### CommandResponse
```json
{
  "command_id": "string",
  "drone_id": "string",
  "command": "string",
  "status": "string (success, partial_success, error)",
  "message": "string"
}
```

#### MoveAlongPathCommandResponse
```json
{
  "command_id": "string",
  "drone_id": "string",
  "command": "move_along_path",
  "status": "string (success, partial_success, error)",
  "message": "string",
  "successful_points_count": "integer (optional; move_along_path only)",
  "successful_points": "array of (x, y, z) triples (optional; move_along_path only)",
  "unsuccessful_points_count": "integer (optional; move_along_path only)",
  "unsuccessful_points": "array of (x, y, z) triples (optional; move_along_path only)"
}
```

Command status values are semantic command outcomes. `success` means the requested command completed fully, `partial_success` means a state-changing command made partial progress but did not complete the full request, and `error` means the command did not execute successfully.
Only `MoveAlongPathCommandResponse` advertises point feedback fields. Successful and partially successful path responses use these fields to list requested waypoints that were reached or not reached as normalized `(x, y, z)` triples. Error responses do not populate point feedback values.

### Target Models

#### TargetRequest
```json
{
  "name": "string",
  "type": "string (fixed, moving, waypoint, circle, polygon)",
  "position": {"x": "float", "y": "float", "z": "float"},
  "description": "string (optional)",
  "velocity": {"x": "float", "y": "float", "z": "float"} (optional, PRIORITY 1: if non-zero, uses velocity mode),
  "radius": "float (optional, default: 1.0)",
  "moving_path": [{"x": "float", "y": "float", "z": "float"}, ...] (optional, PRIORITY 2: used only if velocity is zero/null; consecutive duplicate waypoints are rejected and path segments are obstacle-validated),
  "moving_duration": "float (optional, default: 10.0, time in seconds. Velocity mode: time before reversing. Path mode: time to complete path (speed auto-calculated). If 0: stationary)",
  "charge_amount": "float (optional, for waypoint targets)",
  "vertices": [{"x": "float", "y": "float"}, ...] (required for polygon targets; absolute world coordinates)
}

// Movement Priority for moving targets:
// 1. VELOCITY (Priority 1): velocity non-zero + moving_duration > 0 → velocity-based ping-pong
// 2. PATH (Priority 2): velocity zero/null + moving_path exists + moving_duration > 0 → path-based with auto speed
// 3. STATIONARY: moving_duration == 0 → no movement
// Canonical moving-target response fields:
// - movement_mode: "velocity" | "path" | "stationary"
// - last_motion_update: float | null
// - tracking_status: "tracked" | "stale" | "never_tracked"
// - last_tracked_at: float | null
```

#### Update Target (PUT /targets/{id})

**Request Body (all fields optional):**
```json
{
  "name": "Checkpoint Alpha Updated",
  "position": {"x": 105.0, "y": 55.0, "z": 0.0},
  "description": "Updated primary checkpoint",
  "radius": 8.0
}
```

**Response (200 OK):**
```json
{
  "id": "t1a2b3c4",
  "name": "Checkpoint Alpha Updated",
  "type": "fixed",
  "position": {"x": 105.0, "y": 55.0, "z": 0.0},
  "description": "Updated primary checkpoint",
  "radius": 8.0,
  "velocity": null,
  "moving_path": null,
  "current_path_index": null,
  "charge_amount": null,
  "vertices": null,
  "created_at": 1704067200.0,
  "last_updated": 1704067500.0
}
```

**For Moving Target Update (Path-based):**
```json
{
  "velocity": {"x": 3.0, "y": 2.0, "z": 0.5},
  "moving_path": [
    {"x": 50.0, "y": 50.0, "z": 10.0},
    {"x": 100.0, "y": 80.0, "z": 15.0},
    {"x": 150.0, "y": 50.0, "z": 10.0},
    {"x": 100.0, "y": 20.0, "z": 10.0}
  ]
}
```

**For Moving Target Update (Velocity-based with ping-pong):**
```json
{
  "velocity": {"x": 4.0, "y": 0.0, "z": 0.0},
  "moving_duration": 15.0,
  "moving_path": []
}
```

**For Waypoint Update:**
```json
{
  "charge_amount": 35.0,
  "radius": 12.0
}
```

#### TargetResponse (GET /targets/{id})
```json
{
  "id": "t1a2b3c4",
  "name": "Checkpoint Alpha",
  "type": "fixed",
  "position": {"x": 100.0, "y": 50.0, "z": 0.0},
  "description": "Primary checkpoint for mission",
  "velocity": null,
  "moving_path": null,
  "current_path_index": null,
  "radius": 5.0,
  "charge_amount": null,
  "vertices": null,
  "created_at": 1704067200.0,
  "last_updated": 1704067200.0
}
```

#### WaypointCheckResponse
```json
{
  "waypoint_id": "string",
  "drone_in_range": "boolean",
  "charge_amount": "float",
  "drone_position": {"x": "float", "y": "float", "z": "float"}
}
```

#### NearestWaypointResponse
```json
{
  "id": "string",
  "name": "string",
  "type": "waypoint",
  "position": {"x": "float", "y": "float", "z": "float"},
  "description": "string",
  "velocity": "object or null",
  "moving_path": "array or null",
  "current_path_index": "integer or null",
  "radius": "float",
  "charge_amount": "float",
  "vertices": "array or null",
  "created_at": "float",
  "last_updated": "float"
}
```

### Environment Models

#### EnvironmentRequest
```json
{
  "name": "string",
  "weather": "string (clear, partly_cloudy, cloudy, rain, heavy_rain, snow, fog, windy, storm)",
  "temperature": "float",
  "humidity": "float",
  "pressure": "float (optional, default: 1013.25)",
  "wind_speed": "float (optional, default: 0.0)",
  "wind_direction": "string (north, northeast, east, southeast, south, southwest, west, northwest) (optional, default: north)",
  "visibility": "float (optional, default: 10000.0)"
}
```

#### EnvironmentResponse
```json
{
  "id": "string",
  "name": "string",
  "weather": "string",
  "temperature": "float",
  "humidity": "float",
  "pressure": "float",
  "wind_speed": "float",
  "wind_direction": "string",
  "visibility": "float",
  "created_at": "float (timestamp)",
  "last_updated": "float (timestamp)"
}
```

#### EnvironmentUpdateRequest
```json
{
  "name": "string (optional)",
  "weather": "string (optional)",
  "temperature": "float (optional)",
  "humidity": "float (optional)",
  "pressure": "float (optional)",
  "wind_speed": "float (optional)",
  "wind_direction": "string (optional)",
  "visibility": "float (optional)"
}
```

### Obstacle Models

#### ObstacleRequest
```json
{
  "name": "string",
  "type": "string (point, circle, ellipse, polygon)",
  "position": {"x": "float", "y": "float", "z": "float"},
  "description": "string (optional)",
  "radius": "float (required for point and circle; defaults to 1.0 for point)",
  "width": "float (required for ellipse - semi-major axis)",
  "length": "float (required for ellipse - semi-minor axis)",
  "vertices": [{"x": "float", "y": "float", "z": "float"}, ...] (required for polygon, 3+ vertices),
  "height": "float (optional, default: 10.0) - 0 means impassable at any altitude"
}
```

#### Update Obstacle (PUT /obstacles/{id})

**Request Body (all fields optional):**
```json
{
  "name": "Building A Updated",
  "position": {"x": 55.0, "y": 55.0, "z": 0.0},
  "radius": 18.0,
  "height": 35.0,
  "description": "Updated circular building"
}
```

**Response (200 OK):**
```json
{
  "id": "o1a2b3c4",
  "name": "Building A Updated",
  "type": "circle",
  "position": {"x": 55.0, "y": 55.0, "z": 0.0},
  "description": "Updated circular building",
  "radius": 18.0,
  "width": null,
  "length": null,
  "vertices": [],
  "height": 35.0,
  "area": 1017.8760197630929,
  "created_at": 1704067200.0,
  "last_updated": 1704067500.0
}
```

#### ObstacleResponse (GET /obstacles/{id})
```json
{
  "id": "o1a2b3c4",
  "name": "Building A",
  "type": "circle",
  "position": {"x": 50.0, "y": 50.0, "z": 0.0},
  "description": "Circular building structure",
  "radius": 15.0,
  "width": null,
  "length": null,
  "vertices": [],
  "height": 30.0,
  "area": 706.8583470577034,
  "created_at": 1704067200.0,
  "last_updated": 1704067200.0
}
```

### Collision Detection Models

#### PathCollisionCheckRequest
```json
{
  "start": {"x": "float", "y": "float", "z": "float"},
  "end": {"x": "float", "y": "float", "z": "float"},
  "safety_margin": "float (optional, default: 0.0)"
}
```

**Parameters:**
- `start`: Starting point of the path (x, y, z coordinates)
- `end`: Ending point of the path (x, y, z coordinates)
- `safety_margin`: Additional clearance distance (in meters) around the flight path
  - `0.0` = Check only the direct line path (default for drone commands)
  - `> 0.0` = Create a corridor with specified width on each side of the path
  - Example: `safety_margin=5.0` creates a 10m-wide corridor (5m on each side)

**Note:** Internal drone movement commands (`move_to`, `move_along_path`) use `safety_margin=0.0` by default. The collision check API endpoint allows custom safety margins for planning purposes.

#### CollisionResponse
```json
{
  "obstacle_id": "string",
  "obstacle_name": "string",
  "type": "string",
  "collision_type": "string",
  "distance": "float or null"
}
```

**Note:** This response returns information about the **first** obstacle collision found.

#### PointInObstaclesRequest
```json
{
  "x": "float",
  "y": "float",
  "z": "float (optional)",
  "margin": "float (optional, default: 0.0)"
}
```

**Parameters:**
- `x`: X coordinate of the point
- `y`: Y coordinate of the point
- `z`: Z coordinate (altitude) of the point (optional)
  - If not provided: Performs 2D check only (treats all obstacles as non-flyable)
  - If provided: Considers obstacle height in the check
- `margin`: Margin in meters around obstacles (default: 0.0)
  - Expands obstacle geometry by this amount
  - Also adds to obstacle height for altitude checks

**Height Logic:**
- **z not provided**: Check 2D area only (all obstacles are non-flyable)
- **z provided + obstacle height = 0**: Non-flyable at any altitude
- **z provided + obstacle height > 0**:
  - Point is inside if `z <= obstacle.height + margin`
  - Point is outside if `z > obstacle.height + margin`

#### PointInObstaclesResponse
```json
{
  "result": "boolean",
  "inside_obstacle_ids": ["string", ...],
  "inside_obstacles": [
    {
      "id": "string",
      "name": "string",
      "type": "string",
      "height": "float",
      "distance_to_boundary": "float"
    }
  ],
  "point": {"x": "float", "y": "float", "z": "float (optional)"},
  "margin": "float",
  "message": "string"
}
```

**Response Fields:**
- `result`: `true` if point is inside or on boundary of any obstacle
- `inside_obstacle_ids`: List of all obstacle IDs containing the point
- `inside_obstacles`: Detailed information about each obstacle
  - `distance_to_boundary`: Negative if inside, 0 if on boundary
- `point`: The point that was checked
- `margin`: Margin used for the check
- `message`: Human-readable result description

**Note:** Unlike `CollisionResponse`, this returns **all** obstacles containing the point.

### Session Models

#### SessionRequest
```json
{
  "name": "string",
  "description": "string (optional)",
  "with_examples": "boolean (optional, default: true)",
  "task_type": "string (optional, default: others) - 'area_search', 'area_assignment_and_patrol', 'target_assignment', 'target_tracking', or 'others'",
  "task_description": "string (optional) - Detailed description of the task/mission",
  "is_distance_3d": "boolean (optional, default: false) - Whether to use 3D distance for calculations",
  "canvas_width": "number (optional, default: 1024.0) - Width of simulation canvas in meters",
  "canvas_height": "number (optional, default: 768.0) - Height of simulation canvas in meters",
  "target_reach_statistics": "object (optional) - Summary statistics for target reach events",
  "area_coverage_summary": "object (optional) - Area coverage progress summary",
  "recent_commands": "array (optional) - Recent command executions"
}
```

#### Create Session (POST /sessions)

**Request Body:**
```json
{
  "name": "Mission Alpha",
  "description": "Search and rescue mission in sector 7",
  "with_examples": false,
  "task_type": "area_search",
  "task_description": "Search designated area for survivors"
}
```

**Response (201 Created):**
```json
{
  "id": "s1a2b3c4d5e6f",
  "name": "Mission Alpha",
  "description": "Search and rescue mission in sector 7",
  "status": "active",
  "creator": "system",
  "task_type": "area_search",
  "task_description": "Search designated area for survivors",
  "is_distance_3d": false,
  "canvas_width": 1024.0,
  "canvas_height": 768.0,
  "created_at": 1704067200.0,
  "last_updated": 1704067200.0,
  "statistics": {
    "drone_count": 0,
    "target_count": 0,
    "obstacle_count": 0,
    "environment_id": null,
    "total_commands_executed": 0,
    "total_flight_time": 0.0,
    "total_distance_traveled": 0.0,
    "total_target_reaches": 0,
    "drones_with_target_reaches": 0,
    "unique_targets_reached": 0,
    "session_time": 0.0,
    "command_history_size": 0,
    "target_reach_log_size": 0,
    "task_progress": {
      "task_type": "area_search",
      "progress_percentage": 0,
      "is_completed": false,
      "status_message": "Task to be Done",
      "details": {
        "total_targets": 0,
        "average_coverage": 0.0
      },
      "target_reach_summary": {
        "total_reaches": 0,
        "drones_with_reaches": 0,
        "unique_targets_reached": 0
      },
      "area_coverage_summary": {
        "total_targets_tracked": 0,
        "average_coverage": 0.0,
        "fully_covered_targets": 0
      }
    }
  },
  "target_reaches": {},
  "moving_target_tracking": {},
  "target_reach_statistics": {
    "total_reaches": 0,
    "unique_drones": 0,
    "unique_targets": 0,
    "reaches_by_drone": {},
    "reaches_by_target": {}
  },
  "area_coverage_summary": {
    "total_targets_tracked": 0,
    "average_coverage": 0.0,
    "fully_covered_targets": 0,
    "coverage_by_target": {}
  },
  "recent_commands": []
}
```

#### Update Session (PUT /sessions/{id})

**Request Body (all fields optional):**
```json
{
  "name": "Mission Alpha Updated",
  "description": "Updated search and rescue mission",
  "status": "inactive",
  "is_distance_3d": true,
  "canvas_width": 1200.0,
  "canvas_height": 800.0
}
```

**Response (200 OK):**
```json
{
  "id": "s1a2b3c4d5e6f",
  "name": "Mission Alpha Updated",
  "description": "Updated search and rescue mission",
  "status": "inactive",
  "creator": "system",
  "task_type": "area_search",
  "task_description": "Search designated area for survivors",
  "is_distance_3d": true,
  "canvas_width": 1200.0,
  "canvas_height": 800.0,
  "created_at": 1704067200.0,
  "last_updated": 1704067500.0,
  "statistics": {
    "drone_count": 2,
    "target_count": 3,
    "obstacle_count": 1,
    "environment_id": "env123",
    "total_commands_executed": 15,
    "total_flight_time": 450.5,
    "total_distance_traveled": 1250.75,
    "total_target_reaches": 5,
    "drones_with_target_reaches": 2,
    "unique_targets_reached": 3,
    "session_time": 600.0,
    "command_history_size": 15,
    "target_reach_log_size": 5,
    "task_progress": {
      "task_type": "area_search",
      "progress_percentage": 45,
      "is_completed": false,
      "status_message": "Task to be Done",
      "details": {
        "total_targets": 3,
        "average_coverage": 45.2
      },
      "target_reach_summary": {
        "total_reaches": 5,
        "drones_with_reaches": 2,
        "unique_targets_reached": 3
      },
      "area_coverage_summary": {
        "total_targets_tracked": 3,
        "average_coverage": 45.2,
        "fully_covered_targets": 0
      }
    }
  },
  "target_reaches": {
    "by_drone": {
      "drone1": {
        "target1": {
          "count": 2,
          "first_reached_at": 1704067300.0,
          "last_reached_at": 1704067400.0,
          "recent_reached_at": [1704067300.0, 1704067400.0]
        }
      }
    },
    "by_target": {
      "target1": {
        "total_reaches": 2,
        "unique_drones": 1,
        "reached_by": ["drone1"],
        "first_reached_at": 1704067300.0,
        "last_reached_at": 1704067400.0,
        "recent_reached_at": [1704067300.0, 1704067400.0]
      }
    }
  },
  "moving_target_tracking": {
    "target1": {
      "tracking_status": "tracked",
      "first_tracked_at": 1704067300.0,
      "last_tracked_at": 1704067400.0,
      "last_tracked_by": "drone1",
      "tracked_by": ["drone1"],
      "total_track_events": 2,
      "active_period_start": 1704067300.0,
      "recent_periods": [
        {
          "start_at": 1704067300.0,
          "end_at": 1704067410.0,
          "last_update_at": 1704067400.0,
          "event_count": 2,
          "last_tracked_by": "drone1",
          "tracked_by": ["drone1"]
        }
      ],
      "by_drone": {
        "drone1": {
          "first_tracked_at": 1704067300.0,
          "last_tracked_at": 1704067400.0,
          "total_track_events": 2,
          "recent_periods": [
            {
              "start_at": 1704067300.0,
              "end_at": 1704067410.0,
              "last_update_at": 1704067400.0,
              "event_count": 2
            }
          ]
        }
      }
    }
  },
  "area_coverage_summary": {
    "total_targets_tracked": 3,
    "average_coverage": 45.2,
    "fully_covered_targets": 0,
    "coverage_by_target": {
      "target1": {
        "area_type": "circle",
        "total_area": 1963.4954084936207,
        "covered_area": 887.5,
        "coverage_percentage": 45.2,
        "num_covered_points": 150,
        "covered_points": [[100.0, 100.0], [101.0, 100.0]]
      }
    }
  },
  "recent_commands": [
    {
      "command_id": "cmd123",
      "drone_id": "drone1",
      "command": "move_to",
      "parameters": {"x": 100.0, "y": 50.0, "z": 15.0},
      "status": "success",
      "message": "Moved to position",
      "timestamp": 1704067400.0
    }
  ]
}
```

#### SessionResponse (GET /sessions/{id})
```json
{
  "id": "s1a2b3c4d5e6f",
  "name": "Mission Alpha",
  "description": "Search and rescue mission in sector 7",
  "status": "active",
  "creator": "system",
  "task_type": "area_search",
  "task_description": "Search designated area for survivors",
  "is_distance_3d": false,
  "canvas_width": 1024.0,
  "canvas_height": 768.0,
  "created_at": 1704067200.0,
  "last_updated": 1704067500.0,
  "statistics": {
    "drone_count": 2,
    "target_count": 3,
    "obstacle_count": 1,
    "environment_id": "env123",
    "total_commands_executed": 15,
    "total_flight_time": 450.5,
    "total_distance_traveled": 1250.75,
    "total_target_reaches": 5,
    "drones_with_target_reaches": 2,
    "unique_targets_reached": 3,
    "session_time": 600.0,
    "command_history_size": 15,
    "target_reach_log_size": 5,
    "task_progress": {
      "task_type": "area_search",
      "progress_percentage": 45,
      "is_completed": false,
      "status_message": "Task to be Done",
      "details": {
        "total_targets": 3,
        "average_coverage": 45.2
      },
      "target_reach_summary": {
        "total_reaches": 5,
        "drones_with_reaches": 2,
        "unique_targets_reached": 3
      },
      "area_coverage_summary": {
        "total_targets_tracked": 3,
        "average_coverage": 45.2,
        "fully_covered_targets": 0
      }
    }
  },
  "target_reach_statistics": {
    "total_reaches": 5,
    "unique_drones": 2,
    "unique_targets": 3,
    "reaches_by_drone": {},
    "reaches_by_target": {}
  },
  "area_coverage_summary": {
    "total_targets_tracked": 3,
    "average_coverage": 45.2,
    "fully_covered_targets": 0,
    "coverage_by_target": {}
  },
  "recent_commands": [
    {
      "command": "move_to",
      "timestamp": 1704067400.0,
      "parameters": {
        "x": 10,
        "y": 5,
        "z": 0
      },
      "result": "success"
    }
  ]
}
```

#### SessionDataResponse

Complete session data with flat structure. Extends SessionResponse with entity arrays at the same level.

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "status": "string",
  "creator": "string",
  "task_type": "string",
  "task_description": "string",
  "is_distance_3d": "boolean",
  "canvas_width": "number",
  "canvas_height": "number",
  "created_at": "float",
  "last_updated": "float",
  "statistics": {
    "drone_count": "integer",
    "target_count": "integer",
    "obstacle_count": "integer",
    "environment_id": "string or null",
    "total_commands_executed": "integer",
    "total_flight_time": "float",
    "total_distance_traveled": "float",
    "total_target_reaches": "integer",
    "drones_with_target_reaches": "integer",
    "unique_targets_reached": "integer",
    "session_time": "float",
    "command_history_size": "integer",
    "target_reach_log_size": "integer",
    "task_progress": {
      "task_type": "string",
      "progress_percentage": "integer (0-100)",
      "is_completed": "boolean",
      "status_message": "string",
      "details": "object",
      "target_reach_summary": "object",
      "area_coverage_summary": "object"
    }
  },
  "target_reaches": "object",
  "target_reach_statistics": "object",
  "area_coverage_summary": "object",
  "recent_commands": "array",
  "drones": "Array of DroneResponse",
  "targets": "Array of TargetResponse",
  "obstacles": "Array of ObstacleResponse",
  "environment": "EnvironmentResponse or null",
  "history": {
    "command_history": "array",
    "status_history": "object",
    "target_reaches": "object",
    "moving_target_tracking": "object",
    "area_coverage": "object",
    "path_history": "object"
  }
}
```

### Session Screenshot Endpoints

#### GET /sessions/current/screenshot
- Query Parameters:
  - `format`: `string` (optional) — one of `png`, `jpg`, `jpeg`, `pdf`, `svg`, `eps` (default: `png`)
  - `width`: `integer` (optional) — image width in pixels (default: `1024`)
  - `height`: `integer` (optional) — image height in pixels (default: `768`)
  - `show_status`: `boolean` (optional) — include UI-equivalent path traces, area coverage, reached/tracked target state, and status bar details (default: `false`)
- Response: Binary content with media type `image/png`, `image/jpeg`, `application/pdf`, `image/svg+xml`, or `application/postscript` based on `format`.

#### GET /sessions/{session_id}/screenshot
- Path Parameters:
  - `session_id`: `string` — target session ID
- Query Parameters:
  - `format`: `string` (optional) — one of `png`, `jpg`, `jpeg`, `pdf`, `svg`, `eps` (default: `png`)
  - `width`: `integer` (optional) — image width in pixels (default: `1024`)
  - `height`: `integer` (optional) — image height in pixels (default: `768`)
  - `show_status`: `boolean` (optional) — include UI-equivalent path traces, area coverage, reached/tracked target state, and status bar details (default: `false`)
- Response: Binary content with media type `image/png`, `image/jpeg`, `application/pdf`, `image/svg+xml`, or `application/postscript` based on `format`.

#### POST /sessions/current/reset

Resets the current active session to its initial state by clearing all history tracking data while preserving entities.

**Authentication:** USER role or higher

**What Gets Cleared:**
- Command history (all commands sent to drones)
- Status history (drone status change records)
- Path history (drone movement traces/trajectories)
- Target reach logs
- Area coverage data
- Statistics (total commands executed, flight time, distance traveled)
- Session timer (resets to 0)

**What Gets Preserved:**
- Session ID, name, and description
- All drones with their current positions and states
- All targets
- All obstacles
- Environment configuration
- Task definitions

**Request:** No request body required

**Response (200 OK):**
```json
{
  "id": "session-123abc",
  "name": "Current Session",
  "description": "Active session",
  "status": "active",
  "creator": "system",
  "task_type": "area_search",
  "task_description": "Search designated areas",
  "created_at": 1734000000.0,
  "last_updated": 1734001234.5,
  "statistics": {
    "drone_count": 10,
    "target_count": 5,
    "obstacle_count": 2,
    "total_commands_executed": 0,
    "total_flight_time": 0.0,
    "total_distance_traveled": 0.0,
    "session_time": 0.0,
    "command_history_size": 0,
    "target_reach_log_size": 0
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/sessions/current/reset
```

### Battery Management Models

#### BatteryUpdateRequest
```json
{
  "battery_level": "float (0.0-100.0)"
}
```

#### PathRequest
```json
{
  "path": [
    {"x": "float", "y": "float", "z": "float"},
    {"x": "float", "y": "float", "z": "float"}
  ]
}
```

## Example Usage

### Register a Drone

```bash
curl -X POST http://localhost:8000/drones \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Scout-1",
    "model": "Model-D4",
    "max_speed": 20.0,
    "max_altitude": 120.0,
    "battery_capacity": 100.0
  }'
```

### Send a Command to a Drone

```bash
curl -X POST http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/command \
  -H "Content-Type: application/json" \
  -d '{
    "command": "take_off",
    "parameters": {"altitude": 10.0}
  }'
```

### Move Drone Towards Direction

```bash
# Move 50 meters in current heading direction (no heading parameter = use current)
curl -X POST "http://localhost:8000/drones/drone-123/command/move_towards?distance=50.0"

# Move 50 meters towards East (90 degrees)
curl -X POST "http://localhost:8000/drones/drone-123/command/move_towards?distance=50.0&heading=90.0"

# Move 30 meters Northeast with 5m altitude gain
curl -X POST "http://localhost:8000/drones/drone-123/command/move_towards?distance=30.0&heading=45.0&dz=5.0"

# Move using direction vector
curl -X POST "http://localhost:8000/drones/drone-123/command/move_towards?distance=25.0&dx=1.0&dy=1.0&dz=0.5"

# Move using azimuth and elevation angles
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

### Change Drone Heading (Rotate)

```bash
# Rotate to face North
curl -X POST "http://localhost:8000/drones/drone-123/command/rotate?heading=0.0"

# Rotate to face East
curl -X POST "http://localhost:8000/drones/drone-123/command/rotate?heading=90.0"

# Rotate to face South
curl -X POST "http://localhost:8000/drones/drone-123/command/rotate?heading=180.0"

# Using generic command endpoint
curl -X POST http://localhost:8000/drones/drone-123/command \
  -H "Content-Type: application/json" \
  -d '{
    "command": "rotate",
    "parameters": {
      "heading": 270.0
    }
  }'
```

### Move Drone Along Path

When `allow_partial_move=true`, `status: "partial_success"` means the drone reached at least one waypoint but stopped before the final requested waypoint because an obstacle or insufficient battery blocked the remaining path. `status: "success"` means all requested waypoints were reached, and `status: "error"` means no allowed movement was executed for the failed path command. Successful and partially successful responses include `successful_points_count`, `successful_points`, `unsuccessful_points_count`, and `unsuccessful_points`; point lists contain normalized `(x, y, z)` triples.

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

### Update Drone Battery

```bash
curl -X POST http://localhost:8000/drones/550e8400-e29b-41d4-a716-446655440000/battery \
  -H "Content-Type: application/json" \
  -d '{"battery_level": 75.0}'
```

### Create an Obstacle

```bash
curl -X POST http://localhost:8000/obstacles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tall Building",
    "type": "building",
    "position": {"x": 100.0, "y": 200.0, "z": 0.0},
    "description": "Office building",
    "vertices": [
      {"x": 90.0, "y": 190.0},
      {"x": 110.0, "y": 190.0},
      {"x": 110.0, "y": 210.0},
      {"x": 90.0, "y": 210.0}
    ],
    "height": 50.0
  }'
```

### Check Path Collision

```bash
# Requires SYSTEM role
curl -X POST http://localhost:8000/obstacles/path_collision \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "start": {"x": 0.0, "y": 0.0, "z": 10.0},
    "end": {"x": 200.0, "y": 300.0, "z": 10.0},
    "safety_margin": 2.0
  }'
```

### Check Point Collision

```bash
# 2D check (no altitude) - requires SYSTEM role
curl -X POST http://localhost:8000/obstacles/point_collision \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "x": 100.0,
    "y": 200.0,
    "margin": 0.0
  }'

# 3D check with altitude and margin - requires SYSTEM role
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

### Create a Session

```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Custom Session",
    "description": "A custom session for testing",
    "with_examples": true
  }'
```

### Session Creation and Management

```bash
# Create new session with auto-generated ID
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{"name": "Mission Alpha", "description": "Search mission", "creator": "planner-ops"}'

# Create session with entities
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{
    "name": "Mission with Fleet",
    "creator": "planner-ops",
    "drones": [{"name": "Scout-1", "model": "Model-D", "position": {"x": 0, "y": 0, "z": 0}}],
    "targets": [{"name": "Target-1", "type": "fixed", "position": {"x": 100, "y": 100, "z": 0}}]
  }'

# Restore session with specific ID from backup (automatically overwrites if exists)
curl -X POST "http://localhost:8000/sessions/mission-backup-2024?data=true" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d @backup.json

# Update session metadata
curl -X PUT http://localhost:8000/sessions/session-abc123 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{"name": "Updated Name", "status": "completed"}'

# Update session and get complete data
curl -X PUT "http://localhost:8000/sessions/session-abc123?data=true" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d '{"status": "completed"}'
```

### Get Session with Data Parameter

```bash
# Get current session metadata only (default)
curl -X GET http://localhost:8000/sessions/current

# Get current session with complete data (all drones, targets, obstacles, environment)
curl -X GET "http://localhost:8000/sessions/current?data=true"

# Get current session with complete data (convenience endpoint)
curl -X GET http://localhost:8000/sessions/current/data

# Get specific session metadata only
curl -X GET http://localhost:8000/sessions/session-abc123

# Get specific session with complete data
curl -X GET "http://localhost:8000/sessions/session-abc123?data=true"

# Get specific session with complete data (convenience endpoint)
curl -X GET http://localhost:8000/sessions/session-abc123/data
```

### Complete Save/Restore Workflow

```bash
# 1. Export current session to file (data is already in flat format)
curl -X GET "http://localhost:8000/sessions/current?data=true" > session_backup.json

# The backup file has flat structure with all fields at root level:
# {
#   "id": "session-123",
#   "name": "Mission Alpha",
#   "status": "active",
#   "statistics": {...},
#   "drones": [...],
#   "targets": [...],
#   "obstacles": [...],
#   "environment": {...},
#   "history": {...}
# }

# 2. Later, restore with specific ID and verify in one call
curl -X POST "http://localhost:8000/sessions/mission-restored-$(date +%s)?data=true" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d @session_backup.json

# Response includes all restored drones, targets, obstacles, and environment in flat format!

# 3. Force overwrite if session already exists (useful for re-restoring backups)
curl -X POST "http://localhost:8000/sessions/mission-backup-001?overwrite=true&data=true" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SYSTEM_API_KEY>" \
  -d @session_backup.json

# Deletes existing session and replaces it with backup data
```

---

## Important Notes

### Drone Status Values
- `idle` - On ground, not active
- `ready` - On ground, ready for takeoff
- `taking_off` - Taking off
- `flying` - In air, stable
- `moving` - In air, moving to destination
- `hovering` - In air, stationary
- `landing` - Landing
- `emergency` - Emergency state (low battery)
- `offline` - Not connected

### Target Types
- `fixed` - Static target (can also be used for points of interest)
- `moving` - Moving target with velocity/path
- `waypoint` - Charging station
- `circle` - Geometric circle target (uses `radius` at `position`)
- `polygon` - Geometric polygon target (uses `vertices` absolute coordinates)

#### UI Notes
- `point`: Small circular obstacle with gold color
- `circle`: Filled circle with brown color and white outline
- `ellipse`: Filled ellipse with medium orchid color and white outline
- `polygon`: Filled polygon with dim gray color; selected with expanded boundary outline

### Obstacle Types
- `point` - Point obstacle (requires `position`; `radius` defaults to 1.0m)
- `circle` - Circular obstacle (requires `position` and `radius`)
- `ellipse` - Elliptical obstacle (requires `position`, `width`, and `length`)
- `polygon` - Polygonal obstacle (requires `vertices` with 3+ points)

### Height-Based Passability
- `height = 0`: Impassable area at any altitude (drones cannot fly through)
- `height > 0`: Drones can fly over if their altitude exceeds the obstacle height

### Weather Conditions
`clear`, `partly_cloudy`, `cloudy`, `rain`, `heavy_rain`, `snow`, `fog`, `windy`, `storm`

### Wind Directions
`north`, `northeast`, `east`, `southeast`, `south`, `southwest`, `west`, `northwest`

---

## Additional Resources

- **Full Documentation**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Main README**: [README.md](README.md)
- **Interactive API Docs**: http://localhost:8000/docs (when server running)
- **Client Examples**: `/client` directory
- **Tests**: `test_*.py` files

---

## Check Endpoints (ADMIN Only)

**Authentication Required:** All `/check/` endpoints require ADMIN role authentication via `X-API-Key` header. Responses always include `result` (boolean) and `value` (primary measurement).

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/check/drone_position` | Distance to expected position (3D if `z` provided) |
| GET | `/check/drone_altitude` | Altitude proximity vs expected |
| GET | `/check/drone_status` | Status equality |
| GET | `/check/drone_on_ground` | Grounded check (altitude + ground status) |
| GET | `/check/all_drones_on_ground` | Count/all drones grounded |
| GET | `/check/drone_hovering` | Hovering check (altitude + hovering status) |
| GET | `/check/all_drones_hovering` | Count/all drones hovering |
| GET | `/check/drone_over_height` | Altitude above minimum height |
| GET | `/check/target_within_drone_distance` | Target within distance of a drone |
| GET | `/check/obstacle_within_drone_distance` | Obstacle within distance of a drone |
| GET | `/check/two_drones_distance` | Two drones within distance |
| GET | `/check/drone_group_distance` | Drone group pairwise distance check |
| GET | `/check/drone_battery_level` | Battery level vs minimum |
| GET | `/check/drone_heading` | Heading within tolerance |
| GET | `/check/drone_in_target` | Drone inside target radius |
| GET | `/check/drone_at_home` | Drone near home position |
| GET | `/check/target_within_drone_task_radius` | Target within drone task radius |
| GET | `/check/target_within_drone_perceived_radius` | Target within drone perceived radius |
| GET | `/check/obstacle_within_drone_perceived_radius` | Obstacle within drone perceived radius |
| GET | `/check/drone_has_taken_off` | Check if drone has taken off (history) |
| GET | `/check/drone_has_landed` | Check if drone has landed (history) |
| GET | `/check/drone_has_visited_position` | Check if drone visited a position (history) |
| GET | `/check/drone_has_moved_distance` | Check if drone moved minimum distance (history) |
| GET | `/check/drone_has_moved_directed_distance` | Check if drone moved distance in direction (history) |
| GET | `/check/drone_has_hovered` | Check if drone has hovered (history) |
| GET | `/check/drone_has_taken_photo` | Check if drone has taken photos (history) |
| GET | `/check/target_in_photo_taken_by_drone` | Check if target in drone's photo |
| GET | `/check/drone_has_charged` | Check if drone has charged (history) |
| GET | `/check/drone_has_sent_message` | Check if drone sent messages (history) |
| GET | `/check/all_drones_have_taken_off` | Check if all drones have taken off |
| GET | `/check/all_drones_have_landed` | Check if all drones have landed |
| GET | `/check/target_is_reached` | Any drone reached target |
| GET | `/check/target_is_reached_by_drone` | Specific drone reached target |
| GET | `/check/target_reached_drone_number` | Reached drone count vs expectation |
| GET | `/check/moving_target_tracked` | Moving target tracked for at least a duration |
| GET | `/check/target_is_fully_searched` | Coverage meets threshold (default 0.99) |
| GET | `/check/target_searched_area_percentage` | Coverage vs expected ratio (0-1) |
| GET | `/check/task_progress` | Task progress vs expected ratio (0-1) |
| GET | `/check/task_done` | Task completion using session progress |

### Check Drone Position

**GET** `/check/drone_position` — distance to expected position (3D if `z` provided)  
Query: `drone_id`, `x`, `y`, `z?`, `tolerance?`  
Response: `result` (within tolerance), `value` (distance), plus IDs/positions/tolerance.

**GET** `/check/drone_altitude` — altitude proximity  
Query: `drone_id`, `expected_altitude`, `tolerance?`  
Response: `result` (within tolerance), `value` (altitude), `difference`, `tolerance`.

**GET** `/check/drone_status` — status equality  
Query: `drone_id`, `expected_status`  
Response: `result` (equals), `value` (current status).

**GET** `/check/drone_on_ground` — altitude near ground + ground-like status  
Query: `drone_id`, `tolerance?`  
Response: `result`, `value` (altitude), `status`.

**GET** `/check/all_drones_on_ground` — fleet grounded count  
Query: `tolerance?`  
Response: `result` (all grounded), `value` (# grounded), lists of grounded/not grounded IDs.

**GET** `/check/drone_hovering` — hovering state  
Query: `drone_id`, `tolerance?`  
Response: `result`, `value` (status), `altitude`.

**GET** `/check/all_drones_hovering` — fleet hovering count  
Query: `tolerance?`  
Response: `result` (all hovering), `value` (# hovering), lists of hovering/not hovering IDs.

**GET** `/check/drone_over_height` — altitude above minimum height
Query: `drone_id`, `min_height`, `tolerance?`
Response: `result`, `value` (altitude), `min_height`, `tolerance`.

**GET** `/check/target_within_drone_distance` — is target within distance of drone
Query: `drone_id`, `target_id`, `max_distance`
Response: `result`, `value` (distance), `max_distance`.

**GET** `/check/obstacle_within_drone_distance` — is obstacle within distance of drone
Query: `drone_id`, `obstacle_id`, `max_distance`
Response: `result`, `value` (distance), `max_distance`.

**GET** `/check/two_drones_distance` — are two drones within distance range
Query: `drone_1_id`, `drone_2_id`, `max_distance?` (optional), `min_distance?` (default 0)  
Response: `result` (bool), `value` (distance), `drone_1_id`, `drone_2_id`.

**GET** `/check/drone_group_distance` — do drone-group pairs satisfy distance range rules
Query: repeated `drone_ids` (at least 2), `max_distance?` (optional), `min_distance?` (default 0), `mode?` (`all_pairs` default, or `any_pair`)  
Response: `result` (bool), `value` (# passing pairs), `mode`, `total_pairs`, `passing_pairs`, `failing_pairs`, `pair_distances`.

**GET** `/check/drone_battery_level` — battery level vs minimum
Query: `drone_id`, `min_level?`
Response: `result`, `value` (battery level %), `min_level`.

**GET** `/check/drone_heading` — heading within tolerance
Query: `drone_id`, `expected_heading`, `tolerance?`
Response: `result`, `value` (current heading), `heading_delta`, `tolerance`.

**GET** `/check/drone_in_target` — drone inside target radius (center-based)
Query: `drone_id`, `target_id`
Response: `result`, `value` (distance), `target_radius`.

**GET** `/check/drone_at_home` — drone near its home position
Query: `drone_id`, `tolerance?`
Response: `result`, `value` (distance), `tolerance`, `home_position`.

**GET** `/check/target_within_drone_task_radius` — target inside drone task radius
Query: `drone_id`, `target_id`
Response: `result`, `value` (distance), `task_radius`.

**GET** `/check/target_within_drone_perceived_radius` — target inside perceived radius
Query: `drone_id`, `target_id`  
Response: `result`, `value` (distance), `perceived_radius`.

**GET** `/check/obstacle_within_drone_perceived_radius` — obstacle inside perceived radius
Query: `drone_id`, `obstacle_id`
Response: `result`, `value` (distance), `perceived_radius`.

### History Check Endpoints

**GET** `/check/drone_has_taken_off` — check if drone has taken off in history
Query: `drone_id`, `min_altitude?` (default 5.0), `max_altitude?`, `tolerance?` (default 0.0), `since_timestamp?`
Response: `result` (has matching takeoff), `value` (number of matching takeoff events), `takeoff_count`, `last_takeoff_time`, `max_altitude_reached`, `min_altitude_threshold`, `max_altitude_threshold`, `tolerance`.

Modes:
- Threshold mode: omit `max_altitude`; matches takeoffs with altitude `>= min_altitude - tolerance`
- Range mode: provide both `min_altitude` and `max_altitude`; matches takeoffs within `[min_altitude - tolerance, max_altitude + tolerance]`
- Exact-height mode: set `min_altitude == max_altitude`; `tolerance` then defines the acceptable band around that height

Examples:
```bash
# Backward-compatible minimum threshold check
curl -X GET "http://localhost:8000/check/drone_has_taken_off?drone_id=drone-1&min_altitude=5.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check whether a takeoff was within an altitude range
curl -X GET "http://localhost:8000/check/drone_has_taken_off?drone_id=drone-1&min_altitude=9.0&max_altitude=11.0&tolerance=0.2" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check whether a takeoff reached about 10 meters (10.0 +/- 0.5)
curl -X GET "http://localhost:8000/check/drone_has_taken_off?drone_id=drone-1&min_altitude=10.0&max_altitude=10.0&tolerance=0.5" \
  -H "X-API-Key: <ADMIN_API_KEY>"
```

**GET** `/check/drone_has_landed` — check if drone has landed in history
Query: `drone_id`, `min_count?` (default 1), `since_timestamp?`
Response: `result` (has at least `min_count` landings), `value` (number of landing events), `last_landing_time`, `last_landing_position`.

**GET** `/check/drone_has_visited_position` — check if drone visited a specific position
Query: `drone_id`, `x`, `y`, `z?`, `tolerance?` (default 2.0), `since_timestamp?`
Response: `result` (has visited), `value` (number of visits), `visits` (list of waypoint events at that position).

**GET** `/check/drone_has_moved_distance` — check if drone has moved minimum distance
Query: `drone_id`, `min_distance`, `since_timestamp?`
Response: `result` (moved enough), `value` (total distance moved in meters), `waypoint_count` (number of waypoints).

**GET** `/check/drone_has_moved_directed_distance` — check if drone has moved minimum distance in a specific direction
Query: `drone_id`, `min_distance`, `heading`, `tolerance?` (default 5.0), `since_timestamp?`
Response: `result` (moved enough), `value` (total directed distance), `heading`, `tolerance`.

**GET** `/check/drone_has_hovered` — check if drone has hovered in history
Query: `drone_id`, `min_duration?` (default 0), `since_timestamp?`
Response: `result` (has hovered), `value` (number of hover events), `hover_events` (list of events with durations).

**GET** `/check/drone_has_taken_photo` — check if drone has taken photos
Query: `drone_id`, `min_count?` (default 1), `since_timestamp?`
Response: `result` (has taken photos), `value` (number of photos taken), `photo_events` (list of photo events).

**GET** `/check/target_in_photo_taken_by_drone` — check if target in drone's photo
Query: `drone_id`, `target_id`
Response: `result` (target in photo), `value` (boolean), `matching_photos` (list).

**GET** `/check/drone_has_charged` — check if drone has charged in history
Query: `drone_id`, `min_charge_amount?` (default 0), `since_timestamp?`
Response: `result` (has charged), `value` (number of charging events), `charge_events` (list of events).
Note: If a charge event tops the battery off to 100%, it satisfies `min_charge_amount` even if the actual charge is smaller.

**GET** `/check/drone_has_sent_message` — check if drone has sent messages (includes broadcasts)
Query: `drone_id`, `to_drone_id?`, `min_count?` (default 1), `since_timestamp?`
Response: `result` (bool), `value` (int), `drone_id`, `to_drone_id`, `min_count`, `recipient_drones` (list), `last_message_time`.

**GET** `/check/drone_has_sent_message_content` — check if drone sent message text containing content
Query: `drone_id`, `content`, `to_drone_id?`, `min_count?` (default 1), `since_timestamp?`
Response: `result` (bool), `value` (int), `drone_id`, `content`, `to_drone_id`, `min_count`, `recipient_drones` (list), `last_message_time`, `matched_messages`, `match_mode`.

### Aggregate History Check Endpoints

**GET** `/check/all_drones_have_taken_off` — check if all drones have taken off
Query: `min_altitude?` (default 5.0), `since_timestamp?`, `check_history?` (default true)
Response: `result` (all taken off), `value` (number of drones taken off), `percentage`, `drones_taken_off` (list), `drones_not_taken_off` (list), `total_drones`.

**GET** `/check/all_drones_have_landed` — check if all drones have landed
Query: `min_count?` (default 1), `since_timestamp?`, `check_history?` (default true)
Response: `result` (all landed), `value` (number of drones landed), `percentage`, `drones_landed` (list), `drones_not_landed` (list), `total_drones`.

### Target and Task Check Endpoints

**GET** `/check/target_is_reached` — any drone reached target  
Query: `target_id`, `since_timestamp?`  
Response: `result`, `value` (# drones), `reached_by` list.

**GET** `/check/target_is_reached_by_drone` — specific drone reached target  
Query: `target_id`, `drone_id`, `since_timestamp?`  
Response: `result`, `value` (visits count), `target_id`, `drone_id`.

**GET** `/check/target_reached_drone_number` — reached drone count vs expectation  
Query: `target_id`, `expected_count?`, `since_timestamp?`  
Response: `result`, `value` (count), `reached_by`.

**GET** `/check/moving_target_tracked` — moving target tracked for at least a duration  
Query: `target_id`, `drone_id?`, `min_duration?`, `since_timestamp?`  
Response: `result`, `value` (max tracked duration in seconds), `tracking_status`, `matching_periods`.

**GET** `/check/target_is_fully_searched` — coverage meets threshold (default 0.99)  
Query: `target_id`, `coverage_threshold?`  
Response: `result`, `value` (coverage ratio 0-1), `coverage_percentage`.

**GET** `/check/target_searched_area_percentage` — coverage vs expected ratio (0-1)  
Query: `target_id`, `expected_percentage` (0-1)  
Response: `result`, `value` (coverage ratio), `coverage_percentage`.

**GET** `/check/task_progress` — task progress vs expected ratio (0-1)  
Query: `expected_progress?` (0-1)  
Response: `result`, `value` (progress ratio), `progress_percentage`, `is_completed`.

**GET** `/check/task_done` — completion based on session progress
Query: *(None)*
Response: `result`, `value` (progress ratio), `progress_percentage`, `status_message`, `details`.

### Check Endpoints Examples

```bash
# Check drone position within tolerance
curl -X GET "http://localhost:8000/check/drone_position?drone_id=drone-1&x=50.0&y=30.0&z=10.0&tolerance=2.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check drone battery level
curl -X GET "http://localhost:8000/check/drone_battery_level?drone_id=drone-1&min_level=20.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if drone is at home position
curl -X GET "http://localhost:8000/check/drone_at_home?drone_id=drone-1&tolerance=5.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if target is within drone distance
curl -X GET "http://localhost:8000/check/target_within_drone_distance?drone_id=drone-1&target_id=target-1&max_distance=50.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if two drones are within distance
curl -X GET "http://localhost:8000/check/two_drones_distance?drone_1_id=drone-1&drone_2_id=drone-2&max_distance=100.0" \
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

# Check if drone has taken off (history)
curl -X GET "http://localhost:8000/check/drone_has_taken_off?drone_id=drone-1&min_altitude=5.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if drone has visited a position (history)
curl -X GET "http://localhost:8000/check/drone_has_visited_position?drone_id=drone-1&x=50.0&y=30.0&z=10.0&tolerance=2.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if drone has moved minimum distance (history)
curl -X GET "http://localhost:8000/check/drone_has_moved_distance?drone_id=drone-1&min_distance=100.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if drone has taken photos (history)
curl -X GET "http://localhost:8000/check/drone_has_taken_photo?drone_id=drone-1&min_count=3" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if drone has hovered (history)
curl -X GET "http://localhost:8000/check/drone_has_hovered?drone_id=drone-1&min_duration=5.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if all drones have taken off (check history)
curl -X GET "http://localhost:8000/check/all_drones_have_taken_off?check_history=true&min_altitude=5.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if all drones have taken off (check current status only)
curl -X GET "http://localhost:8000/check/all_drones_have_taken_off?check_history=false&min_altitude=5.0" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if all drones are currently hovering
curl -X GET "http://localhost:8000/check/all_drones_hovering" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if all drones have landed at least once (check history)
curl -X GET "http://localhost:8000/check/all_drones_have_landed?check_history=true&min_count=1" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if all drones are on ground
curl -X GET "http://localhost:8000/check/all_drones_on_ground" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if target has been reached
curl -X GET "http://localhost:8000/check/target_is_reached?target_id=target-1" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if specific drone reached target
curl -X GET "http://localhost:8000/check/target_is_reached_by_drone?target_id=target-1&drone_id=drone-1" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check task progress
curl -X GET "http://localhost:8000/check/task_progress?expected_progress=0.8" \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Check if task is done
curl -X GET "http://localhost:8000/check/task_done" \
  -H "X-API-Key: <ADMIN_API_KEY>"
```

---

**Last Updated:** 2025
**API Version:** 1.0.0
