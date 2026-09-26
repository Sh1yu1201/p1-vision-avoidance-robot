# 基于此芯 CIX P1 的扫地机器人视觉避障系统

2026 此芯科技 Agentic AI 开发者大赛 · 赛道一：端侧本地推理智能体

在 2D LiDAR 基础避障之上，用"单目视觉 + 端侧 AI"识别激光雷达难以发现的低矮、细小、软性障碍物
（拖鞋、电源线、袜子、宠物粪便、门槛、玩具等），并做出语义级避障决策（绕行 / 停止等待 / 上报）。
全部模型在此芯 P1 板端本地推理，无云依赖。

## 1. 关键特性

- **视觉走 NPU**：YOLO 目标检测 + Depth Anything V2 单目深度估计，逐帧处理摄像头流。已在 P1 NPU 上跑通。
- **大模型走 GPU**：MiniCPM-o 2.6 端侧 VLM 做障碍物语义判定，事件触发而非逐帧；经 llama.cpp Vulkan 后端运行。
- **LiDAR 兜底**：底层 2D LiDAR 保持确定性硬避障，深度图转 2.5D 高度图后注入 Nav2 costmap，AI 异常时机器人仍可安全运行。
- **纯视觉可独立演示**：一块 P1 板加一个 USB 摄像头即可拍出"障碍物检测 + 距离 + 语义决策"的 Demo，不依赖底盘硬件。

## 2. 硬件平台

| 模块 | 规格 | 在项目中的用途 |
| --- | --- | --- |
| CPU | 12 核 Armv9.2-A 三丛集（4+4+4），12MB L3 | SLAM 建图、Nav2 导航、传感器驱动、任务调度 |
| GPU | Arm Immortalis-G720 MC10（Vulkan 1.3） | llama.cpp Vulkan 后端运行 VLM |
| NPU | 约 30 TOPS，周易三核 | YOLO 检测、单目深度估计、语义分割 |
| 内存 | LPDDR5(x)，约 100 GB/s | 检测 + 深度 + VLM 多模型并行驻留 |
| 外设 | USB 摄像头（UVC）、2D LiDAR、底盘驱动 MCU | 感知输入与运动执行 |

异构算力合计 45 TOPS。

## 3. 目录结构

```
.
├── docs/                  设计与部署文档
│   ├── 01-deployment.md   P1 NPU 模型部署流程（ONNX → INT8 → .cix → 板端推理）
│   ├── 02-architecture.md 系统架构与避障数据流水线
│   └── 03-hardware.md     硬件清单与接口连接
├── scripts/               可执行脚本
│   ├── export_onnx.py     模型导出 ONNX 并用 onnxsim 固化 shape
│   ├── quantize_cix.sh    NOE Compiler 量化与编译为 .cix 的命令模板
│   └── inference_npu.py   板端 NOE Runtime 推理：检测框 + 距离 + 决策输出
├── configs/               配置模板
│   ├── build.cfg          量化编译配置（校准数据、量化精度）
│   └── nav2_costmap.yaml  深度高度图注入 costmap 的参数骨架
└── ros2_ws/src/           ROS 2 功能包放置目录
```

## 4. 快速开始

```bash
git clone https://github.com/<你的用户名>/p1-vision-avoidance-robot.git
cd p1-vision-avoidance-robot
pip install -r requirements.txt

# 开发机：导出 ONNX 并固化 shape
python scripts/export_onnx.py --weights yolov8n.pt --out models/yolov8n.onnx

# 开发机：量化并编译为板端可执行的 .cix
bash scripts/quantize_cix.sh -c configs/build.cfg -m models/yolov8n.onnx

# P1 板端：运行推理
python scripts/inference_npu.py --model models/yolov8n.cix --source 0 --show
```

完整流程、驱动安装与常见问题见 `docs/01-deployment.md`。

## 5. 项目状态

| 模块 | 状态 |
| --- | --- |
| YOLOv8 / yolov8l_seg 在 P1 NPU 上推理 | 已验证 |
| Depth Anything V2 在 P1 NPU 上推理（Python / C++） | 已验证 |
| MiniCPM-o 2.6 经 llama.cpp Vulkan 在 P1 上运行 | 已验证（图像理解约 7.7 tokens/s） |
| 本仓库的部署脚本与配置封装 | 整理中 |
| 深度图 → 2.5D 高度图 → Nav2 costmap 融合 | 开发中 |
| 底盘联调与实机避障视频 | 计划中 |

## 6. 模型与开源依赖

| 项目 | 用途 | 协议 | 仓库 |
| --- | --- | --- | --- |
| Ultralytics YOLO | 障碍物检测与分割 | AGPL-3.0 | github.com/ultralytics/ultralytics |
| Depth Anything V2 | 单目深度估计 | Apache-2.0 | github.com/DepthAnything/Depth-Anything-V2 |
| MiniCPM-o | 端侧 VLM 语义决策 | Apache-2.0 | github.com/OpenBMB/MiniCPM-o |
| llama.cpp | GPU Vulkan 运行量化 VLM | MIT | github.com/ggerganov/llama.cpp |
| Nav2 | 路径规划与代价地图 | Apache-2.0 | github.com/ros-navigation/navigation2 |
| slam_toolbox | 2D 激光 SLAM 建图 | LGPL-2.1 | github.com/SteveMacenski/slam_toolbox |
| OOMWOO | 扫地机底盘固件与仿真 | Apache-2.0 | github.com/makerspet/oomwoo |

注意：Ultralytics 为 AGPL-3.0 协议，模型权重另有单独许可，商用发布前需单独评估。本仓库不包含第三方模型权重。

## 7. 许可证

本项目以 Apache-2.0 协议开源，二次分发时请保留上游项目的版权声明。
