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
| Current environment, firmware, local setup facts | `references/environment-notes.md` | Known user setup without machine-specific paths |
| Skill maintenance, version drift, official doc changes | `references/maintenance.md` and `scripts/validate_skill.py` | Update policy, revision log, and local preflight checks |
| Applicability, limitations, and escalation rules | `references/usage-boundaries.md` | Scope boundaries before risky work |
| Connected-board smoke test or raw REPL connection failure | `references/canmv-workflows.md` and `references/troubleshooting.md` | Short hardware validation and serial diagnostics |
| mpremote deployment, board file copy, runtime screenshot pull | `references/mpremote-debug-workflows.md`, `references/offline-run-patterns.md`, and `references/troubleshooting.md` | Explicit board-write workflow and SD-card snapshot side-channel |
| Official links, firmware, IDE, downloads | `references/official-links.md` | Source-of-truth link map |
| Official API manual lookup | `references/api-manual-routing.md` | Pick the exact API page before using unfamiliar classes/functions |
| CanMV syntax compatibility, final `main.py` style, desktop compile mismatch | `references/canmv-micropython-compatibility.md` | Conservative MicroPython syntax rules |
| Built-in training examples | `references/local-code-examples.md` | Reuse absorbed contest-oriented patterns without depending on an external code folder |
| Hardware pins, power, connectors, camera/DSI/touch, voltage safety | `references/hardware-pin-resource-quickref.md` | Wiring and resource constraints |
| GPIO/FPIOA, PWM, UART, image drawing/processing/color/feature/code recognition | `references/official-basic-image-patterns.md` | Official example rules and code shapes |
| Circle/ring detection, Hough `find_circles`, full-screen LCD with low-res detection | `references/circle-detection-patterns.md` | Dual-channel circle detection strategy and template |
| Camera/LCD/peripheral CanMV bring-up | `references/canmv-workflows.md` | General CanMV workflow and skeletons |
| YOLOv5, YOLOv8, YOLO11, classify/detect/segment, KModel | `references/yolo-module-patterns.md` | Official YOLO lifecycle and parameters |
| User-style LCD/capture/YOLO/keypoint examples | `references/user-example-patterns.md` | Portable patterns distilled from prior working code |
| 2025-style rectangle target, laser aiming, ROI tracking, `cv_lite` rectangle corners, single-class model-assisted ROI | `references/contest-2025-rectangle-patterns.md` | Contest rectangle target strategy and enhanced UART tracker template |
| Contest architecture, runtime recovery, or reusable project start | `references/contest-patterns.md` and `assets/contest-template/` | Copyable project scaffold, integration rules, and safe-stop/recovery patterns |
| Offline run, `boot.py`, `main.py`, TF-card deployment | `references/offline-run-patterns.md` | Power-on deployment procedure |
| Any failure, logs, non-working hardware, no display, no model result | `references/troubleshooting.md` | Centralized debug checklist |

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
- For ready-to-copy CanMV `main.py`, use conservative MicroPython syntax: avoid f-strings, `lambda`, comprehensions, generator expressions, and complex multi-line inline calls unless the target firmware has been tested with them.
- For YOLO work, probe the board for actual `.kmodel` and official example paths before assuming `/data/...`; current LCKFB SD-card images may store examples and models under `/sdcard/examples/`.
- For contest features similar to the user's training examples, consult `references/local-code-examples.md` and use the corresponding `assets/contest-template/examples/` template before writing final code.
- After modifying this skill, run `scripts/validate_skill.py` plus the system `quick_validate.py` before publishing or syncing the installed copy.
