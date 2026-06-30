# AI Agent Auto-Check UI Gadget

A standalone UI application for automatically testing UAV control tasks using the AI agent, monitoring responses, and checking task completion results.

## Features

- **Auto-Import Sessions**: Automatically imports sessions from the configured storage folder (just like Session Manager)
- **Multi-Session & Task Selection**: Select and queue tasks from multiple sessions for automated testing
- **AI Agent Integration**: Automatically sends commands to the AI agent and monitors execution
- **Task Completion Checking**: Evaluates task completion using execution_check_apis
- **Pause/Resume Control**: Full control over the testing workflow
- **Force Landing Safety**: Optional pre-task drone landing for safety
- **Comprehensive Results Export**: JSON export with detailed statistics and MD5 hash

## Prerequisites

1. **API Server** running on port 8000 (default)
2. **Agent Server** running on port 18000 (see [AGENT_README_API.md](AGENT_README_API.md))
3. Python dependencies (already included in main project):
   - tkinter
   - requests
   - All project utilities (api_server, utils, etc.)

## Quick Start

### Method 1: Using the launcher script

```bash
cd check_ui
python run_agent_checker.py
```

### Method 2: Direct execution

```bash
cd check_ui
python agent_checker.py
```

### Method 3: From project root

```bash
python -m check_ui.agent_checker
```

## Usage Guide

### 1. Load Sessions and Tasks

1. Click **"Refresh Sessions"** to load all available sessions
   - The application automatically imports session files from the storage folder (configured in settings)
   - Sessions are loaded from both the storage folder and the API
   - Only new sessions are imported to avoid duplicates
2. Select a session from the list to view its tasks
3. Tasks will appear in the tasks tree with their status
4. Use **"Filter"** to narrow the visible task list by keyword
   - Matching is case-insensitive
   - The task's session name/ID, task name/ID, and task category metadata are included when available
   - Filtering does not change the session list, task queue, or existing results

**Note**: The session storage folder is the same one used by Session Manager, configured in settings (default: `./sessions/`). Any JSON session files in this folder will be automatically imported when you refresh sessions.

### 2. Build Task Queue

1. Select one or more tasks from the tasks tree (use Ctrl/Cmd+Click for multiple)
2. Click **"Add Selected to Queue"** to add them to the checking queue
3. Use **"Select All"** / **"Deselect All"** for convenience
4. The queue shows all tasks to be checked

### 3. Configure Options

- **Force land all drones before each task**: Check this box to ensure all drones land before executing each task command (safety feature)

### 4. Run Automated Checking

1. Click **"Start"** to begin the automated checking process
2. The application will:
   - For each task in the queue:
     - Optionally land all drones (if checkbox is enabled)
     - Send the task command to the AI agent (port 18000)
     - Wait for agent completion (polling every 5 seconds)
     - Evaluate task completion using execution_check_apis
     - Record results (passed/failed)
   - Move to the next task automatically

3. Monitor progress:
   - Progress bar shows overall completion
   - Current task info displays the active task
   - Log area shows detailed execution steps

### 5. Control Workflow

- **Pause**: Temporarily pause checking (can be resumed)
- **Resume**: Continue from where it was paused
- **Stop**: Completely stop the workflow
- **Clear Queue**: Remove all tasks from queue (only when paused/stopped)

### 6. Export Results

1. Click **"Export Results"** at any time
2. Choose a save location for the JSON file
3. The export includes:
   - Overall statistics (pass rates, totals)
   - Per-task results with detailed check information
   - Timestamps and error messages
   - MD5 hash as unique ID

## Export Format

```json
{
  "id": "md5_hash_of_results",
  "export_timestamp": "2025-12-26T10:30:00",
  "tool": "AI Agent Auto-Check",
  "statistics": {
    "total_tasks": 10,
    "passed_tasks_count": 8,
    "failed_tasks_count": 2,
    "task_pass_rate": 0.8,
    "total_checks": 45,
    "passed_checks": 40,
    "failed_checks": 5,
    "check_pass_rate": 0.8889
  },
  "results": [
    {
      "session_id": "session-uuid",
      "session_name": "Test Session",
      "task_id": "task-uuid",
      "task_name": "Task Name",
      "status": "passed",
      "timestamp": "2025-12-26T10:25:30",
      "error": null,
      "statistics": {
        "total_checks_apis": 5,
        "passed_checks_apis": 5,
        "failed_checks_apis": 0,
        "pass_rate": 1.0
      },
      "details": [...]
    }
  ]
}
```

## Architecture

### File Structure

```
check_ui/
├── __init__.py              # Package initialization
├── README.md                # This file
├── AGENT_README_API.md      # Agent API documentation
├── agent_client.py          # Agent API client wrapper
├── agent_checker.py         # Main UI application
└── run_agent_checker.py     # Launcher script
```

### Key Components

1. **AgentClient** (`agent_client.py`)
   - Handles communication with agent server (port 18000)
   - Async job submission and status polling
   - Health checks and error handling

2. **AgentCheckerApp** (`agent_checker.py`)
   - Main Tkinter UI application
   - Session/task selection interface
   - Automated checking workflow with threading
   - Task completion evaluation (reuses logic from gui_controller.py)
   - Results export functionality

3. **API Integration**
   - Reuses `api_server.py` from main project
   - Added `api_land_all_drones()` method for force landing
   - Uses existing check evaluation logic

## Workflow Details

### Checking Process for Each Task

1. **Preparation**
   - If force landing enabled: Call `POST /drones/land_all`
   - Set session as current: `POST /sessions/{id}/set-current`

2. **Get Task Command**
   - Fetch task data: `GET /sessions/{session_id}/tasks/{task_id}`
   - Select command from task content or aliases (random)

3. **Agent Execution**
   - Submit command: `POST http://localhost:18000/agent/command/async`
   - Get job_id from response
   - Poll status: `GET http://localhost:18000/agent/jobs/{job_id}` (every 5s)
   - Wait for status: `completed` or `failed`

4. **Task Checking**
   - Evaluate execution_check_apis recursively
   - Support for AND/OR/NOT logic groups
   - Make API calls to check endpoints
   - Compare results with expected values
   - Record detailed pass/fail information

5. **Result Recording**
   - Store status, details, timestamp
   - Mark task as done if all checks passed
   - Log results to UI

## Configuration

The application uses the shared `settings.json` via `get_settings()`:

- `api_base_url`: Base URL for UAV API (default: `http://127.0.0.1:8000`)
- `agent_base_url`: Base URL for Agent API (default: `http://localhost:18000`)
- `api_key`: API key for authentication

## Troubleshooting

### Agent Server Unavailable
- Ensure agent_server.py is running: `python agent_server.py`
- Check that port 18000 is not blocked
- Verify agent server health: `curl http://localhost:18000/health`

### API Server Connection Issues
- Ensure api_server.py is running on port 8000
- Check API key in settings
- Verify network connectivity

### Tasks Not Loading
- Ensure sessions exist in the API
- Check API authentication
- Try "Refresh Sessions" button

### Checking Hangs or Timeout
- Default timeout is 300s (5 minutes) per task
- Agent commands may take 1-3 minutes typically
- Check agent server logs for errors
- Use "Stop" button to cancel

## Integration with Main Project

This gadget is designed to be **standalone** but **reuses** existing project functionality:

- **Reused modules**: `api_server.py`, `utils.py`, `app_settings.py`
- **Reused logic**: Task checking algorithm from `gui_controller.py`
- **Added functionality**: `api_land_all_drones()` method in `api_server.py`
- **No breaking changes**: All code isolated in `check_ui/` folder

## Development Notes

### Adding Features

The codebase is modular and can be extended:

- Modify `AgentClient` for new agent API features
- Add UI panels in `setup_ui()` method
- Extend checking logic in `check_single_task()`
- Customize export format in `export_results()`

### Threading Model

- Main UI runs on Tkinter main thread
- Checking workflow runs on background thread (`worker_thread`)
- UI updates use `root.after(0, callback)` for thread safety
- Pause/resume uses polling with `is_paused` flag

## License

Part of the UAV Control System project.

## Support

For issues or questions:
1. Check agent server documentation: [AGENT_README_API.md](AGENT_README_API.md)
2. Review main project documentation
3. Check application logs for error details
