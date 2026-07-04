export const DRONE_MODEL_LOWEST_LOCAL_Y = -2.41;
export const DRONE_VISUAL_GROUND_CLEARANCE = -DRONE_MODEL_LOWEST_LOCAL_Y;
export const DRONE_SHADOW_MIN_ALTITUDE = 0.8;
export const DRONE_SHADOW_BASE_RADIUS = 17;

export type DroneGroundShadowStyle = {
  visible: boolean;
  radius: number;
  opacity: number;
};

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function getDroneGroundShadowStyle(altitude: number): DroneGroundShadowStyle {
  if (altitude <= DRONE_SHADOW_MIN_ALTITUDE) {
    return { visible: false, radius: 0, opacity: 0 };
  }

  return {
    visible: true,
    radius: clamp(12 + altitude * 0.08, DRONE_SHADOW_BASE_RADIUS, 30),
    opacity: clamp(0.32 - altitude * 0.0014, 0.12, 0.3)
  };
}
