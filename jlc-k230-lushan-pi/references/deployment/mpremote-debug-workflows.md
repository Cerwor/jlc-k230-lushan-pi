# mpremote Debug Workflows

Use this file when the user explicitly wants host-driven deployment, board-file copy, or runtime screenshots through `mpremote`.

These workflows complement the normal TF-card `main.py` flow. They are useful while a PC is connected, but contest-ready programs should still boot from `/sdcard/main.py` without a PC.

## Scope

Use this reference only for explicit mpremote board-file deployment, runtime snapshot pulls, and SD-card side-channel debugging.

## Contents

- When To Use mpremote
- Prerequisites
- Host Python Resolution
- Windows-Friendly Deployment
- Raw REPL Deployment Fallback
- Runtime Snapshot Pull
- Snapshot Hook Patterns
- Safety And Failure Modes
- Provenance Hygiene

## When To Use mpremote

Use `mpremote` only when the user asks to deploy to the board, pull files from the board, capture a runtime snapshot, or iterate faster than manual TF-card copy.

Do not use it as the default path for final answers. The skill default remains: provide final `main.py` content and let the user copy it unless they explicitly ask Codex to write the board.

Before any board write, apply the single deployment-mode decision gate in `references/deployment/offline-run-patterns.md#deployment-mode-gate`. The selected transport does not determine the mode: an `mpremote` copy can still be `QUICK_PATCH`, while a one-line actuator or startup change remains `STANDARD`. Do not choose `RECOVERY` before a real deployment step fails.

Prefer `scripts/run_board_probe.py` for standard RAM-only probes that should not touch `/sdcard`, and use `scripts/run_canmv_raw_repl.py` only for an arbitrary script or handshake diagnosis. Prefer `scripts/mpremote_deploy.py` when the user wants to update `/sdcard/main.py` or companion `.py` files.

If `mpremote` is unavailable or one real `mpremote` copy/handshake attempt fails, use `scripts/raw_repl_deploy.py` as the bounded file-upload fallback. It reuses the proven handshake in `scripts/run_canmv_raw_repl.py`; do not improvise another base64 writer in the conversation.

`scripts/_host_tools.py` is an internal shared helper for serial-port listing, conservative port resolution, `mpremote` lookup, and command execution. Do not call it directly from user-facing workflows.

## Prerequisites

Install host dependencies for real board-file deployment:

```powershell
python -m pip install -r .\requirements-host.txt
```

If the repository-level requirements file is unavailable, install the minimum dependencies directly:

```powershell
python -m pip install mpremote pyserial
```

`--dry-run` can preview the deployment commands before `mpremote` is installed. Port listing and Ctrl-C/Ctrl-D recovery still need `pyserial`. Raw `.bin` snapshot decoding also needs `Pillow` and `numpy`.

```powershell
python -m pip install Pillow numpy
```

List detected serial ports:

```powershell
python ".\jlc-k230-lushan-pi\scripts\mpremote_deploy.py" --list-ports
```

The helper treats the tested CanMV USB VID:PID `1209:ABD1` as a high-confidence auto-detection hint, not as a universal K230 identifier. Port listing also marks common descriptions such as CanMV, Kendryte, K230, or USB Serial Device with `?`. If multiple ports exist, pass `--port COM14` or the user's current COM port.

By default, `mpremote_deploy.py` and `mpremote_snapshot.py` auto-select only the tested VID:PID match. If the board appears with a generic USB-serial description, pass `--port` explicitly. Use `--allow-fuzzy-port` only when the user accepts description-based matching.

## Host Python Resolution

`run_board_probe.py`, `run_canmv_raw_repl.py`, `mpremote_deploy.py`, `mpremote_snapshot.py`, and `raw_repl_deploy.py` validate host dependencies before opening the serial port. They first probe the Python interpreter that launched the script. Only when it lacks a required module do they perform bounded discovery through `K230_HOST_PYTHON`, active virtual/Conda environments, the Windows Python Launcher, and Python executables exposed through `PATH`.

The `mpremote` deployment path requires `serial` plus an `mpremote` provider. When an explicit `--mpremote`, `MPREMOTE`, or PATH executable already provides `mpremote`, the selected Python only needs `serial`; otherwise it must import both modules. The raw REPL uploader requires only `serial`.

To force one interpreter, pass `--host-python python`. `K230_HOST_PYTHON` adds a preferred fallback candidate after the current interpreter. An explicit `--host-python` is validated by itself and does not silently fall through to another interpreter. Before deployment, the helper reports the selected runtime:

```text
HOST_PYTHON=<selected interpreter>
HOST_DEPENDENCIES=serial,mpremote
```

If another interpreter is selected, the deployment script is restarted under it once, before port ownership or board writes begin. Re-execution is limited to one level. The helper never installs packages, scans arbitrary disks, or tries a second interpreter after deployment has started. `--dry-run` with an explicit port remains dependency-free because it does not open the serial port or invoke `mpremote`.

## Windows-Friendly Deployment

Deploy `main.py` from the current project directory to `/sdcard/main.py` and hard-reset:

```powershell
python ".\jlc-k230-lushan-pi\scripts\mpremote_deploy.py" --port COM14 main.py
```

Deploy all top-level Python files in a firmware folder:

```powershell
python ".\jlc-k230-lushan-pi\scripts\mpremote_deploy.py" --port COM14 --src-dir ".\firmware" --all-py
```

Preview without writing:

```powershell
python ".\jlc-k230-lushan-pi\scripts\mpremote_deploy.py" --port COM14 main.py --dry-run
```

The deployment helper:

1. Sends a raw Ctrl-C burst with `pyserial` to interrupt an auto-running `main.py`.
2. Runs `mpremote connect <port> resume fs cp <local> :/sdcard/<name>`.
3. Runs `mpremote connect <port> resume reset`, with Ctrl-D soft-reset fallback.

The `resume` step matters because ordinary `mpremote exec`, `run`, or `fs` commands can trigger auto soft-reset/raw-paste behavior. On K230, a busy `main.py` may swallow a single Ctrl-C and leave the handshake stuck.

## Raw REPL Deployment Fallback

Deploy one file without `mpremote`:

```powershell
python ".\jlc-k230-lushan-pi\scripts\raw_repl_deploy.py" main.py --remote /sdcard/main.py --port COM14
```

Preview the byte count, SHA-256, chunk count, selected deployment mode, and reset behavior without opening the serial port:

```powershell
python ".\jlc-k230-lushan-pi\scripts\raw_repl_deploy.py" main.py --remote /sdcard/main.py --dry-run
```

For a gate-approved quick patch, state the evidence explicitly:

```powershell
python ".\jlc-k230-lushan-pi\scripts\raw_repl_deploy.py" main.py --remote /sdcard/main.py --port COM14 --mode QUICK_PATCH --reason "Previously verified display-orientation-only change"
```

This uploader requires `pyserial`, but not `mpremote`. It reads the local file as bytes, writes base64-decoded byte chunks to a sibling `.codex.tmp` file, verifies temporary-file size and SHA-256, replaces the target with `os.replace()` when available or a rollback-safe rename sequence, verifies the final target again, and issues one soft reset. Use `--no-reset` only when the surrounding workflow owns the reset.

The target is untouched until temporary-file verification passes. If a stale `.codex.bak` exists on firmware without `os.replace()`, stop and inspect it instead of deleting it automatically; it may contain the last good target. A failed handshake may try the next configured baud because no file write has started. Once writing starts, fail closed instead of silently changing transport or baud.

Missing `mpremote` at dependency preflight does not by itself change the selected deployment mode; transport and behavioral risk are separate. After one actual `mpremote` deployment failure, enter `RECOVERY`, use this uploader once, and return to the original mode's unfinished acceptance step.

## Runtime Snapshot Pull

The hard problem: after Ctrl-C, the K230 camera pipeline may already be deinitialized, so the frame you wanted to inspect is gone. A reliable pattern is to let the running `main.py` periodically write a small snapshot to `/sdcard`, then have the host pull that file later.

For normal `image.Image` frames, paste the image hook from:

```powershell
python ".\jlc-k230-lushan-pi\scripts\mpremote_snapshot.py" --emit-hook image
```

Then call `maybe_save_image_snapshot(img)` inside the main loop after `img = sensor.snapshot()` or equivalent.

Pull the latest JPEG:

```powershell
python ".\jlc-k230-lushan-pi\scripts\mpremote_snapshot.py" --port COM14 --remote /sdcard/codex_snap.jpg --out ".\snaps\latest.jpg" --delete --open
```

`--delete` is intentionally restricted to snapshot-like paths under `/sdcard/codex_snap*` or `/sdcard/tmp/codex_snap*`. For a deliberate custom path, require `--force-any-remote` and explain the risk before running it.

For PipeLine or AI-channel code that exposes a CHW RGB888 tensor/ulab ndarray, paste the CHW hook:

```powershell
python ".\jlc-k230-lushan-pi\scripts\mpremote_snapshot.py" --emit-hook chw
```

Then call `maybe_save_chw_snapshot(img)` after `img = pl.get_frame()` or the equivalent frame acquisition. The hook writes a stride-subsampled `KSNP` binary file. Pull and decode it locally:

```powershell
python ".\jlc-k230-lushan-pi\scripts\mpremote_snapshot.py" --port COM14 --remote /sdcard/codex_snap.bin --delete --open
```

The `KSNP` format is intentionally simple: magic `KSNP`, little-endian width, height, channels, layout, then raw `uint8` image bytes. Layout `1` means CHW and is decoded to normal HWC before saving.

The host decoder rejects invalid dimensions, channels above 4, and bodies above the configured safety limit, so a corrupt snapshot should fail closed instead of exhausting host memory.

## Snapshot Hook Patterns

Keep snapshot writes throttled. A JPEG save can drop the loop to a few FPS, and even a raw 700 KB binary write is too expensive every frame.

For normal camera/LCD code, prefer the JPEG hook because it avoids local raw decoding and works with `image.Image` objects.

For YOLO/PipeLine code where the frame is a planar CHW tensor, use the CHW hook. Keep `SNAPSHOT_STRIDE = 3` or larger unless the SD card write time is acceptable.

Do not auto-patch unknown `main.py` files by default. If patching is unavoidable, first pull a backup of `/sdcard/main.py`, require a clear anchor line from the user, and insert only a marked block that can be removed later.

## Safety And Failure Modes

- Close CanMV IDE and other serial tools before using `mpremote`; only one process can own the COM port.
- If the port exists but no bytes return, replug USB or reset the board, then retry.
- If SD-card removal makes the serial port disappear, reinsert the SD card and reconnect USB.
- If a bad `/sdcard/main.py` blocks access, rename it to `main_disabled.py` and reboot before trying `mpremote` again.
- Use `--dry-run` on deployment commands before the first real board write.
- Treat `mpremote_deploy.py` as a board-writing tool. Do not run it unless the user has explicitly asked to deploy or update board files.
- Treat `mpremote_snapshot.py --delete` as a remote file deletion. Use it only for temporary snapshot artifacts.
- On one failed copy or handshake, report the failed step and enter `RECOVERY`; do not repeat `mpremote`, resets, and serial listening without a new diagnostic reason.

## Provenance Hygiene

Keep this reference as a workflow summary, not a list of third-party project links. The reusable ideas are raw Ctrl-C bursts before deployment, `mpremote ... resume` to avoid unwanted soft-reset behavior, and SD-card snapshot side-channeling for K230/CanMV debugging.

The command behavior is grounded in MicroPython's `mpremote` documentation: `resume` disables automatic soft-reset for subsequent commands, and `fs cp` uses `:` to mark remote paths.
