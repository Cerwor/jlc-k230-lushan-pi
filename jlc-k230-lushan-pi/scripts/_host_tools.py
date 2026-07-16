#!/usr/bin/env python3
"""Shared host-side helpers for K230 maintenance scripts."""

from __future__ import annotations

import importlib.util
import locale
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


TESTED_CANMV_VID_PID = (0x1209, 0xABD1)
PORT_KEYWORDS = ("canmv", "kendryte", "k230", "usb serial device")
HOST_PYTHON_ENV = "K230_HOST_PYTHON"
HOST_REEXEC_DEPTH_ENV = "K230_HOST_REEXEC_DEPTH"
HOST_PROBE_TIMEOUT = 8


def _normalized_executable(value: str | None) -> str | None:
    if not value:
        return None
    expanded = os.path.expandvars(os.path.expanduser(value.strip().strip('"')))
    if os.path.isfile(expanded):
        return str(Path(expanded).resolve())
    found = shutil.which(expanded)
    if found:
        return str(Path(found).resolve())
    return None


def _executable_key(value: str) -> str:
    return os.path.normcase(os.path.realpath(value))


def same_executable(left: str, right: str) -> bool:
    return _executable_key(left) == _executable_key(right)


def parse_py_launcher_paths(output: str) -> list[str]:
    paths: list[str] = []
    for line in output.splitlines():
        match = re.search(r"([A-Za-z]:[\\/].*?\.exe)(?:\s|$)", line, re.IGNORECASE)
        if match:
            paths.append(match.group(1).strip().strip('"'))
    return paths


def _command_output(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding=locale.getpreferredencoding(False),
            errors="replace",
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout


def discover_python_candidates() -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()

    def add(value: str | None) -> None:
        resolved = _normalized_executable(value)
        if not resolved:
            return
        key = _executable_key(resolved)
        if key in seen:
            return
        seen.add(key)
        candidates.append(resolved)

    add(sys.executable)
    add(os.environ.get(HOST_PYTHON_ENV))

    for env_name in ("VIRTUAL_ENV", "CONDA_PREFIX"):
        prefix = os.environ.get(env_name)
        if not prefix:
            continue
        if os.name == "nt":
            add(os.path.join(prefix, "python.exe"))
        else:
            add(os.path.join(prefix, "bin", "python"))

    if os.name == "nt":
        for path in parse_py_launcher_paths(_command_output(["py", "-0p"])):
            add(path)
        for command_name in ("python", "python3"):
            for line in _command_output(["where.exe", command_name]).splitlines():
                add(line.strip())
    else:
        for command_name in ("python3", "python"):
            add(shutil.which(command_name))

    return candidates


def probe_python_modules(executable: str, modules: tuple[str, ...]) -> tuple[bool, str]:
    code = (
        "import importlib\n"
        "modules=%r\n"
        "for name in modules:\n"
        "    importlib.import_module(name)\n"
    ) % (modules,)
    try:
        result = subprocess.run(
            [executable, "-c", code],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=HOST_PROBE_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if result.returncode == 0:
        return True, ""
    detail = result.stderr.strip().splitlines()
    return False, detail[-1] if detail else "dependency probe failed"


def find_compatible_host_python(
    required_modules: tuple[str, ...], explicit: str | None = None
) -> tuple[str | None, list[tuple[str, str]]]:
    if explicit:
        resolved = _normalized_executable(explicit)
        if not resolved:
            return None, [(explicit, "executable not found")]
        candidates = [resolved]
    else:
        candidates = discover_python_candidates()

    checked: list[tuple[str, str]] = []
    for candidate in candidates:
        compatible, detail = probe_python_modules(candidate, required_modules)
        checked.append((candidate, detail))
        if compatible:
            return candidate, checked
    return None, checked


def ensure_host_python(
    required_modules: tuple[str, ...],
    explicit: str | None,
    script_path: str,
    argv: list[str],
    capabilities: tuple[str, ...] | None = None,
) -> None:
    selected, checked = find_compatible_host_python(required_modules, explicit)
    capability_names = capabilities or required_modules
    capability_text = ",".join(capability_names)
    if not selected:
        details = []
        for executable, reason in checked:
            details.append("  %s: %s" % (executable, reason))
        suffix = "\n" + "\n".join(details) if details else ""
        raise SystemExit(
            "No compatible host Python found for: %s. Pass --host-python or install the missing dependencies.%s"
            % (capability_text, suffix)
        )

    if same_executable(selected, sys.executable):
        print("HOST_PYTHON=%s" % selected)
        print("HOST_DEPENDENCIES=%s" % capability_text)
        return

    try:
        depth = int(os.environ.get(HOST_REEXEC_DEPTH_ENV, "0"))
    except ValueError:
        depth = 0
    if depth >= 1:
        raise SystemExit("Host Python re-execution limit reached before deployment")

    print("HOST_PYTHON_REEXEC=%s" % selected)
    print("HOST_DEPENDENCIES=%s" % capability_text)
    sys.stdout.flush()
    env = os.environ.copy()
    env[HOST_REEXEC_DEPTH_ENV] = str(depth + 1)
    try:
        result = subprocess.run([selected, str(Path(script_path).resolve()), *argv], env=env, check=False)
    except OSError as exc:
        raise SystemExit("Could not start selected host Python %s: %s" % (selected, exc)) from exc
    raise SystemExit(result.returncode)


def require_serial():
    try:
        import serial
        from serial.tools import list_ports
    except ImportError as exc:
        raise SystemExit("pyserial is required: python -m pip install pyserial") from exc
    return serial, list_ports


def send_ctrl_c_burst(port: str, baud: int, count: int) -> None:
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


def send_soft_reset(port: str, baud: int) -> None:
    serial, _list_ports = require_serial()
    with serial.Serial(port, baud, timeout=0.3, write_timeout=2) as ser:
        ser.write(b"\x04")
        ser.flush()


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


def mpremote_host_modules(explicit: str | None) -> tuple[str, ...]:
    external = explicit or os.environ.get("MPREMOTE") or shutil.which("mpremote")
    if external:
        return ("serial",)
    return ("serial", "mpremote")


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
