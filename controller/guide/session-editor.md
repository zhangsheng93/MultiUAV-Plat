# Session Editor

The Session Editor is the visual canvas for placing and editing drones, targets, and obstacles in a session.

It is implemented with `pygame`, so install project dependencies before opening it:

```bash
pip install -r requirements.txt
```

## How to Open

From the Session Manager:

1. Select a session.
2. Click `Edit`.

From the Session GUI Controller:

1. Open the session with `Launch`.
2. Use `Session` -> `Edit Session`, or click `Visually Edit Session` in the `Statistics` tab.

The editor can also be launched internally by `main.py --launch-session-editor` with a generated config file. Normal users should open it through the UI buttons above.

## What It Is For

Use the Session Editor when you need to:

- See a spatial map of the session.
- Drag drones, targets, and obstacles to new positions.
- Add or edit session entities using visual context.
- Check relative placement before saving or launching tasks.

## Editing Workflow

1. Open the editor from `Edit` or `Edit Session`.
2. Inspect the canvas and current entities.
3. Select an entity to view or modify it.
4. Drag entities to change their positions.
5. Double-click or use editor controls to edit detailed attributes.
6. Add drones, targets, or obstacles with the editor's add controls.
7. Save when the layout is correct.

## Canvas Concepts

- The canvas maps session world coordinates to screen coordinates.
- Drones, targets, and obstacles use different colors and shapes.
- Obstacles can be points, circles, ellipses, or polygons.
- Targets can include fixed, moving, waypoint, circle, or polygon types.
- Grid and coordinate transforms help align placement to the configured session area.

## Save, Reload, and Leave

When the editor is opened from the GUI Controller, the controller watches for editor save events.

- `Save`: writes the edited session data back to the caller.
- `Reload`: discards unsaved editor state and reloads the latest session data.
- `Leave`: exits the editor window.

If the controller reports that editors are still open, close or save those editor windows before exiting the controller.

## Best Practices

- Save before returning to task creation or AI checking.
- Keep drones and targets away from obstacles unless the task intentionally tests obstacle handling.
- Use the Session Manager `Preview` after editing if you want to inspect raw session data.
- Generate an initial screenshot during session creation if you need a visual record of a generated session.

## Troubleshooting

- If the editor does not open, verify `pygame` is installed through `requirements.txt`.
- If changes do not appear in the controller, save in the editor and refresh the relevant controller tab.
- If a dragged item appears offset, check the session area size and coordinate values in the editor dialogs.
