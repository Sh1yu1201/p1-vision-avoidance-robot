# P1 端侧模型部署流程

本文件说明如何把 YOLO 检测模型与 Depth Anything V2 深度模型部署到此芯 CIX P1 的 NPU 上运行。

## 1. 总体流程

```
训练 / 下载权重 (PyTorch)
        │  export_onnx.py
        ▼
ONNX 模型 ── onnxsim 固化输入 shape
        │  NOE Compiler (CixBuilder) + 校准数据
        ▼
INT8 量化模型 (.cix)
        │  拷贝到 P1 板端
        ▼
NOE Runtime 推理（npu_load_graph / npu_create_job）
```

## 2. 开发机侧（x86 Linux）

1. 安装工具链：`pip install CixBuilder`（NOE Compiler 的 Python wheel）。
2. 导出并固化 shape：

   ```bash
   python scripts/export_onnx.py --weights yolov8n.pt --imgsz 640 --out models/yolov8n.onnx
   ```

3. 准备校准数据：从清扫场景实拍图中抽取 100 至 300 张，覆盖拖鞋、电源线、袜子、家具腿、地面杂物。
4. 配置并量化编译：

   ```bash
   bash scripts/quantize_cix.sh -c configs/build.cfg -m models/yolov8n.onnx -o models/yolov8n.cix
   ```

   量化精度建议 INT8；对深度模型如出现明显精度损失，可改用 INT16。

## 3. P1 板端侧（Arm64）

1. 安装驱动与运行时：

   ```bash
   sudo dpkg -i cix-npu-driver_*.deb
   sudo dpkg -i cix-noe-umd_*.deb
   ```

2. 验证设备节点与运行时版本（具体命令以厂商 SDK 文档为准）。
3. 运行推理：

   ```bash
   python scripts/inference_npu.py --model models/yolov8n.cix --source 0 --show
   ```

## 4. 加速起步：官方预编译模型

此芯 AI Model Hub 提供 140 余个预编译模型（含 YOLO、深度估计、OpenPose、Qwen 等），含校准数据与推理脚本。
初赛阶段可先用预编译 `.cix` 跑通链路，再替换为自训练的模型。

## 5. 常见问题

- **模型加载失败**：确认 `.cix` 与板端 Runtime 版本匹配，重新编译一次。
- **推理结果明显偏移**：检查输入预处理（letterbox、归一化、通道顺序）与训练时是否一致。
- **NPU 精度不达标**：改用官方 Model Hub 中同类预编译模型做对照，或把该模型退回 CPU（ONNX Runtime）作为兜底。
- **深度值尺度不确定**：使用 LiDAR 稀疏点做尺度对齐，或切换 Depth Pro 等度量深度模型。
