import assert from 'node:assert/strict';
import test from 'node:test';
import { canDirectClickMove, getCommandAvailability } from './uiState.ts';
import type { DroneState } from './types.ts';

function makeDrone(status: string): DroneState {
  return {
    id: `drone-${status}`,
    name: `Drone ${status}`,
    status,
    position: { x: 0, y: 0, z: 0 }
  };
}

test('no selected drone disables all command buttons', () => {
  assert.deepEqual(getCommandAvailability(null), {
    takeoff: false,
    land: false,
    hover: false,
    returnHome: false,
    moveMode: false,
    charge: false,
    emergency: false,
    relativeMove: false,
    altitudeMove: false
  });
});

test('idle drone can only take off', () => {
  assert.deepEqual(getCommandAvailability(makeDrone('idle')), {
    takeoff: true,
    land: false,
    hover: false,
    returnHome: false,
    moveMode: false,
    charge: true,
    emergency: false,
    relativeMove: false,
    altitudeMove: false
  });
});

test('hovering drone can use in-air commands but cannot take off again', () => {
  assert.deepEqual(getCommandAvailability(makeDrone('hovering')), {
    takeoff: false,
    land: true,
    hover: true,
    returnHome: true,
    moveMode: true,
    charge: false,
    emergency: true,
    relativeMove: true,
    altitudeMove: true
  });
});

test('emergency drone disables all normal commands', () => {
  assert.deepEqual(getCommandAvailability(makeDrone('emergency')), {
    takeoff: false,
    land: false,
    hover: false,
    returnHome: false,
    moveMode: false,
    charge: false,
    emergency: false,
    relativeMove: false,
    altitudeMove: false
  });
});

test('direct map click movement mirrors 2D airborne selection behavior', () => {
  assert.equal(canDirectClickMove(makeDrone('flying')), true);
  assert.equal(canDirectClickMove(makeDrone('hovering')), true);
  assert.equal(canDirectClickMove(makeDrone('moving')), true);
  assert.equal(canDirectClickMove(makeDrone('idle')), false);
  assert.equal(canDirectClickMove(makeDrone('offline')), false);
  assert.equal(canDirectClickMove(makeDrone('emergency')), false);
  assert.equal(canDirectClickMove(null), false);
});
