import assert from 'node:assert/strict';
import test from 'node:test';

import * as selectionVisuals from './selectionVisuals.ts';
import { buildSelectionPolygonPoints, getTargetSelectionVisualKind, getUniformLabelBaseScale } from './selectionVisuals.ts';
import type { TargetState } from './types.ts';

function makeTarget(partial: Partial<TargetState>): TargetState {
  return {
    id: 'target-1',
    name: 'Target',
    type: 'fixed',
    position: { x: 10, y: 20, z: 0 },
    ...partial
  };
}

test('label base scale is uniform regardless of label content length', () => {
  assert.deepEqual(getUniformLabelBaseScale(), { width: 68, height: 20 });
});

test('label texture metrics increase backing resolution without changing visual size', () => {
  const getLabelTextureMetrics = (selectionVisuals as unknown as {
    getLabelTextureMetrics?: (devicePixelRatio: number) => {
      cssWidth: number;
      cssHeight: number;
      backingWidth: number;
      backingHeight: number;
      pixelRatio: number;
    };
  }).getLabelTextureMetrics;

  assert.equal(typeof getLabelTextureMetrics, 'function');
  assert.deepEqual(getLabelTextureMetrics(2.4), {
    cssWidth: 512,
    cssHeight: 150,
    backingWidth: 1229,
    backingHeight: 360,
    pixelRatio: 2.4
  });
  assert.deepEqual(getLabelTextureMetrics(6), {
    cssWidth: 512,
    cssHeight: 150,
    backingWidth: 1536,
    backingHeight: 450,
    pixelRatio: 3
  });
  assert.deepEqual(getLabelTextureMetrics(0), {
    cssWidth: 512,
    cssHeight: 150,
    backingWidth: 512,
    backingHeight: 150,
    pixelRatio: 1
  });
});

test('polygon targets use polygon selection visuals instead of circular rings', () => {
  const polygon = makeTarget({
    type: 'polygon',
    vertices: [
      { x: 0, y: 0, z: 0 },
      { x: 20, y: 0, z: 0 },
      { x: 20, y: 20, z: 0 },
      { x: 0, y: 20, z: 0 }
    ]
  });
  const circle = makeTarget({ type: 'circle', radius: 10 });

  assert.equal(getTargetSelectionVisualKind(polygon), 'polygon');
  assert.equal(getTargetSelectionVisualKind(circle), 'circle');
});

test('polygon selection visual preserves square target footprint relative to its origin', () => {
  const points = buildSelectionPolygonPoints([
    { x: 0, y: 0, z: 0 },
    { x: 20, y: 0, z: 0 },
    { x: 20, y: 20, z: 0 },
    { x: 0, y: 20, z: 0 }
  ], { x: 10, y: 10, z: 0 });

  assert.deepEqual(points.map((point) => [point.x, point.y]), [
    [-10, -10],
    [10, -10],
    [10, 10],
    [-10, 10]
  ]);
});
