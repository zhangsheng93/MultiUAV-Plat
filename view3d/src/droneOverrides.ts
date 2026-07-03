import type { ViewerState } from './types.ts';

export type DroneOverrides = {
  perceivedRadius?: Record<string, number>;
};

const STORAGE_KEY = 'multiuav.viewer.droneOverrides';

export function loadDroneOverrides(storage: Storage | null = globalThis.window?.localStorage || null): DroneOverrides {
  if (!storage) return {};
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as DroneOverrides;
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

export function saveDroneOverrides(overrides: DroneOverrides, storage: Storage | null = globalThis.window?.localStorage || null): void {
  if (!storage) return;
  storage.setItem(STORAGE_KEY, JSON.stringify(overrides));
}

export function setPerceivedRadiusOverride(overrides: DroneOverrides, droneId: string, radius: number): void {
  if (!Number.isFinite(radius) || radius <= 0) return;
  overrides.perceivedRadius ??= {};
  overrides.perceivedRadius[droneId] = Number(radius.toFixed(2));
}

export function applyDroneOverrides(state: ViewerState, overrides: DroneOverrides): void {
  const perceivedRadius = overrides.perceivedRadius || {};
  for (const drone of state.drones) {
    const radius = perceivedRadius[drone.id];
    if (Number.isFinite(radius) && radius > 0) {
      drone.perceived_radius = radius;
    }
  }
}
