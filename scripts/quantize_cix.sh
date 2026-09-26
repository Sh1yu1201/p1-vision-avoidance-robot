#!/usr/bin/env bash
# NOE Compiler（NeuralONE / CixBuilder）INT8 量化并编译为板端可执行的 .cix
#
# 用法：
#   bash scripts/quantize_cix.sh -c configs/build.cfg -m models/yolov8n.onnx -o models/yolov8n.cix
#
# 前置条件（开发机，x86 Linux）：
#   pip install CixBuilder        # NOE Compiler 的 Python wheel，以厂商 SDK 文档为准
#   校准数据放在 configs/build.cfg 中 calibration_dir 指向的目录
#
# 注意：不同 SDK 版本的编译命令入口可能略有差异，首次使用请以 `noe_compile --help`
#       与厂商文档为准，再同步修改本脚本。

set -euo pipefail

CONFIG="configs/build.cfg"
MODEL=""
OUTPUT=""

while getopts "c:m:o:h" opt; do
  case "${opt}" in
    c) CONFIG="${OPTARG}" ;;
    m) MODEL="${OPTARG}" ;;
    o) OUTPUT="${OPTARG}" ;;
    h) sed -n '1,20p' "$0"; exit 0 ;;
    *) echo "未知参数，使用 -h 查看用法" >&2; exit 2 ;;
  esac
done

if [[ -z "${MODEL}" ]]; then
  echo "缺少 -m <onnx 模型路径>" >&2
  exit 2
fi

if [[ -z "${OUTPUT}" ]]; then
  OUTPUT="${MODEL%.onnx}.cix"
fi

if ! command -v noe_compile >/dev/null 2>&1; then
  cat >&2 <<'EOF'
未找到 noe_compile 命令，请先安装 NOE Compiler：
    pip install CixBuilder
安装后确认 `noe_compile --help` 可用；若厂商换用了其它入口命令，请修改本脚本。
EOF
  exit 1
fi

echo "[1/3] 检查校准数据"
# TODO: 校准目录来自 configs/build.cfg 的 calibration_dir，建议 100-300 张清扫场景实拍图，
#       覆盖拖鞋、电源线、袜子、家具腿与地面杂物。
export BUILD_CFG="${CONFIG}"
python - <<'PY'
import configparser
import os
cfg = configparser.ConfigParser()
cfg.read(os.environ.get("BUILD_CFG", "configs/build.cfg"))
calib = cfg.get("quantize", "calibration_dir", fallback="calibration")
count = 0
if os.path.isdir(calib):
    count = len([f for f in os.listdir(calib) if f.lower().endswith((".jpg", ".jpeg", ".png"))])
print(f"校准数据目录 {calib}：{count} 张图片")
if count == 0:
    raise SystemExit("校准数据为空，请先放入实拍图片后再量化（INT8 校准必需）")
PY

echo "[2/3] INT8 量化"
# TODO: 具体参数名以 SDK 版本为准；此处按 configs/build.cfg 的字段展开。
noe_compile quantize \
  --config "${CONFIG}" \
  --input "${MODEL}" \
  --precision INT8 \
  --calibration-dir "$(python -c "import configparser;c=configparser.ConfigParser();c.read('${CONFIG}');print(c.get('quantize','calibration_dir',fallback='calibration'))")"

echo "[3/3] 编译为 .cix"
noe_compile build \
  --config "${CONFIG}" \
  --input "${MODEL}" \
  --output "${OUTPUT}"

echo "完成：${OUTPUT}"
echo "请将 .cix 拷贝到 P1 板端，并按 docs/01-deployment.md 运行推理。"
