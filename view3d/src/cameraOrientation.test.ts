import assert from 'node:assert/strict';
import test from 'node:test';
import * as THREE from 'three';

import { getTopViewCameraUp, getWorldViewCameraUp } from './cameraOrientation.ts';

function normalizedArray(vector: THREE.Vector3): number[] {
  return vector.toArray().map((value) => Object.is(value, -0) ? 0 : value);
}

test('top view uses the same screen directions as the 2D map', () => {
  const forward = new THREE.Vector3(0, -1, 0);
  const up = getTopViewCameraUp();
  const right = new THREE.Vector3().crossVectors(forward, up);

  assert.deepEqual(normalizedArray(right), [1, 0, 0]);
  assert.deepEqual(normalizedArray(up), [0, 0, -1]);
});

test('world view keeps altitude as the camera up direction', () => {
  assert.deepEqual(normalizedArray(getWorldViewCameraUp()), [0, 1, 0]);
});
