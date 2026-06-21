# Agent Usage Guide

这份文件用于把本仓库交给不一定原生支持 Codex Skills 的 Agent。执行 K230 相关任务时，请把 `jlc-k230-lushan-pi/` 当作知识包和模板包使用。

## 必须遵守的加载顺序

1. 把 `jlc-k230-lushan-pi/` 视为 Skill 根目录。
2. 先完整阅读 `jlc-k230-lushan-pi/SKILL.md`。
3. 按 `SKILL.md` 的 Quick Routing 表选择需要的 `references/` 文件。
4. 只读取与当前任务相关的参考文件，避免把无关内容混进上下文。
5. 所有脚本、参考资料、模板路径都相对 `SKILL.md` 所在目录解析。
6. 写最终 CanMV `main.py` 前，必须阅读 `references/canmv-micropython-compatibility.md`。
7. 优先复用 `assets/contest-template/` 和 `assets/contest-template/examples/` 里的模板。

## 默认交付策略

- 默认交付可复制的 `main.py` 内容或文件。
- 除非用户明确要求，不主动写入 SD 卡、不通过 IDE 保存到开发板、不覆盖板端文件。
- 如果需要连接开发板测试，优先使用 `scripts/run_canmv_raw_repl.py` 从 RAM 临时运行。
- 如果用户明确要求部署到板端或拉取运行中截图，再读取 `references/mpremote-debug-workflows.md` 并使用 `scripts/mpremote_deploy.py` / `scripts/mpremote_snapshot.py`。
- 对电赛项目，先验证摄像头/LCD，再验证识别，再验证串口，再进入执行器控制。
- 涉及执行器、激光、电机、舵机时，必须先给出安全开关、限幅和失联/丢目标保护。
- 集成型比赛 `main.py` 应包含安全停机输出、目标丢失状态、连续帧异常预算和可见 `FAULT` 状态。

## 路由来源

任务到参考文件的映射只维护在 `jlc-k230-lushan-pi/SKILL.md` 的 `Quick Routing` 表里。其他 Agent 使用本仓库时，应先读完整 `SKILL.md`，再按那张表选择 `references/` 文件；不要在这里复制或维护第二张路由表。

## 视觉任务默认决策

- 3.1 寸 LCD 默认 `Display.ST7701`、`800x480`、全屏显示。
- 实时视觉默认使用“显示通道全屏、检测通道低分辨率”的双通道思路。
- 检测坐标必须缩放回 LCD 坐标后再绘制或通过 UART 输出。
- 串口日志要节流，避免每帧大量打印导致 FPS 下降。
- 控制类题目优先输出相对屏幕中心的误差，例如 `e,<err_x>,<err_y>`。

### 矩形靶优先级

对黑色胶布贴在白纸上的矩形、2025 风格矩形靶、需要中心点输出的控制题：

1. 如果固件支持 `cv_lite`，优先使用 `assets/contest-template/examples/cvlite_rectangle_target_uart_tracker.py`。
2. 默认走 `cv_lite.grayscale_find_rectangles_with_corners`。
3. 严格参数先检测；严格检测失败时再启用 relaxed fallback。
4. 多候选时先用面积，稳定后用上一帧中心选择最近候选。
5. 传统 `image.find_rects` 可做 smoke test 或备用，不应作为已测黑白矩形靶的第一选择。
6. `find_blobs` 可作为粗定位 fallback，但中心可能偏离真实角点中心。

### 圆形目标优先级

对瓶盖、圆环、圆形靶：

1. 使用 `assets/contest-template/examples/circle_detect.py`。
2. 避免全帧 `800x480` 直接 `find_circles`。
3. 用低分辨率检测、合理 stride、结果保持和 LCD 坐标缩放。
4. 圆形检测对阈值、半径范围、光照很敏感，现场应先跑可视化 smoke test。

### YOLO 和模型

- 不要假设模型路径固定，先探测 `/sdcard/examples/`、`/sdcard/` 或用户给出的路径。
- YOLO 可用于粗 ROI 或多物体分类，但精确中心控制通常还需要几何后处理。
- 对固定靶标，单类检测器加传统几何精定位往往比纯 YOLO 更稳。
- 比赛现场光照变化大时，不要只依赖离线阈值；需要 fallback、ROI、曝光/对比度容错或模型辅助。

## CanMV MicroPython 代码风格

最终 `main.py` 使用保守写法：

- 避免 f-string。
- 避免 `lambda`。
- 避免列表/字典/集合推导式和生成器表达式。
- 避免复杂多行内联调用。
- 少用动态分发字典，优先 `if/elif`。
- 常量放在文件顶部：屏幕、帧尺寸、引脚、串口、阈值、模型路径、控制限幅。
- 必须包含必要清理：`Sensor.stop()`、`Display.deinit()`、`MediaManager.deinit()`、`pl.destroy()`、`yolo.deinit()`、`os.exitpoint(...)` 等按实际使用选择。

桌面 Python 能编译通过，不代表 CanMV IDE 或 CanMV MicroPython 一定能解析通过。以保守语法和板端测试为准。

## 连接开发板测试流程

优先从仓库根目录执行：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py" --list-ports
```

运行短摄像头/LCD 测试：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py" ".\jlc-k230-lushan-pi\scripts\smoke_camera_lcd.py"
```

如果摄像头 id、构造方式或固件兼容性不确定，先跑：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py" ".\jlc-k230-lushan-pi\scripts\probe_k230_sensor_init.py"
```

运行模板时先从 RAM 测试，不要直接保存为板端 `main.py`：

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py" ".\jlc-k230-lushan-pi\assets\contest-template\examples\camera_lcd_preview.py"
```

只有用户明确要求写板端文件时，才使用 `mpremote` 部署：

```powershell
python ".\jlc-k230-lushan-pi\scripts\mpremote_deploy.py" --port COM14 main.py
```

需要保留 Ctrl-C 前的运行中画面时，先让用户把 `mpremote_snapshot.py --emit-hook image` 或 `--emit-hook chw` 输出的钩子加入 `main.py`，再拉取 `/sdcard/codex_snap.jpg` 或 `/sdcard/codex_snap.bin`。

如果串口无回显：

- 关闭 CanMV IDE 和其他串口终端。
- 用 `--list-ports` 确认端口还存在。
- 让 raw REPL helper 自动尝试 `2000000` 和 `115200`。
- 如果拔 SD 卡后串口消失，重新插回 SD 卡并重插 USB。
- 如果坏 `/sdcard/main.py` 阻塞 REPL，把它改名为 `main_disabled.py` 后重启。

## 离线运行规则

- CanMV 上电后先执行 TF 卡根目录 `boot.py`，再执行 `main.py`。
- 大多数电赛项目只需要 `main.py`。
- 不要在 `boot.py` 里放死循环。
- 调试阶段不要把未验证复杂脚本留作 `/sdcard/main.py`。
- 验收离线运行时必须经过完整复位或断电重启，而不只是 IDE 绿色运行按钮。

## Skill 维护规则

修改知识包时：

1. 先确定事实属于哪个文件，不要到处重复。
2. 新测试结论写入对应 `references/`。
3. 影响路由时更新 `SKILL.md`。
4. 影响可复用代码时更新 `assets/contest-template/`。
5. 新测试或重要修复写入 `references/maintenance.md` 的 Revision Log。
6. 在仓库根目录运行 `tools/validate.ps1`。
7. `tools/validate.ps1` 会调用 `scripts/validate_skill.py`、`quick_validate.py` 和所有 `.py` 模板的桌面语法检查。
8. 如需发布，优先使用仓库根目录的 `tools/publish.ps1`，并显式传 `-Files` 或 `-All`。
9. 如有开发板，尽量用 raw REPL 跑 smoke test 或相关模板。
10. 手动发布后重新复制 `jlc-k230-lushan-pi` 到 Codex skills 安装目录；如果使用 `tools/publish.ps1`，脚本会自动同步并校验安装副本。

推荐校验命令：

```powershell
.\tools\validate.ps1
.\tools\publish.ps1 -Message "Update skill" -Files @("jlc-k230-lushan-pi\SKILL.md")
```

## 禁止默认假设

- 不要假设 CanMV IDE 路径。
- 不要假设串口号固定。
- 不要假设 UART2 固定在某一组引脚。
- 不要假设模型、标签、例程路径固定。
- 不要假设 `cv_lite` 在所有固件都存在；先 probe，不能用时 fallback。
- 不要假设第三方 K230 速查表中的 API 结论适用于所有固件；先看 `references/canmv-api-known-issues.md` 的边界说明。
- 不要把 RKNN、RK3576、OpenCV/Linux 摄像头代码直接搬进 K230 CanMV。
- 不要在视觉坐标未稳定前驱动执行器。
- 不要在用户未授权时写 SD 卡或覆盖板端文件。
- 不要为了截图自动改写未知 `/sdcard/main.py`；优先使用显式快照钩子。

## 一句话使用提示

如果只能给另一个 Agent 一段短提示，使用：

```text
Use the jlc-k230-lushan-pi folder as a K230 CanMV knowledge pack. Read SKILL.md first, then follow its Quick Routing table. Prefer assets/contest-template examples, use conservative CanMV MicroPython syntax, keep the 3.1-inch LCD at 800x480 full-screen, run heavy vision at lower resolution and scale coordinates back, and do not write to SD card unless the user explicitly asks.
```
