export type Locale = 'zh-CN' | 'en-US';

type MessageKey = string;

type CoreMessageKey =
  | 'app.title'
  | 'language.toggle'
  | 'camera.free'
  | 'camera.top'
  | 'camera.follow'
  | 'camera.fit'
  | 'topbar.cheatSheet'
  | 'topbar.info'
  | 'cheat.title'
  | 'cheat.clear'
  | 'cheat.pan'
  | 'cheat.cameraTop'
  | 'cheat.cameraFollow'
  | 'cheat.cameraFit'
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
  | 'session.summary'
  | 'summary.counts'
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
  | 'field.coveragePoints'
  | 'field.coverageProgress'
  | 'field.charge'
  | 'field.height'
  | 'field.size'
  | 'field.vertices'
  | 'field.area'
  | 'field.name'
  | 'field.width'
  | 'field.length'
  | 'field.movingDuration'
  | 'field.movingPath'
  | 'field.polygonVertices'
  | 'field.velocityX'
  | 'field.velocityY'
  | 'field.velocityZ'
  | 'control.basic'
  | 'control.altitude'
  | 'control.perceivedRadius'
  | 'control.takeoff'
  | 'control.land'
  | 'control.hover'
  | 'control.returnHome'
  | 'control.charge'
  | 'control.emergency'
  | 'control.updatePerceivedRadius'
  | 'control.moveMode'
  | 'control.selectDrone'
  | 'control.backendDisconnected'
  | 'control.moveModeOn'
  | 'control.moveModeOff'
  | 'movement.title'
  | 'movement.step'
  | 'movement.altitudeStep'
  | 'movement.up'
  | 'movement.forward'
  | 'movement.left'
  | 'movement.right'
  | 'movement.backward'
  | 'movement.down'
  | 'editor.title'
  | 'editor.toggleOn'
  | 'editor.toggleOff'
  | 'editor.addDrone'
  | 'editor.addTarget'
  | 'editor.addObstacle'
  | 'editor.moveSelected'
  | 'editor.duplicate'
  | 'editor.delete'
  | 'editor.selection'
  | 'editor.snapGrid'
  | 'editor.save'
  | 'editor.saveAs'
  | 'editor.discard'
  | 'editor.off'
  | 'editor.selectToEdit'
  | 'editor.ready'
  | 'editor.updated'
  | 'editor.added'
  | 'editor.duplicated'
  | 'editor.deleted'
  | 'editor.moved'
  | 'editor.moveOn'
  | 'editor.moveOff'
  | 'editor.snapOn'
  | 'editor.snapOff'
  | 'editor.selectionChanged'
  | 'editor.selectionNoOverlap'
  | 'editor.noSession'
  | 'editor.noSaveSession'
  | 'editor.saveStart'
  | 'editor.saveDone'
  | 'editor.saveAsPrompt'
  | 'editor.saveAsStart'
  | 'editor.saveAsDone'
  | 'editor.unsavedConfirm'
  | 'editor.unsavedUnload'
  | 'editor.discarded'
  | 'editor.enableFirst'
  | 'editor.selectFirst'
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
    'camera.fit': '全局',
    'topbar.cheatSheet': '快捷键',
    'topbar.info': '信息',
    'cheat.title': '快捷键',
    'cheat.clear': '取消选择',
    'cheat.pan': '平移视角',
    'cheat.cameraTop': '俯视',
    'cheat.cameraFollow': '跟随',
    'cheat.cameraFit': '全局',
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
    'session.summary': '{drones} 架无人机 · {targets} 个目标 · {obstacles} 个障碍物',
    'summary.counts': '无人机/目标/障碍物: {drones}/{targets}/{obstacles}',
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
    'field.coveragePoints': '覆盖点数',
    'field.coverageProgress': '覆盖进度',
    'field.charge': '充电量',
    'field.height': '高度',
    'field.size': '尺寸',
    'field.vertices': '顶点数',
    'field.area': '投影面积',
    'field.name': '名称',
    'field.width': '宽度',
    'field.length': '长度',
    'field.movingDuration': '移动时长',
    'field.movingPath': '移动路径',
    'field.polygonVertices': '多边形顶点',
    'field.velocityX': '速度 X',
    'field.velocityY': '速度 Y',
    'field.velocityZ': '速度 Z',
    'control.basic': '基础控制',
    'control.altitude': '起飞/移动高度',
    'control.perceivedRadius': '感知半径',
    'control.takeoff': '起飞',
    'control.land': '降落',
    'control.hover': '悬停',
    'control.returnHome': '返航',
    'control.charge': '充电',
    'control.emergency': '应急',
    'control.updatePerceivedRadius': '更新感知半径',
    'control.moveMode': '点击地面移动',
    'control.selectDrone': '选择无人机后可控制。',
    'control.backendDisconnected': '后端未连接，正在显示演示场景。',
    'control.moveModeOn': '移动模式：点击地面发送 move_to。',
    'control.moveModeOff': '移动模式已关闭。',
    'screenshot.capture': '截图',
    'screenshot.format': '截图格式',
    'nav.label': '视图导航',
    'nav.panUp': '上移视图',
    'nav.panDown': '下移视图',
    'nav.panLeft': '左移视图',
    'nav.panRight': '右移视图',
    'nav.reset': '重置视图',
    'nav.zoomScale': '快速缩放比例尺',
    'backend.title': '后端联调',
    'backend.coverageDisplay': '覆盖显示',
    'backend.coverageSurface': '连续面',
    'backend.coveragePoints': '2D 覆盖点',
    'backend.coverageBoth': '连续面 + 覆盖点',
    'backend.currentSession': '当前会话',
    'backend.refreshSessions': '刷新会话',
    'backend.switch': '切换',
    'backend.resetCurrent': '重置当前',
    'backend.exportJson': '导出 JSON',
    'backend.deleteSession': '删除会话',
    'backend.screenshot': '后端截图',
    'backend.size': '尺寸',
    'backend.includeStatus': '包含状态/路径/覆盖信息',
    'backend.initialStatus': '可直接调用原始后端会话与截图接口。',
    'task.title': '任务与检查',
    'task.current': '当前任务',
    'task.refresh': '刷新任务',
    'task.next': '下一个',
    'task.inspect': '详情',
    'task.check': '检查',
    'task.markDone': '标记完成',
    'task.markPending': '标记待完成',
    'task.sinceTimestamp': 'since_timestamp 可选',
    'task.sincePlaceholder': '例如 1710000000.0',
    'task.checkEndpoint': '检查端点',
    'task.checkParams': '检查参数 JSON',
    'task.runCheck': '运行检查',
    'task.initialStatus': '任务队列和 /check 结果会显示在这里。',
    'advanced.title': '高级命令',
    'advanced.droneId': '无人机 ID',
    'advanced.droneIdPlaceholder': '选中无人机会自动填充',
    'advanced.command': '命令',
    'advanced.params': '参数 JSON',
    'advanced.send': '发送高级命令',
    'advanced.initialStatus': '高级命令通过 /drones/{id}/command 发送。',
    'movement.title': '实时移动',
    'movement.step': '平移步长',
    'movement.altitudeStep': '高度步长',
    'movement.up': '升',
    'movement.forward': '前',
    'movement.left': '左',
    'movement.right': '右',
    'movement.backward': '后',
    'movement.down': '降',
    'editor.title': '场景编辑',
    'editor.toggleOn': '编辑',
    'editor.toggleOff': '退出',
    'editor.addDrone': '加无人机',
    'editor.addTarget': '加目标',
    'editor.addObstacle': '加障碍',
    'editor.moveSelected': '移动选中',
    'editor.duplicate': '复制',
    'editor.delete': '删除',
    'editor.selection': 'Selection',
    'editor.snapGrid': '网格吸附',
    'editor.save': '保存',
    'editor.saveAs': '另存为',
    'editor.discard': '放弃',
    'editor.off': '编辑模式未开启。',
    'editor.selectToEdit': '选择对象后可编辑。',
    'editor.ready': '编辑草稿已就绪。',
    'editor.updated': '草稿已更新。',
    'editor.added': '已新增对象。',
    'editor.duplicated': '已复制选中对象。',
    'editor.deleted': '已删除选中对象。',
    'editor.moved': '选中对象已移动到点击位置。',
    'editor.moveOn': '移动选中已开启。',
    'editor.moveOff': '移动选中已关闭。',
    'editor.snapOn': '网格吸附已开启。',
    'editor.snapOff': '网格吸附已关闭。',
    'editor.selectionChanged': '已切换到重叠位置的下一个对象。',
    'editor.selectionNoOverlap': '当前位置没有可轮选的重叠对象。',
    'editor.noSession': '当前没有可编辑的活动会话。',
    'editor.noSaveSession': '当前没有可保存的会话。',
    'editor.saveStart': '正在保存场景数据...',
    'editor.saveDone': '场景数据已保存。',
    'editor.saveAsPrompt': '输入新会话名称',
    'editor.saveAsStart': '正在另存为新会话...',
    'editor.saveAsDone': '已另存为新会话。',
    'editor.unsavedConfirm': '当前有未保存改动，确定放弃吗？',
    'editor.unsavedUnload': '当前有未保存改动。',
    'editor.discarded': '已放弃未保存改动。',
    'editor.enableFirst': '请先开启编辑模式。',
    'editor.selectFirst': '请先选择对象。',
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
    'camera.fit': 'Fit',
    'topbar.cheatSheet': 'CheatSheet',
    'topbar.info': 'Info',
    'cheat.title': 'Keyboard Shortcuts',
    'cheat.clear': 'Clear selection',
    'cheat.pan': 'Pan view',
    'cheat.cameraTop': 'Top view',
    'cheat.cameraFollow': 'Follow view',
    'cheat.cameraFit': 'Fit all',
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
    'session.summary': '{drones} drones · {targets} targets · {obstacles} obstacles',
    'summary.counts': 'Drones/Targets/Obstacles: {drones}/{targets}/{obstacles}',
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
    'field.coveragePoints': 'Coverage Points',
    'field.coverageProgress': 'Coverage Progress',
    'field.charge': 'Charge',
    'field.height': 'Height',
    'field.size': 'Size',
    'field.vertices': 'Vertices',
    'field.area': 'Area',
    'field.name': 'Name',
    'field.width': 'Width',
    'field.length': 'Length',
    'field.movingDuration': 'Moving Duration',
    'field.movingPath': 'Moving Path',
    'field.polygonVertices': 'Polygon Vertices',
    'field.velocityX': 'Velocity X',
    'field.velocityY': 'Velocity Y',
    'field.velocityZ': 'Velocity Z',
    'control.basic': 'Basic Control',
    'control.altitude': 'Takeoff / Move Altitude',
    'control.perceivedRadius': 'Perception Radius',
    'control.takeoff': 'Take Off',
    'control.land': 'Land',
    'control.hover': 'Hover',
    'control.returnHome': 'Return',
    'control.charge': 'Charge',
    'control.emergency': 'Emergency',
    'control.updatePerceivedRadius': 'Update Perception',
    'control.moveMode': 'Click Ground to Move',
    'control.selectDrone': 'Select a drone to control it.',
    'control.backendDisconnected': 'Backend disconnected. Showing demo scene.',
    'control.moveModeOn': 'Move mode: click ground to send move_to.',
    'control.moveModeOff': 'Move mode off.',
    'screenshot.capture': 'Capture',
    'screenshot.format': 'Screenshot Format',
    'nav.label': 'View Navigation',
    'nav.panUp': 'Pan View Up',
    'nav.panDown': 'Pan View Down',
    'nav.panLeft': 'Pan View Left',
    'nav.panRight': 'Pan View Right',
    'nav.reset': 'Reset View',
    'nav.zoomScale': 'Quick Zoom Scale',
    'backend.title': 'Backend Tools',
    'backend.coverageDisplay': 'Coverage Display',
    'backend.coverageSurface': 'Continuous Surface',
    'backend.coveragePoints': '2D Coverage Points',
    'backend.coverageBoth': 'Surface + Points',
    'backend.currentSession': 'Current Session',
    'backend.refreshSessions': 'Refresh Sessions',
    'backend.switch': 'Switch',
    'backend.resetCurrent': 'Reset Current',
    'backend.exportJson': 'Export JSON',
    'backend.deleteSession': 'Delete Session',
    'backend.screenshot': 'Backend Screenshot',
    'backend.size': 'Size',
    'backend.includeStatus': 'Include status / paths / coverage',
    'backend.initialStatus': 'Calls the original backend session and screenshot APIs directly.',
    'task.title': 'Tasks & Checks',
    'task.current': 'Current Task',
    'task.refresh': 'Refresh Tasks',
    'task.next': 'Next',
    'task.inspect': 'Details',
    'task.check': 'Check',
    'task.markDone': 'Mark Done',
    'task.markPending': 'Mark Pending',
    'task.sinceTimestamp': 'since_timestamp optional',
    'task.sincePlaceholder': 'Example: 1710000000.0',
    'task.checkEndpoint': 'Check Endpoint',
    'task.checkParams': 'Check Params JSON',
    'task.runCheck': 'Run Check',
    'task.initialStatus': 'Task queue and /check results appear here.',
    'advanced.title': 'Advanced Commands',
    'advanced.droneId': 'Drone ID',
    'advanced.droneIdPlaceholder': 'Auto-filled from selected drone',
    'advanced.command': 'Command',
    'advanced.params': 'Params JSON',
    'advanced.send': 'Send Advanced Command',
    'advanced.initialStatus': 'Advanced commands are sent through /drones/{id}/command.',
    'movement.title': 'Live Movement',
    'movement.step': 'Move Step',
    'movement.altitudeStep': 'Altitude Step',
    'movement.up': 'Up',
    'movement.forward': 'Forward',
    'movement.left': 'Left',
    'movement.right': 'Right',
    'movement.backward': 'Back',
    'movement.down': 'Down',
    'editor.title': 'Scene Editor',
    'editor.toggleOn': 'Edit',
    'editor.toggleOff': 'Exit',
    'editor.addDrone': 'Add Drone',
    'editor.addTarget': 'Add Target',
    'editor.addObstacle': 'Add Obstacle',
    'editor.moveSelected': 'Move Selected',
    'editor.duplicate': 'Duplicate',
    'editor.delete': 'Delete',
    'editor.selection': 'Selection',
    'editor.snapGrid': 'Snap to Grid',
    'editor.save': 'Save',
    'editor.saveAs': 'Save As',
    'editor.discard': 'Discard',
    'editor.off': 'Edit mode is off.',
    'editor.selectToEdit': 'Select an object to edit.',
    'editor.ready': 'Edit draft is ready.',
    'editor.updated': 'Draft updated.',
    'editor.added': 'Object added.',
    'editor.duplicated': 'Selected object duplicated.',
    'editor.deleted': 'Selected object deleted.',
    'editor.moved': 'Selected object moved to the clicked position.',
    'editor.moveOn': 'Move selected is on.',
    'editor.moveOff': 'Move selected is off.',
    'editor.snapOn': 'Snap to grid is on.',
    'editor.snapOff': 'Snap to grid is off.',
    'editor.selectionChanged': 'Switched to the next overlapping object.',
    'editor.selectionNoOverlap': 'No overlapping object to cycle at this position.',
    'editor.noSession': 'No active editable session.',
    'editor.noSaveSession': 'No session to save.',
    'editor.saveStart': 'Saving scene data...',
    'editor.saveDone': 'Scene data saved.',
    'editor.saveAsPrompt': 'Enter a new session name',
    'editor.saveAsStart': 'Saving as a new session...',
    'editor.saveAsDone': 'Scene saved as a new session.',
    'editor.unsavedConfirm': 'You have unsaved changes. Discard them?',
    'editor.unsavedUnload': 'You have unsaved changes.',
    'editor.discarded': 'Unsaved changes discarded.',
    'editor.enableFirst': 'Turn on edit mode first.',
    'editor.selectFirst': 'Select an object first.',
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
    '正在更新感知半径...': 'Updating perception radius...',
    '无 current session': 'No current session',
    '请先选择一架无人机。': 'Select a drone first.',
    '感知半径必须大于 0。': 'Perception radius must be greater than 0.',
    '无人机已更新': 'Drone updated',
    '无人机更新请求超时': 'Drone update request timed out',
    '无人机更新请求失败': 'Drone update request failed',
    '无人机需要降落并处于 idle 状态才能充电。': 'The drone must be landed and idle before charging.',
    '当前状态不需要应急降落。': 'The current state does not need emergency landing.',
    '请选择会话。': 'Select a session.',
    '请选择任务。': 'Select a task.',
    '已取消。': 'Canceled.',
    '当前没有可导出的会话。': 'No session available to export.',
    '不能删除唯一的会话，请先创建或切换到其他会话。': 'Cannot delete the only session. Create or switch to another session first.',
    '请填写无人机 ID，或先选中无人机。': 'Enter a drone ID or select a drone first.',
    '参数必须是 JSON 对象。': 'Parameters must be a JSON object.',
    'since_timestamp 必须是数字。': 'since_timestamp must be a number.',
    '请求中...': 'Requesting...',
    '请求失败': 'Request failed',
    '无会话': 'No Session',
    '无任务': 'No Task',
    '未命名': 'Unnamed',
    '截图导出失败': 'Screenshot export failed',
    '已取消选择。': 'Selection cleared.',
    '命令已发送': 'Command sent',
    '命令请求失败': 'Command request failed'
  }
};

const enMessagePatterns: Array<[RegExp, (match: RegExpMatchArray) => string]> = [
  [/^当前状态 (.+) 不允许普通控制。$/, (match) => `Current status ${translateDataValue('en-US', match[1])} does not allow normal control.`],
  [/^当前状态 (.+) 不允许相对移动。$/, (match) => `Current status ${translateDataValue('en-US', match[1])} does not allow relative movement.`],
  [/^当前状态 (.+) 不允许移动。$/, (match) => `Current status ${translateDataValue('en-US', match[1])} does not allow movement.`],
  [/^未知命令: (.+)$/, (match) => `Unknown command: ${match[1]}`],
  [/^当前会话接口失败: HTTP (.+)$/, (match) => `Current session API failed: HTTP ${match[1]}`],
  [/^状态接口失败: HTTP (.+)$/, (match) => `State API failed: HTTP ${match[1]}`],
  [/^会话数据接口失败: HTTP (.+)$/, (match) => `Session data API failed: HTTP ${match[1]}`],
  [/^保存会话失败: HTTP (.+)$/, (match) => `Save session failed: HTTP ${match[1]}`],
  [/^创建会话失败: HTTP (.+)$/, (match) => `Create session failed: HTTP ${match[1]}`],
  [/^切换会话失败: HTTP (.+)$/, (match) => `Switch session failed: HTTP ${match[1]}`],
  [/^后端截图失败: HTTP (.+)$/, (match) => `Backend screenshot failed: HTTP ${match[1]}`],
  [/^命令失败: HTTP (.+)$/, (match) => `Command failed: HTTP ${match[1]}`],
  [/^确认删除会话 (.+)？$/, (match) => `Delete session ${match[1]}?`],
  [/^当前历史字段: (.+)$/, (match) => `Current history fields: ${match[1]}`],
  [/^路径被障碍物 (.+) 阻挡$/, (match) => `Path blocked by obstacle ${match[1]}`],
  [/^路径与障碍物 (.+) 相交$/, (match) => `Path intersects obstacle ${match[1]}`]
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
  const text = String(value);
  const exact = controlledValues[locale][text];
  if (exact) return exact;

  if (locale === 'en-US') {
    for (const [pattern, replace] of enMessagePatterns) {
      const match = text.match(pattern);
      if (match) return replace(match);
    }
  }

  const patterns = locale === 'en-US' ? zhNamePatterns : enNamePatterns;
  for (const [pattern, replacement] of patterns) {
    if (pattern.test(text)) return text.replace(pattern, replacement);
  }

  if (locale === 'en-US' && /^[a-z]+(?:_[a-z]+)+$/.test(text)) {
    return text.split('_').map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(' ');
  }
  return text;
}
