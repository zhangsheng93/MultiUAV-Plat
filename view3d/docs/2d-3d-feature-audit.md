# 2D to 3D Feature Audit

Scope: compare the legacy 2D interface behavior with this standalone display-only 3D frontend. Backend/controller code remains unchanged.

## Implemented / Aligned

- Current session data rendering: drones, targets, obstacles, paths, task progress.
- 2D coordinate semantics in top view: origin lower-left, +X right, +Y up.
- Dynamic scene bounds, grid, axes, minimap, pan, zoom, reset/fit view.
- Object picking for drones, targets, obstacles, including overlapping-object click cycling.
- Read-only selection details for drones, targets, and obstacles, including raw object names, polygon vertices, and backend-provided projected area when available.
- Label visibility toggle and adaptive label/drone scaling. Label size starts at 100% and can be adjusted only while labels are visible.
- Drone path display cycle: 10, 20, 1, hidden, all.
- Camera modes: fit all, top view, follow selected drone, and roam along the selected drone path.
- Target rendering for fixed, moving, waypoint, circle, polygon.
- Obstacle rendering for point/circle, ellipse, polygon, including height=0 non-flyable semantics.
- Area coverage visualization with task-radius half-width semantics.
- Continuous green coverage footprint. Raw coverage points are no longer exposed as a selectable visual layer.
- Target motion paths remain hidden by default and no longer have a visible toggle in the final viewer.
- Frontend screenshot export: PNG/JPG/SVG/PDF/EPS.
- Demo mode without backend and backend-connected mode.

## Removed By Design

- Drone command controls: takeoff, land, hover, return home, charge, emergency, direct move, relative move, and perceived-radius mutation.
- Scene editing: add, duplicate, delete, move selected, save, save-as, discard, and snap-to-grid.
- Backend operation tools: session switch/reset/export/delete, current task inspection/check/marking, generic `/check/*`, advanced drone commands, and backend screenshot download.
- Frontend local obstacle precheck for map-click movement, because the corresponding movement UI has been removed.

## Partially Implemented

- Zoom slider: 2D has a horizontal discrete slider; 3D uses a right-side vertical quick zoom scale plus wheel and keyboard zoom, clamped to 40%-500%.
- View reset semantics: 2D return-home button resets origin when no drone is selected; 3D uses a separate fit/reset camera button.
- 2D task authoring templates: not implemented in the display-only viewer.

## Not Implemented By Design

- Replacing backend controller logic in frontend. The 3D viewer is a read-only visualization surface and does not mutate backend scene or drone state.
- Python/Pygame desktop packaging behavior, macOS reopen handling, and native window lifecycle.
