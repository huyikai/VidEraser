# VidEraser

一个跨平台（Windows/macOS）的桌面端视频去水印/硬字幕擦除工具。

当前已打通完整处理链路，并可在界面选择 **OpenCV / LaMa / ProPainter** 作为修复后端。若项目内存在 **`models/lama/big-lama.pt`**，启动时默认选中 **LaMa**；否则默认 **OpenCV**（ProPainter 依赖 NVIDIA CUDA）。

## 目标与特性

- 导入视频，读取元信息（分辨率、时长、FPS）。
- 后台线程执行耗时任务，UI 保持流畅。
- 最小可用处理链路：probe -> decode -> 输出。
- 支持手动输入去除区域 `x/y/w/h`，或在预览图上拖拽框选（与数值双向同步），任务会优先使用该区域生成 mask。
- 可选 **PaddleOCR 自动检测**：勾选后从已解码帧中**均匀采样至多 8 帧**（见 `OCR_SAMPLE_MAX_FRAMES`），合并各帧文字框为去除区域；若合并框相对画面超过 `OCR_REGION_MAX_WIDTH_FRAC` / `OCR_REGION_MAX_HEIGHT_FRAC` 会**裁切到上限内**（日志 `detect=..._clamped`）；未安装 `paddlepaddle` 或所有采样帧均未检出文字时回退为顶部默认条带。
- 主窗口 **修复模型** 下拉框：`OpenCV`（轻量）、`LaMa`（`simple-lama-inpainting`，CPU/CUDA）、`ProPainter`（`propainter` + pytorchcv，**仅 CUDA**，视频流式补全）。

### 帧率说明（避免「幻灯片」观感）

- **输出视频的帧数与流畅度**由管线 **decode / encode 使用的 FPS** 决定：程序用 ffprobe 读取源视频 `avg_frame_rate`，再与 **`PROCESSING_FPS_CAP`（默认 24）**、全局 `PIPELINE_FPS_CAP` 一起取 **最小值** 并夹在 `[PIPELINE_FPS_MIN, PIPELINE_FPS_CAP]`（见 `src/core/config/constants.py`）后，**整段管线使用同一 FPS** 抽帧与封装。因此**源视频 30fps 时通常按 24fps 处理**，在速度与流畅度之间折中；若需更高帧率可增大该常量并自行重编。
- **OCR 采样帧数只影响「去水印区域」算得准不准**，不会单独减少成片帧数；若成片像幻灯片、时长变短，应检查是否仍在使用极低的管线 FPS（例如历史上曾硬编码 2fps），而不是误以为「OCR 只采了几帧」导致成片只有几帧。
- 支持环境变量快速调参（无需改代码）：`VIDERASER_PROCESSING_FPS_CAP`、`VIDERASER_OCR_SAMPLE_MAX_FRAMES`。

### 速度与修复质量（OpenCV 发糊）

- **耗时**：总帧数 ≈ 视频时长 × 管线 FPS；LaMa/ProPainter 为**逐帧全分辨率推理**，CPU 上 LaMa 会明显慢于 OpenCV。降低 `PROCESSING_FPS_CAP` 可直接减少帧数、缩短总时间（成片帧率随之降低）。
- **OpenCV**：`cv2.inpaint`（TELEA）适合**小范围**修补；**大面积矩形 mask** 时常见**涂抹、发糊**，属算法局限。
- **LaMa** / **ProPainter**：大面积通常观感更好；ProPainter 需 NVIDIA CUDA。水印区域很大时优先尝试 **LaMa** 或 **ProPainter**，并尽量用**手动框选**缩小 mask 到必要范围。

## 待开发 / 路线图

- 任务队列、批量处理与失败重试策略。
- 更细的可选参数：管线 / 处理 FPS 在 UI 中可调、OCR 采样帧数上限、编码预设与质量。
- 预览与导出：分段试处理、对比视图。
- 打包发布：内置 FFmpeg、安装器与自动更新（视需求）。

## 项目结构

```text
app.py
src/
  ui/                # 主窗口与主题
  workers/           # QThread 与信号
  services/          # 任务服务编排
  pipeline/          # 视频处理管线
  video/             # ffmpeg/ffprobe 封装
  ai/                # 模型接口与运行时
  utils/             # 路径与工具函数
scripts/             # 打包与模型脚本占位
models/              # 模型目录（默认不提交）
third_party/ffmpeg/  # ffmpeg 二进制目录（默认不提交）
```

## 快速开始（按步骤复制执行）

### 0) 先安装 FFmpeg（必须）

如果不安装，导入视频会报错：`No such file or directory: 'ffprobe'`。

#### macOS（推荐 Homebrew）

1. 打开“终端”  
2. 执行：

```bash
brew install ffmpeg
```

3. 验证是否安装成功：

```bash
which ffprobe
ffprobe -version
```

只要能看到版本号，就算成功。

#### Windows（推荐 winget）

1. 打开 PowerShell（管理员更稳妥）  
2. 执行：

```powershell
winget install --id Gyan.FFmpeg -e
```

3. 关闭 PowerShell 后重新打开，再验证：

```powershell
where ffprobe
ffprobe -version
```

只要能看到版本号，就算成功。

#### 如果你不会配系统 PATH（兜底方案）

你也可以手动下载 `ffmpeg`/`ffprobe` 后，直接在启动前指定路径：

macOS/Linux:

```bash
export VIDERASER_FFPROBE=/absolute/path/to/ffprobe
export VIDERASER_FFMPEG=/absolute/path/to/ffmpeg
```

Windows（PowerShell）:

```powershell
$env:VIDERASER_FFPROBE="C:\\path\\to\\ffprobe.exe"
$env:VIDERASER_FFMPEG="C:\\path\\to\\ffmpeg.exe"
```

---

### 1) 创建并激活虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows（PowerShell）:

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
```

### 2) 安装 Python 依赖

```bash
pip install -r requirements.txt
```

**自动检测（可选）**：勾选主窗口「自动检测文字区域」前，需安装 `paddlepaddle`（与系统/CPU/GPU 相关，见 [Paddle 安装文档](https://www.paddlepaddle.org.cn/install/quick)）。仅 `pip install paddleocr` 不足以运行推理。

```bash
pip install paddlepaddle
```

### 3) 运行应用

```bash
python app.py
```

## FFmpeg 使用策略（推荐你当前方案）

你希望“流程简单直观、无需用户单独安装”，推荐：

- **不把 ffmpeg 二进制提交到 Git**
- **但在打包发布时带上 ffmpeg/ffprobe**

程序已支持自动查找 `ffmpeg`/`ffprobe`，顺序如下：

1. 环境变量：
   - `VIDERASER_FFPROBE`
   - `VIDERASER_FFMPEG`
2. 系统 `PATH`
3. 常见安装路径（macOS）
4. 项目内置目录：
   - `third_party/ffmpeg/mac/`
   - `third_party/ffmpeg/win/`

> 说明：`.gitignore` 已忽略 `third_party/ffmpeg/**`，因此二进制不会被提交到仓库。

## 可选：手动指定 FFmpeg 路径

如果你已下载 `ffmpeg`/`ffprobe`，但未配置系统 PATH，可在启动前手动指定路径：

```bash
export VIDERASER_FFPROBE=/absolute/path/to/ffprobe
export VIDERASER_FFMPEG=/absolute/path/to/ffmpeg
python app.py
```

Windows（PowerShell）:

```powershell
$env:VIDERASER_FFPROBE="C:\\path\\to\\ffprobe.exe"
$env:VIDERASER_FFMPEG="C:\\path\\to\\ffmpeg.exe"
python app.py
```

## 常见问题

### 导入视频时报错 `No such file or directory: 'ffprobe'`

原因：系统找不到 `ffprobe`。  
解决：安装 FFmpeg，或按上面的环境变量方式指定路径，或在 `third_party/ffmpeg/<平台>/` 放入对应二进制。

### 勾选自动检测后仍像在用「顶区条带」？

请查看任务日志里的 `detect=` 字段：`ocr_union` / `ocr_union_Nframes` 表示已用 OCR 在多帧上合并框；后缀 `_clamped` 表示合并框过大已按画面比例裁切；`default_after_ocr_error` 多为未安装 `paddlepaddle` 或模型初始化失败；`default_after_ocr_empty` 表示采样帧上均未检出文字框。

### LaMa 报错 `urlopen` / `Operation timed out`？

首次使用 LaMa 时会从 GitHub 下载 `big-lama.pt`（约数百 MB）。若网络访问 GitHub 不稳定，会出现超时。可将权重放到项目 **`models/lama/big-lama.pt`**（程序会自动使用，无需再设环境变量）；或**手动下载**后设置 `LAMA_MODEL=/绝对路径/big-lama.pt`；或**换网络/代理后重试**；或先在界面选择 **OpenCV** 跳过下载。

### 选择 ProPainter 提示需要 CUDA？

当前集成的 ProPainter 依赖 `pytorchcv` 流式实现，仅在检测到 NVIDIA CUDA 时可用。Apple Silicon 或无独显机器请改用 **LaMa** 或 **OpenCV**。

### 为什么去除效果还不够理想？

效果与所选修复模型、mask 准确度、管线 FPS 有关。`OpenCV` 仅为快速兜底，**大面积区域**易糊；`LaMa` / `ProPainter` 通常明显更好，但 ProPainter 需 CUDA，且长视频与窗口参数也会影响观感。可按素材切换模型并调整框选或自动检测；自动 OCR 合并区域过大时会裁切（见上文 `detect=`），必要时改用手动框选精确限定水印范围。
