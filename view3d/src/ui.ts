import type { CameraMode, DroneState, ObstacleState, Position, SelectionRef, TargetState, ViewerState } from './types';
import { formatClickPosition, formatStatusSummary, getTrailModeLabel } from './viewerRuntime';
import { getMiniMapObstacleColor, getMiniMapObstacleShape, getMiniMapTargetShape, miniMapToWorld, resolveMiniMapBackingSize, resolveMiniMapBounds, worldToMiniMap, type MiniMapObjectShape, type MiniMapSize } from './miniMap';
import { getTargetVisualState, summarizeCoverage } from './taskVisuals';
import type { Locale } from './i18n.ts';
import { t, translateDataValue } from './i18n.ts';
import type { VisualScaleSettings } from './renderSettings.ts';
import { getTargetBaseColor } from './targetVisuals.ts';

type CameraHandler = (mode: CameraMode) => void;
type TrailHandler = (length: number) => void;
type VisualScaleHandler = (settings: VisualScaleSettings) => void;
type LabelScaleStepHandler = (direction: -1 | 0 | 1) => void;
type ToggleHandler = () => void;
type ScreenshotHandler = (format: string) => void;
type NavigationHandler = (action: 'pan_up' | 'pan_down' | 'pan_left' | 'pan_right' | 'reset_view' | 'zoom_scale', value?: number) => void;
type MiniMapClickHandler = (position: Position) => void;
type DisplayResult = {
  ok: boolean;
  message: string;
};

const MINI_MAP_DRONE_COLOR = '#22c55e';
const MINI_MAP_SELECTED_DRONE_COLOR = '#ef4444';

export class ViewerUI {
  readonly sessionName = document.querySelector<HTMLSpanElement>('#sessionName')!;
  private readonly appTitle = document.querySelector<HTMLElement>('#appTitle')!;
  readonly connectionStatus = document.querySelector<HTMLSpanElement>('#connectionStatus')!;
  readonly selectionTitle = document.querySelector<HTMLHeadingElement>('#selectionTitle')!;
  readonly selectionDetails = document.querySelector<HTMLDivElement>('#selectionDetails')!;
  readonly trailLength = document.querySelector<HTMLInputElement>('#trailLength')!;
  readonly trailLengthLabel = document.querySelector<HTMLSpanElement>('#trailLengthLabel')!;
  private readonly droneScale = document.querySelector<HTMLInputElement>('#droneScale')!;
  private readonly targetScale = document.querySelector<HTMLInputElement>('#targetScale')!;
  private readonly obstacleScale = document.querySelector<HTMLInputElement>('#obstacleScale')!;
  private readonly labelScale = document.querySelector<HTMLInputElement>('#labelScale')!;
  private readonly droneScaleLabel = document.querySelector<HTMLSpanElement>('#droneScaleLabel')!;
  private readonly targetScaleLabel = document.querySelector<HTMLSpanElement>('#targetScaleLabel')!;
  private readonly obstacleScaleLabel = document.querySelector<HTMLSpanElement>('#obstacleScaleLabel')!;
  private readonly labelScaleLabel = document.querySelector<HTMLSpanElement>('#labelScaleLabel')!;
  readonly trailModeToggle = document.querySelector<HTMLButtonElement>('#trailModeToggle')!;
  readonly labelToggle = document.querySelector<HTMLButtonElement>('#labelToggle')!;
  private readonly labelSizeDown = document.querySelector<HTMLButtonElement>('#labelSizeDown')!;
  private readonly labelSizeUp = document.querySelector<HTMLButtonElement>('#labelSizeUp')!;
  private readonly labelSizeValue = document.querySelector<HTMLSpanElement>('#labelSizeValue')!;
  private readonly quickZoomScale = document.querySelector<HTMLInputElement>('#quickZoomScale')!;
  readonly statusSummary = document.querySelector<HTMLSpanElement>('#statusSummary')!;
  readonly clickPosition = document.querySelector<HTMLSpanElement>('#clickPosition')!;
  private readonly zoomScaleStatus = document.querySelector<HTMLSpanElement>('#zoomScaleStatus')!;
  readonly miniMapPanel = document.querySelector<HTMLDivElement>('#miniMapPanel')!;
  readonly miniMapCanvas = document.querySelector<HTMLCanvasElement>('#miniMapCanvas')!;
  private readonly languageToggle = document.querySelector<HTMLButtonElement>('#languageToggle')!;
  private readonly cameraTop = document.querySelector<HTMLButtonElement>('#cameraTop')!;
  private readonly cameraFollow = document.querySelector<HTMLButtonElement>('#cameraFollow')!;
  private readonly cameraRoam = document.querySelector<HTMLButtonElement>('#cameraRoam')!;
  private readonly cameraFit = document.querySelector<HTMLButtonElement>('#cameraFit')!;
  private readonly cheatSheetToggle = document.querySelector<HTMLButtonElement>('#cheatSheetToggle')!;
  private readonly infoToggle = document.querySelector<HTMLButtonElement>('#infoToggle')!;
  private readonly screenshotFormat = document.querySelector<HTMLSelectElement>('#screenshotFormat')!;
  private readonly screenshotButton = document.querySelector<HTMLButtonElement>('#screenshotButton')!;
  private readonly trailLengthText = document.querySelector<HTMLSpanElement>('#trailLengthText')!;
  private readonly droneScaleText = document.querySelector<HTMLSpanElement>('#droneScaleText')!;
  private readonly targetScaleText = document.querySelector<HTMLSpanElement>('#targetScaleText')!;
  private readonly obstacleScaleText = document.querySelector<HTMLSpanElement>('#obstacleScaleText')!;
  private readonly labelScaleText = document.querySelector<HTMLSpanElement>('#labelScaleText')!;
  private readonly activityStatus = document.querySelector<HTMLSpanElement>('#activityStatus')!;
  private readonly liveToggle = document.querySelector<HTMLButtonElement>('#liveToggle')!;
  private state: ViewerState | null = null;
  private selection: SelectionRef | null = null;
  private miniMapVisible = true;
  private locale: Locale = 'zh-CN';
  private live = true;
  private lastClickPosition: Position | null = null;
  private lastZoomScale = 1;
  private lastActivityStatus = '';

  constructor(locale: Locale = 'zh-CN') {
    this.locale = locale;
    this.applyLocale();
  }

  bindCamera(handler: CameraHandler): void {
    this.cameraTop.addEventListener('click', () => handler('top'));
    this.cameraFollow.addEventListener('click', () => handler('follow'));
    this.cameraRoam.addEventListener('click', () => handler('roam'));
    this.cameraFit.addEventListener('click', () => handler('fit'));
  }

  bindLanguage(handler: ToggleHandler): void {
    this.languageToggle.addEventListener('click', handler);
  }

  bindScreenshot(handler: ScreenshotHandler): void {
    this.screenshotButton.addEventListener('click', () => handler(this.screenshotFormat.value));
  }

  bindTrail(handler: TrailHandler): void {
    this.trailLength.addEventListener('input', () => {
      const value = Number(this.trailLength.value);
      this.trailLengthLabel.textContent = String(value);
      handler(value);
    });
  }

  bindVisualScale(handler: VisualScaleHandler): void {
    const bind = (input: HTMLInputElement, label: HTMLSpanElement) => {
      input.addEventListener('input', () => {
        label.textContent = `${input.value}%`;
        handler(this.getVisualScaleSettings());
      });
    };
    bind(this.droneScale, this.droneScaleLabel);
    bind(this.targetScale, this.targetScaleLabel);
    bind(this.obstacleScale, this.obstacleScaleLabel);
    bind(this.labelScale, this.labelScaleLabel);
  }

  bindTrailMode(handler: ToggleHandler): void {
    this.trailModeToggle.addEventListener('click', handler);
  }

  bindLabelToggle(handler: ToggleHandler): void {
    this.labelToggle.addEventListener('click', handler);
  }

  bindLabelScaleStep(handler: LabelScaleStepHandler): void {
    this.labelSizeDown.addEventListener('click', () => handler(-1));
    this.labelSizeUp.addEventListener('click', () => handler(1));
    this.labelSizeValue.addEventListener('dblclick', () => {
      if (this.labelSizeValue.getAttribute('aria-disabled') === 'true') return;
      handler(0);
    });
  }

  bindNavigation(handler: NavigationHandler): void {
    document.querySelector('#panUp')?.addEventListener('click', () => handler('pan_up'));
    document.querySelector('#panDown')?.addEventListener('click', () => handler('pan_down'));
    document.querySelector('#panLeft')?.addEventListener('click', () => handler('pan_left'));
    document.querySelector('#panRight')?.addEventListener('click', () => handler('pan_right'));
    document.querySelector('#resetView')?.addEventListener('click', () => handler('reset_view'));
    this.quickZoomScale.addEventListener('input', () => handler('zoom_scale', Number(this.quickZoomScale.value) / 100));
    this.zoomScaleStatus.addEventListener('dblclick', () => handler('zoom_scale', 1));
  }

  bindMiniMap(handler: MiniMapClickHandler): void {
    this.miniMapCanvas.addEventListener('click', (event) => {
      if (!this.state) return;
      const rect = this.miniMapCanvas.getBoundingClientRect();
      const point = {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top
      };
      handler(miniMapToWorld(point, resolveMiniMapBounds(this.state), this.getMiniMapSize()));
    });
  }

  updateState(state: ViewerState): void {
    this.state = state;
    this.statusSummary.textContent = formatStatusSummary(state, this.locale);
    if (state.session && state.status !== 'no_current_session') {
      this.sessionName.textContent = `${translateDataValue(this.locale, state.session.name)} · ${t(this.locale, 'session.summary', {
        drones: state.drones.length,
        targets: state.targets.length,
        obstacles: state.obstacles.length
      })}`;
      this.connectionStatus.textContent = state.status === 'demo' ? 'Demo' : t(this.locale, 'status.connected');
      this.connectionStatus.className = state.status === 'demo' ? 'status warning' : 'status connected';
    } else {
      this.sessionName.textContent = translateDataValue(this.locale, state.message || t(this.locale, 'status.warningNoSession'));
      this.connectionStatus.textContent = t(this.locale, 'status.noSession');
      this.connectionStatus.className = 'status warning';
    }
    this.updateSelection(this.selection);
  }

  setDisconnected(message: string): void {
    this.connectionStatus.textContent = t(this.locale, 'status.disconnected');
    this.connectionStatus.className = 'status disconnected';
    this.sessionName.textContent = translateDataValue(this.locale, message);
    this.statusSummary.textContent = formatStatusSummary(this.state, this.locale);
  }

  updateSelection(selection: SelectionRef | null): void {
    this.selection = selection;
    if (!selection || !this.state) {
      this.selectionTitle.textContent = t(this.locale, 'selection.none.title');
      this.selectionDetails.textContent = t(this.locale, 'selection.none.detail');
      return;
    }
    if (selection.kind === 'drone') {
      const drone = this.state.drones.find((item) => item.id === selection.id);
      if (drone) this.renderDrone(drone);
    } else if (selection.kind === 'target') {
      const target = this.state.targets.find((item) => item.id === selection.id);
      if (target) this.renderTarget(target);
    } else {
      const obstacle = this.state.obstacles.find((item) => item.id === selection.id);
      if (obstacle) this.renderObstacle(obstacle);
    }
  }

  getVisualScaleSettings(): VisualScaleSettings {
    return {
      drone: Number(this.droneScale.value) / 100,
      target: Number(this.targetScale.value) / 100,
      obstacle: Number(this.obstacleScale.value) / 100,
      label: Number(this.labelScale.value) / 100
    };
  }

  setTrailMode(index: number): void {
    this.trailModeToggle.textContent = getTrailModeLabel(index, this.locale);
  }

  setLabelsVisible(visible: boolean): void {
    this.labelToggle.textContent = visible ? t(this.locale, 'footer.labelsOn') : t(this.locale, 'footer.labelsOff');
    this.labelToggle.title = t(this.locale, 'footer.labelsTitle');
    this.labelToggle.classList.toggle('active', visible);
    this.labelSizeDown.disabled = !visible;
    this.labelSizeUp.disabled = !visible;
    this.labelSizeValue.setAttribute('aria-disabled', String(!visible));
    this.labelSizeValue.classList.toggle('disabled', !visible);
  }

  setCameraMode(mode: CameraMode): void {
    this.cameraRoam.classList.toggle('active', mode === 'roam');
  }

  setVisualScaleSettings(settings: VisualScaleSettings): void {
    this.droneScale.value = String(Math.round(settings.drone * 100));
    this.targetScale.value = String(Math.round(settings.target * 100));
    this.obstacleScale.value = String(Math.round(settings.obstacle * 100));
    this.labelScale.value = String(Math.round(settings.label * 100));
    this.droneScaleLabel.textContent = `${this.droneScale.value}%`;
    this.targetScaleLabel.textContent = `${this.targetScale.value}%`;
    this.obstacleScaleLabel.textContent = `${this.obstacleScale.value}%`;
    this.labelScaleLabel.textContent = `${this.labelScale.value}%`;
    this.labelSizeValue.textContent = t(this.locale, 'footer.labelSizeValue', { value: this.labelScale.value });
  }

  setLive(live: boolean): void {
    this.live = live;
    this.liveToggle.textContent = live ? t(this.locale, 'footer.live') : t(this.locale, 'footer.paused');
  }

  setLocale(locale: Locale): void {
    this.locale = locale;
    this.applyLocale();
    if (this.state) this.updateState(this.state);
    else this.updateSelection(this.selection);
  }

  setMiniMapVisible(visible: boolean): void {
    this.miniMapVisible = visible;
    this.miniMapPanel.classList.toggle('hidden', !visible);
  }

  updateClickPosition(position: Position | null): void {
    this.lastClickPosition = position;
    this.clickPosition.textContent = formatClickPosition(position, this.locale);
  }

  setZoomScale(scale: number): void {
    const percent = Math.max(40, Math.min(500, Math.round(scale * 100)));
    this.lastZoomScale = percent / 100;
    this.quickZoomScale.value = String(percent);
    this.zoomScaleStatus.textContent = t(this.locale, 'footer.zoomScale', { value: String(percent).padStart(3, ' ') });
  }

  setSelectionActivity(selection: SelectionRef | null): void {
    const resolved = selection ? this.resolveSelectionActivity(selection) : null;
    this.setActivityText(resolved ? t(this.locale, 'activity.selection', resolved) : '');
  }

  setCameraActivity(mode: CameraMode, roamSpeedPercent?: number): void {
    if (mode === 'roam' && typeof roamSpeedPercent === 'number') {
      this.setActivityText(t(this.locale, 'activity.cameraChangedWithRoamSpeed', {
        mode: t(this.locale, `camera.${mode}`),
        speed: roamSpeedPercent
      }));
      return;
    }
    this.setActivityText(t(this.locale, 'activity.cameraChanged', { mode: t(this.locale, `camera.${mode}`) }));
  }

  setSelectionClearedActivity(): void {
    this.setActivityText(t(this.locale, 'activity.selectionCleared'));
  }

  setLabelsActivity(visible: boolean): void {
    this.setActivityText(t(this.locale, visible ? 'activity.labelsShown' : 'activity.labelsHidden'));
  }

  setMiniMapActivity(visible: boolean): void {
    this.setActivityText(t(this.locale, visible ? 'activity.minimapShown' : 'activity.minimapHidden'));
  }

  setScreenshotActivity(format: string, ok = true): void {
    this.setActivityText(ok
      ? t(this.locale, 'activity.screenshotSaved', { format: format.toUpperCase() })
      : t(this.locale, 'activity.screenshotFailed'));
  }

  renderMiniMap(viewCenter: Position | null): void {
    if (!this.state || !this.miniMapVisible) return;
    const ctx = this.miniMapCanvas.getContext('2d');
    if (!ctx) return;

    const size = this.prepareMiniMapCanvas(ctx);
    const bounds = resolveMiniMapBounds(this.state);
    ctx.clearRect(0, 0, size.width, size.height);
    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(0, 0, size.width, size.height);
    ctx.strokeStyle = '#cbd5e1';
    ctx.strokeRect(0.5, 0.5, size.width - 1, size.height - 1);

    ctx.strokeStyle = '#94a3b8';
    ctx.lineWidth = 1;
    const bottomLeft = worldToMiniMap({ x: bounds.minX, y: bounds.minY, z: 0 }, bounds, size);
    const topRight = worldToMiniMap({ x: bounds.maxX, y: bounds.maxY, z: 0 }, bounds, size);
    ctx.strokeRect(bottomLeft.x, topRight.y, topRight.x - bottomLeft.x, bottomLeft.y - topRight.y);

    for (const obstacle of this.state.obstacles) {
      const selected = this.selection?.kind === 'obstacle' && this.selection.id === obstacle.id;
      this.drawMiniMapObject(ctx, obstacle.position, getMiniMapObstacleShape(obstacle), bounds, size, this.formatHexColor(getMiniMapObstacleColor(obstacle)), selected);
    }
    for (const target of this.state.targets) {
      const selected = this.selection?.kind === 'target' && this.selection.id === target.id;
      this.drawMiniMapObject(ctx, target.position, getMiniMapTargetShape(target), bounds, size, this.formatHexColor(getTargetBaseColor(target.type)), selected);
    }
    for (const drone of this.state.drones) {
      const point = worldToMiniMap(drone.position, bounds, size);
      const selected = this.selection?.kind === 'drone' && this.selection.id === drone.id;
      ctx.fillStyle = selected ? MINI_MAP_SELECTED_DRONE_COLOR : MINI_MAP_DRONE_COLOR;
      ctx.beginPath();
      ctx.arc(point.x, point.y, selected ? 4.5 : 3.5, 0, Math.PI * 2);
      ctx.fill();
    }

    if (viewCenter) {
      const center = worldToMiniMap(viewCenter, bounds, size);
      ctx.strokeStyle = '#16a34a';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(center.x - 6, center.y);
      ctx.lineTo(center.x + 6, center.y);
      ctx.moveTo(center.x, center.y - 6);
      ctx.lineTo(center.x, center.y + 6);
      ctx.stroke();
    }
  }

  setDisplayStatus(result: DisplayResult): void {
    this.setActivityText(translateDataValue(this.locale, result.message));
  }

  setDisplayMode(): void {
    this.setActivityText(this.lastActivityStatus);
  }

  private renderDrone(drone: DroneState): void {
    this.selectionTitle.textContent = `${t(this.locale, 'entity.drone')} · ${drone.name}`;
    this.selectionDetails.innerHTML = `
      <dl>
        <dt>${t(this.locale, 'field.id')}</dt><dd>${drone.id}</dd>
        <dt>${t(this.locale, 'field.name')}</dt><dd>${translateDataValue(this.locale, drone.name)}</dd>
        <dt>${t(this.locale, 'field.status')}</dt><dd>${translateDataValue(this.locale, drone.status)}</dd>
        <dt>${t(this.locale, 'field.model')}</dt><dd>${translateDataValue(this.locale, drone.model || '-')}</dd>
        <dt>${t(this.locale, 'field.position')}</dt><dd>${this.formatPosition(drone.position)}</dd>
        <dt>${t(this.locale, 'field.heading')}</dt><dd>${this.formatMaybeNumber(drone.heading, '°')}</dd>
        <dt>${t(this.locale, 'field.speed')}</dt><dd>${this.formatMaybeNumber(drone.speed)}</dd>
        <dt>${t(this.locale, 'field.battery')}</dt><dd>${this.formatMaybeNumber(drone.battery_level, '%')}</dd>
        <dt>${t(this.locale, 'field.maxSpeed')}</dt><dd>${this.formatMaybeNumber(drone.max_speed)}</dd>
        <dt>${t(this.locale, 'field.maxAltitude')}</dt><dd>${this.formatMaybeNumber(drone.max_altitude)}</dd>
        <dt>${t(this.locale, 'field.batteryCapacity')}</dt><dd>${this.formatMaybeNumber(drone.battery_capacity)}</dd>
        <dt>${t(this.locale, 'field.perceivedRadius')}</dt><dd>${this.formatMaybeNumber(drone.perceived_radius)}</dd>
        <dt>${t(this.locale, 'field.taskRadius')}</dt><dd>${this.formatMaybeNumber(drone.task_radius)}</dd>
        <dt>${t(this.locale, 'field.home')}</dt><dd>${drone.home_position ? this.formatPosition(drone.home_position) : '-'}</dd>
      </dl>
    `;
  }

  private renderTarget(target: TargetState): void {
    const visual = this.state ? getTargetVisualState(target, this.state, this.locale) : null;
    const coverage = this.state ? summarizeCoverage(this.state, target.id) : null;
    this.selectionTitle.textContent = `${t(this.locale, 'entity.target')} · ${target.name}`;
    this.selectionDetails.innerHTML = `
      <dl>
        <dt>${t(this.locale, 'field.id')}</dt><dd>${target.id}</dd>
        <dt>${t(this.locale, 'field.name')}</dt><dd>${translateDataValue(this.locale, target.name)}</dd>
        <dt>${t(this.locale, 'field.type')}</dt><dd>${translateDataValue(this.locale, target.type)}</dd>
        <dt>${t(this.locale, 'field.position')}</dt><dd>${this.formatPosition(target.position)}</dd>
        <dt>${t(this.locale, 'field.radius')}</dt><dd>${this.formatMaybeNumber(target.radius)}</dd>
        <dt>${t(this.locale, 'field.completed')}</dt><dd>${t(this.locale, target.is_reached ? 'value.yes' : 'value.no')}</dd>
        <dt>${t(this.locale, 'field.movementMode')}</dt><dd>${translateDataValue(this.locale, target.movement_mode || '-')}</dd>
        <dt>${t(this.locale, 'field.trackingStatus')}</dt><dd>${translateDataValue(this.locale, target.tracking_status || '-')}</dd>
        <dt>${t(this.locale, 'field.velocity')}</dt><dd>${target.velocity ? this.formatPosition(target.velocity) : '-'}</dd>
        <dt>${t(this.locale, 'field.pathPoints')}</dt><dd>${target.moving_path?.length ?? 0}</dd>
        <dt>${t(this.locale, 'field.coverageProgress')}</dt><dd>${coverage?.progressPercentage !== null && coverage?.progressPercentage !== undefined ? `${coverage.progressPercentage}%` : '-'}</dd>
        <dt>${t(this.locale, 'field.taskStatus')}</dt><dd>${visual ? translateDataValue(this.locale, visual.label) : '-'}</dd>
        <dt>${t(this.locale, 'field.charge')}</dt><dd>${this.formatMaybeNumber(target.charge_amount)}</dd>
        <dt>${t(this.locale, 'field.vertices')}</dt><dd>${this.formatVertices(target.vertices)}</dd>
        <dt>${t(this.locale, 'field.area')}</dt><dd>${this.formatArea(target.area)}</dd>
        <dt>${t(this.locale, 'field.description')}</dt><dd>${translateDataValue(this.locale, target.description || '-')}</dd>
      </dl>
    `;
  }

  private renderObstacle(obstacle: ObstacleState): void {
    const geometryRows = obstacle.type === 'ellipse'
      ? `
        <dt>${t(this.locale, 'field.width')}</dt><dd>${this.formatMaybeNumber(obstacle.width)}</dd>
        <dt>${t(this.locale, 'field.length')}</dt><dd>${this.formatMaybeNumber(obstacle.length)}</dd>
      `
      : `<dt>${t(this.locale, 'field.radius')}</dt><dd>${this.formatMaybeNumber(obstacle.radius)}</dd>`;
    this.selectionTitle.textContent = `${t(this.locale, 'entity.obstacle')} · ${obstacle.name}`;
    this.selectionDetails.innerHTML = `
      <dl>
        <dt>${t(this.locale, 'field.id')}</dt><dd>${obstacle.id}</dd>
        <dt>${t(this.locale, 'field.name')}</dt><dd>${translateDataValue(this.locale, obstacle.name)}</dd>
        <dt>${t(this.locale, 'field.type')}</dt><dd>${translateDataValue(this.locale, obstacle.type)}</dd>
        <dt>${t(this.locale, 'field.position')}</dt><dd>${this.formatPosition(obstacle.position)}</dd>
        <dt>${t(this.locale, 'field.height')}</dt><dd>${obstacle.height === 0 ? t(this.locale, 'value.notFlyable') : this.formatMaybeNumber(obstacle.height)}</dd>
        ${geometryRows}
        <dt>${t(this.locale, 'field.vertices')}</dt><dd>${this.formatVertices(obstacle.vertices)}</dd>
        <dt>${t(this.locale, 'field.area')}</dt><dd>${this.formatArea(obstacle.area)}</dd>
        <dt>${t(this.locale, 'field.description')}</dt><dd>${translateDataValue(this.locale, obstacle.description || '-')}</dd>
      </dl>
    `;
  }

  private formatVertices(vertices: Array<Partial<Position>> | undefined): string {
    if (!vertices?.length) return '-';
    return vertices.map((vertex, index) => {
      const x = this.formatVertexCoordinate(vertex.x);
      const y = this.formatVertexCoordinate(vertex.y);
      const z = this.formatVertexCoordinate(vertex.z ?? 0);
      return `${index + 1}. (${x}, ${y}, ${z})`;
    }).join('<br>');
  }

  private formatVertexCoordinate(value: unknown): string {
    const numericValue = typeof value === 'number' ? value : Number(value);
    if (!Number.isFinite(numericValue)) return '-';
    return String(Math.round(numericValue * 100) / 100);
  }

  private formatArea(area: number | undefined): string {
    if (typeof area !== 'number' || !Number.isFinite(area)) return '-';
    return String(Math.round(area * 100) / 100);
  }

  private formatPosition(position: Position): string {
    return `x=${position.x.toFixed(1)}, y=${position.y.toFixed(1)}, z=${position.z.toFixed(1)}`;
  }

  private formatMaybeNumber(value: number | undefined, suffix = ''): string {
    if (typeof value !== 'number' || !Number.isFinite(value)) return '-';
    return `${Math.round(value * 100) / 100}${suffix}`;
  }

  private applyLocale(): void {
    document.documentElement.lang = this.locale;
    this.appTitle.textContent = t(this.locale, 'app.title');
    this.languageToggle.textContent = t(this.locale, 'language.toggle');
    this.cameraTop.textContent = t(this.locale, 'camera.top');
    this.cameraFollow.textContent = t(this.locale, 'camera.follow');
    this.cameraRoam.textContent = t(this.locale, 'camera.roam');
    this.cameraFit.textContent = t(this.locale, 'camera.fit');
    this.cheatSheetToggle.textContent = t(this.locale, 'topbar.cheatSheet');
    this.infoToggle.textContent = t(this.locale, 'topbar.info');
    this.setAriaLabel('#cheatSheetPanel', t(this.locale, 'cheat.title'));
    this.setText('#cheatSheetTitle', t(this.locale, 'cheat.title'));
    this.setText('#cheatClear', t(this.locale, 'cheat.clear'));
    this.setText('#cheatPan', t(this.locale, 'cheat.pan'));
    this.setText('#cheatCameraTop', t(this.locale, 'cheat.cameraTop'));
    this.setText('#cheatCameraFollow', t(this.locale, 'cheat.cameraFollow'));
    this.setText('#cheatCameraRoam', t(this.locale, 'cheat.cameraRoam'));
    this.setText('#cheatCameraFit', t(this.locale, 'cheat.cameraFit'));
    this.setText('#cheatRoamSpeed', t(this.locale, 'cheat.roamSpeed'));
    this.setText('#cheatZoom', t(this.locale, 'cheat.zoom'));
    this.setText('#cheatReset', t(this.locale, 'cheat.reset'));
    this.setText('#cheatLabels', t(this.locale, 'cheat.labels'));
    this.setText('#cheatMinimap', t(this.locale, 'cheat.minimap'));
    this.setText('#cheatInfo', t(this.locale, 'cheat.info'));
    this.setTitle('#closeCheatSheet', t(this.locale, 'cheat.close'));
    this.screenshotButton.textContent = t(this.locale, 'screenshot.capture');
    this.screenshotFormat.title = t(this.locale, 'screenshot.format');
    this.setAriaLabel('.nav-overlay', t(this.locale, 'nav.label'));
    this.setTitle('#panUp', t(this.locale, 'nav.panUp'));
    this.setTitle('#panDown', t(this.locale, 'nav.panDown'));
    this.setTitle('#panLeft', t(this.locale, 'nav.panLeft'));
    this.setTitle('#panRight', t(this.locale, 'nav.panRight'));
    this.setTitle('#resetView', t(this.locale, 'nav.reset'));
    this.setAriaLabel('.zoom-rail', t(this.locale, 'nav.zoomScale'));
    this.setTitle('.zoom-rail', t(this.locale, 'nav.zoomScale'));
    this.setLive(this.live);
    this.trailLengthText.textContent = t(this.locale, 'footer.trailLength');
    this.droneScaleText.textContent = t(this.locale, 'footer.droneScale');
    this.targetScaleText.textContent = t(this.locale, 'footer.targetScale');
    this.obstacleScaleText.textContent = t(this.locale, 'footer.obstacleScale');
    this.labelScaleText.textContent = t(this.locale, 'footer.labelScale');
    this.labelSizeDown.textContent = t(this.locale, 'footer.labelSizeDown');
    this.labelSizeUp.textContent = t(this.locale, 'footer.labelSizeUp');
    this.labelSizeDown.title = t(this.locale, 'footer.labelSizeDownTitle');
    this.labelSizeUp.title = t(this.locale, 'footer.labelSizeUpTitle');
    this.labelSizeValue.title = t(this.locale, 'footer.labelSizeResetTitle');
    this.setActivityText(this.lastActivityStatus);
    this.clickPosition.textContent = formatClickPosition(this.lastClickPosition, this.locale);
    this.setZoomScale(this.lastZoomScale);
    this.labelToggle.textContent = this.labelToggle.classList.contains('active') ? t(this.locale, 'footer.labelsOn') : t(this.locale, 'footer.labelsOff');
    this.labelToggle.title = t(this.locale, 'footer.labelsTitle');
    this.trailModeToggle.textContent = getTrailModeLabel(0, this.locale);
    if (!this.state) {
      this.selectionTitle.textContent = t(this.locale, 'selection.none.title');
      this.selectionDetails.textContent = t(this.locale, 'selection.none.detail');
      this.statusSummary.textContent = formatStatusSummary(null, this.locale);
      this.clickPosition.textContent = formatClickPosition(null, this.locale);
    }
  }

  private setText(selector: string, value: string): void {
    const element = document.querySelector<HTMLElement>(selector);
    if (element) element.textContent = value;
  }

  private setTitle(selector: string, value: string): void {
    const element = document.querySelector<HTMLElement>(selector);
    if (element) element.title = value;
  }

  private setAriaLabel(selector: string, value: string): void {
    const element = document.querySelector<HTMLElement>(selector);
    if (element) element.setAttribute('aria-label', value);
  }

  private resolveSelectionActivity(selection: SelectionRef): { kind: string; name: string; id: string } | null {
    if (!this.state) return null;
    if (selection.kind === 'drone') {
      const drone = this.state.drones.find((item) => item.id === selection.id);
      return drone ? { kind: t(this.locale, 'entity.drone'), name: translateDataValue(this.locale, drone.name), id: drone.id } : null;
    }
    if (selection.kind === 'target') {
      const target = this.state.targets.find((item) => item.id === selection.id);
      return target ? { kind: t(this.locale, 'entity.target'), name: translateDataValue(this.locale, target.name), id: target.id } : null;
    }
    const obstacle = this.state.obstacles.find((item) => item.id === selection.id);
    return obstacle ? { kind: t(this.locale, 'entity.obstacle'), name: translateDataValue(this.locale, obstacle.name), id: obstacle.id } : null;
  }

  private setActivityText(text: string): void {
    this.lastActivityStatus = text;
    this.activityStatus.textContent = text;
    this.activityStatus.classList.toggle('hidden', !text);
  }

  private getMiniMapSize(): MiniMapSize {
    const rect = this.miniMapCanvas.getBoundingClientRect();
    return {
      width: Math.max(1, Math.round(rect.width || this.miniMapCanvas.clientWidth || 220)),
      height: Math.max(1, Math.round(rect.height || this.miniMapCanvas.clientHeight || 160)),
      padding: 10
    };
  }

  private prepareMiniMapCanvas(ctx: CanvasRenderingContext2D): MiniMapSize {
    const size = this.getMiniMapSize();
    const backingSize = resolveMiniMapBackingSize(size, window.devicePixelRatio);
    if (this.miniMapCanvas.width !== backingSize.width || this.miniMapCanvas.height !== backingSize.height) {
      this.miniMapCanvas.width = backingSize.width;
      this.miniMapCanvas.height = backingSize.height;
    }
    ctx.setTransform(backingSize.pixelRatio, 0, 0, backingSize.pixelRatio, 0, 0);
    return size;
  }

  private drawMiniMapObject(
    ctx: CanvasRenderingContext2D,
    origin: Position,
    shape: MiniMapObjectShape,
    bounds: ReturnType<typeof resolveMiniMapBounds>,
    size: MiniMapSize,
    color: string,
    selected: boolean
  ): void {
    ctx.save();
    ctx.fillStyle = color;
    ctx.strokeStyle = selected ? MINI_MAP_SELECTED_DRONE_COLOR : color;
    ctx.lineWidth = selected ? 2 : 1;

    if (shape.kind === 'polygon' && shape.vertices.length >= 3) {
      ctx.beginPath();
      shape.vertices.forEach((vertex, index) => {
        const point = worldToMiniMap(vertex, bounds, size);
        if (index === 0) ctx.moveTo(point.x, point.y);
        else ctx.lineTo(point.x, point.y);
      });
      ctx.closePath();
      ctx.globalAlpha = 0.45;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.stroke();
      ctx.restore();
      return;
    }

    let radiusX: number;
    let radiusY: number;
    if (shape.kind === 'ellipse') {
      radiusX = shape.radiusX;
      radiusY = shape.radiusY;
    } else {
      const radius = shape.kind === 'polygon' ? shape.fallbackRadius : shape.radius;
      radiusX = radius;
      radiusY = radius;
    }
    const center = worldToMiniMap(origin, bounds, size);
    const rx = Math.max(3, Math.abs(worldToMiniMap({ x: origin.x + radiusX, y: origin.y, z: origin.z }, bounds, size).x - center.x));
    const ry = Math.max(3, Math.abs(worldToMiniMap({ x: origin.x, y: origin.y + radiusY, z: origin.z }, bounds, size).y - center.y));
    ctx.beginPath();
    ctx.ellipse(center.x, center.y, rx, ry, 0, 0, Math.PI * 2);
    ctx.globalAlpha = 0.45;
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.stroke();
    ctx.restore();
  }

  private formatHexColor(color: number): string {
    return `#${color.toString(16).padStart(6, '0')}`;
  }
}
