# Maintenance

Use this file only when changing the skill package, routing, reusable assets, validators, or firmware-specific conclusions.

## Scope

This reference owns update policy, package boundaries, test entrypoints, and architecture guardrails. Task guidance belongs in its domain reference; chronological evidence belongs in the repository test log.

## Contents

- Update Policy
- Change Workflow
- Test Entrypoints
- Ownership Map
- Tested Baseline
- Architecture Guardrails

## Update Policy

Update the skill when:

- firmware or bundled CanMV APIs change;
- an official source moves or changes a signature;
- a new board revision, camera, LCD, connector, or power path changes a hardware fact;
- a repeated field failure proves that an existing workflow is incomplete;
- a reusable project pattern passes bounded board testing.

Record confidence explicitly: board-tested on a named firmware, documented by an official source, inferred from an example, or still unverified.

## Change Workflow

1. Identify one owning reference; do not add the same operational fact to several files.
2. Update `SKILL.md` only when routing or a global invariant changes.
3. Update a template only when the behavior is reusable, configurable, and accepted by `references/control/contest-patterns.md#template-admission-rules`.
4. Put symptoms and recovery actions in `references/platform/troubleshooting.md`.
5. Put detailed run counters, dates, and transient board state in repository `docs/BOARD_TEST_LOG.md`.
6. For a published behavior change, update the installable `VERSION` and repository `CHANGELOG.md` using semantic `MAJOR.MINOR.PATCH` versioning.
7. Run the installable validator and system `quick_validate.py`.
8. Run host regression tests before publishing.
9. Add the smallest relevant RAM-only board probe when hardware evidence is needed.
10. Recheck the installed copy after synchronization.

Desktop compilation verifies host syntax only. Final CanMV programs must still follow `references/platform/canmv-api-known-issues.md` and, when practical, run on the target firmware.

## Test Entrypoints

The installed skill is self-contained:

```powershell
python .\scripts\validate_skill.py .
python .\scripts\run_board_probe.py --list-ports
python .\scripts\run_board_probe.py --vision all-core --port COM14
python .\scripts\run_board_probe.py --vision resource-cycle --port COM14
```

`run_board_probe.py` dispatches bounded raw-REPL probes from RAM, automatically evaluates supported telemetry, and never writes `/sdcard/main.py`.

The distribution repository may additionally provide:

- `tools/validate.ps1`: local validator plus system quick validation;
- `tools/test.ps1`: validation, all host unit tests, and optional delegation to the installable board-probe entry;
- `tools/publish.ps1`: branch, commit, PR, merge, sync, and installed-copy validation after the full test gate passes.

Root tools are convenience wrappers, not dependencies of the installed skill.

## Ownership Map

| Area | Owner |
| --- | --- |
| Trigger, defaults, and routing | `SKILL.md` |
| UI metadata | `agents/openai.yaml` |
| Platform setup, API quirks, pins, and failures | `references/platform/` |
| Classical vision, models, and YOLO | `references/vision/` |
| Contest integration and actuator protocols | `references/control/` |
| Offline boot, deployment, and snapshots | `references/deployment/` |
| Sources, adaptation, and package maintenance | `references/maintenance/` |
| Stable host CLI and shared helpers | top-level files under `scripts/` |
| Self-contained CanMV board probes | `scripts/probes/`, registered in `run_board_probe.py` |
| Copyable hardware, vision, control, and model starts | `assets/contest-template/examples/` category directories |
| Integrated project skeleton and model package contract | `assets/contest-template/` and `assets/model-package/` |

Do not maintain a second exhaustive file inventory here. The filesystem and validator are the source of truth for package contents.

## Tested Baseline

Current reusable baseline:

- Windows 10/11 host with PowerShell and Python 3; cross-platform convenience wrappers are outside the maintained scope;
- Lushan Pi K230 CanMV with GC2093 camera and 3.1-inch ST7701 `800x480` LCD;
- raw REPL RAM execution with bounded host-Python/serial discovery;
- three-cycle camera/display/media resource lifecycle validation through the RAM-only board probe;
- `cv_lite` grayscale corners as the preferred black-tape rectangle path on the reference firmware;
- circle telemetry as a scene-sensitive diagnostic rather than an always-hit promise;
- bundled YOLO runtime capability, with each user model still requiring package and result-shape validation;
- UART2 pin mapping proven by loopback on the current setup, but requiring reconfirmation on a different connector;
- explicit `STANDARD`, gated `QUICK_PATCH`, and failure-triggered `RECOVERY` board-write modes;
- `mpremote` deployment/snapshot plus raw-REPL byte-preserving upload as explicit, user-authorized board-file workflows.

See repository `docs/BOARD_TEST_LOG.md` for dates, exact firmware observations, counters, timings, and historical regressions.

## Architecture Guardrails

- Keep `SKILL.md` compact and treat its Quick Routing table as the single routing source.
- Put every reference in exactly one of the five category directories; do not add Markdown files directly under `references/`.
- Keep public host commands at the top of `scripts/`; keep `# @runtime: canmv` board probes under `scripts/probes/` and register each one in `run_board_probe.py`.
- Put each example under `hardware`, `vision`, `control`, or `model`; keep only the integrated `main.py` and `boot.py` at the contest-template root.
- Long references need early `## Scope` and `## Contents` sections.
- Keep repository-only docs, tests, CI, and root tools outside `jlc-k230-lushan-pi/`.
- Keep the installed skill's normal commands relative to the folder containing `SKILL.md`.
- Keep generic vision output actuator-neutral; motor frames belong only to the confirmed actuator reference.
- Keep one implementation of host serial, port, reset, and interpreter discovery helpers.
- Prefer links to executable assets over copying their full code into references.
- Add a reference or template only when it has a distinct owner and recurring use.
- Never hard-code maintainer-local absolute paths into the skill or validator.
- Never put raw chronology back into task references; summarize reusable conclusions and link to the repository log.
