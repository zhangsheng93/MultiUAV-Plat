import assert from 'node:assert/strict';
import test from 'node:test';
import { formatDroneInfoLines, formatObstacleInfoLines, formatTargetInfoLines, isDroneInFlight } from './entityLabel.ts';
import type { DroneState, ObstacleState, TargetState } from './types.ts';

function makeDrone(overrides: Partial<DroneState> = {}): DroneState {
  return {
    id: 'drone-1',
    name: 'Alpha',
    status: 'hovering',
    position: { x: 12.34, y: 56.78, z: 9.2 },
    heading: 91.6,
    speed: 3.4,
    battery_level: 76.2,
    ...overrides
  };
}

function makeTarget(overrides: Partial<TargetState> = {}): TargetState {
  return {
    id: 'target-1',
    name: 'Survey A',
    type: 'circle',
    position: { x: 100.12, y: 120.34, z: 0 },
    radius: 15,
    is_reached: false,
    ...overrides
  };
}

function makeObstacle(overrides: Partial<ObstacleState> = {}): ObstacleState {
  return {
    id: 'obstacle-1',
    name: 'Tower',
    type: 'circle',
    position: { x: 50.12, y: 60.34, z: 0 },
    radius: 10,
    height: 25,
    ...overrides
  };
}

test('drone label uses field names and includes full position and battery', () => {
  assert.deepEqual(formatDroneInfoLines(makeDrone(), false), [
    '名称：Alpha · 状态：悬停',
    '位置：x=12.3, y=56.8, z=9.2m',
    '剩余电量：76% · 速度：3.4m/s'
  ]);
  assert.deepEqual(formatDroneInfoLines(makeDrone({ name: '无人机 1' }), false, 'en-US'), [
    'Name: 无人机 1 · Status: Hovering',
    'Position: x=12.3, y=56.8, z=9.2m',
    'Battery: 76% · Speed: 3.4m/s'
  ]);
});

test('selected drone label adds heading without hiding battery', () => {
  assert.deepEqual(formatDroneInfoLines(makeDrone(), true), [
    '名称：Alpha · 状态：悬停',
    '位置：x=12.3, y=56.8, z=9.2m',
    '剩余电量：76% · 速度：3.4m/s · 航向：92°'
  ]);
});

test('drone in-flight detection covers airborne operating states', () => {
  assert.equal(isDroneInFlight(makeDrone({ status: 'idle' })), false);
  assert.equal(isDroneInFlight(makeDrone({ status: 'ready' })), false);
  assert.equal(isDroneInFlight(makeDrone({ status: 'hovering' })), true);
  assert.equal(isDroneInFlight(makeDrone({ status: 'moving' })), true);
  assert.equal(isDroneInFlight(makeDrone({ status: 'landing' })), true);
});

test('selected target label shows basic target details', () => {
  assert.deepEqual(formatTargetInfoLines(makeTarget(), true), [
    '目标：Survey A · 类型：圆形',
    '位置：x=100.1, y=120.3, z=0.0m',
    '半径：15m · 完成：否'
  ]);
  assert.deepEqual(formatTargetInfoLines(makeTarget({ name: '目标 2' }), true, 'en-US'), [
    'Target: 目标 2 · Type: Circle',
    'Position: x=100.1, y=120.3, z=0.0m',
    'Radius: 15m · Completed: No'
  ]);
});

test('selected obstacle label shows basic obstacle details', () => {
  assert.deepEqual(formatObstacleInfoLines(makeObstacle(), true), [
    '障碍物：Tower · 类型：圆形',
    '位置：x=50.1, y=60.3, z=0.0m',
    '高度：25m · 半径：10m'
  ]);
  assert.deepEqual(formatObstacleInfoLines(makeObstacle({ name: '障碍物 3', height: 0 }), true, 'en-US'), [
    'Obstacle: 障碍物 3 · Type: Circle',
    'Position: x=50.1, y=60.3, z=0.0m',
    'Height: Not flyable · Radius: 10m'
  ]);
});
