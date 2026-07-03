import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { formatDroneInfoLines, formatObstacleInfoLines, formatTargetInfoLines } from './entityLabel';
import { getTargetVisualState, normalizeCoveragePoints, normalizeCoverageSurfaces, normalizeTargetMotionPath, shouldRenderTargetMotionPath } from './taskVisuals';
import {
  getCoverageSurfaceY,
  getTargetBaseColor,
  getPolygonTargetPlacement,
  ROUND_TARGET_CENTER_Y,
  ROUND_TARGET_HEIGHT,
  TARGET_SURFACE_HEIGHT,
  toGroundShapePoint
} from './targetVisuals';
import { getObstacleBaseColor, getObstacleMaterialSettings, getObstacleVisualHeight, getPolygonObstaclePlacement } from './obstacleVisuals';
import { getTopViewCameraDistance, resolveSceneBounds } from './sceneBounds.ts';
import { DEFAULT_VISUAL_SCALE_SETTINGS, getAdaptiveBillboardScale, getAdaptiveDroneScale, type VisualScaleSettings } from './renderSettings.ts';
import { buildSelectionPolygonPoints, getLabelTextureMetrics, getTargetSelectionVisualKind, getUniformLabelBaseScale } from './selectionVisuals.ts';
import {
  buildRasterEps,
  buildRasterPdf,
  buildRasterSvg,
  getRasterMimeType,
  getScreenshotExtension,
  getScreenshotMimeType,
  normalizeScreenshotFormat,
  type ScreenshotFormat
} from './screenshotExport.ts';
import { getTopViewCameraUp, getWorldViewCameraUp } from './cameraOrientation.ts';
import { getSceneAxisEnd, sceneGroundToWorld, worldToScenePosition, worldYToSceneZ } from './coordinateSystem.ts';
import type { Locale } from './i18n.ts';
import { DEFAULT_LABELS_VISIBLE } from './viewerRuntime.ts';
import type {
  CameraMode,
  DroneState,
  ObstacleState,
  Position,
  SelectableKind,
  SelectionRef,
  TargetState,
  ViewerState
} from './types';

type SelectCallback = (selection: SelectionRef | null) => void;
type GroundClickCallback = (point: Position) => void;
type PointerWorldCallback = (point: Position | null) => void;
type ZoomScaleCallback = (scale: number) => void;
export type CoverageDisplayMode = 'surface' | 'points' | 'both';

type DroneActor = {
  group: THREE.Group;
  label: THREE.Sprite;
  altitudeLine: THREE.Line;
  targetPosition: THREE.Vector3;
  targetHeading: number;
  status: string;
  accentMaterial: THREE.MeshStandardMaterial;
  rotorGroups: THREE.Group[];
  selectionRadius: number;
};

const statusColors: Record<string, number> = {
  idle: 0x64748b,
  ready: 0x22c55e,
  taking_off: 0x06b6d4,
  flying: 0x3b82f6,
  moving: 0xf59e0b,
  hovering: 0x14b8a6,
  landing: 0xeab308,
  emergency: 0xef4444,
  offline: 0x334155
};

const COVERAGE_SURFACE_Y = getCoverageSurfaceY();
const SCREENSHOT_PIXEL_RATIO = 3;
const SCENE_CLEAR_COLOR = 0xd7e7f5;
const GROUND_EDGE_BUFFER = 1.2;
const MIN_ZOOM_SCALE = 0.4;
const MAX_ZOOM_SCALE = 5;

function toScenePosition(position: Position): THREE.Vector3 {
  return worldToScenePosition(position);
}

function toGroundVector2(point: Position, origin?: Position, scale = 1): THREE.Vector2 {
  const projected = toGroundShapePoint(point, origin);
  return new THREE.Vector2(projected.x * scale, projected.y * scale);
}

function disposeObject(object: THREE.Object3D): void {
  object.traverse((child) => {
    const mesh = child as THREE.Mesh;
    if (mesh.geometry) mesh.geometry.dispose();
    const material = mesh.material as THREE.Material | THREE.Material[] | undefined;
    if (Array.isArray(material)) {
      material.forEach((item) => item.dispose());
    } else if (material) {
      material.dispose();
    }
  });
}

function makeLabel(text: string | string[], color = '#dbeafe'): THREE.Sprite {
  const rawLines = Array.isArray(text) ? text : [text];
  const lines = rawLines.slice(0, 4);
  const multiLine = lines.length > 1;
  const canvas = document.createElement('canvas');
  const metrics = getLabelTextureMetrics(window.devicePixelRatio);
  canvas.width = metrics.backingWidth;
  canvas.height = metrics.backingHeight;
  canvas.style.width = `${metrics.cssWidth}px`;
  canvas.style.height = `${metrics.cssHeight}px`;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    ctx.setTransform(metrics.pixelRatio, 0, 0, metrics.pixelRatio, 0, 0);
    ctx.fillStyle = 'rgba(15,23,42,0.78)';
    ctx.fillRect(0, 0, metrics.cssWidth, metrics.cssHeight);
    ctx.strokeStyle = 'rgba(148,163,184,0.8)';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(1, 1, metrics.cssWidth - 2, metrics.cssHeight - 2);
    ctx.fillStyle = color;
    ctx.font = multiLine ? '600 22px system-ui, sans-serif' : '600 24px system-ui, sans-serif';
    ctx.textAlign = multiLine ? 'left' : 'center';
    ctx.textBaseline = 'middle';
    lines.forEach((line, index) => {
      const y = multiLine ? 30 + index * 30 : metrics.cssHeight / 2;
      ctx.fillText(line, multiLine ? 20 : metrics.cssWidth / 2, y, metrics.cssWidth - 40);
    });
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.generateMipmaps = false;
  texture.needsUpdate = true;
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
  const sprite = new THREE.Sprite(material);
  const baseScale = getUniformLabelBaseScale();
  sprite.scale.set(baseScale.width, baseScale.height, 1);
  sprite.userData.baseScale = sprite.scale.clone();
  return sprite;
}

function makeAxisLabel(text: string, color: string): THREE.Sprite {
  const canvas = document.createElement('canvas');
  const size = 96;
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = size * pixelRatio;
  canvas.height = size * pixelRatio;
  canvas.style.width = `${size}px`;
  canvas.style.height = `${size}px`;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    ctx.fillStyle = 'rgba(248,250,252,0.95)';
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, 34, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = 'rgba(15,23,42,0.28)';
    ctx.lineWidth = 4;
    ctx.stroke();
    ctx.fillStyle = color;
    ctx.font = '900 42px system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, size / 2, size / 2 + 1);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.generateMipmaps = false;
  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: false,
    depthWrite: false
  });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(34, 34, 1);
  sprite.userData.baseScale = sprite.scale.clone();
  sprite.userData.skipAdaptiveScale = true;
  sprite.renderOrder = 120;
  return sprite;
}

function makeAxisArrow(axis: 'x' | 'y' | 'z', length: number, color: number): THREE.Group {
  const group = new THREE.Group();
  const direction = getSceneAxisEnd(axis, 1).normalize();
  const shaftRadius = THREE.MathUtils.clamp(length * 0.018, 1.8, 3.8);
  const headLength = length * 0.18;
  const shaftLength = Math.max(1, length - headLength);
  const material = new THREE.MeshBasicMaterial({
    color,
    depthTest: false,
    depthWrite: false
  });
  const quaternion = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);

  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(shaftRadius, shaftRadius, shaftLength, 16), material);
  shaft.quaternion.copy(quaternion);
  shaft.position.copy(direction.clone().multiplyScalar(shaftLength / 2));
  shaft.renderOrder = 110;
  shaft.frustumCulled = false;
  group.add(shaft);

  const head = new THREE.Mesh(new THREE.ConeGeometry(shaftRadius * 3.2, headLength, 24), material);
  head.quaternion.copy(quaternion);
  head.position.copy(direction.clone().multiplyScalar(shaftLength + headLength / 2));
  head.renderOrder = 111;
  head.frustumCulled = false;
  group.add(head);

  return group;
}

function makeSelectionLine(points: THREE.Vector3[]): THREE.LineLoop {
  const material = new THREE.LineBasicMaterial({
    color: 0xfacc15,
    transparent: true,
    opacity: 0.96,
    depthTest: false,
    depthWrite: false
  });
  const line = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(points), material);
  line.renderOrder = 80;
  return line;
}

function makeCircularSelectionHighlight(radius: number, y: number, position?: THREE.Vector3): THREE.Mesh {
  const mesh = new THREE.Mesh(
    new THREE.TorusGeometry(Math.max(1, radius), 0.28, 8, 96),
    new THREE.MeshBasicMaterial({
      color: 0xfacc15,
      transparent: true,
      opacity: 0.96,
      depthTest: false,
      depthWrite: false
    })
  );
  mesh.rotation.x = Math.PI / 2;
  mesh.position.y = y;
  if (position) mesh.position.copy(position).setY(y);
  mesh.renderOrder = 80;
  return mesh;
}

function configureGrid(grid: THREE.GridHelper): void {
  grid.renderOrder = 2;
  const materials = Array.isArray(grid.material) ? grid.material : [grid.material];
  materials.forEach((material) => {
    material.depthWrite = false;
    material.transparent = true;
    material.opacity = 0.58;
  });
}

function applyStablePlaneMaterial(material: THREE.Material, renderOrder: number): void {
  material.depthWrite = true;
  material.depthTest = true;
  material.polygonOffset = true;
  material.polygonOffsetFactor = -2;
  material.polygonOffsetUnits = -2;
  material.needsUpdate = true;
  material.userData.renderOrder = renderOrder;
}

export class ViewerScene {
  private readonly host: HTMLElement;
  private readonly renderer: THREE.WebGLRenderer;
  private readonly scene: THREE.Scene;
  private readonly camera: THREE.PerspectiveCamera;
  private readonly controls: OrbitControls;
  private readonly clock = new THREE.Clock();
  private readonly raycaster = new THREE.Raycaster();
  private readonly pointer = new THREE.Vector2();
  private readonly selectable: THREE.Object3D[] = [];
  private readonly root = new THREE.Group();
  private readonly droneActors = new Map<string, DroneActor>();
  private readonly trailLines = new Map<string, THREE.Line>();
  private selectionHighlight: THREE.Object3D | null = null;
  private readonly movePreview = new THREE.Mesh(
    new THREE.CylinderGeometry(6, 6, 0.28, 48),
    new THREE.MeshBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.46 })
  );
  private readonly axisGuide = new THREE.Group();
  private readonly ground = new THREE.Mesh(
    new THREE.PlaneGeometry(1024, 768),
    new THREE.MeshStandardMaterial({ color: 0x4f6f46, roughness: 0.9 })
  );
  private readonly grid = new THREE.GridHelper(1024, 32, 0x94a3b8, 0x475569);
  private animationFrame = 0;
  private state: ViewerState | null = null;
  private selected: SelectionRef | null = null;
  private moveMode = false;
  private directClickMove = false;
  private cameraMode: CameraMode = 'free';
  private selectedDroneId: string | null = null;
  private trailLength = 80;
  private labelsVisible = DEFAULT_LABELS_VISIBLE;
  private coverageDisplayMode: CoverageDisplayMode = 'surface';
  private targetMotionVisible = false;
  private visualScaleSettings: VisualScaleSettings = { ...DEFAULT_VISUAL_SCALE_SETTINGS };
  private locale: Locale = 'en-US';
  private selectionCycleKey = '';
  private selectionCycleIndex = 0;
  private selectionCycleCandidates: SelectionRef[] = [];
  private onSelect: SelectCallback = () => undefined;
  private onGroundClick: GroundClickCallback = () => undefined;
  private onPointerWorld: PointerWorldCallback = () => undefined;
  private onZoomScale: ZoomScaleCallback = () => undefined;
  private lastNotifiedZoomScale = 0;

  constructor(host: HTMLElement) {
    this.host = host;
    this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, logarithmicDepthBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.host.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(SCENE_CLEAR_COLOR);
    this.scene.fog = new THREE.Fog(SCENE_CLEAR_COLOR, 4200, 14000);

    this.camera = new THREE.PerspectiveCamera(55, 1, 0.1, 5000);
    this.camera.position.set(260, 240, 360);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.target.set(250, 0, 180);

    const hemi = new THREE.HemisphereLight(0xffffff, 0x4f6f46, 1.2);
    this.scene.add(hemi);
    const sun = new THREE.DirectionalLight(0xffffff, 2);
    sun.position.set(220, 420, 150);
    sun.castShadow = true;
    this.scene.add(sun);

    this.ground.rotation.x = -Math.PI / 2;
    this.ground.receiveShadow = true;
    this.ground.renderOrder = 0;
    this.grid.position.y = 0.32;
    configureGrid(this.grid);
    this.axisGuide.name = 'WorldAxisGuide';
    this.axisGuide.frustumCulled = false;
    this.movePreview.position.y = 0.14;
    this.movePreview.visible = false;
    this.root.add(this.movePreview);
    this.scene.add(this.ground, this.grid, this.axisGuide, this.root);

    this.renderer.domElement.addEventListener('pointerdown', (event) => this.handlePointerDown(event));
    this.renderer.domElement.addEventListener('pointermove', (event) => this.handlePointerMove(event));
    window.addEventListener('resize', () => this.resize());
    this.resize();
    this.animate();
  }

  dispose(): void {
    cancelAnimationFrame(this.animationFrame);
    this.renderer.domElement.remove();
    this.renderer.dispose();
  }

  setCallbacks(onSelect: SelectCallback, onGroundClick: GroundClickCallback, onPointerWorld?: PointerWorldCallback, onZoomScale?: ZoomScaleCallback): void {
    this.onSelect = onSelect;
    this.onGroundClick = onGroundClick;
    this.onPointerWorld = onPointerWorld || (() => undefined);
    this.onZoomScale = onZoomScale || (() => undefined);
  }

  setMoveMode(enabled: boolean): void {
    this.moveMode = enabled;
    this.movePreview.visible = false;
  }

  setDirectClickMove(enabled: boolean): void {
    this.directClickMove = enabled;
  }

  setCameraMode(mode: CameraMode): void {
    this.cameraMode = mode;
    if (mode === 'top') {
      this.fitTopView();
    } else if (mode === 'fit') {
      this.fitAll();
      this.cameraMode = 'free';
    } else if (mode === 'free') {
      this.camera.up.copy(getWorldViewCameraUp());
      this.controls.enabled = true;
    }
  }

  setTrailLength(length: number): void {
    this.trailLength = length;
    if (this.state) this.renderState(this.state);
  }

  setLabelsVisible(visible: boolean): void {
    this.labelsVisible = visible;
    if (this.state) this.renderState(this.state);
  }

  setLocale(locale: Locale): void {
    this.locale = locale;
    if (this.state) this.renderState(this.state);
  }

  clearSelection(): void {
    this.selected = null;
    this.selectedDroneId = null;
    this.selectionCycleKey = '';
    this.selectionCycleIndex = 0;
    this.selectionCycleCandidates = [];
    if (this.state) this.renderState(this.state);
    this.onSelect(null);
  }

  setSelection(selection: SelectionRef | null): void {
    this.selected = selection;
    this.selectedDroneId = selection?.kind === 'drone' ? selection.id : null;
    this.selectionCycleKey = '';
    this.selectionCycleIndex = 0;
    this.selectionCycleCandidates = selection ? [selection] : [];
    if (this.state) this.renderState(this.state);
    this.onSelect(selection);
  }

  setCoverageDisplayMode(mode: CoverageDisplayMode): void {
    this.coverageDisplayMode = mode;
    if (this.state) this.renderState(this.state);
  }

  setTargetMotionVisible(visible: boolean): void {
    this.targetMotionVisible = visible;
    if (this.state) this.renderState(this.state);
  }

  setVisualScaleSettings(settings: VisualScaleSettings): void {
    this.visualScaleSettings = settings;
    if (this.state) this.renderState(this.state);
  }

  cycleSelection(): SelectionRef | null {
    if (!this.selected || this.selectionCycleCandidates.length <= 1) return null;
    const currentIndex = this.selectionCycleCandidates.findIndex((item) => item.kind === this.selected?.kind && item.id === this.selected?.id);
    const nextSelection = this.selectionCycleCandidates[((currentIndex < 0 ? -1 : currentIndex) + 1) % this.selectionCycleCandidates.length];
    this.selected = nextSelection;
    this.selectedDroneId = nextSelection.kind === 'drone' ? nextSelection.id : null;
    if (this.state) this.renderState(this.state);
    this.onSelect(nextSelection);
    return nextSelection;
  }

  panBy(x: number, z: number): void {
    const offset = new THREE.Vector3(x, 0, -z);
    this.camera.position.add(offset);
    this.controls.target.add(offset);
    this.controls.update();
  }

  zoomBy(scale: number): void {
    this.setZoomScale(this.getZoomScale() / scale);
  }

  setZoomScale(scale: number): void {
    const safeScale = THREE.MathUtils.clamp(scale, MIN_ZOOM_SCALE, MAX_ZOOM_SCALE);
    const direction = this.camera.position.clone().sub(this.controls.target);
    if (direction.lengthSq() <= 0.0001) return;
    const baseDistance = this.state ? resolveSceneBounds(this.state).size : 1024;
    direction.setLength(baseDistance / safeScale);
    this.camera.position.copy(this.controls.target.clone().add(direction));
    this.controls.update();
    this.notifyZoomScaleChanged(true);
  }

  resetView(): void {
    this.fitAll();
  }

  async exportScreenshot(formatValue: string): Promise<void> {
    const format = normalizeScreenshotFormat(formatValue);
    const { blob, extension } = await this.captureScreenshot(format);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    link.href = url;
    link.download = `multiuav-3d-${timestamp}.${extension}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  getViewCenter(): Position {
    return {
      x: this.controls.target.x,
      y: -this.controls.target.z,
      z: this.controls.target.y
    };
  }

  setViewCenter(position: Position): void {
    const nextTarget = new THREE.Vector3(position.x, this.controls.target.y, worldYToSceneZ(position.y));
    const offset = nextTarget.clone().sub(this.controls.target);
    this.controls.target.copy(nextTarget);
    this.camera.position.add(offset);
    this.controls.update();
  }

  renderState(state: ViewerState): void {
    const wasEmpty = !this.state;
    this.state = state;
    this.selectable.length = 0;
    this.updateGround(state);
    this.syncDrones(state);
    this.clearStaticObjects();
    state.obstacles.forEach((obstacle) => this.addObstacle(obstacle));
    state.targets.forEach((target) => this.addTarget(target));
    this.addTaskVisuals(state);
    this.droneActors.forEach((actor) => this.selectable.push(actor.group));
    this.refreshSelectionHighlight();
    if (this.cameraMode === 'follow' && this.selectedDroneId) {
      this.followDrone(this.selectedDroneId);
    } else if (wasEmpty) {
      this.fitAll();
    }
  }

  getSelectedDrone(): DroneState | null {
    if (!this.state || !this.selected || this.selected.kind !== 'drone') return null;
    return this.state.drones.find((drone) => drone.id === this.selected?.id) || null;
  }

  private resize(): void {
    const width = Math.max(1, this.host.clientWidth);
    const height = Math.max(1, this.host.clientHeight);
    this.renderer.setSize(width, height);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }

  private animate(): void {
    this.animationFrame = requestAnimationFrame(() => this.animate());
    this.updateDroneActors(this.clock.getDelta());
    this.updateAdaptiveVisualScale();
    this.controls.update();
    this.clampCameraDistanceToZoomBounds();
    this.notifyZoomScaleChanged();
    this.renderer.render(this.scene, this.camera);
  }

  private getZoomBaseDistance(): number {
    return this.state ? resolveSceneBounds(this.state).size : 1024;
  }

  private clampCameraDistanceToZoomBounds(): void {
    const direction = this.camera.position.clone().sub(this.controls.target);
    const distance = direction.length();
    if (distance <= 0.0001) return;
    const baseDistance = this.getZoomBaseDistance();
    const minDistance = baseDistance / MAX_ZOOM_SCALE;
    const maxDistance = baseDistance / MIN_ZOOM_SCALE;
    const clampedDistance = THREE.MathUtils.clamp(distance, minDistance, maxDistance);
    if (Math.abs(clampedDistance - distance) < 0.001) return;
    direction.setLength(clampedDistance);
    this.camera.position.copy(this.controls.target.clone().add(direction));
  }

  private getZoomScale(): number {
    const baseDistance = this.getZoomBaseDistance();
    const distance = Math.max(1, this.camera.position.distanceTo(this.controls.target));
    return THREE.MathUtils.clamp(baseDistance / distance, MIN_ZOOM_SCALE, MAX_ZOOM_SCALE);
  }

  private notifyZoomScaleChanged(force = false): void {
    const scale = this.getZoomScale();
    if (!force && Math.abs(scale - this.lastNotifiedZoomScale) < 0.005) return;
    this.lastNotifiedZoomScale = scale;
    this.onZoomScale(scale);
  }

  private async captureScreenshot(format: ScreenshotFormat): Promise<{ blob: Blob; extension: string }> {
    const originalPixelRatio = this.renderer.getPixelRatio();
    const originalSize = this.renderer.getSize(new THREE.Vector2());
    const originalAspect = this.camera.aspect;
    try {
      this.renderer.setPixelRatio(Math.max(originalPixelRatio, SCREENSHOT_PIXEL_RATIO));
      this.renderer.setSize(originalSize.x, originalSize.y, false);
      this.camera.aspect = originalAspect;
      this.camera.updateProjectionMatrix();

      this.controls.update();
      this.renderer.render(this.scene, this.camera);
      const canvas = this.renderer.domElement;
      const width = canvas.width;
      const height = canvas.height;
      const mime = getRasterMimeType(format);
      const dataUrl = canvas.toDataURL(mime, 0.95);

      if (format === 'svg') {
        return {
          blob: new Blob([buildRasterSvg(dataUrl, width, height)], { type: getScreenshotMimeType(format) }),
          extension: getScreenshotExtension(format)
        };
      }

      if (format === 'eps') {
        const copy = document.createElement('canvas');
        copy.width = width;
        copy.height = height;
        const context = copy.getContext('2d');
        if (!context) throw new Error('Cannot create EPS export canvas.');
        context.drawImage(canvas, 0, 0);
        const pixels = context.getImageData(0, 0, width, height).data;
        return {
          blob: new Blob([buildRasterEps(pixels, width, height)], { type: getScreenshotMimeType(format) }),
          extension: getScreenshotExtension(format)
        };
      }

      if (format === 'pdf') {
        const pdfBytes = buildRasterPdf(dataUrl, width, height);
        const pdfBuffer = new ArrayBuffer(pdfBytes.byteLength);
        new Uint8Array(pdfBuffer).set(pdfBytes);
        return {
          blob: new Blob([pdfBuffer], { type: getScreenshotMimeType(format) }),
          extension: getScreenshotExtension(format)
        };
      }

      const blob = await new Promise<Blob>((resolve, reject) => {
        canvas.toBlob((value) => (value ? resolve(value) : reject(new Error('Screenshot export failed.'))), mime, 0.95);
      });
      return { blob, extension: getScreenshotExtension(format) };
    } finally {
      this.renderer.setPixelRatio(originalPixelRatio);
      this.renderer.setSize(originalSize.x, originalSize.y, false);
      this.camera.aspect = originalAspect;
      this.camera.updateProjectionMatrix();
    }
  }

  private clearRoot(): void {
    [...this.root.children].forEach((child) => {
      this.root.remove(child);
      disposeObject(child);
    });
  }

  private updateGround(state: ViewerState): void {
    const bounds = resolveSceneBounds(state);
    const size = bounds.size * GROUND_EDGE_BUFFER;
    this.ground.geometry.dispose();
    this.ground.geometry = new THREE.PlaneGeometry(size, size);
    this.ground.position.set(bounds.centerX, 0, worldYToSceneZ(bounds.centerY));
    this.grid.geometry.dispose();
    this.grid.geometry = new THREE.BufferGeometry().copy(new THREE.GridHelper(size, Math.max(12, Math.round(size / 32))).geometry);
    this.grid.position.set(bounds.centerX, 0.32, worldYToSceneZ(bounds.centerY));
    configureGrid(this.grid);
    this.updateAxisGuide(bounds, size);
  }

  private updateAxisGuide(bounds: ReturnType<typeof resolveSceneBounds>, groundSize: number): void {
    [...this.axisGuide.children].forEach((child) => {
      this.axisGuide.remove(child);
      disposeObject(child);
    });
    const length = THREE.MathUtils.clamp(bounds.size * 0.09, 72, 150);
    const inset = Math.max(length * 0.72, bounds.size * 0.045);
    const groundMinX = bounds.centerX - groundSize / 2;
    const groundMinY = bounds.centerY - groundSize / 2;
    const origin = new THREE.Vector3(groundMinX + inset, 4, worldYToSceneZ(groundMinY + inset));
    this.axisGuide.position.copy(origin);

    const axes: Array<{ axis: 'x' | 'y' | 'z'; label: string; color: number; textColor: string }> = [
      { axis: 'x', label: 'X', color: 0xef4444, textColor: '#dc2626' },
      { axis: 'y', label: 'Y', color: 0x22c55e, textColor: '#16a34a' },
      { axis: 'z', label: 'Z', color: 0x38bdf8, textColor: '#0284c7' }
    ];

    axes.forEach(({ axis, label, color, textColor }) => {
      const arrow = makeAxisArrow(axis, length, color);
      this.axisGuide.add(arrow);
      const labelSprite = makeAxisLabel(label, textColor);
      labelSprite.position.copy(getSceneAxisEnd(axis, length * 1.18));
      this.axisGuide.add(labelSprite);
    });
  }

  private syncDrones(state: ViewerState): void {
    const activeIds = new Set(state.drones.map((drone) => drone.id));
    for (const [id, actor] of this.droneActors) {
      if (!activeIds.has(id)) {
        this.root.remove(actor.group);
        disposeObject(actor.group);
        this.droneActors.delete(id);
      }
    }
    for (const [id, trail] of this.trailLines) {
      if (!activeIds.has(id)) {
        this.root.remove(trail);
        disposeObject(trail);
        this.trailLines.delete(id);
      }
    }
    state.drones.forEach((drone) => this.upsertDrone(drone, state.paths[drone.id] || []));
  }

  private upsertDrone(drone: DroneState, path: Position[]): void {
    let actor = this.droneActors.get(drone.id);
    if (!actor) {
      actor = this.createDroneActor(drone);
      this.droneActors.set(drone.id, actor);
      this.root.add(actor.group);
    }

    actor.targetPosition.copy(toScenePosition(drone.position));
    actor.targetHeading = -THREE.MathUtils.degToRad(drone.heading || 0);
    actor.status = drone.status;
    const color = statusColors[drone.status] || 0x60a5fa;
    actor.accentMaterial.color.setHex(color);
    actor.accentMaterial.emissive.setHex(color);
    actor.accentMaterial.emissiveIntensity = drone.status === 'emergency' ? 0.42 : 0.18;

    const altitudePoints = [new THREE.Vector3(0, -drone.position.z, 0), new THREE.Vector3(0, 0, 0)];
    actor.altitudeLine.geometry.dispose();
    actor.altitudeLine.geometry = new THREE.BufferGeometry().setFromPoints(altitudePoints);

    this.updateDroneLabel(actor, drone);

    this.updateTrail(drone.id, path);
  }

  private createDroneActor(drone: DroneState): DroneActor {
    const group = new THREE.Group();
    group.position.copy(toScenePosition(drone.position));
    group.rotation.y = -THREE.MathUtils.degToRad(drone.heading || 0);
    group.userData = { selectable: true, kind: 'drone' satisfies SelectableKind, id: drone.id };

    const color = statusColors[drone.status] || 0x60a5fa;
    const bodyMaterial = new THREE.MeshStandardMaterial({ color: 0xe5e7eb, metalness: 0.32, roughness: 0.34 });
    const darkMaterial = new THREE.MeshStandardMaterial({ color: 0x111827, metalness: 0.18, roughness: 0.48 });
    const accentMaterial = new THREE.MeshStandardMaterial({
      color,
      emissive: color,
      emissiveIntensity: drone.status === 'emergency' ? 0.42 : 0.18,
      metalness: 0.2,
      roughness: 0.38
    });
    const glassMaterial = new THREE.MeshStandardMaterial({
      color: 0x0ea5e9,
      transparent: true,
      opacity: 0.72,
      metalness: 0.05,
      roughness: 0.18
    });
    const propMaterial = new THREE.MeshStandardMaterial({
      color: 0x020617,
      transparent: true,
      opacity: 0.42,
      side: THREE.DoubleSide,
      roughness: 0.28
    });
    const ringMaterial = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.2, roughness: 0.42 });
    const rotorGroups: THREE.Group[] = [];

    const fuselage = new THREE.Mesh(new THREE.BoxGeometry(6.2, 2.2, 10), bodyMaterial);
    fuselage.position.y = 0.35;
    fuselage.castShadow = true;
    group.add(fuselage);

    const nose = new THREE.Mesh(new THREE.ConeGeometry(2.9, 4.8, 4), bodyMaterial);
    nose.rotation.x = -Math.PI / 2;
    nose.position.set(0, 0.35, -7.4);
    nose.castShadow = true;
    group.add(nose);

    const canopy = new THREE.Mesh(new THREE.SphereGeometry(2.1, 20, 10), glassMaterial);
    canopy.scale.set(1.15, 0.36, 0.82);
    canopy.position.set(0, 1.72, -1.8);
    canopy.castShadow = true;
    group.add(canopy);

    const statusLight = new THREE.Mesh(new THREE.SphereGeometry(0.55, 16, 8), accentMaterial);
    statusLight.position.set(0, 1.35, -9.75);
    group.add(statusLight);

    const tailAccent = new THREE.Mesh(new THREE.BoxGeometry(3.6, 0.22, 1.1), accentMaterial);
    tailAccent.position.set(0, 1.63, 4.4);
    group.add(tailAccent);

    const cameraPod = new THREE.Mesh(new THREE.SphereGeometry(1.05, 16, 8), darkMaterial);
    cameraPod.scale.set(1, 0.72, 0.86);
    cameraPod.position.set(0, -1.15, -4.3);
    cameraPod.castShadow = true;
    group.add(cameraPod);

    const armA = new THREE.Mesh(new THREE.BoxGeometry(1.15, 0.7, 34), darkMaterial);
    armA.rotation.y = Math.PI / 4;
    const armB = armA.clone();
    armB.rotation.y = -Math.PI / 4;
    group.add(armA, armB);

    for (const [x, z] of [[-12, -12], [12, -12], [-12, 12], [12, 12]]) {
      const rotorGroup = new THREE.Group();
      rotorGroup.position.set(x, 1.34, z);
      rotorGroups.push(rotorGroup);

      const motor = new THREE.Mesh(new THREE.CylinderGeometry(1.8, 2.15, 1.25, 24), darkMaterial);
      motor.position.set(x, 0.55, z);
      motor.castShadow = true;
      group.add(motor);

      const rotorRing = new THREE.Mesh(new THREE.TorusGeometry(4.15, 0.16, 8, 40), ringMaterial);
      rotorRing.rotation.x = Math.PI / 2;
      rotorRing.position.set(x, 1.28, z);
      rotorRing.castShadow = true;
      group.add(rotorRing);

      const bladeA = new THREE.Mesh(new THREE.BoxGeometry(8.4, 0.08, 0.62), propMaterial);
      bladeA.rotation.y = x * z > 0 ? 0.18 : -0.18;
      const bladeB = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.08, 8.4), propMaterial);
      bladeB.rotation.y = x * z > 0 ? 0.18 : -0.18;
      bladeB.position.y = 0.02;
      rotorGroup.add(bladeA, bladeB);
      group.add(rotorGroup);
    }

    for (const x of [-3.8, 3.8]) {
      const skid = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 10.2, 10), darkMaterial);
      skid.rotation.x = Math.PI / 2;
      skid.position.set(x, -2.25, 0);
      skid.castShadow = true;
      group.add(skid);

      for (const z of [-3.9, 3.9]) {
        const strut = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 2.2, 8), darkMaterial);
        strut.position.set(x, -1.18, z);
        strut.castShadow = true;
        group.add(strut);
      }
    }

    const line = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, -drone.position.z, 0), new THREE.Vector3(0, 0, 0)]),
      new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.7 })
    );
    group.add(line);
    const label = makeLabel(formatDroneInfoLines(drone, false, this.locale));
    label.position.set(11, 20, 0);
    group.add(label);

    return {
      group,
      label,
      altitudeLine: line,
      targetPosition: toScenePosition(drone.position),
      targetHeading: group.rotation.y,
      status: drone.status,
      accentMaterial,
      rotorGroups,
      selectionRadius: 16
    };
  }

  private updateDroneLabel(actor: DroneActor, drone: DroneState): void {
    const selected = this.selected?.kind === 'drone' && this.selected.id === drone.id;
    const label = makeLabel(formatDroneInfoLines(drone, selected, this.locale));
    actor.group.remove(actor.label);
    disposeObject(actor.label);
    actor.label = label;
    actor.label.visible = this.labelsVisible;
    actor.label.position.set(selected ? 13 : 11, selected ? 23 : 20, 0);
    actor.group.add(actor.label);
  }

  private refreshDroneLabels(): void {
    if (!this.state) return;
    for (const drone of this.state.drones) {
      const actor = this.droneActors.get(drone.id);
      if (actor) this.updateDroneLabel(actor, drone);
    }
  }

  private updateTrail(droneId: string, path: Position[]): void {
    const trail = this.getTrailPoints(path).map(toScenePosition);
    const existingTrail = this.trailLines.get(droneId);
    if (trail.length <= 1) {
      if (existingTrail) {
        this.root.remove(existingTrail);
        disposeObject(existingTrail);
        this.trailLines.delete(droneId);
      }
      return;
    }

    if (existingTrail) {
      existingTrail.geometry.dispose();
      existingTrail.geometry = new THREE.BufferGeometry().setFromPoints(trail);
      const material = existingTrail.material as THREE.LineBasicMaterial;
      material.color.setHex(0xe5e7eb);
      material.transparent = true;
      material.opacity = 0.24;
      material.depthWrite = false;
      material.depthTest = true;
      material.needsUpdate = true;
      return;
    }

    const trailLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(trail),
      new THREE.LineBasicMaterial({
        color: 0xe5e7eb,
        transparent: true,
        opacity: 0.24,
        depthWrite: false,
        depthTest: true
      })
    );
    this.trailLines.set(droneId, trailLine);
    this.root.add(trailLine);
  }

  private getTrailPoints(path: Position[]): Position[] {
    if (this.trailLength === 0) return [];
    if (this.trailLength === -1) return path;
    if (this.trailLength === 1) return path.slice(-2);
    return path.slice(-this.trailLength);
  }

  private updateDroneActors(deltaSeconds: number): void {
    for (const actor of this.droneActors.values()) {
      actor.group.position.lerp(actor.targetPosition, Math.min(1, deltaSeconds * 6));
      actor.group.rotation.y = THREE.MathUtils.lerp(actor.group.rotation.y, actor.targetHeading, Math.min(1, deltaSeconds * 8));

      const rotorSpeed = this.getRotorSpeed(actor.status);
      actor.rotorGroups.forEach((rotorGroup, index) => {
        rotorGroup.rotation.y += rotorSpeed * deltaSeconds * (index % 2 === 0 ? 1 : -1);
      });
    }
  }

  private updateAdaptiveVisualScale(): void {
    const cameraPosition = this.camera.position;
    for (const actor of this.droneActors.values()) {
      const distance = cameraPosition.distanceTo(actor.group.position);
      actor.group.scale.setScalar(getAdaptiveDroneScale(distance) * this.visualScaleSettings.drone);
    }
    this.scene.traverse((object) => {
      if (!(object instanceof THREE.Sprite) || !object.userData.baseScale || object.userData.skipAdaptiveScale) return;
      const baseScale = object.userData.baseScale as THREE.Vector3;
      const worldPosition = new THREE.Vector3();
      const parentWorldScale = new THREE.Vector3();
      object.getWorldPosition(worldPosition);
      object.parent?.getWorldScale(parentWorldScale);
      const scale = getAdaptiveBillboardScale(cameraPosition.distanceTo(worldPosition));
      const parentScale = parentWorldScale.lengthSq() > 0 ? parentWorldScale.x : 1;
      object.scale.copy(baseScale).multiplyScalar((scale * this.visualScaleSettings.label) / parentScale);
    });
  }

  private getRotorSpeed(status: string): number {
    if (['offline', 'idle'].includes(status)) return 0;
    if (status === 'ready') return 2;
    if (['taking_off', 'landing'].includes(status)) return 18;
    if (['flying', 'moving'].includes(status)) return 28;
    if (status === 'hovering') return 22;
    return 8;
  }

  private clearStaticObjects(): void {
    this.clearSelectionHighlight();
    const persistent = new Set<THREE.Object3D>([this.movePreview]);
    this.droneActors.forEach((actor) => persistent.add(actor.group));
    this.trailLines.forEach((trail) => persistent.add(trail));
    [...this.root.children].forEach((child) => {
      if (!persistent.has(child)) {
        this.root.remove(child);
        disposeObject(child);
      }
    });
  }

  private clearSelectionHighlight(): void {
    if (!this.selectionHighlight) return;
    this.selectionHighlight.removeFromParent();
    disposeObject(this.selectionHighlight);
    this.selectionHighlight = null;
  }

  private refreshSelectionHighlight(): void {
    this.clearSelectionHighlight();
    if (!this.selected) {
      return;
    }

    const selectedObject = this.selectable.find((item) => item.userData.kind === this.selected?.kind && item.userData.id === this.selected?.id);
    if (!selectedObject) {
      return;
    }

    const shapeHighlight = this.createSelectionHighlight(selectedObject);
    const box = new THREE.Box3().setFromObject(selectedObject);
    const size = new THREE.Vector3();
    box.getSize(size);
    const radius = this.selected.kind === 'drone' ? 18 : Math.max(9, size.x * 0.5, size.z * 0.5) + 3;
    const worldCenter = new THREE.Vector3();
    selectedObject.getWorldPosition(worldCenter);

    this.selectionHighlight = shapeHighlight || makeCircularSelectionHighlight(radius, this.selected.kind === 'drone' ? Math.max(2.8, worldCenter.y + 3.2) : 1.25, worldCenter);
    this.root.add(this.selectionHighlight);
  }

  private createSelectionHighlight(selectedObject: THREE.Object3D): THREE.Object3D | null {
    if (!this.state || !this.selected) return null;
    if (this.selected.kind === 'target') {
      const target = this.state.targets.find((item) => item.id === this.selected?.id);
      if (!target || getTargetSelectionVisualKind(target) !== 'polygon' || !target.vertices) return null;
      const points = buildSelectionPolygonPoints(target.vertices, target.position)
        .map((point) => new THREE.Vector3(
          target.position.x + point.x * this.visualScaleSettings.target,
          1.35,
          worldYToSceneZ(target.position.y + point.y * this.visualScaleSettings.target)
        ));
      return makeSelectionLine(points);
    }
    if (this.selected.kind === 'obstacle') {
      const obstacle = this.state.obstacles.find((item) => item.id === this.selected?.id);
      if (!obstacle || obstacle.type !== 'polygon' || !obstacle.vertices || obstacle.vertices.length < 3) return null;
      const points = buildSelectionPolygonPoints(obstacle.vertices, obstacle.position)
        .map((point) => new THREE.Vector3(
          obstacle.position.x + point.x * this.visualScaleSettings.obstacle,
          getObstacleVisualHeight(obstacle.height) * this.visualScaleSettings.obstacle + 1.5,
          worldYToSceneZ(obstacle.position.y + point.y * this.visualScaleSettings.obstacle)
        ));
      return makeSelectionLine(points);
    }
    void selectedObject;
    return null;
  }

  private addTarget(target: TargetState): void {
    const group = new THREE.Group();
    group.userData = { selectable: true, kind: 'target' satisfies SelectableKind, id: target.id };
    group.position.copy(toScenePosition(target.position));
    const selected = this.selected?.kind === 'target' && this.selected.id === target.id;
    const visualState = this.state ? getTargetVisualState(target, this.state, this.locale) : { color: getTargetBaseColor(target.type), label: this.locale === 'zh-CN' ? '目标' : 'Target', emphasis: 'normal' as const };
    const color = getTargetBaseColor(target.type);
    const material = new THREE.MeshStandardMaterial({
      color,
      transparent: true,
      opacity: 0.84,
      roughness: 0.74,
      metalness: 0.02
    });
    applyStablePlaneMaterial(material, 4);
    if (target.type === 'polygon' && target.vertices && target.vertices.length >= 3) {
      const shape = new THREE.Shape(target.vertices.map((point) => toGroundVector2(point, target.position, this.visualScaleSettings.target)));
      const mesh = new THREE.Mesh(
        new THREE.ExtrudeGeometry(shape, { depth: TARGET_SURFACE_HEIGHT, bevelEnabled: false }),
        material
      );
      const placement = getPolygonTargetPlacement();
      mesh.rotation.x = placement.rotationX;
      mesh.position.y = placement.positionY;
      mesh.renderOrder = 4;
      group.add(mesh);
    } else {
      const radius = (target.radius || 6) * this.visualScaleSettings.target;
      const disk = new THREE.Mesh(
        new THREE.CylinderGeometry(radius, radius, ROUND_TARGET_HEIGHT, 48),
        material
      );
      disk.position.y = ROUND_TARGET_CENTER_Y;
      disk.renderOrder = 4;
      group.add(disk);
    }
    if (this.labelsVisible) {
      const taskLabel = this.locale === 'zh-CN' ? `任务状态：${visualState.label}` : `Task Status: ${visualState.label}`;
      const label = makeLabel(selected ? [...formatTargetInfoLines(target, true, this.locale), taskLabel] : [target.name, visualState.label], '#fef3c7');
      label.position.set(10, selected ? 17 : 12, 0);
      group.add(label);
    }
    this.root.add(group);
    this.selectable.push(group);
  }

  private addTaskVisuals(state: ViewerState): void {
    state.targets.forEach((target) => {
      this.addCoverageLayer(state, target);
      if (shouldRenderTargetMotionPath(target, this.targetMotionVisible)) {
        this.addTargetMotionPath(target);
      }
    });
  }

  private addCoverageLayer(state: ViewerState, target: TargetState): void {
    const coverageSurfaces = normalizeCoverageSurfaces(state, target.id);
    const showSurfaces = this.coverageDisplayMode !== 'points';
    const showPoints = this.coverageDisplayMode !== 'surface';
    if (coverageSurfaces.length > 0 && showSurfaces) {
      const material = new THREE.MeshBasicMaterial({
        color: 0x00e676,
        transparent: true,
        opacity: 0.9,
        side: THREE.DoubleSide
      });
      applyStablePlaneMaterial(material, 5);
      material.depthWrite = false;
      material.polygonOffsetFactor = -4;
      material.polygonOffsetUnits = -4;
      coverageSurfaces.forEach((surface, index) => {
        const shape = new THREE.Shape(surface.outer.map((point) => toGroundVector2(point)));
        shape.holes = (surface.holes || []).map((hole) => new THREE.Path(hole.map((point) => toGroundVector2(point))));
        const mesh = new THREE.Mesh(new THREE.ShapeGeometry(shape), material);
        mesh.name = `coverage-surface-${target.id}-${index}`;
        mesh.rotation.x = -Math.PI / 2;
        mesh.position.y = COVERAGE_SURFACE_Y;
        mesh.renderOrder = 8;
        this.root.add(mesh);
      });
      if (!showPoints) return;
    }

    if (!showPoints) return;
    const coveragePoints = normalizeCoveragePoints(state, target.id);
    if (coveragePoints.length === 0) return;

    const visiblePoints = coveragePoints.slice(-2000);
    const geometry = new THREE.CircleGeometry(Math.max(1.8, Math.min(4.5, (target.radius || 24) * 0.08)), 14);
    geometry.rotateX(-Math.PI / 2);
    const material = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.34,
      depthWrite: true,
      depthTest: true,
      polygonOffset: true,
      polygonOffsetFactor: -3,
      polygonOffsetUnits: -3
    });
    const mesh = new THREE.InstancedMesh(geometry, material, visiblePoints.length);
    mesh.name = `coverage-${target.id}`;
    mesh.renderOrder = 5;
    const matrix = new THREE.Matrix4();
    visiblePoints.forEach((point, index) => {
      matrix.makeTranslation(point.x, 0.62, worldYToSceneZ(point.y));
      mesh.setMatrixAt(index, matrix);
    });
    mesh.instanceMatrix.needsUpdate = true;
    this.root.add(mesh);
  }

  private addTargetMotionPath(target: TargetState): void {
    const points = normalizeTargetMotionPath(target);
    if (points.length < 2) return;

    const scenePoints = points.map((point) => new THREE.Vector3(point.x, Math.max(1.2, point.z + 1.2), worldYToSceneZ(point.y)));
    const line = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(scenePoints),
      new THREE.LineBasicMaterial({ color: 0xf97316, transparent: true, opacity: 0.86 })
    );
    line.name = `target-motion-${target.id}`;
    this.root.add(line);

    const end = scenePoints[scenePoints.length - 1];
    const previous = scenePoints[scenePoints.length - 2];
    const direction = end.clone().sub(previous);
    if (direction.lengthSq() <= 0.001) return;

    const arrow = new THREE.Mesh(
      new THREE.ConeGeometry(4.5, 12, 18),
      new THREE.MeshStandardMaterial({ color: 0xf97316, emissive: 0xf97316, emissiveIntensity: 0.18, roughness: 0.44 })
    );
    arrow.position.copy(end);
    arrow.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
    this.root.add(arrow);
  }

  private addObstacle(obstacle: ObstacleState): void {
    const group = new THREE.Group();
    group.userData = { selectable: true, kind: 'obstacle' satisfies SelectableKind, id: obstacle.id };
    group.position.copy(toScenePosition(obstacle.position));
    const selected = this.selected?.kind === 'obstacle' && this.selected.id === obstacle.id;
    const isFlatArea = obstacle.height === 0;
    const height = getObstacleVisualHeight(obstacle.height) * this.visualScaleSettings.obstacle;
    const materialSettings = getObstacleMaterialSettings(obstacle.height);
    const material = new THREE.MeshStandardMaterial({
      color: getObstacleBaseColor(obstacle.type),
      transparent: materialSettings.transparent,
      opacity: materialSettings.opacity,
      roughness: 0.8
    });
    material.depthWrite = true;
    material.depthTest = true;
    let mesh: THREE.Mesh;
    if (obstacle.type === 'ellipse') {
      mesh = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, height, 48), material);
      mesh.scale.set((obstacle.width || 8) * this.visualScaleSettings.obstacle, 1, (obstacle.length || 12) * this.visualScaleSettings.obstacle);
    } else if (obstacle.type === 'polygon' && obstacle.vertices && obstacle.vertices.length >= 3) {
      const shape = new THREE.Shape(obstacle.vertices.map((point) => toGroundVector2(point, obstacle.position, this.visualScaleSettings.obstacle)));
      mesh = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, { depth: height, bevelEnabled: false }), material);
      const placement = getPolygonObstaclePlacement(height);
      mesh.rotation.x = placement.rotationX;
      mesh.position.y = placement.positionY;
    } else {
      const radius = (obstacle.radius || 3) * this.visualScaleSettings.obstacle;
      mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, height, 48), material);
    }
    if (!(obstacle.type === 'polygon' && obstacle.vertices && obstacle.vertices.length >= 3)) {
      mesh.position.y = height / 2;
    }
    mesh.castShadow = true;
    mesh.renderOrder = isFlatArea ? 7 : 3;
    group.add(mesh);
    if (this.labelsVisible) {
      const labelColor = obstacle.height === 0 ? '#fecaca' : '#e2e8f0';
      const label = makeLabel(selected ? formatObstacleInfoLines(obstacle, true, this.locale) : [obstacle.name, obstacle.type], labelColor);
      label.position.set(10, height + (selected ? 17 : 12), 0);
      group.add(label);
    }
    this.root.add(group);
    this.selectable.push(group);
  }

  private handlePointerDown(event: PointerEvent): void {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const groundHit = this.raycaster.intersectObject(this.ground)[0];
    this.onPointerWorld(groundHit ? sceneGroundToWorld(groundHit.point) : null);

    if (this.moveMode) {
      if (groundHit) {
        this.onGroundClick(sceneGroundToWorld(groundHit.point));
      }
      return;
    }

    const candidate = this.pickSelectableCandidate(event);
    if (!candidate) {
      if (this.directClickMove && groundHit) {
        this.onGroundClick(sceneGroundToWorld(groundHit.point));
        return;
      }
      this.clearSelection();
      return;
    }

    this.selected = {
      kind: candidate.userData.kind,
      id: candidate.userData.id
    };
    this.selectedDroneId = this.selected.kind === 'drone' ? this.selected.id : null;
    if (this.state) this.renderState(this.state);
    this.onSelect(this.selected);
  }

  private pickSelectableCandidate(event: PointerEvent): THREE.Object3D | null {
    const candidates: THREE.Object3D[] = [];
    const seen = new Set<string>();
    for (const hit of this.raycaster.intersectObjects(this.selectable, true)) {
      let selectedObject: THREE.Object3D | null = hit.object;
      while (selectedObject && !selectedObject.userData.selectable) {
        selectedObject = selectedObject.parent;
      }
      if (!selectedObject) continue;
      const key = `${selectedObject.userData.kind}:${selectedObject.userData.id}`;
      if (seen.has(key)) continue;
      seen.add(key);
      candidates.push(selectedObject);
    }
    if (candidates.length === 0) {
      this.selectionCycleKey = '';
      this.selectionCycleIndex = 0;
      this.selectionCycleCandidates = [];
      return null;
    }

    const clickKey = `${Math.round(event.clientX / 4)}:${Math.round(event.clientY / 4)}:${candidates.map((item) => `${item.userData.kind}:${item.userData.id}`).join('|')}`;
    this.selectionCycleCandidates = candidates.map((item) => ({ kind: item.userData.kind, id: item.userData.id }));
    if (clickKey === this.selectionCycleKey && candidates.length > 1) {
      this.selectionCycleIndex = (this.selectionCycleIndex + 1) % candidates.length;
    } else {
      this.selectionCycleKey = clickKey;
      this.selectionCycleIndex = 0;
    }
    return candidates[this.selectionCycleIndex] || candidates[0];
  }

  private handlePointerMove(event: PointerEvent): void {
    if (!this.moveMode) return;
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hit = this.raycaster.intersectObject(this.ground)[0];
    if (!hit) {
      this.movePreview.visible = false;
      return;
    }
    this.movePreview.position.set(hit.point.x, 0.14, hit.point.z);
    this.movePreview.visible = true;
  }

  private getSceneCenter(): THREE.Vector3 {
    if (!this.state) return new THREE.Vector3(512, 0, 384);
    const bounds = resolveSceneBounds(this.state);
    return new THREE.Vector3(bounds.centerX, 0, worldYToSceneZ(bounds.centerY));
  }

  private fitAll(): void {
    const center = this.getSceneCenter();
    const size = this.state ? resolveSceneBounds(this.state).size : 1024;
    this.camera.up.copy(getWorldViewCameraUp());
    this.controls.target.copy(center);
    this.camera.position.set(center.x + size * 0.28, size * 0.72, center.z + size * 0.82);
    this.camera.lookAt(center);
    this.controls.update();
  }

  private fitTopView(): void {
    const center = this.getSceneCenter();
    const bounds = this.state ? resolveSceneBounds(this.state) : { width: 1024, height: 1024 };
    const distance = getTopViewCameraDistance(bounds, this.camera.fov, this.camera.aspect);
    this.camera.up.copy(getTopViewCameraUp());
    this.controls.target.copy(center);
    this.camera.position.set(center.x, center.y + distance, center.z);
    this.camera.lookAt(center);
    this.controls.update();
  }

  private followDrone(droneId: string): void {
    const drone = this.state?.drones.find((item) => item.id === droneId);
    if (!drone) return;
    this.camera.up.copy(getWorldViewCameraUp());
    const pos = toScenePosition(drone.position);
    this.controls.target.lerp(pos, 0.18);
    this.camera.position.lerp(pos.clone().add(new THREE.Vector3(-80, 70, -110)), 0.12);
  }
}
