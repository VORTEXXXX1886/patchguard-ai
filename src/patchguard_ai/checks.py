from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path

from patchguard_ai.config import PatchguardConfig


def _git_changed_files(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except FileNotFoundError:
        return []


def _matches_any(patterns: list[str], file_path: str) -> bool:
    return any(
        fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(file_path, f"{pattern}/**")
        for pattern in patterns
    )


def _check_allowed_paths(changed_files: list[str], allowed_paths: list[str]) -> tuple[bool, list[str]]:
    if not allowed_paths:
        return True, []

    violations: list[str] = []
    for file_path in changed_files:
        if not _matches_any(allowed_paths, file_path):
            violations.append(file_path)
    return not violations, violations


def _check_required_files(root: Path, required_files: list[str]) -> tuple[bool, list[str]]:
    missing: list[str] = []
    for relative_path in required_files:
        target = (root / relative_path).resolve()
        if not target.exists():
            missing.append(relative_path)
    return not missing, missing


def run_command(command: str, cwd: Path) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        combined = "\n".join(part for part in [completed.stdout, completed.stderr] if part)
        return completed.returncode == 0, combined.strip()
    except Exception as exc:
        return False, str(exc)


def run_checks(root: Path, config: PatchguardConfig) -> dict:
    changed_files = _git_changed_files(root)
    allowed_ok, scope_violations = _check_allowed_paths(changed_files, config.allowed_paths)
    required_ok, missing_files = _check_required_files(root, config.required_files)

    command_results: list[dict[str, str | bool]] = []
    for command in config.commands:
        success, output = run_command(command, root)
        command_results.append({
            "command": command,
            "passed": success,
            "output": output,
        })

    check_passed = allowed_ok and required_ok and all(item["passed"] for item in command_results)

    return {
        "path": str(root),
        "passed": check_passed,
        "changed_files": changed_files,
        "scope_violations": scope_violations,
        "missing_files": missing_files,
        "command_results": command_results,
        "summary": {
            "allowed_paths_ok": allowed_ok,
            "required_files_ok": required_ok,
            "commands_ok": all(item["passed"] for item in command_results),
        },
    }
