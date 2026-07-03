import assert from 'node:assert/strict';
import test from 'node:test';

import {
  commandGeneric,
  deleteSession,
  downloadBackendScreenshot,
  fetchCurrentTask,
  fetchCurrentTasks,
  fetchNextTask,
  fetchViewerState,
  getApiBaseUrl,
  getBackendScreenshotUrl,
  listSessions,
  markCurrentTaskDone,
  markCurrentTaskPending,
  resetCurrentSession,
  runCheck,
  runCurrentTaskCheck,
  updateDronePerceivedRadius
} from './api.ts';

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

test('session helpers call original session management endpoints', async () => {
  setWindow(undefined);
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    calls.push({ url: String(input), init });
    return new Response(JSON.stringify({ sessions: [{ id: 's-1', name: 'Alpha' }] }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  }) as typeof fetch;

  const sessions = await listSessions();
  await resetCurrentSession();
  await deleteSession('s-1');

  assert.deepEqual(sessions, [{ id: 's-1', name: 'Alpha' }]);
  assert.equal(calls[0].url, 'http://127.0.0.1:8000/sessions');
  assert.equal(calls[1].url, 'http://127.0.0.1:8000/sessions/current/reset');
  assert.equal(calls[1].init?.method, 'POST');
  assert.equal(calls[2].url, 'http://127.0.0.1:8000/sessions/s-1');
  assert.equal(calls[2].init?.method, 'DELETE');
});

test('task helpers call current-session task endpoints', async () => {
  setWindow(undefined);
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    calls.push({ url: String(input), init });
    return new Response(JSON.stringify({ id: 'task-1', tasks: [{ id: 'task-1', name: 'Search' }] }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  }) as typeof fetch;

  const tasks = await fetchCurrentTasks();
  await fetchNextTask();
  await fetchCurrentTask('task-1');
  await runCurrentTaskCheck('task-1', 123.4);
  await markCurrentTaskDone('task-1');
  await markCurrentTaskPending('task-1');

  assert.deepEqual(tasks, [{ id: 'task-1', name: 'Search' }]);
  assert.equal(calls[0].url, 'http://127.0.0.1:8000/sessions/current/tasks');
  assert.equal(calls[1].url, 'http://127.0.0.1:8000/sessions/current/tasks/next');
  assert.equal(calls[2].url, 'http://127.0.0.1:8000/sessions/current/tasks/task-1');
  assert.equal(calls[3].url, 'http://127.0.0.1:8000/sessions/current/tasks/task-1/check?since_timestamp=123.4');
  assert.equal(calls[4].url, 'http://127.0.0.1:8000/sessions/current/tasks/task-1/mark-done');
  assert.equal(calls[4].init?.method, 'POST');
  assert.equal(calls[5].url, 'http://127.0.0.1:8000/sessions/current/tasks/task-1/mark-pending');
  assert.equal(calls[5].init?.method, 'POST');
});

test('check and advanced command helpers preserve query parameters and command body', async () => {
  setWindow(undefined);
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    calls.push({ url: String(input), init });
    return new Response(JSON.stringify({ result: true, message: 'ok' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  }) as typeof fetch;

  await runCheck('target_is_fully_searched', { target_id: 'target 1', threshold: 0.99 });
  const command = await commandGeneric('drone-1', 'send_message', { to_drone_id: 'drone-2', message: 'hold' });

  assert.equal(calls[0].url, 'http://127.0.0.1:8000/check/target_is_fully_searched?target_id=target+1&threshold=0.99');
  assert.equal(calls[1].url, 'http://127.0.0.1:8000/drones/drone-1/command');
  assert.equal(calls[1].init?.method, 'POST');
  assert.equal(calls[1].init?.body, JSON.stringify({
    command: 'send_message',
    parameters: { to_drone_id: 'drone-2', message: 'hold' }
  }));
  assert.equal(command.ok, true);
});

test('updateDronePerceivedRadius saves the selected drone through the current session endpoint', async () => {
  setWindow(undefined);
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    const url = String(input);
    calls.push({ url: String(input), init });
    if (url.endsWith('/sessions/current/data')) {
      return new Response(JSON.stringify({
        id: 'session-1',
        name: 'Session 1',
        status: 'active',
        task_type: 'others',
        canvas_width: 1024,
        canvas_height: 768,
        is_distance_3d: false,
        drones: [{ id: 'drone-1', name: 'Drone 1', status: 'idle', position: { x: 0, y: 0, z: 0 }, perceived_radius: 100 }],
        targets: [],
        obstacles: [],
        environment: null
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    return new Response(JSON.stringify({ id: 'drone-1', perceived_radius: 125 }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  }) as typeof fetch;

  const result = await updateDronePerceivedRadius('drone-1', 125);
  const saved = JSON.parse(String(calls[1].init?.body));

  assert.equal(result.ok, true);
  assert.equal(calls[0].url, 'http://127.0.0.1:8000/sessions/current/data');
  assert.equal(calls[1].url, 'http://127.0.0.1:8000/sessions/session-1');
  assert.equal(calls[1].init?.method, 'POST');
  assert.equal(saved.drones[0].perceived_radius, 125);
});

test('backend screenshot helpers expose current-session screenshot endpoint', async () => {
  setWindow(undefined);
  const urls: string[] = [];
  globalThis.fetch = (async (input: string | URL | Request) => {
    urls.push(String(input));
    return new Response('image-bytes', {
      status: 200,
      headers: { 'Content-Type': 'image/png' }
    });
  }) as typeof fetch;

  assert.equal(
    getBackendScreenshotUrl({ format: 'pdf', showStatus: false, width: 1600, height: 900 }),
    'http://127.0.0.1:8000/sessions/current/screenshot?format=pdf&width=1600&height=900&show_status=false'
  );

  const result = await downloadBackendScreenshot({ format: 'png', showStatus: true });

  assert.equal(urls[0], 'http://127.0.0.1:8000/sessions/current/screenshot?format=png&show_status=true');
  assert.equal(result.contentType, 'image/png');
});
