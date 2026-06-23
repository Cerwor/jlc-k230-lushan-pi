# Test Matrix

This repository-level matrix helps maintainers choose the right test without loading the long board-test history into the installable skill.

## Layers

| Layer | Goal | Default command | Board access | Writes board files | User setup | Pass signal |
| --- | --- | --- | --- | --- | --- | --- |
| Offline preflight | Check skill structure, docs, Python syntax, and quick validation | `.\tools\test.ps1` | No | No | None | `VALIDATE_SKILL_OK`, `Skill is valid!`, `TEST_OK` |
| Port discovery | Confirm the K230 serial port and auto-detection hint | `.\tools\test.ps1 -ListPorts -SkipValidate` | Enumerates host ports | No | Board connected by USB | K230-like port marked with `*`, usually COM14 on the tested setup |
| Smoke | Verify raw REPL, camera, MediaManager, and 3.1-inch LCD | `.\tools\test.ps1 -Board -Port COM14` | Yes, raw REPL | No, RAM-only | Board connected, screen attached | `SMOKE_DONE frames=20 fps=...` |
| Core vision chain | Verify camera/LCD, Sensor modes, and Otsu threshold chain | `.\tools\test.ps1 -Board -Vision all-core -Port COM14` | Yes, raw REPL | No, RAM-only | Board connected; black/white target useful for Otsu | `SMOKE_DONE`, `SENSOR_PROBE_DONE`, `OTSU_PROBE_DONE` |
| Board resources | Discover `.kmodel` and AI/example files without assuming paths | `.\tools\test.ps1 -Board -Vision resources -Port COM14` | Yes, raw REPL | No, RAM-only | Board connected with SD card | `RESOURCE_PROBE_DONE...` plus `ACCEPT_RESOURCES status=...` |
| Rectangle target | Regression-test black-tape rectangle target tracking | `.\tools\test.ps1 -Board -Vision rect-target -Port COM14` | Yes, raw REPL | No, RAM-only | Put the black-tape rectangle in view | `RECT_PROBE_DONE...` plus `ACCEPT_RECT status=...` |
| Circle target | Diagnose bottle-cap/circle raw vs tracked quality | `.\tools\test.ps1 -Board -Vision circle-target -Port COM14` | Yes, raw REPL | No, RAM-only | Put the bottle cap or circular target in view | `CIRCLE_PROBE_DONE...` plus `ACCEPT_CIRCLE status=...` |
| YOLO runtime | Verify YOLO imports, classes, and board model/example resources | `.\tools\test.ps1 -Board -Vision yolo -Port COM14` | Yes, raw REPL | No, RAM-only | Board connected with SD card | `YOLO_PROBE_DONE...` plus `ACCEPT_YOLO status=...` |
| UART loopback | Find actual UART2 TX/RX mapping and sweep common TX candidates | `.\tools\test.ps1 -Board -Vision uart-loopback -Port COM14` | Yes, raw REPL | No, RAM-only | Physical loopback or MCU-side observer | `UART2_LOOPBACK_PROBE_DONE` plus `ACCEPT_UART status=...` |
| Installed skill smoke | Confirm the Codex-loaded skill copy is synced | `.\tools\test.ps1 -Installed -Board -Vision smoke -Port COM14` | Yes, raw REPL | No, RAM-only | Board connected | `TEST_OK skill=...\skills\jlc-k230-lushan-pi` |
| mpremote preview | Preview deployment commands without requiring `mpremote` install | `python .\jlc-k230-lushan-pi\scripts\mpremote_deploy.py --port COM14 main.py --dry-run` | No live board write | No | Local source file exists | Prints planned `mpremote connect ... fs cp ...` commands |
| mpremote deploy | Explicitly copy files to `/sdcard` | `python .\jlc-k230-lushan-pi\scripts\mpremote_deploy.py --port COM14 main.py` | Yes | Yes | User explicitly asks to deploy | File is copied and board reset succeeds |
| Snapshot hook | Emit code for runtime snapshot side-channel | `python .\jlc-k230-lushan-pi\scripts\mpremote_snapshot.py --emit-hook image` | No | No | None | Hook code is printed |
| Snapshot pull | Pull a snapshot file previously written by board code | `python .\jlc-k230-lushan-pi\scripts\mpremote_snapshot.py --port COM14 --remote /sdcard/codex_snap.jpg` | Yes | Optional delete only if requested | Snapshot hook already running on board | Local image/bin file decoded or saved |
| Direct UART loopback | Find actual UART2 TX/RX mapping without repository wrapper | `python .\jlc-k230-lushan-pi\scripts\probe_uart2_loopback.py` | Yes | No, RAM-only | Physical loopback or MCU-side observer | Reports linked GPIO pair or UART RX bytes |
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
- Keep `jlc-k230-lushan-pi/references/maintenance.md` compact: current baseline, repository tooling, and recent summary only.
