# MultiUAV-Plat Web 3D Viewer

Standalone Three.js display-only visualization viewer for MultiUAV-Plat.

The current frontend is designed as the final visual rendering surface. It focuses on live mission visualization and removes drone control, scene editing, and backend mutation tools from the visible user flow.

## What It Does

- Starts in backend-first mode by default with `npm run dev`.
- Reads the current backend session and renders it as a 3D scene.
- Falls back to the local Demo Mission when the backend is unavailable.
- Shows drones, targets, obstacles, altitude lines, path history, and coverage.
- Supports read-only object selection with an information drawer, including object ID/name, raw polygon vertices, and backend-provided projected area when available.
- Provides camera controls: fit all, top-down view, follow selected drone, and roam along the selected drone path.
- Includes a minimap, scene statistics, status summary, label toggle, label size controls, trail mode, continuous coverage surface, quick zoom scale, and client-side screenshot export.
- Uses English as the default UI language.
- Does not send drone commands or edit backend scene data from the final visualization UI.

## Requirements

- Node.js 18 or newer.
- Optional for live data: the `server` FastAPI backend running on `http://127.0.0.1:8000`.

## Install

```bash
cd view3d
npm install
```

## Run

From the repository root, start the backend when you want live session data:

```bash
cd server
python main.py --api-only --host 127.0.0.1 --port 8000
```

From the repository root, start the 3D viewer:

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

Copy `.env.example` to `view3d/.env.development.local` if the backend is not using the default URL or if your backend requires an API key:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_API_KEY=
```

If `VITE_API_KEY` is blank, requests use the backend's default AGENT role behavior. For live backend data, the viewer must be allowed to read:

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

The final visualization UI only needs the current session data endpoint for live rendering:

- `GET /sessions/current/data`

The frontend screenshot feature is client-side and does not require a backend screenshot endpoint.

## Controls

- Left click: select a drone, target, or obstacle for read-only inspection.
- Right click: clear the current selection.
- Mouse drag/wheel: orbit and zoom the camera within the 40%-500% scale range.
- Camera buttons: switch between fit-all, top-down, chase follow, and chase path roam views.
- Info button: open the read-only details drawer for the selected object.
- Minimap click: center the view on the clicked location.
- Label toggle: show or hide object labels. Label size starts at 100%; `Size-` / `Size+`, `[` / `]`, and double-click reset only work while labels are visible.
- Trail mode: change path history visibility.
- Coverage is shown as a continuous surface by default.
- Quick zoom scale: use the right-side vertical slider, mouse wheel, or `+` / `-`; double-click the bottom-right scale text to reset to 100%. The scale also changes Follow and Roam chase-camera distance.
- Screenshot: export the current canvas image from the browser.

Keyboard shortcuts:

- `Esc`: clear selection.
- Arrow keys: pan the view.
- `1`: fit all.
- `2`: top view.
- `3`: follow selected drone from a raised rear chase view.
- `4`: roam the selected drone's full path from a raised rear chase view.
- `.` / `,`: speed up / slow down the current roam playback.
- `+` / `-`: zoom in / out.
- `[` / `]`: decrease / increase label size when labels are visible.
- `R`: reset view.
- `L`: show / hide labels.
- `M`: show / hide minimap.
- `I`: show / hide the info panel.

No commands are sent to drones from the final visualization UI.
