# MultiUAV-Plat Server System

A comprehensive drone control and simulation system featuring a RESTful API built with FastAPI and an interactive visualization UI using Pygame. This system provides a complete framework for simulating, controlling, and monitoring multiple UAVs (Unmanned Aerial Vehicles) in a dynamic environment.

## Key Features

### Drone Management
- **Multi-drone support**: Register and control multiple drones simultaneously
- **Real-time monitoring**: Track position, battery, status, and flight parameters
- **Command execution**: Send various commands (takeoff, landing, movement, etc.)
- **Emergency handling**: Automatic emergency landing on critical battery levels
- **Battery management**: Realistic battery consumption and charging stations

### Environment Simulation
- **Weather conditions**: Multiple weather types (clear, cloudy, rain, storm, etc.)
- **Dynamic obstacles**: Buildings, no-fly zones, and circular obstacles
- **Collision detection**: Path and point collision checking with safety margins
- **Moving targets**: Patrol routes and waypoint navigation
- **Charging stations**: Waypoints that automatically recharge drones

### Developer-Friendly API
- **RESTful endpoints**: Clean, well-documented API using FastAPI
- **Session management**: Save, restore, and manage multiple simulation scenarios
- **Interactive documentation**: Built-in Swagger UI at `/docs`
- **Python client library**: Ready-to-use client examples in `/client`

## Project Structure

```
.
├── api/                # FastAPI implementation
│   ├── __init__.py
│   └── server.py      # API endpoints and server configuration
├── controllers/       # Business logic
│   ├── __init__.py
│   ├── drone_controller.py  # Drone control logic
│   ├── target_controller.py # Target management logic
│   ├── obstacle_controller.py # Obstacle management and collision detection
│   └── environment_controller.py # Environment management logic
├── models/            # Data models
│   ├── __init__.py
│   ├── drone.py       # Drone model and enums
│   ├── target.py      # Target model and enums
│   ├── obstacle.py    # Obstacle model and collision detection
│   └── environment.py # Environment model and enums
├── ui/                # User interface
│   ├── __init__.py
│   └── interface.py   # Pygame UI implementation
├── main.py           # Application entry point
├── requirements.txt  # Project dependencies
└── README.md         # Project documentation
```

## Quick Start

### Prerequisites
- Conda, using Python 3.11 for the recommended server environment
- pip inside the active conda environment

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MultiUAV-Plat/server
   ```

2. **Install dependencies**
   ```bash
   conda create -n multiuav-server python=3.11
   conda activate multiuav-server
   python -m pip install -r requirements.txt
   ```

3. **Run the system**
   ```bash
   # Run both API server and UI
   python main.py

   # Or run only the API server
   python main.py --api-only

   # Or run only the UI
   python main.py --ui

   # Run API server and UI with drone controls, skipping the startup UI prompt
   python main.py --ui-drone-control

   # Retain up to 10,000 HTTP request-history records for the current session
   python main.py --api-only --request-history-limit 10000
   ```

4. **Access the API documentation**
   - Open your browser to http://127.0.0.1:8000/docs for interactive Swagger UI
   - Or visit http://127.0.0.1:8000/redoc for ReDoc documentation

## System Architecture

### Core Components

1. **API Server** (`api/server.py`)
   - FastAPI-based RESTful API
   - Handles all HTTP requests and responses
   - Manages routing and request validation
   - Provides automatic OpenAPI documentation

2. **Controllers** (`controllers/`)
   - `drone_controller.py`: Drone lifecycle and command execution
   - `target_controller.py`: Target and waypoint management
   - `obstacle_controller.py`: Obstacle management and collision detection
   - `environment_controller.py`: Weather and environmental conditions
   - `session_controller.py`: Session state management

3. **Models** (`models/`)
   - `drone.py`: Drone data model and enums (DroneStatus, DroneCommand)
   - `target.py`: Target types (fixed, moving, waypoints, charging stations)
   - `obstacle.py`: Obstacle types and collision geometry
   - `environment.py`: Weather conditions and environmental parameters
   - `session.py`: Session state and statistics

4. **UI Interface** (`ui/interface.py`)
   - Pygame-based visualization
   - Real-time drone tracking
   - Interactive map controls
   - Visual representation of obstacles and targets

### Data Flow

```
Client Request → FastAPI Router → Controller → Model → Database/State
                                              ↓
                                         Response ← JSON Serialization
```

## Interactive UI Controls

When running the UI interface (`python main.py` or `python main.py --ui`):

The startup dialog that asks whether to open the graphical dashboard uses the
same `ui/img/drone.png` window icon as the dashboard itself.

Drone-control UI actions are disabled by default. Start with
`--ui-drone-control` to show the **Take Off**/**Land** button and allow
map-click movement for selected flying drones. When used without `--ui` or
`--api-only`, `--ui-drone-control` starts the graphical dashboard directly
instead of asking whether to open the UI.

| Control | Action |
|---------|--------|
| **Left Click on Drone** | Select and view drone details |
| **Left Click on Target** | Select and view target information |
| **Left Click on Obstacle** | Select and view obstacle details |
| **Left Click on Map** | Send selected drone to clicked location when `--ui-drone-control` is enabled |
| **Mouse Wheel** | Zoom in/out on the map |
| **Arrow Keys** | Pan the map view |
| **About Button** | Show version, copyright, license, paper, project, and website information with clickable links; click outside to close |
| **R Key** | Refresh all data from API server |
| **ESC Key** | Exit the application |

### UI Features
- Real-time position updates for all drones
- Battery level indicators
- Drone status visualization (colors indicate different states)
- Obstacle boundaries and no-fly zones
- Charging station locations
- Moving target trajectories

## API Overview

The system provides a comprehensive RESTful API with the following endpoint categories:

### 📡 Core Endpoint Groups

| Category | Base Path | Description |
|----------|-----------|-------------|
| **Sessions** | `/sessions` | Manage simulation sessions and scenarios |
| **Drones** | `/drones` | Register, control, and monitor drones |
| **Commands** | `/drones/{id}/command` | Execute drone commands |
| **Targets** | `/targets` | Manage waypoints and objectives |
| **Obstacles** | `/obstacles` | Create and manage obstacles |
| **Collision** | `/obstacles/collision` | Check for path and point collisions |
| **Environment** | `/environments` | Weather and environmental conditions |

### 🎮 Available Drone Commands

| Command | Parameters | Description |
|---------|-----------|-------------|
| `take_off` | `altitude` (float) | Lift off to specified altitude |
| `land` | - | Land at current position |
| `move_to` | `x, y, z` (floats) | Move to specific coordinates |
| `move_towards` | `distance, heading (optional)` | Move distance in direction (uses current heading if not specified) |
| `move_along_path` | `waypoints` (list, 1+), `allow_partial_move` (bool, optional) | Follow one or more waypoints and optionally stop at the last safe waypoint before an obstacle |
| `change_altitude` | `altitude` (float) | Change only altitude |
| `hover` | - | Hold current position |
| `rotate` | `heading` (float) | Change heading/orientation (0=N, 90=E, 180=S, 270=W) |
| `return_home` | - | Return to launch position |
| `set_home` | - | Set current position as home |
| `charge` | `charge_amount` (float) | Charge battery (when at waypoint) |
| `take_photo` | - | Capture image at location |
| `send_message` | `target_drone_id, message` | Send message to another drone |
| `broadcast` | `message` | Broadcast to all drones |
| `calibrate` | - | Calibrate sensors |

For detailed API documentation with request/response examples, see:
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Comprehensive guide with examples
- **[API_REFERENCE.md](API_REFERENCE.md)** - Quick reference for developers

```python
import requests

API_BASE_URL = "http://127.0.0.1:8000"

# Register a drone
response = requests.post(f"{API_BASE_URL}/drones", json={
    "name": "Scout Alpha",
    "model": "Model-D4",
    "max_speed": 20.0,
    "max_altitude": 120.0,
    "battery_capacity": 100.0
})
drone = response.json()
drone_id = drone["id"]

# Take off
requests.post(
    f"{API_BASE_URL}/drones/{drone_id}/command",
    json={"command": "take_off", "parameters": {"altitude": 10.0}}
)

# Move to location
requests.post(
    f"{API_BASE_URL}/drones/{drone_id}/command",
    json={"command": "move_to", "parameters": {"x": 50.0, "y": 50.0, "z": 15.0}}
)

# Move along a path and stop early if a later segment becomes blocked
requests.post(
    f"{API_BASE_URL}/drones/{drone_id}/command",
    json={
        "command": "move_along_path",
        "parameters": {
            "waypoints": [
                {"x": 10.0, "y": 20.0, "z": 15.0},
                {"x": 30.0, "y": 40.0, "z": 15.0},
                {"x": 50.0, "y": 60.0, "z": 15.0}
            ],
            "allow_partial_move": True
        }
    }
)

# Land
requests.post(
    f"{API_BASE_URL}/drones/{drone_id}/command",
    json={"command": "land", "parameters": {}}
)
```

#### Using cURL

```bash
# Register a drone
curl -X POST "http://127.0.0.1:8000/drones" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Scout Alpha",
    "model": "Model-D4",
    "max_speed": 20.0,
    "max_altitude": 120.0,
    "battery_capacity": 100.0
  }'

# Send command using direct endpoint
curl -X POST "http://127.0.0.1:8000/drones/{drone_id}/command/take_off?altitude=10.0"

# Move to coordinates
curl -X POST "http://127.0.0.1:8000/drones/{drone_id}/command/move_to?x=50.0&y=30.0&z=15.0"
```

For more comprehensive examples including targets, obstacles, environments, and advanced features, see the `/client` directory and the full API documentation.

## Advanced Features

### Session Management

The system supports session management, allowing you to save and restore complete simulation states. Sessions track who created them (user/system/admin role):

```python
# Create a new session with auto-generated ID (requires SYSTEM or ADMIN role)
headers = {"X-API-Key": "<SYSTEM_API_KEY>"}
response = requests.post(f"{API_BASE_URL}/sessions", headers=headers, json={
    "name": "Mission Alpha",
    "description": "Patrol mission scenario",
    "with_examples": True
})
session_id = response.json()["id"]

# Create session with specific ID and complete data
response = requests.post(f"{API_BASE_URL}/sessions/mission-backup-001?data=true",
    headers=headers,
    json={
        "name": "Restored Mission",
        "description": "From backup",
        "drones": [...],      # Restore drones
        "targets": [...],     # Restore targets
        "obstacles": [...],   # Restore obstacles
        "environment": {...}  # Restore environment
    }
)
# Returns complete session data including all restored entities

# Overwrite existing session (useful for restoring backups)
response = requests.post(f"{API_BASE_URL}/sessions/mission-backup-001?overwrite=true&data=true",
    headers=headers,
    json={
        "name": "Restored Mission (Overwritten)",
        "description": "Replaces existing session",
        "drones": [...],
        "targets": [...]
    }
)
# Deletes old session and creates new one with same ID

# Get current session with complete data
session_data = requests.get(f"{API_BASE_URL}/sessions/current?data=true").json()
# or use convenience URL
session_data = requests.get(f"{API_BASE_URL}/sessions/current/data").json()

# Update session metadata
requests.put(f"{API_BASE_URL}/sessions/{session_id}",
    headers=headers,
    json={"name": "Updated Mission Name", "status": "completed"}
)
```

### Automatic Charging Stations

Create waypoint targets with charging capabilities:

```python
# Create a charging station
requests.post(f"{API_BASE_URL}/targets", json={
    "name": "Charging Station 1",
    "type": "waypoint",
    "position": {"x": 50.0, "y": 50.0, "z": 0.0},
    "radius": 10.0,
    "charge_amount": 30.0  # Instant charge amount in %
})

# Charge a drone when at waypoint
requests.post(f"{API_BASE_URL}/drones/{drone_id}/command", json={
    "command": "charge",
    "parameters": {"charge_amount": 30.0}
})
```

### Collision Detection

Check for obstacles before moving drones:

```python
# Check if path is clear
collision = requests.post(f"{API_BASE_URL}/obstacles/collision/path", json={
    "start": {"x": 0.0, "y": 0.0, "z": 10.0},
    "end": {"x": 100.0, "y": 100.0, "z": 10.0},
    "safety_margin": 5.0
}).json()

if collision:
    print(f"Collision detected with {collision['obstacle_name']}")
```

## Project Files

- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Comprehensive API reference with examples
- **[API_REFERENCE.md](API_REFERENCE.md)** - Quick endpoint reference for developers
- **[BATTERY_SYSTEM.md](BATTERY_SYSTEM.md)** - Complete battery management system documentation
- **`/client`** directory - Ready-to-use Python client examples
- **`/config`** directory - System configuration (battery costs, settings)
- **`test_*.py`** files - API testing examples

## System Requirements

- Python 3.8+
- FastAPI
- Uvicorn (ASGI server)
- Pygame (for UI)
- Pydantic (data validation)

## Dependencies

All dependencies are listed in `requirements.txt`:
- fastapi
- uvicorn[standard]
- pygame
- pydantic

## Deployment (Standalone Executable)

You can build a standalone executable for Windows, macOS, or Linux with the shared PyInstaller spec file at [`multiuav_plat.spec`](multiuav_plat.spec). Build on the target operating system because PyInstaller output is not cross-platform.

### Prerequisites

Install project dependencies and PyInstaller:

```bash
conda activate multiuav-server
python -m pip install -r requirements.txt
python -m pip install pyinstaller
```

### Build Command

Run the same command on Windows, macOS, and Linux:

```bash
pyinstaller --clean --noconfirm multiuav_plat.spec
```

The generated executable is placed in `dist/`. The filename uses the compact app version format from `main.py`:

- Windows: `dist/MultiUAV-Plat.Server.v0.xx.exe`
- macOS: `dist/MultiUAV-Plat.Server.v0.xx`
- Linux: `dist/MultiUAV-Plat.Server.v0.xx`

### What the spec file bundles

The shared spec file removes the platform-specific `--add-data` syntax differences and bundles the folders the application needs at runtime:

- `config/`
- `models/`
- `controllers/`
- `api/`
- `ui/`

It also collects package data and submodules for `fastapi`, `uvicorn`, and `pygame`, plus project submodules under `api`, `config`, `controllers`, `models`, and `ui`, which covers imports used by the frozen API server and UI.

The project includes native executable icon assets derived from `ui/img/drone.png`:

- Windows: `ui/img/drone.ico`
- macOS: `ui/img/drone.icns`

### Running the compiled application

Run the executable directly from `dist/`:

```bash
# Windows
.\dist\MultiUAV-Plat.Server.v0.xx.exe

# macOS / Linux
./dist/MultiUAV-Plat.Server.v0.xx
```

Supported CLI options are the same as when running from source:

```bash
# API only
./dist/MultiUAV-Plat.Server.v0.xx --api-only

# UI only
./dist/MultiUAV-Plat.Server.v0.xx --ui

# API server and UI with drone controls, skipping the startup UI prompt
./dist/MultiUAV-Plat.Server.v0.xx --ui-drone-control

# UI only with drone controls
./dist/MultiUAV-Plat.Server.v0.xx --ui --ui-drone-control

# Custom host and port
./dist/MultiUAV-Plat.Server.v0.xx --host 0.0.0.0 --port 8080

# Retain up to 10,000 HTTP request-history records for the current session
./dist/MultiUAV-Plat.Server.v0.xx --api-only --request-history-limit 10000
```

Open the API docs at [http://localhost:8000/docs](http://localhost:8000/docs) after startup.

### Platform notes

- Build separately on Windows, macOS, and Linux.
- macOS and Linux builds may need `chmod +x dist/MultiUAV-Plat.Server.v0.xx`.
- The spec bundles `ui/img/drone.png`, so the pygame dashboard and startup dialog window icons still work in frozen builds.
- The spec sets the executable icon automatically when a supported native icon file is present.
- Windows builds use `ui/img/drone.ico`; macOS builds use `ui/img/drone.icns`.
- Linux desktop icon behavior depends on the packaging format and desktop environment rather than the PyInstaller binary alone.

### Troubleshooting

If the frozen app cannot find bundled files, rebuild with a clean tree:

```bash
pyinstaller --clean --noconfirm multiuav_plat.spec
```

If startup is blocked by antivirus or platform security checks, sign or notarize the generated binary for your target platform before distribution.

---

## Development

### Running Tests

```bash
# Test session management
python test_session_isolation.py
python test_session_status.py
python test_session_id_generation.py

# Test new session behavior
python test_new_session_behavior.py
```

### Project Status

- ✅ Multi-drone management
- ✅ Session save/restore
- ✅ Charging stations
- ✅ Collision detection
- ✅ Weather simulation
- ✅ Moving targets
- ✅ Interactive UI
- ✅ RESTful API with OpenAPI docs
- ✅ Standalone executable deployment

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).

Copyright (C) 2026 MultiUAV-Plat Server System Project

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

For the complete license text, see the [LICENSE](LICENSE) file in the project root or visit <https://www.gnu.org/licenses/gpl-3.0.html>.

## Contributing

[Add contributing guidelines here]

## Support

For issues, questions, or contributions, please refer to the project repository.
### Target Types

Supported target types:

- `fixed` — Fixed point with `position` and `radius`
- `moving` — Moving target with `velocity` and optional `moving_path`
- `waypoint` — Charging station with `charge_amount`
- `interest` — Point of interest for missions
- `circle` — Geometric circle target defined by `radius` at `position`; rendered filled with a thin outline in the UI
- `polygon` — Geometric polygon target defined by a list of `vertices` (absolute coordinates); rendered filled with an outline in the UI. Selection highlights the polygon boundary with a margin, and labels are placed outside the top-right boundary for readability.
