import * as THREE from 'three';
import type { Position, TargetState } from './types.ts';
import { toGroundShapePoint } from './targetVisuals.ts';

export type SelectionVisualKind = 'circle' | 'polygon';

export type LabelBaseScale = {
  width: number;
  height: number;
};

export type LabelTextureMetrics = {
  cssWidth: number;
  cssHeight: number;
  backingWidth: number;
  backingHeight: number;
  pixelRatio: number;
};

const LABEL_CSS_WIDTH = 512;
const LABEL_CSS_HEIGHT = 150;
const LABEL_TEXTURE_PIXEL_RATIO_MAX = 3;

function normalizeTexturePixelRatio(value: number): number {
  if (!Number.isFinite(value) || value <= 0) return 1;
  return Math.min(LABEL_TEXTURE_PIXEL_RATIO_MAX, Math.max(1, value));
}

export function getUniformLabelBaseScale(): LabelBaseScale {
  return { width: 68, height: 20 };
}

export function getLabelTextureMetrics(devicePixelRatio: number): LabelTextureMetrics {
  const pixelRatio = normalizeTexturePixelRatio(devicePixelRatio);
  return {
    cssWidth: LABEL_CSS_WIDTH,
    cssHeight: LABEL_CSS_HEIGHT,
    backingWidth: Math.round(LABEL_CSS_WIDTH * pixelRatio),
    backingHeight: Math.round(LABEL_CSS_HEIGHT * pixelRatio),
    pixelRatio
  };
}

export function getTargetSelectionVisualKind(target: TargetState): SelectionVisualKind {
  return target.type === 'polygon' && (target.vertices?.length || 0) >= 3 ? 'polygon' : 'circle';
}

export function buildSelectionPolygonPoints(points: Position[], origin: Position): THREE.Vector2[] {
  return points.map((point) => {
    const projected = toGroundShapePoint(point, origin);
    return new THREE.Vector2(projected.x, projected.y);
  });
}
