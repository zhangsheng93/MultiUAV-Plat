# Session GUI Controller

The Session GUI Controller is the main per-session workspace. Open it from the Session Manager by selecting a session and clicking `Launch`.

You can also start it directly:

```bash
python gui_controller.py
```

Direct launch is less convenient because session selection is handled best through the Session Manager.

## Main Areas

The controller uses tabs for the major session resources:

- `Statistics`: session summary, counts, progress, and quick actions.
- `Drones`: drone list, editing, commands, and real-time control.
- `Targets`: waypoint, moving, fixed, circle, and polygon targets.
- `Obstacles`: point, circle, ellipse, and polygon obstacles.
- `Environment`: weather and environment state.
- `Tasks`: task creation, editing, checking, and export.
- `History`: command history viewing, filtering, export, and load-and-run.

## Session Actions

Use the `Session` menu for:

- `Export Session`
- `Save Session`
- `Save Session As...`
- `Session Info`
- `Edit Session`
- `Take Screenshot`
- `Exit`

Use `Edit Session` or the `Visually Edit Session` button in `Statistics` to open the visual Session Editor.

## Drone Workflow

1. Open the `Drones` tab.
2. Click `Add` or use `Drones` -> `Add Drone`.
3. Select a drone from the list.
4. Use `Take Off`, `Land`, `Move To`, `Control`, `Edit`, or `Delete`.
5. Click `Refresh` if another tool or API call changed drone state.

## Target and Obstacle Workflow

Use the `Targets` tab to add or edit:

- `+Waypoint`
- `+Moving`
- `+Fixed`
- `+Circle`
- `+Polygon`

Use the `Obstacles` tab to add or edit:

- `+Point`
- `+Circle`
- `+Ellipse`
- `+Polygon`

Select an item before using `Edit` or `Delete`.

## Environment Workflow

1. Open the `Environment` tab.
2. Click `Create Environment`.
3. Fill weather and environment details.
4. Select an environment and click `Set as Current`.
5. Use `Edit`, `Delete Environment`, and `Refresh` as needed.

## Task Workflow

Open the `Tasks` tab to work with the selected session's tasks.

Common task actions:

- `Add`: create a task manually.
- `From Template`: create a task from a reusable task template.
- `RandomGen`: generate random tasks from compatible templates.
- `Edit`: update the selected task.
- `Duplicate`: copy the selected task.
- `Move Up` / `Move Down`: reorder tasks.
- `Toggle Done/Undone`: update task completion state.
- `Delete`: remove selected tasks.
- `Check`: run task completion checks from `execution_check_apis`.
- `Export`: export task check results.
- `Copy Original Command`: copy the original task content.
- `Copy Command`: copy a random command alias or command variant.

See [Task Generator](task-generator.md) for template and random generation details.

## History Workflow

Use the `History` tab or `History` menu to:

- View API command history.
- Filter history entries.
- Export all history.
- Export selected history.
- Load and run saved history.
- Clear filters.

## Keyboard Shortcuts

- `Ctrl+S` or `Cmd+S`: save session.
- `Ctrl+Shift+S` or `Cmd+Shift+S`: save session as.
- `Ctrl+T`: add task.
- `Ctrl+C` or `Cmd+C` on the `Tasks` tab: copy original command.
- `Ctrl+Shift+C` or `Cmd+Shift+C` on the `Tasks` tab: copy generated command.
- `F5`: refresh all.

## Troubleshooting

- If resource lists are stale, click `Refresh` on the current tab or use `View` -> `Refresh All`.
- If commands fail, confirm the selected session is current and the API server is running.
- If task checking reports missing checks, edit the task or template to add `execution_check_apis`.
- If save prompts appear on exit, choose `Save` to persist local session edits before leaving.
