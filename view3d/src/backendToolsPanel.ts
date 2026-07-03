import {
  commandGeneric,
  deleteSession,
  downloadBackendScreenshot,
  fetchCurrentTask,
  fetchCurrentTasks,
  fetchNextTask,
  fetchSessionData,
  listSessions,
  markCurrentTaskDone,
  markCurrentTaskPending,
  resetCurrentSession,
  runCheck,
  runCurrentTaskCheck,
  setCurrentSession,
  type ApiRecord
} from './api.ts';
import type { CommandResult, DroneState, ViewerState } from './types';
import type { CoverageDisplayMode } from './scene.ts';
import type { Locale } from './i18n.ts';
import { translateDataValue } from './i18n.ts';

type BackendToolsPanelOptions = {
  getLocale: () => Locale;
  getState: () => ViewerState | null;
  getSelectedDrone: () => DroneState | null;
  refreshState: () => Promise<void>;
  clearSelection: () => void;
  setCoverageDisplayMode: (mode: CoverageDisplayMode) => void;
  report: (result: CommandResult) => void;
};

type BackendToolsPanel = {
  sync: (state: ViewerState | null) => void;
};

type ToolRefs = {
  coverageDisplayMode: HTMLSelectElement;
  sessionSelect: HTMLSelectElement;
  sessionRefresh: HTMLButtonElement;
  sessionSwitch: HTMLButtonElement;
  sessionReset: HTMLButtonElement;
  sessionExport: HTMLButtonElement;
  sessionDelete: HTMLButtonElement;
  sessionStatus: HTMLPreElement;
  backendScreenshotButton: HTMLButtonElement;
  backendScreenshotFormat: HTMLSelectElement;
  backendScreenshotSize: HTMLInputElement;
  backendScreenshotShowStatus: HTMLInputElement;
  taskSelect: HTMLSelectElement;
  taskRefresh: HTMLButtonElement;
  taskNext: HTMLButtonElement;
  taskInspect: HTMLButtonElement;
  taskCheck: HTMLButtonElement;
  taskDone: HTMLButtonElement;
  taskPending: HTMLButtonElement;
  taskSinceTimestamp: HTMLInputElement;
  taskStatus: HTMLPreElement;
  checkEndpoint: HTMLSelectElement;
  checkParams: HTMLTextAreaElement;
  checkRun: HTMLButtonElement;
  commandDroneId: HTMLInputElement;
  commandName: HTMLSelectElement;
  commandParams: HTMLTextAreaElement;
  commandRun: HTMLButtonElement;
  commandStatus: HTMLPreElement;
};

function requireElement<T extends HTMLElement>(selector: string): T {
  const element = document.querySelector<T>(selector);
  if (!element) throw new Error(`Missing ${selector} element`);
  return element;
}

function getRefs(): ToolRefs {
  return {
    coverageDisplayMode: requireElement<HTMLSelectElement>('#coverageDisplayMode'),
    sessionSelect: requireElement<HTMLSelectElement>('#sessionToolSelect'),
    sessionRefresh: requireElement<HTMLButtonElement>('#sessionToolRefresh'),
    sessionSwitch: requireElement<HTMLButtonElement>('#sessionToolSwitch'),
    sessionReset: requireElement<HTMLButtonElement>('#sessionToolReset'),
    sessionExport: requireElement<HTMLButtonElement>('#sessionToolExport'),
    sessionDelete: requireElement<HTMLButtonElement>('#sessionToolDelete'),
    sessionStatus: requireElement<HTMLPreElement>('#sessionToolStatus'),
    backendScreenshotButton: requireElement<HTMLButtonElement>('#backendScreenshotButton'),
    backendScreenshotFormat: requireElement<HTMLSelectElement>('#backendScreenshotFormat'),
    backendScreenshotSize: requireElement<HTMLInputElement>('#backendScreenshotSize'),
    backendScreenshotShowStatus: requireElement<HTMLInputElement>('#backendScreenshotShowStatus'),
    taskSelect: requireElement<HTMLSelectElement>('#taskToolSelect'),
    taskRefresh: requireElement<HTMLButtonElement>('#taskToolRefresh'),
    taskNext: requireElement<HTMLButtonElement>('#taskToolNext'),
    taskInspect: requireElement<HTMLButtonElement>('#taskToolInspect'),
    taskCheck: requireElement<HTMLButtonElement>('#taskToolCheck'),
    taskDone: requireElement<HTMLButtonElement>('#taskToolDone'),
    taskPending: requireElement<HTMLButtonElement>('#taskToolPending'),
    taskSinceTimestamp: requireElement<HTMLInputElement>('#taskSinceTimestamp'),
    taskStatus: requireElement<HTMLPreElement>('#taskToolStatus'),
    checkEndpoint: requireElement<HTMLSelectElement>('#checkToolEndpoint'),
    checkParams: requireElement<HTMLTextAreaElement>('#checkToolParams'),
    checkRun: requireElement<HTMLButtonElement>('#checkToolRun'),
    commandDroneId: requireElement<HTMLInputElement>('#advancedCommandDroneId'),
    commandName: requireElement<HTMLSelectElement>('#advancedCommandName'),
    commandParams: requireElement<HTMLTextAreaElement>('#advancedCommandParams'),
    commandRun: requireElement<HTMLButtonElement>('#advancedCommandRun'),
    commandStatus: requireElement<HTMLPreElement>('#advancedCommandStatus')
  };
}

function setOutput(element: HTMLPreElement, value: unknown, ok = true): void {
  element.textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  element.className = `tool-output ${ok ? 'ok' : 'error'}`;
}

function getId(item: ApiRecord): string {
  return String(item.id ?? item.session_id ?? item.task_id ?? '');
}

function getName(item: ApiRecord, locale: Locale): string {
  return String(item.name ?? item.title ?? item.description ?? getId(item) ?? '未命名');
}

function populateSelect(select: HTMLSelectElement, items: ApiRecord[], emptyText: string, selectedId?: string, locale: Locale = 'zh-CN'): void {
  select.innerHTML = '';
  if (items.length === 0) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = translateDataValue(locale, emptyText);
    select.append(option);
    return;
  }
  for (const item of items) {
    const option = document.createElement('option');
    option.value = getId(item);
    option.textContent = `${translateDataValue(locale, getName(item, locale))} (${getId(item)})`;
    select.append(option);
  }
  if (selectedId) select.value = selectedId;
}

function parseJsonObject(text: string, fallback: ApiRecord = {}): ApiRecord {
  const trimmed = text.trim();
  if (!trimmed) return fallback;
  const value = JSON.parse(trimmed) as unknown;
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('参数必须是 JSON 对象。');
  }
  return value as ApiRecord;
}

function parseSinceTimestamp(value: string): number | undefined {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const numberValue = Number(trimmed);
  if (!Number.isFinite(numberValue)) throw new Error('since_timestamp 必须是数字。');
  return numberValue;
}

function parseScreenshotSize(value: string): { width?: number; height?: number } {
  const match = value.trim().match(/^(\d+)\s*x\s*(\d+)$/i);
  if (!match) return {};
  return {
    width: Number(match[1]),
    height: Number(match[2])
  };
}

function saveBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = fileName;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function saveJson(data: unknown, fileName: string): void {
  saveBlob(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }), fileName);
}

async function runTool(element: HTMLPreElement, task: () => Promise<unknown>, options: BackendToolsPanelOptions): Promise<void> {
  try {
    setOutput(element, translateDataValue(options.getLocale(), '请求中...'), true);
    const result = await task();
    setOutput(element, typeof result === 'string' ? translateDataValue(options.getLocale(), result) : result, true);
  } catch (error) {
    const message = error instanceof Error ? error.message : '请求失败';
    const translated = translateDataValue(options.getLocale(), message);
    setOutput(element, translated, false);
    options.report({ ok: false, message: translated });
  }
}

export function bindBackendToolsPanel(options: BackendToolsPanelOptions): BackendToolsPanel {
  const refs = getRefs();

  refs.coverageDisplayMode.addEventListener('change', () => {
    options.setCoverageDisplayMode(refs.coverageDisplayMode.value as CoverageDisplayMode);
    void options.refreshState();
  });

  refs.sessionRefresh.addEventListener('click', () => {
    void runTool(refs.sessionStatus, async () => {
      const sessions = await listSessions();
      populateSelect(refs.sessionSelect, sessions, '无会话', options.getState()?.session?.id, options.getLocale());
      return sessions;
    }, options);
  });

  refs.sessionSwitch.addEventListener('click', () => {
    void runTool(refs.sessionStatus, async () => {
      if (!refs.sessionSelect.value) throw new Error('请选择会话。');
      const result = await setCurrentSession(refs.sessionSelect.value);
      options.clearSelection();
      await options.refreshState();
      return result;
    }, options);
  });

  refs.sessionReset.addEventListener('click', () => {
    void runTool(refs.sessionStatus, async () => {
      const confirmMessage = options.getLocale() === 'zh-CN'
        ? '确认重置当前会话历史、统计和覆盖记录？'
        : 'Reset history, statistics, and coverage records for the current session?';
      if (!window.confirm(confirmMessage)) return translateDataValue(options.getLocale(), '已取消。');
      const result = await resetCurrentSession();
      await options.refreshState();
      return result;
    }, options);
  });

  refs.sessionExport.addEventListener('click', () => {
    void runTool(refs.sessionStatus, async () => {
      const sessionId = options.getState()?.session?.id;
      if (!sessionId) throw new Error('当前没有可导出的会话。');
      const data = await fetchSessionData(sessionId);
      saveJson(data, `multiuav-session-${sessionId}.json`);
      return { exported: sessionId, entities: { drones: data.drones.length, targets: data.targets.length, obstacles: data.obstacles.length } };
    }, options);
  });

  refs.sessionDelete.addEventListener('click', () => {
    void runTool(refs.sessionStatus, async () => {
      if (!refs.sessionSelect.value) throw new Error('请选择会话。');
      const beforeDeleteSessions = await listSessions();
      if (beforeDeleteSessions.length <= 1) {
        throw new Error('不能删除唯一的会话，请先创建或切换到其他会话。');
      }
      const confirmMessage = options.getLocale() === 'zh-CN'
        ? `确认删除会话 ${refs.sessionSelect.value}？`
        : `Delete session ${refs.sessionSelect.value}?`;
      if (!window.confirm(confirmMessage)) return translateDataValue(options.getLocale(), '已取消。');
      const deletedCurrent = refs.sessionSelect.value === options.getState()?.session?.id;
      const result = await deleteSession(refs.sessionSelect.value);
      const sessions = await listSessions();
      populateSelect(refs.sessionSelect, sessions, '无会话', options.getState()?.session?.id, options.getLocale());
      if (deletedCurrent && sessions.length > 0) {
        await setCurrentSession(getId(sessions[0]));
      }
      await options.refreshState();
      return result ?? { deleted: true };
    }, options);
  });

  refs.backendScreenshotButton.addEventListener('click', () => {
    void runTool(refs.sessionStatus, async () => {
      const size = parseScreenshotSize(refs.backendScreenshotSize.value);
      const result = await downloadBackendScreenshot({
        format: refs.backendScreenshotFormat.value,
        showStatus: refs.backendScreenshotShowStatus.checked,
        ...size
      });
      saveBlob(result.blob, result.fileName);
      return { downloaded: result.fileName, contentType: result.contentType };
    }, options);
  });

  refs.taskRefresh.addEventListener('click', () => {
    void runTool(refs.taskStatus, async () => {
      const tasks = await fetchCurrentTasks();
      populateSelect(refs.taskSelect, tasks, '无任务', undefined, options.getLocale());
      return tasks;
    }, options);
  });

  refs.taskNext.addEventListener('click', () => {
    void runTool(refs.taskStatus, async () => {
      const task = await fetchNextTask();
      const taskId = getId(task);
      if (taskId) refs.taskSelect.value = taskId;
      return task;
    }, options);
  });

  refs.taskInspect.addEventListener('click', () => {
    void runTool(refs.taskStatus, async () => {
      if (!refs.taskSelect.value) throw new Error('请选择任务。');
      return fetchCurrentTask(refs.taskSelect.value);
    }, options);
  });

  refs.taskCheck.addEventListener('click', () => {
    void runTool(refs.taskStatus, async () => {
      if (!refs.taskSelect.value) throw new Error('请选择任务。');
      const result = await runCurrentTaskCheck(refs.taskSelect.value, parseSinceTimestamp(refs.taskSinceTimestamp.value));
      await options.refreshState();
      return result;
    }, options);
  });

  refs.taskDone.addEventListener('click', () => {
    void runTool(refs.taskStatus, async () => {
      if (!refs.taskSelect.value) throw new Error('请选择任务。');
      const result = await markCurrentTaskDone(refs.taskSelect.value);
      await options.refreshState();
      return result;
    }, options);
  });

  refs.taskPending.addEventListener('click', () => {
    void runTool(refs.taskStatus, async () => {
      if (!refs.taskSelect.value) throw new Error('请选择任务。');
      const result = await markCurrentTaskPending(refs.taskSelect.value);
      await options.refreshState();
      return result;
    }, options);
  });

  refs.checkRun.addEventListener('click', () => {
    void runTool(refs.taskStatus, async () => {
      const result = await runCheck(refs.checkEndpoint.value, parseJsonObject(refs.checkParams.value));
      await options.refreshState();
      return result;
    }, options);
  });

  refs.commandRun.addEventListener('click', () => {
    void runTool(refs.commandStatus, async () => {
      const droneId = refs.commandDroneId.value.trim();
      if (!droneId) throw new Error('请填写无人机 ID，或先选中无人机。');
      const result = await commandGeneric(droneId, refs.commandName.value, parseJsonObject(refs.commandParams.value));
      options.report(result);
      await options.refreshState();
      return result;
    }, options);
  });

  return {
    sync(state: ViewerState | null): void {
      if (state?.session && refs.sessionSelect.options.length <= 1) {
        populateSelect(refs.sessionSelect, [state.session as unknown as ApiRecord], '无会话', state.session.id, options.getLocale());
      } else if (state?.session?.id) {
        refs.sessionSelect.value = state.session.id;
      } else if (refs.sessionSelect.options.length === 0 || refs.sessionSelect.options[0]?.value === '') {
        populateSelect(refs.sessionSelect, [], '无会话', undefined, options.getLocale());
      }

      const selectedDrone = options.getSelectedDrone();
      if (selectedDrone) refs.commandDroneId.value = selectedDrone.id;

      const history = state?.history ? Object.keys(state.history).join(', ') : '';
      if (history && !refs.taskStatus.classList.contains('ok') && !refs.taskStatus.classList.contains('error')) {
        refs.taskStatus.textContent = translateDataValue(options.getLocale(), `当前历史字段: ${history}`);
      }
    }
  };
}
