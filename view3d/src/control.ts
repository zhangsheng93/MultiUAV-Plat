import {
  commandChangeAltitude,
  commandCharge,
  commandEmergency,
  commandHover,
  commandLand,
  commandMoveTo,
  commandMoveTowards,
  commandReturnHome,
  commandTakeoff,
  updateDronePerceivedRadius
} from './api';
import { canUseAirCommand } from './commandRules';
import { buildRelativeMovement, type RelativeMoveAction } from './movementControls';
import type { CommandResult, DroneState, Position } from './types';

export { canUseAirCommand };

export async function runDroneCommand(command: string, drone: DroneState | null, altitude: number): Promise<CommandResult> {
  if (!drone) {
    return { ok: false, message: '请先选择一架无人机。' };
  }

  if (command === 'charge') {
    if (drone.status !== 'idle') return { ok: false, message: '无人机需要降落并处于 idle 状态才能充电。' };
    return commandCharge(drone.id, 100);
  }

  if (command === 'emergency') {
    if (!['taking_off', 'flying', 'moving', 'hovering', 'landing'].includes(drone.status)) {
      return { ok: false, message: '当前状态不需要应急降落。' };
    }
    return commandEmergency(drone.id);
  }

  if (!canUseAirCommand(drone)) {
    return { ok: false, message: `当前状态 ${drone.status} 不允许普通控制。` };
  }

  if (command === 'takeoff') return commandTakeoff(drone.id, altitude);
  if (command === 'land') return commandLand(drone.id);
  if (command === 'hover') return commandHover(drone.id);
  if (command === 'return_home') return commandReturnHome(drone.id);
  return { ok: false, message: `未知命令: ${command}` };
}

export async function runRelativeMove(
  drone: DroneState | null,
  action: RelativeMoveAction,
  distanceStep: number,
  altitudeStep: number
): Promise<CommandResult> {
  if (!drone) {
    return { ok: false, message: '请先选择一架无人机。' };
  }
  if (!['flying', 'moving', 'hovering'].includes(drone.status)) {
    return { ok: false, message: `当前状态 ${drone.status} 不允许相对移动。` };
  }
  const movement = buildRelativeMovement(drone, action, distanceStep, altitudeStep);
  if (movement.kind === 'change_altitude') {
    return commandChangeAltitude(drone.id, movement.altitude);
  }
  return commandMoveTowards(drone.id, movement.distance, movement.heading);
}

export async function runMoveTo(drone: DroneState | null, groundPoint: Position, defaultAltitude: number): Promise<CommandResult> {
  if (!drone) {
    return { ok: false, message: '请先选择一架无人机。' };
  }
  if (!canUseAirCommand(drone)) {
    return { ok: false, message: `当前状态 ${drone.status} 不允许移动。` };
  }
  const altitude = drone.position.z > 0 ? drone.position.z : defaultAltitude;
  return commandMoveTo(drone.id, {
    x: Number(groundPoint.x.toFixed(2)),
    y: Number(groundPoint.y.toFixed(2)),
    z: Number(altitude.toFixed(2))
  });
}

export async function runUpdatePerceivedRadius(drone: DroneState | null, perceivedRadius: number): Promise<CommandResult> {
  if (!drone) {
    return { ok: false, message: '请先选择一架无人机。' };
  }
  if (!Number.isFinite(perceivedRadius) || perceivedRadius <= 0) {
    return { ok: false, message: '感知半径必须大于 0。' };
  }
  return updateDronePerceivedRadius(drone.id, Number(perceivedRadius.toFixed(2)));
}
