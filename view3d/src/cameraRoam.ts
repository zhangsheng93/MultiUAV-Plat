import type { DroneState, Position } from './types.ts';

export type RoamSample = {
  position: Position;
  nextPosition: Position;
  forwardHint: Position;
  segmentIndex: number;
  done: boolean;
};

const POSITION_EPSILON = 0.001;
const TURN_BLEND_MIN_DISTANCE = 8;
const TURN_BLEND_MAX_DISTANCE = 24;

function distance(a: Position, b: Position): number {
  return Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
}

function subtract(a: Position, b: Position): Position {
  return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
}

function add(a: Position, b: Position): Position {
  return { x: a.x + b.x, y: a.y + b.y, z: a.z + b.z };
}

function scale(vector: Position, scalar: number): Position {
  return { x: vector.x * scalar, y: vector.y * scalar, z: vector.z * scalar };
}

function normalize(vector: Position): Position {
  const length = Math.hypot(vector.x, vector.y, vector.z);
  if (length <= POSITION_EPSILON) return { x: 0, y: 0, z: 0 };
  return { x: vector.x / length, y: vector.y / length, z: vector.z / length };
}

function dot(a: Position, b: Position): number {
  return a.x * b.x + a.y * b.y + a.z * b.z;
}

function isUsableDirection(vector: Position): boolean {
  return Math.hypot(vector.x, vector.y, vector.z) > POSITION_EPSILON;
}

function lerpDirection(from: Position, to: Position, t: number): Position {
  const start = normalize(from);
  const end = normalize(to);
  if (!isUsableDirection(start)) return end;
  if (!isUsableDirection(end)) return start;
  const clampedT = Math.max(0, Math.min(1, t));

  if (dot(start, end) < -0.98) {
    return clampedT < 0.5 ? start : end;
  }

  return normalize(add(scale(start, 1 - clampedT), scale(end, clampedT)));
}

function segmentDirection(path: Position[], segmentIndex: number): Position | null {
  if (segmentIndex < 0 || segmentIndex >= path.length - 1) return null;
  const direction = subtract(path[segmentIndex + 1], path[segmentIndex]);
  return isUsableDirection(direction) ? normalize(direction) : null;
}

function segmentLengthAt(path: Position[], segmentIndex: number): number {
  if (segmentIndex < 0 || segmentIndex >= path.length - 1) return 0;
  return distance(path[segmentIndex], path[segmentIndex + 1]);
}

function getTurnWindow(length: number, turnDistance: number): number {
  if (length <= POSITION_EPSILON) return 0;
  return Math.max(POSITION_EPSILON, Math.min(turnDistance, length / 2));
}

export function getRoamTurnDistance(speed: number): number {
  const preferred = speed * 0.8;
  return Math.max(TURN_BLEND_MIN_DISTANCE, Math.min(TURN_BLEND_MAX_DISTANCE, preferred));
}

export function getSmoothedRoamForward(
  path: Position[],
  segmentIndex: number,
  distanceIntoSegment: number,
  segmentLength: number,
  turnDistance: number
): Position {
  const currentDirection = segmentDirection(path, segmentIndex) || { x: 0, y: 1, z: 0 };
  const previousDirection = segmentDirection(path, segmentIndex - 1);
  const nextDirection = segmentDirection(path, segmentIndex + 1);
  const currentWindow = getTurnWindow(segmentLength, turnDistance);

  if (previousDirection && distanceIntoSegment < currentWindow) {
    const previousWindow = getTurnWindow(segmentLengthAt(path, segmentIndex - 1), turnDistance);
    const totalTurnWindow = previousWindow + currentWindow;
    const progress = totalTurnWindow > POSITION_EPSILON
      ? (previousWindow + distanceIntoSegment) / totalTurnWindow
      : 1;
    return lerpDirection(previousDirection, currentDirection, progress);
  }

  if (nextDirection && segmentLength - distanceIntoSegment < currentWindow) {
    const nextWindow = getTurnWindow(segmentLengthAt(path, segmentIndex + 1), turnDistance);
    const totalTurnWindow = currentWindow + nextWindow;
    const progress = totalTurnWindow > POSITION_EPSILON
      ? (distanceIntoSegment - (segmentLength - currentWindow)) / totalTurnWindow
      : 1;
    return lerpDirection(currentDirection, nextDirection, progress);
  }

  return currentDirection;
}

export function normalizeRoamPath(path: Position[], currentPosition: Position): Position[] {
  const normalized: Position[] = [];
  for (const point of [...path, currentPosition]) {
    const previous = normalized[normalized.length - 1];
    if (!previous || distance(previous, point) > POSITION_EPSILON) {
      normalized.push({ ...point });
    }
  }
  return normalized;
}

export function getRoamPathLength(path: Position[]): number {
  let total = 0;
  for (let index = 1; index < path.length; index += 1) {
    total += distance(path[index - 1], path[index]);
  }
  return total;
}

export function getRoamSpeed(drone: DroneState): number {
  const preferredSpeed = drone.speed && drone.speed > 0
    ? drone.speed
    : drone.max_speed && drone.max_speed > 0
      ? drone.max_speed
      : 20;
  return Math.max(5, Math.min(80, preferredSpeed));
}

export function sampleRoamPath(path: Position[], distanceAlongPath: number, turnDistance = TURN_BLEND_MIN_DISTANCE): RoamSample | null {
  if (path.length < 2) return null;

  const totalLength = getRoamPathLength(path);
  if (totalLength <= POSITION_EPSILON) return null;

  const clampedDistance = Math.max(0, Math.min(totalLength, distanceAlongPath));
  let traversed = 0;

  for (let index = 1; index < path.length; index += 1) {
    const start = path[index - 1];
    const end = path[index];
    const segmentLength = distance(start, end);
    if (segmentLength <= POSITION_EPSILON) continue;

    if (traversed + segmentLength >= clampedDistance || index === path.length - 1) {
      const t = Math.max(0, Math.min(1, (clampedDistance - traversed) / segmentLength));
      const distanceIntoSegment = Math.max(0, Math.min(segmentLength, clampedDistance - traversed));
      return {
        position: {
          x: start.x + (end.x - start.x) * t,
          y: start.y + (end.y - start.y) * t,
          z: start.z + (end.z - start.z) * t
        },
        nextPosition: { ...end },
        forwardHint: getSmoothedRoamForward(path, index - 1, distanceIntoSegment, segmentLength, turnDistance),
        segmentIndex: index - 1,
        done: clampedDistance >= totalLength - POSITION_EPSILON
      };
    }

    traversed += segmentLength;
  }

  return {
    position: { ...path[path.length - 1] },
    nextPosition: { ...path[path.length - 1] },
    forwardHint: segmentDirection(path, path.length - 2) || { x: 0, y: 1, z: 0 },
    segmentIndex: path.length - 2,
    done: true
  };
}
