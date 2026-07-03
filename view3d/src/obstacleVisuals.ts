export const NO_FLY_ZONE_VISUAL_HEIGHT = 90;
export const OBSTACLE_ELLIPSE_COLOR = 0x4f526f;
export const OBSTACLE_CIRCLE_COLOR = 0x92400e;
export const OBSTACLE_POLYGON_COLOR = 0x6b7280;

export type ObstaclePlacement = {
  rotationX: number;
  positionY: number;
};

export type ObstacleMaterialSettings = {
  transparent: boolean;
  opacity: number;
};

export function getPolygonObstaclePlacement(height: number): ObstaclePlacement {
  return {
    rotationX: -Math.PI / 2,
    positionY: 0
  };
}

export function getObstacleVisualHeight(height: number | undefined): number {
  return height === 0 ? NO_FLY_ZONE_VISUAL_HEIGHT : Math.max(1, height || 10);
}

export function getObstacleMaterialSettings(height: number | undefined): ObstacleMaterialSettings {
  if (height === 0) {
    return {
      transparent: false,
      opacity: 1
    };
  }
  return {
    transparent: true,
    opacity: 0.72
  };
}

export function getObstacleBaseColor(type: string): number {
  if (type === 'ellipse') return OBSTACLE_ELLIPSE_COLOR;
  if (type === 'circle' || type === 'point') return OBSTACLE_CIRCLE_COLOR;
  return OBSTACLE_POLYGON_COLOR;
}
