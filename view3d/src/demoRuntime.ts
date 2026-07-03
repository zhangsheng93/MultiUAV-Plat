import { buildRelativeMovement, type RelativeMoveAction } from './movementControls.ts';
import { refreshDemoCoverageSurfaces } from './demoState.ts';
import type { CommandResult, DroneState, Position, ViewerState } from './types.ts';

export function isDemoState(state: ViewerState | null): boolean {
  return state?.status === 'demo';
}

export function moveDemoDroneTo(state: ViewerState, droneId: string | null, position: Position): CommandResult {
  const drone = getDemoDrone(state, droneId);
  if (!drone) return missingDroneResult(droneId);

  applyDemoDronePosition(state, drone, position, 'moving');
  return { ok: true, message: 'Demo 模式：无人机已移动。' };
}

export function runDemoDroneCommand(
  state: ViewerState,
  droneId: string | null,
  command: string,
  altitude: number
): CommandResult {
  const drone = getDemoDrone(state, droneId);
  if (!drone) return missingDroneResult(droneId);

  if (command === 'takeoff') {
    applyDemoDronePosition(state, drone, {
      ...drone.position,
      z: Math.max(1, altitude || 10)
    }, 'flying');
    return { ok: true, message: 'Demo 模式：无人机已起飞。' };
  }

  if (command === 'land') {
    applyDemoDronePosition(state, drone, { ...drone.position, z: 0 }, 'idle');
    return { ok: true, message: 'Demo 模式：无人机已降落。' };
  }

  if (command === 'hover') {
    drone.status = 'hovering';
    state.server_time = Date.now() / 1000;
    return { ok: true, message: 'Demo 模式：无人机悬停。' };
  }

  if (command === 'return_home') {
    const home = drone.home_position || { x: 0, y: 0, z: 0 };
    applyDemoDronePosition(state, drone, {
      x: home.x,
      y: home.y,
      z: Math.max(drone.position.z, altitude || 10)
    }, 'moving');
    return { ok: true, message: 'Demo 模式：无人机返航。' };
  }

  if (command === 'charge') {
    drone.battery_level = 100;
    drone.status = drone.position.z > 0 ? 'hovering' : 'idle';
    state.server_time = Date.now() / 1000;
    return { ok: true, message: 'Demo 模式：电量已充满。' };
  }

  if (command === 'emergency') {
    applyDemoDronePosition(state, drone, { ...drone.position, z: 0 }, 'emergency');
    return { ok: true, message: 'Demo 模式：已执行应急降落。' };
  }

  return { ok: false, message: `未知命令: ${command}` };
}

export function runDemoRelativeMove(
  state: ViewerState,
  droneId: string | null,
  action: RelativeMoveAction,
  distanceStep: number,
  altitudeStep: number
): CommandResult {
  const drone = getDemoDrone(state, droneId);
  if (!drone) return missingDroneResult(droneId);

  const movement = buildRelativeMovement(drone, action, distanceStep, altitudeStep);
  if (movement.kind === 'change_altitude') {
    applyDemoDronePosition(state, drone, { ...drone.position, z: movement.altitude }, movement.altitude > 0 ? 'hovering' : 'idle');
    return { ok: true, message: 'Demo 模式：高度已更新。' };
  }

  const radians = (movement.heading * Math.PI) / 180;
  applyDemoDronePosition(state, drone, {
    x: Number((drone.position.x + Math.sin(radians) * movement.distance).toFixed(2)),
    y: Number((drone.position.y + Math.cos(radians) * movement.distance).toFixed(2)),
    z: drone.position.z
  }, 'moving');
  return { ok: true, message: 'Demo 模式：无人机已移动。' };
}

function getDemoDrone(state: ViewerState, droneId: string | null): DroneState | null {
  if (!droneId) return null;
  return state.drones.find((item) => item.id === droneId) || null;
}

function missingDroneResult(droneId: string | null): CommandResult {
  return { ok: false, message: droneId ? '未找到选中的无人机。' : '请先选择一架无人机。' };
}

function applyDemoDronePosition(state: ViewerState, drone: DroneState, position: Position, status: string): void {
  const previousPosition = { ...drone.position };
  drone.position = { ...position };
  drone.status = status;
  state.paths[drone.id] = [...(state.paths[drone.id] || [previousPosition]), { ...position }];
  refreshDemoCoverageSurfaces(state);
  state.server_time = Date.now() / 1000;
}
