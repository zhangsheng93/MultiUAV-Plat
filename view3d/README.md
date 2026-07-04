# MultiUAV-Plat Web 3D Viewer

Standalone Three.js/Vite mission visualization viewer for MultiUAV-Plat, located in `view3d/`.

Current package version: `0.1.0`.

The viewer is primarily designed for live 3D mission visualization. It renders the current platform session as an interactive scene, falls back to frontend-only demo data when the backend is unavailable, and keeps optional control, session, editor, check, and backend screenshot tools for development or operator workflows.

## What It Does

- Starts in backend-first mode by default with `npm run dev`.
- Reads the current backend session from `GET /sessions/current/data` and renders it as a 3D scene.
- Falls back to the local Demo Mission when the backend is unavailable.
- Shows drones, targets, obstacles, altitude lines, path history, coverage, and mission statistics.
- Supports object selection with an information drawer, including object ID/name, raw polygon vertices, and backend-provided projected area when available.
- Provides camera controls: fit all, top-down view, follow selected drone, and roam along a selected drone path.
- Includes a minimap, scene statistics, status summary, label toggle, label size controls, trail mode, coverage display mode, quick zoom scale, and client-side screenshot export.
- Uses English as the default UI language and includes runtime Chinese/English switching.
- Includes optional backend/session tools, task/check inspection, backend screenshot download, drone command controls, and scene editing controls for development or controlled operation. These tools may modify backend state when used.

## Requirements

- Node.js 18 or newer.
- Optional for live data: the `server/` FastAPI backend running on `http://127.0.0.1:8000`.

## Install

```bash
cd view3d
npm install
```

## Run

Start the backend first when you want live session data:

```bash
cd server
python main.py
```

Start the 3D viewer in another terminal:

```bash
cd view3d
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

`npm run dev` runs Vite with backend mode enabled:

```bash
VITE_VIEWER_DATA_SOURCE=backend vite --host 127.0.0.1 --port 5173
```

If the backend is unavailable or `GET /sessions/current/data` fails, the viewer automatically switches to the local Demo Mission so the page still renders.

For explicit frontend-only demo mode:

```bash
npm run dev:demo
```

## Configuration

Create `view3d/.env.development.local` if the backend is not using the default URL or if your backend requires an API key:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_API_KEY=
```

When `VITE_API_KEY` is set, the viewer sends it as the `X-API-Key` header. If it is blank, requests rely on the backend's default access behavior. For live backend data, the viewer must be allowed to read:

```text
GET /sessions/current/data
```

## Build

```bash
npm run build
```

## Test

```bash
npm test
```

## Backend Contract

The main visualization path only needs the current session data endpoint for live rendering:

- `GET /sessions/current/data`

Optional development and operator tools may call additional session, task, check, drone-command, save/edit, and backend screenshot endpoints when those controls are used. The client-side screenshot feature does not require a backend screenshot endpoint.

## Controls

- Left click: select a drone, target, or obstacle for inspection.
- Right click: clear the current selection.
- Mouse drag/wheel: orbit and zoom the camera within the 40%-500% scale range.
- Camera buttons: switch between fit-all, top-down, chase follow, and chase path roam views.
- Info button: open the details drawer for the selected object.
- Minimap click: center the view on the clicked location.
- Label toggle: show or hide object labels. Label size starts at 100%; `Size-` / `Size+`, `[` / `]`, and double-click reset only work while labels are visible.
- Trail mode: change path history visibility.
- Coverage mode: switch coverage visualization.
- Quick zoom scale: use the right-side vertical slider, mouse wheel, or `+` / `-`; double-click the bottom-right scale text to reset to 100%. The scale also changes Follow and Roam chase-camera distance.
- Screenshot: export the current canvas image from the browser.
- Language button: switch between English and Chinese UI text.
- Optional control/editor/backend tool panels: send drone commands, move selected drones, edit session objects, inspect tasks/checks, and call backend screenshot/session APIs when intentionally operating against the backend.

Keyboard shortcuts:

- `Esc`: clear selection.
- Arrow keys: pan the view.
- `1`: fit all.
- `2`: top view.
- `3`: follow selected drone from a raised rear chase view.
- `4`: roam the selected drone's full path from a raised rear chase view.
- `+` / `-`: zoom in / out.
- `[` / `]`: decrease / increase label size when labels are visible.
- `R`: reset view.
- `L`: show / hide labels.
- `M`: show / hide minimap.
- `I`: show / hide the info panel.
