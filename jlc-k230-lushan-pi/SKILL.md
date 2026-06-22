---
name: jlc-k230-lushan-pi
description: Build, port, debug, and deploy LCKFB/JLC Lushan Pi K230 CanMV projects for e-contest use. Use for CanMV MicroPython, K230 SDK, camera/LCD/image processing, GPIO/FPIOA/PWM/UART/I2C/SPI, YOLO/KModel, 3.1-inch LCD, offline main.py boot, mpremote deployment/snapshot pulls, official examples, and hardware troubleshooting.
---

# JLC K230 Lushan Pi

## Core Defaults

- Assume the board is the LCKFB/JLC Lushan Pi K230-CanMV development board.
- Assume the common host is Windows with CanMV IDE K230, but do not assume the IDE path. Ask for or discover `canmvide.exe` when needed.
- Treat `CanMV_K230_LCKFB_micropython_v1.6-57-gce3418e_nncase_v2.11.0` as a board-tested firmware reference version, not as a universal requirement.
- Assume the common display is the LCKFB 3.1-inch MIPI LCD expansion board; prefer `Display.ST7701`, `800x480`, and `display_mode = "lcd"`.
- Prefer CanMV MicroPython unless the user explicitly asks for K230 SDK/C, firmware building, or low-level porting.
- Treat work as contest-oriented: prioritize fast bring-up, stable wiring, visible diagnostics, safe fallback behavior, and code that can run offline as `main.py`.
- By default, provide the final offline program file/content only. The user usually copies `main.py` to the SD card manually; do not save to the board or write the TF card unless explicitly asked.

## Quick Routing

| User task | Read first | Use this result |
| --- | --- | --- |
| Bring-up, connected-board smoke tests, camera/LCD, raw REPL, setup facts | `references/canmv-workflows.md` and `references/troubleshooting.md` | Known firmware/setup facts, safe hardware validation, and failure diagnosis |
| Final CanMV `main.py`, API quirks, syntax compatibility, unfamiliar API calls | `references/canmv-api-known-issues.md` and `references/api-manual-routing.md` | Conservative MicroPython style plus official API page selection |
| Classical vision, circles, rectangles, colors, thresholds, template choice | This `Template Selection` table, then `references/circle-detection-patterns.md`, `references/contest-2025-rectangle-patterns.md`, or `references/official-basic-image-patterns.md` | Pick the right tested template before writing new code |
| Contest integration, UART/control output, pins, power, actuators, runtime recovery | `references/contest-patterns.md`, `references/hardware-pin-resource-quickref.md`, and `references/official-basic-image-patterns.md` | Safe control architecture and verified wiring/resource constraints |
| YOLO/KModel/PipeLine/model paths | `references/yolo-module-patterns.md` | Model lifecycle, display adaptation, and board resource probing |
| Offline boot, TF-card `main.py`, mpremote deploy, runtime snapshot pull | `references/offline-run-patterns.md`, `references/mpremote-debug-workflows.md`, and `references/troubleshooting.md` | Deployment path, board-write boundaries, and recovery steps |
| Skill maintenance, scope, official sources, version drift | `references/maintenance.md`, `references/usage-boundaries.md`, `references/official-links.md`, and `scripts/validate_skill.py` | Update policy, limitations, source links, and preflight checks |

## Template Selection

Prefer this table before browsing every file under `assets/contest-template/examples/`.

| Need | Start with | Read if needed |
| --- | --- | --- |
| Camera/LCD sanity check | `scripts/smoke_camera_lcd.py`, then `assets/contest-template/examples/camera_lcd_preview.py` | `references/canmv-workflows.md` |
| Bottle cap, ring, circle center | `scripts/probe_circle_target.py`, then `assets/contest-template/examples/circle_detect.py` | `references/circle-detection-patterns.md` |
| Black-tape rectangle target for control | `scripts/probe_cvlite_rectangle_target.py`, then `assets/contest-template/examples/cvlite_rectangle_target_uart_tracker.py` | `references/contest-2025-rectangle-patterns.md` |
| Rectangle smoke test or no `cv_lite` fallback | `assets/contest-template/examples/rectangle_detect.py`, then `assets/contest-template/examples/rectangle_target_uart_tracker.py` | `references/contest-2025-rectangle-patterns.md` |
| Field threshold calibration without a PC | `scripts/probe_otsu_threshold.py`, then `assets/contest-template/examples/offline_threshold_tuner.py` | `references/official-basic-image-patterns.md` |
| UART, servo, laser, PID control pieces | `assets/contest-template/examples/uart2_loopback.py`, `servo_laser_stepper_patterns.py`, `pid_target_centering.py` | `references/contest-patterns.md` and `references/hardware-pin-resource-quickref.md` |
| YOLO official example on 3.1-inch LCD | `assets/contest-template/examples/yolov8_lcd_official_launcher.py` | `references/yolo-module-patterns.md` |

## Working Rules

- Treat `agents/openai.yaml` as UI metadata only. The operational instructions live in `SKILL.md`, `references/`, and `assets/`.
- Resolve all bundled paths relative to the folder that contains this `SKILL.md`; do not rely on the original author's local filesystem paths.
- Verify board-specific facts through official references before making hardware claims.
- Check `usage-boundaries.md` before high-risk hardware, firmware, model-conversion, or unsupported-board work.
- Configure FPIOA before constructing `Pin`, `UART`, `PWM`, I2C, SPI, or other peripheral objects.
- Do not claim a pin assignment is safe unless it comes from the official pin/resource references, `fpioa.help(...)`, the user's schematic, or a user-provided working example.
- Keep constants at the top: display mode, frame size, pins, UART baud rate, thresholds, model path, labels, and control limits.
- For camera/display code, include cleanup for `Sensor.stop()`, `Display.deinit()`, `MediaManager.deinit()`, `pl.destroy()`, `yolo.deinit()`, and `os.exitpoint(...)` where applicable.
- For contest code, separate hardware init, perception, decision, actuation, telemetry, and cleanup.
- For integrated contest `main.py`, include safe output defaults, target-lost behavior, bounded frame-error recovery, and a visible fault state before enabling actuators.
- For real-time vision loops, default to LCD overlays and throttled prints; do not print every frame unless the user explicitly requests serial debugging.
- For final delivery, provide a ready-to-copy `main.py`; mention SD-card placement, but leave copying/flashing to the user unless explicitly requested.
- Treat `scripts/mpremote_deploy.py` and snapshot pull/delete options as explicit board-file operations. Do not run them unless the user asks to deploy, pull, patch, or delete board files.
- For runtime screenshots, prefer adding an explicit snapshot hook from `scripts/mpremote_snapshot.py --emit-hook ...` over automatically patching an unknown `/sdcard/main.py`.
- For ready-to-copy CanMV `main.py`, use `references/canmv-api-known-issues.md` conservative syntax rules: avoid f-strings, `lambda`, comprehensions, generator expressions, and complex multi-line inline calls unless the target firmware has been tested with them.
- For YOLO work, probe the board for actual `.kmodel` and official example paths before assuming `/data/...`; current LCKFB SD-card images may store examples and models under `/sdcard/examples/`.
- For contest features similar to the user's training examples, consult `references/local-code-examples.md` and use the corresponding `assets/contest-template/examples/` template before writing final code.
- After modifying this skill, run `scripts/validate_skill.py` plus the system `quick_validate.py` before publishing or syncing the installed copy.
