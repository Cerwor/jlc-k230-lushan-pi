#!/usr/bin/env python3
"""Pull a K230 runtime snapshot through mpremote and decode it locally.

The board-side main.py must write a snapshot file periodically. Use
--emit-hook to print a conservative hook that can be pasted into main.py.
This host-side script then interrupts the loop, pulls the latest snapshot,
optionally deletes it from /sdcard, and resets the board to resume main.py.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path
from subprocess import CalledProcessError
from subprocess import TimeoutExpired

from _host_tools import command_text
from _host_tools import ensure_host_python
from _host_tools import mpremote_host_modules
from _host_tools import print_ports
from _host_tools import resolve_mpremote
from _host_tools import resolve_port
from _host_tools import run_checked
from _host_tools import send_ctrl_c_burst
from _host_tools import send_soft_reset


DEFAULT_BAUD = 115200
DEFAULT_REMOTE = "/sdcard/codex_snap.bin"
DEFAULT_BREAK_COUNT = 10
SAFE_REMOTE_PREFIXES = ("/sdcard/codex_snap", "/sdcard/tmp/codex_snap")
MAX_KSNP_WIDTH = 4096
MAX_KSNP_HEIGHT = 4096
MAX_KSNP_CHANNELS = 4
MAX_KSNP_BODY_BYTES = 64 * 1024 * 1024
MAGIC = b"KSNP"
HEADER_SIZE = 20
LAYOUT_HWC = 0
LAYOUT_CHW = 1
LAYOUT_GRAY = 2


IMAGE_HOOK = r'''
# === CODEX_SNAPSHOT_IMAGE_BEGIN ===
import time

SNAPSHOT_PATH = "/sdcard/codex_snap.jpg"
SNAPSHOT_INTERVAL_MS = 3000
_snapshot_last_ms = 0

def maybe_save_image_snapshot(img):
    global _snapshot_last_ms
    try:
        now = time.ticks_ms()
        if time.ticks_diff(now, _snapshot_last_ms) < SNAPSHOT_INTERVAL_MS:
            return
        _snapshot_last_ms = now
        img.save(SNAPSHOT_PATH)
        print("SNAPSHOT_OK", SNAPSHOT_PATH)
    except Exception as e:
        print("SNAPSHOT_ERR", e)

# 在主循环拿到 image.Image 后调用:
# maybe_save_image_snapshot(img)
# === CODEX_SNAPSHOT_IMAGE_END ===
'''.strip()


CHW_HOOK = r'''
# === CODEX_SNAPSHOT_CHW_BEGIN ===
import time

SNAPSHOT_PATH = "/sdcard/codex_snap.bin"
SNAPSHOT_INTERVAL_MS = 3000
SNAPSHOT_STRIDE = 3
_snapshot_last_ms = 0

def maybe_save_chw_snapshot(arr):
    global _snapshot_last_ms
    try:
        now = time.ticks_ms()
        if time.ticks_diff(now, _snapshot_last_ms) < SNAPSHOT_INTERVAL_MS:
            return
        _snapshot_last_ms = now
        small = arr[:, ::SNAPSHOT_STRIDE, ::SNAPSHOT_STRIDE]
        channels = int(small.shape[0])
        height = int(small.shape[1])
        width = int(small.shape[2])
        with open(SNAPSHOT_PATH, "wb") as snap_file:
            snap_file.write(b"KSNP")
            snap_file.write(width.to_bytes(4, "little"))
            snap_file.write(height.to_bytes(4, "little"))
            snap_file.write(channels.to_bytes(4, "little"))
            snap_file.write((1).to_bytes(4, "little"))
            snap_file.write(bytes(small.flatten()))
        print("SNAPSHOT_OK", SNAPSHOT_PATH, width, height, channels)
    except Exception as e:
        print("SNAPSHOT_ERR", e)

# 在主循环拿到 CHW RGB888 tensor/ulab ndarray 后调用:
# maybe_save_chw_snapshot(img)
# === CODEX_SNAPSHOT_CHW_END ===
'''.strip()


def log(message: str) -> None:
    print("[mpremote-snapshot] %s" % message)


def reset_after_pull(mpremote: list[str], port: str, baud: int, mode: str, dry_run: bool) -> None:
    if mode == "none":
        log("skip reset")
        return
    if mode == "soft":
        log("send Ctrl-D soft reset")
        if not dry_run:
            send_soft_reset(port, baud)
        return

    log("hard reset through mpremote")
    try:
        run_checked(mpremote + ["connect", port, "resume", "reset"], dry_run, timeout=20)
    except (CalledProcessError, TimeoutExpired) as exc:
        log("mpremote reset failed, fallback to Ctrl-D soft reset: %s" % exc)
        if not dry_run:
            send_soft_reset(port, baud)


def default_output(remote_path: str) -> Path:
    suffix = Path(remote_path).suffix.lower()
    if suffix not in (".jpg", ".jpeg", ".png", ".bmp", ".bin", ".rgb"):
        suffix = ".jpg"
    out_dir = Path("snaps")
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return out_dir / ("k230-snap-%s%s" % (stamp, suffix))


def remote_arg(remote_path: str) -> str:
    if remote_path.startswith(":"):
        return remote_path
    return ":" + remote_path


def validate_remote_snapshot_path(remote_path: str, allow_any: bool) -> str:
    if allow_any:
        return remote_path

    if remote_path.startswith(":"):
        check_path = remote_path[1:]
    else:
        check_path = remote_path

    for prefix in SAFE_REMOTE_PREFIXES:
        if check_path.startswith(prefix):
            return remote_path

    raise SystemExit(
        "Refusing remote snapshot path outside safe prefixes: %s. "
        "Use --force-any-remote when you intentionally need a custom path." % remote_path
    )


def delete_remote_snapshot(mpremote: list[str], port: str, remote_path: str, dry_run: bool) -> None:
    code = """
import os
try:
    os.remove(%r)
    print('SNAP_DELETE_OK')
except Exception as e:
    print('SNAP_DELETE_WARN', e)
""" % remote_path
    run_checked(mpremote + ["connect", port, "resume", "exec", code], dry_run, check=False)


def pull_snapshot(mpremote: list[str], port: str, remote_path: str, local_path: Path, dry_run: bool) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    run_checked(mpremote + ["connect", port, "resume", "fs", "cp", remote_arg(remote_path), str(local_path)], dry_run)


def decode_ksnp(path: Path, out_path: Path | None) -> Path:
    data = path.read_bytes()
    if len(data) < HEADER_SIZE or data[:4] != MAGIC:
        return path

    width = int.from_bytes(data[4:8], "little")
    height = int.from_bytes(data[8:12], "little")
    channels = int.from_bytes(data[12:16], "little")
    layout = int.from_bytes(data[16:20], "little")
    body = data[20:]

    if width <= 0 or height <= 0 or channels <= 0:
        raise SystemExit("invalid snapshot shape: %dx%dx%d" % (width, height, channels))
    if width > MAX_KSNP_WIDTH or height > MAX_KSNP_HEIGHT or channels > MAX_KSNP_CHANNELS:
        raise SystemExit("snapshot shape too large: %dx%dx%d" % (width, height, channels))
    if len(body) > MAX_KSNP_BODY_BYTES:
        raise SystemExit("snapshot body too large: %d bytes" % len(body))

    expected = width * height * channels
    if len(body) != expected:
        raise SystemExit("snapshot body size %d != %d*%d*%d" % (len(body), width, height, channels))

    try:
        import numpy as np
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("Pillow and numpy are required for .bin snapshots: python -m pip install Pillow numpy") from exc

    raw = np.frombuffer(body, dtype=np.uint8)
    if layout == LAYOUT_CHW:
        arr = raw.reshape((channels, height, width)).transpose(1, 2, 0)
    elif layout == LAYOUT_HWC:
        arr = raw.reshape((height, width, channels))
    elif layout == LAYOUT_GRAY:
        arr = raw.reshape((height, width))
    else:
        raise SystemExit("unsupported snapshot layout: %d" % layout)

    if channels == 1 and layout != LAYOUT_GRAY:
        arr = arr.reshape((height, width))

    if out_path is None:
        out_path = path.with_suffix(".jpg")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr).save(out_path)
    log("decoded KSNP %dx%dx%d layout=%d -> %s" % (width, height, channels, layout, out_path))
    return out_path


def open_file(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def emit_hook(kind: str) -> None:
    if kind == "image":
        print(IMAGE_HOOK)
    elif kind == "chw":
        print(CHW_HOOK)
    else:
        raise SystemExit("unknown hook kind: %s" % kind)


def main() -> int:
    parser = argparse.ArgumentParser(description="Pull and decode K230 runtime snapshots through mpremote.")
    parser.add_argument("--emit-hook", choices=("image", "chw"), help="print a board-side snapshot hook and exit")
    parser.add_argument("--remote", default=DEFAULT_REMOTE, help="remote snapshot path")
    parser.add_argument("--out", default=None, help="local output path")
    parser.add_argument("--decode-out", default=None, help="JPEG/PNG output path when pulling KSNP .bin")
    parser.add_argument("--port", default=None, help="serial port such as COM14; defaults to auto-detect")
    parser.add_argument("--allow-fuzzy-port", action="store_true", help="allow description-based serial auto-detection")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help="serial baud for Ctrl-C/Ctrl-D")
    parser.add_argument("--mpremote", default=None, help="mpremote executable; defaults to PATH or python -m mpremote")
    parser.add_argument("--host-python", help="Host Python executable; defaults to current interpreter, then bounded auto-discovery")
    parser.add_argument("--break-count", type=int, default=DEFAULT_BREAK_COUNT, help="number of Ctrl-C bytes before pull")
    parser.add_argument("--no-break", action="store_true", help="do not interrupt the running main.py first")
    parser.add_argument("--delete", action="store_true", help="delete the remote snapshot after pulling")
    parser.add_argument("--force-any-remote", action="store_true", help="allow custom remote path outside safe snapshot prefixes")
    parser.add_argument("--reset-after", choices=("soft", "hard", "none"), default="soft", help="reset after pull")
    parser.add_argument("--list-ports", action="store_true", help="list serial ports and exit")
    parser.add_argument("--open", action="store_true", help="open the final local image with the OS viewer")
    parser.add_argument("--dry-run", action="store_true", help="print commands without touching the board")
    args = parser.parse_args()

    if args.emit_hook:
        emit_hook(args.emit_hook)
        return 0

    if args.list_ports:
        ensure_host_python(("serial",), args.host_python, __file__, sys.argv[1:])
        print_ports()
        return 0

    if not args.dry_run:
        ensure_host_python(
            mpremote_host_modules(args.mpremote),
            args.host_python,
            __file__,
            sys.argv[1:],
            capabilities=("serial", "mpremote"),
        )
    elif not args.port:
        ensure_host_python(("serial",), args.host_python, __file__, sys.argv[1:])

    remote_path = validate_remote_snapshot_path(args.remote, args.force_any_remote)
    port = resolve_port(args.port, allow_fuzzy=args.allow_fuzzy_port)
    mpremote = resolve_mpremote(args.mpremote, required=(not args.dry_run))
    local_path = Path(args.out) if args.out else default_output(remote_path)
    decode_out = Path(args.decode_out) if args.decode_out else None

    log("port: %s" % port)
    log("mpremote: %s" % command_text(mpremote))
    log("remote: %s" % remote_path)

    if not args.no_break:
        log("send Ctrl-C burst on %s" % port)
        if not args.dry_run:
            send_ctrl_c_burst(port, args.baud, args.break_count)

    try:
        pull_snapshot(mpremote, port, remote_path, local_path, args.dry_run)
        if args.delete:
            delete_remote_snapshot(mpremote, port, remote_path, args.dry_run)
    finally:
        reset_after_pull(mpremote, port, args.baud, args.reset_after, args.dry_run)

    final_path = local_path
    if not args.dry_run:
        final_path = decode_ksnp(local_path, decode_out)
        log("saved %s" % final_path)
        if args.open:
            open_file(final_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
