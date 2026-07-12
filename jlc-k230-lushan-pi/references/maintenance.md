# Maintenance

Use this file to keep the skill current as CanMV firmware, LCKFB wiki pages, and user project patterns evolve.

## Scope

Use this reference only when maintaining the skill, updating routing, changing bundled resources, or recording reusable board-tested conclusions.

## Contents

- Update Policy
- Update Steps
- Repository Tooling
- File Ownership Map
- Maintenance Summary
- Architecture Guardrails

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
- `references/sources-and-boundaries.md`: applicability boundaries, official source link index, and official API manual routing table.
- `references/canmv-api-known-issues.md`: compact K230 CanMV API pitfalls, conservative syntax, validation limits, and cross-firmware behavior notes.
- `references/model-vision-pipeline.md`: user-trained `.kmodel` packaging, validation gates, and contest model integration workflow.
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
- `scripts/run_canmv_raw_repl.py`: host-side helper for running MicroPython scripts from RAM over K230 raw REPL.
- `scripts/mpremote_deploy.py`: host-side helper for explicit `/sdcard` file deployment through `mpremote`.
- `scripts/mpremote_snapshot.py`: host-side helper for pulling and decoding runtime snapshot files written by explicit board hooks.
- `scripts/check_model_package.py`: host-side helper for validating a self-trained model package manifest, labels, and `.kmodel` before board integration.
- `scripts/probe_k230_sensor_init.py`: board-side diagnostic for trying several K230 `Sensor` construction and snapshot modes.
- `scripts/probe_otsu_threshold.py`: board-side bounded Otsu grayscale threshold calibration probe for black/white targets.
- `scripts/probe_cvlite_rectangle_target.py`: board-side bounded 300-frame cv_lite rectangle target probe with hit count, FPS, candidate, center-range, jump, and memory telemetry.
- `scripts/probe_circle_target.py`: board-side bounded 300-frame circle target probe with detection-hit, overlay, FPS, center/radius range, jump, and memory telemetry.
- `scripts/probe_yolo_runtime.py`: board-side bounded YOLO runtime/resource probe for `nncase_runtime`, `aicube`, `PipeLine`, YOLOv5/YOLOv8/YOLO11, `.kmodel`, and YOLO example discovery.
- `scripts/evaluate_probe_log.py`: host-side acceptance explainer for rectangle, circle, YOLO, UART, and resource probe logs.
- `scripts/validate_skill.py`: host-side preflight checker for skill structure, Python syntax, CanMV conservative syntax, doc references, local paths, and cache artifacts.
- `scripts/smoke_camera_lcd.py`: board-side short smoke test for default camera and 3.1-inch LCD.
- `assets/contest-template/`: copyable starter project.
- `assets/model-package/`: manifest template for packaging self-trained `.kmodel` deployments.

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

## Architecture Guardrails

- Every long reference must have early `## Scope` and `## Contents` sections so an agent can decide whether to continue reading.
- `SKILL.md` remains the routing source. README and AGENT_USAGE may point at it but should not duplicate the full routing matrix.
- Keep repository-only files such as `README.md`, `LICENSE`, `.github/`, `docs/`, `tests/`, `requirements-host.txt`, and root `tools/` outside the installable `jlc-k230-lushan-pi/` skill folder.
- Add new templates only when `contest-patterns.md#template-admission-rules` is satisfied.
- Keep generic actuator guidance in `contest-patterns.md`; keep ZDT command frames only in `zdt-stepper-gimbal-patterns.md`.
- Keep only reusable conclusions here. Move raw chronological board-test details to repository-level `docs/BOARD_TEST_LOG.md`.

Recent maintenance entries:

- 2026-06-28: Added board-tested ZDT two-axis gimbal control notes: yaw `0x01`, pitch `0x02`, UART2 `PIN5/PIN6`, `cv_lite` rectangle precheck, target-loss stop, ACK retry guidance, and four-direction convergence results.
- 2026-06-28: Added full ZDT gimbal tracking results after removing the short-test cumulative-angle limiter, including `7200`-frame tracking telemetry, lost-stop behavior, and the need for `LOST_STOP -> REACQUIRE -> TRACK` in final continuous-operation code.
- 2026-06-28: Added self-trained single-class YOLOv8 `best.kmodel` board-test notes and ZDT model-tracking tuning guidance, including FC ACK sampling, time-based control periods, target smoothing, and position-feedback validation.
- 2026-06-29: Added reusable direct-UART ZDT speed-mode rectangle tracking guidance and cleaned third-party project URLs from operational references so only portable experience remains.
- 2026-06-29: Slimmed `SKILL.md` working rules, added probe-result action guidance, documented raw-REPL Plan B, and strengthened `agents/openai.yaml` default prompt.
- 2026-06-30: Added host-side CI, dependency manifest, regression tests, mpremote safety hardening, reference Scope guardrails, and repository/skill boundary checks.
- 2026-07-12: Added board-tested continuous `cv_lite` rectangle plus ZDT `F6` tracking lessons: consecutive-hit arming, four-corner center averaging, ACK-aware two-axis UART timing, lost-target rearming, and removal of short-test cumulative displacement latches from explicitly unlimited trackers.
