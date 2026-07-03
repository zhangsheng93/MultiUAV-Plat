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
  assert.equal(t('en-US', 'session.summary', { drones: 2, targets: 1, obstacles: 3 }), '2 drones · 1 targets · 3 obstacles');
  assert.equal(t('en-US', 'task.title'), 'Tasks & Checks');
  assert.equal(t('en-US', 'task.runCheck'), 'Run Check');
  assert.equal(t('en-US', 'backend.coverageDisplay'), 'Coverage Display');
  assert.equal(t('en-US', 'advanced.droneId'), 'Drone ID');
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
  assert.equal(translateDataValue('en-US', '请选择任务。'), 'Select a task.');
  assert.equal(translateDataValue('en-US', '请求中...'), 'Requesting...');
  assert.equal(translateDataValue('en-US', '当前状态 hovering 不允许移动。'), 'Current status Hovering does not allow movement.');
  assert.equal(translateDataValue('en-US', '命令失败: HTTP 500'), 'Command failed: HTTP 500');
  assert.equal(translateDataValue('en-US', '当前历史字段: drones, targets'), 'Current history fields: drones, targets');
});
