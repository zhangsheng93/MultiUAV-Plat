import assert from 'node:assert/strict';
import test from 'node:test';
import { nextLocale, normalizeLocale, t, translateDataValue } from './i18n.ts';

test('normalizes and toggles supported locales', () => {
  assert.equal(normalizeLocale('en-US'), 'en-US');
  assert.equal(normalizeLocale('zh-CN'), 'zh-CN');
  assert.equal(normalizeLocale('fr-FR'), 'en-US');
  assert.equal(normalizeLocale(null), 'en-US');
  assert.equal(nextLocale('zh-CN'), 'en-US');
  assert.equal(nextLocale('en-US'), 'zh-CN');
});

test('translates interface labels with interpolation', () => {
  assert.equal(t('zh-CN', 'camera.free'), '自由视角');
  assert.equal(t('en-US', 'camera.free'), 'Free');
  assert.equal(t('zh-CN', 'camera.roam'), '漫游');
  assert.equal(t('en-US', 'camera.roam'), 'Roam');
  assert.equal(t('en-US', 'cheat.cameraRoam'), 'Roam path');
  assert.equal(t('en-US', 'session.summary', { drones: 2, targets: 1, obstacles: 3 }), '2 drones · 1 targets · 3 obstacles');
  assert.equal(t('zh-CN', 'activity.selection', { kind: '无人机', name: 'Alpha', id: 'd1' }), '已选择 无人机 Alpha（ID: d1），查看详细信息；右键取消选择。');
  assert.equal(t('en-US', 'activity.cameraChanged', { mode: 'Top' }), 'Switched to Top view.');
  assert.equal(t('zh-CN', 'activity.screenshotSaved', { format: 'PNG' }), '已生成截图（PNG）。');
});

test('translates controlled data values and known Chinese object names', () => {
  assert.equal(translateDataValue('zh-CN', 'hovering'), '悬停');
  assert.equal(translateDataValue('en-US', 'hovering'), 'Hovering');
  assert.equal(translateDataValue('en-US', '无人机 2'), 'Drone 2');
  assert.equal(translateDataValue('en-US', '目标 3'), 'Target 3');
  assert.equal(translateDataValue('en-US', '障碍物 4'), 'Obstacle 4');
  assert.equal(translateDataValue('en-US', '不可飞越'), 'Not flyable');
  assert.equal(translateDataValue('en-US', '请先选择一架无人机。'), 'Select a drone first.');
  assert.equal(translateDataValue('en-US', '该无人机没有可漫游路径。'), 'The selected drone has no path to roam.');
  assert.equal(translateDataValue('en-US', '当前会话接口失败: HTTP 500'), 'Current session API failed: HTTP 500');
});
