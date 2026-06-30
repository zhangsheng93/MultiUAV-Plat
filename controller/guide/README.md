# User Guide

This folder contains practical user guides for the MultiUAV-Plat Control System UI tools.

For a broad project overview, see the main [README](../README.md). For API details, see [API documentation](../API_doc/API_DOCUMENTATION.md).

## Prerequisites

Install dependencies from the project root:

```bash
pip install -r requirements.txt
```

Start the UAV API server before using the GUI tools:

```bash
python api_server.py
```

The default API endpoint is `http://127.0.0.1:8000`. Use `Settings` in the Session Manager if your local configuration differs.

## Start the Main App

Launch the Session Manager:

```bash
python main.py
```

The Session Manager is the recommended starting point. From there you can create sessions, launch the controller, open the visual editor, create tasks, and run AI agent checks.

## Guides

1. [Session Manager](session-manager.md)
2. [Session GUI Controller](session-gui-controller.md)
3. [Session Editor](session-editor.md)
4. [Task Generator](task-generator.md)
5. [AI Agent Checker](ai-agent-checker.md)

## Recommended Workflow

1. Open the [Session Manager](session-manager.md) with `python main.py`.
2. Create, import, clone, or select a session.
3. Use `Edit` when you need visual placement of drones, targets, or obstacles.
4. Use `Launch` to open the [Session GUI Controller](session-gui-controller.md) for detailed session operations.
5. Add tasks manually, from templates, or with random generation through the [Task Generator](task-generator.md).
6. Use [AI Agent Checker](ai-agent-checker.md) to run queued tasks against an agent and export results.

## Common Troubleshooting

- If the UI cannot connect, confirm `python api_server.py` is running and check `http://127.0.0.1:8000/docs`.
- If template actions show no compatible choices, verify the session has the drones, targets, or obstacles required by the selected template.
- If the AI checker cannot run tasks, confirm both the UAV API server and the agent server are running.
