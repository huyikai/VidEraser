from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from PIL import Image

from src.ai.inpaint.base_inpainter import BaseInpainter
from src.utils.paths import project_root


def _bundled_lama_weights() -> Path | None:
    """项目内默认权重：models/lama/big-lama.pt（存在则优先于联网下载）。"""
    path = project_root() / "models" / "lama" / "big-lama.pt"
    return path if path.is_file() else None


class LaMaInpainter(BaseInpainter):
    name = "lama"

    def __init__(self) -> None:
        self._lama: Any = None

    def _ensure(self) -> None:
        if self._lama is not None:
            return
        if not os.environ.get("LAMA_MODEL"):
            bundled = _bundled_lama_weights()
            if bundled is not None:
                os.environ["LAMA_MODEL"] = str(bundled.resolve())

        from simple_lama_inpainting import SimpleLama

        if torch.cuda.is_available():
            device = torch.device("cuda")
        else:
            device = torch.device("cpu")
        try:
            self._lama = SimpleLama(device=device)
        except Exception as exc:
            err = str(exc).lower()
            if any(
                x in err
                for x in ("urlopen", "timed out", "timeout", "connection reset", "errno 60")
            ):
                raise RuntimeError(
                    "LaMa 首次运行需从 GitHub 下载模型 `big-lama.pt`，当前下载超时或无法访问 GitHub。\n"
                    "可尝试：① 换网络或使用代理后重试；② 手动下载后设置环境变量 "
                    "LAMA_MODEL=<big-lama.pt 的绝对路径>（见 simple-lama-inpainting 文档）；"
                    "③ 在界面将「修复模型」改为「OpenCV」以跳过下载。\n"
                    f"原始错误: {exc}"
                ) from exc
            raise

    def process(
        self,
        frames_dir: Path,
        masks_dir: Path,
        output_dir: Path,
        progress_cb=None,
        cancel_cb=None,
    ) -> int:
        self._ensure()
        output_dir.mkdir(parents=True, exist_ok=True)
        frame_paths = sorted(frames_dir.glob("frame_*.png"))
        processed = 0
        total = len(frame_paths)
        for frame_path in frame_paths:
            if cancel_cb and cancel_cb():
                break
            mask_path = masks_dir / frame_path.name
            bgr = cv2.imread(str(frame_path))
            if bgr is None:
                continue
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)

            mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
            if mask is None:
                mask = np.zeros((bgr.shape[0], bgr.shape[1]), dtype=np.uint8)
            pil_mask = Image.fromarray(mask)

            out = self._lama(pil_img, pil_mask)
            if isinstance(out, Image.Image):
                out_rgb = np.array(out.convert("RGB"))
            else:
                out_rgb = np.asarray(out)
            out_bgr = cv2.cvtColor(out_rgb, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(output_dir / frame_path.name), out_bgr)
            processed += 1
            if progress_cb and total > 0:
                progress_cb(processed, total)
        return processed
