import assert from 'node:assert/strict';
import test from 'node:test';

import { applyDroneOverrides, setPerceivedRadiusOverride, type DroneOverrides } from './droneOverrides.ts';
import type { ViewerState } from './types.ts';

function makeState(): ViewerState {
  return {
    server_time: 0,
    status: 'active',
    session: {
      id: 'session-1',
      name: 'Session 1',
      task_type: 'others',
      canvas_width: 100,
      canvas_height: 100,
      is_distance_3d: false
    },
    drones: [
      { id: 'drone-1', name: 'Drone 1', status: 'idle', position: { x: 0, y: 0, z: 0 }, perceived_radius: 100 },
      { id: 'drone-2', name: 'Drone 2', status: 'idle', position: { x: 0, y: 0, z: 0 }, perceived_radius: 80 }
    ],
    targets: [],
    obstacles: [],
    paths: {},
    task_progress: {},
    environment: null
  };
}

test('setPerceivedRadiusOverride records finite positive radius values by drone id', () => {
  const overrides: DroneOverrides = {};

  setPerceivedRadiusOverride(overrides, 'drone-1', 125.456);

  assert.deepEqual(overrides, { perceivedRadius: { 'drone-1': 125.46 } });
});

test('applyDroneOverrides keeps local perceived radius values across backend polling refreshes', () => {
  const state = makeState();
  const overrides: DroneOverrides = { perceivedRadius: { 'drone-1': 150 } };

  applyDroneOverrides(state, overrides);

  assert.equal(state.drones[0].perceived_radius, 150);
  assert.equal(state.drones[1].perceived_radius, 80);
});
