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
import importlib.util
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_BAUD = 115200
DEFAULT_REMOTE = "/sdcard/codex_snap.bin"
DEFAULT_BREAK_COUNT = 10
MAGIC = b"KSNP"
HEADER_SIZE = 20
LAYOUT_HWC = 0
LAYOUT_CHW = 1
LAYOUT_GRAY = 2
TESTED_CANMV_VID_PID = (0x1209, 0xABD1)
PORT_KEYWORDS = ("canmv", "kendryte", "k230", "usb serial device")


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


def require_serial():
    try:
        import serial
        from serial.tools import list_ports
    except ImportError as exc:
        raise SystemExit("pyserial is required: python -m pip install pyserial") from exc
    return serial, list_ports


def get_ports():
    _serial, list_ports = require_serial()
    return list(list_ports.comports())


def describe_port(port_info) -> str:
    vid = getattr(port_info, "vid", None)
    pid = getattr(port_info, "pid", None)
    vid_pid = ""
    if vid is not None and pid is not None:
        vid_pid = " VID:PID=%04X:%04X" % (vid, pid)
    text = "%s %s%s" % (port_info.device, port_info.description, vid_pid)
    return text.strip()


def is_likely_k230(port_info) -> bool:
    vid = getattr(port_info, "vid", None)
    pid = getattr(port_info, "pid", None)
    if vid == TESTED_CANMV_VID_PID[0] and pid == TESTED_CANMV_VID_PID[1]:
        return True

    haystack = " ".join(
        str(value)
        for value in (
            getattr(port_info, "description", ""),
            getattr(port_info, "manufacturer", ""),
            getattr(port_info, "product", ""),
            getattr(port_info, "hwid", ""),
        )
    ).lower()
    for keyword in PORT_KEYWORDS:
        if keyword in haystack:
            return True
    return False


def print_ports() -> None:
    ports = get_ports()
    if not ports:
        print("No serial ports found.")
        return

    for item in ports:
        marker = " *" if is_likely_k230(item) else "  "
        print("%s %s" % (marker, describe_port(item)))


def resolve_port(explicit_port: str | None) -> str:
    if explicit_port:
        return explicit_port

    env_port = os.environ.get("K230_PORT") or os.environ.get("PORT")
    if env_port:
        return env_port

    ports = get_ports()
    likely = [item for item in ports if is_likely_k230(item)]
    if len(likely) == 1:
        return likely[0].device
    if len(ports) == 1:
        return ports[0].device
    if likely:
        choices = "\n".join("  %s" % describe_port(item) for item in likely)
        raise SystemExit("Multiple likely K230 ports found; pass --port.\n%s" % choices)

    choices = "\n".join("  %s" % describe_port(item) for item in ports)
    if not choices:
        choices = "  (none)"
    raise SystemExit("No K230 port auto-detected; pass --port.\n%s" % choices)


def resolve_mpremote(explicit: str | None) -> list[str]:
    if explicit:
        return [explicit]

    env_mpremote = os.environ.get("MPREMOTE")
    if env_mpremote:
        return [env_mpremote]

    found = shutil.which("mpremote")
    if found:
        return [found]

    if importlib.util.find_spec("mpremote") is not None:
        return [sys.executable, "-m", "mpremote"]

    raise SystemExit("mpremote is required: python -m pip install mpremote")


def command_text(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def run_checked(command: list[str], dry_run: bool, check: bool = True, timeout: float | None = None) -> subprocess.CompletedProcess:
    print("$ %s" % command_text(command))
    if dry_run:
        return subprocess.CompletedProcess(command, 0)
    return subprocess.run(command, check=check, timeout=timeout)


def break_main_loop(port: str, baud: int, count: int, dry_run: bool) -> None:
    log("send Ctrl-C burst on %s" % port)
    if dry_run:
        return

    serial, _list_ports = require_serial()
    with serial.Serial(port, baud, timeout=0.3, write_timeout=2) as ser:
        try:
            ser.read(ser.in_waiting or 1)
        except Exception:
            pass
        for _index in range(count):
            ser.write(b"\x03")
            ser.flush()
            time.sleep(0.15)
        try:
            ser.read(4096)
        except Exception:
            pass


def soft_reset(port: str, baud: int, dry_run: bool) -> None:
    log("send Ctrl-D soft reset")
    if dry_run:
        return

    serial, _list_ports = require_serial()
    with serial.Serial(port, baud, timeout=0.3, write_timeout=2) as ser:
        ser.write(b"\x04")
        ser.flush()


def reset_after_pull(mpremote: list[str], port: str, baud: int, mode: str, dry_run: bool) -> None:
    if mode == "none":
        log("skip reset")
        return
    if mode == "soft":
        soft_reset(port, baud, dry_run)
        return

    log("hard reset through mpremote")
    try:
        run_checked(mpremote + ["connect", port, "resume", "reset"], dry_run, timeout=20)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        log("mpremote reset failed, fallback to Ctrl-D soft reset: %s" % exc)
        soft_reset(port, baud, dry_run)


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
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help="serial baud for Ctrl-C/Ctrl-D")
    parser.add_argument("--mpremote", default=None, help="mpremote executable; defaults to PATH or python -m mpremote")
    parser.add_argument("--break-count", type=int, default=DEFAULT_BREAK_COUNT, help="number of Ctrl-C bytes before pull")
    parser.add_argument("--no-break", action="store_true", help="do not interrupt the running main.py first")
    parser.add_argument("--delete", action="store_true", help="delete the remote snapshot after pulling")
    parser.add_argument("--reset-after", choices=("soft", "hard", "none"), default="soft", help="reset after pull")
    parser.add_argument("--list-ports", action="store_true", help="list serial ports and exit")
    parser.add_argument("--open", action="store_true", help="open the final local image with the OS viewer")
    parser.add_argument("--dry-run", action="store_true", help="print commands without touching the board")
    args = parser.parse_args()

    if args.emit_hook:
        emit_hook(args.emit_hook)
        return 0

    if args.list_ports:
        print_ports()
        return 0

    port = resolve_port(args.port)
    mpremote = resolve_mpremote(args.mpremote)
    local_path = Path(args.out) if args.out else default_output(args.remote)
    decode_out = Path(args.decode_out) if args.decode_out else None

    log("port: %s" % port)
    log("mpremote: %s" % command_text(mpremote))
    log("remote: %s" % args.remote)

    if not args.no_break:
        break_main_loop(port, args.baud, args.break_count, args.dry_run)

    try:
        pull_snapshot(mpremote, port, args.remote, local_path, args.dry_run)
        if args.delete:
            delete_remote_snapshot(mpremote, port, args.remote, args.dry_run)
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
