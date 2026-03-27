---
name: 视频去水印桌面端 Development Plan
overview: 基于 Python + PySide6 + FFmpeg + ProPainter 的跨平台桌面方案，先搭稳定可扩展骨架，再分层实现视频处理与AI推理，确保UI流畅和任务可观测。
todos:
  - id: scaffold-ui-worker
    content: 创建 PySide6 主窗口、深色主题、TaskWorker 与 Signal 通信骨架
    status: completed
  - id: minimal-video-intake
    content: 实现视频导入与 ffprobe 元数据读取，展示在任务面板
    status: completed
  - id: decode-stage-mvp
    content: 实现 decode_stage 最小闭环（抽帧到缓存目录）并回传进度
    status: completed
  - id: task-lifecycle
    content: 实现任务生命周期：开始、取消、失败、完成与日志输出
    status: completed
  - id: prepare-inpaint-interface
    content: 定义 BaseInpainter/BaseDetector 接口，预留 ProPainter 与 PaddleOCR 接入点
    status: completed
isProject: false
---

# 视频去水印桌面端 Development Plan

## 方案评估（对你给的规划结论）

- 整体可行，且工程上更利于快速落地（相比 Tauri + Python 双栈，`PySide6` 单语言链路更短）。
- `ProPainter` 作为主修复模型是正确方向；建议保留 `LaMa` 作为轻量后备模型（低显存/CPU场景降级）。
- `QThread + Signal/Slot` 非常适合“UI绝对流畅 + 后台耗时任务”的要求。
- 关键成功点不是单一模型，而是 **可插拔推理后端 + 可恢复的视频任务管线 + 跨平台打包策略**。

## 项目目录结构（Project Structure）

- 建议采用“分层 + 可插拔后端”目录：

```text
video-cleaner/
  app.py
  requirements.txt
  README.md
  .env.example

  src/
    ui/
      main_window.py
      widgets/
        video_preview.py
        region_selector.py
        task_panel.py
        settings_panel.py
      themes/
        dark.qss
      resources/
        icons/

    core/
      config/
        settings.py
        constants.py
      models/
        task.py
        progress.py
        result.py
      events/
        bus.py
      logging/
        logger.py

    pipeline/
      orchestrator.py
      stages/
        decode_stage.py
        detect_stage.py
        mask_stage.py
        inpaint_stage.py
        encode_stage.py
      cache/
        frame_store.py
        mask_store.py

    ai/
      inpaint/
        base_inpainter.py
        propainter_inpainter.py
        lama_inpainter.py
      detect/
        base_detector.py
        paddleocr_detector.py
      runtime/
        device_manager.py
        model_registry.py
        weights_manager.py

    video/
      ffmpeg_client.py
      ffmpeg_probe.py
      frame_extractor.py
      frame_assembler.py
      audio_muxer.py

    workers/
      task_worker.py
      worker_signals.py
      thread_pool.py

    services/
      task_service.py
      project_service.py
      export_service.py

    utils/
      paths.py
      timecode.py
      validators.py
      exceptions.py

  models/
    propainter/
    lama/
    paddleocr/

  third_party/
    ffmpeg/
      win/
      mac/

  tests/
    unit/
    integration/
    e2e/

  scripts/
    download_models.py
    package_win.ps1
    package_mac.sh
```

## 核心模块设计

### 1) UI 与后台任务通信（QThread + Signals）

- UI 线程仅负责：交互、预览绘制、参数输入、进度展示。
- 重任务进入 `TaskWorker(QThread)`：解帧/检测/推理/编码全部在工作线程执行。
- 统一信号接口（建议）：
  - `sig_progress(task_id, stage, percent, eta)`
  - `sig_preview(task_id, frame_path_or_qimage)`
  - `sig_log(task_id, level, message)`
  - `sig_error(task_id, code, message, detail)`
  - `sig_done(task_id, output_path, metrics)`
- 可取消机制：`TaskWorker` 内部维护 `cancel_flag`，每个 stage 轮询，做到“可中断+可恢复”。

### 2) 视频处理工作流（Pipeline）

- 统一编排器：`PipelineOrchestrator`
- 标准管道：
  1. `decode_stage`：ffprobe 读取元信息，FFmpeg 解帧（保留时间戳）
  2. `detect_stage`：自动字幕/水印检测（PaddleOCR 可选）或读取用户框选区域
  3. `mask_stage`：生成逐帧 mask（插值/跟踪保证时序稳定）
  4. `inpaint_stage`：批处理送入 ProPainter（OOM 自动降批/降级模型）
  5. `encode_stage`：帧重组 + 原音轨 mux，导出目标编码（H.264/H.265 可选）
- 中间产物写入 `cache/`（frames、masks、segments），支持失败后断点续跑。
- 性能策略：按 segment 分片（例如 2~5 秒），并行 IO + 串行显存敏感推理。

### 3) 模型与运行时策略

- `BaseInpainter` / `BaseDetector` 抽象接口，模型可替换。
- `DeviceManager` 自动探测：CUDA > MPS > CPU（Windows 可拓展 DirectML ONNX 路径）。
- `WeightsManager` 负责模型下载、校验、版本记录与回滚。

## requirements.txt（核心依赖建议）

- GUI
  - `PySide6`
  - `qdarkstyle`（或自定义 qss，仅选其一）
- 视频与图像
  - `opencv-python`
  - `ffmpeg-python`
  - `numpy`
  - `Pillow`
- AI 推理
  - `torch`
  - `torchvision`
  - `einops`
  - `tqdm`
- 检测（可选）
  - `paddleocr`
  - `paddlepaddle`（按平台选择 CPU/GPU 版本）
- 工具与工程化
  - `pydantic`
  - `PyYAML`
  - `loguru`
  - `orjson`
- 打包
  - `pyinstaller`（MVP建议）
  - `nuitka`（后续优化启动性能/保护源码时再评估）

## 第一阶段开发指令（最优起步顺序）

- **结论：先写“可运行空壳 + 任务骨架”，不要先写纯 FFmpeg 工具。**
- 原因：先打通 UI 与后台通信，能最早验证“不卡 UI + 可观测进度”这一核心非功能需求，后续接算法风险更低。
- 第一阶段（建议 3~5 天）
  1. 搭 `PySide6` 主窗口与深色主题，完成视频导入和区域框选占位。
  2. 实现 `TaskWorker + Signals + TaskService`，先用“假任务”模拟 0~100% 进度。
  3. 接入 `ffprobe` 元数据读取与 `decode_stage` 最小闭环（仅抽帧，不推理）。
  4. 打通“开始任务 -> 实时进度 -> 取消 -> 完成提示 -> 打开输出目录”。

## 第二阶段（紧随其后）

- 落地 `mask_stage`（手动框选优先）+ `inpaint_stage`（先接 LaMa 轻量版，再接 ProPainter 主路径）
- 最后补 `encode_stage` 原音轨合成，形成第一条端到端可演示链路。

## 打包与发布建议

- MVP 用 `PyInstaller`：流程简单、排障快。
- 模型与 FFmpeg 使用“外置资源目录 + 首次检查下载/解压”。
- Win/mac 产物分别构建，增加启动自检（GPU、模型、FFmpeg 可用性）。

