import type { ViewerState } from './types';
import { buildAreaCoverageSurfaces } from './stateAdapter.ts';

export function createDemoState(message: string): ViewerState {
  const state: ViewerState = {
    server_time: Date.now() / 1000,
    status: 'demo',
    message,
    session: {
      id: 'demo-session',
      name: 'Demo Mission',
      description: 'Local fallback scene used when the backend is unavailable.',
      status: 'demo',
      creator: 'viewer',
      task_type: 'target_tracking',
      task_description: 'Demonstrate V2 3D scene rendering.',
      canvas_width: 640,
      canvas_height: 420,
      is_distance_3d: false
    },
    drones: [
      {
        id: 'demo-drone-1',
        name: 'Scout Alpha',
        model: 'D4',
        status: 'moving',
        position: { x: 180, y: 120, z: 55 },
        heading: 72,
        speed: 12,
        max_speed: 20,
        max_altitude: 120,
        battery_level: 82,
        perceived_radius: 100,
        task_radius: 20,
        home_position: { x: 40, y: 40, z: 0 }
      },
      {
        id: 'demo-drone-2',
        name: 'Relay Beta',
        model: 'R2',
        status: 'hovering',
        position: { x: 390, y: 250, z: 38 },
        heading: 220,
        speed: 0,
        max_speed: 18,
        max_altitude: 100,
        battery_level: 64,
        perceived_radius: 85,
        task_radius: 18,
        home_position: { x: 80, y: 340, z: 0 }
      }
    ],
    targets: [
      {
        id: 'demo-target-1',
        name: 'Moving Target',
        type: 'moving',
        position: { x: 480, y: 90, z: 0 },
        radius: 18,
        is_reached: false,
        movement_mode: 'path',
        velocity: { x: 2.2, y: 1.1, z: 0 },
        moving_path: [
          { x: 420, y: 70, z: 0 },
          { x: 480, y: 90, z: 0 },
          { x: 530, y: 145, z: 0 }
        ]
      },
      {
        id: 'demo-waypoint-1',
        name: 'Charging Waypoint',
        type: 'waypoint',
        position: { x: 88, y: 330, z: 0 },
        radius: 16,
        is_reached: true
      },
      {
        id: 'demo-area-1',
        name: 'Search Area',
        type: 'circle',
        position: { x: 315, y: 260, z: 0 },
        radius: 58,
        is_reached: false
      }
    ],
    obstacles: [
      {
        id: 'demo-obstacle-1',
        name: 'Building A',
        type: 'circle',
        position: { x: 275, y: 165, z: 0 },
        radius: 28,
        height: 70
      },
      {
        id: 'demo-obstacle-2',
        name: 'No Fly Zone',
        type: 'polygon',
        position: { x: 500, y: 310, z: 0 },
        height: 0,
        vertices: [
          { x: 455, y: 270, z: 0 },
          { x: 545, y: 275, z: 0 },
          { x: 565, y: 345, z: 0 },
          { x: 480, y: 370, z: 0 }
        ]
      }
    ],
    paths: {
      'demo-drone-1': [
        { x: 40, y: 40, z: 0 },
        { x: 76, y: 58, z: 25 },
        { x: 112, y: 78, z: 42 },
        { x: 148, y: 100, z: 52 },
        { x: 180, y: 120, z: 55 }
      ],
      'demo-drone-2': [
        { x: 80, y: 340, z: 0 },
        { x: 160, y: 330, z: 30 },
        { x: 245, y: 300, z: 38 },
        { x: 320, y: 272, z: 38 },
        { x: 390, y: 250, z: 38 }
      ]
    },
    task_progress: {
      task_type: 'area_coverage',
      progress_percentage: 42,
      is_completed: false
    },
    area_coverage: {
      'demo-area-1': {
        covered_points: [
          [282, 238], [292, 238], [302, 238], [312, 238], [322, 238],
          [282, 248], [292, 248], [302, 248], [312, 248], [322, 248], [332, 248],
          [292, 258], [302, 258], [312, 258], [322, 258], [332, 258], [342, 258],
          [302, 268], [312, 268], [322, 268], [332, 268], [342, 268],
          [312, 278], [322, 278], [332, 278]
        ]
      }
    },
    environment: {
      weather: 'clear',
      wind_speed: 1.2,
      wind_direction: 'north'
    }
  };
  refreshDemoCoverageSurfaces(state);
  return state;
}

export function refreshDemoCoverageSurfaces(state: ViewerState): void {
  state.area_coverage_surfaces = buildAreaCoverageSurfaces(state.targets, state.drones, state.paths);
}
