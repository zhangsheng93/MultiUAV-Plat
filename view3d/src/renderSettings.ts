function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function roundToTwo(value: number): number {
  return Math.round(value * 100) / 100;
}

export type VisualScaleSettings = {
  drone: number;
  target: number;
  obstacle: number;
  label: number;
};

export const DEFAULT_VISUAL_SCALE_SETTINGS: VisualScaleSettings = {
  drone: 1,
  target: 1,
  obstacle: 1,
  label: 1
};

const VISUAL_SCALE_MIN = 0.5;
const VISUAL_SCALE_MAX = 3;
const OBJECT_VISUAL_SCALE_MAX = 2;
const VISUAL_SCALE_STORAGE_KEY = 'multiuav.visualScaleSettings';

type StorageLike = Pick<Storage, 'getItem' | 'setItem'>;

export function getAdaptiveDroneScale(cameraDistance: number): number {
  return roundToTwo(clamp(cameraDistance / 1000, 0.48, 1.25));
}

export function getAdaptiveBillboardScale(cameraDistance: number): number {
  return roundToTwo(clamp(cameraDistance / 650, 0.85, 3.2));
}

function normalizeScale(value: unknown, max = VISUAL_SCALE_MAX): number {
  const numberValue = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(numberValue)) return 1;
  return roundToTwo(clamp(numberValue, VISUAL_SCALE_MIN, max));
}

export function normalizeVisualScaleSettings(value: Partial<VisualScaleSettings> | null | undefined): VisualScaleSettings {
  return {
    drone: normalizeScale(value?.drone ?? DEFAULT_VISUAL_SCALE_SETTINGS.drone, OBJECT_VISUAL_SCALE_MAX),
    target: normalizeScale(value?.target ?? DEFAULT_VISUAL_SCALE_SETTINGS.target, OBJECT_VISUAL_SCALE_MAX),
    obstacle: normalizeScale(value?.obstacle ?? DEFAULT_VISUAL_SCALE_SETTINGS.obstacle, OBJECT_VISUAL_SCALE_MAX),
    label: normalizeScale(value?.label ?? DEFAULT_VISUAL_SCALE_SETTINGS.label)
  };
}

export function loadVisualScaleSettings(storage: StorageLike): VisualScaleSettings {
  const raw = storage.getItem(VISUAL_SCALE_STORAGE_KEY);
  if (!raw) return { ...DEFAULT_VISUAL_SCALE_SETTINGS };
  try {
    return {
      ...normalizeVisualScaleSettings(JSON.parse(raw) as Partial<VisualScaleSettings>),
      label: DEFAULT_VISUAL_SCALE_SETTINGS.label
    };
  } catch {
    return { ...DEFAULT_VISUAL_SCALE_SETTINGS };
  }
}

export function saveVisualScaleSettings(storage: StorageLike, settings: VisualScaleSettings): void {
  storage.setItem(VISUAL_SCALE_STORAGE_KEY, JSON.stringify(normalizeVisualScaleSettings(settings)));
}
