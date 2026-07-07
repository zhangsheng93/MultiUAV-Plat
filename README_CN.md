# MultiUAV-Plat 🚁

**面向大语言模型的多无人机协同任务规划平台、基准与工作流框架**

🌐 语言： [English](README.md) | **中文**

[📄 论文](https://arxiv.org/abs/2606.31073) | [🏠 项目主页](https://zhangsheng93.github.io/multiuavweb/) | [💻 代码](https://github.com/zhangsheng93/MultiUAV-Plat) | [📦 测评基准](https://github.com/zhangsheng93/MultiUAV-Plat/releases) | [📚 教程](tutorial/Tutorial_zh.md) | [⬇️ Releases](https://github.com/zhangsheng93/MultiUAV-Plat/releases) | [📝 引用](#-引用)

MultiUAV-Plat 是一个轻量级开源仿真平台与测评基准，用于研究 LLM agent 如何在受限 API 和局部观测条件下，对多无人机任务进行规划、执行、观察与验证。

| 任务会话 | 自然语言任务 | 验证检查 |
| --- | --- | --- |
| 75 | 1500 | 9396 |

<table>
  <tr>
    <th width="50%">2D overview view</th>
    <th width="50%">3D visualization view</th>
  </tr>
  <tr>
    <td width="50%"><img src="assets/2d-view.png" alt="2D overview view" width="100%"></td>
    <td width="50%"><img src="assets/3d-view.png" alt="3D visualization view" width="100%"></td>
  </tr>
</table>

## ✨ 概览

大语言模型为高级机器人任务规划提供了有前景的交互接口，但在多无人机协同场景中，系统化评估仍然很困难。现有 UAV 仿真器通常更关注动力学、感知或底层控制，而 LLM-agent 评估需要面向任务层的接口，包括受限 API、基于角色的信息访问、局部观测、隐藏验证逻辑和闭环执行。

论文资源、可视化介绍、下载入口和 leaderboard 更新可访问 [MultiUAV-Plat 项目主页](https://zhangsheng93.github.io/multiuavweb/)。

MultiUAV-Plat 主要包含三个研究贡献：

- **MultiUAV-Plat platform**：RESTful 多无人机仿真环境，支持 agent-facing observations、角色权限、会话管理和可选 2D/3D 可视化。
- **MultiUAV-Plat Benchmark**：用于可复现实验的可执行多无人机任务基准，包含自然语言任务与隐藏验证检查。
- **MultiUAV-Agent Workflow**：面向多无人机规划、执行、验证与重规划的任务特定工作流，本仓库中以 Agent4Drone 作为参考实现。

本仓库还包含 **MultiUAV-Plat Web 3D Viewer**，这是一个独立的 Three.js/Vite 任务三维可视化查看器，由 [@Damonhellokitty](https://github.com/Damonhellokitty) 贡献。当前版本默认读取后端实时数据，在后端不可用时回退到本地 demo mission，支持中英文界面切换，并新增用于检查 UAV 轨迹的跟随/漫游相机模式。

## 🧭 主要特性

- 🛰️ 面向任务级 UAV 控制、感知、会话管理和验证的 RESTful APIs。
- 🔐 基于角色的访问控制与 agent-facing observations，避免 agent 直接访问特权仿真状态。
- ✅ 隐藏任务验证器，用于可复现的闭环测评。
- 🗺️ 支持 2D 和 3D 可视化：2D 视图适合快速查看任务全局状态和编辑场景，3D 视图适合沉浸式检查 UAV 轨迹、高度、覆盖区域、目标、障碍物、小地图上下文、跟随/漫游相机和截图导出。
- 🎛️ GUI controller 支持会话创建、编辑、导入/导出和监控。
- 🤖 MultiUAV-Agent Workflow 覆盖 observation、memory、task understanding、planning、execution、verification 和 replanning，Agent4Drone 是其参考实现。
- 📊 Benchmark 覆盖 Target Assignment、Area Search、Area Assignment and Patrol 三类场景。

## 📁 仓库结构

```text
server/       主仿真服务端与 REST API
controller/   GUI/session controller
agent4drone/  基于 LLM 的 UAV agent 框架与 agent API service
benchmark/    测评基准会话和场景资源
view3d/       基于 Web 的 3D 任务可视化查看器
tutorial/     带截图的分步使用教程
```

每个组件都包含更详细的独立说明文档。如果需要按截图逐步了解 server/controller 启动、场景编辑、任务管理、AI 智能体自动检查和 3D 查看器使用流程，请查看[中文教程](tutorial/Tutorial_zh.md)或[英文教程](tutorial/tutorial_en.md)。

## ⬇️ Releases

如果你只是希望直接运行平台，可以从 [GitHub Releases](https://github.com/zhangsheng93/MultiUAV-Plat/releases) 下载预编译二进制包，无需安装源码依赖。Release 包中包含独立的仿真服务端可执行文件、GUI controller 可执行文件，以及配套文档和会话资源。

请先启动 server，再启动 controller。

| 系统 | Release 包 | 运行方式 |
| --- | --- | --- |
| Windows | `MultiUAV-Plat-v0.40_Windows.zip` | 双击 `MultiUAV-Plat.Server.v0.40.exe`，再双击 `MultiUAV-Plat.Controller.v0.40.exe`。 |
| macOS | `MultiUAV-Plat-v0.40_Mac.zip` | 可以双击可执行文件，也可以在终端中运行 `./MultiUAV-Plat.Server.v0.40` 和 `./MultiUAV-Plat.Controller.v0.40`。 |
| Linux | Linux release package | 在 shell 中运行 server 和 controller 可执行文件，同样按照先 server、后 controller 的顺序启动。 |

macOS/Linux 通过终端运行时，可能需要先添加可执行权限：

```bash
chmod +x MultiUAV-Plat.Server.v0.40 MultiUAV-Plat.Controller.v0.40
./MultiUAV-Plat.Server.v0.40
./MultiUAV-Plat.Controller.v0.40
```

下面的源码 Quick Start 更适合开发、定制和复现实验。

## 🚀 快速开始（从源码启动）

### 1. 启动仿真服务端

完整的服务端配置、UI 选项、API 分组和故障排查说明见 [server README](server/README.md)。

```bash
cd server
pip install -r requirements.txt
python main.py
```

默认端点：

- Server API: `http://127.0.0.1:8000`
- Server docs: `http://127.0.0.1:8000/docs`

常用服务端文档：

- [API Documentation](server/docs/API_DOCUMENTATION.md)：完整端点说明和示例。
- [API Reference](server/docs/API_REFERENCE.md)：更细粒度的路由级参考。
- [Authentication](server/docs/AUTHENTICATION.md)：角色、API key 用法与权限模型。
- [Agent API Guide](server/docs/API_AGENT_GUIDE.md)：面向 agent 的使用模式和约束。
- [Task Template Edit Guide](server/docs/TASK_TEMPLATE_EDIT_GUIDE.md)：任务/会话模板编辑指南。
- [Changelog](server/docs/CHANGELOG.md)：API 与平台更新记录。

### 2. 启动 GUI controller

Session manager 工作流、GUI tabs、导入/导出行为和 controller 故障排查见 [controller README](controller/README.md)。

```bash
cd controller
pip install -r requirements.txt
python main.py
```

controller 会连接本地 server，并提供会话管理、场景编辑、导入/导出和监控工具。

### 3. 启动 Web 3D viewer（可选）

请先启动仿真 server。Viewer 的安装、backend mode、demo mode、配置、控制方式、可选开发工具、构建和测试说明见 [view3d README](view3d/README.md)。

```bash
cd view3d
npm install
npm run dev
```

默认访问地址：

- Web 3D Viewer: `http://127.0.0.1:5173`

`npm run dev` 会通过 `GET /sessions/current/data` 从本地 server 读取实时任务数据。如果只想在无 server 的情况下查看前端 demo，可以使用：

```bash
npm run dev:demo
```

### 4. 运行 Agent4Drone

Agent4Drone 会调用外部 LLM backend，因此启动前需要提供你自己的大模型服务 API key。你可以在本地编辑 `llm_settings.json`，也可以导出 `OPENAI_API_KEY` 或 `LLM_API_KEY` 等环境变量。

```bash
cd agent4drone
cp llm_settings.example.json llm_settings.json
# 在 llm_settings.json 中填入自己的 LLM API key，或导出 OPENAI_API_KEY / LLM_API_KEY。
```

Agent4Drone 支持两种运行模式：

**方式 A：交互式 agent UI**

当你希望通过本地交互界面运行 Agent4Drone 时，使用此模式。

```bash
python main.py
```

**方式 B：后台 agent API service**

当你希望其他应用、脚本或 controller 通过 HTTP 调用 Agent4Drone 时，使用此模式。

```bash
python agent_api_service.py
```

默认服务端点：

- Agent API: `http://localhost:18000`
- Agent docs: `http://localhost:18000/docs`

在 service 模式下，agent command 可以同步提交，也可以通过异步 job API 提交。更多说明见 `agent4drone/README_SERVICE.md` 和 `agent4drone/README_API.md`。

## 📦 测评基准

MultiUAV-Plat Benchmark 用于评估 agent 是否能理解自然语言目标、选择 UAV、收集缺失信息、执行有效 API 动作、协调多架无人机，并满足隐藏任务级检查。

Benchmark 包含：

- 75 个任务会话
- 1500 个自然语言任务
- 9396 个验证检查
- 3 类场景：Target Assignment、Area Search、Area Assignment and Patrol
- 5 个难度等级：Easy、Intermediate、Moderate、Hard、Extreme

Benchmark session 将结构化 JSON 场景数据与可视化资源配对。Agent 应通过平台 API 交互完成任务，而不是直接访问特权仿真状态或隐藏验证器定义。

## 🏆 实验结果

以下排行榜结果基于完整测评基准计算，包含 75 个任务会话、1500 个自然语言任务和 9396 个验证检查。**后端 LLM** 列表示该次 agent 运行所使用的大模型。

| 方法 | 后端 LLM | 通过任务数 | 完全失败任务数 | 任务通过率 | 平均检查通过率 | 全局检查通过率 | 完全失败率 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Agent4Drone | DeepSeek V4 Pro | **1054 / 1500** | **93 / 1500** | **70.27%** | **84.86%** | **82.82%** | **6.20%** |
| Agent4Drone | DeepSeek V4 Flash | 1044 / 1500 | 102 / 1500 | 69.60% | 83.40% | 80.76% | 6.80% |
| ReAct | DeepSeek V4 Pro | 954 / 1500 | 118 / 1500 | 63.60% | 79.72% | 73.09% | 7.87% |
| Agent4Drone | doubao-2-pro | 869 / 1500 | 194 / 1500 | 57.93% | 74.58% | 71.96% | 12.93% |
| ReAct | qwen3.5 | 629 / 1500 | 333 / 1500 | 41.93% | 59.42% | 56.29% | 22.20% |
| ReAct | doubao-2-pro | 459 / 1500 | 486 / 1500 | 30.60% | 47.91% | 43.15% | 32.40% |

在配对的 doubao-2-pro 对比中，Agent4Drone 相比 ReAct baseline 的任务通过率提升 **+27.33 个百分点**，并将完全失败率从 **32.40%** 降低到 **12.93%**。在更强的 DeepSeek 后端模型下，Agent4Drone 达到 **70.27%** 的任务通过率和 **82.82%** 的全局检查通过率。更详细的场景级和难度级分析见论文与项目材料。

## 📝 引用

如果你在研究中使用 MultiUAV-Plat、MultiUAV-Plat Benchmark 或 Agent4Drone，请引用以下 arXiv 预印本条目。

```bibtex
@article{zhang2026multiuavplat,
  title         = {MultiUAV-Plat: An LLM-Oriented Platform, Benchmark and Framework for Multi-UAV Collaborative Task Planning},
  author        = {Zhang, Sheng and Li, Qinglin and Zang, Yuechao and Huang, Xueqin and Fu, Yijia and Zhu, Cheng},
  journal       = {arXiv preprint arXiv:2606.31073},
  year          = {2026},
  eprint        = {2606.31073},
  archivePrefix = {arXiv},
  url           = {https://arxiv.org/abs/2606.31073}
}
```

## 📜 许可证与致谢

本项目遵循 [LICENSE](LICENSE) 中的开源许可证。
