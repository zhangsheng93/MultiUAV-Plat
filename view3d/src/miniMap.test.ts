import assert from 'node:assert/strict';
import test from 'node:test';
import {
  miniMapToWorld,
  resolveMiniMapBounds,
  worldToMiniMap
} from './miniMap.ts';
import type { ViewerState } from './types.ts';

function makeState(overrides: Partial<ViewerState> = {}): ViewerState {
  return {
    server_time: 100,
    status: 'active',
    session: {
      id: 'session-1',
      name: 'Demo',
      task_type: 'target_tracking',
      canvas_width: 400,
      canvas_height: 300,
      is_distance_3d: false
    },
    drones: [
      { id: 'd1', name: 'D1', status: 'hovering', position: { x: 20, y: 40, z: 30 } }
    ],
    targets: [
      { id: 't1', name: 'T1', type: 'circle', position: { x: 350, y: 250, z: 0 }, radius: 30 }
    ],
    obstacles: [
      { id: 'o1', name: 'O1', type: 'polygon', position: { x: 100, y: 100, z: 0 }, vertices: [
        { x: -20, y: 10, z: 0 },
        { x: 80, y: 50, z: 0 },
        { x: 60, y: 120, z: 0 }
      ] }
    ],
    paths: {},
    task_progress: {},
    environment: null,
    ...overrides
  };
}

test('mini map bounds include session canvas and object extents', () => {
  const bounds = resolveMiniMapBounds(makeState());

  assert.equal(bounds.minX, -20);
  assert.equal(bounds.minY, 0);
  assert.equal(bounds.maxX, 1024);
  assert.equal(bounds.maxY, 768);
});

test('mini map maps world points with y-up semantics and can invert the click', () => {
  const bounds = { minX: 0, minY: 0, maxX: 400, maxY: 300 };
  const size = { width: 220, height: 160, padding: 10 };

  assert.deepEqual(worldToMiniMap({ x: 0, y: 0, z: 0 }, bounds, size), { x: 10, y: 150 });
  assert.deepEqual(worldToMiniMap({ x: 400, y: 300, z: 0 }, bounds, size), { x: 210, y: 10 });
  assert.deepEqual(miniMapToWorld({ x: 110, y: 80 }, bounds, size), { x: 200, y: 150, z: 0 });
});
