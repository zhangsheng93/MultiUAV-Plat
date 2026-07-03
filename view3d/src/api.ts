import type { CommandResult, DroneState, Position, SessionData, ViewerState } from './types';
import { sessionDataToViewerState } from './stateAdapter.ts';
import { createDemoState } from './demoState.ts';
import { buildSessionSavePayload } from './editorState.ts';

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000';
let demoViewerState: ViewerState | null = null;

type ApiBaseUrlOptions = {
  preferSameOrigin?: boolean;
};

export type ApiRecord = Record<string, unknown>;

export type BackendScreenshotOptions = {
  format: string;
  showStatus?: boolean;
  width?: number;
  height?: number;
  centerX?: number;
  centerY?: number;
  scalePxPerMeter?: number;
};

export type BackendScreenshotDownload = {
  blob: Blob;
  contentType: string;
  fileName: string;
};

function getViteEnvValue(key: 'VITE_API_BASE_URL' | 'VITE_API_KEY' | 'VITE_VIEWER_DATA_SOURCE'): string | undefined {
  return (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env?.[key];
}

function getPackagedSameOriginUrl(): string | null {
  const location = globalThis.window?.location;
  if (!location?.origin || !location.pathname?.startsWith('/app')) return null;
  return location.origin.replace(/\/$/, '');
}

function getViewerDataSource(): string | undefined {
  return globalThis.window?.__MULTIUAV_VIEWER_DATA_SOURCE || getViteEnvValue('VITE_VIEWER_DATA_SOURCE');
}

export function getApiBaseUrl(options: ApiBaseUrlOptions = {}): string {
  const runtimeUrl = globalThis.window?.__MULTIUAV_API_BASE_URL;
  if (runtimeUrl) return runtimeUrl.replace(/\/$/, '');

  const envUrl = getViteEnvValue('VITE_API_BASE_URL');
  if (envUrl) return envUrl.replace(/\/$/, '');

  const packagedSameOriginUrl = getPackagedSameOriginUrl();
  if (packagedSameOriginUrl) return packagedSameOriginUrl;

  if (options.preferSameOrigin && globalThis.window?.location?.origin) return globalThis.window.location.origin.replace(/\/$/, '');

  return DEFAULT_API_BASE_URL;
}

function getApiHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json'
  };
  const apiKey = getViteEnvValue('VITE_API_KEY');
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }
  return headers;
}

async function apiJson<T>(endpoint: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${endpoint}`, {
    ...init,
    headers: {
      ...getApiHeaders(),
      ...init.headers
    }
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.detail || data?.message || `接口请求失败: HTTP ${response.status}`);
  }
  return data as T;
}

function buildQuery(params: Record<string, unknown>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue;
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item !== undefined && item !== null && item !== '') query.append(key, String(item));
      }
    } else if (typeof value === 'object') {
      query.set(key, JSON.stringify(value));
    } else {
      query.set(key, String(value));
    }
  }
  return query.toString();
}

function normalizeArrayResponse(data: unknown, key: string): ApiRecord[] {
  if (Array.isArray(data)) return data as ApiRecord[];
  if (data && typeof data === 'object' && Array.isArray((data as ApiRecord)[key])) {
    return (data as ApiRecord)[key] as ApiRecord[];
  }
  return [];
}

export async function fetchViewerState(): Promise<ViewerState> {
  if (getViewerDataSource() === 'demo') {
    demoViewerState ??= createDemoState('Local demo data source is active.');
    return demoViewerState;
  }

  const response = await fetch(`${getApiBaseUrl()}/sessions/current/data`, {
    headers: getApiHeaders()
  });
  if (!response.ok) {
    throw new Error(`当前会话接口失败: HTTP ${response.status}`);
  }
  return sessionDataToViewerState((await response.json()) as SessionData);
}

export async function fetchSessionData(sessionId: string): Promise<SessionData> {
  const response = await fetch(`${getApiBaseUrl()}/sessions/${encodeURIComponent(sessionId)}/data`, {
    headers: getApiHeaders()
  });
  if (!response.ok) {
    throw new Error(`会话数据接口失败: HTTP ${response.status}`);
  }
  return (await response.json()) as SessionData;
}

export async function saveSessionWithId(sessionId: string, payload: SessionData): Promise<SessionData> {
  const response = await fetch(`${getApiBaseUrl()}/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'POST',
    headers: getApiHeaders(),
    body: JSON.stringify(payload)
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.detail || data?.message || `保存会话失败: HTTP ${response.status}`);
  }
  return data as SessionData;
}

export async function createSession(payload: Partial<SessionData> & { name: string }): Promise<SessionData> {
  const response = await fetch(`${getApiBaseUrl()}/sessions`, {
    method: 'POST',
    headers: getApiHeaders(),
    body: JSON.stringify(payload)
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.detail || data?.message || `创建会话失败: HTTP ${response.status}`);
  }
  return data as SessionData;
}

export async function setCurrentSession(sessionId: string): Promise<SessionData> {
  const response = await fetch(`${getApiBaseUrl()}/sessions/${encodeURIComponent(sessionId)}/set-current`, {
    method: 'POST',
    headers: getApiHeaders()
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.detail || data?.message || `切换会话失败: HTTP ${response.status}`);
  }
  return data as SessionData;
}

export async function listSessions(): Promise<ApiRecord[]> {
  return normalizeArrayResponse(await apiJson<unknown>('/sessions'), 'sessions');
}

export async function resetCurrentSession(): Promise<ApiRecord> {
  return apiJson<ApiRecord>('/sessions/current/reset', {
    method: 'POST'
  });
}

export async function deleteSession(sessionId: string): Promise<ApiRecord | null> {
  return apiJson<ApiRecord | null>(`/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE'
  });
}

export async function fetchCurrentTasks(): Promise<ApiRecord[]> {
  return normalizeArrayResponse(await apiJson<unknown>('/sessions/current/tasks'), 'tasks');
}

export async function fetchNextTask(): Promise<ApiRecord> {
  return apiJson<ApiRecord>('/sessions/current/tasks/next');
}

export async function fetchCurrentTask(taskId: string): Promise<ApiRecord> {
  return apiJson<ApiRecord>(`/sessions/current/tasks/${encodeURIComponent(taskId)}`);
}

export async function runCurrentTaskCheck(taskId: string, sinceTimestamp?: number): Promise<ApiRecord> {
  const query = buildQuery({ since_timestamp: sinceTimestamp });
  return apiJson<ApiRecord>(`/sessions/current/tasks/${encodeURIComponent(taskId)}/check${query ? `?${query}` : ''}`);
}

export async function markCurrentTaskDone(taskId: string): Promise<ApiRecord> {
  return apiJson<ApiRecord>(`/sessions/current/tasks/${encodeURIComponent(taskId)}/mark-done`, {
    method: 'POST'
  });
}

export async function markCurrentTaskPending(taskId: string): Promise<ApiRecord> {
  return apiJson<ApiRecord>(`/sessions/current/tasks/${encodeURIComponent(taskId)}/mark-pending`, {
    method: 'POST'
  });
}

export async function runCheck(endpoint: string, params: Record<string, unknown> = {}): Promise<ApiRecord> {
  const cleanEndpoint = endpoint.replace(/^\/+/, '').replace(/^check\/?/, '');
  const query = buildQuery(params);
  return apiJson<ApiRecord>(`/check/${encodeURIComponent(cleanEndpoint)}${query ? `?${query}` : ''}`);
}

export function getBackendScreenshotUrl(options: BackendScreenshotOptions): string {
  const query = buildQuery({
    format: options.format,
    width: options.width,
    height: options.height,
    center_x: options.centerX,
    center_y: options.centerY,
    scale_px_per_meter: options.scalePxPerMeter,
    show_status: options.showStatus ?? true
  });
  return `${getApiBaseUrl()}/sessions/current/screenshot?${query}`;
}

export async function downloadBackendScreenshot(options: BackendScreenshotOptions): Promise<BackendScreenshotDownload> {
  const response = await fetch(getBackendScreenshotUrl(options), {
    headers: getApiHeaders()
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail || data?.message || `后端截图失败: HTTP ${response.status}`);
  }
  const format = options.format || 'png';
  return {
    blob: await response.blob(),
    contentType: response.headers.get('Content-Type') || 'application/octet-stream',
    fileName: `multiuav-backend-${Date.now()}.${format}`
  };
}

async function postCommand(endpoint: string, body?: unknown): Promise<CommandResult> {
  try {
    const response = await fetch(`${getApiBaseUrl()}${endpoint}`, {
      method: 'POST',
      headers: getApiHeaders(),
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      return {
        ok: false,
        message: data?.detail || data?.message || `命令失败: HTTP ${response.status}`,
        data
      };
    }
    return {
      ok: true,
      message: data?.message || '命令已发送',
      data
    };
  } catch (error) {
    return {
      ok: false,
      message: error instanceof Error ? error.message : '命令请求失败'
    };
  }
}

async function patchCurrentSessionDrone(droneId: string, patch: Partial<DroneState>): Promise<CommandResult> {
  try {
    const sessionData = await apiJson<SessionData>('/sessions/current/data');
    const draft = sessionDataToViewerState(sessionData);
    const drone = draft.drones.find((item) => item.id === droneId);
    if (!drone) {
      return { ok: false, message: '请先选择一架无人机。' };
    }
    Object.assign(drone, patch);
    await saveSessionWithId(sessionData.id, buildSessionSavePayload(sessionData, draft));
    return {
      ok: true,
      message: '无人机已更新',
      data: drone
    };
  } catch (error) {
    return {
      ok: false,
      message: error instanceof Error ? error.message : '无人机更新请求失败'
    };
  }
}

export async function updateDronePerceivedRadius(droneId: string, perceivedRadius: number): Promise<CommandResult> {
  return patchCurrentSessionDrone(droneId, { perceived_radius: perceivedRadius });
}

export function commandGeneric(droneId: string, command: string, parameters: ApiRecord = {}): Promise<CommandResult> {
  return postCommand(`/drones/${encodeURIComponent(droneId)}/command`, {
    command,
    parameters
  });
}

export function commandTakeoff(droneId: string, altitude: number): Promise<CommandResult> {
  return postCommand(`/drones/${encodeURIComponent(droneId)}/command/take_off?altitude=${altitude}`);
}

export function commandLand(droneId: string): Promise<CommandResult> {
  return postCommand(`/drones/${encodeURIComponent(droneId)}/command/land`);
}

export function commandHover(droneId: string): Promise<CommandResult> {
  return postCommand(`/drones/${encodeURIComponent(droneId)}/command/hover`);
}

export function commandReturnHome(droneId: string): Promise<CommandResult> {
  return postCommand(`/drones/${encodeURIComponent(droneId)}/command/return_home`);
}

export function commandCharge(droneId: string, chargeAmount = 100): Promise<CommandResult> {
  return postCommand(`/drones/${encodeURIComponent(droneId)}/command/charge?charge_amount=${chargeAmount}`);
}

export function commandEmergency(droneId: string): Promise<CommandResult> {
  return postCommand(`/drones/${encodeURIComponent(droneId)}/command`, {
    command: 'emergency',
    parameters: {}
  });
}

export function commandMoveTo(droneId: string, position: Position): Promise<CommandResult> {
  const params = new URLSearchParams({
    x: String(position.x),
    y: String(position.y),
    z: String(position.z)
  });
  return postCommand(`/drones/${encodeURIComponent(droneId)}/command/move_to?${params.toString()}`);
}

export function commandMoveTowards(droneId: string, distance: number, heading: number): Promise<CommandResult> {
  const params = new URLSearchParams({
    distance: String(distance),
    heading: String(heading)
  });
  return postCommand(`/drones/${encodeURIComponent(droneId)}/command/move_towards?${params.toString()}`);
}

export function commandChangeAltitude(droneId: string, altitude: number): Promise<CommandResult> {
  return postCommand(`/drones/${encodeURIComponent(droneId)}/command/change_altitude?altitude=${altitude}`);
}
