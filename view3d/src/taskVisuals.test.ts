import assert from 'node:assert/strict';
import test from 'node:test';
import {
  getTargetVisualState,
  normalizeCoveragePoints,
  normalizeCoverageSurfaces,
  normalizeTargetMotionPath,
  shouldRenderTargetMotionPath,
  summarizeCoverage
} from './taskVisuals.ts';
import type { TargetState, ViewerState } from './types.ts';

function makeState(overrides: Partial<ViewerState> = {}): ViewerState {
  return {
    server_time: 100,
    status: 'active',
    session: {
      id: 'session-1',
      name: 'Coverage Mission',
      task_type: 'area_coverage',
      canvas_width: 500,
      canvas_height: 400,
      is_distance_3d: false
    },
    drones: [],
    targets: [
      { id: 'area-1', name: 'Area 1', type: 'circle', position: { x: 200, y: 160, z: 0 }, radius: 50 }
    ],
    obstacles: [],
    paths: {},
    task_progress: {
      task_type: 'area_coverage',
      progress_percentage: 38,
      is_completed: false
    },
    environment: null,
    ...overrides
  };
}

test('normalizes coverage points from history payload and filters invalid entries', () => {
  const state = makeState({
    history: {
      area_coverage: {
        'area-1': {
          covered_points: [
            [10, 20],
            { x: 12.5, y: 24.25, z: 3 },
            ['bad', 30],
            [40]
          ]
        }
      }
    }
  } as Partial<ViewerState>);

  assert.deepEqual(normalizeCoveragePoints(state, 'area-1'), [
    { x: 10, y: 20, z: 0 },
    { x: 12.5, y: 24.25, z: 3 }
  ]);
});

test('normalizes coverage points from top-level session payload', () => {
  const state = makeState({
    area_coverage: {
      'area-1': {
        covered_points: [[100, 120, 4]]
      }
    }
  } as Partial<ViewerState>);

  assert.deepEqual(normalizeCoveragePoints(state, 'area-1'), [
    { x: 100, y: 120, z: 4 }
  ]);
});

test('normalizes continuous coverage surfaces from viewer payload', () => {
  const state = makeState({
    area_coverage_surfaces: {
      'area-1': {
        progress_percentage: 42.5,
        covered_area: 170,
        target_area: 400,
        surfaces: [
          {
            outer: [{ x: 1, y: 2 }, { x: 8, y: 2 }, { x: 8, y: 6 }],
            holes: [[{ x: 3, y: 3 }, { x: 4, y: 3 }, { x: 4, y: 4 }]]
          }
        ]
      }
    }
  } as Partial<ViewerState>);

  const surfaces = normalizeCoverageSurfaces(state, 'area-1');

  assert.equal(surfaces.length, 1);
  assert.deepEqual(surfaces[0].outer[0], { x: 1, y: 2, z: 0 });
  assert.equal(surfaces[0].holes?.[0].length, 3);
});

test('summarizes coverage count and percentage from task progress when present', () => {
  const state = makeState({
    history: {
      area_coverage: {
        'area-1': { covered_points: [[1, 2], [3, 4], [5, 6]] }
      }
    }
  } as Partial<ViewerState>);

  assert.deepEqual(summarizeCoverage(state, 'area-1'), {
    points: 3,
    progressPercentage: 38
  });
});

test('normalizes moving target path and appends velocity projection', () => {
  const target: TargetState = {
    id: 'moving-1',
    name: 'Moving 1',
    type: 'moving',
    position: { x: 50, y: 60, z: 0 },
    moving_path: [
      { x: 10, y: 20, z: 0 },
      { x: 30, y: 40, z: 0 }
    ],
    velocity: { x: 4, y: -2, z: 0 }
  };

  assert.deepEqual(normalizeTargetMotionPath(target), [
    { x: 10, y: 20, z: 0 },
    { x: 30, y: 40, z: 0 },
    { x: 90, y: 40, z: 0 }
  ]);
});

test('target motion path rendering is hidden by default and shown only by explicit toggle', () => {
  const target: TargetState = {
    id: 'moving-1',
    name: 'Moving 1',
    type: 'moving',
    position: { x: 50, y: 60, z: 0 },
    moving_path: [
      { x: 10, y: 20, z: 0 },
      { x: 30, y: 40, z: 0 }
    ]
  };

  assert.equal(shouldRenderTargetMotionPath(target), false);
  assert.equal(shouldRenderTargetMotionPath(target, false), false);
  assert.equal(shouldRenderTargetMotionPath(target, true), true);
  assert.equal(shouldRenderTargetMotionPath({ ...target, moving_path: [] }, true), false);
});

test('target visual state exposes completed, coverage, and motion labels', () => {
  assert.deepEqual(
    getTargetVisualState(
      { id: 'done', name: 'Done', type: 'fixed', position: { x: 0, y: 0, z: 0 }, is_reached: true },
      makeState()
    ),
    { color: 0x22c55e, label: '已完成', emphasis: 'complete' }
  );

  assert.deepEqual(
    getTargetVisualState(
      { id: 'area-1', name: 'Area 1', type: 'circle', position: { x: 0, y: 0, z: 0 } },
      makeState()
    ),
    { color: 0xfacc15, label: '覆盖 38%', emphasis: 'coverage' }
  );

  assert.deepEqual(
    getTargetVisualState(
      { id: 'area-1', name: 'Area 1', type: 'polygon', position: { x: 0, y: 0, z: 0 }, vertices: [
        { x: 0, y: 0, z: 0 },
        { x: 10, y: 0, z: 0 },
        { x: 10, y: 10, z: 0 }
      ] },
      makeState({
        area_coverage_surfaces: {
          'area-1': {
            progress_percentage: 100,
            covered_area: 100,
            target_area: 100,
            surfaces: []
          }
        }
      } as Partial<ViewerState>)
    ),
    { color: 0x22c55e, label: '覆盖 100%', emphasis: 'complete' }
  );

  assert.deepEqual(
    getTargetVisualState(
      { id: 'area-1', name: 'Area 1', type: 'circle', position: { x: 0, y: 0, z: 0 } },
      makeState({
        session: { ...makeState().session, task_type: 'others' },
        task_progress: undefined,
        area_coverage_surfaces: {
          'area-1': {
            progress_percentage: 42.5,
            covered_area: 170,
            target_area: 400,
            surfaces: []
          }
        }
      } as Partial<ViewerState>)
    ),
    { color: 0xfacc15, label: '覆盖 43%', emphasis: 'coverage' }
  );

  assert.deepEqual(
    getTargetVisualState(
      { id: 'area-1', name: 'Area 1', type: 'polygon', position: { x: 0, y: 0, z: 0 }, is_reached: true, vertices: [
        { x: 0, y: 0, z: 0 },
        { x: 10, y: 0, z: 0 },
        { x: 10, y: 10, z: 0 }
      ] },
      makeState({
        area_coverage_surfaces: {
          'area-1': {
            progress_percentage: 48,
            covered_area: 48,
            target_area: 100,
            surfaces: []
          }
        }
      } as Partial<ViewerState>)
    ),
    { color: 0xfacc15, label: '覆盖 48%', emphasis: 'coverage' }
  );

  assert.deepEqual(
    getTargetVisualState(
      { id: 'point', name: 'Point', type: 'fixed', position: { x: 0, y: 0, z: 0 } },
      makeState({
        session: { ...makeState().session, task_type: 'others' },
        task_progress: {}
      })
    ),
    { color: 0xfacc15, label: '目标', emphasis: 'normal' }
  );

  assert.deepEqual(
    getTargetVisualState(
      { id: 'moving', name: 'Moving', type: 'moving', position: { x: 0, y: 0, z: 0 } },
      makeState()
    ),
    { color: 0xfacc15, label: '动态目标', emphasis: 'motion' }
  );
});
