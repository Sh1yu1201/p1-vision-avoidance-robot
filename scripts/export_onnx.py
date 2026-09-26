#!/usr/bin/env python3
"""导出检测模型为 ONNX，并用 onnxsim 固化输入 shape。

用法：
    python scripts/export_onnx.py --weights yolov8n.pt --imgsz 640 --out models/yolov8n.onnx

说明：
    NOE Compiler 量化前需要固定 shape 的 ONNX，动态 batch / 动态尺寸会显著增加
    量化失败的概率，因此这里统一做一次 onnxsim 化简。
"""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导出 ONNX 并固化输入 shape")
    parser.add_argument("--weights", default="yolov8n.pt", help="PyTorch 权重或模型名")
    parser.add_argument("--imgsz", type=int, default=640, help="输入分辨率")
    parser.add_argument("--opset", type=int, default=12, help="ONNX opset")
    parser.add_argument("--out", default="models/model.onnx", help="输出 ONNX 路径")
    parser.add_argument("--no-simplify", action="store_true", help="跳过 onnxsim 化简")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from ultralytics import YOLO
    except ImportError:
        print("需要先安装依赖：pip install -r requirements.txt")
        return 1

    model = YOLO(args.weights)
    exported = model.export(
        format="onnx",
        imgsz=args.imgsz,
        opset=args.opset,
        simplify=False,  # 统一交给下面的 onnxsim 处理
        dynamic=False,
        half=False,
    )
    exported_path = Path(exported)
    print(f"ONNX 已导出：{exported_path}")

    if args.no_simplify:
        exported_path.replace(out_path)
        print(f"已跳过化简，输出：{out_path}")
        return 0

    try:
        import onnx
        from onnxsim import simplify
    except ImportError:
        print("未安装 onnx / onnxsim，直接使用原始 ONNX 输出")
        exported_path.replace(out_path)
        return 0

    model_proto = onnx.load(str(exported_path))
    simplified, ok = simplify(model_proto)
    if not ok:
        print("onnxsim 化简失败，保留原始 ONNX")
        simplified = model_proto
    onnx.save(simplified, str(out_path))
    print(f"化简完成，输出：{out_path}")
    print("下一步：bash scripts/quantize_cix.sh -c configs/build.cfg -m " + str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
