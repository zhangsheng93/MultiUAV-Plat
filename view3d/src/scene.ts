import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { Line2 } from 'three/examples/jsm/lines/Line2.js';
import { LineGeometry } from 'three/examples/jsm/lines/LineGeometry.js';
import { LineMaterial } from 'three/examples/jsm/lines/LineMaterial.js';
import { formatDroneInfoLines, formatObstacleInfoLines, formatTargetInfoLines } from './entityLabel';
import { getTargetVisualState, normalizeCoverageSurfaces, normalizeTargetMotionPath, shouldRenderTargetMotionPath } from './taskVisuals';
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
import { getSceneCameraFarPlane, getSceneGroundDimensions, getTopViewCameraDistance, resolveSceneBounds, type SceneGroundDimensions } from './sceneBounds.ts';
import { DEFAULT_VISUAL_SCALE_SETTINGS, getAdaptiveBillboardScale, getAdaptiveDroneScale, type VisualScaleSettings } from './renderSettings.ts';
import {
  buildSelectionEllipsePoints,
  buildSelectionPolygonPoints,
  getLabelTextureMetrics,
  getObstacleSelectionVisualKind,
  getTargetSelectionVisualKind,
  getUniformLabelBaseScale
} from './selectionVisuals.ts';
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
import { DRONE_SHADOW_BASE_RADIUS, DRONE_VISUAL_GROUND_CLEARANCE, getDroneGroundShadowStyle } from './droneVisuals.ts';
import { getRoamPathLength, getRoamSpeed, getRoamTurnDistance, normalizeRoamPath, sampleRoamPath, stepRoamSpeedMultiplier } from './cameraRoam.ts';
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
type PointerWorldCallback = (point: Position | null) => void;
type ZoomScaleCallback = (scale: number) => void;
export type CameraModeResult = { ok: boolean; message?: string; roamSpeedMultiplier?: number };
export type RoamSpeedResult = CameraModeResult & { multiplier?: number };

type RoamState = {
  droneId: string;
  path: Position[];
  baseSpeed: number;
  speedMultiplier: number;
  speed: number;
  distance: number;
  totalLength: number;
  turnDistance: number;
  done: boolean;
};

type DroneActor = {
  group: THREE.Group;
  label: THREE.Sprite;
  altitudeLine: THREE.Line;
  groundShadow: THREE.Group;
  targetPosition: THREE.Vector3;
  targetHeading: number;
  status: string;
  accentMaterial: THREE.MeshStandardMaterial;
  rotorGroups: THREE.Group[];
  selectionRadius: number;
};

type RoamGhostDrone = THREE.Group & {
  userData: {
    rotorGroups: THREE.Group[];
  };
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
const OBSTACLE_SELECTION_HIGHLIGHT_Y = 1.25;
const DRONE_SHADOW_Y = COVERAGE_SURFACE_Y + 0.08;
const DRONE_ROTOR_OFFSET = 10;
const DRONE_ARM_LENGTH = 28;
const DRONE_SHADOW_ARM_LENGTH = 29;
const FOLLOW_CHASE_EYE = new THREE.Vector3(0, 26, 54);
const FOLLOW_CHASE_TARGET = new THREE.Vector3(0, 5, -10);
const FOLLOW_CHASE_DELTA = FOLLOW_CHASE_EYE.clone().sub(FOLLOW_CHASE_TARGET);
const ROAM_TRAIL_COLOR = 0x22c55e;
const DEFAULT_TRAIL_COLOR = 0xe5e7eb;
const DEFAULT_TRAIL_OPACITY = 0.24;
const ROAM_TRAIL_LINE_WIDTH = 3;

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

function flattenLinePoints(points: THREE.Vector3[]): number[] {
  return points.flatMap((point) => [point.x, point.y, point.z]);
}

function makeWideLine(points: THREE.Vector3[], color: number, opacity: number, linewidth: number): Line2 {
  const geometry = new LineGeometry();
  geometry.setPositions(flattenLinePoints(points));
  const material = new LineMaterial({
    color,
    linewidth,
    transparent: true,
    opacity,
    depthWrite: false,
    depthTest: true
  });
  const line = new Line2(geometry, material);
  line.computeLineDistances();
  line.frustumCulled = false;
  return line;
}

function updateWideLineGeometry(line: Line2, points: THREE.Vector3[]): void {
  line.geometry.dispose();
  line.geometry = new LineGeometry();
  line.geometry.setPositions(flattenLinePoints(points));
  line.computeLineDistances();
}

function makeCircularSelectionHighlight(radius: number, y: number, position?: THREE.Vector3, thickness = 0.28): THREE.Mesh {
  const mesh = new THREE.Mesh(
    new THREE.TorusGeometry(Math.max(1, radius), thickness, 8, 96),
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

function makeDroneShadowMaterial(): THREE.MeshBasicMaterial {
  return new THREE.MeshBasicMaterial({
    color: 0x020617,
    transparent: true,
    opacity: 0,
    depthWrite: false,
    depthTest: true,
    polygonOffset: true,
    polygonOffsetFactor: -5,
    polygonOffsetUnits: -5
  });
}

function makeDroneShadowBox(width: number, depth: number, material: THREE.Material, x = 0, z = 0, rotationY = 0): THREE.Mesh {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(width, 0.035, depth), material);
  mesh.position.set(x, 0, z);
  mesh.rotation.y = rotationY;
  return mesh;
}

function makeDroneShadowNose(material: THREE.Material): THREE.Mesh {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    'position',
    new THREE.Float32BufferAttribute([
      0, 0, -10.6,
      -3.4, 0, -5.5,
      3.4, 0, -5.5
    ], 3)
  );
  geometry.setIndex([0, 1, 2]);
  geometry.computeVertexNormals();
  return new THREE.Mesh(geometry, material);
}

function makeDroneGroundShadow(): THREE.Group {
  const group = new THREE.Group();
  const material = makeDroneShadowMaterial();

  group.add(
    makeDroneShadowBox(6.8, 11.5, material),
    makeDroneShadowNose(material),
    makeDroneShadowBox(1.25, DRONE_SHADOW_ARM_LENGTH, material, 0, 0, Math.PI / 4),
    makeDroneShadowBox(1.25, DRONE_SHADOW_ARM_LENGTH, material, 0, 0, -Math.PI / 4),
    makeDroneShadowBox(0.42, 10.4, material, -3.8, 0),
    makeDroneShadowBox(0.42, 10.4, material, 3.8, 0)
  );

  for (const [x, z] of [
    [-DRONE_ROTOR_OFFSET, -DRONE_ROTOR_OFFSET],
    [DRONE_ROTOR_OFFSET, -DRONE_ROTOR_OFFSET],
    [-DRONE_ROTOR_OFFSET, DRONE_ROTOR_OFFSET],
    [DRONE_ROTOR_OFFSET, DRONE_ROTOR_OFFSET]
  ]) {
    const rotor = new THREE.Mesh(new THREE.CylinderGeometry(4.45, 4.45, 0.035, 36), material);
    rotor.position.set(x, 0, z);
    group.add(rotor);
  }

  group.renderOrder = 9;
  group.visible = false;
  return group;
}

function makeRoamGhostDrone(): RoamGhostDrone {
  const rotorGroups: THREE.Group[] = [];
  const group = new THREE.Group() as RoamGhostDrone;
  group.userData.rotorGroups = rotorGroups;
  group.visible = false;
  group.renderOrder = 30;

  const bodyMaterial = new THREE.MeshStandardMaterial({
    color: 0x93c5fd,
    transparent: true,
    opacity: 0.8,
    depthWrite: false,
    metalness: 0.16,
    roughness: 0.38
  });
  const darkMaterial = new THREE.MeshStandardMaterial({
    color: 0x0f172a,
    transparent: true,
    opacity: 0.7,
    depthWrite: false,
    roughness: 0.5
  });
  const ringMaterial = new THREE.MeshStandardMaterial({
    color: 0x22c55e,
    transparent: true,
    opacity: 0.7,
    depthWrite: false,
    roughness: 0.42
  });
  const glassMaterial = new THREE.MeshStandardMaterial({
    color: 0x0ea5e9,
    transparent: true,
    opacity: 0.7,
    depthWrite: false,
    metalness: 0.05,
    roughness: 0.18
  });
  const rotorBlurMaterial = new THREE.MeshStandardMaterial({
    color: 0x020617,
    transparent: true,
    opacity: 0.18,
    depthWrite: false,
    side: THREE.DoubleSide,
    roughness: 0.28
  });
  const bladeMaterial = new THREE.MeshStandardMaterial({
    color: 0x020617,
    transparent: true,
    opacity: 0.7,
    depthWrite: false,
    side: THREE.DoubleSide,
    roughness: 0.28
  });

  const body = new THREE.Mesh(new THREE.BoxGeometry(6.2, 2.2, 10), bodyMaterial);
  body.position.y = 0.35;
  const nose = new THREE.Mesh(new THREE.ConeGeometry(2.9, 4.8, 4), bodyMaterial);
  nose.rotation.x = -Math.PI / 2;
  nose.position.set(0, 0.35, -7.4);
  const canopy = new THREE.Mesh(new THREE.SphereGeometry(2.1, 20, 10), glassMaterial);
  canopy.scale.set(1.15, 0.36, 0.82);
  canopy.position.set(0, 1.72, -1.8);
  const statusLight = new THREE.Mesh(new THREE.SphereGeometry(0.55, 16, 8), ringMaterial);
  statusLight.position.set(0, 1.35, -9.75);
  const tailAccent = new THREE.Mesh(new THREE.BoxGeometry(3.6, 0.22, 1.1), ringMaterial);
  tailAccent.position.set(0, 1.63, 4.4);
  const cameraPod = new THREE.Mesh(new THREE.SphereGeometry(1.05, 16, 8), darkMaterial);
  cameraPod.scale.set(1, 0.72, 0.86);
  cameraPod.position.set(0, -1.15, -4.3);
  group.add(body, nose, canopy, statusLight, tailAccent, cameraPod);

  const armA = new THREE.Mesh(new THREE.BoxGeometry(1.15, 0.7, DRONE_ARM_LENGTH), darkMaterial);
  armA.rotation.y = Math.PI / 4;
  const armB = armA.clone();
  armB.rotation.y = -Math.PI / 4;
  group.add(armA, armB);

  for (const [x, z] of [
    [-DRONE_ROTOR_OFFSET, -DRONE_ROTOR_OFFSET],
    [DRONE_ROTOR_OFFSET, -DRONE_ROTOR_OFFSET],
    [-DRONE_ROTOR_OFFSET, DRONE_ROTOR_OFFSET],
    [DRONE_ROTOR_OFFSET, DRONE_ROTOR_OFFSET]
  ]) {
    const ring = new THREE.Mesh(new THREE.TorusGeometry(4.15, 0.16, 8, 40), ringMaterial);
    ring.rotation.x = Math.PI / 2;
    ring.position.set(x, 1.28, z);
    const motor = new THREE.Mesh(new THREE.CylinderGeometry(1.8, 2.15, 1.25, 24), darkMaterial);
    motor.position.set(x, 0.55, z);
    const rotorGroup = new THREE.Group();
    rotorGroup.position.set(x, 1.34, z);
    rotorGroups.push(rotorGroup);

    const rotorBlur = new THREE.Mesh(new THREE.CylinderGeometry(4.45, 4.45, 0.035, 36), rotorBlurMaterial);
    rotorBlur.position.y = -0.04;
    const bladeA = new THREE.Mesh(new THREE.BoxGeometry(8.4, 0.08, 0.62), bladeMaterial);
    bladeA.rotation.y = x * z > 0 ? 0.18 : -0.18;
    bladeA.position.y = 0.06;
    const bladeB = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.08, 8.4), bladeMaterial);
    bladeB.rotation.y = x * z > 0 ? 0.18 : -0.18;
    bladeB.position.y = 0.1;
    rotorGroup.add(rotorBlur, bladeA, bladeB);
    group.add(ring, motor, rotorGroup);
  }

  for (const x of [-3.8, 3.8]) {
    const skid = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 10.2, 10), darkMaterial);
    skid.rotation.x = Math.PI / 2;
    skid.position.set(x, -2.25, 0);
    group.add(skid);

    for (const z of [-3.9, 3.9]) {
      const strut = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 2.2, 8), darkMaterial);
      strut.position.set(x, -1.18, z);
      group.add(strut);
    }
  }

  group.traverse((object) => {
    object.renderOrder = 30;
  });

  return group;
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
  private readonly roamGhostDrone = makeRoamGhostDrone();
  private roamTrailLine: Line2 | null = null;
  private selectionHighlight: THREE.Object3D | null = null;
  private readonly axisGuide = new THREE.Group();
  private readonly ground = new THREE.Mesh(
    new THREE.PlaneGeometry(1024, 768),
    new THREE.MeshStandardMaterial({ color: 0x4f6f46, roughness: 0.9 })
  );
  private readonly grid = new THREE.GridHelper(1024, 32, 0x94a3b8, 0x475569);
  private animationFrame = 0;
  private state: ViewerState | null = null;
  private selected: SelectionRef | null = null;
  private cameraMode: CameraMode = 'free';
  private selectedDroneId: string | null = null;
  private roamState: RoamState | null = null;
  private trailLength = 80;
  private labelsVisible = DEFAULT_LABELS_VISIBLE;
  private targetMotionVisible = false;
  private visualScaleSettings: VisualScaleSettings = { ...DEFAULT_VISUAL_SCALE_SETTINGS };
  private locale: Locale = 'en-US';
  private selectionCycleKey = '';
  private selectionCycleIndex = 0;
  private selectionCycleCandidates: SelectionRef[] = [];
  private onSelect: SelectCallback = () => undefined;
  private onPointerWorld: PointerWorldCallback = () => undefined;
  private onZoomScale: ZoomScaleCallback = () => undefined;
  private zoomBaseDistance = 1024;
  private zoomScale = 1;
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
    this.root.add(this.roamGhostDrone);
    this.scene.add(this.ground, this.grid, this.axisGuide, this.root);

    this.renderer.domElement.addEventListener('pointerdown', (event) => this.handlePointerDown(event));
    this.renderer.domElement.addEventListener('pointermove', (event) => this.handlePointerMove(event));
    this.renderer.domElement.addEventListener('wheel', (event) => this.handleWheel(event), { passive: false });
    window.addEventListener('resize', () => this.resize());
    this.resize();
    this.animate();
  }

  dispose(): void {
    cancelAnimationFrame(this.animationFrame);
    this.renderer.domElement.remove();
    this.renderer.dispose();
  }

  setCallbacks(onSelect: SelectCallback, onPointerWorld?: PointerWorldCallback, onZoomScale?: ZoomScaleCallback): void {
    this.onSelect = onSelect;
    this.onPointerWorld = onPointerWorld || (() => undefined);
    this.onZoomScale = onZoomScale || (() => undefined);
  }

  getCameraMode(): CameraMode {
    return this.cameraMode;
  }

  setCameraMode(mode: CameraMode): CameraModeResult {
    if (mode === 'follow' || mode === 'roam') {
      if (!this.selectedDroneId || !this.getSelectedDrone()) {
        return { ok: false, message: '请先选择一架无人机。' };
      }
    }

    if (mode === 'roam') {
      const result = this.startRoam();
      if (!result.ok) return result;
    } else {
      this.stopRoamVisuals();
    }

    this.cameraMode = mode;
    if (mode === 'top') {
      this.controls.enabled = true;
      this.fitTopView();
    } else if (mode === 'fit') {
      this.controls.enabled = true;
      this.fitAll();
      this.cameraMode = 'free';
    } else if (mode === 'free') {
      this.camera.up.copy(getWorldViewCameraUp());
      this.controls.enabled = true;
    } else if (mode === 'follow' || mode === 'roam') {
      this.controls.enabled = false;
      this.camera.up.copy(getWorldViewCameraUp());
    }
    return { ok: true };
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
    this.stopFirstPersonCamera();
    this.selectionCycleKey = '';
    this.selectionCycleIndex = 0;
    this.selectionCycleCandidates = [];
    if (this.state) this.renderState(this.state);
    this.onSelect(null);
  }

  setSelection(selection: SelectionRef | null): void {
    const previousDroneId = this.selectedDroneId;
    this.selected = selection;
    this.selectedDroneId = selection?.kind === 'drone' ? selection.id : null;
    if (this.cameraMode === 'roam' && previousDroneId !== this.selectedDroneId) {
      this.stopFirstPersonCamera();
    }
    this.selectionCycleKey = '';
    this.selectionCycleIndex = 0;
    this.selectionCycleCandidates = selection ? [selection] : [];
    if (this.state) this.renderState(this.state);
    this.onSelect(selection);
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
    const previousDroneId = this.selectedDroneId;
    this.selectedDroneId = nextSelection.kind === 'drone' ? nextSelection.id : null;
    if (this.cameraMode === 'roam' && previousDroneId !== this.selectedDroneId) {
      this.stopFirstPersonCamera();
    }
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
    this.setZoomScale(this.zoomScale / scale);
  }

  setZoomScale(scale: number): void {
    const safeScale = THREE.MathUtils.clamp(scale, MIN_ZOOM_SCALE, MAX_ZOOM_SCALE);
    this.zoomScale = safeScale;
    if (this.cameraMode === 'follow' || this.cameraMode === 'roam') {
      this.updateFirstPersonCamera(0);
      this.notifyZoomScaleChanged(true);
      return;
    }

    const direction = this.camera.position.clone().sub(this.controls.target);
    if (direction.lengthSq() <= 0.0001) return;
    const baseDistance = this.getZoomBaseDistance();
    direction.setLength(baseDistance / safeScale);
    this.camera.position.copy(this.controls.target.clone().add(direction));
    this.controls.update();
    this.notifyZoomScaleChanged(true);
  }

  stepRoamSpeed(direction: -1 | 1): RoamSpeedResult {
    if (this.cameraMode !== 'roam' || !this.roamState) {
      return { ok: false, message: '请先进入漫游模式。' };
    }

    const nextMultiplier = stepRoamSpeedMultiplier(this.roamState.speedMultiplier, direction);
    this.roamState.speedMultiplier = nextMultiplier;
    this.roamState.speed = this.roamState.baseSpeed * nextMultiplier;
    this.roamState.turnDistance = getRoamTurnDistance(this.roamState.speed);
    return { ok: true, multiplier: nextMultiplier };
  }

  resetView(): void {
    this.stopRoamVisuals();
    this.cameraMode = 'free';
    this.controls.enabled = true;
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
    if (wasEmpty && this.cameraMode !== 'follow' && this.cameraMode !== 'roam') {
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
    this.updateRoamTrailResolution();
  }

  private animate(): void {
    this.animationFrame = requestAnimationFrame(() => this.animate());
    const deltaSeconds = this.clock.getDelta();
    this.updateDroneActors(deltaSeconds);
    this.updateFirstPersonCamera(deltaSeconds);
    this.updateAdaptiveVisualScale();
    if (this.cameraMode === 'follow' || this.cameraMode === 'roam') {
      this.notifyZoomScaleChanged();
    } else {
      this.controls.update();
      this.clampCameraDistanceToZoomBounds();
      this.notifyZoomScaleChanged();
    }
    this.renderer.render(this.scene, this.camera);
  }

  private getZoomBaseDistance(): number {
    return this.zoomBaseDistance;
  }

  private resetZoomBaseDistanceToCurrentView(): void {
    this.zoomBaseDistance = Math.max(1, this.camera.position.distanceTo(this.controls.target));
    this.zoomScale = 1;
    this.notifyZoomScaleChanged(true);
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
    if (this.cameraMode === 'follow' || this.cameraMode === 'roam') {
      return this.zoomScale;
    }

    const baseDistance = this.getZoomBaseDistance();
    const distance = Math.max(1, this.camera.position.distanceTo(this.controls.target));
    this.zoomScale = THREE.MathUtils.clamp(baseDistance / distance, MIN_ZOOM_SCALE, MAX_ZOOM_SCALE);
    return this.zoomScale;
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
    this.updateCameraDepthRange(bounds);
    const groundDimensions = getSceneGroundDimensions(bounds, GROUND_EDGE_BUFFER);
    this.ground.geometry.dispose();
    this.ground.geometry = new THREE.PlaneGeometry(groundDimensions.width, groundDimensions.height);
    this.ground.position.set(bounds.centerX, 0, worldYToSceneZ(bounds.centerY));
    this.grid.geometry.dispose();
    this.grid.geometry = new THREE.BufferGeometry().copy(
      new THREE.GridHelper(groundDimensions.baseSize, Math.max(12, Math.round(groundDimensions.baseSize / 32))).geometry
    );
    this.grid.scale.set(groundDimensions.gridScaleX, 1, groundDimensions.gridScaleZ);
    this.grid.position.set(bounds.centerX, 0.32, worldYToSceneZ(bounds.centerY));
    configureGrid(this.grid);
    this.updateAxisGuide(bounds, groundDimensions);
  }

  private updateCameraDepthRange(bounds: ReturnType<typeof resolveSceneBounds>): void {
    const far = getSceneCameraFarPlane(bounds, MIN_ZOOM_SCALE, GROUND_EDGE_BUFFER);
    if (Math.abs(this.camera.far - far) < 1) return;
    this.camera.far = far;
    this.camera.updateProjectionMatrix();
    this.scene.fog = new THREE.Fog(SCENE_CLEAR_COLOR, Math.max(4200, far * 0.35), Math.max(14000, far * 0.92));
  }

  private updateAxisGuide(bounds: ReturnType<typeof resolveSceneBounds>, groundDimensions: SceneGroundDimensions): void {
    [...this.axisGuide.children].forEach((child) => {
      this.axisGuide.remove(child);
      disposeObject(child);
    });
    const length = THREE.MathUtils.clamp(bounds.size * 0.09, 72, 150);
    const inset = Math.max(length * 0.72, bounds.size * 0.045);
    const groundMinX = bounds.centerX - groundDimensions.width / 2;
    const groundMinY = bounds.centerY - groundDimensions.height / 2;
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
        this.root.remove(actor.groundShadow);
        disposeObject(actor.group);
        disposeObject(actor.groundShadow);
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
    state.drones.forEach((drone) => this.upsertDrone(drone, this.getDroneHistoryPath(drone, state)));
  }

  private getDroneHistoryPath(drone: DroneState, state: ViewerState | null = this.state): Position[] {
    return normalizeRoamPath(state?.paths[drone.id] || [], drone.position);
  }

  private upsertDrone(drone: DroneState, path: Position[]): void {
    let actor = this.droneActors.get(drone.id);
    if (!actor) {
      actor = this.createDroneActor(drone);
      this.droneActors.set(drone.id, actor);
      this.root.add(actor.groundShadow, actor.group);
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
    this.updateDroneGroundShadow(actor);

    this.updateTrail(drone.id, path);
  }

  private createDroneActor(drone: DroneState): DroneActor {
    const group = new THREE.Group();
    group.position.copy(toScenePosition(drone.position));
    group.rotation.y = -THREE.MathUtils.degToRad(drone.heading || 0);
    group.userData = { selectable: true, kind: 'drone' satisfies SelectableKind, id: drone.id };
    const airframe = new THREE.Group();
    airframe.position.y = DRONE_VISUAL_GROUND_CLEARANCE;
    group.add(airframe);

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
    airframe.add(fuselage);

    const nose = new THREE.Mesh(new THREE.ConeGeometry(2.9, 4.8, 4), bodyMaterial);
    nose.rotation.x = -Math.PI / 2;
    nose.position.set(0, 0.35, -7.4);
    nose.castShadow = true;
    airframe.add(nose);

    const canopy = new THREE.Mesh(new THREE.SphereGeometry(2.1, 20, 10), glassMaterial);
    canopy.scale.set(1.15, 0.36, 0.82);
    canopy.position.set(0, 1.72, -1.8);
    canopy.castShadow = true;
    airframe.add(canopy);

    const statusLight = new THREE.Mesh(new THREE.SphereGeometry(0.55, 16, 8), accentMaterial);
    statusLight.position.set(0, 1.35, -9.75);
    airframe.add(statusLight);

    const tailAccent = new THREE.Mesh(new THREE.BoxGeometry(3.6, 0.22, 1.1), accentMaterial);
    tailAccent.position.set(0, 1.63, 4.4);
    airframe.add(tailAccent);

    const cameraPod = new THREE.Mesh(new THREE.SphereGeometry(1.05, 16, 8), darkMaterial);
    cameraPod.scale.set(1, 0.72, 0.86);
    cameraPod.position.set(0, -1.15, -4.3);
    cameraPod.castShadow = true;
    airframe.add(cameraPod);

    const armA = new THREE.Mesh(new THREE.BoxGeometry(1.15, 0.7, DRONE_ARM_LENGTH), darkMaterial);
    armA.rotation.y = Math.PI / 4;
    const armB = armA.clone();
    armB.rotation.y = -Math.PI / 4;
    airframe.add(armA, armB);

    for (const [x, z] of [
      [-DRONE_ROTOR_OFFSET, -DRONE_ROTOR_OFFSET],
      [DRONE_ROTOR_OFFSET, -DRONE_ROTOR_OFFSET],
      [-DRONE_ROTOR_OFFSET, DRONE_ROTOR_OFFSET],
      [DRONE_ROTOR_OFFSET, DRONE_ROTOR_OFFSET]
    ]) {
      const rotorGroup = new THREE.Group();
      rotorGroup.position.set(x, 1.34, z);
      rotorGroups.push(rotorGroup);

      const motor = new THREE.Mesh(new THREE.CylinderGeometry(1.8, 2.15, 1.25, 24), darkMaterial);
      motor.position.set(x, 0.55, z);
      motor.castShadow = true;
      airframe.add(motor);

      const rotorRing = new THREE.Mesh(new THREE.TorusGeometry(4.15, 0.16, 8, 40), ringMaterial);
      rotorRing.rotation.x = Math.PI / 2;
      rotorRing.position.set(x, 1.28, z);
      rotorRing.castShadow = true;
      airframe.add(rotorRing);

      const bladeA = new THREE.Mesh(new THREE.BoxGeometry(8.4, 0.08, 0.62), propMaterial);
      bladeA.rotation.y = x * z > 0 ? 0.18 : -0.18;
      const bladeB = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.08, 8.4), propMaterial);
      bladeB.rotation.y = x * z > 0 ? 0.18 : -0.18;
      bladeB.position.y = 0.02;
      rotorGroup.add(bladeA, bladeB);
      airframe.add(rotorGroup);
    }

    for (const x of [-3.8, 3.8]) {
      const skid = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 10.2, 10), darkMaterial);
      skid.rotation.x = Math.PI / 2;
      skid.position.set(x, -2.25, 0);
      skid.castShadow = true;
      airframe.add(skid);

      for (const z of [-3.9, 3.9]) {
        const strut = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 2.2, 8), darkMaterial);
        strut.position.set(x, -1.18, z);
        strut.castShadow = true;
        airframe.add(strut);
      }
    }

    const line = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, -drone.position.z, 0), new THREE.Vector3(0, 0, 0)]),
      new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.7 })
    );
    group.add(line);

    const groundShadow = makeDroneGroundShadow();
    groundShadow.position.set(group.position.x, DRONE_SHADOW_Y, group.position.z);

    const label = makeLabel(formatDroneInfoLines(drone, false, this.locale));
    label.position.set(11, 20, 0);
    group.add(label);

    return {
      group,
      label,
      altitudeLine: line,
      groundShadow,
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
      material.color.setHex(DEFAULT_TRAIL_COLOR);
      material.transparent = true;
      material.opacity = DEFAULT_TRAIL_OPACITY;
      material.depthWrite = false;
      material.depthTest = true;
      material.needsUpdate = true;
      return;
    }

    const trailLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(trail),
      new THREE.LineBasicMaterial({
        color: DEFAULT_TRAIL_COLOR,
        transparent: true,
        opacity: DEFAULT_TRAIL_OPACITY,
        depthWrite: false,
        depthTest: true
      })
    );
    this.trailLines.set(droneId, trailLine);
    this.root.add(trailLine);
  }

  private updateRoamTrail(path: Position[] | null = this.roamState?.path || null): void {
    if (!path) {
      this.clearRoamTrail();
      return;
    }

    const points = path.map(toScenePosition);
    if (points.length <= 1) {
      this.clearRoamTrail();
      return;
    }

    if (this.roamTrailLine) {
      updateWideLineGeometry(this.roamTrailLine, points);
      this.updateRoamTrailResolution();
      return;
    }

    this.roamTrailLine = makeWideLine(points, ROAM_TRAIL_COLOR, 0.92, ROAM_TRAIL_LINE_WIDTH);
    this.roamTrailLine.renderOrder = 18;
    this.updateRoamTrailResolution();
    this.root.add(this.roamTrailLine);
  }

  private updateRoamTrailResolution(): void {
    if (!this.roamTrailLine) return;
    const material = this.roamTrailLine.material as LineMaterial;
    material.resolution.set(Math.max(1, this.host.clientWidth), Math.max(1, this.host.clientHeight));
  }

  private clearRoamTrail(): void {
    if (!this.roamTrailLine) return;
    this.root.remove(this.roamTrailLine);
    disposeObject(this.roamTrailLine);
    this.roamTrailLine = null;
  }

  private getTrailPoints(path: Position[]): Position[] {
    if (this.trailLength === 0) return [];
    if (this.trailLength === -1) return path;
    if (this.trailLength === 1) return path.slice(-2);
    return path.slice(-this.trailLength);
  }

  private startRoam(): CameraModeResult {
    const drone = this.getSelectedDrone();
    if (!drone) return { ok: false, message: '请先选择一架无人机。' };
    const path = this.getDroneHistoryPath(drone);
    const totalLength = getRoamPathLength(path);
    if (path.length < 2 || totalLength <= 0) {
      return { ok: false, message: '该无人机没有可漫游路径。' };
    }

    const speed = getRoamSpeed(drone);
    this.roamState = {
      droneId: drone.id,
      path,
      baseSpeed: speed,
      speedMultiplier: 1,
      speed,
      distance: 0,
      totalLength,
      turnDistance: getRoamTurnDistance(speed),
      done: false
    };
    this.updateRoamTrail();
    this.updateTrail(drone.id, path);
    return { ok: true, roamSpeedMultiplier: 1 };
  }

  private stopFirstPersonCamera(): void {
    this.stopRoamVisuals();
    if (this.cameraMode === 'follow' || this.cameraMode === 'roam') {
      this.cameraMode = 'free';
      this.controls.enabled = true;
      this.camera.up.copy(getWorldViewCameraUp());
    }
  }

  private stopRoamVisuals(): void {
    const previousRoamDroneId = this.roamState?.droneId;
    this.roamState = null;
    this.roamGhostDrone.visible = false;
    this.clearRoamTrail();
    if (previousRoamDroneId && this.state) {
      const drone = this.state.drones.find((item) => item.id === previousRoamDroneId);
      this.updateTrail(previousRoamDroneId, drone ? this.getDroneHistoryPath(drone) : this.state.paths[previousRoamDroneId] || []);
    }
  }

  private updateDroneActors(deltaSeconds: number): void {
    for (const actor of this.droneActors.values()) {
      actor.group.position.lerp(actor.targetPosition, Math.min(1, deltaSeconds * 6));
      actor.group.rotation.y = THREE.MathUtils.lerp(actor.group.rotation.y, actor.targetHeading, Math.min(1, deltaSeconds * 8));
      this.updateDroneGroundShadow(actor);

      const rotorSpeed = this.getRotorSpeed(actor.status);
      actor.rotorGroups.forEach((rotorGroup, index) => {
        rotorGroup.rotation.y += rotorSpeed * deltaSeconds * (index % 2 === 0 ? 1 : -1);
      });
    }

    this.updateSelectedDroneHighlightPosition();

    if (this.roamGhostDrone.visible) {
      const rotorSpeed = this.getRotorSpeed('moving');
      this.roamGhostDrone.userData.rotorGroups.forEach((rotorGroup, index) => {
        rotorGroup.rotation.y += rotorSpeed * deltaSeconds * (index % 2 === 0 ? 1 : -1);
      });
    }
  }

  private updateSelectedDroneHighlightPosition(): void {
    if (!this.selectionHighlight || this.selected?.kind !== 'drone') return;
    const actor = this.droneActors.get(this.selected.id);
    if (!actor) return;

    const worldCenter = new THREE.Vector3();
    actor.group.getWorldPosition(worldCenter);
    this.selectionHighlight.position.set(
      worldCenter.x,
      Math.max(2.8, worldCenter.y + 3.2),
      worldCenter.z
    );
  }

  private updateFirstPersonCamera(deltaSeconds: number): void {
    if (this.cameraMode === 'follow') {
      if (!this.selectedDroneId) return;
      this.followDrone(this.selectedDroneId);
    } else if (this.cameraMode === 'roam') {
      this.updateRoamCamera(deltaSeconds);
    }
  }

  private setDroneChaseCamera(position: THREE.Vector3, rotationY: number): void {
    const pivot = new THREE.Object3D();
    pivot.position.copy(position);
    pivot.rotation.y = rotationY;
    const target = pivot.localToWorld(FOLLOW_CHASE_TARGET.clone());
    const scaledEye = FOLLOW_CHASE_TARGET.clone().add(FOLLOW_CHASE_DELTA.clone().divideScalar(this.zoomScale));
    const eye = pivot.localToWorld(scaledEye);
    this.camera.up.copy(getWorldViewCameraUp());
    this.camera.position.copy(eye);
    this.controls.target.copy(target);
    this.camera.lookAt(target);
  }

  private setPathChaseCamera(position: THREE.Vector3, forward: THREE.Vector3): void {
    const safeForward = forward.clone().normalize();
    const target = position.clone()
      .add(safeForward.clone().multiplyScalar(-FOLLOW_CHASE_TARGET.z))
      .add(new THREE.Vector3(0, FOLLOW_CHASE_TARGET.y, 0));
    const eye = target.clone()
      .add(safeForward.clone().multiplyScalar(-FOLLOW_CHASE_DELTA.z / this.zoomScale))
      .add(new THREE.Vector3(0, FOLLOW_CHASE_DELTA.y / this.zoomScale, 0));
    this.camera.up.copy(getWorldViewCameraUp());
    this.camera.position.copy(eye);
    this.controls.target.copy(target);
    this.camera.lookAt(target);
  }

  private updateRoamCamera(deltaSeconds: number): void {
    const roam = this.roamState;
    if (!roam) return;

    const sample = sampleRoamPath(roam.path, roam.distance, roam.turnDistance);
    if (!sample) {
      roam.done = true;
      this.hideRoamGhost();
      return;
    }

    roam.done = sample.done;
    this.updateRoamTrail(sample.done ? [] : this.getRemainingRoamPath(roam.path, sample));
    const position = toScenePosition(sample.position);
    const direction = worldToScenePosition(sample.forwardHint);
    if (direction.lengthSq() <= 0.0001 && sample.segmentIndex > 0) {
      direction.copy(position.clone().sub(toScenePosition(roam.path[sample.segmentIndex])));
    }
    if (direction.lengthSq() <= 0.0001) {
      const actor = this.droneActors.get(roam.droneId);
      if (actor) {
        if (roam.done) this.hideRoamGhost();
        else this.updateRoamGhost(position, actor.group.rotation.y);
        this.setDroneChaseCamera(position, actor.group.rotation.y);
      }
      return;
    }

    const rotationY = this.getRotationYForForward(direction);
    if (roam.done) this.hideRoamGhost();
    else this.updateRoamGhost(position, rotationY);
    this.setPathChaseCamera(position, direction);

    if (!roam.done) {
      roam.distance = Math.min(roam.totalLength, roam.distance + roam.speed * deltaSeconds);
    }
  }

  private getRemainingRoamPath(path: Position[], sample: { position: Position; segmentIndex: number }): Position[] {
    const remaining = [{ ...sample.position }];
    for (const point of path.slice(sample.segmentIndex + 1)) {
      const previous = remaining[remaining.length - 1];
      if (Math.hypot(previous.x - point.x, previous.y - point.y, previous.z - point.z) > 0.001) {
        remaining.push({ ...point });
      }
    }
    return remaining;
  }

  private getRotationYForForward(forward: THREE.Vector3): number {
    const normalized = forward.clone().normalize();
    return Math.atan2(-normalized.x, -normalized.z);
  }

  private updateRoamGhost(position: THREE.Vector3, rotationY: number): void {
    this.roamGhostDrone.visible = this.cameraMode === 'roam';
    this.roamGhostDrone.position.copy(position);
    this.roamGhostDrone.rotation.y = rotationY;
  }

  private hideRoamGhost(): void {
    this.roamGhostDrone.visible = false;
  }

  private updateDroneGroundShadow(actor: DroneActor): void {
    const style = getDroneGroundShadowStyle(actor.group.position.y);
    actor.groundShadow.position.set(actor.group.position.x, DRONE_SHADOW_Y, actor.group.position.z);
    actor.groundShadow.rotation.y = actor.group.rotation.y;
    actor.groundShadow.visible = style.visible;
    if (!style.visible) return;

    const scale = (style.radius / DRONE_SHADOW_BASE_RADIUS) * this.visualScaleSettings.drone;
    actor.groundShadow.scale.setScalar(scale);
    actor.groundShadow.traverse((child) => {
      const material = (child as THREE.Mesh).material as THREE.MeshBasicMaterial | undefined;
      if (!material) return;
      material.opacity = style.opacity;
      material.needsUpdate = true;
    });
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
    const persistent = new Set<THREE.Object3D>([this.roamGhostDrone]);
    if (this.roamTrailLine) persistent.add(this.roamTrailLine);
    this.droneActors.forEach((actor) => {
      persistent.add(actor.group);
      persistent.add(actor.groundShadow);
    });
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

    this.selectionHighlight = shapeHighlight || makeCircularSelectionHighlight(
      radius,
      this.selected.kind === 'drone' ? Math.max(2.8, worldCenter.y + 3.2) : OBSTACLE_SELECTION_HIGHLIGHT_Y,
      worldCenter,
      this.selected.kind === 'drone' ? 0.44 : 0.28
    );
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
      if (!obstacle) return null;
      if (getObstacleSelectionVisualKind(obstacle) === 'ellipse') {
        const points = buildSelectionEllipsePoints(obstacle.width, obstacle.length)
          .map((point) => new THREE.Vector3(
            obstacle.position.x + point.x * this.visualScaleSettings.obstacle,
            OBSTACLE_SELECTION_HIGHLIGHT_Y,
            worldYToSceneZ(obstacle.position.y + point.y * this.visualScaleSettings.obstacle)
          ));
        return makeSelectionLine(points);
      }
      if (getObstacleSelectionVisualKind(obstacle) !== 'polygon' || !obstacle.vertices) return null;
      const points = buildSelectionPolygonPoints(obstacle.vertices, obstacle.position)
        .map((point) => new THREE.Vector3(
          obstacle.position.x + point.x * this.visualScaleSettings.obstacle,
          OBSTACLE_SELECTION_HIGHLIGHT_Y,
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
    if (coverageSurfaces.length === 0) return;
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

    const candidate = this.pickSelectableCandidate(event);
    if (!candidate) {
      this.clearSelection();
      return;
    }

    this.selected = {
      kind: candidate.userData.kind,
      id: candidate.userData.id
    };
    const previousDroneId = this.selectedDroneId;
    this.selectedDroneId = this.selected.kind === 'drone' ? this.selected.id : null;
    if (this.cameraMode === 'roam' && previousDroneId !== this.selectedDroneId) {
      this.stopFirstPersonCamera();
    }
    if (this.state) this.renderState(this.state);
    this.onSelect(this.selected);
  }

  private handleWheel(event: WheelEvent): void {
    if (this.cameraMode !== 'follow' && this.cameraMode !== 'roam') return;
    event.preventDefault();
    const scaleStep = event.deltaY > 0 ? 0.88 : 1.14;
    this.setZoomScale(this.zoomScale * scaleStep);
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
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hit = this.raycaster.intersectObject(this.ground)[0];
    this.onPointerWorld(hit ? sceneGroundToWorld(hit.point) : null);
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
    this.resetZoomBaseDistanceToCurrentView();
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
    this.resetZoomBaseDistanceToCurrentView();
  }

  private followDrone(droneId: string): void {
    const actor = this.droneActors.get(droneId);
    if (!actor) return;
    this.setDroneChaseCamera(actor.group.position, actor.group.rotation.y);
  }
}
