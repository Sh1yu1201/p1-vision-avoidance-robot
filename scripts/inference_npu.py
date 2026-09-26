#!/usr/bin/env python3
"""P1 板端视觉避障推理：检测框 + 距离 + 语义决策。

用法：
    python scripts/inference_npu.py --model models/yolov8n.cix --source 0 --show

设计说明：
    脚本把"推理后端"与"业务逻辑"分开：
      * NPUBackend   —— 走此芯 NOE Runtime（板端，需安装 cix-npu-driver / cix-noe-umd）
      * OnnxBackend  —— 走 ONNX Runtime CPU（开发机对照与兜底）
    在没有板端运行时的机器上，会自动退回 OnnxBackend，便于先在开发机验证前后处理逻辑。

    NOE Runtime 的具体 API（noe_load_graph / noe_create_job 等）以厂商 SDK 文档为准，
    这里只保留调用点与 TODO，不做未经验证的假设。
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Detection:
    label: str
    confidence: float
    box: tuple[float, float, float, float]


class OnnxBackend:
    """ONNX Runtime CPU 后端：开发机对照与 NPU 异常时的兜底路径。"""

    name = "onnxruntime-cpu"

    def __init__(self, model_path: str, imgsz: int = 640) -> None:
        import onnxruntime as ort

        self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.imgsz = imgsz

    def infer(self, frame):
        import cv2
        import numpy as np

        img = cv2.resize(frame, (self.imgsz, self.imgsz))
        blob = img[:, :, ::-1].transpose(2, 0, 1).astype("float32") / 255.0
        outputs = self.session.run(None, {self.input_name: np.expand_dims(blob, 0)})
        return outputs[0]


class NPUBackend:
    """此芯 P1 NPU 后端（NOE Runtime）。"""

    name = "cix-noe-npu"

    def __init__(self, model_path: str) -> None:
        # TODO: 按厂商 SDK 文档替换为真实的加载流程，例如：
        #   import noe_runtime as noe
        #   self.graph = noe.noe_load_graph(model_path)
        #   self.job = noe.noe_create_job(self.graph)
        raise RuntimeError(
            "NOE Runtime 调用点尚未接入：请依据此芯 SDK 文档补全 noe_load_graph / noe_create_job 的用法"
        )

    def infer(self, frame):
        raise NotImplementedError


def build_backend(model_path: str, prefer_npu: bool):
    if prefer_npu and model_path.endswith(".cix"):
        try:
            return NPUBackend(model_path)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] NPU 后端不可用（{exc}），退回 ONNX Runtime CPU")
    return OnnxBackend(model_path.replace(".cix", ".onnx"))


def postprocess(outputs, conf_threshold: float = 0.5) -> list[Detection]:
    """把网络输出解析为检测结果。

    TODO: 按实际模型的输出布局补全（YOLOv8 为 (1, 4+nc, 8400)，
          需要做置信度筛选、NMS 与坐标还原 letterbox 偏移）。
    """
    print(f"[info] 收到推理输出，shape={getattr(outputs, 'shape', None)}，待补全后处理")
    return []


def estimate_distance(detection: Detection, depth_map) -> float | None:
    """用检测框内的深度中位数估计障碍物距离（米）。

    TODO: 接入 Depth Anything V2 的深度输出，并完成尺度对齐
          （可用 LiDAR 稀疏点标定，或改用 Depth Pro 得到度量深度）。
    """
    if depth_map is None:
        return None
    return None


def decide_semantics(detections: list[Detection], distance: float | None) -> str:
    """语义决策：绕行 / 停止 / 上报。

    TODO: 复杂障碍（电源线、宠物粪便等）截取 ROI 后交给 GPU 上的 MiniCPM-o 判定，
          这里先用规则给出占位决策，保证链路可跑通。
    """
    risky = {"power_cord", "pet_waste"}
    for det in detections:
        if det.label in risky and distance is not None and distance < 0.3:
            return "stop"
    return "avoid" if detections else "continue"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="P1 视觉避障推理")
    parser.add_argument("--model", default="models/yolov8n.cix", help=".cix（板端）或 .onnx（开发机）")
    parser.add_argument("--source", default="0", help="摄像头序号或视频路径")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.5)
    parser.add_argument("--show", action="store_true", help="显示实时画面")
    parser.add_argument("--save", default="", help="保存结果视频路径")
    parser.add_argument("--cpu-only", action="store_true", help="强制使用 ONNX Runtime CPU")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not Path(args.model).exists() and not Path(args.model.replace(".cix", ".onnx")).exists():
        print(f"找不到模型文件：{args.model}")
        return 1

    backend = build_backend(args.model, prefer_npu=not args.cpu_only)
    print(f"[info] 推理后端：{backend.name}")

    try:
        import cv2
    except ImportError:
        print("需要先安装依赖：pip install -r requirements.txt")
        return 1

    source = int(args.source) if str(args.source).isdigit() else args.source
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        print(f"无法打开视频源：{args.source}")
        return 1

    while True:
        ok, frame = capture.read()
        if not ok:
            break
        outputs = backend.infer(frame)
        detections = postprocess(outputs, conf_threshold=args.conf)
        distance = estimate_distance(detections[0], None) if detections else None
        decision = decide_semantics(detections, distance)

        if args.show or args.save:
            for det in detections:
                x1, y1, x2, y2 = (int(v) for v in det.box)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (200, 140, 91), 2)
                cv2.putText(
                    frame,
                    f"{det.label} {det.confidence:.2f}",
                    (x1, max(18, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
            cv2.putText(
                frame,
                f"decision: {decision}",
                (16, 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            if args.show:
                cv2.imshow("P1 vision avoidance", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    capture.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
