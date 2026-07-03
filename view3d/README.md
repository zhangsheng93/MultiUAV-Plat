# MultiUAV-Plat Web 3D Viewer

Standalone Three.js/Vite mission visualization viewer for MultiUAV-Plat, located in `view3d/`.

The viewer is primarily designed for live 3D mission visualization. It renders the current platform session as an interactive scene and can also run in frontend-only demo mode when the backend server is unavailable.

## What It Does

- Starts in backend live mode by default with `npm run dev`.
- Reads the current backend session from `GET /sessions/current/data` and renders it as a 3D scene.
- Falls back to a local Demo Mission when the backend is unavailable.
- Shows drones, targets, obstacles, altitude lines, path history, coverage, and mission statistics.
- Supports object selection with an information drawer, including object ID/name, raw polygon vertices, and backend-provided projected area when available.
- Provides camera controls: fit all, top-down view, and follow selected drone.
- Includes a minimap, scene statistics, status summary, label toggle, label size controls, trail mode, coverage display mode, quick zoom scale, and client-side screenshot export.
- Uses English as the default UI language and includes runtime language switching.
- May expose backend/session tools or editing controls for development and debugging in the current UI; use those tools only when you intend to modify or inspect backend state.

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

Start the 3D viewer:

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

If `VITE_API_KEY` is blank, requests use the backend's default access behavior. For live backend data, the viewer must be allowed to read:

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

The visualization path only requires the current session data endpoint for live rendering:

- `GET /sessions/current/data`

Development/debug panels may call additional session, screenshot, check, or drone-command endpoints when those controls are used. The client-side screenshot feature does not require a backend screenshot endpoint.

## Controls

- Left click: select a drone, target, or obstacle for inspection.
- Right click: clear the current selection.
- Mouse drag/wheel: orbit and zoom the camera within the 40%-500% scale range.
- Camera buttons: switch between fit-all, top-down, and follow-selected-drone views.
- Info button: open the details drawer for the selected object.
- Minimap click: center the view on the clicked location.
- Label toggle: show or hide object labels. Label size starts at 100%; `Size-` / `Size+`, `[` / `]`, and double-click reset only work while labels are visible.
- Trail mode: change path history visibility.
- Coverage mode: switch coverage visualization.
- Quick zoom scale: use the right-side vertical slider, mouse wheel, or `+` / `-`; double-click the bottom-right scale text to reset to 100%.
- Screenshot: export the current canvas image from the browser.

Keyboard shortcuts:

- `Esc`: clear selection.
- Arrow keys: pan the view.
- `1`: fit all.
- `2`: top view.
- `3`: follow selected drone.
- `+` / `-`: zoom in / out.
- `[` / `]`: decrease / increase label size when labels are visible.
- `R`: reset view.
- `L`: show / hide labels.
- `M`: show / hide minimap.
- `I`: show / hide the info panel.
