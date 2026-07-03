import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildRelativeMovement,
  normalizeHeading,
  type RelativeMoveAction
} from './movementControls.ts';
import type { DroneState } from './types.ts';

function makeDrone(overrides: Partial<DroneState> = {}): DroneState {
  return {
    id: 'd1',
    name: 'Drone 1',
    status: 'hovering',
    position: { x: 100, y: 200, z: 40 },
    heading: 45,
    max_altitude: 120,
    ...overrides
  };
}

test('normalizes headings to compass range', () => {
  assert.equal(normalizeHeading(370), 10);
  assert.equal(normalizeHeading(-90), 270);
});

test('relative horizontal movement uses drone heading and side bearings', () => {
  const cases: Array<[RelativeMoveAction, number]> = [
    ['forward', 45],
    ['backward', 225],
    ['left', 315],
    ['right', 135]
  ];

  for (const [action, heading] of cases) {
    assert.deepEqual(buildRelativeMovement(makeDrone(), action, 20, 5), {
      kind: 'move_towards',
      distance: 20,
      heading
    });
  }
});

test('relative altitude movement clamps to ground and max altitude', () => {
  assert.deepEqual(buildRelativeMovement(makeDrone(), 'up', 20, 100), {
    kind: 'change_altitude',
    altitude: 120
  });
  assert.deepEqual(buildRelativeMovement(makeDrone({ position: { x: 0, y: 0, z: 3 } }), 'down', 20, 10), {
    kind: 'change_altitude',
    altitude: 0
  });
});
