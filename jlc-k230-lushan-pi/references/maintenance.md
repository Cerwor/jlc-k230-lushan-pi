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
- 2026-06-18: Regression pass: documented the need to recopy the skill folder after repository updates because Codex loads the installed copy under the skills directory, not the development repository.
- 2026-06-18: Board recovery finding: removing the SD card made the CanMV USB serial disappear; reinserting the SD card while renaming a blocking `main.py` to `main_disabled.py` restored COM14, ordinary REPL, raw REPL, and the camera/LCD smoke test.
- 2026-06-18: Raw REPL robustness pass: extended the helper's `Ctrl-B` read window and skip redundant `Ctrl-C` when the ordinary `>>>` prompt is already visible.
- 2026-06-18: Board-tested the original rectangle template and found full-frame `800x480` `find_rects` ran at about 2 FPS; updated `rectangle_detect.py` to full-screen display plus `400x240` detection-channel scaling.
- 2026-06-18: Board-tested `color_line_tracking.py` and found the old `640x360` single-channel template ran around 11 FPS and did not match full-screen LCD guidance; updated it to full-screen display plus `400x240` detection-channel scaling.
- 2026-06-18: Board-tested `rectangle_target_uart_tracker.py` with a rectangle target. The old single-channel full-frame tracker ran around 8 FPS; the dual-channel tracker ran about 30-35 FPS and detected the target while keeping LCD-coordinate UART output semantics.
- 2026-06-18: Board-tested `circle_detect.py` with a bottle-cap target. The old `threshold=2500`, stride `4` settings missed the cap; parameter sweep found `threshold=1200`, stride `2`, producing `circles=1` at about 55-60 FPS with result hold enabled.
- 2026-06-18: Updated `scripts/run_canmv_raw_repl.py` to auto-try baud `2000000` then `115200` because COM14 sometimes returned no bytes at one baud while working at the other during repeated board tests; also made occupied-port/open failures report as a concise diagnostic instead of a Python traceback.
- 2026-06-18: UART2 loopback finding: a user shorted `PIN5/PIN6`, not the template default `PIN11/PIN12`. GPIO link scanning showed `PIN5/PIN6` matched, UART2 remapped to `PIN5/PIN6` received `rx=4`, and `scripts/probe_uart2_loopback.py` was added to auto-scan common UART2 FPIOA pairs before loopback testing.
- 2026-06-19: Long-run circle stability test with a bottle-cap target: `circle_detect.py` parameters ran 3000 frames through raw REPL on COM14 at about 63 FPS, with 999/1000 detection passes hitting, 2997/3000 overlay-visible frames, LCD center averaging `(403,213)` with x/y ranges `(384..422)/(196..226)`, radius range `52..86`, and no obvious memory leak (`mem_start=4000480`, `mem_end=3999424`).
- 2026-06-19: Offline auto-run smoke passed: a minimal TF-card-root `main.py` with camera preview, `Display.ST7701`, `800x480`, and `to_ide=False` showed `OFFLINE MAIN OK` on the 3.1-inch LCD, held about 61 FPS, and reappeared automatically after reset.
