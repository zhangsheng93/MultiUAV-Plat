import type { DroneState } from './types.ts';

export function canUseAirCommand(drone: DroneState | null): boolean {
  if (!drone) return false;
  return !['emergency', 'offline'].includes(drone.status);
}

