# Session Manager

The Session Manager is the main entry point for creating, organizing, launching, and checking UAV sessions.

Start it from the project root:

```bash
python main.py
```

## What You See

- `Available Sessions`: the list of known sessions.
- `Session Details`: selected session metadata, task type, task description, entity counts, and task counts.
- Main action buttons:
  - `Launch`
  - `Preview`
  - `Rename`
  - `Edit`
  - `Export`
  - `Delete`
  - `CheckUI`
  - `New`
  - `Clone`
  - `Import`
  - `About`
  - `Settings`
  - `Refresh`
  - `TaskUI`

## Basic Workflow

1. Start the API server:

   ```bash
   python api_server.py
   ```

2. Start the Session Manager:

   ```bash
   python main.py
   ```

3. Click `New`, `Clone`, or `Import`.
4. Select a session in `Available Sessions`.
5. Click `Launch` to open the Session GUI Controller.

## Creating Sessions

Click `New` to open the session creation dialog.

Use the dialog to set:

- Session name and description.
- Task type and task description.
- Area size.
- Initialization mode:
  - seed with API example data
  - start empty
  - auto-generate random entities
- Random entity counts for drones, targets, and obstacles.
- Optional task generation from templates.
- Optional initial screenshot generation.
- Optional automatic launch after creation.

Click `Create` for one session or `Create Batch` for multiple sessions.

## Managing Existing Sessions

- `Launch`: opens the selected session in the Session GUI Controller.
- `Preview`: displays full session data without opening the controller.
- `Rename`: changes the session name.
- `Edit`: opens the visual Session Editor.
- `Export`: saves session data to a JSON file.
- `Delete`: removes selected sessions after confirmation.
- `Clone`: duplicates an existing session.
- `Import`: restores a session from a JSON file.
- `Refresh`: reloads the session list from the API and configured storage.

## Settings

Click `Settings` to configure shared app settings such as storage locations, API URL, API key, and username.

These settings are shared by the Session Manager, Session GUI Controller, TaskUI, and AI Agent Checker.

## TaskUI and CheckUI

- `TaskUI`: opens the multi-session task template creator. Use it to create tasks from one template across several sessions.
- `CheckUI`: opens the AI Agent Auto-Check interface. Use it to queue tasks and check whether an AI agent completes them.

## Keyboard Shortcuts

- `Enter`: launch selected session.
- `Space`: preview selected session.
- `Delete` or `Backspace`: delete selected session.
- `F5`: refresh sessions.

## Troubleshooting

- If no sessions appear, click `Refresh` and confirm the API server is running.
- If import fails, verify the file is a valid session export JSON.
- If `Edit` cannot open, install dependencies from `requirements.txt`; the visual editor requires `pygame`.
- If `CheckUI` opens but cannot run checks, confirm the agent server is running as described in [AI Agent Checker](ai-agent-checker.md).
