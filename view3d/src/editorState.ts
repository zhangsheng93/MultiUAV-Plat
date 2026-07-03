import type {
  DroneState,
  ObstacleState,
  Position,
  SelectableKind,
  SelectionRef,
  SessionData,
  TargetState,
  ViewerState
} from './types';

export type EditableEntity = DroneState | TargetState | ObstacleState;

export type EntityPatch = {
  name?: string;
  model?: string;
  type?: string;
  description?: string;
  radius?: number;
  width?: number;
  length?: number;
  height?: number;
  battery_level?: number;
  battery_capacity?: number;
  heading?: number;
  speed?: number;
  status?: string;
  max_speed?: number;
  max_altitude?: number;
  perceived_radius?: number;
  task_radius?: number;
  moving_duration?: number;
  movement_mode?: string;
  velocity?: Partial<Position>;
  moving_path?: Position[];
  vertices?: Position[];
  charge_amount?: number;
  position?: Partial<Position>;
};

const COPY_OFFSET = 12;

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function makeId(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function getCollection(state: ViewerState, kind: SelectableKind): EditableEntity[] {
  if (kind === 'drone') return state.drones;
  if (kind === 'target') return state.targets;
  return state.obstacles;
}

function getSelectionPosition(state: ViewerState, selection: SelectionRef | null): Position | null {
  const entity = getSelectedEntity(state, selection);
  return entity?.position || null;
}

function mergePosition(current: Position, patch?: Partial<Position>): Position {
  if (!patch) return current;
  return {
    x: patch.x ?? current.x,
    y: patch.y ?? current.y,
    z: patch.z ?? current.z
  };
}

function formatNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function uniqueClosingVertex(vertices: Position[]): Position[] {
  if (vertices.length < 4) return vertices;
  const first = vertices[0];
  const last = vertices[vertices.length - 1];
  if (first.x === last.x && first.y === last.y) return vertices.slice(0, -1);
  return vertices;
}

function polygonArea(vertices: Position[]): number {
  let area = 0;
  for (let index = 0; index < vertices.length; index += 1) {
    const current = vertices[index];
    const next = vertices[(index + 1) % vertices.length];
    area += current.x * next.y - next.x * current.y;
  }
  return Math.abs(area / 2);
}

function getPolygonCenter(vertices: Position[]): Position {
  const count = vertices.length || 1;
  return {
    x: vertices.reduce((sum, vertex) => sum + vertex.x, 0) / count,
    y: vertices.reduce((sum, vertex) => sum + vertex.y, 0) / count,
    z: vertices.reduce((sum, vertex) => sum + (vertex.z ?? 0), 0) / count
  };
}

function validatePolygon(vertices: Position[]): void {
  if (vertices.length < 3) throw new Error('Polygon must have at least 3 vertices');
  const unique = new Set(vertices.map((vertex) => `${vertex.x},${vertex.y}`));
  if (unique.size < 3) throw new Error('Polygon must have at least 3 unique vertices');
  for (let index = 1; index < vertices.length; index += 1) {
    if (vertices[index].x === vertices[index - 1].x && vertices[index].y === vertices[index - 1].y) {
      throw new Error('Polygon cannot contain consecutive duplicate vertices');
    }
  }
  if (polygonArea(vertices) <= 1e-9) throw new Error('Polygon must have non-zero area');
}

export function parseVerticesText(text: string): Position[] {
  const vertices = text
    .trim()
    .split('\n')
    .flatMap((line, lineIndex) => {
      const content = line.split('#')[0].trim();
      if (!content) return [];
      const parts = content.includes(',') ? content.split(',').map((part) => part.trim()) : content.split(/\s+/);
      if (parts.length !== 2) throw new Error(`Line ${lineIndex + 1}: Expected 2 values (x, y), got ${parts.length}`);
      const x = Number(parts[0]);
      const y = Number(parts[1]);
      if (!Number.isFinite(x) || !Number.isFinite(y)) throw new Error(`Line ${lineIndex + 1}: Invalid number format`);
      return [{ x, y, z: 0 }];
    });

  const normalized = uniqueClosingVertex(vertices);
  validatePolygon(normalized);
  return normalized;
}

export function formatVerticesText(vertices?: Position[]): string {
  return (vertices || []).map((vertex) => `${formatNumber(vertex.x)}, ${formatNumber(vertex.y)}`).join('\n');
}

export function parseMovingPathText(pathText: string, targetAltitude: number): Position[] {
  const trimmed = pathText.trim();
  if (!trimmed) return [];
  return trimmed.split('\n').flatMap((line, lineIndex) => {
    const content = line.trim();
    if (!content) return [];
    const parts = content.split(',').map((part) => part.trim());
    if (parts.length !== 2 && parts.length !== 3) {
      throw new Error(`Line ${lineIndex + 1}: Expected 2 or 3 numbers, got ${parts.length}`);
    }
    const x = Number(parts[0]);
    const y = Number(parts[1]);
    const z = parts.length === 3 ? Number(parts[2]) : targetAltitude;
    if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) {
      throw new Error(`Line ${lineIndex + 1}: Invalid numbers`);
    }
    return [{ x, y, z }];
  });
}

export function formatMovingPathText(movingPath?: Position[]): string {
  return (movingPath || []).map((point) => `${formatNumber(point.x)}, ${formatNumber(point.y)}, ${formatNumber(point.z)}`).join('\n');
}

export function snapPositionToGrid(position: Position, gridSize: number): Position {
  if (gridSize <= 0) return { ...position };
  return {
    x: Math.round(position.x / gridSize) * gridSize,
    y: Math.round(position.y / gridSize) * gridSize,
    z: position.z
  };
}

export function selectNextAtSamePosition(state: ViewerState, selection: SelectionRef | null, tolerance = 1e-6): SelectionRef | null {
  const position = getSelectionPosition(state, selection);
  if (!position || !selection) return null;

  const candidates: SelectionRef[] = [
    ...state.drones.map((entity) => ({ kind: 'drone' as const, id: entity.id, position: entity.position })),
    ...state.targets.map((entity) => ({ kind: 'target' as const, id: entity.id, position: entity.position })),
    ...state.obstacles.map((entity) => ({ kind: 'obstacle' as const, id: entity.id, position: entity.position }))
  ]
    .filter((candidate) => (
      Math.abs(candidate.position.x - position.x) <= tolerance
      && Math.abs(candidate.position.y - position.y) <= tolerance
      && Math.abs(candidate.position.z - position.z) <= tolerance
    ))
    .map((candidate) => ({ kind: candidate.kind, id: candidate.id }));

  if (candidates.length <= 1) return null;
  const currentIndex = candidates.findIndex((candidate) => candidate.kind === selection.kind && candidate.id === selection.id);
  return candidates[((currentIndex < 0 ? -1 : currentIndex) + 1) % candidates.length];
}

function offsetVertices<T extends { vertices?: Position[] }>(entity: T, deltaX: number, deltaY: number, deltaZ: number): void {
  if (!entity.vertices) return;
  entity.vertices = entity.vertices.map((vertex) => ({
    x: vertex.x + deltaX,
    y: vertex.y + deltaY,
    z: (vertex.z ?? 0) + deltaZ
  }));
}

function applyTargetTypeRules(target: TargetState): void {
  if (target.type === 'polygon') {
    delete target.radius;
  } else {
    delete target.vertices;
    if (target.radius === undefined) target.radius = 10;
  }

  if (target.type !== 'moving') {
    delete target.velocity;
    delete target.moving_path;
    delete target.moving_duration;
    delete target.movement_mode;
  }

  if (target.type !== 'waypoint') {
    delete target.charge_amount;
  }
}

function applyTargetMovementModeRules(target: TargetState): void {
  if (target.type !== 'moving') return;
  if (target.movement_mode === 'path') {
    delete target.velocity;
    if (!target.moving_path) target.moving_path = [];
    return;
  }
  if (target.movement_mode === 'stationary') {
    target.moving_duration = 0;
    delete target.velocity;
    delete target.moving_path;
    return;
  }
  if (target.movement_mode === 'velocity') {
    delete target.moving_path;
    if (!target.velocity) target.velocity = { x: 0, y: 0, z: 0 };
  }
}

function applyObstacleTypeRules(obstacle: ObstacleState): void {
  if (obstacle.type === 'polygon') {
    delete obstacle.radius;
    delete obstacle.width;
    delete obstacle.length;
    return;
  }

  delete obstacle.vertices;
  if (obstacle.type === 'ellipse') {
    delete obstacle.radius;
    if (obstacle.width === undefined) obstacle.width = 10;
    if (obstacle.length === undefined) obstacle.length = 10;
    return;
  }

  delete obstacle.width;
  delete obstacle.length;
  if (obstacle.radius === undefined) obstacle.radius = 10;
}

export function cloneEditorDraft(state: ViewerState): ViewerState {
  return clone(state);
}

export function getSelectedEntity(state: ViewerState, selection: SelectionRef | null): EditableEntity | null {
  if (!selection) return null;
  return getCollection(state, selection.kind).find((entity) => entity.id === selection.id) || null;
}

export function updateSelectedEntity(state: ViewerState, selection: SelectionRef | null, patch: EntityPatch): boolean {
  const entity = getSelectedEntity(state, selection);
  if (!entity) return false;

  const previousPosition = entity.position;
  const previousVelocity = selection?.kind === 'target' ? { ...((entity as TargetState).velocity || { x: 0, y: 0, z: 0 }) } : null;
  Object.assign(entity, patch);
  entity.position = mergePosition(previousPosition, patch.position);
  if (selection?.kind === 'target' && patch.velocity) {
    const target = entity as TargetState;
    target.velocity = mergePosition(previousVelocity || { x: 0, y: 0, z: 0 }, patch.velocity);
  }

  if (patch.position && (selection?.kind === 'target' || selection?.kind === 'obstacle')) {
    const deltaX = entity.position.x - previousPosition.x;
    const deltaY = entity.position.y - previousPosition.y;
    const deltaZ = entity.position.z - previousPosition.z;
    offsetVertices(entity as TargetState | ObstacleState, deltaX, deltaY, deltaZ);
  }
  if (patch.vertices && (selection?.kind === 'target' || selection?.kind === 'obstacle')) {
    entity.position = getPolygonCenter(patch.vertices);
  }
  if (selection?.kind === 'target' && patch.type) {
    applyTargetTypeRules(entity as TargetState);
  }
  if (selection?.kind === 'target' && (patch.type || patch.movement_mode || patch.velocity || patch.moving_path)) {
    applyTargetMovementModeRules(entity as TargetState);
  }
  if (selection?.kind === 'obstacle' && patch.type) {
    applyObstacleTypeRules(entity as ObstacleState);
  }
  return true;
}

export function moveSelectedEntity(state: ViewerState, selection: SelectionRef | null, position: Position): boolean {
  return updateSelectedEntity(state, selection, { position });
}

export function duplicateSelectedEntity(state: ViewerState, selection: SelectionRef | null): SelectionRef | null {
  const entity = getSelectedEntity(state, selection);
  if (!entity || !selection) return selection;

  const copy = clone(entity) as EditableEntity;
  copy.id = makeId(selection.kind);
  copy.name = `${entity.name} Copy`;
  copy.position = {
    x: entity.position.x + COPY_OFFSET,
    y: entity.position.y + COPY_OFFSET,
    z: entity.position.z
  };
  if ((selection.kind === 'target' || selection.kind === 'obstacle') && 'vertices' in copy && copy.vertices) {
    copy.vertices = copy.vertices.map((vertex) => ({
      x: vertex.x + COPY_OFFSET,
      y: vertex.y + COPY_OFFSET,
      z: vertex.z
    }));
  }

  getCollection(state, selection.kind).push(copy);
  return { kind: selection.kind, id: copy.id };
}

export function deleteSelectedEntity(state: ViewerState, selection: SelectionRef | null): SelectionRef | null {
  if (!selection) return null;
  const collection = getCollection(state, selection.kind);
  const index = collection.findIndex((entity) => entity.id === selection.id);
  if (index >= 0) collection.splice(index, 1);
  return null;
}

export function addDefaultEntity(state: ViewerState, kind: SelectableKind): SelectionRef {
  const center = {
    x: (state.session?.canvas_width || 300) / 2,
    y: (state.session?.canvas_height || 200) / 2,
    z: 0
  };

  if (kind === 'drone') {
    const drone: DroneState = {
      id: makeId('drone'),
      name: `Drone ${state.drones.length + 1}`,
      model: 'Generic',
      status: 'idle',
      position: { ...center },
      heading: 0,
      speed: 0,
      battery_level: 100,
      battery_capacity: 1000,
      max_speed: 20,
      max_altitude: 120,
      perceived_radius: 100,
      task_radius: 10,
      home_position: { ...center }
    };
    state.drones.push(drone);
    return { kind, id: drone.id };
  }

  if (kind === 'target') {
    const target: TargetState = {
      id: makeId('target'),
      name: `Target ${state.targets.length + 1}`,
      type: 'fixed',
      position: { ...center },
      radius: 8,
      description: ''
    };
    state.targets.push(target);
    return { kind, id: target.id };
  }

  const obstacle: ObstacleState = {
    id: makeId('obstacle'),
    name: `Obstacle ${state.obstacles.length + 1}`,
    type: 'circle',
    position: { ...center },
    radius: 10,
    height: 30,
    description: ''
  };
  state.obstacles.push(obstacle);
  return { kind, id: obstacle.id };
}

export function buildSessionSavePayload(sessionData: SessionData, draft: ViewerState): SessionData {
  return {
    ...clone(sessionData),
    drones: clone(draft.drones),
    targets: clone(draft.targets),
    obstacles: clone(draft.obstacles),
    canvas_width: draft.session?.canvas_width ?? sessionData.canvas_width,
    canvas_height: draft.session?.canvas_height ?? sessionData.canvas_height,
    is_distance_3d: draft.session?.is_distance_3d ?? sessionData.is_distance_3d
  };
}
