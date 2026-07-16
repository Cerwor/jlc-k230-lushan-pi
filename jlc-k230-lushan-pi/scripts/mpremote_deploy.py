#!/usr/bin/env python3
"""Deploy K230 CanMV files to /sdcard through mpremote.

This is a host-side helper. It writes files to the board, so run it only
when the user explicitly wants mpremote deployment instead of manual TF-card
copy or RAM-only raw REPL testing.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path
from subprocess import CalledProcessError
from subprocess import TimeoutExpired

from _host_tools import command_text
from _host_tools import ensure_host_python
from _host_tools import print_ports
from _host_tools import require_serial
from _host_tools import resolve_mpremote
from _host_tools import resolve_port
from _host_tools import run_checked


DEFAULT_BAUD = 115200
DEFAULT_REMOTE_DIR = "/sdcard"
DEFAULT_BREAK_COUNT = 10


def log(message: str) -> None:
    print("[mpremote-deploy] %s" % message)


def collect_files(files: list[str], src_dir: str, all_py: bool) -> list[Path]:
    root = Path(src_dir).resolve()
    selected: list[Path] = []

    if files:
        for item in files:
            direct = Path(item)
            if direct.is_file():
                selected.append(direct.resolve())
                continue
            candidate = root / Path(item).name
            if candidate.is_file():
                selected.append(candidate.resolve())
                continue
            raise SystemExit("file not found: %s" % item)
    elif all_py:
        selected = sorted(path.resolve() for path in root.glob("*.py") if path.is_file())
    else:
        main_py = root / "main.py"
        if main_py.is_file():
            selected = [main_py.resolve()]
        else:
            raise SystemExit("no files specified and %s does not exist; pass files or --all-py" % main_py)

    if not selected:
        raise SystemExit("no files selected for deployment")
    return selected


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


def remote_path(remote_dir: str, local_file: Path) -> str:
    clean_dir = remote_dir.rstrip("/")
    if not clean_dir:
        clean_dir = "/"
    if clean_dir == "/":
        path = "/" + local_file.name
    else:
        path = clean_dir + "/" + local_file.name
    return ":" + path


def deploy_file(mpremote: list[str], port: str, src: Path, remote_dir: str, dry_run: bool) -> None:
    target = remote_path(remote_dir, src)
    log("copy %s -> %s" % (src.name, target))
    run_checked(mpremote + ["connect", port, "resume", "fs", "cp", str(src), target], dry_run)


def reset_device(mpremote: list[str], port: str, baud: int, mode: str, dry_run: bool) -> None:
    if mode == "none":
        log("skip reset")
        return
    if mode == "soft":
        soft_reset(port, baud, dry_run)
        return

    log("hard reset through mpremote")
    try:
        run_checked(mpremote + ["connect", port, "resume", "reset"], dry_run, timeout=20)
    except (CalledProcessError, TimeoutExpired) as exc:
        log("mpremote reset failed, fallback to Ctrl-D soft reset: %s" % exc)
        soft_reset(port, baud, dry_run)


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy K230 CanMV files to /sdcard with mpremote.")
    parser.add_argument("files", nargs="*", help="local files to copy; default is main.py in --src-dir")
    parser.add_argument("--src-dir", default=os.getcwd(), help="directory used when resolving bare filenames")
    parser.add_argument("--all-py", action="store_true", help="copy every *.py in --src-dir")
    parser.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR, help="remote directory, default /sdcard")
    parser.add_argument("--port", default=None, help="serial port such as COM14; defaults to auto-detect")
    parser.add_argument("--allow-fuzzy-port", action="store_true", help="allow description-based serial auto-detection")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help="serial baud for Ctrl-C/Ctrl-D")
    parser.add_argument("--mpremote", default=None, help="mpremote executable; defaults to PATH or python -m mpremote")
    parser.add_argument("--host-python", default=None, help="host Python executable; defaults to current interpreter, then bounded auto-discovery")
    parser.add_argument("--break-count", type=int, default=DEFAULT_BREAK_COUNT, help="number of Ctrl-C bytes before copy")
    parser.add_argument("--no-break", action="store_true", help="do not interrupt the running main.py first")
    parser.add_argument("--reset", choices=("hard", "soft", "none"), default="hard", help="reset after copy")
    parser.add_argument("--no-reset", action="store_true", help="same as --reset none")
    parser.add_argument("--list-ports", action="store_true", help="list serial ports and exit")
    parser.add_argument("--dry-run", action="store_true", help="print commands without writing to the board")
    args = parser.parse_args()

    if args.list_ports:
        ensure_host_python(("serial",), args.host_python, __file__, sys.argv[1:])
        print_ports()
        return 0

    if not args.dry_run:
        external_mpremote = args.mpremote or os.environ.get("MPREMOTE") or shutil.which("mpremote")
        required_modules = ("serial",) if external_mpremote else ("serial", "mpremote")
        ensure_host_python(
            required_modules,
            args.host_python,
            __file__,
            sys.argv[1:],
            capabilities=("serial", "mpremote"),
        )
    elif not args.port:
        ensure_host_python(("serial",), args.host_python, __file__, sys.argv[1:])

    port = resolve_port(args.port, allow_fuzzy=args.allow_fuzzy_port)
    mpremote = resolve_mpremote(args.mpremote, required=(not args.dry_run))
    files = collect_files(args.files, args.src_dir, args.all_py)
    reset_mode = "none" if args.no_reset else args.reset

    log("port: %s" % port)
    log("mpremote: %s" % command_text(mpremote))
    log("selected files: %s" % ", ".join(path.name for path in files))

    if not args.no_break:
        break_main_loop(port, args.baud, args.break_count, args.dry_run)

    for src in files:
        deploy_file(mpremote, port, src, args.remote_dir, args.dry_run)

    reset_device(mpremote, port, args.baud, reset_mode, args.dry_run)
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
