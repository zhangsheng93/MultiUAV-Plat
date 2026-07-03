import assert from 'node:assert/strict';
import test from 'node:test';
import {
  DEFAULT_LABELS_VISIBLE,
  DISPLAY_ONLY_MODE,
  formatClickPosition,
  formatStatusSummary,
  getShortcutAction,
  getTrailModeLabel,
  getTrailModeValue,
  nextTrailMode
} from './viewerRuntime.ts';
import type { ViewerState } from './types.ts';

function makeState(overrides: Partial<ViewerState> = {}): ViewerState {
  return {
    server_time: 100,
    status: 'active',
    session: {
      id: 'session-1',
      name: 'Demo',
      task_type: 'target_tracking',
      canvas_width: 1024,
      canvas_height: 768,
      is_distance_3d: false
    },
    drones: [
      { id: 'd1', name: 'D1', status: 'idle', position: { x: 0, y: 0, z: 0 } },
      { id: 'd2', name: 'D2', status: 'hovering', position: { x: 1, y: 2, z: 3 } }
    ],
    targets: [
      { id: 't1', name: 'T1', type: 'fixed', position: { x: 10, y: 20, z: 0 } }
    ],
    obstacles: [
      { id: 'o1', name: 'O1', type: 'circle', position: { x: 30, y: 40, z: 0 }, radius: 5 },
      { id: 'o2', name: 'O2', type: 'polygon', position: { x: 50, y: 60, z: 0 } }
    ],
    paths: {},
    task_progress: {
      task_type: 'target_tracking',
      progress_percentage: 67,
      is_completed: false
    },
    environment: null,
    ...overrides
  };
}

test('scene labels are hidden by default to keep the 3D view uncluttered', () => {
  assert.equal(DEFAULT_LABELS_VISIBLE, false);
  assert.equal(DISPLAY_ONLY_MODE, true);
});

test('status summary mirrors 2D counts and task progress', () => {
  assert.equal(
    formatStatusSummary(makeState()),
    '无人机/目标/障碍物: 2/1/2 · 任务: 67%'
  );
  assert.equal(
    formatStatusSummary(makeState(), 'en-US'),
    'Drones/Targets/Obstacles: 2/1/2 · Task: 67%'
  );
});

test('status summary reports finished task and omits others progress', () => {
  assert.equal(
    formatStatusSummary(makeState({
      task_progress: { task_type: 'target_tracking', progress_percentage: 100, is_completed: true }
    })),
    '无人机/目标/障碍物: 2/1/2 · 任务已完成'
  );

  assert.equal(
    formatStatusSummary(makeState({
      task_progress: { task_type: 'others', progress_percentage: 0, is_completed: false }
    })),
    '无人机/目标/障碍物: 2/1/2'
  );
});

test('click position is formatted for status bar display', () => {
  assert.equal(formatClickPosition(null), '点击: (-, -, -)');
  assert.equal(formatClickPosition(null, 'en-US'), 'Click: (-, -, -)');
  assert.equal(formatClickPosition({ x: 12.345, y: 67.891, z: 4.2 }), '点击: (12.3, 67.9, 4.2)');
  assert.equal(formatClickPosition({ x: 12.345, y: 67.891, z: 4.2 }, 'en-US'), 'Click: (12.3, 67.9, 4.2)');
});

test('trail modes cycle like the 2D scene', () => {
  assert.equal(getTrailModeValue(0), 10);
  assert.equal(getTrailModeValue(1), 20);
  assert.equal(getTrailModeValue(2), 1);
  assert.equal(getTrailModeValue(3), 0);
  assert.equal(getTrailModeValue(4), -1);
  assert.equal(nextTrailMode(4), 0);
  assert.equal(getTrailModeLabel(0), '轨迹: 10');
  assert.equal(getTrailModeLabel(2), '轨迹: 1段');
  assert.equal(getTrailModeLabel(3), '轨迹: 隐藏');
  assert.equal(getTrailModeLabel(4), '轨迹: 全部');
  assert.equal(getTrailModeLabel(0, 'en-US'), 'Trail: 10');
  assert.equal(getTrailModeLabel(2, 'en-US'), 'Trail: 1 segment');
  assert.equal(getTrailModeLabel(3, 'en-US'), 'Trail: Hidden');
  assert.equal(getTrailModeLabel(4, 'en-US'), 'Trail: All');
});

test('keyboard shortcuts cover first phase 2D parity actions', () => {
  assert.equal(getShortcutAction('Escape'), 'clear_selection');
  assert.equal(getShortcutAction('ArrowUp'), 'pan_up');
  assert.equal(getShortcutAction('ArrowDown'), 'pan_down');
  assert.equal(getShortcutAction('ArrowLeft'), 'pan_left');
  assert.equal(getShortcutAction('ArrowRight'), 'pan_right');
  assert.equal(getShortcutAction('+'), 'zoom_in');
  assert.equal(getShortcutAction('='), 'zoom_in');
  assert.equal(getShortcutAction('-'), 'zoom_out');
  assert.equal(getShortcutAction('l'), 'toggle_labels');
  assert.equal(getShortcutAction('L'), 'toggle_labels');
  assert.equal(getShortcutAction('m'), 'toggle_minimap');
  assert.equal(getShortcutAction('M'), 'toggle_minimap');
  assert.equal(getShortcutAction('i'), 'toggle_info');
  assert.equal(getShortcutAction('I'), 'toggle_info');
  assert.equal(getShortcutAction('['), 'label_size_down');
  assert.equal(getShortcutAction(']'), 'label_size_up');
  assert.equal(getShortcutAction('r'), 'reset_view');
  assert.equal(getShortcutAction('R'), 'reset_view');
  assert.equal(getShortcutAction('1'), 'camera_fit');
  assert.equal(getShortcutAction('2'), 'camera_top');
  assert.equal(getShortcutAction('3'), 'camera_follow');
  assert.equal(getShortcutAction('4'), null);
  assert.equal(getShortcutAction('x'), null);
});

test('display-only mode disables editor operation shortcuts', () => {
  assert.equal(getShortcutAction('Delete', { editMode: true }), null);
  assert.equal(getShortcutAction('e', { editMode: true }), null);
  assert.equal(getShortcutAction('d', { editMode: true }), null);
  assert.equal(getShortcutAction('g', { editMode: true }), null);
  assert.equal(getShortcutAction('Tab', { editMode: true }), null);
  assert.equal(getShortcutAction('s', { editMode: true, ctrlKey: true }), null);
  assert.equal(getShortcutAction('S', { editMode: true, ctrlKey: true, shiftKey: true }), null);
  assert.equal(getShortcutAction('m', { editMode: true }), 'toggle_minimap');
});
