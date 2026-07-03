import type { Position, ViewerState } from './types';
import { resolveSceneBounds, type SceneBounds } from './sceneBounds.ts';

export type MiniMapBounds = Pick<SceneBounds, 'minX' | 'minY' | 'maxX' | 'maxY'>;

export type MiniMapSize = {
  width: number;
  height: number;
  padding: number;
};

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
