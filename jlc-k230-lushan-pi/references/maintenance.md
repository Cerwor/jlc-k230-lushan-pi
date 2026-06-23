# Maintenance

Use this file to keep the skill current as CanMV firmware, LCKFB wiki pages, and user project patterns evolve.

## Contents

- Update Policy
- Update Steps
- Repository Tooling
- File Ownership Map
- Maintenance Summary

## Update Policy

Update this skill when:

- The user's firmware string changes.
- Official LCKFB wiki pages move, rename, or change API signatures.
- CanMV IDE changes offline-save behavior.
- YOLO/PipeLine/Ai2d/AIBase constructor parameters change.
- New working user examples prove a better contest pattern.
- Hardware notes change for a new board revision, expansion board, screen, or camera.

## Update Steps

1. Record the new firmware/version/source in this file or `canmv-workflows.md`.
2. Update only the relevant reference file; avoid duplicating the same fact in multiple places.
3. If the change affects routing, update `SKILL.md`.
4. If the change affects reusable project code, update `assets/contest-template/`.
5. Move troubleshooting facts to `troubleshooting.md`, not task-specific reference files.
6. In the distribution repository, use `docs/TEST_MATRIX.md` to choose the smallest useful test.
7. Prefer root `tools/test.ps1`; by default it calls `tools/validate.ps1` and keeps hardware tests opt-in.
8. Use `tools/test.ps1 -Board` for raw-REPL smoke tests and `tools/test.ps1 -Board -Vision all-core` for camera/LCD, Sensor initialization, and Otsu threshold probes.
9. If the root tools are unavailable, run `scripts/validate_skill.py` from this skill, then run `quick_validate.py` on the skill folder.
10. Syntax-check any Python files in `assets/contest-template/` where possible.
11. When hardware is available, run final-style templates in CanMV IDE or with `scripts/run_canmv_raw_repl.py`; desktop `py_compile` alone does not prove CanMV parser compatibility.
12. Put long chronological test notes in repository-level `docs/BOARD_TEST_LOG.md`, not in this installable reference.

## Repository Tooling

These scripts live in the distribution repository root and are not part of the installed skill folder:

- `tools/test.ps1`: layered test entrypoint. Default runs offline validation only; `-ListPorts` enumerates serial ports; `-Board` runs RAM-only raw REPL tests; `-Vision all-core` runs camera/LCD smoke, Sensor mode probing, and Otsu threshold probing; `-Vision resources` runs the bounded board resource probe; `-Vision rect-target` and `-Vision circle-target` run target-specific bounded probes; `-Vision yolo` probes YOLO runtime/resources; `-Vision uart-loopback` runs UART2 loopback/TX sweep. Supported probe modes automatically call `scripts/evaluate_probe_log.py`.
- `tools/validate.ps1`: offline preflight that calls this skill's `scripts/validate_skill.py`, the system `quick_validate.py`, and desktop Python syntax checks.
- `tools/publish.ps1`: validation, branch, commit, PR, squash-merge, local sync, installed-skill sync, and installed-copy validation.

## File Ownership Map

- `SKILL.md`: compact trigger context, quick routing, and global working rules.
- `agents/openai.yaml`: UI metadata only; not an operational prompt.
- `references/official-links.md`: source link index.
- `references/api-manual-routing.md`: official API manual routing table.
- `references/canmv-api-known-issues.md`: compact K230 CanMV API pitfalls, conservative syntax, validation limits, and cross-firmware behavior notes.
- `references/local-code-examples.md`: built-in contest-oriented training patterns.
- `references/hardware-pin-resource-quickref.md`: hardware resources, power, voltage, connectors, camera/DSI/touch.
- `references/official-basic-image-patterns.md`: official GPIO/FPIOA/PWM/UART and image-recognition example patterns.
- `references/mpremote-debug-workflows.md`: optional host-side `mpremote` deployment and runtime snapshot workflows.
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
- `scripts/mpremote_deploy.py`: host-side helper for explicit `/sdcard` file deployment through `mpremote`.
- `scripts/mpremote_snapshot.py`: host-side helper for pulling and decoding runtime snapshot files written by explicit board hooks.
- `scripts/probe_k230_sensor_init.py`: board-side diagnostic for trying several K230 `Sensor` construction and snapshot modes.
- `scripts/probe_otsu_threshold.py`: board-side bounded Otsu grayscale threshold calibration probe for black/white targets.
- `scripts/probe_cvlite_rectangle_target.py`: board-side bounded 300-frame cv_lite rectangle target probe with hit count, FPS, candidate, center-range, jump, and memory telemetry.
- `scripts/probe_circle_target.py`: board-side bounded 300-frame circle target probe with detection-hit, overlay, FPS, center/radius range, jump, and memory telemetry.
- `scripts/probe_yolo_runtime.py`: board-side bounded YOLO runtime/resource probe for `nncase_runtime`, `aicube`, `PipeLine`, YOLOv5/YOLOv8/YOLO11, `.kmodel`, and YOLO example discovery.
- `scripts/evaluate_probe_log.py`: host-side acceptance explainer for rectangle, circle, YOLO, UART, and resource probe logs.
- `scripts/validate_skill.py`: host-side preflight checker for skill structure, Python syntax, CanMV conservative syntax, doc references, local paths, and cache artifacts.
- `scripts/smoke_camera_lcd.py`: board-side short smoke test for default camera and 3.1-inch LCD.
- `assets/contest-template/`: copyable starter project.

## Maintenance Summary

Keep this installable reference compact. Put task-specific facts in the task reference, not in a chronological log. Keep detailed historical board-test notes in the distribution repository file `docs/BOARD_TEST_LOG.md`, which is intentionally outside the installed skill.

Current tested baseline:

- Lushan Pi K230 CanMV with GC2093 camera and 3.1-inch ST7701 LCD.
- `scripts/run_canmv_raw_repl.py` is the default RAM-only board-test path and does not write `/sdcard/main.py`.
- `tools/test.ps1` is the repository-level layered test entrypoint; use `-Board` only when hardware is intentionally involved.
- `tools/test.ps1` prints `ACCEPT_* status=pass|warn|fail` for target/resource probes. Treat `warn` as a prompt to check placement, lighting, wiring, or SD-card resources before integration.
- `tools/test.ps1 -Board -Vision yolo -Port COM14` is board-tested with `ACCEPT_YOLO status=pass` on the current SD-card image: YOLO imports passed, 63 `.kmodel` files and 54 YOLO/detection examples were found, and `truncated=0`.
- `tools/test.ps1 -Board -Vision uart-loopback -Port COM14` is board-tested with `ACCEPT_UART status=pass` when the current loopback short connects `PIN5/PIN6`: UART2 remap received 63 bytes.
- `cv_lite` grayscale rectangle tracking is the preferred black-tape rectangle target path on the tested firmware.
- Circle detection is useful but more scene-sensitive; use raw-vs-tracked telemetry from `probe_circle_target.py` to judge field quality.
- `mpremote_deploy.py` and snapshot pull/delete paths are explicit board-file workflows; dry-run is safe for command preview.

Recent maintenance entries:

- 2026-06-22: Added layered root `tools/test.ps1` with offline validation, smoke, Sensor, Otsu, resources, rectangle target, and circle target modes.
- 2026-06-22: Bounded `probe_board_resources.py` after a populated SD-card scan could time out and leave raw REPL silent until reset.
- 2026-06-22: Allowed `mpremote_deploy.py --dry-run` to work without host `mpremote` installed.
- 2026-06-22: Productized rectangle and circle target probes and recorded their latest board-test behavior in the relevant references.
- 2026-06-23: Added tiered reference-loading guidance, YOLO runtime probing, and probe-log acceptance explanations for rectangle, circle, YOLO, UART, and resource tests.
- 2026-06-23: Board-tested the new YOLO and UART acceptance modes after reset; fixed `probe_yolo_runtime.py` resource caps/de-duplication so it reaches YOLO example directories before reporting acceptance.
- 2026-06-23: Cleaned stale maintenance anchors, made `user-example-patterns.md` directly reachable from `SKILL.md`, and extended conservative syntax validation to the target-specific board probes.
