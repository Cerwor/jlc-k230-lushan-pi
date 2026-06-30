# mpremote Debug Workflows

Use this file when the user explicitly wants host-driven deployment, board-file copy, or runtime screenshots through `mpremote`.

These workflows complement the normal TF-card `main.py` flow. They are useful while a PC is connected, but contest-ready programs should still boot from `/sdcard/main.py` without a PC.

## Scope

Use this reference only for explicit mpremote board-file deployment, runtime snapshot pulls, and SD-card side-channel debugging.

## Contents

- When To Use mpremote
- Prerequisites
- Windows-Friendly Deployment
- Runtime Snapshot Pull
- Snapshot Hook Patterns
- Safety And Failure Modes
- Provenance Hygiene

## When To Use mpremote

Use `mpremote` only when the user asks to deploy to the board, pull files from the board, capture a runtime snapshot, or iterate faster than manual TF-card copy.

Do not use it as the default path for final answers. The skill default remains: provide final `main.py` content and let the user copy it unless they explicitly ask Codex to write the board.

Prefer `scripts/run_canmv_raw_repl.py` for RAM-only smoke tests that should not touch `/sdcard`. Prefer `scripts/mpremote_deploy.py` when the user wants to update `/sdcard/main.py` or companion `.py` files.

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

## Provenance Hygiene

Keep this reference as a workflow summary, not a list of third-party project links. The reusable ideas are raw Ctrl-C bursts before deployment, `mpremote ... resume` to avoid unwanted soft-reset behavior, and SD-card snapshot side-channeling for K230/CanMV debugging.

The command behavior is grounded in MicroPython's `mpremote` documentation: `resume` disables automatic soft-reset for subsequent commands, and `fs cp` uses `:` to mark remote paths.
