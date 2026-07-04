import assert from 'node:assert/strict';
import test from 'node:test';
import { getRoamPathLength, getRoamSpeed, getRoamTurnDistance, getSmoothedRoamForward, normalizeRoamPath, sampleRoamPath, stepRoamSpeedMultiplier } from './cameraRoam.ts';

test('normalizeRoamPath appends current position and removes consecutive duplicates', () => {
  assert.deepEqual(
    normalizeRoamPath([
      { x: 0, y: 0, z: 10 },
      { x: 0, y: 0, z: 10 },
      { x: 10, y: 0, z: 10 }
    ], { x: 10, y: 0, z: 10 }),
    [
      { x: 0, y: 0, z: 10 },
      { x: 10, y: 0, z: 10 }
    ]
  );
});

test('normalizeRoamPath reverses latest-first histories so roam starts at the earliest point', () => {
  assert.deepEqual(
    normalizeRoamPath([
      { x: 30, y: 30, z: 20 },
      { x: 20, y: 20, z: 20 },
      { x: 10, y: 10, z: 20 }
    ], { x: 30, y: 30, z: 20 }),
    [
      { x: 10, y: 10, z: 20 },
      { x: 20, y: 20, z: 20 },
      { x: 30, y: 30, z: 20 }
    ]
  );
});

test('normalizeRoamPath reverses latest-first histories when the current position is newer than history', () => {
  assert.deepEqual(
    normalizeRoamPath([
      { x: 25, y: 25, z: 20 },
      { x: 20, y: 20, z: 20 },
      { x: 10, y: 10, z: 20 }
    ], { x: 30, y: 30, z: 20 }),
    [
      { x: 10, y: 10, z: 20 },
      { x: 20, y: 20, z: 20 },
      { x: 25, y: 25, z: 20 },
      { x: 30, y: 30, z: 20 }
    ]
  );
});

test('normalizeRoamPath preserves earliest-first histories and appends the current position once', () => {
  assert.deepEqual(
    normalizeRoamPath([
      { x: 10, y: 10, z: 20 },
      { x: 20, y: 20, z: 20 }
    ], { x: 30, y: 30, z: 20 }),
    [
      { x: 10, y: 10, z: 20 },
      { x: 20, y: 20, z: 20 },
      { x: 30, y: 30, z: 20 }
    ]
  );
});

test('getRoamPathLength sums 3D segment distances', () => {
  assert.equal(getRoamPathLength([
    { x: 0, y: 0, z: 0 },
    { x: 3, y: 4, z: 0 },
    { x: 3, y: 4, z: 12 }
  ]), 17);
});

test('sampleRoamPath interpolates by distance and exposes path tangent target', () => {
  const sample = sampleRoamPath([
    { x: 0, y: 0, z: 10 },
    { x: 10, y: 0, z: 10 },
    { x: 10, y: 10, z: 20 }
  ], 5);

  assert.deepEqual(sample?.position, { x: 5, y: 0, z: 10 });
  assert.deepEqual(sample?.nextPosition, { x: 10, y: 0, z: 10 });
  assert.ok(sample?.forwardHint.x && sample.forwardHint.x > 0);
  assert.equal(sample?.segmentIndex, 0);
  assert.equal(sample?.done, false);
});

test('sampleRoamPath starts at the first normalized history point at distance zero', () => {
  const path = normalizeRoamPath([
    { x: 30, y: 30, z: 20 },
    { x: 20, y: 20, z: 20 },
    { x: 10, y: 10, z: 20 }
  ], { x: 30, y: 30, z: 20 });
  const sample = sampleRoamPath(path, 0);

  assert.deepEqual(sample?.position, { x: 10, y: 10, z: 20 });
  assert.equal(sample?.segmentIndex, 0);
  assert.equal(sample?.done, false);
});

test('sampleRoamPath rejects empty, single-point, and repeated-only paths', () => {
  assert.equal(sampleRoamPath([], 0), null);
  assert.equal(sampleRoamPath([{ x: 0, y: 0, z: 0 }], 0), null);
  assert.equal(sampleRoamPath([{ x: 0, y: 0, z: 0 }, { x: 0, y: 0, z: 0 }], 0), null);
});

test('getRoamSpeed uses drone speed, then max speed, then default with clamps', () => {
  assert.equal(getRoamSpeed({ id: 'd1', name: 'D1', status: 'moving', position: { x: 0, y: 0, z: 0 }, speed: 2, max_speed: 60 }), 5);
  assert.equal(getRoamSpeed({ id: 'd2', name: 'D2', status: 'moving', position: { x: 0, y: 0, z: 0 }, speed: 25, max_speed: 60 }), 25);
  assert.equal(getRoamSpeed({ id: 'd3', name: 'D3', status: 'moving', position: { x: 0, y: 0, z: 0 }, max_speed: 90 }), 80);
  assert.equal(getRoamSpeed({ id: 'd4', name: 'D4', status: 'moving', position: { x: 0, y: 0, z: 0 } }), 20);
});

test('getRoamTurnDistance scales with speed and clamps', () => {
  assert.equal(getRoamTurnDistance(5), 8);
  assert.equal(getRoamTurnDistance(20), 16);
  assert.equal(getRoamTurnDistance(80), 24);
});

test('stepRoamSpeedMultiplier adjusts roam speed within fixed bounds', () => {
  assert.equal(stepRoamSpeedMultiplier(1, 1), 1.25);
  assert.equal(stepRoamSpeedMultiplier(1, -1), 0.8);
  assert.equal(stepRoamSpeedMultiplier(4, 1), 4);
  assert.equal(stepRoamSpeedMultiplier(0.25, -1), 0.25);
  assert.equal(stepRoamSpeedMultiplier(Number.NaN, 1), 1.25);
});

test('smoothed roam forward keeps straight paths aligned to the segment', () => {
  const forward = getSmoothedRoamForward([
    { x: 0, y: 0, z: 0 },
    { x: 20, y: 0, z: 0 },
    { x: 40, y: 0, z: 0 }
  ], 0, 10, 20, 8);

  assert.ok(Math.abs(forward.x - 1) < 0.001);
  assert.ok(Math.abs(forward.y) < 0.001);
  assert.ok(Math.abs(forward.z) < 0.001);
});

test('smoothed roam forward starts turning before a 90 degree corner', () => {
  const sample = sampleRoamPath([
    { x: 0, y: 0, z: 0 },
    { x: 20, y: 0, z: 0 },
    { x: 20, y: 20, z: 0 }
  ], 17, 8);

  assert.ok(sample);
  assert.ok(sample!.forwardHint.x > 0.4);
  assert.ok(sample!.forwardHint.y > 0.2);
  assert.ok(sample!.forwardHint.x < 1);
});

test('smoothed roam forward continues turning after a corner', () => {
  const sample = sampleRoamPath([
    { x: 0, y: 0, z: 0 },
    { x: 20, y: 0, z: 0 },
    { x: 20, y: 20, z: 0 }
  ], 23, 8);

  assert.ok(sample);
  assert.ok(sample!.forwardHint.x > 0.2);
  assert.ok(sample!.forwardHint.y > 0.4);
  assert.ok(sample!.forwardHint.y < 1);
});

test('smoothed roam forward does not restart after crossing a corner', () => {
  const path = [
    { x: 0, y: 0, z: 0 },
    { x: 20, y: 0, z: 0 },
    { x: 20, y: 20, z: 0 }
  ];
  const beforeCorner = sampleRoamPath(path, 19.9, 8);
  const afterCorner = sampleRoamPath(path, 20.1, 8);

  assert.ok(beforeCorner);
  assert.ok(afterCorner);
  assert.ok(beforeCorner!.forwardHint.x > 0.55);
  assert.ok(beforeCorner!.forwardHint.y > 0.55);
  assert.ok(afterCorner!.forwardHint.x > 0.55);
  assert.ok(afterCorner!.forwardHint.y > 0.55);
  assert.ok(Math.abs(afterCorner!.forwardHint.x - beforeCorner!.forwardHint.x) < 0.04);
  assert.ok(Math.abs(afterCorner!.forwardHint.y - beforeCorner!.forwardHint.y) < 0.04);
});

test('smoothed roam forward turns smoothly through near-180 degree corners', () => {
  const path = [
    { x: 0, y: 0, z: 0 },
    { x: 20, y: 0, z: 0 },
    { x: 0, y: 0, z: 0 }
  ];
  const beforeCorner = sampleRoamPath(path, 19.9, 8);
  const afterCorner = sampleRoamPath(path, 20.1, 8);

  assert.ok(beforeCorner);
  assert.ok(afterCorner);
  assert.ok(beforeCorner!.forwardHint.y > 0.9);
  assert.ok(afterCorner!.forwardHint.y > 0.9);
  assert.ok(dotForTest(beforeCorner!.forwardHint, afterCorner!.forwardHint) > 0.99);
});

test('smoothed roam forward handles endpoints and short segments without invalid values', () => {
  const endpoint = sampleRoamPath([
    { x: 0, y: 0, z: 0 },
    { x: 4, y: 0, z: 0 },
    { x: 4, y: 4, z: 0 }
  ], 8, 24);

  assert.ok(endpoint);
  assert.equal(Number.isFinite(endpoint!.forwardHint.x), true);
  assert.equal(Number.isFinite(endpoint!.forwardHint.y), true);
  assert.equal(Number.isFinite(endpoint!.forwardHint.z), true);
  assert.ok(Math.hypot(endpoint!.forwardHint.x, endpoint!.forwardHint.y, endpoint!.forwardHint.z) > 0.9);
});

function dotForTest(a: { x: number; y: number; z: number }, b: { x: number; y: number; z: number }): number {
  return a.x * b.x + a.y * b.y + a.z * b.z;
}
