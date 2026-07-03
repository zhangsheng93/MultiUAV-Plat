import type { CameraMode, CommandResult, DroneState, ObstacleState, Position, SelectionRef, TargetState, ViewerState } from './types';
import { getCommandAvailability } from './uiState';
import { formatClickPosition, formatStatusSummary, getTrailModeLabel } from './viewerRuntime';
import { miniMapToWorld, resolveMiniMapBounds, worldToMiniMap } from './miniMap';
import { getTargetVisualState, summarizeCoverage } from './taskVisuals';
import type { RelativeMoveAction } from './movementControls';
import { formatMovingPathText, formatVerticesText, parseMovingPathText, parseVerticesText, type EntityPatch } from './editorState';
import type { Locale } from './i18n.ts';
import { t, translateDataValue } from './i18n.ts';
import type { VisualScaleSettings } from './renderSettings.ts';
import type { CoverageDisplayMode } from './scene.ts';

type CommandHandler = (command: string) => void;
type PerceivedRadiusHandler = (radius: number) => void;
type CameraHandler = (mode: CameraMode) => void;
type TrailHandler = (length: number) => void;
type VisualScaleHandler = (settings: VisualScaleSettings) => void;
type LabelScaleStepHandler = (direction: -1 | 0 | 1) => void;
type ToggleHandler = () => void;
type ScreenshotHandler = (format: string) => void;
type NavigationHandler = (action: 'pan_up' | 'pan_down' | 'pan_left' | 'pan_right' | 'reset_view' | 'zoom_scale', value?: number) => void;
type MiniMapClickHandler = (position: Position) => void;
type RelativeMoveHandler = (action: RelativeMoveAction) => void;
type CoverageDisplayHandler = (mode: CoverageDisplayMode) => void;
export type EditorAction =
  | { type: 'toggle' }
  | { type: 'add'; kind: SelectionRef['kind'] }
  | { type: 'move_selected' }
  | { type: 'cycle_selection' }
  | { type: 'toggle_snap_grid' }
  | { type: 'duplicate' }
  | { type: 'delete' }
  | { type: 'save' }
  | { type: 'save_as' }
  | { type: 'discard' }
  | { type: 'patch'; patch: EntityPatch };
type EditorHandler = (action: EditorAction) => void;

const droneStatuses = ['idle', 'ready', 'taking_off', 'flying', 'moving', 'hovering', 'landing', 'emergency', 'offline'];
const targetTypes = ['fixed', 'moving', 'waypoint', 'circle', 'polygon'];
const obstacleTypes = ['point', 'circle', 'ellipse', 'polygon'];
const movementModes = ['velocity', 'path', 'stationary'];

export class ViewerUI {
  readonly sessionName = document.querySelector<HTMLSpanElement>('#sessionName')!;
  private readonly appTitle = document.querySelector<HTMLElement>('#appTitle')!;
  readonly connectionStatus = document.querySelector<HTMLSpanElement>('#connectionStatus')!;
  readonly selectionTitle = document.querySelector<HTMLHeadingElement>('#selectionTitle')!;
  readonly selectionDetails = document.querySelector<HTMLDivElement>('#selectionDetails')!;
  readonly commandStatus = document.querySelector<HTMLParagraphElement>('#commandStatus')!;
  readonly altitudeInput = document.querySelector<HTMLInputElement>('#altitudeInput')!;
  readonly perceivedRadiusInput = document.querySelector<HTMLInputElement>('#perceivedRadiusInput')!;
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
  readonly moveStepInput = document.querySelector<HTMLInputElement>('#moveStepInput')!;
  readonly altitudeStepInput = document.querySelector<HTMLInputElement>('#altitudeStepInput')!;
  private readonly languageToggle = document.querySelector<HTMLButtonElement>('#languageToggle')!;
  private readonly cameraTop = document.querySelector<HTMLButtonElement>('#cameraTop')!;
  private readonly cameraFollow = document.querySelector<HTMLButtonElement>('#cameraFollow')!;
  private readonly cameraFit = document.querySelector<HTMLButtonElement>('#cameraFit')!;
  private readonly cheatSheetToggle = document.querySelector<HTMLButtonElement>('#cheatSheetToggle')!;
  private readonly infoToggle = document.querySelector<HTMLButtonElement>('#infoToggle')!;
  private readonly screenshotFormat = document.querySelector<HTMLSelectElement>('#screenshotFormat')!;
  private readonly screenshotButton = document.querySelector<HTMLButtonElement>('#screenshotButton')!;
  private readonly displayCoverageMode = document.querySelector<HTMLSelectElement>('#displayCoverageMode')!;
  private readonly basicControlTitle = document.querySelector<HTMLHeadingElement>('#basicControlTitle')!;
  private readonly altitudeLabel = document.querySelector<HTMLSpanElement>('#altitudeLabel')!;
  private readonly perceivedRadiusLabel = document.querySelector<HTMLSpanElement>('#perceivedRadiusLabel')!;
  private readonly movementTitle = document.querySelector<HTMLHeadingElement>('#movementTitle')!;
  private readonly moveStepLabel = document.querySelector<HTMLSpanElement>('#moveStepLabel')!;
  private readonly altitudeStepLabel = document.querySelector<HTMLSpanElement>('#altitudeStepLabel')!;
  private readonly editorTitle = document.querySelector<HTMLHeadingElement>('#editorTitle')!;
  private readonly trailLengthText = document.querySelector<HTMLSpanElement>('#trailLengthText')!;
  private readonly droneScaleText = document.querySelector<HTMLSpanElement>('#droneScaleText')!;
  private readonly targetScaleText = document.querySelector<HTMLSpanElement>('#targetScaleText')!;
  private readonly obstacleScaleText = document.querySelector<HTMLSpanElement>('#obstacleScaleText')!;
  private readonly labelScaleText = document.querySelector<HTMLSpanElement>('#labelScaleText')!;
  private readonly activityStatus = document.querySelector<HTMLSpanElement>('#activityStatus')!;
  private readonly liveToggle = document.querySelector<HTMLButtonElement>('#liveToggle')!;
  private readonly cmdTakeoff = document.querySelector<HTMLButtonElement>('#cmdTakeoff')!;
  private readonly cmdLand = document.querySelector<HTMLButtonElement>('#cmdLand')!;
  private readonly cmdHover = document.querySelector<HTMLButtonElement>('#cmdHover')!;
  private readonly cmdReturnHome = document.querySelector<HTMLButtonElement>('#cmdReturnHome')!;
  private readonly cmdCharge = document.querySelector<HTMLButtonElement>('#cmdCharge')!;
  private readonly cmdEmergency = document.querySelector<HTMLButtonElement>('#cmdEmergency')!;
  private readonly cmdUpdatePerceivedRadius = document.querySelector<HTMLButtonElement>('#cmdUpdatePerceivedRadius')!;
  private readonly cmdMoveMode = document.querySelector<HTMLButtonElement>('#cmdMoveMode')!;
  private readonly relForward = document.querySelector<HTMLButtonElement>('#relForward')!;
  private readonly relBackward = document.querySelector<HTMLButtonElement>('#relBackward')!;
  private readonly relLeft = document.querySelector<HTMLButtonElement>('#relLeft')!;
  private readonly relRight = document.querySelector<HTMLButtonElement>('#relRight')!;
  private readonly relUp = document.querySelector<HTMLButtonElement>('#relUp')!;
  private readonly relDown = document.querySelector<HTMLButtonElement>('#relDown')!;
  private readonly editModeToggle = document.querySelector<HTMLButtonElement>('#editModeToggle')!;
  private readonly addDrone = document.querySelector<HTMLButtonElement>('#addDrone')!;
  private readonly addTarget = document.querySelector<HTMLButtonElement>('#addTarget')!;
  private readonly addObstacle = document.querySelector<HTMLButtonElement>('#addObstacle')!;
  private readonly editMoveSelected = document.querySelector<HTMLButtonElement>('#editMoveSelected')!;
  private readonly cycleSelection = document.querySelector<HTMLButtonElement>('#cycleSelection')!;
  private readonly snapToGridToggle = document.querySelector<HTMLButtonElement>('#snapToGridToggle')!;
  private readonly duplicateSelected = document.querySelector<HTMLButtonElement>('#duplicateSelected')!;
  private readonly deleteSelected = document.querySelector<HTMLButtonElement>('#deleteSelected')!;
  private readonly saveSceneEdits = document.querySelector<HTMLButtonElement>('#saveSceneEdits')!;
  private readonly saveSceneAs = document.querySelector<HTMLButtonElement>('#saveSceneAs')!;
  private readonly discardSceneEdits = document.querySelector<HTMLButtonElement>('#discardSceneEdits')!;
  private readonly editorStatus = document.querySelector<HTMLParagraphElement>('#editorStatus')!;
  private readonly editForm = document.querySelector<HTMLDivElement>('#editForm')!;
  private readonly editName = document.querySelector<HTMLInputElement>('#editName')!;
  private readonly editModel = document.querySelector<HTMLInputElement>('#editModel')!;
  private readonly editType = document.querySelector<HTMLSelectElement>('#editType')!;
  private readonly editStatus = document.querySelector<HTMLSelectElement>('#editStatus')!;
  private readonly editMovementMode = document.querySelector<HTMLSelectElement>('#editMovementMode')!;
  private readonly editX = document.querySelector<HTMLInputElement>('#editX')!;
  private readonly editY = document.querySelector<HTMLInputElement>('#editY')!;
  private readonly editZ = document.querySelector<HTMLInputElement>('#editZ')!;
  private readonly editRadius = document.querySelector<HTMLInputElement>('#editRadius')!;
  private readonly editHeading = document.querySelector<HTMLInputElement>('#editHeading')!;
  private readonly editBattery = document.querySelector<HTMLInputElement>('#editBattery')!;
  private readonly editMaxSpeed = document.querySelector<HTMLInputElement>('#editMaxSpeed')!;
  private readonly editMaxAltitude = document.querySelector<HTMLInputElement>('#editMaxAltitude')!;
  private readonly editBatteryCapacity = document.querySelector<HTMLInputElement>('#editBatteryCapacity')!;
  private readonly editPerceivedRadius = document.querySelector<HTMLInputElement>('#editPerceivedRadius')!;
  private readonly editTaskRadius = document.querySelector<HTMLInputElement>('#editTaskRadius')!;
  private readonly editWidth = document.querySelector<HTMLInputElement>('#editWidth')!;
  private readonly editLength = document.querySelector<HTMLInputElement>('#editLength')!;
  private readonly editMovingDuration = document.querySelector<HTMLInputElement>('#editMovingDuration')!;
  private readonly editChargeAmount = document.querySelector<HTMLInputElement>('#editChargeAmount')!;
  private readonly editVelocityX = document.querySelector<HTMLInputElement>('#editVelocityX')!;
  private readonly editVelocityY = document.querySelector<HTMLInputElement>('#editVelocityY')!;
  private readonly editVelocityZ = document.querySelector<HTMLInputElement>('#editVelocityZ')!;
  private readonly editMovingPath = document.querySelector<HTMLTextAreaElement>('#editMovingPath')!;
  private readonly editVertices = document.querySelector<HTMLTextAreaElement>('#editVertices')!;
  private readonly editHeight = document.querySelector<HTMLInputElement>('#editHeight')!;
  private readonly editDescription = document.querySelector<HTMLTextAreaElement>('#editDescription')!;
  private state: ViewerState | null = null;
  private selection: SelectionRef | null = null;
  private miniMapVisible = true;
  private editMode = false;
  private editDirty = false;
  private editMoveMode = false;
  private snapToGrid = false;
  private locale: Locale = 'zh-CN';
  private live = true;
  private lastClickPosition: Position | null = null;
  private lastZoomScale = 1;
  private lastActivityStatus = '';
  private lastPerceivedRadiusDroneId: string | null = null;

  constructor(locale: Locale = 'zh-CN') {
    this.locale = locale;
    this.populateSelects();
    this.applyLocale();
  }

  bindCommands(handler: CommandHandler): void {
    this.cmdTakeoff.addEventListener('click', () => handler('takeoff'));
    this.cmdLand.addEventListener('click', () => handler('land'));
    this.cmdHover.addEventListener('click', () => handler('hover'));
    this.cmdReturnHome.addEventListener('click', () => handler('return_home'));
    this.cmdCharge.addEventListener('click', () => handler('charge'));
    this.cmdEmergency.addEventListener('click', () => handler('emergency'));
    this.cmdMoveMode.addEventListener('click', () => handler('move_mode'));
  }

  bindPerceivedRadius(handler: PerceivedRadiusHandler): void {
    this.cmdUpdatePerceivedRadius.addEventListener('click', () => handler(this.getPerceivedRadius()));
  }

  bindCamera(handler: CameraHandler): void {
    this.cameraTop.addEventListener('click', () => handler('top'));
    this.cameraFollow.addEventListener('click', () => handler('follow'));
    this.cameraFit.addEventListener('click', () => handler('fit'));
  }

  bindLanguage(handler: ToggleHandler): void {
    this.languageToggle.addEventListener('click', handler);
  }

  bindScreenshot(handler: ScreenshotHandler): void {
    this.screenshotButton.addEventListener('click', () => handler(this.screenshotFormat.value));
  }

  bindDisplayLayers(onCoverageMode: CoverageDisplayHandler): void {
    this.displayCoverageMode.addEventListener('change', () => onCoverageMode(this.displayCoverageMode.value as CoverageDisplayMode));
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
      const scaleX = this.miniMapCanvas.width / rect.width;
      const scaleY = this.miniMapCanvas.height / rect.height;
      const point = {
        x: (event.clientX - rect.left) * scaleX,
        y: (event.clientY - rect.top) * scaleY
      };
      handler(miniMapToWorld(point, resolveMiniMapBounds(this.state), this.getMiniMapSize()));
    });
  }

  bindRelativeMove(handler: RelativeMoveHandler): void {
    this.relForward.addEventListener('click', () => handler('forward'));
    this.relBackward.addEventListener('click', () => handler('backward'));
    this.relLeft.addEventListener('click', () => handler('left'));
    this.relRight.addEventListener('click', () => handler('right'));
    this.relUp.addEventListener('click', () => handler('up'));
    this.relDown.addEventListener('click', () => handler('down'));
  }

  bindEditor(handler: EditorHandler): void {
    this.editModeToggle.addEventListener('click', () => handler({ type: 'toggle' }));
    this.addDrone.addEventListener('click', () => handler({ type: 'add', kind: 'drone' }));
    this.addTarget.addEventListener('click', () => handler({ type: 'add', kind: 'target' }));
    this.addObstacle.addEventListener('click', () => handler({ type: 'add', kind: 'obstacle' }));
    this.editMoveSelected.addEventListener('click', () => handler({ type: 'move_selected' }));
    this.cycleSelection.addEventListener('click', () => handler({ type: 'cycle_selection' }));
    this.snapToGridToggle.addEventListener('click', () => handler({ type: 'toggle_snap_grid' }));
    this.duplicateSelected.addEventListener('click', () => handler({ type: 'duplicate' }));
    this.deleteSelected.addEventListener('click', () => handler({ type: 'delete' }));
    this.saveSceneEdits.addEventListener('click', () => handler({ type: 'save' }));
    this.saveSceneAs.addEventListener('click', () => handler({ type: 'save_as' }));
    this.discardSceneEdits.addEventListener('click', () => handler({ type: 'discard' }));
    this.editName.addEventListener('input', () => handler({ type: 'patch', patch: { name: this.editName.value } }));
    this.editModel.addEventListener('input', () => handler({ type: 'patch', patch: { model: this.editModel.value } }));
    this.editType.addEventListener('change', () => handler({ type: 'patch', patch: { type: this.editType.value } }));
    this.editStatus.addEventListener('change', () => handler({ type: 'patch', patch: { status: this.editStatus.value } }));
    this.editMovementMode.addEventListener('change', () => handler({ type: 'patch', patch: { movement_mode: this.editMovementMode.value } }));
    this.editDescription.addEventListener('input', () => handler({ type: 'patch', patch: { description: this.editDescription.value } }));
    this.bindNumericEditorInput(this.editX, (value) => ({ position: { x: value } }), handler);
    this.bindNumericEditorInput(this.editY, (value) => ({ position: { y: value } }), handler);
    this.bindNumericEditorInput(this.editZ, (value) => ({ position: { z: value } }), handler);
    this.bindNumericEditorInput(this.editRadius, (value) => ({ radius: value }), handler);
    this.bindNumericEditorInput(this.editHeading, (value) => ({ heading: value }), handler);
    this.bindNumericEditorInput(this.editBattery, (value) => ({ battery_level: value }), handler);
    this.bindNumericEditorInput(this.editMaxSpeed, (value) => ({ max_speed: value }), handler);
    this.bindNumericEditorInput(this.editMaxAltitude, (value) => ({ max_altitude: value }), handler);
    this.bindNumericEditorInput(this.editBatteryCapacity, (value) => ({ battery_capacity: value }), handler);
    this.bindNumericEditorInput(this.editPerceivedRadius, (value) => ({ perceived_radius: value }), handler);
    this.bindNumericEditorInput(this.editTaskRadius, (value) => ({ task_radius: value }), handler);
    this.bindNumericEditorInput(this.editWidth, (value) => ({ width: value }), handler);
    this.bindNumericEditorInput(this.editLength, (value) => ({ length: value }), handler);
    this.bindNumericEditorInput(this.editMovingDuration, (value) => ({ moving_duration: value }), handler);
    this.bindNumericEditorInput(this.editChargeAmount, (value) => ({ charge_amount: value }), handler);
    this.bindNumericEditorInput(this.editVelocityX, (value) => ({ velocity: { x: value } }), handler);
    this.bindNumericEditorInput(this.editVelocityY, (value) => ({ velocity: { y: value } }), handler);
    this.bindNumericEditorInput(this.editVelocityZ, (value) => ({ velocity: { z: value } }), handler);
    this.bindNumericEditorInput(this.editHeight, (value) => ({ height: value }), handler);
    this.editVertices.addEventListener('input', () => {
      try {
        handler({ type: 'patch', patch: { vertices: parseVerticesText(this.editVertices.value) } });
      } catch (error) {
        this.setEditorStatus(error instanceof Error ? error.message : String(error), false);
      }
    });
    this.editMovingPath.addEventListener('input', () => {
      try {
        handler({
          type: 'patch',
          patch: { moving_path: parseMovingPathText(this.editMovingPath.value, Number(this.editZ.value) || 0) }
        });
      } catch (error) {
        this.setEditorStatus(error instanceof Error ? error.message : String(error), false);
      }
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
    this.setCommandStatus(t(this.locale, 'control.backendDisconnected'), false);
  }

  updateSelection(selection: SelectionRef | null): void {
    this.selection = selection;
    if (!selection || !this.state) {
      this.selectionTitle.textContent = t(this.locale, 'selection.none.title');
      this.selectionDetails.textContent = t(this.locale, 'selection.none.detail');
      this.updateCommandAvailability(null);
      this.renderEditorForm();
      return;
    }
    if (selection.kind === 'drone') {
      const drone = this.state.drones.find((item) => item.id === selection.id);
      if (drone) this.renderDrone(drone);
    } else if (selection.kind === 'target') {
      const target = this.state.targets.find((item) => item.id === selection.id);
      if (target) this.renderTarget(target);
      this.updateCommandAvailability(null);
    } else {
      const obstacle = this.state.obstacles.find((item) => item.id === selection.id);
      if (obstacle) this.renderObstacle(obstacle);
      this.updateCommandAvailability(null);
    }
    this.renderEditorForm();
  }

  getSelectedDrone(): DroneState | null {
    if (!this.state || !this.selection || this.selection.kind !== 'drone') return null;
    return this.state.drones.find((drone) => drone.id === this.selection?.id) || null;
  }

  getAltitude(): number {
    return Number(this.altitudeInput.value) || 10;
  }

  getPerceivedRadius(): number {
    return Number(this.perceivedRadiusInput.value);
  }

  getMoveStep(): number {
    return Number(this.moveStepInput.value) || 20;
  }

  getAltitudeStep(): number {
    return Number(this.altitudeStepInput.value) || 5;
  }

  getVisualScaleSettings(): VisualScaleSettings {
    return {
      drone: Number(this.droneScale.value) / 100,
      target: Number(this.targetScale.value) / 100,
      obstacle: Number(this.obstacleScale.value) / 100,
      label: Number(this.labelScale.value) / 100
    };
  }

  setMoveMode(active: boolean): void {
    this.cmdMoveMode.classList.toggle('active', active);
    this.setCommandStatus(active ? t(this.locale, 'control.moveModeOn') : t(this.locale, 'control.moveModeOff'), true);
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

  updateClickPosition(position: { x: number; y: number; z: number } | null): void {
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

  setCameraActivity(mode: CameraMode): void {
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

    const size = this.getMiniMapSize();
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
      this.drawMiniMapObject(ctx, obstacle.position, obstacle.radius || Math.max(obstacle.width || 0, obstacle.length || 0) / 2 || 6, bounds, size, '#64748b');
    }
    for (const target of this.state.targets) {
      const visualState = getTargetVisualState(target, this.state);
      this.drawMiniMapObject(ctx, target.position, target.radius || 6, bounds, size, `#${visualState.color.toString(16).padStart(6, '0')}`);
    }
    for (const drone of this.state.drones) {
      const point = worldToMiniMap(drone.position, bounds, size);
      const selected = this.selection?.kind === 'drone' && this.selection.id === drone.id;
      ctx.fillStyle = selected ? '#ef4444' : '#2563eb';
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

  setCommandResult(result: CommandResult): void {
    this.setCommandStatus(translateDataValue(this.locale, result.message), result.ok);
  }

  setDisplayStatus(result: CommandResult): void {
    this.setCommandStatus(translateDataValue(this.locale, result.message), result.ok);
  }

  setCommandStatus(message: string, ok: boolean): void {
    this.commandStatus.textContent = message;
    this.commandStatus.className = `command-status ${ok ? 'ok' : 'error'}`;
  }

  setEditorState(active: boolean, dirty: boolean, moveMode: boolean): void {
    this.editMode = active;
    this.editDirty = dirty;
    this.editMoveMode = moveMode;
    this.editModeToggle.textContent = active ? t(this.locale, 'editor.toggleOff') : t(this.locale, 'editor.toggleOn');
    this.editModeToggle.classList.toggle('active', active);
    this.editMoveSelected.classList.toggle('active', moveMode);
    this.renderEditorForm();
  }

  setSnapToGrid(active: boolean): void {
    this.snapToGrid = active;
    this.snapToGridToggle.classList.toggle('active', active);
    this.snapToGridToggle.textContent = active ? `${t(this.locale, 'editor.snapGrid')} ✓` : t(this.locale, 'editor.snapGrid');
  }

  setEditorStatus(message: string, ok: boolean): void {
    this.editorStatus.textContent = translateDataValue(this.locale, message);
    this.editorStatus.className = `command-status ${ok ? 'ok' : 'error'}`;
  }

  setDisplayMode(): void {
    this.updateCommandAvailability(null);
    this.setEditorState(false, false, false);
    this.commandStatus.textContent = t(this.locale, 'selection.none.detail');
    this.commandStatus.className = 'command-status';
    this.setActivityText(this.lastActivityStatus);
  }

  private renderDrone(drone: DroneState): void {
    this.updateCommandAvailability(drone);
    if (document.activeElement !== this.perceivedRadiusInput || this.lastPerceivedRadiusDroneId !== drone.id) {
      this.perceivedRadiusInput.value = this.formatInputNumber(drone.perceived_radius);
    }
    this.lastPerceivedRadiusDroneId = drone.id;
    this.selectionTitle.textContent = `${t(this.locale, 'entity.drone')} · ${drone.name}`;
    this.selectionDetails.innerHTML = `
      <dl>
        <dt>${t(this.locale, 'field.id')}</dt><dd>${drone.id}</dd>
        <dt>${t(this.locale, 'field.name')}</dt><dd>${drone.name}</dd>
        <dt>${t(this.locale, 'field.status')}</dt><dd>${translateDataValue(this.locale, drone.status)}</dd>
        <dt>${t(this.locale, 'field.position')}</dt><dd>${this.formatPosition(drone.position)}</dd>
        <dt>${t(this.locale, 'field.heading')}</dt><dd>${Math.round(drone.heading || 0)}°</dd>
        <dt>${t(this.locale, 'field.speed')}</dt><dd>${drone.speed ?? 0} m/s</dd>
        <dt>${t(this.locale, 'field.battery')}</dt><dd>${Math.round(drone.battery_level ?? 0)}%</dd>
        <dt>${t(this.locale, 'field.model')}</dt><dd>${translateDataValue(this.locale, drone.model || '-')}</dd>
        <dt>${t(this.locale, 'field.maxSpeed')}</dt><dd>${drone.max_speed ?? '-'} m/s</dd>
        <dt>${t(this.locale, 'field.maxAltitude')}</dt><dd>${drone.max_altitude ?? '-'} m</dd>
        <dt>${t(this.locale, 'field.perceivedRadius')}</dt><dd>${drone.perceived_radius ?? '-'} m</dd>
        <dt>${t(this.locale, 'field.taskRadius')}</dt><dd>${drone.task_radius ?? '-'} m</dd>
        <dt>${t(this.locale, 'field.home')}</dt><dd>${drone.home_position ? this.formatPosition(drone.home_position) : '-'}</dd>
      </dl>
    `;
  }

  private setActivityText(value: string): void {
    this.lastActivityStatus = value;
    this.activityStatus.textContent = value;
    this.activityStatus.classList.toggle('hidden', value === '');
  }

  private resolveSelectionActivity(selection: SelectionRef): { kind: string; name: string; id: string } | null {
    if (!this.state) return null;
    if (selection.kind === 'drone') {
      const drone = this.state.drones.find((item) => item.id === selection.id);
      return drone ? { kind: t(this.locale, 'entity.drone'), name: drone.name, id: drone.id } : null;
    }
    if (selection.kind === 'target') {
      const target = this.state.targets.find((item) => item.id === selection.id);
      return target ? { kind: t(this.locale, 'entity.target'), name: target.name, id: target.id } : null;
    }
    const obstacle = this.state.obstacles.find((item) => item.id === selection.id);
    return obstacle ? { kind: t(this.locale, 'entity.obstacle'), name: obstacle.name, id: obstacle.id } : null;
  }

  private renderTarget(target: TargetState): void {
    const visualState = this.state ? getTargetVisualState(target, this.state, this.locale) : null;
    const coverage = this.state ? summarizeCoverage(this.state, target.id) : { points: 0, progressPercentage: null };
    const geometryRows = [
      target.type === 'polygon'
        ? `<dt>${t(this.locale, 'field.polygonVertices')}</dt><dd class="detail-list">${this.formatVertices(target.vertices)}</dd>`
        : `<dt>${t(this.locale, 'field.radius')}</dt><dd>${target.radius ?? '-'}</dd>`
    ].join('');
    this.selectionTitle.textContent = `${t(this.locale, 'entity.target')} · ${target.name}`;
    this.selectionDetails.innerHTML = `
      <dl>
        <dt>${t(this.locale, 'field.id')}</dt><dd>${target.id}</dd>
        <dt>${t(this.locale, 'field.name')}</dt><dd>${target.name}</dd>
        <dt>${t(this.locale, 'field.type')}</dt><dd>${translateDataValue(this.locale, target.type)}</dd>
        <dt>${t(this.locale, 'field.position')}</dt><dd>${this.formatPosition(target.position)}</dd>
        ${geometryRows}
        <dt>${t(this.locale, 'field.area')}</dt><dd>${this.formatArea(target.area)}</dd>
        <dt>${t(this.locale, 'field.completed')}</dt><dd>${target.is_reached ? t(this.locale, 'value.yes') : t(this.locale, 'value.no')}</dd>
        <dt>${t(this.locale, 'field.description')}</dt><dd>${translateDataValue(this.locale, target.description || '-')}</dd>
        <dt>${t(this.locale, 'field.movementMode')}</dt><dd>${translateDataValue(this.locale, target.movement_mode || '-')}</dd>
        <dt>${t(this.locale, 'field.trackingStatus')}</dt><dd>${translateDataValue(this.locale, target.tracking_status || '-')}</dd>
        <dt>${t(this.locale, 'field.pathPoints')}</dt><dd>${target.moving_path?.length ?? target.vertices?.length ?? '-'}</dd>
        <dt>${t(this.locale, 'field.velocity')}</dt><dd>${target.velocity ? this.formatPosition(target.velocity) : '-'}</dd>
        <dt>${t(this.locale, 'field.taskStatus')}</dt><dd>${visualState?.label || '-'}</dd>
        <dt>${t(this.locale, 'field.coveragePoints')}</dt><dd>${coverage.points}</dd>
        <dt>${t(this.locale, 'field.coverageProgress')}</dt><dd>${coverage.progressPercentage === null ? '-' : `${coverage.progressPercentage}%`}</dd>
        <dt>${t(this.locale, 'field.charge')}</dt><dd>${target.charge_amount ?? '-'}</dd>
      </dl>
    `;
  }

  private renderObstacle(obstacle: ObstacleState): void {
    const geometryRows = [
      ['point', 'circle'].includes(obstacle.type) ? `<dt>${t(this.locale, 'field.radius')}</dt><dd>${obstacle.radius ?? '-'}</dd>` : '',
      obstacle.type === 'ellipse' ? `<dt>${t(this.locale, 'field.size')}</dt><dd>${obstacle.width ?? '-'} x ${obstacle.length ?? '-'}</dd>` : '',
      obstacle.type === 'polygon' ? `<dt>${t(this.locale, 'field.polygonVertices')}</dt><dd class="detail-list">${this.formatVertices(obstacle.vertices)}</dd>` : ''
    ].join('');
    this.selectionTitle.textContent = `${t(this.locale, 'entity.obstacle')} · ${obstacle.name}`;
    this.selectionDetails.innerHTML = `
      <dl>
        <dt>${t(this.locale, 'field.id')}</dt><dd>${obstacle.id}</dd>
        <dt>${t(this.locale, 'field.name')}</dt><dd>${obstacle.name}</dd>
        <dt>${t(this.locale, 'field.type')}</dt><dd>${translateDataValue(this.locale, obstacle.type)}</dd>
        <dt>${t(this.locale, 'field.height')}</dt><dd>${obstacle.height === 0 ? t(this.locale, 'value.notFlyable') : `${obstacle.height ?? 0}m`}</dd>
        <dt>${t(this.locale, 'field.position')}</dt><dd>${this.formatPosition(obstacle.position)}</dd>
        ${geometryRows}
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

  private updateCommandAvailability(drone: DroneState | null): void {
    const availability = getCommandAvailability(drone);
    this.cmdTakeoff.disabled = !availability.takeoff;
    this.cmdLand.disabled = !availability.land;
    this.cmdHover.disabled = !availability.hover;
    this.cmdReturnHome.disabled = !availability.returnHome;
    this.cmdCharge.disabled = !availability.charge;
    this.cmdEmergency.disabled = !availability.emergency;
    this.cmdUpdatePerceivedRadius.disabled = !drone;
    this.perceivedRadiusInput.disabled = !drone;
    this.cmdMoveMode.disabled = !availability.moveMode;
    this.relForward.disabled = !availability.relativeMove;
    this.relBackward.disabled = !availability.relativeMove;
    this.relLeft.disabled = !availability.relativeMove;
    this.relRight.disabled = !availability.relativeMove;
    this.relUp.disabled = !availability.altitudeMove;
    this.relDown.disabled = !availability.altitudeMove;
  }

  private bindNumericEditorInput(
    input: HTMLInputElement,
    makePatch: (value: number | undefined) => EntityPatch,
    handler: EditorHandler
  ): void {
    input.addEventListener('input', () => {
      const value = input.value === '' ? undefined : Number(input.value);
      handler({ type: 'patch', patch: makePatch(Number.isFinite(value) ? value : undefined) });
    });
  }

  private renderEditorForm(): void {
    const entity = this.getSelectedEditableEntity();
    const hasSelection = Boolean(entity);
    const enabled = this.editMode && hasSelection;
    this.editForm.classList.toggle('hidden', !enabled);

    this.addDrone.disabled = !this.editMode;
    this.addTarget.disabled = !this.editMode;
    this.addObstacle.disabled = !this.editMode;
    this.editMoveSelected.disabled = !enabled;
    this.cycleSelection.disabled = !enabled;
    this.snapToGridToggle.disabled = !this.editMode;
    this.duplicateSelected.disabled = !enabled;
    this.deleteSelected.disabled = !enabled;
    this.saveSceneEdits.disabled = !this.editMode || !this.editDirty;
    this.saveSceneAs.disabled = !this.editMode;
    this.discardSceneEdits.disabled = !this.editMode;

    for (const field of [
      this.editName,
      this.editModel,
      this.editType,
      this.editStatus,
      this.editMovementMode,
      this.editX,
      this.editY,
      this.editZ,
      this.editRadius,
      this.editHeading,
      this.editBattery,
      this.editMaxSpeed,
      this.editMaxAltitude,
      this.editBatteryCapacity,
      this.editPerceivedRadius,
      this.editTaskRadius,
      this.editWidth,
      this.editLength,
      this.editMovingDuration,
      this.editChargeAmount,
      this.editVelocityX,
      this.editVelocityY,
      this.editVelocityZ,
      this.editMovingPath,
      this.editVertices,
      this.editHeight,
      this.editDescription
    ]) {
      field.disabled = !enabled;
    }

    if (!this.editMode) {
      this.editorStatus.textContent = t(this.locale, 'editor.off');
      this.editorStatus.className = 'command-status';
      return;
    }
    if (!entity) {
      if (!this.editDirty) {
        this.editorStatus.textContent = t(this.locale, 'editor.selectToEdit');
        this.editorStatus.className = 'command-status';
      }
      return;
    }

    this.updateFieldVisibility(entity);
    this.populateSelects();
    this.editName.value = entity.name || '';
    this.editModel.value = 'model' in entity ? entity.model || '' : '';
    this.editType.value = 'type' in entity ? entity.type || '' : '';
    this.editStatus.value = 'status' in entity ? entity.status || '' : '';
    this.editMovementMode.value = 'movement_mode' in entity ? entity.movement_mode || 'velocity' : 'velocity';
    this.editX.value = this.formatInputNumber(entity.position.x);
    this.editY.value = this.formatInputNumber(entity.position.y);
    this.editZ.value = this.formatInputNumber(entity.position.z);
    this.editRadius.value = this.formatInputNumber('radius' in entity ? entity.radius : undefined);
    this.editHeading.value = this.formatInputNumber('heading' in entity ? entity.heading : undefined);
    this.editBattery.value = this.formatInputNumber('battery_level' in entity ? entity.battery_level : undefined);
    this.editMaxSpeed.value = this.formatInputNumber('max_speed' in entity ? entity.max_speed : undefined);
    this.editMaxAltitude.value = this.formatInputNumber('max_altitude' in entity ? entity.max_altitude : undefined);
    this.editBatteryCapacity.value = this.formatInputNumber('battery_capacity' in entity ? entity.battery_capacity : undefined);
    this.editPerceivedRadius.value = this.formatInputNumber('perceived_radius' in entity ? entity.perceived_radius : undefined);
    this.editTaskRadius.value = this.formatInputNumber('task_radius' in entity ? entity.task_radius : undefined);
    this.editWidth.value = this.formatInputNumber('width' in entity ? entity.width : undefined);
    this.editLength.value = this.formatInputNumber('length' in entity ? entity.length : undefined);
    this.editMovingDuration.value = this.formatInputNumber('moving_duration' in entity ? entity.moving_duration : undefined);
    this.editChargeAmount.value = this.formatInputNumber('charge_amount' in entity ? entity.charge_amount : undefined);
    this.editVelocityX.value = this.formatInputNumber('velocity' in entity ? entity.velocity?.x : undefined);
    this.editVelocityY.value = this.formatInputNumber('velocity' in entity ? entity.velocity?.y : undefined);
    this.editVelocityZ.value = this.formatInputNumber('velocity' in entity ? entity.velocity?.z : undefined);
    this.editMovingPath.value = formatMovingPathText('moving_path' in entity ? entity.moving_path : undefined);
    this.editVertices.value = formatVerticesText('vertices' in entity ? entity.vertices : undefined);
    this.editHeight.value = this.formatInputNumber('height' in entity ? entity.height : undefined);
    this.editDescription.value = 'description' in entity ? translateDataValue(this.locale, entity.description || '') : '';
    if (!this.editDirty) {
      this.editorStatus.textContent = t(this.locale, 'editor.ready');
      this.editorStatus.className = 'command-status ok';
    }
  }

  private getSelectedEditableEntity(): DroneState | TargetState | ObstacleState | null {
    if (!this.state || !this.selection) return null;
    if (this.selection.kind === 'drone') {
      return this.state.drones.find((drone) => drone.id === this.selection?.id) || null;
    }
    if (this.selection.kind === 'target') {
      return this.state.targets.find((target) => target.id === this.selection?.id) || null;
    }
    return this.state.obstacles.find((obstacle) => obstacle.id === this.selection?.id) || null;
  }

  private formatInputNumber(value: number | undefined): string {
    return value === undefined || Number.isNaN(value) ? '' : String(Number(value.toFixed(2)));
  }

  private updateFieldVisibility(entity: DroneState | TargetState | ObstacleState): void {
    const isDrone = this.selection?.kind === 'drone';
    const isTarget = this.selection?.kind === 'target';
    const isObstacle = this.selection?.kind === 'obstacle';
    const entityType = 'type' in entity ? entity.type : '';
    const movementMode = 'movement_mode' in entity ? entity.movement_mode || 'velocity' : 'velocity';
    const isPolygon = entityType === 'polygon';
    const isMovingTarget = isTarget && entityType === 'moving';

    this.setInputVisible(this.editModel, isDrone);
    this.setInputVisible(this.editStatus, isDrone);
    this.setGroupVisible('drone-motion', isDrone);
    this.setGroupVisible('drone-spec', isDrone);
    this.setInputVisible(this.editType, isTarget || isObstacle);
    this.setInputVisible(this.editDescription, isTarget || isObstacle);
    this.setInputVisible(this.editX, !isPolygon);
    this.setInputVisible(this.editY, !isPolygon);
    this.setInputVisible(this.editZ, isDrone || (isTarget && ['fixed', 'moving'].includes(entityType)));
    this.setInputVisible(this.editRadius, isTarget ? entityType !== 'polygon' : isObstacle && ['point', 'circle'].includes(entityType));
    this.setInputVisible(this.editWidth, isObstacle && entityType === 'ellipse');
    this.setInputVisible(this.editLength, isObstacle && entityType === 'ellipse');
    this.setInputVisible(this.editHeight, isObstacle);
    this.setGroupVisible('target-motion', isTarget && (entityType === 'moving' || entityType === 'waypoint'));
    this.setGroupVisible('target-motion-mode', isMovingTarget);
    this.setInputVisible(this.editMovingDuration, isMovingTarget);
    this.setInputVisible(this.editChargeAmount, isTarget && entityType === 'waypoint');
    this.setGroupVisible('target-velocity', isMovingTarget && movementMode === 'velocity');
    this.setGroupVisible('target-path', isMovingTarget && movementMode === 'path');
    this.setGroupVisible('polygon-vertices', (isTarget || isObstacle) && isPolygon);
  }

  private setInputVisible(input: HTMLElement, visible: boolean): void {
    const label = input.closest('label');
    if (label) label.classList.toggle('hidden', !visible);
  }

  private setGroupVisible(group: string, visible: boolean): void {
    document.querySelectorAll<HTMLElement>(`[data-edit-field="${group}"]`).forEach((item) => {
      item.classList.toggle('hidden', !visible);
    });
  }

  private formatPosition(position: Position): string {
    return `x=${position.x.toFixed(1)}, y=${position.y.toFixed(1)}, z=${position.z.toFixed(1)}`;
  }

  private applyLocale(): void {
    document.documentElement.lang = this.locale;
    this.populateSelects();
    this.appTitle.textContent = t(this.locale, 'app.title');
    this.languageToggle.textContent = t(this.locale, 'language.toggle');
    this.cameraTop.textContent = t(this.locale, 'camera.top');
    this.cameraFollow.textContent = t(this.locale, 'camera.follow');
    this.cameraFit.textContent = t(this.locale, 'camera.fit');
    this.cheatSheetToggle.textContent = t(this.locale, 'topbar.cheatSheet');
    this.infoToggle.textContent = t(this.locale, 'topbar.info');
    this.setAriaLabel('#cheatSheetPanel', t(this.locale, 'cheat.title'));
    this.setText('#cheatSheetTitle', t(this.locale, 'cheat.title'));
    this.setText('#cheatClear', t(this.locale, 'cheat.clear'));
    this.setText('#cheatPan', t(this.locale, 'cheat.pan'));
    this.setText('#cheatCameraTop', t(this.locale, 'cheat.cameraTop'));
    this.setText('#cheatCameraFollow', t(this.locale, 'cheat.cameraFollow'));
    this.setText('#cheatCameraFit', t(this.locale, 'cheat.cameraFit'));
    this.setText('#cheatZoom', t(this.locale, 'cheat.zoom'));
    this.setText('#cheatReset', t(this.locale, 'cheat.reset'));
    this.setText('#cheatLabels', t(this.locale, 'cheat.labels'));
    this.setText('#cheatMinimap', t(this.locale, 'cheat.minimap'));
    this.setText('#cheatInfo', t(this.locale, 'cheat.info'));
    this.setTitle('#closeCheatSheet', t(this.locale, 'cheat.close'));
    this.screenshotButton.textContent = t(this.locale, 'screenshot.capture');
    this.screenshotFormat.title = t(this.locale, 'screenshot.format');
    this.displayCoverageMode.title = t(this.locale, 'backend.coverageDisplay');
    this.setOptionText('#displayCoverageMode', 'surface', t(this.locale, 'backend.coverageSurface'));
    this.setOptionText('#displayCoverageMode', 'points', t(this.locale, 'backend.coveragePoints'));
    this.setOptionText('#displayCoverageMode', 'both', t(this.locale, 'backend.coverageBoth'));
    this.setAriaLabel('.nav-overlay', t(this.locale, 'nav.label'));
    this.setTitle('#panUp', t(this.locale, 'nav.panUp'));
    this.setTitle('#panDown', t(this.locale, 'nav.panDown'));
    this.setTitle('#panLeft', t(this.locale, 'nav.panLeft'));
    this.setTitle('#panRight', t(this.locale, 'nav.panRight'));
    this.setTitle('#resetView', t(this.locale, 'nav.reset'));
    this.setAriaLabel('.zoom-rail', t(this.locale, 'nav.zoomScale'));
    this.setTitle('.zoom-rail', t(this.locale, 'nav.zoomScale'));
    this.applyBackendToolLocale();
    this.basicControlTitle.textContent = t(this.locale, 'control.basic');
    this.altitudeLabel.textContent = t(this.locale, 'control.altitude');
    this.perceivedRadiusLabel.textContent = t(this.locale, 'control.perceivedRadius');
    this.cmdTakeoff.textContent = t(this.locale, 'control.takeoff');
    this.cmdLand.textContent = t(this.locale, 'control.land');
    this.cmdHover.textContent = t(this.locale, 'control.hover');
    this.cmdReturnHome.textContent = t(this.locale, 'control.returnHome');
    this.cmdCharge.textContent = t(this.locale, 'control.charge');
    this.cmdEmergency.textContent = t(this.locale, 'control.emergency');
    this.cmdUpdatePerceivedRadius.textContent = t(this.locale, 'control.updatePerceivedRadius');
    this.cmdMoveMode.textContent = t(this.locale, 'control.moveMode');
    this.movementTitle.textContent = t(this.locale, 'movement.title');
    this.moveStepLabel.textContent = t(this.locale, 'movement.step');
    this.altitudeStepLabel.textContent = t(this.locale, 'movement.altitudeStep');
    this.relUp.textContent = t(this.locale, 'movement.up');
    this.relForward.textContent = t(this.locale, 'movement.forward');
    this.relLeft.textContent = t(this.locale, 'movement.left');
    this.relRight.textContent = t(this.locale, 'movement.right');
    this.relBackward.textContent = t(this.locale, 'movement.backward');
    this.relDown.textContent = t(this.locale, 'movement.down');
    this.editorTitle.textContent = t(this.locale, 'editor.title');
    this.editModeToggle.textContent = this.editMode ? t(this.locale, 'editor.toggleOff') : t(this.locale, 'editor.toggleOn');
    this.addDrone.textContent = t(this.locale, 'editor.addDrone');
    this.addTarget.textContent = t(this.locale, 'editor.addTarget');
    this.addObstacle.textContent = t(this.locale, 'editor.addObstacle');
    this.editMoveSelected.textContent = t(this.locale, 'editor.moveSelected');
    this.cycleSelection.textContent = t(this.locale, 'editor.selection');
    this.setSnapToGrid(this.snapToGrid);
    this.duplicateSelected.textContent = t(this.locale, 'editor.duplicate');
    this.deleteSelected.textContent = t(this.locale, 'editor.delete');
    this.saveSceneEdits.textContent = t(this.locale, 'editor.save');
    this.saveSceneAs.textContent = t(this.locale, 'editor.saveAs');
    this.discardSceneEdits.textContent = t(this.locale, 'editor.discard');
    this.setText('#editNameLabel', t(this.locale, 'field.name'));
    this.setText('#editModelLabel', t(this.locale, 'field.model'));
    this.setText('#editTypeLabel', t(this.locale, 'field.type'));
    this.setText('#editStatusLabel', t(this.locale, 'field.status'));
    this.setText('#editMovementModeLabel', t(this.locale, 'field.movementMode'));
    this.setText('#editXLabel', 'X');
    this.setText('#editYLabel', 'Y');
    this.setText('#editZLabel', 'Z');
    this.setText('#editRadiusLabel', t(this.locale, 'field.radius'));
    this.setText('#editHeadingLabel', t(this.locale, 'field.heading'));
    this.setText('#editBatteryLabel', t(this.locale, 'field.battery'));
    this.setText('#editMaxSpeedLabel', t(this.locale, 'field.maxSpeed'));
    this.setText('#editMaxAltitudeLabel', t(this.locale, 'field.maxAltitude'));
    this.setText('#editBatteryCapacityLabel', t(this.locale, 'field.batteryCapacity'));
    this.setText('#editPerceivedRadiusLabel', t(this.locale, 'field.perceivedRadius'));
    this.setText('#editTaskRadiusLabel', t(this.locale, 'field.taskRadius'));
    this.setText('#editWidthLabel', t(this.locale, 'field.width'));
    this.setText('#editLengthLabel', t(this.locale, 'field.length'));
    this.setText('#editMovingDurationLabel', t(this.locale, 'field.movingDuration'));
    this.setText('#editChargeAmountLabel', t(this.locale, 'field.charge'));
    this.setText('#editVelocityXLabel', t(this.locale, 'field.velocityX'));
    this.setText('#editVelocityYLabel', t(this.locale, 'field.velocityY'));
    this.setText('#editVelocityZLabel', t(this.locale, 'field.velocityZ'));
    this.setText('#editMovingPathLabel', t(this.locale, 'field.movingPath'));
    this.setText('#editVerticesLabel', t(this.locale, 'field.polygonVertices'));
    this.setText('#editHeightLabel', t(this.locale, 'field.height'));
    this.setText('#editDescriptionLabel', t(this.locale, 'field.description'));
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
      this.commandStatus.textContent = t(this.locale, 'control.selectDrone');
      this.editorStatus.textContent = t(this.locale, 'editor.off');
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

  private setPlaceholder(selector: string, value: string): void {
    const element = document.querySelector<HTMLInputElement | HTMLTextAreaElement>(selector);
    if (element) element.placeholder = value;
  }

  private setOptionText(selectSelector: string, value: string, text: string): void {
    const option = document.querySelector<HTMLOptionElement>(`${selectSelector} option[value="${value}"]`);
    if (option) option.textContent = text;
  }

  private setInitialToolOutput(selector: string, text: string): void {
    const element = document.querySelector<HTMLPreElement>(selector);
    if (element && !element.classList.contains('ok') && !element.classList.contains('error')) {
      element.textContent = text;
    }
  }

  private applyBackendToolLocale(): void {
    this.setText('#backendToolsTitle', t(this.locale, 'backend.title'));
    this.setText('#sessionToolRefresh', t(this.locale, 'backend.refreshSessions'));
    this.setText('#sessionToolSwitch', t(this.locale, 'backend.switch'));
    this.setText('#sessionToolReset', t(this.locale, 'backend.resetCurrent'));
    this.setText('#sessionToolExport', t(this.locale, 'backend.exportJson'));
    this.setText('#sessionToolDelete', t(this.locale, 'backend.deleteSession'));
    this.setText('#backendScreenshotButton', t(this.locale, 'backend.screenshot'));
    this.setText('#taskToolRefresh', t(this.locale, 'task.refresh'));
    this.setText('#taskToolNext', t(this.locale, 'task.next'));
    this.setText('#taskToolInspect', t(this.locale, 'task.inspect'));
    this.setText('#taskToolCheck', t(this.locale, 'task.check'));
    this.setText('#taskToolDone', t(this.locale, 'task.markDone'));
    this.setText('#taskToolPending', t(this.locale, 'task.markPending'));
    this.setText('#checkToolRun', t(this.locale, 'task.runCheck'));
    this.setText('#advancedCommandRun', t(this.locale, 'advanced.send'));
    this.setPlaceholder('#taskSinceTimestamp', t(this.locale, 'task.sincePlaceholder'));
    this.setPlaceholder('#advancedCommandDroneId', t(this.locale, 'advanced.droneIdPlaceholder'));
    this.setOptionText('#coverageDisplayMode', 'surface', t(this.locale, 'backend.coverageSurface'));
    this.setOptionText('#coverageDisplayMode', 'points', t(this.locale, 'backend.coveragePoints'));
    this.setOptionText('#coverageDisplayMode', 'both', t(this.locale, 'backend.coverageBoth'));
    this.setInitialToolOutput('#sessionToolStatus', t(this.locale, 'backend.initialStatus'));
    this.setInitialToolOutput('#taskToolStatus', t(this.locale, 'task.initialStatus'));
    this.setInitialToolOutput('#advancedCommandStatus', t(this.locale, 'advanced.initialStatus'));

    const labels: Array<[string, string]> = [
      ['#coverageDisplayMode', 'backend.coverageDisplay'],
      ['#sessionToolSelect', 'backend.currentSession'],
      ['#backendScreenshotFormat', 'screenshot.format'],
      ['#backendScreenshotSize', 'backend.size'],
      ['#backendScreenshotShowStatus', 'backend.includeStatus'],
      ['#taskToolSelect', 'task.current'],
      ['#taskSinceTimestamp', 'task.sinceTimestamp'],
      ['#checkToolEndpoint', 'task.checkEndpoint'],
      ['#checkToolParams', 'task.checkParams'],
      ['#advancedCommandDroneId', 'advanced.droneId'],
      ['#advancedCommandName', 'advanced.command'],
      ['#advancedCommandParams', 'advanced.params']
    ];
    for (const [inputSelector, key] of labels) {
      const label = document.querySelector<HTMLElement>(inputSelector)?.closest('label')?.querySelector('span');
      if (label) label.textContent = t(this.locale, key);
    }

    const cardTitles: Array<[string, string]> = [
      ['#backendToolsTitle', 'backend.title'],
      ['#taskToolsTitle', 'task.title'],
      ['#advancedCommandTitle', 'advanced.title']
    ];
    for (const [selector, key] of cardTitles) this.setText(selector, t(this.locale, key));
  }

  private populateSelects(): void {
    this.populateSelect(this.editStatus, droneStatuses);
    this.populateSelect(this.editMovementMode, movementModes);
    const currentTypeOptions = this.selection?.kind === 'obstacle' ? obstacleTypes : targetTypes;
    this.populateSelect(this.editType, currentTypeOptions);
  }

  private populateSelect(select: HTMLSelectElement, values: string[]): void {
    const previous = select.value;
    select.innerHTML = '';
    values.forEach((value) => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = translateDataValue(this.locale, value);
      select.appendChild(option);
    });
    if (values.includes(previous)) select.value = previous;
  }

  private getMiniMapSize(): { width: number; height: number; padding: number } {
    return { width: this.miniMapCanvas.width, height: this.miniMapCanvas.height, padding: 10 };
  }

  private drawMiniMapObject(
    ctx: CanvasRenderingContext2D,
    position: Position,
    radius: number,
    bounds: ReturnType<typeof resolveMiniMapBounds>,
    size: ReturnType<ViewerUI['getMiniMapSize']>,
    color: string
  ): void {
    const point = worldToMiniMap(position, bounds, size);
    const radiusPoint = worldToMiniMap({ x: position.x + radius, y: position.y, z: position.z }, bounds, size);
    const pixelRadius = Math.max(2, Math.abs(radiusPoint.x - point.x));
    ctx.fillStyle = color;
    ctx.globalAlpha = 0.78;
    ctx.beginPath();
    ctx.arc(point.x, point.y, pixelRadius, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
  }
}
