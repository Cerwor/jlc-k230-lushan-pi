# JLC K230 Lushan Pi Codex Skill

面向立创·庐山派 K230-CanMV 的 Codex Skill，服务于电赛视觉、3.1 寸 LCD、外设控制、YOLO/KModel、离线部署和现场排障。

`CanMV MicroPython` · `ST7701 800x480` · `经典视觉` · `YOLO/KModel` · `UART/云台` · `离线 main.py`

> Codex 的实际入口是 [`jlc-k230-lushan-pi/SKILL.md`](./jlc-k230-lushan-pi/SKILL.md)。README 只负责安装和项目导航，不复制 Skill 内的任务路由。

## 核心能力

- 摄像头与 3.1 寸 ST7701 LCD 初始化、全屏显示和性能优化
- 圆形、矩形、色块、线条、二维码、AprilTag 等经典视觉任务
- YOLOv5、YOLOv8、YOLO11、自训练 `.kmodel` 和模型交付校验
- GPIO/FPIOA、UART、PWM、I2C、SPI 及板端资源探测
- 通用视觉闭环、激光打靶、云台跟随和 ZDT 闭环步进电机控制
- TF 卡离线启动、raw REPL、mpremote、截图回传和故障恢复

## 快速开始

### 1. 安装 Skill

在仓库根目录执行。

**Windows PowerShell**

```powershell
$skills = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME "skills" } else { Join-Path $HOME ".codex\skills" }
$target = Join-Path $skills "jlc-k230-lushan-pi"
New-Item -ItemType Directory -Force -Path $skills | Out-Null
Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item -LiteralPath ".\jlc-k230-lushan-pi" -Destination $target -Recurse
```

**macOS / Linux**

```bash
skills="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$skills"
rm -rf "$skills/jlc-k230-lushan-pi"
cp -R ./jlc-k230-lushan-pi "$skills/"
```

安装后重启 Codex，或刷新 Skill 列表。

### 2. 直接使用

```text
使用 jlc-k230-lushan-pi skill，帮我写一个 K230 CanMV 的黑色矩形检测 main.py，
屏幕是 3.1 寸，并输出矩形中心坐标。
```

Codex 会从 [`SKILL.md`](./jlc-k230-lushan-pi/SKILL.md) 的 `Quick Routing` 选择最少的参考文件和最接近的已测模板。

## 默认环境

| 项目 | 默认值或边界 |
| --- | --- |
| 开发板 | 立创·庐山派 K230-CanMV |
| 显示屏 | 3.1 寸 ST7701 MIPI LCD，`800x480` |
| 开发方式 | 优先 CanMV MicroPython，最终交付 `main.py` |
| 固件基线 | `CanMV_K230_LCKFB_micropython_v1.6-57-gce3418e_nncase_v2.11.0`，仅代表已测版本 |
| 板端测试 | 默认从 RAM 运行，不覆盖 `/sdcard/main.py` |
| 板端写入 | 必须经过部署档位判断，并获得用户明确授权 |

硬件、固件或接线不同时，以当前设备探测结果为准，不把上述默认值当作通用结论。

## 工作流入口

| 任务 | 首选入口 | 详细说明 |
| --- | --- | --- |
| 摄像头、LCD、板卡冒烟测试 | `scripts/run_board_probe.py --vision smoke` | [CanMV 工作流](./jlc-k230-lushan-pi/references/platform/canmv-workflows.md) |
| 圆形、矩形和颜色检测 | `SKILL.md` 的 `Template Selection` | [矩形模式](./jlc-k230-lushan-pi/references/vision/contest-2025-rectangle-patterns.md) |
| 自训练 `.kmodel` | `scripts/check_model_package.py` | [模型视觉闭环](./jlc-k230-lushan-pi/references/vision/model-vision-pipeline.md) |
| UART、执行器和视觉闭环 | `references/control/contest-patterns.md` | [硬件引脚速查](./jlc-k230-lushan-pi/references/platform/hardware-pin-resource-quickref.md) |
| ZDT 步进电机云台 | `references/control/zdt-stepper-gimbal-patterns.md` | [控制安全边界](./jlc-k230-lushan-pi/references/control/contest-patterns.md) |
| 离线部署与恢复 | `references/deployment/offline-run-patterns.md` | [故障排查](./jlc-k230-lushan-pi/references/platform/troubleshooting.md) |

## 常用命令

### 离线校验

```powershell
.\tools\test.ps1
```

### 查看串口

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_board_probe.py" --list-ports
```

### RAM-only 冒烟测试

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_board_probe.py" --vision smoke --port COM14
```

### 基础视觉与资源测试

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_board_probe.py" --vision all-core --port COM14
```

### raw REPL 不可用时导出探针

该命令只在电脑上生成文件，不写入开发板。

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_board_probe.py" --vision smoke --export-main ".\probe-export\main.py"
```

### 显式部署 `main.py`

优先使用 mpremote；握手不兼容时再使用 raw REPL 回退。

```powershell
python -m pip install -r .\requirements-host.txt
python ".\jlc-k230-lushan-pi\scripts\mpremote_deploy.py" --port COM14 main.py
python ".\jlc-k230-lushan-pi\scripts\raw_repl_deploy.py" main.py --remote /sdcard/main.py --port COM14
```

完整测试选择和验收条件见 [`docs/TEST_MATRIX.md`](./docs/TEST_MATRIX.md)。

## 模型交付

只有 `.kmodel` 也可以开始探测，但完整交付包能显著减少标签顺序、输入尺寸和后处理不匹配：

```text
model-package/
  model_manifest.json
  labels.txt
  target.kmodel
  sample-test.jpg       # 可选
  conversion-log.txt    # 可选
```

`model_manifest.json` 建议记录任务类型、输入尺寸、标签顺序、模型路径、nncase 版本、量化方式和目标固件。模板位于 [`assets/model-package`](./jlc-k230-lushan-pi/assets/model-package/)，预检命令如下：

```powershell
python ".\jlc-k230-lushan-pi\scripts\check_model_package.py" ".\model-package"
```

## 仓库结构

```text
K230/
├── jlc-k230-lushan-pi/   # 可安装 Skill
│   ├── SKILL.md          # 唯一任务路由
│   ├── references/
│   │   ├── platform/     # 板卡、API、引脚与排障
│   │   ├── vision/       # 经典视觉、模型与 YOLO
│   │   ├── control/      # 电赛控制与执行器协议
│   │   ├── deployment/   # 离线运行、部署与截图
│   │   └── maintenance/  # 来源、适配与维护规则
│   ├── assets/
│   │   ├── contest-template/examples/  # hardware / vision / control / model
│   │   └── model-package/              # 自训练模型交付约定
│   └── scripts/
│       ├── probes/       # 自包含板端短探针
│       └── *.py          # 稳定的主机 CLI
├── docs/                 # 测试矩阵与实测记录
├── tests/                # 主机回归测试
├── tools/                # 仓库维护入口
├── AGENT_USAGE.md        # 其他 Agent 的使用说明
└── CHANGELOG.md          # 版本记录
```

## 维护与发布

修改后先运行完整离线验证：

```powershell
.\tools\test.ps1
```

按文件发布并创建 PR：

```powershell
.\tools\publish.ps1 -Message "Update skill docs" -Files @("README.md")
```

版本变化见 [`CHANGELOG.md`](./CHANGELOG.md)，板端实测记录见 [`docs/BOARD_TEST_LOG.md`](./docs/BOARD_TEST_LOG.md)，维护边界见 [`references/maintenance/maintenance.md`](./jlc-k230-lushan-pi/references/maintenance/maintenance.md)。

## 安全边界

- 视觉结果未稳定前，不驱动电机、舵机或激光。
- 不猜测 GPIO、UART、PWM 映射，先查原理图或运行资源探针。
- 不假设模型和例程路径固定，先探测当前固件。
- 未经明确授权，不写 TF 卡、不覆盖板端文件。
- 不把未经验证的复杂程序直接保存为 `/sdcard/main.py`。

## License

见 [`LICENSE`](./LICENSE)。
