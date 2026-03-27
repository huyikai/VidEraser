# VidEraser

一个跨平台（Windows/macOS）的桌面端视频去水印/硬字幕擦除工具。

当前版本重点是打通工程骨架：`PySide6 UI + 后台任务线程 + FFprobe 元信息 + Decode 抽帧管线`，为后续接入 ProPainter/LaMa 做准备。

## 目标与特性

- 导入视频，读取元信息（分辨率、时长、FPS）。
- 后台线程执行耗时任务，UI 保持流畅。
- 最小可用处理链路：probe -> decode -> 输出。
- 支持手动输入去除区域 `x/y/w/h`，任务会优先使用该区域生成 mask。
- 预留 AI 抽象接口（Inpaint/Detect），后续可平滑接入模型。

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

### 为什么去除效果还不够理想？

当前版本已接入基础 `detect -> mask -> inpaint -> encode` 流程，但 `inpaint` 仍是 OpenCV 轻量兜底实现（非 ProPainter/LaMa 最终效果）。后续会继续接入深度模型以提升复杂场景质量。
