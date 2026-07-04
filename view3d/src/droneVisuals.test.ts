import assert from 'node:assert/strict';
import test from 'node:test';

import {
  DRONE_MODEL_LOWEST_LOCAL_Y,
  DRONE_SHADOW_BASE_RADIUS,
  DRONE_SHADOW_MIN_ALTITUDE,
  DRONE_VISUAL_GROUND_CLEARANCE,
  getDroneGroundShadowStyle
} from './droneVisuals.ts';

test('landed drone visual is lifted so the lowest model point rests on the ground', () => {
  assert.equal(DRONE_MODEL_LOWEST_LOCAL_Y + DRONE_VISUAL_GROUND_CLEARANCE, 0);
  assert.ok(DRONE_VISUAL_GROUND_CLEARANCE > 0);
});

test('ground shadow appears only for airborne drones and softens with altitude', () => {
  assert.deepEqual(getDroneGroundShadowStyle(DRONE_SHADOW_MIN_ALTITUDE), {
    visible: false,
    radius: 0,
    opacity: 0
  });

  const lowHover = getDroneGroundShadowStyle(10);
  const highHover = getDroneGroundShadowStyle(120);

  assert.ok(lowHover.radius >= DRONE_SHADOW_BASE_RADIUS);
  assert.equal(lowHover.visible, true);
  assert.equal(highHover.visible, true);
  assert.ok(highHover.radius > lowHover.radius);
  assert.ok(highHover.opacity < lowHover.opacity);
});
