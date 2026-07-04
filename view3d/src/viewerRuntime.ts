import type { Position, ViewerState } from './types';
import type { Locale } from './i18n.ts';
import { t } from './i18n.ts';

export type ShortcutAction =
  | 'clear_selection'
  | 'pan_up'
  | 'pan_down'
  | 'pan_left'
  | 'pan_right'
  | 'zoom_in'
  | 'zoom_out'
  | 'toggle_labels'
  | 'toggle_minimap'
  | 'toggle_info'
  | 'label_size_down'
  | 'label_size_up'
  | 'camera_top'
  | 'camera_follow'
  | 'camera_roam'
  | 'camera_fit'
  | 'roam_speed_up'
  | 'roam_speed_down'
  | 'reset_view';

export type ShortcutOptions = {
  editMode?: boolean;
  ctrlKey?: boolean;
  metaKey?: boolean;
  shiftKey?: boolean;
};

const trailModes = [10, 20, 1, 0, -1] as const;

export const DEFAULT_LABELS_VISIBLE = false;
export const DISPLAY_ONLY_MODE = true;

export function formatStatusSummary(state: ViewerState | null, locale: Locale = 'zh-CN'): string {
  if (!state) return '';

  const parts: string[] = [];
  const progress = state.task_progress || {};
  const taskType = progress.task_type;

  if (taskType && taskType !== 'others') {
    if (progress.is_completed) {
      parts.push(t(locale, 'summary.finished'));
    } else if (typeof progress.progress_percentage === 'number') {
      parts.push(t(locale, 'summary.task', { progress: Math.round(progress.progress_percentage) }));
    }
  }

  return parts.join(' · ');
}

export function formatClickPosition(position: Position | null, locale: Locale = 'zh-CN'): string {
  if (!position) return t(locale, 'click.empty');
  return t(locale, 'click.position', {
    x: position.x.toFixed(1),
    y: position.y.toFixed(1),
    z: position.z.toFixed(1)
  });
}

export function getTrailModeValue(index: number): number {
  const normalized = ((index % trailModes.length) + trailModes.length) % trailModes.length;
  return trailModes[normalized];
}

export function nextTrailMode(index: number): number {
  return (index + 1) % trailModes.length;
}

export function getTrailModeLabel(index: number, locale: Locale = 'zh-CN'): string {
  const value = getTrailModeValue(index);
  const prefix = t(locale, 'trail.prefix');
  if (value === -1) return `${prefix}: ${t(locale, 'trail.all')}`;
  if (value === 0) return `${prefix}: ${t(locale, 'trail.hidden')}`;
  if (value === 1) return `${prefix}: ${t(locale, 'trail.segment')}`;
  return `${prefix}: ${value}`;
}

export function getShortcutAction(key: string, options: ShortcutOptions = {}): ShortcutAction | null {
  void options;
  if (key === 'Escape') return 'clear_selection';
  if (key === 'ArrowUp') return 'pan_up';
  if (key === 'ArrowDown') return 'pan_down';
  if (key === 'ArrowLeft') return 'pan_left';
  if (key === 'ArrowRight') return 'pan_right';
  if (key === '+' || key === '=') return 'zoom_in';
  if (key === '-') return 'zoom_out';
  if (key === 'l' || key === 'L') return 'toggle_labels';
  if (key === 'm' || key === 'M') return 'toggle_minimap';
  if (key === 'i' || key === 'I') return 'toggle_info';
  if (key === '[') return 'label_size_down';
  if (key === ']') return 'label_size_up';
  if (key === 'r' || key === 'R') return 'reset_view';
  if (key === '1') return 'camera_fit';
  if (key === '2') return 'camera_top';
  if (key === '3') return 'camera_follow';
  if (key === '4') return 'camera_roam';
  if (key === '.') return 'roam_speed_up';
  if (key === ',') return 'roam_speed_down';
  return null;
}
