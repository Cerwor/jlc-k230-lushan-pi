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

LOCAL_PATH_PATTERNS = [
    re.compile(r"C:\\Users\\Cerwor", re.IGNORECASE),
    re.compile(r"E:\\MyData", re.IGNORECASE),
    re.compile(r"E:\\Codex_WorkSpace", re.IGNORECASE),
]


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


def check_no_local_paths(root: Path, failures: list[str]) -> None:
    checked_suffixes = (".md", ".py", ".yaml", ".yml")
    for path in collect_files(root, checked_suffixes):
        text = read_text(path)
        for pattern in LOCAL_PATH_PATTERNS:
            if pattern.search(text):
                failures.append("%s contains local machine path pattern %s" % (rel(path, root), pattern.pattern))


def check_no_pycache(root: Path, failures: list[str]) -> None:
    for current, dirnames, _filenames in os.walk(root):
        if "__pycache__" in dirnames:
            failures.append("found __pycache__ under %s" % rel(Path(current) / "__pycache__", root))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the jlc-k230-lushan-pi skill package.")
    parser.add_argument("skill_root", nargs="?", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--strict-warnings", action="store_true", help="treat warnings as failures")
    args = parser.parse_args()

    root = Path(args.skill_root).resolve()
    failures: list[str] = []
    warnings: list[str] = []

    if not root.exists():
        print("skill root does not exist: %s" % root)
        return 2

    py_files = collect_files(root, (".py",))
    check_skill_frontmatter(root, failures)
    check_openai_yaml(root, failures, warnings)
    check_python_syntax(root, py_files, failures)
    check_canmv_conservative_style(root, py_files, failures)
    check_python_documentation_links(root, py_files, failures)
    check_reference_contents(root, warnings)
    check_no_local_paths(root, failures)
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
