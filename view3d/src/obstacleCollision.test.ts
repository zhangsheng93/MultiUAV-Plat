import assert from 'node:assert/strict';
import test from 'node:test';
import { checkMovePathCollision } from './obstacleCollision.ts';
import type { ObstacleState, Position } from './types.ts';

const start: Position = { x: 0, y: 0, z: 20 };
const end: Position = { x: 100, y: 0, z: 20 };

function circleObstacle(overrides: Partial<ObstacleState> = {}): ObstacleState {
  return {
    id: 'obs-1',
    name: 'Building',
    type: 'circle',
    position: { x: 50, y: 0, z: 0 },
    radius: 10,
    height: 30,
    ...overrides
  };
}

test('3D obstacle precheck blocks paths below or at obstacle height', () => {
  const result = checkMovePathCollision(start, end, [circleObstacle()]);

  assert.equal(result.blocked, true);
  assert.equal(result.obstacleId, 'obs-1');
});

test('3D obstacle precheck allows paths above finite-height obstacles', () => {
  const result = checkMovePathCollision(
    { x: 0, y: 0, z: 40 },
    { x: 100, y: 0, z: 40 },
    [circleObstacle()]
  );

  assert.equal(result.blocked, false);
});

test('height zero obstacles are treated as non-flyable at any altitude', () => {
  const result = checkMovePathCollision(
    { x: 0, y: 0, z: 120 },
    { x: 100, y: 0, z: 120 },
    [circleObstacle({ height: 0 })]
  );

  assert.equal(result.blocked, true);
});

test('polygon obstacles block intersecting segments', () => {
  const result = checkMovePathCollision(start, end, [{
    id: 'poly-1',
    name: 'No Fly Polygon',
    type: 'polygon',
    position: { x: 0, y: 0, z: 0 },
    vertices: [
      { x: 40, y: -10, z: 0 },
      { x: 60, y: -10, z: 0 },
      { x: 60, y: 10, z: 0 },
      { x: 40, y: 10, z: 0 }
    ],
    height: 0
  }]);

  assert.equal(result.blocked, true);
  assert.equal(result.obstacleId, 'poly-1');
});

test('ellipse obstacles use width and length as radii like the 2D scene', () => {
  const result = checkMovePathCollision(start, end, [{
    id: 'ellipse-1',
    name: 'Ellipse',
    type: 'ellipse',
    position: { x: 50, y: 0, z: 0 },
    width: 8,
    length: 20,
    height: 25
  }]);

  assert.equal(result.blocked, true);
});
