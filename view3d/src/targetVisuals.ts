export const TARGET_SURFACE_HEIGHT = 0.5;
export const ROUND_TARGET_HEIGHT = 0.5;
export const ROUND_TARGET_CENTER_Y = 0.7;
export const COVERAGE_SURFACE_CLEARANCE = 0.12;
export const TARGET_POLYGON_COLOR = 0x06b6d4;
export const TARGET_CIRCLE_COLOR = 0x2563eb;
export const TARGET_POINT_COLOR = 0x2563eb;

export type TargetPlacement = {
  rotationX: number;
  positionY: number;
};

export type GroundPoint = {
  x: number;
  y: number;
};

export function toGroundShapePoint(point: GroundPoint, origin: GroundPoint = { x: 0, y: 0 }): GroundPoint {
  return {
    x: point.x - origin.x,
    y: point.y - origin.y
  };
}

export function getPolygonTargetPlacement(): TargetPlacement {
  return {
    rotationX: -Math.PI / 2,
    positionY: 0
  };
}

export function getRoundTargetTopY(): number {
  return ROUND_TARGET_CENTER_Y + ROUND_TARGET_HEIGHT / 2;
}

export function getCoverageSurfaceY(): number {
  return Math.max(TARGET_SURFACE_HEIGHT, getRoundTargetTopY()) + COVERAGE_SURFACE_CLEARANCE;
}

export function getTargetBaseColor(type: string): number {
  if (type === 'polygon') return TARGET_POLYGON_COLOR;
  if (type === 'circle') return TARGET_CIRCLE_COLOR;
  return TARGET_POINT_COLOR;
}
