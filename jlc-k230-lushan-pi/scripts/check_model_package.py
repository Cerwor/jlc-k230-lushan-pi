#!/usr/bin/env python3
"""检查 K230 模型包 manifest、labels 和 kmodel 是否自洽。"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


VALID_TASK_TYPES = {"classify", "detect", "segment"}
VALID_YOLO_CLASSES = {"YOLOv5", "YOLOv8", "YOLO11", "custom"}
THRESHOLD_FIELDS = ("confidence_threshold", "nms_threshold", "mask_threshold")
CONVERSION_FIELDS = (
    "source_format",
    "nncase_version",
    "target_chip",
    "quantization",
    "target_firmware",
)


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def read_json(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail("cannot read manifest %s: %s" % (path, exc), failures)
        return {}
    if not isinstance(data, dict):
        fail("manifest root must be an object", failures)
        return {}
    return data


def read_labels(path: Path, failures: list[str]) -> list[str]:
    if not path.exists():
        fail("labels file not found: %s" % path, failures)
        return []
    if not path.is_file():
        fail("labels path is not a file: %s" % path, failures)
        return []
    labels: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().lstrip("\ufeff")
        if line:
            labels.append(line)
    if not labels:
        fail("labels file is empty: %s" % path, failures)
    return labels


def require_string(data: dict[str, Any], key: str, failures: list[str]) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        fail("manifest field %s must be a non-empty string" % key, failures)
        return ""
    return value.strip()


def package_relative_path(package_root: Path, raw: str, key: str, failures: list[str]) -> Path:
    path = Path(raw)
    if path.is_absolute():
        fail("manifest field %s must be package-relative, got absolute path: %s" % (key, raw), failures)
        return package_root / path.name
    if ".." in path.parts:
        fail("manifest field %s must not contain '..': %s" % (key, raw), failures)
    return package_root / path


def validate_size_list(data: dict[str, Any], key: str, failures: list[str], required: bool) -> None:
    value = data.get(key)
    if value is None and not required:
        return
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not isinstance(value[0], int)
        or not isinstance(value[1], int)
        or value[0] <= 0
        or value[1] <= 0
    ):
        fail("manifest field %s must be [positive_int, positive_int]" % key, failures)


def validate_thresholds(data: dict[str, Any], failures: list[str]) -> None:
    for key in THRESHOLD_FIELDS:
        value = data.get(key)
        if value is None:
            continue
        if not isinstance(value, (int, float)) or value < 0 or value > 1:
            fail("manifest field %s must be a number in [0, 1]" % key, failures)


def validate_conversion_metadata(
    data: dict[str, Any],
    failures: list[str],
    warnings: list[str],
) -> None:
    conversion = data.get("conversion")
    if conversion is None:
        warnings.append("manifest has no conversion metadata; retain the nncase and firmware versions externally")
        return
    if not isinstance(conversion, dict):
        fail("manifest field conversion must be an object", failures)
        return

    for key in CONVERSION_FIELDS:
        value = conversion.get(key)
        if value is None:
            warnings.append("conversion metadata missing %s" % key)
        elif not isinstance(value, str) or not value.strip():
            fail("manifest field conversion.%s must be a non-empty string" % key, failures)

    target_chip = conversion.get("target_chip")
    if isinstance(target_chip, str) and target_chip.strip() and "k230" not in target_chip.lower():
        warnings.append("conversion target_chip does not mention K230: %s" % target_chip)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def validate_package(package_root: Path) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    manifest_path = package_root / "model_manifest.json"
    if not manifest_path.exists():
        failures.append("missing model_manifest.json")
        return failures, warnings

    data = read_json(manifest_path, failures)
    if not data:
        return failures, warnings

    model_name = require_string(data, "model_name", failures)
    task_type = require_string(data, "task_type", failures)
    yolo_class = require_string(data, "yolo_class", failures)
    kmodel_file = require_string(data, "kmodel_file", failures)
    labels_file = require_string(data, "labels_file", failures)
    board_kmodel_path = require_string(data, "board_kmodel_path", failures)

    if task_type and task_type not in VALID_TASK_TYPES:
        fail("task_type must be one of %s" % sorted(VALID_TASK_TYPES), failures)
    if yolo_class and yolo_class not in VALID_YOLO_CLASSES:
        fail("yolo_class must be one of %s" % sorted(VALID_YOLO_CLASSES), failures)
    if board_kmodel_path and not board_kmodel_path.startswith("/"):
        fail("board_kmodel_path should be an absolute board path such as /sdcard/models/name.kmodel", failures)

    validate_size_list(data, "model_input_size", failures, required=True)
    validate_size_list(data, "rgb888p_size", failures, required=False)
    validate_size_list(data, "display_size", failures, required=False)
    validate_thresholds(data, failures)
    validate_conversion_metadata(data, failures, warnings)

    kmodel_path = package_relative_path(package_root, kmodel_file, "kmodel_file", failures)
    labels_path = package_relative_path(package_root, labels_file, "labels_file", failures)

    kmodel_ok = False
    if not kmodel_path.exists():
        fail("kmodel file not found: %s" % kmodel_path, failures)
    elif not kmodel_path.is_file():
        fail("kmodel path is not a file: %s" % kmodel_path, failures)
    elif kmodel_path.suffix.lower() != ".kmodel":
        fail("kmodel_file should end with .kmodel: %s" % kmodel_path.name, failures)
    else:
        kmodel_ok = True

    labels = read_labels(labels_path, failures)
    inline_labels = data.get("labels")
    if inline_labels is not None:
        if not isinstance(inline_labels, list) or not all(isinstance(item, str) for item in inline_labels):
            fail("manifest field labels must be a list of strings", failures)
        elif labels and inline_labels != labels:
            fail("manifest labels do not match labels.txt order/content", failures)

    if task_type == "detect" and "nms_threshold" not in data:
        warnings.append("detect model has no nms_threshold")
    if task_type == "segment" and "mask_threshold" not in data:
        warnings.append("segment model has no mask_threshold")
    if yolo_class == "custom":
        warnings.append("custom model: board code must define preprocessing and postprocess explicitly")
    if "preprocess" not in data:
        warnings.append("manifest has no preprocess note")
    if "postprocess" not in data:
        warnings.append("manifest has no postprocess note")

    print("MODEL_PACKAGE %s" % package_root)
    if model_name:
        print("MODEL_NAME %s" % model_name)
    if labels:
        print("LABELS %d %s" % (len(labels), ",".join(labels)))
    if kmodel_ok:
        print("KMODEL_SHA256 %s" % file_sha256(kmodel_path))

    return failures, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a K230 model package folder.")
    parser.add_argument("package_root", help="folder containing model_manifest.json, labels.txt, and .kmodel")
    args = parser.parse_args()

    package_root = Path(args.package_root).resolve()
    if not package_root.exists() or not package_root.is_dir():
        print("MODEL_PACKAGE_FAIL package folder not found: %s" % package_root)
        return 2

    failures, warnings = validate_package(package_root)
    for item in warnings:
        print("WARN %s" % item)
    for item in failures:
        print("FAIL %s" % item)

    if failures:
        print("MODEL_PACKAGE_FAIL failures=%d warnings=%d" % (len(failures), len(warnings)))
        return 1

    print("MODEL_PACKAGE_OK warnings=%d" % len(warnings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
