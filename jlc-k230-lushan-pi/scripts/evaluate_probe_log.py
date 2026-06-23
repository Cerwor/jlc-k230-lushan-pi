#!/usr/bin/env python3
"""判读 K230 板端探针日志，输出简短的验收结论。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


FIELD_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)")


def read_log(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8", errors="replace")


def find_last_line(text: str, prefix: str) -> str | None:
    found = None
    for line in text.splitlines():
        line = line.lstrip("\ufeff")
        if line.startswith(prefix):
            found = line
    return found


def fields_from_line(line: str | None) -> dict[str, str]:
    if not line:
        return {}
    values: dict[str, str] = {}
    for match in FIELD_RE.finditer(line):
        values[match.group(1)] = match.group(2)
    return values


def to_int(fields: dict[str, str], key: str, default: int = 0) -> int:
    raw = fields.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def rate(num: int, den: int) -> float:
    if den <= 0:
        return 0.0
    return float(num) / float(den)


def worse_status(current: str, next_status: str) -> str:
    order = {"pass": 0, "warn": 1, "fail": 2}
    if order[next_status] > order[current]:
        return next_status
    return current


def emit(tag: str, status: str, facts: list[str], notes: list[str], strict: bool) -> int:
    if strict and status == "warn":
        status = "fail"
        notes.append("strict mode treats warnings as failures")
    print("%s status=%s %s" % (tag, status, " ".join(facts)))
    if notes:
        print("%s_NOTES %s" % (tag, "; ".join(notes)))
    if status == "fail":
        return 1
    return 0


def eval_rect(text: str, strict: bool) -> int:
    line = find_last_line(text, "RECT_PROBE_DONE")
    if not line:
        return emit("ACCEPT_RECT", "fail", [], ["missing RECT_PROBE_DONE"], strict)

    fields = fields_from_line(line)
    frames = to_int(fields, "frames")
    hits = to_int(fields, "hits")
    misses = to_int(fields, "misses")
    fps = to_int(fields, "fps")
    big_jumps = to_int(fields, "big_jumps")
    max_step = to_int(fields, "max_step")
    cv_lite = to_int(fields, "cv_lite", 1)
    hit_rate = rate(hits, frames)

    status = "pass"
    notes: list[str] = []
    if cv_lite == 0:
        status = "fail"
        notes.append("cv_lite is unavailable")
    if frames < 100:
        status = worse_status(status, "fail")
        notes.append("too few frames for target regression")
    if hit_rate < 0.80:
        status = worse_status(status, "fail")
        notes.append("hit rate below 80 percent")
    elif hit_rate < 0.95:
        status = worse_status(status, "warn")
        notes.append("hit rate below contest-ready 95 percent")
    if fps < 20:
        status = worse_status(status, "fail")
        notes.append("fps below 20")
    elif fps < 45:
        status = worse_status(status, "warn")
        notes.append("fps below the tested high-FPS rectangle baseline")
    if big_jumps > 5:
        status = worse_status(status, "warn")
        notes.append("large center jumps observed")

    facts = [
        "frames=%d" % frames,
        "hits=%d" % hits,
        "misses=%d" % misses,
        "hit_rate=%.1f%%" % (hit_rate * 100.0),
        "fps=%d" % fps,
        "max_step=%d" % max_step,
        "big_jumps=%d" % big_jumps,
    ]
    return emit("ACCEPT_RECT", status, facts, notes, strict)


def eval_circle(text: str, strict: bool) -> int:
    line = find_last_line(text, "CIRCLE_PROBE_DONE")
    if not line:
        return emit("ACCEPT_CIRCLE", "fail", [], ["missing CIRCLE_PROBE_DONE"], strict)

    fields = fields_from_line(line)
    frames = to_int(fields, "frames")
    detect_runs = to_int(fields, "detect_runs")
    raw_hits = to_int(fields, "raw_hits")
    track_hits = to_int(fields, "track_hits")
    overlay_frames = to_int(fields, "overlay_frames")
    fps = to_int(fields, "fps")
    big_jumps = to_int(fields, "big_jumps")
    raw_rate = rate(raw_hits, detect_runs)
    track_rate = rate(track_hits, detect_runs)
    overlay_rate = rate(overlay_frames, frames)

    status = "pass"
    notes: list[str] = []
    if frames < 100 or detect_runs < 20:
        status = worse_status(status, "fail")
        notes.append("too few frames or detection runs")
    if fps < 10:
        status = worse_status(status, "fail")
        notes.append("fps below 10")
    elif fps < 25:
        status = worse_status(status, "warn")
        notes.append("fps is low for live aiming")
    if overlay_frames == 0:
        status = worse_status(status, "fail")
        notes.append("no held circle overlay was produced")
    elif overlay_rate < 0.50:
        status = worse_status(status, "warn")
        notes.append("overlay hold rate below 50 percent")
    if raw_rate < 0.50:
        status = worse_status(status, "warn")
        notes.append("raw circle detection is scene-sensitive")
    if track_rate < 0.30:
        status = worse_status(status, "warn")
        notes.append("tracked circle rate is weak")
    if big_jumps > 5:
        status = worse_status(status, "warn")
        notes.append("large circle jumps observed")

    facts = [
        "frames=%d" % frames,
        "detect_runs=%d" % detect_runs,
        "raw_rate=%.1f%%" % (raw_rate * 100.0),
        "track_rate=%.1f%%" % (track_rate * 100.0),
        "overlay_rate=%.1f%%" % (overlay_rate * 100.0),
        "fps=%d" % fps,
        "big_jumps=%d" % big_jumps,
    ]
    return emit("ACCEPT_CIRCLE", status, facts, notes, strict)


def eval_yolo(text: str, strict: bool) -> int:
    line = find_last_line(text, "YOLO_PROBE_DONE")
    if not line:
        return emit("ACCEPT_YOLO", "fail", [], ["missing YOLO_PROBE_DONE"], strict)

    fields = fields_from_line(line)
    required = ("nncase", "aicube", "pipeline", "yolo5", "yolo8", "yolo11")
    status = "pass"
    notes: list[str] = []
    for key in required:
        if to_int(fields, key) != 1:
            status = worse_status(status, "fail")
            notes.append("%s import failed" % key)

    kmodels = to_int(fields, "kmodels")
    examples = to_int(fields, "examples")
    truncated = to_int(fields, "truncated")
    if kmodels <= 0:
        status = worse_status(status, "warn")
        notes.append("no .kmodel files found in scanned roots")
    if examples <= 0:
        status = worse_status(status, "warn")
        notes.append("no YOLO examples found in scanned roots")
    if truncated:
        status = worse_status(status, "warn")
        notes.append("resource scan was truncated")

    facts = [
        "nncase=%d" % to_int(fields, "nncase"),
        "aicube=%d" % to_int(fields, "aicube"),
        "pipeline=%d" % to_int(fields, "pipeline"),
        "yolo5=%d" % to_int(fields, "yolo5"),
        "yolo8=%d" % to_int(fields, "yolo8"),
        "yolo11=%d" % to_int(fields, "yolo11"),
        "kmodels=%d" % kmodels,
        "examples=%d" % examples,
    ]
    return emit("ACCEPT_YOLO", status, facts, notes, strict)


def eval_uart(text: str, strict: bool) -> int:
    if "UART2_LOOPBACK_PROBE_ERROR" in text:
        return emit("ACCEPT_UART", "fail", [], ["UART2 loopback probe raised an error"], strict)
    if "UART2_LOOPBACK_PROBE_DONE" not in text:
        return emit("ACCEPT_UART", "fail", [], ["missing UART2_LOOPBACK_PROBE_DONE"], strict)

    line = find_last_line(text, "UART2_LOOPBACK_DONE")
    tx_sweep_done = "UART_TX_SWEEP_DONE" in text
    if line:
        fields = fields_from_line(line)
        rx_count = to_int(fields, "rx")
        byte_count = to_int(fields, "bytes")
        status = "pass"
        notes: list[str] = []
        if rx_count <= 0 or byte_count <= 0:
            status = worse_status(status, "warn")
            notes.append("loopback pair was found but no UART bytes returned")
        if not tx_sweep_done:
            status = worse_status(status, "warn")
            notes.append("TX sweep did not finish")
        facts = [
            "tx_pin=%d" % to_int(fields, "tx_pin"),
            "rx_pin=%d" % to_int(fields, "rx_pin"),
            "rx=%d" % rx_count,
            "bytes=%d" % byte_count,
            "tx_sweep=%d" % int(tx_sweep_done),
        ]
        return emit("ACCEPT_UART", status, facts, notes, strict)

    status = "warn"
    notes = ["no physical loopback pair detected; verify TX/RX short and common ground"]
    facts = ["loopback=0", "tx_sweep=%d" % int(tx_sweep_done)]
    return emit("ACCEPT_UART", status, facts, notes, strict)


def eval_resources(text: str, strict: bool) -> int:
    line = find_last_line(text, "RESOURCE_PROBE_DONE")
    if not line:
        return emit("ACCEPT_RESOURCES", "fail", [], ["missing RESOURCE_PROBE_DONE"], strict)

    fields = fields_from_line(line)
    kmodels_line = find_last_line(text, "KMODELS count=")
    examples_line = find_last_line(text, "YOLO_PY_EXAMPLES count=")
    kmodels = 0
    examples = 0
    if kmodels_line:
        kmodels = to_int(fields_from_line(kmodels_line.replace("count=", "count_value=")), "count_value")
    if examples_line:
        examples = to_int(fields_from_line(examples_line.replace("count=", "count_value=")), "count_value")

    status = "pass"
    notes: list[str] = []
    if to_int(fields, "truncated"):
        status = worse_status(status, "warn")
        notes.append("scan was truncated")
    if kmodels <= 0 and examples <= 0:
        status = worse_status(status, "warn")
        notes.append("no models or YOLO examples found")

    facts = [
        "dirs=%d" % to_int(fields, "dirs"),
        "truncated=%d" % to_int(fields, "truncated"),
        "kmodels=%d" % kmodels,
        "examples=%d" % examples,
    ]
    return emit("ACCEPT_RESOURCES", status, facts, notes, strict)


def infer_kind(text: str) -> str:
    if "RECT_PROBE_DONE" in text:
        return "rect"
    if "CIRCLE_PROBE_DONE" in text:
        return "circle"
    if "YOLO_PROBE_DONE" in text:
        return "yolo"
    if "UART2_LOOPBACK_PROBE_DONE" in text:
        return "uart"
    if "RESOURCE_PROBE_DONE" in text:
        return "resources"
    return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate K230 probe logs.")
    parser.add_argument("log", help="log file path, or - for stdin")
    parser.add_argument("--kind", default="auto", choices=("auto", "rect", "circle", "yolo", "uart", "resources"))
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = parser.parse_args()

    text = read_log(args.log)
    kind = args.kind
    if kind == "auto":
        kind = infer_kind(text)

    if kind == "rect":
        return eval_rect(text, args.strict)
    if kind == "circle":
        return eval_circle(text, args.strict)
    if kind == "yolo":
        return eval_yolo(text, args.strict)
    if kind == "uart":
        return eval_uart(text, args.strict)
    if kind == "resources":
        return eval_resources(text, args.strict)

    print("ACCEPT_UNKNOWN status=fail")
    print("ACCEPT_UNKNOWN_NOTES could not infer probe type")
    return 1


if __name__ == "__main__":
    sys.exit(main())
