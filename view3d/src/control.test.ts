import assert from 'node:assert/strict';
import test from 'node:test';
import { canUseAirCommand } from './commandRules.ts';
import type { DroneState } from './types.ts';

function makeDrone(status: string): DroneState {
  return {
    id: `drone-${status}`,
    name: `Drone ${status}`,
    status,
    position: { x: 0, y: 0, z: 0 }
  };
}

test('air commands require a selected operational drone', () => {
  assert.equal(canUseAirCommand(null), false);
  assert.equal(canUseAirCommand(makeDrone('offline')), false);
  assert.equal(canUseAirCommand(makeDrone('emergency')), false);
  assert.equal(canUseAirCommand(makeDrone('idle')), true);
  assert.equal(canUseAirCommand(makeDrone('hovering')), true);
});
