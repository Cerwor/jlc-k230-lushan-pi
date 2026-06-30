from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "jlc-k230-lushan-pi"
SCRIPTS_DIR = SKILL_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import mpremote_snapshot  # noqa: E402
import validate_skill  # noqa: E402


def cleanup_skill_pycache() -> None:
    shutil.rmtree(SCRIPTS_DIR / "__pycache__", ignore_errors=True)


def run_python(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [sys.executable, *args],
            cwd=str(REPO_ROOT),
            input=input_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    finally:
        cleanup_skill_pycache()


def write_valid_model_package(root: Path) -> None:
    (root / "demo.kmodel").write_bytes(b"\x00\x01demo")
    (root / "labels.txt").write_text("target\n", encoding="utf-8")
    manifest = {
        "model_name": "ci-demo",
        "task_type": "detect",
        "yolo_class": "YOLOv8",
        "kmodel_file": "demo.kmodel",
        "labels_file": "labels.txt",
        "board_kmodel_path": "/sdcard/models/demo.kmodel",
        "model_input_size": [320, 320],
        "confidence_threshold": 0.35,
        "nms_threshold": 0.45,
        "labels": ["target"],
        "preprocess": "documented",
        "postprocess": "documented",
    }
    (root / "model_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class ModelPackageTests(unittest.TestCase):
    def test_valid_model_package_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package = Path(temp_dir)
            write_valid_model_package(package)
            result = run_python(str(SCRIPTS_DIR / "check_model_package.py"), str(package))

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("MODEL_PACKAGE_OK", result.stdout)

    def test_path_traversal_model_package_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package = Path(temp_dir)
            write_valid_model_package(package)
            manifest_path = package / "model_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["kmodel_file"] = "../escape.kmodel"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = run_python(str(SCRIPTS_DIR / "check_model_package.py"), str(package))

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("must not contain '..'", result.stdout)


class ProbeLogTests(unittest.TestCase):
    def test_rect_probe_passes_on_good_summary(self) -> None:
        log = "RECT_PROBE_DONE frames=300 hits=296 misses=4 fps=58 big_jumps=0 max_step=8 cv_lite=1\n"
        result = run_python(str(SCRIPTS_DIR / "evaluate_probe_log.py"), "--kind", "rect", "-", input_text=log)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("ACCEPT_RECT status=pass", result.stdout)

    def test_missing_probe_summary_fails(self) -> None:
        result = run_python(
            str(SCRIPTS_DIR / "evaluate_probe_log.py"),
            "--kind",
            "rect",
            "-",
            input_text="NO_RECT_RESULT\n",
        )

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("missing RECT_PROBE_DONE", result.stdout)


class MpremoteSnapshotTests(unittest.TestCase):
    def test_unsafe_remote_path_is_rejected(self) -> None:
        result = run_python(
            str(SCRIPTS_DIR / "mpremote_snapshot.py"),
            "--remote",
            "/sdcard/not_snap.jpg",
            "--port",
            "COM1",
            "--dry-run",
        )

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("outside safe prefixes", result.stdout)

    def test_safe_snapshot_dry_run_does_not_require_mpremote(self) -> None:
        result = run_python(
            str(SCRIPTS_DIR / "mpremote_snapshot.py"),
            "--remote",
            "/sdcard/codex_snap.jpg",
            "--port",
            "COM1",
            "--dry-run",
            "--no-break",
            "--reset-after",
            "none",
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("mpremote connect COM1", result.stdout)

    def test_oversized_ksnp_is_rejected_before_decoding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot = Path(temp_dir) / "bad.bin"
            header = b"KSNP" + struct.pack("<IIII", 5000, 480, 3, mpremote_snapshot.LAYOUT_HWC)
            snapshot.write_bytes(header)
            with self.assertRaises(SystemExit) as raised:
                mpremote_snapshot.decode_ksnp(snapshot, None)

        self.assertIn("snapshot shape too large", str(raised.exception))


class SkillValidatorGuardrailTests(unittest.TestCase):
    def test_current_skill_validation_passes(self) -> None:
        cleanup_skill_pycache()
        result = run_python(str(SCRIPTS_DIR / "validate_skill.py"), str(SKILL_ROOT))

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("VALIDATE_SKILL_OK warnings=0", result.stdout)

    def test_repo_only_file_inside_skill_is_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text("repo-only", encoding="utf-8")
            failures: list[str] = []
            validate_skill.check_installable_boundary(root, failures)

        self.assertTrue(failures)
        self.assertIn("repo-only", failures[0])

    def test_long_reference_without_scope_warns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            refs = root / "references"
            refs.mkdir()
            lines = ["# Long Ref", "", "## Contents", "", "- A"]
            lines.extend("line %03d" % index for index in range(120))
            (refs / "long.md").write_text("\n".join(lines), encoding="utf-8")
            warnings: list[str] = []
            validate_skill.check_reference_contents(root, warnings)

        self.assertTrue(any("no early Scope section" in item for item in warnings))


if __name__ == "__main__":
    unittest.main()
