---
name: jlc-k230-lushan-pi
description: Build, port, debug, and deploy LCKFB/JLC Lushan Pi K230 CanMV projects for e-contest use. Use for CanMV MicroPython, K230 SDK, camera/LCD/image processing, GPIO/FPIOA/PWM/UART/I2C/SPI, YOLO/KModel, 3.1-inch LCD, offline main.py boot, mpremote deployment/snapshot pulls, ZDT closed-loop stepper gimbals, laser aiming/tracing, official examples, and hardware troubleshooting.
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

Load references in tiers. Always read `SKILL.md` first, then read only the Tier-1 file for the task. Open Tier-2 files only when the task needs that detail or the first attempt fails.

| User task | Read first | Use this result |
| --- | --- | --- |
| Bring-up, connected-board smoke tests, camera/LCD, raw REPL, setup facts | Tier-1: `references/canmv-workflows.md`; Tier-2 on failure: `references/troubleshooting.md` | Known firmware/setup facts, safe hardware validation, and failure diagnosis |
| Final CanMV `main.py`, API quirks, syntax compatibility, unfamiliar API calls | Tier-1: `references/canmv-api-known-issues.md`; Tier-2 for official lookup: `references/sources-and-boundaries.md` | Conservative MicroPython style plus official API page selection |
| Classical vision, circles, rectangles, colors, thresholds, template choice | Tier-1: this `Template Selection` table; Tier-2: only the matching task reference | Pick the right tested template before writing new code |
| Contest integration, UART/control output, pins, power, actuators, generic laser/gimbal target following, runtime recovery | Tier-1: `references/contest-patterns.md`; Tier-2 for pins: `references/hardware-pin-resource-quickref.md`; Tier-2 for basic APIs: `references/official-basic-image-patterns.md` | Safe control architecture, generic actuator boundaries, and verified wiring/resource constraints |
| Confirmed ZDT XS-series closed-loop stepper, Emm/ZDT free protocol, fixed `0x6B` checksum, `F1/FC` fast position deltas | Tier-1: `references/zdt-stepper-gimbal-patterns.md`; Tier-2 for pins/safety: `references/hardware-pin-resource-quickref.md` and `references/contest-patterns.md` | Tested ZDT-specific command frames, UART2 mapping caveats, fast-position loop, and motor safety strategy |
| Porting user examples, matching prior project style, training/data-collection patterns | Tier-1: `references/local-code-examples.md`; Tier-2 for the user's prior working-code style: `references/user-example-patterns.md` | Reuse portable patterns without depending on local paths or external folders |
| Self-trained `.kmodel`, model package, YOLO/KModel/PipeLine/model paths | Tier-1: `references/model-vision-pipeline.md`; Tier-2 for board code: `references/yolo-module-patterns.md`; Tier-2 if paths are unknown: run `scripts/probe_yolo_runtime.py` or `scripts/probe_board_resources.py` | Model package contract, validation gates, model lifecycle, display adaptation, and board resource probing |
| Offline boot, TF-card `main.py`, mpremote deploy, runtime snapshot pull | Tier-1: `references/offline-run-patterns.md`; Tier-2 for mpremote/snapshot: `references/mpremote-debug-workflows.md`; Tier-2 on failure: `references/troubleshooting.md` | Deployment path, board-write boundaries, and recovery steps |
| Skill maintenance, scope, official sources, version drift | Tier-1: `references/maintenance.md`; Tier-2 for boundaries/sources: `references/sources-and-boundaries.md` and `scripts/validate_skill.py` | Update policy, limitations, source links, and preflight checks |

## Template Selection

Prefer this table before browsing every file under `assets/contest-template/examples/`.

| Need | Start with | Read if needed |
| --- | --- | --- |
| Camera/LCD sanity check | `scripts/smoke_camera_lcd.py`, then `assets/contest-template/examples/camera_lcd_preview.py` | `references/canmv-workflows.md` |
| Bottle cap, ring, circle center | `scripts/probe_circle_target.py`, then `assets/contest-template/examples/circle_detect.py` | `references/circle-detection-patterns.md` |
| Black-tape rectangle target for control | `scripts/probe_cvlite_rectangle_target.py`, then `assets/contest-template/examples/cvlite_rectangle_target_uart_tracker.py` | `references/contest-2025-rectangle-patterns.md` |
| Rectangle smoke test or no `cv_lite` fallback | `assets/contest-template/examples/rectangle_detect.py`, then `assets/contest-template/examples/rectangle_target_uart_tracker.py` | `references/contest-2025-rectangle-patterns.md` |
| Field threshold calibration without a PC | `scripts/probe_otsu_threshold.py`, then `assets/contest-template/examples/offline_threshold_tuner.py` | `references/official-basic-image-patterns.md` |
| Generic UART, servo, laser, PID, unknown gimbal actuator | `assets/contest-template/examples/uart2_loopback.py`, `servo_laser_stepper_patterns.py`, `pid_target_centering.py` | `references/contest-patterns.md` and `references/hardware-pin-resource-quickref.md` |
| Confirmed ZDT closed-loop stepper gimbal axis | `references/zdt-stepper-gimbal-patterns.md`, then adapt `assets/contest-template/examples/pid_target_centering.py` | `references/contest-patterns.md` |
| Self-trained `.kmodel` after user conversion | `assets/model-package/model_manifest.example.json`, then `scripts/check_model_package.py` | `references/model-vision-pipeline.md` |
| YOLO official example on 3.1-inch LCD | `scripts/probe_yolo_runtime.py`, then `assets/contest-template/examples/yolov8_lcd_official_launcher.py` | `references/yolo-module-patterns.md` |

Use `scripts/evaluate_probe_log.py` to interpret bounded probe output for rectangle, circle, YOLO, UART, and board-resource tests. Repository `tools/test.ps1` calls it automatically for supported board-test modes. For `ACCEPT_* status=warn|fail`, read `references/troubleshooting.md#probe-result-actions` before enabling actuators or changing final code.

## Working Rules

- Treat `agents/openai.yaml` as UI metadata only. The operational instructions live in `SKILL.md`, `references/`, and `assets/`.
- Resolve all bundled paths relative to the folder that contains this `SKILL.md`; do not rely on the original author's local filesystem paths.
- Verify board-specific facts through official references before making hardware claims.
- Check `sources-and-boundaries.md` before high-risk hardware, firmware, model-conversion, unsupported-board work, or unfamiliar official API calls.
- Keep constants at the top: display mode, frame size, pins, UART baud rate, thresholds, model path, labels, and control limits.
- For any board write, default to `STANDARD`; use `QUICK_PATCH` only when every gate in `references/offline-run-patterns.md#deployment-mode-gate` passes, and enter `RECOVERY` only after a deployment attempt fails.
- For final delivery, provide a ready-to-copy `main.py`; mention SD-card placement, but leave copying/flashing to the user unless explicitly requested.
- For ready-to-copy CanMV `main.py`, use `references/canmv-api-known-issues.md` conservative syntax rules: avoid f-strings, `lambda`, comprehensions, generator expressions, and complex multi-line inline calls unless the target firmware has been tested with them.
- For user-trained models, assume the user trains and converts to `.kmodel`; request the `.kmodel`, label order, input size, task type, and conversion notes, then validate the package before writing final board code.
- For contest features similar to the user's training examples, consult `references/local-code-examples.md` and use the corresponding `assets/contest-template/examples/` template before writing final code.
- After modifying this skill, run `scripts/validate_skill.py` plus the system `quick_validate.py` before publishing or syncing the installed copy.
