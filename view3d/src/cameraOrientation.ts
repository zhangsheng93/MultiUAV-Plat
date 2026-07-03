import * as THREE from 'three';

export function getTopViewCameraUp(): THREE.Vector3 {
  return new THREE.Vector3(0, 0, -1);
}

export function getWorldViewCameraUp(): THREE.Vector3 {
  return new THREE.Vector3(0, 1, 0);
}
