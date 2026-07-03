import { canUseAirCommand } from './commandRules.ts';
import type { DroneState } from './types.ts';

export type CommandAvailability = {
  takeoff: boolean;
  land: boolean;
  hover: boolean;
  returnHome: boolean;
  moveMode: boolean;
  charge: boolean;
  emergency: boolean;
  relativeMove: boolean;
  altitudeMove: boolean;
};

export function getCommandAvailability(drone: DroneState | null): CommandAvailability {
  if (!drone || !canUseAirCommand(drone)) {
    return {
      takeoff: false,
      land: false,
      hover: false,
      returnHome: false,
      moveMode: false,
      charge: false,
      emergency: false,
      relativeMove: false,
      altitudeMove: false
    };
  }

  const status = drone.status;
  const canTakeoff = ['idle', 'ready'].includes(status);
  const canUseInAirCommand = ['taking_off', 'flying', 'moving', 'hovering', 'landing'].includes(status);
  const canUseDirectionalMove = ['flying', 'moving', 'hovering'].includes(status);

  return {
    takeoff: canTakeoff,
    land: canUseInAirCommand,
    hover: canUseInAirCommand,
    returnHome: canUseInAirCommand,
    moveMode: canUseDirectionalMove,
    charge: status === 'idle',
    emergency: canUseInAirCommand,
    relativeMove: canUseDirectionalMove,
    altitudeMove: canUseDirectionalMove
  };
}

export function canDirectClickMove(drone: DroneState | null): boolean {
  return Boolean(drone && ['flying', 'moving', 'hovering'].includes(drone.status));
}
