# Maintenance

Use this file to keep the skill current as CanMV firmware, LCKFB wiki pages, and user project patterns evolve.

## Update Policy

Update this skill when:

- The user's firmware string changes.
- Official LCKFB wiki pages move, rename, or change API signatures.
- CanMV IDE changes offline-save behavior.
- YOLO/PipeLine/Ai2d/AIBase constructor parameters change.
- New working user examples prove a better contest pattern.
- Hardware notes change for a new board revision, expansion board, screen, or camera.

## Update Steps

1. Record the new firmware/version/source in this file or `environment-notes.md`.
2. Update only the relevant reference file; avoid duplicating the same fact in multiple places.
3. If the change affects routing, update `SKILL.md`.
4. If the change affects reusable project code, update `assets/contest-template/`.
5. Move troubleshooting facts to `troubleshooting.md`, not task-specific reference files.
6. Run `quick_validate.py` on the skill folder.
7. Syntax-check any Python files in `assets/contest-template/` where possible.
8. When hardware is available, run final-style templates in CanMV IDE or with `scripts/run_canmv_raw_repl.py`; desktop `py_compile` alone does not prove CanMV parser compatibility.

## File Ownership Map

- `SKILL.md`: compact trigger context, quick routing, and global working rules.
- `agents/openai.yaml`: UI metadata only; not an operational prompt.
- `references/official-links.md`: source link index.
- `references/api-manual-routing.md`: official API manual routing table.
- `references/canmv-micropython-compatibility.md`: conservative CanMV MicroPython syntax style and validation limits.
- `references/local-code-examples.md`: built-in contest-oriented training patterns.
- `references/environment-notes.md`: known user setup and firmware references.
- `references/hardware-pin-resource-quickref.md`: hardware resources, power, voltage, connectors, camera/DSI/touch.
- `references/official-basic-image-patterns.md`: official GPIO/FPIOA/PWM/UART and image-recognition example patterns.
- `references/circle-detection-patterns.md`: circle/ring detection strategy, dual-channel display/detection mode, ROI/coordinate rules, and FPS cautions.
- `references/canmv-workflows.md`: normal CanMV bring-up workflows and skeletons.
- `references/yolo-module-patterns.md`: official YOLO module lifecycle and parameters.
- `references/user-example-patterns.md`: portable patterns distilled from user working examples.
- `references/contest-2025-rectangle-patterns.md`: 2025-style rectangle target tracking, single-class model-assisted ROI, and UART coordinate output.
- `references/contest-patterns.md`: contest architecture and template usage.
- `references/offline-run-patterns.md`: normal offline deployment.
- `references/troubleshooting.md`: centralized failure diagnosis.
- `references/usage-boundaries.md`: scope, assumptions, and escalation rules.
- `scripts/run_canmv_raw_repl.py`: host-side helper for running MicroPython scripts from RAM over K230 raw REPL.
- `scripts/smoke_camera_lcd.py`: board-side short smoke test for default camera and 3.1-inch LCD.
- `assets/contest-template/`: copyable starter project.

## Revision Log

- 2026-06-13: Created and validated the initial Lushan Pi K230 skill with official wiki links, CanMV workflows, YOLO module notes, offline deployment, hardware quick reference, centralized troubleshooting, usage boundaries, maintenance policy, and a copyable contest template.
- 2026-06-13: Recorded user preference that Codex should normally provide the final offline `main.py` only; the user manually copies it to the SD card unless explicit save/write action is requested.
- 2026-06-13: Added lessons from live YOLOv8 board test: probe actual board model paths before assuming `/data/...`; tested SD card stored models/examples under `/sdcard/examples/`; official YOLOv8 example needed HDMI-to-LCD display mode adaptation; successful LCD run reached about 29 FPS and was saved to board `main.py` after explicit user approval.
- 2026-06-13: Added board-tested rectangle detection example and replaced `sys.print_exception(e)` in templates with `print("error:", e)` for compatibility with the tested firmware.
- 2026-06-13: Added official API manual routing and absorbed useful training examples into built-in Skill references/templates so the skill is self-contained.
- 2026-06-15: Added lessons from `abcDesolate/25-vision-collection`: 2025-style rectangle target strategy, single-class `AnchorBaseDet` ROI-assist notes, and an enhanced rectangle UART tracker template.
- 2026-06-15: Board-tested `rectangle_target_uart_tracker.py` through raw REPL on COM14/baud 2000000 for 60 frames. Camera/LCD initialized, `gc2093_csi2` was detected, no target was present, and the 800x480 grayscale/binary/full-frame rectangle search ran at about 8 FPS. Added `scripts/run_canmv_raw_repl.py` for repeatable RAM-only tests without saving to SD.
- 2026-06-15: Added circle-detection lessons from Skill usage: avoid full-frame `800x480` `find_circles`, default to full-screen LCD with low-resolution detection, clarify detection/LCD coordinate spaces, throttle serial prints, document `Display.bind_layer` tradeoff, and add `circle_detect.py`.
- 2026-06-15: Added CanMV MicroPython conservative syntax guidance after a script passed desktop `py_compile` but failed in CanMV IDE with `SyntaxError`. Final templates should avoid f-strings, `lambda`, comprehensions, generator expressions, and complex inline/multi-line calls unless the target firmware has been tested.
- 2026-06-15: Self-check pass: made key templates more conservative by replacing `.format(...)` with `%` formatting, replacing a YOLO class dictionary dispatch with `if/elif`, removing remaining template list comprehensions, and making `probe_board_resources.py` warn when it is run on desktop Python instead of the K230 board.
- 2026-06-16: Made the distribution package portable for other users by removing author-local install paths from the top-level README, documenting copy-based installation, clarifying that bundled paths are relative to `SKILL.md`, and describing the firmware string as a board-tested reference rather than a current-user requirement.
- 2026-06-16: Debug pass: removed remaining conditional expressions from CanMV templates, removed a generator expression from the board resource probe, and kept template code closer to conservative MicroPython style.
- 2026-06-17: Improved raw REPL host helper with retry and handshake diagnostics after a board sometimes printed `MPY: soft reboot` before accepting `Ctrl-A`; added `scripts/smoke_camera_lcd.py` for 20-frame camera/LCD validation.
- 2026-06-18: Regression pass: added `--list-ports` to the raw REPL helper, included target port/baud in no-byte diagnostics, and reported board-side `Traceback` separately from upload timeouts.
