# 2D to 3D Feature Audit

Scope: compare `drone/ui/interface.py` with the standalone `web_3d_viewer` frontend. `drone/` remains unchanged.

## Implemented / Aligned

- Current session data rendering: drones, targets, obstacles, paths, task progress.
- 2D coordinate semantics in top view: origin lower-left, +X right, +Y up.
- Dynamic scene bounds, grid, axes, minimap, pan, zoom, reset/fit view.
- Object picking for drones, targets, obstacles, including overlapping-object click cycling.
- Selection details for drones, targets, and obstacles, including raw object names, polygon vertices, and backend-provided projected area when available.
- Label visibility toggle and adaptive label/drone scaling. Label size starts at 100% and can be adjusted only while labels are visible.
- Drone path display cycle: 10, 20, 1, hidden, all.
- Basic drone commands: takeoff, land, hover, return home, charge, emergency.
- Relative movement controls and altitude movement controls.
- 2D-style direct map click movement after selecting an airborne drone.
- Explicit click-ground move mode.
- Frontend local obstacle precheck before map-click movement, mirroring backend obstacle height semantics.
- Target rendering for fixed, moving, waypoint, circle, polygon.
- Obstacle rendering for point/circle, ellipse, polygon, including height=0 non-flyable semantics.
- Area coverage visualization with task-radius half-width semantics.
- Continuous green coverage footprint and optional 2D coverage point display.
- Target motion paths remain hidden by default and no longer have a visible toggle in the final viewer.
- Session refresh, switch, reset, export JSON, delete.
- Current-session task list, next, inspect, check, mark done, mark pending.
- Generic `/check/*` runner with the backend check endpoint list.
- Advanced generic drone command runner through `/drones/{id}/command`.
- Frontend screenshot export: PNG/JPG/SVG/PDF/EPS.
- Backend screenshot download: PNG/JPG/SVG/PDF/EPS.
- Demo mode without backend and backend-connected mode.

## Partially Implemented

- Zoom slider: 2D has a horizontal discrete slider; 3D uses a right-side vertical quick zoom scale plus wheel and keyboard zoom, clamped to 40%-500%.
- View reset semantics: 2D return-home button resets origin when no drone is selected; 3D uses a separate fit/reset camera button.
- 2D task authoring templates: 3D can inspect/check/mark current tasks but does not provide full task template creation, update, delete, or swap UI.
- Raw check forms: 3D supports every endpoint through JSON parameters, but not dedicated typed forms for each check.

## Not Implemented By Design

- Replacing backend controller logic in frontend. 3D mirrors key display and precheck semantics but backend remains authoritative for command execution.
- Python/Pygame desktop packaging behavior, macOS reopen handling, and native window lifecycle.
- Full local backend data mutation outside existing session save/edit and task endpoints.
