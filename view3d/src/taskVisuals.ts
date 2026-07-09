import type { Position, TargetState, ViewerState } from './types';
import type { Locale } from './i18n.ts';
import { t } from './i18n.ts';

export type TargetVisualState = {
  color: number;
  label: string;
  emphasis: 'complete' | 'coverage' | 'motion' | 'normal';
};

export type CoverageSummary = {
  progressPercentage: number | null;
};

export type CoverageSurface = {
  outer: Position[];
  holes?: Position[][];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function asFiniteNumber(value: unknown): number | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null;
  return value;
}

function normalizePoint(value: unknown): Position | null {
  if (Array.isArray(value)) {
    const x = asFiniteNumber(value[0]);
    const y = asFiniteNumber(value[1]);
    if (x === null || y === null) return null;
    return { x, y, z: asFiniteNumber(value[2]) ?? 0 };
  }
  if (isRecord(value)) {
    const x = asFiniteNumber(value.x);
    const y = asFiniteNumber(value.y);
    if (x === null || y === null) return null;
    return { x, y, z: asFiniteNumber(value.z) ?? 0 };
  }
  return null;
}

function normalizeRing(value: unknown): Position[] {
  if (!Array.isArray(value)) return [];
  return value
    .map(normalizePoint)
    .filter((point): point is Position => Boolean(point));
}

export function normalizeCoverageSurfaces(state: ViewerState, targetId: string): CoverageSurface[] {
  const payload = state.area_coverage_surfaces?.[targetId];
  if (!payload || !Array.isArray(payload.surfaces)) return [];
  const surfaces: CoverageSurface[] = [];
  for (const surface of payload.surfaces) {
    const outer = normalizeRing(surface.outer);
    if (outer.length < 3) continue;
    const holes = Array.isArray(surface.holes)
      ? surface.holes.map(normalizeRing).filter((ring) => ring.length >= 3)
      : [];
    surfaces.push({ outer, holes });
  }
  return surfaces;
}

export function summarizeCoverage(state: ViewerState, targetId: string): CoverageSummary {
  const progress = state.task_progress || {};
  const surfacePayload = state.area_coverage_surfaces?.[targetId];
  return {
    progressPercentage: typeof surfacePayload?.progress_percentage === 'number'
      ? Math.round(surfacePayload.progress_percentage)
      : typeof progress.progress_percentage === 'number' ? Math.round(progress.progress_percentage) : null
  };
}

export function normalizeTargetMotionPath(target: TargetState): Position[] {
  const path = [...(target.moving_path || [])];
  if (target.velocity) {
    path.push({
      x: target.position.x + target.velocity.x * 10,
      y: target.position.y + target.velocity.y * 10,
      z: target.position.z + target.velocity.z * 10
    });
  }
  return path;
}

export function shouldRenderTargetMotionPath(target: TargetState, visible = false): boolean {
  return visible && normalizeTargetMotionPath(target).length >= 2;
}

export function getTargetVisualState(target: TargetState, state: ViewerState, locale: Locale = 'zh-CN'): TargetVisualState {
  const taskType = state.task_progress?.task_type || state.session?.task_type;
  const isAreaTask = taskType === 'area_coverage' || taskType === 'area_search';
  const isAreaTarget = target.type === 'circle' || target.type === 'polygon';
  const hasCoverageSurface = Boolean(state.area_coverage_surfaces?.[target.id]);
  if ((isAreaTask && isAreaTarget) || hasCoverageSurface) {
    const summary = summarizeCoverage(state, target.id);
    const suffix = summary.progressPercentage === null ? '' : ` ${summary.progressPercentage}%`;
    if (summary.progressPercentage !== null && summary.progressPercentage >= 100) {
      return { color: 0x22c55e, label: `${locale === 'zh-CN' ? '覆盖' : 'Coverage'}${suffix}`, emphasis: 'complete' };
    }
    return { color: 0xfacc15, label: `${locale === 'zh-CN' ? '覆盖' : 'Coverage'}${suffix}`, emphasis: 'coverage' };
  }

  if (target.is_reached) {
    return { color: 0x22c55e, label: locale === 'zh-CN' ? '已完成' : 'Completed', emphasis: 'complete' };
  }

  if (target.type === 'moving' || target.movement_mode || target.velocity || target.moving_path?.length) {
    return { color: 0xfacc15, label: locale === 'zh-CN' ? '动态目标' : 'Moving Target', emphasis: 'motion' };
  }

  return { color: 0xfacc15, label: t(locale, 'entity.target'), emphasis: 'normal' };
}
