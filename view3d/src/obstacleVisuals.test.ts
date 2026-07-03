import assert from 'node:assert/strict';
import test from 'node:test';
import * as THREE from 'three';
import {
  getObstacleBaseColor,
  getObstacleMaterialSettings,
  getObstacleVisualHeight,
  getPolygonObstaclePlacement,
  NO_FLY_ZONE_VISUAL_HEIGHT,
  OBSTACLE_CIRCLE_COLOR,
  OBSTACLE_ELLIPSE_COLOR,
  OBSTACLE_POLYGON_COLOR
} from './obstacleVisuals.ts';

test('flat obstacle areas render as raised obstacle volumes', () => {
  assert.equal(getObstacleVisualHeight(0), NO_FLY_ZONE_VISUAL_HEIGHT);
  assert.equal(getObstacleVisualHeight(undefined), 10);
  assert.equal(getObstacleVisualHeight(24), 24);
});

test('flat obstacle areas use opaque materials to avoid transparent sort flicker', () => {
  assert.deepEqual(getObstacleMaterialSettings(0), {
    transparent: false,
    opacity: 1
  });
  assert.deepEqual(getObstacleMaterialSettings(24), {
    transparent: true,
    opacity: 0.72
  });
});

test('polygon obstacle extrusion stays above the ground plane', () => {
  const height = 90;
  const shape = new THREE.Shape([
    new THREE.Vector2(-10, -10),
    new THREE.Vector2(10, -10),
    new THREE.Vector2(10, 10),
    new THREE.Vector2(-10, 10)
  ]);
  const geometry = new THREE.ExtrudeGeometry(shape, { depth: height, bevelEnabled: false });
  const mesh = new THREE.Mesh(geometry);
  const placement = getPolygonObstaclePlacement(height);

  mesh.rotation.x = placement.rotationX;
  mesh.position.y = placement.positionY;
  mesh.updateMatrixWorld(true);

  const bounds = new THREE.Box3().setFromObject(mesh);
  assert.equal(Math.abs(Math.round(bounds.min.y * 1000) / 1000), 0);
  assert.equal(Math.round(bounds.max.y * 1000) / 1000, height);
});

test('obstacle base colors match 2D geometry semantics', () => {
  assert.equal(getObstacleBaseColor('ellipse'), OBSTACLE_ELLIPSE_COLOR);
  assert.equal(getObstacleBaseColor('circle'), OBSTACLE_CIRCLE_COLOR);
  assert.equal(getObstacleBaseColor('point'), OBSTACLE_CIRCLE_COLOR);
  assert.equal(getObstacleBaseColor('polygon'), OBSTACLE_POLYGON_COLOR);
});
