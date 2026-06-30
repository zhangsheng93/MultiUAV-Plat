# AI Agent Auto-Check - Quick Start Guide

## Prerequisites

1. **Start API Server** (port 8000)
   ```bash
   python api_server.py
   ```

2. **Start Agent Server** (port 18000)
   ```bash
   python agent_server.py
   ```

## Launch Application

```bash
cd check_ui
python run_agent_checker.py
```

## Basic Workflow

### Step 1: Select Tasks
1. Click "Refresh Sessions"
   - 📁 Auto-imports session files from storage folder
   - 🔄 Loads all sessions from API
2. Click on a session to load its tasks
3. Select tasks from the tree (Ctrl+Click for multiple)
4. Click "Add Selected to Queue"

### Step 2: Configure
- ☑️ Check "Force land all drones before each task" if you want safety landing

### Step 3: Run
1. Click "Start"
2. Monitor progress in the log area
3. Use "Pause"/"Resume" as needed

### Step 4: Export
- Click "Export Results" to save a JSON report

## What It Does Automatically

For each task in the queue:
1. 🛬 Lands all drones (if option enabled)
2. 📤 Sends command to AI agent
3. ⏳ Waits for agent completion (polls every 5s)
4. ✅ Checks task completion using execution_check_apis
5. 📊 Records results (passed/failed)
6. ➡️ Moves to next task

## Key Controls

- **Start**: Begin automated checking
- **Pause**: Temporarily pause (can resume later)
- **Resume**: Continue from paused state
- **Stop**: Completely stop workflow
- **Clear Queue**: Remove all tasks from queue
- **Export Results**: Save results to JSON file

## Tips

- Select tasks from multiple sessions - they'll all be checked in order
- Check the log area for detailed execution information
- Export results at any time (even during execution)
- Unchecked tasks are treated as "failed" in exports

## Troubleshooting

**"Agent server unavailable"**
→ Make sure agent_server.py is running on port 18000

**"No sessions found"**
→ Check that API server is running and has session data

**Tasks hang**
→ Default timeout is 5 minutes per task. Check agent server logs.

## Example Output

```
[10:30:15] Loading sessions from API...
[10:30:16] Loaded 3 sessions
[10:30:18] Added 5 tasks to queue (Total: 5)
[10:30:20] Started automated checking
[10:30:21] [1/5] Processing: Take off drone-1
[10:30:22]   Landing all drones...
[10:30:24]   Drones landed
[10:30:25]   Command: Take off drone-1 to 15 meters
[10:30:26]   Submitting to agent...
[10:30:27]   Agent status: queued (1.0s)
[10:30:32]   Agent status: running (6.0s)
[10:31:15]   Agent output: Successfully took off drone-1 to 15 meters...
[10:31:16]   Checking task completion...
[10:31:17]   Check result: PASSED (5/5 checks passed)
[10:31:18] [2/5] Processing: Move drone-1 to waypoint...
...
```

## Export File Example

The exported JSON contains:
- Summary statistics (pass rates, counts)
- Per-task results with detailed check information
- Timestamps for all operations
- MD5 hash as unique report ID

See [README.md](README.md) for full export format details.
