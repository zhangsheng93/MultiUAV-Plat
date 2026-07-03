import type { DroneState, Position, SessionData, TargetState, ViewerState } from './types';

type CoverageSurfacePayload = NonNullable<ViewerState['area_coverage_surfaces']>[string];

type Bounds = {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
};

type CoverageSurface = {
  outer: Position[];
};

type Point2 = {
  x: number;
  y: number;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function asRecord(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {};
}

function asPosition(value: unknown): Position | null {
  if (!isRecord(value)) return null;
  const x = value.x;
  const y = value.y;
  const z = value.z;
  if (typeof x !== 'number' || typeof y !== 'number' || !Number.isFinite(x) || !Number.isFinite(y)) return null;
  return {
    x,
    y,
    z: typeof z === 'number' && Number.isFinite(z) ? z : 0
  };
}

function normalizePathHistory(history: unknown): Record<string, Position[]> {
  const rawPaths = asRecord(asRecord(history).path_history);
  const paths: Record<string, Position[]> = {};
  for (const [droneId, rawPath] of Object.entries(rawPaths)) {
    if (!Array.isArray(rawPath)) continue;
    const points = rawPath.map(asPosition).filter((point): point is Position => Boolean(point));
    if (points.length > 0) paths[droneId] = points;
  }
  return paths;
}

function getCoverageRadius(drone: DroneState): number {
  if (typeof drone.coverage_width === 'number' && drone.coverage_width > 0) return drone.coverage_width / 2;
  if (typeof drone.task_radius === 'number' && drone.task_radius > 0) return drone.task_radius;
  if (typeof drone.perceived_radius === 'number' && drone.perceived_radius > 0) return drone.perceived_radius;
  return 0;
}

function getTargetBounds(target: TargetState): Bounds | null {
  if (target.type === 'circle') {
    const radius = target.radius || 0;
    if (radius <= 0) return null;
    return {
      minX: target.position.x - radius,
      maxX: target.position.x + radius,
      minY: target.position.y - radius,
      maxY: target.position.y + radius
    };
  }

  if (target.type === 'polygon' && target.vertices && target.vertices.length >= 3) {
    return target.vertices.reduce<Bounds>((bounds, vertex) => ({
      minX: Math.min(bounds.minX, vertex.x),
      maxX: Math.max(bounds.maxX, vertex.x),
      minY: Math.min(bounds.minY, vertex.y),
      maxY: Math.max(bounds.maxY, vertex.y)
    }), {
      minX: Number.POSITIVE_INFINITY,
      maxX: Number.NEGATIVE_INFINITY,
      minY: Number.POSITIVE_INFINITY,
      maxY: Number.NEGATIVE_INFINITY
    });
  }

  return null;
}

function pointInPolygon(point: Position, vertices: Position[]): boolean {
  let inside = false;
  for (let index = 0, previous = vertices.length - 1; index < vertices.length; previous = index, index += 1) {
    const currentVertex = vertices[index];
    const previousVertex = vertices[previous];
    const intersects = (
      (currentVertex.y > point.y) !== (previousVertex.y > point.y)
      && point.x < ((previousVertex.x - currentVertex.x) * (point.y - currentVertex.y)) / (previousVertex.y - currentVertex.y) + currentVertex.x
    );
    if (intersects) inside = !inside;
  }
  return inside;
}

function pointInTarget(point: Position, target: TargetState): boolean {
  if (target.type === 'circle') {
    const radius = target.radius || 0;
    const dx = point.x - target.position.x;
    const dy = point.y - target.position.y;
    return dx * dx + dy * dy <= radius * radius;
  }
  if (target.type === 'polygon' && target.vertices && target.vertices.length >= 3) {
    return pointInPolygon(point, target.vertices);
  }
  return false;
}

function distanceToSegment(point: Position, start: Position, end: Position): number {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const lengthSq = dx * dx + dy * dy;
  if (lengthSq <= 1e-9) {
    return Math.hypot(point.x - start.x, point.y - start.y);
  }
  const t = Math.max(0, Math.min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / lengthSq));
  return Math.hypot(point.x - (start.x + t * dx), point.y - (start.y + t * dy));
}

function isCoveredByDronePaths(point: Position, drones: DroneState[], paths: Record<string, Position[]>): boolean {
  for (const drone of drones) {
    const radius = getCoverageRadius(drone);
    if (radius <= 0) continue;
    const path = [...(paths[drone.id] || []), drone.position];
    if (path.length === 1 && Math.hypot(point.x - path[0].x, point.y - path[0].y) <= radius) return true;
    for (let index = 1; index < path.length; index += 1) {
      if (distanceToSegment(point, path[index - 1], path[index]) <= radius) return true;
    }
  }
  return false;
}

function makeCircleSurface(target: TargetState): { outer: Position[] } | null {
  const radius = target.radius || 0;
  if (radius <= 0) return null;
  const segments = 96;
  const outer = Array.from({ length: segments }, (_, index) => {
    const angle = (index / segments) * Math.PI * 2;
    return {
      x: target.position.x + Math.cos(angle) * radius,
      y: target.position.y + Math.sin(angle) * radius,
      z: 0
    };
  });
  return { outer };
}

function makeWholeTargetSurface(target: TargetState): Array<{ outer: Position[] }> {
  if (target.type === 'polygon' && target.vertices && target.vertices.length >= 3) {
    return [{ outer: target.vertices.map((vertex) => ({ x: vertex.x, y: vertex.y, z: vertex.z || 0 })) }];
  }
  const circleSurface = makeCircleSurface(target);
  return circleSurface ? [circleSurface] : [];
}

function polygonArea(points: Point2[]): number {
  let area = 0;
  for (let index = 0; index < points.length; index += 1) {
    const current = points[index];
    const next = points[(index + 1) % points.length];
    area += current.x * next.y - next.x * current.y;
  }
  return area / 2;
}

function normalizeCounterClockwise(points: Point2[]): Point2[] {
  return polygonArea(points) >= 0 ? points : [...points].reverse();
}

function makeCirclePolygon(center: Position, radius: number, segments = 48): Point2[] {
  return Array.from({ length: segments }, (_, index) => {
    const angle = (index / segments) * Math.PI * 2;
    return {
      x: center.x + Math.cos(angle) * radius,
      y: center.y + Math.sin(angle) * radius
    };
  });
}

function getTargetClipPolygon(target: TargetState): Point2[] {
  if (target.type === 'polygon' && target.vertices && target.vertices.length >= 3) {
    return normalizeCounterClockwise(target.vertices.map((point) => ({ x: point.x, y: point.y })));
  }
  if (target.type === 'circle') {
    const radius = target.radius || 0;
    return radius > 0 ? normalizeCounterClockwise(makeCirclePolygon(target.position, radius, 96)) : [];
  }
  return [];
}

function isInsideClipEdge(point: Point2, edgeStart: Point2, edgeEnd: Point2): boolean {
  return ((edgeEnd.x - edgeStart.x) * (point.y - edgeStart.y) - (edgeEnd.y - edgeStart.y) * (point.x - edgeStart.x)) >= -1e-7;
}

function intersectLines(lineStart: Point2, lineEnd: Point2, edgeStart: Point2, edgeEnd: Point2): Point2 {
  const lineDx = lineEnd.x - lineStart.x;
  const lineDy = lineEnd.y - lineStart.y;
  const edgeDx = edgeEnd.x - edgeStart.x;
  const edgeDy = edgeEnd.y - edgeStart.y;
  const denominator = lineDx * edgeDy - lineDy * edgeDx;
  if (Math.abs(denominator) <= 1e-9) return lineEnd;
  const t = ((edgeStart.x - lineStart.x) * edgeDy - (edgeStart.y - lineStart.y) * edgeDx) / denominator;
  return {
    x: lineStart.x + t * lineDx,
    y: lineStart.y + t * lineDy
  };
}

function clipPolygonToConvexPolygon(subject: Point2[], clip: Point2[]): Point2[] {
  let output = subject;
  for (let index = 0; index < clip.length; index += 1) {
    const edgeStart = clip[index];
    const edgeEnd = clip[(index + 1) % clip.length];
    const input = output;
    output = [];
    if (input.length === 0) break;

    let previous = input[input.length - 1];
    for (const current of input) {
      const currentInside = isInsideClipEdge(current, edgeStart, edgeEnd);
      const previousInside = isInsideClipEdge(previous, edgeStart, edgeEnd);
      if (currentInside) {
        if (!previousInside) output.push(intersectLines(previous, current, edgeStart, edgeEnd));
        output.push(current);
      } else if (previousInside) {
        output.push(intersectLines(previous, current, edgeStart, edgeEnd));
      }
      previous = current;
    }
  }
  return output;
}

function makeSegmentFootprint(start: Position, end: Position, radius: number): Point2[] {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const length = Math.hypot(dx, dy);
  if (length <= 1e-9) return makeCirclePolygon(start, radius, 32);

  const unitX = dx / length;
  const unitY = dy / length;
  const normalX = -unitY;
  const normalY = unitX;
  const capSegments = 8;
  const points: Point2[] = [
    { x: start.x + normalX * radius, y: start.y + normalY * radius },
    { x: end.x + normalX * radius, y: end.y + normalY * radius }
  ];

  const heading = Math.atan2(unitY, unitX);
  for (let index = 1; index <= capSegments; index += 1) {
    const angle = heading + Math.PI / 2 - (index / capSegments) * Math.PI;
    points.push({
      x: end.x + Math.cos(angle) * radius,
      y: end.y + Math.sin(angle) * radius
    });
  }

  points.push({ x: start.x - normalX * radius, y: start.y - normalY * radius });

  for (let index = 1; index <= capSegments; index += 1) {
    const angle = heading - Math.PI / 2 - (index / capSegments) * Math.PI;
    points.push({
      x: start.x + Math.cos(angle) * radius,
      y: start.y + Math.sin(angle) * radius
    });
  }

  return normalizeCounterClockwise(points);
}

function toSurface(points: Point2[]): CoverageSurface {
  return {
    outer: points.map((point) => ({
      x: Math.round(point.x * 1000) / 1000,
      y: Math.round(point.y * 1000) / 1000,
      z: 0
    }))
  };
}

function buildCoverageFootprintSurfaces(
  target: TargetState,
  drones: DroneState[],
  paths: Record<string, Position[]>
): CoverageSurface[] {
  const targetClip = getTargetClipPolygon(target);
  if (targetClip.length < 3) return [];

  const surfaces: CoverageSurface[] = [];
  for (const drone of drones) {
    const radius = getCoverageRadius(drone);
    if (radius <= 0) continue;
    const path = [...(paths[drone.id] || []), drone.position];
    if (path.length === 1) {
      const clipped = clipPolygonToConvexPolygon(makeCirclePolygon(path[0], radius, 32), targetClip);
      if (clipped.length >= 3) surfaces.push(toSurface(clipped));
      continue;
    }
    for (let index = 1; index < path.length; index += 1) {
      const footprint = makeSegmentFootprint(path[index - 1], path[index], radius);
      const clipped = clipPolygonToConvexPolygon(footprint, targetClip);
      if (clipped.length >= 3) surfaces.push(toSurface(clipped));
    }
  }
  return surfaces;
}

function getCoverageCellSize(drones: DroneState[]): number {
  const radii = drones.map(getCoverageRadius).filter((radius) => radius > 0);
  if (radii.length === 0) return 16;
  const minRadius = Math.min(...radii);
  return Math.max(5, Math.min(16, minRadius / 2));
}

export function buildAreaCoverageSurfaces(
  targets: TargetState[],
  drones: DroneState[],
  paths: Record<string, Position[]>
): Record<string, CoverageSurfacePayload> {
  const result: Record<string, CoverageSurfacePayload> = {};
  const activeDrones = drones.filter((drone) => getCoverageRadius(drone) > 0);
  if (activeDrones.length === 0) return result;

  const cellSize = getCoverageCellSize(activeDrones);
  for (const target of targets) {
    if (target.type !== 'circle' && target.type !== 'polygon') continue;
    const bounds = getTargetBounds(target);
    if (!bounds) continue;

    let totalCells = 0;
    let coveredCells = 0;
    for (let y = bounds.minY + cellSize / 2; y <= bounds.maxY; y += cellSize) {
      for (let x = bounds.minX + cellSize / 2; x <= bounds.maxX; x += cellSize) {
        const center = { x, y, z: 0 };
        if (!pointInTarget(center, target)) continue;
        totalCells += 1;
        if (!isCoveredByDronePaths(center, activeDrones, paths)) continue;
        coveredCells += 1;
      }
    }

    if (totalCells > 0) {
      const rawProgress = coveredCells / totalCells;
      const progressPercentage = Math.round(rawProgress * 10000) / 100;
      const surfaces = rawProgress >= 0.995
        ? makeWholeTargetSurface(target)
        : buildCoverageFootprintSurfaces(target, activeDrones, paths);
      result[target.id] = {
        covered_area: Math.round(coveredCells * cellSize * cellSize * 1000) / 1000,
        target_area: Math.round(totalCells * cellSize * cellSize * 1000) / 1000,
        progress_percentage: rawProgress >= 0.995 ? 100 : progressPercentage,
        surfaces
      };
    }
  }
  return result;
}

export function sessionDataToViewerState(sessionData: SessionData, serverTime = Date.now() / 1000): ViewerState {
  const history = asRecord(sessionData.history);
  const statistics = asRecord(sessionData.statistics);
  const taskProgress = asRecord(statistics.task_progress);
  const paths = normalizePathHistory(history);
  const areaCoverage = isRecord(history.area_coverage)
    ? history.area_coverage as ViewerState['area_coverage']
    : undefined;

  return {
    server_time: serverTime,
    status: sessionData.status || 'active',
    session: {
      id: sessionData.id,
      name: sessionData.name,
      description: sessionData.description,
      status: sessionData.status,
      creator: sessionData.creator,
      task_type: sessionData.task_type || 'others',
      task_description: sessionData.task_description,
      canvas_width: sessionData.canvas_width,
      canvas_height: sessionData.canvas_height,
      is_distance_3d: sessionData.is_distance_3d,
      created_at: sessionData.created_at,
      last_updated: sessionData.last_updated
    },
    drones: sessionData.drones || [],
    targets: sessionData.targets || [],
    obstacles: sessionData.obstacles || [],
    paths,
    task_progress: taskProgress,
    area_coverage: areaCoverage,
    area_coverage_surfaces: buildAreaCoverageSurfaces(sessionData.targets || [], sessionData.drones || [], paths),
    history: areaCoverage ? { area_coverage: areaCoverage } : undefined,
    environment: sessionData.environment || null
  };
}
