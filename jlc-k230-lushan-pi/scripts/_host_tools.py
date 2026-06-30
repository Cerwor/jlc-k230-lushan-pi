#!/usr/bin/env python3
"""Shared host-side helpers for K230 maintenance scripts."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys


TESTED_CANMV_VID_PID = (0x1209, 0xABD1)
PORT_KEYWORDS = ("canmv", "kendryte", "k230", "usb serial device")


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


def is_tested_canmv_port(port_info) -> bool:
    vid = getattr(port_info, "vid", None)
    pid = getattr(port_info, "pid", None)
    return vid == TESTED_CANMV_VID_PID[0] and pid == TESTED_CANMV_VID_PID[1]


def is_fuzzy_k230_port(port_info) -> bool:
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


def is_likely_k230(port_info, allow_fuzzy: bool = True) -> bool:
    if is_tested_canmv_port(port_info):
        return True
    return allow_fuzzy and is_fuzzy_k230_port(port_info)


def print_ports() -> None:
    ports = get_ports()
    if not ports:
        print("No serial ports found.")
        return

    for item in ports:
        if is_tested_canmv_port(item):
            marker = " *"
        elif is_fuzzy_k230_port(item):
            marker = " ?"
        else:
            marker = "  "
        print("%s %s" % (marker, describe_port(item)))
    print("Legend: * tested VID:PID match, ? fuzzy description match")


def resolve_port(explicit_port: str | None, allow_fuzzy: bool = False) -> str:
    if explicit_port:
        return explicit_port

    env_port = os.environ.get("K230_PORT") or os.environ.get("PORT")
    if env_port:
        return env_port

    ports = get_ports()
    tested = [item for item in ports if is_tested_canmv_port(item)]
    if len(tested) == 1:
        return tested[0].device
    if len(tested) > 1:
        choices = "\n".join("  %s" % describe_port(item) for item in tested)
        raise SystemExit("Multiple tested K230 ports found; pass --port.\n%s" % choices)

    fuzzy = [item for item in ports if is_fuzzy_k230_port(item)]
    if allow_fuzzy and len(fuzzy) == 1:
        return fuzzy[0].device
    if allow_fuzzy and len(fuzzy) > 1:
        choices = "\n".join("  %s" % describe_port(item) for item in fuzzy)
        raise SystemExit("Multiple fuzzy K230 ports found; pass --port.\n%s" % choices)

    choices = "\n".join("  %s" % describe_port(item) for item in ports)
    if not choices:
        choices = "  (none)"
    hint = "Pass --port explicitly"
    if fuzzy and not allow_fuzzy:
        hint += " or add --allow-fuzzy-port for description-based matching"
    raise SystemExit("No tested K230 VID:PID port auto-detected. %s.\n%s" % (hint, choices))


def resolve_mpremote(explicit: str | None, required: bool = True) -> list[str]:
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

    if not required:
        return ["mpremote"]

    raise SystemExit("mpremote is required: python -m pip install mpremote")


def command_text(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def run_checked(
    command: list[str],
    dry_run: bool,
    check: bool = True,
    timeout: float | None = None,
) -> subprocess.CompletedProcess:
    print("$ %s" % command_text(command))
    if dry_run:
        return subprocess.CompletedProcess(command, 0)
    return subprocess.run(command, check=check, timeout=timeout)
