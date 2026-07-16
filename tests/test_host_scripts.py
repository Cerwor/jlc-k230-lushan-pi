from __future__ import annotations

import hashlib
import io
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "jlc-k230-lushan-pi"
SCRIPTS_DIR = SKILL_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import mpremote_snapshot  # noqa: E402
import raw_repl_deploy  # noqa: E402
import run_board_probe  # noqa: E402
import run_canmv_raw_repl  # noqa: E402
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

    def test_invalid_manifest_json_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package = Path(temp_dir)
            (package / "model_manifest.json").write_text("{broken", encoding="utf-8")
            result = run_python(str(SCRIPTS_DIR / "check_model_package.py"), str(package))

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("cannot read manifest", result.stdout)

    def test_empty_labels_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package = Path(temp_dir)
            write_valid_model_package(package)
            (package / "labels.txt").write_text("\n\n", encoding="utf-8")
            result = run_python(str(SCRIPTS_DIR / "check_model_package.py"), str(package))

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("labels file is empty", result.stdout)


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

    def test_rect_warning_fails_only_in_strict_mode(self) -> None:
        log = "RECT_PROBE_DONE frames=300 hits=280 misses=20 fps=55 big_jumps=0 max_step=8 cv_lite=1\n"
        normal = run_python(
            str(SCRIPTS_DIR / "evaluate_probe_log.py"),
            "--kind",
            "rect",
            "-",
            input_text=log,
        )
        strict = run_python(
            str(SCRIPTS_DIR / "evaluate_probe_log.py"),
            "--kind",
            "rect",
            "--strict",
            "-",
            input_text=log,
        )

        self.assertEqual(normal.returncode, 0, normal.stdout)
        self.assertIn("ACCEPT_RECT status=warn", normal.stdout)
        self.assertEqual(strict.returncode, 1, strict.stdout)
        self.assertIn("ACCEPT_RECT status=fail", strict.stdout)

    def test_truncated_resource_scan_warns(self) -> None:
        log = (
            "KMODELS count=1\n"
            "YOLO_PY_EXAMPLES count=1\n"
            "RESOURCE_PROBE_DONE dirs=120 truncated=1\n"
        )
        result = run_python(
            str(SCRIPTS_DIR / "evaluate_probe_log.py"),
            "--kind",
            "resources",
            "-",
            input_text=log,
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("ACCEPT_RESOURCES status=warn", result.stdout)
        self.assertIn("scan was truncated", result.stdout)

    def test_lifecycle_probe_requires_all_three_cycles(self) -> None:
        good_log = (
            "LIFECYCLE_PROBE_DONE cycles=3 passed=3 "
            "mem_start=2000000 mem_end=1950000 min_mem=1900000\n"
        )
        bad_log = (
            "LIFECYCLE_PROBE_DONE cycles=3 passed=2 "
            "mem_start=2000000 mem_end=1950000 min_mem=1900000\n"
        )
        good = run_python(
            str(SCRIPTS_DIR / "evaluate_probe_log.py"),
            "--kind",
            "lifecycle",
            "-",
            input_text=good_log,
        )
        bad = run_python(
            str(SCRIPTS_DIR / "evaluate_probe_log.py"),
            "--kind",
            "lifecycle",
            "-",
            input_text=bad_log,
        )

        self.assertEqual(good.returncode, 0, good.stdout)
        self.assertIn("ACCEPT_LIFECYCLE status=pass", good.stdout)
        self.assertEqual(bad.returncode, 1, bad.stdout)
        self.assertIn("ACCEPT_LIFECYCLE status=fail", bad.stdout)


class RawReplHandshakeTests(unittest.TestCase):
    def test_enter_raw_repl_accepts_banner(self) -> None:
        output = io.StringIO()
        with patch.object(
            run_canmv_raw_repl,
            "write_and_read",
            side_effect=(b">>> ", b"raw REPL; CTRL-B to exit\r\n>"),
        ) as mocked:
            with redirect_stdout(output):
                run_canmv_raw_repl.enter_raw_repl(object(), "COM14", 2000000)

        self.assertEqual(mocked.call_count, 2)
        self.assertIn("raw REPL", output.getvalue())

    def test_enter_raw_repl_reports_no_serial_bytes(self) -> None:
        with patch.object(run_canmv_raw_repl, "RAW_REPL_ATTEMPTS", 1):
            with patch.object(run_canmv_raw_repl, "write_and_read", return_value=b""):
                with patch.object(run_canmv_raw_repl, "read_available", return_value=b""):
                    with patch.object(run_canmv_raw_repl.time, "sleep"):
                        with self.assertRaises(run_canmv_raw_repl.RawReplEnterError) as raised:
                            run_canmv_raw_repl.enter_raw_repl(object(), "COM14", 2000000)

        self.assertIn("No serial bytes were received from COM14", str(raised.exception))


class MpremoteDeployTests(unittest.TestCase):
    def test_deploy_dry_run_needs_no_board(self) -> None:
        source = SKILL_ROOT / "assets" / "contest-template" / "main.py"
        result = run_python(
            str(SCRIPTS_DIR / "mpremote_deploy.py"),
            str(source),
            "--port",
            "COM1",
            "--dry-run",
            "--no-break",
            "--reset",
            "none",
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("copy main.py -> :/sdcard/main.py", result.stdout)
        self.assertIn("skip reset", result.stdout)


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


class BoardProbeRunnerTests(unittest.TestCase):
    def test_all_core_has_three_bounded_probes(self) -> None:
        probes = run_board_probe.PROBE_MODES["all-core"]

        self.assertEqual(len(probes), 3)
        self.assertEqual(probes[0][0], "smoke_camera_lcd.py")

    def test_rect_mode_has_automatic_assessment(self) -> None:
        probes = run_board_probe.PROBE_MODES["rect-target"]

        self.assertEqual(probes, (("probe_cvlite_rectangle_target.py", "rect"),))

    def test_resource_cycle_mode_has_lifecycle_assessment(self) -> None:
        probes = run_board_probe.PROBE_MODES["resource-cycle"]

        self.assertEqual(probes, (("probe_resource_lifecycle.py", "lifecycle"),))

    def test_dry_run_needs_no_serial_or_board(self) -> None:
        result = run_python(
            str(SCRIPTS_DIR / "run_board_probe.py"),
            "--vision",
            "rect-target",
            "--dry-run",
            "--host-python",
            "missing-python-is-ignored-for-dry-run",
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("probe_cvlite_rectangle_target.py", result.stdout)
        self.assertIn("ASSESSMENT_PLANNED kind=rect", result.stdout)
        self.assertIn("writes_sdcard=0", result.stdout)


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

    def test_invalid_version_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "VERSION").write_text("release-one\n", encoding="utf-8")
            failures: list[str] = []
            validate_skill.check_version_file(root, failures)

        self.assertTrue(any("MAJOR.MINOR.PATCH" in item for item in failures))

    def test_reference_without_scope_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            refs = root / "references"
            refs.mkdir()
            lines = ["# Ref", "", "## Contents", "", "- A"]
            (refs / "long.md").write_text("\n".join(lines), encoding="utf-8")
            failures: list[str] = []
            validate_skill.check_reference_contents(root, failures)

        self.assertTrue(any("no Scope section" in item for item in failures))

    def test_missing_local_document_anchor_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            refs = root / "references"
            refs.mkdir()
            (root / "SKILL.md").write_text(
                "Read `references/topic.md#missing-heading`.\n",
                encoding="utf-8",
            )
            (refs / "topic.md").write_text(
                "# Topic\n\n## Scope\n\nScope.\n\n## Contents\n\n- Existing\n\n## Existing\n",
                encoding="utf-8",
            )
            failures: list[str] = []
            validate_skill.check_document_links(root, failures)

        self.assertTrue(any("missing anchor" in item for item in failures))

    def test_canmv_sensor_without_cleanup_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            template = root / "assets" / "contest-template"
            template.mkdir(parents=True)
            script = template / "main.py"
            script.write_text(
                "# @runtime: canmv\n"
                "# @route: bring-up\n"
                "# @requires: camera\n\n"
                "from media.sensor import Sensor\n"
                "sensor = Sensor()\n",
                encoding="utf-8",
            )
            failures: list[str] = []
            validate_skill.check_runtime_contracts(root, [script], failures)

        self.assertTrue(any("without Sensor.stop" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
