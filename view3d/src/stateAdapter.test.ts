import assert from 'node:assert/strict';
import test from 'node:test';

import { buildAreaCoverageSurfaces, sessionDataToViewerState } from './stateAdapter.ts';
import type { SessionData } from './types.ts';

function makeSession(overrides: Partial<SessionData> = {}): SessionData {
  return {
    id: 'session-1',
    name: 'Original Backend Session',
    description: 'Loaded from the unmodified drone API.',
    status: 'active',
    creator: 'system',
    task_type: 'area_coverage',
    task_description: 'Cover the search area.',
    canvas_width: 300,
    canvas_height: 240,
    is_distance_3d: false,
    created_at: 10,
    last_updated: 20,
    statistics: {
      task_progress: {
        task_type: 'area_coverage',
        progress_percentage: 35,
        is_completed: false
      }
    },
    drones: [
      {
        id: 'drone-1',
        name: 'Drone 1',
        status: 'moving',
        position: { x: 90, y: 90, z: 20 },
        task_radius: 18
      }
    ],
    targets: [
      {
        id: 'target-1',
        name: 'Search Area',
        type: 'polygon',
        position: { x: 100, y: 90, z: 0 },
        vertices: [
          { x: 40, y: 40, z: 0 },
          { x: 160, y: 40, z: 0 },
          { x: 160, y: 140, z: 0 },
          { x: 40, y: 140, z: 0 }
        ]
      }
    ],
    obstacles: [],
    environment: null,
    tasks: [],
    history: {
      path_history: {
        'drone-1': [
          { x: 50, y: 90, z: 20 },
          { x: 90, y: 90, z: 20 }
        ]
      },
      area_coverage: {
        'target-1': {
          covered_points: [[60, 90], [80, 90]]
        }
      }
    },
    ...overrides
  };
}

test('sessionDataToViewerState adapts original backend session data without viewer-specific API fields', () => {
  const state = sessionDataToViewerState(makeSession(), 1234);

  assert.equal(state.server_time, 1234);
  assert.equal(state.status, 'active');
  assert.equal(state.session?.id, 'session-1');
  assert.deepEqual(state.paths['drone-1'], [
    { x: 50, y: 90, z: 20 },
    { x: 90, y: 90, z: 20 }
  ]);
  assert.deepEqual(state.task_progress, {
    task_type: 'area_coverage',
    progress_percentage: 35,
    is_completed: false
  });
  assert.deepEqual(state.area_coverage?.['target-1'].covered_points, [[60, 90], [80, 90]]);
});

test('sessionDataToViewerState builds front-end continuous coverage surfaces from drone paths', () => {
  const state = sessionDataToViewerState(makeSession(), 1234);
  const surfacePayload = state.area_coverage_surfaces?.['target-1'];

  assert.ok(surfacePayload);
  assert.ok(surfacePayload.surfaces && surfacePayload.surfaces.length > 0);
  assert.ok((surfacePayload.progress_percentage ?? 0) > 0);
  assert.ok((surfacePayload.progress_percentage ?? 0) < 100);
});

test('buildAreaCoverageSurfaces emits the whole target as green surface when fully covered', () => {
  const surfaces = buildAreaCoverageSurfaces(
    [
      {
        id: 'target-full',
        name: 'Full Target',
        type: 'polygon',
        position: { x: 50, y: 50, z: 0 },
        vertices: [
          { x: 0, y: 0, z: 0 },
          { x: 100, y: 0, z: 0 },
          { x: 100, y: 100, z: 0 },
          { x: 0, y: 100, z: 0 }
        ]
      }
    ],
    [
      {
        id: 'drone-full',
        name: 'Wide Drone',
        status: 'moving',
        position: { x: 100, y: 100, z: 20 },
        coverage_width: 400
      }
    ],
    {
      'drone-full': [{ x: 0, y: 0, z: 20 }]
    }
  );

  assert.equal(surfaces['target-full'].progress_percentage, 100);
  assert.deepEqual(surfaces['target-full'].surfaces?.[0].outer, [
    { x: 0, y: 0, z: 0 },
    { x: 100, y: 0, z: 0 },
    { x: 100, y: 100, z: 0 },
    { x: 0, y: 100, z: 0 }
  ]);
});

test('buildAreaCoverageSurfaces renders partial coverage as path-aligned footprint strips', () => {
  const surfaces = buildAreaCoverageSurfaces(
    [
      {
        id: 'target-strip',
        name: 'Strip Target',
        type: 'polygon',
        position: { x: 50, y: 50, z: 0 },
        vertices: [
          { x: 0, y: 0, z: 0 },
          { x: 100, y: 0, z: 0 },
          { x: 100, y: 100, z: 0 },
          { x: 0, y: 100, z: 0 }
        ]
      }
    ],
    [
      {
        id: 'drone-strip',
        name: 'Strip Drone',
        status: 'moving',
        position: { x: 80, y: 50, z: 20 },
        coverage_width: 20
      }
    ],
    {
      'drone-strip': [{ x: 20, y: 50, z: 20 }]
    }
  );

  const outer = surfaces['target-strip'].surfaces?.[0].outer || [];
  assert.ok(outer.length >= 4);
  assert.ok(outer.some((point) => Math.abs(point.y - 40) < 0.001));
  assert.ok(outer.some((point) => Math.abs(point.y - 60) < 0.001));
  assert.ok(outer.every((point) => point.x >= 0 && point.x <= 100 && point.y >= 0 && point.y <= 100));
  assert.ok((surfaces['target-strip'].progress_percentage ?? 0) > 0);
  assert.ok((surfaces['target-strip'].progress_percentage ?? 0) < 100);
});
