#!/usr/bin/env python3
"""Deploy one binary file to K230 storage through the existing raw REPL transport."""

from __future__ import annotations

import argparse
import base64
import hashlib
import re
import sys
import time
from pathlib import Path

from _host_tools import ensure_host_python
from _host_tools import print_ports
from _host_tools import require_serial
from _host_tools import resolve_port
from run_canmv_raw_repl import (
    DEFAULT_BAUDS,
    RawReplEnterError,
    enter_raw_repl,
    run_code,
)


DEFAULT_REMOTE_ROOT = "/sdcard"
DEFAULT_DATA_CHUNK_SIZE = 768
VERIFY_RE = re.compile(r"RAW_DEPLOY_VERIFY size=(\d+) sha256=([0-9a-fA-F]{64})")


def normalize_remote_path(remote: str | None, local_name: str) -> str:
    value = remote or (DEFAULT_REMOTE_ROOT + "/" + local_name)
    if "\\" in value or "\x00" in value or ":" in value:
        raise ValueError("remote path must use a safe POSIX path under /sdcard")
    if not value.startswith(DEFAULT_REMOTE_ROOT + "/"):
        raise ValueError("remote path must be a file under /sdcard")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts[2:]):
        raise ValueError("remote path must not contain empty, '.' or '..' components")
    if value.endswith("/"):
        raise ValueError("remote path must name a file")
    return value


def deployment_paths(target: str) -> tuple[str, str, str]:
    return target, target + ".codex.tmp", target + ".codex.bak"


def iter_payload_chunks(payload: bytes, chunk_size: int):
    for offset in range(0, len(payload), chunk_size):
        yield payload[offset : offset + chunk_size]


def board_init_code(temp_path: str) -> str:
    return "_f=open(%r,'wb')\n_f.close()\nprint('RAW_DEPLOY_TEMP_READY')\n" % temp_path


def board_append_code(temp_path: str, chunk: bytes) -> str:
    encoded = base64.b64encode(chunk).decode("ascii")
    # CanMV 的 a2b_base64() 要求 bytes，生成代码时必须保留 b 前缀。
    return (
        "import binascii\n"
        "_f=open(%r,'ab')\n"
        "_f.write(binascii.a2b_base64(b'%s'))\n"
        "_f.close()\n"
        "print('RAW_DEPLOY_CHUNK_OK')\n"
    ) % (temp_path, encoded)


def board_verify_code(path: str) -> str:
    return (
        "import hashlib,binascii\n"
        "_h=hashlib.sha256()\n"
        "_n=0\n"
        "_f=open(%r,'rb')\n"
        "while True:\n"
        "    _b=_f.read(4096)\n"
        "    if not _b:\n"
        "        break\n"
        "    _n+=len(_b)\n"
        "    _h.update(_b)\n"
        "_f.close()\n"
        "_d=binascii.hexlify(_h.digest()).decode()\n"
        "print('RAW_DEPLOY_VERIFY size=%%d sha256=%%s' %% (_n,_d))\n"
    ) % path


def board_replace_code(target: str, temp_path: str, backup_path: str) -> str:
    return (
        "import os\n"
        "def _exists(_p):\n"
        "    try:\n"
        "        os.stat(_p)\n"
        "        return True\n"
        "    except OSError:\n"
        "        return False\n"
        "_target=%r\n"
        "_temp=%r\n"
        "_backup=%r\n"
        "if hasattr(os,'replace'):\n"
        "    os.replace(_temp,_target)\n"
        "else:\n"
        "    if _exists(_backup):\n"
        "        raise OSError('stale deployment backup exists: '+_backup)\n"
        "    _had_target=_exists(_target)\n"
        "    if _had_target:\n"
        "        os.rename(_target,_backup)\n"
        "    try:\n"
        "        os.rename(_temp,_target)\n"
        "    except Exception:\n"
        "        if _had_target and not _exists(_target):\n"
        "            os.rename(_backup,_target)\n"
        "        raise\n"
        "    if _had_target:\n"
        "        os.remove(_backup)\n"
        "print('RAW_DEPLOY_REPLACED')\n"
    ) % (target, temp_path, backup_path)


def board_cleanup_code(temp_path: str) -> str:
    return (
        "import os\n"
        "try:\n"
        "    os.remove(%r)\n"
        "except OSError:\n"
        "    pass\n"
        "print('RAW_DEPLOY_TEMP_CLEAN')\n"
    ) % temp_path


def parse_verify_output(output: str) -> tuple[int, str]:
    match = VERIFY_RE.search(output)
    if not match:
        raise ValueError("board verification marker is missing")
    return int(match.group(1)), match.group(2).lower()


def verify_remote(ser, path: str, expected_size: int, expected_sha256: str, timeout: float, code_chunk_size: int) -> None:
    output = run_code(ser, board_verify_code(path), timeout, code_chunk_size)
    actual_size, actual_sha256 = parse_verify_output(output)
    if actual_size != expected_size or actual_sha256 != expected_sha256:
        raise RuntimeError(
            "remote verification failed for %s: expected size=%d sha256=%s, got size=%d sha256=%s"
            % (path, expected_size, expected_sha256, actual_size, actual_sha256)
        )
    print("RAW_DEPLOY_VERIFIED path=%s size=%d sha256=%s" % (path, actual_size, actual_sha256))


def cleanup_temp(ser, temp_path: str, timeout: float, code_chunk_size: int) -> None:
    try:
        run_code(ser, board_cleanup_code(temp_path), timeout, code_chunk_size)
    except BaseException as exc:
        sys.stderr.write("Warning: could not remove temporary board file %s: %s\n" % (temp_path, exc))


def soft_reset_once(ser) -> None:
    # 退出 raw REPL 后只发送一次 Ctrl-D，不追加自动启动验证。
    ser.write(b"\x02")
    ser.flush()
    time.sleep(0.15)
    ser.write(b"\x04")
    ser.flush()
    print("RAW_DEPLOY_RESET_ONCE")


def deploy(ser, payload: bytes, target: str, data_chunk_size: int, timeout: float, code_chunk_size: int, reset: bool) -> None:
    target, temp_path, backup_path = deployment_paths(target)
    expected_size = len(payload)
    expected_sha256 = hashlib.sha256(payload).hexdigest()
    started_write = False

    try:
        run_code(ser, board_init_code(temp_path), timeout, code_chunk_size)
        started_write = True
        for index, chunk in enumerate(iter_payload_chunks(payload, data_chunk_size), start=1):
            run_code(ser, board_append_code(temp_path, chunk), timeout, code_chunk_size)
            print("RAW_DEPLOY_CHUNK index=%d bytes=%d" % (index, len(chunk)))

        verify_remote(ser, temp_path, expected_size, expected_sha256, timeout, code_chunk_size)
        run_code(ser, board_replace_code(target, temp_path, backup_path), timeout, code_chunk_size)
        verify_remote(ser, target, expected_size, expected_sha256, timeout, code_chunk_size)
        if reset:
            soft_reset_once(ser)
    except BaseException:
        if started_write:
            cleanup_temp(ser, temp_path, timeout, code_chunk_size)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deploy one binary file to K230 /sdcard through the existing raw REPL handshake."
    )
    parser.add_argument("local_file", nargs="?", help="local file; bytes are preserved exactly")
    parser.add_argument("--remote", help="target path under /sdcard; defaults to /sdcard/<local filename>")
    parser.add_argument("--port", help="serial port such as COM14; omitted means conservative auto-detection")
    parser.add_argument("--baud", type=int, help="serial baud; omitted tries 2000000 then 115200")
    parser.add_argument("--timeout", type=float, default=15.0, help="seconds for each raw REPL operation")
    parser.add_argument("--data-chunk-size", type=int, default=DEFAULT_DATA_CHUNK_SIZE, help="source bytes per append")
    parser.add_argument("--code-chunk-size", type=int, default=128, help="raw REPL transport write chunk")
    parser.add_argument("--no-reset", action="store_true", help="do not issue the single soft reset after verification")
    parser.add_argument("--dry-run", action="store_true", help="show the deployment plan without opening a serial port")
    parser.add_argument("--list-ports", action="store_true", help="list detected serial ports and exit")
    parser.add_argument("--host-python", help="host Python executable; defaults to current interpreter, then bounded auto-discovery")
    parser.add_argument("--mode", choices=("STANDARD", "QUICK_PATCH", "RECOVERY"), default="STANDARD")
    parser.add_argument("--reason", help="concise deployment-mode evidence; required for QUICK_PATCH and RECOVERY")
    args = parser.parse_args()

    if args.data_chunk_size <= 0 or args.code_chunk_size <= 0:
        parser.error("chunk sizes must be positive")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.mode != "STANDARD" and not args.reason:
        parser.error("--reason is required for QUICK_PATCH and RECOVERY")

    if args.list_ports:
        ensure_host_python(("serial",), args.host_python, __file__, sys.argv[1:])
        print_ports()
        return 0
    if not args.local_file:
        parser.error("local_file is required unless --list-ports is used")

    local_path = Path(args.local_file).resolve()
    if not local_path.is_file():
        raise SystemExit("local file does not exist: %s" % local_path)
    try:
        target = normalize_remote_path(args.remote, local_path.name)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    payload = local_path.read_bytes()
    expected_sha256 = hashlib.sha256(payload).hexdigest()
    chunk_count = (len(payload) + args.data_chunk_size - 1) // args.data_chunk_size
    reason = args.reason or "Default board-write mode"
    print("DEPLOY_MODE=%s" % args.mode)
    print("REASON=%s" % reason)
    print(
        "RAW_DEPLOY_PLAN local=%s remote=%s bytes=%d sha256=%s chunks=%d reset=%s"
        % (local_path, target, len(payload), expected_sha256, chunk_count, not args.no_reset)
    )
    if args.dry_run:
        print("RAW_DEPLOY_DRY_RUN")
        return 0

    ensure_host_python(("serial",), args.host_python, __file__, sys.argv[1:])
    serial, _list_ports = require_serial()
    port = resolve_port(args.port, allow_fuzzy=True)
    baud_list = (args.baud,) if args.baud else DEFAULT_BAUDS
    last_enter_error = None

    for baud in baud_list:
        try:
            ser = serial.Serial(port, baud, timeout=0.2, write_timeout=5)
        except Exception as exc:
            raise SystemExit("Could not open %s at %d baud: %s" % (port, baud, exc)) from exc
        entered = False
        try:
            enter_raw_repl(ser, port, baud)
            entered = True
            deploy(
                ser,
                payload,
                target,
                args.data_chunk_size,
                args.timeout,
                args.code_chunk_size,
                not args.no_reset,
            )
            print("RAW_DEPLOY_OK remote=%s" % target)
            return 0
        except RawReplEnterError as exc:
            last_enter_error = str(exc)
            if len(baud_list) > 1:
                sys.stderr.write("Raw REPL handshake failed at %d baud; trying next baud if available.\n" % baud)
            else:
                sys.stderr.write(last_enter_error + "\n")
                return 1
        except (RuntimeError, ValueError) as exc:
            sys.stderr.write("RAW_DEPLOY_FAIL %s\n" % exc)
            return 1
        except SystemExit as exc:
            return int(exc.code) if isinstance(exc.code, int) else 1
        finally:
            if entered and args.no_reset:
                try:
                    ser.write(b"\x02")
                    ser.flush()
                except Exception:
                    pass
            ser.close()

    if last_enter_error:
        sys.stderr.write(last_enter_error + "\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
