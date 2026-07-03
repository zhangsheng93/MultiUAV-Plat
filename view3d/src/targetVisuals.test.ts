import assert from 'node:assert/strict';
import test from 'node:test';
import * as THREE from 'three';
import {
  TARGET_CIRCLE_COLOR,
  TARGET_POLYGON_COLOR,
  TARGET_POINT_COLOR,
  TARGET_SURFACE_HEIGHT,
  getCoverageSurfaceY,
  getPolygonTargetPlacement,
  getRoundTargetTopY,
  getTargetBaseColor,
  toGroundShapePoint
} from './targetVisuals.ts';

test('polygon target surface renders as a shallow volume above the ground plane', () => {
  const shape = new THREE.Shape([
    new THREE.Vector2(-10, -10),
    new THREE.Vector2(10, -10),
    new THREE.Vector2(10, 10),
    new THREE.Vector2(-10, 10)
  ]);
  const geometry = new THREE.ExtrudeGeometry(shape, { depth: TARGET_SURFACE_HEIGHT, bevelEnabled: false });
  const mesh = new THREE.Mesh(geometry);
  const placement = getPolygonTargetPlacement();

  mesh.rotation.x = placement.rotationX;
  mesh.position.y = placement.positionY;
  mesh.updateMatrixWorld(true);

  const bounds = new THREE.Box3().setFromObject(mesh);
  assert.equal(Math.abs(Math.round(bounds.min.y * 1000) / 1000), 0);
  assert.equal(Math.round(bounds.max.y * 1000) / 1000, TARGET_SURFACE_HEIGHT);
});

test('ground shape projection preserves world x/y after extrusion rotation', () => {
  const origin = { x: 100, y: 100 };
  const vertex = { x: 110, y: 140 };
  const projected = toGroundShapePoint(vertex, origin);
  const point = new THREE.Vector3(projected.x, projected.y, 0);
  const placement = getPolygonTargetPlacement();
  point.applyEuler(new THREE.Euler(placement.rotationX, 0, 0));
  point.add(new THREE.Vector3(origin.x, 0, -origin.y));

  assert.equal(Math.round(point.x * 1000) / 1000, vertex.x);
  assert.equal(Math.round(point.z * 1000) / 1000, -vertex.y);
});

test('coverage surface is above target geometry so green coverage remains visible', () => {
  assert.ok(getCoverageSurfaceY() > TARGET_SURFACE_HEIGHT);
  assert.ok(getCoverageSurfaceY() > getRoundTargetTopY());
});

test('target base colors match 2D geometry semantics', () => {
  assert.equal(getTargetBaseColor('polygon'), TARGET_POLYGON_COLOR);
  assert.equal(getTargetBaseColor('circle'), TARGET_CIRCLE_COLOR);
  assert.equal(getTargetBaseColor('fixed'), TARGET_POINT_COLOR);
});
