from __future__ import annotations

import hashlib
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
import raw_repl_deploy  # noqa: E402
import validate_skill  # noqa: E402
import _host_tools  # noqa: E402


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
        self.assertIn("connect COM1", result.stdout)

    def test_oversized_ksnp_is_rejected_before_decoding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot = Path(temp_dir) / "bad.bin"
            header = b"KSNP" + struct.pack("<IIII", 5000, 480, 3, mpremote_snapshot.LAYOUT_HWC)
            snapshot.write_bytes(header)
            with self.assertRaises(SystemExit) as raised:
                mpremote_snapshot.decode_ksnp(snapshot, None)

        self.assertIn("snapshot shape too large", str(raised.exception))


class RawReplDeployTests(unittest.TestCase):
    def test_remote_path_traversal_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            raw_repl_deploy.normalize_remote_path("/sdcard/../main.py", "main.py")

    def test_generated_base64_decoder_receives_bytes(self) -> None:
        code = raw_repl_deploy.board_append_code("/sdcard/main.py.codex.tmp", b"\x00abc\xff")

        self.assertIn("a2b_base64(b'", code)
        self.assertNotIn("a2b_base64('", code)

    def test_verify_output_parser(self) -> None:
        digest = "ab" * 32
        size, parsed_digest = raw_repl_deploy.parse_verify_output(
            "raw output\nRAW_DEPLOY_VERIFY size=513 sha256=%s\n" % digest
        )

        self.assertEqual(size, 513)
        self.assertEqual(parsed_digest, digest)

    def test_binary_dry_run_reports_size_hash_and_one_reset(self) -> None:
        payload = b"\x00\xffK230\r\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "main.py"
            source.write_bytes(payload)
            result = run_python(
                str(SCRIPTS_DIR / "raw_repl_deploy.py"),
                str(source),
                "--remote",
                "/sdcard/main.py",
                "--dry-run",
                "--host-python",
                "missing-python-is-ignored-for-dry-run",
            )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("DEPLOY_MODE=STANDARD", result.stdout)
        self.assertIn("bytes=%d" % len(payload), result.stdout)
        self.assertIn("sha256=%s" % hashlib.sha256(payload).hexdigest(), result.stdout)
        self.assertIn("reset=True", result.stdout)
        self.assertIn("RAW_DEPLOY_DRY_RUN", result.stdout)

    def test_soft_reset_sends_one_ctrl_d(self) -> None:
        class FakeSerial:
            def __init__(self) -> None:
                self.writes: list[bytes] = []

            def write(self, data: bytes) -> None:
                self.writes.append(data)

            def flush(self) -> None:
                pass

        serial = FakeSerial()
        raw_repl_deploy.soft_reset_once(serial)

        self.assertEqual(serial.writes, [b"\x02", b"\x04"])


class HostPythonResolutionTests(unittest.TestCase):
    def test_python_launcher_paths_are_parsed(self) -> None:
        output = " -V:3.12 * C:\\Runtime A\\python.exe\n -V:3.11 C:\\RuntimeB\\python.exe\n"

        paths = _host_tools.parse_py_launcher_paths(output)

        self.assertEqual(paths, ["C:\\Runtime A\\python.exe", "C:\\RuntimeB\\python.exe"])

    def test_explicit_compatible_python_is_selected(self) -> None:
        selected, checked = _host_tools.find_compatible_host_python(("json",), sys.executable)

        self.assertIsNotNone(selected)
        self.assertTrue(_host_tools.same_executable(selected or "", sys.executable))
        self.assertEqual(len(checked), 1)

    def test_explicit_python_does_not_fall_through(self) -> None:
        selected, checked = _host_tools.find_compatible_host_python(
            ("module_that_must_not_exist_for_k230_test",),
            sys.executable,
        )

        self.assertIsNone(selected)
        self.assertEqual(len(checked), 1)
        self.assertTrue(checked[0][1])


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
