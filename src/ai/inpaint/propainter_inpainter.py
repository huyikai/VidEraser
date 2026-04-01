from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import torch

from src.ai.inpaint.base_inpainter import BaseInpainter


class ProPainterInpainter(BaseInpainter):
    """Video inpainting via propainter + pytorchcv (NVIDIA CUDA required)."""

    name = "propainter"

    def process(
        self,
        frames_dir: Path,
        masks_dir: Path,
        output_dir: Path,
        progress_cb=None,
        cancel_cb=None,
    ) -> int:
        if not torch.cuda.is_available():
            raise RuntimeError(
                "当前集成的 ProPainter（propainter / pytorchcv）需要 NVIDIA CUDA。"
                "无独显或未装 CUDA 驱动时，请在界面选择「LaMa」或「OpenCV」。"
            )

        frame_paths = sorted(frames_dir.glob("frame_*.png"))
        if len(frame_paths) < 2:
            raise RuntimeError(
                "ProPainter 至少需要 2 张抽帧，请提高视频时长或降低抽帧间隔。"
            )

        from propainter.propainter_video import (
            FilePathDirSequencer,
            RawFrameSequencer,
            RawMaskSequencer,
            ScaledProPainterIterator,
        )

        frames_seq = RawFrameSequencer(data=FilePathDirSequencer(str(frames_dir)))
        masks_seq = RawMaskSequencer(
            data=FilePathDirSequencer(str(masks_dir)),
            pre_raw_mask_dilation=0,
        )

        n = len(frames_seq)
        pp_window = 80
        if n < pp_window:
            pp_window = n if n % 2 == 0 else max(2, n - 1)
            if pp_window % 2 != 0:
                pp_window -= 1
        pp_stride = min(5, max(1, pp_window // 4))
        step = min(10, max(1, n // 2))

        iterator = ScaledProPainterIterator(
            raw_frames=frames_seq,
            raw_masks=masks_seq,
            image_resize_ratio=1.0,
            mask_dilation=4,
            post_raw_mask_dilation=0,
            use_cuda=True,
            pp_window_size=pp_window,
            pp_stride=pp_stride,
            step=step,
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        total = len(frame_paths)
        processed = 0
        out_chunks: list[np.ndarray] = []

        # ScaledProPainterIterator 会按窗口流式输出片段；这里做“最佳努力”的逐片进度回报。
        for chunk in iterator:
            if cancel_cb and cancel_cb():
                break
            if not isinstance(chunk, np.ndarray):
                continue
            if chunk.ndim != 4:
                continue

            out_chunks.append(chunk)
            processed = min(processed + chunk.shape[0], total)
            if progress_cb:
                progress_cb(processed, total)

        if not out_chunks:
            return 0

        out_frames = np.concatenate(out_chunks, axis=0)
        if out_frames.ndim != 4:
            raise RuntimeError(f"ProPainter 输出维度异常: {out_frames.shape}")

        count = min(out_frames.shape[0], total)
        for i in range(count):
            rgb = out_frames[i]
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(output_dir / frame_paths[i].name), bgr)

        return count
