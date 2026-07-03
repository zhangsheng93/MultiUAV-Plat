import * as THREE from 'three';
import type { Position } from './types.ts';

export function worldToScenePosition(position: Position): THREE.Vector3 {
  return new THREE.Vector3(position.x, position.z, -position.y);
}

export function sceneGroundToWorld(point: THREE.Vector3): Position {
  return { x: point.x, y: -point.z, z: 0 };
}

export function worldYToSceneZ(y: number): number {
  return -y;
}

export function getSceneAxisEnd(axis: 'x' | 'y' | 'z', length: number): THREE.Vector3 {
  if (axis === 'x') return new THREE.Vector3(length, 0, 0);
  if (axis === 'y') return new THREE.Vector3(0, 0, -length);
  return new THREE.Vector3(0, length, 0);
}
