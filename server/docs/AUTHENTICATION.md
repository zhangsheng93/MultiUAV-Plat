# API Authentication & Role Guide

The MultiUAV-Plat Server System API uses **API Key-based authentication** with a hierarchical role-based access control (RBAC) system.

---

## 1. Authentication Overview

### 🔓 Default Behavior
**When no API key is provided, the system defaults to the AGENT role.**

### API Key Usage
To access specific roles, provide a valid API key in the `X-API-Key` header:

```bash
# Example for SYSTEM access
curl -H "X-API-Key: <SYSTEM_API_KEY>" http://localhost:8000/drones
```

### 🔑 API Keys
The software accepts one AGENT key and multiple hard-coded privilege keys for USER, SYSTEM, and ADMIN. The actual key values are stored in the application code and are intentionally omitted from this document.

| Role | Accepted Keys |
|:---|:---|
| **AGENT** | `<AGENT_API_KEY>` |
| **USER** | 3+ hard-coded USER privilege keys |
| **SYSTEM** | 3+ hard-coded SYSTEM privilege keys |
| **ADMIN** | 3+ hard-coded ADMIN privilege keys |

### User Roles

| Role | Access Level | Description |
|:---|:---|:---|
| **AGENT** | **Pilot Access** | Can fly drones, view local surroundings, and see basic session stats. Blind to global lists (targets/obstacles). |
| **USER** | **Viewer Access** | Inherits AGENT. Can view the full global scenario (all targets/obstacles) and session entities. |
| **SYSTEM** | **Management** | Inherits USER. Can create/edit/delete entities (Drones, Targets, etc.) and manage sessions. |
| **ADMIN** | **Full Access** | Inherits SYSTEM. Exclusive access to validation and grading (`/check/*`) endpoints. |

---

## 2. Role Hierarchy & Comparison

The system uses a linear inheritance model: **ADMIN > SYSTEM > USER > AGENT**.

| Category | Function / Endpoint | AGENT | USER | SYSTEM | ADMIN |
|:---|:---|:---:|:---:|:---:|:---:|
| **Drones** | Control Drone (Flight Commands) | ✅ | ✅ | ✅ | ✅ |
| | Get Command History / Status | ✅ | ✅ | ✅ | ✅ |
| | **Register / Delete Drone** | ❌ | ❌ | ✅ | ✅ |
| **Targets** | Get Specific Target Info | ✅ | ✅ | ✅ | ✅ |
| | **List All Targets (Global)** | ❌ | ✅ | ✅ | ✅ |
| | **Add / Update / Delete Target** | ❌ | ❌ | ✅ | ✅ |
| **Obstacles** | Get Specific Obstacle Info | ✅ | ✅ | ✅ | ✅ |
| | **List All Obstacles (Global)** | ❌ | ✅ | ✅ | ✅ |
| | **Add / Update / Delete Obstacle** | ❌ | ❌ | ✅ | ✅ |
| **Sessions** | Get Session Metadata | ✅ | ✅ | ✅ | ✅ |
| | **Get Session Entity Data** | ❌ | ✅ | ✅ | ✅ |
| | **Get Session History Data** | ❌ | ❌ | ✅ | ✅ |
| | **Reset Current Session** | ❌ | ❌ | ✅ | ✅ |
| | **Create / Restore / Delete Session** | ❌ | ❌ | ✅ | ✅ |
| **Tasks** | View / Mark Done | ✅ | ✅ | ✅ | ✅ |
| | **Create / Update / Delete Task** | ❌ | ❌ | ✅ | ✅ |
| **Validation** | **All `/check` Endpoints** | ❌ | ❌ | ❌ | ✅ |

### Data Visibility & Masking
To protect scenario integrity:
*   **AGENT**: `GET /sessions/current` always returns **metadata only**.
*   **USER**: `GET /sessions/current?data=true` returns entities (Drones, Targets) but **hides history**.
*   **Task Details**: For AGENT/USER, sensitive task fields (like hidden API checks) are masked.

---

## 3. Detailed API Endpoint Permissions

The following table lists every API endpoint and the **minimum role** required to access it.

### Legend
- **AGENT+**: Accessible by AGENT, USER, SYSTEM, and ADMIN.
- **USER+**: Accessible by USER, SYSTEM, and ADMIN.
- **SYSTEM+**: Accessible by SYSTEM and ADMIN only.
- **ADMIN**: Accessible by ADMIN only.

### 🚁 Drones

| Method | Endpoint | Description | Minimum Role |
|:---|:---|:---|:---:|
| `GET` | `/drones` | Get all registered drones | **AGENT+** |
| `POST` | `/drones` | Register a new drone | **SYSTEM+** |
| `GET` | `/drones/{id}` | Get specific drone details | **AGENT+** |
| `PUT` | `/drones/{id}` | Update drone properties | **SYSTEM+** |
| `DELETE` | `/drones/{id}` | Delete a drone | **SYSTEM+** |
| `PUT` | `/drones/{id}/position` | Admin set position | **SYSTEM+** |
| `GET` | `/drones/{id}/nearby` | Local perception (All types) | **AGENT+** |
| `GET` | `/drones/{id}/nearby/drones` | Local perception (Drones) | **AGENT+** |
| `GET` | `/drones/{id}/nearby/targets` | Local perception (Targets) | **AGENT+** |
| `GET` | `/drones/{id}/nearby/obstacles` | Local perception (Obstacles) | **AGENT+** |
| `POST` | `/drones/{id}/battery` | Update battery (Test) | **AGENT+** |
| `POST` | `/drones/land_all` | Land all drones (Management) | **SYSTEM+** |
| `POST` | `/drones/charge_all` | Charge all drones (Management) | **SYSTEM+** |

### 🎮 Drone Commands (Pilot)

| Method | Endpoint | Description | Minimum Role |
|:---|:---|:---|:---:|
| `POST` | `/drones/{id}/command` | Send generic command | **AGENT+** |
| `GET` | `/drones/{id}/commands` | Get command history | **AGENT+** |
| `GET` | `/commands/{id}` | Get command status | **AGENT+** |
| `POST` | `/drones/{id}/command/take_off` | Take off | **AGENT+** |
| `POST` | `/drones/{id}/command/land` | Land | **AGENT+** |
| `POST` | `/drones/{id}/command/move_to` | Move to coordinates | **AGENT+** |
| `POST` | `/drones/{id}/command/move_towards` | Move in direction | **AGENT+** |
| `POST` | `/drones/{id}/command/move_along_path` | Follow path | **AGENT+** |
| `POST` | `/drones/{id}/command/change_altitude` | Change altitude | **AGENT+** |
| `POST` | `/drones/{id}/command/hover` | Hover | **AGENT+** |
| `POST` | `/drones/{id}/command/rotate` | Rotate heading | **AGENT+** |
| `POST` | `/drones/{id}/command/return_home` | Return to home position | **AGENT+** |
| `POST` | `/drones/{id}/command/set_home` | Set current pos as home | **AGENT+** |
| `POST` | `/drones/{id}/command/calibrate` | Calibrate sensors | **AGENT+** |
| `POST` | `/drones/{id}/command/take_photo` | Take photo | **AGENT+** |
| `POST` | `/drones/{id}/command/send_message` | Send message | **AGENT+** |
| `POST` | `/drones/{id}/command/broadcast` | Broadcast message | **AGENT+** |
| `POST` | `/drones/{id}/command/charge` | Charge battery | **AGENT+** |

### 🎯 Targets

| Method | Endpoint | Description | Minimum Role |
|:---|:---|:---|:---:|
| `GET` | `/targets` | Get all targets (Global List) | **USER+** |
| `POST` | `/targets` | Create new target | **SYSTEM+** |
| `GET` | `/targets/{id}` | Get specific target | **AGENT+** |
| `PUT` | `/targets/{id}` | Update target | **SYSTEM+** |
| `DELETE` | `/targets/{id}` | Delete target | **SYSTEM+** |
| `GET` | `/targets/type/{type}` | Get targets by type | **USER+** |
| `POST` | `/targets/waypoints/{id}/check-drone` | Check charging status | **USER+** |

### 🧱 Obstacles

| Method | Endpoint | Description | Minimum Role |
|:---|:---|:---|:---:|
| `GET` | `/obstacles` | Get all obstacles (Global List) | **USER+** |
| `POST` | `/obstacles` | Create new obstacle | **SYSTEM+** |
| `GET` | `/obstacles/{id}` | Get specific obstacle | **AGENT+** |
| `PUT` | `/obstacles/{id}` | Update obstacle | **SYSTEM+** |
| `DELETE` | `/obstacles/{id}` | Delete obstacle | **SYSTEM+** |
| `GET` | `/obstacles/type/{type}` | Get obstacles by type | **USER+** |
| `POST` | `/obstacles/path_collision` | Check path collision | **SYSTEM+** |
| `POST` | `/obstacles/point_collision` | Check point collision | **SYSTEM+** |

### 🌤️ Environment

| Method | Endpoint | Description | Minimum Role |
|:---|:---|:---|:---:|
| `GET` | `/environments` | Get all environments | **SYSTEM+** |
| `POST` | `/environments` | Create environment | **SYSTEM+** |
| `GET` | `/environments/current` | Get current environment | **AGENT+** |
| `GET` | `/environments/{id}` | Get specific environment | **AGENT+** |
| `PUT` | `/environments/{id}` | Update environment | **SYSTEM+** |
| `DELETE` | `/environments/{id}` | Delete environment | **SYSTEM+** |
| `POST` | `/environments/{id}/set-current` | Set active environment | **SYSTEM+** |

### 🎬 Sessions

| Method | Endpoint | Description | Minimum Role |
|:---|:---|:---|:---:|
| `GET` | `/sessions` | Get all sessions (metadata only) | **AGENT+** |
| `POST` | `/sessions` | Create new session | **SYSTEM+** |
| `GET` | `/sessions/current` | Get current session metadata | **AGENT+** |
| `GET` | `/sessions/current/data` | Get full session data + History | **SYSTEM+** |
| `POST` | `/sessions/current/reset` | Reset session history | **SYSTEM+** |
| `GET` | `/sessions/current/screenshot` | Get current screenshot | **AGENT+** |
| `GET` | `/sessions/{id}` | Get session metadata | **SYSTEM+** |
| `POST` | `/sessions/{id}` | Create/Restore with ID | **SYSTEM+** |
| `PUT` | `/sessions/{id}` | Update session metadata | **SYSTEM+** |
| `DELETE` | `/sessions/{id}` | Delete session | **SYSTEM+** |
| `POST` | `/sessions/{id}/set-current` | Set active session (metadata only) | **AGENT+** |
| `POST` | `/sessions/{id}/reset` | Reset session history | **SYSTEM+** |
| `GET` | `/sessions/{id}/data` | Get full session data | **SYSTEM+** |
| `GET` | `/sessions/{id}/screenshot` | Get specific screenshot | **SYSTEM+** |

### 📋 Tasks & Tracking

| Method | Endpoint | Description | Minimum Role |
|:---|:---|:---|:---:|
| `GET` | `/sessions/current/task-progress` | Get current task progress | **AGENT+** |
| `GET` | `/sessions/current/tasks` | Get current tasks | **AGENT+** |
| `GET` | `/sessions/current/tasks/next` | Get next pending task | **AGENT+** |
| `GET` | `/sessions/current/tasks/{id}/check` | Check task and set is_passed | **AGENT+** |
| `GET` | `/sessions/current/tasks/{id}` | Get specific task | **AGENT+** |
| `POST` | `/sessions/current/tasks/{id}/mark-done` | Mark task completed (current session) | **AGENT+** |
| `POST` | `/sessions/current/tasks/{id}/mark-pending` | Mark task pending (current session) | **AGENT+** |
| `GET` | `/sessions/{id}/tasks` | Get all tasks in session | **USER+** |
| `POST` | `/sessions/{id}/tasks` | Create new task | **SYSTEM+** |
| `GET` | `/sessions/{id}/tasks/{id}` | Get specific task | **USER+** |
| `PUT` | `/sessions/{id}/tasks/{id}` | Update task | **SYSTEM+** |
| `DELETE` | `/sessions/{id}/tasks/{id}` | Delete task | **SYSTEM+** |
| `POST` | `/sessions/{id}/tasks/{id}/mark-done` | Mark task completed | **SYSTEM+** |
| `POST` | `/sessions/{id}/tasks/{id}/mark-pending` | Mark task pending | **SYSTEM+** |
| `POST` | `/sessions/{id}/tasks/swap` | Swap task order | **SYSTEM+** |
| `GET` | `/sessions/{id}/command-history` | Get command history | **SYSTEM+** |
| `GET` | `/sessions/{id}/status-history` | Get status history | **SYSTEM+** |
| `GET` | `/sessions/{id}/target-reaches` | Get target reach logs | **SYSTEM+** |
| `GET` | `/sessions/{id}/moving-target-tracking` | Get moving target tracking summaries | **SYSTEM+** |
| `GET` | `/sessions/{id}/area-coverage` | Get area coverage logs | **SYSTEM+** |
| `GET` | `/sessions/{id}/task-progress` | Get task progress | **SYSTEM+** |

### ✅ System Checks (Admin Only)

| Method | Endpoint | Description | Minimum Role |
|:---|:---|:---|:---:|
| `GET` | `/check/drone_position` | Verify drone coordinates | **ADMIN** |
| `GET` | `/check/drone_status` | Verify drone status | **ADMIN** |
| `GET` | `/check/drone_battery_level` | Verify battery level | **ADMIN** |
| `GET` | `/check/drone_heading` | Verify heading | **ADMIN** |
| `GET` | `/check/drone_over_height` | Verify min altitude | **ADMIN** |
| `GET` | `/check/drone_altitude` | Verify exact altitude | **ADMIN** |
| `GET` | `/check/drone_in_target` | Verify drone inside target | **ADMIN** |
| `GET` | `/check/drone_at_home` | Verify drone at home | **ADMIN** |
| `GET` | `/check/target_within_drone_distance` | Check dist target to drone | **ADMIN** |
| `GET` | `/check/target_in_photo_taken_by_drone` | Check target in photo | **ADMIN** |
| `GET` | `/check/obstacle_within_drone_distance` | Check dist obstacle to drone | **ADMIN** |
| `GET` | `/check/two_drones_distance` | Check distance between drones (params: `drone_1_id`, `drone_2_id`) | **ADMIN** |
| `GET` | `/check/drone_on_ground` | Verify drone on ground | **ADMIN** |
| `GET` | `/check/all_drones_on_ground` | Verify all drones on ground | **ADMIN** |
| `GET` | `/check/drone_hovering` | Verify drone hovering | **ADMIN** |
| `GET` | `/check/all_drones_hovering` | Verify all drones hovering | **ADMIN** |
| `GET` | `/check/target_is_reached` | Verify target reached (any) | **ADMIN** |
| `GET` | `/check/target_is_reached_by_drone` | Verify target reached (specific) | **ADMIN** |
| `GET` | `/check/drone_group_distance` | Check pairwise distances across a drone group (params: repeated `drone_ids`, `mode`) | **ADMIN** |
| `GET` | `/check/moving_target_tracked` | Verify moving target tracked duration | **ADMIN** |
| `GET` | `/check/target_is_fully_searched` | Verify search coverage | **ADMIN** |
| `GET` | `/check/task_progress` | Verify task progress % | **ADMIN** |
| `GET` | `/check/task_done` | Verify task completion | **ADMIN** |
| `GET` | `/check/drone_has_taken_off` | History: Check takeoff | **ADMIN** |
| `GET` | `/check/drone_has_landed` | History: Check landing | **ADMIN** |
| `GET` | `/check/drone_has_visited_position` | History: Check position visit | **ADMIN** |
| `GET` | `/check/drone_has_moved_distance` | History: Check distance flown | **ADMIN** |
| `GET` | `/check/drone_has_moved_directed_distance` | History: Check directed distance | **ADMIN** |
| `GET` | `/check/drone_has_hovered` | History: Check hover duration | **ADMIN** |
| `GET` | `/check/drone_has_taken_photo` | History: Check photos taken | **ADMIN** |
| `GET` | `/check/drone_has_charged` | History: Check charging | **ADMIN** |
| `GET` | `/check/drone_has_sent_message` | History: Check messaging | **ADMIN** |
| `GET` | `/check/drone_has_sent_message_content` | History: Check message content match | **ADMIN** |
| `GET` | `/check/all_drones_have_taken_off` | History: Check all took off | **ADMIN** |
| `GET` | `/check/all_drones_have_landed` | History: Check all landed | **ADMIN** |

### 🌐 Public / Misc

| Method | Endpoint | Description | Minimum Role |
|:---|:---|:---|:---:|
| `GET` | `/` | System Health Check | **Public** |
| `GET` | `/version` | Server version info | **AGENT+** |
