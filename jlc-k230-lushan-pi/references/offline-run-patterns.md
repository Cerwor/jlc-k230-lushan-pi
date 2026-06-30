# Offline Run Patterns

These notes distill the official LCKFB/JLC Lushan Pi K230 page for running code offline without CanMV IDE.

Official source: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/ide-usage/offline-run.html

For failures, use `troubleshooting.md#no-offline-auto-run`.

## Scope

Use this reference for final /sdcard/main.py boot behavior, TF-card deployment boundaries, and offline contest startup checks.

## Contents

- Core Rule
- Boot Order
- boot.py Guidance
- main.py Guidance
- Save Through CanMV IDE
- Manual Save
- Deployment Checklist
- Troubleshooting

## Core Rule

Running a script with the green run button in CanMV IDE K230 does not save the MicroPython script to the TF card. It runs from memory, so the script is lost after power-off or reset.

For standalone/e-contest deployment, save the final program as `main.py` in the TF card `sdcard` root so it runs automatically after boot.

User preference: normally provide the final `main.py` program only. The user will manually copy it to the SD card. Do not use CanMV IDE to save to board or modify the TF card unless the user explicitly asks.

If the user explicitly asks for PC-assisted deployment, `references/mpremote-debug-workflows.md` documents `scripts/mpremote_deploy.py` as a supplemental path. It can copy files to `/sdcard` through `mpremote`, but this is still a board-write operation and should not become the default final-answer workflow.

## Boot Order

CanMV firmware starts MicroPython on boot and looks in the `sdcard` directory for:

1. `boot.py`
2. `main.py`

Execution order:

1. Power-on/reset.
2. Execute `boot.py` if it exists.
3. Execute `main.py` after `boot.py` finishes.
4. If `main.py` has no persistent loop, the program may exit.

## boot.py Guidance

Use `boot.py` only for lightweight startup configuration, such as hardware environment setup, basic I/O setup, power management, serial/network initialization, or other necessary boot configuration.

Avoid putting main contest logic in `boot.py`.

Do not put a dead loop in `boot.py`, because it prevents `main.py` from running.

For most simple CanMV/e-contest projects, omit `boot.py` and use only `main.py`.

## main.py Guidance

Put the core user logic in `main.py`, such as:

- image capture
- AI inference
- LCD display
- communication
- decision/control loop
- telemetry/debug output

For contest code, make `main.py` self-contained and suitable for power-on operation:

- use top-level constants for mode, pins, thresholds, model paths, and UART settings
- initialize all required hardware explicitly
- print startup status
- show visible status on the LCD if available
- keep a main loop alive
- stop actuators safely in exception/finally paths
- release camera/display/model/pipeline resources where practical

During debugging, avoid leaving an unverified complex script as `/sdcard/main.py`. Run it from CanMV IDE or raw REPL first, or keep it under a temporary filename. If a bad auto-run script blocks REPL access, rename `/sdcard/main.py` to `main_disabled.py` and `/sdcard/boot.py` to `boot_disabled.py`, then reboot and retry.

## Save Through CanMV IDE

Use this only when the user explicitly asks Codex to save to the board through IDE. Otherwise, provide the `main.py` file/content and let the user copy it manually.

After the script is debugged online:

1. Connect the board in CanMV IDE K230.
2. Open the final script.
3. Use the menu item `Tools -> save open script to CanMV board (as main.py)`.
4. When prompted to remove comments and convert spaces to tabs, the official guide says to choose yes.
5. Wait for the save progress to finish.
6. Power-cycle or reset the board and verify `main.py` auto-runs.

## Manual Save

Preferred user workflow:

1. Rename the final program to `main.py`.
2. Copy it to the TF card `sdcard` root.
3. Power-cycle or reset the board.
4. Verify the program auto-runs.

## Deployment Checklist

Before saying a project is contest-ready:

- Confirm the final file is named `main.py`.
- Confirm it is in the TF card `sdcard` root.
- Confirm model files, labels, and data files are at the paths used in code, such as `/data/...`.
- Confirm the script works after a full power cycle, not only after pressing run in IDE.
- Confirm no `boot.py` loop blocks `main.py`.
- Confirm LCD/serial startup messages appear without IDE interaction.
- Confirm safe fallback behavior if the camera, model, UART, or actuator init fails.
- Keep a known-good backup copy of the final `main.py`.

## Troubleshooting

Use `troubleshooting.md` for offline boot failures. This file only defines the normal deployment process.
