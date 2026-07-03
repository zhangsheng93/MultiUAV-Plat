import type { Position, ViewerState } from './types';

export type SceneBounds = {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  width: number;
  height: number;
  centerX: number;
  centerY: number;
  size: number;
};

type BoundsDraft = {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
};

const DEFAULT_MIN_SCENE_WIDTH = 1024;
const DEFAULT_MIN_SCENE_HEIGHT = 768;

function expandAxis(rawMin: number, rawMax: number, padding: number, minSize: number): { min: number; max: number } {
  const paddedMin = rawMin - padding;
  const paddedMax = rawMax + padding;
  const size = paddedMax - paddedMin;
  if (size >= minSize) return { min: paddedMin, max: paddedMax };

  const center = (paddedMin + paddedMax) / 2;
  const halfSize = minSize / 2;
  return { min: center - halfSize, max: center + halfSize };
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function includePoint(bounds: BoundsDraft, point: Partial<Position> | { x?: unknown; y?: unknown } | undefined): void {
  if (!point || !isFiniteNumber(point.x) || !isFiniteNumber(point.y)) return;
  bounds.minX = Math.min(bounds.minX, point.x);
  bounds.minY = Math.min(bounds.minY, point.y);
  bounds.maxX = Math.max(bounds.maxX, point.x);
  bounds.maxY = Math.max(bounds.maxY, point.y);
}

function includeRadius(bounds: BoundsDraft, position: Position, radius = 0): void {
  const safeRadius = Math.max(0, radius);
  includePoint(bounds, { x: position.x - safeRadius, y: position.y - safeRadius });
  includePoint(bounds, { x: position.x + safeRadius, y: position.y + safeRadius });
}

function includeCoveragePoint(bounds: BoundsDraft, point: Position | { x: number; y: number } | [number, number] | [number, number, number]): void {
  if (Array.isArray(point)) {
    includePoint(bounds, { x: point[0], y: point[1] });
    return;
  }
  includePoint(bounds, point);
}

function includeCoveragePayload(bounds: BoundsDraft, payload?: { covered_points?: Array<Position | [number, number] | [number, number, number]> }): void {
  payload?.covered_points?.forEach((point) => includeCoveragePoint(bounds, point));
}

function finishBounds(bounds: BoundsDraft, padding: number, minWidth: number, minHeight: number): SceneBounds {
  if (bounds.maxX <= bounds.minX) bounds.maxX = bounds.minX + 1;
  if (bounds.maxY <= bounds.minY) bounds.maxY = bounds.minY + 1;

  const safePadding = Math.max(0, padding);
  const xAxis = expandAxis(bounds.minX, bounds.maxX, safePadding, minWidth);
  const yAxis = expandAxis(bounds.minY, bounds.maxY, safePadding, minHeight);
  const minX = xAxis.min;
  const minY = yAxis.min;
  const maxX = xAxis.max;
  const maxY = yAxis.max;

  const width = maxX - minX;
  const height = maxY - minY;
  return {
    minX,
    minY,
    maxX,
    maxY,
    width,
    height,
    centerX: minX + width / 2,
    centerY: minY + height / 2,
    size: Math.max(width, height)
  };
}

export function resolveSceneBounds(state: ViewerState, padding = 120): SceneBounds {
  const minWidth = Math.max(DEFAULT_MIN_SCENE_WIDTH, state.session?.canvas_width || 0);
  const minHeight = Math.max(DEFAULT_MIN_SCENE_HEIGHT, state.session?.canvas_height || 0);
  const bounds: BoundsDraft = {
    minX: 0,
    minY: 0,
    maxX: minWidth,
    maxY: minHeight
  };

  for (const drone of state.drones) {
    includePoint(bounds, drone.position);
    if (drone.home_position) includePoint(bounds, drone.home_position);
  }

  for (const path of Object.values(state.paths || {})) {
    path.forEach((point) => includePoint(bounds, point));
  }

  for (const target of state.targets) {
    if (target.vertices?.length) {
      target.vertices.forEach((point) => includePoint(bounds, point));
    } else {
      includeRadius(bounds, target.position, target.radius || 0);
    }
    target.moving_path?.forEach((point) => includePoint(bounds, point));
  }

  for (const obstacle of state.obstacles) {
    if (obstacle.vertices?.length) {
      obstacle.vertices.forEach((point) => includePoint(bounds, point));
    } else {
      includeRadius(bounds, obstacle.position, obstacle.radius || Math.max(obstacle.width || 0, obstacle.length || 0) / 2);
    }
  }

  Object.values(state.area_coverage || {}).forEach((payload) => includeCoveragePayload(bounds, payload));
  Object.values(state.area_coverage_surfaces || {}).forEach((payload) => {
    payload.surfaces?.forEach((surface) => {
      surface.outer?.forEach((point) => includeCoveragePoint(bounds, point));
      surface.holes?.forEach((hole) => hole.forEach((point) => includeCoveragePoint(bounds, point)));
    });
  });

  return finishBounds(bounds, padding, minWidth, minHeight);
}

export function getTopViewCameraDistance(bounds: Pick<SceneBounds, 'width' | 'height'>, verticalFovDegrees: number, aspect: number): number {
  const safeAspect = Math.max(0.1, aspect);
  const fovRadians = (Math.max(1, verticalFovDegrees) * Math.PI) / 180;
  const halfFovTangent = Math.tan(fovRadians / 2);
  const distanceForHeight = bounds.height / (2 * halfFovTangent);
  const distanceForWidth = bounds.width / (2 * halfFovTangent * safeAspect);
  return Math.max(500, Math.max(distanceForHeight, distanceForWidth) * 1.35);
}
