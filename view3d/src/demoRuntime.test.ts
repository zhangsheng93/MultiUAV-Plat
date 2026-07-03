import assert from 'node:assert/strict';
import test from 'node:test';

import { moveDemoDroneTo, runDemoDroneCommand, runDemoRelativeMove } from './demoRuntime.ts';
import { createDemoState } from './demoState.ts';
import type { ViewerState } from './types.ts';

function makeDemoState(): ViewerState {
  return {
    server_time: 1,
    status: 'demo',
    session: {
      id: 'demo',
      name: 'Demo',
      task_type: 'others',
      canvas_width: 400,
      canvas_height: 300,
      is_distance_3d: false
    },
    drones: [
      { id: 'drone-1', name: 'Drone 1', status: 'hovering', position: { x: 10, y: 20, z: 30 } }
    ],
    targets: [],
    obstacles: [],
    paths: {
      'drone-1': [{ x: 10, y: 20, z: 30 }]
    },
    task_progress: {},
    environment: null
  };
}

test('moveDemoDroneTo updates selected drone position and appends path history', () => {
  const state = makeDemoState();
  const result = moveDemoDroneTo(state, 'drone-1', { x: 80, y: 90, z: 30 });

  assert.equal(result.ok, true);
  assert.deepEqual(state.drones[0].position, { x: 80, y: 90, z: 30 });
  assert.deepEqual(state.paths['drone-1'], [
    { x: 10, y: 20, z: 30 },
    { x: 80, y: 90, z: 30 }
  ]);
});

test('moveDemoDroneTo rejects missing drone ids', () => {
  const result = moveDemoDroneTo(makeDemoState(), 'missing', { x: 80, y: 90, z: 30 });

  assert.equal(result.ok, false);
});

test('moveDemoDroneTo refreshes demo coverage surfaces after path updates', () => {
  const state = createDemoState('demo');
  const before = state.area_coverage_surfaces?.['demo-area-1']?.progress_percentage ?? 0;

  const result = moveDemoDroneTo(state, 'demo-drone-1', { x: 315, y: 260, z: 55 });

  assert.equal(result.ok, true);
  const after = state.area_coverage_surfaces?.['demo-area-1']?.progress_percentage ?? 0;
  assert.ok(after > before);
  assert.ok((state.area_coverage_surfaces?.['demo-area-1']?.surfaces?.length ?? 0) > 0);
});

test('runDemoDroneCommand updates basic command state locally', () => {
  const state = makeDemoState();

  assert.equal(runDemoDroneCommand(state, 'drone-1', 'hover', 50).ok, true);
  assert.equal(state.drones[0].status, 'hovering');

  assert.equal(runDemoDroneCommand(state, 'drone-1', 'land', 50).ok, true);
  assert.equal(state.drones[0].status, 'idle');
  assert.equal(state.drones[0].position.z, 0);

  assert.equal(runDemoDroneCommand(state, 'drone-1', 'takeoff', 45).ok, true);
  assert.equal(state.drones[0].status, 'flying');
  assert.equal(state.drones[0].position.z, 45);
});

test('runDemoRelativeMove moves selected drone according to heading and altitude controls', () => {
  const state = makeDemoState();
  state.drones[0].heading = 0;

  assert.equal(runDemoRelativeMove(state, 'drone-1', 'forward', 20, 5).ok, true);
  assert.deepEqual(state.drones[0].position, { x: 10, y: 40, z: 30 });

  assert.equal(runDemoRelativeMove(state, 'drone-1', 'right', 20, 5).ok, true);
  assert.deepEqual(state.drones[0].position, { x: 30, y: 40, z: 30 });

  assert.equal(runDemoRelativeMove(state, 'drone-1', 'up', 20, 5).ok, true);
  assert.deepEqual(state.drones[0].position, { x: 30, y: 40, z: 35 });
});
