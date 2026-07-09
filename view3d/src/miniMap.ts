import type { ObstacleState, Position, TargetState, ViewerState } from './types';
import { resolveSceneBounds, type SceneBounds } from './sceneBounds.ts';
import { getObstacleBaseColor } from './obstacleVisuals.ts';

export type MiniMapBounds = Pick<SceneBounds, 'minX' | 'minY' | 'maxX' | 'maxY'>;

export type MiniMapSize = {
  width: number;
  height: number;
  padding: number;
};

export type MiniMapBackingSize = {
  width: number;
  height: number;
  pixelRatio: number;
};

export type MiniMapObjectShape =
  | { kind: 'circle'; radius: number }
  | { kind: 'ellipse'; radiusX: number; radiusY: number }
  | { kind: 'polygon'; vertices: Position[]; fallbackRadius: number };

export function resolveMiniMapBounds(state: ViewerState): MiniMapBounds {
  return resolveSceneBounds(state, 0);
}

export function worldToMiniMap(position: Position, bounds: MiniMapBounds, size: MiniMapSize): { x: number; y: number } {
  const usableWidth = Math.max(1, size.width - size.padding * 2);
  const usableHeight = Math.max(1, size.height - size.padding * 2);
  const normalizedX = (position.x - bounds.minX) / (bounds.maxX - bounds.minX);
  const normalizedY = (position.y - bounds.minY) / (bounds.maxY - bounds.minY);
  return {
    x: Math.round(size.padding + normalizedX * usableWidth),
    y: Math.round(size.height - size.padding - normalizedY * usableHeight)
  };
}

export function miniMapToWorld(point: { x: number; y: number }, bounds: MiniMapBounds, size: MiniMapSize): Position {
  const usableWidth = Math.max(1, size.width - size.padding * 2);
  const usableHeight = Math.max(1, size.height - size.padding * 2);
  const normalizedX = (point.x - size.padding) / usableWidth;
  const normalizedY = (size.height - size.padding - point.y) / usableHeight;
  return {
    x: bounds.minX + Math.max(0, Math.min(1, normalizedX)) * (bounds.maxX - bounds.minX),
    y: bounds.minY + Math.max(0, Math.min(1, normalizedY)) * (bounds.maxY - bounds.minY),
    z: 0
  };
}

export function resolveMiniMapBackingSize(size: MiniMapSize, devicePixelRatio: number): MiniMapBackingSize {
  const pixelRatio = Math.min(Math.max(devicePixelRatio || 1, 1), 3);
  return {
    width: Math.max(1, Math.round(size.width * pixelRatio)),
    height: Math.max(1, Math.round(size.height * pixelRatio)),
    pixelRatio
  };
}

function safePositive(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : 0;
}

function polygonRadius(position: Position, vertices: Position[] | undefined): number {
  if (!vertices?.length) return 0;
  return vertices.reduce((radius, vertex) => {
    if (!Number.isFinite(vertex.x) || !Number.isFinite(vertex.y)) return radius;
    return Math.max(radius, Math.hypot(vertex.x - position.x, vertex.y - position.y));
  }, 0);
}

export function getMiniMapTargetRadius(target: TargetState): number {
  if (target.type === 'polygon') {
    return polygonRadius(target.position, target.vertices) || safePositive(target.radius) || 6;
  }
  return safePositive(target.radius) || 6;
}

export function getMiniMapTargetShape(target: TargetState): MiniMapObjectShape {
  if (target.type === 'polygon' && target.vertices && target.vertices.length >= 3) {
    return { kind: 'polygon', vertices: target.vertices, fallbackRadius: getMiniMapTargetRadius(target) };
  }
  return { kind: 'circle', radius: getMiniMapTargetRadius(target) };
}

export function getMiniMapObstacleRadius(obstacle: ObstacleState): number {
  if (obstacle.type === 'polygon') {
    return polygonRadius(obstacle.position, obstacle.vertices) || safePositive(obstacle.radius) || 6;
  }
  if (obstacle.type === 'ellipse') {
    return Math.max(safePositive(obstacle.width), safePositive(obstacle.length)) || 6;
  }
  return safePositive(obstacle.radius) || 6;
}

export function getMiniMapObstacleShape(obstacle: ObstacleState): MiniMapObjectShape {
  if (obstacle.type === 'polygon' && obstacle.vertices && obstacle.vertices.length >= 3) {
    return { kind: 'polygon', vertices: obstacle.vertices, fallbackRadius: getMiniMapObstacleRadius(obstacle) };
  }
  if (obstacle.type === 'ellipse') {
    return {
      kind: 'ellipse',
      radiusX: safePositive(obstacle.width) || 6,
      radiusY: safePositive(obstacle.length) || 6
    };
  }
  return { kind: 'circle', radius: getMiniMapObstacleRadius(obstacle) };
}

export function getMiniMapObstacleColor(obstacle: ObstacleState): number {
  return getObstacleBaseColor(obstacle.type);
}
