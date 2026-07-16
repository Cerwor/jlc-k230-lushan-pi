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
MAX_TEMPLATE_EXAMPLES = 16
REPO_ONLY_NAMES = (
    ".github",
    "docs",
    "tests",
    "tools",
    "README.md",
    "AGENT_USAGE.md",
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


def is_board_side_python(root: Path, path: Path) -> bool:
    rel_path = rel(path, root)
    if rel_path.startswith("assets/contest-template/"):
        return True
    if rel_path in (
        "scripts/probe_board_resources.py",
        "scripts/probe_circle_target.py",
        "scripts/probe_cvlite_rectangle_target.py",
        "scripts/probe_k230_sensor_init.py",
        "scripts/probe_otsu_threshold.py",
        "scripts/probe_uart2_loopback.py",
        "scripts/probe_yolo_runtime.py",
        "scripts/smoke_camera_lcd.py",
    ):
        return True
    return False


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


def check_reference_contents(root: Path, warnings: list[str]) -> None:
    for path in sorted((root / "references").glob("*.md")):
        lines = read_text(path).splitlines()
        if len(lines) > 100:
            head = "\n".join(lines[:40])
            if "## Contents" not in head:
                warnings.append("%s is longer than 100 lines but has no early Contents section" % rel(path, root))
            if "## Scope" not in head:
                warnings.append("%s is longer than 100 lines but has no early Scope section" % rel(path, root))


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
    mpremote_deploy = read_text(root / "scripts" / "mpremote_deploy.py")
    raw_deploy = read_text(root / "scripts" / "raw_repl_deploy.py")
    workflow = read_text(root / "references" / "mpremote-debug-workflows.md")

    required_helpers = (
        "discover_python_candidates",
        "probe_python_modules",
        "find_compatible_host_python",
        "ensure_host_python",
        "HOST_REEXEC_DEPTH_ENV",
    )
    for marker in required_helpers:
        if marker not in host_tools:
            failures.append("_host_tools.py missing host-Python marker: %s" % marker)
    for name, text in (("mpremote_deploy.py", mpremote_deploy), ("raw_repl_deploy.py", raw_deploy)):
        if "--host-python" not in text or "ensure_host_python" not in text:
            failures.append("%s must use bounded host-Python resolution" % name)
    if "## Host Python Resolution" not in workflow:
        failures.append("mpremote-debug-workflows.md missing Host Python Resolution guidance")
    if "never installs packages" not in workflow:
        failures.append("host-Python workflow must forbid automatic package installation")


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
    check_openai_yaml(root, failures, warnings)
    check_python_syntax(root, py_files, failures)
    check_canmv_conservative_style(root, py_files, failures)
    check_python_documentation_links(root, py_files, failures)
    check_reference_contents(root, warnings)
    check_template_inventory(root, warnings)
    check_installable_boundary(root, failures)
    check_actuator_boundaries(root, warnings)
    check_deployment_mode_gate(root, failures)
    check_raw_repl_deployer(root, failures)
    check_host_python_resolution(root, failures)
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
