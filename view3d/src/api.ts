import type { SessionData, ViewerState } from './types';
import { sessionDataToViewerState } from './stateAdapter.ts';
import { createDemoState } from './demoState.ts';

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000';
let demoViewerState: ViewerState | null = null;

type ApiBaseUrlOptions = {
  preferSameOrigin?: boolean;
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
