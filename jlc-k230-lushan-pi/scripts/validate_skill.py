#!/usr/bin/env python3
"""Run local preflight checks for the jlc-k230-lushan-pi skill."""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from pathlib import Path


CANMV_FORBIDDEN_NODES = (
    ast.DictComp,
    ast.GeneratorExp,
    ast.IfExp,
    ast.JoinedStr,
    ast.Lambda,
    ast.ListComp,
    ast.SetComp,
)

CANMV_FORBIDDEN_NAMES = {
    ast.DictComp: "dict comprehension",
    ast.GeneratorExp: "generator expression",
    ast.IfExp: "conditional expression",
    ast.JoinedStr: "f-string",
    ast.Lambda: "lambda",
    ast.ListComp: "list comprehension",
    ast.SetComp: "set comprehension",
}

WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"\b[A-Za-z]:\\[^\s`'\"<>|]+")
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
INLINE_LOCAL_DOC_RE = re.compile(
    r"`((?:references/)?(?:SKILL|[A-Za-z0-9_.-]+)\.md(?:#[A-Za-z0-9_-]+)?)`"
)
MARKDOWN_LOCAL_DOC_RE = re.compile(
    r"\[[^\]]+\]\(((?:references/)?(?:SKILL|[A-Za-z0-9_.-]+)\.md(?:#[A-Za-z0-9_-]+)?)\)"
)
MAX_TEMPLATE_EXAMPLES = 16
REPO_ONLY_NAMES = (
    ".github",
    "docs",
    "tests",
    "tools",
    "README.md",
    "AGENT_USAGE.md",
    "CHANGELOG.md",
    "LICENSE",
    "requirements-host.txt",
    "requirements.txt",
    "pyproject.toml",
)


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def collect_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if "__pycache__" in path.parts:
            continue
        if path.is_file() and path.suffix.lower() in suffixes:
            files.append(path)
    return sorted(files)


def check_skill_frontmatter(root: Path, failures: list[str]) -> None:
    skill_md = root / "SKILL.md"
    if not skill_md.exists():
        failures.append("missing SKILL.md")
        return

    text = read_text(skill_md)
    if not text.startswith("---\n"):
        failures.append("SKILL.md missing YAML frontmatter")
        return

    end = text.find("\n---\n", 4)
    if end < 0:
        failures.append("SKILL.md frontmatter is not closed")
        return

    frontmatter = text[4:end]
    if "name: jlc-k230-lushan-pi" not in frontmatter:
        failures.append("SKILL.md frontmatter name is not jlc-k230-lushan-pi")
    if "description:" not in frontmatter:
        failures.append("SKILL.md frontmatter missing description")


def check_version_file(root: Path, failures: list[str]) -> None:
    path = root / "VERSION"
    if not path.exists():
        failures.append("missing VERSION")
        return
    version = read_text(path).strip()
    if not SEMVER_RE.fullmatch(version):
        failures.append("VERSION must use MAJOR.MINOR.PATCH, got: %s" % version)


def check_openai_yaml(root: Path, failures: list[str], warnings: list[str]) -> None:
    yaml_path = root / "agents" / "openai.yaml"
    if not yaml_path.exists():
        warnings.append("agents/openai.yaml is missing")
        return

    text = read_text(yaml_path)
    if "$jlc-k230-lushan-pi" not in text:
        failures.append("agents/openai.yaml default_prompt should mention $jlc-k230-lushan-pi")
    if "display_name:" not in text or "short_description:" not in text:
        failures.append("agents/openai.yaml missing interface display fields")


def check_python_syntax(root: Path, py_files: list[Path], failures: list[str]) -> None:
    for path in py_files:
        try:
            compile(read_text(path), str(path), "exec")
        except SyntaxError as exc:
            failures.append("%s syntax error: %s" % (rel(path, root), exc))


def runtime_metadata(path: Path) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in read_text(path).splitlines()[:12]:
        match = re.match(r"^#\s*@([a-z-]+):\s*(\S.*)$", line)
        if match:
            metadata[match.group(1)] = match.group(2).strip()
    return metadata


def is_board_side_python(root: Path, path: Path) -> bool:
    del root
    return runtime_metadata(path).get("runtime") == "canmv"


def check_runtime_contracts(root: Path, py_files: list[Path], failures: list[str]) -> None:
    for path in py_files:
        rel_path = rel(path, root)
        metadata = runtime_metadata(path)
        is_template = rel_path.startswith("assets/contest-template/")
        is_probe = rel_path.startswith("scripts/probe_") or rel_path == "scripts/smoke_camera_lcd.py"

        if is_template or is_probe:
            if metadata.get("runtime") != "canmv":
                failures.append("%s must declare # @runtime: canmv" % rel_path)
        if is_template:
            for key in ("route", "requires"):
                if not metadata.get(key):
                    failures.append("%s must declare # @%s" % (rel_path, key))

        if metadata.get("runtime") != "canmv":
            continue
        text = read_text(path)
        cleanup_pairs = (
            ("Sensor(", ".stop(", "Sensor.stop"),
            ("Display.init(", "Display.deinit(", "Display.deinit"),
            ("MediaManager.init(", "MediaManager.deinit(", "MediaManager.deinit"),
            ("PipeLine(", ".destroy(", "PipeLine.destroy"),
        )
        for initializer, cleanup, label in cleanup_pairs:
            if initializer in text and cleanup not in text:
                failures.append("%s initializes a resource without %s" % (rel_path, label))


def check_canmv_conservative_style(root: Path, py_files: list[Path], failures: list[str]) -> None:
    for path in py_files:
        if not is_board_side_python(root, path):
            continue
        text = read_text(path)
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            for node_type in CANMV_FORBIDDEN_NODES:
                if isinstance(node, node_type):
                    failures.append(
                        "%s uses %s at line %s"
                        % (rel(path, root), CANMV_FORBIDDEN_NAMES[node_type], getattr(node, "lineno", "?"))
                    )
        if ".format(" in text:
            failures.append("%s uses .format(); prefer %% formatting for final CanMV code" % rel(path, root))


def check_python_documentation_links(root: Path, py_files: list[Path], failures: list[str]) -> None:
    doc_files = collect_files(root, (".md", ".yaml", ".yml"))
    doc_text_parts: list[str] = []
    for path in doc_files:
        doc_text_parts.append(read_text(path))
    doc_text = "\n".join(doc_text_parts).replace("\\", "/")

    for path in py_files:
        rel_path = rel(path, root)
        if rel_path.endswith("/__init__.py"):
            continue
        basename = path.name
        if rel_path not in doc_text and basename not in doc_text:
            failures.append("%s is not referenced by skill docs/metadata" % rel_path)


def markdown_anchor(heading: str) -> str:
    heading = re.sub(r"<[^>]+>", "", heading)
    heading = heading.replace("`", "").strip().lower()
    heading = re.sub(r"[^\w\- ]", "", heading)
    return re.sub(r"\s+", "-", heading)


def document_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    duplicate_counts: dict[str, int] = {}
    for line in read_text(path).splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        base = markdown_anchor(match.group(1))
        if not base:
            continue
        count = duplicate_counts.get(base, 0)
        duplicate_counts[base] = count + 1
        if count:
            anchors.add("%s-%d" % (base, count))
        else:
            anchors.add(base)
    return anchors


def resolve_local_doc(root: Path, target: str) -> tuple[Path, str]:
    path_text, separator, anchor = target.partition("#")
    if path_text == "SKILL.md":
        path = root / path_text
    elif path_text.startswith("references/"):
        path = root / Path(path_text)
    else:
        path = root / "references" / path_text
    if not separator:
        anchor = ""
    return path, anchor.lower()


def check_document_links(root: Path, failures: list[str]) -> None:
    docs = [root / "SKILL.md"]
    docs.extend(sorted((root / "references").glob("*.md")))
    anchors_by_path: dict[Path, set[str]] = {}

    for source in docs:
        if not source.exists():
            continue
        text = read_text(source)
        targets = INLINE_LOCAL_DOC_RE.findall(text)
        targets.extend(MARKDOWN_LOCAL_DOC_RE.findall(text))
        for target in targets:
            path_text = target.partition("#")[0]
            if path_text in REPO_ONLY_NAMES:
                continue
            path, anchor = resolve_local_doc(root, target)
            if not path.exists():
                failures.append("%s references missing document: %s" % (rel(source, root), target))
                continue
            if not anchor:
                continue
            if path not in anchors_by_path:
                anchors_by_path[path] = document_anchors(path)
            if anchor not in anchors_by_path[path]:
                failures.append("%s references missing anchor: %s" % (rel(source, root), target))


def check_reference_contents(root: Path, failures: list[str]) -> None:
    for path in sorted((root / "references").glob("*.md")):
        lines = read_text(path).splitlines()
        head = "\n".join(lines[:40])
        if "## Contents" not in head:
            failures.append("%s has no Contents section in its first 40 lines" % rel(path, root))
        if "## Scope" not in head:
            failures.append("%s has no Scope section in its first 40 lines" % rel(path, root))


def check_template_inventory(root: Path, warnings: list[str]) -> None:
    examples_dir = root / "assets" / "contest-template" / "examples"
    if not examples_dir.exists():
        return

    examples = sorted(path for path in examples_dir.glob("*.py") if path.is_file())
    if len(examples) > MAX_TEMPLATE_EXAMPLES:
        warnings.append(
            "template example count %d exceeds guardrail %d; move one-off patterns to references"
            % (len(examples), MAX_TEMPLATE_EXAMPLES)
        )

    contest_text = read_text(root / "references" / "contest-patterns.md")
    skill_text = read_text(root / "SKILL.md")
    combined = contest_text + "\n" + skill_text
    if "Template Admission Rules" not in contest_text:
        warnings.append("contest-patterns.md missing Template Admission Rules")

    for path in examples:
        if path.name not in combined:
            warnings.append("%s is not listed in SKILL.md or contest-patterns.md" % rel(path, root))


def check_installable_boundary(root: Path, failures: list[str]) -> None:
    for name in REPO_ONLY_NAMES:
        if (root / name).exists():
            failures.append("repo-only file or directory must not be inside installable skill: %s" % name)


def check_actuator_boundaries(root: Path, warnings: list[str]) -> None:
    contest_text = read_text(root / "references" / "contest-patterns.md")
    zdt_text = read_text(root / "references" / "zdt-stepper-gimbal-patterns.md")
    if "Do not emit ZDT command frames in final code" not in zdt_text:
        warnings.append("zdt-stepper-gimbal-patterns.md should explicitly forbid ZDT frames before protocol confirmation")
    if "Do not copy motor-specific command frames" not in contest_text:
        warnings.append("contest-patterns.md should keep generic actuator guidance separate from motor-specific frames")


def check_deployment_mode_gate(root: Path, failures: list[str]) -> None:
    skill_text = read_text(root / "SKILL.md")
    offline_text = read_text(root / "references" / "offline-run-patterns.md")
    mpremote_text = read_text(root / "references" / "mpremote-debug-workflows.md")

    if "default to `STANDARD`" not in skill_text:
        failures.append("SKILL.md must keep STANDARD as the default board-write mode")
    if "`QUICK_PATCH` is a strict whitelist exception" not in offline_text:
        failures.append("offline-run-patterns.md must keep QUICK_PATCH as a strict whitelist exception")
    if "Use `QUICK_PATCH` only when every condition below is true" not in offline_text:
        failures.append("offline-run-patterns.md must require every QUICK_PATCH gate")
    if "Enter `RECOVERY` only after `QUICK_PATCH` or `STANDARD` fails once" not in offline_text:
        failures.append("offline-run-patterns.md must keep RECOVERY failure-triggered")
    if "offline-run-patterns.md#deployment-mode-gate" not in mpremote_text:
        failures.append("mpremote-debug-workflows.md must route board writes through the deployment mode gate")


def check_raw_repl_deployer(root: Path, failures: list[str]) -> None:
    path = root / "scripts" / "raw_repl_deploy.py"
    if not path.exists():
        failures.append("scripts/raw_repl_deploy.py is missing")
        return

    text = read_text(path)
    required_markers = (
        "from run_canmv_raw_repl import",
        "a2b_base64(b'",
        ".codex.tmp",
        "hashlib.sha256",
        "os.replace",
        "RAW_DEPLOY_RESET_ONCE",
    )
    for marker in required_markers:
        if marker not in text:
            failures.append("raw_repl_deploy.py missing safety marker: %s" % marker)


def check_host_python_resolution(root: Path, failures: list[str]) -> None:
    host_tools = read_text(root / "scripts" / "_host_tools.py")
    workflow = read_text(root / "references" / "mpremote-debug-workflows.md")

    required_helpers = (
        "discover_python_candidates",
        "probe_python_modules",
        "find_compatible_host_python",
        "ensure_host_python",
        "HOST_REEXEC_DEPTH_ENV",
        "send_ctrl_c_burst",
        "send_soft_reset",
        "mpremote_host_modules",
    )
    for marker in required_helpers:
        if marker not in host_tools:
            failures.append("_host_tools.py missing host-Python marker: %s" % marker)
    script_names = (
        "run_board_probe.py",
        "run_canmv_raw_repl.py",
        "mpremote_deploy.py",
        "mpremote_snapshot.py",
        "raw_repl_deploy.py",
    )
    script_texts: dict[str, str] = {}
    for name in script_names:
        path = root / "scripts" / name
        if not path.exists():
            failures.append("missing host script: scripts/%s" % name)
            continue
        text = read_text(path)
        script_texts[name] = text
        if "--host-python" not in text or "ensure_host_python" not in text:
            failures.append("%s must use bounded host-Python resolution" % name)

    raw_runner = script_texts.get("run_canmv_raw_repl.py", "")
    for marker in ("def require_serial", "def print_ports", "def resolve_port"):
        if marker in raw_runner:
            failures.append("run_canmv_raw_repl.py duplicates shared host helper: %s" % marker)

    for name in ("mpremote_deploy.py", "mpremote_snapshot.py"):
        text = script_texts.get(name, "")
        for marker in ("def break_main_loop", "def soft_reset"):
            if marker in text:
                failures.append("%s duplicates shared serial reset helper: %s" % (name, marker))

    if "## Host Python Resolution" not in workflow:
        failures.append("mpremote-debug-workflows.md missing Host Python Resolution guidance")
    if "never installs packages" not in workflow:
        failures.append("host-Python workflow must forbid automatic package installation")


def check_board_probe_entry(root: Path, failures: list[str]) -> None:
    path = root / "scripts" / "run_board_probe.py"
    if not path.exists():
        failures.append("scripts/run_board_probe.py is missing")
        return

    text = read_text(path)
    for marker in ("PROBE_MODES", "run_canmv_raw_repl.py", "evaluate_probe_log.py", "writes_sdcard=0"):
        if marker not in text:
            failures.append("run_board_probe.py missing self-contained probe marker: %s" % marker)

    skill_text = read_text(root / "SKILL.md")
    if "scripts/run_board_probe.py" not in skill_text:
        failures.append("SKILL.md must document scripts/run_board_probe.py as the board-test entry")

    for doc in collect_files(root, (".md",)):
        if doc.name == "maintenance.md":
            continue
        if "tools/test.ps1 -Board" in read_text(doc):
            failures.append("%s depends on repository-only board tooling" % rel(doc, root))


def check_reference_boundaries(root: Path, failures: list[str]) -> None:
    legacy = root / "references" / "user-example-patterns.md"
    if legacy.exists():
        failures.append("user-example-patterns.md must stay merged into local-code-examples.md")

    for doc in collect_files(root, (".md", ".yaml", ".yml")):
        if "user-example-patterns.md" in read_text(doc):
            failures.append("%s references removed user-example-patterns.md" % rel(doc, root))

    rectangle_text = read_text(root / "references" / "contest-2025-rectangle-patterns.md")
    for marker in ("F6", "F1/FC", "motion ACK"):
        if marker in rectangle_text:
            failures.append("rectangle reference contains motor-protocol marker: %s" % marker)
    if "actuator-neutral observation" not in rectangle_text:
        failures.append("rectangle reference must end at an actuator-neutral observation")

    yolo_text = read_text(root / "references" / "yolo-module-patterns.md")
    for marker in ("exec(code)", "replacements = ("):
        if marker in yolo_text:
            failures.append("YOLO reference duplicates launcher implementation: %s" % marker)


def load_extra_local_path_patterns(config_path: str | None, warnings: list[str]) -> list[str]:
    if not config_path:
        return []

    path = Path(config_path).expanduser()
    if not path.exists():
        warnings.append("local path config does not exist: %s" % path)
        return []

    patterns: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def check_no_local_paths(root: Path, failures: list[str], extra_patterns: list[str]) -> None:
    checked_suffixes = (".md", ".py", ".yaml", ".yml")
    for path in collect_files(root, checked_suffixes):
        text = read_text(path)
        for match in WINDOWS_ABSOLUTE_PATH_RE.finditer(text):
            failures.append("%s contains Windows absolute path: %s" % (rel(path, root), match.group(0)))
        for pattern in extra_patterns:
            if pattern in text:
                failures.append("%s contains configured local path pattern: %s" % (rel(path, root), pattern))


def check_no_pycache(root: Path, failures: list[str]) -> None:
    for current, dirnames, _filenames in os.walk(root):
        if "__pycache__" in dirnames:
            failures.append("found __pycache__ under %s" % rel(Path(current) / "__pycache__", root))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the jlc-k230-lushan-pi skill package.")
    parser.add_argument("skill_root", nargs="?", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--strict-warnings", action="store_true", help="treat warnings as failures")
    parser.add_argument(
        "--local-path-config",
        default=os.environ.get("JLC_K230_LOCAL_PATH_CONFIG"),
        help="optional UTF-8 file outside the skill; each non-comment line is a literal local path pattern to reject",
    )
    args = parser.parse_args()

    root = Path(args.skill_root).resolve()
    failures: list[str] = []
    warnings: list[str] = []

    if not root.exists():
        print("skill root does not exist: %s" % root)
        return 2

    extra_local_path_patterns = load_extra_local_path_patterns(args.local_path_config, warnings)
    py_files = collect_files(root, (".py",))
    check_skill_frontmatter(root, failures)
    check_version_file(root, failures)
    check_openai_yaml(root, failures, warnings)
    check_python_syntax(root, py_files, failures)
    check_runtime_contracts(root, py_files, failures)
    check_canmv_conservative_style(root, py_files, failures)
    check_python_documentation_links(root, py_files, failures)
    check_document_links(root, failures)
    check_reference_contents(root, failures)
    check_template_inventory(root, warnings)
    check_installable_boundary(root, failures)
    check_actuator_boundaries(root, warnings)
    check_deployment_mode_gate(root, failures)
    check_raw_repl_deployer(root, failures)
    check_host_python_resolution(root, failures)
    check_board_probe_entry(root, failures)
    check_reference_boundaries(root, failures)
    check_no_local_paths(root, failures, extra_local_path_patterns)
    check_no_pycache(root, failures)

    print("SKILL_ROOT %s" % root)
    print("PY_FILES %d" % len(py_files))

    for item in warnings:
        print("WARN %s" % item)
    for item in failures:
        print("FAIL %s" % item)

    if failures or (warnings and args.strict_warnings):
        print("VALIDATE_SKILL_FAIL failures=%d warnings=%d" % (len(failures), len(warnings)))
        return 1

    print("VALIDATE_SKILL_OK warnings=%d" % len(warnings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
