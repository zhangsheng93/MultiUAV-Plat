# 无人机仿真与控制系统教程

【撰写人】：符倚嘉、赵江伟、胡天宇

【审校人】：张胜

【版本号】：v0.4

【时  间】：2026-7-2

# 启动系统

系统包含服务器端和控制器端，服务器端为平台的主要端口，控制器端为人工控制端口，可作为开发参考。需要在服务器端的基础上完成开发。

## 1.1 无人机仿真系统

启动 `MultiUAV-Plat.Server.exe`，出现命令提示符窗口。

<p align="center">
  <img src="./images/1.1-1.png" alt="图1.1-1" />
</p>

<p align="center"><em>图1.1-1 启动服务器后出现的命令提示符窗口</em></p>

此时 **REST API 服务已在后台启动**（默认地址 `http://127.0.0.1:8000`），随后会弹出选项窗口，询问是否打开图形界面。

<p align="center">
  <img src="./images/1.1-2.png" alt="图1.1-2" />
</p>

<p align="center"><em>图1.1-2 是否启动图形界面的选项窗口</em></p>

窗口提示：`The API server is running in the background.`（API 服务已在后台运行），并询问 `Would you like to open the graphical dashboard?`（是否打开图形仪表盘）。

| 选项 | 效果 |
| --- | --- |
| **Yes（是）** | 在 API 服务继续运行的基础上，额外打开 **2D 图形界面**（Pygame 仿真仪表盘），可进行可视化监控与部分手动操作 |
| **No（否）** | **仅保留 API 服务器**，不启动图形界面；命令提示符窗口保持运行，可在其中看到 `API server running in background. Press Ctrl+C to stop.` 等提示 |
| **关闭窗口（×）** | 取消启动，程序退出 |

选择 **No** 时，仿真平台仍以 **纯 API 模式** 运行，Controller、3D 查看器、智能体服务等外部程序均可正常连接 `http://127.0.0.1:8000` 进行开发与测试；只是不会弹出 1.1-3 所示的 2D 可视化窗口。适合只需 API、不需要本地图形界面的场景。

选择 **Yes** 后，图形界面如下图所示。

<p align="center">
  <img src="./images/1.1-3.png" alt="图1.1-3" />
</p>

<p align="center"><em>图1.1-3 图形界面（选择 Yes 后打开）</em></p>

无人机仿真系统启动成功！

## 1.2无人机控制系统

启动MultiUAV-Plat.Controller.exe，出现命令提示符窗口和场景管理窗口。

<p align="center">
  <img src="./images/1.2-1.png" alt="图1.2-1" />
</p>

<p align="center"><em>图1.2-1 控制器命令提示符窗口</em></p>

<p align="center">
  <img src="./images/1.2-2.png" alt="图1.2-2" />
</p>

<p align="center"><em>图1.2-2 场景管理窗口</em></p>

无人机控制系统启动成功！

# 2.编辑整体场景

## 2.1创建场景

在场景管理窗口，点击“New”按钮，进入新场景创建界面。

<p align="center">
  <img src="./images/2.1-1.png" alt="图2.1-1" />
</p>

<p align="center"><em>图2.1-1 点击 New 按钮进入新场景创建</em></p>

新场景创建界面如下图所示。

<p align="center">
  <img src="./images/2.1-2.png" alt="图2.1-2" />
</p>

<p align="center"><em>图2.1-2 新场景创建界面</em></p>

Session Name：场景名称

Description：场景描述

Task Type：任务类型，有5个选项。

| 名称 | 含义 |
| --- | --- |
| area_search | 区域搜索 |
| area_assignment_and_patrol | 区域分配与巡逻 |
| target_assignment | 目标分配 |
| target_tracking | 目标跟踪 |
| others | 其他 |

Task Des.：任务描述

Area Size：区域面积，Width宽度，Height高度

Initialization：初始化方式，有3个选项。

| 名称 | 含义 |
| --- | --- |
| Seed with example data | 创建预设数据场景 |
| Start empty session | 创建空白场景 |
| Start auto-generate random entities | 创建随机实体场景 |

选择Start auto-generate random entities选项以后，需要指定随机生成的无人机（Drones）、目标（Targets）、障碍物（Obstacles）数量。按此方式创建场景以后，会随机生成指定数量的这3类实体。

Generate session init screenshot：展示新建场景的图形界面

Create tasks from templates：从模板创建任务，选择此选项以后，需要指定任务数量（Task Num）

Auto load created session：自动加载已创建的会话

Create：创建场景

Create Batch：批量创建场景。点击后会出现一个窗口，填写需要批量创建的场景数量。

<p align="center">
  <img src="./images/2.1-3.png" alt="图2.1-3" />
</p>

<p align="center"><em>图2.1-3 批量创建场景窗口</em></p>

下面以Start empty session初始化方式为例，创建一个空白场景，如下图中的New Session 1所示。

<p align="center">
  <img src="./images/2.1-4.png" alt="图2.1-4" />
</p>

<p align="center"><em>图2.1-4 创建成功的空白场景 New Session 1</em></p>

场景创建成功！

## 2.2打开场景

选中刚才创建的New Session 1，点击“Launch”按钮，打开场景。

<p align="center">
  <img src="./images/2.2-1.png" alt="图2.2-1" />
</p>

<p align="center"><em>图2.2-1 选中场景并点击 Launch 按钮</em></p>

打开场景后，会进入控制台界面。点击 **View Full Data** 按钮，会弹出 **Session Data** 对话框，以结构化方式展示当前场景的基本信息与各实体列表。

<p align="center">
  <img src="./images/2.2-2.png" alt="图2.2-2" />
</p>

<p align="center"><em>图2.2-2 控制台界面与 View Full Data 按钮</em></p>

在该对话框右下角点击 **View Raw Data**，会再弹出一个 **Session Data - Raw Data** 窗口，以带语法高亮的 JSON 格式展示场景的**完整原始数据**，便于核对或复制。窗口底部提供 **Copy**（复制全部 JSON）和 **Close**（关闭）按钮。

典型字段包括：

| 类别 | 字段示例 | 说明 |
|------|----------|------|
| 会话标识 | `id`、`name`、`description`、`status`、`creator` | 场景 ID、名称、描述、运行状态与创建者 |
| 任务信息 | `task_type`、`task_description` | 任务类型与说明 |
| 画布设置 | `canvas_width`、`canvas_height`、`is_distance_3d` | 仿真画布尺寸与距离计算模式 |
| 时间戳 | `created_at`、`last_updated` | 创建与最后更新时间（Unix 时间戳） |
| 统计信息 | `statistics.drone_count`、`target_count`、`obstacle_count` 等 | 无人机、目标、障碍物数量及累计飞行数据 |

<p align="center">
  <img src="./images/2.2-3.png" alt="图2.2-3" />
</p>

<p align="center"><em>图2.2-3 点击 View Raw Data 后显示的完整 JSON 原始数据</em></p>

观察之前打开的仿真系统图形界面，会发现已经更新为选定的空白场景。

<p align="center">
  <img src="./images/2.2-4.png" alt="图2.2-4" />
</p>

<p align="center"><em>图2.2-4 仿真系统更新为选定的空白场景</em></p>

场景打开成功！

## 2.3导出场景

选中刚才创建的New Session 1，点击“Export”按钮，导出场景。场景会以json格式的文件存储在本地。

<p align="center">
  <img src="./images/2.3-1.png" alt="图2.3-1" />
</p>

<p align="center"><em>图2.3-1 点击 Export 按钮导出场景</em></p>

## 2.4删除场景

选中刚才创建的New Session 1，点击“Delete”按钮。

<p align="center">
  <img src="./images/2.4-1.png" alt="图2.4-1" />
</p>

<p align="center"><em>图2.4-1 删除场景Delete按钮</em></p>

出现一个删除场景窗口，点击“是”即可删除场景。

<p align="center">
  <img src="./images/2.4-2.png" alt="图2.4-2" />
</p>

<p align="center"><em>图2.4-2 删除场景确认窗口</em></p>

# 3.修改场景内容

打开1个场景。观察控制台界面，发现上面有4个子页面：无人机（Drones）、目标（Targets）、障碍物（Obstacles）、气象环境（Environments）。这些是一个场景中的要素，可以修改。

<p align="center">
  <img src="./images/3-1.png" alt="图3-1" />
</p>

<p align="center"><em>图3-1 控制台的四个子页面</em></p>

## 3.1无人机

### 3.1.1添加

点击“Drones”子页面，然后点击“Add”按钮。

<p align="center">
  <img src="./images/3.1.1-1.png" alt="图3.1.1-1" />
</p>

<p align="center"><em>图3.1.1-1 Drones 子页面与 Add 按钮</em></p>

出现了添加无人机的界面。

<p align="center">
  <img src="./images/3.1.1-2.png" alt="图3.1.1-2" />
</p>

<p align="center"><em>图3.1.1-2 添加无人机界面</em></p>

Name：名称

Model：仿真的模型

Position X/Y：水平坐标

Altitude：高度

Heading：方向角，0表示正北，顺时针增加。

Battery Level：电量百分比

Status：状态，有4个选项。

| 名称 | 含义 |
| --- | --- |
| idle | 空闲 |
| hovering | 正在悬停 |
| emergency | 故障 |
| offline | 断开连接 |

Max Speed：最大速度

Max Altitude：最大高度

Battery Capacity：电池容量

Perceived Radius：探测半径

Task Radius：任务半径

点击“Add Drone”按钮，即可添加无人机。

### 3.1.2编辑

选中一个无人机，点击“Edit”按钮。

<p align="center">
  <img src="./images/3.1.2-1.png" alt="图3.1.2-1" />
</p>

<p align="center"><em>图3.1.2-1 选中无人机并点击 Edit 按钮</em></p>

出现了编辑无人机的界面。其中的内容与添加无人机的界面相同，不再赘述。点击“Save Changes”按钮，保存设置。

<p align="center">
  <img src="./images/3.1.2-2.png" alt="图3.1.2-2" />
</p>

<p align="center"><em>图3.1.2-2 编辑无人机界面</em></p>

### 3.1.3删除

选中一个无人机，点击“Delete”按钮。

<p align="center">
  <img src="./images/3.1.3-1.png" alt="图3.1.3-1" />
</p>

<p align="center"><em>图3.1.3-1 选中无人机并点击 Delete 按钮</em></p>

出现了删除无人机的界面，点击“Delete”按钮即可删除该无人机。

<p align="center">
  <img src="./images/3.1.3-2.png" alt="图3.1.3-2" />
</p>

<p align="center"><em>图3.1.3-2 删除无人机界面</em></p>

## 3.2目标

目标分为5种：航点目标（Waypoint）、活动目标（Moving）、固定目标（Fixed）、圆形目标（Circle）和多边形目标（Polygon）。以下是一个仿真系统图形界面示例：

<p align="center">
  <img src="./images/3.2-1.png" alt="图3.2-1" />
</p>

<p align="center"><em>图3.2-1 五种目标的显示效果</em></p>

图中绿色表示航点目标，红色表示活动目标，黄色表示固定目标，深蓝色表示圆形目标，浅蓝色表示多边形目标。编辑和删除操作与无人机的类似，不再赘述。下面介绍这5类目标的添加操作。

### 3.2.1航点目标（充电站）

点击“Target”子页面，然后点击“+Waypoint”按钮。

<p align="center">
  <img src="./images/3.2.1-1.png" alt="图3.2.1-1" />
</p>

<p align="center"><em>图3.2.1-1 Target 子页面与 +Waypoint 按钮</em></p>

出现了添加航点目标的界面。

<p align="center">
  <img src="./images/3.2.1-2.png" alt="图3.2.1-2" />
</p>

<p align="center"><em>图3.2.1-2 航点目标信息</em></p>

Name：名称

Description：描述

Position X/Y：空间位置

Radius：半径

Charge Amount：可充电量

点击“Add Target”按钮，即可添加航点目标。

### 3.2.2活动目标

点击“+Moving”按钮。

<p align="center">
  <img src="./images/3.2.2-1.png" alt="图3.2.2-1" />
</p>

<p align="center"><em>图3.2.2-1 点击 +Moving 按钮</em></p>

出现了添加活动目标的界面。

<p align="center">
  <img src="./images/3.2.2-2.png" alt="图3.2.2-2" />
</p>

<p align="center"><em>图3.2.2-2 添加活动目标界面</em></p>

Velocity X/Y/Z：在3个维度上的速度

Duration：目标运动的总持续时间

Movement Mode：运动模式，包含以下3种模式

| 名称 | 含义 |
| --- | --- |
| Velocity-based (Ping-pong movement) | 基于速度的往复运动 |
| Path-based (Follow waypoints) | 基于路径的航点跟随 |
| Stationary (No movement) | 静止不动 |

### 3.2.3固定目标

点击“+Fixed”按钮。

<p align="center">
  <img src="./images/3.2.3-1.png" alt="图3.2.3-1" />
</p>

<p align="center"><em>图3.2.3-1 点击 +Fixed 按钮</em></p>

出现了添加固定目标的界面。

<p align="center">
  <img src="./images/3.2.3-2.png" alt="图3.2.3-2" />
</p>

<p align="center"><em>图3.2.3-2 添加固定目标界面</em></p>

### 3.2.4圆形目标

点击“+Circle”按钮。

<p align="center">
  <img src="./images/3.2.4-1.png" alt="图3.2.4-1" />
</p>

<p align="center"><em>图3.2.4-1 点击 +Circle 按钮</em></p>

出现了添加圆形目标的界面。

<p align="center">
  <img src="./images/3.2.4-2.png" alt="图3.2.4-2" />
</p>

<p align="center"><em>图3.2.4-2 添加圆形目标界面</em></p>

### 3.2.5多边形目标

点击“+Polygon”按钮。

<p align="center">
  <img src="./images/3.2.5-1.png" alt="图3.2.5-1" />
</p>

<p align="center"><em>图3.2.5-1 点击 +Polygon 按钮</em></p>

出现了添加多边形目标的界面。

<p align="center">
  <img src="./images/3.2.5-2.png" alt="图3.2.5-2" />
</p>

<p align="center"><em>图3.2.5-2 添加多边形目标界面</em></p>

Vertices：顶点水平坐标，至少要填3行，表示至少要有3个顶点。

## 3.3障碍物

障碍物分为4种：点障碍物（Point）、圆柱障碍物（Circle）、椭圆柱障碍物（Ellipse）、多面体障碍物（Polygon）。以下是一个仿真系统图形界面示例：

<p align="center">
  <img src="./images/3.3-1.png" alt="图3.3-1" />
</p>

<p align="center"><em>图3.3-1 四种障碍物的显示效果</em></p>

图中，黑色表示点障碍物，棕色表示圆柱障碍物，灰蓝色表示椭圆柱障碍物，灰色表示多面体障碍物。编辑和删除操作与无人机的类似，不再赘述。下面介绍这4类障碍物的添加操作。

### 3.3.1点障碍物

点击“Obstacles”子页面，然后点击“+Point”按钮。

<p align="center">
  <img src="./images/3.3.1-1.png" alt="图3.3.1-1" />
</p>

<p align="center"><em>图3.3.1-1 Obstacles 子页面与 +Point 按钮</em></p>

出现了添加点障碍物的界面。

<p align="center">
  <img src="./images/3.3.1-2.png" alt="图3.3.1-2" />
</p>

<p align="center"><em>图3.3.1-2 添加点障碍物界面</em></p>

Name：名称

Description：描述

Position X/Y/Z：空间坐标

Radius：半径

点击“Add Obstacle”按钮，即可添加点障碍物。

### 3.3.2圆柱障碍物

点击“+Circle”按钮。

<p align="center">
  <img src="./images/3.3.2-1.png" alt="图3.3.2-1" />
</p>

<p align="center"><em>图3.3.2-1 点击 +Circle 按钮</em></p>

出现了添加圆柱障碍物的界面。

<p align="center">
  <img src="./images/3.3.2-2.png" alt="图3.3.2-2" />
</p>

<p align="center"><em>图3.3.2-2 添加圆柱障碍物界面</em></p>

### 3.3.3椭圆柱障碍物

点击“+Ellipse”按钮。

<p align="center">
  <img src="./images/3.3.3-1.png" alt="图3.3.3-1" />
</p>

<p align="center"><em>图3.3.3-1 点击 +Ellipse 按钮</em></p>

出现了添加椭圆柱障碍物的界面。

<p align="center">
  <img src="./images/3.3.3-2.png" alt="图3.3.3-2" />
</p>

<p align="center"><em>图3.3.3-2 添加椭圆柱障碍物界面</em></p>

Width：宽度

Length：长度

### 3.3.4多面体障碍物

点击“+Polygon”按钮。

<p align="center">
  <img src="./images/3.3.4-1.png" alt="图3.3.4-1" />
</p>

<p align="center"><em>图3.3.4-1 点击 +Polygon 按钮</em></p>

出现了添加多面体障碍物的界面。

<p align="center">
  <img src="./images/3.3.4-2.png" alt="图3.3.4-2" />
</p>

<p align="center"><em>图3.3.4-2 添加多面体障碍物界面</em></p>

Vertices：顶点水平坐标，至少要填3行，表示底面至少要有3个顶点。

## 3.4气象环境

编辑和删除操作与无人机的类似，不再赘述。下面介绍气象环境的添加操作。

点击“Environment”子页面，然后点击“Create Environment”按钮。

<p align="center">
  <img src="./images/3.4-1.png" alt="图3.4-1" />
</p>

<p align="center"><em>图3.4-1 Environment 子页面与 Create Environment 按钮</em></p>

出现了添加气象环境的界面。

<p align="center">
  <img src="./images/3.4-2.png" alt="图3.4-2" />
</p>

<p align="center"><em>图3.4-2 气象环境信息</em></p>

Name：名称

Description：描述

Weather Condition：天气情况，有6个选项。

| 名称 | 含义 |
| --- | --- |
| clear | 晴天 |
| cloudy | 阴 |
| rainy | 下雨 |
| storm | 风暴 |
| fog | 起雾 |
| snow | 下雪 |
| partly_cloudy | 多云 |
| heavy_rain | 暴雨 |

Temperature：温度

Humidity：湿度

Wind Speed：风速

Wind Direction：风向，有8个选项。

| 名称 | 含义 |
| --- | --- |
| north | 北风 |
| northeast | 东北风 |
| east | 东风 |
| southeast | 东南风 |
| south | 南风 |
| southwest | 西南风 |
| west | 西风 |
| northwest | 西北风 |

Visibility：能见度

点击“Create”按钮，即可添加气象环境。回到控制台界面，选中刚才添加的气象环境，点击“Set as Current”按钮，即可设为当前气象环境。

<p align="center">
  <img src="./images/3.4-3.png" alt="图3.4-3" />
</p>

<p align="center"><em>图3.4-3 设置当前气象环境</em></p>

## 3.5图形化修改

回到初始的控制台界面，点击“Visually Edit Session”按钮。

<p align="center">
  <img src="./images/3.5-1.png" alt="图3.5-1" />
</p>

<p align="center"><em>图3.5-1 点击 Visually Edit Session 按钮</em></p>

出现了图形化修改界面。

<p align="center">
  <img src="./images/3.5-2.png" alt="图3.5-2" />
</p>

<p align="center"><em>图3.5-2 图形化修改界面</em></p>

可以看到，图形化修改界面有“Add Drone”“Add Target”“Add Obstacle”按钮，支持无人机、目标、障碍物的添加。点击选中一个要素以后：

| 按钮 | 功能 |
| --- | --- |
| Move | 拖动位置 |
| Edit | 编辑内容 |
| Delete | 删除 |
| Duplicate | 复制 |

“Snap to Grid”按钮表示网格吸附，可以配合“Move”使用。

点击“Save”保存修改，“Save As”另存为，“Close”关闭。

# 4.无人机控制

有2个途径可以控制无人机，一个是通过仿真系统，另一个是通过控制系统。

## 4.1仿真系统

转到仿真系统图形界面，点击选中1个无人机。

<p align="center">
  <img src="./images/4.1-1.png" alt="图4.1-1" />
</p>

<p align="center"><em>图4.1-1 在仿真系统中选中一个无人机</em></p>

点击“Take Off”按钮，让无人机起飞。

<p align="center">
  <img src="./images/4.1-2.png" alt="图4.1-2" />
</p>

<p align="center"><em>图4.1-2 点击 Take Off 按钮让无人机起飞</em></p>

然后可以通过点击图上的任意位置，将无人机移动至该位置。点击“Land”按钮降落，“Cancel Selection”取消选择。

## 4.2控制系统

转到控制台的Drones页面，观察到下方有4个按钮“Take Off”“Land”“Move To”“Control”。

<p align="center">
  <img src="./images/4.2-1.png" alt="图4.2-1" />
</p>

<p align="center"><em>图4.2-1 控制台 Drones 页面的控制按钮</em></p>

点击选中1个无人机，然后点击“Take Off”按钮，出现一个起飞高度设置界面。

<p align="center">
  <img src="./images/4.2-2.png" alt="图4.2-2" />
</p>

<p align="center"><em>图4.2-2 起飞高度设置界面</em></p>

设置高度后，点击“OK”，无人机起飞。然后选中该无人机，点击“Move To”按钮，出现一个坐标设置界面。

<p align="center">
  <img src="./images/4.2-3.png" alt="图4.2-3" />
</p>

<p align="center"><em>图4.2-3 坐标设置界面</em></p>

设置X/Y/Z坐标后，点击“Move”按钮，无人机飞到设置的坐标。然后选中该无人机，点击“Land”按钮，无人机降落。

要想实现手柄式的无人机控制，需要选中1个无人机，点击“Control”按钮，进入手柄式控制界面。

<p align="center">
  <img src="./images/4.2-4.png" alt="图4.2-4" />
</p>

<p align="center"><em>图4.2-4 手柄式控制界面</em></p>

Drone Status：无人机状态

Nearby：无人机周围情况

Basic Controls：无人机基本控制指令

| 名称 | 含义 |
| --- | --- |
| Take Off | 起飞 |
| Land | 降落 |
| Charge | 充电 |
| Return Home | 回到出发点 |

Movement Controls：无人机移动，有前后左右上下6个方向，以及移动的距离。

Manual Position Control：设置X/Y/Z坐标，点击“Move to Position”按钮，无人机飞到设置的坐标。

# 5.任务管理

编辑和删除操作与无人机的类似，不再赘述。

## 5.1添加任务

回到控制台界面，点击“Tasks”子页面。

<p align="center">
  <img src="./images/5.1-1.png" alt="图5.1-1" />
</p>

<p align="center"><em>图5.1-1 Tasks 子页面</em></p>

| 名称 | 含义 |
| --- | --- |
| Add | 添加 |
| Edit | 编辑 |
| Duplicate | 复制 |
| ↑/↓ | 向上移动/向下移动 |
| From Template | 从模板加载 |
| Refresh | 刷新 |
| Copy Original Command | 复制原始命令 |
| Copy Command | 复制命令 |
| Done | 标记完成 |
| Check | 检查 |
| Export Results | 导出结果 |
| Land All Drones | 让所有无人机降落 |
| Charge All Drones | 让所有无人机充电 |

点击“Add”按钮，出现了创建任务的界面。

<p align="center">
  <img src="./images/5.1-2.png" alt="图5.1-2" />
</p>

<p align="center"><em>图5.1-2 创建任务界面</em></p>

Name：任务名称

Creator：创建者

Difficulty：难度，有3个选项。

| 名称 | 含义 |
| --- | --- |
| easy | 简单 |
| medium | 中等 |
| hard | 困难 |

Content：任务内容

Content Aliases：任务代号

Description：任务描述

Related APIs：关联服务器API。点击“Add”，弹窗后点击“Category”可以查看选择API实施对象，点击“API Endpoint”选择具体指令。选择之后，“Parameters”栏会显示具体参数

<p align="center">
  <img src="./images/5.1-3.png" alt="图5.1-3" />
</p>

<p align="center"><em>图5.1-3 关联 API 的类别选择</em></p>

<p align="center">
  <img src="./images/5.1-4.png" alt="图5.1-4" />
</p>

<p align="center"><em>图5.1-4 选择具体 API 指令</em></p>

<p align="center">
  <img src="./images/5.1-5.png" alt="图5.1-5" />
</p>

<p align="center"><em>图5.1-5 具体参数显示</em></p>

| 名称 | 含义 |
| --- | --- |
| Add | 添加 |
| Edit | 编辑 |
| Duplicate | 复制 |
| Remove | 移除 |
| ↑/↓ | 向上移动/向下移动 |
| import | 加载 |

Execution Check APIs：执行检察API

| 名称 | 含义 |
| --- | --- |
| Add Check | 添加 |
| Add Group | 添加分组 |
| Remove | 移除 |
| ↑/↓ | 向上移动/向下移动 |

## 5.2标记任务完成情况

点击选中1个未完成的任务，然后点击“Done”按钮，标记该任务已完成。

点击选中1个已完成的任务，然后点击“Undone”按钮，标记该任务未完成。

<p align="center">
  <img src="./images/5.2-1.png" alt="图5.2-1" />
</p>

<p align="center"><em>图5.2-1 标记任务为已完成</em></p>

<p align="center">
  <img src="./images/5.2-2.png" alt="图5.2-2" />
</p>

<p align="center"><em>图5.2-2 标记任务为未完成</em></p>

## 5.3任务模板

除了手动逐项创建任务，系统还提供了任务模板功能。任务模板是一段可复用的任务定义，其中使用占位符（如 `{drone_1_name}`、`{random_altitude}` 等）代替具体的实体或数值。通过模板，可以快速、批量地生成结构一致但参数不同的任务。

模板分为两类：

- **内置模板**：系统自带的常用模板（如 `basic_takeoff_land`、`patrol_mission`、`search_task`、`grid_search` 等），不可删除，但可以复制后修改成自定义模板。
- **自定义模板**：用户自行创建或由内置模板复制而来，存储在本地 `./templates/task_templates.json` 文件中。

### 5.3.1编辑任务模板

在“Tasks”子页面点击“From Template”按钮，打开任务模板浏览器。

<p align="center">
  <img src="./images/5.3-1.png" alt="图5.3-1" />
</p>

<p align="center"><em>图5.3-1 Tasks 子页面的 From Template 按钮</em></p>

任务模板浏览器如下图所示，列出了所有可用模板（名称、分类、难度、适用任务类型、检查数量），选中某个模板后，下方会显示其描述与任务内容。

<p align="center">
  <img src="./images/5.3-2.png" alt="图5.3-2" />
</p>

<p align="center"><em>图5.3-2 任务模板浏览器</em></p>

在浏览器中：

- 选中一个模板，可查看其描述与内容。
- 对内置模板可执行“复制（Duplicate）”，生成一个可编辑的自定义副本。复制时会弹出对话框，为副本输入名称。
- 对自定义模板可执行编辑（Edit）、删除（Delete）操作。

<p align="center">
  <img src="./images/5.3-3.png" alt="图5.3-3" />
</p>

<p align="center"><em>图5.3-3 复制模板并命名</em></p>

点击“Edit”按钮，进入任务模板编辑器。编辑器中可以修改模板名称、分类、难度、适用任务类型、任务内容（Content）、任务代号（Aliases）、描述、关联 API（Related APIs）以及执行检查 API（Execution Check APIs）。右侧的“Detected Placeholders”会检测模板中使用的占位符，“Quick Insert”可快速插入常用占位符。

<p align="center">
  <img src="./images/5.3-4.png" alt="图5.3-4" />
</p>

<p align="center"><em>图5.3-4 任务模板编辑器</em></p>

模板的主要字段如下：

| 字段 | 含义 |
| --- | --- |
| name | 模板名称（必填） |
| description | 模板描述 |
| content | 任务内容，可包含占位符 |
| content_aliases | 任务代号（备用表述） |
| difficulty | 难度（easy/medium/hard） |
| creator | 创建者 |
| category | 分类 |
| related_apis | 关联的服务器 API 及参数（同样支持占位符） |

常用占位符说明：

| 占位符 | 含义 |
| --- | --- |
| `{drone_id}` / `{drone_name}` | 单个无人机的 ID / 名称 |
| `{drone_1_id}`…`{drone_5_id}` | 多个无人机的编号 ID（`_name` 同理） |
| `{target_1_id}` / `{obstacle_1_id}` | 目标 / 障碍物的编号 ID（`_name` 同理） |
| `{random_altitude}`、`{random_speed}` 等 | 预定义随机数（同一任务内保持一致） |
| `{random:min:max}`、`{randint:min:max}` | 自定义范围的随机数（每次出现重新生成） |
| `{randxy}`、`{randxyz}`、`{randpos}` | 带避障的随机坐标组合 |
| `{mission_name}` 等自定义名称 | 生成任务时手动输入的自由文本 |

> 说明：编号占位符 `_id` 与 `_name` 建议成对使用，界面才能自动显示实体下拉框；同一编号在模板中多处出现时会复用同一实体。

### 5.3.2通过任务模板快速生成任务

在任务模板浏览器中选中目标模板后，双击或点击“Use Template”按钮，进入“Customize Template（自定义模板）”界面，按以下步骤生成任务：

<p align="center">
  <img src="./images/5.3-5.png" alt="图5.3-5" />
</p>

<p align="center"><em>图5.3-5 自定义模板（Customize Template）界面</em></p>

1. 填写任务名称（必填）。
2. 为无人机 / 目标 / 障碍物等实体占位符选择具体实体，也可选择 `[RANDOM]`（随机挑选）或 `[ORDERED]`（按列表顺序循环）。
3. 为其他自由文本占位符填写具体值；随机数类占位符无需输入。
4. 生成任务：
   - 点击“Create Task”生成单个任务。
   - 点击“Batch Create”批量生成多个任务，弹出对话框输入要生成的任务数量后点击“OK”即可。任务名称会自动编号，实体与随机值在每次生成时分别抽取。

<p align="center">
  <img src="./images/5.3-6.png" alt="图5.3-6" />
</p>

<p align="center"><em>图5.3-6 批量生成任务数量输入框</em></p>

生成任务时，系统会先完成占位符替换，再创建任务，因此每个任务的实体和随机参数都可以不同，非常适合快速构造大量测试任务。

# 6.AI智能体自动检查

自动检查功能会把会话中的任务交给 AI 智能体执行，等待智能体完成后再评估任务的完成情况。因此，在使用自动检查之前，必须先启动 `agent4drone` 智能体服务，否则自动检查界面无法将命令发送给智能体。

## 6.1 启动 AI 智能体服务（agent4drone）

AI 智能体位于 `agent4drone/` 目录，是一个基于大语言模型（LLM）的无人机控制程序。它有两种使用方式：

| 方式 | 启动命令 | 用途 |
| --- | --- | --- |
| **REST 服务** | `python agent_api_service.py` | 供自动检查界面（CheckUI）批量调用，默认端口 `18000` |
| **可视化对话界面** | `python main.py` | 人工输入自然语言指令，实时查看智能体执行过程 |

下面分别说明环境准备、服务启动，以及**在可视化界面中发送指令的完整流程**。

### 6.1.1 环境准备

**第一步，安装依赖（首次使用时执行）：**

```bash
cd agent4drone
pip install -r requirements.txt
```

**第二步，配置大模型。** 智能体通过 `agent4drone/llm_settings.json` 配置 LLM 服务商（如火山引擎 volcengine、Ollama 或 OpenAI 兼容接口）。在对应 Provider 的 `api_key` 字段填入密钥，或将密钥写入环境变量：

```bash
# 可选：通过环境变量传入 LLM 密钥
DEEPSEEK_API_KEY=sk-你的密钥
# 可选：UAV 仿真平台地址（默认 http://localhost:8000）
UAV_API_URL=http://127.0.0.1:8000
UAV_API_KEY=
```

**第三步，确保 UAV 仿真平台已启动。** 无论使用哪种智能体方式，都需要先运行 `MultiUAV-Plat.Server.exe`，并在 Controller 中 **Launch** 激活目标会话，使当前会话处于可用状态。

### 6.1.2 启动 REST 服务（供自动检查使用）

自动检查界面默认连接 `http://localhost:18000`，需要以服务模式启动：

```bash
cd agent4drone
python agent_api_service.py
```

服务启动后：

- 服务地址：`http://localhost:18000`
- 接口文档（Swagger）：`http://localhost:18000/docs`

> 若仅做手动对话测试，可跳过本小节，直接使用 6.1.3 的可视化界面。

### 6.1.3 在可视化界面发送指令

可视化界面（**UAV Control Interface**）适合人工调试：用自然语言描述任务，观察智能体如何理解、规划并控制无人机。

**（1）启动界面**

在项目目录下执行：

```bash
cd agent4drone
python main.py
```

启动后将打开 **UAV Control Interface** 窗口，界面自上而下分为四个区域：**LLM Provider**、**UAV Connection**、**Conversation / Intermediate Steps**、**Command 输入区**。

<p align="center">
  <img src="./images/6.1-1.png" alt="图6.1-1" />
</p>

<p align="center"><em>图6.1-1 UAV Control Interface 界面与指令输入</em></p>

**（2）配置 LLM Provider（大模型）**

在窗口顶部的 **LLM Provider** 区域完成模型配置：

| 控件 | 说明 |
| --- | --- |
| Provider | 选择 LLM 服务商（如 `volcengine (agent plan)`） |
| Model | 选择具体模型（如 `deepseek-v4-pro`） |
| Temperature | 控制输出随机性，建议保持较低值（如 `0.1`） |
| Verbose / Debug | 勾选后可在 **Intermediate Steps** 标签页查看更详细的推理与工具调用过程 |
| Configure | 打开配置对话框，编辑 `llm_settings.json` 中的 Provider 与 API Key |

配置完成后，界面会显示 `Agent initialized with model '...'`，表示大模型已就绪。

**（3）配置 UAV Connection（仿真平台连接）**

在 **UAV Connection** 区域设置与仿真平台的连接：

| 控件 | 说明 |
| --- | --- |
| UAV API Base URL | 仿真平台 API 地址，默认 `http://localhost:8000` |
| API Key (Optional) | UAV 平台密钥；AGENT 角色通常可留空 |
| Reload Agent | 修改配置或切换会话后，重新加载智能体 |
| Session Summary | 刷新当前会话摘要（任务进度、无人机状态等） |

点击 **Session Summary** 后，**Conversation** 区域会显示当前会话信息，例如：

- 会话名称（如 `Area Search Easy 1`）
- 任务类型与完成进度（如 `21%`）
- 各无人机 ID、状态（idle / hovering / flying）与剩余电量

发送指令前，应先确认目标无人机处于可执行状态（通常为 `idle` 或已在空中 `hovering`）。

**（4）输入并发送自然语言指令**

在窗口底部的 **Command** 文本框中，用自然语言描述要执行的操作。指令应包含：**哪架无人机**、**做什么动作**、**关键参数**（高度、坐标、目标名称等）。

示例指令：

```text
Drone Drone 3 should take off to 13 meters, then climb to 28 meters altitude and hover.
```

含义：让 Drone 3 先起飞到 13 米，再爬升到 28 米并悬停。

输入完成后，点击 **Send Command** 发送。发送后按钮会暂时不可用，防止重复提交；智能体处理期间可切换到 **Intermediate Steps** 标签页查看逐步推理过程。

**（5）查看执行结果**

指令执行完成后，**Conversation** 区域会显示智能体的回复，通常包括：

1. **执行步骤表**：将自然语言任务拆解为若干子步骤（如 Descend to 13m → Climb to 28m → Hover），并标注每步结果；
2. **最终状态**：无人机当前坐标 `(x, y, z)` 与剩余电量；
3. **完成标记**：末尾出现 `[TASK DONE]`，表示智能体认为该指令已执行完毕。

<p align="center">
  <img src="./images/6.1-2.png" alt="图6.1-2" />
</p>

<p align="center"><em>图6.1-2 指令执行完成后的对话记录</em></p>

窗口底部 **Command completed.** 复选框会被勾选，表示本轮指令处理结束。若结果不符合预期，可修改指令重新发送，或点击 **Reload Agent** 后再次尝试。

**（6）可视化界面发送指令流程小结**

```text
启动 Server + 在 Controller 中 Launch 会话
        ↓
cd agent4drone && python main.py
        ↓
配置 LLM Provider（Provider / Model / API Key）
        ↓
配置 UAV Connection（Base URL）→ 点击 Session Summary 确认会话与无人机状态
        ↓
在 Command 框输入自然语言指令 → 点击 Send Command
        ↓
在 Conversation / Intermediate Steps 中查看推理与执行过程
        ↓
确认 [TASK DONE] 与 Command completed → 继续下一条指令或关闭界面
```

> **提示：** 可视化界面（`main.py`）与 REST 服务（`agent_api_service.py`）共用同一套 `llm_settings.json` 配置，但运行方式不同。自动检查（6.2 节起）依赖 REST 服务；手动调试与演示推荐使用本节的可视化界面。

启动智能体服务或打开可视化界面后，即可进入 6.2 节的自动检查流程，或继续在界面中逐条测试任务指令。

## 6.2进入自动检查界面

在场景管理窗口，点击“CheckUI”按钮，进入自动检查界面。

<p align="center">
  <img src="./images/6.2-1.png" alt="图6.2-1" />
</p>

<p align="center"><em>图6.2-1 场景管理窗口的 CheckUI 按钮</em></p>

自动检查界面如图所示

<p align="center">
  <img src="./images/6.2-2.png" alt="图6.2-2" />
</p>

<p align="center"><em>图6.2-2 自动检查界面</em></p>

Session & Task Selection：会话和任务选择

| 名称 | 含义 |
| --- | --- |
| Refresh Sessions | 刷新会话 |
| Add Tasks in Sessions | 在会话中添加任务 |

Control & Progress：控制与进度

| 名称 | 含义 |
| --- | --- |
| Skip already checked tasks | 跳过已检查过的任务 |
| Skip passed tasks | 跳过已通过的任务 |
| Force land all drones before each task | 每个任务前强制无人机降落 |
| Force charge all drones before each task | 每个任务前强制无人机充电 |
| Random send one of the commands | 随机发送其中一条命令 |
| Reload session before each task | 每个任务前重新加载会话 |
| Start | 开始 |
| Pause | 暂停 |
| Clear | 清空 |
| Uncheck | 标记为未检查 |
| Export | 导出 |
| Import | 导入 |
| Agent Timeout | 智能体超时 |

## 6.3导入会话

在“Sessions”界面选中（可多选）想要检查的会话后，“Tasks”界面会显示该会话包含的任务。点击“Add Tasks in Sessions”将选中的会话加入检查队列

<p align="center">
  <img src="./images/6.3-1.png" alt="图6.3-1" />
</p>

<p align="center"><em>图6.3-1 导入会话</em></p>

## 6.4 开始检查

根据需求勾选检查方式，点击 **Start** 开始自动检查；点击 **Pause** 暂停检查；点击 **Clear** 清空检查列表；选择列表中的任务后点击 **Uncheck** 将其标记为未检查状态；点击 **Export / Import** 可导出或导入检查结果。

<p align="center">
  <img src="./images/6.4-1.png" alt="图6.4-1" />
</p>

<p align="center"><em>图6.4-1 开始自动检查</em></p>

### 6.4.1 批量检查的运行状态说明

点击 **Start** 后，界面进入批量检查运行状态。此时右侧 **Control & Progress** 区域会实时更新队列进度、任务结果与日志输出，便于观察智能体逐条执行任务的情况。

<p align="center">
  <img src="./images/6.4-2.png" alt="图6.4-2" />
</p>

<p align="center"><em>图6.4-2 批量检查运行中的界面状态</em></p>

界面各区域在运行过程中的含义如下。

**（1）左侧：Sessions 与 Tasks**

| 区域 | 运行时的表现 |
| --- | --- |
| **Sessions** | 显示已加入检查的会话列表；当前检查的会话（如 `Area Search Easy 1`）处于选中状态 |
| **Tasks** | 列出该会话下的全部任务及其 **Status**：已完成任务显示 **Done**，尚未执行的任务显示 **Pending** |

左侧 Tasks 表格反映的是会话内任务的原始状态；右侧 Task Queue 则反映本次批量检查的实时进度，二者可对照查看。

**（2）右上：Control & Progress 控制区**

运行过程中可使用以下按钮控制批量检查：

| 按钮 | 作用 |
| --- | --- |
| **Stop** | 停止当前批量检查 |
| **Pause / Resume** | 暂停或恢复检查；暂停后底部状态栏显示 `Paused`，**Resume** 按钮高亮可用 |
| **Remove** | 从队列中移除选中的任务 |
| **Clear** | 清空整个检查队列（运行结束后使用） |
| **Uncheck** | 将选中任务标记为未检查，以便重新执行 |
| **Export / Import** | 导出或导入检查结果 |
| **Compare** | 对比两次检查结果 |

常用选项说明：

- **Force land all drones before each task**：每条任务开始前强制所有无人机降落，保证任务独立执行；
- **Force charge all drones before each task**：每条任务开始前强制充电；
- **Agent Timeout (s)**：单条任务等待智能体的最长时间（示例中为 `500` 秒），超时则判定失败；
- **Wait before start (s)**：点击 Start 后、正式开始前的等待秒数。

**（3）Real-time Score：实时统计行**

统计行位于控制按钮下方，格式示例：

```text
Queue 2/20 | Tasks 2 passed / 0 failed | Checks 4/4 passed (100%) | Running 3/20
```

| 字段 | 含义 |
| --- | --- |
| `Queue 2/20` | 队列中已完成 2 条，共 20 条 |
| `Tasks 2 passed / 0 failed` | 已通过 2 条任务，失败 0 条 |
| `Checks 4/4 passed (100%)` | 验证检查点 4 个全部通过，通过率 100% |
| `Running 3/20` | 当前正在执行第 3 条任务 |

**（4）Task Queue：任务队列状态**

Task Queue 列表用图标与颜色区分每条任务的执行状态：

| 视觉表现 | 含义 |
| --- | --- |
| **浅蓝色高亮** + 统计后缀 `(Checked:2 Passed:2 Rate:100%)` | 该任务已检查完毕，并显示通过数与通过率 |
| **▶ 播放图标** | 当前正在执行的任务（示例中为 `Quick Checkpoint Visit 1`） |
| **⏳ 沙漏图标** | 排队等待中的后续任务 |

**（5）Log：执行日志**

Log 窗口按时间顺序输出每条任务的详细过程，典型日志包括：

```text
[3/20] 当前进度（第 3 条 / 共 20 条）
Agent output: All commands executed successfully   ← 智能体执行反馈
Check result: PASSED                               ← 任务验证结果
Landing all drones / Drones landed                 ← 任务前强制降落（若已勾选）
Charging all drones                                ← 任务前强制充电（若已勾选）
Submitting to agent                                ← 正在向智能体提交指令
Command: Drone Drone 3 takes off to 14 meters...  ← 发送给智能体的具体任务文本
```

通过 Log 可以追溯：智能体收到了什么指令、执行是否成功、平台验证是否通过。

**（6）底部状态栏**

窗口最底部的状态栏显示当前整体状态，例如：

- **Running**：批量检查正在进行；
- **Paused**：已暂停，点击 **Resume** 继续；
- **Stopped / Idle**：已停止或未开始。

**（7）批量检查运行流程小结**

```text
勾选检查选项 → 点击 Start
        ↓
Real-time Score 与 Task Queue 实时更新进度
        ↓
当前任务（▶）→ 提交 Command 给 Agent（18000 端口）→ 等待执行
        ↓
Log 输出 Agent output 与 Check result（PASSED / FAILED）
        ↓
任务完成后队列条目变蓝，自动进入下一条（⏳ → ▶）
        ↓
全部完成后 Export 导出 JSON 报告
```

> **提示：** 批量检查依赖 6.1.2 节启动的 REST 服务（`agent_api_service.py`）。若 Log 中出现 Agent 连接失败，请先确认 `http://localhost:18000/health` 返回正常，且 UAV Server 与目标会话均已 Launch 激活。

# 7.3D 可视化查看器

3D 可视化查看器是一个基于 Three.js 的独立 Web 应用，位于 `view3d/` 目录。它可以读取平台的当前会话数据，将其渲染为三维交互场景，支持无人机、目标、障碍物、高度线、轨迹、覆盖区等要素的立体展示。

## 7.3.1 环境要求与界面概览

**环境要求：**

- **Node.js 18** 或更高版本
- **UAV API 服务器**（可选）：启动后可显示实时会话数据；不启动时自动进入演示模式

启动成功后，浏览器中将打开 **MultiUAV-Plat 3D Viewer**。默认以 **Fit（全景）** 视角展示当前会话，可一览无人机、目标、障碍物与坐标轴等全部要素；此时尚未进入漫游模式，适合作为 3D 查看器的整体认识。

<p align="center">
  <img src="./images/7.1-1.png" alt="图7.1-1" />
</p>

<p align="center"><em>图7.1-1 3D 可视化查看器默认界面</em></p>

图中可见：顶部工具栏提供 Fit / Top / Follow / Roam 等视角切换（默认选中 **Fit**）；中央为带网格的 3D 场景，展示多架无人机（四旋翼模型）、蓝色目标区域与各色柱状障碍物；左下角为小地图，底部显示 **Server Connected** 表示已连接仿真平台。

## 7.3.2 启动 3D 查看器

启动 3D 查看器前，确保已进入 `view3d/` 目录并安装依赖：

```bash
cd view3d
npm install
```

安装成功后，执行以下命令启动 dev server：

```bash
npm run dev
```

如果使用 Windows PowerShell，也可以使用以下方式启动：

```powershell
$env:VITE_VIEWER_DATA_SOURCE="backend"; npx vite --host 127.0.0.1 --port 5173
```

启动后，在浏览器中打开 **http://127.0.0.1:5173/**，即可看到如 7.1 节图7.1-1 所示的 3D 可视化界面。

## 7.3.3 界面说明

3D 查看器界面自上而下分为 **顶部工具栏**、**中央 3D 场景区** 与 **底部状态栏** 三部分。

**（1）顶部工具栏**

| 控件 | 说明 |
| --- | --- |
| 标题栏 | 显示 `MultiUAV-Plat 3D Viewer` 及当前会话摘要（会话名、无人机/目标/障碍物数量） |
| **Fit** | 全景显示，自动调整相机以容纳整个场景（见 7.1 节图7.1-1） |
| **Top** | 俯视图，从正上方观察任务区域 |
| **Follow** | 跟随模式，相机锁定并跟踪选中的无人机 |
| **Roam** | 漫游模式，沿选中无人机的历史轨迹第一人称飞行（详见 7.7 节） |
| **Continuous Surface** | 地面渲染方式下拉选项 |
| **PNG / Capture** | 导出当前画面为图片 |
| **CheatSheet / Info** | 快捷键说明与帮助信息 |
| **中文** | 界面语言切换 |

**（2）中央 3D 场景区**

以三维方式展示当前会话中的所有要素：

- **无人机**：四旋翼三维模型，附带编号标签、高度线与当前状态
- **目标**：地面上的蓝色区域（圆形、矩形、多边形等），表示任务目标
- **障碍物**：圆柱、长方体等立体几何体（灰色、橙色、蓝色等），表示不可飞越区域
- **坐标轴**：场景原点处的 X（红）/ Y（绿）/ Z（蓝）轴，标示空间方向
- **轨迹线**：绿色线条，记录无人机的历史飞行路径
- **覆盖区**：任务覆盖范围的可视化着色区域

**（3）底部状态栏**

| 区域 | 说明 |
| --- | --- |
| **小地图**（左下） | 2D 俯视图概览，绿点表示无人机，蓝/红色块表示目标与障碍物；点击可跳转视角 |
| **Live / Trail / Show Labels** | 实时刷新开关、轨迹显示长度、标签显示开关 |
| **Size- / 标签 / Size+** | 调整对象标签字号 |
| **Server Connected** | 绿色表示已成功连接 UAV API 服务器，数据实时同步 |
| **Task: xx%** | 当前会话任务完成进度（连接后端时显示） |
| **Click: (x, y, z)** | 鼠标点击处的三维坐标 |
| **方向键控件**（右下） | 手动平移/旋转视角 |
| **缩放滑块**（右下） | 纵向滑块快速调节视距；旁侧显示当前 Scale 百分比 |

以下为 2D 仿真系统界面的对比参考：

<p align="center">
  <img src="./images/7-2.png" alt="图7-2" />
</p>

<p align="center"><em>图7-2 2D 仿真系统界面（对比）</em></p>

## 7.3.4 基本操作

| 操作 | 说明 |
| --- | --- |
| **左键单击** | 选中无人机 / 目标 / 障碍物，查看详细信息 |
| **右键单击** | 取消当前选中 |
| **鼠标拖拽** | 旋转视角 |
| **滚轮** | 缩放（40% ~ 500%） |
| **Fit / Top / Follow / Roam** | 顶部工具栏视角切换：全景 / 俯视 / 跟随 / 漫游 |
| **Info 按钮** | 打开选中对象的详情抽屉 |
| **Show Labels** | 显示 / 隐藏对象名称标签 |
| **Size- / Size+** | 调整标签字号 |
| **Trail** | 切换路径历史记录的显示长度 |
| **缩放滑块**（右下） | 纵向滑块，快速缩放 |
| **PNG / Capture** | 将当前画面导出为图片 |

## 7.3.5键盘快捷键

| 快捷键 | 功能 |
| --- | --- |
| `Esc` | 取消选中（漫游模式下退出漫游） |
| `方向键` | 平移视角 |
| `1` | 全景显示 |
| `2` | 俯视图 |
| `3` | 跟随选中无人机 |
| `4` | 漫游模式（沿选中无人机的飞行轨迹飞行） |
| `.`（句号） | 漫游加速 |
| `,`（逗号） | 漫游减速 |
| `+` / `-` | 放大 / 缩小 |
| `[` / `]` | 缩小 / 放大标签 |
| `R` | 重置视角 |
| `L` | 显示/隐藏标签 |
| `M` | 显示/隐藏小地图 |
| `I` | 显示/隐藏信息面板 |

## 7.3.6与后端联动的场景可视化

将 3D 查看器与 UAV API 服务器配合使用时，可以实时呈现当前会话内容：

1. **启动 UAV API 服务器**（`MultiUAV-Plat.Server.exe`），并打开一个包含无人机、目标等要素的场景。
2. **启动 3D 查看器**，Vite 会自动从 API 获取 `GET /sessions/current/data` 的会话数据。
3. **控制无人机**后，返回 3D 查看器刷新场景，可观察无人机位置、轨迹和状态的实时变化。

如果 UAV API 服务器未运行，查看器会自动切换为**演示模式（Demo Mission）**，展示一组预设的模拟场景，方便用户在无后端时了解 3D 查看器的功能。此时界面左上角会显示“未连接 / Failed to fetch”提示。

<p align="center">
  <img src="./images/7.6-1.png" alt="图7.6-1" />
</p>

<p align="center"><em>图7.6-1 演示模式（未连接后端）下的 3D 场景</em></p>

## 7.3.7 漫游模式

漫游模式是一种**第一人称路径飞行**视角：相机沿选中无人机的历史飞行轨迹自动前进，模拟从无人机视角观察任务场景。图7.7-1 展示了 `Area Search Easy 1` 会话中进入漫游模式后的效果。

<p align="center">
  <img src="./images/7.7-1.png" alt="图7.7-1" />
</p>

<p align="center"><em>图7.7-1 漫游模式（Roam 视角，Area Search Easy 1）</em></p>

图中可见：相机贴近 **Drone 3** 的四旋翼模型，前方半透明蓝色包围框标示当前跟踪的无人机；地面绿色线条为剩余飞行路径；远处另一架无人机以黄色高亮圈标记；底部状态栏显示 `Switched to Roam view` 与 `Task: 23%`。

### 进入漫游模式

1. **在 3D 场景中选中一架无人机**（左键单击，或 Tab 键切换选择）。
2. **点击顶部工具栏的 Roam 按钮**，或按快捷键 **`4`**。
3. 相机自动切换到该无人机历史路径的起点，并沿路径开始飞行。

> 注意：若选中无人机没有足够的历史轨迹（路径点少于 2 个），则无法进入漫游模式。需先在 2D 仿真界面或智能体控制下让无人机飞行一段距离，产生路径记录后再漫游。

### 漫游过程中的视觉元素

| 元素 | 说明 |
| --- | --- |
| **绿色路径线** | 显示无人机剩余未飞行的路径轨迹，随漫游进度逐渐缩短 |
| **半透明无人机模型** | 位于相机前方的四旋翼模型，指示当前沿路径的前进方向 |
| **黄色高亮圈** | 标记场景中其他无人机或关注对象的位置 |
| **底部 Roam 按钮高亮** | 顶部工具栏 **Roam** 呈选中状态，状态栏显示 `Switched to Roam view` |

### 操作说明

| 操作 | 说明 |
| --- | --- |
| **按 `.`（句号）** | 加速，速度倍率 ×1.25 |
| **按 `,`（逗号）** | 减速，速度倍率 ÷1.25 |
| **滚轮** | 调整相机与路径点的距离（缩放） |
| **按 `Esc`** | 退出漫游模式，恢复为 Fit 全景显示 |
| **按 `4` / 再次点击 Roam** | 退出漫游模式 |
| **切换选中无人机** | 自动退出漫游模式 |

漫游速度由无人机的最大速度属性决定，可在 **25% ~ 400%** 范围内调节。界面状态栏会实时显示当前漫游速度百分比，例如 `漫游速度: 100%`。

### 路径转弯平滑

漫游模式在路径拐角处会自动平滑过渡：相机在接近转弯点时，前进方向在上一段与下一段路径方向之间逐渐过渡。转弯距离与当前速度成正比（速度越快，转弯开始越早），保证飞行视角流畅自然。

### 到达终点

相机沿路径飞行至终点后，漫游自动结束并保持终点位置。按 `Esc` 或 `4` 键可退出漫游，恢复自由视角（Fit / Top / Follow）。
