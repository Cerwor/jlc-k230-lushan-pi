# JLC K230 Lushan Pi Skill

This document explains how to use the `jlc-k230-lushan-pi` skill as a human-readable guide or as a knowledge pack for agents that do not automatically support Codex Skills.

Skill folder:

```text
E:\Codex_WorkSpace\jlc-k230-lushan-pi
```

## Purpose

This skill helps an agent create, port, debug, and deploy LCKFB/JLC Lushan Pi K230 CanMV projects, especially electronic-design-contest projects.

It focuses on:

- CanMV MicroPython on Lushan Pi K230
- 3.1-inch ST7701 MIPI LCD workflows
- camera, LCD, GPIO/FPIOA, UART, PWM, I2C, SPI examples
- image processing such as rectangles, circles, color blobs, lines, QR/barcode/AprilTag
- YOLO/KModel/AI demo use on K230
- offline `main.py` deployment
- contest-oriented project templates and troubleshooting

## How To Use With Codex

In Codex, install or expose the skill folder as a normal Skill. Codex should automatically trigger it when the user asks about Lushan Pi K230, CanMV, K230 contest projects, YOLO/KModel, camera/LCD, or related peripherals.

Typical request:

```text
Use $jlc-k230-lushan-pi to write a K230 CanMV main.py for rectangle detection on the 3.1-inch LCD.
```

## How To Use With Other Agents

For agents such as Claude Code, opencode, or other coding assistants, provide this instruction:

```text
Use E:\Codex_WorkSpace\jlc-k230-lushan-pi as a K230 CanMV knowledge pack.
First read SKILL.md completely.
Then use the Quick Routing table in SKILL.md to choose only the needed files under references/.
Prefer reusable templates under assets/contest-template/.
For final CanMV main.py code, read references/canmv-micropython-compatibility.md and use conservative MicroPython syntax.
By default, provide a ready-to-copy main.py; do not write to SD card or save to the board unless explicitly requested.
```

## Directory Map

```text
jlc-k230-lushan-pi/
  SKILL.md
  agents/
    openai.yaml
  references/
  assets/
    contest-template/
  scripts/
```

Important files:

- `SKILL.md`: main routing table and global rules
- `references/canmv-micropython-compatibility.md`: conservative CanMV syntax rules
- `references/canmv-workflows.md`: camera, LCD, peripheral bring-up workflow
- `references/official-basic-image-patterns.md`: GPIO/FPIOA/PWM/UART and image-processing patterns
- `references/circle-detection-patterns.md`: full-screen LCD plus low-resolution circle detection
- `references/contest-2025-rectangle-patterns.md`: rectangle target and UART tracking strategy
- `references/yolo-module-patterns.md`: YOLOv5, YOLOv8, YOLO11 and KModel guidance
- `references/offline-run-patterns.md`: `main.py` and `boot.py` offline deployment
- `references/troubleshooting.md`: centralized debug checklist
- `assets/contest-template/`: copyable contest project scaffold
- `scripts/run_canmv_raw_repl.py`: run a script on K230 through raw REPL from RAM
- `scripts/probe_board_resources.py`: run on the board to find `.kmodel` and example files

## Default Development Flow

1. Read `SKILL.md`.
2. Use the Quick Routing table to select the relevant reference file.
3. Start from the closest template in `assets/contest-template/examples/`.
4. Keep constants at the top of the program.
5. Use full-screen `800x480` LCD output for the 3.1-inch screen unless a debug view is explicitly requested.
6. For expensive image algorithms, use low-resolution detection and scale coordinates back to LCD coordinates.
7. Use LCD overlays and throttled serial prints instead of printing every frame.
8. Keep final code conservative for CanMV MicroPython.
9. Provide `main.py`; the user normally copies it to the SD card manually.

## Useful Commands

Validate the Skill with Codex's skill creator validator:

```powershell
python C:\Users\Cerwor\.codex\skills\.system\skill-creator\scripts\quick_validate.py E:\Codex_WorkSpace\jlc-k230-lushan-pi
```

Run a temporary script on the connected K230 through raw REPL:

```powershell
python E:\Codex_WorkSpace\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py E:\Codex_WorkSpace\jlc-k230-lushan-pi\assets\contest-template\examples\camera_lcd_preview.py
```

Run the board resource probe on K230, not desktop Python:

```powershell
python E:\Codex_WorkSpace\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py E:\Codex_WorkSpace\jlc-k230-lushan-pi\scripts\probe_board_resources.py
```

## Important Notes

- The user's known firmware reference is `CanMV_K230_LCKFB_micropython_v1.6-57-gce3418e_nncase_v2.11.0`.
- Treat that firmware string as a reference, not a universal requirement.
- Desktop `python -m py_compile` is useful but does not prove CanMV IDE parser compatibility.
- Do not assume a fixed CanMV IDE path. Ask for or discover `canmvide.exe`.
- Do not assume model paths such as `/data/...`; probe the board when possible.
- Do not drive actuators until camera/model/perception output is stable.
- Do not save to the board or write the TF card unless the user explicitly asks.

## Current Status

The skill has been validated with `quick_validate.py`.

Several templates have also been syntax-checked on desktop Python and adjusted toward conservative CanMV MicroPython style. The rectangle target tracker has been tested on a connected Lushan Pi K230 through raw REPL for a limited run; camera and LCD initialization succeeded.
