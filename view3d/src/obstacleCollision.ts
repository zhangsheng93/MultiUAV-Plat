import type { ObstacleState, Position } from './types.ts';

export type MovePathCollisionResult = {
  blocked: boolean;
  obstacleId?: string;
  obstacleName?: string;
  reason?: string;
};

type Point2 = {
  x: number;
  y: number;
};

const EPSILON = 1e-9;

function maxFlightAltitude(start: Position, end: Position): number {
  return Math.max(start.z || 0, end.z || 0);
}

function isObstacleRelevantAtAltitude(obstacle: ObstacleState, start: Position, end: Position): boolean {
  const height = obstacle.height ?? 10;
  return height === 0 || maxFlightAltitude(start, end) <= height;
}

function distancePointToSegment(point: Point2, start: Point2, end: Point2): number {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const lengthSq = dx * dx + dy * dy;
  if (lengthSq <= EPSILON) return Math.hypot(point.x - start.x, point.y - start.y);
  const t = Math.max(0, Math.min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / lengthSq));
  return Math.hypot(point.x - (start.x + t * dx), point.y - (start.y + t * dy));
}

function pointInCircle(point: Point2, center: Point2, radius: number): boolean {
  return Math.hypot(point.x - center.x, point.y - center.y) <= radius;
}

function pointInEllipse(point: Point2, center: Point2, radiusX: number, radiusY: number): boolean {
  if (radiusX <= 0 || radiusY <= 0) return false;
  const dx = (point.x - center.x) / radiusX;
  const dy = (point.y - center.y) / radiusY;
  return dx * dx + dy * dy <= 1;
}

function pointInPolygon(point: Point2, vertices: Point2[]): boolean {
  let inside = false;
  for (let index = 0, previous = vertices.length - 1; index < vertices.length; previous = index, index += 1) {
    const current = vertices[index];
    const previousVertex = vertices[previous];
    const crosses = (
      (current.y > point.y) !== (previousVertex.y > point.y)
      && point.x < ((previousVertex.x - current.x) * (point.y - current.y)) / (previousVertex.y - current.y) + current.x
    );
    if (crosses) inside = !inside;
  }
  return inside;
}

function orientation(a: Point2, b: Point2, c: Point2): number {
  return (b.y - a.y) * (c.x - b.x) - (b.x - a.x) * (c.y - b.y);
}

function onSegment(a: Point2, b: Point2, c: Point2): boolean {
  return b.x <= Math.max(a.x, c.x) + EPSILON
    && b.x + EPSILON >= Math.min(a.x, c.x)
    && b.y <= Math.max(a.y, c.y) + EPSILON
    && b.y + EPSILON >= Math.min(a.y, c.y);
}

function segmentsIntersect(a: Point2, b: Point2, c: Point2, d: Point2): boolean {
  const o1 = orientation(a, b, c);
  const o2 = orientation(a, b, d);
  const o3 = orientation(c, d, a);
  const o4 = orientation(c, d, b);

  if (Math.abs(o1) <= EPSILON && onSegment(a, c, b)) return true;
  if (Math.abs(o2) <= EPSILON && onSegment(a, d, b)) return true;
  if (Math.abs(o3) <= EPSILON && onSegment(c, a, d)) return true;
  if (Math.abs(o4) <= EPSILON && onSegment(c, b, d)) return true;
  return (o1 > 0) !== (o2 > 0) && (o3 > 0) !== (o4 > 0);
}

function segmentIntersectsPolygon(start: Point2, end: Point2, vertices: Point2[]): boolean {
  if (vertices.length < 3) return false;
  if (pointInPolygon(start, vertices) || pointInPolygon(end, vertices)) return true;
  for (let index = 0; index < vertices.length; index += 1) {
    if (segmentsIntersect(start, end, vertices[index], vertices[(index + 1) % vertices.length])) return true;
  }
  return false;
}

function segmentIntersectsCircle(start: Point2, end: Point2, center: Point2, radius: number): boolean {
  return pointInCircle(start, center, radius)
    || pointInCircle(end, center, radius)
    || distancePointToSegment(center, start, end) <= radius;
}

function segmentIntersectsEllipse(start: Point2, end: Point2, center: Point2, radiusX: number, radiusY: number): boolean {
  if (radiusX <= 0 || radiusY <= 0) return false;
  const normalizedStart = {
    x: (start.x - center.x) / radiusX,
    y: (start.y - center.y) / radiusY
  };
  const normalizedEnd = {
    x: (end.x - center.x) / radiusX,
    y: (end.y - center.y) / radiusY
  };
  return segmentIntersectsCircle(normalizedStart, normalizedEnd, { x: 0, y: 0 }, 1);
}

function segmentIntersectsObstacle(start: Position, end: Position, obstacle: ObstacleState): boolean {
  if (!isObstacleRelevantAtAltitude(obstacle, start, end)) return false;
  const start2 = { x: start.x, y: start.y };
  const end2 = { x: end.x, y: end.y };
  const center = { x: obstacle.position.x, y: obstacle.position.y };

  if (obstacle.type === 'polygon' && obstacle.vertices && obstacle.vertices.length >= 3) {
    return segmentIntersectsPolygon(start2, end2, obstacle.vertices.map((vertex) => ({ x: vertex.x, y: vertex.y })));
  }

  if (obstacle.type === 'ellipse') {
    return segmentIntersectsEllipse(start2, end2, center, obstacle.width || 0, obstacle.length || 0);
  }

  const radius = obstacle.radius || (obstacle.type === 'point' ? 3 : 10);
  return segmentIntersectsCircle(start2, end2, center, radius);
}

export function checkMovePathCollision(start: Position, end: Position, obstacles: ObstacleState[]): MovePathCollisionResult {
  for (const obstacle of obstacles) {
    if (!segmentIntersectsObstacle(start, end, obstacle)) continue;
    return {
      blocked: true,
      obstacleId: obstacle.id,
      obstacleName: obstacle.name,
      reason: `路径与障碍物 ${obstacle.name} 相交`
    };
  }
  return { blocked: false };
}
