import type { DroneState } from './types';

export type RelativeMoveAction = 'forward' | 'backward' | 'left' | 'right' | 'up' | 'down';

export type RelativeMovement =
  | { kind: 'move_towards'; distance: number; heading: number }
  | { kind: 'change_altitude'; altitude: number };

export function normalizeHeading(value: number): number {
  return ((value % 360) + 360) % 360;
}

export function buildRelativeMovement(
  drone: DroneState,
  action: RelativeMoveAction,
  distanceStep: number,
  altitudeStep: number
): RelativeMovement {
  const heading = drone.heading || 0;
  const distance = Math.max(1, Number(distanceStep) || 1);
  const altitudeDelta = Math.max(1, Number(altitudeStep) || 1);

  if (action === 'up' || action === 'down') {
    const targetAltitude = action === 'up'
      ? drone.position.z + altitudeDelta
      : drone.position.z - altitudeDelta;
    const maxAltitude = drone.max_altitude ?? Number.POSITIVE_INFINITY;
    return {
      kind: 'change_altitude',
      altitude: Number(Math.max(0, Math.min(maxAltitude, targetAltitude)).toFixed(2))
    };
  }

  const offset = {
    forward: 0,
    backward: 180,
    left: -90,
    right: 90
  }[action];

  return {
    kind: 'move_towards',
    distance,
    heading: normalizeHeading(heading + offset)
  };
}
