import './style.css';
import { fetchViewerState } from './api';
import { createDemoState } from './demoState';
import { ReplayState } from './replay';
import { ViewerScene } from './scene';
import { ViewerUI } from './ui';
import type { CameraMode, SelectionRef, ViewerState } from './types';
import type { Locale } from './i18n.ts';
import { nextLocale, normalizeLocale, t, translateDataValue } from './i18n.ts';
import { loadVisualScaleSettings, normalizeVisualScaleSettings, saveVisualScaleSettings } from './renderSettings.ts';
import { DEFAULT_LABELS_VISIBLE, getShortcutAction, getTrailModeValue, nextTrailMode, type ShortcutAction } from './viewerRuntime';

const sceneHost = document.querySelector<HTMLElement>('#sceneHost');
if (!sceneHost) throw new Error('Missing #sceneHost element');

let locale: Locale = normalizeLocale(window.localStorage.getItem('multiuav.locale'));
const ui = new ViewerUI(locale);
const scene = new ViewerScene(sceneHost);
scene.setLocale(locale);
let visualScaleSettings = loadVisualScaleSettings(window.localStorage);
scene.setVisualScaleSettings(visualScaleSettings);
ui.setVisualScaleSettings(visualScaleSettings);
const replay = new ReplayState();

if (import.meta.env.DEV) {
  const recorderWindow = window as unknown as { __viewerScene?: ViewerScene; __viewerUI?: ViewerUI };
  recorderWindow.__viewerScene = scene;
  recorderWindow.__viewerUI = ui;
}

let latestState: ViewerState | null = null;
let selected: SelectionRef | null = null;
let labelsVisible = DEFAULT_LABELS_VISIBLE;
let miniMapVisible = true;
let trailModeIndex = 0;
let pollingHandle: number | undefined;

const appRoot = document.querySelector<HTMLElement>('#app');
const infoToggle = document.querySelector<HTMLButtonElement>('#infoToggle');
const closeInfo = document.querySelector<HTMLButtonElement>('#closeInfo');
const cheatSheetToggle = document.querySelector<HTMLButtonElement>('#cheatSheetToggle');
const cheatSheetPanel = document.querySelector<HTMLElement>('#cheatSheetPanel');
const closeCheatSheet = document.querySelector<HTMLButtonElement>('#closeCheatSheet');

scene.setCallbacks(
  (selection) => {
    selected = selection;
    ui.updateSelection(selection);
    ui.setSelectionActivity(selection);
    setInfoDrawer(Boolean(selection));
    refreshMiniMap();
  },
  (point) => {
    ui.updateClickPosition(point);
  },
  (point) => {
    ui.updateClickPosition(point);
  },
  (scale) => {
    ui.setZoomScale(scale);
  }
);
scene.setDirectClickMove(false);

ui.bindScreenshot((format) => {
  void scene.exportScreenshot(format)
    .then(() => ui.setScreenshotActivity(format, true))
    .catch((error) => {
      ui.setScreenshotActivity(format, false);
      ui.setDisplayStatus({
        ok: false,
        message: translateDataValue(locale, error instanceof Error ? error.message : '截图导出失败')
      });
    });
});
ui.bindDisplayLayers((mode) => scene.setCoverageDisplayMode(mode));

ui.bindCamera((mode: CameraMode) => {
  handleCameraModeRequest(mode);
});
ui.bindTrail((length) => {
  replay.setTrailLength(length);
  scene.setTrailLength(replay.trailLength);
});
ui.bindTrailMode(() => {
  trailModeIndex = nextTrailMode(trailModeIndex);
  const length = getTrailModeValue(trailModeIndex);
  scene.setTrailLength(length);
  if (length > 1) {
    replay.setTrailLength(length);
    ui.trailLength.value = String(replay.trailLength);
    ui.trailLengthLabel.textContent = String(replay.trailLength);
  }
  ui.setTrailMode(trailModeIndex);
});
ui.bindLabelToggle(() => {
  labelsVisible = !labelsVisible;
  scene.setLabelsVisible(labelsVisible);
  ui.setLabelsVisible(labelsVisible);
  ui.setLabelsActivity(labelsVisible);
});
ui.bindVisualScale((settings) => {
  applyVisualScaleSettings(settings);
});
ui.bindLabelScaleStep((direction) => {
  if (!labelsVisible) return;
  if (direction === 0) {
    applyVisualScaleSettings({
      ...visualScaleSettings,
      label: 1
    });
    return;
  }
  stepLabelScale(direction);
});
ui.bindLanguage(() => {
  locale = nextLocale(locale);
  window.localStorage.setItem('multiuav.locale', locale);
  scene.setLocale(locale);
  ui.setLocale(locale);
  ui.setTrailMode(trailModeIndex);
  ui.setLabelsVisible(labelsVisible);
  ui.setLive(replay.live);
  if (latestState) ui.updateState(latestState);
});
ui.bindNavigation((action, value) => {
  if (action === 'zoom_scale') {
    scene.setZoomScale(typeof value === 'number' ? value : 1);
    refreshMiniMap();
    return;
  }
  handleShortcutAction(action);
});
ui.bindMiniMap((position) => {
  scene.setViewCenter(position);
  ui.updateClickPosition(position);
  refreshMiniMap();
});
ui.setTrailMode(trailModeIndex);
ui.setLabelsVisible(labelsVisible);
ui.setMiniMapVisible(miniMapVisible);
ui.setDisplayMode();

infoToggle?.addEventListener('click', () => {
  const open = !appRoot?.classList.contains('info-open');
  setInfoDrawer(open);
  if (open) setCheatSheet(false);
});
closeInfo?.addEventListener('click', () => setInfoDrawer(false));
closeCheatSheet?.addEventListener('click', () => setCheatSheet(false));
cheatSheetToggle?.addEventListener('click', (event) => {
  event.stopPropagation();
  const open = !appRoot?.classList.contains('cheat-sheet-open');
  setCheatSheet(open);
  if (open) setInfoDrawer(false);
});
cheatSheetPanel?.addEventListener('click', (event) => event.stopPropagation());

document.addEventListener('click', (event) => {
  if (!appRoot?.classList.contains('cheat-sheet-open')) return;
  const target = event.target;
  if (!(target instanceof Node)) return;
  if (cheatSheetToggle?.contains(target) || cheatSheetPanel?.contains(target)) return;
  setCheatSheet(false);
});

function handleShortcutAction(action: ShortcutAction): void {
  if (action === 'clear_selection') {
    if (scene.getCameraMode() === 'roam') {
      exitRoamMode();
      return;
    }
    clearActiveSelection();
  } else if (action === 'toggle_labels') {
    labelsVisible = !labelsVisible;
    scene.setLabelsVisible(labelsVisible);
    ui.setLabelsVisible(labelsVisible);
    ui.setLabelsActivity(labelsVisible);
  } else if (action === 'zoom_in') {
    scene.zoomBy(0.85);
  } else if (action === 'zoom_out') {
    scene.zoomBy(1.18);
  } else if (action === 'reset_view') {
    scene.resetView();
  } else if (action === 'toggle_minimap') {
    miniMapVisible = !miniMapVisible;
    ui.setMiniMapVisible(miniMapVisible);
    ui.setMiniMapActivity(miniMapVisible);
  } else if (action === 'toggle_info') {
    setInfoDrawer(!appRoot?.classList.contains('info-open'));
  } else if (action === 'label_size_down') {
    stepLabelScale(-1);
  } else if (action === 'label_size_up') {
    stepLabelScale(1);
  } else if (action === 'camera_top') {
    handleCameraModeRequest('top');
  } else if (action === 'camera_follow') {
    handleCameraModeRequest('follow');
  } else if (action === 'camera_roam') {
    handleCameraModeRequest('roam');
  } else if (action === 'roam_speed_up') {
    handleRoamSpeedStep(1);
  } else if (action === 'roam_speed_down') {
    handleRoamSpeedStep(-1);
  } else if (action === 'camera_fit') {
    handleCameraModeRequest('fit');
  } else if (action === 'pan_up') {
    scene.panBy(0, 24);
  } else if (action === 'pan_down') {
    scene.panBy(0, -24);
  } else if (action === 'pan_left') {
    scene.panBy(-24, 0);
  } else if (action === 'pan_right') {
    scene.panBy(24, 0);
  }
  refreshMiniMap();
}

function handleRoamSpeedStep(direction: -1 | 1): void {
  const result = scene.stepRoamSpeed(direction);
  if (result.ok && typeof result.multiplier === 'number') {
    const percent = Math.round(result.multiplier * 100);
    ui.setCameraActivity('roam', percent);
    return;
  }

  ui.setDisplayStatus({
    ok: false,
    message: translateDataValue(locale, result.message || '请求失败')
  });
}

function exitRoamMode(): void {
  applyCameraMode('fit');
  refreshMiniMap();
}

function handleCameraModeRequest(mode: CameraMode): void {
  if (mode === 'roam' && scene.getCameraMode() === 'roam') {
    exitRoamMode();
    return;
  }
  applyCameraMode(mode);
}

function applyCameraMode(mode: CameraMode): void {
  const result = scene.setCameraMode(mode);
  if (result.ok) {
    if (mode === 'follow' || mode === 'roam') {
      scene.setZoomScale(1);
    }
    ui.setCameraMode(mode);
    ui.setCameraActivity(
      mode,
      mode === 'roam' && typeof result.roamSpeedMultiplier === 'number'
        ? Math.round(result.roamSpeedMultiplier * 100)
        : undefined
    );
    return;
  }
  ui.setDisplayStatus({ ok: false, message: result.message || '请求失败' });
}

function clearActiveSelection(): void {
  selected = null;
  scene.setMoveMode(false);
  scene.clearSelection();
  ui.updateSelection(null);
  setInfoDrawer(false);
  setCheatSheet(false);
  ui.setSelectionClearedActivity();
  refreshMiniMap();
}

function setInfoDrawer(open: boolean): void {
  appRoot?.classList.toggle('info-open', open);
  if (infoToggle) infoToggle.classList.toggle('active', open);
}

function setCheatSheet(open: boolean): void {
  appRoot?.classList.toggle('cheat-sheet-open', open);
  if (cheatSheetToggle) {
    cheatSheetToggle.classList.toggle('active', open);
    cheatSheetToggle.setAttribute('aria-expanded', String(open));
  }
}

function applyVisualScaleSettings(settings: Partial<typeof visualScaleSettings>): void {
  visualScaleSettings = normalizeVisualScaleSettings(settings);
  saveVisualScaleSettings(window.localStorage, visualScaleSettings);
  ui.setVisualScaleSettings(visualScaleSettings);
  scene.setVisualScaleSettings(visualScaleSettings);
}

function stepLabelScale(direction: -1 | 1): void {
  if (!labelsVisible) return;
  applyVisualScaleSettings({
    ...visualScaleSettings,
    label: visualScaleSettings.label + direction * 0.25
  });
}

sceneHost.addEventListener('contextmenu', (event) => {
  event.preventDefault();
  clearActiveSelection();
  ui.setDisplayStatus({ ok: true, message: translateDataValue(locale, '已取消选择。') });
});

window.addEventListener('keydown', (event) => {
  const target = event.target;
  const isTextEditing = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement;
  const action = getShortcutAction(event.key);
  if (!action || isTextEditing) return;
  event.preventDefault();
  handleShortcutAction(action);
});

function refreshMiniMap(): void {
  ui.renderMiniMap(scene.getViewCenter());
}

async function refreshState(): Promise<void> {
  try {
    latestState = await fetchViewerState();
    ui.updateState(latestState);
    scene.renderState(latestState);
    ui.updateSelection(selected);
    refreshMiniMap();
  } catch (error) {
    const message = error instanceof Error ? error.message : t(locale, 'control.backendDisconnected');
    ui.setDisconnected(message);
    if (!latestState) {
      latestState = createDemoState(message);
      ui.updateState(latestState);
      scene.renderState(latestState);
      ui.updateSelection(selected);
      refreshMiniMap();
    }
  }
}

void refreshState();
pollingHandle = window.setInterval(() => {
  if (replay.live) void refreshState();
}, 3000);

document.querySelector('#liveToggle')?.addEventListener('click', () => {
  replay.setLive(!replay.live);
  ui.setLive(replay.live);
  if (replay.live) void refreshState();
});

window.addEventListener('beforeunload', () => {
  if (pollingHandle) window.clearInterval(pollingHandle);
  scene.dispose();
});
