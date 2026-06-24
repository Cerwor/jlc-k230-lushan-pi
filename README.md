# JLC K230 Lushan Pi Codex Skill

这个仓库发布一个可安装到 Codex 的 Skill，用于立创·庐山派 K230-CanMV 开发板的视觉、屏幕、外设、离线运行和电赛项目快速开发。

真正会被 Codex 加载的是这个文件夹：

```text
jlc-k230-lushan-pi/
```

仓库根目录的 `README.md` 和 `AGENT_USAGE.md` 只用于说明、分发和交给其他 Agent 使用。安装时请复制整个 `jlc-k230-lushan-pi` 文件夹。

任务路由以 `jlc-k230-lushan-pi/SKILL.md` 的 `Quick Routing` 表为唯一信源。README 和 AGENT_USAGE 不复制完整路由表，避免新增 reference 时多处维护。

仓库根目录的 `tools/` 是维护仓库用的脚本，不属于可安装 Skill 本体。

## 适用场景

这个 Skill 主要覆盖：

- CanMV MicroPython 项目编写、移植、调试和离线部署
- 立创·庐山派 K230-CanMV 开发板常见环境
- 3.1 寸 ST7701 MIPI LCD，默认 `800x480` 全屏显示
- 摄像头、LCD、GPIO/FPIOA、UART、PWM、I2C、SPI
- 圆形、矩形、色块、线条、二维码、条形码、AprilTag 等视觉任务
- YOLOv5、YOLOv8、YOLO11、KModel、`nncase_runtime`、`aicube`
- 电赛控制类题目的视觉坐标输出、串口通信、离线 `main.py` 启动
- 现场调试、raw REPL、坏 `main.py` 恢复、屏幕缩放/FPS 问题排查

## 已沉积的实测结论

这些结论来自已连接开发板测试，应作为默认经验使用；如果用户说明自己的固件、屏幕、摄像头或接线不同，以用户当前硬件为准。

| 项目 | 结论 |
| --- | --- |
| 固件参考 | `CanMV_K230_LCKFB_micropython_v1.6-57-gce3418e_nncase_v2.11.0` 是已测参考版本，不是强制要求 |
| 3.1 寸屏 | 默认使用 `Display.ST7701`、`800x480`、全屏显示 |
| 显示缩小问题 | 不要把低分辨率检测帧直接居中显示到 LCD；应 LCD 全屏显示，检测低分辨率后把坐标缩放回屏幕坐标 |
| raw REPL | `scripts/run_canmv_raw_repl.py` 可从 RAM 临时运行脚本，已加入串口列举、握手诊断、`2000000/115200` 自动尝试 |
| 探针验收 | `scripts/evaluate_probe_log.py` 可把矩形、圆形、YOLO、UART、资源探针日志判读为 `pass/warn/fail` |
| mpremote 调试 | 提供 `scripts/mpremote_deploy.py` 和 `scripts/mpremote_snapshot.py` 作为显式授权后的板端文件部署、运行中截图拉取补充方案 |
| 离线运行 | TF 卡根目录 `main.py` 可上电自动运行；坏脚本阻塞时可改名为 `main_disabled.py` 后重启 |
| 圆形检测 | 瓶盖目标长测约 63 FPS，适合低分辨率检测加结果保持 |
| 矩形检测 | 黑色胶布白纸矩形优先用 `cv_lite.grayscale_find_rectangles_with_corners`，约 58-59 FPS |
| 移动矩形 | 严格参数加 relaxed fallback 的 `cv_lite` 跟踪在移动/倾斜/距离变化下更稳 |
| 光照变化 | normal/bright/shadow/dim 四阶段测试中，fallback 可吸收曝光和对比度变化 |
| Otsu 阈值 | `scripts/probe_otsu_threshold.py` 可短跑验证黑白目标自动阈值链路；本机实测 30 帧采样得 26 个有效样本，阈值约 `0..120` |
| YOLO | 已测固件支持 `nncase_runtime`、`aicube`、`libs.PipeLine`、YOLOv5/YOLOv8/YOLO11 |
| UART2 | 不要假设唯一引脚；可用 `scripts/probe_uart2_loopback.py` 扫描常见 UART2 映射 |

## 安装

### Windows PowerShell

在仓库根目录执行：

```powershell
$skills = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME "skills" } else { Join-Path $HOME ".codex\skills" }
New-Item -ItemType Directory -Force -Path $skills | Out-Null
Copy-Item -Recurse -Force ".\jlc-k230-lushan-pi" $skills
```

如果 Codex 没有自动刷新 Skill 列表，重启 Codex。

### 更新已有安装

每次拉取、合并或修改仓库后，需要重新复制 Skill 文件夹。Codex 读取的是安装目录里的副本，不是开发仓库里的副本。

```powershell
$skills = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME "skills" } else { Join-Path $HOME ".codex\skills" }
Remove-Item -Recurse -Force (Join-Path $skills "jlc-k230-lushan-pi") -ErrorAction SilentlyContinue
Copy-Item -Recurse -Force ".\jlc-k230-lushan-pi" $skills
```

### macOS/Linux

在仓库根目录执行：

```bash
skills="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$skills"
rm -rf "$skills/jlc-k230-lushan-pi"
cp -R ./jlc-k230-lushan-pi "$skills/"
```

## 安装检查

安装后应能看到：

```text
%CODEX_HOME%\skills\jlc-k230-lushan-pi\SKILL.md
%USERPROFILE%\.codex\skills\jlc-k230-lushan-pi\SKILL.md
$CODEX_HOME/skills/jlc-k230-lushan-pi/SKILL.md
$HOME/.codex/skills/jlc-k230-lushan-pi/SKILL.md
```

可以这样触发：

```text
使用 jlc-k230-lushan-pi 这个 skill，帮我写一个 K230 CanMV 的矩形检测 main.py，屏幕是 3.1 寸。
```

也可以英文触发：

```text
Use $jlc-k230-lushan-pi to write a K230 CanMV main.py for rectangle tracking on the 3.1-inch LCD.
```

## 仓库结构

```text
jlc-k230-lushan-pi/
  SKILL.md
  agents/
    openai.yaml
  references/
  assets/
    contest-template/
  scripts/
docs/
README.md
AGENT_USAGE.md
tools/
```

关键文件：

- `jlc-k230-lushan-pi/SKILL.md`：Skill 入口、快速路由表、全局规则
- `jlc-k230-lushan-pi/references/canmv-api-known-issues.md`：K230 CanMV API 坑点、保守语法、跨固件差异和代码生成检查
- `jlc-k230-lushan-pi/references/sources-and-boundaries.md`：适用边界、官方来源链接和 API 手册路由
- `jlc-k230-lushan-pi/references/canmv-workflows.md`：固件参考、摄像头、LCD、外设 bring-up 流程
- `jlc-k230-lushan-pi/references/mpremote-debug-workflows.md`：`mpremote` 部署、运行中截图拉取和 SD 卡侧信道调试
- `jlc-k230-lushan-pi/references/official-basic-image-patterns.md`：GPIO/FPIOA/PWM/UART 与基础图像处理模式
- `jlc-k230-lushan-pi/references/circle-detection-patterns.md`：圆形/圆环检测与低分辨率检测坐标缩放策略
- `jlc-k230-lushan-pi/references/contest-2025-rectangle-patterns.md`：2025 风格矩形靶、`cv_lite`、ROI、串口输出策略
- `jlc-k230-lushan-pi/references/yolo-module-patterns.md`：YOLO/KModel/PipeLine 使用要点
- `jlc-k230-lushan-pi/references/offline-run-patterns.md`：TF 卡 `main.py`、`boot.py`、离线自启动
- `jlc-k230-lushan-pi/references/troubleshooting.md`：集中排障清单
- `jlc-k230-lushan-pi/assets/contest-template/`：可复制的电赛项目模板
- `jlc-k230-lushan-pi/scripts/run_canmv_raw_repl.py`：通过 raw REPL 从 RAM 临时运行脚本
- `jlc-k230-lushan-pi/scripts/mpremote_deploy.py`：显式把本地文件复制到板端 `/sdcard` 的 `mpremote` 部署助手
- `jlc-k230-lushan-pi/scripts/mpremote_snapshot.py`：拉取并解码运行中快照文件的 `mpremote` 调试助手
- `jlc-k230-lushan-pi/scripts/probe_k230_sensor_init.py`：尝试多种 K230 `Sensor` 初始化/抓帧方式的诊断脚本
- `jlc-k230-lushan-pi/scripts/probe_otsu_threshold.py`：黑白目标 Otsu 自动阈值短跑探针
- `jlc-k230-lushan-pi/scripts/probe_cvlite_rectangle_target.py`：黑胶布矩形靶 300 帧命中率/FPS/中心稳定性短跑探针
- `jlc-k230-lushan-pi/scripts/probe_circle_target.py`：瓶盖/圆形目标 300 帧命中率/FPS/圆心稳定性短跑探针
- `jlc-k230-lushan-pi/scripts/probe_yolo_runtime.py`：YOLO 运行时导入、YOLO 类可用性、板端模型和例程路径短探针
- `jlc-k230-lushan-pi/scripts/evaluate_probe_log.py`：矩形、圆形、YOLO、UART、资源探针日志验收解释器
- `jlc-k230-lushan-pi/scripts/validate_skill.py`：桌面端 Skill 预检脚本
- `jlc-k230-lushan-pi/scripts/probe_uart2_loopback.py`：常见 UART2 映射扫描与回环测试
- `jlc-k230-lushan-pi/scripts/smoke_camera_lcd.py`：短摄像头/LCD 冒烟测试
- `docs/TEST_MATRIX.md`：仓库级测试矩阵，说明每类测试是否上板、是否写卡、需要什么人工准备
- `docs/BOARD_TEST_LOG.md`：仓库级历史实测流水账，不安装到 Codex skill

## 常用模板

| 文件 | 用途 |
| --- | --- |
| `assets/contest-template/main.py` | 电赛项目主入口骨架 |
| `assets/contest-template/examples/camera_lcd_preview.py` | 摄像头和 3.1 寸 LCD 预览 |
| `assets/contest-template/examples/circle_detect.py` | 瓶盖/圆环等圆形目标检测 |
| `assets/contest-template/examples/rectangle_detect.py` | 简单矩形检测 smoke test |
| `assets/contest-template/examples/cvlite_rectangle_target_uart_tracker.py` | 已测高 FPS 黑白矩形靶跟踪，优先用于 2025 风格控制题 |
| `assets/contest-template/examples/rectangle_target_uart_tracker.py` | 无 `cv_lite` 时的传统矩形跟踪备用方案 |
| `assets/contest-template/examples/offline_threshold_tuner.py` | 无电脑现场阈值调试思路 |
| `assets/contest-template/examples/button_capture.py` | USR 按键拍照/保存流程 |
| `assets/contest-template/examples/yolov8_lcd_official_launcher.py` | 官方 YOLOv8 LCD 视频示例入口 |

## 推荐开发流程

1. 先让 Agent 读取 `SKILL.md`。
2. 根据 `SKILL.md` 的 Quick Routing 表只打开相关 `references/` 文件。
3. 从最接近任务的 `assets/contest-template/examples/` 模板开始。
4. 摄像头/LCD 先跑冒烟测试，再加识别，再加 UART/控制。
5. 3.1 寸屏默认保持 `800x480` 全屏显示；耗时视觉算法使用低分辨率检测并缩放坐标。
6. 串口打印要节流，最终控制建议发送固定格式坐标或误差。
7. 最终交付优先给 `main.py` 内容；除非用户明确要求，不主动写入 SD 卡或开发板。
8. 离线运行前，确认 TF 卡根目录存在最终 `main.py`，并经过完整断电/复位测试。

## 分层测试流程

仓库根目录提供统一入口 `tools/test.ps1`。默认模式只做本地预检，不连接开发板、不写 SD 卡：

完整测试选择规则见 `docs/TEST_MATRIX.md`。

```powershell
.\tools\test.ps1
```

连接开发板后，先只列出串口：

```powershell
.\tools\test.ps1 -ListPorts -SkipValidate
```

从 RAM 临时运行摄像头和 3.1 寸 LCD 冒烟测试：

```powershell
.\tools\test.ps1 -Board -Port COM14
```

运行基础硬件视觉链路测试：摄像头/LCD、`Sensor` 初始化探测、Otsu 阈值链路。

```powershell
.\tools\test.ps1 -Board -Vision all-core -Port COM14
```

探测板端模型和例程路径：

```powershell
.\tools\test.ps1 -Board -Vision resources -Port COM14
```

短跑验证黑胶布矩形靶或瓶盖目标：

```powershell
.\tools\test.ps1 -Board -Vision rect-target -Port COM14
.\tools\test.ps1 -Board -Vision circle-target -Port COM14
```

运行 YOLO 运行时/资源探针，或 UART 回环/TX 扫描：

```powershell
.\tools\test.ps1 -Board -Vision yolo -Port COM14
.\tools\test.ps1 -Board -Vision uart-loopback -Port COM14
```

测试已安装到 Codex 的 Skill 副本：

```powershell
.\tools\test.ps1 -Installed -Board -Vision smoke -Port COM14
```

`tools/test.ps1` 的上板模式只使用 raw REPL 从 RAM 运行脚本，不会覆盖 `/sdcard/main.py`。对 `resources`、`rect-target`、`circle-target`、`yolo`、`uart-loopback` 模式，脚本会自动输出 `ACCEPT_* status=pass|warn|fail` 和简短原因。圆形、矩形、移动靶、光照变化、UART 回环、离线自启动这类依赖现场摆放或接线的测试，仍按对应 reference 的专门步骤执行，并把新的实测结论写入 `references/maintenance.md`。

## 连接开发板时的常用命令

列出串口：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py" --list-ports
```

从 RAM 临时运行摄像头/LCD 预览：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py" ".\jlc-k230-lushan-pi\assets\contest-template\examples\camera_lcd_preview.py"
```

运行短冒烟测试：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py" ".\jlc-k230-lushan-pi\scripts\smoke_camera_lcd.py"
```

探测板端模型、例程和资源：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py" ".\jlc-k230-lushan-pi\scripts\probe_board_resources.py"
```

探测 YOLO 运行时和资源：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py" ".\jlc-k230-lushan-pi\scripts\probe_yolo_runtime.py"
```

单独判读已保存的探针日志：

```powershell
python ".\jlc-k230-lushan-pi\scripts\evaluate_probe_log.py" --kind rect ".\rect.log"
```

扫描常见 UART2 回环映射：

```powershell
python ".\jlc-k230-lushan-pi\scripts\probe_uart2_loopback.py"
```

诊断摄像头初始化方式：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py" ".\jlc-k230-lushan-pi\scripts\probe_k230_sensor_init.py"
```

短跑验证 Otsu 自动阈值：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py" ".\jlc-k230-lushan-pi\scripts\probe_otsu_threshold.py"
```

显式使用 `mpremote` 部署 `main.py` 到板端 `/sdcard`：

```powershell
python ".\jlc-k230-lushan-pi\scripts\mpremote_deploy.py" --port COM14 main.py
```

输出运行中截图钩子并拉取快照：

```powershell
python ".\jlc-k230-lushan-pi\scripts\mpremote_snapshot.py" --emit-hook image
python ".\jlc-k230-lushan-pi\scripts\mpremote_snapshot.py" --port COM14 --remote /sdcard/codex_snap.jpg --delete --open
```

## 维护与验证

修改 Skill 后建议至少执行：

```powershell
.\tools\test.ps1
```

对模板做桌面语法检查：

```powershell
python -c "import pathlib; root=pathlib.Path(r'.\jlc-k230-lushan-pi'); files=list(root.rglob('*.py')); [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in files]; print('PY_SYNTAX_OK files=%d' % len(files))"
```

`tools/validate.ps1` 会调用 `scripts/validate_skill.py`、系统 `quick_validate.py` 和桌面 Python 语法检查。注意：桌面 Python 语法检查不能证明 CanMV IDE 或 CanMV MicroPython 一定能运行。最终 `main.py` 仍应遵循 `references/canmv-api-known-issues.md#conservative-syntax-and-validation` 的保守语法规则，并尽量在开发板上用 CanMV IDE 或 raw REPL 验证。

`scripts/validate_skill.py` 不再硬编码维护者本机路径。它会拒绝通用 Windows 绝对路径；如果需要追加本机私有路径模式，把这些模式放在仓库外的 UTF-8 文本文件中，并设置：

```powershell
$env:JLC_K230_LOCAL_PATH_CONFIG = "$HOME\.jlc-k230-local-paths.txt"
```

发布并合并到 GitHub 的常用命令：

```powershell
.\tools\publish.ps1 -Message "Harden YOLO launcher" -Files @("README.md", "jlc-k230-lushan-pi\SKILL.md")
```

如果确认整个工作区都属于本次改动，可以显式使用：

```powershell
.\tools\publish.ps1 -Message "Update skill docs" -All
```

`tools/publish.ps1` 会运行校验、建分支、提交、推送、创建 PR、确认 PR 可 clean merge、squash 合并、拉回 `master`、同步安装目录并校验安装副本。

更新原则：

- 新硬件、新固件、新屏幕、新接线结论写入对应 `references/` 文件。
- 会影响 Agent 路由的内容同步更新 `SKILL.md`。
- 会影响可复用代码的内容同步更新 `assets/contest-template/`。
- 可复用实测结论写入对应 `references/`；长历史记录写入 `docs/BOARD_TEST_LOG.md`。
- 修改仓库后重新复制 `jlc-k230-lushan-pi` 到 Codex skills 安装目录。

## 安全边界

- 不要在未验证视觉结果前驱动舵机、激光、电机等执行器。
- 不要假设 UART、PWM、GPIO 引脚安全可用；先查官方资料、原理图、`fpioa.help(...)` 或用户确认。
- 不要假设模型路径固定为 `/data/...`；优先探测开发板上的实际路径。
- 不要把未验证的复杂脚本直接作为 `/sdcard/main.py` 留在板上。
- 不要在用户未明确授权时写 TF 卡、保存到板端或覆盖用户已有文件。

## 当前状态

Skill 已通过 `quick_validate.py` 校验。多个模板已经做过桌面语法检查，并按已测 CanMV MicroPython 环境调整为更保守的写法。

已连接 Lushan Pi K230 实测过：摄像头/LCD、raw REPL、离线 `main.py` 自动运行、圆形检测、传统矩形检测、`cv_lite` 矩形角点检测、动态矩形跟踪、光照鲁棒性、Otsu 自动阈值、YOLO 能力探测、数据保存、USR 按键、UART2 回环扫描。仓库也提供了桌面端 `scripts/validate_skill.py` 作为 CI/PR 前的预检入口。
