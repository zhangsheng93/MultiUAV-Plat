import assert from 'node:assert/strict';
import test from 'node:test';

import {
  DEFAULT_VISUAL_SCALE_SETTINGS,
  getAdaptiveBillboardScale,
  getAdaptiveDroneScale,
  loadVisualScaleSettings,
  normalizeVisualScaleSettings,
  saveVisualScaleSettings
} from './renderSettings.ts';

test('adaptive drone scale grows with camera distance and stays clamped', () => {
  assert.equal(getAdaptiveDroneScale(50), 0.48);
  assert.equal(getAdaptiveDroneScale(700), 0.7);
  assert.equal(getAdaptiveDroneScale(5000), 1.25);
});

test('billboard scale follows camera distance and stays clamped', () => {
  assert.equal(getAdaptiveBillboardScale(60), 0.85);
  assert.equal(getAdaptiveBillboardScale(900), 1.38);
  assert.equal(getAdaptiveBillboardScale(4000), 3.2);
});

test('visual scale settings clamp every element class independently', () => {
  assert.deepEqual(normalizeVisualScaleSettings({
    drone: 0.1,
    target: 1.45,
    obstacle: 5,
    label: 5
  }), {
    drone: 0.5,
    target: 1.45,
    obstacle: 2,
    label: 3
  });
});

test('visual scale settings persist to browser storage', () => {
  const values = new Map<string, string>();
  const storage = {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => {
      values.set(key, value);
    }
  };

  assert.deepEqual(loadVisualScaleSettings(storage), DEFAULT_VISUAL_SCALE_SETTINGS);
  saveVisualScaleSettings(storage, { drone: 1.2, target: 1.3, obstacle: 0.7, label: 1.8 });
  assert.deepEqual(loadVisualScaleSettings(storage), { drone: 1.2, target: 1.3, obstacle: 0.7, label: 1 });
});
