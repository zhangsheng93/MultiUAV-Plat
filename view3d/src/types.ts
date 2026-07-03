export type Position = {
  x: number;
  y: number;
  z: number;
};

export type ViewerSession = {
  id: string;
  name: string;
  description?: string;
  status?: string;
  creator?: string;
  task_type: string;
  task_description?: string;
  canvas_width: number;
  canvas_height: number;
  is_distance_3d: boolean;
  created_at?: number;
  last_updated?: number;
};

export type DroneState = {
  id: string;
  name: string;
  model?: string;
  status: string;
  position: Position;
  heading?: number;
  speed?: number;
  max_speed?: number;
  max_altitude?: number;
  battery_level?: number;
  battery_capacity?: number;
  coverage_width?: number;
  perceived_radius?: number;
  task_radius?: number;
  home_position?: Position;
};

export type TargetState = {
  id: string;
  name: string;
  type: string;
  position: Position;
  description?: string;
  radius?: number;
  charge_amount?: number;
  vertices?: Position[];
  velocity?: Position;
  moving_path?: Position[];
  moving_duration?: number;
  movement_mode?: string;
  tracking_status?: string;
  current_path_index?: number;
  path_direction?: number;
  is_reached?: boolean;
  area?: number;
};

export type ObstacleState = {
  id: string;
  name: string;
  type: string;
  position: Position;
  description?: string;
  radius?: number;
  width?: number;
  length?: number;
  vertices?: Position[];
  height?: number;
  area?: number;
};

export type ViewerState = {
  server_time: number;
  status: 'active' | 'no_current_session' | string;
  message?: string;
  session: ViewerSession | null;
  drones: DroneState[];
  targets: TargetState[];
  obstacles: ObstacleState[];
  paths: Record<string, Position[]>;
  task_progress: Record<string, unknown>;
  area_coverage?: Record<string, { covered_points?: Array<Position | [number, number] | [number, number, number]> }>;
  area_coverage_surfaces?: Record<string, {
    progress_percentage?: number;
    covered_area?: number;
    target_area?: number;
    surfaces?: Array<{
      outer?: Array<Position | { x: number; y: number } | [number, number]>;
      holes?: Array<Array<Position | { x: number; y: number } | [number, number]>>;
    }>;
  }>;
  history?: {
    area_coverage?: Record<string, { covered_points?: Array<Position | [number, number] | [number, number, number]> }>;
  };
  environment: Record<string, unknown> | null;
};

export type SessionData = ViewerSession & {
  status: string;
  creator?: string;
  created_at?: number;
  last_updated?: number;
  statistics?: Record<string, unknown>;
  drones: DroneState[];
  targets: TargetState[];
  obstacles: ObstacleState[];
  environment: Record<string, unknown> | null;
  tasks?: Array<Record<string, unknown>>;
  history?: Record<string, unknown>;
};

export type SelectableKind = 'drone' | 'target' | 'obstacle';

export type SelectionRef = {
  kind: SelectableKind;
  id: string;
};

export type CameraMode = 'free' | 'top' | 'follow' | 'fit';

export type CommandResult = {
  ok: boolean;
  message: string;
  data?: unknown;
};
