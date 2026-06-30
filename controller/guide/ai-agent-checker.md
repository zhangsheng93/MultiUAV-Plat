# AI Agent Checker

The AI Agent Checker runs session tasks through an AI agent, waits for the agent to finish, evaluates completion checks, and exports results.

For deeper details, see the [AI Agent Auto-Check README](../check_ui/README.md) and [Quick Start](../check_ui/QUICK_START.md).

## Prerequisites

Start the UAV API server:

```bash
python api_server.py
```

Start the agent server expected by your environment. The checker defaults to `http://localhost:18000` for agent requests.

The checker uses shared settings from `settings.json`, including API base URL, agent base URL, API key, storage paths, and username.

## How to Open

From the Session Manager:

1. Start the app:

   ```bash
   python main.py
   ```

2. Click `CheckUI`.

From the project root:

```bash
python -m check_ui.agent_checker
```

From the `check_ui` folder:

```bash
python run_agent_checker.py
```

## Main Workflow

1. Click `Refresh Sessions`.
2. Select a session to load its tasks.
3. Select one or more tasks.
4. Click `Add Selected to Queue`.
5. Configure options such as force landing.
6. Click `Start`.
7. Watch progress, logs, and score summaries.
8. Click `Export` or use `Results` -> `Export Results` to save a JSON report.

## Session and Task Selection

The left panel loads sessions from the API and can auto-import session files from the configured storage folder.

Use:

- `Refresh Sessions`: reload sessions and auto-import new stored session files.
- `Add Tasks in Sessions`: add tasks from selected sessions.
- `Select All` / `Deselect All`: manage task selection.
- `Add Selected to Queue`: enqueue chosen tasks.
- `Filter`: narrow the visible task list by keyword. Matching is case-insensitive and includes the task's session name/ID, task name/ID, and task category metadata when present. The session list, queued tasks, and results are not changed.

## Queue and Run Controls

Use the queue controls to manage checking:

- `Start`: begin automated checking.
- `Stop`: stop the active run.
- `Pause`: temporarily pause a run.
- `Resume`: continue a paused run.
- `Clear`: remove queued items when the run is not active.
- `Uncheck`: mark selected queued task as unchecked.
- `Export`: save current results.
- `Import`: load previous result data.

Menu equivalents are available under `Sessions`, `Queue`, `Run`, and `Results`.

## Force Landing

Enable force landing when you want all drones to land before each task starts.

This is useful when tasks should run independently or when a previous task may have left drones in flight.

## What Happens During a Run

For each queued task, the checker:

1. Sets the task's session as current.
2. Optionally lands all drones.
3. Reads the task command or command alias.
4. Sends the command to the agent server.
5. Polls the agent job until completion or failure.
6. Evaluates the task's `execution_check_apis`.
7. Records passed or failed checks.
8. Moves to the next queued task.

## Results Export

Exports are JSON files containing:

- Overall task and check statistics.
- Per-task status.
- Session and task identifiers.
- Check details.
- Errors and timestamps.
- A report ID hash.

Unchecked queued tasks are treated as failed in exports.

## Troubleshooting

- `Agent server unavailable`: confirm the agent server is running on the configured agent base URL.
- `No sessions found`: confirm the UAV API server is running and click `Refresh Sessions`.
- Tasks do not appear: verify the selected session has tasks and the API key is valid.
- Checks fail immediately: inspect the task's `execution_check_apis` and related APIs.
- Run appears stuck: wait for the task timeout or use `Stop`; then inspect the agent server logs.
- Export has unexpected failures: confirm every queued task actually ran or was intentionally left unchecked.
