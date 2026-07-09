export type Locale = 'zh-CN' | 'en-US';

type MessageKey = string;

type CoreMessageKey =
  | 'app.title'
  | 'language.toggle'
  | 'camera.free'
  | 'camera.top'
  | 'camera.follow'
  | 'camera.roam'
  | 'camera.fit'
  | 'topbar.cheatSheet'
  | 'topbar.info'
  | 'cheat.title'
  | 'cheat.clear'
  | 'cheat.pan'
  | 'cheat.cameraTop'
  | 'cheat.cameraFollow'
  | 'cheat.cameraRoam'
  | 'cheat.cameraFit'
  | 'cheat.roamSpeed'
  | 'cheat.zoom'
  | 'cheat.reset'
  | 'cheat.labels'
  | 'cheat.minimap'
  | 'cheat.info'
  | 'cheat.close'
  | 'status.connected'
  | 'status.disconnected'
  | 'status.noSession'
  | 'status.warningNoSession'
  | 'status.backendDisconnected'
  | 'session.summary'
  | 'summary.task'
  | 'summary.finished'
  | 'click.position'
  | 'click.empty'
  | 'trail.prefix'
  | 'trail.hidden'
  | 'trail.all'
  | 'trail.segment'
  | 'selection.none.title'
  | 'selection.none.detail'
  | 'entity.drone'
  | 'entity.target'
  | 'entity.obstacle'
  | 'field.id'
  | 'field.status'
  | 'field.position'
  | 'field.heading'
  | 'field.speed'
  | 'field.battery'
  | 'field.model'
  | 'field.maxSpeed'
  | 'field.maxAltitude'
  | 'field.batteryCapacity'
  | 'field.perceivedRadius'
  | 'field.taskRadius'
  | 'field.home'
  | 'field.type'
  | 'field.radius'
  | 'field.completed'
  | 'field.description'
  | 'field.movementMode'
  | 'field.trackingStatus'
  | 'field.pathPoints'
  | 'field.velocity'
  | 'field.taskStatus'
  | 'field.coverageProgress'
  | 'field.charge'
  | 'field.height'
  | 'field.size'
  | 'field.vertices'
  | 'field.area'
  | 'field.name'
  | 'field.width'
  | 'field.length'
  | 'screenshot.capture'
  | 'screenshot.format'
  | 'nav.label'
  | 'nav.panUp'
  | 'nav.panDown'
  | 'nav.panLeft'
  | 'nav.panRight'
  | 'nav.reset'
  | 'nav.zoomScale'
  | 'footer.live'
  | 'footer.paused'
  | 'footer.labelsOn'
  | 'footer.labelsOff'
  | 'footer.labelsTitle'
  | 'footer.trailLength'
  | 'footer.droneScale'
  | 'footer.targetScale'
  | 'footer.obstacleScale'
  | 'footer.labelScale'
  | 'footer.labelSizeValue'
  | 'footer.labelSizeDown'
  | 'footer.labelSizeUp'
  | 'footer.labelSizeDownTitle'
  | 'footer.labelSizeUpTitle'
  | 'footer.labelSizeResetTitle'
  | 'footer.zoomScale'
  | 'activity.selection'
  | 'activity.cameraChanged'
  | 'activity.cameraChangedWithRoamSpeed'
  | 'activity.selectionCleared'
  | 'activity.labelsShown'
  | 'activity.labelsHidden'
  | 'activity.minimapShown'
  | 'activity.minimapHidden'
  | 'activity.screenshotSaved'
  | 'activity.screenshotFailed'
  | 'value.yes'
  | 'value.no'
  | 'value.notFlyable';

const messages: Record<Locale, Record<MessageKey | CoreMessageKey, string>> = {
  'zh-CN': {
    'app.title': 'MultiUAV-Plat 3D 可视化',
    'language.toggle': 'English',
    'camera.free': '自由视角',
    'camera.top': '俯视',
    'camera.follow': '跟随',
    'camera.roam': '漫游',
    'camera.fit': '全局',
    'topbar.cheatSheet': '快捷键',
    'topbar.info': '信息',
    'cheat.title': '快捷键',
    'cheat.clear': '取消选择',
    'cheat.pan': '平移视角',
    'cheat.cameraTop': '俯视',
    'cheat.cameraFollow': '跟随',
    'cheat.cameraRoam': '漫游路径',
    'cheat.cameraFit': '全局',
    'cheat.roamSpeed': '漫游加速 / 减速',
    'cheat.zoom': '放大 / 缩小',
    'cheat.reset': '重置视角',
    'cheat.labels': '显示 / 隐藏标签',
    'cheat.minimap': '显示 / 隐藏小地图',
    'cheat.info': '显示 / 隐藏信息面板',
    'cheat.close': '关闭快捷键',
    'status.connected': '已连接服务器',
    'status.disconnected': '未连接',
    'status.noSession': '无会话',
    'status.warningNoSession': '无 current session',
    'status.backendDisconnected': '后端未连接，正在显示演示场景。',
    'session.summary': '{drones} 架无人机 · {targets} 个目标 · {obstacles} 个障碍物',
    'summary.task': '任务: {progress}%',
    'summary.finished': '任务已完成',
    'click.position': '点击: ({x}, {y}, {z})',
    'click.empty': '点击: (-, -, -)',
    'trail.prefix': '轨迹',
    'trail.hidden': '隐藏',
    'trail.all': '全部',
    'trail.segment': '1段',
    'selection.none.title': '未选中对象',
    'selection.none.detail': '点击无人机、目标或障碍物查看详情。',
    'entity.drone': '无人机',
    'entity.target': '目标',
    'entity.obstacle': '障碍物',
    'field.id': 'ID',
    'field.status': '状态',
    'field.position': '位置',
    'field.heading': '航向',
    'field.speed': '速度',
    'field.battery': '剩余电量',
    'field.model': '型号',
    'field.maxSpeed': '最大速度',
    'field.maxAltitude': '最大高度',
    'field.batteryCapacity': '电池容量',
    'field.perceivedRadius': '感知半径',
    'field.taskRadius': '任务半径',
    'field.home': '返航点',
    'field.type': '类型',
    'field.radius': '半径',
    'field.completed': '完成',
    'field.description': '描述',
    'field.movementMode': '移动模式',
    'field.trackingStatus': '跟踪状态',
    'field.pathPoints': '路径点数',
    'field.velocity': '速度向量',
    'field.taskStatus': '任务状态',
    'field.coverageProgress': '覆盖进度',
    'field.charge': '充电量',
    'field.height': '高度',
    'field.size': '尺寸',
    'field.vertices': '顶点数',
    'field.area': '投影面积',
    'field.name': '名称',
    'field.width': '宽度',
    'field.length': '长度',
    'screenshot.capture': '截图',
    'screenshot.format': '截图格式',
    'nav.label': '视图导航',
    'nav.panUp': '上移视图',
    'nav.panDown': '下移视图',
    'nav.panLeft': '左移视图',
    'nav.panRight': '右移视图',
    'nav.reset': '重置视图',
    'nav.zoomScale': '快速缩放比例尺',
    'footer.live': '实时',
    'footer.paused': '暂停',
    'footer.labelsOn': '隐藏标签',
    'footer.labelsOff': '显示标签',
    'footer.labelsTitle': '显示或隐藏无人机、目标、障碍物信息牌',
    'footer.trailLength': '轨迹长度',
    'footer.droneScale': '无人机',
    'footer.targetScale': '目标',
    'footer.obstacleScale': '障碍物',
    'footer.labelScale': '标签',
    'footer.labelSizeValue': '标签 {value}%',
    'footer.labelSizeDown': '缩小',
    'footer.labelSizeUp': '放大',
    'footer.labelSizeDownTitle': '缩小标签（[）',
    'footer.labelSizeUpTitle': '放大标签（]）',
    'footer.labelSizeResetTitle': '双击重置标签大小为 100%',
    'footer.zoomScale': '比例尺：{value}%',
    'activity.selection': '已选择 {kind} {name}（ID: {id}），查看详细信息；右键取消选择。',
    'activity.cameraChanged': '已切换到 {mode}视角。',
    'activity.cameraChangedWithRoamSpeed': '已切换到 {mode}视角 · 漫游速度: {speed}%',
    'activity.selectionCleared': '已取消选择。',
    'activity.labelsShown': '已显示标签。',
    'activity.labelsHidden': '已隐藏标签。',
    'activity.minimapShown': '已显示小地图。',
    'activity.minimapHidden': '已隐藏小地图。',
    'activity.screenshotSaved': '已生成截图（{format}）。',
    'activity.screenshotFailed': '截图生成失败。',
    'value.yes': '是',
    'value.no': '否',
    'value.notFlyable': '不可飞越'
  },
  'en-US': {
    'app.title': 'MultiUAV-Plat 3D Viewer',
    'language.toggle': '中文',
    'camera.free': 'Free',
    'camera.top': 'Top',
    'camera.follow': 'Follow',
    'camera.roam': 'Roam',
    'camera.fit': 'Fit',
    'topbar.cheatSheet': 'CheatSheet',
    'topbar.info': 'Info',
    'cheat.title': 'Keyboard Shortcuts',
    'cheat.clear': 'Clear selection',
    'cheat.pan': 'Pan view',
    'cheat.cameraTop': 'Top view',
    'cheat.cameraFollow': 'Follow view',
    'cheat.cameraRoam': 'Roam path',
    'cheat.cameraFit': 'Fit all',
    'cheat.roamSpeed': 'Roam speed up / down',
    'cheat.zoom': 'Zoom in / out',
    'cheat.reset': 'Reset view',
    'cheat.labels': 'Show / hide labels',
    'cheat.minimap': 'Show / hide minimap',
    'cheat.info': 'Show / hide info panel',
    'cheat.close': 'Close shortcuts',
    'status.connected': 'Server Connected',
    'status.disconnected': 'Disconnected',
    'status.noSession': 'No Session',
    'status.warningNoSession': 'No current session',
    'status.backendDisconnected': 'Backend disconnected. Showing demo scene.',
    'session.summary': '{drones} drones · {targets} targets · {obstacles} obstacles',
    'summary.task': 'Task: {progress}%',
    'summary.finished': 'Task Finished',
    'click.position': 'Click: ({x}, {y}, {z})',
    'click.empty': 'Click: (-, -, -)',
    'trail.prefix': 'Trail',
    'trail.hidden': 'Hidden',
    'trail.all': 'All',
    'trail.segment': '1 segment',
    'selection.none.title': 'No Selection',
    'selection.none.detail': 'Click a drone, target, or obstacle to view details.',
    'entity.drone': 'Drone',
    'entity.target': 'Target',
    'entity.obstacle': 'Obstacle',
    'field.id': 'ID',
    'field.status': 'Status',
    'field.position': 'Position',
    'field.heading': 'Heading',
    'field.speed': 'Speed',
    'field.battery': 'Battery',
    'field.model': 'Model',
    'field.maxSpeed': 'Max Speed',
    'field.maxAltitude': 'Max Altitude',
    'field.batteryCapacity': 'Battery Capacity',
    'field.perceivedRadius': 'Perception Radius',
    'field.taskRadius': 'Task Radius',
    'field.home': 'Home',
    'field.type': 'Type',
    'field.radius': 'Radius',
    'field.completed': 'Completed',
    'field.description': 'Description',
    'field.movementMode': 'Movement Mode',
    'field.trackingStatus': 'Tracking Status',
    'field.pathPoints': 'Path Points',
    'field.velocity': 'Velocity',
    'field.taskStatus': 'Task Status',
    'field.coverageProgress': 'Coverage Progress',
    'field.charge': 'Charge',
    'field.height': 'Height',
    'field.size': 'Size',
    'field.vertices': 'Vertices',
    'field.area': 'Area',
    'field.name': 'Name',
    'field.width': 'Width',
    'field.length': 'Length',
    'screenshot.capture': 'Capture',
    'screenshot.format': 'Screenshot Format',
    'nav.label': 'View Navigation',
    'nav.panUp': 'Pan View Up',
    'nav.panDown': 'Pan View Down',
    'nav.panLeft': 'Pan View Left',
    'nav.panRight': 'Pan View Right',
    'nav.reset': 'Reset View',
    'nav.zoomScale': 'Quick Zoom Scale',
    'footer.live': 'Live',
    'footer.paused': 'Paused',
    'footer.labelsOn': 'Hide Labels',
    'footer.labelsOff': 'Show Labels',
    'footer.labelsTitle': 'Show or hide drone, target, and obstacle info panels',
    'footer.trailLength': 'Trail Length',
    'footer.droneScale': 'Drone',
    'footer.targetScale': 'Target',
    'footer.obstacleScale': 'Obstacle',
    'footer.labelScale': 'Label',
    'footer.labelSizeValue': 'Label {value}%',
    'footer.labelSizeDown': 'Size-',
    'footer.labelSizeUp': 'Size+',
    'footer.labelSizeDownTitle': 'Decrease label size ([)',
    'footer.labelSizeUpTitle': 'Increase label size (])',
    'footer.labelSizeResetTitle': 'Double-click to reset label size to 100%',
    'footer.zoomScale': 'Scale: {value}%',
    'activity.selection': 'Selected {kind} {name} (ID: {id}). Viewing details; right-click to clear.',
    'activity.cameraChanged': 'Switched to {mode} view.',
    'activity.cameraChangedWithRoamSpeed': 'Switched to {mode} view · Roam speed: {speed}%',
    'activity.selectionCleared': 'Selection cleared.',
    'activity.labelsShown': 'Labels shown.',
    'activity.labelsHidden': 'Labels hidden.',
    'activity.minimapShown': 'Minimap shown.',
    'activity.minimapHidden': 'Minimap hidden.',
    'activity.screenshotSaved': 'Screenshot generated ({format}).',
    'activity.screenshotFailed': 'Screenshot failed.',
    'value.yes': 'Yes',
    'value.no': 'No',
    'value.notFlyable': 'Not flyable'
  }
};

const controlledValues: Record<Locale, Record<string, string>> = {
  'zh-CN': {
    idle: '空闲',
    ready: '就绪',
    taking_off: '起飞中',
    flying: '飞行中',
    moving: '移动中',
    hovering: '悬停',
    landing: '降落中',
    emergency: '应急',
    offline: '离线',
    fixed: '固定',
    waypoint: '航点',
    circle: '圆形',
    ellipse: '椭圆',
    polygon: '多边形',
    point: '点',
    area_coverage: '区域覆盖',
    area_search: '区域搜索',
    target_tracking: '目标跟踪',
    target_assignment: '目标分配',
    area_assignment_and_patrol: '区域分配与巡逻',
    others: '其他',
    velocity: '速度',
    path: '路径',
    stationary: '静止',
    true: '是',
    false: '否',
    'Not flyable': '不可飞越'
  },
  'en-US': {
    idle: 'Idle',
    ready: 'Ready',
    taking_off: 'Taking Off',
    flying: 'Flying',
    moving: 'Moving',
    hovering: 'Hovering',
    landing: 'Landing',
    emergency: 'Emergency',
    offline: 'Offline',
    fixed: 'Fixed',
    waypoint: 'Waypoint',
    circle: 'Circle',
    ellipse: 'Ellipse',
    polygon: 'Polygon',
    point: 'Point',
    area_coverage: 'Area Coverage',
    area_search: 'Area Search',
    target_tracking: 'Target Tracking',
    target_assignment: 'Target Assignment',
    area_assignment_and_patrol: 'Area Assignment and Patrol',
    others: 'Others',
    velocity: 'Velocity',
    path: 'Path',
    stationary: 'Stationary',
    true: 'Yes',
    false: 'No',
    '不可飞越': 'Not flyable',
    '无 current session': 'No current session',
    '请先选择一架无人机。': 'Select a drone first.',
    '该无人机没有可漫游路径。': 'The selected drone has no path to roam.',
    '请先进入漫游模式。': 'Enter roam mode first.',
    '截图导出失败': 'Screenshot export failed.',
    '已取消选择。': 'Selection cleared.'
  }
};

const enMessagePatterns: Array<[RegExp, (match: RegExpMatchArray) => string]> = [
  [/^当前会话接口失败: HTTP (.+)$/, (match) => `Current session API failed: HTTP ${match[1]}`]
];

const zhNamePatterns: Array<[RegExp, string]> = [
  [/^无人机\s*(\d+)$/, 'Drone $1'],
  [/^目标\s*(\d+)$/, 'Target $1'],
  [/^障碍物\s*(\d+)$/, 'Obstacle $1']
];

const enNamePatterns: Array<[RegExp, string]> = [
  [/^Drone\s*(\d+)$/i, '无人机 $1'],
  [/^Target\s*(\d+)$/i, '目标 $1'],
  [/^Obstacle\s*(\d+)$/i, '障碍物 $1']
];

export function normalizeLocale(value: string | null | undefined): Locale {
  return value === 'en-US' || value === 'zh-CN' ? value : 'en-US';
}

export function nextLocale(locale: Locale): Locale {
  return locale === 'zh-CN' ? 'en-US' : 'zh-CN';
}

export function t(locale: Locale, key: MessageKey, params: Record<string, string | number> = {}): string {
  let template = messages[locale][key] || messages['zh-CN'][key] || key;
  for (const [name, value] of Object.entries(params)) {
    template = template.split(`{${name}}`).join(String(value));
  }
  return template;
}

export function translateDataValue(locale: Locale, value: unknown): string {
  if (value === null || value === undefined || value === '') return '-';
  const raw = String(value);
  const direct = controlledValues[locale][raw];
  if (direct) return direct;

  if (locale === 'en-US') {
    for (const [pattern, formatter] of enMessagePatterns) {
      const match = raw.match(pattern);
      if (match) return formatter(match);
    }
    for (const [pattern, replacement] of zhNamePatterns) {
      if (pattern.test(raw)) return raw.replace(pattern, replacement);
    }
  } else {
    for (const [pattern, replacement] of enNamePatterns) {
      if (pattern.test(raw)) return raw.replace(pattern, replacement);
    }
  }

  return raw;
}
