import assert from 'node:assert/strict';
import test from 'node:test';
import { getSceneCameraFarPlane, getSceneGroundDimensions, getTopViewCameraDistance, resolveSceneBounds } from './sceneBounds.ts';
import type { ViewerState } from './types.ts';

function makeState(overrides: Partial<ViewerState> = {}): ViewerState {
  return {
    server_time: 100,
    status: 'active',
    session: {
      id: 'session-1',
      name: 'Extended Mission',
      task_type: 'area_coverage',
      canvas_width: 400,
      canvas_height: 300,
      is_distance_3d: false
    },
    drones: [
      { id: 'd1', name: 'D1', status: 'hovering', position: { x: 620, y: 480, z: 40 }, home_position: { x: 20, y: 30, z: 0 } }
    ],
    targets: [],
    obstacles: [],
    paths: {
      d1: [
        { x: 20, y: 30, z: 0 },
        { x: 760, y: -140, z: 40 }
      ]
    },
    task_progress: {},
    area_coverage_surfaces: {
      area1: {
        surfaces: [
          {
            outer: [{ x: 650, y: 470 }, { x: 820, y: 470 }, { x: 820, y: 620 }, { x: 650, y: 620 }]
          }
        ]
      }
    },
    environment: null,
    ...overrides
  };
}

test('scene bounds expand beyond the nominal canvas to include flight paths and coverage surfaces', () => {
  const bounds = resolveSceneBounds(makeState(), 100);

  assert.equal(bounds.minX, -100);
  assert.equal(bounds.minY, -240);
  assert.equal(bounds.maxX, 1124);
  assert.equal(bounds.maxY, 868);
  assert.equal(bounds.width, 1224);
  assert.equal(bounds.height, 1108);
  assert.equal(bounds.centerX, 512);
  assert.equal(bounds.centerY, 314);
  assert.equal(bounds.size, 1224);
});

test('ground dimensions preserve rectangular scene bounds instead of forcing a square', () => {
  const bounds = resolveSceneBounds(makeState(), 100);
  const ground = getSceneGroundDimensions(bounds, 1.2);

  assert.equal(ground.width, bounds.width * 1.2);
  assert.equal(ground.height, bounds.height * 1.2);
  assert.equal(ground.baseSize, ground.width);
  assert.equal(ground.gridScaleX, 1);
  assert.equal(Math.round(ground.gridScaleZ * 1000) / 1000, 0.905);
  assert.ok(ground.height < ground.width);
});

test('scene bounds use at least 1024 by 768 when session canvas is smaller', () => {
  const bounds = resolveSceneBounds(makeState({
    drones: [],
    paths: {},
    area_coverage_surfaces: {}
  }), 0);

  assert.equal(bounds.minX, 0);
  assert.equal(bounds.minY, 0);
  assert.equal(bounds.maxX, 1024);
  assert.equal(bounds.maxY, 768);
  assert.equal(bounds.width, 1024);
  assert.equal(bounds.height, 768);
});

test('scene bounds keep a larger session canvas as the minimum extent', () => {
  const bounds = resolveSceneBounds(makeState({
    session: {
      id: 'session-large',
      name: 'Large Mission',
      task_type: 'area_coverage',
      canvas_width: 1800,
      canvas_height: 1200,
      is_distance_3d: false
    },
    drones: [],
    paths: {},
    area_coverage_surfaces: {}
  }), 0);

  assert.equal(bounds.minX, 0);
  assert.equal(bounds.minY, 0);
  assert.equal(bounds.maxX, 1800);
  assert.equal(bounds.maxY, 1200);
  assert.equal(bounds.width, 1800);
  assert.equal(bounds.height, 1200);
});

test('scene bounds expand beyond the canvas minimum for distant visible content', () => {
  const bounds = resolveSceneBounds(makeState({
    drones: [
      { id: 'd-far', name: 'Far', status: 'hovering', position: { x: 2200, y: 1600, z: 20 } }
    ],
    paths: {},
    area_coverage_surfaces: {}
  }), 50);

  assert.equal(bounds.minX, -50);
  assert.equal(bounds.minY, -50);
  assert.equal(bounds.maxX, 2250);
  assert.equal(bounds.maxY, 1650);
  assert.equal(bounds.width, 2300);
  assert.equal(bounds.height, 1700);
});

test('scene bounds ignore historical coverage that is not currently visible', () => {
  const bounds = resolveSceneBounds(makeState({
    drones: [],
    paths: {},
    area_coverage_surfaces: {},
    history: {
      area_coverage: {
        old: {
          covered_points: [{ x: 5000, y: 5000, z: 0 }]
        }
      }
    }
  }), 0);

  assert.equal(bounds.maxX, 1024);
  assert.equal(bounds.maxY, 768);
});

test('top view camera distance leaves padding for wide and tall scene bounds', () => {
  const wideDistance = getTopViewCameraDistance({ width: 1600, height: 600 }, 55, 16 / 9);
  const tallDistance = getTopViewCameraDistance({ width: 600, height: 1600 }, 55, 16 / 9);

  assert.ok(wideDistance > 860);
  assert.ok(tallDistance > 2000);
  assert.equal(getTopViewCameraDistance({ width: 10, height: 10 }, 55, 16 / 9), 500);
});

test('camera far plane covers the ground at minimum zoom', () => {
  const bounds = resolveSceneBounds(makeState(), 100);

  assert.equal(getSceneCameraFarPlane({ width: 10, height: 10, size: 10 }, 0.4, 1.2), 5000);
  assert.ok(getSceneCameraFarPlane(bounds, 0.4, 1.2) > 7000);
});
