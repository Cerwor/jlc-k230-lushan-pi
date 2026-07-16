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
- 通用云台/激光打靶/描图/跟随的控制架构，以及 ZDT 闭环步进电机的专用 UART 控制经验
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
| 板端探针 | `scripts/run_board_probe.py` 是安装包内统一入口，从 RAM 运行并自动判读矩形、圆形、YOLO、UART、资源与生命周期探针，不写 `/sdcard/main.py` |
| raw REPL | `scripts/run_canmv_raw_repl.py` 提供握手诊断与 `2000000/115200` 尝试；主机脚本会有限搜索已装 `serial`/`mpremote` 的 Python，不自动安装依赖 |
| 部署与截图 | 显式授权后可用 `mpremote_deploy.py`、`mpremote_snapshot.py`；`mpremote` 握手失败时可用 `raw_repl_deploy.py` 做字节校验和原子替换的单文件回退 |
| 离线运行 | TF 卡根目录 `main.py` 可上电自动运行；坏脚本阻塞时可改名为 `main_disabled.py` 后重启 |
| 圆形检测 | 场景敏感，适合低分辨率检测、半径/ROI 约束和短时结果保持 |
| 矩形检测 | 黑色胶布白纸矩形优先用 `cv_lite.grayscale_find_rectangles_with_corners`，并保留严格检测后的按需 fallback |
| 移动矩形 | 严格参数加 relaxed fallback 的 `cv_lite` 跟踪在移动/倾斜/距离变化下更稳 |
| 光照变化 | normal/bright/shadow/dim 四阶段测试中，fallback 可吸收曝光和对比度变化 |
| Otsu 阈值 | `scripts/probe_otsu_threshold.py` 可短跑验证黑白目标自动阈值、验证和默认值回退链路 |
| YOLO | 已测固件支持 `nncase_runtime`、`aicube`、`libs.PipeLine`、YOLOv5/YOLOv8/YOLO11 |
| UART2 | 不要假设唯一引脚；可用 `scripts/probe_uart2_loopback.py` 扫描常见 UART2 映射 |
| 云台和 ZDT 电机 | 通用云台/激光跟随先走 `contest-patterns.md`；确认是 ZDT XS 系列闭环步进后，再用 `zdt-stepper-gimbal-patterns.md` 的 UART2、`F1/FC`、急停和反馈节流经验 |

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

安装包版本可直接读取：

```powershell
Get-Content "$HOME\.codex\skills\jlc-k230-lushan-pi\VERSION"
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
  VERSION
  SKILL.md
  agents/
    openai.yaml
  references/
  assets/
    contest-template/
    model-package/
  scripts/
docs/
tests/
README.md
AGENT_USAGE.md
tools/
```

按职责查看即可，不维护第二份逐文件清单：

| 区域 | 职责 |
| --- | --- |
| `SKILL.md`、`agents/` | 触发、默认值、唯一任务路由和 UI 元数据 |
| `references/` | 按任务加载的工作流、视觉、模型、硬件、控制和排障知识 |
| `scripts/` | 主机公共能力、验证器、部署器、统一板端探针入口及板端短探针 |
| `assets/contest-template/` | 可复制的电赛项目骨架和有限模板 |
| `assets/model-package/` | 自训练 `.kmodel` 交付包约定 |
| `docs/`、`tests/`、`tools/` | 仓库级测试矩阵、历史实测、主机回归和发布维护，不安装到 Skill |

具体任务先看 `SKILL.md#Quick-Routing`；包内容完整性由 `scripts/validate_skill.py` 检查，而不是靠 README 手工同步文件名。

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
| `assets/model-package/model_manifest.example.json` | 自训练 `.kmodel`、标签、输入尺寸和板端路径的模型包清单模板 |

## 自训练模型交付包

如果用户自己训练模型并转换为 `.kmodel`，建议把模型按下面结构交给 Agent：

```text
model-package/
  model_manifest.json
  labels.txt
  target.kmodel
  sample-test.jpg         可选，用于 still-image 验证
  conversion-log.txt      可选，首次上板或加载失败时很有用
```

最少需要提供 `.kmodel`、`labels.txt`、任务类型、模型输入尺寸、YOLO 包装类或自定义后处理说明，以及计划放到板端的路径。可从 `jlc-k230-lushan-pi/assets/model-package/model_manifest.example.json` 复制 manifest 模板，并用下面命令预检：

```powershell
python ".\jlc-k230-lushan-pi\scripts\check_model_package.py" ".\model-package"
```

完整验收流程见 `jlc-k230-lushan-pi/references/model-vision-pipeline.md`。

## 三条快速路径

1. 经典视觉：先跑 `smoke`，再跑 `rect-target` 或 `circle-target`，从对应模板生成 `main.py`，确认稳定框和坐标后才接控制。
2. 自训练模型：先校验模型包，再跑 `yolo` 资源探针，依次完成已知图片、摄像头 LCD、现场光照测试，最后开放执行器。
3. 视觉闭环：先让视觉只输出有时效的屏幕误差，再验证 UART/执行器方向、限速和丢失保持，最后做小范围闭环及离线复位验收。

每条路径遇到 `warn` 或 `fail` 都回到 `SKILL.md` 的 Quick Routing 和 `references/troubleshooting.md#probe-result-actions`，不要跳过未通过的前置层。

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

安装后的 Skill 以 `scripts/run_board_probe.py` 为统一上板入口；它可以直接列端口、调度 RAM-only 探针并判读结果。仓库根目录的 `tools/test.ps1` 是维护封装，默认执行离线验证和全部主机单元测试，只有显式 `-Board` 才连接开发板：

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

验证摄像头、LCD 与媒体池能连续初始化和释放三轮：

```powershell
.\tools\test.ps1 -Board -Vision resource-cycle -Port COM14
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

`tools/test.ps1` 委托安装包内的 `run_board_probe.py`，上板时只从 RAM 运行，不覆盖 `/sdcard/main.py`。对 `resources`、`resource-cycle`、`rect-target`、`circle-target`、`yolo`、`uart-loopback` 会自动输出 `ACCEPT_* status=pass|warn|fail`。可复用结论写入对应 reference；日期、计数、耗时等原始实测写入 `docs/BOARD_TEST_LOG.md`。

## 连接开发板时的常用命令

列出串口：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_board_probe.py" --list-ports
```

从 RAM 临时运行摄像头/LCD 预览：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py" ".\jlc-k230-lushan-pi\assets\contest-template\examples\camera_lcd_preview.py"
```

运行短冒烟测试：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_board_probe.py" --vision smoke --port COM14
```

探测板端模型、例程和资源：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_board_probe.py" --vision resources --port COM14
```

探测 YOLO 运行时和资源：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_board_probe.py" --vision yolo --port COM14
```

单独判读已保存的探针日志：

```powershell
python ".\jlc-k230-lushan-pi\scripts\evaluate_probe_log.py" --kind rect ".\rect.log"
```

扫描常见 UART2 回环映射：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_board_probe.py" --vision uart-loopback --port COM14
```

诊断摄像头初始化方式：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_board_probe.py" --vision sensor --port COM14
```

短跑验证 Otsu 自动阈值：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_board_probe.py" --vision otsu --port COM14
```

显式使用 `mpremote` 部署 `main.py` 到板端 `/sdcard`：

```powershell
python -m pip install -r .\requirements-host.txt
python ".\jlc-k230-lushan-pi\scripts\mpremote_deploy.py" --port COM14 main.py
```

如果 `mpremote` 无法与当前固件进入 REPL，可改用复用已测 raw-REPL 握手的单文件回退：

```powershell
python ".\jlc-k230-lushan-pi\scripts\raw_repl_deploy.py" main.py --remote /sdcard/main.py --port COM14
```

主机脚本会先检查当前解释器，再有限搜索系统中已经安装所需 `serial`/`mpremote` 能力的 Python；也可显式传 `--host-python` 或设置 `K230_HOST_PYTHON`。它不会自行安装软件包。

输出运行中截图钩子并拉取快照：

```powershell
python ".\jlc-k230-lushan-pi\scripts\mpremote_snapshot.py" --emit-hook image
python ".\jlc-k230-lushan-pi\scripts\mpremote_snapshot.py" --port COM14 --remote /sdcard/codex_snap.jpg --delete --open
```

`mpremote_*` 工具默认只自动选择已实测的 CanMV USB VID:PID 端口；如果系统只显示通用 USB 串口描述，优先传 `--port COM14`，确实需要时再加 `--allow-fuzzy-port`。`mpremote_snapshot.py --delete` 默认只允许删除 `/sdcard/codex_snap*` 或 `/sdcard/tmp/codex_snap*` 这类快照文件，自定义远端路径需要显式 `--force-any-remote`。所有板端写入仍受 `references/offline-run-patterns.md` 的部署档位门禁约束。

## 维护与验证

修改 Skill 后建议至少执行：

```powershell
.\tools\test.ps1
```

对模板做桌面语法检查：

```powershell
python -c "import pathlib; root=pathlib.Path(r'.\jlc-k230-lushan-pi'); files=list(root.rglob('*.py')); [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in files]; print('PY_SYNTAX_OK files=%d' % len(files))"
```

`tools/test.ps1` 会先调用 `tools/validate.ps1`，再运行 `tests/` 下全部主机回归测试；`tools/publish.ps1` 在创建和自动合并 PR 前调用同一测试入口。桌面测试不能证明 CanMV IDE 或 CanMV MicroPython 一定能运行，最终 `main.py` 仍应遵循保守语法规则，并尽量在开发板上验证。

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

`tools/publish.ps1` 会运行校验和全部主机单测，再建分支、提交、推送、创建 PR、确认 PR 可 clean merge、squash 合并、拉回默认分支、同步安装目录并校验安装副本。

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

已连接 Lushan Pi K230 实测过：摄像头/LCD、三轮资源生命周期、raw REPL、离线 `main.py` 自动运行、圆形检测、传统矩形检测、`cv_lite` 矩形角点检测、动态矩形跟踪、光照鲁棒性、Otsu 自动阈值、YOLO 能力探测、数据保存、USR 按键、UART2 回环扫描、ZDT 闭环步进电机单轴云台控制链路。仓库也提供了桌面端 `scripts/validate_skill.py` 作为 CI/PR 前的预检入口。
