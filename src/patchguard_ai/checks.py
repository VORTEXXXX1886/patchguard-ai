from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path

from patchguard_ai.config import PatchguardConfig


class GitError(RuntimeError):
    """Raised when the requested git repository cannot be inspected."""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitError("Git executable was not found") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or f"git {' '.join(args)} failed"
        raise GitError(detail)
    return result


def _nul_paths(output: str) -> list[str]:
    return [path for path in output.split("\0") if path]


def _git_status_paths(root: Path) -> list[str]:
    result = _git(root, "status", "--porcelain")
    files: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        status = line[:2]
        path_part = line[3:]

        if " -> " in path_part:
            _, new_path = path_part.split(" -> ", 1)
            files.append(new_path.strip())
            continue

        if status.startswith("??"):
            files.append(path_part.strip())
            continue

        if status.strip():
            files.append(path_part.strip())

    return [item for item in files if item]


def _git_changed_files(root: Path, base: str | None = None) -> list[str]:
    """Return changed file paths for the worktree, optionally comparing to a base ref.

    Without ``base``, we use `git status --porcelain` because it captures staged,
    unstaged, and untracked files. With ``base``, we also include files changed
    between the base and HEAD, which makes PR-style comparisons possible.
    """
    _git(root, "rev-parse", "--show-toplevel")

    files: list[str] = []
    if base:
        # Compare the requested base ref to the current HEAD. This is useful for PR
        # or branch review flows where the relevant patch is the delta since a target.
        try:
            base_diff = _git(root, "diff", "--name-only", "-z", f"{base}...HEAD")
            files.extend(_nul_paths(base_diff.stdout))
        except GitError:
            # The base ref may not exist yet; in that case we fall back to worktree status.
            pass

    files.extend(_git_status_paths(root))
    return list(dict.fromkeys(files))


def _matches_any(patterns: list[str], file_path: str) -> bool:
    return any(
        fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(file_path, f"{pattern}/**")
        for pattern in patterns
    )


def _check_allowed_paths(changed_files: list[str], allowed_paths: list[str]) -> tuple[bool, list[str]]:
    if not allowed_paths:
        return True, []

    violations = [
        file_path for file_path in changed_files if not _matches_any(allowed_paths, file_path)
    ]
    return not violations, violations


def _check_required_files(root: Path, required_files: list[str]) -> tuple[bool, list[str]]:
    missing = [
        relative_path for relative_path in required_files if not (root / relative_path).resolve().exists()
    ]
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
    except Exception as exc:  # pragma: no cover - defensive path
        return False, str(exc)


def run_checks(root: Path, config: PatchguardConfig, base: str | None = None) -> dict:
    git_error: str | None = None
    try:
        changed_files = _git_changed_files(root, base)
    except GitError as exc:
        changed_files = []
        git_error = str(exc)

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

    commands_ok = all(item["passed"] for item in command_results)
    git_ok = git_error is None
    passed = git_ok and allowed_ok and required_ok and commands_ok

    return {
        "path": str(root),
        "base": base,
        "passed": passed,
        "git_error": git_error,
        "changed_files": changed_files,
        "scope_violations": scope_violations,
        "missing_files": missing_files,
        "command_results": command_results,
        "summary": {
            "git_ok": git_ok,
            "allowed_paths_ok": allowed_ok,
            "required_files_ok": required_ok,
            "commands_ok": commands_ok,
        },
    }
