#!/usr/bin/env python3
"""Run bounded K230 board probes from an installed skill."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from _host_tools import command_text
from _host_tools import ensure_host_python
from _host_tools import print_ports


PROBE_MODES = {
    "smoke": (("smoke_camera_lcd.py", ""),),
    "sensor": (("probe_k230_sensor_init.py", ""),),
    "otsu": (("probe_otsu_threshold.py", ""),),
    "resources": (("probe_board_resources.py", "resources"),),
    "resource-cycle": (("probe_resource_lifecycle.py", "lifecycle"),),
    "rect-target": (("probe_cvlite_rectangle_target.py", "rect"),),
    "circle-target": (("probe_circle_target.py", "circle"),),
    "yolo": (("probe_yolo_runtime.py", "yolo"),),
    "uart-loopback": (("probe_uart2_loopback.py", "uart"),),
    "all-core": (
        ("smoke_camera_lcd.py", ""),
        ("probe_k230_sensor_init.py", ""),
        ("probe_otsu_threshold.py", ""),
    ),
}


def build_raw_command(
    python_executable: str,
    raw_runner: Path,
    probe_path: Path,
    port: str | None,
    baud: int | None,
    timeout: float,
) -> list[str]:
    command = [python_executable, str(raw_runner)]
    if port:
        command.extend(("--port", port))
    if baud:
        command.extend(("--baud", str(baud)))
    command.extend(("--timeout", str(timeout), str(probe_path)))
    return command


def run_captured(command: list[str], input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        input=input_text,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def run_probe(
    command: list[str],
    assessment_kind: str,
    evaluator: Path,
    strict: bool,
    dry_run: bool,
) -> int:
    print("$ %s" % command_text(command))
    if dry_run:
        if assessment_kind:
            print("ASSESSMENT_PLANNED kind=%s" % assessment_kind)
        return 0

    result = run_captured(command)
    if result.stdout:
        sys.stdout.write(result.stdout)
        if not result.stdout.endswith("\n"):
            sys.stdout.write("\n")
    if result.returncode != 0:
        return result.returncode

    if not assessment_kind:
        return 0

    assess_command = [sys.executable, str(evaluator), "--kind", assessment_kind]
    if strict:
        assess_command.append("--strict")
    assess_command.append("-")
    print("$ %s" % command_text(assess_command))
    assessment = run_captured(assess_command, result.stdout)
    if assessment.stdout:
        sys.stdout.write(assessment.stdout)
        if not assessment.stdout.endswith("\n"):
            sys.stdout.write("\n")
    return assessment.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run read-only K230 probes through raw REPL without writing /sdcard/main.py."
    )
    parser.add_argument("--vision", choices=("none", *PROBE_MODES), default="none")
    parser.add_argument("--port", help="serial port such as COM14; defaults to bounded auto-detection")
    parser.add_argument("--baud", type=int, help="raw REPL baud; defaults to the raw runner fallback sequence")
    parser.add_argument("--timeout", type=float, default=45.0, help="seconds allowed for each board probe")
    parser.add_argument("--host-python", help="host Python executable; otherwise use bounded auto-discovery")
    parser.add_argument("--list-ports", action="store_true", help="list serial ports and exit")
    parser.add_argument("--strict", action="store_true", help="treat probe assessment warnings as failures")
    parser.add_argument("--dry-run", action="store_true", help="print the planned RAM-only probe commands")
    args = parser.parse_args()

    if args.list_ports:
        if not args.dry_run:
            ensure_host_python(("serial",), args.host_python, __file__, sys.argv[1:])
            print_ports()
        else:
            print("LIST_PORTS_PLANNED")
        print("BOARD_PROBE_OK vision=none scripts=0 writes_sdcard=0")
        return 0

    if args.vision == "none":
        parser.error("choose --vision or use --list-ports")

    scripts_dir = Path(__file__).resolve().parent
    raw_runner = scripts_dir / "run_canmv_raw_repl.py"
    evaluator = scripts_dir / "evaluate_probe_log.py"
    if not raw_runner.exists() or not evaluator.exists():
        raise SystemExit("installed skill is incomplete: raw runner or evaluator is missing")

    if not args.dry_run:
        ensure_host_python(("serial",), args.host_python, __file__, sys.argv[1:])

    probes = PROBE_MODES[args.vision]
    for script_name, assessment_kind in probes:
        probe_path = scripts_dir / script_name
        if not probe_path.exists():
            raise SystemExit("board probe is missing: %s" % probe_path)
        command = build_raw_command(
            sys.executable,
            raw_runner,
            probe_path,
            args.port,
            args.baud,
            args.timeout,
        )
        result = run_probe(command, assessment_kind, evaluator, args.strict, args.dry_run)
        if result != 0:
            return result

    print("BOARD_PROBE_OK vision=%s scripts=%d writes_sdcard=0" % (args.vision, len(probes)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
