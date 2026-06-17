# JLC K230 Lushan Pi Skill

This repository distributes an installable Codex skill for LCKFB/JLC Lushan Pi K230 CanMV projects.

The installable skill folder is:

```text
jlc-k230-lushan-pi/
```

Copy that folder exactly into a Codex skills directory. The repository root files are only for human-facing distribution notes; Codex loads the skill from `jlc-k230-lushan-pi/SKILL.md`.

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

## Install

### Windows PowerShell

From the repository root:

```powershell
$skills = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME "skills" } else { Join-Path $HOME ".codex\skills" }
New-Item -ItemType Directory -Force -Path $skills | Out-Null
Copy-Item -Recurse -Force ".\jlc-k230-lushan-pi" $skills
```

Restart Codex after copying if the skill list does not refresh automatically.

### Update Existing Install

After pulling or merging repository changes, copy the skill folder again so Codex uses the updated version:

```powershell
$skills = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME "skills" } else { Join-Path $HOME ".codex\skills" }
Remove-Item -Recurse -Force (Join-Path $skills "jlc-k230-lushan-pi") -ErrorAction SilentlyContinue
Copy-Item -Recurse -Force ".\jlc-k230-lushan-pi" $skills
```

Restart Codex if the old skill behavior remains visible after copying.

### macOS/Linux

From the repository root:

```bash
skills="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$skills"
cp -R ./jlc-k230-lushan-pi "$skills/"
```

Restart Codex after copying if the skill list does not refresh automatically.

## Install Check

After installation, the skill should exist at one of these locations:

```text
%CODEX_HOME%\skills\jlc-k230-lushan-pi\SKILL.md
%USERPROFILE%\.codex\skills\jlc-k230-lushan-pi\SKILL.md
$CODEX_HOME/skills/jlc-k230-lushan-pi/SKILL.md
$HOME/.codex/skills/jlc-k230-lushan-pi/SKILL.md
```

Typical request:

```text
Use $jlc-k230-lushan-pi to write a K230 CanMV main.py for rectangle detection on the 3.1-inch LCD.
```

## How To Use With Other Agents

For agents that do not automatically support Codex Skills, provide this instruction:

```text
Use the jlc-k230-lushan-pi folder as a K230 CanMV knowledge pack.
First read SKILL.md completely.
Then use the Quick Routing table in SKILL.md to choose only the needed files under references/.
Prefer reusable templates under assets/contest-template/.
For final CanMV main.py code, read references/canmv-micropython-compatibility.md and use conservative MicroPython syntax.
Resolve all scripts, references, and assets relative to the folder that contains SKILL.md.
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
- `scripts/smoke_camera_lcd.py`: short connected-board camera/LCD smoke test

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

Validate the skill with Codex's skill-creator validator when it is available:

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$validator = Join-Path $codexHome "skills\.system\skill-creator\scripts\quick_validate.py"
python $validator ".\jlc-k230-lushan-pi"
```

Run a temporary script on the connected K230 through raw REPL:

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py" ".\jlc-k230-lushan-pi\assets\contest-template\examples\camera_lcd_preview.py"
```

List serial ports before choosing `--port`:

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py" --list-ports
```

Run a short camera/LCD smoke test that exits automatically:

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py" ".\jlc-k230-lushan-pi\scripts\smoke_camera_lcd.py"
```

Run the board resource probe on K230, not desktop Python:

```powershell
python ".\jlc-k230-lushan-pi\scripts\run_canmv_raw_repl.py" ".\jlc-k230-lushan-pi\scripts\probe_board_resources.py"
```

## Important Notes

- The bundled compatibility notes are based partly on the tested firmware reference `CanMV_K230_LCKFB_micropython_v1.6-57-gce3418e_nncase_v2.11.0`.
- Treat that firmware string as a tested reference, not a universal requirement.
- Desktop `python -m py_compile` is useful but does not prove CanMV IDE parser compatibility.
- Do not assume a fixed CanMV IDE path. Ask for or discover `canmvide.exe`.
- If raw REPL connection fails, close CanMV IDE/serial terminals and inspect the helper's handshake log. Some firmware prints `MPY: soft reboot` before the ordinary `>>>` prompt appears. Use `--list-ports` to verify the selected serial port.
- Do not assume model paths such as `/data/...`; probe the board when possible.
- Do not drive actuators until camera/model/perception output is stable.
- Do not save to the board or write the TF card unless the user explicitly asks.

## Current Status

The skill has been validated with `quick_validate.py`.

Several templates have also been syntax-checked on desktop Python and adjusted toward conservative CanMV MicroPython style. The rectangle target tracker and the short camera/LCD smoke test have been tested on a connected Lushan Pi K230 through raw REPL; camera and LCD initialization succeeded.
