import assert from 'node:assert/strict';
import test from 'node:test';

import { createDemoState } from './demoState.ts';

test('createDemoState includes renderable coverage surfaces for the search area', () => {
  const state = createDemoState('demo');
  const surfacePayload = state.area_coverage_surfaces?.['demo-area-1'];

  assert.ok(surfacePayload);
  assert.ok(surfacePayload.surfaces && surfacePayload.surfaces.length > 0);
  assert.ok((surfacePayload.progress_percentage ?? 0) > 0);
});
