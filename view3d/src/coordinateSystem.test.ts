import assert from 'node:assert/strict';
import test from 'node:test';
import * as THREE from 'three';

import { getSceneAxisEnd, sceneGroundToWorld, worldToScenePosition } from './coordinateSystem.ts';
import { getTopViewCameraUp } from './cameraOrientation.ts';

test('world y maps to negative scene z so top view matches 2D directions', () => {
  assert.deepEqual(worldToScenePosition({ x: 10, y: 20, z: 30 }).toArray(), [10, 30, -20]);
  assert.deepEqual(sceneGroundToWorld(new THREE.Vector3(10, 0, -20)), { x: 10, y: 20, z: 0 });
});

test('top camera projection maps world +x right and world +y up', () => {
  const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 5000);
  camera.up.copy(getTopViewCameraUp());
  camera.position.set(0, 100, 0);
  camera.lookAt(0, 0, 0);
  camera.updateMatrixWorld(true);
  camera.updateProjectionMatrix();

  const origin = worldToScenePosition({ x: 0, y: 0, z: 0 }).project(camera);
  const plusX = worldToScenePosition({ x: 10, y: 0, z: 0 }).project(camera);
  const plusY = worldToScenePosition({ x: 0, y: 10, z: 0 }).project(camera);

  assert.ok(plusX.x > origin.x);
  assert.ok(plusY.y > origin.y);
});

test('visual axis endpoints use 2D world directions on the ground plane', () => {
  assert.deepEqual(getSceneAxisEnd('x', 10).toArray(), [10, 0, 0]);
  assert.deepEqual(getSceneAxisEnd('y', 10).toArray(), [0, 0, -10]);
  assert.deepEqual(getSceneAxisEnd('z', 10).toArray(), [0, 10, 0]);
});
