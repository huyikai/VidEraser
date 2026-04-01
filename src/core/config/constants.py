import os

APP_NAME = "VidEraser"


def _env_float(name: str, default: float, minimum: float | None = None) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        val = float(raw)
    except ValueError:
        return default
    if minimum is not None:
        val = max(minimum, val)
    return val


def _env_int(name: str, default: int, minimum: int | None = None) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        val = int(raw)
    except ValueError:
        return default
    if minimum is not None:
        val = max(minimum, val)
    return val

# 与 UI / VideoTask.inpaint_backend 一致
INPAINT_BACKEND_OPENCV = "opencv"
INPAINT_BACKEND_LAMA = "lama"
INPAINT_BACKEND_PROPAINTER = "propainter"

VALID_INPAINT_BACKENDS: frozenset[str] = frozenset(
    {INPAINT_BACKEND_OPENCV, INPAINT_BACKEND_LAMA, INPAINT_BACKEND_PROPAINTER}
)

# 管线 decode/encode 帧率：跟随源视频并夹在区间内
PIPELINE_FPS_MIN = 1.0
PIPELINE_FPS_CAP = 60.0
PIPELINE_FPS_FALLBACK = 30.0

# 处理阶段额外 FPS 上限（加速；与源 FPS 取 min），可用环境变量覆盖：
# VIDERASER_PROCESSING_FPS_CAP
PROCESSING_FPS_CAP = _env_float("VIDERASER_PROCESSING_FPS_CAP", 24.0, minimum=1.0)

# 自动 OCR：从已解码帧中均匀采样若干张合并框，可用环境变量覆盖：
# VIDERASER_OCR_SAMPLE_MAX_FRAMES
OCR_SAMPLE_MAX_FRAMES = _env_int("VIDERASER_OCR_SAMPLE_MAX_FRAMES", 8, minimum=1)

# OCR 合并框相对画面宽高的上限，超出则裁切到上限内（避免整屏 mask 发糊/极慢）
OCR_REGION_MAX_WIDTH_FRAC = 0.92
OCR_REGION_MAX_HEIGHT_FRAC = 0.18
