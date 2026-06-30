# MultiUAV-Plat Control System - GUI Controller

A Python GUI application for controlling UAVs (drones) through a RESTful API interface. This system provides an intuitive graphical interface to manage sessions, drones, targets, and environments.

## Features

### Session Management
- **Session Creation**: Create new sessions with custom names and descriptions
- **Session Loading**: Load and switch between existing sessions
- **Session Export/Import**: Save sessions to JSON files and load them later
- **Session Details**: View session statistics (drones, targets, obstacles count)
- **Session Deletion**: Remove unwanted sessions

### Drone Management
- **Drone Management**: Add new drones, send commands (take off, land, move, emergency)
- **Target Management**: Create waypoints, moving targets, and fixed observation targets
- **Environment Management**: Create and manage different weather environments
- **Real-time Updates**: Refresh data to see current drone status and positions
- **User-friendly Interface**: Tabbed interface with easy-to-use dialogs

## Prerequisites

Before running the GUI controller, make sure you have:

1. Python 3.7 or higher installed
2. The MultiUAV-Plat Control System API server running on `http://127.0.0.1:8000`

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

Note: `tkinter` is usually included with Python installations, but if you encounter issues, you may need to install it separately depending on your system.

## Usage

### Starting the Application

The application now starts with a Session Manager that allows you to manage sessions before entering the main GUI controller:

```bash
python main.py
```

Alternatively, you can still run the GUI controller directly (but you'll need to manage sessions through the API):

```bash
python gui_controller.py
```

### Session Management Workflow

1. **Start the Application**: Run `python main.py` to open the Session Manager
2. **Create or Select Session**: 
   - Create a new session with "Create New Session"
   - Select an existing session from the list
   - Import a session from a JSON file
3. **Launch Session**: Double-click a session or click "Launch Session" to enter the main GUI
4. **Return to Session Manager**: When you exit the main GUI, you'll return to the Session Manager

### Session Manager Features

#### Session Operations
- **Create New Session**: Create a session with custom name, description, and optional example data
- **Launch Session**: Enter the main GUI controller for the selected session
- **Load Session**: View complete session data including all drones, targets, obstacles, and environment
- **Delete Session**: Remove unwanted sessions (with confirmation)
- **Export Session**: Save complete session data to a JSON file using the enhanced `/data` endpoint
- **Import Session**: Restore session data from a JSON file using the new `/restore` endpoint
- **Refresh**: Update the session list with latest data from the API

#### Session Details Panel
When you select a session, you can view:
- Session name and status
- Description
- Number of drones, targets, and obstacles
- Creation timestamp

### Interface Overview

The application has three main tabs:

#### 1. Drones Tab
- **View Drones**: Lists all registered drones with their status, battery level, and position
- **Add Drone**: Register a new drone with custom specifications
- **Take Off**: Command selected drone to take off to specified altitude
- **Land**: Command selected drone to land
- **Move To**: Move selected drone to specific coordinates (x, y, z)
- **Emergency**: Execute emergency landing for selected drone
- **Refresh**: Update the drone list with latest data

#### 2. Targets Tab
- **View Targets**: Lists all targets with their type and position
- **Add Waypoint**: Create a static waypoint target
- **Add Moving Target**: Create a target that moves with specified velocity
- **Add Fixed**: Create a fixed target (also covers points of interest)
- **Delete Target**: Remove selected target
- **Refresh**: Update the target list

#### 3. Environment Tab
- **View Environments**: Lists all environments with weather conditions
- **Create Environment**: Create new weather environment with custom conditions
- **Set as Current**: Set selected environment as the active one
- **Delete Environment**: Remove selected environment
- **Refresh**: Update the environment list

### How to Use

1. **Start the API Server**: Make sure the MultiUAV-Plat Control System API is running on port 8000
2. **Launch Application**: Run `python main.py` to start the Session Manager
3. **Manage Sessions**: Create a new session or select an existing one
4. **Launch GUI**: Double-click a session or click "Launch Session" to enter the main controller
5. **Add Drones**: Use the "Add Drone" button to register new drones
6. **Control Drones**: Select a drone from the list and use control buttons
7. **Manage Targets**: Switch to the Targets tab to create waypoints and objectives
8. **Set Environment**: Use the Environment tab to create and activate weather conditions
9. **Exit Session**: Close the main GUI to return to the Session Manager

### Example Workflow

1. **Create and launch a session**:
   - Run `python main.py` to start the Session Manager
   - Click "Create New Session" and provide a name and description
   - Select the new session and click "Launch Session"

2. **Add a new drone**:
   - Click "Add Drone" in the Drones tab
   - Fill in drone specifications (name, model, capabilities, initial position)
   - Click "Add Drone" to register

3. **Take off and move**:
   - Select the drone from the list
   - Click "Take Off" and specify altitude (e.g., 10 meters)
   - Click "Move To" and specify target coordinates
   - Monitor drone status in the list

4. **Create targets**:
   - Switch to Targets tab
   - Click "Add Waypoint" to create a navigation point
   - Click "Add Moving Target" for dynamic objectives
   - Use "Add POI" for observation points

5. **Set environment**:
   - Switch to Environment tab
   - Click "Create Environment" to define weather conditions
   - Select the environment and click "Set as Current"

6. **Export session**:
   - Exit the main GUI to return to Session Manager
   - Select your session and click "Export Session" to save your work
   - The export includes complete session data: drones, targets, obstacles, and environment

7. **Import session**:
   - Click "Import Session" to restore a previously exported session
   - The system supports both old and new export formats
   - Complete session restoration includes all associated data

### Enhanced Session Management

The session manager has been updated with improved functionality using new API endpoints:

#### Export Functionality
- **Complete Data Export**: Uses the `/sessions/{id}/data` endpoint to export all session data
- **Export Metadata**: Includes export timestamp and version information
- **Detailed Logging**: Logs comprehensive information about exported content
- **User Feedback**: Shows detailed success messages with export statistics

#### Import Functionality
- **Session Restoration**: Uses the new `/sessions/restore` endpoint for complete session restoration
- **Backward Compatibility**: Supports both old and new export file formats
- **Complete Data Import**: Restores drones, targets, obstacles, and environment data
- **Import Validation**: Validates import data and provides detailed feedback
- **Conflict Resolution**: Handles session name conflicts during import

#### Load Session Feature
- **Data Viewing**: New "Load Session" button to view complete session data
- **Enhanced Display**: Shows session data in a formatted, scrollable window
- **Detailed Logging**: Logs comprehensive information about loaded session content
- **Status Updates**: Provides detailed status information during loading

### API Endpoints Used

The application interacts with these API endpoints:

#### Session Management
- **Sessions**: `/sessions`, `/sessions/{id}`, `/sessions/{id}/set-current`
- **Session Data**: `/sessions/{id}/data` (enhanced endpoint for complete data export)
- **Session Restore**: `/sessions/restore` (new endpoint for importing complete session data)

#### Main GUI Controller
- **Drones**: `/drones`, `/drones/{id}/command`
- **Targets**: `/targets`, `/targets/{id}`
- **Environments**: `/environments`, `/environments/{id}/set-current`

### Error Handling

- Connection errors are displayed if the API server is not running
- Input validation ensures proper data types for coordinates and parameters
- Status bar shows current operation status and results

### Troubleshooting

**"Could not connect to the API server"**:
- Ensure the MultiUAV-Plat Control System API is running on `http://127.0.0.1:8000`
- Check if the server is accessible by visiting `http://127.0.0.1:8000/docs`

**"No Selection" warnings**:
- Make sure to select an item from the list before using control buttons

**"Invalid Input" errors**:
- Ensure numeric fields contain valid numbers
- Check that required fields are not empty

## Features in Detail

### Drone Commands
- **Take Off**: Lifts drone to specified altitude
- **Land**: Brings drone down to ground level
- **Move To**: Navigates drone to specific 3D coordinates
- **Emergency**: Immediate emergency landing procedure

### Target Types
- **Waypoint**: Static navigation points
- **Moving**: Targets with velocity vectors
- **Fixed**: Static observation or task targets (use for former points of interest)

### Environment Conditions
- Weather types: clear, cloudy, rainy, storm, fog, snow
- Wind directions: 8-point compass (north, northeast, etc.)
- Configurable temperature, humidity, wind speed, and visibility

## Development

The GUI is built using Python's tkinter library and follows a modular design:

- `UAVControllerGUI`: Main application class
- `DroneDialog`: Dialog for adding new drones
- `MoveToDialog`: Dialog for drone movement commands
- `TargetDialog`: Dialog for creating targets
- `EnvironmentDialog`: Dialog for creating environments
- `utils.py`: Shared utilities (logging, dialog helpers, session API helpers, editor math)

All API communication is handled through the `make_request()` method with proper error handling and user feedback.

### Logging System

The application uses a unified logging system that ensures both the Session Manager and GUI Controller write to the same log file:

#### Shared Logging Features
- **Single Log File**: Both `session_manager.py` and `gui_controller.py` write to the same timestamped log file (`logs/uav_system_YYYYMMDD_HHMMSS.log`)
- **Module Identification**: Log entries include the module name (SessionManager or UAVController) for easy identification
- **Consistent Formatting**: Unified log format with timestamp, level, module, function, line number, and message
- **Dual Output**: Logs are written to both file and console for development convenience
- **Automatic Directory Creation**: The `logs/` directory is created automatically if it doesn't exist

#### Log File Format
```
2025-07-20 22:38:13 - INFO - [SessionManager:setup_logging:61] - Session Manager started
2025-07-20 22:38:13 - INFO - [UAVController:setup_logging:38] - UAV Controller GUI started
```

#### Usage
The shared logging is automatically configured when either module starts. No manual configuration is required. Log files are stored in the `logs/` directory and are automatically timestamped to prevent conflicts.

## Building Executables with PyInstaller

You can bundle the application into a standalone executable with [PyInstaller](https://pyinstaller.org/) on any platform.

### Prerequisites

1. Install PyInstaller:
```bash
pip install pyinstaller
```

2. Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Building the Executable

**IMPORTANT**: The application uses dynamically imported modules (`session_editor`, `session_editor_dialogs`) that PyInstaller cannot detect automatically. You **must** use the provided spec file to ensure these modules are included.

#### Recommended Method (All Platforms)

Use the included `uav_controller.spec` file:

```bash
pyinstaller uav_controller.spec
```

The executable will be created in the `dist/` directory.

#### Platform-Specific Notes

**Windows**:
- The spec file uses `img/controller.ico` as the icon
- For best results, ensure `controller.ico` exists in the `img/` directory
- The executable will be `dist/uav_controller.exe`

**macOS**:
- The spec file uses `img/controller.png` as the icon
- For best results, convert to `.icns` format: create `img/controller.icns`
- Gatekeeper may require code signing for distribution
- To create a windowed app bundle, modify the spec file: change `console=True` to `console=False`

**Linux**:
- The executable will be `dist/uav_controller` (ELF binary)
- Make sure it has execute permission: `chmod +x dist/uav_controller`
- Install required system packages for tkinter if missing

### Alternative: Manual Build (Not Recommended)

If you need to build without the spec file (not recommended as it will break session_editor functionality):

**Windows**:
```powershell
pyinstaller --noconfirm --clean --onefile --add-data "./logs;logs" --add-data "./img;img" --hidden-import=session_editor --hidden-import=session_editor_dialogs --icon "img/controller.ico" --name "uav_controller" main.py
```

**macOS/Linux**:
```bash
pyinstaller --noconfirm --clean --onefile --add-data "./logs:logs" --add-data "./img:img" --hidden-import=session_editor --hidden-import=session_editor_dialogs --icon "img/controller.png" --name "uav_controller" main.py
```

### Troubleshooting PyInstaller Builds

**Session Editor not opening in executable**:
- This happens when `session_editor.py` is not included in the bundle
- **Solution**: Always use `uav_controller.spec` instead of manual commands
- The spec file explicitly includes all dynamically imported modules

**Missing tkinter or GUI libraries**:
- Install system packages: `python3-tk` (Debian/Ubuntu) or `tk` (other systems)
- Ensure tkinter works before building: `python -m tkinter`

**Icon not appearing**:
- Windows: Use `.ico` format (`img/controller.ico`)
- macOS: Use `.icns` format (`img/controller.icns`)
- Linux: Use `.png` format (`img/controller.png`)

### Distribution

- The generated executable in `dist/` is standalone and can be distributed
- Ensure the target machine has:
  - The MultiUAV-Plat API server accessible
  - Network connectivity to `http://127.0.0.1:8000` (or configured server address)
- For production deployment, update the API server URL in settings

### Tips
- Run from a virtual environment to keep dependencies isolated
- The spec file automatically includes all Python modules in the project directory
- Logs will be created in a `logs/` directory relative to the executable
- To customize the build, edit `uav_controller.spec` (well-commented for easy modification)
