import assert from 'node:assert/strict';
import test from 'node:test';

import { fetchViewerState, getApiBaseUrl } from './api.ts';

type WindowLike = {
  __MULTIUAV_API_BASE_URL?: string;
  __MULTIUAV_VIEWER_DATA_SOURCE?: string;
  location?: {
    origin?: string;
    pathname?: string;
  };
};

const originalWindow = (globalThis as typeof globalThis & { window?: WindowLike }).window;
const originalFetch = globalThis.fetch;

function setWindow(value: WindowLike | undefined): void {
  if (value === undefined) {
    Reflect.deleteProperty(globalThis, 'window');
    return;
  }
  Object.defineProperty(globalThis, 'window', {
    value,
    configurable: true,
    writable: true
  });
}

test.afterEach(() => {
  setWindow(originalWindow);
  globalThis.fetch = originalFetch;
});

test('getApiBaseUrl prefers runtime Windows package API base URL', () => {
  setWindow({
    __MULTIUAV_API_BASE_URL: 'http://127.0.0.1:8123/'
  });

  assert.equal(getApiBaseUrl(), 'http://127.0.0.1:8123');
});

test('getApiBaseUrl can use production same-origin URL when no runtime override is present', () => {
  setWindow({
    location: {
      origin: 'http://127.0.0.1:9000',
      pathname: '/app/'
    }
  });

  assert.equal(getApiBaseUrl(), 'http://127.0.0.1:9000');
});

test('getApiBaseUrl keeps the existing development default without runtime configuration', () => {
  setWindow(undefined);

  assert.equal(getApiBaseUrl(), 'http://127.0.0.1:8000');
});

test('fetchViewerState adapts original current session endpoint instead of using viewer-specific backend API', async () => {
  setWindow(undefined);
  const requestedUrls: string[] = [];
  globalThis.fetch = (async (input: string | URL | Request) => {
    requestedUrls.push(String(input));
    return new Response(JSON.stringify({
      id: 'session-1',
      name: 'Session 1',
      status: 'active',
      task_type: 'others',
      canvas_width: 1024,
      canvas_height: 768,
      is_distance_3d: false,
      drones: [],
      targets: [],
      obstacles: [],
      environment: null,
      statistics: {},
      history: {}
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  }) as typeof fetch;

  const state = await fetchViewerState();

  assert.equal(state.session?.id, 'session-1');
  assert.deepEqual(requestedUrls, ['http://127.0.0.1:8000/sessions/current/data']);
});

test('fetchViewerState can run in explicit demo mode without requesting the drone backend', async () => {
  setWindow({ __MULTIUAV_VIEWER_DATA_SOURCE: 'demo' });
  let fetchCalled = false;
  globalThis.fetch = (async () => {
    fetchCalled = true;
    throw new Error('fetch should not be called in demo mode');
  }) as typeof fetch;

  const state = await fetchViewerState();

  assert.equal(fetchCalled, false);
  assert.equal(state.status, 'demo');
});

test('fetchViewerState keeps demo state stable across polling refreshes', async () => {
  setWindow({ __MULTIUAV_VIEWER_DATA_SOURCE: 'demo' });

  const first = await fetchViewerState();
  const second = await fetchViewerState();

  assert.equal(first, second);
});
