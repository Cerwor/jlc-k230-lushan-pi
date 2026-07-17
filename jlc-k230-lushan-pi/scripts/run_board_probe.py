#!/usr/bin/env python3
"""Run bounded K230 board probes from an installed skill."""

from __future__ import annotations

import argparse
import hashlib
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


def export_probe(
    probes: tuple[tuple[str, str], ...],
    probes_dir: Path,
    evaluator: Path,
    vision: str,
    output_text: str,
    force: bool,
) -> int:
    if len(probes) != 1:
        raise SystemExit(
            "--export-main requires a single-script mode; %s contains %d probes"
            % (vision, len(probes))
        )

    script_name, assessment_kind = probes[0]
    source = (probes_dir / script_name).resolve()
    if not source.exists():
        raise SystemExit("board probe is missing: %s" % source)

    output = Path(output_text).expanduser().resolve()
    if output.suffix.lower() != ".py":
        raise SystemExit("--export-main output must end with .py: %s" % output)
    if output == source:
        raise SystemExit("refusing to overwrite the bundled probe source: %s" % source)
    if output.exists() and not force:
        raise SystemExit("export output already exists: %s; use --force-export to replace it" % output)

    payload = source.read_bytes()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()

    print("BOARD_PROBE_EXPORT source=%s" % source)
    print("BOARD_PROBE_EXPORT output=%s bytes=%d sha256=%s" % (output, len(payload), digest))
    if assessment_kind:
        command = [sys.executable, str(evaluator), "--kind", assessment_kind, "probe.log"]
        print("BOARD_PROBE_EXPORT_ASSESS %s" % command_text(command))
    print("BOARD_PROBE_EXPORT_OK vision=%s scripts=1 writes_sdcard=0" % vision)
    return 0


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
    parser.add_argument(
        "--export-main",
        metavar="PATH",
        help="export one self-contained probe as a local .py file for manual CanMV IDE or SD-card use",
    )
    parser.add_argument(
        "--force-export",
        action="store_true",
        help="allow --export-main to replace an existing local output file",
    )
    args = parser.parse_args()

    if args.force_export and not args.export_main:
        parser.error("--force-export requires --export-main")
    if args.export_main and args.list_ports:
        parser.error("--export-main cannot be combined with --list-ports")
    if args.export_main and args.dry_run:
        parser.error("--export-main cannot be combined with --dry-run")

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
    probes_dir = scripts_dir / "probes"
    raw_runner = scripts_dir / "run_canmv_raw_repl.py"
    evaluator = scripts_dir / "evaluate_probe_log.py"
    if not probes_dir.is_dir() or not raw_runner.exists() or not evaluator.exists():
        raise SystemExit("installed skill is incomplete: probes, raw runner, or evaluator is missing")

    probes = PROBE_MODES[args.vision]
    if args.export_main:
        return export_probe(
            probes,
            probes_dir,
            evaluator,
            args.vision,
            args.export_main,
            args.force_export,
        )

    if not args.dry_run:
        ensure_host_python(("serial",), args.host_python, __file__, sys.argv[1:])

    for script_name, assessment_kind in probes:
        probe_path = probes_dir / script_name
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
