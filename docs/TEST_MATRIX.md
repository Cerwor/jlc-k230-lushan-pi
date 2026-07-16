# Test Matrix

This repository-level matrix helps maintainers choose the right test without loading the long board-test history into the installable skill.

## Layers

| Layer | Goal | Default command | Board access | Writes board files | User setup | Pass signal |
| --- | --- | --- | --- | --- | --- | --- |
| Offline preflight + host tests | Check skill structure, docs, Python syntax, quick validation, deploy safety, and architecture guardrails | `.\tools\test.ps1` | No | No | None | `VALIDATE_SKILL_OK`, unit-test `OK`, `TEST_OK` |
| Host unit tests only | Run the same host regressions directly while developing a test | `python -m unittest discover -s tests` | No | No | None | `Ran ... tests`, `OK` |
| Port discovery | Confirm the K230 serial port and auto-detection hint | `python .\jlc-k230-lushan-pi\scripts\run_board_probe.py --list-ports` | Enumerates host ports | No | Board connected by USB | `*` means tested VID:PID match; `?` means fuzzy description match |
| Smoke | Verify raw REPL, camera, MediaManager, and 3.1-inch LCD | `python .\jlc-k230-lushan-pi\scripts\run_board_probe.py --vision smoke --port COM14` | Yes, raw REPL | No, RAM-only | Board connected, screen attached | `SMOKE_DONE frames=20 fps=...` |
| Resource lifecycle | Repeat camera/LCD/media initialize and cleanup exactly three times | `python .\jlc-k230-lushan-pi\scripts\run_board_probe.py --vision resource-cycle --port COM14` | Yes, raw REPL | No, RAM-only | Board connected, screen attached | `LIFECYCLE_PROBE_DONE cycles=3 passed=3...` plus `ACCEPT_LIFECYCLE status=pass` |
| Core vision chain | Verify camera/LCD, Sensor modes, and Otsu threshold chain | `python .\jlc-k230-lushan-pi\scripts\run_board_probe.py --vision all-core --port COM14` | Yes, raw REPL | No, RAM-only | Board connected; black/white target useful for Otsu | `SMOKE_DONE`, `SENSOR_PROBE_DONE`, `OTSU_PROBE_DONE` |
| Board resources | Discover `.kmodel` and AI/example files without assuming paths | `python .\jlc-k230-lushan-pi\scripts\run_board_probe.py --vision resources --port COM14` | Yes, raw REPL | No, RAM-only | Board connected with SD card | `RESOURCE_PROBE_DONE...` plus `ACCEPT_RESOURCES status=...` |
| Rectangle target | Regression-test black-tape rectangle target tracking | `python .\jlc-k230-lushan-pi\scripts\run_board_probe.py --vision rect-target --port COM14` | Yes, raw REPL | No, RAM-only | Put the black-tape rectangle in view | `RECT_PROBE_DONE...` plus `ACCEPT_RECT status=...` |
| Circle target | Diagnose bottle-cap/circle raw vs tracked quality | `python .\jlc-k230-lushan-pi\scripts\run_board_probe.py --vision circle-target --port COM14` | Yes, raw REPL | No, RAM-only | Put the bottle cap or circular target in view | `CIRCLE_PROBE_DONE...` plus `ACCEPT_CIRCLE status=...` |
| YOLO runtime | Verify YOLO imports, classes, and board model/example resources | `python .\jlc-k230-lushan-pi\scripts\run_board_probe.py --vision yolo --port COM14` | Yes, raw REPL | No, RAM-only | Board connected with SD card | `YOLO_PROBE_DONE...` plus `ACCEPT_YOLO status=...` |
| UART loopback | Find actual UART2 TX/RX mapping and sweep common TX candidates | `python .\jlc-k230-lushan-pi\scripts\run_board_probe.py --vision uart-loopback --port COM14` | Yes, raw REPL | No, RAM-only | Physical loopback or MCU-side observer | `UART2_LOOPBACK_PROBE_DONE` plus `ACCEPT_UART status=...` |
| Installed skill smoke | Confirm the Codex-loaded skill copy is synced | `.\tools\test.ps1 -Installed -Board -Vision smoke -Port COM14` | Yes, raw REPL | No, RAM-only | Board connected | `TEST_OK skill=...\skills\jlc-k230-lushan-pi` |
| mpremote preview | Preview deployment commands without requiring `mpremote` install | `python .\jlc-k230-lushan-pi\scripts\mpremote_deploy.py --port COM14 main.py --dry-run` | No live board write | No | Local source file exists | Prints planned `mpremote connect ... fs cp ...` commands |
| mpremote deploy | Explicitly copy files to `/sdcard` | `python .\jlc-k230-lushan-pi\scripts\mpremote_deploy.py --port COM14 main.py` | Yes | Yes | User explicitly asks to deploy | File is copied and board reset succeeds |
| Raw-REPL deploy fallback | Upload one file after mpremote is unavailable or fails once | `python .\jlc-k230-lushan-pi\scripts\raw_repl_deploy.py main.py --remote /sdcard/main.py --port COM14` | Yes | Yes | User explicitly asks to deploy | Byte count and SHA-256 match, replace succeeds, one reset |
| Snapshot hook | Emit code for runtime snapshot side-channel | `python .\jlc-k230-lushan-pi\scripts\mpremote_snapshot.py --emit-hook image` | No | No | None | Hook code is printed |
| Snapshot pull | Pull a snapshot file previously written by board code | `python .\jlc-k230-lushan-pi\scripts\mpremote_snapshot.py --port COM14 --remote /sdcard/codex_snap.jpg` | Yes | Optional delete only if requested | Snapshot hook already running on board | Local image/bin file decoded or saved |
| Offline boot | Verify `/sdcard/main.py` survives reset/power cycle | Manual SD-card workflow | Yes | Yes | User explicitly places/renames `main.py` | LCD/serial startup status reappears after reset |

## Confidence Labels

Use these labels in notes and PR descriptions:

| Label | Meaning |
| --- | --- |
| `offline` | Host-side validation only; no hardware confidence. |
| `ram-only` | Board ran the script through raw REPL without writing `/sdcard/main.py`. |
| `board-write` | Test intentionally wrote or deleted files on the board or SD card. |
| `target-dependent` | Result depends on object placement, lighting, and scene clutter. |
| `diagnostic` | Useful for observing state, not a strict pass/fail assertion. |
| `contest-ready` | A final-style workflow passed with expected safety/recovery behavior. |

## Recording Results

- Put reusable facts into the relevant `jlc-k230-lushan-pi/references/` file.
- Put failures and recovery rules into `jlc-k230-lushan-pi/references/troubleshooting.md`.
- Put long chronological test history into `docs/BOARD_TEST_LOG.md`, not the installable skill.
- Keep `jlc-k230-lushan-pi/references/maintenance.md` compact: update policy, architecture baseline, and guardrails only.
